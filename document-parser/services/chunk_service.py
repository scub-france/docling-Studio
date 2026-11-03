"""Chunk service — canonical chunk lifecycle for a document (#256).

Sits between the API layer and the chunk / chunk_edit / chunk_push
repositories. Owns the invariants of the canonical chunkset:

- ordering by `sequence` (dense ascending, gaps allowed after split)
- soft-delete (audit log keeps before/after pointers valid)
- atomic mutation + audit row (one ChunkEdit per mutation)
- promotion from the first completed analysis (idempotent)

Re-uses `DocumentChunker` for rechunk (same port that
`AnalysisService.rechunk` uses), so chunking strategy logic is not
duplicated.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain import chunk_editing, hashing
from domain.chunk_serialization import (
    chunk_from_dict,
    chunk_to_audit_dict,
    chunk_to_ingestion_dict,
)
from domain.models import Chunk, ChunkEdit, ChunkPush, Document, DocumentStoreLink
from domain.value_objects import ChunkEditAction, ChunkingOptions
from services.errors import ServiceError
from services.navigation_errors import DocumentNotFoundError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from domain.ports import (
        AnalysisRepository,
        ChunkEditRepository,
        ChunkPushRepository,
        ChunkRepository,
        DocumentChunker,
        DocumentRepository,
        DocumentStoreLinkRepository,
        StoreRepository,
    )
    from services.ingestion_service import IngestionService
    from services.store_backend_resolver import StoreBackendResolver

logger = logging.getLogger(__name__)

# Sentinel for "not yet probed" in `list_pushes`'s store-name cache.
# Distinct from None (which means "store row deleted after the push").
_UNSET = object()


# ---------------------------------------------------------------------------
# Errors — carry the HTTP status the API layer answers with (`ServiceError`).
# An unknown document raises the shared `DocumentNotFoundError` (404).
# ---------------------------------------------------------------------------


class ChunkServiceError(ServiceError):
    http_status = 400


class ChunkNotFoundError(ChunkServiceError):
    http_status = 404


class ChunkConflictError(ChunkServiceError):
    http_status = 409


class ChunkValidationError(ChunkServiceError):
    http_status = 400


# Why the domain refused an edit → the error the API answers it with.
_REFUSALS: dict[type[chunk_editing.ChunkEditingError], type[ChunkServiceError]] = {
    chunk_editing.InvalidChunkEditError: ChunkValidationError,
    chunk_editing.UnknownChunkError: ChunkNotFoundError,
    chunk_editing.NonContiguousMergeError: ChunkConflictError,
}


@contextmanager
def _refusals_as_service_errors() -> Iterator[None]:
    try:
        yield
    except chunk_editing.ChunkEditingError as exc:
        raise _REFUSALS[type(exc)](str(exc)) from exc


async def require_document(documents: DocumentRepository, document_id: str) -> Document:
    """The document, or the shared 404 — the guard every chunk use case opens with."""
    doc = await documents.find_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document not found: {document_id}")
    return doc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ChunkService:
    """Orchestrates canonical chunk operations for a document."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_edit_repo: ChunkEditRepository,
        chunk_push_repo: ChunkPushRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        chunker: DocumentChunker | None = None,
        ingestion_service: IngestionService | None = None,
        store_repo: StoreRepository | None = None,
        link_repo: DocumentStoreLinkRepository | None = None,
        backend_resolver: StoreBackendResolver | None = None,
        actor: str = "user",
    ) -> None:
        self._chunks = chunk_repo
        self._edits = chunk_edit_repo
        self._pushes = chunk_push_repo
        self._documents = document_repo
        self._analyses = analysis_repo
        self._chunker = chunker
        self._ingestion = ingestion_service
        # Optional — used by `push_to_store` to resolve the slug coming
        # from the API to the actual `stores.id` (the chunk_pushes FK).
        # When None, push_to_store falls back to using the passed value
        # verbatim (legacy callers may already pass an id).
        self._stores = store_repo
        # Optional — used by `push_to_store` to upsert the live
        # `document_store_links` row that drives the per-store state
        # badges in the UI (Ingested / Stale / Failed). Without it the
        # audit row in `chunk_pushes` still lands but the user-visible
        # state stays NotPushed forever.
        self._links = link_repo
        # Optional — resolves a Store to its concrete backend pair
        # (#279). When wired, `push_to_store` uses it to pick the per-
        # store driver from the pool; when None, the IngestionService
        # falls back to its service-level defaults (env-based, pre-#279
        # behaviour).
        self._backend_resolver = backend_resolver
        self._actor = actor
        # Duck-typed recorder for document versions (#267). Wired in
        # main.py to `VersionService.record_on_rechunk` so each
        # `+ Generate chunks` call appends a frozen pair to History.
        self._version_recorder = None

    def set_version_recorder(self, version_service) -> None:
        """Inject the document-version recorder (#267). Contract: a
        coroutine `(document_id: str, analysis_id: str | None) -> DocumentVersion`."""
        self._version_recorder = version_service

    # -- promotion (called by AnalysisService after first successful analysis)

    async def promote_from_analysis_if_empty(self, document_id: str, chunks_json: str) -> int:
        """Populate the canonical chunkset from an analysis result, ONLY if
        the document has no canonical chunks yet. Idempotent.

        Returns the number of chunks promoted (0 if skipped).
        """
        if await self._chunks.count_for_document(document_id) > 0:
            return 0
        try:
            raw_chunks = json.loads(chunks_json)
        except json.JSONDecodeError:
            logger.exception("Invalid chunks_json for doc %s — skipping promotion", document_id)
            return 0
        if not isinstance(raw_chunks, list) or not raw_chunks:
            return 0

        canonical = [
            chunk_from_dict(raw, document_id=document_id, sequence=seq)
            for seq, raw in enumerate(raw_chunks)
            if not raw.get("deleted")
        ]
        if not canonical:
            return 0

        now = _utcnow()
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            add=canonical,
            edits=[
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=c.id,
                    action=ChunkEditAction.INSERT,
                    actor="system:initial-analysis",
                    at=now,
                    after=chunk_to_audit_dict(c),
                )
                for c in canonical
            ],
        )
        logger.info(
            "chunk.promote docId=%s count=%d (initial-analysis)", document_id, len(canonical)
        )
        return len(canonical)

    # -- read

    async def list_chunks(self, document_id: str) -> list[Chunk]:
        await self._require_doc(document_id)
        return await self._chunks.find_for_document(document_id)

    # -- mutations

    async def add_chunk(self, document_id: str, *, text: str, after_id: str | None = None) -> Chunk:
        await self._require_doc(document_id)
        existing = await self._chunks.find_for_document(document_id)
        with _refusals_as_service_errors():
            sequence = chunk_editing.sequence_after(existing, after_id)
        now = _utcnow()
        await self._shift_sequences(document_id, existing, from_sequence=sequence, at=now)

        new_chunk = Chunk(
            document_id=document_id,
            sequence=sequence,
            text=text,
            created_at=now,
            updated_at=now,
        )
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            add=[new_chunk],
            edits=[
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=new_chunk.id,
                    action=ChunkEditAction.INSERT,
                    actor=self._actor,
                    at=now,
                    after=chunk_to_audit_dict(new_chunk),
                )
            ],
        )
        logger.info(
            "chunk.add docId=%s chunkId=%s sequence=%d", document_id, new_chunk.id, sequence
        )
        return new_chunk

    async def update_chunk(
        self,
        document_id: str,
        chunk_id: str,
        *,
        text: str | None = None,
        headings: list[str] | None = None,
    ) -> Chunk:
        chunk = await self._require_chunk(document_id, chunk_id)
        before = chunk_to_audit_dict(chunk)
        if text is not None:
            chunk.text = text
        if headings is not None:
            chunk.headings = list(headings)
        chunk.updated_at = _utcnow()
        await self._chunks.update(chunk)
        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=chunk.id,
                action=ChunkEditAction.UPDATE,
                actor=self._actor,
                at=_utcnow(),
                before=before,
                after=chunk_to_audit_dict(chunk),
            )
        )
        logger.info("chunk.update docId=%s chunkId=%s", document_id, chunk.id)
        return chunk

    async def delete_chunk(self, document_id: str, chunk_id: str) -> None:
        chunk = await self._require_chunk(document_id, chunk_id)
        before = chunk_to_audit_dict(chunk)
        deleted = await self._chunks.soft_delete(chunk_id, at=_utcnow())
        if not deleted:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=chunk_id,
                action=ChunkEditAction.DELETE,
                actor=self._actor,
                at=_utcnow(),
                before=before,
            )
        )
        logger.info("chunk.delete docId=%s chunkId=%s", document_id, chunk.id)

    async def split_chunk(self, document_id: str, chunk_id: str, cursor_offset: int) -> list[Chunk]:
        source = await self._require_chunk(document_id, chunk_id)
        with _refusals_as_service_errors():
            head, tail = chunk_editing.split(source, cursor_offset)
        existing = await self._chunks.find_for_document(document_id)
        before = chunk_to_audit_dict(source)

        # Push subsequent sequences by 1 to make room for `tail`. Should the
        # replacement below fail, the shift only leaves a gap, which the
        # ordering invariant allows.
        now = _utcnow()
        await self._shift_sequences(
            document_id, existing, from_sequence=source.sequence + 1, at=now
        )
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[source.id],
            add=[head, tail],
            edits=[
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=source.id,
                    action=ChunkEditAction.SPLIT,
                    actor=self._actor,
                    at=now,
                    before=before,
                    children=[head.id, tail.id],
                )
            ],
        )
        logger.info(
            "chunk.split docId=%s sourceId=%s newIds=[%s,%s]",
            document_id,
            source.id,
            head.id,
            tail.id,
        )
        return [head, tail]

    async def merge_chunks(self, document_id: str, ids: list[str]) -> Chunk:
        existing = await self._chunks.find_for_document(document_id)
        with _refusals_as_service_errors():
            ordered, merged = chunk_editing.merge(existing, ids)

        now = _utcnow()
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[c.id for c in ordered],
            add=[merged],
            edits=[
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=merged.id,
                    action=ChunkEditAction.MERGE,
                    actor=self._actor,
                    at=now,
                    parents=[c.id for c in ordered],
                    after=chunk_to_audit_dict(merged),
                )
            ],
        )
        logger.info(
            "chunk.merge docId=%s sourceIds=%s newId=%s",
            document_id,
            [c.id for c in ordered],
            merged.id,
        )
        return merged

    async def rechunk_document(self, document_id: str, options: dict | None = None) -> list[Chunk]:
        """Re-run the chunker on the latest completed analysis JSON and
        replace the canonical chunkset.

        Emits one INSERT edit per new chunk and one DELETE per old chunk
        — keeps the audit log within the existing `ChunkEditAction` enum.
        """
        await self._require_doc(document_id)
        if not self._chunker:
            raise ChunkServiceError("Chunker not configured", http_status=503)

        job = await self._analyses.find_latest_completed_by_document(document_id)
        if not job or not job.document_json:
            raise ChunkServiceError(
                "No completed analysis with document_json available for rechunk",
                http_status=409,
            )

        chunk_opts = ChunkingOptions(**options) if options else ChunkingOptions()
        new_results = await self._chunker.chunk(job.document_json, chunk_opts)

        existing = await self._chunks.find_for_document(document_id)
        now = _utcnow()
        new_chunks = [
            Chunk(
                document_id=document_id,
                sequence=seq,
                text=r.text,
                headings=list(r.headings),
                source_page=r.source_page,
                bboxes=list(r.bboxes),
                doc_items=list(r.doc_items),
                token_count=r.token_count or None,
            )
            for seq, r in enumerate(new_results)
        ]
        # One transaction: the old chunkset is retired and the new one
        # journaled together, or not at all.
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[c.id for c in existing],
            add=new_chunks,
            edits=[
                *(
                    ChunkEdit(
                        id=_new_id(),
                        document_id=document_id,
                        chunk_id=c.id,
                        action=ChunkEditAction.DELETE,
                        actor="system:rechunk",
                        at=now,
                        before=chunk_to_audit_dict(c),
                    )
                    for c in existing
                ),
                *(
                    ChunkEdit(
                        id=_new_id(),
                        document_id=document_id,
                        chunk_id=c.id,
                        action=ChunkEditAction.INSERT,
                        actor="system:rechunk",
                        at=now,
                        after=chunk_to_audit_dict(c),
                    )
                    for c in new_chunks
                ),
            ],
        )
        logger.info(
            "chunk.rechunk docId=%s oldCount=%d newCount=%d",
            document_id,
            len(existing),
            len(new_chunks),
        )

        # Record a frozen (analysis, chunks_snapshot) pair in the
        # workspace History timeline (#267). Snapshots the chunks we
        # just wrote, paired with the analysis they came from.
        if self._version_recorder is not None:
            try:
                await self._version_recorder.record_on_rechunk(document_id, job.id)
            except Exception:
                # Best-effort hook — never fail the rechunk if the
                # version snapshot write hits a snag.
                logger.exception(
                    "Version snapshot failed for doc %s after rechunk",
                    document_id,
                )

        return new_chunks

    # -- diff (against last push to a store)

    async def diff_against_store(self, document_id: str, store_id: str) -> list[dict]:
        """Compare the canonical chunkset to the last push for `store_id`.

        Returns a list of `ChunkDiff`-shaped dicts (camelCase) covering:
          - canonical chunks not in the last push → status "added"
          - canonical chunks updated since last push → status "modified"
          - canonical chunks unchanged since push → status "unchanged"
          - chunk ids in last push absent from canonical → status "removed"

        Coarse-grained — does not produce a textDiff today (follow-up).
        """
        await self._require_doc(document_id)
        canonical = await self._chunks.find_for_document(document_id)
        last_push = await self._pushes.find_latest(document_id, store_id)
        if last_push is None:
            return [{"chunkId": c.id, "status": "added", "textDiff": None} for c in canonical]

        pushed_ids = set(last_push.chunk_ids)
        diffs: list[dict] = []
        for c in canonical:
            if c.id not in pushed_ids:
                diffs.append({"chunkId": c.id, "status": "added", "textDiff": None})
                continue
            if c.updated_at > last_push.pushed_at:
                diffs.append({"chunkId": c.id, "status": "modified", "textDiff": None})
            else:
                diffs.append({"chunkId": c.id, "status": "unchanged", "textDiff": None})
        canonical_ids = {c.id for c in canonical}
        for cid in pushed_ids - canonical_ids:
            diffs.append({"chunkId": cid, "status": "removed", "textDiff": None})
        return diffs

    # -- push (delegates to IngestionService; per-store dispatch is a follow-up)

    async def push_to_store(self, document_id: str, store_id: str) -> dict:
        """Push the canonical chunkset to a store and record a `ChunkPush`.

        The `store_id` argument is the value the API caller passed —
        the frontend currently passes the **slug** (`POST /chunks/push`
        body), but the `chunk_pushes` FK targets `stores.id`. We
        resolve the slug to the real id when a `store_repo` is wired;
        otherwise we assume the caller already passed an id.

        Today the ingestion itself still delegates to the globally-
        configured `IngestionService` (one bucket). Per-store dispatch
        by `store.kind` is a follow-up issue — recording the right
        store id on the `ChunkPush` row is the prerequisite, and lands
        here.
        """
        await self._require_doc(document_id)
        if self._ingestion is None:
            raise ChunkServiceError(
                "Ingestion not available — set EMBEDDING_URL and at least one of "
                "OPENSEARCH_URL or NEO4J_URI on the backend",
                http_status=503,
            )
        # Resolve slug → store row. Refuses to push to an unknown store
        # (catches typos before the FK insert fails with a generic
        # IntegrityError 500).
        resolved_store_id = store_id
        if self._stores is not None:
            store = await self._stores.find_by_slug(store_id)
            if store is None:
                # Maybe the caller already passed an id — accept that
                # too for backwards compat with older callers.
                store = await self._stores.find_by_id(store_id)
            if store is None:
                raise ChunkServiceError(
                    f"Store not found: {store_id}",
                    http_status=404,
                )
            resolved_store_id = store.id

        doc = await self._documents.find_by_id(document_id)
        canonical = await self._chunks.find_for_document(document_id)
        if not canonical:
            raise ChunkServiceError(
                "No canonical chunks to push — run analysis or rechunk first",
                http_status=409,
            )

        chunks_payload = [chunk_to_ingestion_dict(c) for c in canonical]
        chunks_json_payload = json.dumps(chunks_payload)
        chunkset_hash = hashing.chunkset_hash(canonical)
        # Resolve the per-store backends through the pool (#279). When
        # the resolver is not wired the call falls back to the
        # IngestionService's service-level defaults — preserves
        # behaviour for existing tests and for installs that still
        # rely on env-var fallbacks.
        targets = None
        if self._backend_resolver is not None and store is not None:
            try:
                targets = await self._backend_resolver.resolve(store)
            except Exception as exc:
                await self._mark_link_failed(document_id, resolved_store_id, error=str(exc))
                raise ChunkServiceError(
                    f"Cannot resolve backend for store {store.slug!r}: {exc}",
                    http_status=503,
                ) from exc
        try:
            ingestion_result = await self._ingestion.ingest(
                doc_id=document_id,
                filename=(doc.filename if doc else document_id),
                chunks_json=chunks_json_payload,
                targets=targets,
            )
        except Exception as exc:
            # Push failed mid-flight — record the failure on the link
            # so the UI can show "Failed" instead of an indefinite
            # "Pushing…" or the previous state. Then re-raise.
            await self._mark_link_failed(document_id, resolved_store_id, error=str(exc))
            raise

        chunk_ids = [c.id for c in canonical]
        pushed_at = _utcnow()
        push = ChunkPush(
            id=_new_id(),
            document_id=document_id,
            store_id=resolved_store_id,
            chunkset_hash=chunkset_hash,
            chunk_ids=chunk_ids,
            pushed_at=pushed_at,
        )
        await self._pushes.insert(push)

        # Upsert the live link row that the UI reads from. Without
        # this, `Document.storeLinks` (the source of truth for the
        # Ingest view badges) stays NotPushed indefinitely even
        # though the audit log records the push.
        await self._upsert_link_ingested(
            document_id,
            resolved_store_id,
            chunkset_hash=chunkset_hash,
            at=pushed_at,
            run_id=push.id,
        )

        token_total = sum((c.token_count or 0) for c in canonical)
        logger.info(
            "chunk.push docId=%s store=%s count=%d tokens=%d",
            document_id,
            store_id,
            ingestion_result.chunks_indexed,
            token_total,
        )
        return {
            "pushId": push.id,
            "summary": {
                "embeds": ingestion_result.chunks_indexed,
                "tokens": token_total,
            },
        }

    async def list_pushes(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List the document's push history, newest first (#283).

        Joined view: each row carries the store slug + kind (via the
        store_repo) so the UI does not need a second round-trip to
        render the history list. When the store row was deleted
        after the push, slug and kind are returned as None — the
        push remains an immutable audit row.

        Returns a paginated envelope `{items, total, limit, offset}`.
        """
        await self._require_doc(document_id)
        total = await self._pushes.count_for_document(document_id)
        if total == 0:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        pushes = await self._pushes.find_for_document(document_id, limit=limit, offset=offset)
        # Resolve store names in one repo round per unique store_id
        # (typically 1-3 stores for a given doc).
        store_cache: dict[str, object | None] = {}
        items: list[dict] = []
        for push in pushes:
            store = store_cache.get(push.store_id, _UNSET)
            if store is _UNSET:
                store = (
                    await self._stores.find_by_id(push.store_id)
                    if self._stores is not None
                    else None
                )
                store_cache[push.store_id] = store
            items.append(
                {
                    "id": push.id,
                    "documentId": push.document_id,
                    "storeId": push.store_id,
                    "storeSlug": getattr(store, "slug", None),
                    "storeName": getattr(store, "name", None),
                    "storeKind": getattr(store.kind, "value", None) if store else None,
                    "chunksetHash": push.chunkset_hash,
                    "chunkCount": len(push.chunk_ids),
                    "pushedAt": push.pushed_at.isoformat() if push.pushed_at else None,
                }
            )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def _upsert_link_ingested(
        self,
        document_id: str,
        store_id: str,
        *,
        chunkset_hash: str,
        at: datetime,
        run_id: str,
    ) -> None:
        """Mark the (doc, store) link as Ingested. No-op if no link repo
        is wired (legacy ChunkService instances without store wiring).
        """
        if self._links is None:
            return
        existing = await self._links.find_one(document_id, store_id)
        link = existing or DocumentStoreLink(
            document_id=document_id,
            store_id=store_id,
        )
        link.mark_ingested(hash_=chunkset_hash, at=at, run_id=run_id)
        await self._links.upsert(link)

    async def _mark_link_failed(self, document_id: str, store_id: str, *, error: str) -> None:
        """Best-effort failure marker — never raises (we're already
        in an error path; the original push exception must bubble up
        unchanged).
        """
        if self._links is None:
            return
        try:
            existing = await self._links.find_one(document_id, store_id)
            link = existing or DocumentStoreLink(
                document_id=document_id,
                store_id=store_id,
            )
            link.mark_failed(error=error[:500])
            await self._links.upsert(link)
        except Exception:
            logger.exception(
                "Failed to record push failure on document_store_links for doc=%s store=%s",
                document_id,
                store_id,
            )

    # -- guards

    async def _require_doc(self, document_id: str) -> None:
        await require_document(self._documents, document_id)

    async def _require_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        chunk = await self._chunks.find_by_id(chunk_id)
        if not chunk or chunk.document_id != document_id or chunk.deleted_at is not None:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        return chunk

    # -- sequence helpers

    async def _shift_sequences(
        self,
        document_id: str,
        existing: list[Chunk],
        *,
        from_sequence: int,
        at: datetime,
    ) -> None:
        """Push live chunks at >= from_sequence one slot up to make room, in
        one UPDATE — skipped when nothing sits there (append at the end)."""
        if any(c.sequence >= from_sequence for c in existing):
            await self._chunks.shift_sequences(document_id, from_sequence=from_sequence, at=at)

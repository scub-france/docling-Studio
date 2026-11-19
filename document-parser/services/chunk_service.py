"""Chunk service — canonical chunk lifecycle for a document (#256).

Sits between the API layer and the chunk / chunk_push
repositories. Owns the invariants of the canonical chunkset:

- ordering by `sequence` (dense ascending, gaps allowed after split)
- soft-delete (removed chunks remain available for history inspection)
- promotion from the first completed analysis (idempotent)

Re-uses `DocumentChunker` for rechunk (same port that
`AnalysisService.rechunk` uses), so chunking strategy logic is not
duplicated.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from domain import chunk_editing
from domain.analysis_editing import AnalysisEditUnavailableError, hash_result
from domain.chunk_editing import ChunkEditingError, ChunkMergeGapError
from domain.heading_tree import nest_by_heading
from domain.models import (
    AnalysisStatus,
    Chunk,
    ChunkPush,
    DocumentAnalysisState,
    DocumentStoreLink,
    generate_id,
    get_utc_now,
)
from domain.navigation import is_heading
from domain.value_objects import (
    ChunkBbox,
    ChunkDocItem,
    ChunkingOptions,
)
from services.errors import ServiceError

if TYPE_CHECKING:
    from domain.ports import (
        ActiveAnalysisResultReader,
        AnalysisRepository,
        ChunkPushRepository,
        ChunkRepository,
        CurrentAnalysisReader,
        DocumentAnalysisStateRepository,
        DocumentChunker,
        DocumentRepository,
        DocumentStoreLinkRepository,
        DocumentTreeReader,
        StoreRepository,
    )
    from services.ingestion_service import IngestionService
    from services.store_backend_resolver import StoreBackendResolver

logger = logging.getLogger(__name__)

# Sentinel for "not yet probed" in `list_pushes`'s store-name cache.
# Distinct from None (which means "store row deleted after the push").
_UNSET = object()


# ---------------------------------------------------------------------------
# Errors — `ServiceError` carries the http_status hint (#396).
# ---------------------------------------------------------------------------


class ChunkServiceError(ServiceError):
    http_status: int = 400


class ChunkNotFoundError(ChunkServiceError):
    http_status = 404


class DocumentNotFoundError(ChunkServiceError):
    http_status = 404


class ChunkConflictError(ChunkServiceError):
    http_status = 409


class ChunkValidationError(ChunkServiceError):
    http_status = 400


# ---------------------------------------------------------------------------
# Helpers — chunk ↔ dict conversions for analysis chunks_json.
# ---------------------------------------------------------------------------


def _bbox_from_dict(d: dict) -> ChunkBbox:
    return ChunkBbox(page=d["page"], bbox=list(d["bbox"]))


def _doc_item_from_dict(d: dict) -> ChunkDocItem:
    return ChunkDocItem(
        self_ref=d.get("selfRef") or d.get("self_ref", ""), label=d.get("label", "")
    )


def _analysis_chunk_to_canonical(
    document_id: str,
    sequence: int,
    raw: dict,
) -> Chunk:
    """Convert an entry from `AnalysisJob.chunks_json` (camelCase) into a
    canonical `Chunk`. Used by `_promote_from_analysis`."""
    return Chunk(
        document_id=document_id,
        sequence=sequence,
        text=raw.get("text", ""),
        headings=list(raw.get("headings", [])),
        source_page=raw.get("sourcePage"),
        bboxes=[_bbox_from_dict(b) for b in raw.get("bboxes", [])],
        doc_items=[_doc_item_from_dict(d) for d in raw.get("docItems", [])],
        token_count=raw.get("tokenCount"),
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ChunkService:
    """Orchestrates canonical chunk operations for a document."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_push_repo: ChunkPushRepository,
        document_repo: DocumentRepository,
        analysis_state_repo: DocumentAnalysisStateRepository,
        analysis_repo: AnalysisRepository,
        current_analysis: CurrentAnalysisReader,
        tree_reader: DocumentTreeReader,
        chunker: DocumentChunker | None = None,
        ingestion_service: IngestionService | None = None,
        store_repo: StoreRepository | None = None,
        link_repo: DocumentStoreLinkRepository | None = None,
        backend_resolver: StoreBackendResolver | None = None,
        active_result_service: ActiveAnalysisResultReader | None = None,
    ) -> None:
        self._chunks = chunk_repo
        self._pushes = chunk_push_repo
        self._documents = document_repo
        self._states = analysis_state_repo
        self._analyses = analysis_repo
        self._current = current_analysis
        # `DocumentTreeReader` port (#audit-01) — replaces the local
        # `from infra.docling_tree import ...` smell hiding inside two
        # tree-walking helpers. Required so the tree views stay rendable.
        self._tree = tree_reader
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
        self._active_result_service = active_result_service
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
            _analysis_chunk_to_canonical(document_id, seq, raw)
            for seq, raw in enumerate(raw_chunks)
            if not raw.get("deleted")
        ]
        if not canonical:
            return 0

        await self._chunks.insert_many(canonical)
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
        sequence = self._compute_sequence_after(existing, after_id)
        await self._shift_sequences(document_id, from_sequence=sequence)

        new_chunk = Chunk(
            document_id=document_id,
            sequence=sequence,
            text=text,
            created_at=get_utc_now(),
            updated_at=get_utc_now(),
        )
        await self._chunks.insert(new_chunk)
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
        if text is not None:
            chunk.text = text
        if headings is not None:
            chunk.headings = list(headings)
        chunk.updated_at = get_utc_now()
        await self._chunks.update(chunk)
        logger.info("chunk.update docId=%s chunkId=%s", document_id, chunk.id)
        return chunk

    async def delete_chunk(self, document_id: str, chunk_id: str) -> None:
        chunk = await self._require_chunk(document_id, chunk_id)
        deleted = await self._chunks.soft_delete(chunk_id, at=get_utc_now())
        if not deleted:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        logger.info("chunk.delete docId=%s chunkId=%s", document_id, chunk.id)

    async def split_chunk(self, document_id: str, chunk_id: str, cursor_offset: int) -> list[Chunk]:
        source = await self._require_chunk(document_id, chunk_id)
        try:
            head, tail = chunk_editing.split(
                source, at_offset=cursor_offset, document_id=document_id
            )
        except ChunkEditingError as exc:
            raise ChunkValidationError(str(exc)) from exc

        # Push subsequent sequences by 1 to make room for `tail`.
        await self._shift_sequences(document_id, from_sequence=source.sequence + 1)
        await self._chunks.soft_delete(source.id, at=get_utc_now())
        await self._chunks.insert_many([head, tail])

        logger.info(
            "chunk.split docId=%s sourceId=%s newIds=[%s,%s]",
            document_id,
            source.id,
            head.id,
            tail.id,
        )
        return [head, tail]

    async def merge_chunks(self, document_id: str, ids: list[str]) -> Chunk:
        try:
            chunk_editing.check_merge_count(ids)
        except ChunkEditingError as exc:
            raise ChunkValidationError(str(exc)) from exc
        existing = await self._chunks.find_for_document(document_id)
        by_id = {c.id: c for c in existing}
        targets = [by_id.get(i) for i in ids]
        if any(t is None for t in targets):
            missing = [i for i, t in zip(ids, targets, strict=True) if t is None]
            raise ChunkNotFoundError(f"Chunks not found: {missing}")

        try:
            ordered, merged = chunk_editing.merge(targets, document_id=document_id)
        except ChunkMergeGapError as exc:
            raise ChunkConflictError(str(exc)) from exc
        except ChunkEditingError as exc:
            raise ChunkValidationError(str(exc)) from exc

        await self._chunks.soft_delete_many([c.id for c in ordered], at=get_utc_now())
        await self._chunks.insert(merged)

        logger.info(
            "chunk.merge docId=%s sourceIds=%s newId=%s",
            document_id,
            [c.id for c in ordered],
            merged.id,
        )
        return merged

    async def rechunk_document(self, document_id: str, options: dict | None = None) -> list[Chunk]:
        """Re-run the chunker on the current analysis result and replace the chunkset.

        The current analysis is read with its saved edits when the editor's
        reader is wired, as stored otherwise. The new chunks and the record of
        their source are written in one transaction (02-2.4.3); only the
        source is written, so an analysis that becomes active while the
        chunker runs stays active and the new chunks report stale against it,
        which they are. The History version that follows is a separate,
        best-effort write: when it fails the chunks stand without a matching
        History entry, as before.
        """
        await self._require_doc(document_id)
        if not self._chunker:
            raise ChunkServiceError("Chunker not configured", http_status=503)

        active = None
        if self._active_result_service is not None:
            try:
                active = await self._active_result_service.load_active_result(document_id)
            except AnalysisEditUnavailableError as exc:
                raise ChunkServiceError(str(exc), http_status=409) from exc
        job = (
            active.job
            if active is not None
            else await self._current.load_current_analysis(document_id)
        )
        if not job or not job.document_json:
            raise ChunkServiceError(
                "No completed analysis with document_json available for rechunk",
                http_status=409,
            )

        chunk_opts = ChunkingOptions(**options) if options else ChunkingOptions()
        new_results = await self._chunker.chunk(job.document_json, chunk_opts)

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

        source_analysis_id = job.id
        if active is not None:
            source_analysis_id = active.base_analysis_id
        source_result_hash = hash_result(job.document_json)
        state = await self._states.find_state(document_id) or DocumentAnalysisState(document_id)
        state.record_chunk_source(source_analysis_id, source_result_hash)
        old_count = await self._chunks.replace_for_document(
            document_id, new_chunks, at=get_utc_now(), state=state
        )
        logger.info(
            "chunk.rechunk docId=%s oldCount=%d newCount=%d",
            document_id,
            old_count,
            len(new_chunks),
        )

        # Record a frozen (analysis, chunks_snapshot) pair in the
        # workspace History timeline (#267). Snapshots the chunks we
        # just wrote, paired with the analysis they came from.
        if self._version_recorder is not None:
            try:
                await self._version_recorder.record_on_rechunk(
                    document_id, source_analysis_id, source_result_hash
                )
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

        chunks_payload = [_chunk_to_ingestion_dict(c) for c in canonical]
        chunks_json_payload = json.dumps(chunks_payload)
        chunkset_hash = _compute_chunkset_hash(canonical)
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
        pushed_at = get_utc_now()
        push = ChunkPush(
            id=generate_id(),
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

    # -- tree (read from an analysis document_json)

    async def get_tree(self, document_id: str, analysis_id: str | None = None) -> list[dict]:
        """Build a doc tree from the requested or active analysis.

        Returns a list of `DocTreeNode`-shaped dicts (camelCase). Empty
        list if no analysis is available yet — caller decides if that is
        an error or just "not parsed yet".
        """
        await self._require_doc(document_id)
        if analysis_id:
            job = await self._analyses.find_by_id(analysis_id)
            if not job or job.document_id != document_id or job.status != AnalysisStatus.COMPLETED:
                raise ChunkNotFoundError(f"Analysis not found: {analysis_id}")
        else:
            if self._active_result_service is not None:
                try:
                    job = (await self._active_result_service.load_active_result(document_id)).job
                except AnalysisEditUnavailableError:
                    return []
            else:
                job = await self._current.load_current_analysis(document_id)
        if not job or not job.document_json:
            return []
        try:
            doc_data = json.loads(job.document_json)
        except json.JSONDecodeError:
            logger.exception("Invalid document_json for analysis %s", job.id)
            return []
        return _build_tree_nodes(doc_data, self._tree)

    # -- guards

    async def _require_doc(self, document_id: str) -> None:
        doc = await self._documents.find_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

    async def _require_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        chunk = await self._chunks.find_by_id(chunk_id)
        if not chunk or chunk.document_id != document_id or chunk.deleted_at is not None:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        return chunk

    # -- sequence helpers

    @staticmethod
    def _compute_sequence_after(existing: list[Chunk], after_id: str | None) -> int:
        if after_id is None:
            return (max((c.sequence for c in existing), default=-1)) + 1
        anchor = next((c for c in existing if c.id == after_id), None)
        if anchor is None:
            raise ChunkNotFoundError(f"Anchor chunk not found: {after_id}")
        return anchor.sequence + 1

    async def _shift_sequences(self, document_id: str, *, from_sequence: int) -> None:
        """Push live chunks at >= from_sequence one slot up to make room, in one UPDATE."""
        await self._chunks.shift_sequences(
            document_id, from_sequence=from_sequence, at=get_utc_now()
        )


# ---------------------------------------------------------------------------
# Tree projection — extract a hierarchical outline from a DoclingDocument.
# Kept module-level so it stays cheap to test in isolation.
# ---------------------------------------------------------------------------


def _chunk_to_ingestion_dict(c: Chunk) -> dict:
    """Convert a canonical `Chunk` into the legacy chunks_json shape that
    `IngestionService.ingest` consumes (camelCase, modeled after
    `analysis_service._chunk_to_dict`)."""
    return {
        "text": c.text,
        "headings": list(c.headings),
        "sourcePage": c.source_page,
        "tokenCount": c.token_count or 0,
        "bboxes": [{"page": b.page, "bbox": list(b.bbox)} for b in c.bboxes],
        "docItems": [{"selfRef": d.self_ref, "label": d.label} for d in c.doc_items],
    }


def _compute_chunkset_hash(chunks: list[Chunk]) -> str:
    """Stable hash of the canonical chunkset content.

    Used by `ChunkPush` snapshots so we can answer 'is the store in sync
    with the current canonical state' without listing chunks from the
    vector store.
    """
    import hashlib

    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode("utf-8"))
        h.update(b"\x00")
        h.update(c.text.encode("utf-8"))
        h.update(b"\x00")
        h.update(str(c.updated_at).encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def _build_tree_nodes(doc_data: dict, tree_reader: DocumentTreeReader) -> list[dict]:
    """Project a Docling document JSON into a hierarchical `[DocTreeNode]` outline.

    Two stacking rules combine to follow the document's natural structure:

    1. **Headings nest by level.** `title` opens a level-0 container; each
       `section_header` opens a container at its declared `level` (default 1).
       A new heading pops the stack until the top has a strictly lower level,
       so siblings stay siblings and sub-sections nest inside their parent.
    2. **Docling parent/child is preserved for containers.** `list` keeps its
       `list_item` descendants under it; everything else (paragraph, table,
       picture) is a leaf under the current section.

    Inline-group style runs and picture sub-elements are skipped via the
    shared `build_collapse_index` helper — keeps the projection in sync
    with the Neo4j tree writer and the in-memory graph payload.
    """
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)
    by_ref: dict[str, dict] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item

    body = doc_data.get("body") or {}
    entries: list[tuple[str, dict]] = []
    for ch in body.get("children") or []:
        ref = ch.get("$ref") or ch.get("cref")
        if not ref or ref in skip_refs:
            continue
        item = by_ref.get(ref)
        if item is None:
            continue
        entries.append((ref, item))

    root: list[dict] = []
    nodes: dict[int, dict] = {}
    nesting = nest_by_heading([item for _, item in entries], level_of=_read_tree_heading_level)
    for step in nesting.steps:
        ref, item = entries[step.position]
        if step.level is not None:
            node = _make_node(ref, _get_label_type(item), item, inline_meta, tree_reader)
        else:
            node = _build_item_subtree(ref, item, by_ref, skip_refs, inline_meta, tree_reader)
        siblings = root if step.parent is None else nodes[step.parent]["children"]
        siblings.append(node)
        nodes[step.position] = node
    return root


def _get_label_type(item: dict) -> str:
    return (item.get("label") or "").lower() or "text"


def _read_tree_heading_level(item: dict) -> int | None:
    """`title` is level 0, a `section_header` its declared level (at least 1).

    Unlike the parse index, a level that is not a number raises here: the
    tree has always failed on such a document rather than guess.
    """
    label_type = _get_label_type(item)
    if not is_heading(label_type):
        return None
    return 0 if label_type == "title" else max(int(item.get("level") or 1), 1)


def _build_item_subtree(
    ref: str,
    item: dict,
    by_ref: dict[str, dict],
    skip_refs: set[str],
    inline_meta: dict[str, dict],
    tree_reader: DocumentTreeReader,
) -> dict:
    """Build a leaf or nested subtree for a non-heading item.

    Containers (list, group, form_area, key_value_area) keep their explicit
    Docling children so the outline mirrors structures like `list` → `list_item`.
    Other items are emitted as leaves — pictures and inline groups had their
    descendants pruned upstream by `build_collapse_index`.
    """
    label_type = _get_label_type(item)
    node = _make_node(ref, label_type, item, inline_meta, tree_reader)
    if label_type in {"list", "group", "form_area", "key_value_area"}:
        for ch in item.get("children") or []:
            child_ref = ch.get("$ref") or ch.get("cref")
            if not child_ref or child_ref in skip_refs:
                continue
            child_item = by_ref.get(child_ref)
            if child_item is None:
                continue
            node["children"].append(
                _build_item_subtree(
                    child_ref, child_item, by_ref, skip_refs, inline_meta, tree_reader
                )
            )
    return node


def _make_node(
    ref: str,
    label_type: str,
    item: dict,
    inline_meta: dict[str, dict],
    tree_reader: DocumentTreeReader,
) -> dict:
    return {
        "ref": ref,
        "type": label_type,
        "label": _pick_display_label(item, inline_meta, tree_reader),
        "children": [],
    }


def _pick_display_label(item: dict, inline_meta: dict[str, dict], tree_reader) -> str:
    """Pick the most human-readable label for the tree node."""
    ref = item.get("self_ref") or ""
    label_type = (item.get("label") or "").lower()

    if tree_reader.is_inline_group(item):
        meta = inline_meta.get(ref)
        if meta and meta.get("text"):
            return _truncate(meta["text"])

    text = (item.get("text") or "").strip()
    if text:
        return _truncate(text)

    if label_type == "table":
        return "Table"
    if label_type == "picture":
        return "Figure"
    if label_type == "list":
        return "List"
    if label_type == "group":
        return (item.get("name") or "Group").strip()
    return label_type or "node"


def _truncate(text: str, max_len: int = 80) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

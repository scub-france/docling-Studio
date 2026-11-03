"""Chunk push service — the canonical chunkset against the stores (#256, #283).

Diffs the chunkset against the last push to a store, pushes it through the
`IngestionService`, and lists the push history. Each push writes an
immutable `chunk_pushes` row and upserts the (document, store)
`DocumentStoreLink` the UI reads its per-store badge from.

Split out of `ChunkService`, which edits the chunkset (audit 0.7.4, 03 MAJ
3.3.2). Store ingestion is deprecated and goes away in 0.8.0.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain import hashing
from domain.chunk_serialization import chunk_to_ingestion_dict
from domain.models import ChunkPush, DocumentStoreLink
from services.chunk_service import ChunkServiceError, require_document

if TYPE_CHECKING:
    from domain.models import Chunk, Document, Store
    from domain.ports import (
        ChunkPushRepository,
        ChunkRepository,
        DocumentRepository,
        DocumentStoreLinkRepository,
        StoreRepository,
    )
    from services.ingestion_service import IngestionService
    from services.store_backend_resolver import IngestionTargets, StoreBackendResolver

logger = logging.getLogger(__name__)

# Sentinel for "not yet probed" in `list_pushes`'s store-name cache.
# Distinct from None (which means "store row deleted after the push").
_UNSET = object()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class ChunkPushService:
    """Pushes a document's canonical chunkset to a store and keeps the record."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_push_repo: ChunkPushRepository,
        document_repo: DocumentRepository,
        ingestion_service: IngestionService | None = None,
        store_repo: StoreRepository | None = None,
        link_repo: DocumentStoreLinkRepository | None = None,
        backend_resolver: StoreBackendResolver | None = None,
    ) -> None:
        self._chunks = chunk_repo
        self._pushes = chunk_push_repo
        self._documents = document_repo
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
        await require_document(self._documents, document_id)
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

        One step per concern, in this order: everything the push needs is
        checked first (document, ingestion, store, chunks); then the store's
        backends are resolved and the chunks ingested, either failure marking
        the link Failed; only a successful ingestion is recorded.
        """
        doc = await require_document(self._documents, document_id)
        ingestion = self._require_ingestion()
        store = await self._resolve_store(store_id)
        resolved_store_id = store.id if store is not None else store_id
        chunks = await self._chunks_to_push(document_id)
        targets = await self._resolve_backends(document_id, resolved_store_id, store)
        indexed = await self._ingest(
            ingestion, doc, resolved_store_id, chunks=chunks, targets=targets
        )
        push = await self._record_push(document_id, resolved_store_id, chunks)

        token_total = sum((c.token_count or 0) for c in chunks)
        logger.info(
            "chunk.push docId=%s store=%s count=%d tokens=%d",
            document_id,
            store_id,
            indexed,
            token_total,
        )
        return {"pushId": push.id, "summary": {"embeds": indexed, "tokens": token_total}}

    def _require_ingestion(self) -> IngestionService:
        if self._ingestion is None:
            raise ChunkServiceError(
                "Ingestion not available — set EMBEDDING_URL and at least one of "
                "OPENSEARCH_URL or NEO4J_URI on the backend",
                http_status=503,
            )
        return self._ingestion

    async def _resolve_store(self, store_ref: str) -> Store | None:
        """The store `store_ref` names — by slug, else by id for older callers.

        Refuses an unknown store (catches typos before the FK insert fails
        with a generic IntegrityError 500). None when no store repository is
        wired: the caller's value is then taken as the store id.
        """
        if self._stores is None:
            return None
        store = await self._stores.find_by_slug(store_ref)
        if store is None:
            store = await self._stores.find_by_id(store_ref)
        if store is None:
            raise ChunkServiceError(f"Store not found: {store_ref}", http_status=404)
        return store

    async def _chunks_to_push(self, document_id: str) -> list[Chunk]:
        chunks = await self._chunks.find_for_document(document_id)
        if not chunks:
            raise ChunkServiceError(
                "No canonical chunks to push — run analysis or rechunk first",
                http_status=409,
            )
        return chunks

    async def _resolve_backends(
        self, document_id: str, store_id: str, store: Store | None
    ) -> IngestionTargets | None:
        """The store's own backends, from the pool (#279).

        None — the IngestionService's service-level defaults, env-based —
        when no resolver is wired or no store row was resolved. A store whose
        backends cannot be resolved marks the link Failed and answers 503.
        """
        if self._backend_resolver is None or store is None:
            return None
        try:
            return await self._backend_resolver.resolve(store)
        except Exception as exc:
            await self._mark_link_failed(document_id, store_id, error=str(exc))
            raise ChunkServiceError(
                f"Cannot resolve backend for store {store.slug!r}: {exc}",
                http_status=503,
            ) from exc

    async def _ingest(
        self,
        ingestion: IngestionService,
        doc: Document,
        store_id: str,
        *,
        chunks: list[Chunk],
        targets: IngestionTargets | None,
    ) -> int:
        """Embed and index `chunks`; returns how many were indexed.

        A failure mid-flight marks the link Failed — so the UI shows "Failed"
        instead of an indefinite "Pushing…" or the previous state — then
        propagates unchanged.
        """
        try:
            result = await ingestion.ingest(
                doc_id=doc.id,
                filename=doc.filename,
                chunks_json=json.dumps([chunk_to_ingestion_dict(c) for c in chunks]),
                targets=targets,
            )
        except Exception as exc:
            await self._mark_link_failed(doc.id, store_id, error=str(exc))
            raise
        return result.chunks_indexed

    async def _record_push(self, document_id: str, store_id: str, chunks: list[Chunk]) -> ChunkPush:
        """Write the immutable `chunk_pushes` row, then point the live link at it.

        Without the link upsert, `Document.storeLinks` (the source of truth
        for the Ingest view badges) stays NotPushed indefinitely even though
        the audit log records the push.
        """
        push = ChunkPush(
            id=_new_id(),
            document_id=document_id,
            store_id=store_id,
            chunkset_hash=hashing.chunkset_hash(chunks),
            chunk_ids=[c.id for c in chunks],
            pushed_at=_utcnow(),
        )
        await self._pushes.insert(push)
        await self._upsert_link_ingested(
            document_id,
            store_id,
            chunkset_hash=push.chunkset_hash,
            at=push.pushed_at,
            run_id=push.id,
        )
        return push

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
        await require_document(self._documents, document_id)
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
        is wired (legacy instances without store wiring).
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

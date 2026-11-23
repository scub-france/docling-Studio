"""Chunk push service — the canonical chunkset against the stores it was pushed to.

Diffs the chunkset against the last push to a store, pushes it through the
`IngestionService` and records the `ChunkPush` audit row plus the live
`document_store_links` row the UI reads, and lists the push history (#256,
#283).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from domain.models import ChunkPush, DocumentStoreLink, generate_id, get_utc_now
from domain.value_objects import IngestionSource
from services.chunk_errors import ChunkServiceError, require_document

if TYPE_CHECKING:
    from domain.models import Chunk, Store
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


class ChunkPushService:
    """Pushes a document's canonical chunkset to stores and keeps its history."""

    def __init__(
        self,
        *,
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

    # -- push (through IngestionService, to the store's own backends)

    async def push_to_store(self, document_id: str, store_id: str) -> dict:
        """Push the canonical chunkset to a store and record a `ChunkPush`.

        The `store_id` argument is the value the API caller passed —
        the frontend currently passes the **slug** (`POST /chunks/push`
        body), but the `chunk_pushes` FK targets `stores.id`. We
        resolve the slug to the real id when a `store_repo` is wired;
        otherwise we assume the caller already passed an id.

        The chunks go to the store's own backends when the backend resolver
        is wired (`_resolve_targets`), else to the `IngestionService` defaults.
        """
        await require_document(self._documents, document_id)
        ingestion = self._require_ingestion()
        store, resolved_store_id = await self._resolve_store(store_id)

        doc = await self._documents.find_by_id(document_id)
        canonical = await self._load_chunks_to_push(document_id)
        chunks_json_payload = json.dumps([_chunk_to_ingestion_dict(c) for c in canonical])
        chunkset_hash = _compute_chunkset_hash(canonical)
        targets = await self._resolve_targets(document_id, store, resolved_store_id)
        filename = doc.filename if doc else document_id
        source = IngestionSource(doc_id=document_id, filename=filename)
        try:
            ingestion_result = await ingestion.ingest(source, chunks_json_payload, targets=targets)
        except Exception as exc:
            # So the UI shows "Failed", not an endless "Pushing…" or the previous state.
            await self._mark_link_failed(document_id, resolved_store_id, error=str(exc))
            raise

        push = await self._record_push(document_id, resolved_store_id, canonical, chunkset_hash)

        token_total = sum((c.token_count or 0) for c in canonical)
        logger.info(
            "chunk.push docId=%s store=%s count=%d tokens=%d",
            document_id,
            store_id,
            ingestion_result.chunks_indexed,
            token_total,
        )
        return _build_push_response(push.id, ingestion_result.chunks_indexed, token_total)

    def _require_ingestion(self) -> IngestionService:
        if self._ingestion is None:
            raise ChunkServiceError(
                "Ingestion not available — set EMBEDDING_URL and at least one of "
                "OPENSEARCH_URL or NEO4J_URI on the backend",
                http_status=503,
            )
        return self._ingestion

    async def _resolve_store(self, store_id: str) -> tuple[Store | None, str]:
        """The store row and its id, from the slug or id the caller passed.

        Refuses to push to an unknown store (catches typos before the FK
        insert fails with a generic IntegrityError 500). Without a store
        repository there is no row, and the value is taken as the id.
        """
        if self._stores is None:
            return None, store_id
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
        return store, store.id

    async def _load_chunks_to_push(self, document_id: str) -> list[Chunk]:
        canonical = await self._chunks.find_for_document(document_id)
        if not canonical:
            raise ChunkServiceError(
                "No canonical chunks to push — run analysis or rechunk first",
                http_status=409,
            )
        return canonical

    async def _resolve_targets(
        self, document_id: str, store: Store | None, resolved_store_id: str
    ) -> IngestionTargets | None:
        """The store's own backends, through the pool (#279).

        When the resolver is not wired the ingestion falls back to the
        IngestionService's service-level defaults — preserves behaviour
        for existing tests and for installs that still rely on env-var
        fallbacks.
        """
        if self._backend_resolver is None or store is None:
            return None
        try:
            return await self._backend_resolver.resolve(store)
        except Exception as exc:
            await self._mark_link_failed(document_id, resolved_store_id, error=str(exc))
            raise ChunkServiceError(
                f"Cannot resolve backend for store {store.slug!r}: {exc}",
                http_status=503,
            ) from exc

    async def _record_push(
        self, document_id: str, store_id: str, canonical: list[Chunk], chunkset_hash: str
    ) -> ChunkPush:
        """Write the `ChunkPush` audit row, then the live link row it points at."""
        chunk_ids = [c.id for c in canonical]
        pushed_at = get_utc_now()
        push = ChunkPush(
            id=generate_id(),
            document_id=document_id,
            store_id=store_id,
            chunkset_hash=chunkset_hash,
            chunk_ids=chunk_ids,
            pushed_at=pushed_at,
        )
        await self._pushes.insert(push)

        # Upsert the live link row that the UI reads from. Without
        # this, `Document.storeLinks` (the source of truth for the
        # Ingest view badges) stays NotPushed indefinitely even
        # though the audit log records the push.
        await self._mark_link_ingested(push)
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
            items.append(_build_push_item(push, store))
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def _mark_link_ingested(self, push: ChunkPush) -> None:
        """Mark the push's (doc, store) link as Ingested. No-op if no link
        repo is wired (legacy instances without store wiring).
        """
        if self._links is None:
            return
        existing = await self._links.find_one(push.document_id, push.store_id)
        link = existing or DocumentStoreLink(
            document_id=push.document_id,
            store_id=push.store_id,
        )
        link.mark_ingested(hash_=push.chunkset_hash, at=push.pushed_at, run_id=push.id)
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


def _build_push_response(push_id: str, embeds: int, tokens: int) -> dict:
    return {
        "pushId": push_id,
        "summary": {
            "embeds": embeds,
            "tokens": tokens,
        },
    }


def _build_push_item(push: ChunkPush, store: object | None) -> dict:
    """One history row; slug, name and kind are None once the store row is gone."""
    return {
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
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode("utf-8"))
        h.update(b"\x00")
        h.update(c.text.encode("utf-8"))
        h.update(b"\x00")
        h.update(str(c.updated_at).encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()

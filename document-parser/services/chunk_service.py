"""Chunk service — canonical chunk lifecycle for a document (#256).

Sits between the API layer and the chunk repository. Owns the invariants
of the canonical chunkset:

- ordering by `sequence` (dense ascending, gaps allowed after split)
- soft-delete (removed chunks remain available for history inspection)
- promotion from the first completed analysis (idempotent)

Re-uses `DocumentChunker` for rechunk (same port that
`AnalysisService.rechunk` uses), so chunking strategy logic is not
duplicated.

The chunk routes also push the chunkset to stores and read the document
tree: `ChunkService` hands those to `ChunkPushService` and
`DocumentTreeService`, built from the same repositories, so the routes and
the composition root keep one service to call.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from domain import chunk_editing
from domain.analysis_editing import AnalysisEditUnavailableError, hash_result
from domain.chunk_editing import ChunkEditingError, ChunkMergeGapError
from domain.models import Chunk, DocumentChunkSource, get_utc_now
from domain.value_objects import (
    ChunkBbox,
    ChunkDocItem,
    ChunkingOptions,
)
from services.chunk_errors import (
    ChunkConflictError,
    ChunkNotFoundError,
    ChunkServiceError,
    ChunkValidationError,
    require_document,
)
from services.chunk_push_service import ChunkPushService
from services.document_tree_service import DocumentTreeService

if TYPE_CHECKING:
    from domain.ports import (
        ActiveAnalysisResultReader,
        AnalysisRepository,
        ChunkPushRepository,
        ChunkRepository,
        DocumentChunker,
        DocumentRepository,
        DocumentStoreLinkRepository,
        DocumentTreeReader,
        StoreRepository,
    )
    from services.ingestion_service import IngestionService
    from services.store_backend_resolver import StoreBackendResolver

logger = logging.getLogger(__name__)


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
    canonical `Chunk`. Used by `promote_from_analysis_if_empty`."""
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
        analysis_repo: AnalysisRepository,
        tree_reader: DocumentTreeReader,
        active_result_service: ActiveAnalysisResultReader,
        chunker: DocumentChunker | None = None,
        ingestion_service: IngestionService | None = None,
        store_repo: StoreRepository | None = None,
        link_repo: DocumentStoreLinkRepository | None = None,
        backend_resolver: StoreBackendResolver | None = None,
    ) -> None:
        self._chunks = chunk_repo
        self._documents = document_repo
        self._chunker = chunker
        self._active_result_service = active_result_service
        # Duck-typed recorder for document versions (#267). Wired in
        # main.py to `VersionService.record_on_rechunk` so each
        # `+ Generate chunks` call appends a frozen pair to History.
        self._version_recorder = None
        self._push = ChunkPushService(
            chunk_repo=chunk_repo,
            chunk_push_repo=chunk_push_repo,
            document_repo=document_repo,
            ingestion_service=ingestion_service,
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=backend_resolver,
        )
        self._tree = DocumentTreeService(
            document_repo=document_repo,
            analysis_repo=analysis_repo,
            tree_reader=tree_reader,
            active_result_service=active_result_service,
        )

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

        The current analysis is read with its saved edits. The new chunks and
        the record of their source are written in one transaction (02-2.4.3);
        the selection is kept, so an analysis that becomes active while the
        chunker runs stays active and the new chunks report stale against it,
        which they are. A document with no state row gets one selecting the
        analysis just chunked, the one the fallback rule gave it. The History
        version that follows is a separate, best-effort write: when it fails
        the chunks stand without a matching History entry, as before.
        """
        await self._require_doc(document_id)
        if not self._chunker:
            raise ChunkServiceError("Chunker not configured", http_status=503)

        try:
            current = await self._active_result_service.load_current_edited(document_id)
        except AnalysisEditUnavailableError as exc:
            raise ChunkServiceError(str(exc), http_status=409) from exc
        job = current.job
        if not job.document_json:
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

        source_analysis_id = current.base_analysis_id
        source_result_hash = hash_result(job.document_json)
        old_count = await self._chunks.replace_for_document(
            document_id,
            new_chunks,
            at=get_utc_now(),
            chunk_source=DocumentChunkSource(document_id, source_analysis_id, source_result_hash),
            active_analysis_id=source_analysis_id,
            keep_selection=True,
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

    # -- stores and tree, handed to their own services

    async def diff_against_store(self, document_id: str, store_id: str) -> list[dict]:
        """See `ChunkPushService.diff_against_store`."""
        return await self._push.diff_against_store(document_id, store_id)

    async def push_to_store(self, document_id: str, store_id: str) -> dict:
        """See `ChunkPushService.push_to_store`."""
        return await self._push.push_to_store(document_id, store_id)

    async def list_pushes(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """See `ChunkPushService.list_pushes`."""
        return await self._push.list_pushes(document_id, limit=limit, offset=offset)

    async def get_tree(self, document_id: str, analysis_id: str | None = None) -> list[dict]:
        """See `DocumentTreeService.get_tree`."""
        return await self._tree.get_tree(document_id, analysis_id)

    # -- guards

    async def _require_doc(self, document_id: str) -> None:
        await require_document(self._documents, document_id)

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

"""Chunk service — editing a document's canonical chunkset (#256).

Sits between the API layer and the chunk / chunk_edit repositories. The
rules of an edit (where a chunk lands, how one splits, how several merge)
live in `domain/chunk_editing.py`; this service loads the live chunkset,
applies them, and persists the result with one `chunk_edits` journal row
per chunk touched. Promotion, add, split, merge and rechunk write chunks
and journal in one transaction (`replace_chunkset`); update and delete
write the chunk, then its row. Invariants kept:

- ordering by `sequence` (dense ascending, gaps allowed after split)
- soft-delete (audit log keeps before/after pointers valid)
- promotion from the first completed analysis (idempotent)

Re-uses `DocumentChunker` for rechunk (same port that `AnalysisService`
uses), so chunking strategy logic is not duplicated. The document tree and
the push to stores are services of their own (`document_tree_service`,
`chunk_push_service`).
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain import chunk_editing
from domain.chunk_editing import EditJournal
from domain.chunk_serialization import chunk_from_dict
from domain.models import Chunk
from domain.value_objects import ChunkingOptions
from services.chunk_errors import (
    ChunkNotFoundError,
    ChunkServiceError,
    refusals_as_service_errors,
    require_document,
)

if TYPE_CHECKING:
    from domain.models import AnalysisJob
    from domain.ports import (
        AnalysisRepository,
        ChunkEditRepository,
        ChunkRepository,
        DocumentChunker,
        DocumentRepository,
    )

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ChunkService:
    """Orchestrates canonical chunk operations for a document."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_edit_repo: ChunkEditRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        chunker: DocumentChunker | None = None,
        actor: str = "user",
    ) -> None:
        self._chunks = chunk_repo
        self._edits = chunk_edit_repo
        self._documents = document_repo
        self._analyses = analysis_repo
        self._chunker = chunker
        self._actor = actor
        # Duck-typed recorder for document versions (#267). Wired by
        # `bootstrap.builder` to `VersionService` so each `+ Generate
        # chunks` call appends a frozen pair to the document's versions.
        self._version_recorder = None

    def set_version_recorder(self, version_service) -> None:
        """Inject the document-version recorder (#267). Contract: a
        coroutine `(document_id: str, analysis_id: str | None) -> DocumentVersion`."""
        self._version_recorder = version_service

    # -- promotion (AnalysisService keeps the hook; its flow no longer calls it, #266)

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
        journal = EditJournal(document_id, "system:initial-analysis", now)
        await self._chunks.replace_chunkset(
            document_id, at=now, add=canonical, edits=[journal.inserted(c) for c in canonical]
        )
        logger.info(
            "chunk.promote docId=%s count=%d (initial-analysis)", document_id, len(canonical)
        )
        return len(canonical)

    # -- read

    async def list_chunks(self, document_id: str) -> list[Chunk]:
        await require_document(self._documents, document_id)
        return await self._chunks.find_for_document(document_id)

    # -- mutations

    async def add_chunk(self, document_id: str, *, text: str, after_id: str | None = None) -> Chunk:
        await require_document(self._documents, document_id)
        existing = await self._chunks.find_for_document(document_id)
        with refusals_as_service_errors():
            sequence = chunk_editing.sequence_after(existing, after_id)
        now = _utcnow()
        await self._shift_sequences(document_id, existing, from_sequence=sequence, at=now)

        new_chunk = Chunk(
            document_id=document_id, sequence=sequence, text=text, created_at=now, updated_at=now
        )
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            add=[new_chunk],
            edits=[self._journal(document_id, now).inserted(new_chunk)],
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
        changes: dict = {"updated_at": _utcnow()}
        if text is not None:
            changes["text"] = text
        if headings is not None:
            changes["headings"] = list(headings)
        updated = replace(chunk, **changes)
        await self._chunks.update(updated)
        await self._edits.insert(self._journal(document_id, _utcnow()).updated(chunk, updated))
        logger.info("chunk.update docId=%s chunkId=%s", document_id, chunk.id)
        return updated

    async def delete_chunk(self, document_id: str, chunk_id: str) -> None:
        chunk = await self._require_chunk(document_id, chunk_id)
        deleted = await self._chunks.soft_delete(chunk_id, at=_utcnow())
        if not deleted:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        await self._edits.insert(self._journal(document_id, _utcnow()).deleted(chunk))
        logger.info("chunk.delete docId=%s chunkId=%s", document_id, chunk.id)

    async def split_chunk(self, document_id: str, chunk_id: str, cursor_offset: int) -> list[Chunk]:
        source = await self._require_chunk(document_id, chunk_id)
        with refusals_as_service_errors():
            head, tail = chunk_editing.split(source, cursor_offset)
        existing = await self._chunks.find_for_document(document_id)

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
            edits=[self._journal(document_id, now).split(source, [head, tail])],
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
        with refusals_as_service_errors():
            ordered, merged = chunk_editing.merge(existing, ids)

        now = _utcnow()
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[c.id for c in ordered],
            add=[merged],
            edits=[self._journal(document_id, now).merged(ordered, merged)],
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
        await require_document(self._documents, document_id)
        chunker = self._require_chunker()
        job = await self._analysis_to_rechunk(document_id)
        chunk_opts = ChunkingOptions(**options) if options else ChunkingOptions()
        results = await chunker.chunk(job.document_json, chunk_opts)

        existing = await self._chunks.find_for_document(document_id)
        now = _utcnow()
        new_chunks = chunk_editing.chunkset_from_results(document_id, results)
        # One transaction: the old chunkset is retired and the new one
        # journaled together, or not at all.
        journal = EditJournal(document_id, "system:rechunk", now)
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[c.id for c in existing],
            add=new_chunks,
            edits=[*map(journal.deleted, existing), *map(journal.inserted, new_chunks)],
        )
        logger.info(
            "chunk.rechunk docId=%s oldCount=%d newCount=%d",
            document_id,
            len(existing),
            len(new_chunks),
        )
        await self._record_version(document_id, job.id)
        return new_chunks

    def _require_chunker(self) -> DocumentChunker:
        if not self._chunker:
            raise ChunkServiceError("Chunker not configured", http_status=503)
        return self._chunker

    async def _analysis_to_rechunk(self, document_id: str) -> AnalysisJob:
        job = await self._analyses.find_latest_completed_by_document(document_id)
        if not job or not job.document_json:
            raise ChunkServiceError(
                "No completed analysis with document_json available for rechunk",
                http_status=409,
            )
        return job

    async def _record_version(self, document_id: str, analysis_id: str) -> None:
        """Record a frozen (analysis, chunks_snapshot) pair as a new document
        version (#267): the chunks just written, paired with the
        analysis they came from. Best effort — a failed snapshot never fails
        the rechunk."""
        if self._version_recorder is None:
            return
        try:
            await self._version_recorder.record_on_rechunk(document_id, analysis_id)
        except Exception:
            logger.exception("Version snapshot failed for doc %s after rechunk", document_id)

    def _journal(self, document_id: str, at: datetime) -> EditJournal:
        """The journal of an edit made by this service's actor."""
        return EditJournal(document_id, self._actor, at)

    # -- guards

    async def _require_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        chunk = await self._chunks.find_by_id(chunk_id)
        if not chunk or chunk.document_id != document_id or chunk.deleted_at is not None:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        return chunk

    # -- sequence helpers

    async def _shift_sequences(
        self, document_id: str, existing: list[Chunk], *, from_sequence: int, at: datetime
    ) -> None:
        """Push live chunks at >= from_sequence one slot up to make room, in
        one UPDATE — skipped when nothing sits there (append at the end)."""
        if any(c.sequence >= from_sequence for c in existing):
            await self._chunks.shift_sequences(document_id, from_sequence=from_sequence, at=at)

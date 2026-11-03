"""Document-version service (#267).

Records frozen (analysis_id, chunks_snapshot) pairs at the two explicit
version-creating triggers — a `+ New analysis` run completes, or a
`+ Generate chunks` (rechunk) invocation finishes. Manual chunk edits
between snapshots are NOT recorded as versions; they mutate the live
chunkset and only land in History when the next explicit trigger fires.

`restore(document_id, version_id)` writes the version's chunks_snapshot
back into the live `chunks` table. The current analysis pointer is
managed by the workspace (frontend reads `version.analysis_id` to
re-render the OCR side).
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.chunk_editing import EditJournal
from domain.chunk_serialization import chunk_from_dict, chunk_to_snapshot_dict
from domain.models import Chunk, DocumentVersion, DocumentVersionKind
from domain.ports import DocumentVersionEntry
from domain.value_objects import ChunkEditAction
from services.errors import ServiceError

if TYPE_CHECKING:
    from domain.ports import (
        ChunkRepository,
        DocumentRepository,
        DocumentVersionRepository,
    )

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _serialize_chunks(chunks: list[Chunk]) -> str:
    """Freeze a list of live `Chunk` rows into the `chunks_snapshot` JSON a
    restore reads back (shape: `domain.chunk_serialization`)."""
    return json.dumps([chunk_to_snapshot_dict(c) for c in chunks])


class VersionServiceError(ServiceError):
    http_status = 400


class VersionNotFoundError(VersionServiceError):
    http_status = 404


class VersionService:
    """Records and restores frozen (analysis, chunks) version snapshots."""

    def __init__(
        self,
        version_repo: DocumentVersionRepository,
        chunk_repo: ChunkRepository,
        document_repo: DocumentRepository,
    ):
        self._versions = version_repo
        # Journals the restore too: `replace_chunkset` writes the chunks and
        # their `chunk_edits` rows in one transaction.
        self._chunks = chunk_repo
        self._documents = document_repo

    async def list_for_document(self, document_id: str) -> list[DocumentVersionEntry]:
        """The document's history, newest first: each version without its
        snapshot body, with the number of chunks the snapshot holds."""
        await self._require_doc(document_id)
        return await self._versions.list_for_document(document_id)

    async def record_on_analysis(
        self,
        document_id: str,
        analysis_id: str,
    ) -> DocumentVersion:
        """Called by `AnalysisService` after a successful analysis run.

        The new version pairs the freshly-completed analysis with a
        snapshot of the LIVE chunks at this moment (preserves any user
        edits since the previous snapshot). When no chunks exist yet
        (first analysis of a doc), the snapshot is the literal empty
        JSON array.
        """
        chunks = await self._chunks.find_for_document(document_id)
        version = DocumentVersion(
            id=_new_id(),
            document_id=document_id,
            kind=DocumentVersionKind.ANALYSIS,
            analysis_id=analysis_id,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Analysis run",
            created_at=_utcnow(),
        )
        await self._versions.insert(version)
        return version

    async def record_on_rechunk(
        self,
        document_id: str,
        analysis_id: str | None,
    ) -> DocumentVersion:
        """Called by `ChunkService.rechunk_document` after the live
        chunkset has been replaced. Snapshots the new chunks; the
        analysis pointer is the one rechunk just consumed."""
        chunks = await self._chunks.find_for_document(document_id)
        version = DocumentVersion(
            id=_new_id(),
            document_id=document_id,
            kind=DocumentVersionKind.CHUNKS,
            analysis_id=analysis_id,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Chunks generated",
            created_at=_utcnow(),
        )
        await self._versions.insert(version)
        return version

    async def restore(self, document_id: str, version_id: str) -> DocumentVersionEntry:
        """Replace the live chunkset with the version's snapshot. The
        active-analysis pointer is the caller's responsibility (the
        frontend reads `version.analysis_id` and updates the workspace
        store).

        Returns the restored version as a history row: without its snapshot
        body, with the number of chunks restored — counted from the snapshot
        decoded here, so the caller never parses it a second time.
        """
        await self._require_doc(document_id)
        version = await self._versions.find_by_id(version_id)
        if not version or version.document_id != document_id:
            raise VersionNotFoundError(f"Version not found: {version_id}")

        # Retire the live chunks and insert the snapshot's under fresh ids,
        # journaled, in one transaction: a failure leaves the live chunkset
        # as it was. The snapshot is decoded first, so a corrupt one never
        # gets as far as deleting anything.
        new_chunks = [
            _chunk_from_snapshot(document_id, raw)
            for raw in json.loads(version.chunks_snapshot or "[]")
        ]
        now = _utcnow()

        # A restore journals no before/after snapshot, and its rows keep the
        # hex ids they always had.
        journal = EditJournal(document_id, f"system:restore:{version_id}", now, new_id=_new_id)

        existing = await self._chunks.find_for_document(document_id)
        await self._chunks.replace_chunkset(
            document_id,
            at=now,
            retire_ids=[c.id for c in existing],
            add=new_chunks,
            edits=[
                *(journal.without_snapshot(ChunkEditAction.DELETE, c) for c in existing),
                *(journal.without_snapshot(ChunkEditAction.INSERT, c) for c in new_chunks),
            ],
        )

        logger.info(
            "Restored doc %s to version %s (%d chunks)",
            document_id,
            version_id,
            len(new_chunks),
        )
        return DocumentVersionEntry(
            version=replace(version, chunks_snapshot=None), chunk_count=len(new_chunks)
        )

    async def _require_doc(self, document_id: str) -> None:
        doc = await self._documents.find_by_id(document_id)
        if not doc:
            raise VersionServiceError(f"Document not found: {document_id}", http_status=404)


def _chunk_from_snapshot(document_id: str, raw: dict) -> Chunk:
    """Inverse of `_serialize_chunks`. Skips the wire-only `id`/timestamps
    so the restored chunk gets a fresh identity (the old ids are gone
    after the soft-delete pass)."""
    return chunk_from_dict(
        raw, document_id=document_id, sequence=raw.get("sequence", 0), chunk_id=_new_id()
    )

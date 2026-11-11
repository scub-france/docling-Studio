"""Document-version service (#267).

Records frozen analysis selection and chunk snapshots at the two explicit
version-creating triggers — a `+ New analysis` run completes, or a
`+ Generate chunks` (rechunk) invocation finishes. Manual chunk edits
between snapshots are NOT recorded as versions; they mutate the live
chunkset and only land in History when the next explicit trigger fires.

`restore(document_id, version_id)` writes the version's chunks_snapshot
back into the live `chunks` table and updates the active analysis selection.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.models import (
    AnalysisStatus,
    Chunk,
    DocumentAnalysisSelection,
    DocumentChunkSource,
    DocumentVersion,
    DocumentVersionKind,
)

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        AnalysisSelectionRepository,
        ChunkRepository,
        ChunkSourceRepository,
        DocumentRepository,
    )
    from persistence.document_version_repo import SqliteDocumentVersionRepository

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _serialize_chunks(chunks: list[Chunk]) -> str:
    """Freeze a list of live `Chunk` rows into the wire-stable JSON shape
    the frontend reads back via `chunks_snapshot`. Mirrors `_chunk_to_dict`
    in ChunkService — kept independent to avoid an import cycle."""
    return json.dumps(
        [
            {
                "id": c.id,
                "documentId": c.document_id,
                "sequence": c.sequence,
                "text": c.text,
                "headings": list(c.headings),
                "sourcePage": c.source_page,
                "tokenCount": c.token_count,
                "bboxes": [{"page": b.page, "bbox": list(b.bbox)} for b in c.bboxes],
                "docItems": [{"selfRef": d.self_ref, "label": d.label} for d in c.doc_items],
                "createdAt": str(c.created_at),
                "updatedAt": str(c.updated_at),
            }
            for c in chunks
        ]
    )


class VersionServiceError(Exception):
    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class VersionNotFoundError(VersionServiceError):
    http_status = 404


class VersionService:
    """Records and restores analysis selections with chunk snapshots."""

    def __init__(
        self,
        version_repo: SqliteDocumentVersionRepository,
        chunk_repo: ChunkRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        selection_repo: AnalysisSelectionRepository,
        chunk_source_repo: ChunkSourceRepository,
    ):
        self._versions = version_repo
        self._chunks = chunk_repo
        self._documents = document_repo
        self._analyses = analysis_repo
        self._selection = selection_repo
        self._chunk_sources = chunk_source_repo

    async def list_for_document(self, document_id: str) -> list[DocumentVersion]:
        await self._require_doc(document_id)
        return await self._versions.find_for_document(document_id)

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
        source = await self._chunk_sources.get_chunk_source(document_id)
        version = DocumentVersion(
            id=_new_id(),
            document_id=document_id,
            kind=DocumentVersionKind.ANALYSIS,
            analysis_id=analysis_id,
            chunks_source_analysis_id=source.analysis_id if source else None,
            chunks_source_result_hash=source.result_hash if source else None,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Analysis run",
            created_at=_utcnow(),
        )
        await self._versions.insert(version)
        return version

    async def record_on_rechunk(
        self,
        document_id: str,
        analysis_id: str,
        source_result_hash: str,
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
            chunks_source_analysis_id=analysis_id,
            chunks_source_result_hash=source_result_hash,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Chunks generated",
            created_at=_utcnow(),
        )
        await self._versions.insert(version)
        return version

    async def restore(self, document_id: str, version_id: str) -> DocumentVersion:
        """Replace the live chunkset and select its source analysis."""
        await self._require_doc(document_id)
        version = await self._versions.find_by_id(version_id)
        if not version or version.document_id != document_id:
            raise VersionNotFoundError(f"Version not found: {version_id}")
        if version.analysis_id is not None:
            analysis = await self._analyses.find_by_id(version.analysis_id)
            if (
                analysis is None
                or analysis.document_id != document_id
                or analysis.status != AnalysisStatus.COMPLETED
            ):
                raise VersionServiceError(
                    "Version analysis is no longer available", http_status=409
                )

        # Wipe live chunks (soft-delete), then re-insert the
        # snapshot's chunks under fresh ids.
        now = _utcnow()
        existing = await self._chunks.find_for_document(document_id)
        for c in existing:
            await self._chunks.soft_delete(c.id, at=now)

        raw_chunks = json.loads(version.chunks_snapshot or "[]")
        new_chunks: list[Chunk] = []
        for raw in raw_chunks:
            new_chunks.append(_chunk_from_snapshot(document_id, raw))

        if new_chunks:
            await self._chunks.insert_many(new_chunks)

        # History restore is an aggregate operation: the backend, rather
        # than the frontend, owns which immutable analysis is active.
        if version.analysis_id is None:
            await self._selection.clear_selection(document_id)
        else:
            await self._selection.select(
                DocumentAnalysisSelection(document_id, version.analysis_id)
            )
        if version.chunks_source_analysis_id is None:
            await self._chunk_sources.clear_chunk_source(document_id)
        else:
            await self._chunk_sources.set_chunk_source(
                DocumentChunkSource(
                    document_id,
                    version.chunks_source_analysis_id,
                    version.chunks_source_result_hash,
                )
            )

        logger.info(
            "Restored doc %s to version %s (%d chunks)",
            document_id,
            version_id,
            len(new_chunks),
        )
        return version

    async def _require_doc(self, document_id: str) -> None:
        doc = await self._documents.find_by_id(document_id)
        if not doc:
            raise VersionServiceError(f"Document not found: {document_id}", http_status=404)


def _chunk_from_snapshot(document_id: str, raw: dict) -> Chunk:
    """Inverse of `_serialize_chunks`. Skips the wire-only `id`/timestamps
    so the restored chunk gets a fresh identity (the old ids are gone
    after the soft-delete pass)."""
    from domain.value_objects import ChunkBbox, ChunkDocItem

    return Chunk(
        id=_new_id(),
        document_id=document_id,
        sequence=raw.get("sequence", 0),
        text=raw.get("text", ""),
        headings=list(raw.get("headings", [])),
        source_page=raw.get("sourcePage"),
        bboxes=[ChunkBbox(page=b["page"], bbox=list(b["bbox"])) for b in raw.get("bboxes", [])],
        doc_items=[
            ChunkDocItem(self_ref=d.get("selfRef", ""), label=d.get("label", ""))
            for d in raw.get("docItems", [])
        ],
        token_count=raw.get("tokenCount"),
    )

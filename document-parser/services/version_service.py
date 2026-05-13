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
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.models import Chunk, ChunkEdit, DocumentVersion, DocumentVersionKind
from domain.value_objects import ChunkEditAction

if TYPE_CHECKING:
    from domain.ports import (
        ChunkEditRepository,
        ChunkRepository,
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
    """Records and restores frozen (analysis, chunks) version snapshots."""

    def __init__(
        self,
        version_repo: SqliteDocumentVersionRepository,
        chunk_repo: ChunkRepository,
        chunk_edit_repo: ChunkEditRepository,
        document_repo: DocumentRepository,
    ):
        self._versions = version_repo
        self._chunks = chunk_repo
        self._edits = chunk_edit_repo
        self._documents = document_repo

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

    async def restore(self, document_id: str, version_id: str) -> DocumentVersion:
        """Replace the live chunkset with the version's snapshot. The
        active-analysis pointer is the caller's responsibility (the
        frontend reads `version.analysis_id` and updates the workspace
        store)."""
        await self._require_doc(document_id)
        version = await self._versions.find_by_id(version_id)
        if not version or version.document_id != document_id:
            raise VersionNotFoundError(f"Version not found: {version_id}")

        # Wipe live chunks (soft-delete + audit), then re-insert the
        # snapshot's chunks under fresh ids.
        now = _utcnow()
        existing = await self._chunks.find_for_document(document_id)
        for c in existing:
            await self._chunks.soft_delete(c.id, at=now)
            await self._edits.insert(
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=c.id,
                    action=ChunkEditAction.DELETE,
                    actor=f"system:restore:{version_id}",
                    at=now,
                )
            )

        raw_chunks = json.loads(version.chunks_snapshot or "[]")
        new_chunks: list[Chunk] = []
        for raw in raw_chunks:
            new_chunks.append(_chunk_from_snapshot(document_id, raw))

        if new_chunks:
            await self._chunks.insert_many(new_chunks)
            for c in new_chunks:
                await self._edits.insert(
                    ChunkEdit(
                        id=_new_id(),
                        document_id=document_id,
                        chunk_id=c.id,
                        action=ChunkEditAction.INSERT,
                        actor=f"system:restore:{version_id}",
                        at=now,
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

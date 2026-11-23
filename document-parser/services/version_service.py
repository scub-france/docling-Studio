"""Document-version service (#267).

Records frozen analysis selection and chunk snapshots at the two explicit
version-creating triggers — a `+ New analysis` run completes, or a
`+ Generate chunks` (rechunk) invocation finishes. Manual chunk edits
between snapshots are NOT recorded as versions; they mutate the live
chunkset and only land in History when the next explicit trigger fires.

`restore(document_id, version_id)` writes the version's chunks_snapshot
back into the live `chunks` table and updates the document's analysis state
(active analysis and chunk source), in one transaction.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from domain.exceptions import AnalysisNotSelectableError
from domain.models import (
    Chunk,
    ChunkReplacement,
    DocumentVersion,
    DocumentVersionKind,
    generate_compact_id,
    get_utc_now,
    resolve_selection_after_restore,
)
from services.errors import ServiceError

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        ChunkRepository,
        CurrentAnalysisReader,
        DocumentAnalysisStateRepository,
        DocumentRepository,
        DocumentVersionRepository,
    )

logger = logging.getLogger(__name__)


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


class VersionServiceError(ServiceError):
    http_status: int = 400


class VersionNotFoundError(VersionServiceError):
    http_status = 404


def _build_version_analysis_gone_error() -> VersionServiceError:
    return VersionServiceError("Version analysis is no longer available", http_status=409)


class VersionService:
    """Records and restores analysis selections with chunk snapshots."""

    def __init__(
        self,
        version_repo: DocumentVersionRepository,
        chunk_repo: ChunkRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        analysis_state_repo: DocumentAnalysisStateRepository,
        current_analysis: CurrentAnalysisReader,
    ):
        self._versions = version_repo
        self._current = current_analysis
        self._chunks = chunk_repo
        self._documents = document_repo
        self._analyses = analysis_repo
        self._states = analysis_state_repo

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
        state = await self._states.find_state(document_id)
        source = state.chunk_source if state else None
        version = DocumentVersion(
            id=generate_compact_id(),
            document_id=document_id,
            kind=DocumentVersionKind.ANALYSIS,
            analysis_id=analysis_id,
            chunks_source_analysis_id=source.analysis_id if source else None,
            chunks_source_result_hash=source.result_hash if source else None,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Analysis run",
            created_at=get_utc_now(),
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
            id=generate_compact_id(),
            document_id=document_id,
            kind=DocumentVersionKind.CHUNKS,
            analysis_id=analysis_id,
            chunks_source_analysis_id=analysis_id,
            chunks_source_result_hash=source_result_hash,
            chunks_snapshot=_serialize_chunks(chunks),
            summary="Chunks generated",
            created_at=get_utc_now(),
        )
        await self._versions.insert(version)
        return version

    async def restore(self, document_id: str, version_id: str) -> DocumentVersion:
        """Replace the live chunkset and select its source analysis.

        The chunk replacement and the analysis state (active analysis, chunk
        source) are one transaction (02-2.4.3): a failure leaves both as they
        were, never restored chunks recorded against the previous analysis.
        The checks before it read separately: an analysis deleted between the
        check and the write is refused by the state trigger, the transaction
        rolls back and the caller gets the same 409 as the check gives.
        """
        await self._require_doc(document_id)
        version = await self._load_restorable_version(document_id, version_id)

        # The snapshot's chunks come back under fresh ids.
        raw_chunks = json.loads(version.chunks_snapshot or "[]")
        new_chunks: list[Chunk] = []
        for raw in raw_chunks:
            new_chunks.append(_chunk_from_snapshot(document_id, raw))

        active_analysis_id = await self._resolve_restored_selection(document_id, version)
        try:
            await self._chunks.replace_and_select(
                ChunkReplacement(
                    document_id,
                    new_chunks,
                    at=get_utc_now(),
                    chunk_source=version.chunk_source,
                    active_analysis_id=active_analysis_id,
                )
            )
        except AnalysisNotSelectableError as exc:
            raise _build_version_analysis_gone_error() from exc

        logger.info(
            "Restored doc %s to version %s (%d chunks)",
            document_id,
            version_id,
            len(new_chunks),
        )
        return version

    async def _load_restorable_version(self, document_id: str, version_id: str) -> DocumentVersion:
        """The document's version, refused when its analysis can no longer be selected."""
        version = await self._versions.find_by_id(version_id)
        if not version or version.document_id != document_id:
            raise VersionNotFoundError(f"Version not found: {version_id}")
        if version.analysis_id is not None:
            analysis = await self._analyses.find_by_id(version.analysis_id)
            if analysis is None or not analysis.can_be_current_of(document_id):
                raise _build_version_analysis_gone_error()
        return version

    async def _resolve_restored_selection(
        self, document_id: str, version: DocumentVersion
    ) -> str | None:
        # History restore is an aggregate operation: the backend, rather
        # than the frontend, owns which immutable analysis is active.
        state = await self._states.find_state(document_id)
        # The fallback is only read when the rule can pick it.
        fallback_id = None
        if version.analysis_id is None and state is None:
            fallback_id = await self._current.find_current_analysis_id(document_id)
        return resolve_selection_after_restore(state, version.analysis_id, fallback_id)

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
        id=generate_compact_id(),
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

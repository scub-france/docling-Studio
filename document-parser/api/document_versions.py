"""Document versions API router (#267).

Exposes a document's versions — frozen (analysis_id, chunks_snapshot)
pairs created on `+ New analysis` runs and on `+ Generate chunks`
invocations — and restores any of them over the live chunkset.

The restore route names its path variable `document_version_id`: it takes
a `DocumentVersion` id, never the `version_id` of an anchor, which names a
parse (`docs/architecture/glossary.md`). The URL is the same.

Routes mount under `/api/documents/{doc_id}/...`. Read-mostly + a single
write endpoint (`restore`) — the version-creation triggers fire from
`AnalysisService` and `ChunkService`, not from the API layer.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from api import deps  # noqa: TC001
from api.schemas import DocumentVersionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _to_response(version, chunks_snapshot_size: int) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        id=version.id,
        document_id=version.document_id,
        kind=version.kind.value,
        analysis_id=version.analysis_id,
        chunks_snapshot_size=chunks_snapshot_size,
        summary=version.summary,
        created_at=str(version.created_at),
    )


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionResponse])
async def list_versions(
    doc_id: str, service: deps.VersionServiceDep
) -> list[DocumentVersionResponse]:
    """List frozen versions for a document, newest-first. The chunk counts
    come from the store: the snapshots themselves are never loaded here."""
    entries = await service.list_for_document(doc_id)
    return [_to_response(e.version, e.chunk_count) for e in entries]


@router.post(
    "/{doc_id}/versions/{document_version_id}/restore",
    response_model=DocumentVersionResponse,
)
async def restore_version(
    doc_id: str, document_version_id: str, service: deps.VersionServiceDep
) -> DocumentVersionResponse:
    """Restore a frozen version — overwrites the live chunkset with the
    version's snapshot. The active-analysis pointer is managed
    client-side (the frontend reads `analysisId` off the response).
    The chunk count is the service's: the snapshot is not decoded here.
    """
    entry = await service.restore(doc_id, document_version_id)
    return _to_response(entry.version, entry.chunk_count)

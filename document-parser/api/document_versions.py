"""Document versions API router (#267).

Exposes the History timeline for a document — frozen (analysis_id,
chunks_snapshot) pairs created on `+ New analysis` runs and on
`+ Generate chunks` invocations. The drawer in the doc workspace reads
this list and can restore any version to overwrite the live chunkset.

Routes mount under `/api/documents/{doc_id}/...`. Read-mostly + a single
write endpoint (`restore`) — the version-creation triggers fire from
`AnalysisService` and `ChunkService`, not from the API layer.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.schemas import DocumentVersionResponse
from services.version_service import VersionService, VersionServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_service(request: Request) -> VersionService:
    svc = getattr(request.app.state, "version_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Version service not available")
    return svc


ServiceDep = Annotated[VersionService, Depends(_get_service)]


def _to_response(version) -> DocumentVersionResponse:
    snapshot_size = 0
    if version.chunks_snapshot:
        try:
            snapshot_size = len(json.loads(version.chunks_snapshot))
        except (json.JSONDecodeError, TypeError):
            snapshot_size = 0
    return DocumentVersionResponse(
        id=version.id,
        document_id=version.document_id,
        kind=version.kind.value,
        analysis_id=version.analysis_id,
        chunks_snapshot_size=snapshot_size,
        summary=version.summary,
        created_at=str(version.created_at),
    )


def _raise_for(error: VersionServiceError) -> None:
    raise HTTPException(status_code=error.http_status, detail=str(error))


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionResponse])
async def list_versions(doc_id: str, service: ServiceDep) -> list[DocumentVersionResponse]:
    """List frozen versions for a document, newest-first."""
    try:
        versions = await service.list_for_document(doc_id)
    except VersionServiceError as e:
        _raise_for(e)
    return [_to_response(v) for v in versions]


@router.post(
    "/{doc_id}/versions/{version_id}/restore",
    response_model=DocumentVersionResponse,
)
async def restore_version(
    doc_id: str, version_id: str, service: ServiceDep
) -> DocumentVersionResponse:
    """Restore a frozen version — overwrites the live chunkset with the
    version's snapshot. The active-analysis pointer is managed
    client-side (the frontend reads `analysisId` off the response).
    """
    try:
        version = await service.restore(doc_id, version_id)
    except VersionServiceError as e:
        _raise_for(e)
    return _to_response(version)

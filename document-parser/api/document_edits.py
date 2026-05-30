"""Document edit API router — optimistic document_json text edits."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.schemas import (
    ApplyDocumentEditCommandsRequest,
    CommitDocumentEditsRequest,
    DocumentEditCommitResponse,
    DocumentEditCommandResponse,
    DocumentEditSessionResponse,
)
from services.document_edit_service import DocumentEditService, DocumentEditServiceError

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_service(request: Request) -> DocumentEditService:
    svc = getattr(request.app.state, "document_edit_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Document edit service not available")
    return svc


ServiceDep = Annotated[DocumentEditService, Depends(_get_service)]


def _raise_for(error: DocumentEditServiceError) -> None:
    raise HTTPException(status_code=error.http_status, detail=str(error))


@router.get("/{doc_id}/edits/session", response_model=DocumentEditSessionResponse)
async def get_session(doc_id: str, service: ServiceDep) -> DocumentEditSessionResponse:
    try:
        payload = await service.get_session(doc_id)
    except DocumentEditServiceError as e:
        _raise_for(e)
        raise
    return DocumentEditSessionResponse(
        analysis_id=payload["analysisId"],
        pages=payload["pages"],
        tree=payload["tree"],
        pending_commands=[DocumentEditCommandResponse(**cmd) for cmd in payload["pendingCommands"]],
    )


@router.post("/{doc_id}/edits/commands", response_model=DocumentEditSessionResponse)
async def apply_commands(
    doc_id: str,
    body: ApplyDocumentEditCommandsRequest,
    service: ServiceDep,
) -> DocumentEditSessionResponse:
    try:
        payload = await service.apply_commands(
            doc_id,
            commands=[command.model_dump(by_alias=True) for command in body.commands],
        )
    except DocumentEditServiceError as e:
        _raise_for(e)
        raise
    return DocumentEditSessionResponse(
        analysis_id=payload["analysisId"],
        pages=payload["pages"],
        tree=payload["tree"],
        pending_commands=[DocumentEditCommandResponse(**cmd) for cmd in payload["pendingCommands"]],
    )


@router.post("/{doc_id}/edits/commit", response_model=DocumentEditCommitResponse)
async def commit_edits(
    doc_id: str,
    body: CommitDocumentEditsRequest,
    service: ServiceDep,
) -> DocumentEditCommitResponse:
    try:
        payload = await service.commit(doc_id, body.frontend_pages)
    except DocumentEditServiceError as e:
        _raise_for(e)
        raise
    return DocumentEditCommitResponse(**payload)


@router.delete("/{doc_id}/edits/session", response_model=None, status_code=204)
async def discard_session(doc_id: str, service: ServiceDep) -> None:
    try:
        await service.discard(doc_id)
    except DocumentEditServiceError as e:
        _raise_for(e)

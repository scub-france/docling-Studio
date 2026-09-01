"""Analysis editor API: load, preview, save, and rebuild."""

from __future__ import annotations

import json
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query

from api import deps  # noqa: TC001
from api.schemas import (
    AnalysisEditHistoryEntryResponse,
    AnalysisEditorResponse,
    AnalysisEditRequest,
    AnalysisEditSaveResponse,
    AnalysisResponse,
)
from domain.analysis_editing import (
    AnalysisEditConflictError,
    AnalysisEditError,
    AnalysisEditUnavailableError,
    EditCommand,
)

router = APIRouter(prefix="/api/documents", tags=["analysis-editor"])


def _analysis(job) -> AnalysisResponse:
    return AnalysisResponse(
        id=job.id,
        document_id=job.document_id,
        document_filename=job.document_filename,
        status=job.status.value,
        content_markdown=job.content_markdown,
        content_html=job.content_html,
        pages_json=job.pages_json,
        chunks_json=job.chunks_json,
        has_document_json=job.document_json is not None,
        error_message=job.error_message,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        started_at=str(job.started_at) if job.started_at else None,
        completed_at=str(job.completed_at) if job.completed_at else None,
        created_at=str(job.created_at),
    )


def _tree(node) -> dict:
    return {
        "elementId": node.element_id,
        "type": node.type,
        "label": node.label,
        "children": [_tree(child) for child in node.children],
    }


def _response(snapshot) -> AnalysisEditorResponse:
    model = json.loads(snapshot.projection.editor_model_json)
    return AnalysisEditorResponse(
        model=model,
        tree=[_tree(node) for node in snapshot.projection.tree],
        reading_order=[element.id for element in snapshot.projection.elements],
        result=_analysis(snapshot.job),
        applied_through_sequence=snapshot.applied_through_sequence,
        chunks_stale=snapshot.chunks_stale,
        warnings=list(snapshot.projection.warnings),
        reference_changes=snapshot.projection.reference_changes,
    )


def _history_entry(record) -> AnalysisEditHistoryEntryResponse:
    return AnalysisEditHistoryEntryResponse(
        id=record.id,
        sequence=record.sequence,
        command_version=record.command.command_version,
        command_type=record.command.command_type,
        payload=record.command.payload,
        command_hash=record.command_hash,
        created_at=str(record.created_at),
    )


def _commands(body: AnalysisEditRequest) -> list[EditCommand]:
    commands: list[EditCommand] = []
    for command in body.commands:
        if command.type == "replaceText":
            payload = {"elementId": command.element_id, "text": command.text}
        elif command.type == "mergeText":
            payload = {"elementIds": command.element_ids, "separator": command.separator}
        elif command.type == "setHeadingLevel":
            payload = {"elementId": command.element_id, "level": command.level}
        elif command.type == "deleteElement":
            payload = {"elementId": command.element_id}
        else:
            payload = {
                "elementId": command.element_id,
                "beforeElementId": command.before_element_id,
            }
        commands.append(EditCommand(command_type=command.type, payload=payload))
    return commands


def _raise(exc: Exception) -> NoReturn:
    if isinstance(exc, AnalysisEditConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, AnalysisEditUnavailableError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, AnalysisEditError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("/{doc_id}/analysis-editor", response_model=AnalysisEditorResponse)
async def load_editor(
    doc_id: str,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _response(await service.load_editor(doc_id, analysis_id))
    except Exception as exc:
        _raise(exc)


@router.post("/{doc_id}/analysis-edits/preview", response_model=AnalysisEditorResponse)
async def preview_edits(
    doc_id: str,
    body: AnalysisEditRequest,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _response(await service.preview(doc_id, _commands(body), analysis_id))
    except Exception as exc:
        _raise(exc)


@router.get(
    "/{doc_id}/analysis-edits/history",
    response_model=list[AnalysisEditHistoryEntryResponse],
)
async def edit_history(
    doc_id: str,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> list[AnalysisEditHistoryEntryResponse]:
    try:
        return [_history_entry(record) for record in await service.history(doc_id, analysis_id)]
    except Exception as exc:
        _raise(exc)


@router.post("/{doc_id}/analysis-edits", response_model=AnalysisEditSaveResponse)
async def save_edits(
    doc_id: str,
    body: AnalysisEditRequest,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditSaveResponse:
    try:
        snapshot = await service.save(
            doc_id,
            _commands(body),
            body.expected_applied_through_sequence,
            analysis_id,
        )
        return AnalysisEditSaveResponse(
            result=_analysis(snapshot.job),
            base_analysis_id=snapshot.base_analysis_id,
            applied_through_sequence=snapshot.applied_through_sequence,
            chunks_stale=snapshot.chunks_stale,
        )
    except Exception as exc:
        _raise(exc)


@router.post("/{doc_id}/analysis-edits/rebuild", response_model=AnalysisEditorResponse)
async def rebuild_edits(
    doc_id: str,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _response(await service.rebuild(doc_id, analysis_id))
    except Exception as exc:
        _raise(exc)

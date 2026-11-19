"""Analysis editor API: load, preview, save, and rebuild."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Query

from api import deps  # noqa: TC001
from api.errors import to_http_error
from api.schemas import (
    AnalysisEditHistoryActionRequest,
    AnalysisEditHistoryEntryResponse,
    AnalysisEditorModelResponse,
    AnalysisEditorResponse,
    AnalysisEditRequest,
    AnalysisEditSaveResponse,
    AnalysisResponse,
    EditorTreeNodeResponse,
)
from domain.analysis_editing import AnalysisEditError, EditCommand

if TYPE_CHECKING:
    from domain.analysis_editing import EditorTreeNode

router = APIRouter(prefix="/api/documents", tags=["analysis-editor"])


def _to_analysis_response(job) -> AnalysisResponse:
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


def _to_tree_node_response(node: EditorTreeNode) -> EditorTreeNodeResponse:
    return EditorTreeNodeResponse(
        element_id=node.element_id,
        type=node.type,
        label=node.label,
        children=[_to_tree_node_response(child) for child in node.children],
    )


def _to_editor_response(snapshot) -> AnalysisEditorResponse:
    return AnalysisEditorResponse(
        # The projector writes this JSON on every projection, cached or not,
        # so it always has the shape the model declares.
        model=AnalysisEditorModelResponse.model_validate(snapshot.projection.read_editor_model()),
        tree=[_to_tree_node_response(node) for node in snapshot.projection.tree],
        reading_order=[element.id for element in snapshot.projection.elements],
        result=_to_analysis_response(snapshot.job),
        applied_through_sequence=snapshot.applied_through_sequence,
        chunks_stale=snapshot.chunks_stale,
        warnings=list(snapshot.projection.warnings),
        reference_changes=snapshot.projection.reference_changes,
    )


def _to_history_entry(entry) -> AnalysisEditHistoryEntryResponse:
    record = entry.record
    return AnalysisEditHistoryEntryResponse(
        id=record.id,
        sequence=record.sequence,
        command_version=record.command.command_version,
        command_type=record.command.command_type,
        payload=record.command.payload,
        command_hash=record.command_hash,
        created_at=str(record.created_at),
        active=entry.active,
    )


def _to_edit_commands(body: AnalysisEditRequest) -> list[EditCommand]:
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
        elif command.type == "deleteElements":
            payload = {"elementIds": command.element_ids}
        else:
            payload = {
                "elementId": command.element_id,
                "beforeElementId": command.before_element_id,
                "targetElementId": command.target_element_id,
                "placement": command.placement,
            }
        commands.append(EditCommand(command_type=command.type, payload=payload))
    return commands


@router.get("/{doc_id}/analysis-editor", response_model=AnalysisEditorResponse)
async def load_editor(
    doc_id: str,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _to_editor_response(await service.load_editor(doc_id, analysis_id))
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc


@router.post("/{doc_id}/analysis-edits/preview", response_model=AnalysisEditorResponse)
async def preview_edits(
    doc_id: str,
    body: AnalysisEditRequest,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _to_editor_response(
            await service.preview(doc_id, _to_edit_commands(body), analysis_id)
        )
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc


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
        entries = await service.list_history_entries(doc_id, analysis_id)
        return [_to_history_entry(entry) for entry in entries]
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc


@router.patch("/{doc_id}/analysis-edits/history/{sequence}", response_model=AnalysisEditorResponse)
async def set_edit_active(
    doc_id: str,
    sequence: int,
    body: AnalysisEditHistoryActionRequest,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _to_editor_response(
            await service.set_command_active(
                doc_id,
                sequence,
                body.active,
                body.expected_applied_through_sequence,
                analysis_id,
            )
        )
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc


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
            _to_edit_commands(body),
            body.expected_applied_through_sequence,
            analysis_id,
        )
        return AnalysisEditSaveResponse(
            result=_to_analysis_response(snapshot.job),
            base_analysis_id=snapshot.base_analysis_id,
            applied_through_sequence=snapshot.applied_through_sequence,
            chunks_stale=snapshot.chunks_stale,
        )
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc


@router.post("/{doc_id}/analysis-edits/rebuild", response_model=AnalysisEditorResponse)
async def rebuild_edits(
    doc_id: str,
    service: deps.AnalysisEditServiceDep,
    analysis_id: str | None = Query(default=None, alias="analysisId"),
) -> AnalysisEditorResponse:
    try:
        return _to_editor_response(await service.rebuild(doc_id, analysis_id))
    except AnalysisEditError as exc:
        raise to_http_error(exc) from exc

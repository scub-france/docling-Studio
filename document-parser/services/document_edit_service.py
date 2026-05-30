"""Document edit service — optimistic document_json mutations with replay."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from docling_core.types.doc import DocItem, DoclingDocument, SectionHeaderItem, TextItem, TitleItem
from docling_core.types.doc.base import BoundingBox, CoordOrigin
from docling_core.types.doc.labels import DocItemLabel

from domain.models import DocumentEdit
from domain.value_objects import DocumentEditAction, DocumentEditStatus
from infra.docling_tree import DoclingTreeReader
from infra.local_converter import _extract_pages_detail
from services.chunk_service import _build_tree_nodes

if TYPE_CHECKING:
    from domain.models import AnalysisJob, Document
    from domain.ports import (
        AnalysisRepository,
        DocumentEditRepository,
        DocumentRepository,
        DocumentTreeReader,
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class DocumentEditServiceError(Exception):
    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class DocumentEditNotFoundError(DocumentEditServiceError):
    http_status = 404


class DocumentEditConflictError(DocumentEditServiceError):
    http_status = 409


class DocumentEditService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        edit_repo: DocumentEditRepository,
        tree_reader: DocumentTreeReader | None = None,
        actor: str = "user",
    ) -> None:
        self._documents = document_repo
        self._analyses = analysis_repo
        self._edits = edit_repo
        self._tree = tree_reader or DoclingTreeReader()
        self._actor = actor

    async def get_session(self, document_id: str) -> dict[str, Any]:
        await self._require_document(document_id)
        analysis = await self._require_analysis(document_id)
        edits = await self._edits.find_pending_for_document(document_id)
        document = self._load_doc(analysis.document_json)
        self._apply_edits(document, edits)
        return {
            "analysisId": analysis.id,
            "pages": self._render_pages(document),
            "tree": self._render_tree(document),
            "pendingCommands": [self._edit_to_dict(edit) for edit in edits],
        }

    async def apply_commands(
        self,
        document_id: str,
        *,
        commands: list[dict[str, Any]],
        actor: str | None = None,
    ) -> dict[str, Any]:
        await self._require_document(document_id)
        analysis = await self._require_analysis(document_id)
        pending = await self._edits.find_pending_for_document(document_id)
        new_edits = [
            self._command_to_edit(document_id, analysis.id, command, actor=actor or self._actor)
            for command in commands
        ]
        preview_document = self._preview_document(analysis, [*pending, *new_edits])
        for edit in new_edits:
            await self._edits.insert(edit)
        return {
            "analysisId": analysis.id,
            "pages": self._render_pages(preview_document),
            "tree": self._render_tree(preview_document),
            "pendingCommands": [self._edit_to_dict(cmd) for cmd in [*pending, *new_edits]],
        }

    async def commit(
        self,
        document_id: str,
        frontend_pages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        await self._require_document(document_id)
        analysis = await self._require_analysis(document_id)
        pending = await self._edits.find_pending_for_document(document_id)
        if not pending:
            return {
                "committed": True,
                "consistent": True,
                "differences": [],
                "pages": [],
                "tree": [],
            }

        document = self._load_doc(analysis.document_json)
        self._apply_edits(document, pending)
        backend_pages = self._render_pages(document)
        backend_tree = self._render_tree(document)
        differences = _diff_pages(frontend_pages, backend_pages)
        if differences:
            return {
                "committed": False,
                "consistent": False,
                "differences": differences,
                "pages": backend_pages,
                "tree": backend_tree,
            }

        analysis.document_json = json.dumps(document.export_to_dict())
        analysis.pages_json = json.dumps(backend_pages)
        analysis.content_markdown = document.export_to_markdown()
        analysis.content_html = document.export_to_html()
        analysis.completed_at = _utcnow()
        await self._analyses.update_status(analysis)
        await self._edits.mark_committed([edit.id for edit in pending])
        return {
            "committed": True,
            "consistent": True,
            "differences": [],
            "pages": backend_pages,
            "tree": backend_tree,
        }

    async def discard(self, document_id: str) -> int:
        await self._require_document(document_id)
        return await self._edits.clear_pending_for_document(document_id)

    async def _require_document(self, document_id: str) -> Document:
        doc = await self._documents.find_by_id(document_id)
        if doc is None:
            raise DocumentEditNotFoundError(f"Document not found: {document_id}")
        return doc

    async def _require_analysis(self, document_id: str) -> AnalysisJob:
        job = await self._analyses.find_latest_completed_by_document(document_id)
        if job is None or not job.document_json:
            raise DocumentEditNotFoundError(
                f"No completed analysis with document_json for document {document_id}"
            )
        return job

    def _preview_from(
        self, analysis: AnalysisJob, edits: list[DocumentEdit]
    ) -> list[dict[str, Any]]:
        return self._render_pages(self._preview_document(analysis, edits))

    def _preview_document(
        self, analysis: AnalysisJob, edits: list[DocumentEdit]
    ) -> DoclingDocument:
        document = self._load_doc(analysis.document_json)
        self._apply_edits(document, edits)
        return document

    def _load_doc(self, raw_document_json: str | None) -> DoclingDocument:
        if not raw_document_json:
            raise DocumentEditNotFoundError("Missing document_json")
        return DoclingDocument.model_validate(json.loads(raw_document_json))

    def _apply_edits(self, document: DoclingDocument, edits: list[DocumentEdit]) -> None:
        for edit in edits:
            if edit.action is DocumentEditAction.UPDATE_PAGE_ELEMENT:
                self._apply_update_page_element(document, edit)

    def _command_to_edit(
        self,
        document_id: str,
        analysis_id: str,
        command: dict[str, Any],
        *,
        actor: str,
    ) -> DocumentEdit:
        action = DocumentEditAction(command.get("action"))
        target_ref = str(command.get("targetRef") or command.get("target_ref") or "")
        payload = command.get("payload")
        if not isinstance(payload, dict):
            raise DocumentEditConflictError("Document edit command payload must be an object")
        if not target_ref:
            raise DocumentEditConflictError("Document edit command targetRef is required")
        self._validate_payload(action, payload)
        return DocumentEdit(
            id=_new_id(),
            document_id=document_id,
            analysis_id=analysis_id,
            action=action,
            target_ref=target_ref,
            payload=payload,
            actor=actor,
            at=_utcnow(),
            status=DocumentEditStatus.PENDING,
        )

    def _validate_payload(self, action: DocumentEditAction, payload: dict[str, Any]) -> None:
        if action is not DocumentEditAction.UPDATE_PAGE_ELEMENT:
            raise DocumentEditConflictError(f"Unsupported document edit action: {action.value}")
        allowed = {"content", "bbox", "type"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise DocumentEditConflictError(
                f"Unsupported update_page_element payload fields: {', '.join(unknown)}"
            )
        if not payload:
            raise DocumentEditConflictError("update_page_element payload cannot be empty")
        if (
            "content" in payload
            and payload["content"] is not None
            and not isinstance(payload["content"], str)
        ):
            raise DocumentEditConflictError("payload.content must be a string")
        if (
            "type" in payload
            and payload["type"] is not None
            and not isinstance(payload["type"], str)
        ):
            raise DocumentEditConflictError("payload.type must be a string")
        if "bbox" in payload:
            bbox = payload["bbox"]
            if not isinstance(bbox, list) or len(bbox) != 4:
                raise DocumentEditConflictError("payload.bbox must be a 4-number list")
            try:
                [float(value) for value in bbox]
            except (TypeError, ValueError) as exc:
                raise DocumentEditConflictError("payload.bbox must contain only numbers") from exc

    def _apply_update_page_element(self, document: DoclingDocument, edit: DocumentEdit) -> None:
        item = self._find_item(document, edit.target_ref)
        payload = edit.payload
        if "content" in payload:
            self._apply_content(item, edit.target_ref, payload.get("content"))
        if "bbox" in payload:
            self._apply_bbox(document, item, payload["bbox"])
        if "type" in payload:
            self._apply_type(document, item, edit.target_ref, payload.get("type"))

    def _apply_content(self, item: DocItem, target_ref: str, content: Any) -> None:
        if not hasattr(item, "text"):
            raise DocumentEditConflictError(f"Item does not support content edits: {target_ref}")
        next_text = "" if content is None else str(content)
        item.text = next_text
        if hasattr(item, "orig"):
            item.orig = next_text

    def _apply_bbox(self, document: DoclingDocument, item: DocItem, bbox_values: list[Any]) -> None:
        if not getattr(item, "prov", None):
            raise DocumentEditConflictError(
                f"Item does not have provenance: {getattr(item, 'self_ref', '')}"
            )
        for prov in item.prov:
            page = document.pages.get(prov.page_no)
            if page is None:
                raise DocumentEditConflictError(f"Page not found for bbox update: {prov.page_no}")
            top_left_bbox = BoundingBox(
                l=float(bbox_values[0]),
                t=float(bbox_values[1]),
                r=float(bbox_values[2]),
                b=float(bbox_values[3]),
                coord_origin=CoordOrigin.TOPLEFT,
            )
            current_bbox = prov.bbox
            if current_bbox is not None and current_bbox.coord_origin is CoordOrigin.BOTTOMLEFT:
                prov.bbox = top_left_bbox.to_bottom_left_origin(page.size.height)
            else:
                prov.bbox = top_left_bbox

    def _apply_type(
        self, document: DoclingDocument, item: DocItem, target_ref: str, type_name: Any
    ) -> None:
        if type_name is None:
            return
        next_label = _TYPE_TO_LABEL.get(str(type_name))
        if next_label is None:
            raise DocumentEditConflictError(f"Unsupported page element type: {type_name}")
        allowed = _allowed_labels_for_item(item)
        if next_label not in allowed:
            supported = ", ".join(sorted(_label_to_type_name(label) for label in allowed))
            raise DocumentEditConflictError(
                f"Type change not supported for {target_ref}: {type_name} (allowed: {supported})"
            )
        if isinstance(item, TextItem):
            replacement = _build_text_family_item(item, next_label)
            if replacement is None:
                item.label = next_label
                return
            _replace_text_item_in_document(document, item, replacement)
            return
        item.label = next_label

    def _find_item(self, document: DoclingDocument, target_ref: str):
        for item, _level in document.iterate_items(with_groups=True):
            if getattr(item, "self_ref", "") == target_ref:
                return item
        raise DocumentEditNotFoundError(f"Document item not found: {target_ref}")

    def _render_pages(self, document: DoclingDocument) -> list[dict[str, Any]]:
        pages, _skipped = _extract_pages_detail(SimpleNamespace(document=document))
        return [asdict(page) for page in pages]

    def _render_tree(self, document: DoclingDocument) -> list[dict[str, Any]]:
        return _build_tree_nodes(document.export_to_dict(), self._tree)

    def _edit_to_dict(self, edit: DocumentEdit) -> dict[str, Any]:
        return {
            "id": edit.id,
            "analysisId": edit.analysis_id,
            "action": edit.action.value,
            "targetRef": edit.target_ref,
            "payload": edit.payload,
            "actor": edit.actor,
            "at": str(edit.at),
            "status": edit.status.value,
        }


def _diff_pages(
    frontend_pages: list[dict[str, Any]], backend_pages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    frontend_by_ref = _elements_by_ref(frontend_pages)
    backend_by_ref = _elements_by_ref(backend_pages)
    differences: list[dict[str, Any]] = []
    for ref in sorted(set(frontend_by_ref) | set(backend_by_ref)):
        frontend = frontend_by_ref.get(ref)
        backend = backend_by_ref.get(ref)
        if frontend is None or backend is None:
            differences.append(
                {"ref": ref, "field": "presence", "frontend": frontend, "backend": backend}
            )
            continue
        for field in ("type", "content", "level"):
            if frontend.get(field) != backend.get(field):
                differences.append(
                    {
                        "ref": ref,
                        "field": field,
                        "frontend": frontend.get(field),
                        "backend": backend.get(field),
                    }
                )
        if not _bbox_equal(frontend.get("bbox"), backend.get("bbox")):
            differences.append(
                {
                    "ref": ref,
                    "field": "bbox",
                    "frontend": frontend.get("bbox"),
                    "backend": backend.get("bbox"),
                }
            )
    return differences


def _elements_by_ref(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for page in pages:
        for element in page.get("elements", []):
            ref = element.get("self_ref") or ""
            if ref:
                out[ref] = element
    return out


def _bbox_equal(left: Any, right: Any, tolerance: float = 0.001) -> bool:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return left == right
    return all(abs(float(a) - float(b)) <= tolerance for a, b in zip(left, right, strict=False))


_TYPE_TO_LABEL: dict[str, DocItemLabel] = {
    "text": DocItemLabel.TEXT,
    "title": DocItemLabel.TITLE,
    "section_header": DocItemLabel.SECTION_HEADER,
    "list": DocItemLabel.LIST_ITEM,
    "formula": DocItemLabel.FORMULA,
    "code": DocItemLabel.CODE,
    "picture": DocItemLabel.PICTURE,
    "table": DocItemLabel.TABLE,
    "caption": DocItemLabel.CAPTION,
    "floating": DocItemLabel.FOOTNOTE,
}


def _allowed_labels_for_item(item: DocItem) -> set[DocItemLabel]:
    class_name = item.__class__.__name__
    if class_name in {
        "TextItem",
        "TitleItem",
        "SectionHeaderItem",
        "ListItem",
        "CodeItem",
        "FormulaItem",
    }:
        return {
            DocItemLabel.TEXT,
            DocItemLabel.TITLE,
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.LIST_ITEM,
            DocItemLabel.CODE,
            DocItemLabel.FORMULA,
            DocItemLabel.CAPTION,
        }
    if class_name == "PictureItem":
        return {DocItemLabel.PICTURE, DocItemLabel.CHART}
    if class_name == "TableItem":
        return {DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX}
    return {getattr(item, "label", DocItemLabel.TEXT)}


def _label_to_type_name(label: DocItemLabel) -> str:
    if label is DocItemLabel.LIST_ITEM:
        return "list"
    if label is DocItemLabel.CHART:
        return "picture"
    if label is DocItemLabel.DOCUMENT_INDEX:
        return "table"
    if label is DocItemLabel.FOOTNOTE:
        return "floating"
    return str(label.value)


def _build_text_family_item(item: TextItem, next_label: DocItemLabel) -> TextItem | None:
    payload = item.model_dump(mode="python")
    payload["label"] = next_label
    if next_label is DocItemLabel.TITLE:
        payload.pop("level", None)
        return TitleItem.model_validate(payload)
    if next_label is DocItemLabel.SECTION_HEADER:
        payload["level"] = getattr(item, "level", 1) or 1
        return SectionHeaderItem.model_validate(payload)
    if next_label in {
        DocItemLabel.CAPTION,
        DocItemLabel.CHECKBOX_SELECTED,
        DocItemLabel.CHECKBOX_UNSELECTED,
        DocItemLabel.FOOTNOTE,
        DocItemLabel.PAGE_FOOTER,
        DocItemLabel.PAGE_HEADER,
        DocItemLabel.PARAGRAPH,
        DocItemLabel.REFERENCE,
        DocItemLabel.TEXT,
        DocItemLabel.EMPTY_VALUE,
        DocItemLabel.FIELD_KEY,
        DocItemLabel.FIELD_HINT,
        DocItemLabel.MARKER,
        DocItemLabel.HANDWRITTEN_TEXT,
    }:
        payload.pop("level", None)
        return TextItem.model_validate(payload)
    return None


def _replace_text_item_in_document(
    document: DoclingDocument, old_item: TextItem, new_item: TextItem
) -> None:
    path = old_item.self_ref.split("/")
    if len(path) != 3 or path[1] != "texts":
        raise DocumentEditConflictError(
            f"Unsupported text item ref for type replacement: {old_item.self_ref}"
        )
    try:
        index = int(path[2])
    except ValueError as exc:
        raise DocumentEditConflictError(
            f"Unsupported text item ref for type replacement: {old_item.self_ref}"
        ) from exc
    # Mutate the canonical texts array in place so the self_ref and tree references stay stable.
    document.texts[index] = new_item

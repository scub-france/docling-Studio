"""Experimental Docling document editing service.

Provides an in-memory editing session over the latest completed
`document_json` for a document. The session tracks undo/redo with RFC 6902
patches and can be committed as a new completed analysis snapshot.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import jsonpatch
from docling_core.types.doc.document import (
    BoundingBox,
    CodeItem,
    DocItem,
    DoclingDocument,
    FloatingItem,
    FormulaItem,
    GroupItem,
    ListItem,
    PictureItem,
    RefItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from domain.models import AnalysisJob, AnalysisStatus
from domain.value_objects import DEFAULT_PAGE_HEIGHT, DEFAULT_PAGE_WIDTH, PageDetail, PageElement
from infra.bbox import to_topleft_list
from services.chunk_service import _build_tree_nodes


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DoclingEditServiceError(Exception):
    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class EditSessionNotFoundError(DoclingEditServiceError):
    http_status = 404


class EditSourceNotFoundError(DoclingEditServiceError):
    http_status = 404


class EditValidationError(DoclingEditServiceError):
    http_status = 400


def _iter_doc_collections(doc: DoclingDocument) -> list[list[Any]]:
    return [
        list(getattr(doc, "furniture", []) or []),
        list(getattr(doc, "groups", []) or []),
        list(getattr(doc, "texts", []) or []),
        list(getattr(doc, "pictures", []) or []),
        list(getattr(doc, "tables", []) or []),
        list(getattr(doc, "key_value_items", []) or []),
        list(getattr(doc, "form_items", []) or []),
        list(getattr(doc, "field_regions", []) or []),
        list(getattr(doc, "field_items", []) or []),
    ]


def get_document_item(doc: DoclingDocument, ref: str) -> Any:
    for collection in _iter_doc_collections(doc):
        for item in collection:
            if getattr(item, "self_ref", None) == ref:
                return item
    return None


def _get_parent_children(doc: DoclingDocument, parent_ref: str | None) -> list[RefItem] | None:
    if parent_ref in (None, "#/body"):
        body = getattr(doc, "body", None)
        return getattr(body, "children", None)
    parent = get_document_item(doc, parent_ref)
    if parent is None:
        return None
    return getattr(parent, "children", None)


def _merge_provenance(lead_item: TextItem, trail_item: TextItem) -> None:
    if not lead_item.prov:
        return
    for prov in lead_item.prov:
        prov.charspan = [0, len(lead_item.text)]
    if not trail_item.prov:
        return
    lead_bbox = lead_item.prov[0].bbox
    trail_bbox = trail_item.prov[0].bbox
    if lead_bbox and trail_bbox:
        lead_item.prov[0].bbox = BoundingBox(
            l=min(lead_bbox.l, trail_bbox.l),
            t=min(lead_bbox.t, trail_bbox.t),
            r=max(lead_bbox.r, trail_bbox.r),
            b=max(lead_bbox.b, trail_bbox.b),
            coord_origin=lead_bbox.coord_origin,
        )
    if len(trail_item.prov) > 1:
        lead_item.prov.extend(copy.deepcopy(trail_item.prov[1:]))


def _assert_adjacent_texts(doc: DoclingDocument, leading_ref: str, trailing_ref: str) -> None:
    lead_item = get_document_item(doc, leading_ref)
    trail_item = get_document_item(doc, trailing_ref)
    if not isinstance(lead_item, TextItem) or not isinstance(trail_item, TextItem):
        raise EditValidationError("Both items must be TextItem instances")
    lead_parent_ref = lead_item.parent.cref if lead_item.parent else None
    trail_parent_ref = trail_item.parent.cref if trail_item.parent else None
    if lead_parent_ref != trail_parent_ref:
        raise EditValidationError("Text items must share the same parent to merge")
    siblings = _get_parent_children(doc, lead_parent_ref)
    if not siblings:
        raise EditValidationError("Cannot resolve sibling order for merge")
    sibling_refs = [ref.cref for ref in siblings]
    try:
        lead_ix = sibling_refs.index(leading_ref)
        trail_ix = sibling_refs.index(trailing_ref)
    except ValueError as exc:
        raise EditValidationError("Text items are not present in the parent children list") from exc
    if trail_ix != lead_ix + 1:
        raise EditValidationError("Text items must be adjacent siblings to merge")


def edit_text_item(doc: DoclingDocument, item_ref: str, text: str) -> DoclingDocument:
    doc_copy = copy.deepcopy(doc)
    item = get_document_item(doc_copy, item_ref)
    if not isinstance(item, TextItem):
        raise EditValidationError(f"Item {item_ref} is not a TextItem")
    item.text = text
    item.orig = text
    for prov in item.prov or []:
        prov.charspan = [0, len(text)]
    return doc_copy


def reparent_item(doc: DoclingDocument, child_ref: str, target_parent_ref: str) -> DoclingDocument:
    doc_copy = copy.deepcopy(doc)
    child = get_document_item(doc_copy, child_ref)
    if child is None:
        raise EditValidationError(f"Item not found: {child_ref}")
    target_parent = get_document_item(doc_copy, target_parent_ref)
    if not isinstance(target_parent, GroupItem):
        raise EditValidationError(f"Target parent is not a group: {target_parent_ref}")

    old_parent_ref = child.parent.cref if getattr(child, "parent", None) else None
    old_parent_children = _get_parent_children(doc_copy, old_parent_ref)
    if old_parent_children is not None:
        old_parent_children[:] = [ref for ref in old_parent_children if ref.cref != child_ref]

    target_children = getattr(target_parent, "children", None)
    if target_children is None:
        target_parent.children = []
        target_children = target_parent.children
    if not any(ref.cref == child_ref for ref in target_children):
        target_children.append(RefItem(cref=child_ref))
    child.parent = RefItem(cref=target_parent_ref)
    return doc_copy


def merge_adjacent_texts(
    doc: DoclingDocument,
    leading_ref: str,
    trailing_ref: str,
    spacer: str = " ",
) -> DoclingDocument:
    _assert_adjacent_texts(doc, leading_ref, trailing_ref)
    doc_copy = copy.deepcopy(doc)
    lead_item = get_document_item(doc_copy, leading_ref)
    trail_item = get_document_item(doc_copy, trailing_ref)
    if not isinstance(lead_item, TextItem) or not isinstance(trail_item, TextItem):
        raise EditValidationError("Both items must be TextItem instances")

    lead_item.text = f"{lead_item.text}{spacer}{trail_item.text}"
    lead_item.orig = (
        f"{lead_item.orig or lead_item.text}{spacer}{trail_item.orig or trail_item.text}"
    )
    _merge_provenance(lead_item, trail_item)
    doc_copy.delete_items(node_items=[trail_item])
    return doc_copy


class DoclingTransactionManager:
    def __init__(self, doc: DoclingDocument):
        self.doc = doc
        self.undo_stack: list[tuple[jsonpatch.JsonPatch, jsonpatch.JsonPatch]] = []
        self.redo_stack: list[tuple[jsonpatch.JsonPatch, jsonpatch.JsonPatch]] = []

    def _get_clean_dict(self, doc: DoclingDocument) -> dict:
        cached_pages = doc.pages
        doc.pages = {}
        try:
            return doc.export_to_dict()
        finally:
            doc.pages = cached_pages

    def commit_document(self, new_doc: DoclingDocument) -> bool:
        old_state = self._get_clean_dict(self.doc)
        new_state = self._get_clean_dict(new_doc)
        forward_patch = jsonpatch.JsonPatch.from_diff(old_state, new_state)
        reverse_patch = jsonpatch.JsonPatch.from_diff(new_state, old_state)
        if len(forward_patch.patch) == 0:
            return False
        new_doc.pages = self.doc.pages
        self.doc = new_doc
        self.undo_stack.append((forward_patch, reverse_patch))
        self.redo_stack.clear()
        return True

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        forward_patch, reverse_patch = self.undo_stack.pop()
        current_state = self._get_clean_dict(self.doc)
        restored_state = reverse_patch.apply(current_state)
        restored_doc = DoclingDocument.model_validate(restored_state)
        restored_doc.pages = self.doc.pages
        self.doc = restored_doc
        self.redo_stack.append((forward_patch, reverse_patch))
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        forward_patch, reverse_patch = self.redo_stack.pop()
        current_state = self._get_clean_dict(self.doc)
        restored_state = forward_patch.apply(current_state)
        restored_doc = DoclingDocument.model_validate(restored_state)
        restored_doc.pages = self.doc.pages
        self.doc = restored_doc
        self.undo_stack.append((forward_patch, reverse_patch))
        return True

    @property
    def has_changes(self) -> bool:
        return bool(self.undo_stack)


_ELEMENT_TYPE_MAP: list[tuple[type, str]] = [
    (TableItem, "table"),
    (PictureItem, "picture"),
    (TitleItem, "title"),
    (SectionHeaderItem, "section_header"),
    (ListItem, "list"),
    (FormulaItem, "formula"),
    (CodeItem, "code"),
    (FloatingItem, "floating"),
    (TextItem, "text"),
]


def _get_element_type(item: DocItem) -> str:
    for cls, type_name in _ELEMENT_TYPE_MAP:
        if isinstance(item, cls):
            return type_name
    return "text"


def _build_pages_json(doc: DoclingDocument) -> str:
    pages: dict[int, PageDetail] = {}
    for page_key, page_obj in doc.pages.items():
        page_no = int(page_key) if isinstance(page_key, str) else page_key
        pages[page_no] = PageDetail(
            page_number=page_no,
            width=page_obj.size.width,
            height=page_obj.size.height,
        )
    for item, level in doc.iterate_items():
        if isinstance(item, GroupItem):
            continue
        if not isinstance(item, DocItem) or not item.prov:
            continue
        for prov in item.prov:
            page_no = prov.page_no
            if page_no not in pages:
                pages[page_no] = PageDetail(
                    page_number=page_no,
                    width=DEFAULT_PAGE_WIDTH,
                    height=DEFAULT_PAGE_HEIGHT,
                )
            page_height = pages[page_no].height
            bbox = [0.0, 0.0, 0.0, 0.0]
            if prov.bbox:
                bbox = to_topleft_list(prov.bbox, page_height)
            content = getattr(item, "text", "") or ""
            if isinstance(item, TableItem):
                try:
                    content = item.export_to_markdown()
                except (AttributeError, ValueError):
                    content = getattr(item, "text", "") or ""
            pages[page_no].elements.append(
                PageElement(
                    type=_get_element_type(item),
                    bbox=bbox,
                    content=content,
                    level=level,
                    self_ref=getattr(item, "self_ref", "") or "",
                )
            )
    return json.dumps(
        [asdict(page) for page in sorted(pages.values(), key=lambda p: p.page_number)]
    )


@dataclass
class _EditSession:
    document_id: str
    base_analysis: AnalysisJob
    manager: DoclingTransactionManager
    created_at: datetime = field(default_factory=_utcnow)


class DoclingEditService:
    """Experimental in-memory Docling document editing workflow."""

    def __init__(self, document_repo, analysis_repo):
        self._documents = document_repo
        self._analyses = analysis_repo
        self._sessions: dict[str, _EditSession] = {}

    async def get_or_create_session(self, document_id: str) -> dict:
        session = await self._ensure_session(document_id)
        return self._serialize_session(session)

    async def edit_text(self, document_id: str, item_ref: str, text: str) -> dict:
        session = await self._ensure_session(document_id)
        session.manager.commit_document(edit_text_item(session.manager.doc, item_ref, text))
        return self._serialize_session(session)

    async def reparent_item(self, document_id: str, child_ref: str, target_parent_ref: str) -> dict:
        session = await self._ensure_session(document_id)
        session.manager.commit_document(
            reparent_item(session.manager.doc, child_ref, target_parent_ref)
        )
        return self._serialize_session(session)

    async def merge_texts(
        self,
        document_id: str,
        leading_ref: str,
        trailing_ref: str,
        spacer: str = " ",
    ) -> dict:
        session = await self._ensure_session(document_id)
        session.manager.commit_document(
            merge_adjacent_texts(session.manager.doc, leading_ref, trailing_ref, spacer)
        )
        return self._serialize_session(session)

    async def undo(self, document_id: str) -> dict:
        session = await self._require_session(document_id)
        if not session.manager.undo():
            raise EditValidationError("Nothing to undo")
        return self._serialize_session(session)

    async def redo(self, document_id: str) -> dict:
        session = await self._require_session(document_id)
        if not session.manager.redo():
            raise EditValidationError("Nothing to redo")
        return self._serialize_session(session)

    async def commit(self, document_id: str) -> AnalysisJob:
        session = await self._require_session(document_id)
        doc = session.manager.doc
        committed = AnalysisJob(
            document_id=document_id,
            status=AnalysisStatus.COMPLETED,
            content_markdown=doc.export_to_markdown(),
            content_html=doc.export_to_html(),
            pages_json=_build_pages_json(doc),
            document_json=json.dumps(doc.export_to_dict()),
            chunks_json=None,
            started_at=_utcnow(),
            completed_at=_utcnow(),
        )
        await self._analyses.insert(committed)
        await self._analyses.update_status(committed)
        self._sessions.pop(document_id, None)
        return committed

    async def discard(self, document_id: str) -> None:
        if document_id not in self._sessions:
            raise EditSessionNotFoundError(f"Edit session not found: {document_id}")
        self._sessions.pop(document_id, None)

    async def _ensure_session(self, document_id: str) -> _EditSession:
        existing = self._sessions.get(document_id)
        if existing is not None:
            return existing
        return await self._create_session(document_id)

    async def _require_session(self, document_id: str) -> _EditSession:
        session = self._sessions.get(document_id)
        if session is None:
            raise EditSessionNotFoundError(f"Edit session not found: {document_id}")
        return session

    async def _create_session(self, document_id: str) -> _EditSession:
        doc = await self._documents.find_by_id(document_id)
        if doc is None:
            raise EditSourceNotFoundError(f"Document not found: {document_id}", http_status=404)
        job = await self._analyses.find_latest_completed_by_document(document_id)
        if job is None or not job.document_json:
            raise EditSourceNotFoundError(
                f"No completed analysis with document_json found for document: {document_id}",
                http_status=404,
            )
        try:
            parsed = DoclingDocument.model_validate(json.loads(job.document_json))
        except Exception as exc:
            raise EditValidationError(
                f"Invalid stored document_json for analysis {job.id}"
            ) from exc
        session = _EditSession(
            document_id=document_id,
            base_analysis=job,
            manager=DoclingTransactionManager(parsed),
        )
        self._sessions[document_id] = session
        return session

    def _serialize_session(self, session: _EditSession) -> dict:
        document_dict = session.manager.doc.export_to_dict()
        return {
            "documentId": session.document_id,
            "baseAnalysisId": session.base_analysis.id,
            "hasChanges": session.manager.has_changes,
            "canUndo": bool(session.manager.undo_stack),
            "canRedo": bool(session.manager.redo_stack),
            "documentJson": json.dumps(document_dict),
            "tree": _build_tree_nodes(document_dict),
        }

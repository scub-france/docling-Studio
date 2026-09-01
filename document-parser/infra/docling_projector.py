"""Canonical projection of an edited DoclingDocument."""

from __future__ import annotations

import json
from typing import Any

from docling_core.types.doc import DocItem, DoclingDocument, SectionHeaderItem, TableItem, TextItem

from domain.analysis_editing import (
    EditorElement,
    EditorProvenance,
    EditorTreeNode,
    ProjectedAnalysis,
)
from domain.value_objects import PageDetail, PageElement
from infra.bbox import to_topleft_list

_TEXT_LABELS = {"text", "paragraph", "title", "section_header", "caption", "list_item", "code", "formula"}


class DoclingAnalysisProjector:
    """Build all frontend projections from one validated Docling model."""

    def project(
        self,
        document: Any,
        *,
        base_analysis_id: str,
        logical_ids: dict[str, str],
        reference_changes: dict[str, str] | None = None,
        warnings: tuple[str, ...] = (),
    ) -> ProjectedAnalysis:
        items_with_levels = list(document.iterate_items(with_groups=True, traverse_pictures=True))
        by_ref = {
            item.self_ref: item
            for item, _ in items_with_levels
            if getattr(item, "self_ref", None)
        }
        ref_to_id = {ref: logical for logical, ref in logical_ids.items()}
        object_to_id = {
            id(item): ref_to_id[item.self_ref]
            for item, _ in items_with_levels
            if getattr(item, "self_ref", None) in ref_to_id
        }
        editor_elements = tuple(
            self._editor_element(item, level, object_to_id, document)
            for item, level in items_with_levels
            if getattr(item, "self_ref", None)
        )
        pages = self._pages(document, items_with_levels, object_to_id)
        tree = self._tree(document, by_ref, object_to_id)
        model = {
            "baseAnalysisId": base_analysis_id,
            "elements": [self._element_dict(element) for element in editor_elements],
        }
        return ProjectedAnalysis(
            document_json=document.model_dump_json(),
            content_markdown=document.export_to_markdown(),
            content_html=document.export_to_html(),
            pages_json=json.dumps([self._page_dict(page) for page in pages]),
            editor_model_json=json.dumps(model),
            tree=tree,
            elements=editor_elements,
            reference_changes=reference_changes or {},
            warnings=warnings,
        )

    def project_serialized(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        editor_model_json: str,
    ) -> ProjectedAnalysis:
        """Project a validated working copy without replaying its commands."""
        document = DoclingDocument.model_validate_json(document_json)
        model = json.loads(editor_model_json)
        logical_ids = {
            element["id"]: element["selfRef"] for element in model.get("elements", [])
        }
        return self.project(
            document,
            base_analysis_id=base_analysis_id,
            logical_ids=logical_ids,
        )

    @staticmethod
    def _label(item: Any) -> str:
        value = getattr(item, "label", "text")
        return str(getattr(value, "value", value)).lower()

    def _editor_element(
        self,
        item: Any,
        level: int,
        object_to_id: dict[int, str],
        document: Any,
    ) -> EditorElement:
        label = self._label(item)
        parent = item.parent.resolve(doc=document) if getattr(item, "parent", None) else None
        parent_id = object_to_id.get(id(parent)) if parent is not None else None
        children = tuple(
            object_to_id[id(ref.resolve(document))]
            for ref in getattr(item, "children", [])
            if id(ref.resolve(doc=document)) in object_to_id
        )
        text = getattr(item, "text", None)
        if isinstance(item, TableItem):
            text = item.export_to_markdown()
        provenance = tuple(
            EditorProvenance(
                page=int(prov.page_no),
                bbox=tuple(
                    to_topleft_list(
                        prov.bbox,
                        float(
                            document.pages[int(prov.page_no)].size.height
                            if int(prov.page_no) in document.pages
                            else 792.0
                        ),
                    )
                ),
            )
            for prov in getattr(item, "prov", [])
        )
        editable = isinstance(item, TextItem)
        operations: tuple[str, ...] = ("replaceText", "deleteElement") if editable else ()
        if isinstance(item, SectionHeaderItem):
            operations = ("replaceText", "setHeadingLevel", "deleteElement")
        if label in {"text", "paragraph"} and editable:
            operations = ("replaceText", "mergeText", "moveElement", "deleteElement")
        reason = None if editable else "This Docling element is structural or not editable."
        return EditorElement(
            id=object_to_id[id(item)],
            self_ref=item.self_ref,
            parent_id=parent_id,
            type=label,
            text=text,
            heading_level=getattr(item, "level", None),
            children=children,
            provenance=provenance,
            editable=editable,
            supported_operations=operations,  # type: ignore[arg-type]
            non_editable_reason=reason,
        )

    def _pages(
        self,
        document: Any,
        items_with_levels: list[tuple[Any, int]],
        object_to_id: dict[int, str],
    ) -> list[PageDetail]:
        pages: dict[int, PageDetail] = {}
        for page_no, page in document.pages.items():
            pages[int(page_no)] = PageDetail(
                page_number=int(page_no), width=float(page.size.width), height=float(page.size.height)
            )
        for item, level in items_with_levels:
            if not isinstance(item, DocItem):
                continue
            label = self._label(item)
            content = getattr(item, "text", "") or ""
            if isinstance(item, TableItem):
                content = item.export_to_markdown()
            for prov in item.prov:
                page_no = int(prov.page_no)
                page = pages.setdefault(page_no, PageDetail(page_no, 612.0, 792.0))
                bbox = to_topleft_list(prov.bbox, page.height)
                page.elements.append(
                    PageElement(
                        type=label,
                        bbox=bbox,
                        content=content,
                        level=int(getattr(item, "level", level) or level),
                        self_ref=item.self_ref,
                    )
                )
        return sorted(pages.values(), key=lambda page: page.page_number)

    def _tree(
        self,
        document: Any,
        by_ref: dict[str, Any],
        object_to_id: dict[int, str],
    ) -> tuple[EditorTreeNode, ...]:
        def node(item: Any) -> EditorTreeNode:
            label = self._label(item)
            text = getattr(item, "text", None) or getattr(item, "name", None) or label
            children = tuple(
                node(child)
                for child_ref in getattr(item, "children", [])
                if (child := child_ref.resolve(doc=document)) is not None
            )
            return EditorTreeNode(object_to_id[id(item)], label, str(text), children)

        # Docling keeps ordinary body items in reading order and stores
        # heading levels as metadata.  Build the semantic outline here so
        # the editor tree reflects the same hierarchy users see in Markdown.
        roots: list[dict[str, Any]] = []
        heading_stack: list[tuple[int, dict[str, Any]]] = []
        for child_ref in document.body.children:
            child = by_ref.get(child_ref.cref)
            if child is None or id(child) not in object_to_id:
                continue
            built = node(child)
            is_heading = isinstance(child, SectionHeaderItem) or self._label(child) == "title"
            if is_heading:
                level = int(getattr(child, "level", 0) or 0)
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                target = heading_stack[-1][1]["children"] if heading_stack else roots
                entry = {"node": built, "children": []}
                target.append(entry)
                heading_stack.append((level, entry))
            else:
                target = heading_stack[-1][1]["children"] if heading_stack else roots
                target.append({"node": built, "children": []})

        def freeze(entries: list[dict[str, Any]]) -> tuple[EditorTreeNode, ...]:
            return tuple(
                EditorTreeNode(
                    element_id=entry["node"].element_id,
                    type=entry["node"].type,
                    label=entry["node"].label,
                    children=freeze(entry["children"]) or entry["node"].children,
                )
                for entry in entries
            )

        return freeze(roots)

    @staticmethod
    def _element_dict(element: EditorElement) -> dict[str, Any]:
        return {
            "id": element.id,
            "selfRef": element.self_ref,
            "parentId": element.parent_id,
            "type": element.type,
            "text": element.text,
            "headingLevel": element.heading_level,
            "children": list(element.children),
            "provenance": [
                {"page": p.page, "bbox": list(p.bbox)} for p in element.provenance
            ],
            "editable": element.editable,
            "supportedOperations": list(element.supported_operations),
            "nonEditableReason": element.non_editable_reason,
        }

    @staticmethod
    def _page_dict(page: PageDetail) -> dict[str, Any]:
        return {
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height,
            "elements": [
                {
                    "type": element.type,
                    "bbox": element.bbox,
                    "content": element.content,
                    "level": element.level,
                    "self_ref": element.self_ref,
                }
                for element in page.elements
            ],
        }

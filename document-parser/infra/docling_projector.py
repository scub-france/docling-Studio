"""Canonical projection of an edited DoclingDocument."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from docling_core.types.doc import DoclingDocument, SectionHeaderItem, TableItem, TextItem

from domain.analysis_editing import (
    MERGEABLE_TEXT_LABELS,
    EditorElement,
    EditorProvenance,
    EditorTreeNode,
    ProjectedAnalysis,
)
from domain.heading_tree import nest_by_heading
from domain.value_objects import DEFAULT_PAGE_HEIGHT
from infra.bbox import to_topleft_list
from infra.docling_pages import extract_pages_detail


class DoclingAnalysisProjector:
    """Build all frontend projections from one validated Docling model."""

    def project(
        self,
        document: Any,
        *,
        base_analysis_id: str,
        logical_ids: dict[str, str],
    ) -> ProjectedAnalysis:
        items_with_levels = list(document.iterate_items(with_groups=True, traverse_pictures=True))
        by_ref = {
            item.self_ref: item for item, _ in items_with_levels if getattr(item, "self_ref", None)
        }
        ref_to_id = {ref: logical for logical, ref in logical_ids.items()}
        object_to_id = {
            id(item): ref_to_id[item.self_ref]
            for item, _ in items_with_levels
            if getattr(item, "self_ref", None) in ref_to_id
        }
        editor_elements = tuple(
            self._build_editor_element(item, level, object_to_id, document)
            for item, level in items_with_levels
            if getattr(item, "self_ref", None)
        )
        # Same page mapping as a fresh conversion (#396): the workspace shows
        # this projection by default, so element types must match the parser's.
        pages, _ = extract_pages_detail(document)
        tree = self._build_tree(document, by_ref, object_to_id)
        model = {
            "baseAnalysisId": base_analysis_id,
            "elements": [self._to_element_dict(element) for element in editor_elements],
        }
        export_document = document.model_copy(deep=True)
        for item in export_document.texts:
            if isinstance(item, TextItem) and item.orig != item.text:
                # Docling's exporters prefer `orig` as OCR evidence. Keep that
                # immutable in document_json, but render the user's edited text
                # in Markdown and HTML projections.
                item.orig = item.text
        return ProjectedAnalysis(
            document_json=document.model_dump_json(),
            content_markdown=export_document.export_to_markdown(),
            content_html=export_document.export_to_html(),
            pages_json=json.dumps([asdict(page) for page in pages]),
            editor_model_json=json.dumps(model),
            tree=tree,
            elements=editor_elements,
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
        logical_ids = {element["id"]: element["selfRef"] for element in model.get("elements", [])}
        return self.project(
            document,
            base_analysis_id=base_analysis_id,
            logical_ids=logical_ids,
        )

    @staticmethod
    def _get_label(item: Any) -> str:
        value = getattr(item, "label", "text")
        return str(getattr(value, "value", value)).lower()

    @classmethod
    def _read_heading_level(cls, item: Any) -> int | None:
        """Section headers by class and the title by label; a title has no
        `level`, so it is 0 and contains the sections after it."""
        if not isinstance(item, SectionHeaderItem) and cls._get_label(item) != "title":
            return None
        return int(getattr(item, "level", 0) or 0)

    def _build_editor_element(
        self,
        item: Any,
        level: int,
        object_to_id: dict[int, str],
        document: Any,
    ) -> EditorElement:
        label = self._get_label(item)
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
                            else DEFAULT_PAGE_HEIGHT
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
        if label in MERGEABLE_TEXT_LABELS and editable:
            operations = (
                "replaceText",
                "mergeText",
                "moveElement",
                "deleteElement",
                "deleteElements",
            )
        reason = (
            None
            if editable
            else f"{label.replace('_', ' ').capitalize()} elements are not editable yet."
        )
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

    def _build_tree(
        self,
        document: Any,
        by_ref: dict[str, Any],
        object_to_id: dict[int, str],
    ) -> tuple[EditorTreeNode, ...]:
        def build_node(item: Any) -> EditorTreeNode:
            label = self._get_label(item)
            text = getattr(item, "text", None) or getattr(item, "name", None) or label
            children = tuple(
                build_node(child)
                for child_ref in getattr(item, "children", [])
                if (child := child_ref.resolve(doc=document)) is not None
            )
            return EditorTreeNode(object_to_id[id(item)], label, str(text), children)

        # Docling keeps ordinary body items in reading order and stores
        # heading levels as metadata.  Build the semantic outline here so
        # the editor tree reflects the same hierarchy users see in Markdown.
        top_level = [
            child
            for child_ref in document.body.children
            if (child := by_ref.get(child_ref.cref)) is not None and id(child) in object_to_id
        ]
        roots: list[dict[str, Any]] = []
        placed: list[dict[str, Any]] = []
        for step in nest_by_heading(top_level, level_of=self._read_heading_level).steps:
            entry = {"node": build_node(top_level[step.position]), "children": []}
            siblings = roots if step.parent is None else placed[step.parent]["children"]
            siblings.append(entry)
            placed.append(entry)

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
    def _to_element_dict(element: EditorElement) -> dict[str, Any]:
        return {
            "id": element.id,
            "selfRef": element.self_ref,
            "parentId": element.parent_id,
            "type": element.type,
            "text": element.text,
            "headingLevel": element.heading_level,
            "children": list(element.children),
            "provenance": [{"page": p.page, "bbox": list(p.bbox)} for p in element.provenance],
            "editable": element.editable,
            "supportedOperations": list(element.supported_operations),
            "nonEditableReason": element.non_editable_reason,
        }

"""Docling mutation adapter for the analysis editor.

The adapter deliberately owns all Docling-specific behavior.  The service
layer deals only in versioned commands and projected results.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    SectionHeaderItem,
    TextItem,
    TitleItem,
)

from domain.analysis_editing import AnalysisEditError, EditCommand


@dataclass(frozen=True)
class MutationResult:
    document: DoclingDocument
    logical_ids: dict[str, str]
    reference_changes: dict[str, str]
    warnings: tuple[str, ...] = ()


class DoclingDocumentEditor:
    """Apply editor commands to a validated Docling document."""

    def apply(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        commands: Iterable[EditCommand],
    ) -> MutationResult:
        try:
            document = DoclingDocument.model_validate_json(document_json)
        except Exception as exc:  # pydantic errors are implementation detail
            raise AnalysisEditError(f"Invalid canonical Docling document: {exc}") from exc

        logical_objects = self._logical_refs(document, base_analysis_id)
        before_refs = {logical: obj.self_ref for logical, obj in logical_objects.items()}
        for command in commands:
            self._apply_one(document, logical_objects, command)

        try:
            document.validate_tree(document.body, raise_on_error=True)
            document.validate_document()
            # Round-trip validation catches stale references which an in-memory
            # model can otherwise hide.
            reloaded = DoclingDocument.model_validate_json(document.model_dump_json())
            reloaded.validate_tree(reloaded.body, raise_on_error=True)
        except Exception as exc:
            raise AnalysisEditError(f"Edited Docling document failed validation: {exc}") from exc

        current_refs = {
            logical: obj.self_ref
            for logical, obj in logical_objects.items()
            if self._is_live(document, obj)
        }
        changes = {
            old_ref: new_ref
            for logical, old_ref in before_refs.items()
            if (new_ref := current_refs.get(logical)) is not None and old_ref != new_ref
        }
        return MutationResult(document, current_refs, changes)

    @staticmethod
    def _all_items(document: DoclingDocument) -> list[Any]:
        return [
            item for item, _ in document.iterate_items(with_groups=True, traverse_pictures=True)
        ]

    def _logical_refs(self, document: DoclingDocument, base_id: str) -> dict[str, Any]:
        return {
            f"{base_id}:{item.self_ref}": item
            for item in self._all_items(document)
            if getattr(item, "self_ref", None)
        }

    @staticmethod
    def _get(logical_objects: dict[str, Any], element_id: str) -> Any:
        item = logical_objects.get(element_id)
        if item is None:
            raise AnalysisEditError(f"Unknown editor element: {element_id}")
        return item

    def _apply_one(
        self,
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        command: EditCommand,
    ) -> None:
        if command.command_version != 1:
            raise AnalysisEditError(f"Unsupported command version: {command.command_version}")
        payload = command.payload
        if command.command_type == "replaceText":
            item = self._get(logical_objects, str(payload.get("elementId", "")))
            self._replace_text(item, payload.get("text"))
        elif command.command_type == "setHeadingLevel":
            item = self._get(logical_objects, str(payload.get("elementId", "")))
            self._set_heading_level(document, logical_objects, item, payload.get("level"))
        elif command.command_type == "mergeText":
            self._merge_text(document, logical_objects, payload)
        elif command.command_type == "moveElement":
            self._move_element(document, logical_objects, payload)
        elif command.command_type == "deleteElement":
            item = self._get(logical_objects, str(payload.get("elementId", "")))
            if item is document.body:
                raise AnalysisEditError("The document root cannot be deleted")
            document.delete_items(node_items=[item])
        elif command.command_type == "deleteElements":
            self._delete_elements(document, logical_objects, payload)
        else:
            raise AnalysisEditError(f"Unsupported edit command: {command.command_type}")

    @staticmethod
    def _replace_text(item: Any, value: Any) -> None:
        if not isinstance(item, TextItem) or not isinstance(value, str):
            raise AnalysisEditError("replaceText requires a text item and string text")
        item.text = value

    def _delete_elements(
        self,
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        raw_ids = payload.get("elementIds")
        if not isinstance(raw_ids, list) or not raw_ids:
            raise AnalysisEditError("deleteElements requires at least one element")
        items: list[Any] = []
        for item_id in raw_ids:
            item = self._get(logical_objects, str(item_id))
            if not any(existing is item for existing in items):
                items.append(item)
        if any(item is document.body or item.parent is None for item in items):
            raise AnalysisEditError("The document root cannot be deleted")
        roots = [
            item
            for item in items
            if not any(
                other is not item and self._is_descendant(item, other, document) for other in items
            )
        ]
        document.delete_items(node_items=roots)

    @staticmethod
    def _set_heading_level(
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        item: Any,
        value: Any,
    ) -> None:
        if not isinstance(item, SectionHeaderItem) or not isinstance(value, int):
            raise AnalysisEditError("setHeadingLevel requires a section header and integer level")
        if value < -1 or value > 6:
            raise AnalysisEditError("Heading level must be -1, 0, or between 1 and 6")
        if value in {-1, 0}:
            if value == 0 and any(isinstance(candidate, TitleItem) for candidate in document.texts):
                raise AnalysisEditError("A document can contain only one title")
            replacement_type = TitleItem if value == 0 else TextItem
            replacement = replacement_type(
                self_ref=item.self_ref,
                parent=item.parent,
                children=list(item.children),
                content_layer=item.content_layer,
                meta=item.meta,
                label=DocItemLabel.TITLE if value == 0 else DocItemLabel.TEXT,
                prov=list(item.prov),
                source=list(item.source),
                comments=list(item.comments),
                orig=item.orig,
                text=item.text,
                formatting=item.formatting,
                hyperlink=item.hyperlink,
            )
            document.replace_item(new_item=replacement, old_item=item)
            for key, candidate in list(logical_objects.items()):
                if candidate is item:
                    logical_objects[key] = replacement
            return
        item.level = value

    def _merge_text(
        self,
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        raw_ids = payload.get("elementIds")
        separator = payload.get("separator", " ")
        if not isinstance(raw_ids, list) or len(raw_ids) < 2 or not isinstance(separator, str):
            raise AnalysisEditError("mergeText requires at least two element IDs and a separator")
        items = [self._get(logical_objects, str(item_id)) for item_id in raw_ids]
        if any(not isinstance(item, TextItem) for item in items):
            raise AnalysisEditError("Only text items can be merged")
        labels = {str(item.label) for item in items}
        if len(labels) != 1 or next(iter(labels)).lower() not in {"text", "paragraph"}:
            raise AnalysisEditError("Only compatible paragraph text items can be merged")
        target = items[0]
        if target.parent is None:
            raise AnalysisEditError("The document root cannot be merged")
        parent = target.parent.resolve(doc=document)
        insertion_index = list(parent.children).index(target.get_ref()) + 1
        for item in items[1:]:
            if item.parent is None:
                raise AnalysisEditError("The document root cannot be merged")
            item_parent = item.parent.resolve(doc=document)
            if item_parent is parent:
                old_index = list(parent.children).index(item.get_ref())
                if old_index < insertion_index:
                    insertion_index -= 1
            # A merge command makes its selected text a contiguous run under
            # the first item's parent before applying the text-level merge.
            self._move_subtree(document, item, parent, insertion_index)
            insertion_index += 1
        target_text = target.text
        target_orig = target.orig or target.text
        for item in items[1:]:
            continuation = item.text.lstrip()
            original_continuation = (item.orig or item.text).lstrip()
            is_word_continuation = target_text.endswith("\u00ad") or (
                target_text.endswith("-") and continuation and continuation[0].islower()
            )
            joiner = "" if is_word_continuation else separator
            if is_word_continuation:
                target_text = target_text[:-1]
                if target_orig.endswith(("\u00ad", "-")):
                    target_orig = target_orig[:-1]
            target_text += joiner + continuation
            target_orig += joiner + original_continuation
        target.text = target_text
        target.orig = target_orig
        target.prov = [prov for item in items for prov in item.prov]
        if any(item.hyperlink != target.hyperlink for item in items[1:]):
            target.hyperlink = None
        document.delete_items(node_items=items[1:])

    def _move_element(
        self,
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        item = self._get(logical_objects, str(payload.get("elementId", "")))
        target_id = payload.get("targetElementId")
        placement = payload.get("placement")
        if target_id is not None or placement is not None:
            if not isinstance(target_id, str) or placement not in {"before", "after", "inside"}:
                raise AnalysisEditError("moveElement requires a target and placement")
            target = self._get(logical_objects, target_id)
            if target is item or self._is_descendant(target, item, document):
                raise AnalysisEditError("Move would create a cycle")
            if placement == "inside":
                if not isinstance(target, SectionHeaderItem):
                    raise AnalysisEditError("Elements can only be moved inside a section heading")
                parent = target
                target_index = len(parent.children)
            else:
                if target.parent is None:
                    raise AnalysisEditError("The document root cannot be used as a move target")
                parent = target.parent.resolve(doc=document)
                target_index = list(parent.children).index(target.get_ref())
                if placement == "after":
                    target_index += 1
            source_parent = item.parent.resolve(doc=document) if item.parent is not None else None
            if parent is source_parent and target_index > list(parent.children).index(
                item.get_ref()
            ):
                target_index -= 1
            self._move_subtree(document, item, parent, target_index)
            return
        before_id = payload.get("beforeElementId")
        before = self._get(logical_objects, str(before_id)) if before_id else None
        if item.parent is None:
            raise AnalysisEditError("The document root cannot be moved")
        source_parent = item.parent.resolve(doc=document)
        parent = source_parent
        if before is not None:
            if before.parent is None:
                raise AnalysisEditError("The document root cannot be used as a move target")
            if before is item or self._is_descendant(before, item, document):
                raise AnalysisEditError("Move would create a cycle")
            parent = before.parent.resolve(doc=document)
        target_refs = list(parent.children)
        target_index = len(target_refs) if before is None else target_refs.index(before.get_ref())
        if parent is source_parent and target_index > target_refs.index(item.get_ref()):
            target_index -= 1
        # Docling has no public move API; this private helper updates both
        # parent references and child order atomically.
        self._move_subtree(document, item, parent, target_index)

    @staticmethod
    def _move_subtree(document: DoclingDocument, item: Any, parent: Any, position: int) -> None:
        """Use Docling's private move primitive only after verifying its contract."""
        move = getattr(document, "_move_subtree", None)
        if not callable(move):
            raise AnalysisEditError(
                "Installed Docling does not support subtree moves required by the analysis editor"
            )
        try:
            inspect.signature(move).bind(old_subroot=item, new_subroot=parent, pos=position)
        except TypeError as exc:
            raise AnalysisEditError(
                "Installed Docling has an incompatible subtree move API; upgrade compatibility is required"
            ) from exc
        move(old_subroot=item, new_subroot=parent, pos=position)

    @staticmethod
    def _is_descendant(candidate: Any, ancestor: Any, document: DoclingDocument) -> bool:
        current = candidate
        while current.parent is not None:
            current = current.parent.resolve(doc=document)
            if current is ancestor:
                return True
        return False

    @staticmethod
    def _is_live(document: DoclingDocument, item: Any) -> bool:
        return any(
            candidate is item
            for candidate, _ in document.iterate_items(with_groups=True, traverse_pictures=True)
        )

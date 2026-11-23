"""Docling mutation adapter for the analysis editor.

The adapter deliberately owns all Docling-specific behavior.  The service
layer deals only in versioned commands and projected results.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    SectionHeaderItem,
    TextItem,
    TitleItem,
)

from domain.analysis_editing import (
    AnalysisEditError,
    EditCommand,
    check_command_version,
    check_delete_request,
    check_heading_level,
    check_merge_request,
    check_mergeable_labels,
    check_move_target,
)


@dataclass(frozen=True)
class MutationResult:
    document: DoclingDocument
    logical_ids: dict[str, str]


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

        logical_objects = self._map_logical_refs(document, base_analysis_id)
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

        live_object_ids = {id(item) for item in self._list_all_items(document)}
        current_refs = {
            logical: obj.self_ref
            for logical, obj in logical_objects.items()
            if id(obj) in live_object_ids
        }
        return MutationResult(document, current_refs)

    @staticmethod
    def _list_all_items(document: DoclingDocument) -> list[Any]:
        return [
            item for item, _ in document.iterate_items(with_groups=True, traverse_pictures=True)
        ]

    def _map_logical_refs(self, document: DoclingDocument, base_id: str) -> dict[str, Any]:
        return {
            f"{base_id}:{item.self_ref}": item
            for item in self._list_all_items(document)
            if getattr(item, "self_ref", None)
        }

    @classmethod
    def _sort_in_document_order(cls, document: DoclingDocument, items: list[Any]) -> list[Any]:
        """Sort `items` by their current reading order in `document` (#392).

        A merge keeps the text in reading order, whatever order the client
        sent the ids in: the first item in the document is the target and the
        others follow it. Duplicate ids are kept, so validation still sees them.
        """
        position = {id(item): index for index, item in enumerate(cls._list_all_items(document))}
        return sorted(items, key=lambda item: position.get(id(item), len(position)))

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
        check_command_version(command.command_version)
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
        check_delete_request(raw_ids)
        # Identity sets keep a delete of every element of a long document linear.
        items: list[Any] = []
        selected: set[int] = set()
        for item_id in raw_ids:
            item = self._get(logical_objects, str(item_id))
            if id(item) not in selected:
                selected.add(id(item))
                items.append(item)
        if any(item is document.body or item.parent is None for item in items):
            raise AnalysisEditError("The document root cannot be deleted")
        # A selected item under a selected ancestor goes with that ancestor.
        roots = [
            item
            for item in items
            if not any(id(ancestor) in selected for ancestor in _iter_ancestors(item, document))
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
        # The title scan only matters, and only runs, for level 0.
        title_exists = value == 0 and any(isinstance(text, TitleItem) for text in document.texts)
        check_heading_level(value, title_exists=title_exists)
        if value in {-1, 0}:
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
        check_merge_request(raw_ids, separator)
        items = self._sort_in_document_order(
            document, [self._get(logical_objects, str(item_id)) for item_id in raw_ids]
        )
        if any(not isinstance(item, TextItem) for item in items):
            raise AnalysisEditError("Only text items can be merged")
        check_mergeable_labels({str(item.label) for item in items})
        self._gather_merge_run(document, items)
        target = items[0]
        target.text, target.orig = _join_merged_text(items, separator)
        target.prov = [prov for item in items for prov in item.prov]
        if any(item.hyperlink != target.hyperlink for item in items[1:]):
            target.hyperlink = None
        document.delete_items(node_items=items[1:])

    def _gather_merge_run(self, document: DoclingDocument, items: list[Any]) -> None:
        """Move `items[1:]` right after `items[0]`, under its parent, in order.

        A merge command makes its selected text a contiguous run under the
        first item's parent before applying the text-level merge.
        """
        target = items[0]
        if target.parent is None:
            raise AnalysisEditError("The document root cannot be merged")
        parent = target.parent.resolve(doc=document)
        # Positions are read once: the moves only touch the run, which grows
        # right after the target, and the siblings after it. An item of the
        # parent sits before the run's end when it is already in the run (a
        # repeated id) or was before the target, and then its removal shifts
        # the insertion point.
        position = {ref.cref: index for index, ref in enumerate(parent.children)}
        target_index = position[target.self_ref]
        insertion_index = target_index + 1
        in_run = {id(target)}
        for item in items[1:]:
            if item.parent is None:
                raise AnalysisEditError("The document root cannot be merged")
            item_parent = item.parent.resolve(doc=document)
            if item_parent is parent and (
                id(item) in in_run or position[item.self_ref] < target_index
            ):
                insertion_index -= 1
            self._move_subtree(document, item, parent, insertion_index)
            insertion_index += 1
            in_run.add(id(item))

    def _move_element(
        self,
        document: DoclingDocument,
        logical_objects: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Move an element before, after or inside (a section heading) its target."""
        item = self._get(logical_objects, str(payload.get("elementId", "")))
        target_id = payload.get("targetElementId")
        placement = payload.get("placement")
        check_move_target(target_id, placement)
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
        if parent is source_parent and target_index > list(parent.children).index(item.get_ref()):
            target_index -= 1
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
        return any(node is ancestor for node in _iter_ancestors(candidate, document))


def _iter_ancestors(item: Any, document: DoclingDocument) -> Iterator[Any]:
    """`item`'s parent, its parent's parent, and so on up to the body."""
    while item.parent is not None:
        item = item.parent.resolve(doc=document)
        yield item


def _join_merged_text(items: list[Any], separator: str) -> tuple[str, str]:
    """The merged `text` and `orig` of `items`, the first one's followed by the others'.

    A word broken across items (soft hyphen, or a hyphen before a lowercase
    continuation) is joined without the hyphen and without the separator.
    """
    target = items[0]
    target_text = target.text
    target_orig = target.orig or target.text
    for item in items[1:]:
        continuation = item.text.lstrip()
        original_continuation = (item.orig or item.text).lstrip()
        is_word_continuation = target_text.endswith("­") or (
            target_text.endswith("-") and continuation and continuation[0].islower()
        )
        joiner = "" if is_word_continuation else separator
        if is_word_continuation:
            target_text = target_text[:-1]
            if target_orig.endswith(("­", "-")):
                target_orig = target_orig[:-1]
        target_text += joiner + continuation
        target_orig += joiner + original_continuation
    return target_text, target_orig

"""Tree projection — extract a hierarchical outline from a DoclingDocument.

Pure projection over a serialized document: every docling-shaped access goes
through the injected `DocumentTreeReader` port. Kept module-level so it stays
cheap to test in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.heading_tree import nest_by_heading
from domain.navigation import is_heading
from domain.parse_index import index_items_by_ref

if TYPE_CHECKING:
    from domain.ports import DocumentTreeReader

_CONTAINER_TYPES = {"list", "group", "form_area", "key_value_area"}


@dataclass(frozen=True)
class _TreeContext:
    """What every node of one projection reads: the items by ref, the refs the
    collapse index skips, the inline-group metadata, and the reader port."""

    by_ref: dict[str, dict]
    skip_refs: set[str]
    inline_meta: dict[str, dict]
    tree_reader: DocumentTreeReader


def build_tree_nodes(doc_data: dict, tree_reader: DocumentTreeReader) -> list[dict]:
    """Project a Docling document JSON into a hierarchical `[DocTreeNode]` outline.

    Two stacking rules combine to follow the document's natural structure:

    1. **Headings nest by level.** `title` opens a level-0 container; each
       `section_header` opens a container at its declared `level` (default 1).
       A new heading pops the stack until the top has a strictly lower level,
       so siblings stay siblings and sub-sections nest inside their parent.
    2. **Docling parent/child is preserved for containers.** `list` keeps its
       `list_item` descendants under it; everything else (paragraph, table,
       picture) is a leaf under the current section.

    Inline-group style runs and picture sub-elements are skipped via the
    shared `build_collapse_index` helper — keeps the projection in sync
    with the Neo4j tree writer and the in-memory graph payload.
    """
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)
    context = _TreeContext(
        by_ref=index_items_by_ref(doc_data, tree_reader),
        skip_refs=skip_refs,
        inline_meta=inline_meta,
        tree_reader=tree_reader,
    )
    entries = _list_body_entries(doc_data, context)

    root: list[dict] = []
    nodes: dict[int, dict] = {}
    nesting = nest_by_heading([item for _, item in entries], level_of=_read_tree_heading_level)
    for step in nesting.steps:
        ref, item = entries[step.position]
        if step.level is not None:
            node = _make_node(ref, _get_label_type(item), item, context)
        else:
            node = _build_item_subtree(ref, item, context)
        siblings = root if step.parent is None else nodes[step.parent]["children"]
        siblings.append(node)
        nodes[step.position] = node
    return root


def _list_body_entries(doc_data: dict, context: _TreeContext) -> list[tuple[str, dict]]:
    """The body's direct children, in order, minus the skipped and unknown refs."""
    body = doc_data.get("body") or {}
    entries: list[tuple[str, dict]] = []
    for ch in body.get("children") or []:
        ref = ch.get("$ref") or ch.get("cref")
        if not ref or ref in context.skip_refs:
            continue
        item = context.by_ref.get(ref)
        if item is None:
            continue
        entries.append((ref, item))
    return entries


def _get_label_type(item: dict) -> str:
    return (item.get("label") or "").lower() or "text"


def _read_tree_heading_level(item: dict) -> int | None:
    """`title` is level 0, a `section_header` its declared level (at least 1).

    Unlike the parse index, a level that is not a number raises here: the
    tree has always failed on such a document rather than guess.
    """
    label_type = _get_label_type(item)
    if not is_heading(label_type):
        return None
    return 0 if label_type == "title" else max(int(item.get("level") or 1), 1)


def _build_item_subtree(ref: str, item: dict, context: _TreeContext) -> dict:
    """Build a leaf or nested subtree for a non-heading item.

    Containers (list, group, form_area, key_value_area) keep their explicit
    Docling children so the outline mirrors structures like `list` → `list_item`.
    Other items are emitted as leaves — pictures and inline groups had their
    descendants pruned upstream by `build_collapse_index`.
    """
    label_type = _get_label_type(item)
    node = _make_node(ref, label_type, item, context)
    if label_type in _CONTAINER_TYPES:
        for ch in item.get("children") or []:
            child_ref = ch.get("$ref") or ch.get("cref")
            if not child_ref or child_ref in context.skip_refs:
                continue
            child_item = context.by_ref.get(child_ref)
            if child_item is None:
                continue
            node["children"].append(_build_item_subtree(child_ref, child_item, context))
    return node


def _make_node(ref: str, label_type: str, item: dict, context: _TreeContext) -> dict:
    return {
        "ref": ref,
        "type": label_type,
        "label": _pick_display_label(item, context),
        "children": [],
    }


def _pick_display_label(item: dict, context: _TreeContext) -> str:
    """Pick the most human-readable label for the tree node."""
    ref = item.get("self_ref") or ""
    label_type = (item.get("label") or "").lower()

    if context.tree_reader.is_inline_group(item):
        meta = context.inline_meta.get(ref)
        if meta and meta.get("text"):
            return _truncate(meta["text"])

    text = (item.get("text") or "").strip()
    if text:
        return _truncate(text)

    if label_type == "table":
        return "Table"
    if label_type == "picture":
        return "Figure"
    if label_type == "list":
        return "List"
    if label_type == "group":
        return (item.get("name") or "Group").strip()
    return label_type or "node"


def _truncate(text: str, max_len: int = 80) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

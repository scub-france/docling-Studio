"""The document tree of the Chunks view: a parse projected into nested nodes.

Pure projection over a serialized `DoclingDocument`: no I/O and no docling
import. Every docling-shaped access goes through the injected
`DocumentTreeReader` port, as in `domain/parse_index.py`.

Each node is a `DocTreeNode`-shaped dict — `{"ref", "type", "label",
"children"}` — which the API returns as is.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from domain.ports import DocumentTreeReader

# Labels whose Docling children stay nested under them in the tree.
_CONTAINER_LABELS = frozenset({"list", "group", "form_area", "key_value_area"})

_MAX_LABEL_LEN = 80


def build_doc_tree(doc_data: dict[str, Any], tree_reader: DocumentTreeReader) -> list[dict]:
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
    by_ref: dict[str, dict] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item

    body = doc_data.get("body") or {}
    root: list[dict] = []
    # Stack entries: (heading_level, children_list). The sentinel level -1
    # represents the document root so any heading nests inside it.
    stack: list[tuple[int, list[dict]]] = [(-1, root)]

    def walk(children: list[dict] | None) -> None:
        if not children:
            return
        for ch in children:
            ref = ch.get("$ref") or ch.get("cref")
            if not ref or ref in skip_refs:
                continue
            item = by_ref.get(ref)
            if item is None:
                continue
            label_type = (item.get("label") or "").lower() or "text"

            if label_type in {"title", "section_header"}:
                level = 0 if label_type == "title" else max(int(item.get("level") or 1), 1)
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                node = _make_node(ref, label_type, item, inline_meta, tree_reader)
                stack[-1][1].append(node)
                stack.append((level, node["children"]))
            else:
                node = _build_item_subtree(ref, item, by_ref, skip_refs, inline_meta, tree_reader)
                stack[-1][1].append(node)

    walk(body.get("children"))
    return root


def _build_item_subtree(
    ref: str,
    item: dict,
    by_ref: dict[str, dict],
    skip_refs: set[str],
    inline_meta: dict[str, dict],
    tree_reader: DocumentTreeReader,
) -> dict:
    """Build a leaf or nested subtree for a non-heading item.

    Containers (list, group, form_area, key_value_area) keep their explicit
    Docling children so the outline mirrors structures like `list` → `list_item`.
    Other items are emitted as leaves — pictures and inline groups had their
    descendants pruned upstream by `build_collapse_index`.
    """
    label_type = (item.get("label") or "").lower() or "text"
    node = _make_node(ref, label_type, item, inline_meta, tree_reader)
    if label_type in _CONTAINER_LABELS:
        for ch in item.get("children") or []:
            child_ref = ch.get("$ref") or ch.get("cref")
            if not child_ref or child_ref in skip_refs:
                continue
            child_item = by_ref.get(child_ref)
            if child_item is None:
                continue
            node["children"].append(
                _build_item_subtree(
                    child_ref, child_item, by_ref, skip_refs, inline_meta, tree_reader
                )
            )
    return node


def _make_node(
    ref: str,
    label_type: str,
    item: dict,
    inline_meta: dict[str, dict],
    tree_reader: DocumentTreeReader,
) -> dict:
    return {
        "ref": ref,
        "type": label_type,
        "label": _display_label(item, inline_meta, tree_reader),
        "children": [],
    }


def _display_label(
    item: dict, inline_meta: dict[str, dict], tree_reader: DocumentTreeReader
) -> str:
    """Pick the most human-readable label for the tree node."""
    ref = item.get("self_ref") or ""
    label_type = (item.get("label") or "").lower()

    if tree_reader.is_inline_group(item):
        meta = inline_meta.get(ref)
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


def _truncate(text: str, max_len: int = _MAX_LABEL_LEN) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

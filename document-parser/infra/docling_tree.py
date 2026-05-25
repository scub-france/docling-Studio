"""Pure helpers over a serialized `DoclingDocument` dict.

No I/O, no Neo4j. Shared between:
- `infra.neo4j.tree_writer` — persists the tree into Neo4j during the Maintain
  step (IngestionPipeline).
- `infra.docling_graph` — builds an in-memory `GraphPayload` from the SQLite
  `document_json` blob for the reasoning-trace viewer.

Keep this module the single source of truth for how we read Docling's own
structure, so the two consumers can't drift.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

# Docling label -> specific Neo4j/Cytoscape label. Every element carries the
# generic :Element tag too. Kept 1:1 with docling-core's label taxonomy so the
# projection is a faithful mirror of the DoclingDocument.
LABEL_MAP: dict[str, str] = {
    "section_header": "SectionHeader",
    "title": "SectionHeader",
    "paragraph": "Paragraph",
    "text": "Paragraph",
    "list_item": "ListItem",
    "list": "List",  # distinct from :ListItem — a list is a container
    "inline": "Paragraph",  # see issue #197 — collapsed into one paragraph node
    "table": "Table",
    "picture": "Figure",
    "formula": "Formula",
    "code": "Code",
    "caption": "Caption",
    "footnote": "Footnote",
    "page_header": "PageHeader",
    "page_footer": "PageFooter",
    "key_value_area": "KeyValueArea",
    "form_area": "FormArea",
    "document_index": "DocumentIndex",
}
DEFAULT_LABEL = "TextElement"


def element_label(docling_label: str) -> str:
    return LABEL_MAP.get(docling_label.lower(), DEFAULT_LABEL)


def is_inline_group(item: dict[str, Any]) -> bool:
    """True iff `item` is a Docling InlineGroup (paragraph of mixed style runs).

    Docling represents an inline-styled paragraph as one entry in `groups[]`
    (label `inline`) plus N entries in `texts[]` (label `text`), one per style
    run. We collapse them into a single Paragraph projection — see #197.
    """
    return (item.get("label") or "").lower() == "inline"


def is_picture(item: dict[str, Any]) -> bool:
    """True iff `item` is a Docling PictureItem (figure or chart).

    A `picture` keeps its node in the graph (it IS the figure), but its
    `children` — internal text labels extracted from a flowchart, diagram,
    chart axis labels — are noise for graph readability and are skipped.
    Captions live in a separate `captions` field on the picture, not in
    `children`, so they are unaffected by this skip.
    """
    return (item.get("label") or "").lower() in {"picture", "chart"}


def iter_items(doc_data: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield every item from texts/tables/pictures/groups with its source list key."""
    for key in ("texts", "tables", "pictures", "groups"):
        for item in doc_data.get(key, []) or []:
            yield key, item


def parent_ref(item: dict[str, Any]) -> str | None:
    parent = item.get("parent")
    if isinstance(parent, dict):
        return parent.get("$ref") or parent.get("cref")
    return None


def iter_provs(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a Docling item's `prov[]` into a list of dict rows.

    A single item may have multiple provs when it spans page breaks or appears
    more than once in the layout. The returned dicts carry the original index
    under `order` so sequence is preserved.
    """
    provs = item.get("prov") or []
    rows: list[dict[str, Any]] = []
    for idx, p in enumerate(provs):
        bbox = p.get("bbox")
        l_, t_, r_, b_ = 0.0, 0.0, 0.0, 0.0
        if isinstance(bbox, dict):
            l_ = float(bbox.get("l", 0.0) or 0.0)
            t_ = float(bbox.get("t", 0.0) or 0.0)
            r_ = float(bbox.get("r", 0.0) or 0.0)
            b_ = float(bbox.get("b", 0.0) or 0.0)
        elif isinstance(bbox, list | tuple) and len(bbox) >= 4:
            l_, t_, r_, b_ = (float(x) for x in bbox[:4])
        coord_origin = (bbox.get("coord_origin") if isinstance(bbox, dict) else None) or "TOPLEFT"
        charspan = p.get("charspan") or []
        rows.append(
            {
                "order": idx,
                "page_no": p.get("page_no"),
                "bbox_l": l_,
                "bbox_t": t_,
                "bbox_r": r_,
                "bbox_b": b_,
                "coord_origin": coord_origin,
                "charspan_start": int(charspan[0]) if len(charspan) >= 1 else None,
                "charspan_end": int(charspan[1]) if len(charspan) >= 2 else None,
            }
        )
    return rows


def dfs_order(doc_data: dict[str, Any], skip_refs: set[str] | None = None) -> list[str]:
    """Return `self_ref`s in reading order (DFS pre-order from body).

    `skip_refs` (typically the set returned by `build_inline_index`) is omitted
    from the chain. Inline groups themselves are emitted but the walk does not
    recurse into their style-run children, so the resulting order references
    only nodes that survive the InlineGroup collapse.
    """
    skip = skip_refs or set()
    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item
    body = doc_data.get("body") or {}
    order: list[str] = []

    def walk(children: list[dict[str, Any]] | None) -> None:
        if not children:
            return
        for ch in children:
            ref = ch.get("$ref") or ch.get("cref")
            if not ref or ref in skip:
                continue
            order.append(ref)
            child = by_ref.get(ref)
            if child and not is_inline_group(child):
                walk(child.get("children"))

    walk(body.get("children"))
    return order


def build_collapse_index(
    doc_data: dict[str, Any],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Pre-compute graph-projection collapses for a serialized DoclingDocument.

    Two cases produce noise nodes if mirrored 1:1 — see issue #197:

    1. **InlineGroup** — Docling emits one `groups[]` entry (label `inline`)
       plus N `texts[]` style runs. We collapse the children into the group,
       which is then projected as a single `:Paragraph` with concatenated
       text and the union of children's provs.
    2. **Picture / Chart** — internal text labels extracted from flowcharts,
       diagrams or chart axes hang off the picture's `children`. The picture
       node itself stays, but its descendants are skipped so the graph isn't
       drowned in dozens of tiny labels.

    Returns `(skip_refs, inline_meta)`:

    - `skip_refs`: every `self_ref` to drop from element / edge projections.
    - `inline_meta[group_ref]`: `{"text": str, "provs": list[dict]}` —
      override values for the inline group projection. Pictures don't have
      an entry here; they keep their own text/prov.
    """
    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item

    skip_refs: set[str] = set()
    inline_meta: dict[str, dict[str, Any]] = {}

    for item in by_ref.values():
        ref = item.get("self_ref") or ""
        if not ref:
            continue
        if is_inline_group(item):
            text_parts, provs = _collect_inline_descendants(ref, by_ref, skip_refs)
            # Re-index prov order so the resulting :Provenance nodes are 0..N-1
            # contiguous instead of carrying each child's individual indices.
            for idx, prov in enumerate(provs):
                prov["order"] = idx
            inline_meta[ref] = {
                "text": " ".join(text_parts),
                "provs": provs,
            }
        elif is_picture(item):
            _collect_descendants(ref, by_ref, skip_refs)

    return skip_refs, inline_meta


def _collect_descendants(
    root_ref: str,
    by_ref: dict[str, dict[str, Any]],
    skip_refs: set[str],
) -> None:
    """DFS `root_ref`'s subtree and add every descendant to `skip_refs`.

    Used for picture children — we just want them dropped, not aggregated.
    """

    def walk(ref: str) -> None:
        item = by_ref.get(ref)
        if item is None:
            return
        for ch in item.get("children") or []:
            child_ref = ch.get("$ref") or ch.get("cref")
            if not child_ref or child_ref in skip_refs:
                continue
            skip_refs.add(child_ref)
            walk(child_ref)

    walk(root_ref)


def _collect_inline_descendants(
    group_ref: str,
    by_ref: dict[str, dict[str, Any]],
    skip_refs: set[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    """DFS an inline group's subtree, returning its text parts and provs in
    document order. `skip_refs` is mutated with every visited descendant."""
    text_parts: list[str] = []
    provs: list[dict[str, Any]] = []

    def walk(ref: str) -> None:
        item = by_ref.get(ref)
        if item is None:
            return
        for ch in item.get("children") or []:
            child_ref = ch.get("$ref") or ch.get("cref")
            if not child_ref or child_ref in skip_refs:
                continue
            skip_refs.add(child_ref)
            child = by_ref.get(child_ref)
            if child is None:
                continue
            if is_inline_group(child):
                walk(child_ref)
                continue
            text = child.get("text") or ""
            if text:
                text_parts.append(text)
            provs.extend(iter_provs(child))

    walk(group_ref)
    return text_parts, provs


def iter_pages(doc_data: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield page dicts with `page_no`, `width`, `height` from the `pages` map."""
    for page_no_str, page_obj in (doc_data.get("pages") or {}).items():
        try:
            page_no = int(page_no_str)
        except (TypeError, ValueError):
            continue
        size = (page_obj or {}).get("size") or {}
        yield {
            "page_no": page_no,
            "width": size.get("width"),
            "height": size.get("height"),
        }


# ---------------------------------------------------------------------------
# Adapter class — implements `domain.ports.DocumentTreeReader` (#audit-01).
# Wraps the module-level free functions so services can depend on the port
# rather than reaching into infra at call sites. The free functions stay
# public so other infra modules (`docling_graph`, `neo4j.tree_writer`) can
# keep using them at module level — they're peers, not consumers.
# ---------------------------------------------------------------------------


class DoclingTreeReader:
    """Stateless adapter for the `DocumentTreeReader` port."""

    def iter_items(self, doc_data: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
        return iter_items(doc_data)

    def is_inline_group(self, item: dict[str, Any]) -> bool:
        return is_inline_group(item)

    def build_collapse_index(
        self, doc_data: dict[str, Any]
    ) -> tuple[set[str], dict[str, dict[str, Any]]]:
        return build_collapse_index(doc_data)

"""Indexing a parse — one walk, everything a later read needs.

Pure projection over a serialized `DoclingDocument`: no I/O, no dates, no
randomness, and no docling import. Every docling-shaped access goes through
the injected `DocumentTreeReader` port, so this module knows the *structure*
of a parsed document without importing the library that produced it.

The index is built once per (document, parse) and read many times — reading
order, heading breadcrumbs, section boundaries and page provenance are all
computed here so that resolving a ref, rendering a section or drawing an
outline is a lookup rather than another walk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from domain.heading_tree import nest_by_heading
from domain.navigation import BoundingBox, is_heading

if TYPE_CHECKING:
    from domain.ports import DocumentTreeReader

# Virtual refs for the page fallback. They are not docling `self_ref`s — the
# navigator synthesises them — but they round-trip through the same anchor
# grammar, so an agent handles both kinds without a special case.
PAGE_REF_PREFIX = "#/pages/"

_MAX_TITLE_LEN = 96


def build_page_ref(page: int) -> str:
    return f"{PAGE_REF_PREFIX}{page}"


def parse_page_ref(ref: str) -> int | None:
    """Return the page number of a virtual page ref, or None if it isn't one."""
    if not ref.startswith(PAGE_REF_PREFIX):
        return None
    try:
        return int(ref[len(PAGE_REF_PREFIX) :])
    except ValueError:
        return None


@dataclass(frozen=True)
class DocumentIndex:
    """Everything one walk of the parse can pre-compute.

    Built once per (document, version) read. Callers treat it as opaque and
    go through the module's functions.
    """

    by_ref: dict[str, dict[str, Any]]
    order: list[str]
    position: dict[str, int]
    heading_path: dict[str, list[str]]
    section_end: dict[str, int]
    # The page an element *starts* on — what a citation reports.
    page_of: dict[str, int]
    # Every page an element touches. An element that straddles a page break is
    # on both, and a "read page N" that only knew about starting pages would
    # silently drop the half of the paragraph the reader can actually see.
    pages_of: dict[str, frozenset[int]]
    bbox_of: dict[str, BoundingBox]
    inline_meta: dict[str, dict[str, Any]]
    page_numbers: list[int] = field(default_factory=list)
    page_sizes: dict[int, tuple[float, float]] = field(default_factory=dict)
    # Every box an element has, one per provenance. `bbox_of` keeps the
    # first, which is what a citation reports; drawing where a section sits
    # needs the rest too, or the half of a paragraph after a page break, the
    # half a reader sees on the next page, has no box.
    boxes_of: dict[str, tuple[BoundingBox, ...]] = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return max(self.page_numbers) if self.page_numbers else 0


@dataclass(frozen=True)
class _Provenance:
    """Where each located element sits: see the fields of `DocumentIndex`."""

    page_of: dict[str, int]
    pages_of: dict[str, frozenset[int]]
    bbox_of: dict[str, BoundingBox]
    boxes_of: dict[str, tuple[BoundingBox, ...]]


def build_index(doc_data: dict[str, Any], tree_reader: DocumentTreeReader) -> DocumentIndex:
    """Walk a parse once and pre-compute order, breadcrumbs and provenance."""
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)
    by_ref = index_items_by_ref(doc_data, tree_reader)

    order = [ref for ref in tree_reader.list_dfs_order(doc_data, skip_refs) if ref in by_ref]
    position = {ref: idx for idx, ref in enumerate(order)}
    heading_path, section_end = _map_sections(order, by_ref, inline_meta)
    page_sizes = _read_page_sizes(doc_data, tree_reader)
    located = _locate_items(by_ref, inline_meta, page_sizes, tree_reader)

    page_numbers = _list_page_numbers(page_sizes, located)

    return DocumentIndex(
        by_ref=by_ref,
        order=order,
        position=position,
        heading_path=heading_path,
        section_end=section_end,
        page_of=located.page_of,
        pages_of=located.pages_of,
        bbox_of=located.bbox_of,
        inline_meta=inline_meta,
        page_numbers=page_numbers,
        page_sizes=page_sizes,
        boxes_of=located.boxes_of,
    )


def index_items_by_ref(
    doc_data: dict[str, Any], tree_reader: DocumentTreeReader
) -> dict[str, dict[str, Any]]:
    """Every item of the parse that has a `self_ref`, by that ref."""
    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item
    return by_ref


def _map_sections(
    order: list[str],
    by_ref: dict[str, dict[str, Any]],
    inline_meta: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Each element's heading breadcrumb, and where each heading's section ends.

    A section ends where the next heading at its level or above starts, or
    at the end of the document; the breadcrumb is the open headings' titles.
    """
    heading_path: dict[str, list[str]] = {}
    section_end: dict[str, int] = {}
    titles: dict[int, str] = {}
    nesting = nest_by_heading([by_ref[ref] for ref in order], level_of=read_heading_level)
    for step in nesting.steps:
        ref = order[step.position]
        for closed in step.closed:
            section_end[order[closed]] = step.position
        heading_path[ref] = [titles[ancestor] for ancestor in step.ancestors]
        if step.opened:
            titles[step.position] = get_title(by_ref[ref], inline_meta)
    for still_open in reversed(nesting.still_open):
        section_end[order[still_open]] = len(order)
    return heading_path, section_end


def _list_page_numbers(
    page_sizes: dict[int, tuple[float, float]], located: _Provenance
) -> list[int]:
    # Union, not `or`: a parse whose `pages` map is partial (a page with no
    # `size`) would otherwise drop that page from the map entirely — and the
    # page fallback exists precisely for scans, where that metadata is the
    # first thing to be missing. A page an element sits on is a page.
    return sorted(
        set(page_sizes) | {number for pages in located.pages_of.values() for number in pages}
    )


def _read_page_sizes(
    doc_data: dict[str, Any], tree_reader: DocumentTreeReader
) -> dict[int, tuple[float, float]]:
    page_sizes: dict[int, tuple[float, float]] = {}
    for page in tree_reader.iter_pages(doc_data):
        number = page.get("page_no")
        if number is None:
            continue
        width, height = page.get("width"), page.get("height")
        if width and height:
            page_sizes[int(number)] = (float(width), float(height))
    return page_sizes


def _locate_items(
    by_ref: dict[str, dict[str, Any]],
    inline_meta: dict[str, dict[str, Any]],
    page_sizes: dict[int, tuple[float, float]],
    tree_reader: DocumentTreeReader,
) -> _Provenance:
    """The pages and boxes of every element with a located provenance."""
    located_items = _Provenance(page_of={}, pages_of={}, bbox_of={}, boxes_of={})
    for ref, item in by_ref.items():
        provs = tree_reader.iter_provs(item)
        if not provs and ref in inline_meta:
            provs = inline_meta[ref].get("provs") or []
        located = [p for p in provs if p.get("page_no") is not None]
        if not located:
            continue
        located_items.page_of[ref] = int(located[0]["page_no"])
        located_items.pages_of[ref] = frozenset(int(p["page_no"]) for p in located)
        boxes = tuple(_to_box(prov, page_sizes) for prov in located)
        located_items.bbox_of[ref] = boxes[0]
        located_items.boxes_of[ref] = boxes
    return located_items


def _to_box(prov: dict[str, Any], page_sizes: dict[int, tuple[float, float]]) -> BoundingBox:
    """One provenance row as a box on its own page, with that page's size."""
    page = int(prov["page_no"])
    width, height = page_sizes.get(page, (None, None))
    return BoundingBox(
        page=page,
        left=float(prov.get("bbox_l", 0.0)),
        top=float(prov.get("bbox_t", 0.0)),
        right=float(prov.get("bbox_r", 0.0)),
        bottom=float(prov.get("bbox_b", 0.0)),
        coord_origin=str(prov.get("coord_origin") or "TOPLEFT"),
        page_width=width,
        page_height=height,
    )


def get_heading_level(item: dict[str, Any]) -> int:
    """0 for the document title, >=1 for section headers (docling `level`)."""
    if get_label(item) == "title":
        return 0
    try:
        return max(int(item.get("level") or 1), 1)
    except (TypeError, ValueError):
        return 1


def read_heading_level(item: dict[str, Any]) -> int | None:
    """The heading level of an item, None when its label is not a heading.

    The rule the parse index and the outline nest by: `HEADING_LABELS` for
    what a heading is, `get_heading_level` for its level.
    """
    return get_heading_level(item) if is_heading(get_label(item)) else None


def get_label(item: dict[str, Any]) -> str:
    return (item.get("label") or "text").lower()


def get_title(item: dict[str, Any], inline_meta: dict[str, dict[str, Any]]) -> str:
    ref = item.get("self_ref") or ""
    meta = inline_meta.get(ref)
    raw = (meta or {}).get("text") or item.get("text") or ""
    title = str(raw).strip()
    if title:
        return truncate_title(title)
    label = get_label(item)
    return {"table": "Table", "picture": "Figure", "list": "List"}.get(label, label or "node")


def truncate_title(text: str, max_len: int = _MAX_TITLE_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

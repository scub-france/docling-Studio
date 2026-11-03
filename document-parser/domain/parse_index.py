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

from domain.navigation import BoundingBox, is_heading

if TYPE_CHECKING:
    from domain.ports import DocumentTreeReader

# Virtual refs for the page fallback. They are not docling `self_ref`s — the
# navigator synthesises them — but they round-trip through the same anchor
# grammar, so an agent handles both kinds without a special case.
PAGE_REF_PREFIX = "#/pages/"

_MAX_TITLE_LEN = 96


def page_ref(page: int) -> str:
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


def build_index(doc_data: dict[str, Any], tree_reader: DocumentTreeReader) -> DocumentIndex:
    """Walk a parse once and pre-compute order, breadcrumbs and provenance."""
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)
    by_ref = _items_by_ref(doc_data, tree_reader)
    order = [ref for ref in tree_reader.dfs_order(doc_data, skip_refs) if ref in by_ref]
    heading_path, section_end = _heading_paths(order, by_ref, inline_meta)
    page_sizes = _page_sizes(doc_data, tree_reader)
    provenance = _provenance(by_ref, inline_meta, tree_reader, page_sizes)

    # Union, not `or`: a parse whose `pages` map is partial (a page with no
    # `size`) would otherwise drop that page from the map entirely — and the
    # page fallback exists precisely for scans, where that metadata is the
    # first thing to be missing. A page an element sits on is a page.
    page_numbers = sorted(
        set(page_sizes) | {number for pages in provenance.pages_of.values() for number in pages}
    )

    return DocumentIndex(
        by_ref=by_ref,
        order=order,
        position={ref: idx for idx, ref in enumerate(order)},
        heading_path=heading_path,
        section_end=section_end,
        page_of=provenance.page_of,
        pages_of=provenance.pages_of,
        bbox_of=provenance.bbox_of,
        inline_meta=inline_meta,
        page_numbers=page_numbers,
        page_sizes=page_sizes,
        boxes_of=provenance.boxes_of,
    )


def _items_by_ref(
    doc_data: dict[str, Any], tree_reader: DocumentTreeReader
) -> dict[str, dict[str, Any]]:
    """Every element of the parse by its `self_ref`; one without a ref is not
    addressable, so it is left out."""
    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item
    return by_ref


def _heading_paths(
    order: list[str],
    by_ref: dict[str, dict[str, Any]],
    inline_meta: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Each element's heading breadcrumb, and where each heading's section ends.

    One pass over reading order with a stack of open headings: a heading
    closes every open one at its level or deeper, so its section ends where
    the next peer (or a higher heading) starts. `section_end` is a position
    in `order`, exclusive; a section still open at the end runs to the end.
    """
    heading_path: dict[str, list[str]] = {}
    section_end: dict[str, int] = {}
    stack: list[tuple[int, str, str]] = []  # (level, ref, title)

    for idx, ref in enumerate(order):
        item = by_ref[ref]
        label = label_of(item)
        if is_heading(label):
            level = heading_level(item)
            while stack and stack[-1][0] >= level:
                _, closed, _ = stack.pop()
                section_end[closed] = idx
            heading_path[ref] = [title for _, _, title in stack]
            stack.append((level, ref, title_of(item, inline_meta)))
        else:
            heading_path[ref] = [title for _, _, title in stack]
    while stack:
        _, closed, _ = stack.pop()
        section_end[closed] = len(order)
    return heading_path, section_end


def _page_sizes(
    doc_data: dict[str, Any], tree_reader: DocumentTreeReader
) -> dict[int, tuple[float, float]]:
    """`(width, height)` of each page the parse gives a full size for."""
    page_sizes: dict[int, tuple[float, float]] = {}
    for page in tree_reader.iter_pages(doc_data):
        number = page.get("page_no")
        if number is None:
            continue
        width, height = page.get("width"), page.get("height")
        if width and height:
            page_sizes[int(number)] = (float(width), float(height))
    return page_sizes


@dataclass(frozen=True)
class _Provenance:
    """Where each located element sits — see the fields of `DocumentIndex`."""

    page_of: dict[str, int]
    pages_of: dict[str, frozenset[int]]
    bbox_of: dict[str, BoundingBox]
    boxes_of: dict[str, tuple[BoundingBox, ...]]


def _provenance(
    by_ref: dict[str, dict[str, Any]],
    inline_meta: dict[str, dict[str, Any]],
    tree_reader: DocumentTreeReader,
    page_sizes: dict[int, tuple[float, float]],
) -> _Provenance:
    """The pages and boxes of every element that has a page.

    An inline group has no provenance of its own: it takes its runs', which
    the collapse index gathered. An element with no page is left out.
    """
    page_of: dict[str, int] = {}
    pages_of: dict[str, frozenset[int]] = {}
    bbox_of: dict[str, BoundingBox] = {}
    boxes_of: dict[str, tuple[BoundingBox, ...]] = {}
    for ref, item in by_ref.items():
        provs = tree_reader.iter_provs(item)
        if not provs and ref in inline_meta:
            provs = inline_meta[ref].get("provs") or []
        located = [p for p in provs if p.get("page_no") is not None]
        if not located:
            continue
        page_of[ref] = int(located[0]["page_no"])
        pages_of[ref] = frozenset(int(p["page_no"]) for p in located)
        boxes = tuple(_box(prov, page_sizes) for prov in located)
        bbox_of[ref] = boxes[0]
        boxes_of[ref] = boxes
    return _Provenance(page_of=page_of, pages_of=pages_of, bbox_of=bbox_of, boxes_of=boxes_of)


def _box(prov: dict[str, Any], page_sizes: dict[int, tuple[float, float]]) -> BoundingBox:
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


def heading_level(item: dict[str, Any]) -> int:
    """0 for the document title, >=1 for section headers (docling `level`).

    Docling writes `level` as an int in 1..100 (`SectionHeaderItem.level`,
    and an imported document is re-serialized by docling-core). Anything
    else — absent, zero, negative, not a number — reads as 1, so one odd
    header never fails the walk of a whole document.
    """
    if label_of(item) == "title":
        return 0
    try:
        return max(int(item.get("level") or 1), 1)
    except (TypeError, ValueError):
        return 1


def label_of(item: dict[str, Any]) -> str:
    return (item.get("label") or "text").lower()


def title_of(item: dict[str, Any], inline_meta: dict[str, dict[str, Any]]) -> str:
    ref = item.get("self_ref") or ""
    meta = inline_meta.get(ref)
    raw = (meta or {}).get("text") or item.get("text") or ""
    title = str(raw).strip()
    if title:
        return truncate_title(title)
    label = label_of(item)
    return {"table": "Table", "picture": "Figure", "list": "List"}.get(label, label or "node")


def truncate_title(text: str, max_len: int = _MAX_TITLE_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

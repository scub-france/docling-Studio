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

    @property
    def page_count(self) -> int:
        return max(self.page_numbers) if self.page_numbers else 0


def build_index(doc_data: dict[str, Any], tree_reader: DocumentTreeReader) -> DocumentIndex:
    """Walk a parse once and pre-compute order, breadcrumbs and provenance."""
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)

    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item

    order = [ref for ref in tree_reader.dfs_order(doc_data, skip_refs) if ref in by_ref]
    position = {ref: idx for idx, ref in enumerate(order)}

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

    page_sizes: dict[int, tuple[float, float]] = {}
    for page in tree_reader.iter_pages(doc_data):
        number = page.get("page_no")
        if number is None:
            continue
        width, height = page.get("width"), page.get("height")
        if width and height:
            page_sizes[int(number)] = (float(width), float(height))

    page_of: dict[str, int] = {}
    pages_of: dict[str, frozenset[int]] = {}
    bbox_of: dict[str, BoundingBox] = {}
    for ref, item in by_ref.items():
        provs = tree_reader.iter_provs(item)
        if not provs and ref in inline_meta:
            provs = inline_meta[ref].get("provs") or []
        located = [p for p in provs if p.get("page_no") is not None]
        if not located:
            continue
        first = located[0]
        page = int(first["page_no"])
        page_of[ref] = page
        pages_of[ref] = frozenset(int(p["page_no"]) for p in located)
        width, height = page_sizes.get(page, (None, None))
        bbox_of[ref] = BoundingBox(
            page=page,
            left=float(first.get("bbox_l", 0.0)),
            top=float(first.get("bbox_t", 0.0)),
            right=float(first.get("bbox_r", 0.0)),
            bottom=float(first.get("bbox_b", 0.0)),
            coord_origin=str(first.get("coord_origin") or "TOPLEFT"),
            page_width=width,
            page_height=height,
        )

    # Union, not `or`: a parse whose `pages` map is partial (a page with no
    # `size`) would otherwise drop that page from the map entirely — and the
    # page fallback exists precisely for scans, where that metadata is the
    # first thing to be missing. A page an element sits on is a page.
    page_numbers = sorted(
        set(page_sizes) | {number for pages in pages_of.values() for number in pages}
    )

    return DocumentIndex(
        by_ref=by_ref,
        order=order,
        position=position,
        heading_path=heading_path,
        section_end=section_end,
        page_of=page_of,
        pages_of=pages_of,
        bbox_of=bbox_of,
        inline_meta=inline_meta,
        page_numbers=page_numbers,
        page_sizes=page_sizes,
    )


def heading_level(item: dict[str, Any]) -> int:
    """0 for the document title, >=1 for section headers (docling `level`)."""
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

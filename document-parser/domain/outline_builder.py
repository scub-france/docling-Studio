"""Projecting an indexed parse into the map an agent reads first.

Sections when the parse carries at least two headings, pages otherwise — a
scanned PDF with no `section_header` is the common case, not the edge case,
and a map is what makes the rest of the surface usable. Text before the first
heading gets a node of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.element_reader import element_text, section_refs
from domain.navigation import OutlineNode, estimate_tokens, is_heading
from domain.parse_index import (
    heading_level,
    label_of,
    page_ref,
    title_of,
    truncate_title,
)
from domain.spans import span_ref

if TYPE_CHECKING:
    from domain.parse_index import DocumentIndex


@dataclass(frozen=True)
class OutlineDraft:
    """`build_outline`'s answer: the nodes plus how the map was cut."""

    nodes: list[OutlineNode]
    mode: str  # "sections" | "pages"
    total_est_tokens: int
    depth_limited: bool = False
    node_limited: bool = False


def build_outline(
    index: DocumentIndex,
    *,
    depth: int = 2,
    max_nodes: int = 200,
) -> OutlineDraft:
    """Project the index into a map.

    `mode` is `"sections"` from two headings up, `"pages"` below — a scanned
    PDF still gets a usable map.
    """
    total = sum(estimate_tokens(element_text(index, ref)) for ref in index.order)
    headings = [ref for ref in index.order if is_heading(label_of(index.by_ref[ref]))]
    # One heading makes a one-node map that says nothing; pages say more.
    if len(headings) < 2:
        nodes, node_limited = _page_nodes(index, max_nodes=max_nodes)
        return OutlineDraft(
            nodes=nodes, mode="pages", total_est_tokens=total, node_limited=node_limited
        )

    nodes, depth_limited, node_limited = _section_nodes(
        index, headings, depth=depth, max_nodes=max_nodes
    )
    preamble = preamble_range(index)
    if preamble is not None:
        nodes.insert(0, _preamble_node(index, preamble[0]))
    return OutlineDraft(
        nodes=nodes,
        mode="sections",
        total_est_tokens=total,
        depth_limited=depth_limited,
        node_limited=node_limited,
    )


def _section_nodes(
    index: DocumentIndex,
    headings: list[str],
    *,
    depth: int,
    max_nodes: int,
) -> tuple[list[OutlineNode], bool, bool]:
    roots: list[OutlineNode] = []
    # Stack of (level, mutable children list) — the root sentinel is level -1
    # so any heading nests inside it, mirroring `ChunkService`'s doc tree.
    stack: list[tuple[int, list[OutlineNode]]] = [(-1, roots)]
    emitted = 0
    depth_limited = False
    node_limited = False
    child_counts = _child_counts(index, headings)

    for ref in headings:
        item = index.by_ref[ref]
        level = heading_level(item)
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        # A document `title` wraps everything without being a level a reader
        # thinks about, so it does not consume depth budget: `depth=2` means
        # chapters and their subsections, title or no title.
        nesting = sum(1 for open_level, _ in stack[1:] if open_level > 0)
        if nesting >= depth:
            # Deeper than requested: its tokens still count towards the
            # nearest emitted ancestor, so nothing is hidden from the budget.
            depth_limited = True
            continue
        if emitted >= max_nodes:
            node_limited = True
            break
        children: list[OutlineNode] = []
        node = OutlineNode(
            ref=ref,
            uri="",  # stamped by the service, which owns the version token
            title=title_of(item, index.inline_meta),
            kind="section",
            level=level,
            page=index.page_of.get(ref),
            est_tokens=section_est_tokens(index, ref),
            child_count=child_counts.get(ref, 0),
            children=children,
        )
        stack[-1][1].append(node)
        stack.append((level, children))
        emitted += 1

    return roots, depth_limited, node_limited


def _page_nodes(index: DocumentIndex, *, max_nodes: int) -> tuple[list[OutlineNode], bool]:
    pages = index.page_numbers or sorted({p for pages in index.pages_of.values() for p in pages})
    truncated = len(pages) > max_nodes
    nodes: list[OutlineNode] = []
    for page in pages[:max_nodes]:
        refs = [ref for ref in index.order if page in index.pages_of.get(ref, frozenset())]
        text = " ".join(element_text(index, ref) for ref in refs).strip()
        nodes.append(
            OutlineNode(
                ref=page_ref(page),
                uri="",
                title=truncate_title(text) if text else f"Page {page}",
                kind="page",
                level=1,
                page=page,
                est_tokens=estimate_tokens(text),
                child_count=len(refs),
            )
        )
    return nodes, truncated


def section_est_tokens(index: DocumentIndex, ref: str) -> int:
    return sum(estimate_tokens(element_text(index, r)) for r in section_refs(index, ref))


def _child_counts(index: DocumentIndex, headings: list[str]) -> dict[str, int]:
    """How many headings nest directly under each one — by the same rule the
    outline nests them (pop while the open heading is not shallower), so the
    count agrees with `children` even when docling skips a level."""
    counts: dict[str, int] = {}
    open_headings: list[tuple[int, str]] = []
    for ref in headings:
        level = heading_level(index.by_ref[ref])
        while open_headings and open_headings[-1][0] >= level:
            open_headings.pop()
        if open_headings:
            parent = open_headings[-1][1]
            counts[parent] = counts.get(parent, 0) + 1
        open_headings.append((level, ref))
    return counts


def preamble_range(index: DocumentIndex) -> tuple[str, int, int] | None:
    """`(ref, start, end)` of the text before the first heading, or None.

    A contract names its parties before its first article, and a heading-only
    map would leave that text unreachable. The ref is the element itself when
    one carries text, the span over those that do otherwise — spans already
    read, budget and verify like any ref.
    """
    first = next(
        (i for i, ref in enumerate(index.order) if is_heading(label_of(index.by_ref[ref]))),
        None,
    )
    if not first:
        return None
    texts = [ref for ref in index.order[:first] if element_text(index, ref).strip()]
    if not texts:
        return None
    ref = texts[0] if len(texts) == 1 else span_ref(texts[0], texts[-1])
    return ref, 0, first


def _preamble_node(index: DocumentIndex, ref: str) -> OutlineNode:
    first = ref.split("..", 1)[0]
    return OutlineNode(
        ref=ref,
        uri="",
        title=truncate_title(element_text(index, first)),
        kind="preamble",
        level=1,
        page=index.page_of.get(first),
        est_tokens=section_est_tokens(index, ref),
        child_count=0,
    )

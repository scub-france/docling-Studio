"""Projecting an indexed parse into the map an agent reads first.

Sections when the parse carries headings, pages when it does not — a scanned
PDF with no `section_header` is the common case, not the edge case, and a map
is what makes the rest of the surface usable.
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

    `mode` is `"sections"` when the parse carries headings, `"pages"` when it
    doesn't — a scanned PDF still gets a usable map.
    """
    total = sum(estimate_tokens(element_text(index, ref)) for ref in index.order)
    headings = [ref for ref in index.order if is_heading(label_of(index.by_ref[ref]))]
    if not headings:
        nodes, node_limited = _page_nodes(index, max_nodes=max_nodes)
        return OutlineDraft(
            nodes=nodes, mode="pages", total_est_tokens=total, node_limited=node_limited
        )

    nodes, depth_limited, node_limited = _section_nodes(
        index, headings, depth=depth, max_nodes=max_nodes
    )
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
            child_count=_direct_child_headings(index, ref, level),
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


def _direct_child_headings(index: DocumentIndex, ref: str, level: int) -> int:
    """Count the subsections that nest *directly* under `ref`.

    Not `level + 1`: docling derives heading levels from the document's visual
    hierarchy and routinely skips numbers (an h1 followed by h3s). The outline
    nests by relative depth — pop until the top of the stack is shallower — so
    counting by absolute level would publish `child_count: 0` next to a
    non-empty `children` list. The direct children are the headings at the
    *shallowest level present* inside the section.
    """
    start = index.position.get(ref)
    if start is None:
        return 0
    end = index.section_end.get(ref, start + 1)
    levels = [
        heading_level(index.by_ref[candidate])
        for candidate in index.order[start + 1 : end]
        if is_heading(label_of(index.by_ref[candidate]))
    ]
    inner = [value for value in levels if value > level]
    if not inner:
        return 0
    shallowest = min(inner)
    return sum(1 for value in inner if value == shallowest)

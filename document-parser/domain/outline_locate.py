"""Where an element sits on the outline — containment, shared by projections.

An anchor names an *element* (`#/texts/91`); the outline holds *sections* —
or virtual pages, for a document with no headings. `containing_chain` resolves
an element to the outline candidates that contain it, deepest first, so a
projection can attribute it to the first one the outline actually published.

Pure: it reads the parse's `DocumentIndex` and the outline, nothing else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.navigation import is_heading
from domain.outline_builder import preamble_range
from domain.parse_index import label_of, page_ref, parse_page_ref
from domain.spans import span_start

if TYPE_CHECKING:
    from domain.navigation import OutlineNode
    from domain.parse_index import DocumentIndex


def containing_chain(
    ref: str,
    index: DocumentIndex,
    ranges: list[tuple[str, int, int]],
    *,
    mode: str,
) -> list[str]:
    """Outline candidates containing `ref`, deepest first.

    A span (`#/texts/91..#/texts/94`) is located by its first member — the
    same rule the citation crop uses for a passage straddling two pages.
    """
    target = span_start(ref)
    if mode == "pages":
        page = parse_page_ref(target) or index.page_of.get(target)
        return [page_ref(page)] if page is not None else []

    position = index.position.get(target)
    if position is None:
        return []
    holding = [(start, held) for held, start, end in ranges if start <= position < end]
    return [held for _, held in sorted(holding, reverse=True)]


def heading_ranges(index: DocumentIndex) -> list[tuple[str, int, int]]:
    """`(ref, start, end)` for every heading and the preamble before the first,
    as half-open reading-order slices."""
    preamble = preamble_range(index)
    ranges: list[tuple[str, int, int]] = [preamble] if preamble else []
    for position, ref in enumerate(index.order):
        if not is_heading(label_of(index.by_ref[ref])):
            continue
        ranges.append((ref, position, index.section_end.get(ref, position + 1)))
    return ranges


def flatten(nodes: list[OutlineNode]) -> list[tuple[OutlineNode, list[str]]]:
    """Outline tree to `(node, ancestor refs)` in pre-order — document order."""
    flat: list[tuple[OutlineNode, list[str]]] = []

    def walk(current: list[OutlineNode], ancestors: list[str]) -> None:
        for node in current:
            flat.append((node, ancestors))
            walk(node.children, [*ancestors, node.ref])

    walk(nodes, [])
    return flat

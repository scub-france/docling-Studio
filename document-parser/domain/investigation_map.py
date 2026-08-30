"""The navigation tree — an investigation projected onto the document map.

`reasoning[]` says how the agent thought; this says *where it went*. Same
record, read against the structure of the document instead of against the
order of the conversation: the outline nodes the investigation touched, in
document order, each marked with what happened there.

Pure, like `trace_builder` and for the same reason — it takes a
`DocumentOutline`, an `Investigation` and the parse's `DocumentIndex`, and
returns value objects. It loads nothing and asks no service anything.

The one piece of real work is containment. An attempt cites an *element*
(`#/texts/91`); the outline holds *sections* — or virtual pages, for a
document with no headings. So each attempt is resolved to the chain of
outline candidates that contain it, deepest first, and attributed to the
first one the outline actually published: a section elided by `depth` or cut
by the node cap is not a place the reader can navigate to, so its hits
belong to its nearest visible ancestor rather than vanishing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.investigation import AttemptOutcome
from domain.navigation import is_heading
from domain.parse_index import label_of, page_ref, parse_page_ref
from domain.spans import span_start

if TYPE_CHECKING:
    from domain.investigation import Attempt, Investigation
    from domain.navigation import DocumentOutline, OutlineNode
    from domain.parse_index import DocumentIndex

# Ordered weakest to strongest: a node that was rejected once and kept once
# is a place the investigation ended up, not a dead end.
STATUS_PATH = "path"
STATUS_VISITED = "visited"
STATUS_REJECTED = "rejected"
STATUS_KEPT = "kept"

_RANK = {STATUS_PATH: 0, STATUS_VISITED: 1, STATUS_REJECTED: 2, STATUS_KEPT: 3}


@dataclass(frozen=True)
class MapNode:
    """One outline node, annotated with what the investigation did there.

    `status` is `kept` (a ref here was allowed to be cited), `rejected` (one
    was tried and did not hold up), `visited` (tried, verdict still pending)
    or `path` (touched only as the route to a marked descendant).
    """

    ref: str
    uri: str
    title: str
    kind: str
    level: int
    status: str
    page: int | None = None
    step_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InvestigationReport:
    """An investigation as its readers want it: the record, the tree it draws,
    and the name of the document both are about.

    `filename` is here rather than looked up again by each caller — the
    service has the parse open when it builds the map, and a viewer that has
    to make a second call to say which document it is showing is a viewer
    that will sometimes show the wrong one."""

    investigation: Investigation
    filename: str
    map: list[MapNode]


def build_navigation_map(
    outline: DocumentOutline,
    investigation: Investigation,
    index: DocumentIndex,
) -> list[MapNode]:
    """Project `investigation` onto `outline`, in document order."""
    flat = _flatten(outline.nodes)
    published = {node.ref for node, _ in flat}
    ranges = _heading_ranges(index) if outline.mode == "sections" else []

    status: dict[str, str] = {}
    steps: dict[str, list[str]] = {}
    for step in investigation.steps:
        for attempt in step.attempts:
            target = _target(attempt, index, published, ranges, mode=outline.mode)
            if target is None:
                continue
            status[target] = _stronger(status.get(target), _status_of(attempt))
            reached = steps.setdefault(target, [])
            if step.id not in reached:
                reached.append(step.id)

    keep = set(status)
    for node, ancestors in flat:
        if node.ref in status:
            keep.update(ancestors)

    return [
        MapNode(
            ref=node.ref,
            uri=node.uri,
            title=node.title,
            kind=node.kind,
            level=node.level,
            page=node.page,
            status=status.get(node.ref, STATUS_PATH),
            step_ids=steps.get(node.ref, []),
        )
        for node, _ in flat
        if node.ref in keep
    ]


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


def _target(
    attempt: Attempt,
    index: DocumentIndex,
    published: set[str],
    ranges: list[tuple[str, int, int]],
    *,
    mode: str,
) -> str | None:
    """The published outline node this attempt belongs to, if any."""
    ref = _ref_of(attempt.citation_uri)
    if ref is None:
        return None
    for candidate in containing_chain(ref, index, ranges, mode=mode):
        if candidate in published:
            return candidate
    return None


def _ref_of(uri: str) -> str | None:
    """The ref of an anchor, or None when it never was one.

    A `bad_anchor` attempt has nowhere to land on the map by definition; it
    still appears in `reasoning[]`, which is where a malformed uri belongs.
    """
    from domain.anchors import AnchorParseError, DocumentAnchor

    try:
        return DocumentAnchor.parse(uri).ref
    except AnchorParseError:
        return None


def _status_of(attempt: Attempt) -> str:
    if attempt.outcome is AttemptOutcome.KEPT:
        return STATUS_KEPT
    return STATUS_REJECTED if attempt.settled else STATUS_VISITED


def _stronger(current: str | None, candidate: str) -> str:
    if current is None:
        return candidate
    return candidate if _RANK[candidate] > _RANK[current] else current


def _heading_ranges(index: DocumentIndex) -> list[tuple[str, int, int]]:
    """`(ref, start, end)` for every heading, as half-open reading-order slices."""
    ranges: list[tuple[str, int, int]] = []
    for position, ref in enumerate(index.order):
        if not is_heading(label_of(index.by_ref[ref])):
            continue
        ranges.append((ref, position, index.section_end.get(ref, position + 1)))
    return ranges


def _flatten(nodes: list[OutlineNode]) -> list[tuple[OutlineNode, list[str]]]:
    """Outline tree to `(node, ancestor refs)` in pre-order — document order."""
    flat: list[tuple[OutlineNode, list[str]]] = []

    def walk(current: list[OutlineNode], ancestors: list[str]) -> None:
        for node in current:
            flat.append((node, ancestors))
            walk(node.children, [*ancestors, node.ref])

    walk(nodes, [])
    return flat

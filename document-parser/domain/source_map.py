"""Where an answer came from — the anchors an agent read and cited, on the map.

Chunkless RAG leaves a trail by construction: the agent reads the outline,
opens a few sections, quotes a few passages. This projects that trail onto
the outline, in document order, and counts what the reading cost against the
whole document — the figure that says the agent did not need the rest.

Stateless on purpose: everything it needs arrives with the call (the anchors
the server issued, in the order the agent used them), so there is no journal
to keep, no state to go stale, and nothing for the agent to follow but its
own reading.

Pure: it takes a `DocumentOutline` and the parse's `DocumentIndex` and returns
value objects. It loads nothing and asks no service anything.

The one piece of real work is containment (`domain.outline_locate`): each
anchor is attributed to the deepest outline node that contains it among those
the outline published. A section elided by `depth` or cut by the node cap is
not a place the reader can navigate to, so its hits belong to its nearest
visible ancestor rather than vanishing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from domain.element_reader import list_section_refs, read_element_text
from domain.navigation import read_cost
from domain.outline_locate import find_containing_chain, flatten, list_heading_ranges
from domain.page_regions import collect_regions
from domain.source_bar import SourceSegment, build_segments
from domain.spans import get_span_start

if TYPE_CHECKING:
    from collections.abc import Callable

    from domain.navigation import DocumentOutline, OutlineNode
    from domain.page_regions import PageRegion
    from domain.parse_index import DocumentIndex

# Ordered weakest to strongest: a section that was read and also quoted from
# is a source, not merely a place the agent passed through.
STATUS_PATH = "path"
STATUS_READ = "read"
STATUS_CITED = "cited"

_RANK = {STATUS_PATH: 0, STATUS_READ: 1, STATUS_CITED: 2}


@dataclass(frozen=True)
class SourceRead:
    """One round, as the agent reports it: the anchor its read returned, why
    it went there, and what it found — the reason and the outcome of one turn
    of the Chunkless RAG loop."""

    ref: str
    uri: str
    why: str = ""
    found: str = ""


@dataclass(frozen=True)
class SourceCited:
    """One anchor the agent cites in its answer, with the quote it gave.

    `status` is what the server said of that quote when it checked it again
    (a `CitationStatus` value), or None when no quote came with the anchor:
    a citation nobody checked is shown as cited, never as verified.
    """

    ref: str
    uri: str
    quote: str = ""
    status: str | None = None


@dataclass(frozen=True)
class SourceHop:
    """One round: one section read, in reading order — the unit of the path.

    `node_ref` is the published outline node the read landed in (None when
    the outline does not reach it); `cited` holds the anchors quoted from what
    this read covered.
    """

    hop_id: str
    ordinal: int
    ref: str
    uri: str
    title: str
    why: str
    est_tokens: int
    found: str = ""
    node_ref: str | None = None
    page: int | None = None
    cited: list[str] = field(default_factory=list)
    # Where the section read sits: one block per column run, page by page.
    regions: list[PageRegion] = field(default_factory=list)


@dataclass(frozen=True)
class SourcePassage:
    """One cited passage: its quote, the server's word on it, where it sits.

    `hop_id` is the round whose read covered it, or None when no read did:
    the passage still shows, on its own page. `section` is the title of the
    deepest section on the map that holds it. `marks` are the lines the quote
    itself covers, found in the PDF's text layer by the service; empty when
    it could not be placed there, and the passage is drawn by its `regions`.
    """

    uri: str
    ref: str
    quote: str
    status: str | None
    regions: list[PageRegion]
    hop_id: str | None = None
    page: int | None = None
    section: str = ""
    marks: list[PageRegion] = field(default_factory=list)


@dataclass(frozen=True)
class SourceNode:
    """One outline node on the trail.

    `status` is `cited` (a quoted anchor sits here), `read` (a read landed
    here) or `path` (touched only as the route to a marked descendant).
    """

    ref: str
    uri: str
    title: str
    kind: str
    level: int
    status: str
    est_tokens: int = 0
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceTotals:
    """What the reading cost, against the whole document.

    `tokens_read` counts every element the reads covered, once, at the cost
    the map announces — an upper bound when a read stopped at its budget, so
    the ratio errs against the agent, never for it.
    """

    mode: str
    rounds: int
    sections_read: int
    sections_total: int
    tokens_read: int
    tokens_total: int

    @property
    def percent(self) -> float:
        if self.tokens_total <= 0:
            return 0.0
        return round(100 * self.tokens_read / self.tokens_total, 1)


@dataclass(frozen=True)
class SourceMap:
    nodes: list[SourceNode]
    hops: list[SourceHop]
    totals: SourceTotals
    # The whole document, section by section — the bar the card draws.
    segments: list[SourceSegment] = field(default_factory=list)
    # The passages cited, in the order the agent gave them: one per quote, so
    # three rows quoted out of one table are three passages, not one.
    passages: list[SourcePassage] = field(default_factory=list)


def build_source_map(
    outline: DocumentOutline,
    index: DocumentIndex,
    reads: list[SourceRead],
    cited: list[SourceCited],
) -> SourceMap:
    """Project the reads and the cited anchors onto `outline`."""
    flat = flatten(outline.nodes)
    published = {node.ref: node for node, _ in flat}
    locate = _build_locator(outline, index, published)
    hops, covered = _build_hops(reads, index, published, locate)
    trail = _Trail()
    for hop in hops:
        trail.mark(hop.node_ref, STATUS_READ, hop.hop_id)
    passages: dict[tuple[str, str], SourcePassage] = {}
    for anchor in cited:
        hop = _find_covering_hop(get_span_start(anchor.ref), hops, covered)
        if hop is not None and anchor.uri not in hop.cited:
            hop.cited.append(anchor.uri)
        node_ref = locate(anchor.ref)
        trail.mark(node_ref, STATUS_CITED, hop.hop_id if hop else None)
        node = published.get(node_ref) if node_ref else None
        passages.setdefault(
            (anchor.uri, anchor.quote),
            _build_passage(anchor, index, hop, node.title if node else ""),
        )

    return SourceMap(
        nodes=trail.build_nodes(flat),
        hops=hops,
        totals=_compute_totals(outline, len(flat), hops, covered, index),
        segments=build_segments(flat, trail.status, trail.reached),
        passages=list(passages.values()),
    )


def _build_locator(
    outline: DocumentOutline, index: DocumentIndex, published: dict[str, OutlineNode]
) -> Callable[[str], str | None]:
    """The function giving the deepest published node that holds a ref."""
    ranges = list_heading_ranges(index) if outline.mode == "sections" else []

    def locate(ref: str) -> str | None:
        for candidate in find_containing_chain(ref, index, ranges, mode=outline.mode):
            if candidate in published:
                return candidate
        return None

    return locate


def _build_passage(
    anchor: SourceCited, index: DocumentIndex, hop: SourceHop | None, section: str
) -> SourcePassage:
    start = get_span_start(anchor.ref)
    return SourcePassage(
        uri=anchor.uri,
        ref=anchor.ref,
        quote=anchor.quote,
        status=anchor.status,
        regions=collect_regions(index, list_section_refs(index, anchor.ref) or [start]),
        hop_id=hop.hop_id if hop else None,
        page=index.page_of.get(start),
        section=section,
    )


def _compute_totals(
    outline: DocumentOutline,
    sections_total: int,
    hops: list[SourceHop],
    covered: dict[str, set[str]],
    index: DocumentIndex,
) -> SourceTotals:
    every = set().union(*covered.values()) if covered else set()
    return SourceTotals(
        mode=outline.mode,
        rounds=len(hops),
        sections_read=len({hop.node_ref for hop in hops if hop.node_ref}),
        sections_total=sections_total,
        tokens_read=_compute_cost(index, every),
        tokens_total=outline.total_est_tokens,
    )


class _Trail:
    """The status and the hops reaching each outline node, strongest status
    winning — then the nodes to draw, ancestors included."""

    def __init__(self) -> None:
        self.status: dict[str, str] = {}
        self.reached: dict[str, list[str]] = {}

    def mark(self, node_ref: str | None, state: str, hop_id: str | None) -> None:
        if node_ref is None:
            return
        self.status[node_ref] = _pick_stronger(self.status.get(node_ref), state)
        ids = self.reached.setdefault(node_ref, [])
        if hop_id and hop_id not in ids:
            ids.append(hop_id)

    def build_nodes(self, flat: list[tuple[OutlineNode, list[str]]]) -> list[SourceNode]:
        keep = set(self.status)
        for node, ancestors in flat:
            if node.ref in self.status:
                keep.update(ancestors)
        return [
            SourceNode(
                ref=node.ref,
                uri=node.uri,
                title=node.title,
                kind=node.kind,
                level=node.level,
                status=self.status.get(node.ref, STATUS_PATH),
                est_tokens=node.est_tokens,
                page=node.page,
                hop_ids=self.reached.get(node.ref, []),
            )
            for node, _ in flat
            if node.ref in keep
        ]


def _build_hops(
    reads: list[SourceRead],
    index: DocumentIndex,
    published: dict[str, OutlineNode],
    locate: Callable[[str], str | None],
) -> tuple[list[SourceHop], dict[str, set[str]]]:
    """One hop per distinct ref read, in the order the agent read them.

    A ref read twice — a cursor resuming a long section — is one round: its
    first `why` explains going there, its last `found` says what it gave.
    """
    hops: list[SourceHop] = []
    covered: dict[str, set[str]] = {}
    seen: dict[str, int] = {}
    for read in reads:
        if read.ref in seen:
            if read.found:
                at = seen[read.ref]
                hops[at] = replace(hops[at], found=read.found)
            continue
        seen[read.ref] = len(hops)
        node_ref = locate(read.ref)
        node = published.get(node_ref) if node_ref else None
        hop, refs = _build_hop(read, len(hops) + 1, index, node)
        covered[hop.hop_id] = refs
        hops.append(hop)
    return hops, covered


def _build_hop(
    read: SourceRead, ordinal: int, index: DocumentIndex, node: OutlineNode | None
) -> tuple[SourceHop, set[str]]:
    """The hop for one read, landing on `node`, with the refs its read covered."""
    ordered = list_section_refs(index, read.ref) or [read.ref]
    refs = set(ordered)
    hop = SourceHop(
        hop_id=f"h{ordinal}",
        ordinal=ordinal,
        ref=read.ref,
        uri=read.uri,
        title=node.title if node else read.ref,
        why=read.why,
        found=read.found,
        est_tokens=_compute_cost(index, refs),
        node_ref=node.ref if node else None,
        page=index.page_of.get(get_span_start(read.ref)) or (node.page if node else None),
        regions=collect_regions(index, ordered),
    )
    return hop, refs


def _find_covering_hop(
    ref: str, hops: list[SourceHop], covered: dict[str, set[str]]
) -> SourceHop | None:
    """The first hop whose read covered `ref` — where the quote was read."""
    for hop in hops:
        if ref in covered[hop.hop_id] or ref == hop.ref:
            return hop
    return None


def _compute_cost(index: DocumentIndex, refs: set[str]) -> int:
    return sum(read_cost(read_element_text(index, ref)) for ref in refs)


def _pick_stronger(current: str | None, candidate: str) -> str:
    if current is None:
        return candidate
    return candidate if _RANK[candidate] > _RANK[current] else current

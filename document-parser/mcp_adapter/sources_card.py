"""The path card `show_sources` renders in (#363), built from a source report.

The card shows where an answer came from: the sections the agent read, in
reading order, each boxed on its pages; the passages it quoted, each with its
quote checked again by the server; and what the reading cost against the
whole document. The boxes travel as fractions of the page, so the card lays
them over a page raster of any size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.anchors import DocumentAnchor
from mcp_adapter.wire import neutralise

if TYPE_CHECKING:
    from domain.page_regions import PageRegion
    from domain.source_bar import SourceSegment
    from domain.source_map import SourceHop, SourceNode, SourcePassage, SourceTotals
    from services.source_service import SourceReport


@dataclass(frozen=True)
class RegionOut:
    """A block of a page: `box` is `[left, top, right, bottom]`, fractions of
    the page from its top-left corner."""

    page: int
    box: list[float]


@dataclass(frozen=True)
class PassageOut:
    """One cited passage. `status` is the server's word on `quote` (a
    `verify_citation` status), absent when no quote came with the anchor.
    `marks` are the lines the quote covers, found in the PDF's text layer;
    `regions` the blocks of its element, drawn when `marks` is empty."""

    uri: str
    ref: str
    quote: str
    status: str | None
    regions: list[RegionOut]
    hop_id: str | None = None
    page: int | None = None
    deep_link: str | None = None
    section: str = ""
    marks: list[RegionOut] = field(default_factory=list)


@dataclass(frozen=True)
class SourceHopOut:
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
    deep_link: str | None = None
    regions: list[RegionOut] = field(default_factory=list)


@dataclass(frozen=True)
class SourceNodeOut:
    ref: str
    uri: str
    title: str
    kind: str
    level: int
    status: str
    est_tokens: int = 0
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)
    deep_link: str | None = None


@dataclass(frozen=True)
class SourceSegmentOut:
    ref: str
    title: str
    level: int
    tokens: int
    status: str
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceTotalsOut:
    mode: str
    rounds: int
    max_rounds: int
    over_cap: bool
    sections_read: int
    sections_total: int
    tokens_read: int
    tokens_total: int
    percent: float


@dataclass(frozen=True)
class SourcesCard:
    """Where an answer came from, for the card and for a host without one.

    `hops` is the reading order — one per round of the loop, each with its
    `why`, what it `found` and where it sits on its pages — `passages` the
    quotes cited, `map` the same reads placed on the outline (status `cited`,
    `read`, or `path` for an ancestor), `summary` the one line a reader
    quotes. `unknown` lists every anchor that resolved to nothing — shown,
    never silently dropped.
    """

    document_id: str
    version_id: str
    filename: str
    question: str
    summary: str
    totals: SourceTotalsOut
    hops: list[SourceHopOut]
    map: list[SourceNodeOut]
    segments: list[SourceSegmentOut] = field(default_factory=list)
    passages: list[PassageOut] = field(default_factory=list)
    page_count: int | None = None
    unknown: list[str] = field(default_factory=list)
    next_step: str = ""
    # The document's title as the parse found it, else its filename.
    title: str = ""


def build_sources_card(report: SourceReport) -> SourcesCard:
    sources, links = report.sources, report.deep_links
    return SourcesCard(
        document_id=report.document_id,
        version_id=report.version_id,
        filename=neutralise(report.filename),
        question=neutralise(report.question),
        summary=_build_summary(sources.totals, report.max_rounds),
        totals=_to_totals_out(sources.totals, report.max_rounds),
        hops=[_to_hop_out(hop, links) for hop in sources.hops],
        map=[_to_node_out(node, links) for node in sources.nodes],
        segments=[_to_segment_out(s) for s in sources.segments],
        passages=[_to_passage_out(p, links) for p in sources.passages],
        page_count=report.page_count,
        title=neutralise(report.title or report.filename),
        unknown=list(report.unknown),
        next_step=(
            "If no card appeared, relay this tree and each `deep_link`, which opens the "
            "passage in Docling Studio."
        ),
    )


def _build_summary(totals: SourceTotals, cap: int) -> str:
    unit = "pages" if totals.mode == "pages" else "sections"
    rounds = (
        f"{totals.rounds} rounds, over the {cap}-round cap"
        if totals.rounds > cap
        else f"{totals.rounds} of {cap} rounds"
    )
    return (
        f"{rounds} · read {totals.sections_read} of {totals.sections_total} {unit} — "
        f"~{totals.tokens_read:,} of {totals.tokens_total:,} tokens ({totals.percent:g} %)."
    )


def _to_totals_out(totals: SourceTotals, cap: int) -> SourceTotalsOut:
    return SourceTotalsOut(
        mode=totals.mode,
        rounds=totals.rounds,
        max_rounds=cap,
        over_cap=totals.rounds > cap,
        sections_read=totals.sections_read,
        sections_total=totals.sections_total,
        tokens_read=totals.tokens_read,
        tokens_total=totals.tokens_total,
        percent=totals.percent,
    )


def _to_segment_out(segment: SourceSegment) -> SourceSegmentOut:
    return SourceSegmentOut(
        ref=segment.ref,
        title=neutralise(segment.title),
        level=segment.level,
        tokens=segment.tokens,
        status=segment.status,
        page=segment.page,
        hop_ids=list(segment.hop_ids),
    )


def _to_hop_out(hop: SourceHop, links: dict[str, str]) -> SourceHopOut:
    cited_link = next((links.get(DocumentAnchor.parse(u).ref) for u in hop.cited), None)
    return SourceHopOut(
        hop_id=hop.hop_id,
        ordinal=hop.ordinal,
        ref=hop.ref,
        uri=hop.uri,
        title=neutralise(hop.title),
        why=neutralise(hop.why),
        est_tokens=hop.est_tokens,
        found=neutralise(hop.found),
        node_ref=hop.node_ref,
        page=hop.page,
        cited=list(hop.cited),
        deep_link=cited_link or links.get(hop.node_ref or hop.ref),
        regions=_to_regions_out(hop.regions),
    )


def _to_passage_out(passage: SourcePassage, links: dict[str, str]) -> PassageOut:
    return PassageOut(
        uri=passage.uri,
        ref=passage.ref,
        quote=neutralise(passage.quote),
        status=passage.status,
        regions=_to_regions_out(passage.regions),
        hop_id=passage.hop_id,
        page=passage.page,
        deep_link=links.get(passage.ref),
        section=neutralise(passage.section),
        marks=_to_regions_out(passage.marks),
    )


def _to_regions_out(regions: list[PageRegion]) -> list[RegionOut]:
    # Four places: a ten-thousandth of a page is under a pixel on any screen.
    return [
        RegionOut(
            page=r.page,
            box=[round(r.left, 4), round(r.top, 4), round(r.right, 4), round(r.bottom, 4)],
        )
        for r in regions
    ]


def _to_node_out(node: SourceNode, links: dict[str, str]) -> SourceNodeOut:
    return SourceNodeOut(
        ref=node.ref,
        uri=node.uri,
        title=neutralise(node.title),
        kind=node.kind,
        level=node.level,
        status=node.status,
        est_tokens=node.est_tokens,
        page=node.page,
        hop_ids=list(node.hop_ids),
        deep_link=links.get(node.ref),
    )

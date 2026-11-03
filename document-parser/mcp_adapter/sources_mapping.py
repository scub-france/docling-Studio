"""A `SourceReport`, in the shape the sources card publishes (#363).

The translation half of `sources_wire.py`, kept apart from it as
`wire_mapping.py` is from `wire.py`. Every document-derived string passes
through `neutralise` on the way out, titles and quotes included.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.anchors import DocumentAnchor
from mcp_adapter.sources_wire import (
    PassageOut,
    RegionOut,
    SourceHopOut,
    SourceNodeOut,
    SourcesCard,
    SourceSegmentOut,
    SourceTotalsOut,
)
from mcp_adapter.wire import neutralise

if TYPE_CHECKING:
    from domain.page_regions import PageRegion
    from domain.source_map import SourceHop, SourceNode, SourcePassage
    from services.source_service import SourceReport


def sources_card(report: SourceReport) -> SourcesCard:
    sources, links = report.sources, report.deep_links
    totals, cap = sources.totals, report.max_rounds
    unit = "pages" if totals.mode == "pages" else "sections"
    rounds = (
        f"{totals.rounds} rounds, over the {cap}-round cap"
        if totals.rounds > cap
        else f"{totals.rounds} of {cap} rounds"
    )
    summary = (
        f"{rounds} · read {totals.sections_read} of {totals.sections_total} {unit} — "
        f"~{totals.tokens_read:,} of {totals.tokens_total:,} tokens ({totals.percent:g} %)."
    )
    return SourcesCard(
        document_id=report.document_id,
        version_id=report.version_id,
        filename=neutralise(report.filename),
        question=neutralise(report.question),
        summary=summary,
        totals=SourceTotalsOut(
            mode=totals.mode,
            rounds=totals.rounds,
            max_rounds=cap,
            over_cap=totals.rounds > cap,
            sections_read=totals.sections_read,
            sections_total=totals.sections_total,
            tokens_read=totals.tokens_read,
            tokens_total=totals.tokens_total,
            percent=totals.percent,
        ),
        hops=[_hop(hop, links) for hop in sources.hops],
        map=[_node(node, links) for node in sources.nodes],
        segments=[
            SourceSegmentOut(
                ref=s.ref,
                title=neutralise(s.title),
                level=s.level,
                tokens=s.tokens,
                status=s.status,
                page=s.page,
                hop_ids=list(s.hop_ids),
            )
            for s in sources.segments
        ],
        passages=[_passage(p, links) for p in sources.passages],
        page_count=report.page_count,
        title=neutralise(report.title or report.filename),
        unknown=list(report.unknown),
        next_step=(
            "If no card appeared, relay this tree and each `deep_link`, which opens the "
            "passage in Docling Studio."
        ),
    )


def _hop(hop: SourceHop, links: dict[str, str]) -> SourceHopOut:
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
        regions=_regions(hop.regions),
    )


def _passage(passage: SourcePassage, links: dict[str, str]) -> PassageOut:
    return PassageOut(
        uri=passage.uri,
        ref=passage.ref,
        quote=neutralise(passage.quote),
        status=passage.status,
        regions=_regions(passage.regions),
        hop_id=passage.hop_id,
        page=passage.page,
        deep_link=links.get(passage.ref),
        section=neutralise(passage.section),
        marks=_regions(passage.marks),
    )


def _regions(regions: list[PageRegion]) -> list[RegionOut]:
    # Four places: a ten-thousandth of a page is under a pixel on any screen.
    return [
        RegionOut(
            page=r.page,
            box=[round(r.left, 4), round(r.top, 4), round(r.right, 4), round(r.bottom, 4)],
        )
        for r in regions
    ]


def _node(node: SourceNode, links: dict[str, str]) -> SourceNodeOut:
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

"""`show_sources` and the path card it renders in (#363).

The card shows where an answer came from: the sections the agent read, in
reading order, each with its page; the passages it quoted, boxed on those
pages; and what the reading cost against the whole document. Same template
and same page tool the investigation card used — only its source changed,
from a journal the agent had to keep to the anchors it already holds.

A host without MCP Apps gets the same record as a short text tree, built
here rather than left to the SDK's pretty-printed JSON: that text is what a
model reads on such a host, and a tree is what a reader asks it to relay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import TypeAdapter

from domain.anchors import AnchorParseError, DocumentAnchor
from mcp_adapter.page_image import CitationImageOut, image_out
from mcp_adapter.wire import neutralise
from services.navigation_errors import NavigationServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.apps import Apps

    from domain.source_map import SourceHop, SourceNode
    from services.document_tools import DocumentTools
    from services.source_service import SourceReport

SOURCES_APP_HTML = (Path(__file__).parent / "sources_app.html").read_text(encoding="utf-8")


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
    `why` and what it `found` — `map` the same reads placed on the outline
    (status `cited`, `read`, or `path` for an ancestor), `summary` the one
    line a reader quotes. `unknown` lists every anchor that resolved to
    nothing — shown, never silently dropped.
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
    unknown: list[str] = field(default_factory=list)
    next_step: str = ""


_CARD = TypeAdapter(SourcesCard)

_DESCRIPTION = (
    "End the answer with where it came from, as one card. `read`: one entry per round, "
    "in order: the read_element `uri`, a one-line `why`, what it `found`. `cited`: the "
    "verified anchors."
)


def register_sources_view(apps: Apps, tools: Callable[[], DocumentTools], uri: str) -> None:
    """Publish `show_sources` and the card's own page tool, bound to `uri`."""

    @apps.tool(
        resource_uri=uri,
        visibility=["model"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=_DESCRIPTION,
    )
    async def show_sources(
        question: str,
        read: list[dict[str, str]],
        cited: list[str] | None = None,
    ) -> Annotated[CallToolResult, SourcesCard]:
        reads = [
            (str(e.get("uri") or ""), str(e.get("why") or ""), str(e.get("found") or ""))
            for e in read
        ]
        try:
            report = await tools().sources.show(question, reads, cited or [])
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc
        card = sources_card(report)
        return CallToolResult(
            content=[TextContent(type="text", text=sources_text(card))],
            structured_content=_CARD.dump_python(card, mode="json"),
        )

    @apps.tool(
        resource_uri=uri,
        # App-only, like `get_citation_image`, and bound to this card's own
        # resource: a host may scope an app's calls to the tools its template
        # declares, so the path fetches through a tool that is plainly its.
        visibility=["app"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description="Internal to the sources card: a page image as a data URI. Not for reading.",
    )
    async def get_source_page(
        uri: str, max_width: int = 240, page: int | None = None
    ) -> CitationImageOut:
        try:
            image = await tools().images.render_page(
                uri, max_width=max(120, min(max_width, 1600)), page=page
            )
        except (AnchorParseError, NavigationServiceError) as exc:
            raise ToolError(str(exc)) from exc
        return image_out(image)


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
    )


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


def sources_text(card: SourcesCard) -> str:
    """The card as a tree a text-only host can relay as is."""
    lines = [f"Sources — {card.question}", f"{card.filename}: {card.summary}", ""]
    lines.append("Rounds:")
    cap = card.totals.max_rounds
    for hop in card.hops:
        page = f", p.{hop.page}" if hop.page else ""
        why = f" — {hop.why}" if hop.why else ""
        lines.append(f"{hop.ordinal}/{cap}. {hop.title}{page} (~{hop.est_tokens:,} t){why}")
        if hop.found:
            lines.append(f"   found: {hop.found}")
        for uri in hop.cited:
            lines.append(f"   cited {DocumentAnchor.parse(uri).ref}")
        if hop.deep_link:
            lines.append(f"   open in Studio: {hop.deep_link}")
    lines += ["", "On the map:"]
    lines += [f"{'  ' * max(0, n.level - 1)}- {n.title} [{n.status}]" for n in card.map]
    if card.unknown:
        lines += ["", "Unknown anchors (not shown): " + ", ".join(card.unknown)]
    return "\n".join(lines)

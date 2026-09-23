"""MCP Apps extension — the two viewers (`io.modelcontextprotocol/ui`).

`show_citation` shows one passage on its page; `show_investigation` (#329)
shows a whole recorded investigation — the steps, the verdict on every ref
tried, and the navigation tree those verdicts draw on the document. Each is
bound to one predeclared `ui://` template. That shape is the spec's, not a
preference: SEP-1865 models UI as a *static* resource the host fetches once
and caches, with the tool result pushed into the sandboxed iframe afterwards.
So there is one HTML document per view and no HTML generated per result.

Why this view first: `verify_citation` answers "is this quote really in the
document" with a boolean, which is exactly the kind of claim a reader wants to
check with their own eyes. Showing the pixels the quote was lifted from is the
one thing text cannot do — and among the 26 published MCP Apps examples, no
citation view exists.

Degradation is a spec requirement (SEP-2133) and it is the reason this costs
nothing to ship: a host that never advertises the extension never fetches the
template, and both tools return the same text-only payload they would have
returned anyway. Claude Code sees exactly what it sees today —
`show_investigation` degrades to precisely what `get_investigation` returns,
which is why it carries no extra field a reader could only see rendered.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.apps import Apps, ResourcePermissions
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from domain.anchors import AnchorParseError
from domain.investigation import AttemptOutcome, StepState, step_tally
from domain.navigation import estimate_tokens
from mcp_adapter.investigation_wire import (
    MapEntry,
    TraceStep,
    map_entries,
    trace_steps,
)
from mcp_adapter.wire import neutralise
from services.navigation_errors import NavigationServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.document_tools import DocumentTools


def _versioned_uri(name: str, html: str) -> str:
    """The template's uri carries a hash of its content.

    SEP-1865 says a host fetches a `ui://` resource once and caches it, and a
    live host took that literally: across three server restarts it never
    fetched the template again — its MCP session (a long-lived proxy) outlives
    the server, so a redeployed card rendered with last session's markup,
    indefinitely. Versioning the uri is the spec-shaped answer: a changed
    template is a *different resource*, one the host has never seen, so the
    fetch-once rule works for it instead of against it. Staleness is then
    bounded by the tools/list cache (`MCP_CACHE_TTL_SECONDS`), not by how
    long the host keeps a session open.
    """
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]
    return f"ui://docling-studio/{name}.{digest}.html"


CITATION_APP_HTML = (Path(__file__).parent / "citation_app.html").read_text(encoding="utf-8")
CITATION_APP_URI = _versioned_uri("citation", CITATION_APP_HTML)

INVESTIGATION_APP_HTML = (Path(__file__).parent / "investigation_app.html").read_text(
    encoding="utf-8"
)
INVESTIGATION_APP_URI = _versioned_uri("investigation", INVESTIGATION_APP_HTML)


@dataclass(frozen=True)
class CitationImageOut:
    """A raster for the viewer, never for the model.

    `highlight` is the cited passage's box **in this image's own pixels** —
    the renderer knows the dpi it settled on, so the view draws a rectangle
    instead of converting page points. Present on a page thumbnail, absent on
    a crop, which is already the passage.
    """

    data_uri: str
    media_type: str
    width: int
    height: int
    page: int
    bytes: int
    highlight: list[int] | None = None
    page_count: int | None = None


@dataclass(frozen=True)
class CitationView:
    """What the viewer renders — and what a text-only host reads instead.

    `label`, `document_id`, `version_id` and `quote_hash` are the provenance
    the anchor already encodes, unpacked so the viewer does not have to parse
    a `dstudio://` uri to show where a passage comes from. `label` also drives
    the element-type swatch, which uses the Studio palette
    (`frontend/src/shared/elementColors.ts`) so a table reads as a table on
    both surfaces.

    `est_tokens` is what the quote costs a reader's context, measured by the
    same `estimate_tokens` that prices `get_outline` entries and `read_element`
    excerpts — one estimator across the surface, so the numbers on a card and
    in a map can be compared. Like those, it is the ~4-chars-per-token
    heuristic applied to the text alone: it prices neither the JSON envelope
    nor the image.

    The page image is not here: the viewer fetches it through
    `get_citation_image`, so the model never pays for a raster it cannot read.
    """

    uri: str
    ref: str
    label: str
    document_id: str
    version_id: str
    quote: str
    quote_hash: str
    est_tokens: int
    page: int | None
    headings: list[str]
    deep_link: str | None = None
    next_step: str | None = None


@dataclass(frozen=True)
class InvestigationCard:
    """A whole investigation, for the viewer and for a host without one.

    Field for field the same record `get_investigation` returns — same
    `reasoning`, same `map`, same mappers — plus the three numbers a card
    states and prose would have to recount: the step tally and the attempt
    budget each step was allowed. A viewer that showed
    something the text payload does not carry would be a second account of
    the investigation, and the two would drift.

    `max_attempts_per_step` is what lets the card draw a budget rather than a
    count: three marks with none of them kept says the document did not
    answer, which a bare "3 attempts" does not.
    """

    investigation_id: str
    document_id: str
    version_id: str
    filename: str
    question: str
    state: str
    stale: bool
    reasoning: list[TraceStep]
    map: list[MapEntry]
    steps_answered: int
    steps_unanswered: int
    steps_pending: int
    attempts_kept: int
    max_attempts_per_step: int
    answer: str | None = None


# What to do when the card does not appear. Phrased to hold whether or not a
# viewer mounted: the server has no way to know.
_NO_CARD = (
    "The page image is not in this payload — the citation viewer fetches it itself. If no "
    "card appeared for the reader, this host does not render one: give them `deep_link`, "
    "which opens this passage in Docling Studio at the right page. Do not call "
    "get_citation_image — it answers with binary you cannot read."
)


def build_apps_extension(
    tools: Callable[[], DocumentTools],
    *,
    investigations: bool = True,
) -> Apps:
    """Build the Apps extension over the same lazily-resolved service.

    `investigations` follows `MCP_INVESTIGATION_ENABLED`: a viewer for a
    record the server does not keep would be a tool that always errors.
    """
    apps = Apps()

    # One sentence more when the journal is on: `show_citation`'s "prefer it
    # whenever someone asks to see a passage" is right for ad-hoc reading and
    # wrong at the end of an investigation, where it produced a card per kept
    # anchor instead of the one card that shows the record. The carve-out is
    # conditional because it names `show_investigation`, and a description
    # pointing at a tool this server did not publish would be a trap.
    citation_description = (
        "Show a citation where it lives: the region of the page it was lifted "
        "from, rendered as an image, next to its verbatim text. verify_citation "
        "answers whether a quote is real; this one lets the reader see that it "
        "is. Prefer it whenever the citation itself is the point — a figure, a "
        "table, a number, a date, a clause, a contested wording — and whenever "
        "someone asks to see, check or point at a passage. It carries a raster "
        "of the page, so it costs more than a text citation: for ordinary "
        "explanatory prose, quote the text instead. Takes the uri of a citation "
        "returned by read_element — `citations[].uri` for one element, or "
        "`span_uri` for a passage running across several. On a host that cannot "
        "display it, it returns the same citation as text."
    ) + (
        " To display an investigation's findings, end with show_investigation "
        "instead — one card carries the whole record — and keep this for the "
        "single passage that is itself in dispute."
        if investigations
        else ""
    )

    @apps.tool(
        resource_uri=CITATION_APP_URI,
        # The model addresses this tool; the app never calls back into it.
        # Anything reachable from inside an iframe is reachable by script
        # injected through a document, so the surface stays as small as the
        # view actually needs.
        visibility=["model"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=citation_description,
    )
    async def show_citation(uri: str) -> CitationView:
        # `get_citation` is the named use case for "what does this anchor
        # point at": no quote to check, just the citation.
        try:
            citation = await tools().citations.get_citation(uri)
        except AnchorParseError as exc:
            raise ToolError(str(exc)) from exc
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc
        return CitationView(
            uri=citation.uri,
            ref=citation.ref,
            label=citation.label,
            document_id=citation.document_id,
            version_id=citation.version_id,
            quote=neutralise(citation.quote),
            quote_hash=citation.quote_hash,
            est_tokens=estimate_tokens(citation.quote),
            page=citation.page,
            headings=[neutralise(h) for h in citation.headings],
            deep_link=citation.deep_link,
            next_step=_NO_CARD,
        )

    @apps.tool(
        resource_uri=CITATION_APP_URI,
        # App-only: the model is never offered this tool, because its answer is
        # a base64 raster it cannot read and would pay for by the token.
        visibility=["app"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=(
            "Internal — the citation viewer's own page fetch: a raster of the page a "
            "cited passage sits on, sized by `max_width`, with the passage's box in "
            "the image's own pixels, as a data URI. Not for reading."
        ),
    )
    async def get_citation_image(uri: str, max_width: int = 320) -> CitationImageOut:
        # App-only (`visibility: ["app"]`): the spec requires a host to keep it
        # out of the agent's tool list. The SDK adds no server-side filter, so
        # on a host that ignores it the worst case is a wasteful read-only call.
        # Clamped so a caller cannot ask for a raster nobody can use: the dpi
        # ladder bounds the bytes, this bounds the work.
        try:
            image = await tools().images.render_page(uri, max_width=max(120, min(max_width, 1600)))
        except AnchorParseError as exc:
            raise ToolError(str(exc)) from exc
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc
        return CitationImageOut(
            data_uri=image.data_uri,
            media_type=image.media_type,
            width=image.width,
            height=image.height,
            page=image.page,
            bytes=len(image.png),
            highlight=list(image.highlight) if image.highlight else None,
            page_count=image.page_count,
        )

    if investigations:
        _register_investigation_view(apps, tools)

    apps.add_html_resource(
        CITATION_APP_URI,
        CITATION_APP_HTML,
        title="Citation",
        description="Shows a cited passage on the page it came from.",
        prefers_border=True,
        # The view's two copy buttons write to the clipboard, which a sandboxed
        # iframe cannot do unless the host is asked for it: without this,
        # `navigator.clipboard` is either absent or rejects, and the buttons
        # look broken rather than blocked.
        permissions=ResourcePermissions(clipboard_write={}),
        # No `csp=`: the default policy already allows `img-src data:`, which
        # is all this view loads. Declaring a domain would mean the image
        # travels as a URL — and then the view only works while the Studio
        # backend is reachable from the host, which it is not over stdio.
    )
    if investigations:
        apps.add_html_resource(
            INVESTIGATION_APP_URI,
            INVESTIGATION_APP_HTML,
            title="Investigation",
            description="Shows what an agent tried in a document, and what held up.",
            prefers_border=True,
            # No clipboard permission and no `csp=`: the default policy already
            # allows `img-src data:`, which is all the path view's thumbnails
            # need. The record renders the tool result it was handed; only the
            # path tab fetches, through `get_investigation_page`, and only when
            # opened.
        )
    return apps


def _register_investigation_view(apps: Apps, tools: Callable[[], DocumentTools]) -> None:
    """Publish the investigation viewer.

    Split out so the flag guards the *registration* rather than the handler:
    a tool that exists and always errors is worse than one that is absent,
    because a model reads the description before it learns otherwise.
    """

    @apps.tool(
        resource_uri=INVESTIGATION_APP_URI,
        visibility=["model"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=(
            "Show a recorded investigation: the steps, every ref tried with the "
            "server's verdict on it, and the navigation tree those verdicts draw on "
            "the document. This is the view to end an investigation with — prefer it "
            "over show_citation there, and decisively: a citation card shows one "
            "passage that held up, and cannot show the steps, the refs that did not, "
            "or the parts the document did not answer. Reach for show_citation "
            "afterwards, for the one passage that is itself in dispute. It returns the "
            "same record as get_investigation, so call one or the other, not both. On a "
            "host that cannot render it, that record is the answer."
        ),
    )
    async def show_investigation(investigation_id: str) -> InvestigationCard:
        try:
            report = await tools().investigations.view(investigation_id)
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc

        investigation = report.investigation
        tally = step_tally(investigation)
        return InvestigationCard(
            investigation_id=investigation.id,
            document_id=investigation.document_id,
            version_id=investigation.version_id,
            filename=neutralise(report.filename),
            question=neutralise(investigation.question),
            state=str(investigation.state),
            stale=investigation.stale,
            reasoning=trace_steps(investigation),
            map=map_entries(report.map),
            steps_answered=tally[StepState.ANSWERED],
            steps_unanswered=tally[StepState.UNANSWERED],
            steps_pending=tally[StepState.PENDING],
            attempts_kept=sum(
                1
                for step in investigation.steps
                for attempt in step.attempts
                if attempt.outcome is AttemptOutcome.KEPT
            ),
            max_attempts_per_step=tools().investigations.config.max_attempts_per_step,
            answer=neutralise(investigation.answer) if investigation.answer else None,
        )

    @apps.tool(
        resource_uri=INVESTIGATION_APP_URI,
        # App-only, like `get_citation_image`, and bound to this view's own
        # resource: a host is free to scope an app's calls to the tools its
        # template declares, so the path view fetches through a tool that is
        # unambiguously its.
        visibility=["app"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=(
            "Internal — the investigation viewer's own page fetch. Returns a "
            "raster of a page of the document a kept ref pins, sized by "
            "`max_width` — the path tab's thumbnail, its enlarged reading view, "
            "and (via `page`) any other page when the reader leafs through — "
            "with the passage's box, on its own page only, in the image's own "
            "pixels, as a data URI. Not for reading: it answers with binary, and "
            "show_investigation already carries everything a reader needs."
        ),
    )
    async def get_investigation_page(
        uri: str, max_width: int = 240, page: int | None = None
    ) -> CitationImageOut:
        # Same clamp as `get_citation_image(kind='page')`: the dpi ladder
        # bounds the bytes, this bounds the work.
        try:
            image = await tools().images.render_page(
                uri, max_width=max(120, min(max_width, 1600)), page=page
            )
        except AnchorParseError as exc:
            raise ToolError(str(exc)) from exc
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc
        return CitationImageOut(
            data_uri=image.data_uri,
            media_type=image.media_type,
            width=image.width,
            height=image.height,
            page=image.page,
            bytes=len(image.png),
            highlight=list(image.highlight) if image.highlight else None,
            page_count=image.page_count,
        )

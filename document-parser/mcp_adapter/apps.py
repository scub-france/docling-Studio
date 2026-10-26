"""MCP Apps extension — the two viewers (`io.modelcontextprotocol/ui`).

`show_citation` shows one passage on its page; `show_sources` (#363) shows
where a whole answer came from — the sections read, in order, on their pages,
and the passages cited (see `sources_view`). Each is
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
template, and both tools return their record as text: `show_sources` as a
short tree a model can relay.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from mcp.server.apps import Apps, ResourcePermissions
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, ToolAnnotations

from domain.anchors import AnchorParseError
from domain.navigation import estimate_tokens
from mcp_adapter.page_image import CitationImageOut, image_out
from mcp_adapter.results import compact
from mcp_adapter.sources_view import SOURCES_APP_HTML, register_sources_view
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
    bounded by when the host next lists tools, not by how long it keeps a
    session open.
    """
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]
    return f"ui://docling-studio/{name}.{digest}.html"


CITATION_APP_HTML = (Path(__file__).parent / "citation_app.html").read_text(encoding="utf-8")
CITATION_APP_URI = _versioned_uri("citation", CITATION_APP_HTML)

SOURCES_APP_URI = _versioned_uri("sources", SOURCES_APP_HTML)


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


# What to do when the card does not appear. Phrased to hold whether or not a
# viewer mounted: the server has no way to know.
def _no_card(deep_link: str | None) -> str:
    fallback = (
        "give the reader `deep_link`, which opens it in Docling Studio"
        if deep_link
        else "quote the passage with its anchor"
    )
    return (
        f"If no card appeared, this host cannot show one: {fallback}. Do not call "
        "get_citation_image: it returns an image you cannot read."
    )


def build_apps_extension(tools: Callable[[], DocumentTools]) -> Apps:
    """Build the Apps extension — the two cards — over the same lazily-resolved
    service."""
    apps = Apps()

    citation_description = (
        "Show a citation on its page, highlighted, beside its text: for the passage that "
        "carries the answer (a figure, a number, a clause) or one the reader asks to see. "
        "`uri`: an anchor a read returned."
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
    async def show_citation(uri: str) -> Annotated[CallToolResult, CitationView]:
        # `get_citation` is the named use case for "what does this anchor
        # point at": no quote to check, just the citation.
        try:
            citation = await tools().citations.get_citation(uri)
        except AnchorParseError as exc:
            raise ToolError(str(exc)) from exc
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc
        view = CitationView(
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
            next_step=_no_card(citation.deep_link),
        )
        return compact(view)

    @apps.tool(
        resource_uri=CITATION_APP_URI,
        # App-only: the model is never offered this tool, because its answer is
        # a base64 raster it cannot read and would pay for by the token.
        visibility=["app"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=(
            "Internal to the citation viewer: a page image as a data URI. Not for reading."
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
        return image_out(image)

    register_sources_view(apps, tools, SOURCES_APP_URI)

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
    apps.add_html_resource(
        SOURCES_APP_URI,
        SOURCES_APP_HTML,
        title="Sources",
        description="Shows where an answer came from: the sections read, on their pages.",
        prefers_border=True,
        # No clipboard permission and no `csp=`: the default policy already
        # allows `img-src data:`, which is all the path's thumbnails need. The
        # card renders the tool result it was handed; only the path fetches,
        # through `get_source_page`, and only when opened.
    )
    return apps

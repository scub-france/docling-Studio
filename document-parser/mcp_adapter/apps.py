"""MCP Apps extension — the citation viewer (`io.modelcontextprotocol/ui`).

One tool, `show_citation`, bound to one predeclared `ui://` template. That
shape is the spec's, not a preference: SEP-1865 models UI as a *static*
resource the host fetches once and caches, with the tool result pushed into
the sandboxed iframe afterwards. So there is one HTML document for the view
and no HTML generated per citation.

Why this view first: `verify_citation` answers "is this quote really in the
document" with a boolean, which is exactly the kind of claim a reader wants to
check with their own eyes. Showing the pixels the quote was lifted from is the
one thing text cannot do — and among the 26 published MCP Apps examples, no
citation view exists.

Degradation is a spec requirement (SEP-2133) and it is the reason this costs
nothing to ship: a host that never advertises the extension never fetches the
template, and `show_citation` returns the same text-only payload it would have
returned anyway. Claude Code sees exactly what it sees today.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.apps import Apps, client_supports_apps

# `Context` is a runtime import: the SDK reads this annotation at registration
# time to decide whether to inject the request context, so a checker-only
# import would silently turn `ctx` into an ordinary tool argument.
from mcp.server.mcpserver import Context  # noqa: TC002
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from domain.navigation import AnchorParseError
from mcp_adapter.wire import neutralise
from services.navigation_service import NavigationServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.navigation_service import NavigationService

logger = logging.getLogger(__name__)

CITATION_APP_URI = "ui://docling-studio/citation.html"
CITATION_APP_HTML = (Path(__file__).parent / "citation_app.html").read_text(encoding="utf-8")


@dataclass(frozen=True)
class CitationView:
    """What the viewer renders — and what a text-only host reads instead.

    `page_image` is a `data:` PNG of the page region the citation points at.
    It is populated **only** for a host that negotiated MCP Apps: it is tens of
    kilobytes, and on a host that cannot render it those bytes would land in
    the model's context for nothing.
    """

    uri: str
    ref: str
    quote: str
    page: int | None
    headings: list[str]
    deep_link: str | None = None
    page_image: str | None = None
    image_note: str | None = None


def build_apps_extension(navigation: Callable[[], NavigationService]) -> Apps:
    """Build the Apps extension over the same lazily-resolved service."""
    apps = Apps()

    @apps.tool(
        resource_uri=CITATION_APP_URI,
        # The model addresses this tool; the app never calls back into it.
        # Anything reachable from inside an iframe is reachable by script
        # injected through a document, so the surface stays as small as the
        # view actually needs.
        visibility=["model"],
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        description=(
            "Show a citation where it lives: the region of the page it was lifted "
            "from, rendered as an image, next to its verbatim text. Use it when a "
            "user asks to see, check or point at a passage — verify_citation "
            "answers whether a quote is real, this shows them. Takes the uri of a "
            "citation returned by read_element. On a host that cannot display it, "
            "it returns the same citation as text."
        ),
    )
    async def show_citation(ctx: Context, uri: str, padding: int = 8) -> CitationView:
        try:
            check = await navigation().verify_citation(uri, "")
        except AnchorParseError as exc:
            raise ToolError(str(exc)) from exc
        except NavigationServiceError as exc:
            raise ToolError(str(exc)) from exc

        citation = check.citation
        if citation is None:
            raise ToolError(check.detail)

        view = CitationView(
            uri=citation.uri,
            ref=citation.ref,
            quote=neutralise(citation.quote),
            page=citation.page,
            headings=[neutralise(h) for h in citation.headings],
            deep_link=citation.deep_link,
        )

        if not client_supports_apps(ctx):
            return view

        try:
            image = await navigation().render_citation(uri, padding=padding)
        except NavigationServiceError as exc:
            # A citation without provenance, or an unreadable source file, is
            # not a failed tool call: the text is still the answer.
            return _with_note(view, str(exc))
        except Exception as exc:
            logger.exception("Citation rendering failed for %s", uri)
            return _with_note(view, f"The page could not be rendered ({exc}).")

        return _with_image(view, image.data_uri, image.page)

    apps.add_html_resource(
        CITATION_APP_URI,
        CITATION_APP_HTML,
        title="Citation",
        description="Shows a cited passage on the page it came from.",
        prefers_border=True,
        # No `csp=`: the default policy already allows `img-src data:`, which
        # is all this view loads. Declaring a domain would mean the image
        # travels as a URL — and then the view only works while the Studio
        # backend is reachable from the host, which it is not over stdio.
    )
    return apps


def _with_image(view: CitationView, data_uri: str, page: int) -> CitationView:
    from dataclasses import replace

    return replace(view, page_image=data_uri, page=view.page or page)


def _with_note(view: CitationView, note: str) -> CitationView:
    from dataclasses import replace

    return replace(view, image_note=note)

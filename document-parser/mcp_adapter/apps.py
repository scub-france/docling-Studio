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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.apps import Apps, ResourcePermissions, client_supports_apps

# `Context` is a runtime import: the SDK reads this annotation at registration
# time to decide whether to inject the request context, so a checker-only
# import would silently turn `ctx` into an ordinary tool argument.
from mcp.server.mcpserver import Context  # noqa: TC002
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from domain.anchors import AnchorParseError
from domain.navigation import estimate_tokens
from mcp_adapter.wire import neutralise
from services.navigation_errors import NavigationServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp_adapter.ledger import Ledger
    from services.document_tools import DocumentTools

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

    `image_bytes` is the page raster's size in bytes, not tokens, and is
    reported separately for that reason: how an image is priced is the host's
    business, and quoting a token figure for it would be inventing one.

    `total_est_tokens` / `total_calls` are the running tally kept by `Ledger`,
    whose scope is one server process — read its module docstring before
    presenting either number as a per-conversation figure.
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
    total_est_tokens: int = 0
    total_calls: int = 0
    deep_link: str | None = None
    page_image: str | None = None
    image_bytes: int | None = None
    image_note: str | None = None


def build_apps_extension(tools: Callable[[], DocumentTools], ledger: Ledger) -> Apps:
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
            "from, rendered as an image, next to its verbatim text. verify_citation "
            "answers whether a quote is real; this one lets the reader see that it "
            "is. Prefer it whenever the citation itself is the point — a figure, a "
            "table, a number, a date, a clause, a contested wording — and whenever "
            "someone asks to see, check or point at a passage. It carries a raster "
            "of the page, so it costs more than a text citation: for ordinary "
            "explanatory prose, quote the text instead. Takes the uri of a citation "
            "returned by read_element (`citations[].uri`). On a host that cannot "
            "display it, it returns the same citation as text."
        ),
    )
    async def show_citation(ctx: Context, uri: str, padding: int = 8) -> CitationView:
        # `get_citation` is the named use case for "what does this anchor
        # point at". This used to call `verify_citation(uri, "")` and harvest
        # the citation off its rejection branch — a dependency on the shape of
        # an error path, which tightening that path would have broken.
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
        )

        # Price this citation into the tally first, then read it back, so the
        # figure the card shows includes the call the card is showing.
        ledger.record(view)
        usage = ledger.snapshot()
        view = replace(view, total_est_tokens=usage.est_tokens, total_calls=usage.calls)

        if not client_supports_apps(ctx):
            return view

        try:
            image = await tools().images.render(uri, padding=padding)
        except NavigationServiceError as exc:
            # A citation without provenance, or an unreadable source file, is
            # not a failed tool call: the text is still the answer.
            return _with_note(view, str(exc))
        except Exception as exc:
            logger.exception("Citation rendering failed for %s", uri)
            return _with_note(view, f"The page could not be rendered ({exc}).")

        return _with_image(view, image.data_uri, image.page, len(image.png))

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
    return apps


def _with_image(view: CitationView, data_uri: str, page: int, png_bytes: int) -> CitationView:
    # The raster's own size, not the base64 it travels as: the encoding is a
    # transport detail, the pixels are what was actually produced.
    return replace(view, page_image=data_uri, page=view.page or page, image_bytes=png_bytes)


def _with_note(view: CitationView, note: str) -> CitationView:
    return replace(view, image_note=note)

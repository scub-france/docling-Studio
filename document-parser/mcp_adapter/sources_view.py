"""`show_sources` and the path card it renders in (#363).

The card shows where an answer came from: the sections the agent read, in
reading order, each boxed on its pages; the passages it quoted, each with its
quote checked again by the server; and what the reading cost against the
whole document.

This module registers the two tools and nothing else. The contract they
return is `sources_wire`, the translation from the service's report
`sources_mapping`, and the text tree a host without MCP Apps gets instead of
the card `sources_text`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import TypeAdapter

from domain.anchors import AnchorParseError
from mcp_adapter.page_image import CitationImageOut, image_out
from mcp_adapter.sources_mapping import sources_card
from mcp_adapter.sources_text import sources_text
from mcp_adapter.sources_wire import SourcesCard
from services.navigation_errors import NavigationServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.apps import Apps

    from services.document_tools import DocumentTools

SOURCES_APP_HTML = (Path(__file__).parent / "sources_app.html").read_text(encoding="utf-8")

_CARD = TypeAdapter(SourcesCard)

_DESCRIPTION = (
    "End the answer with its sources, as one card. `read`: one entry per round, in order: "
    "the read_element `uri`, a one-line `why`, what it `found`. `cited`: each verified "
    "quote as `{uri, quote}`."
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
        cited: list[dict[str, str] | str] | None = None,
    ) -> Annotated[CallToolResult, SourcesCard]:
        reads = [
            (str(e.get("uri") or ""), str(e.get("why") or ""), str(e.get("found") or ""))
            for e in read
        ]
        try:
            report = await tools().sources.show(question, reads, _citations(cited or []))
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


def _citations(cited: list[dict[str, str] | str]) -> list[tuple[str, str]]:
    """`(uri, quote)` pairs. A bare anchor is still taken — the shape before
    quotes travelled with it — and shows as cited, not verified."""
    return [
        (entry, "")
        if isinstance(entry, str)
        else (str(entry.get("uri") or ""), str(entry.get("quote") or ""))
        for entry in cited
    ]

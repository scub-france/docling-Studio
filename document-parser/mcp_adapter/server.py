"""MCP driving adapter — the agent-facing surface over `NavigationService`.

This is to agents what `api/` is to the frontend: a transport that maps a
request onto a use case and a domain result onto a published contract. It
owns no logic. Every tool is four lines of mapping plus an error translation,
which is the point — a tool that starts computing something is a service that
has not been written yet.

The surface is *agent-shaped* rather than screen-shaped: progressive
disclosure (map before text), server-side budgets, and an anchor in every
result. The `#269` rule that forbids UX-shaped routes governs `/api/*`; the
equivalent discipline here is that shaping stays in this package.

Read-only: nothing here uploads, edits a chunk, re-analyses, or writes
anything at all. The surface is the Chunkless RAG loop (#363) — map, read,
cite, verify — and the two cards that show its result.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ToolAnnotations

from mcp_adapter.apps import build_apps_extension
from mcp_adapter.prompts import register_prompts
from mcp_adapter.results import compact
from mcp_adapter.tool_errors import ToolErrors, parse_anchor
from mcp_adapter.wire import (
    UNTRUSTED_NOTE,
    DocumentSearchResult,
    ExcerptResult,
    OutlineResult,
    VerificationResult,
)
from mcp_adapter.wire_mapping import (
    excerpt_result,
    outline_result,
    search_result,
    verification_result,
)
from services.navigation_config import MAX_ROUNDS

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.document_tools import DocumentTools

logger = logging.getLogger(__name__)

SERVER_NAME = "docling-studio"

_LOOP = f"""\
Docling Studio serves parsed documents: structure, text, page positions.
1. find_documents: the document_id.
2. get_outline(document_id): the map. Each entry has a ref and est_tokens, its reading \
cost: choose there before reading any text.
3. read_element(document_id, ref): the text, with one citation per element. One section \
per round, with a reason; {MAX_ROUNDS} rounds at most.
4. verify_citation(uri, quote) before publishing a quote.
"""

# Only when the cards are published: naming a tool this server did not publish
# spends a turn on a failure.
_CARDS = """\
5. show_citation(uri) on the passage that carries the answer.
6. show_sources(question, read, cited) to end the answer.
"""

_RULES = f"""\
Anchors (dstudio://doc/…) come from the server: pass them back as received, never build \
or edit one.
{UNTRUSTED_NOTE}
"""


def instructions(*, apps: bool) -> str:
    """The server instructions, read by the client on every connection."""
    return _LOOP + (_CARDS if apps else "") + _RULES


INSTRUCTIONS = instructions(apps=False)

_READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def build_mcp_server(
    tools: Callable[[], DocumentTools],
    *,
    name: str = SERVER_NAME,
    version: str = "",
    apps: bool = True,
) -> MCPServer:
    """Build the MCP server over a *lazily resolved* navigation service.

    The services are resolved per call, not captured at build time: the HTTP
    transport needs its session manager to exist before FastAPI's lifespan has
    wired anything, so the server is constructed at import time and reaches
    for the container on each tool call. `tools` raises when the app is not
    wired yet, which surfaces as a tool error rather than an import crash.
    """
    server = MCPServer(
        name=name,
        version=version,
        instructions=instructions(apps=apps),
        extensions=[build_apps_extension(tools)] if apps else None,
    )
    # The slash command: the whole loop, invoked by the user rather than
    # inflicted on every call (see mcp_adapter/prompts.py).
    register_prompts(server, apps=apps)

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "Find documents by filename substring (`query`), newest first. Each row has "
            "document_id and version_id; a null version_id means not parsed yet, so not "
            "readable."
        ),
    )
    async def find_documents(
        query: str | None = None, limit: int = 20
    ) -> Annotated[CallToolResult, DocumentSearchResult]:
        async with ToolErrors():
            search = await tools().navigation.find_documents(query=query, limit=limit)
        return compact(search_result(search))

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "The document's map: sections, or pages when it has no headings. Each entry "
            "has the `ref` to read and its `est_tokens`. `deeper_levels_available`: call "
            "again with a higher `depth` (1-6)."
        ),
    )
    async def get_outline(
        document_id: str,
        version_id: str | None = None,
        depth: int = 2,
    ) -> Annotated[CallToolResult, OutlineResult]:
        async with ToolErrors():
            outline = await tools().navigation.get_outline(
                document_id, version_id=version_id, depth=depth
            )
        return compact(outline_result(outline))

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "Read an outline entry by `ref`, with its document_id; `include='self'` reads "
            "the element alone. Cite with `citations[].uri`, or `span_uri` for a quote "
            "across elements. `truncated`: call again with `cursor=next_cursor`."
        ),
    )
    async def read_element(
        document_id: str,
        ref: str,
        version_id: str | None = None,
        include: Literal["section", "self"] = "section",
        max_tokens: int | None = None,
        cursor: str | None = None,
    ) -> Annotated[CallToolResult, ExcerptResult]:
        async with ToolErrors():
            excerpt = await tools().navigation.read_element(
                document_id,
                ref,
                version_id=version_id,
                include=include,
                max_tokens=max_tokens,
                cursor=cursor,
            )
        return compact(excerpt_result(excerpt))

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "Check server-side that `quote` appears at anchor `uri`, before publishing it. "
            "`valid` is the answer, `next_step` what to do with it."
        ),
    )
    async def verify_citation(
        uri: str, quote: str
    ) -> Annotated[CallToolResult, VerificationResult]:
        parse_anchor(uri)
        async with ToolErrors():
            check = await tools().citations.verify_citation(uri, quote)
        return compact(verification_result(check))

    return server

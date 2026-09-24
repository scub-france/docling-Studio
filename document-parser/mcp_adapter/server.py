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

Read-only towards documents: nothing here uploads, edits a chunk or
re-analyses. The only writes are the investigation journal's own tables,
behind MCP_INVESTIGATION_ENABLED.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from mcp.server.caching import CACHEABLE_METHODS, CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from mcp_adapter.apps import build_apps_extension
from mcp_adapter.investigation_tools import (
    INSTRUCTIONS as INVESTIGATION_INSTRUCTIONS,
)
from mcp_adapter.investigation_tools import (
    register_investigation_tools,
)
from mcp_adapter.prompts import register_prompts
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

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.document_tools import DocumentTools

logger = logging.getLogger(__name__)

SERVER_NAME = "docling-studio"

INSTRUCTIONS = f"""\
Docling Studio serves parsed documents: structure, text, page positions.
1. find_documents: the document_id.
2. get_outline(document_id): the map. Each entry has a ref and est_tokens, its reading \
cost: choose there before reading any text.
3. read_element(document_id, ref): the text, with one citation per element.
4. verify_citation(uri, quote) before publishing a quote.
Anchors (dstudio://doc/…) come from the server: pass them back as received, never build \
or edit one.
{UNTRUSTED_NOTE}
"""

_READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def build_mcp_server(
    tools: Callable[[], DocumentTools],
    *,
    name: str = SERVER_NAME,
    version: str = "",
    apps: bool = True,
    cache_ttl_seconds: int = 0,
    investigations: bool = True,
) -> MCPServer:
    """Build the MCP server over a *lazily resolved* navigation service.

    The services are resolved per call, not captured at build time: the HTTP
    transport needs its session manager to exist before FastAPI's lifespan has
    wired anything, so the server is constructed at import time and reaches
    for the container on each tool call. `tools` raises when the app is not
    wired yet, which surfaces as a tool error rather than an import crash.
    """
    extensions = [build_apps_extension(tools, investigations=investigations)] if apps else None
    server = MCPServer(
        name=name,
        version=version,
        # One sentence when the journal is on, pointing at the prompt rather
        # than restating the protocol: instructions are read on every
        # connection, and a protocol belongs where it is chosen.
        instructions=INSTRUCTIONS + (INVESTIGATION_INSTRUCTIONS if investigations else ""),
        extensions=extensions,
        cache_hints=_cache_hints(cache_ttl_seconds),
    )
    # Slash commands: the thorough protocols, invoked by the user rather than
    # inflicted on every call (see mcp_adapter/prompts.py).
    register_prompts(server, investigations=investigations, apps=apps)
    if investigations:
        # #329 — the journal. Off leaves the four read-only tools of #327
        # byte-identical to what they were. `viewer` tracks `apps`: that is
        # the flag `show_investigation`'s registration follows.
        register_investigation_tools(server, tools, viewer=apps)

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "Find documents by filename substring (`query`), newest first. Each row has "
            "document_id and version_id; a null version_id means not parsed yet, so not "
            "readable."
        ),
    )
    async def find_documents(query: str | None = None, limit: int = 20) -> DocumentSearchResult:
        async with ToolErrors():
            search = await tools().navigation.find_documents(query=query, limit=limit)
        return search_result(search)

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
    ) -> OutlineResult:
        async with ToolErrors():
            outline = await tools().navigation.get_outline(
                document_id, version_id=version_id, depth=depth
            )
        return outline_result(outline)

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
    ) -> ExcerptResult:
        async with ToolErrors():
            excerpt = await tools().navigation.read_element(
                document_id,
                ref,
                version_id=version_id,
                include=include,
                max_tokens=max_tokens,
                cursor=cursor,
            )
        return excerpt_result(excerpt)

    @server.tool(
        annotations=_READ_ONLY,
        description=(
            "Check server-side that `quote` appears at anchor `uri`, before publishing it. "
            "`valid` is the answer, `next_step` what to do with it."
        ),
    )
    async def verify_citation(uri: str, quote: str) -> VerificationResult:
        parse_anchor(uri)
        async with ToolErrors():
            check = await tools().citations.verify_citation(uri, quote)
        return verification_result(check)

    return server


def _cache_hints(ttl_seconds: int) -> dict[Any, CacheHint] | None:
    """Freshness hints for the methods the protocol lets a client cache.

    Everything cacheable here is deploy-scoped and identical for every
    caller — the tool list, the prompt list, the `ui://` viewer — so the
    scope is `public` and the only real question is how long a host may hold
    a surface that a redeploy has changed underneath it.

    Note what is *not* in `CACHEABLE_METHODS`: `tools/call`. The protocol
    offers caching exactly where this server's cost is not. This amortises
    connecting, never reading.
    """
    if ttl_seconds <= 0:
        return None
    hint = CacheHint(ttl_ms=ttl_seconds * 1000, scope="public")
    return dict.fromkeys(CACHEABLE_METHODS, hint)

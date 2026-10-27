"""Mount the MCP document server on the FastAPI app (composition root).

Kept in `bootstrap/` for the same reason the rest of the wiring is: it binds
a setting to a concrete adapter and reaches across layers. `main.py` calls one
function and enters one context.

Two ordering constraints drive the shape of this module:

1. The SDK creates the streamable-HTTP session manager inside
   `streamable_http_app()`, and `session_manager.run()` must be entered by the
   *parent* app's lifespan — Starlette does not propagate lifespan into
   mounted sub-apps. So the app is built at import time and the returned
   context manager is entered by `main.lifespan`.
2. The tools therefore exist before the container is wired. They resolve the
   navigation service per call through `_navigation_from`, which raises a
   clear error if a request somehow lands before boot finished.

The returned session is single-use, like the SDK's own session manager: one
mount, one lifespan, which is how uvicorn runs an app. A test (or anything
else) that enters the same app's lifespan twice must mount again. The server
comes back with it so the admin panel can say what it publishes (#364):
`describe_mcp_server` maps it onto a domain value object, which keeps the SDK
out of the service that reports it.

The route is appended to the app's own router rather than `app.mount()`ed:
mounting a sub-app at `/mcp` makes Starlette redirect `POST /mcp` to
`/mcp/` (307), and not every MCP client follows a redirect on a POST.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from domain.mcp_config import McpServerStatus, McpToolInfo
from infra.settings import settings
from mcp_adapter import build_mcp_server
from services.navigation_errors import NavigationUnavailableError

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from fastapi import FastAPI
    from mcp.server.mcpserver import MCPServer
    from mcp.types import Tool

    from api.state import AppState
    from services.document_tools import DocumentTools

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"

# MCP Apps: a tool with no `visibility` is offered to both the model and the
# card it belongs to.
_DEFAULT_VISIBILITY = ("model", "app")


@dataclass(frozen=True)
class MountedMcpServer:
    """What a mount leaves behind: the server, and the session its lifespan enters."""

    server: MCPServer
    session: AbstractAsyncContextManager[None]


def mount_mcp_server(app: FastAPI) -> MountedMcpServer | None:
    """Attach `POST /mcp` to `app`; return the server and the session to enter.

    Returns `None` — and mounts nothing — when the surface is disabled.
    """
    if not settings.mcp_enabled:
        logger.info("MCP document server disabled (MCP_ENABLED not set)")
        return None

    server = build_mcp_server(
        lambda: _tools_from(app),
        version=settings.app_version,
        apps=settings.mcp_apps_enabled,
        citation_card=settings.mcp_citation_card,
        # The instructions are built once, here, before the database is open:
        # they state the env cap. The prompt and the sources card read the
        # effective one on every call (#364).
        max_rounds=settings.mcp_max_rounds,
    )
    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        # Stateless: every request stands alone, so the surface survives a
        # reload or a second worker without sticky sessions. The tools need no
        # continuity between calls — but note what it costs, because it is not
        # nothing: on the 2025-era protocol path the SDK serves each request
        # from a fresh `Connection.from_envelope(pv, None, None)`, so
        # `ctx.client_capabilities` is None and anything derived from the
        # client's `initialize` — `client_supports_apps` above all — reads as
        # "not supported" for every HTTP caller. Nothing here consults it (see
        # `mcp_adapter/apps.py`); a future branch on negotiated capabilities
        # would have to go stateful, and pay for session affinity, first.
        stateless_http=True,
        transport_security=_transport_security(),
    )
    app.router.routes.extend(mcp_app.routes)

    logger.warning(
        "MCP document server mounted at %s — UNAUTHENTICATED: it reads every document. "
        "Keep it on localhost or behind an authenticating proxy.",
        MCP_PATH,
    )
    return MountedMcpServer(server=server, session=server.session_manager.run())


async def describe_mcp_server(mounted: MountedMcpServer | None) -> McpServerStatus:
    """The mounted surface as the admin panel shows it — read from the built
    server, so a tool the flags would predict but the server lacks never shows."""
    status = McpServerStatus(
        enabled=mounted is not None,
        path=MCP_PATH,
        allowed_hosts=tuple(settings.mcp_allowed_hosts),
        apps_enabled=settings.mcp_apps_enabled,
        citation_card=settings.mcp_citation_card,
    )
    if mounted is None:
        return status
    tools = tuple(_tool_info(tool) for tool in await mounted.server.list_tools())
    prompts = tuple(prompt.name for prompt in await mounted.server.list_prompts())
    return replace(status, tools=tools, prompts=prompts)


def _tool_info(tool: Tool) -> McpToolInfo:
    ui = (tool.meta or {}).get("ui") or {}
    visibility = tuple(ui.get("visibility") or _DEFAULT_VISIBILITY)
    return McpToolInfo(name=tool.name, visibility=visibility, card="resourceUri" in ui)


def _tools_from(app: FastAPI) -> DocumentTools:
    """Resolve the wired service, typed — `app.state` itself stays untyped.

    The one `getattr` is the same read `api.state.get_app_state` does, and for
    the same reason: `app.state` is a namespace, and the container is absent
    until the lifespan publishes it. Everything after it goes through the
    typed `AppState`, so a renamed slot is a checker error rather than a
    silently missing tool at request time.
    """
    container: AppState | None = getattr(app.state, "container", None)
    if container is None or container.document_tools is None:
        raise NavigationUnavailableError(
            "Docling Studio is still starting up — no document navigation available yet. "
            "Retry in a moment."
        )
    return container.document_tools


def _transport_security():
    """DNS-rebinding protection for the streamable-HTTP transport.

    The SDK's own default only trusts localhost, which silently 421s a
    containerised deployment. Making the allow-list an explicit setting turns
    that into a decision an operator takes, and `MCP_ALLOWED_HOSTS=*` is the
    documented way to delegate the check to a fronting proxy.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = list(settings.mcp_allowed_hosts)
    if "*" in hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    origins: list[str] = []
    for host in hosts:
        origins.extend([f"http://{host}", f"https://{host}"])
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )

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

The returned context is single-use, like the SDK's own session manager: one
mount, one lifespan, which is how uvicorn runs an app. A test (or anything
else) that enters the same app's lifespan twice must mount again.

The route is appended to the app's own router rather than `app.mount()`ed:
mounting a sub-app at `/mcp` makes Starlette redirect `POST /mcp` to
`/mcp/` (307), and not every MCP client follows a redirect on a POST.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from infra.settings import settings
from mcp_adapter import build_mcp_server, deps_present, deps_provenance
from services.navigation_service import NavigationUnavailableError

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from fastapi import FastAPI

    from api.state import AppState
    from services.navigation_service import NavigationService

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"


def mount_mcp_server(app: FastAPI) -> AbstractAsyncContextManager[None] | None:
    """Attach `POST /mcp` to `app`; return the context its lifespan must enter.

    Returns `None` — and mounts nothing — when the surface is disabled or the
    optional SDK is absent. The caller treats `None` as "no MCP today".
    """
    if not settings.mcp_enabled:
        logger.info("MCP document server disabled (MCP_ENABLED not set)")
        return None

    if not deps_present():
        logger.warning(
            "MCP_ENABLED is true but the MCP SDK is not importable (%s) — surface not "
            "mounted. Install it with `uv sync --group mcp`; a bare `uvicorn` resolves "
            "against the ambient interpreter, not the project venv.",
            deps_provenance(),
        )
        return None

    server = build_mcp_server(
        lambda: _navigation_from(app),
        version=settings.app_version,
    )
    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        # Stateless: every request stands alone, so the surface survives a
        # reload or a second worker without sticky sessions. Nothing the
        # tools do needs continuity between calls.
        stateless_http=True,
        transport_security=_transport_security(),
    )
    app.router.routes.extend(mcp_app.routes)

    logger.warning(
        "MCP document server mounted at %s (%s) — READ-ONLY and UNAUTHENTICATED. "
        "Keep it on localhost or behind an authenticating proxy.",
        MCP_PATH,
        deps_provenance(),
    )
    return server.session_manager.run()


def _navigation_from(app: FastAPI) -> NavigationService:
    """Resolve the wired service, typed — `app.state` itself stays untyped.

    The one `getattr` is the same read `api.state.get_app_state` does, and for
    the same reason: `app.state` is a namespace, and the container is absent
    until the lifespan publishes it. Everything after it goes through the
    typed `AppState`, so a renamed slot is a checker error rather than a
    silently missing tool at request time.
    """
    container: AppState | None = getattr(app.state, "container", None)
    if container is None or container.navigation_service is None:
        raise NavigationUnavailableError(
            "Docling Studio is still starting up — no document navigation available yet. "
            "Retry in a moment."
        )
    return container.navigation_service


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

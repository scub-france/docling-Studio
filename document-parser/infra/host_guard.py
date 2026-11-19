"""`Host` header check on `/api/*`: DNS-rebinding protection (08 MAJ).

A page on a hostile domain whose DNS later resolves to 127.0.0.1 can call an
instance on the user's machine as same-origin: CORS does not apply, only the
`Host` header still names the hostile domain. Checking it closes that door.

The check is opt-in (`API_ALLOWED_HOSTS`): turned on by default it would cut
every deployment reached by a LAN name or behind a proxy. Patterns follow
`MCP_ALLOWED_HOSTS`: an exact `name:port`, `name:*` for any port, `*` for no
check. One difference: `name:*` also accepts the bare `name`, because nginx
forwards `/api` with `Host $host`, which drops the port. Loopback names are
always accepted, so container health checks and local tools keep working.

The rejection mirrors the MCP transport's: 421 with `Invalid Host header`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse

if TYPE_CHECKING:
    from collections.abc import Iterable

    from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

API_PATH_PREFIX = "/api/"
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
INVALID_HOST_STATUS = 421
INVALID_HOST_MESSAGE = "Invalid Host header"


def split_host(host: str) -> tuple[str, str | None]:
    """`host` as (name, port), the name lowercased; the port is None when absent.

    An IPv6 literal keeps its brackets, as it is written in a `Host` header.
    """
    host = host.strip().lower()
    if host.startswith("["):
        end = host.find("]")
        if end == -1:
            return host, None
        name, rest = host[: end + 1], host[end + 1 :]
        return name, rest[1:] if rest.startswith(":") else None
    name, sep, port = host.partition(":")
    return name, port if sep else None


def is_allowed_host(host: str | None, allowed_hosts: Iterable[str]) -> bool:
    """Whether a request whose `Host` header is `host` may reach `/api`."""
    if not host:
        return False
    full = host.strip().lower()
    name, _ = split_host(full)
    if name in LOOPBACK_HOSTS:
        return True
    for raw in allowed_hosts:
        pattern = raw.strip().lower()
        if pattern == "*" or full == pattern:
            return True
        if pattern.endswith(":*") and name == pattern[:-2]:
            return True
    return False


def is_host_check_on(allowed_hosts: Iterable[str]) -> bool:
    """On when hosts are listed, unless one of them is the `*` wildcard."""
    hosts = [host.strip() for host in allowed_hosts]
    return bool(hosts) and "*" not in hosts


def describe_host_check(allowed_hosts: Iterable[str]) -> str:
    """The start-up line saying whether `/api` checks `Host`, and for which hosts."""
    hosts = [host.strip() for host in allowed_hosts]
    if "*" in hosts:
        return "API Host check off (API_ALLOWED_HOSTS=*): /api accepts any Host header"
    if not hosts:
        return (
            "API Host check off (API_ALLOWED_HOSTS unset): /api accepts any Host header, "
            "open to DNS rebinding on a workstation"
        )
    return f"API Host check on: /api accepts loopback and {', '.join(hosts)}"


class ApiHostGuardMiddleware:
    """Answer 421 to an `/api/*` request whose `Host` is not allowed.

    Pure ASGI rather than `BaseHTTPMiddleware`: it only reads the headers and
    never wraps the response, so streamed exports pass through untouched.
    Anything outside `/api/` (the SPA, `/mcp`, OpenAPI) is not checked here;
    `/mcp` has its own check.
    """

    def __init__(self, app: ASGIApp, *, allowed_hosts: Iterable[str]) -> None:
        self._app = app
        self._allowed_hosts = tuple(allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(API_PATH_PREFIX):
            await self._app(scope, receive, send)
            return
        host = Headers(scope=scope).get("host")
        if is_allowed_host(host, self._allowed_hosts):
            await self._app(scope, receive, send)
            return
        logger.warning("Rejected /api request with Host %r (API_ALLOWED_HOSTS)", host)
        response = PlainTextResponse(INVALID_HOST_MESSAGE, status_code=INVALID_HOST_STATUS)
        await response(scope, receive, send)

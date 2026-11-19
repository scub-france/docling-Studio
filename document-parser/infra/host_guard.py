"""`Host` header check on `/api/*`: DNS-rebinding protection (08 MAJ).

A page on a hostile domain whose DNS later resolves to 127.0.0.1 can call an
instance on the user's machine as same-origin: CORS does not apply, only the
`Host` header still names the hostile domain. Checking its name closes that
door; the port plays no part, so it is ignored on both sides.

The check is opt-in (`API_ALLOWED_HOSTS`): turned on by default it would cut
every deployment reached by a LAN name or behind a proxy. An entry is a name,
optionally with a port (`name:port`, `name:*`) that is ignored; `*` turns the
check off. Loopback names are always accepted, so container health checks and
local tools keep working. A malformed `Host` is refused.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Iterable

    from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
# A host name or a bracketed IPv6 literal, then an optional numeric port.
# A `*` port is only for the allow-list entries.
_HOST = re.compile(r"(?P<name>[a-z0-9_.-]+|\[[0-9a-f:.]+\])(?::(?:[0-9]{1,5}|\*))?", re.ASCII)


def parse_host_name(host: str | None, *, port_wildcard: bool = False) -> str | None:
    """The lowercased name of a `Host` value, or None when it is malformed."""
    match = _HOST.fullmatch((host or "").strip().lower())
    if match is None or (not port_wildcard and match.group(0).endswith(":*")):
        return None
    return match["name"]


def is_host_check_on(allowed_hosts: Iterable[str]) -> bool:
    """On when hosts are listed, unless one of them is the `*` wildcard."""
    hosts = [host.strip() for host in allowed_hosts]
    return bool(hosts) and "*" not in hosts


def split_allowed_hosts(allowed_hosts: Iterable[str]) -> tuple[list[str], list[str]]:
    """The names the check keeps, and the entries it ignores because they are
    not a name (`http://studio.lan`, `*.example.com`), each in listed order."""
    names: list[str] = []
    ignored: list[str] = []
    for host in allowed_hosts:
        name = parse_host_name(host, port_wildcard=True)
        if name is None:
            ignored.append(host.strip())
        elif name not in names:
            names.append(name)
    return names, ignored


def describe_host_check(allowed_hosts: Iterable[str]) -> str:
    """The start-up line saying whether `/api` checks `Host`, and for which names."""
    hosts = [host.strip() for host in allowed_hosts]
    if "*" in hosts:
        return "API Host check off (API_ALLOWED_HOSTS=*): /api accepts any Host header"
    if not hosts:
        return (
            "API Host check off (API_ALLOWED_HOSTS unset): /api accepts any Host header, "
            "open to DNS rebinding on a workstation"
        )
    names, _ = split_allowed_hosts(hosts)
    # The names actually compared, so a dropped entry does not look accepted.
    return f"API Host check on: /api accepts {', '.join(['loopback', *names])}"


def log_host_check(allowed_hosts: Iterable[str]) -> None:
    """Log the start-up line, and one warning naming the entries the check ignores."""
    hosts = list(allowed_hosts)
    if is_host_check_on(hosts):
        _, ignored = split_allowed_hosts(hosts)
        if ignored:
            # Silently dropped, an entry would refuse the host it meant to allow.
            logger.warning(
                "API_ALLOWED_HOSTS entries ignored, not a host name: %s", ", ".join(ignored)
            )
    logger.info(describe_host_check(hosts))


class ApiHostGuardMiddleware:
    """Answer 421 to an `/api/*` request whose `Host` names a host not allowed.

    Pure ASGI: it only reads the headers and never wraps the response, so
    streamed exports pass through untouched. Starlette's `TrustedHostMiddleware`
    answers 400 for the whole app; this one leaves the SPA and `/mcp` (which has
    its own check) alone.
    """

    def __init__(self, app: ASGIApp, *, allowed_hosts: Iterable[str]) -> None:
        self._app = app
        names, _ = split_allowed_hosts(allowed_hosts)
        self._names = LOOPBACK_HOSTS | set(names)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self._app(scope, receive, send)
            return
        host = Headers(scope=scope).get("host")
        if parse_host_name(host) in self._names:
            await self._app(scope, receive, send)
            return
        # DEBUG: nothing bounds how many of these a client sends.
        logger.debug("Rejected /api request with Host %r (API_ALLOWED_HOSTS)", host)
        response = JSONResponse({"detail": "Invalid Host header"}, status_code=421)
        await response(scope, receive, send)

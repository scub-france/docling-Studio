"""Ollama host probe adapter (#317).

Implements the `LLMHostProbe` port: hits `GET {host}/api/tags` and maps the
installed models. Never raises — every failure becomes
`LLMHostProbeResult(reachable=False, error=...)` so the API layer can return
a plain 200 carrying the outcome (an unreachable host is an answer, not an
exception).
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx

from domain.app_config import LLMHostProbeResult

logger = logging.getLogger(__name__)

# Same endpoint the sync `OllamaProvider.health_check` uses — returns 200 with
# the installed model list even on a fresh install.
_TAGS_PATH = "/api/tags"
_PROBE_TIMEOUT_SECONDS = 3.0

_BLOCKED_TARGET_ERROR = "blocked target address (link-local/metadata/reserved)"


def _resolved_target_is_blocked(host: str) -> bool:
    """SSRF guard for the user-supplied probe target (MAJ-08a).

    The legitimate target — an Ollama daemon — lives on loopback or the LAN by
    default (`http://localhost:11434`), so we deliberately DO NOT block loopback
    or the RFC1918 private ranges: doing so would break the normal feature. We
    only reject addresses that are never a legitimate Ollama:
      - link-local (covers the cloud metadata endpoint 169.254.169.254 and
        fe80::/10),
      - multicast,
      - reserved,
      - unspecified (0.0.0.0, ::).

    Loopback is allowed explicitly and takes precedence: IPv6 `::1` is flagged
    `is_reserved` by `ipaddress`, so without this guard `localhost` (which
    resolves to `::1` on most hosts) would be wrongly blocked. RFC1918 private
    addresses carry none of the four blocked flags, so they pass through
    naturally without an explicit allow (unlike `is_private`, which in the
    stdlib also covers 169.254.0.0/16 and would let the metadata endpoint slip
    past — so we must not allow-gate on it).

    Resolution failures are treated as "not blocked" here; the caller then lets
    httpx surface the connection error as an unreachable result (never raises).
    Returns True when at least one resolved address falls in a blocked class.
    """
    hostname = urlparse(host).hostname
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
    return False


class OllamaProbe:
    """httpx-backed implementation of `LLMHostProbe` for Ollama daemons."""

    async def probe(self, host: str) -> LLMHostProbeResult:
        # Resolve and screen the target BEFORE any outbound request so a
        # blocked host never produces network traffic (SSRF, MAJ-08a).
        if _resolved_target_is_blocked(host):
            logger.debug("Ollama probe blocked for %s: link-local/metadata/reserved", host)
            return LLMHostProbeResult(reachable=False, error=_BLOCKED_TARGET_ERROR)
        url = f"{host.rstrip('/')}{_TAGS_PATH}"
        try:
            async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECONDS) as client:
                resp = await client.get(url)
        except httpx.HTTPError as e:
            logger.debug("Ollama probe failed for %s: %s", host, e)
            return LLMHostProbeResult(reachable=False, error=str(e) or type(e).__name__)
        if resp.status_code != 200:
            return LLMHostProbeResult(
                reachable=False,
                error=f"HTTP {resp.status_code} on {_TAGS_PATH}",
            )
        try:
            payload = resp.json()
            models = sorted(m["name"] for m in payload.get("models", []) if m.get("name"))
        except Exception as e:
            # 200 but not the Ollama tags shape — the host answers HTTP yet is
            # not (or not only) an Ollama daemon.
            return LLMHostProbeResult(reachable=False, error=f"unexpected response: {e}")
        return LLMHostProbeResult(reachable=True, models=models)

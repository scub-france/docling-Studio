"""Ollama host probe adapter (#317).

Implements the `LLMHostProbe` port: hits `GET {host}/api/tags` and maps the
installed models. Never raises — every failure becomes
`LLMHostProbeResult(reachable=False, error=...)` so the API layer can return
a plain 200 carrying the outcome (an unreachable host is an answer, not an
exception).
"""

from __future__ import annotations

import logging

import httpx

from domain.app_config import LLMHostProbeResult
from infra.ssrf_guard import BLOCKED_TARGET_REASON, resolved_target_is_blocked

logger = logging.getLogger(__name__)

# Ollama's list of installed models: it answers 200 even on a fresh install,
# with an empty list, so reachable and "no model yet" stay distinct.
_TAGS_PATH = "/api/tags"
_PROBE_TIMEOUT_SECONDS = 3.0

_BLOCKED_TARGET_ERROR = f"blocked target address ({BLOCKED_TARGET_REASON})"


class OllamaProbe:
    """httpx-backed implementation of `LLMHostProbe` for Ollama daemons."""

    async def probe(self, host: str) -> LLMHostProbeResult:
        # Resolve and screen the target BEFORE any outbound request so a
        # blocked host never produces network traffic (SSRF, MAJ-08a).
        if resolved_target_is_blocked(host):
            logger.debug("Ollama probe blocked for %s: %s", host, BLOCKED_TARGET_REASON)
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

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

logger = logging.getLogger(__name__)

# Same endpoint the sync `OllamaProvider.health_check` uses — returns 200 with
# the installed model list even on a fresh install.
_TAGS_PATH = "/api/tags"
_PROBE_TIMEOUT_SECONDS = 3.0


class OllamaProbe:
    """httpx-backed implementation of `LLMHostProbe` for Ollama daemons."""

    async def probe(self, host: str) -> LLMHostProbeResult:
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

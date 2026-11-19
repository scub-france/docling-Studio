"""Ollama LLM provider adapter.

Implements `LLMProvider` for a locally-reachable Ollama instance. Holds the
host URL + default model id; exposes a cheap `health_check` (HEAD `/api/tags`)
that doesn't load any model.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Ollama's tags endpoint returns 200 with an empty list even on a fresh
# install — perfect for a "is the daemon up?" probe.
_HEALTH_PATH = "/api/tags"
_HEALTH_TIMEOUT_SECONDS = 1.5


class OllamaProvider:
    def __init__(self, host: str, default_model_id: str) -> None:
        self._host = host.rstrip("/")
        self._default_model_id = default_model_id

    @property
    def host(self) -> str:
        return self._host

    @property
    def default_model_id(self) -> str:
        return self._default_model_id

    def health_check(self) -> bool:
        try:
            resp = httpx.get(f"{self._host}{_HEALTH_PATH}", timeout=_HEALTH_TIMEOUT_SECONDS)
        except httpx.HTTPError as e:
            logger.debug("Ollama health check failed for %s: %s", self._host, e)
            return False
        return resp.status_code == 200

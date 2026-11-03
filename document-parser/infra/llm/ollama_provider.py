"""Ollama LLM provider adapter.

Implements `LLMProvider` for a locally-reachable Ollama instance: the host
URL and the default model id the reasoning runner reads. Reachability is
probed by `OllamaProbe` (`infra/llm/ollama_probe.py`), not here.
"""

from __future__ import annotations


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

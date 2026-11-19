"""Tests for `infra.llm.ollama_provider.OllamaProvider`."""

from __future__ import annotations

from domain.ports import LLMProvider
from infra.llm.ollama_provider import OllamaProvider


def test_provider_satisfies_llmprovider_protocol() -> None:
    """R13 — `OllamaProvider` is structurally a `LLMProvider`."""
    p = OllamaProvider(host="http://localhost:11434", default_model_id="m")
    assert isinstance(p, LLMProvider)


def test_provider_exposes_host_and_default_model_id() -> None:
    p = OllamaProvider(host="http://ollama:11434", default_model_id="gpt-oss:20b")
    assert p.host == "http://ollama:11434"
    assert p.default_model_id == "gpt-oss:20b"


def test_host_trailing_slash_is_stripped() -> None:
    p = OllamaProvider(host="http://localhost:11434/", default_model_id="m")
    assert p.host == "http://localhost:11434"

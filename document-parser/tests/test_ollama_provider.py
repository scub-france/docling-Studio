"""Tests for `infra.llm.ollama_provider.OllamaProvider`.

A plain carrier of the host and the default model: reachability is probed by
`OllamaProbe` (`tests/test_ollama_probe.py`), not by the provider.
"""

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


def test_the_port_carries_no_type_tag_nor_health_check() -> None:
    """#audit-04 — one backend: nothing to dispatch on, and the panel's
    reachability check is `OllamaProbe`'s."""
    p = OllamaProvider(host="http://localhost:11434", default_model_id="m")
    assert not hasattr(p, "type")
    assert not hasattr(p, "health_check")

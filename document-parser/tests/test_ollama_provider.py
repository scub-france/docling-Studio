"""Tests for `infra.llm.ollama_provider.OllamaProvider`.

Network is stubbed via `httpx` MockTransport so the tests don't depend on a
running Ollama instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from domain.ports import LLMProvider
from infra.llm.ollama_provider import OllamaProvider

if TYPE_CHECKING:
    import pytest


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


def test_health_check_returns_true_on_200(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": []})

    transport = httpx.MockTransport(handler)
    real_get = httpx.get

    def fake_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        with httpx.Client(transport=transport) as client:
            return client.get(url, **kwargs)

    monkeypatch.setattr(httpx, "get", fake_get)
    p = OllamaProvider(host="http://localhost:11434", default_model_id="m")
    assert p.health_check() is True

    # Restore (defensive, MonkeyPatch handles it but explicit is fine)
    monkeypatch.setattr(httpx, "get", real_get)


def test_health_check_returns_false_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", fake_get)
    p = OllamaProvider(host="http://nowhere:11434", default_model_id="m")
    assert p.health_check() is False


def test_health_check_returns_false_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)

    def fake_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        with httpx.Client(transport=transport) as client:
            return client.get(url, **kwargs)

    monkeypatch.setattr(httpx, "get", fake_get)
    p = OllamaProvider(host="http://localhost:11434", default_model_id="m")
    assert p.health_check() is False

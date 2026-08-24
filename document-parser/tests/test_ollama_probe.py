"""Tests for `infra.llm.ollama_probe.OllamaProbe` — SSRF hardening (MAJ-08a).

The probe resolves the user-supplied host and refuses link-local / metadata /
reserved / unspecified targets *before* issuing any outbound request. Loopback
and the RFC1918 private ranges stay allowed on purpose — that is where a
legitimate Ollama daemon lives (`http://localhost:11434`).

`httpx.AsyncClient` is patched throughout so the tests never touch the network.
"""

from __future__ import annotations

import socket
from typing import ClassVar
from unittest.mock import patch

import httpx

from infra.llm.ollama_probe import OllamaProbe


class _FakeAsyncClient:
    """Minimal async-context-manager stand-in for `httpx.AsyncClient`.

    Records every requested URL on the class so a test can assert a request
    was (or was not) made, and returns a canned response from `.get`.
    """

    requested_urls: ClassVar[list[str]] = []
    response: ClassVar[httpx.Response | None] = None

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url: str, **kwargs) -> httpx.Response:
        _FakeAsyncClient.requested_urls.append(url)
        assert _FakeAsyncClient.response is not None
        return _FakeAsyncClient.response


async def test_metadata_ip_is_blocked_without_any_request() -> None:
    """A host resolving to the cloud metadata IP (169.254.169.254, link-local)
    is refused and no outbound httpx request is ever made."""
    with patch("infra.llm.ollama_probe.httpx.AsyncClient") as mock_client:
        result = await OllamaProbe().probe("http://169.254.169.254:11434")

    assert result.reachable is False
    assert "blocked" in (result.error or "")
    # The whole point: the SSRF guard fires before httpx is even constructed.
    mock_client.assert_not_called()


async def test_localhost_is_allowed_and_reaches_httpx() -> None:
    """`http://localhost:11434` (loopback) is NOT blocked — the probe reaches
    the httpx branch and maps the installed models from a 200 response."""
    _FakeAsyncClient.requested_urls = []
    _FakeAsyncClient.response = httpx.Response(200, json={"models": [{"name": "llama3"}]})

    with patch("infra.llm.ollama_probe.httpx.AsyncClient", _FakeAsyncClient):
        result = await OllamaProbe().probe("http://localhost:11434")

    assert result.reachable is True
    assert result.models == ["llama3"]
    # Loopback reached the network branch (guard did not short-circuit).
    assert _FakeAsyncClient.requested_urls == ["http://localhost:11434/api/tags"]


async def test_resolution_failure_returns_unreachable_without_raising() -> None:
    """An unresolvable host never raises — it degrades to reachable=False.

    The guard treats a resolution failure as "not blocked" and lets httpx
    surface the connection error as an unreachable result."""

    def _boom(*args, **kwargs):
        raise socket.gaierror("name resolution failed")

    async def _connect_error(self, url: str, **kwargs):
        raise httpx.ConnectError("connection refused")

    with (
        patch("infra.llm.ollama_probe.socket.getaddrinfo", _boom),
        patch.object(_FakeAsyncClient, "get", _connect_error),
        patch("infra.llm.ollama_probe.httpx.AsyncClient", _FakeAsyncClient),
    ):
        result = await OllamaProbe().probe("http://does-not-exist.invalid:11434")

    assert result.reachable is False
    assert result.error

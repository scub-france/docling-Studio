"""Tests for the MCP mount — the wiring that actually exposes the surface.

Exercises `bootstrap.mcp_mount` against a throwaway FastAPI app rather than
`main.app`, so the assertions are about the mount contract (flag, route,
transport guard) and not about the rest of the backend booting.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.mcp_mount import mount_mcp_server
from infra.settings import settings as real_settings

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def _app(**overrides) -> tuple[FastAPI, object]:
    """Build an app with the MCP surface mounted under patched settings."""
    settings = replace(real_settings, **overrides)
    session = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if session is not None:
            async with session:
                yield
        else:
            yield

    app = FastAPI(lifespan=lifespan)
    with patch("bootstrap.mcp_mount.settings", settings):
        mounted = mount_mcp_server(app)
    session = mounted.session if mounted is not None else None
    return app, mounted


def _paths(app: FastAPI) -> set[str]:
    return {getattr(route, "path", "") for route in app.router.routes}


class TestMountFlag:
    def test_disabled_by_default_mounts_nothing(self):
        app, session = _app(mcp_enabled=False)
        assert session is None
        assert "/mcp" not in _paths(app)

    def test_enabled_adds_the_route_without_a_redirect_hop(self):
        app, session = _app(mcp_enabled=True)
        assert session is not None
        assert "/mcp" in _paths(app)

    def test_route_stays_out_of_the_openapi_contract(self):
        app, _ = _app(mcp_enabled=True)
        with TestClient(app) as client:
            assert "/mcp" not in client.get("/openapi.json").json()["paths"]


class TestTransport:
    def test_serves_an_initialize_handshake_on_an_allowed_host(self):
        app, _ = _app(mcp_enabled=True, mcp_allowed_hosts=["testserver"])
        with TestClient(app) as client:
            response = client.post("/mcp", json=INITIALIZE, headers=HEADERS, follow_redirects=False)
        assert response.status_code == 200
        assert "docling-studio" in response.text

    def test_rejects_a_host_outside_the_allow_list(self):
        app, _ = _app(mcp_enabled=True, mcp_allowed_hosts=["example.com"])
        with TestClient(app) as client:
            response = client.post("/mcp", json=INITIALIZE, headers=HEADERS)
        assert response.status_code == 421

    def test_the_shipped_default_allow_list_accepts_a_localhost_client(self):
        # The value that actually ships is the only thing standing between a
        # local Claude Code / Desktop client and a 421, so it is exercised as
        # shipped rather than overridden.
        for base in ("http://localhost:8000", "http://127.0.0.1:8000"):
            # A fresh app per client: the SDK's session manager is a
            # single-use context, so one process may enter one lifespan per
            # mount — which is exactly how uvicorn runs it.
            app, _ = _app(mcp_enabled=True)
            with TestClient(app, base_url=base) as client:
                response = client.post("/mcp", json=INITIALIZE, headers=HEADERS)
            assert response.status_code == 200, base

    def test_the_shipped_default_rejects_a_foreign_host(self):
        app, _ = _app(mcp_enabled=True)
        with TestClient(app, base_url="http://evil.example.com") as client:
            response = client.post("/mcp", json=INITIALIZE, headers=HEADERS)
        assert response.status_code == 421

    def test_wildcard_delegates_the_check_to_the_proxy(self):
        app, _ = _app(mcp_enabled=True, mcp_allowed_hosts=["*"])
        with TestClient(app) as client:
            response = client.post("/mcp", json=INITIALIZE, headers=HEADERS)
        assert response.status_code == 200


class TestDescribe:
    """#364 — what the admin panel reports, read from the built server."""

    async def test_disabled_reports_no_surface(self):
        from bootstrap.mcp_mount import describe_mcp_server

        settings = replace(real_settings, mcp_allowed_hosts=["localhost:*"])
        with patch("bootstrap.mcp_mount.settings", settings):
            status = await describe_mcp_server(None)
        assert status.enabled is False
        assert status.path == "/mcp"
        assert status.allowed_hosts == ("localhost:*",)
        assert status.tools == () and status.prompts == ()

    async def test_lists_what_the_built_server_publishes(self):
        from bootstrap.mcp_mount import describe_mcp_server

        settings = replace(real_settings, mcp_enabled=True, mcp_citation_card=True)
        app = FastAPI()
        with patch("bootstrap.mcp_mount.settings", settings):
            mounted = mount_mcp_server(app)
            status = await describe_mcp_server(mounted)

        tools = {tool.name: tool for tool in status.tools}
        assert status.enabled is True and status.citation_card is True
        assert tools["read_element"].visibility == ("model", "app")
        assert tools["read_element"].card is False
        assert tools["show_sources"].visibility == ("model",) and tools["show_sources"].card
        assert tools["get_source_page"].visibility == ("app",)
        assert "show_citation" in tools
        assert status.prompts == ("chunkless_rag",)

    async def test_the_citation_card_is_absent_when_off(self):
        from bootstrap.mcp_mount import describe_mcp_server

        settings = replace(real_settings, mcp_enabled=True, mcp_citation_card=False)
        with patch("bootstrap.mcp_mount.settings", settings):
            status = await describe_mcp_server(mount_mcp_server(FastAPI()))
        assert "show_citation" not in {tool.name for tool in status.tools}

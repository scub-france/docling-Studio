"""Tests for the MCP admin routes (#364) — `/api/config/mcp` and `/api/mcp/server`.

Wires the real `McpConfigService` over an in-memory repo, so the router →
service path and the status-code mapping are exercised, and pins the camelCase
wire contract the admin panel codes against.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import router as config_router
from api.mcp import router as mcp_router
from domain.mcp_config import McpRuntimeConfig, McpServerStatus, McpToolInfo
from services.mcp_config_service import McpConfigService
from tests.app_state import wire_state

ENV = McpRuntimeConfig(max_rounds=5, max_read_tokens=4000, studio_base_url="")
STATUS = McpServerStatus(
    enabled=True,
    path="/mcp",
    allowed_hosts=("127.0.0.1:*", "localhost:*"),
    apps_enabled=True,
    citation_card=False,
    tools=(
        McpToolInfo(name="read_element", visibility=("model", "app"), card=False),
        McpToolInfo(name="show_sources", visibility=("model",), card=True),
        McpToolInfo(name="get_source_page", visibility=("app",), card=True),
    ),
    prompts=("chunkless_rag",),
)


class _FakeRepo:
    def __init__(self, rows: dict[str, str] | None = None) -> None:
        self.rows = dict(rows or {})

    async def get_namespace(self, namespace: str) -> dict[str, str]:
        return dict(self.rows)

    async def set_many(self, namespace: str, values: dict[str, str]) -> None:
        self.rows.update(values)

    async def delete_namespace(self, namespace: str) -> int:
        removed = len(self.rows)
        self.rows.clear()
        return removed


def _client(
    *, rows: dict[str, str] | None = None, read_only: bool = False
) -> tuple[TestClient, list[McpRuntimeConfig], _FakeRepo]:
    repo = _FakeRepo(rows)
    applied: list[McpRuntimeConfig] = []

    async def status() -> McpServerStatus:
        return STATUS

    service = McpConfigService(
        repo=repo,
        env_defaults=ENV,
        read_only=read_only,
        apply_config=applied.append,
        status_provider=status,
    )
    app = FastAPI()
    app.include_router(config_router)
    app.include_router(mcp_router)
    wire_state(app, mcp_config_service=service)
    return TestClient(app), applied, repo


BODY = {"maxRounds": 3, "maxReadTokens": 1500, "studioBaseUrl": "http://localhost:3000"}


class TestGetConfig:
    def test_wire_shape_is_camel_case_with_sources(self):
        client, _, _ = _client(rows={"max_rounds": "3"})
        response = client.get("/api/config/mcp")
        assert response.status_code == 200
        assert response.json() == {
            "maxRounds": 3,
            "maxReadTokens": 4000,
            "studioBaseUrl": "",
            "sources": {"maxRounds": "db", "maxReadTokens": "env", "studioBaseUrl": "env"},
            "readOnly": False,
        }


class TestPutConfig:
    def test_replaces_the_overrides_and_applies(self):
        client, applied, repo = _client()
        response = client.put("/api/config/mcp", json=BODY)
        assert response.status_code == 200
        assert response.json()["maxReadTokens"] == 1500
        assert set(response.json()["sources"].values()) == {"db"}
        assert applied == [McpRuntimeConfig(3, 1500, "http://localhost:3000")]
        assert repo.rows["max_rounds"] == "3"

    def test_invalid_values_are_400(self):
        client, applied, _ = _client()
        response = client.put("/api/config/mcp", json={**BODY, "maxRounds": 0})
        assert response.status_code == 400
        assert "max_rounds" in response.json()["detail"]
        assert applied == []

    def test_every_field_is_required(self):
        client, applied, _ = _client()
        body = {"maxRounds": 3, "maxReadTokens": 1500}
        assert client.put("/api/config/mcp", json=body).status_code == 422
        assert applied == []

    def test_read_only_is_403(self):
        client, applied, _ = _client(read_only=True)
        response = client.put("/api/config/mcp", json=BODY)
        assert response.status_code == 403
        assert applied == []


class TestResetConfig:
    def test_drops_the_overrides(self):
        client, applied, repo = _client(rows={"max_rounds": "3"})
        response = client.delete("/api/config/mcp")
        assert response.status_code == 200
        assert response.json()["maxRounds"] == 5
        assert repo.rows == {} and applied == [ENV]

    def test_read_only_is_403(self):
        client, _, repo = _client(rows={"max_rounds": "3"}, read_only=True)
        assert client.delete("/api/config/mcp").status_code == 403
        assert repo.rows == {"max_rounds": "3"}


class TestServer:
    def test_reports_the_running_server(self):
        client, _, _ = _client()
        response = client.get("/api/mcp/server")
        assert response.status_code == 200
        body = response.json()
        assert body["enabled"] is True
        assert body["path"] == "/mcp"
        assert body["allowedHosts"] == ["127.0.0.1:*", "localhost:*"]
        assert (body["appsEnabled"], body["citationCard"]) == (True, False)
        assert body["tools"][1] == {"name": "show_sources", "visibility": ["model"], "card": True}
        assert body["prompts"] == ["chunkless_rag"]

    def test_unwired_is_503(self):
        app = FastAPI()
        app.include_router(mcp_router)
        wire_state(app)
        assert TestClient(app).get("/api/mcp/server").status_code == 503

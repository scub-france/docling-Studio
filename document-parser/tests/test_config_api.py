"""Tests for `api.config` — the HTTP layer over `AppConfigService` (#317).

Wires the real service (so the router → service path and the status-code
mapping are exercised) backed by in-memory fakes, and asserts the camelCase
wire contract: config values, per-field sources keyed camelCase, diagnostics,
and the 400/403 refusals. Follows the `test_reasoning_api.py` pattern.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import router
from domain.app_config import (
    LLMHostProbeResult,
    ReasoningConfig,
    ReasoningDiagnostics,
)
from services.app_config_service import AppConfigService
from tests.app_state import wire_state

ENV = ReasoningConfig(
    enabled=False,
    ollama_host="http://env-host:11434",
    model_id="env-model:7b",
    max_iterations=5,
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


class _FakeProbe:
    def __init__(self, result: LLMHostProbeResult) -> None:
        self.result = result
        self.calls: list[str] = []

    async def probe(self, host: str) -> LLMHostProbeResult:
        self.calls.append(host)
        return self.result


def _make_client(
    *,
    rows: dict[str, str] | None = None,
    read_only: bool = False,
    probe_result: LLMHostProbeResult | None = None,
) -> tuple[TestClient, list[ReasoningConfig], _FakeRepo]:
    applied: list[ReasoningConfig] = []
    repo = _FakeRepo(rows)
    probe = _FakeProbe(probe_result or LLMHostProbeResult(reachable=True, models=["m:7b"]))
    service = AppConfigService(
        repo=repo,
        env_defaults=ENV,
        provider_type="ollama",
        read_only=read_only,
        probe=probe,
        apply_config=applied.append,
        diagnostics_provider=lambda: ReasoningDiagnostics(
            deps_present=True, provenance="docling-agent 0.6.0 from /test", available=True
        ),
    )
    app = FastAPI()
    app.include_router(router)
    wire_state(app, app_config_service=service)
    return TestClient(app), applied, repo


_VALID_BODY = {
    "enabled": True,
    "ollamaHost": "http://new-host:11434",
    "modelId": "new-model:8b",
    "maxIterations": 7,
}


class TestGetConfig:
    def test_env_only_wire_shape(self):
        client, _, _ = _make_client()

        resp = client.get("/api/config/reasoning")

        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is False
        assert body["ollamaHost"] == "http://env-host:11434"
        assert body["modelId"] == "env-model:7b"
        assert body["maxIterations"] == 5
        assert body["sources"] == {
            "enabled": "env",
            "ollamaHost": "env",
            "modelId": "env",
            "maxIterations": "env",
        }
        assert body["providerType"] == "ollama"
        assert body["readOnly"] is False
        assert body["diagnostics"] == {
            "depsPresent": True,
            "provenance": "docling-agent 0.6.0 from /test",
            "available": True,
        }

    def test_read_only_flag_surfaces_on_get(self):
        client, _, _ = _make_client(read_only=True)

        resp = client.get("/api/config/reasoning")

        assert resp.status_code == 200
        assert resp.json()["readOnly"] is True


class TestPutConfig:
    def test_happy_path_persists_and_rebuilds(self):
        client, applied, repo = _make_client()

        resp = client.put("/api/config/reasoning", json=_VALID_BODY)

        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["modelId"] == "new-model:8b"
        assert body["maxIterations"] == 7
        assert all(source == "db" for source in body["sources"].values())
        assert repo.rows["ollama_host"] == "http://new-host:11434"
        assert applied == [
            ReasoningConfig(
                enabled=True,
                ollama_host="http://new-host:11434",
                model_id="new-model:8b",
                max_iterations=7,
            )
        ]

    def test_invalid_host_is_400(self):
        client, applied, _ = _make_client()

        resp = client.put("/api/config/reasoning", json={**_VALID_BODY, "ollamaHost": "nope"})

        assert resp.status_code == 400
        assert "http" in resp.json()["detail"]
        assert applied == []

    def test_out_of_bounds_iterations_is_400(self):
        client, _, _ = _make_client()

        resp = client.put("/api/config/reasoning", json={**_VALID_BODY, "maxIterations": 21})

        assert resp.status_code == 400
        assert "max_iterations" in resp.json()["detail"]

    def test_missing_field_is_422(self):
        body = {k: v for k, v in _VALID_BODY.items() if k != "maxIterations"}
        client, _, _ = _make_client()

        resp = client.put("/api/config/reasoning", json=body)

        assert resp.status_code == 422

    def test_read_only_is_403(self):
        client, applied, repo = _make_client(read_only=True)

        resp = client.put("/api/config/reasoning", json=_VALID_BODY)

        assert resp.status_code == 403
        assert repo.rows == {}
        assert applied == []


class TestDeleteConfig:
    def test_reset_returns_env_sources_and_rebuilds(self):
        client, applied, repo = _make_client(rows={"enabled": "true", "model_id": "db:8b"})

        resp = client.delete("/api/config/reasoning")

        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is False
        assert body["modelId"] == "env-model:7b"
        assert all(source == "env" for source in body["sources"].values())
        assert repo.rows == {}
        assert applied == [ENV]

    def test_read_only_is_403(self):
        client, _, repo = _make_client(rows={"enabled": "true"}, read_only=True)

        resp = client.delete("/api/config/reasoning")

        assert resp.status_code == 403
        assert repo.rows == {"enabled": "true"}


class TestProbe:
    def test_reachable_host_returns_models(self):
        client, _, _ = _make_client(
            probe_result=LLMHostProbeResult(reachable=True, models=["a:7b", "b:8b"])
        )

        resp = client.post("/api/config/reasoning/test", json={"host": "http://h:11434"})

        assert resp.status_code == 200
        assert resp.json() == {"reachable": True, "models": ["a:7b", "b:8b"], "error": None}

    def test_unreachable_host_is_200_not_500(self):
        client, _, _ = _make_client(
            probe_result=LLMHostProbeResult(reachable=False, error="connection refused")
        )

        resp = client.post("/api/config/reasoning/test", json={"host": "http://down:11434"})

        assert resp.status_code == 200
        assert resp.json() == {"reachable": False, "models": [], "error": "connection refused"}

    def test_malformed_url_is_400(self):
        client, _, _ = _make_client()

        resp = client.post("/api/config/reasoning/test", json={"host": "not-a-url"})

        assert resp.status_code == 400

    def test_read_only_is_403(self):
        client, _, _ = _make_client(read_only=True)

        resp = client.post("/api/config/reasoning/test", json={"host": "http://h:11434"})

        assert resp.status_code == 403

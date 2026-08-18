"""Tests for `AppConfigService` (#317).

Covers the precedence rule (db overrides over env bootstrap defaults),
tolerant reads (corrupt rows fall back to env), strict writes (validation +
read-only refusals), the hot-rebuild hook invocation, and probe delegation.
All collaborators are in-memory fakes — no SQLite, no HTTP.
"""

from __future__ import annotations

import pytest

from domain.app_config import (
    LLMHostProbeResult,
    ReasoningConfig,
    ReasoningDiagnostics,
)
from services.app_config_service import (
    AppConfigReadOnlyError,
    AppConfigService,
    AppConfigValidationError,
)

ENV = ReasoningConfig(
    enabled=False,
    ollama_host="http://env-host:11434",
    model_id="env-model:7b",
    max_iterations=5,
)

DIAGNOSTICS = ReasoningDiagnostics(deps_present=True, provenance="test-provenance", available=True)


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
    def __init__(self, result: LLMHostProbeResult | None = None) -> None:
        self.result = result or LLMHostProbeResult(reachable=True, models=["a", "b"])
        self.calls: list[str] = []

    async def probe(self, host: str) -> LLMHostProbeResult:
        self.calls.append(host)
        return self.result


def _service(
    *,
    rows: dict[str, str] | None = None,
    read_only: bool = False,
    probe: _FakeProbe | None = None,
) -> tuple[AppConfigService, _FakeRepo, list[ReasoningConfig], _FakeProbe]:
    repo = _FakeRepo(rows)
    applied: list[ReasoningConfig] = []
    probe = probe or _FakeProbe()
    service = AppConfigService(
        repo=repo,
        env_defaults=ENV,
        provider_type="ollama",
        read_only=read_only,
        probe=probe,
        apply_config=applied.append,
        diagnostics_provider=lambda: DIAGNOSTICS,
    )
    return service, repo, applied, probe


class TestGetReasoning:
    async def test_env_only_view(self):
        service, _, _, _ = _service()

        view = await service.get_reasoning()

        assert view.config == ENV
        assert view.sources == {
            "enabled": "env",
            "ollama_host": "env",
            "model_id": "env",
            "max_iterations": "env",
        }
        assert view.provider_type == "ollama"
        assert view.read_only is False
        assert view.diagnostics == DIAGNOSTICS

    async def test_db_rows_override_env(self):
        service, _, _, _ = _service(
            rows={
                "enabled": "true",
                "ollama_host": "http://db-host:11434",
                "model_id": "db-model:8b",
                "max_iterations": "9",
            }
        )

        view = await service.get_reasoning()

        assert view.config == ReasoningConfig(
            enabled=True,
            ollama_host="http://db-host:11434",
            model_id="db-model:8b",
            max_iterations=9,
        )
        assert all(source == "db" for source in view.sources.values())

    async def test_partial_rows_yield_mixed_sources(self):
        service, _, _, _ = _service(rows={"model_id": "db-model:8b"})

        view = await service.get_reasoning()

        assert view.config.model_id == "db-model:8b"
        assert view.config.ollama_host == ENV.ollama_host
        assert view.sources["model_id"] == "db"
        assert view.sources["ollama_host"] == "env"

    @pytest.mark.parametrize(
        "rows",
        [
            {"enabled": "maybe"},
            {"max_iterations": "abc"},
            {"max_iterations": "999"},  # out of bounds
            {"max_iterations": "0"},
            {"ollama_host": "   "},
            {"model_id": ""},
        ],
    )
    async def test_corrupt_rows_fall_back_to_env(self, rows):
        service, _, _, _ = _service(rows=rows)

        view = await service.get_reasoning()

        assert view.config == ENV
        assert all(source == "env" for source in view.sources.values())


class TestUpdateReasoning:
    async def test_persists_applies_and_reports_db_sources(self):
        service, repo, applied, _ = _service()
        config = ReasoningConfig(
            enabled=True,
            ollama_host="http://new-host:11434",
            model_id="new-model:8b",
            max_iterations=7,
        )

        view = await service.update_reasoning(config)

        assert repo.rows == {
            "enabled": "true",
            "ollama_host": "http://new-host:11434",
            "model_id": "new-model:8b",
            "max_iterations": "7",
        }
        assert applied == [config]
        assert view.config == config
        assert all(source == "db" for source in view.sources.values())

    async def test_strips_text_fields_before_persisting(self):
        service, repo, _, _ = _service()

        await service.update_reasoning(
            ReasoningConfig(
                enabled=False,
                ollama_host="  http://h:11434  ",
                model_id="  m:7b  ",
                max_iterations=5,
            )
        )

        assert repo.rows["ollama_host"] == "http://h:11434"
        assert repo.rows["model_id"] == "m:7b"

    @pytest.mark.parametrize(
        ("config", "match"),
        [
            (
                ReasoningConfig(
                    enabled=True, ollama_host="not-a-url", model_id="m", max_iterations=5
                ),
                "http",
            ),
            (
                ReasoningConfig(
                    enabled=True, ollama_host="ftp://h:1", model_id="m", max_iterations=5
                ),
                "http",
            ),
            (
                ReasoningConfig(
                    enabled=True, ollama_host="http://h:1", model_id="  ", max_iterations=5
                ),
                "model_id",
            ),
            (
                ReasoningConfig(
                    enabled=True, ollama_host="http://h:1", model_id="m", max_iterations=0
                ),
                "max_iterations",
            ),
            (
                ReasoningConfig(
                    enabled=True, ollama_host="http://h:1", model_id="m", max_iterations=21
                ),
                "max_iterations",
            ),
        ],
    )
    async def test_invalid_config_raises_400_and_persists_nothing(self, config, match):
        service, repo, applied, _ = _service()

        with pytest.raises(AppConfigValidationError, match=match) as exc_info:
            await service.update_reasoning(config)

        assert exc_info.value.http_status == 400
        assert repo.rows == {}
        assert applied == []

    async def test_read_only_refuses_with_403(self):
        service, repo, applied, _ = _service(read_only=True)

        with pytest.raises(AppConfigReadOnlyError) as exc_info:
            await service.update_reasoning(
                ReasoningConfig(
                    enabled=True, ollama_host="http://h:1", model_id="m", max_iterations=5
                )
            )

        assert exc_info.value.http_status == 403
        assert repo.rows == {}
        assert applied == []


class TestResetReasoning:
    async def test_drops_overrides_and_applies_env(self):
        service, repo, applied, _ = _service(rows={"enabled": "true", "model_id": "db:8b"})

        view = await service.reset_reasoning()

        assert repo.rows == {}
        assert applied == [ENV]
        assert view.config == ENV
        assert all(source == "env" for source in view.sources.values())

    async def test_read_only_refuses(self):
        service, repo, _, _ = _service(rows={"enabled": "true"}, read_only=True)

        with pytest.raises(AppConfigReadOnlyError):
            await service.reset_reasoning()

        assert repo.rows == {"enabled": "true"}


class TestTestConnection:
    async def test_delegates_to_probe(self):
        probe = _FakeProbe(LLMHostProbeResult(reachable=True, models=["granite3.3:8b"]))
        service, _, _, _ = _service(probe=probe)

        result = await service.test_connection("http://somewhere:11434")

        assert probe.calls == ["http://somewhere:11434"]
        assert result.reachable is True
        assert result.models == ["granite3.3:8b"]

    async def test_malformed_url_raises_400_without_probing(self):
        service, _, _, probe = _service()

        with pytest.raises(AppConfigValidationError):
            await service.test_connection("not-a-url")

        assert probe.calls == []

    async def test_read_only_refuses_probe(self):
        service, _, _, probe = _service(read_only=True)

        with pytest.raises(AppConfigReadOnlyError):
            await service.test_connection("http://h:11434")

        assert probe.calls == []


class TestApplyEffective:
    async def test_applies_env_when_no_overrides(self):
        service, _, applied, _ = _service()

        await service.apply_effective()

        assert applied == [ENV]

    async def test_applies_db_overrides_at_boot(self):
        service, _, applied, _ = _service(rows={"enabled": "true", "max_iterations": "3"})

        await service.apply_effective()

        assert applied == [
            ReasoningConfig(
                enabled=True,
                ollama_host=ENV.ollama_host,
                model_id=ENV.model_id,
                max_iterations=3,
            )
        ]

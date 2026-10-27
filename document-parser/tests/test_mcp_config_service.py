"""Tests for the MCP runtime config (#364) — domain rules, service, wiring.

The service is exercised against an in-memory repo; the wiring tests use the
real factories to pin what a hot apply promises: new budgets on the next
call, the old ones kept by a call already holding its services, and one parse
index across rebuilds.
"""

from __future__ import annotations

import pytest

from domain.mcp_config import (
    McpRuntimeConfig,
    McpServerStatus,
    McpToolInfo,
    validate_mcp_config,
)
from services.config_overrides import AppConfigReadOnlyError, AppConfigValidationError
from services.mcp_config_service import McpConfigService, load_effective_mcp_config

ENV = McpRuntimeConfig(max_rounds=5, max_read_tokens=4000, studio_base_url="")
STATUS = McpServerStatus(
    enabled=True,
    path="/mcp",
    allowed_hosts=("localhost:*",),
    apps_enabled=True,
    citation_card=False,
    tools=(McpToolInfo(name="read_element", visibility=("model", "app"), card=False),),
    prompts=("chunkless_rag",),
)


class _FakeRepo:
    def __init__(self, rows: dict[str, str] | None = None) -> None:
        self.rows = dict(rows or {})
        self.namespaces: list[str] = []

    async def get_namespace(self, namespace: str) -> dict[str, str]:
        self.namespaces.append(namespace)
        return dict(self.rows)

    async def set_many(self, namespace: str, values: dict[str, str]) -> None:
        self.namespaces.append(namespace)
        self.rows.update(values)

    async def delete_namespace(self, namespace: str) -> int:
        self.namespaces.append(namespace)
        removed = len(self.rows)
        self.rows.clear()
        return removed


def _service(
    *, rows: dict[str, str] | None = None, read_only: bool = False
) -> tuple[McpConfigService, _FakeRepo, list[McpRuntimeConfig]]:
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
    return service, repo, applied


class TestValidation:
    def test_the_env_defaults_are_valid(self):
        assert validate_mcp_config(ENV) == []

    @pytest.mark.parametrize("rounds", [0, 21])
    def test_rounds_out_of_bounds(self, rounds):
        errors = validate_mcp_config(McpRuntimeConfig(rounds, 4000, ""))
        assert len(errors) == 1 and "max_rounds" in errors[0]

    @pytest.mark.parametrize("tokens", [99, 32_001])
    def test_read_tokens_out_of_bounds(self, tokens):
        errors = validate_mcp_config(McpRuntimeConfig(5, tokens, ""))
        assert len(errors) == 1 and "max_read_tokens" in errors[0]

    @pytest.mark.parametrize("url", ["", "http://localhost:3000", "https://studio.example"])
    def test_base_url_empty_or_http(self, url):
        assert validate_mcp_config(McpRuntimeConfig(5, 4000, url)) == []

    @pytest.mark.parametrize("url", ["localhost:3000", "ftp://host", "javascript:alert(1)"])
    def test_base_url_refused(self, url):
        errors = validate_mcp_config(McpRuntimeConfig(5, 4000, url))
        assert len(errors) == 1 and "studio_base_url" in errors[0]

    def test_base_url_length_is_capped(self):
        errors = validate_mcp_config(McpRuntimeConfig(5, 4000, "http://h/" + "a" * 500))
        assert "<= 500" in errors[0]


class TestGetConfig:
    async def test_env_only(self):
        service, repo, _ = _service()
        view = await service.get_config()
        assert view.config == ENV
        assert set(view.sources.values()) == {"env"}
        assert view.read_only is False
        assert repo.namespaces == ["mcp"]

    async def test_db_rows_override_env_field_by_field(self):
        service, _, _ = _service(rows={"max_rounds": "3", "studio_base_url": "http://h:3000"})
        view = await service.get_config()
        assert view.config == McpRuntimeConfig(3, 4000, "http://h:3000")
        assert view.sources == {
            "max_rounds": "db",
            "max_read_tokens": "env",
            "studio_base_url": "db",
        }

    async def test_an_empty_base_url_row_is_a_value(self):
        service, _, _ = _service(rows={"studio_base_url": ""})
        view = await service.get_config()
        assert view.config.studio_base_url == ""
        assert view.sources["studio_base_url"] == "db"

    async def test_unparseable_rows_fall_back_to_env(self, caplog):
        service, _, _ = _service(
            rows={"max_rounds": "lots", "max_read_tokens": "50", "studio_base_url": "ftp://x"}
        )
        view = await service.get_config()
        assert view.config == ENV
        assert set(view.sources.values()) == {"env"}
        assert caplog.text.count("Ignoring unparseable app_settings row mcp.") == 3


class TestUpdate:
    async def test_persists_applies_and_reports_db(self):
        service, repo, applied = _service()
        wanted = McpRuntimeConfig(3, 1500, " http://h:3000 ")

        view = await service.update_config(wanted)

        assert repo.rows == {
            "max_rounds": "3",
            "max_read_tokens": "1500",
            "studio_base_url": "http://h:3000",
        }
        assert applied == [McpRuntimeConfig(3, 1500, "http://h:3000")]
        assert view.config == applied[0]
        assert set(view.sources.values()) == {"db"}

    async def test_invalid_values_are_refused_before_any_write(self):
        service, repo, applied = _service()
        with pytest.raises(AppConfigValidationError) as exc:
            await service.update_config(McpRuntimeConfig(0, 50, "nope"))
        assert exc.value.http_status == 400
        assert repo.rows == {} and applied == []

    async def test_read_only_refuses_the_write(self):
        service, repo, applied = _service(read_only=True)
        with pytest.raises(AppConfigReadOnlyError) as exc:
            await service.update_config(ENV)
        assert exc.value.http_status == 403
        assert repo.rows == {} and applied == []


class TestReset:
    async def test_drops_the_overrides_and_applies_env(self):
        service, repo, applied = _service(rows={"max_rounds": "3"})
        view = await service.reset_config()
        assert repo.rows == {}
        assert applied == [ENV]
        assert set(view.sources.values()) == {"env"}

    async def test_read_only_refuses_the_reset(self):
        service, repo, _ = _service(rows={"max_rounds": "3"}, read_only=True)
        with pytest.raises(AppConfigReadOnlyError):
            await service.reset_config()
        assert repo.rows == {"max_rounds": "3"}


class TestBootAndStatus:
    async def test_apply_effective_applies_the_overrides(self):
        service, _, applied = _service(rows={"max_read_tokens": "2000"})
        await service.apply_effective()
        assert applied == [McpRuntimeConfig(5, 2000, "")]

    async def test_server_status_is_the_provider_s(self):
        service, _, _ = _service()
        assert await service.server_status() == STATUS

    async def test_stdio_resolves_the_same_precedence(self):
        repo = _FakeRepo({"max_rounds": "2"})
        assert await load_effective_mcp_config(repo, ENV) == McpRuntimeConfig(2, 4000, "")


class TestWiring:
    """The factories behind a hot apply."""

    def _parses(self):
        from bootstrap.factories import build_parse_loader
        from tests.navigation_fixtures import FakeAnalysisRepository, FakeDocumentRepository

        return build_parse_loader(FakeDocumentRepository([]), FakeAnalysisRepository([]))

    def test_the_runtime_knobs_reach_every_budget(self):
        from bootstrap.factories import build_document_tools

        tools = build_document_tools(self._parses(), McpRuntimeConfig(3, 1500, "http://h"))
        assert (tools.config.max_rounds, tools.config.max_read_tokens) == (3, 1500)
        assert tools.config.studio_base_url == "http://h"
        assert tools.sources._config is tools.config
        assert tools.navigation._config is tools.config

    def test_a_rebuild_shares_the_parse_index_and_leaves_the_old_set_alone(self):
        from bootstrap.factories import build_document_tools

        parses = self._parses()
        before = build_document_tools(parses, ENV)
        after = build_document_tools(parses, McpRuntimeConfig(3, 1500, ""))

        assert before.navigation._parses is after.navigation._parses is parses
        assert before.config.max_rounds == 5  # a call holding `before` keeps its budgets
        assert after.config.max_rounds == 3

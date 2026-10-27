"""MCP runtime config service (#364) — env bootstrap, SQLite override, hot apply.

Same precedence as the reasoning config (#317): `app_settings` rows in
namespace `mcp` override the env defaults, field by field, and each value
reports its source. A write rebuilds the document-agent services, so the next
tool call runs on the new budgets with no restart.

It also reports what the running server publishes. That part is read-only:
the server is built at import, and the stateless transport cannot tell a
client its tool list changed, so the switches behind it stay in the env.

The service imports neither infra nor the MCP SDK. The env defaults come in as
a domain value object, the rebuild as `apply_config`, the server's description
as `status_provider` — all bound in `bootstrap/`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from domain.mcp_config import (
    MAX_ROUNDS_MAX,
    MAX_ROUNDS_MIN,
    READ_TOKENS_MAX,
    READ_TOKENS_MIN,
    McpRuntimeConfig,
    McpRuntimeConfigView,
    validate_base_url,
    validate_mcp_config,
)
from services.config_overrides import (
    AppConfigValidationError,
    parse_int_between,
    pick,
    require_writable,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from domain.app_config import ConfigSource
    from domain.mcp_config import McpServerStatus
    from domain.ports import AppSettingsRepository

logger = logging.getLogger(__name__)

_NAMESPACE = "mcp"
_KEY_MAX_ROUNDS = "max_rounds"
_KEY_MAX_READ_TOKENS = "max_read_tokens"
_KEY_BASE_URL = "studio_base_url"

_parse_rounds = parse_int_between(MAX_ROUNDS_MIN, MAX_ROUNDS_MAX)
_parse_read_tokens = parse_int_between(READ_TOKENS_MIN, READ_TOKENS_MAX)


def _parse_base_url(raw: str) -> str | None:
    """Empty is a value here — no deep links — not a missing one."""
    stripped = raw.strip()
    return None if validate_base_url(stripped) else stripped


async def resolve_mcp_config(
    repo: AppSettingsRepository, env: McpRuntimeConfig
) -> tuple[McpRuntimeConfig, dict[str, ConfigSource]]:
    """The effective config (db over env) and where each value came from."""
    rows = await repo.get_namespace(_NAMESPACE)
    ns = _NAMESPACE
    rounds, rounds_src = pick(rows, _KEY_MAX_ROUNDS, env.max_rounds, _parse_rounds, namespace=ns)
    tokens, tokens_src = pick(
        rows, _KEY_MAX_READ_TOKENS, env.max_read_tokens, _parse_read_tokens, namespace=ns
    )
    base, base_src = pick(rows, _KEY_BASE_URL, env.studio_base_url, _parse_base_url, namespace=ns)
    config = McpRuntimeConfig(max_rounds=rounds, max_read_tokens=tokens, studio_base_url=base)
    sources: dict[str, ConfigSource] = {
        "max_rounds": rounds_src,
        "max_read_tokens": tokens_src,
        "studio_base_url": base_src,
    }
    return config, sources


async def load_effective_mcp_config(
    repo: AppSettingsRepository, env: McpRuntimeConfig
) -> McpRuntimeConfig:
    """The effective config alone — for the stdio entry point, which builds
    its server once per launch and has nothing to hot-apply."""
    config, _ = await resolve_mcp_config(repo, env)
    return config


class McpConfigService:
    """Resolve, persist and hot-apply the MCP runtime config; report the server."""

    def __init__(
        self,
        *,
        repo: AppSettingsRepository,
        env_defaults: McpRuntimeConfig,
        read_only: bool,
        apply_config: Callable[[McpRuntimeConfig], None],
        status_provider: Callable[[], Awaitable[McpServerStatus]],
    ) -> None:
        self._repo = repo
        self._env_defaults = env_defaults
        self._read_only = read_only
        self._apply_config = apply_config
        self._status_provider = status_provider

    async def get_config(self) -> McpRuntimeConfigView:
        """Effective config (db over env) + per-field sources."""
        config, sources = await resolve_mcp_config(self._repo, self._env_defaults)
        return self._view(config, sources)

    async def update_config(self, config: McpRuntimeConfig) -> McpRuntimeConfigView:
        """Validate, persist the full override set, rebuild the services in place.

        Raises:
            AppConfigReadOnlyError: writes refused on this deployment (403).
            AppConfigValidationError: invalid values (400).
        """
        require_writable(self._read_only)
        errors = validate_mcp_config(config)
        if errors:
            raise AppConfigValidationError("; ".join(errors))
        await self._repo.set_many(
            _NAMESPACE,
            {
                _KEY_MAX_ROUNDS: str(config.max_rounds),
                _KEY_MAX_READ_TOKENS: str(config.max_read_tokens),
                _KEY_BASE_URL: config.studio_base_url.strip(),
            },
        )
        return await self._apply_and_view()

    async def reset_config(self) -> McpRuntimeConfigView:
        """Drop every override — env defaults become effective again."""
        require_writable(self._read_only)
        removed = await self._repo.delete_namespace(_NAMESPACE)
        logger.info("MCP config reset to environment (%d override(s) dropped)", removed)
        return await self._apply_and_view()

    async def apply_effective(self) -> None:
        """Resolve and apply the effective config — called once at boot so
        persisted overrides win over the env from the first tool call."""
        config, _ = await resolve_mcp_config(self._repo, self._env_defaults)
        self._apply_config(config)

    async def server_status(self) -> McpServerStatus:
        """What the running server publishes — fixed until the next start."""
        return await self._status_provider()

    async def _apply_and_view(self) -> McpRuntimeConfigView:
        config, sources = await resolve_mcp_config(self._repo, self._env_defaults)
        self._apply_config(config)
        logger.info(
            "MCP config applied: max_rounds=%d max_read_tokens=%d studio_base_url=%r",
            config.max_rounds,
            config.max_read_tokens,
            config.studio_base_url,
        )
        return self._view(config, sources)

    def _view(
        self, config: McpRuntimeConfig, sources: dict[str, ConfigSource]
    ) -> McpRuntimeConfigView:
        return McpRuntimeConfigView(config=config, sources=sources, read_only=self._read_only)

"""Runtime application config service (#317) — env bootstrap, SQLite override.

Owns the precedence rule for the reasoning runtime config: persisted
`app_settings` rows (namespace `reasoning`) override the env-derived bootstrap
defaults. Reads are tolerant — an unparseable row falls back to env and keeps
`source: env` — writes are strict (`domain.app_config.validate_reasoning_config`).

The service must not import `infra/` (architecture test). Everything
infra-flavored is constructor-injected by `main.py`: the env defaults as a
domain VO, the Ollama probe behind the `LLMHostProbe` port, the hot rebuild of
`app.state.reasoning_runner` / `reasoning_service` as the `apply_config`
callback, and the diagnostics snapshot as a callable — same binding pattern as
`StoreBackendResolver.graph_writer_factory` (#audit-01).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from domain.app_config import (
    MAX_ITERATIONS_MAX,
    MAX_ITERATIONS_MIN,
    ReasoningConfig,
    ReasoningConfigView,
    validate_host_url,
    validate_reasoning_config,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from domain.app_config import ConfigSource, LLMHostProbeResult, ReasoningDiagnostics
    from domain.ports import AppSettingsRepository, LLMHostProbe

logger = logging.getLogger(__name__)

_NAMESPACE = "reasoning"
_KEY_ENABLED = "enabled"
_KEY_HOST = "ollama_host"
_KEY_MODEL = "model_id"
_KEY_MAX_ITERATIONS = "max_iterations"

_TRUE_VALUES = ("1", "true", "yes", "on")
_FALSE_VALUES = ("0", "false", "no", "off")


class AppConfigError(Exception):
    """Base error for app-config rejections, carrying an HTTP-status hint."""

    http_status: int = 500


class AppConfigValidationError(AppConfigError):
    """Raised on an invalid write-path value (maps to 400)."""

    http_status = 400


class AppConfigReadOnlyError(AppConfigError):
    """Raised when writes are refused on this deployment (maps to 403)."""

    http_status = 403


def _parse_bool(raw: str) -> bool | None:
    lowered = raw.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


def _parse_text(raw: str) -> str | None:
    stripped = raw.strip()
    return stripped or None


def _parse_iterations(raw: str) -> int | None:
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    if not (MAX_ITERATIONS_MIN <= value <= MAX_ITERATIONS_MAX):
        return None
    return value


class AppConfigService:
    """Resolve, persist and hot-apply the reasoning runtime config."""

    def __init__(
        self,
        *,
        repo: AppSettingsRepository,
        env_defaults: ReasoningConfig,
        provider_type: str,
        read_only: bool,
        probe: LLMHostProbe,
        apply_config: Callable[[ReasoningConfig], None],
        diagnostics_provider: Callable[[], ReasoningDiagnostics],
    ) -> None:
        self._repo = repo
        self._env_defaults = env_defaults
        self._provider_type = provider_type
        self._read_only = read_only
        self._probe = probe
        self._apply_config = apply_config
        self._diagnostics_provider = diagnostics_provider

    async def get_reasoning(self) -> ReasoningConfigView:
        """Effective config (db over env) + per-field sources + diagnostics."""
        config, sources = await self._resolve()
        return self._view(config, sources)

    async def update_reasoning(self, config: ReasoningConfig) -> ReasoningConfigView:
        """Validate, persist the full override set, rebuild the runner in place.

        Raises:
            AppConfigReadOnlyError: writes refused on this deployment (403).
            AppConfigValidationError: invalid values (400).
        """
        self._require_writable()
        errors = validate_reasoning_config(config)
        if errors:
            raise AppConfigValidationError("; ".join(errors))
        await self._repo.set_many(
            _NAMESPACE,
            {
                _KEY_ENABLED: "true" if config.enabled else "false",
                _KEY_HOST: config.ollama_host.strip(),
                _KEY_MODEL: config.model_id.strip(),
                _KEY_MAX_ITERATIONS: str(config.max_iterations),
            },
        )
        return await self._apply_and_view()

    async def reset_reasoning(self) -> ReasoningConfigView:
        """Drop every override — env defaults become effective again."""
        self._require_writable()
        removed = await self._repo.delete_namespace(_NAMESPACE)
        logger.info("Reasoning config reset to environment (%d override(s) dropped)", removed)
        return await self._apply_and_view()

    async def test_connection(self, host: str) -> LLMHostProbeResult:
        """Probe `host` for reachability + installed models.

        Refused on read-only deployments (the probe is a server-side request to
        a user-supplied URL — SSRF surface on a public Space). A malformed URL
        raises 400; an unreachable host is a normal result, never an error.
        """
        self._require_writable()
        error = validate_host_url(host)
        if error is not None:
            raise AppConfigValidationError(error)
        return await self._probe.probe(host)

    async def apply_effective(self) -> None:
        """Resolve and apply the effective config — called once at boot so
        persisted overrides take effect over the module-scope env build."""
        config, _ = await self._resolve()
        self._apply_config(config)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_writable(self) -> None:
        if self._read_only:
            raise AppConfigReadOnlyError(
                "Runtime configuration is read-only on this deployment (huggingface)"
            )

    async def _apply_and_view(self) -> ReasoningConfigView:
        config, sources = await self._resolve()
        self._apply_config(config)
        logger.info(
            "Reasoning config applied: enabled=%s host=%s model=%s max_iterations=%d",
            config.enabled,
            config.ollama_host,
            config.model_id,
            config.max_iterations,
        )
        return self._view(config, sources)

    async def _resolve(self) -> tuple[ReasoningConfig, dict[str, ConfigSource]]:
        rows = await self._repo.get_namespace(_NAMESPACE)
        env = self._env_defaults
        enabled, enabled_src = _pick(rows, _KEY_ENABLED, env.enabled, _parse_bool)
        host, host_src = _pick(rows, _KEY_HOST, env.ollama_host, _parse_text)
        model, model_src = _pick(rows, _KEY_MODEL, env.model_id, _parse_text)
        iters, iters_src = _pick(rows, _KEY_MAX_ITERATIONS, env.max_iterations, _parse_iterations)
        config = ReasoningConfig(
            enabled=enabled, ollama_host=host, model_id=model, max_iterations=iters
        )
        sources: dict[str, ConfigSource] = {
            "enabled": enabled_src,
            "ollama_host": host_src,
            "model_id": model_src,
            "max_iterations": iters_src,
        }
        return config, sources

    def _view(
        self, config: ReasoningConfig, sources: dict[str, ConfigSource]
    ) -> ReasoningConfigView:
        return ReasoningConfigView(
            config=config,
            sources=sources,
            provider_type=self._provider_type,
            read_only=self._read_only,
            diagnostics=self._diagnostics_provider(),
        )


def _pick(rows, key, env_value, parse):
    """One field's effective (value, source). Tolerant: a missing row means
    env; an unparseable row logs a warning and falls back to env too."""
    raw = rows.get(key)
    if raw is None:
        return env_value, "env"
    parsed = parse(raw)
    if parsed is None:
        logger.warning(
            "Ignoring unparseable app_settings row %s.%s=%r — falling back to env",
            _NAMESPACE,
            key,
            raw,
        )
        return env_value, "env"
    return parsed, "db"

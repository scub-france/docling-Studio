"""Runtime application configuration — domain model (#317).

Value objects and validation for the runtime-configurable reasoning knobs.
The precedence rule (SQLite overrides over env bootstrap defaults) lives in
`services/app_config_service.py`; this module only defines the shapes and the
write-path validation. Reads are tolerant by design — a corrupt persisted value
falls back to the env default — so validation is a pure function called on
writes, never a `__post_init__` constraint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

ConfigSource = Literal["env", "db"]

# Bounds for the RAG loop iteration cap — the settings bootstrap and the API
# write path both validate against these (infra/api import them, never the
# reverse).
MAX_ITERATIONS_MIN = 1
MAX_ITERATIONS_MAX = 20

# Defensive caps on free-text fields — they end up in logs and config rows.
HOST_MAX_LEN = 500
MODEL_ID_MAX_LEN = 200


@dataclass(frozen=True)
class ReasoningConfig:
    """The runtime-configurable reasoning knobs."""

    enabled: bool
    ollama_host: str
    model_id: str
    max_iterations: int


@dataclass(frozen=True)
class ReasoningDiagnostics:
    """Read-only reasoning-stack diagnostics surfaced by the admin panel.

    `provenance` carries the resolved docling-agent version + import path (or
    the not-importable reason) so boot failures are diagnosable from the UI.
    """

    deps_present: bool
    provenance: str
    available: bool


@dataclass(frozen=True)
class ReasoningConfigView:
    """Effective config + provenance, as consumed by the API layer.

    `sources` is keyed by `ReasoningConfig` field name and says where each
    effective value came from (`env` bootstrap default or `db` override).
    """

    config: ReasoningConfig
    sources: dict[str, ConfigSource]
    provider_type: str
    read_only: bool
    diagnostics: ReasoningDiagnostics


@dataclass(frozen=True)
class LLMHostProbeResult:
    """Outcome of probing an LLM host for reachability + installed models."""

    reachable: bool
    models: list[str] = field(default_factory=list)
    error: str | None = None


def validate_host_url(host: str) -> str | None:
    """Return an error message when `host` is not a well-formed http(s) URL."""
    if not host.strip():
        return "ollama_host must not be empty"
    if len(host) > HOST_MAX_LEN:
        return f"ollama_host must be <= {HOST_MAX_LEN} characters"
    parsed = urlparse(host)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return f"ollama_host must be an http(s) URL (got '{host}')"
    return None


def validate_reasoning_config(config: ReasoningConfig) -> list[str]:
    """Validate a write-path config. Returns human-readable errors (empty = valid)."""
    errors: list[str] = []
    host_error = validate_host_url(config.ollama_host)
    if host_error is not None:
        errors.append(host_error)
    if not config.model_id.strip():
        errors.append("model_id must not be empty")
    elif len(config.model_id) > MODEL_ID_MAX_LEN:
        errors.append(f"model_id must be <= {MODEL_ID_MAX_LEN} characters")
    if not (MAX_ITERATIONS_MIN <= config.max_iterations <= MAX_ITERATIONS_MAX):
        errors.append(
            f"max_iterations must be between {MAX_ITERATIONS_MIN} and "
            f"{MAX_ITERATIONS_MAX} (got {config.max_iterations})"
        )
    return errors

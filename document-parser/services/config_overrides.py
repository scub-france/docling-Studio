"""Runtime config overrides — the rules every config service shares (#317, #364).

Env vars are bootstrap defaults; `app_settings` rows override them. Reads are
tolerant: a missing row means env, an unparseable one logs a warning and means
env too. Writes are strict and refused on a read-only deployment. The errors
carry the HTTP status the API layer maps them to.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from domain.app_config import ConfigSource

logger = logging.getLogger(__name__)

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


def require_writable(read_only: bool) -> None:
    """Refuse a write on a read-only deployment (the Hugging Face Space)."""
    if read_only:
        raise AppConfigReadOnlyError(
            "Runtime configuration is read-only on this deployment (huggingface)"
        )


def parse_bool(raw: str) -> bool | None:
    lowered = raw.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


def parse_text(raw: str) -> str | None:
    """A non-empty string; empty counts as unparseable."""
    stripped = raw.strip()
    return stripped or None


def parse_int_between(low: int, high: int) -> Callable[[str], int | None]:
    """A parser for an int within `[low, high]`; anything else is unparseable."""

    def parse(raw: str) -> int | None:
        try:
            value = int(raw.strip())
        except ValueError:
            return None
        return value if low <= value <= high else None

    return parse


def pick[T](
    rows: dict[str, str],
    key: str,
    env_value: T,
    parse: Callable[[str], T | None],
    *,
    namespace: str,
) -> tuple[T, ConfigSource]:
    """One field's effective `(value, source)`: the row when it parses, env otherwise."""
    raw = rows.get(key)
    if raw is None:
        return env_value, "env"
    parsed = parse(raw)
    if parsed is None:
        logger.warning(
            "Ignoring unparseable app_settings row %s.%s=%r — falling back to env",
            namespace,
            key,
            raw,
        )
        return env_value, "env"
    return parsed, "db"

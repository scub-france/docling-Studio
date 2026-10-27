"""MCP runtime configuration — domain model (#364).

Two kinds of facts the admin panel shows about the MCP surface:

- `McpRuntimeConfig`: the knobs that change on the next tool call — the round
  cap, the read ceiling, the deep-link base. Env vars seed them, `app_settings`
  rows (namespace `mcp`) override them; the precedence lives in
  `services/mcp_config_service.py`.
- `McpServerStatus`: what the running server publishes. Fixed at boot — the
  server is built at import and the stateless transport cannot tell a client
  its tool list changed — so it is reported, never edited.

Validation is a pure function called on writes only: reads are tolerant, a
corrupt persisted value falls back to its env default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from domain.app_config import ConfigSource

# The round cap: one section read per round. Same bounds as the reasoning
# loop's iteration cap, the other runner of the same idea.
MAX_ROUNDS_MIN = 1
MAX_ROUNDS_MAX = 20

# The read ceiling, in tokens. Below 100 a read cannot carry a paragraph; above
# 32 000 one call would flood a client's context.
READ_TOKENS_MIN = 100
READ_TOKENS_MAX = 32_000

BASE_URL_MAX_LEN = 500


@dataclass(frozen=True)
class McpRuntimeConfig:
    """The MCP knobs that apply on the next tool call, with no restart."""

    max_rounds: int
    max_read_tokens: int
    # Empty: citations carry no deep link.
    studio_base_url: str


@dataclass(frozen=True)
class McpRuntimeConfigView:
    """Effective config + where each value comes from (`env` or `db`)."""

    config: McpRuntimeConfig
    sources: dict[str, ConfigSource]
    read_only: bool


@dataclass(frozen=True)
class McpToolInfo:
    """One tool as the running server publishes it.

    `visibility` is who may call it: `model`, `app` (a card's own fetch), or
    both. `card` is true when the tool renders an MCP Apps card.
    """

    name: str
    visibility: tuple[str, ...]
    card: bool


@dataclass(frozen=True)
class McpServerStatus:
    """The HTTP transport as it was mounted at boot. Restart-only facts."""

    enabled: bool
    path: str
    allowed_hosts: tuple[str, ...]
    apps_enabled: bool
    citation_card: bool
    tools: tuple[McpToolInfo, ...] = ()
    prompts: tuple[str, ...] = ()


def validate_base_url(url: str) -> str | None:
    """Error message when `url` is neither empty nor a well-formed http(s) URL."""
    stripped = url.strip()
    if not stripped:
        return None
    if len(stripped) > BASE_URL_MAX_LEN:
        return f"studio_base_url must be <= {BASE_URL_MAX_LEN} characters"
    parsed = urlparse(stripped)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return f"studio_base_url must be empty or an http(s) URL (got '{stripped}')"
    return None


def validate_mcp_config(config: McpRuntimeConfig) -> list[str]:
    """Validate a write-path config. Returns human-readable errors (empty = valid)."""
    errors: list[str] = []
    if not (MAX_ROUNDS_MIN <= config.max_rounds <= MAX_ROUNDS_MAX):
        errors.append(
            f"max_rounds must be between {MAX_ROUNDS_MIN} and {MAX_ROUNDS_MAX} "
            f"(got {config.max_rounds})"
        )
    if not (READ_TOKENS_MIN <= config.max_read_tokens <= READ_TOKENS_MAX):
        errors.append(
            f"max_read_tokens must be between {READ_TOKENS_MIN} and {READ_TOKENS_MAX} "
            f"(got {config.max_read_tokens})"
        )
    url_error = validate_base_url(config.studio_base_url)
    if url_error is not None:
        errors.append(url_error)
    return errors

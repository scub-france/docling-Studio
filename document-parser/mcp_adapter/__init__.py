"""MCP document server — the agent-facing driving adapter.

Imports of the `mcp` SDK are deferred to `build_mcp_server` so the package is
importable without the optional dependency, exactly like
`infra.docling_agent_reasoning` does for the reasoning stack: a backend
installed without `--group mcp` boots normally, and the surface simply stays
unmounted.

The package is named `mcp_adapter`, not `mcp`, because a top-level `mcp`
package in the backend root would shadow the SDK on `sys.path`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.navigation_service import NavigationService

__all__ = ["build_mcp_server", "deps_present", "deps_provenance"]


def deps_present() -> bool:
    """True when the MCP SDK is importable in this interpreter."""
    try:
        import mcp.server.mcpserver  # noqa: F401
    except Exception:
        return False
    return True


def deps_provenance() -> str:
    """Human-readable provenance of the SDK, for boot logs and diagnostics."""
    try:
        from importlib.metadata import version

        import mcp

        return f"mcp {version('mcp')} from {getattr(mcp, '__file__', '?')}"
    except Exception as exc:
        return f"mcp unavailable ({exc})"


def build_mcp_server(navigation: Callable[[], NavigationService], **kwargs: Any) -> Any:
    """Build the MCP server. Raises ImportError when the SDK is absent."""
    from mcp_adapter.server import build_mcp_server as _build

    return _build(navigation, **kwargs)

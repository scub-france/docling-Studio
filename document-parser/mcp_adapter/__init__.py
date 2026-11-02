"""MCP document server — the agent-facing driving adapter.

The SDK is imported when a server is built, not when this package is: a
backend with MCP_ENABLED off never loads it.

The package is named `mcp_adapter`, not `mcp`, because a top-level `mcp`
package in the backend root would shadow the SDK on `sys.path`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.document_tools import DocumentTools

__all__ = ["build_mcp_server"]


def build_mcp_server(tools: Callable[[], DocumentTools], **kwargs: Any) -> Any:
    """Build the MCP server over lazily resolved document services."""
    from mcp_adapter.server import build_mcp_server as _build

    return _build(tools, **kwargs)

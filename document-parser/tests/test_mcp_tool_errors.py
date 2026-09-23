"""The one place a failure becomes text an agent reads.

Only the protocol's own rejections carry their message to the client; any
other exception is a crash whose text belongs to the server log. Cancellation
is not a failure at all, and passes through untouched.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip(
    "mcp.server.mcpserver",
    reason="MCP SDK not installed — `uv sync --group mcp` to exercise the adapter",
)

from mcp.server.mcpserver.exceptions import ToolError

from mcp_adapter.tool_errors import ToolErrors
from services.navigation_errors import RefNotFoundError


async def test_a_service_rejection_reaches_the_agent_verbatim():
    with pytest.raises(ToolError, match="Ref '#/texts/9' does not exist"):
        async with ToolErrors():
            raise RefNotFoundError("Ref '#/texts/9' does not exist")


async def test_a_crash_keeps_its_text_on_the_server():
    with pytest.raises(ToolError) as caught:
        async with ToolErrors():
            raise FileNotFoundError("/srv/uploads/contrat-confidentiel.pdf")
    assert "contrat-confidentiel" not in str(caught.value)


async def test_cancellation_is_not_turned_into_a_tool_error():
    with pytest.raises(asyncio.CancelledError):
        async with ToolErrors():
            raise asyncio.CancelledError

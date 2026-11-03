"""The one place a failure becomes text an agent reads.

Only the protocol's own rejections carry their message to the client; any
other exception is a crash whose text belongs to the server log. Cancellation
is not a failure at all, and passes through untouched.
"""

from __future__ import annotations

import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_adapter.tool_errors import ToolErrors
from services.chunk_service import ChunkServiceError
from services.navigation_errors import DocumentNotFoundError, RefNotFoundError


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


async def test_a_missing_document_reaches_the_agent_verbatim():
    # The one `DocumentNotFoundError` is shared with the chunk and analysis
    # services; it stays in the navigation family this adapter reports.
    with pytest.raises(ToolError, match="Document not found: d1"):
        async with ToolErrors():
            raise DocumentNotFoundError("Document not found: d1")


async def test_another_service_family_keeps_its_text_on_the_server():
    # Every service error is a `ServiceError` now; the filter must not have
    # widened to that base — a chunk-service rejection is not the agent's.
    with pytest.raises(ToolError) as caught:
        async with ToolErrors():
            raise ChunkServiceError("Chunker not configured", http_status=503)
    assert "Chunker" not in str(caught.value)

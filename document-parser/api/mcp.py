"""MCP server API (#364) — what the running MCP transport publishes.

One read-only route on its own aggregate (#269): the server as it was mounted
at boot — on or off, its path, its host allow-list, the tools and prompts it
publishes. Nothing here is writable: these facts change only with the
environment and a restart. The editable budgets live under `/api/config/mcp`.
"""

from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: TC001
from api.schemas import McpServerResponse

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/server", response_model=McpServerResponse)
async def get_mcp_server(service: deps.McpConfigServiceDep) -> McpServerResponse:
    return McpServerResponse.from_status(await service.server_status())

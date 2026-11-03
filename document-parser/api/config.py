"""Runtime configuration API (#317, #364) — HTTP layer over the config services.

DDD-granular routes (#269), one aggregate per path: the reasoning runtime
config (read, replace, reset to environment, probe an Ollama host) and the MCP
runtime config (read, replace, reset). The router only maps DTOs — the
services own precedence, validation, persistence and the hot rebuild, and
their typed errors (400 invalid values, 403 read-only deployment) reach the
app-level handler (`api/errors.py`). Zero imports from infra / persistence.
"""

from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: TC001
from api.schemas import (
    McpConfigResponse,
    McpConfigUpdateRequest,
    ReasoningConfigResponse,
    ReasoningConfigUpdateRequest,
    ReasoningProbeRequest,
    ReasoningProbeResponse,
)
from domain.app_config import ReasoningConfig
from domain.mcp_config import McpRuntimeConfig

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/reasoning", response_model=ReasoningConfigResponse)
async def get_reasoning_config(service: deps.AppConfigServiceDep) -> ReasoningConfigResponse:
    return ReasoningConfigResponse.from_view(await service.get_reasoning())


@router.put("/reasoning", response_model=ReasoningConfigResponse)
async def put_reasoning_config(
    body: ReasoningConfigUpdateRequest, service: deps.AppConfigServiceDep
) -> ReasoningConfigResponse:
    config = ReasoningConfig(
        enabled=body.enabled,
        ollama_host=body.ollama_host,
        model_id=body.model_id,
        max_iterations=body.max_iterations,
    )
    view = await service.update_reasoning(config)
    return ReasoningConfigResponse.from_view(view)


@router.delete("/reasoning", response_model=ReasoningConfigResponse)
async def reset_reasoning_config(service: deps.AppConfigServiceDep) -> ReasoningConfigResponse:
    view = await service.reset_reasoning()
    return ReasoningConfigResponse.from_view(view)


@router.post("/reasoning/test", response_model=ReasoningProbeResponse)
async def test_reasoning_connection(
    body: ReasoningProbeRequest, service: deps.AppConfigServiceDep
) -> ReasoningProbeResponse:
    result = await service.test_connection(body.host)
    return ReasoningProbeResponse.from_result(result)


@router.get("/mcp", response_model=McpConfigResponse)
async def get_mcp_config(service: deps.McpConfigServiceDep) -> McpConfigResponse:
    return McpConfigResponse.from_view(await service.get_config())


@router.put("/mcp", response_model=McpConfigResponse)
async def put_mcp_config(
    body: McpConfigUpdateRequest, service: deps.McpConfigServiceDep
) -> McpConfigResponse:
    config = McpRuntimeConfig(
        max_rounds=body.max_rounds,
        max_read_tokens=body.max_read_tokens,
        studio_base_url=body.studio_base_url,
        enabled=body.enabled,
    )
    view = await service.update_config(config)
    return McpConfigResponse.from_view(view)


@router.delete("/mcp", response_model=McpConfigResponse)
async def reset_mcp_config(service: deps.McpConfigServiceDep) -> McpConfigResponse:
    view = await service.reset_config()
    return McpConfigResponse.from_view(view)

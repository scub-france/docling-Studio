"""Runtime configuration API (#317) — HTTP layer over `AppConfigService`.

Four DDD-granular routes (#269) on the reasoning runtime-config aggregate:
read the effective config, replace the override set, drop it (reset to
environment), probe an Ollama host. The router only maps DTOs and translates
the service's typed errors (`http_status` hint) into responses — the service
owns precedence, validation, persistence and the hot rebuild. Zero imports
from infra / persistence.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import deps  # noqa: TC001
from api.schemas import (
    ReasoningConfigResponse,
    ReasoningConfigUpdateRequest,
    ReasoningProbeRequest,
    ReasoningProbeResponse,
)
from domain.app_config import ReasoningConfig
from services.app_config_service import AppConfigError

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
    try:
        view = await service.update_reasoning(config)
    except AppConfigError as exc:
        # 400 (invalid values) / 403 (read-only deployment) — the service
        # carries the status hint, like `ReasoningServiceError`.
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return ReasoningConfigResponse.from_view(view)


@router.delete("/reasoning", response_model=ReasoningConfigResponse)
async def reset_reasoning_config(service: deps.AppConfigServiceDep) -> ReasoningConfigResponse:
    try:
        view = await service.reset_reasoning()
    except AppConfigError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return ReasoningConfigResponse.from_view(view)


@router.post("/reasoning/test", response_model=ReasoningProbeResponse)
async def test_reasoning_connection(
    body: ReasoningProbeRequest, service: deps.AppConfigServiceDep
) -> ReasoningProbeResponse:
    try:
        result = await service.test_connection(body.host)
    except AppConfigError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return ReasoningProbeResponse.from_result(result)

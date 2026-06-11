"""Reasoning API — HTTP layer over `ReasoningService`.

`POST /api/documents/:id/reasoning` runs the wired-up reasoning service
against the document's latest completed analysis and returns a camelCase
`ReasoningTraceResponse` (the Parse-view trace timeline contract, #303).

This module has zero coupling to docling-agent / mellea / docling-core. The
service (set on `app.state.reasoning_service` at boot) owns the runner and
the analysis lookup; the router only maps DTOs and translates the service's
typed errors into HTTP status codes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    ReasoningRunRequest,
    ReasoningStepResponse,
    ReasoningTraceResponse,
)
from domain.ports import ReasoningParseError
from services.reasoning_service import ReasoningService, ReasoningServiceError

if TYPE_CHECKING:
    from domain.value_objects import ReasoningTrace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["reasoning"])


def _service(request: Request) -> ReasoningService:
    svc = getattr(request.app.state, "reasoning_service", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="ReasoningService not wired")
    return svc


def _to_response(trace: ReasoningTrace) -> ReasoningTraceResponse:
    return ReasoningTraceResponse(
        answer=trace.answer,
        converged=trace.converged,
        steps=[
            ReasoningStepResponse(
                id=step.id,
                kind=step.kind.value,
                title=step.title,
                summary=step.summary,
                duration_ms=step.duration_ms,
                token_count=step.token_count,
                citations=step.citations,
                payload=step.payload,
            )
            for step in trace.steps
        ],
        total_duration_ms=trace.total_duration_ms,
        tokens_in=trace.tokens_in,
        tokens_out=trace.tokens_out,
        model_id=trace.model_id,
    )


@router.post("/{doc_id}/reasoning", response_model=ReasoningTraceResponse)
async def run_reasoning(
    doc_id: str, body: ReasoningRunRequest, request: Request
) -> ReasoningTraceResponse:
    try:
        trace = await _service(request).run(doc_id, body.query, body.model_id)
    except ReasoningServiceError as exc:
        # 503 (unavailable) / 400 (empty query) / 404 (no analysis) — the
        # service carries the status hint.
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    except ReasoningParseError as exc:
        # The upstream LLM couldn't produce a parseable answer after retries.
        # 502 Bad Gateway — not our fault — with guidance the UI can show.
        raise HTTPException(
            status_code=502,
            detail=(
                f"The model '{exc.model_id}' couldn't produce a parseable "
                "answer after retries. Try a different model (e.g. "
                "mistral-small3.2) or rephrase the question."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Reasoning run failed for doc %s", doc_id)
        raise HTTPException(status_code=500, detail=f"Reasoning run failed: {exc}") from exc

    return _to_response(trace)

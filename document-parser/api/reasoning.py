"""Reasoning API — HTTP layer over `ReasoningService`.

`POST /api/documents/:id/reasoning` runs the wired-up reasoning service
against the document's latest completed analysis and returns a camelCase
`ReasoningTraceResponse` (the Parse-view trace timeline contract, #303).

This module has zero coupling to docling-agent / mellea / docling-core. The
service (resolved from the typed `AppState` container) owns the runner and
the analysis lookup; the router only maps DTOs and translates the service's
typed errors into HTTP status codes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api import deps  # noqa: TC001
from api.schemas import ReasoningRunRequest, ReasoningTraceResponse
from domain.ports import ReasoningParseError
from services.reasoning_service import ReasoningServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["reasoning"])


@router.post("/{doc_id}/reasoning", response_model=ReasoningTraceResponse)
async def run_reasoning(
    doc_id: str, body: ReasoningRunRequest, service: deps.ReasoningServiceDep
) -> ReasoningTraceResponse:
    try:
        trace = await service.run(doc_id, body.query, body.model_id)
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

    return ReasoningTraceResponse.from_trace(trace)

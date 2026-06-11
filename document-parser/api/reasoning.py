"""Reasoning API — HTTP layer over a `ReasoningRunner` port.

`POST /api/documents/:id/reasoning` invokes the wired-up `ReasoningRunner`
against the stored `DoclingDocument` and returns a `ReasoningResultResponse`
in the same shape the v1 import dialog already consumes — so the frontend
overlay code is fully reused.

This module has zero coupling to docling-agent / mellea / docling-core. The
runner (concrete adapter in `infra/docling_agent_reasoning.py`) is set on
`app.state.reasoning_runner` at boot when `REASONING_ENABLED=true` and the
deps are importable. Otherwise it stays `None` and we 503.

Sync blocking call offloaded to a thread by the adapter so we don't stall
the event loop. No streaming at this step (see design doc §7 for v2 SSE plan).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import deps  # noqa: TC001
from domain.ports import ReasoningParseError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["reasoning"])


class ReasoningRunRequest(BaseModel):
    query: str
    # Optional per-run override; falls back to the runner's default model.
    model_id: str | None = None


class ReasoningIterationResponse(BaseModel):
    iteration: int
    section_ref: str
    reason: str
    section_text_length: int
    can_answer: bool
    response: str


class ReasoningResultResponse(BaseModel):
    answer: str
    iterations: list[ReasoningIterationResponse]
    converged: bool


@router.post("/{doc_id}/reasoning", response_model=ReasoningResultResponse)
async def run_reasoning(
    doc_id: str,
    body: ReasoningRunRequest,
    runner: deps.ReasoningRunnerDep,
    analysis_repo: deps.AnalysisRepoDep,
) -> ReasoningResultResponse:
    if runner is None or not runner.is_available:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live reasoning disabled (REASONING_ENABLED=false or docling-agent not installed)"
            ),
        )

    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")
    latest = await analysis_repo.find_latest_completed_by_document(doc_id)
    if latest is None or not latest.document_json:
        raise HTTPException(
            status_code=404,
            detail=f"No completed analysis with document_json for {doc_id}",
        )

    try:
        result = await runner.run(
            document_json=latest.document_json,
            query=body.query,
            model_id=body.model_id,
        )
    except ReasoningParseError as e:
        # The upstream LLM couldn't produce a parseable answer after retries.
        # 502 Bad Gateway — not our fault — with guidance the UI can show.
        raise HTTPException(
            status_code=502,
            detail=(
                f"The model '{e.model_id}' couldn't produce a parseable "
                "answer after retries. Try a different model (e.g. "
                "mistral-small3.2) or rephrase the question."
            ),
        ) from e
    except Exception as e:
        logger.exception("Reasoning loop failed for doc %s", doc_id)
        raise HTTPException(status_code=500, detail=f"Reasoning loop failed: {e}") from e

    return ReasoningResultResponse(
        answer=result.answer,
        iterations=[
            ReasoningIterationResponse(
                iteration=it.iteration,
                section_ref=it.section_ref,
                reason=it.reason,
                section_text_length=it.section_text_length,
                can_answer=it.can_answer,
                response=it.response,
            )
            for it in result.iterations
        ],
        converged=result.converged,
    )

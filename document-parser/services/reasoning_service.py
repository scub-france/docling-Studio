"""Reasoning service — orchestrates a single live-reasoning run.

Sits between the API router and the `ReasoningRunner` port so `api/reasoning.py`
stops reaching into `app.state.analysis_repo` directly (API → services →
persistence/infra). Mirrors `GraphService` conventions: typed errors carry an
`http_status` hint the router translates into a response.

The service owns the use-case sequencing — validate the query, resolve the
latest completed analysis, time the run, project the raw `ReasoningResult`
onto a `ReasoningTrace` via the pure `domain.trace_builder`. It must not
import `infra/` (architecture test): the default model id is constructor-
injected from settings by `main.py`, like every other service.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from domain.trace_builder import build_trace

if TYPE_CHECKING:
    from domain.ports import AnalysisRepository, ReasoningRunner
    from domain.value_objects import ReasoningTrace


class ReasoningServiceError(Exception):
    """Base error for reasoning-service rejections, carrying an HTTP-status hint."""

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class ReasoningUnavailableError(ReasoningServiceError):
    """Raised when no runner is wired in, or it reports itself unavailable
    (REASONING_ENABLED=false or docling-agent / mellea not importable)."""

    http_status = 503


class ReasoningEmptyQueryError(ReasoningServiceError):
    """Raised on an empty / whitespace-only query.

    Kept as an explicit service-side check (not a Pydantic `min_length`) so
    the wire contract stays 400 — `min_length` returns 422 and would accept a
    whitespace-only string.
    """

    http_status = 400


class ReasoningNoAnalysisError(ReasoningServiceError):
    """Raised when the document has no completed analysis carrying
    `document_json` to reason over."""

    http_status = 404


class ReasoningService:
    """Orchestrates one reasoning run end to end."""

    def __init__(
        self,
        *,
        runner: ReasoningRunner | None,
        analysis_repo: AnalysisRepository,
        default_model_id: str,
    ) -> None:
        self._runner = runner
        self._analyses = analysis_repo
        self._default_model_id = default_model_id

    async def run(
        self,
        doc_id: str,
        query: str,
        model_id: str | None = None,
    ) -> ReasoningTrace:
        """Run reasoning over the document's latest completed analysis.

        Raises:
            ReasoningUnavailableError: runner unwired / unavailable (503).
            ReasoningEmptyQueryError: empty or whitespace-only query (400).
            ReasoningNoAnalysisError: no completed analysis with
                `document_json` for this document (404).
            ReasoningParseError: the model produced no parseable answer
                (propagates from the runner; router maps it to 502).
        """
        if self._runner is None or not self._runner.is_available:
            raise ReasoningUnavailableError(
                "Live reasoning disabled (REASONING_ENABLED=false or docling-agent not installed)"
            )

        if not query.strip():
            raise ReasoningEmptyQueryError("Query must not be empty")

        latest = await self._analyses.find_latest_completed_by_document(doc_id)
        if latest is None or not latest.document_json:
            raise ReasoningNoAnalysisError(f"No completed analysis with document_json for {doc_id}")

        effective_model = model_id or self._default_model_id
        t0 = time.perf_counter()
        result = await self._runner.run(
            document_json=latest.document_json,
            query=query,
            model_id=model_id,
        )
        wall_ms = int((time.perf_counter() - t0) * 1000)

        return build_trace(
            result=result,
            model_id=effective_model,
            total_duration_ms=wall_ms,
        )

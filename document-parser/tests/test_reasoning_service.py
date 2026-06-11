"""Tests for `services.reasoning_service.ReasoningService`.

Covers the use-case sequencing the router relies on: availability gating
(503), empty-query rejection (400), missing-analysis (404), wall-clock
capture feeding the trace, default-model injection, and parse-error
passthrough (502 is mapped by the router).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from domain.ports import ReasoningParseError
from domain.value_objects import ReasoningIteration, ReasoningResult, ReasoningTrace
from services.reasoning_service import (
    ReasoningEmptyQueryError,
    ReasoningNoAnalysisError,
    ReasoningService,
    ReasoningUnavailableError,
)


class _FakeRunner:
    def __init__(self, *, available: bool = True, result=None, exc: Exception | None = None):
        self._available = available
        self._result = result
        self._exc = exc
        self.calls: list[dict] = []

    @property
    def is_available(self) -> bool:
        return self._available

    async def run(self, *, document_json: str, query: str, model_id=None) -> ReasoningResult:
        self.calls.append({"document_json": document_json, "query": query, "model_id": model_id})
        if self._exc is not None:
            raise self._exc
        return self._result


class _FakeAnalysisRepo:
    def __init__(self, *, latest=None):
        self._latest = latest

    async def find_latest_completed_by_document(self, document_id: str):
        return self._latest


def _result(**overrides) -> ReasoningResult:
    fields = {
        "answer": "the answer",
        "iterations": [
            ReasoningIteration(
                iteration=1,
                section_ref="#/texts/0",
                reason="r",
                section_text_length=10,
                can_answer=True,
                response="a",
            )
        ],
        "converged": True,
        "duration_ms": 0,
        "model_id": "",
    }
    fields.update(overrides)
    return ReasoningResult(**fields)


def _service(*, runner, latest=None, default_model_id="default:7b") -> ReasoningService:
    return ReasoningService(
        runner=runner,
        analysis_repo=_FakeAnalysisRepo(latest=latest),
        default_model_id=default_model_id,
    )


async def test_503_when_runner_is_none():
    svc = _service(runner=None)
    with pytest.raises(ReasoningUnavailableError) as exc:
        await svc.run("doc-1", "question")
    assert exc.value.http_status == 503


async def test_503_when_runner_unavailable():
    svc = _service(runner=_FakeRunner(available=False))
    with pytest.raises(ReasoningUnavailableError):
        await svc.run("doc-1", "question")


async def test_400_on_empty_query():
    svc = _service(runner=_FakeRunner(result=_result()))
    with pytest.raises(ReasoningEmptyQueryError) as exc:
        await svc.run("doc-1", "")
    assert exc.value.http_status == 400


async def test_400_on_whitespace_query():
    svc = _service(runner=_FakeRunner(result=_result()))
    with pytest.raises(ReasoningEmptyQueryError):
        await svc.run("doc-1", "   \n\t ")


async def test_404_when_no_analysis():
    svc = _service(runner=_FakeRunner(result=_result()), latest=None)
    with pytest.raises(ReasoningNoAnalysisError) as exc:
        await svc.run("doc-1", "question")
    assert exc.value.http_status == 404


async def test_404_when_analysis_has_no_document_json():
    latest = SimpleNamespace(document_json="", document_filename="f.pdf")
    svc = _service(runner=_FakeRunner(result=_result()), latest=latest)
    with pytest.raises(ReasoningNoAnalysisError):
        await svc.run("doc-1", "question")


async def test_runs_and_returns_trace():
    latest = SimpleNamespace(document_json='{"doc": 1}', document_filename="f.pdf")
    runner = _FakeRunner(result=_result(answer="42"))
    svc = _service(runner=runner, latest=latest)

    trace = await svc.run("doc-1", "question")

    assert isinstance(trace, ReasoningTrace)
    assert trace.answer == "42"
    assert len(trace.steps) == 1
    # the runner received the stored document_json
    assert runner.calls[0]["document_json"] == '{"doc": 1}'


async def test_wall_clock_feeds_total_duration():
    latest = SimpleNamespace(document_json="{}", document_filename="f")

    class _SlowRunner(_FakeRunner):
        async def run(self, *, document_json, query, model_id=None):
            await asyncio.sleep(0.01)  # 10 ms — proves wall-clock is measured
            return _result(duration_ms=0)  # no agent timing → wall-clock wins

    svc = _service(runner=_SlowRunner(), latest=latest)
    trace = await svc.run("doc-1", "question")
    assert trace.total_duration_ms >= 5


async def test_default_model_injected_when_result_unstamped():
    latest = SimpleNamespace(document_json="{}", document_filename="f")
    runner = _FakeRunner(result=_result(model_id=""))
    svc = _service(runner=runner, latest=latest, default_model_id="granite:8b")

    trace = await svc.run("doc-1", "question")

    assert trace.model_id == "granite:8b"
    # no per-call override → runner sees model_id=None
    assert runner.calls[0]["model_id"] is None


async def test_model_override_passed_through():
    latest = SimpleNamespace(document_json="{}", document_filename="f")
    runner = _FakeRunner(result=_result(model_id=""))
    svc = _service(runner=runner, latest=latest, default_model_id="default:7b")

    trace = await svc.run("doc-1", "question", model_id="override:13b")

    assert runner.calls[0]["model_id"] == "override:13b"
    assert trace.model_id == "override:13b"


async def test_parse_error_propagates():
    latest = SimpleNamespace(document_json="{}", document_filename="f")
    runner = _FakeRunner(exc=ReasoningParseError(model_id="m", reason="no json"))
    svc = _service(runner=runner, latest=latest)

    with pytest.raises(ReasoningParseError):
        await svc.run("doc-1", "question")

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
from tests.analysis_state_helpers import set_selection


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


class _FakeCurrentAnalysis:
    """The `CurrentAnalysisReader` port: `latest` stands for the current analysis."""

    def __init__(self, *, latest=None):
        self._latest = latest

    async def load_current_original(self, document_id: str):
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
        current_analysis=_FakeCurrentAnalysis(latest=latest),
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


async def _seed_two_analyses(tmp_path, monkeypatch):
    """A document analysed twice, on SQLite: `newer` completed last and is active."""
    from domain.models import AnalysisJob, AnalysisOutput, Document
    from persistence import database
    from persistence.analysis_repo import SqliteAnalysisRepository
    from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
    from persistence.document_repo import SqliteDocumentRepository
    from services.current_analysis import CurrentAnalysisResolver

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "ask.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(
        Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a.pdf")
    )
    analyses = SqliteAnalysisRepository()
    for job_id in ("older", "newer"):
        job = AnalysisJob(id=job_id, document_id="doc-1")
        await analyses.insert(job)
        job.mark_running()
        job.mark_completed(
            AnalysisOutput(
                markdown=job_id, html="", pages_json="[]", document_json=f'{{"v": "{job_id}"}}'
            )
        )
        await analyses.complete_and_select(job)
    states = SqliteDocumentAnalysisRepository()
    return states, CurrentAnalysisResolver(state_repo=states, analysis_repo=analyses)


async def test_reads_the_active_analysis_not_the_latest(tmp_path, monkeypatch):
    """02-2.3.1: after a restore of the older analysis, Ask reads it, as stored."""
    _, current = await _seed_two_analyses(tmp_path, monkeypatch)
    await set_selection("doc-1", "older")
    runner = _FakeRunner(result=_result())
    svc = ReasoningService(runner=runner, current_analysis=current, default_model_id="m")

    await svc.run("doc-1", "question")

    assert runner.calls[0]["document_json"] == '{"v": "older"}'


async def test_404_when_the_document_was_left_without_an_active_analysis(tmp_path, monkeypatch):
    """A cleared selection is a choice: Ask does not fall back to the latest analysis."""
    _, current = await _seed_two_analyses(tmp_path, monkeypatch)
    await set_selection("doc-1", None)
    svc = ReasoningService(
        runner=_FakeRunner(result=_result()), current_analysis=current, default_model_id="m"
    )

    with pytest.raises(ReasoningNoAnalysisError):
        await svc.run("doc-1", "question")

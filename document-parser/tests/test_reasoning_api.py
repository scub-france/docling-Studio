"""Tests for `api.reasoning` — the HTTP layer over `ReasoningService`.

The API layer is decoupled from docling-agent / mellea / docling-core. Tests
wire a real `ReasoningService` (so the full router → service → runner path and
its status-code mapping are exercised) backed by a fake `ReasoningRunner` and
a fake analysis repo, and assert the camelCase trace contract on the wire.

Adapter behaviour (the actual docling-agent integration) is tested separately
in `tests/test_docling_agent_reasoning.py`; the projection rules in
`tests/test_trace_builder.py`.
"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.reasoning import router
from domain.ports import ReasoningParseError
from domain.value_objects import ReasoningIteration, ReasoningResult
from services.reasoning_service import ReasoningService
from tests.app_state import wire_state


def _sample_result() -> ReasoningResult:
    return ReasoningResult(
        answer="stub answer",
        converged=True,
        iterations=[
            ReasoningIteration(
                iteration=1,
                section_ref="#/texts/0",
                reason="looks relevant",
                section_text_length=42,
                can_answer=True,
                response="stub answer",
                duration_ms=120,
            )
        ],
        duration_ms=300,
        model_id="granite3.3:8b",
    )


class _FakeRunner:
    """In-memory ReasoningRunner. Records the last call so tests can assert on
    the args without touching docling-agent."""

    def __init__(
        self,
        *,
        result: ReasoningResult | None = None,
        is_available: bool = True,
        raises: Exception | None = None,
    ) -> None:
        self._result = result or _sample_result()
        self._is_available = is_available
        self._raises = raises
        self.last_call: dict | None = None

    @property
    def is_available(self) -> bool:
        return self._is_available

    async def run(self, *, document_json: str, query: str, model_id: str | None = None):
        self.last_call = {"document_json": document_json, "query": query, "model_id": model_id}
        if self._raises is not None:
            raise self._raises
        return self._result


class _FakeAnalysisRepo:
    def __init__(self, *, latest=None):
        self._latest = latest

    async def find_latest_completed_by_document(self, document_id: str):
        return self._latest


_DEFAULT_LATEST = SimpleNamespace(document_json='{"stub": true}', document_filename="hello.pdf")


def _make_client(
    *,
    runner: _FakeRunner | None,
    latest=_DEFAULT_LATEST,
    default_model_id: str = "default:7b",
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    wire_state(
        app,
        reasoning_service=ReasoningService(
            runner=runner,
            analysis_repo=_FakeAnalysisRepo(latest=latest),
            default_model_id=default_model_id,
        ),
    )
    return TestClient(app)


class TestReasoningDisabled:
    def test_503_when_runner_not_wired(self) -> None:
        client = _make_client(runner=None)
        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})
        assert resp.status_code == 503
        assert "REASONING_ENABLED" in resp.json()["detail"]

    def test_503_when_runner_unavailable(self) -> None:
        client = _make_client(runner=_FakeRunner(is_available=False))
        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})
        assert resp.status_code == 503


class TestReasoningValidation:
    def test_400_when_query_empty(self) -> None:
        client = _make_client(runner=_FakeRunner())
        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "   "})
        assert resp.status_code == 400

    def test_404_when_no_completed_analysis(self) -> None:
        client = _make_client(runner=_FakeRunner(), latest=None)
        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})
        assert resp.status_code == 404


class TestReasoningSuccess:
    def test_returns_camelcase_trace_shape(self) -> None:
        client = _make_client(runner=_FakeRunner())

        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "What is this?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "stub answer"
        assert data["converged"] is True
        assert data["totalDurationMs"] == 300  # result.duration_ms preferred
        assert data["modelId"] == "granite3.3:8b"
        assert data["tokensIn"] == 0
        assert data["tokensOut"] == 0
        assert len(data["steps"]) == 1
        step = data["steps"][0]
        assert step["id"] == "s1"
        assert step["kind"] == "read"
        assert step["title"] == "looks relevant"  # title = reason.strip()
        assert step["summary"] == "stub answer"  # summary = response (can_answer)
        assert step["durationMs"] == 120
        assert step["citations"] == ["#/texts/0"]
        # payload keys are camelCase by construction (binding UI contract)
        assert step["payload"]["canAnswer"] is True
        assert step["payload"]["sectionRef"] == "#/texts/0"
        assert step["payload"]["sectionTextLength"] == 42

    def test_passes_query_and_doc_json_to_runner(self) -> None:
        runner = _FakeRunner()
        client = _make_client(runner=runner)

        client.post("/api/documents/doc-1/reasoning", json={"query": "Hello?"})

        assert runner.last_call is not None
        assert runner.last_call["query"] == "Hello?"
        assert runner.last_call["document_json"] == '{"stub": true}'

    def test_no_model_override_passes_none(self) -> None:
        runner = _FakeRunner()
        client = _make_client(runner=runner)

        client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})

        assert runner.last_call is not None
        assert runner.last_call["model_id"] is None

    def test_per_request_model_id_override_wins(self) -> None:
        runner = _FakeRunner()
        client = _make_client(runner=runner)

        client.post(
            "/api/documents/doc-1/reasoning",
            json={"query": "Q", "modelId": "override:13b"},
        )

        assert runner.last_call is not None
        assert runner.last_call["model_id"] == "override:13b"

    def test_multiple_steps_serialize_in_order(self) -> None:
        result = ReasoningResult(
            answer="final",
            converged=False,
            iterations=[
                ReasoningIteration(
                    iteration=1,
                    section_ref="#/texts/0",
                    reason="r1",
                    section_text_length=10,
                    can_answer=False,
                    response="not yet",
                ),
                ReasoningIteration(
                    iteration=2,
                    section_ref="#/texts/5",
                    reason="r2",
                    section_text_length=20,
                    can_answer=True,
                    response="final",
                ),
            ],
        )
        client = _make_client(runner=_FakeRunner(result=result))

        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["converged"] is False
        assert [s["id"] for s in data["steps"]] == ["s1", "s2"]
        assert [s["citations"][0] for s in data["steps"]] == ["#/texts/0", "#/texts/5"]
        assert data["steps"][0]["summary"] == "Insufficient — 10 chars read, agent moved on."
        assert data["steps"][0]["payload"]["canAnswer"] is False
        assert data["steps"][1]["payload"]["canAnswer"] is True


class TestReasoningUpstreamFailure:
    def test_502_when_runner_raises_parse_error(self) -> None:
        """The model couldn't produce a parseable JSON answer after retries."""
        runner = _FakeRunner(
            raises=ReasoningParseError(model_id="granite4:micro-h", reason="no parseable answer")
        )
        client = _make_client(runner=runner)

        resp = client.post(
            "/api/documents/doc-1/reasoning",
            json={"query": "Quelle tarification ?"},
        )
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert "granite4:micro-h" in detail
        assert "parseable" in detail or "rephrase" in detail

    def test_500_for_other_unexpected_errors(self) -> None:
        runner = _FakeRunner(raises=RuntimeError("Ollama unreachable"))
        client = _make_client(runner=runner)

        resp = client.post("/api/documents/doc-1/reasoning", json={"query": "Q"})
        assert resp.status_code == 500
        assert "Ollama unreachable" in resp.json()["detail"]

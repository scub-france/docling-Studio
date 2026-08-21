"""Tests for `infra.docling_agent_reasoning.DoclingAgentReasoningRunner`.

docling-agent + mellea + docling-core are NOT installed in the CI test env
(heavy deps). We stub the modules via `sys.modules` injection so the tests
cover the real adapter code path without bringing in Ollama or any LLM client.

The adapter consumes the public `run_with_trace(task, document)` (docling-agent
0.6.0) and builds a per-instance Ollama backend from `BackendConfig` — no
private `_rag_loop`, no `os.environ["OLLAMA_HOST"]` mutation. Timing/model
fields are read from `model_dump()` with a default so the adapter survives the
0.6.0 models, which declare neither.
"""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import infra.docling_agent_reasoning as mod
from domain.ports import ReasoningParseError, ReasoningRunner
from infra.llm.ollama_provider import OllamaProvider


class _FakeModel(SimpleNamespace):
    """Stand-in for docling-agent's pydantic `RAGResult` / `RAGIteration`.

    The adapter maps through `model_dump()` (#306 review), so the stub has to
    expose it — and nest it the way pydantic does, dumping children to dicts.
    """

    def model_dump(self) -> dict:
        return {
            k: [c.model_dump() for c in v] if k == "iterations" else v
            for k, v in vars(self).items()
        }


def _make_iteration(*, with_timing: bool) -> _FakeModel:
    fields = {
        "iteration": 1,
        "section_ref": "#/texts/0",
        "reason": "looks relevant",
        "section_text_length": 42,
        "can_answer": True,
        "response": "stub answer",
    }
    if with_timing:
        fields["duration_ms"] = 1234
    return _FakeModel(**fields)


def _make_rag_result(*, with_timing: bool) -> _FakeModel:
    fields = {
        "answer": "stub answer",
        "converged": True,
        "iterations": [_make_iteration(with_timing=with_timing)],
    }
    if with_timing:
        fields["duration_ms"] = 5678
        fields["model_id"] = "granite3.3:8b"
    return _FakeModel(**fields)


@pytest.fixture
def stub_fork(monkeypatch: pytest.MonkeyPatch):
    """Inject fake docling-agent + docling-core modules so the adapter's lazy
    imports resolve to stubs. Returns a namespace exposing the agent class /
    instance, the recorded BackendConfig, and a setter for the RAGTrace."""
    state = SimpleNamespace(rag_result=_make_rag_result(with_timing=True))

    agent_instance = MagicMock()

    def _run_with_trace(*, task, document):
        return SimpleNamespace(
            query=task,
            per_document=[state.rag_result],
            final_answer=state.rag_result.answer,
        )

    agent_instance.run_with_trace = MagicMock(side_effect=_run_with_trace)
    agent_class = MagicMock(return_value=agent_instance)

    def fake_create_backend(config):
        state.backend_config = config
        return SimpleNamespace(kind="fake-ollama-backend", config=config)

    class FakeBackendConfig:
        def __init__(self, *, type=None, base_url=None, models=None, **kw):
            self.type = type
            self.base_url = base_url
            self.models = models

    class FakeModelConfig:
        def __init__(self, *, reasoning=None, writing=None, **kw):
            self.reasoning = reasoning
            self.writing = writing

    # docling_agent package + submodules
    fake_agents_mod = types.ModuleType("docling_agent.agents")
    fake_agents_mod.DoclingRAGAgent = agent_class
    fake_backends_mod = types.ModuleType("docling_agent.backends")
    fake_backends_mod.create_backend = fake_create_backend
    fake_task_mod = types.ModuleType("docling_agent.task_model")
    fake_task_mod.BackendConfig = FakeBackendConfig
    fake_task_mod.ModelConfig = FakeModelConfig
    fake_root_mod = types.ModuleType("docling_agent")
    fake_root_mod.agents = fake_agents_mod
    fake_root_mod.backends = fake_backends_mod
    fake_root_mod.task_model = fake_task_mod

    fake_doc_class = MagicMock()
    fake_doc_class.model_validate_json = MagicMock(return_value="fake-doc-instance")
    fake_doc_mod = types.ModuleType("docling_core.types.doc.document")
    fake_doc_mod.DoclingDocument = fake_doc_class

    fake_mellea_mod = types.ModuleType("mellea")

    monkeypatch.setitem(sys.modules, "docling_agent", fake_root_mod)
    monkeypatch.setitem(sys.modules, "docling_agent.agents", fake_agents_mod)
    monkeypatch.setitem(sys.modules, "docling_agent.backends", fake_backends_mod)
    monkeypatch.setitem(sys.modules, "docling_agent.task_model", fake_task_mod)
    monkeypatch.setitem(sys.modules, "docling_core.types.doc.document", fake_doc_mod)
    monkeypatch.setitem(sys.modules, "mellea", fake_mellea_mod)

    state.agent_class = agent_class
    state.agent_instance = agent_instance
    state.doc_class = fake_doc_class
    return state


def _make_runner(
    *,
    host: str = "http://ollama:11434",
    default_model_id: str = "gpt-oss:20b",
    max_iterations: int = 5,
):
    """Build the runner bypassing the live deps-check (stubs are injected via
    sys.modules; we force `_deps_ok` so construction order doesn't matter)."""
    runner = mod.DoclingAgentReasoningRunner.__new__(mod.DoclingAgentReasoningRunner)
    runner._provider = OllamaProvider(host=host, default_model_id=default_model_id)
    runner._max_iterations = max_iterations
    runner._deps_ok = True
    return runner


class TestProtocolConformance:
    def test_runner_satisfies_reasoning_runner_protocol(self) -> None:
        runner = _make_runner()
        assert isinstance(runner, ReasoningRunner)


class TestProviderRejection:
    def test_rejects_non_ollama_provider(self) -> None:
        class _FakeProvider:
            type = "openai"
            host = "x"
            default_model_id = "y"

            def health_check(self) -> bool:
                return True

        with pytest.raises(NotImplementedError, match="Ollama"):
            mod.DoclingAgentReasoningRunner(provider=_FakeProvider())  # type: ignore[arg-type]


class TestRunHappyPath:
    @pytest.mark.asyncio
    async def test_returns_domain_reasoning_result(self, stub_fork) -> None:
        runner = _make_runner()

        result = await runner.run(document_json='{"stub": true}', query="What is this?")

        assert result.answer == "stub answer"
        assert result.converged is True
        assert len(result.iterations) == 1
        it = result.iterations[0]
        assert it.iteration == 1
        assert it.section_ref == "#/texts/0"
        assert it.can_answer is True

    @pytest.mark.asyncio
    async def test_maps_timing_and_model_when_present(self, stub_fork) -> None:
        """Post-timing-commit reality: duration_ms / model_id flow through."""
        runner = _make_runner()

        result = await runner.run(document_json="{}", query="Q")

        assert result.duration_ms == 5678
        assert result.model_id == "granite3.3:8b"
        assert result.iterations[0].duration_ms == 1234

    @pytest.mark.asyncio
    async def test_defensive_mapping_when_timing_absent(self, stub_fork) -> None:
        """Pinned-release reality: docling-agent 0.6.0 declares no timing
        fields — the dump has no such keys, so they default to 0 and model_id
        falls back to the requested model."""
        stub_fork.rag_result = _make_rag_result(with_timing=False)
        runner = _make_runner(default_model_id="fallback:7b")

        result = await runner.run(document_json="{}", query="Q")

        assert result.duration_ms == 0
        assert result.model_id == "fallback:7b"
        assert result.iterations[0].duration_ms == 0

    @pytest.mark.asyncio
    async def test_builds_ollama_backend_from_default_model(self, stub_fork) -> None:
        runner = _make_runner(host="http://h:11434", default_model_id="custom-model:7b")

        await runner.run(document_json="{}", query="Q")

        cfg = stub_fork.backend_config
        assert cfg.type == "ollama"
        assert cfg.base_url == "http://h:11434"
        assert cfg.models.reasoning == "custom-model:7b"
        assert cfg.models.writing == "custom-model:7b"

    @pytest.mark.asyncio
    async def test_per_call_model_id_override_wins(self, stub_fork) -> None:
        runner = _make_runner(default_model_id="default:7b")

        await runner.run(document_json="{}", query="Q", model_id="override:13b")

        assert stub_fork.backend_config.models.reasoning == "override:13b"

    @pytest.mark.asyncio
    async def test_constructs_agent_with_tools_and_backend(self, stub_fork) -> None:
        runner = _make_runner()

        await runner.run(document_json="{}", query="Q")

        stub_fork.agent_class.assert_called_once()
        kwargs = stub_fork.agent_class.call_args.kwargs
        assert kwargs["tools"] == []
        assert kwargs["backend"].kind == "fake-ollama-backend"
        assert kwargs["max_iterations"] == 5

    @pytest.mark.asyncio
    async def test_threads_max_iterations_into_agent(self, stub_fork) -> None:
        """#317 — the runtime-configurable iteration cap must actually reach
        `DoclingRAGAgent`, otherwise the admin knob is decorative."""
        runner = _make_runner(max_iterations=9)

        await runner.run(document_json="{}", query="Q")

        assert stub_fork.agent_class.call_args.kwargs["max_iterations"] == 9

    @pytest.mark.asyncio
    async def test_calls_run_with_trace_with_query_and_doc(self, stub_fork) -> None:
        runner = _make_runner()

        await runner.run(document_json="{}", query="Hello?")

        stub_fork.agent_instance.run_with_trace.assert_called_once()
        kwargs = stub_fork.agent_instance.run_with_trace.call_args.kwargs
        assert kwargs["task"] == "Hello?"
        assert kwargs["document"] == "fake-doc-instance"

    @pytest.mark.asyncio
    async def test_does_not_mutate_ollama_host_env(self, stub_fork, monkeypatch) -> None:
        """The new adapter carries the host on BackendConfig, not os.environ."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        runner = _make_runner(host="http://specific:11434")

        await runner.run(document_json="{}", query="Q")

        import os

        assert "OLLAMA_HOST" not in os.environ

    @pytest.mark.asyncio
    async def test_offloads_run_with_trace_to_thread(self, stub_fork, monkeypatch) -> None:
        """The 20-40s sync run must be thread-offloaded so it can't block the
        event loop. Pin the offload so a refactor to a direct blocking call
        fails the suite (design §9)."""

        calls: list = []
        real_to_thread = asyncio.to_thread

        async def spy(func, /, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(mod.asyncio, "to_thread", spy)
        runner = _make_runner()

        await runner.run(document_json="{}", query="Q")

        assert stub_fork.agent_instance.run_with_trace in calls


class TestRunUpstreamFailure:
    @pytest.mark.asyncio
    async def test_indexerror_translates_to_parse_error(self, stub_fork) -> None:
        """docling-agent's known IndexError → domain `ReasoningParseError`."""
        stub_fork.agent_instance.run_with_trace.side_effect = IndexError("list index out of range")
        runner = _make_runner(default_model_id="granite4:micro-h")

        with pytest.raises(ReasoningParseError) as exc_info:
            await runner.run(document_json="{}", query="Q")

        assert exc_info.value.model_id == "granite4:micro-h"

    @pytest.mark.asyncio
    async def test_empty_per_document_translates_to_parse_error(self, stub_fork) -> None:
        """An empty `per_document` (agent produced no result) → `ReasoningParseError`,
        not an uncaught IndexError surfacing as a generic 500."""

        def _empty(*, task, document):
            return SimpleNamespace(query=task, per_document=[], final_answer="")

        stub_fork.agent_instance.run_with_trace.side_effect = _empty
        runner = _make_runner(default_model_id="granite4:micro-h")

        with pytest.raises(ReasoningParseError) as exc_info:
            await runner.run(document_json="{}", query="Q")

        assert exc_info.value.model_id == "granite4:micro-h"

    @pytest.mark.asyncio
    async def test_other_exceptions_propagate(self, stub_fork) -> None:
        stub_fork.agent_instance.run_with_trace.side_effect = RuntimeError("Ollama unreachable")
        runner = _make_runner()

        with pytest.raises(RuntimeError, match="Ollama unreachable"):
            await runner.run(document_json="{}", query="Q")


class TestDepsPresent:
    def test_deps_present_returns_false_when_modules_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When docling-agent/mellea aren't importable, the wiring code should
        know not to instantiate the runner."""
        monkeypatch.setitem(sys.modules, "docling_agent", None)
        monkeypatch.setitem(sys.modules, "docling_agent.agents", None)
        monkeypatch.setitem(sys.modules, "mellea", None)

        assert mod.deps_present() is False

    def test_deps_present_returns_true_when_whole_surface_is_importable(self, stub_fork) -> None:

        assert mod.deps_present() is True

    def test_deps_present_returns_false_when_backends_missing(
        self, stub_fork, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """docling-agent 0.1.0 has `agents` but no `backends` package. The old
        two-module check passed on `agents` alone and the adapter only blew up
        at call time — cf. the 500 that motivated the 0.6.0 pin."""
        monkeypatch.setitem(sys.modules, "docling_agent.backends", None)

        assert mod.deps_present() is False

    def test_deps_present_returns_false_when_agent_lacks_run_with_trace(self, stub_fork) -> None:
        """Releases before docling-project/docling-agent#39 import cleanly but
        don't expose the trace surface the adapter binds to."""

        class _PreTraceAgent:
            """docling-agent < 0.6.0: run(), but no run_with_trace()."""

            def run(self, *a, **kw): ...

        sys.modules["docling_agent.agents"].DoclingRAGAgent = _PreTraceAgent

        assert mod.deps_present() is False


class TestDepsProvenance:
    def test_reports_version_and_resolved_path(self, stub_fork, monkeypatch) -> None:
        """The boot log has to name *which* docling-agent won, not just that one
        is importable — a bare `uvicorn` resolves against the ambient
        interpreter and that is invisible from the version alone."""
        import importlib.metadata as md

        sys.modules["docling_agent"].__file__ = "/somewhere/docling_agent/__init__.py"
        monkeypatch.setattr(md, "version", lambda name: "0.6.0")

        assert mod.deps_provenance() == (
            "docling-agent 0.6.0 from /somewhere/docling_agent/__init__.py"
        )

    def test_does_not_raise_when_docling_agent_is_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "docling_agent", None)

        assert mod.deps_provenance() == "docling-agent not importable"

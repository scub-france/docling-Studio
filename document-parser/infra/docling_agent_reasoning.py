"""docling-agent reasoning runner adapter.

Implements `ReasoningRunner` for an `OllamaProvider`-backed `LLMProvider`.
Encapsulates everything that talks to docling-agent / mellea so neither the
domain nor the API layer depends on those packages.

Consumes the **public** `run_with_trace(task, document)` surface, released in
docling-agent 0.6.0 (docling-project/docling-agent#39) — the v1 adapter reached
into the private `_rag_loop`. `duration_ms`/`model_id` are read defensively
(`getattr`): 0.6.0 carries them on neither `RAGResult` nor `RAGIteration`, so
the trace timeline degrades to 0 until docling-project/docling-agent#42 lands.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from domain.ports import LLMProvider, ReasoningParseError
from domain.value_objects import (
    LLMProviderType,
    ReasoningIteration,
    ReasoningResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class _Deps(NamedTuple):
    """The docling-agent / docling-core surface this adapter binds to."""

    rag_agent_cls: type
    create_backend: Callable[..., Any]
    backend_config_cls: type
    model_config_cls: type
    document_cls: type


def _import_deps() -> _Deps:
    """Import every symbol the adapter needs, and assert the agent really
    carries the trace surface.

    Single source of truth for the dependency contract: `run()` calls it to do
    its work and `deps_present()` calls it to decide availability at boot, so
    the boot check cannot drift from what `run()` actually imports. That drift
    is what let docling-agent 0.1.0 — which has `agents` but neither `backends`
    nor `run_with_trace` — pass the old two-module check, advertise
    `reasoning_available: true`, and then 500 on the first Ask.

    Raises ImportError when a module is missing or when the version resolved is
    too old to expose `run_with_trace`.
    """
    import mellea  # noqa: F401
    from docling_agent.agents import DoclingRAGAgent
    from docling_agent.backends import create_backend
    from docling_agent.task_model import BackendConfig, ModelConfig
    from docling_core.types.doc.document import DoclingDocument

    if not hasattr(DoclingRAGAgent, "run_with_trace"):
        raise ImportError(
            "DoclingRAGAgent has no run_with_trace() — docling-agent >= 0.6.0 is "
            "required (docling-project/docling-agent#39)"
        )

    return _Deps(
        rag_agent_cls=DoclingRAGAgent,
        create_backend=create_backend,
        backend_config_cls=BackendConfig,
        model_config_cls=ModelConfig,
        document_cls=DoclingDocument,
    )


def deps_present() -> bool:
    """Whether the reasoning stack is importable *and* new enough. Used by the
    DI wire-up to decide whether to instantiate the runner at all, so a missing
    or stale docling-agent surfaces as `reasoning_available: false` at boot
    rather than a 500 on the first Ask."""
    try:
        _import_deps()
    except ImportError as e:
        logger.debug("Reasoning deps unusable: %s", e)
        return False
    return True


def deps_provenance() -> str:
    """Which docling-agent actually got resolved, as `version from path`.

    Logged at boot: the install is easy to get wrong (a bare `uvicorn` picks up
    the ambient interpreter rather than the project venv), and the version alone
    doesn't say which one won. Never raises — this is diagnostics.
    """
    import importlib.metadata as md

    try:
        import docling_agent
    except ImportError:
        return "docling-agent not importable"
    try:
        version = md.version("docling-agent")
    except md.PackageNotFoundError:
        version = "unknown version"
    return f"docling-agent {version} from {docling_agent.__file__}"


class DoclingAgentReasoningRunner:
    """ReasoningRunner adapter wrapping docling-agent + mellea.

    The Ollama host is carried on a per-instance `BackendConfig` and threaded
    into the agent's backend at call time — no process-wide `OLLAMA_HOST` env
    mutation, so concurrent runs can't race on a shared global.
    """

    def __init__(self, provider: LLMProvider, *, max_iterations: int = 5) -> None:
        if provider.type is not LLMProviderType.OLLAMA:
            raise NotImplementedError(
                f"The reasoning runner only supports Ollama, got provider type {provider.type!r}."
            )
        self._provider = provider
        self._max_iterations = max_iterations
        self._deps_ok = deps_present()

    @property
    def is_available(self) -> bool:
        return self._deps_ok

    async def run(
        self,
        *,
        document_json: str,
        query: str,
        model_id: str | None = None,
    ) -> ReasoningResult:
        if not self._deps_ok:
            raise RuntimeError("docling-agent / mellea not importable — cannot run reasoning")

        # Lazy import keeps the module loadable when deps are missing. Shared
        # with `deps_present()` so the boot check covers exactly what runs here.
        deps = _import_deps()

        raw_model_id = model_id or self._provider.default_model_id

        try:
            doc = deps.document_cls.model_validate_json(document_json)
        except Exception as e:
            raise RuntimeError(f"Failed to parse document_json: {e}") from e

        # Per-instance Ollama backend — the host lives on the config, not in a
        # shared env var. `reasoning` is the role the RAG loop reads; `writing`
        # mirrors it so the merge step (multi-doc, unused here) stays coherent.
        backend = deps.create_backend(
            deps.backend_config_cls(
                type="ollama",
                base_url=self._provider.host,
                models=deps.model_config_cls(reasoning=raw_model_id, writing=raw_model_id),
            )
        )
        # `max_iterations` bounds the RAG loop — runtime-configurable via the
        # admin panel (#317); DoclingRAGAgent's own default is 5.
        agent = deps.rag_agent_cls(tools=[], backend=backend, max_iterations=self._max_iterations)
        logger.info(
            "Reasoning run: model_id=%s ollama_host=%s max_iterations=%d query=%r",
            raw_model_id,
            self._provider.host,
            self._max_iterations,
            query[:120],
        )

        try:
            # `run_with_trace` is sync + LLM-heavy (N * model latency). Offload
            # to a worker thread so concurrent calls don't block the event loop.
            run_result = await asyncio.to_thread(agent.run_with_trace, task=query, document=doc)
        except IndexError as e:
            # docling-agent's `_attempt_answer` still ends with an unguarded
            # `find_json_dicts(answer)[0]`. When the model can't produce a
            # parseable JSON after rejection-sampling retries, the list is
            # empty and `[0]` raises IndexError. Translate to a domain-level
            # error the API maps to 502.
            logger.warning(
                "docling-agent produced no parseable JSON for model=%s query=%r",
                raw_model_id,
                query[:120],
            )
            raise ReasoningParseError(
                model_id=raw_model_id,
                reason="no parseable answer after retries",
            ) from e

        # Single-document reasoning: read the first (only) per-document result.
        # An empty list means the agent produced nothing for the doc — map it to
        # a domain parse error (502) instead of letting IndexError surface as 500.
        if not run_result.per_document:
            logger.warning(
                "docling-agent returned no per-document result for model=%s query=%r",
                raw_model_id,
                query[:120],
            )
            raise ReasoningParseError(
                model_id=raw_model_id,
                reason="agent returned no per-document result",
            )
        rag_result = run_result.per_document[0]

        # Defensive mapping — the fork at the pinned SHA may not carry
        # `duration_ms`/`model_id` yet (the timing commit adds them; the
        # eventual upstream release may not). getattr keeps this adapter green
        # either way; the trace timeline degrades gracefully when timing is 0.
        return ReasoningResult(
            answer=rag_result.answer,
            iterations=[
                ReasoningIteration(
                    iteration=it.iteration,
                    section_ref=it.section_ref,
                    reason=it.reason,
                    section_text_length=it.section_text_length,
                    can_answer=it.can_answer,
                    response=it.response,
                    duration_ms=getattr(it, "duration_ms", 0),
                )
                for it in rag_result.iterations
            ],
            converged=rag_result.converged,
            duration_ms=getattr(rag_result, "duration_ms", 0),
            model_id=getattr(rag_result, "model_id", "") or raw_model_id,
        )

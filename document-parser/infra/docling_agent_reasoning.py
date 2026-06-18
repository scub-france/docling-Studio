"""docling-agent reasoning runner adapter.

Implements `ReasoningRunner` for an `OllamaProvider`-backed `LLMProvider`.
Encapsulates everything that talks to docling-agent / mellea so neither the
domain nor the API layer depends on those packages.

Consumes the fork's **public** `run_with_trace(task, document)` surface
(`pjmalandrino/docling-agent@dev/rag-run-with-trace`, upstream PR
docling-project/docling-agent#39) — the v1 adapter reached into the private
`_rag_loop`. The fork's timing commit adds `duration_ms`/`model_id` to the
`RAGIteration`/`RAGResult` models; this adapter still reads them defensively
(`getattr`) so it keeps working against a pinned SHA without them and against
the eventual upstream release.
"""

from __future__ import annotations

import asyncio
import logging

from domain.ports import LLMProvider, ReasoningParseError
from domain.value_objects import (
    LLMProviderType,
    ReasoningIteration,
    ReasoningResult,
)

logger = logging.getLogger(__name__)


def deps_present() -> bool:
    """Import-check for the heavy reasoning deps. Used by the DI wire-up to
    decide whether to instantiate the runner at all (so the backend boots
    cleanly when docling-agent + mellea aren't installed)."""
    try:
        import docling_agent.agents  # noqa: F401
        import mellea  # noqa: F401
    except ImportError:
        return False
    return True


class DoclingAgentReasoningRunner:
    """ReasoningRunner adapter wrapping docling-agent + mellea.

    The Ollama host is carried on a per-instance `BackendConfig` and threaded
    into the agent's backend at call time — no process-wide `OLLAMA_HOST` env
    mutation, so concurrent runs can't race on a shared global.
    """

    def __init__(self, provider: LLMProvider) -> None:
        if provider.type is not LLMProviderType.OLLAMA:
            raise NotImplementedError(
                f"The reasoning runner only supports Ollama, got provider type {provider.type!r}."
            )
        self._provider = provider
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

        # Lazy imports keep the module loadable when deps are missing (the
        # runner is only ever instantiated when `deps_present()` is True, but
        # this also makes the import surface explicit).
        from docling_agent.agents import DoclingRAGAgent
        from docling_agent.backends import create_backend
        from docling_agent.task_model import BackendConfig, ModelConfig
        from docling_core.types.doc.document import DoclingDocument

        raw_model_id = model_id or self._provider.default_model_id

        try:
            doc = DoclingDocument.model_validate_json(document_json)
        except Exception as e:
            raise RuntimeError(f"Failed to parse document_json: {e}") from e

        # Per-instance Ollama backend — the host lives on the config, not in a
        # shared env var. `reasoning` is the role the RAG loop reads; `writing`
        # mirrors it so the merge step (multi-doc, unused here) stays coherent.
        backend = create_backend(
            BackendConfig(
                type="ollama",
                base_url=self._provider.host,
                models=ModelConfig(reasoning=raw_model_id, writing=raw_model_id),
            )
        )
        agent = DoclingRAGAgent(tools=[], backend=backend)
        logger.info(
            "Reasoning run: model_id=%s ollama_host=%s query=%r",
            raw_model_id,
            self._provider.host,
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

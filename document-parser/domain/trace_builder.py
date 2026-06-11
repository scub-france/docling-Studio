"""Project a debugger-facing `ReasoningTrace` from a raw `ReasoningResult`.

Pure function over domain value objects — no HTTP, no DB, no docling-agent.
It lives in `domain/` (not `infra/`, where docling-lens keeps it) precisely
because it touches nothing but domain types; the architecture tests enforce
that boundary.

The trace timeline renders typed steps (PLAN/RETRIEVE/RERANK/READ/VERIFY/
ANSWER/MAP). docling-agent's chunkless RAG loop emits only READ-style
iterations today, so every `ReasoningIteration` maps 1:1 to a `READ` step.

Per-iteration `duration_ms` flows from the upstream `RAGIteration` (fork
branch with public `run_with_trace` + the timing commit). The trace total
prefers the agent's own `RAGResult.duration_ms` (LLM time) over the API
wall-clock fallback, since that's the signal the timeline actually cares
about. Token counts stay zero until mellea exposes usage stats.

Two deliberate divergences from the docling-lens reference:
  - title fallback uses ``or`` (not ``if it.reason``), so a whitespace-only
    reason also falls back to ``Read {ref}``;
  - `payload` keys are **camelCase** — the binding wire contract the UI reads
    (`payload.canAnswer`); Pydantic does not alias dict contents, so the keys
    are constructed already-cased here.
"""

from __future__ import annotations

from domain.value_objects import (
    ReasoningIteration,
    ReasoningResult,
    ReasoningStep,
    ReasoningStepKind,
    ReasoningTrace,
)


def _read_step(it: ReasoningIteration) -> ReasoningStep:
    # docling-agent's `reason` is the LLM's stated motivation for picking this
    # section — the most informative per-step label we have. Fall back to the
    # section ref when it's missing or whitespace-only (`or`, not `if`).
    title = it.reason.strip() or f"Read {it.section_ref}"
    # Trim long titles so the timeline row doesn't blow up (<=96 chars).
    if len(title) > 96:
        title = title[:93].rstrip() + "…"

    if it.can_answer:
        summary = it.response.strip()
    else:
        summary = (
            f"Insufficient — {it.section_text_length} chars read, agent moved on."
            if it.section_text_length
            else "Insufficient — agent moved on."
        )

    return ReasoningStep(
        id=f"s{it.iteration}",
        kind=ReasoningStepKind.READ,
        title=title,
        summary=summary,
        duration_ms=it.duration_ms,
        citations=[it.section_ref] if it.section_ref else [],
        payload={
            "iteration": it.iteration,
            "sectionRef": it.section_ref,
            "reason": it.reason,
            "sectionTextLength": it.section_text_length,
            "canAnswer": it.can_answer,
            "response": it.response,
            "durationMs": it.duration_ms,
        },
    )


def build_trace(
    *,
    result: ReasoningResult,
    model_id: str,
    total_duration_ms: int = 0,
) -> ReasoningTrace:
    """Project a docling-agent `ReasoningResult` onto the trace timeline shape.

    `total_duration_ms` is the API wall-clock; `result.duration_ms` wins when
    the upstream loop captured it (non-zero) since that's LLM-only time. The
    `model_id` arg is the request/default model; `result.model_id` overrides
    when the agent self-describes.
    """
    steps = [_read_step(it) for it in result.iterations]
    effective_total = result.duration_ms if result.duration_ms > 0 else total_duration_ms
    effective_model = result.model_id or model_id
    return ReasoningTrace(
        answer=result.answer,
        converged=result.converged,
        steps=steps,
        total_duration_ms=effective_total,
        tokens_in=0,
        tokens_out=0,
        model_id=effective_model,
    )

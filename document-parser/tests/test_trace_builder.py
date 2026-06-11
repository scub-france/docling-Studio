"""Tests for `domain.trace_builder.build_trace` — the pure projection from a
docling-agent `ReasoningResult` onto the trace-timeline `ReasoningTrace`.

Locks the projection rules the UI binds to (title fallback + truncation,
insufficient summary, camelCase payload, duration/model preference).
"""

from __future__ import annotations

from domain.trace_builder import build_trace
from domain.value_objects import (
    ReasoningIteration,
    ReasoningResult,
    ReasoningStepKind,
)


def _iteration(**overrides) -> ReasoningIteration:
    fields = {
        "iteration": 1,
        "section_ref": "#/texts/0",
        "reason": "Scan the intro for the answer",
        "section_text_length": 412,
        "can_answer": True,
        "response": "  The answer is 42.  ",
        "duration_ms": 0,
    }
    fields.update(overrides)
    return ReasoningIteration(**fields)


def _result(iterations, **overrides) -> ReasoningResult:
    fields = {
        "answer": "final answer",
        "iterations": iterations,
        "converged": True,
        "duration_ms": 0,
        "model_id": "",
    }
    fields.update(overrides)
    return ReasoningResult(**fields)


def test_one_read_step_per_iteration_with_id():
    result = _result([_iteration(iteration=1), _iteration(iteration=2)])
    trace = build_trace(result=result, model_id="m")
    assert [s.id for s in trace.steps] == ["s1", "s2"]
    assert all(s.kind is ReasoningStepKind.READ for s in trace.steps)


def test_title_is_the_reason_trimmed():
    trace = build_trace(result=_result([_iteration(reason="  Pick section A  ")]), model_id="m")
    assert trace.steps[0].title == "Pick section A"


def test_whitespace_only_reason_falls_back_to_read_ref():
    """Studio divergence from lens: `or`, not `if it.reason` — a whitespace-only
    reason also falls back to `Read {ref}`."""
    trace = build_trace(
        result=_result([_iteration(reason="   ", section_ref="#/texts/7")]),
        model_id="m",
    )
    assert trace.steps[0].title == "Read #/texts/7"


def test_empty_reason_falls_back_to_read_ref():
    trace = build_trace(
        result=_result([_iteration(reason="", section_ref="#/texts/9")]),
        model_id="m",
    )
    assert trace.steps[0].title == "Read #/texts/9"


def test_long_title_is_truncated_to_96_with_ellipsis():
    long_reason = "x" * 200
    trace = build_trace(result=_result([_iteration(reason=long_reason)]), model_id="m")
    title = trace.steps[0].title
    assert title.endswith("…")
    assert len(title) <= 96
    assert title == "x" * 93 + "…"


def test_summary_is_response_when_can_answer():
    trace = build_trace(
        result=_result([_iteration(can_answer=True, response="  Cast Swiftmend.  ")]),
        model_id="m",
    )
    assert trace.steps[0].summary == "Cast Swiftmend."


def test_summary_insufficient_with_char_count():
    trace = build_trace(
        result=_result([_iteration(can_answer=False, section_text_length=412)]),
        model_id="m",
    )
    assert trace.steps[0].summary == "Insufficient — 412 chars read, agent moved on."


def test_summary_insufficient_without_char_count():
    trace = build_trace(
        result=_result([_iteration(can_answer=False, section_text_length=0)]),
        model_id="m",
    )
    assert trace.steps[0].summary == "Insufficient — agent moved on."


def test_citations_carry_section_ref():
    trace = build_trace(result=_result([_iteration(section_ref="#/texts/3")]), model_id="m")
    assert trace.steps[0].citations == ["#/texts/3"]


def test_citations_empty_when_no_section_ref():
    trace = build_trace(result=_result([_iteration(section_ref="")]), model_id="m")
    assert trace.steps[0].citations == []


def test_payload_keys_are_camelcase():
    trace = build_trace(
        result=_result(
            [
                _iteration(
                    iteration=2,
                    section_ref="#/texts/5",
                    reason="why",
                    section_text_length=99,
                    can_answer=False,
                    response="missing X",
                    duration_ms=321,
                )
            ]
        ),
        model_id="m",
    )
    payload = trace.steps[0].payload
    assert payload == {
        "iteration": 2,
        "sectionRef": "#/texts/5",
        "reason": "why",
        "sectionTextLength": 99,
        "canAnswer": False,
        "response": "missing X",
        "durationMs": 321,
    }
    # step.duration_ms and payload["durationMs"] derive from the same source.
    assert trace.steps[0].duration_ms == 321


def test_step_duration_flows_from_iteration():
    trace = build_trace(result=_result([_iteration(duration_ms=777)]), model_id="m")
    assert trace.steps[0].duration_ms == 777


def test_total_duration_prefers_result_over_wall_clock():
    result = _result([_iteration()], duration_ms=5000)
    trace = build_trace(result=result, model_id="m", total_duration_ms=9000)
    assert trace.total_duration_ms == 5000


def test_total_duration_falls_back_to_wall_clock():
    result = _result([_iteration()], duration_ms=0)
    trace = build_trace(result=result, model_id="m", total_duration_ms=9000)
    assert trace.total_duration_ms == 9000


def test_model_id_prefers_result_over_arg():
    result = _result([_iteration()], model_id="granite3.3:8b")
    trace = build_trace(result=result, model_id="arg-model")
    assert trace.model_id == "granite3.3:8b"


def test_model_id_falls_back_to_arg_when_result_empty():
    result = _result([_iteration()], model_id="")
    trace = build_trace(result=result, model_id="arg-model")
    assert trace.model_id == "arg-model"


def test_answer_and_converged_pass_through():
    result = _result([_iteration()], answer="42", converged=False)
    trace = build_trace(result=result, model_id="m")
    assert trace.answer == "42"
    assert trace.converged is False


def test_tokens_are_zero():
    trace = build_trace(result=_result([_iteration()]), model_id="m")
    assert trace.tokens_in == 0
    assert trace.tokens_out == 0


def test_empty_iterations_yields_no_steps():
    trace = build_trace(result=_result([]), model_id="m", total_duration_ms=120)
    assert trace.steps == []
    assert trace.total_duration_ms == 120

"""The investigation journal's published shapes, and how a record becomes one.

Shapes and mapping in one module, unlike `wire.py` / `wire_mapping.py`: these
types have exactly one producer, and splitting a hundred lines across two
files would buy a convention rather than a seam.

Same wire conventions as the rest of the surface — frozen dataclasses the SDK
turns into output schemas, snake_case because the reader is a model, and a
`next_step` on every result so the steering arrives when it applies rather
than as a rule stated once at connection time.

One rule matters more here than anywhere else on this surface: **every string
that leaves this module is `neutralise()`d**. The journal stores text a model
wrote after reading a document, and hands it back later — to the same agent
resuming, or to another one entirely. A delimiter forged in a PDF and copied
into a thought would otherwise be replayed as if the server had said it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.investigation import InvestigationState, StepState, next_pending, step_tally
from domain.navigation import clip_to_tokens

# Runtime import, not TYPE_CHECKING: `OutlineResult` is a dataclass field
# annotation below, and the SDK resolves those when it derives a tool's
# output schema — an import that only exists for a checker would fail there.
from mcp_adapter.wire import OutlineResult, neutralise
from mcp_adapter.wire_mapping import outline_result

if TYPE_CHECKING:
    from domain.investigation import Attempt, Investigation, Step
    from domain.investigation_map import InvestigationReport, MapNode


# What a replayed record keeps of `actual_quote` (~400 characters).
_TRACE_QUOTE_TOKENS = 100


@dataclass(frozen=True)
class InvestigationOpened:
    """The investigation, and the map to plan against.

    The outline ships with the open rather than in a second call: one round
    trip saved, and reading the map before any text stops being advice.
    """

    investigation_id: str
    document_id: str
    version_id: str
    filename: str
    question: str
    outline: OutlineResult
    max_steps: int
    max_attempts_per_step: int
    next_step: str


@dataclass(frozen=True)
class PlannedStep:
    step_id: str
    ordinal: int
    question: str


@dataclass(frozen=True)
class PlanAccepted:
    investigation_id: str
    steps: list[PlannedStep]
    attempts_per_step: int
    next_step: str
    first_step_id: str | None = None


@dataclass(frozen=True)
class AttemptSettled:
    """The server's verdict on one ref, and where it leaves the step.

    `outcome` is `kept` or one of the rejections. On a kept attempt,
    `kept_uri` is the anchor to cite: the precise element inside a section, or
    the span a quote across elements needs. `attempts_left` is the number to
    act on: "try a sibling section" or "this step is over".
    """

    investigation_id: str
    step_id: str
    outcome: str
    detail: str
    step_state: str
    attempts_left: int
    next_step: str
    kept_uri: str | None = None
    actual_quote: str | None = None
    next_step_id: str | None = None
    stale: bool = False


@dataclass(frozen=True)
class StepAbandoned:
    """A step dropped on purpose, with the plan's remaining work restated."""

    investigation_id: str
    step_id: str
    steps_pending: int
    next_step: str
    next_step_id: str | None = None


@dataclass(frozen=True)
class InvestigationClosed:
    investigation_id: str
    steps_answered: int
    steps_unanswered: int
    citations: list[str]
    stale: bool
    next_step: str


@dataclass(frozen=True)
class TraceAttempt:
    """One ref tried, as it is read back. `thought` is what the model said it
    was thinking — recorded, never checked. `outcome` is what the server
    decided, which is the part that was."""

    ordinal: int
    thought: str
    uri: str
    detail: str
    outcome: str | None = None
    quote: str | None = None
    kept_uri: str | None = None
    actual_quote: str | None = None


@dataclass(frozen=True)
class TraceStep:
    step_id: str
    ordinal: int
    question: str
    why: str
    state: str
    attempts: list[TraceAttempt] = field(default_factory=list)


@dataclass(frozen=True)
class MapEntry:
    """One outline node the investigation touched.

    `status` is `kept` (a ref here was allowed to be cited), `rejected` (one
    was tried and did not hold), `visited` (tried, verdict pending) or `path`
    (on the route to a marked descendant, not itself a destination).
    """

    ref: str
    uri: str
    title: str
    kind: str
    level: int
    status: str
    page: int | None = None
    step_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InvestigationView:
    """The record twice over: how the agent thought, and where it went.

    `reasoning` is the tree of steps and attempts in the order they happened.
    `map` is the same record projected onto the document outline, in document
    order — the navigation tree. Nothing in `reasoning` is verified except
    each attempt's `outcome`; `map` inherits exactly that.
    """

    investigation_id: str
    document_id: str
    version_id: str
    filename: str
    question: str
    state: str
    stale: bool
    reasoning: list[TraceStep]
    map: list[MapEntry]
    next_step: str
    answer: str | None = None


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------


def opened_result(investigation, outline, *, max_steps: int, max_attempts: int):
    return InvestigationOpened(
        investigation_id=investigation.id,
        document_id=investigation.document_id,
        version_id=investigation.version_id,
        filename=neutralise(outline.filename),
        question=neutralise(investigation.question),
        outline=outline_result(outline),
        max_steps=max_steps,
        max_attempts_per_step=max_attempts,
        next_step=(
            f"plan_steps: at most {max_steps} steps, each one a section of this outline can answer."
        ),
    )


def plan_result(investigation: Investigation, *, attempts_per_step: int) -> PlanAccepted:
    first = investigation.steps[0] if investigation.steps else None
    return PlanAccepted(
        investigation_id=investigation.id,
        steps=[
            PlannedStep(step_id=s.id, ordinal=s.ordinal, question=neutralise(s.question))
            for s in investigation.steps
        ],
        attempts_per_step=attempts_per_step,
        first_step_id=first.id if first else None,
        next_step=(
            f"Work step {first.ordinal} ({first.id}): read_element the entry likely to answer "
            "it, then record_attempt with its uri and the quote you would publish."
            if first
            else "The plan is empty."
        ),
    )


def attempt_result(verdict, *, investigation_id: str) -> AttemptSettled:
    attempt = verdict.attempt
    return AttemptSettled(
        investigation_id=investigation_id,
        step_id=attempt.step_id,
        outcome=str(attempt.outcome) if attempt.outcome else "pending",
        detail=neutralise(attempt.detail),
        step_state=str(verdict.step_state),
        attempts_left=verdict.attempts_left,
        kept_uri=attempt.kept_uri,
        actual_quote=neutralise(attempt.actual_quote) if attempt.actual_quote else None,
        next_step_id=verdict.next_step_id,
        stale=verdict.stale,
        next_step=_attempt_next_step(verdict),
    )


def abandoned_result(investigation: Investigation, step_id: str) -> StepAbandoned:
    pending = next_pending(investigation)
    remaining = step_tally(investigation)[StepState.PENDING]
    return StepAbandoned(
        investigation_id=investigation.id,
        step_id=step_id,
        steps_pending=remaining,
        next_step_id=pending.id if pending else None,
        next_step=(
            f"Recorded as dropped. Next: step {pending.id}."
            if pending
            else "Every step is settled: close_investigation."
        ),
    )


def closed_result(
    investigation: Investigation, citations: list[str], *, viewer: bool = False
) -> InvestigationClosed:
    tally = step_tally(investigation)
    # `viewer` says whether `show_investigation` is on this surface: this line
    # is what the model reads at the moment it chooses how to display.
    return InvestigationClosed(
        investigation_id=investigation.id,
        steps_answered=tally[StepState.ANSWERED],
        steps_unanswered=tally[StepState.UNANSWERED],
        citations=citations,
        stale=investigation.stale,
        next_step=(
            (
                "Published. Show it with show_investigation: one card for the whole record, "
                "not a show_citation per anchor."
                if viewer
                else "Published. get_investigation returns the record."
            )
            + (
                " Its parse has since been superseded: the quotes hold, a re-read would cite "
                "the current one."
                if investigation.stale
                else ""
            )
        ),
    )


def view_result(report: InvestigationReport) -> InvestigationView:
    investigation = report.investigation
    return InvestigationView(
        investigation_id=investigation.id,
        document_id=investigation.document_id,
        version_id=investigation.version_id,
        filename=neutralise(report.filename),
        question=neutralise(investigation.question),
        state=str(investigation.state),
        stale=investigation.stale,
        answer=neutralise(investigation.answer) if investigation.answer else None,
        reasoning=trace_steps(investigation),
        map=map_entries(report.map),
        next_step=_view_next_step(report),
    )


def _view_next_step(report: InvestigationReport) -> str:
    investigation = report.investigation
    note = "" if report.parse_available else "Its parse was deleted in Studio: no map. "
    if investigation.state is InvestigationState.CLOSED:
        return note + "Closed: `answer` is final."
    pending = next_pending(investigation)
    if pending is None:
        return note + "Every step is settled: close_investigation."
    return note + f"Resume with step {pending.id}."


def trace_steps(investigation: Investigation) -> list[TraceStep]:
    """The record as the wire publishes it. Shared with the Apps viewer, which
    renders exactly what a text-only host reads — the same shapes, so the two
    surfaces cannot drift into two different accounts of one investigation."""
    return [_trace_step(step) for step in investigation.steps]


def map_entries(nodes: list[MapNode]) -> list[MapEntry]:
    return [_map_entry(node) for node in nodes]


def _trace_step(step: Step) -> TraceStep:
    return TraceStep(
        step_id=step.id,
        ordinal=step.ordinal,
        question=neutralise(step.question),
        why=neutralise(step.why),
        state=str(step.state),
        attempts=[_trace_attempt(attempt) for attempt in step.attempts],
    )


def _trace_attempt(attempt: Attempt) -> TraceAttempt:
    return TraceAttempt(
        ordinal=attempt.ordinal,
        thought=neutralise(attempt.thought),
        uri=attempt.uri,
        detail=neutralise(attempt.detail),
        outcome=str(attempt.outcome) if attempt.outcome else None,
        quote=neutralise(attempt.quote) if attempt.quote else None,
        kept_uri=attempt.kept_uri,
        # The record is replayed on every read: what the element said is a
        # hint there, not the element — re-read it for the full text.
        actual_quote=(
            neutralise(clip_to_tokens(attempt.actual_quote, _TRACE_QUOTE_TOKENS))
            if attempt.actual_quote
            else None
        ),
    )


def _map_entry(node: MapNode) -> MapEntry:
    return MapEntry(
        ref=node.ref,
        uri=node.uri,
        title=neutralise(node.title),
        kind=node.kind,
        level=node.level,
        status=node.status,
        page=node.page,
        step_ids=list(node.step_ids),
    )


def _attempt_next_step(verdict) -> str:
    """What to do with the verdict — the steering, at the moment it applies."""
    attempt = verdict.attempt
    outcome = str(attempt.outcome or "")
    if outcome == "kept" and not (attempt.quote or "").strip():
        # Citable, but the passage was not checked: the step stays open.
        return (
            f"Citable as {attempt.citation_uri}, but nothing was verified without a quote, so "
            f"the step stays open ({verdict.attempts_left} attempts left). Send the passage "
            "you will publish."
        )
    if outcome == "kept":
        follow = (
            f"Next: step {verdict.next_step_id}."
            if verdict.next_step_id
            else "Every step is settled: close_investigation."
        )
        return f"Kept; cite it as {attempt.citation_uri}. {follow}"
    if str(verdict.step_state) == "unanswered":
        return (
            "No attempts left: the step is unanswered, a finding your answer must state. "
            + (f"Next: step {verdict.next_step_id}." if verdict.next_step_id else "")
        ).strip()
    hint = {
        "quote_drift": "The quote is not at this anchor; `actual_quote` is what is.",
        "unknown_ref": "No such element in this parse: use a uri a read returned.",
        "empty_element": "That element has no text: try the one holding the passage.",
        "bad_anchor": "Not a well-formed anchor: pass back a uri you were given.",
        "foreign_document": "That anchor belongs to another document.",
    }.get(outcome, "Try another ref for this step.")
    return f"Attempt {attempt.ordinal} of {attempt.ordinal + verdict.attempts_left}. {hint}"

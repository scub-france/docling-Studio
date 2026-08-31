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

from domain.investigation import StepState, next_pending, step_tally

# Runtime import, not TYPE_CHECKING: `OutlineResult` is a dataclass field
# annotation below, and the SDK resolves those when it derives a tool's
# output schema — an import that only exists for a checker would fail there.
from mcp_adapter.wire import OutlineResult, neutralise
from mcp_adapter.wire_mapping import outline_result

if TYPE_CHECKING:
    from domain.investigation import Attempt, Investigation, Step
    from domain.investigation_map import InvestigationReport, MapNode


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

    `outcome` is `kept` or one of the rejections. `kept_uri` is the anchor to
    cite when it differs from the one sent — verification widens a quote that
    ran across element boundaries, and hands back the precise element inside
    a section. `attempts_left` is the number to act on: it is the difference
    between "try a sibling section" and "this step is over".
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
            f"Decompose the question into at most {max_steps} steps the document can each "
            "answer, then call plan_steps. Use the outline above to choose them: a step "
            "nobody can point at a section for is a step to fold into another."
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
            f"Work step {first.ordinal} ({first.id}): read what the outline says is likely to "
            f"answer it, then record_attempt with the uri and the quote you would publish. "
            f"You have {attempts_per_step} attempts on it; the server decides whether each "
            "one held up."
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
            else "Every step is settled. close_investigation with an answer that cites only "
            "anchors this investigation kept, and says which steps went unanswered."
        ),
    )


def closed_result(
    investigation: Investigation, citations: list[str], *, viewer: bool = False
) -> InvestigationClosed:
    tally = step_tally(investigation)
    # `viewer` says whether `show_investigation` is on this surface. The prompt
    # already asks for it, but the prompt is thirty turns behind by now; this
    # line is what the model reads at the moment it chooses how to display —
    # steering it here is what stopped a show_citation per kept anchor.
    return InvestigationClosed(
        investigation_id=investigation.id,
        steps_answered=tally[StepState.ANSWERED],
        steps_unanswered=tally[StepState.UNANSWERED],
        citations=citations,
        stale=investigation.stale,
        next_step=(
            (
                "Published. Now call `show_investigation`, before any other display: it "
                "renders the whole record — the steps, every verdict, the navigation "
                "tree. Not a show_citation per kept anchor: a citation card shows one "
                "passage, and the reader has just been handed an investigation. A "
                "show_citation belongs after the card, and only for a passage itself "
                "in dispute."
                if viewer
                else "Published. get_investigation returns the record and the navigation "
                "tree — the sections this answer came from, in document order."
            )
            + (
                " This investigation ran on a parse that has since been superseded: the "
                "quotes are real, a re-read would cite the current parse."
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
        next_step=(
            "`reasoning` is what the agent said it was doing — thoughts are recorded, not "
            "verified. `outcome` on each attempt is the server's verdict, and `map` is those "
            "verdicts placed on the document. Resume by working the first pending step."
        ),
    )


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
        actual_quote=neutralise(attempt.actual_quote) if attempt.actual_quote else None,
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
        # It resolves, so it is citable; nothing about the passage was checked,
        # so the step is not answered by it. Saying only "kept" here is what
        # let a step close on a ref nobody verified.
        return (
            f"The ref resolves and is citable as {attempt.citation_uri}, but no quote was "
            f"given, so nothing was verified and the step is still open "
            f"({verdict.attempts_left} attempts left). "
            "Send the passage you intend to publish to settle it."
        )
    if outcome == "kept":
        if verdict.next_step_id:
            return f"Kept and verified. Cite it as {attempt.citation_uri}. Next: step {verdict.next_step_id}."
        return (
            f"Kept and verified. Cite it as {attempt.citation_uri}. Every step is settled — "
            "close_investigation with an answer that cites only anchors this investigation "
            "kept, then show_investigation so the reader can see where it came from."
        )
    if str(verdict.step_state) == "unanswered":
        return (
            "That was the last attempt, so this step is closed as unanswered. That is a "
            "finding: the answer has to say the document does not settle it. "
            + (f"Next: step {verdict.next_step_id}." if verdict.next_step_id else "")
        ).strip()
    hint = {
        "quote_drift": "The anchor is right and the quote is not in it — `actual_quote` says "
        "what is there. Quote that, or try the neighbouring element.",
        "unknown_ref": "No such element in this parse. Take a ref from the outline or from a "
        "read; never build one.",
        "empty_element": "That ref carries no text. Try the element that holds the passage.",
        "bad_anchor": "That was not a well-formed anchor. Pass back a uri you were given.",
        "foreign_document": "That anchor belongs to another document.",
    }.get(outcome, "Try another ref for this step.")
    return f"Attempt {attempt.ordinal} of {attempt.ordinal + verdict.attempts_left}. {hint}"

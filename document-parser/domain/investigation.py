"""An agent's recorded exploration of one parse of one document.

The four read-only tools of the MCP surface give an agent no memory: each
call stands alone, so nothing counts how many refs a question has already
cost, and nothing survives the conversation. This is the shape that fixes
both halves — a question, its decomposition into steps, and the refs tried
against each step with the verdict *the server* reached.

Two invariants are worth stating here rather than discovering downstream:

- **One parse per investigation.** `version_id` is pinned when it opens. A
  docling `self_ref` is stable inside one analysis and meaningless across
  two, so an investigation that followed a re-parse would be citing text it
  never read. When the parse is superseded the investigation is marked
  `stale` and carries on against the version it started with.
- **A `thought` is declarative.** It is what the model said it was thinking.
  Nothing checks it, and nothing can. What *is* checked is the anchor and the
  quote — `AttemptOutcome` is the server's verdict, not the model's.

Pure: no I/O, no clock, no id generation. The service supplies both.
"""

from __future__ import annotations

# `datetime` stays a runtime import (not TYPE_CHECKING): these are dataclass
# annotations, and the repository adapter resolves them when it hydrates a row.
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class InvestigationState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ABANDONED = "abandoned"


class StepState(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    # The step spent its attempt budget without a ref that held up. A
    # result, not a failure: the tree then says the document does not answer
    # there, and the final answer has to say so too.
    UNANSWERED = "unanswered"


class AttemptOutcome(StrEnum):
    """What the server decided about one ref tried against one step."""

    KEPT = "kept"
    # The uri is not a well-formed `dstudio://` anchor.
    BAD_ANCHOR = "bad_anchor"
    # It resolves, but to another document than the one under investigation.
    FOREIGN_DOCUMENT = "foreign_document"
    # No such element in this parse (or the version is unknown).
    UNKNOWN_REF = "unknown_ref"
    # It resolves and carries no text — a page break, an empty group.
    EMPTY_ELEMENT = "empty_element"
    # The anchor is fine and the quote is not in what it covers.
    QUOTE_DRIFT = "quote_drift"


REJECTIONS = frozenset(AttemptOutcome) - {AttemptOutcome.KEPT}


@dataclass(frozen=True)
class Attempt:
    """One ref tried against one step.

    `outcome` is None while the attempt is in flight: the row is written
    before adjudication runs, so a crash mid-verdict loses the verdict and
    not the reasoning. `kept_uri` may differ from `uri` — verification hands
    back a more precise anchor, or the span covering a quote that ran across
    element boundaries, and that is the one to cite.
    """

    id: str
    step_id: str
    ordinal: int
    thought: str
    uri: str
    created_at: datetime
    quote: str | None = None
    outcome: AttemptOutcome | None = None
    detail: str = ""
    kept_uri: str | None = None
    actual_quote: str | None = None

    @property
    def settled(self) -> bool:
        return self.outcome is not None

    @property
    def citation_uri(self) -> str:
        return self.kept_uri or self.uri


@dataclass(frozen=True)
class Step:
    """One sub-question of the decomposition, and what was tried for it."""

    id: str
    ordinal: int
    question: str
    why: str = ""
    state: StepState = StepState.PENDING
    attempts: list[Attempt] = field(default_factory=list)


@dataclass(frozen=True)
class Investigation:
    """The whole record: question, plan, attempts, verdicts, answer."""

    id: str
    document_id: str
    version_id: str
    question: str
    created_at: datetime
    state: InvestigationState = InvestigationState.OPEN
    stale: bool = False
    answer: str | None = None
    steps: list[Step] = field(default_factory=list)
    closed_at: datetime | None = None

    @property
    def planned(self) -> bool:
        return bool(self.steps)


@dataclass(frozen=True)
class AttemptVerdict:
    """What `record_attempt` settled: the attempt, and where that leaves the step.

    `attempts_left` is on the result rather than looked up, because it is the
    number the agent has to act on — it is the difference between "try a
    sibling section" and "this step is over".
    """

    attempt: Attempt
    step_state: StepState
    attempts_left: int
    next_step_id: str | None = None
    stale: bool = False


# ---------------------------------------------------------------------------
# Pure questions the service asks instead of re-deriving state from rows
# ---------------------------------------------------------------------------


def attempts_spent(step: Step) -> int:
    """Every recorded attempt counts, settled or not.

    An attempt that died before its verdict still consumed a try — otherwise
    a request that reliably crashes adjudication would buy infinite retries.
    """
    return len(step.attempts)


def attempts_left(step: Step, cap: int) -> int:
    return max(0, cap - attempts_spent(step))


def is_exhausted(step: Step, cap: int) -> bool:
    return attempts_left(step, cap) <= 0


def find_step(investigation: Investigation, step_id: str) -> Step | None:
    return next((step for step in investigation.steps if step.id == step_id), None)


def next_pending(investigation: Investigation) -> Step | None:
    return next((s for s in investigation.steps if s.state is StepState.PENDING), None)


def kept_attempts(investigation: Investigation) -> list[Attempt]:
    return [
        attempt
        for step in investigation.steps
        for attempt in step.attempts
        if attempt.outcome is AttemptOutcome.KEPT
    ]


def kept_uris(investigation: Investigation) -> set[str]:
    """Every anchor an attempt was allowed to keep.

    Both forms are in the set: an agent may cite the uri it passed in, or the
    widened / more precise one verification handed back. Rejecting the first
    would punish an agent for quoting exactly what it read.
    """
    uris: set[str] = set()
    for attempt in kept_attempts(investigation):
        uris.add(attempt.uri)
        if attempt.kept_uri:
            uris.add(attempt.kept_uri)
    return uris


def unbacked_anchors(investigation: Investigation, answer: str) -> list[str]:
    """Anchors cited in `answer` that no attempt was allowed to keep.

    Reads the prose the model is about to publish, because that is the only
    place the failure shows up: every individual quote may have verified and
    the answer still rest on an anchor nobody checked.
    """
    from domain.anchors import find_anchors

    allowed = kept_uris(investigation)
    return [uri for uri in find_anchors(answer) if uri not in allowed]


def cites_nothing(answer: str) -> bool:
    from domain.anchors import find_anchors

    return not find_anchors(answer)


def step_tally(investigation: Investigation) -> dict[StepState, int]:
    tally = dict.fromkeys(StepState, 0)
    for step in investigation.steps:
        tally[step.state] += 1
    return tally

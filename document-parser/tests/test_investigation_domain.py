"""The investigation record as pure data — the state machine and the predicates.

No service, no repository, no parse. These are the questions the service asks
instead of re-deriving state from rows, plus the two that decide whether an
answer is allowed to be published.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.anchors import find_anchors
from domain.investigation import (
    Attempt,
    AttemptOutcome,
    Investigation,
    Step,
    StepState,
    attempts_left,
    attempts_spent,
    cites_nothing,
    find_step,
    is_exhausted,
    kept_uris,
    next_pending,
    step_tally,
    unbacked_anchors,
)

AT = datetime(2026, 8, 30, tzinfo=UTC)
URI = "dstudio://doc/d1@v1#/texts/4"
WIDER = "dstudio://doc/d1@v1#/texts/4..#/texts/5"


def attempt(ordinal=1, outcome=None, uri=URI, kept_uri=None, step_id="s1"):
    return Attempt(
        id=f"a{ordinal}",
        step_id=step_id,
        ordinal=ordinal,
        thought="looks like the right clause",
        uri=uri,
        created_at=AT,
        outcome=outcome,
        kept_uri=kept_uri,
    )


def step(state=StepState.PENDING, attempts=None, step_id="s1", ordinal=1):
    return Step(
        id=step_id,
        ordinal=ordinal,
        question="What is the notice period?",
        why="the question turns on it",
        state=state,
        attempts=list(attempts or []),
    )


def investigation(steps=None, **kwargs):
    return Investigation(
        id="i1",
        document_id="d1",
        version_id="v1",
        question="How does one terminate?",
        created_at=AT,
        steps=list(steps or []),
        **kwargs,
    )


class TestAttemptBudget:
    def test_an_unsettled_attempt_still_spends_a_try(self):
        """Otherwise a request that reliably crashes adjudication buys infinite retries."""
        assert attempts_spent(step(attempts=[attempt(1, outcome=None)])) == 1

    def test_attempts_left_floors_at_zero(self):
        spent = step(attempts=[attempt(i) for i in (1, 2, 3, 4)])
        assert attempts_left(spent, cap=3) == 0
        assert is_exhausted(spent, cap=3)

    def test_a_fresh_step_has_its_whole_budget(self):
        assert attempts_left(step(), cap=3) == 3
        assert not is_exhausted(step(), cap=3)


class TestNavigationOfTheRecord:
    def test_next_pending_skips_settled_steps(self):
        record = investigation(
            [
                step(StepState.ANSWERED, step_id="s1", ordinal=1),
                step(StepState.UNANSWERED, step_id="s2", ordinal=2),
                step(StepState.PENDING, step_id="s3", ordinal=3),
            ]
        )
        assert next_pending(record).id == "s3"

    def test_next_pending_is_none_when_everything_is_settled(self):
        record = investigation([step(StepState.ANSWERED)])
        assert next_pending(record) is None

    def test_find_step_returns_none_for_a_foreign_id(self):
        assert find_step(investigation([step()]), "nope") is None

    def test_step_tally_counts_every_state(self):
        record = investigation(
            [
                step(StepState.ANSWERED, step_id="s1"),
                step(StepState.ANSWERED, step_id="s2"),
                step(StepState.UNANSWERED, step_id="s3"),
            ]
        )
        tally = step_tally(record)
        assert tally[StepState.ANSWERED] == 2
        assert tally[StepState.UNANSWERED] == 1
        assert tally[StepState.PENDING] == 0


class TestKeptAnchors:
    def test_only_kept_attempts_contribute(self):
        record = investigation(
            [
                step(
                    attempts=[
                        attempt(1, outcome=AttemptOutcome.QUOTE_DRIFT),
                        attempt(2, outcome=AttemptOutcome.KEPT),
                    ]
                )
            ]
        )
        assert kept_uris(record) == {URI}

    def test_both_the_sent_and_the_widened_anchor_are_allowed(self):
        """An agent quoting exactly what it read must not be punished for it."""
        record = investigation(
            [step(attempts=[attempt(1, outcome=AttemptOutcome.KEPT, kept_uri=WIDER)])]
        )
        assert kept_uris(record) == {URI, WIDER}

    def test_an_unsettled_attempt_keeps_nothing(self):
        assert kept_uris(investigation([step(attempts=[attempt(1)])])) == set()


class TestAnswerBacking:
    def test_an_anchor_nobody_kept_is_reported(self):
        record = investigation([step(attempts=[attempt(1, outcome=AttemptOutcome.KEPT)])])
        answer = f"The notice is three months ({URI}), see also dstudio://doc/d1@v1#/texts/9."
        assert unbacked_anchors(record, answer) == ["dstudio://doc/d1@v1#/texts/9"]

    def test_a_fully_backed_answer_has_no_gaps(self):
        record = investigation([step(attempts=[attempt(1, outcome=AttemptOutcome.KEPT)])])
        assert unbacked_anchors(record, f"Three months. {URI}") == []

    def test_citing_the_widened_anchor_is_backed(self):
        record = investigation(
            [step(attempts=[attempt(1, outcome=AttemptOutcome.KEPT, kept_uri=WIDER)])]
        )
        assert unbacked_anchors(record, f"See {WIDER}.") == []

    @pytest.mark.parametrize(
        ("answer", "expected"),
        [
            ("The document does not say.", True),
            (f"It says three months: {URI}", False),
        ],
    )
    def test_cites_nothing(self, answer, expected):
        assert cites_nothing(answer) is expected


class TestFindAnchors:
    def test_punctuation_around_an_anchor_is_not_part_of_it(self):
        assert find_anchors(f"See ({URI}).") == [URI]

    def test_anchors_are_deduplicated_in_order(self):
        other = "dstudio://doc/d1@v1#/texts/9"
        assert find_anchors(f"{URI} then {other} then {URI}") == [URI, other]

    def test_prose_without_anchors_yields_nothing(self):
        assert find_anchors("No citation here, only confidence.") == []

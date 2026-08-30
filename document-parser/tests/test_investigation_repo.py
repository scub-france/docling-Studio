"""`SqliteInvestigationRepository` — the journal against a real database.

Temp-file SQLite, same fixture pattern as `test_repos.py`. Two things here are
not exercisable against the in-memory fake the service tests use: the ordinal
the database assigns inside the cap check, and what happens when two callers
race for the last attempt in a step.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from domain.investigation import (
    Attempt,
    AttemptOutcome,
    Investigation,
    InvestigationState,
    Step,
    StepState,
)
from domain.models import Document
from domain.ports import AttemptBudgetSpentError
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.investigation_repo import SqliteInvestigationRepository

AT = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
DOC_ID = "doc-1"
URI = "dstudio://doc/doc-1@an-1#/texts/4"


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    await SqliteDocumentRepository().insert(
        Document(id=DOC_ID, filename="contrat.pdf", storage_path="/tmp/contrat.pdf")
    )


@pytest.fixture
def repo():
    return SqliteInvestigationRepository()


def make_investigation(investigation_id="i1", document_id=DOC_ID, **kwargs):
    return Investigation(
        id=investigation_id,
        document_id=document_id,
        version_id="an-1",
        question="Comment résilier ?",
        created_at=AT,
        **kwargs,
    )


def make_step(step_id="s1", ordinal=1):
    return Step(id=step_id, ordinal=ordinal, question=f"q{ordinal}", why="parce que")


def make_attempt(step_id="s1", attempt_id="a1", uri=URI, quote=None):
    return Attempt(
        id=attempt_id,
        step_id=step_id,
        ordinal=0,
        thought="looks right",
        uri=uri,
        created_at=AT,
        quote=quote,
    )


class TestRoundTrip:
    async def test_an_investigation_comes_back_as_it_went_in(self, repo):
        await repo.create(make_investigation())
        found = await repo.find_by_id("i1")

        assert found.question == "Comment résilier ?"
        assert found.version_id == "an-1"
        assert found.state is InvestigationState.OPEN
        assert found.stale is False
        assert found.steps == []

    async def test_an_unknown_id_is_none_rather_than_an_error(self, repo):
        assert await repo.find_by_id("nope") is None

    async def test_steps_and_attempts_are_assembled_in_order(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step("s2", 2), make_step("s1", 1)])
        await repo.record_attempt(make_attempt("s1", "a1"), cap=3)
        await repo.record_attempt(make_attempt("s1", "a2"), cap=3)

        found = await repo.find_by_id("i1")
        assert [s.ordinal for s in found.steps] == [1, 2]
        assert [a.ordinal for a in found.steps[0].attempts] == [1, 2]

    async def test_adding_no_steps_is_a_no_op(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [])
        assert (await repo.find_by_id("i1")).steps == []


class TestAttemptBudget:
    async def test_the_database_assigns_the_ordinal(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])

        first = await repo.record_attempt(make_attempt(attempt_id="a1"), cap=3)
        second = await repo.record_attempt(make_attempt(attempt_id="a2"), cap=3)
        assert (first.ordinal, second.ordinal) == (1, 2)

    async def test_the_cap_refuses_the_insert_rather_than_recording_it(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])
        for index in range(2):
            await repo.record_attempt(make_attempt(attempt_id=f"a{index}"), cap=2)

        with pytest.raises(AttemptBudgetSpentError):
            await repo.record_attempt(make_attempt(attempt_id="a9"), cap=2)
        assert len((await repo.find_by_id("i1")).steps[0].attempts) == 2

    async def test_concurrent_callers_cannot_both_take_the_last_attempt(self, repo):
        """`stateless_http` has no session, so two workers can land at once."""
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])
        await repo.record_attempt(make_attempt(attempt_id="a0"), cap=2)

        results = await asyncio.gather(
            repo.record_attempt(make_attempt(attempt_id="a1"), cap=2),
            repo.record_attempt(make_attempt(attempt_id="a2"), cap=2),
            return_exceptions=True,
        )
        spent = [r for r in results if isinstance(r, AttemptBudgetSpentError)]
        assert len(spent) == 1, "exactly one caller must lose"
        assert len((await repo.find_by_id("i1")).steps[0].attempts) == 2


class TestSettling:
    async def test_a_verdict_is_persisted_onto_the_attempt(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])
        stored = await repo.record_attempt(make_attempt(quote="trois mois"), cap=3)

        await repo.settle_attempt(
            replace(
                stored,
                outcome=AttemptOutcome.KEPT,
                detail="verified",
                kept_uri=URI,
            )
        )
        attempt = (await repo.find_by_id("i1")).steps[0].attempts[0]
        assert attempt.outcome is AttemptOutcome.KEPT
        assert attempt.kept_uri == URI
        assert attempt.quote == "trois mois"

    async def test_an_unsettled_attempt_reads_back_with_no_outcome(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])
        await repo.record_attempt(make_attempt(), cap=3)

        attempt = (await repo.find_by_id("i1")).steps[0].attempts[0]
        assert attempt.outcome is None
        assert attempt.settled is False

    async def test_step_state_and_staleness_are_persisted(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])

        await repo.set_step_state("s1", StepState.UNANSWERED)
        await repo.mark_stale("i1")

        found = await repo.find_by_id("i1")
        assert found.steps[0].state is StepState.UNANSWERED
        assert found.stale is True

    async def test_closing_stores_the_answer_and_the_time(self, repo):
        await repo.create(make_investigation())
        await repo.close("i1", answer="Trois mois.", at=AT)

        found = await repo.find_by_id("i1")
        assert found.state is InvestigationState.CLOSED
        assert found.answer == "Trois mois."
        assert found.closed_at == AT


class TestListing:
    async def test_open_investigations_are_counted_per_document(self, repo):
        await repo.create(make_investigation("i1"))
        await repo.create(make_investigation("i2"))
        await repo.close("i2", answer="done", at=AT)

        assert await repo.count_open_for_document(DOC_ID) == 1
        assert await repo.count_open_for_document("other") == 0

    async def test_listing_is_newest_first_and_limited(self, repo):
        for index in range(3):
            await repo.create(
                replace(make_investigation(f"i{index}"), created_at=AT.replace(hour=12 + index))
            )
        found = await repo.find_for_document(DOC_ID, limit=2)
        assert [i.id for i in found] == ["i2", "i1"]


class TestCascade:
    async def test_deleting_the_document_takes_its_investigations_with_it(self, repo):
        await repo.create(make_investigation())
        await repo.add_steps("i1", [make_step()])
        await repo.record_attempt(make_attempt(), cap=3)

        assert await SqliteDocumentRepository().delete(DOC_ID) is True
        assert await repo.find_by_id("i1") is None

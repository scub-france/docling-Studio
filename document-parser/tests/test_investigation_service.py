"""The journal's use cases — above all, the verdict the server reaches on a ref.

The point of this suite is the adjudication matrix: one case per outcome, with
and without a quote, plus what each verdict does to the step's budget. That is
the behaviour the whole feature exists for — a bad ref becomes a second
attempt instead of a wrong answer — and it is decided here, not by the model.
"""

from __future__ import annotations

import copy

import pytest

from domain.investigation import AttemptOutcome, InvestigationState, StepState
from services.navigation_config import InvestigationConfig
from services.navigation_errors import (
    DocumentNotFoundError,
    InvalidArgumentError,
    InvestigationClosedError,
    InvestigationNotFoundError,
    NoParseError,
    StepNotFoundError,
    StepSettledError,
    UnbackedAnswerError,
)
from tests.navigation_fixtures import (
    DOC_ID,
    JOB_ID,
    PREAVIS_REF,
    PREAVIS_TEXT,
    SECTIONED,
    FakeInvestigationRepository,
    anchor_uri,
    make_document,
    make_document_tools,
    make_job,
)

PREAVIS_URI = anchor_uri(PREAVIS_REF)
PREAVIS_SECTION_URI = anchor_uri("#/texts/3")


@pytest.fixture
def service():
    return make_document_tools().investigations


async def planned(service, *, questions=("Quel est le préavis ?",)):
    investigation, _ = await service.open(document="contrat", question="Comment résilier ?")
    return await service.plan(investigation.id, [(q, "parce que") for q in questions])


class TestOpen:
    async def test_it_pins_the_parse_and_returns_the_map(self, service):
        investigation, outline = await service.open(document="contrat", question="Résiliation ?")

        assert investigation.document_id == DOC_ID
        assert investigation.version_id == JOB_ID
        assert investigation.state is InvestigationState.OPEN
        assert outline.nodes, "the outline ships with the open — no second call"

    async def test_an_empty_question_is_refused(self, service):
        with pytest.raises(InvalidArgumentError):
            await service.open(document="contrat", question="   ")

    async def test_an_unknown_document_is_refused(self, service):
        with pytest.raises(DocumentNotFoundError):
            await service.open(document="bail-commercial", question="Résiliation ?")

    async def test_an_ambiguous_name_is_refused_rather_than_guessed(self):
        tools = make_document_tools(
            documents=[make_document("d1", "contrat-a.pdf"), make_document("d2", "contrat-b.pdf")]
        )
        with pytest.raises(InvalidArgumentError, match="matches several documents"):
            await tools.investigations.open(document="contrat", question="Résiliation ?")

    async def test_an_unparsed_document_has_nothing_to_investigate(self):
        tools = make_document_tools(job=None)
        with pytest.raises(NoParseError):
            await tools.investigations.open(document="contrat", question="Résiliation ?")

    async def test_open_investigations_are_capped_per_document(self):
        tools = make_document_tools(
            investigation_config=InvestigationConfig(max_open_per_document=1)
        )
        await tools.investigations.open(document="contrat", question="Une")
        with pytest.raises(InvalidArgumentError, match="already has 1 open"):
            await tools.investigations.open(document="contrat", question="Deux")


class TestPlan:
    async def test_steps_are_numbered_in_the_order_given(self, service):
        investigation = await planned(service, questions=("Préavis ?", "Indemnité ?"))
        assert [(s.ordinal, s.question) for s in investigation.steps] == [
            (1, "Préavis ?"),
            (2, "Indemnité ?"),
        ]

    async def test_a_plan_cannot_be_submitted_twice(self, service):
        investigation = await planned(service)
        with pytest.raises(InvestigationClosedError, match="already planned"):
            await service.plan(investigation.id, [("Autre chose ?", "")])

    async def test_an_empty_plan_is_refused(self, service):
        investigation, _ = await service.open(document="contrat", question="Q")
        with pytest.raises(InvalidArgumentError):
            await service.plan(investigation.id, [("   ", "")])

    async def test_a_plan_is_capped(self):
        tools = make_document_tools(
            investigation_config=InvestigationConfig(max_steps_per_investigation=2)
        )
        investigation, _ = await tools.investigations.open(document="contrat", question="Q")
        with pytest.raises(InvalidArgumentError, match="capped at 2 steps"):
            await tools.investigations.plan(investigation.id, [(f"q{i}", "") for i in range(3)])

    async def test_planning_an_unknown_investigation_is_refused(self, service):
        with pytest.raises(InvestigationNotFoundError):
            await service.plan("nope", [("q", "")])


class TestAdjudication:
    """One case per outcome. The server decides; the model is only heard."""

    async def test_a_verified_quote_is_kept_and_settles_the_step(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="12.2 should carry the notice period",
            uri=PREAVIS_URI,
            quote=PREAVIS_TEXT,
        )
        assert verdict.attempt.outcome is AttemptOutcome.KEPT
        assert verdict.step_state is StepState.ANSWERED
        assert verdict.attempts_left == 2

    async def test_a_ref_without_a_quote_is_kept_on_resolution_alone(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="reading it first",
            uri=PREAVIS_URI,
        )
        assert verdict.attempt.outcome is AttemptOutcome.KEPT
        assert "nothing was verified" in verdict.attempt.detail

    async def test_a_fabricated_quote_drifts_and_leaves_the_step_open(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="I think it says six months",
            uri=PREAVIS_URI,
            quote="Le préavis est de six mois.",
        )
        assert verdict.attempt.outcome is AttemptOutcome.QUOTE_DRIFT
        assert verdict.attempt.actual_quote
        assert verdict.step_state is StepState.PENDING
        assert verdict.attempts_left == 2

    async def test_an_unknown_ref_is_rejected(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="guessing",
            uri=anchor_uri("#/texts/999"),
        )
        assert verdict.attempt.outcome is AttemptOutcome.UNKNOWN_REF

    async def test_a_malformed_anchor_is_rejected_before_any_read(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="built one myself",
            uri="texts/4",
        )
        assert verdict.attempt.outcome is AttemptOutcome.BAD_ANCHOR

    async def test_an_anchor_from_another_document_is_rejected(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="wrong file",
            uri=anchor_uri(PREAVIS_REF, doc_id="other-doc"),
        )
        assert verdict.attempt.outcome is AttemptOutcome.FOREIGN_DOCUMENT

    async def test_an_element_with_no_text_is_rejected(self):
        payload = copy.deepcopy(SECTIONED)
        payload["texts"][7]["text"] = ""  # #/texts/7 — "Les factures…"
        tools = make_document_tools(job=make_job(payload))
        investigation = await planned(tools.investigations)

        verdict = await tools.investigations.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="empty block",
            uri=anchor_uri("#/texts/7"),
        )
        assert verdict.attempt.outcome is AttemptOutcome.EMPTY_ELEMENT

    async def test_a_section_anchor_is_kept_with_the_precise_element_to_cite(self, service):
        """Verification hands back the element inside the section; that is the
        anchor to publish, and the one recorded as kept."""
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="the whole 12.2 section",
            uri=PREAVIS_SECTION_URI,
            quote=PREAVIS_TEXT,
        )
        assert verdict.attempt.outcome is AttemptOutcome.KEPT
        assert verdict.attempt.kept_uri == PREAVIS_URI
        assert verdict.attempt.citation_uri == PREAVIS_URI

    async def test_a_superseded_parse_still_verifies_and_flags_the_investigation(self):
        """`stale_version` is a kept citation — the quote is really there."""
        old, new = make_job(job_id="an-0"), make_job(job_id="an-1")
        tools = make_document_tools(jobs=[old, new])
        investigation = await planned(tools.investigations)

        verdict = await tools.investigations.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="from an earlier read",
            uri=anchor_uri(PREAVIS_REF, job_id="an-0"),
            quote=PREAVIS_TEXT,
        )
        assert verdict.attempt.outcome is AttemptOutcome.KEPT
        assert verdict.stale is True


class TestAttemptBudget:
    async def test_the_step_closes_as_unanswered_when_the_budget_runs_out(self, service):
        investigation = await planned(service)
        step_id = investigation.steps[0].id
        for index in range(3):
            verdict = await service.record_attempt(
                investigation_id=investigation.id,
                step_id=step_id,
                thought=f"try {index}",
                uri=PREAVIS_URI,
                quote="Le préavis est de six mois.",
            )
        assert verdict.step_state is StepState.UNANSWERED
        assert verdict.attempts_left == 0

    async def test_a_fourth_attempt_is_refused_rather_than_served(self, service):
        investigation = await planned(service)
        step_id = investigation.steps[0].id
        for _ in range(3):
            await service.record_attempt(
                investigation_id=investigation.id,
                step_id=step_id,
                thought="try",
                uri=PREAVIS_URI,
                quote="Le préavis est de six mois.",
            )
        with pytest.raises(StepSettledError, match="unanswered"):
            await service.record_attempt(
                investigation_id=investigation.id,
                step_id=step_id,
                thought="one more",
                uri=PREAVIS_URI,
                quote=PREAVIS_TEXT,
            )

    async def test_an_answered_step_takes_no_further_attempts(self, service):
        investigation = await planned(service)
        step_id = investigation.steps[0].id
        await service.record_attempt(
            investigation_id=investigation.id,
            step_id=step_id,
            thought="found it",
            uri=PREAVIS_URI,
            quote=PREAVIS_TEXT,
        )
        with pytest.raises(StepSettledError, match="already"):
            await service.record_attempt(
                investigation_id=investigation.id,
                step_id=step_id,
                thought="again",
                uri=PREAVIS_URI,
            )

    async def test_the_next_pending_step_is_named(self, service):
        investigation = await planned(service, questions=("Préavis ?", "Indemnité ?"))
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="found it",
            uri=PREAVIS_URI,
            quote=PREAVIS_TEXT,
        )
        assert verdict.next_step_id == investigation.steps[1].id

    async def test_an_unknown_step_is_refused(self, service):
        investigation = await planned(service)
        with pytest.raises(StepNotFoundError):
            await service.record_attempt(
                investigation_id=investigation.id,
                step_id="nope",
                thought="…",
                uri=PREAVIS_URI,
            )

    async def test_the_thought_is_recorded_even_when_the_ref_is_rejected(self, service):
        investigation = await planned(service)
        verdict = await service.record_attempt(
            investigation_id=investigation.id,
            step_id=investigation.steps[0].id,
            thought="I reasoned my way to a wrong ref",
            uri="not-an-anchor",
        )
        assert verdict.attempt.thought == "I reasoned my way to a wrong ref"


class TestClose:
    async def test_an_answer_citing_a_kept_anchor_is_published(self, service):
        investigation = await service_with_one_kept(service)
        closed = await service.close(investigation.id, f"Trois mois. {PREAVIS_URI}")

        assert closed.state is InvestigationState.CLOSED
        assert closed.closed_at is not None

    async def test_an_answer_citing_an_unverified_anchor_is_refused(self, service):
        investigation = await service_with_one_kept(service)
        with pytest.raises(UnbackedAnswerError, match="never kept"):
            await service.close(investigation.id, f"Trois mois {anchor_uri('#/texts/7')}.")

    async def test_an_investigation_with_evidence_must_cite_it(self, service):
        investigation = await service_with_one_kept(service)
        with pytest.raises(UnbackedAnswerError, match="cites none of it"):
            await service.close(investigation.id, "Le préavis est de trois mois.")

    async def test_an_investigation_that_found_nothing_may_say_so(self, service):
        """The honest 'the document does not answer' case — and only that case."""
        investigation = await planned(service)
        for _ in range(3):
            await service.record_attempt(
                investigation_id=investigation.id,
                step_id=investigation.steps[0].id,
                thought="try",
                uri=PREAVIS_URI,
                quote="Le préavis est de six mois.",
            )
        closed = await service.close(investigation.id, "Ce document ne le dit pas.")
        assert closed.state is InvestigationState.CLOSED

    async def test_an_empty_answer_is_refused(self, service):
        investigation = await service_with_one_kept(service)
        with pytest.raises(InvalidArgumentError):
            await service.close(investigation.id, "   ")

    async def test_a_closed_investigation_takes_no_further_writes(self, service):
        investigation = await service_with_one_kept(service)
        await service.close(investigation.id, f"Trois mois. {PREAVIS_URI}")
        with pytest.raises(InvestigationClosedError):
            await service.close(investigation.id, f"Encore. {PREAVIS_URI}")


class TestView:
    async def test_the_record_comes_back_with_its_navigation_tree(self, service):
        investigation = await service_with_one_kept(service)
        record, nodes = await service.view(investigation.id)

        assert record.steps[0].attempts[0].outcome is AttemptOutcome.KEPT
        assert [node.ref for node in nodes] == ["#/texts/0", "#/texts/1", "#/texts/3"]
        assert nodes[-1].status == "kept"

    async def test_an_unknown_investigation_is_refused(self, service):
        with pytest.raises(InvestigationNotFoundError):
            await service.view("nope")

    async def test_an_open_investigation_can_be_read_back_to_resume(self, service):
        investigation = await planned(service)
        record, _ = await service.view(investigation.id)
        assert record.state is InvestigationState.OPEN


class TestRepositoryContract:
    async def test_the_fake_and_the_service_agree_on_where_state_lives(self):
        """The service never keeps state of its own — everything is in the repo."""
        repo = FakeInvestigationRepository()
        tools = make_document_tools(investigations=repo)
        investigation = await planned(tools.investigations)

        assert list(repo.investigations) == [investigation.id]
        assert repo.investigations[investigation.id].steps[0].id == investigation.steps[0].id


async def service_with_one_kept(service):
    investigation = await planned(service)
    await service.record_attempt(
        investigation_id=investigation.id,
        step_id=investigation.steps[0].id,
        thought="12.2 carries it",
        uri=PREAVIS_URI,
        quote=PREAVIS_TEXT,
    )
    return investigation

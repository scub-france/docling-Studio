"""Investigating a document: plan, try a ref, be told whether it held up.

The reading services answer *what does this say*. This one answers *did that
answer the question I was chasing* — and it answers it server-side, which is
the whole point. An agent proposes a ref; whether the anchor resolves, the
element carries text and the quote is really there are not opinions, so none
of them is left to the model that has an interest in the answer being yes.
The verdict itself lives in `investigation_adjudicator`; this module owns the
sequencing, the budgets and the bookkeeping around it.

What the model does own is the thinking: the decomposition into steps, and
the `thought` on every attempt. Those are recorded verbatim and never
checked — see `domain.investigation`. The journal is honest about which half
is which.

Transport-agnostic like its peers: `mcp_adapter` is the first consumer, and
an HTTP route (#330) would be the same calls.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from domain.investigation import (
    Attempt,
    AttemptOutcome,
    AttemptVerdict,
    Investigation,
    InvestigationState,
    Step,
    StepState,
    cites_nothing,
    find_step,
    step_tally,
    unbacked_anchors,
)
from domain.investigation_map import build_navigation_map
from domain.ports import AttemptBudgetSpentError
from services.investigation_adjudicator import Adjudicator
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

if TYPE_CHECKING:
    from domain.investigation_map import MapNode
    from domain.navigation import DocumentOutline, DocumentSummary
    from domain.ports import InvestigationRepository
    from services.citation_service import CitationService
    from services.navigation_service import NavigationService
    from services.parse_loader import ParseLoader

logger = logging.getLogger(__name__)

# The deepest map the outline builder will draw. An investigation is read
# after the fact, so the finest available grain is right — unlike
# `get_outline`, where depth is what keeps the first call cheap.
_MAP_DEPTH = 6


class InvestigationService:
    def __init__(
        self,
        *,
        parses: ParseLoader,
        navigation: NavigationService,
        citations: CitationService,
        investigations: InvestigationRepository,
        config: InvestigationConfig | None = None,
    ) -> None:
        self._parses = parses
        self._navigation = navigation
        self._repo = investigations
        self._config = config or InvestigationConfig()
        self._adjudicator = Adjudicator(navigation=navigation, citations=citations)

    @property
    def config(self) -> InvestigationConfig:
        return self._config

    async def open(self, *, document: str, question: str) -> tuple[Investigation, DocumentOutline]:
        """Resolve the document, pin its parse, and hand back the map.

        The outline comes back with the investigation rather than in a second
        call: one round trip saved, and *map before text* stops being advice.
        """
        question = (question or "").strip()
        if not question:
            raise InvalidArgumentError("An investigation needs a question to investigate.")
        summary = await self._resolve_document(document)
        await self._check_open_budget(summary.document_id)

        outline = await self._navigation.get_outline(summary.document_id)
        investigation = Investigation(
            id=uuid4().hex,
            document_id=outline.document_id,
            version_id=outline.version_id,
            question=question,
            created_at=datetime.now(UTC),
        )
        await self._repo.create(investigation)
        logger.info(
            "Investigation %s opened on document %s (parse %s)",
            investigation.id,
            investigation.document_id,
            investigation.version_id,
        )
        return investigation, outline

    async def plan(self, investigation_id: str, steps: list[tuple[str, str]]) -> Investigation:
        """Record the decomposition. Once — a plan that grows is not a plan."""
        investigation = await self._load_open(investigation_id)
        if investigation.planned:
            raise InvestigationClosedError(
                "This investigation is already planned. Work the steps it has, or open a "
                "new investigation for a different decomposition."
            )
        planned = self._build_steps(steps)
        await self._repo.add_steps(investigation.id, planned)
        return replace(investigation, steps=planned)

    async def record_attempt(
        self,
        *,
        investigation_id: str,
        step_id: str,
        thought: str,
        uri: str,
        quote: str | None = None,
    ) -> AttemptVerdict:
        """Try `uri` against a step, and settle whether it holds up."""
        investigation = await self._load_open(investigation_id)
        step = self._pending_step(investigation, step_id)
        attempt = await self._open_attempt(step, thought=thought, uri=uri, quote=quote)

        settled, stale = await self._adjudicator.settle(investigation, attempt)
        await self._repo.settle_attempt(settled)
        if stale and not investigation.stale:
            await self._repo.mark_stale(investigation.id)
        return await self._settle_step(investigation, step, settled, stale=stale)

    async def close(self, investigation_id: str, answer: str) -> Investigation:
        """Publish the answer — if every anchor in it was allowed to be kept."""
        investigation = await self._load_open(investigation_id)
        answer = (answer or "").strip()
        if not answer:
            raise InvalidArgumentError("An investigation is closed with an answer, not silence.")
        self._check_backing(investigation, answer)

        at = datetime.now(UTC)
        await self._repo.close(investigation.id, answer=answer, at=at)
        tally = step_tally(investigation)
        logger.info(
            "Investigation %s closed (%d answered, %d unanswered)",
            investigation.id,
            tally[StepState.ANSWERED],
            tally[StepState.UNANSWERED],
        )
        return replace(investigation, state=InvestigationState.CLOSED, answer=answer, closed_at=at)

    async def view(self, investigation_id: str) -> tuple[Investigation, list[MapNode]]:
        """The record, and the navigation tree derived from it."""
        investigation = await self._repo.find_by_id(investigation_id)
        if investigation is None:
            raise InvestigationNotFoundError(f"No investigation {investigation_id!r}.")
        parse = await self._parses.load(investigation.document_id, investigation.version_id)
        outline = await self._navigation.get_outline(
            investigation.document_id,
            version_id=investigation.version_id,
            depth=_MAP_DEPTH,
        )
        return investigation, build_navigation_map(outline, investigation, parse.index)

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------

    def _build_steps(self, steps: list[tuple[str, str]]) -> list[Step]:
        cleaned = [(q.strip(), (why or "").strip()) for q, why in steps if (q or "").strip()]
        if not cleaned:
            raise InvalidArgumentError("A plan needs at least one step with a question.")
        cap = self._config.max_steps_per_investigation
        if len(cleaned) > cap:
            raise InvalidArgumentError(
                f"A plan is capped at {cap} steps ({len(cleaned)} given). Fold the narrow "
                "ones together — a step is a question the document can answer, not a sentence."
            )
        return [
            Step(id=uuid4().hex, ordinal=index, question=question, why=why)
            for index, (question, why) in enumerate(cleaned, start=1)
        ]

    async def _open_attempt(
        self,
        step: Step,
        *,
        thought: str,
        uri: str,
        quote: str | None,
    ) -> Attempt:
        """Persist the attempt before adjudicating it.

        Deliberate order: the thought is on disk before anything can fail, so
        a crash mid-verdict loses the verdict and not the reasoning. The
        repository assigns the ordinal inside the same statement that checks
        the cap, which is what makes the budget hold under `stateless_http`.
        """
        attempt = Attempt(
            id=uuid4().hex,
            step_id=step.id,
            ordinal=0,
            thought=(thought or "").strip(),
            uri=(uri or "").strip(),
            created_at=datetime.now(UTC),
            quote=(quote or "").strip() or None,
        )
        try:
            return await self._repo.record_attempt(attempt, cap=self._config.max_attempts_per_step)
        except AttemptBudgetSpentError as exc:
            await self._repo.set_step_state(step.id, StepState.UNANSWERED)
            raise StepSettledError(
                f"Step {step.id} has spent its {self._config.max_attempts_per_step} attempts "
                "and is closed as unanswered. Say so in the answer rather than trying again: "
                "a document that does not answer is a finding."
            ) from exc

    async def _settle_step(
        self,
        investigation: Investigation,
        step: Step,
        attempt: Attempt,
        *,
        stale: bool,
    ) -> AttemptVerdict:
        cap = self._config.max_attempts_per_step
        if attempt.outcome is AttemptOutcome.KEPT:
            state = StepState.ANSWERED
        elif attempt.ordinal >= cap:
            state = StepState.UNANSWERED
        else:
            state = StepState.PENDING
        if state is not StepState.PENDING:
            await self._repo.set_step_state(step.id, state)

        updated = [replace(s, state=state) if s.id == step.id else s for s in investigation.steps]
        return AttemptVerdict(
            attempt=attempt,
            step_state=state,
            attempts_left=max(0, cap - attempt.ordinal),
            next_step_id=next((s.id for s in updated if s.state is StepState.PENDING), None),
            stale=stale or investigation.stale,
        )

    def _check_backing(self, investigation: Investigation, answer: str) -> None:
        """Refuse an answer the investigation did not earn."""
        unbacked = unbacked_anchors(investigation, answer)
        if unbacked:
            raise UnbackedAnswerError(
                "These anchors were never kept by an attempt in this investigation: "
                + ", ".join(unbacked)
                + ". Record and verify them first, or drop the claims that rest on them."
            )
        if cites_nothing(answer) and step_tally(investigation)[StepState.ANSWERED]:
            raise UnbackedAnswerError(
                "This investigation kept evidence and the answer cites none of it. Cite the "
                "anchors you kept, or say plainly which steps the document did not answer."
            )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    async def _load_open(self, investigation_id: str) -> Investigation:
        investigation = await self._repo.find_by_id(investigation_id)
        if investigation is None:
            raise InvestigationNotFoundError(
                f"No investigation {investigation_id!r}. Open one with open_investigation."
            )
        if investigation.state is not InvestigationState.OPEN:
            raise InvestigationClosedError(
                f"Investigation {investigation_id} is {investigation.state} and accepts no "
                "further writes. Read it with get_investigation."
            )
        return investigation

    async def _resolve_document(self, document: str) -> DocumentSummary:
        needle = (document or "").strip()
        if not needle:
            raise InvalidArgumentError("Name the document to investigate.")
        matches = (await self._navigation.find_documents(query=needle, limit=5)).documents
        if not matches:
            raise DocumentNotFoundError(
                f"No document matching {needle!r}. find_documents lists what is available; "
                "an empty result with truncated=true means 'not in that window'."
            )
        if len(matches) > 1:
            names = ", ".join(f"{d.filename} ({d.document_id})" for d in matches)
            raise InvalidArgumentError(
                f"{needle!r} matches several documents: {names}. Ask which one before reading."
            )
        if not matches[0].version_id:
            raise NoParseError(
                f"{matches[0].filename} has never been parsed, so there is nothing to "
                "investigate. Run an analysis in Studio first."
            )
        return matches[0]

    async def _check_open_budget(self, document_id: str) -> None:
        cap = self._config.max_open_per_document
        if await self._repo.count_open_for_document(document_id) >= cap:
            raise InvalidArgumentError(
                f"This document already has {cap} open investigations. Close one before "
                "opening another — an investigation is closed with its answer."
            )

    def _pending_step(self, investigation: Investigation, step_id: str) -> Step:
        step = find_step(investigation, step_id)
        if step is None:
            raise StepNotFoundError(
                f"No step {step_id!r} in investigation {investigation.id}. Step ids come "
                "from plan_steps."
            )
        if step.state is not StepState.PENDING:
            raise StepSettledError(
                f"Step {step_id} is already {step.state}. Move to the next pending step."
            )
        return step

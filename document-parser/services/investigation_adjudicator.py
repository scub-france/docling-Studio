"""The server's verdict on one ref — the half the model does not get to decide.

Split out of `InvestigationService` because it is a different question. The
service sequences a use case; this decides a fact, and it decides it from
evidence that is not open to interpretation: an anchor parses or it does not,
an element resolves or it does not, a quote is in the text or it is not.

First failure wins, cheapest check first — a malformed uri costs a regex, a
missing element costs an indexed read, a drifted quote costs the full
verification. Nothing here writes; the caller persists what it returns.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from domain.anchors import AnchorParseError, DocumentAnchor
from domain.investigation import Attempt, AttemptOutcome
from domain.navigation import CitationStatus
from services.navigation_errors import NoParseError, RefNotFoundError

if TYPE_CHECKING:
    from domain.investigation import Investigation
    from services.citation_service import CitationService
    from services.navigation_service import NavigationService


class Adjudicator:
    """Settles one attempt against the document. Returns `(attempt, stale)`."""

    def __init__(self, *, navigation: NavigationService, citations: CitationService) -> None:
        self._navigation = navigation
        self._citations = citations

    async def settle(
        self,
        investigation: Investigation,
        attempt: Attempt,
    ) -> tuple[Attempt, bool]:
        try:
            anchor = DocumentAnchor.parse(attempt.uri)
        except AnchorParseError as exc:
            return _settle(attempt, AttemptOutcome.BAD_ANCHOR, str(exc)), False

        if anchor.document_id != investigation.document_id:
            return _settle(
                attempt,
                AttemptOutcome.FOREIGN_DOCUMENT,
                "That anchor points at another document. An investigation stays inside the "
                f"document it opened on ({investigation.document_id}).",
            ), False

        rejection = await self._read_check(anchor, attempt)
        if rejection is not None:
            return rejection, False
        if not (attempt.quote or "").strip():
            return _settle(
                attempt,
                AttemptOutcome.KEPT,
                "Element read and kept. No quote was given, so nothing was verified — pass "
                "the quote you intend to publish to have it checked.",
            ), False
        return await self._verify(attempt)

    async def _read_check(self, anchor: DocumentAnchor, attempt: Attempt) -> Attempt | None:
        """`None` when the element resolves and carries text; a rejection otherwise."""
        try:
            excerpt = await self._navigation.read_element(
                anchor.document_id,
                anchor.ref,
                version_id=anchor.version_id,
                include="self",
            )
        except (RefNotFoundError, NoParseError) as exc:
            return _settle(attempt, AttemptOutcome.UNKNOWN_REF, str(exc))
        if not excerpt.markdown.strip():
            return _settle(
                attempt,
                AttemptOutcome.EMPTY_ELEMENT,
                "That ref resolves but carries no text — a group, or a page break. Try the "
                "element that holds the passage.",
            )
        return None

    async def _verify(self, attempt: Attempt) -> tuple[Attempt, bool]:
        """Run the quote through `verify_citation` and map its status.

        `stale_version` is a *kept* citation: the quote is really there, the
        parse behind it has merely been superseded. The second element of the
        tuple is what tells the caller to flag the investigation.
        """
        check = await self._citations.verify_citation(attempt.uri, attempt.quote or "")
        # The widened or more precise anchor verification hands back — a span
        # covering a quote that ran across element boundaries, or the exact
        # element inside a section. That is the one worth citing.
        precise = check.citation.uri if check.citation else None

        if check.status is CitationStatus.VERIFIED:
            return _settle(attempt, AttemptOutcome.KEPT, check.detail, kept_uri=precise), False
        if check.status is CitationStatus.STALE_VERSION:
            return _settle(attempt, AttemptOutcome.KEPT, check.detail, kept_uri=precise), True
        if check.status is CitationStatus.QUOTE_DRIFT:
            return _settle(
                attempt,
                AttemptOutcome.QUOTE_DRIFT,
                check.detail,
                actual_quote=check.actual_quote,
            ), False
        return _settle(attempt, AttemptOutcome.UNKNOWN_REF, check.detail), False


def _settle(
    attempt: Attempt,
    outcome: AttemptOutcome,
    detail: str,
    *,
    kept_uri: str | None = None,
    actual_quote: str | None = None,
) -> Attempt:
    return replace(
        attempt,
        outcome=outcome,
        detail=detail,
        kept_uri=kept_uri,
        actual_quote=actual_quote,
    )

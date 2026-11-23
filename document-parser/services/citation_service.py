"""Citations — building them, resolving them, and checking they are real.

Split out of the navigation service because "what does this anchor point at"
and "does this quote really say that" are a different question from "what
should I read next", and because the citation is the part of this surface
that carries a promise: the server, not the model, is the source of truth for
what a document says.

Verification is deliberately tolerant in three ways, each covering how an
honest agent quotes — a partial quote, a quote from inside the section an
anchor covers, and reflowed whitespace — and strict about the two failures
that matter: a ref that does not exist, and a quote that is nowhere in what
the ref covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from domain.anchors import DocumentAnchor, hash_quote, normalise_quote
from domain.element_reader import resolve
from domain.navigation import (
    Citation,
    CitationCheck,
    CitationStatus,
    clip_to_tokens,
    estimate_tokens,
)
from domain.parse_index import parse_page_ref
from domain.quote_location import locate_quote
from domain.spans import get_span_start, is_span
from services.navigation_errors import (
    InvalidArgumentError,
    NavigationServiceError,
    RefNotFoundError,
)

# Below this, a match proves nothing: "e" or "mois" is in most sections.
MIN_QUOTE_CHARS = 10

if TYPE_CHECKING:
    from domain.navigation import ResolvedElement
    from services.navigation_config import NavigationConfig
    from services.parse_loader import LoadedParse, ParseLoader


class CitationService:
    def __init__(self, *, parses: ParseLoader, config: NavigationConfig) -> None:
        self._parses = parses
        self._config = config

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------

    async def get_citation(self, uri: str) -> Citation:
        """Resolve an anchor into the citation it names.

        The read-only half of `verify_citation`, for callers that hold an
        anchor and want what it points at — the citation view, chiefly —
        without claiming a quote to check against it.
        """
        anchor = DocumentAnchor.parse(uri)
        parse = await self._parses.load(anchor.document_id, anchor.version_id)
        element = resolve(parse.index, anchor.ref)
        if element is None:
            raise RefNotFoundError(
                f"Ref {anchor.ref!r} does not exist in version {parse.version_id}."
            )
        return self.build(parse.document.id, parse.version_id, element)

    def check_quote(self, quote: str | None) -> None:
        """Refuse a quote too short to prove anything, or too long for one read.

        Matching runs on the event loop and costs more the longer the quote,
        so a quote no read could have produced is refused before any of it.
        An empty quote passes: the caller decides what "no quote" means.
        """
        claimed = normalise_quote(quote or "")
        if claimed and len(claimed) < MIN_QUOTE_CHARS:
            raise InvalidArgumentError(
                f"A {len(claimed)}-character quote proves nothing. Quote at least "
                f"{MIN_QUOTE_CHARS} characters: the words that carry the claim."
            )
        ceiling = self._config.max_read_tokens
        size = estimate_tokens(quote or "")
        if size > ceiling:
            raise InvalidArgumentError(
                f"The quote is ~{size} tokens; a quote is capped at {ceiling}, the most one "
                "read returns. Quote the passage that carries the claim."
            )

    async def verify_citation(
        self,
        uri: str,
        quote: str,
        *,
        current_parse_ids: dict[str, str] | None = None,
    ) -> CitationCheck:
        """Re-resolve an anchor server-side and check the claimed quote.

        `current_parse_ids` (document id to current parse id) lets a caller
        checking many citations resolve the current parses once; without it
        they are resolved here.
        """
        self.check_quote(quote)
        anchor = DocumentAnchor.parse(uri)
        try:
            parse = await self._parses.load(anchor.document_id, anchor.version_id)
        except NavigationServiceError as exc:
            return CitationCheck(
                valid=False, status=CitationStatus.UNKNOWN_VERSION, detail=str(exc)
            )

        element = resolve(parse.index, anchor.ref)
        if element is None:
            return CitationCheck(
                valid=False,
                status=CitationStatus.UNKNOWN_REF,
                detail=f"Ref {anchor.ref!r} does not exist in version {parse.version_id}.",
            )

        claimed = normalise_quote(quote)
        if not claimed:
            return self._build_drift_check(parse, element, "No quote supplied to verify.")
        match = locate_quote(parse.index, anchor.ref, element, claimed)
        if match is None:
            return self._build_drift_check(
                parse,
                element,
                "The quote does not appear at this anchor. Use `actual_quote` as the "
                "verbatim, or re-read the element.",
            )
        return await self._build_match_check(anchor, parse, match, current_parse_ids)

    def _build_drift_check(
        self, parse: LoadedParse, element: ResolvedElement, detail: str
    ) -> CitationCheck:
        """The failed check, with the anchor's own citation and its verbatim text."""
        return CitationCheck(
            valid=False,
            status=CitationStatus.QUOTE_DRIFT,
            detail=detail,
            citation=self.build(parse.document.id, parse.version_id, element),
            actual_quote=self._clip(element.text),
        )

    async def _build_match_check(
        self,
        anchor: DocumentAnchor,
        parse: LoadedParse,
        match: ResolvedElement,
        current_parse_ids: dict[str, str] | None,
    ) -> CitationCheck:
        """The passed check, flagged stale when the anchor pins a superseded parse."""
        matched = self.build(parse.document.id, parse.version_id, match)
        current = await self._find_superseding_parse(
            parse.document.id, parse.version_id, current_parse_ids
        )
        if current is not None:
            return CitationCheck(
                valid=True,
                status=CitationStatus.STALE_VERSION,
                detail=(
                    "The quote appears verbatim at this anchor, but the anchor pins a "
                    f"parse that is no longer current: {current} is. Re-read the "
                    "document to cite the current parse."
                ),
                citation=matched,
                actual_quote=self._clip(match.text),
            )
        return CitationCheck(
            valid=True,
            status=CitationStatus.VERIFIED,
            detail=_describe_found(anchor.ref, match.ref),
            citation=matched,
            actual_quote=self._clip(match.text),
        )

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, document_id: str, version_id: str, element: ResolvedElement) -> Citation:
        """Assemble the citation for one resolved element.

        The quote is clipped to the same ceiling a read obeys. A budget that
        governed `read_element` but not `verify_citation` would not be a
        budget: a caller wanting an unbudgeted read would simply verify
        instead, and a 300-row table came back at 19 795 tokens that way.
        The hash covers the clipped text, so what is published is what was
        checked.
        """
        anchor = DocumentAnchor(document_id, version_id, element.ref)
        quote = clip_to_tokens(element.text, self._config.max_read_tokens)
        return Citation(
            uri=anchor.uri,
            document_id=document_id,
            version_id=version_id,
            ref=element.ref,
            label=element.label,
            quote=quote,
            quote_hash=hash_quote(quote),
            page=element.page,
            bbox=element.bbox,
            headings=list(element.headings),
            deep_link=self.build_deep_link(version_id, element),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _clip(self, text: str) -> str:
        return clip_to_tokens(text, self._config.max_read_tokens)

    async def _find_superseding_parse(
        self, document_id: str, version_id: str, current_parse_ids: dict[str, str] | None
    ) -> str | None:
        """The id of the current parse when the anchor pins another one."""
        if current_parse_ids is None:
            current_parse_ids = await self._parses.find_current_parse_ids([document_id])
        current = current_parse_ids.get(document_id)
        return current if current is not None and current != version_id else None

    def build_deep_link(self, version_id: str, element: ResolvedElement) -> str | None:
        """The Studio URL that opens the cited parse on this element — None
        without a configured base: a bare path is no link for a reader."""
        base = self._config.studio_base_url.rstrip("/")
        if not base:
            return None
        query: dict[str, str | int] = {}
        # The viewer focuses one element: a span opens on its first, and a
        # virtual page has none — its page is the whole target.
        if parse_page_ref(element.ref) is None:
            query["ref"] = get_span_start(element.ref)
        if element.page is not None:
            query["page"] = element.page
        return f"{base}/analyses/{version_id}" + (f"?{urlencode(query)}" if query else "")


def _describe_found(asked: str, found: str) -> str:
    """What to tell an agent about where its quote actually turned up."""
    if found == asked:
        return "The quote appears verbatim in the cited element."
    if is_span(found):
        return (
            f"The quote runs across several elements ({found}). `citation` carries the span "
            "anchor covering all of them — cite that, not one of the halves."
        )
    return (
        f"The quote appears in {found}, which the cited section covers. "
        "`citation` carries the precise anchor — prefer it."
    )

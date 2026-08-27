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
from urllib.parse import quote as urlquote

from domain.anchors import DocumentAnchor, normalise_quote, quote_hash
from domain.element_reader import element_text, resolve, section_refs
from domain.navigation import Citation, CitationCheck, CitationStatus, clip_to_tokens
from domain.spans import is_span, span_ref, span_start
from services.navigation_errors import NavigationServiceError, RefNotFoundError

if TYPE_CHECKING:
    from domain.navigation import ResolvedElement
    from domain.parse_index import DocumentIndex
    from services.navigation_config import NavigationConfig
    from services.parse_loader import ParseLoader


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

    async def verify_citation(self, uri: str, quote: str) -> CitationCheck:
        """Re-resolve an anchor server-side and check the claimed quote."""
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

        citation = self.build(parse.document.id, parse.version_id, element)
        claimed = normalise_quote(quote)
        if not claimed:
            return CitationCheck(
                valid=False,
                status=CitationStatus.QUOTE_DRIFT,
                detail="No quote supplied to verify.",
                citation=citation,
                actual_quote=self._clipped(element.text),
            )

        match = self._locate_quote(parse.index, anchor.ref, element, claimed)
        if match is None:
            return CitationCheck(
                valid=False,
                status=CitationStatus.QUOTE_DRIFT,
                detail=(
                    "The quote does not appear at this anchor. Use `actual_quote` as the "
                    "verbatim, or re-read the element."
                ),
                citation=citation,
                actual_quote=self._clipped(element.text),
            )

        matched = self.build(parse.document.id, parse.version_id, match)
        current = await self._superseding_parse(parse.document.id, parse.version_id)
        if current is not None:
            return CitationCheck(
                valid=True,
                status=CitationStatus.STALE_VERSION,
                detail=(
                    "The quote appears verbatim at this anchor, but the anchor pins an "
                    f"earlier parse: {current} is now the current one. Re-read the "
                    "document to cite the current parse."
                ),
                citation=matched,
                actual_quote=self._clipped(match.text),
            )
        return CitationCheck(
            valid=True,
            status=CitationStatus.VERIFIED,
            detail=_found_detail(anchor.ref, match.ref),
            citation=matched,
            actual_quote=self._clipped(match.text),
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
            quote_hash=quote_hash(quote),
            page=element.page,
            bbox=element.bbox,
            headings=list(element.headings),
            deep_link=self._deep_link(document_id, element),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _clipped(self, text: str) -> str:
        return clip_to_tokens(text, self._config.max_read_tokens)

    async def _superseding_parse(self, document_id: str, version_id: str) -> str | None:
        """The id of the current parse when the anchor pins an older one."""
        latest = await self._parses.analyses.find_latest_completed_by_document(document_id)
        return latest.id if latest is not None and latest.id != version_id else None

    @staticmethod
    def _locate_quote(
        index: DocumentIndex,
        ref: str,
        element: ResolvedElement,
        claimed: str,
    ) -> ResolvedElement | None:
        """Return the element carrying `claimed`, or None.

        Three passes, narrowest first: the anchor itself, then each element it
        covers, then runs of consecutive elements. The third is what makes a
        quote that finishes in the next paragraph verifiable instead of
        drifted — and it answers with a span anchor, so the citation the agent
        publishes covers the whole passage it quoted.
        """
        if claimed in normalise_quote(element.text):
            return element
        covered = section_refs(index, ref)
        for candidate in covered:
            if candidate == ref:
                continue
            found = resolve(index, candidate)
            if found is not None and claimed in normalise_quote(found.text):
                return found
        return CitationService._locate_across(index, covered, claimed)

    @staticmethod
    def _locate_across(
        index: DocumentIndex,
        refs: list[str],
        claimed: str,
    ) -> ResolvedElement | None:
        """The smallest run of consecutive elements containing `claimed`.

        Windows grow from each starting element and stop as soon as the text
        *before* the window's last addition is already longer than the claim:
        past that point no match could still involve the element the window
        starts at, so extending it only re-tests what the next start will.
        That bound is what keeps this linear-ish over a long section instead
        of quadratic.
        """
        texts = [(ref, normalise_quote(element_text(index, ref))) for ref in refs]
        texts = [(ref, text) for ref, text in texts if text]
        for start, (_, head) in enumerate(texts):
            joined = head
            for end in range(start + 1, len(texts)):
                if len(joined) > len(claimed) + len(head):
                    break
                joined = f"{joined} {texts[end][1]}"
                if claimed in joined:
                    first = CitationService._trim_left(texts, start, end, claimed)
                    return resolve(index, span_ref(texts[first][0], texts[end][0]))
        return None

    @staticmethod
    def _trim_left(
        texts: list[tuple[str, str]],
        start: int,
        end: int,
        claimed: str,
    ) -> int:
        """Drop leading elements the quote does not actually reach into.

        The scan finds the leftmost start that works, and the section's own
        heading works for every quote inside it — so without this, quoting one
        paragraph of Article 12 would come back as a span opening on the title
        of Article 12. The end needs no such trim: the scan already stops at
        the first one that matches.
        """
        while start < end and claimed in " ".join(text for _, text in texts[start + 1 : end + 1]):
            start += 1
        return start

    def _deep_link(self, document_id: str, element: ResolvedElement) -> str:
        """A Studio URL that reopens the cited element in the viewer."""
        # The Studio viewer scrolls to one element, so a span links to the
        # element it opens on rather than to a range it cannot resolve.
        path = f"/docs/{document_id}?ref={urlquote(span_start(element.ref), safe='')}"
        if element.page is not None:
            path += f"&page={element.page}"
        base = self._config.studio_base_url.rstrip("/")
        return f"{base}{path}" if base else path


def _found_detail(asked: str, found: str) -> str:
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

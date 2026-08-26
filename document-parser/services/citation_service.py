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
from domain.element_reader import resolve, section_refs
from domain.navigation import Citation, CitationCheck, CitationStatus
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
                actual_quote=element.text,
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
                actual_quote=element.text,
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
                actual_quote=match.text,
            )
        return CitationCheck(
            valid=True,
            status=CitationStatus.VERIFIED,
            detail=(
                "The quote appears verbatim in the cited element."
                if match.ref == anchor.ref
                else (
                    f"The quote appears in {match.ref}, which the cited section covers. "
                    "`citation` carries the precise anchor — prefer it."
                )
            ),
            citation=matched,
            actual_quote=match.text,
        )

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, document_id: str, version_id: str, element: ResolvedElement) -> Citation:
        """Assemble the citation for one resolved element."""
        anchor = DocumentAnchor(document_id, version_id, element.ref)
        return Citation(
            uri=anchor.uri,
            document_id=document_id,
            version_id=version_id,
            ref=element.ref,
            label=element.label,
            quote=element.text,
            quote_hash=quote_hash(element.text),
            page=element.page,
            bbox=element.bbox,
            headings=list(element.headings),
            deep_link=self._deep_link(document_id, element),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

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
        """Return the element carrying `claimed`, or None. Searches the anchor
        first, then the elements it covers."""
        if claimed in normalise_quote(element.text):
            return element
        for candidate in section_refs(index, ref):
            if candidate == ref:
                continue
            covered = resolve(index, candidate)
            if covered is not None and claimed in normalise_quote(covered.text):
                return covered
        return None

    def _deep_link(self, document_id: str, element: ResolvedElement) -> str:
        """A Studio URL that reopens the cited element in the viewer."""
        path = f"/docs/{document_id}?ref={urlquote(element.ref, safe='')}"
        if element.page is not None:
            path += f"&page={element.page}"
        base = self._config.studio_base_url.rstrip("/")
        return f"{base}{path}" if base else path

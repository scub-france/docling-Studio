"""Where an answer came from — the use case behind `show_sources` (#363).

Stateless: the agent hands back the anchors it read and cited, in its own
order, and this resolves them against the one parse they all pin, then
projects them onto that parse's map (`domain.source_map`). Nothing is stored,
so nothing has to be cleaned up, raced over, or kept in step with a re-parse.

Every anchor is one the server issued: a read returned it, or a citation
check settled on it. An anchor that does not parse, or names an element the
parse does not hold, is reported back as `unknown` rather than dropped — the
card must not quietly show less than the agent claimed to have used.

Each cited quote is checked again here, as `verify_citation` checks it, so
the card says "verified" on the server's word, never on the agent's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.anchors import AnchorParseError, DocumentAnchor
from domain.element_reader import resolve
from domain.source_map import SourceCited, SourceRead, build_source_map
from services.navigation_errors import InvalidArgumentError, NavigationServiceError

if TYPE_CHECKING:
    from domain.source_map import SourceMap
    from services.citation_service import CitationService
    from services.navigation_config import NavigationConfig
    from services.navigation_service import NavigationService
    from services.parse_loader import LoadedParse, ParseLoader

# The whole map: a source is wherever the agent read, however deep, and the
# card's tree folds what the reader does not open.
_MAP_DEPTH = 6


@dataclass(frozen=True)
class SourceReport:
    document_id: str
    version_id: str
    filename: str
    question: str
    sources: SourceMap
    # ref -> Studio URL opening the parse on it; empty without a base URL.
    deep_links: dict[str, str]
    unknown: list[str]
    # The loop's cap, so a reader sees the rounds against it (#363).
    max_rounds: int
    # The parse's pages, so a viewer can leaf through before any is fetched.
    page_count: int | None = None


class SourceService:
    def __init__(
        self,
        *,
        parses: ParseLoader,
        navigation: NavigationService,
        citations: CitationService,
        config: NavigationConfig,
    ) -> None:
        self._parses = parses
        self._navigation = navigation
        self._citations = citations
        self._config = config

    async def show(
        self,
        question: str,
        reads: list[tuple[str, str, str]],
        cited: list[tuple[str, str]],
    ) -> SourceReport:
        """Project `(uri, why, found)` rounds and `(uri, quote)` citations onto
        the parse they pin."""
        self._bound(question, reads, cited)
        unknown: list[str] = []
        read_anchors = [(a, w, f) for uri, w, f in reads if (a := _anchor(uri, unknown))]
        checked = [await self._check(uri, quote) for uri, quote in cited]
        cited_anchors = [(a, q, st) for uri, q, st in checked if (a := _anchor(uri, unknown))]
        anchors = [a for a, *_ in read_anchors] + [a for a, *_ in cited_anchors]
        document_id, version_id = _single_pin(anchors)

        parse = await self._parses.load(document_id, version_id)
        outline = await self._navigation.get_outline(
            document_id, version_id=version_id, depth=_MAP_DEPTH
        )
        known = _resolvable(parse, anchors, unknown)
        sources = build_source_map(
            outline,
            parse.index,
            [
                SourceRead(a.ref, a.uri, why.strip(), found.strip())
                for a, why, found in read_anchors
                if a.uri in known
            ],
            [
                SourceCited(a.ref, a.uri, quote, status)
                for a, quote, status in cited_anchors
                if a.uri in known
            ],
        )
        return SourceReport(
            document_id=document_id,
            version_id=version_id,
            filename=parse.document.filename,
            question=question.strip(),
            sources=sources,
            deep_links=self._deep_links(parse, sources),
            unknown=unknown,
            max_rounds=self._config.max_rounds,
            page_count=parse.index.page_count or None,
        )

    async def _check(self, uri: str, quote: str) -> tuple[str, str, str | None]:
        """The anchor to show for one citation, and the server's word on its quote.

        A quote that checks out may sit in a narrower element than the anchor
        named — a section anchor, a span — and the passage drawn is that
        element, the one the quote is in. No quote, or one refused before any
        matching (too short to prove anything, an anchor that does not
        parse): no status, so the card shows it as cited, not verified.
        """
        quote = (quote or "").strip()
        if not quote:
            return uri, "", None
        try:
            check = await self._citations.verify_citation(uri, quote)
        except (AnchorParseError, NavigationServiceError):
            return uri, quote, None
        narrowed = check.citation.uri if check.valid and check.citation else uri
        return narrowed, quote, check.status.value

    def _bound(
        self, question: str, reads: list[tuple[str, str, str]], cited: list[tuple[str, str]]
    ) -> None:
        """Refuse an input past its ceiling before any work is done."""
        cap = self._config.max_source_anchors
        if len(reads) + len(cited) > cap:
            raise InvalidArgumentError(
                f"{len(reads) + len(cited)} anchors; one answer shows at most {cap}."
            )
        limit = self._config.max_source_text_chars
        texts = [("question", question)]
        texts += [
            (label, text)
            for _, why, found in reads
            for label, text in (("why", why), ("found", found))
        ]
        texts += [("quote", quote) for _, quote in cited]
        for label, text in texts:
            if len(text or "") > limit:
                raise InvalidArgumentError(f"`{label}` is over {limit} characters. Shorten it.")

    def _deep_links(self, parse: LoadedParse, sources: SourceMap) -> dict[str, str]:
        refs = (
            {node.ref for node in sources.nodes}
            | {DocumentAnchor.parse(uri).ref for hop in sources.hops for uri in hop.cited}
            | {passage.ref for passage in sources.passages}
        )
        links: dict[str, str] = {}
        for ref in refs:
            element = resolve(parse.index, ref)
            link = self._citations.deep_link(parse.version_id, element) if element else None
            if link:
                links[ref] = link
        return links


def _anchor(uri: str, unknown: list[str]) -> DocumentAnchor | None:
    try:
        return DocumentAnchor.parse(uri)
    except AnchorParseError:
        unknown.append(uri)
        return None


def _single_pin(anchors: list[DocumentAnchor]) -> tuple[str, str]:
    """The one `(document_id, version_id)` every anchor names."""
    pins = {(anchor.document_id, anchor.version_id) for anchor in anchors}
    if not pins:
        raise InvalidArgumentError(
            "No usable anchor: pass the `uri` of each read_element result in `read`, "
            "and the verified anchors in `cited`, as the server returned them."
        )
    if len(pins) > 1:
        raise InvalidArgumentError(
            "These anchors point into more than one document or parse. Show the sources "
            "of one answer, about one document, at a time."
        )
    return pins.pop()


def _resolvable(parse: LoadedParse, anchors: list[DocumentAnchor], unknown: list[str]) -> set[str]:
    """The uris whose ref this parse holds; the others join `unknown`."""
    known: set[str] = set()
    for anchor in anchors:
        if anchor.uri in known:
            continue
        if resolve(parse.index, anchor.ref) is None:
            if anchor.uri not in unknown:
                unknown.append(anchor.uri)
        else:
            known.add(anchor.uri)
    return known

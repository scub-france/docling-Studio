"""Navigation service — map, read and verify a parsed document.

The use-case layer behind the MCP document server: it resolves a document and
the parse to read it from, delegates every docling-shaped operation to the
pure `domain.navigation_builder` projections, enforces the token budget, and
stamps anchors + citations onto what it returns.

It is transport-agnostic on purpose. `mcp_adapter` is its first consumer, the
HTTP layer can become its second (a `/api/documents/{id}/outline` route is the
same call), and the split is what keeps the MCP tools thin enough to review.

Errors mirror `ReasoningService`: typed exceptions carrying an `http_status`
hint, which the adapter maps to a tool error and a router would map to a
response code.
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from urllib.parse import quote as urlquote

from domain.navigation import (
    Citation,
    CitationCheck,
    CitationStatus,
    DocumentAnchor,
    DocumentOutline,
    DocumentSearch,
    DocumentSummary,
    Excerpt,
    OutlineNode,
    ResolvedElement,
    chars_for_tokens,
    estimate_tokens,
    is_heading,
    normalise_quote,
    quote_hash,
)
from domain.navigation_builder import (
    build_index,
    build_outline,
    parse_page_ref,
    render_markdown,
    resolve,
    section_refs,
)

if TYPE_CHECKING:
    from domain.models import AnalysisJob, Document
    from domain.navigation_builder import DocumentIndex
    from domain.ports import AnalysisRepository, DocumentRepository, DocumentTreeReader

logger = logging.getLogger(__name__)

READ_MODES = ("self", "section")


class NavigationServiceError(Exception):
    """Base error for navigation rejections, carrying an HTTP-status hint."""

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class DocumentNotFoundError(NavigationServiceError):
    http_status = 404


class NoParseError(NavigationServiceError):
    """The document exists but carries no completed analysis to read."""

    http_status = 409


class RefNotFoundError(NavigationServiceError):
    http_status = 404


class InvalidArgumentError(NavigationServiceError):
    http_status = 400


class NavigationUnavailableError(NavigationServiceError):
    """Raised when the service is not wired yet — the app is still booting.

    Lives here rather than in the composition root so the adapter can catch it
    with the rest of the service's errors instead of special-casing a builtin
    exception type, which would swallow genuine internal failures.
    """

    http_status = 503


@dataclass(frozen=True)
class NavigationConfig:
    """Budgets and link generation — every value is a server-side ceiling.

    A client argument may lower them, never raise them: an agent must not be
    able to ask for a 40 000-token response by passing `max_tokens=40000`.
    """

    studio_base_url: str = ""
    default_read_tokens: int = 1200
    max_read_tokens: int = 4000
    max_outline_nodes: int = 200
    max_documents: int = 50
    # How many parsed documents to keep indexed in memory. A parse is
    # immutable for a given analysis id, so the cache can never go stale;
    # it is bounded because `document_json` runs to megabytes.
    index_cache_size: int = 4


class NavigationService:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        tree_reader: DocumentTreeReader,
        config: NavigationConfig | None = None,
    ) -> None:
        self._documents = document_repo
        self._analyses = analysis_repo
        self._tree = tree_reader
        self._config = config or NavigationConfig()
        self._index_cache: OrderedDict[str, DocumentIndex] = OrderedDict()

    @property
    def config(self) -> NavigationConfig:
        return self._config

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    async def find_documents(
        self,
        *,
        query: str | None = None,
        limit: int = 20,
    ) -> DocumentSearch:
        """List documents, optionally filtered by a filename substring.

        The filter runs service-side over the most recent `max_documents`
        rows: the repository has no search predicate today, and adding one is
        a persistence change this lot deliberately does not make. The window
        is reported back (`scanned`, `scan_limit`, `truncated`) rather than
        left implicit — otherwise an empty result reads as "no such document"
        when it means "not among the newest 50".
        """
        limit = max(1, min(limit, self._config.max_documents))
        scan_limit = self._config.max_documents
        docs = await self._documents.find_all(limit=scan_limit)
        scanned = len(docs)

        needle = (query or "").strip().lower()
        if needle:
            docs = [doc for doc in docs if needle in (doc.filename or "").lower()]

        summaries: list[DocumentSummary] = []
        for doc in docs[:limit]:
            job = await self._analyses.find_latest_completed_by_document(doc.id)
            summaries.append(
                DocumentSummary(
                    document_id=doc.id,
                    filename=doc.filename,
                    lifecycle_state=str(doc.lifecycle_state),
                    page_count=doc.page_count,
                    version_id=job.id if job and job.document_json else None,
                    created_at=doc.created_at.isoformat() if doc.created_at else None,
                )
            )
        return DocumentSearch(
            documents=summaries,
            scanned=scanned,
            scan_limit=scan_limit,
            truncated=scanned >= scan_limit,
        )

    async def get_outline(
        self,
        document_id: str,
        *,
        version_id: str | None = None,
        depth: int = 2,
    ) -> DocumentOutline:
        """Return the document map — sections when there are headings, pages otherwise."""
        depth = max(1, min(depth, 6))
        doc, job, index = await self._load(document_id, version_id)
        draft = build_outline(index, depth=depth, max_nodes=self._config.max_outline_nodes)
        return DocumentOutline(
            document_id=doc.id,
            version_id=job.id,
            filename=doc.filename,
            page_count=doc.page_count or index.page_count or None,
            total_est_tokens=draft.total_est_tokens,
            mode=draft.mode,
            nodes=[self._stamp(node, doc.id, job.id) for node in draft.nodes],
            depth_limited=draft.depth_limited,
            node_limited=draft.node_limited,
        )

    async def read_element(
        self,
        document_id: str,
        ref: str,
        *,
        version_id: str | None = None,
        include: str = "section",
        max_tokens: int | None = None,
        cursor: str | None = None,
    ) -> Excerpt:
        """Read one element — or the whole section it opens — under a budget."""
        if include not in READ_MODES:
            raise InvalidArgumentError(f"include must be one of {READ_MODES}, got {include!r}")

        doc, job, index = await self._load(document_id, version_id)
        target = resolve(index, ref)
        if target is None:
            raise RefNotFoundError(
                f"Ref {ref!r} does not exist in version {job.id} of document {document_id}. "
                "Call get_outline to obtain valid refs."
            )

        # A page ref carries no text of its own, so `self` would read nothing
        # at all — for it, both modes mean "everything on this page".
        read_whole = include == "section" or parse_page_ref(ref) is not None
        # `section_refs` is empty for a ref that resolves but sits outside
        # reading order — a caption, or text pruned from inside a picture.
        # Those refs carry text and `include="self"` returns it, so the
        # default mode must not answer "this element is empty" for them.
        refs = (section_refs(index, ref) or [ref]) if read_whole else [ref]
        if cursor:
            if cursor not in refs:
                raise InvalidArgumentError(
                    f"Cursor {cursor!r} does not belong to this section — pass back the "
                    "`next_cursor` returned by the previous read, unchanged."
                )
            refs = refs[refs.index(cursor) :]

        budget = self._budget(max_tokens)
        picked: list[ResolvedElement] = []
        spent = 0
        truncated = False
        next_cursor: str | None = None

        for index_position, candidate in enumerate(refs):
            element = resolve(index, candidate)
            if element is None or not element.text.strip():
                continue
            cost = element.est_tokens
            if picked and spent + cost > budget:
                truncated = True
                next_cursor = candidate
                break
            if not picked and cost > budget:
                # One element larger than the whole budget. Returning it
                # whole would break the ceiling the config promises, and
                # skipping it would return nothing, so it is clipped at a
                # word boundary and flagged. The citation quotes the clipped
                # text, which still verifies (verification is a substring
                # match), and the operator's lever is MCP_MAX_READ_TOKENS.
                element = replace(element, text=_clip(element.text, budget))
                picked.append(element)
                spent += element.est_tokens
                truncated = True
                next_cursor = refs[index_position + 1] if index_position + 1 < len(refs) else None
                break
            picked.append(element)
            spent += cost

        pages = [element.page for element in picked if element.page is not None]
        return Excerpt(
            document_id=doc.id,
            version_id=job.id,
            ref=ref,
            uri=DocumentAnchor(doc.id, job.id, ref).uri,
            title=self._excerpt_title(target, doc),
            markdown=render_markdown(picked),
            citations=[self._citation(doc.id, job.id, element) for element in picked],
            est_tokens=spent,
            truncated=truncated,
            next_cursor=next_cursor,
            page_range=(min(pages), max(pages)) if pages else None,
        )

    async def verify_citation(self, uri: str, quote: str) -> CitationCheck:
        """Re-resolve an anchor server-side and check the claimed quote.

        Three deliberate tolerances, each covering a way an honest agent
        quotes:

        - **Partial quotes verify.** Quoting one sentence out of a paragraph
          is citing correctly, so the comparison is a normalised substring
          match rather than equality.
        - **A section anchor covers its section.** `read_element` defaults to
          reading a whole section, so the uri an agent holds is often the
          section's, not the paragraph's. The quote is looked for in the
          elements the anchor covers, and the returned citation points at the
          element that actually carries it — the agent gets the precise
          anchor back rather than a false negative.
        - **Whitespace is not drift.** Reflowing is what models do to text.

        What it catches is the two failures that matter: a ref that does not
        exist, and a quote that is nowhere in what the ref covers.
        """
        anchor = DocumentAnchor.parse(uri)
        try:
            doc, job, index = await self._load(anchor.document_id, anchor.version_id)
        except NavigationServiceError as exc:
            return CitationCheck(
                valid=False, status=CitationStatus.UNKNOWN_VERSION, detail=str(exc)
            )

        element = resolve(index, anchor.ref)
        if element is None:
            return CitationCheck(
                valid=False,
                status=CitationStatus.UNKNOWN_REF,
                detail=f"Ref {anchor.ref!r} does not exist in version {job.id}.",
            )

        citation = self._citation(doc.id, job.id, element)
        claimed = normalise_quote(quote)
        if not claimed:
            return CitationCheck(
                valid=False,
                status=CitationStatus.QUOTE_DRIFT,
                detail="No quote supplied to verify.",
                citation=citation,
                actual_quote=element.text,
            )

        match = self._locate_quote(index, anchor.ref, element, claimed)
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

        matched = self._citation(doc.id, job.id, match)
        latest = await self._analyses.find_latest_completed_by_document(doc.id)
        if latest and latest.id != job.id:
            return CitationCheck(
                valid=True,
                status=CitationStatus.STALE_VERSION,
                detail=(
                    "The quote appears verbatim at this anchor, but the anchor pins an "
                    f"earlier parse: {latest.id} is now the current one. Re-read the "
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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _load(
        self,
        document_id: str,
        version_id: str | None,
    ) -> tuple[Document, AnalysisJob, DocumentIndex]:
        doc = await self._documents.find_by_id(document_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

        if version_id:
            job = await self._analyses.find_by_id(version_id)
            if job is None or job.document_id != document_id:
                raise NoParseError(
                    f"Version {version_id} does not belong to document {document_id}.",
                    http_status=404,
                )
        else:
            job = await self._analyses.find_latest_completed_by_document(document_id)

        if job is None or not job.document_json:
            raise NoParseError(
                f"Document {document_id} has no parsed content to navigate yet. "
                "Run an analysis in Docling Studio first."
            )

        return doc, job, self._index_for(job)

    def _index_for(self, job: AnalysisJob) -> DocumentIndex:
        cached = self._index_cache.get(job.id)
        if cached is not None:
            self._index_cache.move_to_end(job.id)
            return cached
        try:
            doc_data = json.loads(job.document_json or "{}")
        except json.JSONDecodeError as exc:
            logger.exception("Invalid document_json for analysis %s", job.id)
            raise NoParseError(
                f"The stored parse for version {job.id} is unreadable.", http_status=500
            ) from exc

        index = build_index(doc_data, self._tree)
        self._index_cache[job.id] = index
        while len(self._index_cache) > self._config.index_cache_size:
            self._index_cache.popitem(last=False)
        return index

    def _budget(self, max_tokens: int | None) -> int:
        requested = max_tokens or self._config.default_read_tokens
        return max(1, min(requested, self._config.max_read_tokens))

    def _stamp(self, node: OutlineNode, document_id: str, version_id: str) -> OutlineNode:
        """Attach the anchor URI to an outline node and its subtree."""
        return replace(
            node,
            uri=DocumentAnchor(document_id, version_id, node.ref).uri,
            children=[self._stamp(child, document_id, version_id) for child in node.children],
        )

    def _citation(self, document_id: str, version_id: str, element: ResolvedElement) -> Citation:
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

    def _deep_link(self, document_id: str, element: ResolvedElement) -> str:
        """A Studio URL that reopens the cited element in the viewer."""
        path = f"/docs/{document_id}?ref={urlquote(element.ref, safe='')}"
        if element.page is not None:
            path += f"&page={element.page}"
        base = self._config.studio_base_url.rstrip("/")
        return f"{base}{path}" if base else path

    @staticmethod
    def _excerpt_title(target: ResolvedElement, doc: Document) -> str:
        if is_heading(target.label) and target.text.strip():
            return " ".join(target.text.split())[:96]
        if target.label == "page" and target.page is not None:
            return f"Page {target.page}"
        if target.headings:
            return target.headings[-1]
        return doc.filename or target.ref


CLIP_MARKER = " […clipped]"


def _clip(text: str, budget: int) -> str:
    """Cut `text` to `budget` tokens at a word boundary, marking the cut.

    The marker is part of the returned text on purpose — an agent that quotes
    a clipped element must be able to see it is holding a prefix — and it is
    charged to the budget, so the promised ceiling still holds for the whole
    string rather than for the string minus its own footnote.
    """
    limit = chars_for_tokens(max(1, budget - estimate_tokens(CLIP_MARKER)))
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = head.rsplit(" ", 1)[0] if " " in head else head
    return f"{cut.rstrip()}{CLIP_MARKER}"

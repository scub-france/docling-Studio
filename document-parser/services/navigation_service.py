"""Navigating a parsed document: find it, map it, read part of it.

The reading half of the document-agent surface. Resolution and caching belong
to `ParseLoader`, citations to `CitationService`, rasters to
`CitationImageService`; what is left here is the three questions an agent asks
in order — which document, what is in it, and what does this part say — and
the budget that keeps the third one affordable. The budget's rules are pure
and live in `domain.read_budget`; this service applies the configured ceilings.

Transport-agnostic on purpose: `mcp_adapter` is its first consumer, and an
HTTP route would be the same call.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from domain.anchors import DocumentAnchor
from domain.element_reader import render_markdown, resolve
from domain.navigation import (
    DocumentOutline,
    DocumentSearch,
    DocumentSummary,
    Excerpt,
    OutlineNode,
    is_heading,
)
from domain.outline_builder import build_outline
from domain.read_budget import (
    READ_MODES,
    InvalidCursorError,
    pick_within_budget,
    read_span_ref,
    refs_to_read,
)
from services.navigation_config import NavigationConfig
from services.navigation_errors import InvalidArgumentError, RefNotFoundError

if TYPE_CHECKING:
    from domain.models import Document
    from domain.navigation import ResolvedElement
    from services.citation_service import CitationService
    from services.parse_loader import LoadedParse, ParseLoader

logger = logging.getLogger(__name__)


class NavigationService:
    def __init__(
        self,
        *,
        parses: ParseLoader,
        citations: CitationService,
        config: NavigationConfig | None = None,
    ) -> None:
        self._parses = parses
        self._citations = citations
        self._config = config or NavigationConfig()

    @property
    def config(self) -> NavigationConfig:
        return self._config

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------

    async def find_documents(
        self,
        *,
        query: str | None = None,
        limit: int = 20,
    ) -> DocumentSearch:
        """List documents, newest first, optionally filtered by a filename substring.

        Two queries whatever the count: the documents, then the latest parse
        id of each — never a whole analysis row.
        """
        limit = max(1, min(limit, self._config.max_documents))
        docs = await self._parses.documents.find_all(
            limit=limit + 1, filename_like=(query or "").strip() or None
        )
        truncated = len(docs) > limit
        docs = docs[:limit]
        latest = await self._parses.analyses.latest_parsed_ids([doc.id for doc in docs])
        summaries = [
            DocumentSummary(
                document_id=doc.id,
                filename=doc.filename,
                lifecycle_state=str(doc.lifecycle_state),
                page_count=doc.page_count,
                version_id=latest.get(doc.id),
                created_at=doc.created_at.isoformat() if doc.created_at else None,
            )
            for doc in docs
        ]
        return DocumentSearch(documents=summaries, truncated=truncated)

    async def get_outline(
        self,
        document_id: str,
        *,
        version_id: str | None = None,
        depth: int = 2,
    ) -> DocumentOutline:
        """Return the document map — sections when there are headings, pages otherwise."""
        parse = await self._parses.load(document_id, version_id)
        return self.outline_of(parse, depth=depth)

    def outline_of(self, parse: LoadedParse, *, depth: int = 2) -> DocumentOutline:
        """The map of a parse the caller has already loaded (`show_sources`)."""
        depth = max(1, min(depth, 6))
        draft = build_outline(parse.index, depth=depth, max_nodes=self._config.max_outline_nodes)
        return DocumentOutline(
            document_id=parse.document.id,
            version_id=parse.version_id,
            filename=parse.document.filename,
            page_count=parse.document.page_count or parse.index.page_count or None,
            total_est_tokens=draft.total_est_tokens,
            mode=draft.mode,
            nodes=[self._stamp(node, parse.document.id, parse.version_id) for node in draft.nodes],
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

        parse = await self._parses.load(document_id, version_id)
        target = resolve(parse.index, ref)
        if target is None:
            raise RefNotFoundError(
                f"Ref {ref!r} does not exist in version {parse.version_id} of document "
                f"{document_id}. Call get_outline to obtain valid refs."
            )

        try:
            refs, start = refs_to_read(parse.index, ref, include=include, cursor=cursor)
        except InvalidCursorError as exc:
            raise InvalidArgumentError(str(exc)) from exc
        read = pick_within_budget(parse.index, refs, self._budget(max_tokens), start)
        picked = read.elements

        span = read_span_ref(parse.index, refs, picked)
        span_uri = DocumentAnchor(parse.document.id, parse.version_id, span).uri if span else None
        pages = [element.page for element in picked if element.page is not None]
        return Excerpt(
            document_id=parse.document.id,
            version_id=parse.version_id,
            ref=ref,
            uri=DocumentAnchor(parse.document.id, parse.version_id, ref).uri,
            title=self._excerpt_title(target, parse.document),
            markdown=render_markdown(picked),
            citations=[
                self._citations.build(parse.document.id, parse.version_id, element)
                for element in picked
            ],
            est_tokens=read.spent,
            truncated=read.truncated,
            next_cursor=read.next_cursor,
            page_range=(min(pages), max(pages)) if pages else None,
            span_uri=span_uri,
        )

    # ------------------------------------------------------------------
    # Reading internals
    # ------------------------------------------------------------------

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

    @staticmethod
    def _excerpt_title(target: ResolvedElement, doc: Document) -> str:
        if is_heading(target.label) and target.text.strip():
            return " ".join(target.text.split())[:96]
        if target.label == "page" and target.page is not None:
            return f"Page {target.page}"
        if target.headings:
            return target.headings[-1]
        return doc.filename or target.ref

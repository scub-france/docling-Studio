"""Navigating a parsed document: find it, map it, read part of it.

The reading half of the document-agent surface. Resolution and caching belong
to `ParseLoader`, citations to `CitationService`, rasters to
`CitationImageService`; what is left here is the three questions an agent asks
in order — which document, what is in it, and what does this part say — and
the budget that keeps the third one affordable.

Transport-agnostic on purpose: `mcp_adapter` is its first consumer, and an
HTTP route would be the same call.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from domain.anchors import DocumentAnchor
from domain.element_reader import render_markdown, resolve, section_refs
from domain.navigation import (
    DocumentOutline,
    DocumentSearch,
    DocumentSummary,
    Excerpt,
    OutlineNode,
    clip_to_tokens,
    is_heading,
)
from domain.outline_builder import build_outline
from domain.parse_index import parse_page_ref
from services.navigation_config import NavigationConfig
from services.navigation_errors import InvalidArgumentError, RefNotFoundError

if TYPE_CHECKING:
    from domain.models import Document
    from domain.navigation import ResolvedElement
    from services.citation_service import CitationService
    from services.parse_loader import LoadedParse, ParseLoader

logger = logging.getLogger(__name__)

READ_MODES = ("self", "section")


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
        docs = await self._parses.documents.find_all(limit=scan_limit)
        scanned = len(docs)

        needle = (query or "").strip().lower()
        if needle:
            docs = [doc for doc in docs if needle in (doc.filename or "").lower()]

        summaries: list[DocumentSummary] = []
        for doc in docs[:limit]:
            job = await self._parses.analyses.find_latest_completed_by_document(doc.id)
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
        parse = await self._parses.load(document_id, version_id)
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

        refs = self._refs_to_read(parse, ref, include=include, cursor=cursor)
        picked, spent, truncated, next_cursor = self._pick(parse, refs, self._budget(max_tokens))

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
            est_tokens=spent,
            truncated=truncated,
            next_cursor=next_cursor,
            page_range=(min(pages), max(pages)) if pages else None,
        )

    # ------------------------------------------------------------------
    # Reading internals
    # ------------------------------------------------------------------

    def _refs_to_read(
        self,
        parse: LoadedParse,
        ref: str,
        *,
        include: str,
        cursor: str | None,
    ) -> list[str]:
        # A page ref carries no text of its own, so `self` would read nothing
        # at all — for it, both modes mean "everything on this page".
        read_whole = include == "section" or parse_page_ref(ref) is not None
        # `section_refs` is empty for a ref that resolves but sits outside
        # reading order — a caption, or text pruned from inside a picture.
        # Those refs carry text and `include="self"` returns it, so the
        # default mode must not answer "this element is empty" for them.
        refs = (section_refs(parse.index, ref) or [ref]) if read_whole else [ref]
        if not cursor:
            return refs
        if cursor not in refs:
            raise InvalidArgumentError(
                f"Cursor {cursor!r} does not belong to this section — pass back the "
                "`next_cursor` returned by the previous read, unchanged."
            )
        return refs[refs.index(cursor) :]

    def _pick(
        self,
        parse: LoadedParse,
        refs: list[str],
        budget: int,
    ) -> tuple[list[ResolvedElement], int, bool, str | None]:
        """Take elements in reading order until the budget is spent."""
        picked: list[ResolvedElement] = []
        spent = 0

        for position, candidate in enumerate(refs):
            element = resolve(parse.index, candidate)
            if element is None or not element.text.strip():
                continue
            cost = element.est_tokens
            if picked and spent + cost > budget:
                return picked, spent, True, candidate
            if not picked and cost > budget:
                # One element larger than the whole budget. Returning it
                # whole would break the ceiling the config promises, and
                # skipping it would return nothing, so it is clipped at a
                # word boundary and flagged. The citation quotes the clipped
                # text, which still verifies (verification is a substring
                # match), and the operator's lever is MCP_MAX_READ_TOKENS.
                clipped = replace(element, text=clip_to_tokens(element.text, budget))
                following = refs[position + 1] if position + 1 < len(refs) else None
                return [clipped], clipped.est_tokens, True, following
            picked.append(element)
            spent += cost

        return picked, spent, False, None

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

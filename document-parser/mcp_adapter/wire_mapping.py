"""Domain results, in the shapes the wire publishes.

Kept apart from the dataclasses they build: `wire.py` is the contract a
connected agent reads, this is the translation, and mixing the two made a
single 370-line module where a rename and a mapping change looked the same in
a diff.

Every document-derived string passes through `neutralise` on the way out —
titles and quotes included, not just excerpt bodies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.navigation import CitationStatus
from mcp_adapter.wire import (
    CitationOut,
    CitationRef,
    DocumentRow,
    DocumentSearchResult,
    ExcerptResult,
    OutlineEntry,
    OutlineResult,
    VerificationResult,
    neutralise,
    wrap_content,
)

if TYPE_CHECKING:
    from domain.navigation import (
        Citation,
        CitationCheck,
        DocumentOutline,
        DocumentSearch,
        DocumentSummary,
        Excerpt,
        OutlineNode,
    )


def _neutralise_all(values: list[str]) -> list[str]:
    return [neutralise(value) for value in values]


def document_row(summary: DocumentSummary) -> DocumentRow:
    return DocumentRow(
        document_id=summary.document_id,
        filename=neutralise(summary.filename),
        state=summary.lifecycle_state,
        pages=summary.page_count,
        version_id=summary.version_id,
        created_at=summary.created_at,
    )


def search_result(search: DocumentSearch) -> DocumentSearchResult:
    unparsed = [row for row in search.documents if row.version_id is None]
    hint = "get_outline(document_id) on the document you need."
    if search.truncated:
        hint += " More matched: narrow the query."
    if unparsed:
        hint += " Rows with a null version_id cannot be read yet."
    return DocumentSearchResult(
        documents=[document_row(summary) for summary in search.documents],
        truncated=search.truncated,
        next_step=hint,
    )


def outline_entry(node: OutlineNode) -> OutlineEntry:
    return OutlineEntry(
        ref=node.ref,
        title=neutralise(node.title),
        kind=node.kind,
        level=node.level,
        est_tokens=node.est_tokens,
        child_count=node.child_count,
        page=node.page,
        children=[outline_entry(child) for child in node.children],
    )


def outline_result(outline: DocumentOutline) -> OutlineResult:
    return OutlineResult(
        document_id=outline.document_id,
        version_id=outline.version_id,
        filename=neutralise(outline.filename),
        mode=outline.mode,
        total_est_tokens=outline.total_est_tokens,
        deeper_levels_available=outline.depth_limited,
        entries_omitted=outline.node_limited,
        entries=[outline_entry(node) for node in outline.nodes],
        pages=outline.page_count,
        next_step=(
            "read_element(document_id, ref) on the entries that answer; the whole document "
            f"is ~{outline.total_est_tokens} tokens."
        ),
    )


# Enough words to tell one passage from another without re-sending it.
PREVIEW_WORDS = 8


def citation_ref(citation: Citation) -> CitationRef:
    """The pointer form: anchor, page, and a few words to recognise it by."""
    words = neutralise(citation.quote).split()
    preview = " ".join(words[:PREVIEW_WORDS])
    if len(words) > PREVIEW_WORDS:
        preview += " …"
    return CitationRef(
        uri=citation.uri,
        ref=citation.ref,
        preview=preview,
        page=citation.page,
    )


def citation_out(citation: Citation) -> CitationOut:
    bbox = citation.bbox
    return CitationOut(
        uri=citation.uri,
        ref=citation.ref,
        label=citation.label,
        quote=neutralise(citation.quote),
        quote_hash=citation.quote_hash,
        headings=_neutralise_all(list(citation.headings)),
        page=citation.page,
        bbox=[bbox.left, bbox.top, bbox.right, bbox.bottom] if bbox else None,
        coord_origin=bbox.coord_origin if bbox else None,
        page_width=bbox.page_width if bbox else None,
        page_height=bbox.page_height if bbox else None,
        deep_link=citation.deep_link,
    )


# What to do next, delivered with the result: a rule attached to the payload
# arrives at the moment it applies.
_CITE_WITH = (
    "Quote with the `citations[].uri` of the element you quote, and verify_citation "
    "before publishing."
)
_CITE_SPAN = " A quote across several elements cites `span_uri`."

_VERIFICATION_NEXT_STEP = {
    CitationStatus.VERIFIED: "Safe to publish, citing citation.uri.",
    CitationStatus.STALE_VERSION: (
        "Publishable, but the anchor pins a superseded parse: re-read to cite the current one."
    ),
    CitationStatus.QUOTE_DRIFT: (
        "Do not publish this quote: use `actual_quote` verbatim, or re-read and quote what "
        "is there."
    ),
    CitationStatus.UNKNOWN_REF: "No such ref in this parse: cite a uri a read returned.",
    CitationStatus.UNKNOWN_VERSION: (
        "That parse no longer exists: read the document again and cite the new uri."
    ),
}


def _excerpt_next_step(excerpt: Excerpt) -> str:
    if excerpt.truncated and excerpt.next_cursor:
        return (
            "Cut at the budget: call read_element again with the same ref and "
            f"cursor='{excerpt.next_cursor}'. {_CITE_WITH}"
        )
    if not excerpt.citations:
        return "Nothing readable at this anchor. Pick another entry from get_outline."
    return _CITE_WITH + (_CITE_SPAN if excerpt.span_uri else "")


def excerpt_result(excerpt: Excerpt) -> ExcerptResult:
    return ExcerptResult(
        uri=excerpt.uri,
        document_id=excerpt.document_id,
        version_id=excerpt.version_id,
        title=neutralise(excerpt.title),
        content=wrap_content(
            excerpt.markdown,
            document_id=excerpt.document_id,
            version_id=excerpt.version_id,
            ref=excerpt.ref,
        ),
        est_tokens=excerpt.est_tokens,
        truncated=excerpt.truncated,
        citations=[citation_ref(citation) for citation in excerpt.citations],
        next_step=_excerpt_next_step(excerpt),
        next_cursor=excerpt.next_cursor,
        first_page=excerpt.page_range[0] if excerpt.page_range else None,
        last_page=excerpt.page_range[1] if excerpt.page_range else None,
        span_uri=excerpt.span_uri,
    )


def verification_result(check: CitationCheck) -> VerificationResult:
    return VerificationResult(
        valid=check.valid,
        status=check.status,
        detail=check.detail,
        next_step=_VERIFICATION_NEXT_STEP.get(check.status, ""),
        actual_quote=neutralise(check.actual_quote) if check.actual_quote else None,
        citation=citation_out(check.citation) if check.citation else None,
    )

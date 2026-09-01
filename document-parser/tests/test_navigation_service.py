"""Tests for NavigationService — resolution, budget, citations, verification.

Repositories are `AsyncMock`s holding real domain objects, matching the
convention of `tests/test_document_service.py`. The docling payload comes
from `tests.navigation_fixtures`, so refs and quotes asserted here are the
same ones the domain tests assert.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from domain.navigation import CitationStatus
from services.navigation_config import NavigationConfig
from services.navigation_errors import (
    DocumentNotFoundError,
    InvalidArgumentError,
    NoParseError,
    RefNotFoundError,
)
from tests.navigation_fixtures import (
    DOC_ID,
    FLAT,
    JOB_ID,
    MESSY,
    PREAVIS_REF,
    PREAVIS_TEXT,
    SECTIONED,
)
from tests.navigation_fixtures import (
    FakeRasterizer as _FakeRasterizer,
)
from tests.navigation_fixtures import (
    anchor_uri as _uri,
)
from tests.navigation_fixtures import (
    make_document as _document,
)
from tests.navigation_fixtures import (
    make_document_tools as _tools,
)
from tests.navigation_fixtures import (
    make_job as _job,
)
from tests.navigation_fixtures import (
    make_navigation_service as _service,
)


class TestFindDocuments:
    async def test_returns_the_version_token_of_the_latest_parse(self):
        search = await _service().find_documents()
        assert [row.document_id for row in search.documents] == [DOC_ID]
        assert search.documents[0].version_id == JOB_ID
        assert search.documents[0].filename == "contrat.pdf"

    async def test_reports_no_version_when_nothing_is_parsed(self):
        search = await _service(job=None).find_documents()
        assert search.documents[0].version_id is None

    async def test_filters_on_the_filename(self):
        docs = [_document(), _document("doc-2", "facture.pdf")]
        search = await _service(documents=docs).find_documents(query="fact")
        assert [row.filename for row in search.documents] == ["facture.pdf"]

    async def test_limit_is_capped_server_side(self):
        docs = [_document(f"doc-{i}", f"f{i}.pdf") for i in range(10)]
        service = _service(documents=docs, config=NavigationConfig(max_documents=3))
        search = await service.find_documents(limit=99)
        assert len(search.documents) == 3

    async def test_reports_the_search_window_so_empty_is_not_ambiguous(self):
        # A filled window means "there may be older documents I did not look
        # at" — an empty result then is not proof the document is absent.
        docs = [_document(f"doc-{i}", f"f{i}.pdf") for i in range(3)]
        service = _service(documents=docs, config=NavigationConfig(max_documents=3))
        search = await service.find_documents(query="nothing-matches")
        assert search.documents == []
        assert (search.scanned, search.scan_limit, search.truncated) == (3, 3, True)

    async def test_a_partial_window_is_not_flagged_as_truncated(self):
        search = await _service().find_documents()
        assert search.truncated is False


class TestGetOutline:
    async def test_stamps_an_anchor_on_every_node(self):
        outline = await _service().get_outline(DOC_ID)
        root = outline.nodes[0]
        assert root.uri == _uri(root.ref)
        assert root.children[0].uri.startswith("dstudio://doc/doc-1@an-1#")
        assert outline.version_id == JOB_ID
        assert outline.mode == "sections"

    async def test_page_mode_for_a_document_without_headings(self):
        outline = await _service(job=_job(FLAT)).get_outline(DOC_ID)
        assert outline.mode == "pages"
        assert outline.nodes[0].ref == "#/pages/1"

    async def test_unknown_document(self):
        with pytest.raises(DocumentNotFoundError):
            await _service().get_outline("nope")

    async def test_document_without_a_parse(self):
        with pytest.raises(NoParseError, match="no parsed content"):
            await _service(job=None).get_outline(DOC_ID)

    async def test_version_belonging_to_another_document_is_refused(self):
        with pytest.raises(NoParseError, match="does not belong"):
            await _service().get_outline(DOC_ID, version_id="other-analysis")

    async def test_parse_is_indexed_once_and_reused(self):
        service = _service()
        await service.get_outline(DOC_ID)
        first = service._parses._cache[JOB_ID]
        await service.get_outline(DOC_ID)
        assert service._parses._cache[JOB_ID] is first


class TestReadElement:
    async def test_reads_a_section_with_one_citation_per_element(self):
        excerpt = await _service().read_element(DOC_ID, "#/texts/3")
        assert excerpt.title == "12.2 Préavis"
        assert PREAVIS_TEXT in excerpt.markdown
        # The section runs to the next heading of the same or a higher level,
        # so the table and the figure that follow the paragraph belong to it.
        assert [c.ref for c in excerpt.citations] == [
            "#/texts/3",
            PREAVIS_REF,
            "#/tables/0",
            "#/pictures/0",
        ]
        assert excerpt.truncated is False
        assert excerpt.page_range == (1, 2)

    async def test_self_mode_reads_only_that_element(self):
        excerpt = await _service().read_element(DOC_ID, "#/texts/3", include="self")
        assert excerpt.markdown == "### 12.2 Préavis"
        assert len(excerpt.citations) == 1

    async def test_citation_carries_verbatim_page_bbox_and_deep_link(self):
        excerpt = await _service().read_element(DOC_ID, PREAVIS_REF, include="self")
        citation = excerpt.citations[0]
        assert citation.quote == PREAVIS_TEXT
        assert citation.quote_hash.startswith("sha256:")
        assert citation.page == 1
        assert citation.bbox is not None and citation.bbox.page == 1
        assert citation.headings[-1] == "12.2 Préavis"
        assert citation.deep_link == ("http://localhost:3000/docs/doc-1?ref=%23%2Ftexts%2F4&page=1")

    async def test_budget_truncates_at_an_element_boundary_and_resumes(self):
        service = _service()
        first = await service.read_element(DOC_ID, "#/texts/0", max_tokens=12)
        assert first.truncated is True
        assert first.next_cursor is not None
        # No half element: the cursor is the first ref that did not fit.
        assert first.next_cursor not in [c.ref for c in first.citations]

        second = await service.read_element(
            DOC_ID, "#/texts/0", cursor=first.next_cursor, max_tokens=200
        )
        assert second.citations[0].ref == first.next_cursor

    async def test_always_returns_at_least_one_element(self):
        excerpt = await _service().read_element(DOC_ID, PREAVIS_REF, max_tokens=1)
        assert len(excerpt.citations) == 1
        assert excerpt.markdown

    async def test_client_cannot_raise_the_server_ceiling(self):
        service = _service(config=NavigationConfig(max_read_tokens=5))
        excerpt = await service.read_element(DOC_ID, "#/texts/0", max_tokens=10_000)
        assert excerpt.truncated is True

    async def test_self_mode_on_a_page_still_reads_the_page(self):
        # A page ref has no text of its own; "self" must not return nothing.
        excerpt = await _service(job=_job(FLAT)).read_element(DOC_ID, "#/pages/1", include="self")
        assert "Première ligne" in excerpt.markdown

    async def test_reading_a_page_ref(self):
        excerpt = await _service(job=_job(FLAT)).read_element(DOC_ID, "#/pages/2")
        assert excerpt.title == "Page 2"
        assert "page deux" in excerpt.markdown

    async def test_unknown_ref(self):
        with pytest.raises(RefNotFoundError, match="get_outline"):
            await _service().read_element(DOC_ID, "#/texts/999")

    async def test_unknown_include_mode(self):
        with pytest.raises(InvalidArgumentError):
            await _service().read_element(DOC_ID, "#/texts/0", include="everything")

    async def test_foreign_cursor_is_refused(self):
        with pytest.raises(InvalidArgumentError, match="does not belong"):
            await _service().read_element(DOC_ID, "#/texts/3", cursor="#/texts/7")


class TestVerifyCitation:
    async def test_verifies_a_full_quote(self):
        check = await _tools().citations.verify_citation(_uri(PREAVIS_REF), PREAVIS_TEXT)
        assert check.valid is True
        assert check.status is CitationStatus.VERIFIED
        assert check.citation is not None

    async def test_verifies_a_partial_quote(self):
        check = await _tools().citations.verify_citation(_uri(PREAVIS_REF), "trois mois")
        assert check.valid is True

    async def test_tolerates_reflowed_whitespace(self):
        check = await _tools().citations.verify_citation(
            _uri(PREAVIS_REF), "Le  préavis\nest de trois mois"
        )
        assert check.valid is True

    async def test_catches_a_fabricated_quote(self):
        check = await _tools().citations.verify_citation(
            _uri(PREAVIS_REF), "Le préavis est de six mois"
        )
        assert check.valid is False
        assert check.status is CitationStatus.QUOTE_DRIFT
        assert check.actual_quote == PREAVIS_TEXT

    async def test_catches_an_unknown_ref(self):
        check = await _tools().citations.verify_citation(_uri("#/texts/999"), "anything")
        assert (check.valid, check.status) == (False, CitationStatus.UNKNOWN_REF)

    async def test_catches_an_unknown_version(self):
        check = await _tools().citations.verify_citation(
            _uri(PREAVIS_REF, job_id="ghost"), PREAVIS_TEXT
        )
        assert (check.valid, check.status) == (False, CitationStatus.UNKNOWN_VERSION)

    async def test_empty_quote_is_not_a_verification(self):
        check = await _tools().citations.verify_citation(_uri(PREAVIS_REF), "   ")
        assert check.valid is False

    async def test_flags_an_anchor_pinned_to_a_superseded_parse(self):
        tools = _tools()
        tools.citations._parses.analyses.find_latest_completed_by_document = AsyncMock(
            return_value=_job(job_id="an-2")
        )
        check = await tools.citations.verify_citation(_uri(PREAVIS_REF), "trois mois")
        # Still valid — the quote is there — but the anchor is not the current
        # parse, and that is a distinct status, not a note buried in prose.
        assert check.valid is True
        assert check.status is CitationStatus.STALE_VERSION
        assert "an-2" in check.detail

    async def test_a_section_anchor_verifies_a_quote_from_inside_it(self):
        # The advertised workflow reads a section by its uri, so the uri an
        # agent holds is usually the section's, not the paragraph's. That must
        # not read as a fabricated quote.
        check = await _tools().citations.verify_citation(_uri("#/texts/3"), "trois mois")
        assert check.valid is True
        assert check.status is CitationStatus.VERIFIED
        # …and it hands back the precise anchor to cite instead.
        assert check.citation is not None
        assert check.citation.ref == PREAVIS_REF

    async def test_a_quote_from_another_section_still_drifts(self):
        check = await _tools().citations.verify_citation(
            _uri("#/texts/3"), "Les factures sont émises"
        )
        assert check.valid is False
        assert check.status is CitationStatus.QUOTE_DRIFT


class TestVersionPinning:
    """The anchor grammar's whole premise: `@version` selects the parse."""

    async def test_reads_the_pinned_parse_not_the_latest(self):
        # Two parses of one document with *different* content. Pinning the
        # older one must return the older content, or a citation stops meaning
        # anything the moment a document is re-analysed.
        service = _service(jobs=[_job(SECTIONED, "an-1"), _job(FLAT, "an-2")])
        pinned = await service.get_outline(DOC_ID, version_id="an-1")
        latest = await service.get_outline(DOC_ID)
        assert (pinned.version_id, pinned.mode) == ("an-1", "sections")
        assert (latest.version_id, latest.mode) == ("an-2", "pages")

    async def test_a_ref_of_the_pinned_parse_reads_its_own_text(self):
        service = _service(jobs=[_job(SECTIONED, "an-1"), _job(FLAT, "an-2")])
        excerpt = await service.read_element(DOC_ID, PREAVIS_REF, version_id="an-1", include="self")
        assert PREAVIS_TEXT in excerpt.markdown
        assert excerpt.version_id == "an-1"

    async def test_the_same_ref_in_the_newer_parse_is_other_text(self):
        # #/texts/2 exists in both parses and says something different in each —
        # exactly the drift the version token prevents.
        service = _service(jobs=[_job(SECTIONED, "an-1"), _job(FLAT, "an-2")])
        old = await service.read_element(DOC_ID, "#/texts/2", version_id="an-1", include="self")
        new = await service.read_element(DOC_ID, "#/texts/2", version_id="an-2", include="self")
        assert old.markdown != new.markdown


class TestBudgetEdges:
    async def test_an_element_that_fits_exactly_is_included(self):
        # Pins `>` rather than `>=` at the cut-off: an element that exactly
        # fills the remaining budget belongs to this page, not the next.
        service = _service()
        first = await service.read_element(DOC_ID, PREAVIS_REF, include="self")
        exact = first.est_tokens
        excerpt = await service.read_element(DOC_ID, PREAVIS_REF, max_tokens=exact)
        assert excerpt.est_tokens == exact
        assert excerpt.truncated is False

    async def test_one_element_over_the_ceiling_is_clipped_not_smuggled_through(self):
        # The config promises a ceiling a client cannot raise; an element
        # larger than the whole budget must not sail past it unannounced.
        service = _service(config=NavigationConfig(max_read_tokens=5))
        excerpt = await service.read_element(DOC_ID, PREAVIS_REF, include="self")
        # The clip marker is charged to the budget too, so the ceiling holds
        # for the whole string rather than for the string minus its footnote.
        assert excerpt.est_tokens <= 5
        assert excerpt.truncated is True
        assert excerpt.markdown.endswith("[…clipped]")

    async def test_a_clipped_quote_still_verifies(self):
        tools = _tools(config=NavigationConfig(max_read_tokens=5))
        excerpt = await tools.navigation.read_element(DOC_ID, PREAVIS_REF, include="self")
        citation = excerpt.citations[0]
        check = await tools.citations.verify_citation(citation.uri, citation.quote.split(" […")[0])
        assert check.valid is True


class TestUnorderedRefs:
    async def test_a_ref_outside_reading_order_still_reads(self):
        # A caption lives in `texts` but hangs off a picture, so it is not in
        # `body.children`. `include="self"` has always returned its text; the
        # default mode must not answer "this element is empty".
        service = _service()
        section = await service.read_element(DOC_ID, "#/texts/5")
        alone = await service.read_element(DOC_ID, "#/texts/5", include="self")
        assert section.markdown == alone.markdown
        assert len(section.citations) == 1

    async def test_read_and_verify_agree_on_such_a_ref(self):
        tools = _tools()
        excerpt = await tools.navigation.read_element(DOC_ID, "#/texts/5")
        check = await tools.citations.verify_citation(_uri("#/texts/5"), "Figure 1")
        assert excerpt.citations[0].ref == "#/texts/5"
        assert check.valid is True


class TestIndexCache:
    async def test_evicts_the_least_recently_used_parse(self):
        jobs = [_job(SECTIONED, f"an-{i}") for i in range(5)]
        service = _service(jobs=jobs, config=NavigationConfig(index_cache_size=2))
        await service.get_outline(DOC_ID, version_id="an-0")
        await service.get_outline(DOC_ID, version_id="an-1")
        # Touching an-0 makes an-1 the least recently used…
        await service.get_outline(DOC_ID, version_id="an-0")
        await service.get_outline(DOC_ID, version_id="an-2")
        assert set(service._parses._cache) == {"an-0", "an-2"}

    async def test_never_grows_past_the_configured_bound(self):
        jobs = [_job(SECTIONED, f"an-{i}") for i in range(6)]
        service = _service(jobs=jobs, config=NavigationConfig(index_cache_size=2))
        for job in jobs:
            await service.get_outline(DOC_ID, version_id=job.id)
        assert len(service._parses._cache) == 2

    async def test_a_pinned_parse_is_indexed_from_its_own_json(self):
        # Guards the cache key: two parses must never share an index.
        service = _service(jobs=[_job(SECTIONED, "an-1"), _job(FLAT, "an-2")])
        await service.get_outline(DOC_ID, version_id="an-1")
        await service.get_outline(DOC_ID, version_id="an-2")
        assert service._parses._cache["an-1"][0] is not service._parses._cache["an-2"][0]


class TestMessyParse:
    async def test_page_read_includes_an_element_that_started_earlier(self):
        service = _service(job=_job(MESSY))
        excerpt = await service.read_element(DOC_ID, "#/pages/2")
        assert "commence page un" in excerpt.markdown

    async def test_running_headers_never_reach_an_excerpt(self):
        service = _service(job=_job(MESSY))
        excerpt = await service.read_element(DOC_ID, "#/pages/2")
        assert "page 2/2" not in excerpt.markdown
        assert all(c.label not in {"page_header", "page_footer"} for c in excerpt.citations)


class TestSpanCitations:
    """A quote that does not respect one element's boundary."""

    async def test_a_read_hands_back_the_span_covering_what_it_returned(self):
        excerpt = await _service().read_element(DOC_ID, "#/texts/3")
        first, last = excerpt.citations[0].ref, excerpt.citations[-1].ref
        assert excerpt.span_uri == _uri(f"{first}..{last}")

    async def test_a_single_element_read_offers_no_span(self):
        # Nothing to span. Offering the range would be noise on every read.
        excerpt = await _service().read_element(DOC_ID, PREAVIS_REF, include="self")
        assert excerpt.span_uri is None

    async def test_the_span_covers_nothing_the_read_did_not_return(self):
        # A page read picks elements by provenance, which need not be
        # contiguous in reading order; a span over them would silently cover
        # text the caller never saw.
        service = _service(job=_job(FLAT))
        excerpt = await service.read_element(DOC_ID, "#/pages/1")
        if excerpt.span_uri is not None:
            from domain.anchors import DocumentAnchor
            from domain.spans import parse_span

            start, end = parse_span(DocumentAnchor.parse(excerpt.span_uri).ref)
            read = {citation.ref for citation in excerpt.citations}
            assert start in read and end in read

    async def test_a_quote_running_across_two_elements_verifies(self):
        # This is the failure the span exists for: quoted one element at a
        # time, the sentence is in neither.
        across = "Chaque partie peut résilier le contrat. 12.2 Préavis"
        check = await _tools().citations.verify_citation(_uri("#/texts/2"), across)
        assert check.valid is False

        check = await _tools().citations.verify_citation(_uri("#/texts/1"), across)
        assert check.valid is True
        assert check.status is CitationStatus.VERIFIED
        assert check.citation.ref == "#/texts/2..#/texts/3"
        assert check.citation.label == "span"

    async def test_the_span_returned_is_the_smallest_one_that_contains_the_quote(self):
        quote = "12.2 Préavis Le préavis est de trois mois"
        check = await _tools().citations.verify_citation(_uri("#/texts/1"), quote)
        assert check.citation.ref == f"#/texts/3..{PREAVIS_REF}"

    async def test_the_detail_says_the_quote_spans_several_elements(self):
        check = await _tools().citations.verify_citation(
            _uri("#/texts/1"), "Chaque partie peut résilier le contrat. 12.2 Préavis"
        )
        assert "runs across several elements" in check.detail

    async def test_widening_does_not_invent_a_quote_that_is_not_there(self):
        check = await _tools().citations.verify_citation(
            _uri("#/texts/1"), "Chaque partie peut résilier le bail. 12.2 Préavis"
        )
        assert check.valid is False
        assert check.status is CitationStatus.QUOTE_DRIFT

    async def test_a_span_anchor_reads_and_cites_like_any_other(self):
        tools = _tools()
        span = _uri("#/texts/2..#/texts/3")
        excerpt = await tools.navigation.read_element(DOC_ID, "#/texts/2..#/texts/3")
        assert [c.ref for c in excerpt.citations] == ["#/texts/2", "#/texts/3"]

        citation = await tools.citations.get_citation(span)
        assert citation.label == "span"
        assert "Chaque partie" in citation.quote and "Préavis" in citation.quote

    async def test_a_span_deep_links_to_the_element_it_opens_on(self):
        # The Studio viewer scrolls to one ref; a range is not one it can
        # resolve.
        citation = await _tools().citations.get_citation(_uri("#/texts/2..#/texts/3"))
        assert citation.deep_link.endswith("ref=%23%2Ftexts%2F2&page=1")

    async def test_a_span_renders_as_one_crop_over_its_members(self, tmp_path):
        pdf = tmp_path / "contrat.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        document = _document()
        document.storage_path = str(pdf)
        tools = _tools(documents=[document])

        image = await tools.images.render(_uri("#/texts/2..#/texts/3"))
        assert image.page == 1
        assert image.width > 0


class TestPageRasterBudget:
    """The page path used to be the one raster path with no byte ceiling."""

    def _tools(self, tmp_path, **kwargs):
        pdf = tmp_path / "contrat.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        document = _document()
        document.storage_path = str(pdf)
        return _tools(documents=[document], **kwargs)

    async def test_a_page_that_blows_the_budget_is_rendered_smaller(self, tmp_path):
        raster = _FakeRasterizer(png_bytes=900_000)
        tools = self._tools(tmp_path, rasterizer=raster)
        await tools.images.render_page(_uri(PREAVIS_REF), max_width=1400)
        # The ladder halved rather than handing back the first render.
        assert len(raster.renders) > 1
        assert raster.renders[-1][1] < raster.renders[0][1]

    async def test_the_marker_is_placed_at_the_dpi_the_ladder_settled_on(self, tmp_path):
        # Computing it from the dpi that was *asked* for would put the marker
        # somewhere the passage is not.
        raster = _FakeRasterizer(png_bytes=900_000)
        tools = self._tools(tmp_path, rasterizer=raster)
        shrunk = await tools.images.render_page(_uri(PREAVIS_REF), max_width=1400)

        roomy = self._tools(tmp_path).images
        full = await roomy.render_page(_uri(PREAVIS_REF), max_width=1400)

        assert shrunk.dpi < full.dpi
        assert shrunk.highlight is not None
        # Same box, projected at a smaller dpi: strictly closer to the origin.
        assert shrunk.highlight[1] < full.highlight[1]

    async def test_an_ordinary_thumbnail_still_renders_once(self, tmp_path):
        raster = _FakeRasterizer()
        tools = self._tools(tmp_path, rasterizer=raster)
        await tools.images.render_page(_uri(PREAVIS_REF), max_width=320)
        assert len(raster.renders) == 1

    async def test_another_page_renders_without_the_passage_marker(self, tmp_path):
        """`page` lets a viewer leaf through the document — and the highlight
        stays on the anchor's own page, because on any other there is no
        passage to mark."""
        raster = _FakeRasterizer()
        tools = self._tools(tmp_path, rasterizer=raster)
        image = await tools.images.render_page(_uri(PREAVIS_REF), max_width=320, page=2)
        assert raster.renders[-1][0] == 2
        assert image.page == 2
        assert image.highlight is None
        assert image.page_count == 2

    async def test_the_page_is_clamped_to_the_parse(self, tmp_path):
        tools = self._tools(tmp_path)
        beyond = await tools.images.render_page(_uri(PREAVIS_REF), max_width=320, page=99)
        assert beyond.page == 2
        before = await tools.images.render_page(_uri(PREAVIS_REF), max_width=320, page=0)
        assert before.page == 1

"""`SourceService` — resolving the anchors an agent used, then mapping them.

The projection itself is covered in `test_source_map.py`. These tests cover
what the service adds: one parse pinned by every anchor, unknown anchors
reported rather than dropped, input bounds, and deep links.
"""

from __future__ import annotations

import pytest

from services.navigation_config import NavigationConfig
from services.navigation_errors import InvalidArgumentError, NoParseError
from tests.navigation_fixtures import (
    DOC_ID,
    JOB_ID,
    PREAVIS_REF,
    anchor_uri,
    make_document_tools,
)

PREAVIS_SECTION = "#/texts/3"


async def show(reads=(), cited=(), question="Quel est le préavis ?", **kwargs):
    tools = make_document_tools(**kwargs)
    return await tools.sources.show(question, list(reads), list(cited))


class TestResolution:
    async def test_the_report_names_the_parse_the_anchors_pin(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "le préavis", "")])
        assert (report.document_id, report.version_id) == (DOC_ID, JOB_ID)
        assert report.filename == "contrat.pdf"
        assert report.question == "Quel est le préavis ?"
        assert [round_.why for round_ in report.sources.rounds] == ["le préavis"]
        assert report.max_rounds == 5

    async def test_what_a_round_found_is_carried(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "le préavis", "trois mois")])
        assert report.sources.rounds[0].found == "trois mois"

    async def test_a_malformed_anchor_is_reported_not_dropped(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=[("not-an-anchor", "")]
        )
        assert report.unknown == ["not-an-anchor"]
        assert len(report.sources.rounds) == 1

    async def test_a_ref_the_parse_does_not_hold_is_reported(self):
        missing = anchor_uri("#/texts/999")
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=[(missing, "")])
        assert report.unknown == [missing]
        assert report.sources.rounds[0].cited == []

    async def test_anchors_into_two_parses_are_refused(self):
        with pytest.raises(InvalidArgumentError, match="more than one document or parse"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
                cited=[(anchor_uri(PREAVIS_REF, job_id="another-parse"), "")],
            )

    async def test_no_usable_anchor_is_refused(self):
        with pytest.raises(InvalidArgumentError, match="No usable anchor"):
            await show(reads=[("garbage", "", "")])

    async def test_a_parse_that_is_not_this_documents_is_refused(self):
        with pytest.raises(NoParseError):
            await show(reads=[(anchor_uri(PREAVIS_SECTION, job_id="ghost-parse"), "", "")])


class TestBounds:
    async def test_too_many_anchors_are_refused_before_any_work(self):
        config = NavigationConfig(max_source_anchors=2)
        reads = [(anchor_uri(PREAVIS_SECTION), "", "")] * 3
        with pytest.raises(InvalidArgumentError, match="at most 2"):
            await show(reads=reads, config=config)

    async def test_an_overlong_why_is_refused(self):
        config = NavigationConfig(max_source_text_chars=10)
        with pytest.raises(InvalidArgumentError, match="`why`"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "x" * 11, "")],
                question="Préavis ?",
                config=config,
            )

    async def test_an_overlong_found_is_refused(self):
        config = NavigationConfig(max_source_text_chars=10)
        with pytest.raises(InvalidArgumentError, match="`found`"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "x" * 11)],
                question="Préavis ?",
                config=config,
            )

    async def test_an_overlong_quote_is_refused(self):
        config = NavigationConfig(max_source_text_chars=10)
        with pytest.raises(InvalidArgumentError, match="`quote`"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
                cited=[(anchor_uri(PREAVIS_REF), "x" * 11)],
                question="Préavis ?",
                config=config,
            )

    async def test_an_overlong_question_is_refused(self):
        config = NavigationConfig(max_source_text_chars=10)
        with pytest.raises(InvalidArgumentError, match="`question`"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "")], question="x" * 11, config=config
            )


class TestQuotes:
    """Each cited quote is checked again: "verified" is the server's word."""

    async def test_a_quote_that_is_there_is_verified(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), "  trois mois à compter de la notification ")],
        )
        [passage] = report.sources.passages
        assert passage.status == "verified"
        assert passage.quote == "trois mois à compter de la notification"
        assert passage.round_id == "h1"

    async def test_a_section_anchor_is_narrowed_to_the_element_holding_the_quote(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_SECTION), "trois mois à compter de la notification")],
        )
        [passage] = report.sources.passages
        assert (passage.ref, passage.status) == (PREAVIS_REF, "verified")

    async def test_a_quote_that_is_not_there_says_so(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), "six mois à compter de la signature")],
        )
        [passage] = report.sources.passages
        assert (passage.ref, passage.status) == (PREAVIS_REF, "quote_drift")

    @pytest.mark.parametrize("quote", ["", "mois"], ids=["no quote", "too short to prove"])
    async def test_an_unchecked_citation_has_no_status(self, quote):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), quote)],
        )
        [passage] = report.sources.passages
        assert passage.status is None

    async def test_the_report_carries_the_page_count(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "", "")])
        assert report.page_count == 2


class TestMarks:
    """The quoted lines, found in the PDF's text layer: best effort, never a
    reason for the card to fail."""

    QUOTE = "trois mois à compter de la notification"

    @staticmethod
    def stored():
        from dataclasses import replace

        from tests.navigation_fixtures import make_document

        return [replace(make_document(), storage_path="/uploads/contrat.pdf")]

    class Reader:
        """The préavis sentence, set on one line inside its block on page 1."""

        def __init__(self, *, fails=False):
            self.fails = fails
            self.asked: list[tuple[str, int]] = []

        def glyphs(self, storage_path, *, page):
            from domain.quote_marks import Glyph

            self.asked.append((storage_path, page))
            if self.fails:
                raise OSError("unreadable")
            text = "Le préavis est de trois mois à compter de la notification."
            return [
                Glyph(c, None if c == " " else (0.12 + n * 0.01, 0.38, 0.13 + n * 0.01, 0.395))
                for n, c in enumerate(text)
            ]

    async def test_a_quote_found_on_its_page_carries_its_lines(self):
        reader = self.Reader()
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), self.QUOTE)],
            documents=self.stored(),
            page_text=reader,
        )
        [passage] = report.sources.passages
        [mark] = passage.marks
        assert mark.page == 1
        # "trois" is the 19th character of the sentence.
        assert mark.left == pytest.approx(0.12 + 18 * 0.01)
        assert reader.asked == [("/uploads/contrat.pdf", 1)]

    async def test_an_unreadable_page_leaves_the_passage_drawn_by_its_block(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), self.QUOTE)],
            documents=self.stored(),
            page_text=self.Reader(fails=True),
        )
        [passage] = report.sources.passages
        assert passage.marks == []
        assert passage.regions

    async def test_without_a_stored_file_nothing_is_read(self):
        reader = self.Reader()
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), self.QUOTE)],
            page_text=reader,
        )
        assert report.sources.passages[0].marks == []
        assert reader.asked == []

    async def test_a_citation_without_a_quote_is_not_looked_for(self):
        reader = self.Reader()
        await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), "")],
            documents=self.stored(),
            page_text=reader,
        )
        assert reader.asked == []


class TestWhereItSits:
    async def test_the_report_carries_the_documents_own_title(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "", "")])
        assert report.title == "Contrat de prestation"

    async def test_a_passage_carries_the_section_that_holds_it(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            cited=[(anchor_uri(PREAVIS_REF), "trois mois à compter de la notification")],
        )
        assert report.sources.passages[0].section == "12.2 Préavis"


class TestTitle:
    """The document's own title, read off the parse — Docling often labels a
    paper's title a section header."""

    @staticmethod
    def title_of(*items):
        from domain.element_reader import document_title
        from domain.parse_index import build_index
        from infra.docling_tree import DoclingTreeReader

        texts = [
            {
                "self_ref": f"#/texts/{n}",
                "label": label,
                "text": text,
                "prov": [
                    {
                        "page_no": page,
                        "bbox": {"l": 72, "t": 80 + 40 * n, "r": 520, "b": 100 + 40 * n},
                        "charspan": [0, len(text)],
                    }
                ],
            }
            for n, (label, text, page) in enumerate(items)
        ]
        doc = {
            "schema_name": "DoclingDocument",
            "version": "1.0.0",
            "name": "doc",
            "pages": {
                str(n): {"page_no": n, "size": {"width": 612, "height": 792}} for n in (1, 2)
            },
            "body": {"self_ref": "#/body", "children": [{"$ref": t["self_ref"]} for t in texts]},
            "texts": texts,
        }
        return document_title(build_index(doc, DoclingTreeReader()))

    def test_a_title_element_is_the_title(self):
        assert self.title_of(("text", "Intro", 1), ("title", "Le contrat", 1)) == "Le contrat"

    def test_a_heading_opening_the_document_on_page_one_is_taken(self):
        title = self.title_of(
            ("page_header", "arXiv preprint", 1),
            ("section_header", "Tetra: Serving LLMs", 1),
            ("text", "Abstract text", 1),
        )
        assert title == "Tetra: Serving LLMs"

    def test_a_numbered_heading_names_a_section_not_the_document(self):
        assert self.title_of(("section_header", "1 Introduction", 1)) == ""

    def test_a_document_opening_on_text_has_no_title(self):
        assert self.title_of(("text", "Some prose", 1), ("section_header", "Later", 1)) == ""


class TestOneParsePerCall:
    """Every anchor pins the same parse, so it is loaded once per call — not
    once more per quote checked and once more for the map — and whether a
    newer parse supersedes it is asked once, not once per quote verified."""

    @staticmethod
    def sources_over_a_counting_loader(*, newer_parse: str | None = None):
        from infra.docling_tree import DoclingTreeReader
        from services.citation_service import CitationService
        from services.navigation_service import NavigationService
        from services.parse_loader import ParseLoader
        from services.source_service import SourceService
        from tests.navigation_fixtures import (
            FakeAnalysisRepository,
            FakeDocumentRepository,
            make_document,
            make_job,
        )

        class CountingParseLoader(ParseLoader):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.loads: list[tuple[str, str | None]] = []

            async def load(self, document_id, version_id=None):
                self.loads.append((document_id, version_id))
                return await super().load(document_id, version_id)

        class CountingAnalysisRepository(FakeAnalysisRepository):
            def __init__(self, jobs):
                super().__init__(jobs)
                self.latest_lookups: list[list[str]] = []

            async def latest_parsed_ids(self, document_ids):
                self.latest_lookups.append(list(document_ids))
                return await super().latest_parsed_ids(document_ids)

        jobs = [make_job()] + ([make_job(job_id=newer_parse)] if newer_parse else [])
        config = NavigationConfig(studio_base_url="http://localhost:3000")
        parses = CountingParseLoader(
            document_repo=FakeDocumentRepository([make_document()]),
            analysis_repo=CountingAnalysisRepository(jobs),
            tree_reader=DoclingTreeReader(),
            config=config,
        )
        citations = CitationService(parses=parses, config=config)
        navigation = NavigationService(parses=parses, citations=citations, config=config)
        sources = SourceService(
            parses=parses, navigation=navigation, citations=citations, config=config
        )
        return sources, parses

    THREE_QUOTES = (
        (anchor_uri(PREAVIS_SECTION), "trois mois à compter de la notification"),
        (anchor_uri("#/texts/2"), "Chaque partie peut résilier le contrat."),
        (anchor_uri("#/texts/2"), "six mois à compter de la signature"),
    )

    async def test_the_parse_is_loaded_once_however_many_quotes_are_checked(self):
        sources, parses = self.sources_over_a_counting_loader()
        report = await sources.show(
            "Quel est le préavis ?",
            [(anchor_uri(PREAVIS_SECTION), "le préavis", "trois mois")],
            list(self.THREE_QUOTES),
        )
        assert parses.loads == [(DOC_ID, JOB_ID)]
        # Each quote was still checked against it, the section one narrowed.
        assert [(p.ref, p.status) for p in report.sources.passages] == [
            (PREAVIS_REF, "verified"),
            ("#/texts/2", "verified"),
            ("#/texts/2", "quote_drift"),
        ]
        # Two quotes found, one question about the current parse.
        assert parses.analyses.latest_lookups == [[DOC_ID]]

    async def test_a_superseded_parse_is_looked_up_once_and_marks_every_found_quote(self):
        sources, parses = self.sources_over_a_counting_loader(newer_parse="an-2")
        report = await sources.show("Quel est le préavis ?", [], list(self.THREE_QUOTES))
        assert parses.analyses.latest_lookups == [[DOC_ID]]
        assert [(p.ref, p.status) for p in report.sources.passages] == [
            (PREAVIS_REF, "stale_version"),
            ("#/texts/2", "stale_version"),
            ("#/texts/2", "quote_drift"),
        ]

    async def test_no_quote_no_lookup(self):
        sources, parses = self.sources_over_a_counting_loader(newer_parse="an-2")
        await sources.show("Quel est le préavis ?", [(anchor_uri(PREAVIS_SECTION), "", "")], [])
        assert parses.analyses.latest_lookups == []

    async def test_a_parse_that_cannot_be_loaded_is_still_refused(self):
        sources, parses = self.sources_over_a_counting_loader()
        with pytest.raises(NoParseError):
            await sources.show(
                "Quel est le préavis ?",
                [(anchor_uri(PREAVIS_SECTION, job_id="ghost-parse"), "", "")],
                [(anchor_uri(PREAVIS_REF, job_id="ghost-parse"), "trois mois à compter de")],
            )
        assert parses.loads == [(DOC_ID, "ghost-parse")]


class TestDeepLinks:
    async def test_cited_elements_and_map_nodes_get_a_studio_link(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=[(anchor_uri(PREAVIS_REF), "")]
        )
        assert report.deep_links[PREAVIS_REF].startswith(
            f"http://localhost:3000/analyses/{JOB_ID}?ref=%23%2Ftexts%2F4"
        )
        assert PREAVIS_SECTION in report.deep_links

    async def test_without_a_studio_url_there_is_no_link(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
            config=NavigationConfig(studio_base_url=""),
        )
        assert report.deep_links == {}

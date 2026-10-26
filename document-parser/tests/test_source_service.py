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
        assert [hop.why for hop in report.sources.hops] == ["le préavis"]
        assert report.max_rounds == 5

    async def test_what_a_round_found_is_carried(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "le préavis", "trois mois")])
        assert report.sources.hops[0].found == "trois mois"

    async def test_a_malformed_anchor_is_reported_not_dropped(self):
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=["not-an-anchor"])
        assert report.unknown == ["not-an-anchor"]
        assert len(report.sources.hops) == 1

    async def test_a_ref_the_parse_does_not_hold_is_reported(self):
        missing = anchor_uri("#/texts/999")
        report = await show(reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=[missing])
        assert report.unknown == [missing]
        assert report.sources.hops[0].cited == []

    async def test_anchors_into_two_parses_are_refused(self):
        with pytest.raises(InvalidArgumentError, match="more than one document or parse"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "")],
                cited=[anchor_uri(PREAVIS_REF, job_id="another-parse")],
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

    async def test_an_overlong_question_is_refused(self):
        config = NavigationConfig(max_source_text_chars=10)
        with pytest.raises(InvalidArgumentError, match="`question`"):
            await show(
                reads=[(anchor_uri(PREAVIS_SECTION), "", "")], question="x" * 11, config=config
            )


class TestDeepLinks:
    async def test_cited_elements_and_map_nodes_get_a_studio_link(self):
        report = await show(
            reads=[(anchor_uri(PREAVIS_SECTION), "", "")], cited=[anchor_uri(PREAVIS_REF)]
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

"""Where an answer came from — the reads and citations, on the document's map.

Pure projection, so these tests build an outline and an index from the shared
fixtures and assert against real refs. Most of the interesting cases are about
containment: an anchor names an element, the outline holds sections, and the
section that holds an element is not always one the outline published.
"""

from __future__ import annotations

import copy

from domain.source_map import (
    STATUS_CITED,
    STATUS_PATH,
    STATUS_READ,
    SourceCited,
    SourceRead,
    build_source_map,
)
from tests.navigation_fixtures import (
    DOC_ID,
    FLAT,
    PREAVIS_REF,
    SECTIONED,
    anchor_uri,
    make_job,
    make_navigation_service,
)

TITLE = "#/texts/0"
ARTICLE_12 = "#/texts/1"
PREAVIS_SECTION = "#/texts/3"
ARTICLE_13 = "#/texts/6"


def read(ref, why=""):
    return SourceRead(ref=ref, uri=anchor_uri(ref), why=why)


def cite(ref):
    return SourceCited(ref=ref, uri=anchor_uri(ref))


async def project(reads=(), cited=(), *, depth=6, payload=None):
    """Outline + index for the fixture document, then the projection."""
    navigation = make_navigation_service(job=make_job(payload) if payload else make_job())
    outline = await navigation.get_outline(DOC_ID, depth=depth)
    parse = await navigation._parses.load(DOC_ID)
    return build_source_map(outline, parse.index, list(reads), list(cited)), outline


def status_of(sources):
    return {node.ref: node.status for node in sources.nodes}


def _count(nodes):
    return sum(1 + _count(node.children) for node in nodes)


def _refs(nodes):
    return {node.ref for node in nodes} | {child.ref for node in nodes for child in node.children}


class TestContainment:
    async def test_a_cited_element_is_attributed_to_the_section_that_holds_it(self):
        sources, _ = await project(cited=[cite(PREAVIS_REF)])
        assert status_of(sources)[PREAVIS_SECTION] == STATUS_CITED

    async def test_ancestors_are_kept_so_the_tree_is_connected(self):
        sources, _ = await project(cited=[cite(PREAVIS_REF)])
        statuses = status_of(sources)
        assert statuses[TITLE] == STATUS_PATH
        assert statuses[ARTICLE_12] == STATUS_PATH

    async def test_untouched_branches_are_left_out(self):
        sources, _ = await project(reads=[read(PREAVIS_SECTION)])
        assert ARTICLE_13 not in status_of(sources)

    async def test_a_section_elided_by_depth_hands_its_hits_to_its_visible_ancestor(self):
        """At depth=1 the outline stops at the articles, so `12.2 Préavis` is
        not a place the reader can navigate to. Its hits belong to Article 12
        rather than vanishing from the tree."""
        sources, outline = await project(cited=[cite(PREAVIS_REF)], depth=1)
        assert PREAVIS_SECTION not in _refs(outline.nodes)
        assert status_of(sources)[ARTICLE_12] == STATUS_CITED

    async def test_a_span_is_located_by_its_first_member(self):
        sources, _ = await project(cited=[cite(f"{PREAVIS_REF}..#/tables/0")])
        assert status_of(sources)[PREAVIS_SECTION] == STATUS_CITED

    async def test_an_anchor_before_the_first_heading_lands_on_the_preamble(self):
        payload = copy.deepcopy(SECTIONED)
        payload["texts"][0]["label"] = "text"  # the title becomes preamble text
        sources, _ = await project(cited=[cite(TITLE)], payload=payload)
        assert status_of(sources) == {TITLE: STATUS_CITED}


class TestStatus:
    async def test_a_section_read_is_marked_read(self):
        sources, _ = await project(reads=[read(PREAVIS_SECTION)])
        assert status_of(sources)[PREAVIS_SECTION] == STATUS_READ

    async def test_cited_wins_over_read_on_the_same_node(self):
        """A section the answer quotes from is a source, not just a stop."""
        sources, _ = await project(reads=[read(PREAVIS_SECTION)], cited=[cite(PREAVIS_REF)])
        assert status_of(sources)[PREAVIS_SECTION] == STATUS_CITED

    async def test_every_hop_that_reached_a_node_is_recorded(self):
        sources, _ = await project(reads=[read(ARTICLE_12), read(PREAVIS_SECTION)])
        node = next(n for n in sources.nodes if n.ref == PREAVIS_SECTION)
        assert node.hop_ids == ["h2"]
        article = next(n for n in sources.nodes if n.ref == ARTICLE_12)
        assert article.hop_ids == ["h1"]

    async def test_nodes_come_back_in_document_order_with_their_anchor(self):
        sources, _ = await project(reads=[read(ARTICLE_13), read(PREAVIS_SECTION)])
        assert [node.ref for node in sources.nodes] == [
            TITLE,
            ARTICLE_12,
            PREAVIS_SECTION,
            ARTICLE_13,
        ]
        node = next(n for n in sources.nodes if n.ref == PREAVIS_SECTION)
        assert node.uri == anchor_uri(PREAVIS_SECTION)
        assert node.title == "12.2 Préavis"

    async def test_nothing_read_maps_to_nothing(self):
        sources, _ = await project()
        assert sources.nodes == []
        assert sources.hops == []


class TestReadingOrder:
    async def test_hops_keep_the_order_the_agent_read_in(self):
        sources, _ = await project(
            reads=[read(ARTICLE_13, "the end"), read(PREAVIS_SECTION, "the notice")]
        )
        assert [(h.ordinal, h.ref, h.why) for h in sources.hops] == [
            (1, ARTICLE_13, "the end"),
            (2, PREAVIS_SECTION, "the notice"),
        ]

    async def test_a_ref_read_twice_is_one_hop_with_its_first_why(self):
        """A cursor resuming a long section is one place on the path."""
        sources, _ = await project(
            reads=[read(PREAVIS_SECTION, "first"), read(PREAVIS_SECTION, "again")]
        )
        assert [(h.ref, h.why) for h in sources.hops] == [(PREAVIS_SECTION, "first")]

    async def test_a_quote_is_attributed_to_the_hop_that_read_it(self):
        sources, _ = await project(
            reads=[read(ARTICLE_13), read(PREAVIS_SECTION)], cited=[cite(PREAVIS_REF)]
        )
        assert sources.hops[0].cited == []
        assert sources.hops[1].cited == [anchor_uri(PREAVIS_REF)]

    async def test_a_hop_carries_its_section_title_and_page(self):
        sources, _ = await project(reads=[read(PREAVIS_SECTION)])
        hop = sources.hops[0]
        assert hop.title == "12.2 Préavis"
        assert hop.node_ref == PREAVIS_SECTION
        assert hop.page == 1


class TestTotals:
    async def test_the_whole_document_is_the_outline_total(self):
        sources, outline = await project(reads=[read(PREAVIS_SECTION)])
        assert sources.totals.tokens_total == outline.total_est_tokens
        assert 0 < sources.totals.tokens_read < sources.totals.tokens_total

    async def test_an_element_read_twice_is_counted_once(self):
        """Article 12 holds 12.2: reading both must not count 12.2 twice."""
        nested, _ = await project(reads=[read(ARTICLE_12), read(PREAVIS_SECTION)])
        alone, _ = await project(reads=[read(ARTICLE_12)])
        assert nested.totals.tokens_read == alone.totals.tokens_read

    async def test_sections_read_and_total(self):
        sources, outline = await project(reads=[read(ARTICLE_13), read(PREAVIS_SECTION)])
        assert sources.totals.sections_read == 2
        assert sources.totals.sections_total == _count(outline.nodes)

    async def test_percent_is_tokens_read_over_the_document(self):
        sources, _ = await project(reads=[read(PREAVIS_SECTION)])
        totals = sources.totals
        assert totals.percent == round(100 * totals.tokens_read / totals.tokens_total, 1)


class TestHeadlessDocument:
    """A scanned PDF has no headings, so the map is made of virtual pages."""

    async def test_an_element_is_attributed_to_its_page(self):
        sources, outline = await project(cited=[cite("#/texts/1")], payload=FLAT)
        assert outline.mode == "pages"
        assert status_of(sources) == {"#/pages/1": STATUS_CITED}
        assert sources.totals.mode == "pages"

    async def test_a_virtual_page_read_maps_to_itself(self):
        sources, _ = await project(reads=[read("#/pages/2")], payload=FLAT)
        assert status_of(sources) == {"#/pages/2": STATUS_READ}

"""The navigation tree — where an investigation went, on the document's own map.

Pure projection, so these tests build an outline and an index from the shared
fixtures and assert against real refs. The interesting cases are all about
containment: an attempt cites an element, the outline holds sections, and the
section that holds an element is not always one the outline published.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.investigation import Attempt, AttemptOutcome, Investigation, Step
from domain.investigation_map import (
    STATUS_KEPT,
    STATUS_PATH,
    STATUS_REJECTED,
    STATUS_VISITED,
    build_navigation_map,
)
from tests.navigation_fixtures import (
    DOC_ID,
    FLAT,
    JOB_ID,
    PREAVIS_REF,
    anchor_uri,
    make_job,
    make_navigation_service,
)

AT = datetime(2026, 8, 30, tzinfo=UTC)

TITLE = "#/texts/0"
ARTICLE_12 = "#/texts/1"
PREAVIS_SECTION = "#/texts/3"
ARTICLE_13 = "#/texts/6"


def attempt(uri, outcome=AttemptOutcome.KEPT, ordinal=1, step_id="s1"):
    return Attempt(
        id=f"a{step_id}{ordinal}",
        step_id=step_id,
        ordinal=ordinal,
        thought="this looks like it",
        uri=uri,
        created_at=AT,
        outcome=outcome,
    )


def investigation(*attempts_per_step):
    steps = [
        Step(id=f"s{index}", ordinal=index, question=f"q{index}", attempts=list(attempts))
        for index, attempts in enumerate(attempts_per_step, start=1)
    ]
    return Investigation(
        id="i1",
        document_id=DOC_ID,
        version_id=JOB_ID,
        question="How does one terminate?",
        created_at=AT,
        steps=steps,
    )


async def project(record, *, depth=6, payload=None):
    """Outline + index for the fixture document, then the projection."""
    navigation = make_navigation_service(job=make_job(payload) if payload else None)
    if payload is None:
        navigation = make_navigation_service()
    outline = await navigation.get_outline(DOC_ID, depth=depth)
    parse = await navigation._parses.load(DOC_ID)
    return build_navigation_map(outline, record, parse.index), outline


def status_of(nodes):
    return {node.ref: node.status for node in nodes}


def _refs(nodes):
    return {node.ref for node in nodes} | {child.ref for node in nodes for child in node.children}


class TestContainment:
    async def test_an_element_is_attributed_to_the_section_that_holds_it(self):
        nodes, _ = await project(investigation([attempt(anchor_uri(PREAVIS_REF))]))
        assert status_of(nodes)[PREAVIS_SECTION] == STATUS_KEPT

    async def test_ancestors_are_kept_so_the_tree_is_connected(self):
        nodes, _ = await project(investigation([attempt(anchor_uri(PREAVIS_REF))]))
        statuses = status_of(nodes)
        assert statuses[TITLE] == STATUS_PATH
        assert statuses[ARTICLE_12] == STATUS_PATH

    async def test_untouched_branches_are_left_out(self):
        nodes, _ = await project(investigation([attempt(anchor_uri(PREAVIS_REF))]))
        assert ARTICLE_13 not in status_of(nodes)

    async def test_a_section_elided_by_depth_hands_its_hits_to_its_visible_ancestor(self):
        """At depth=1 the outline stops at the articles, so `12.2 Préavis` is
        not a place the reader can navigate to. Its hits belong to Article 12
        rather than vanishing from the tree."""
        nodes, outline = await project(investigation([attempt(anchor_uri(PREAVIS_REF))]), depth=1)
        assert PREAVIS_SECTION not in _refs(outline.nodes)
        assert status_of(nodes)[ARTICLE_12] == STATUS_KEPT

    async def test_a_span_is_located_by_its_first_member(self):
        span = anchor_uri(f"{PREAVIS_REF}..#/tables/0")
        nodes, _ = await project(investigation([attempt(span)]))
        assert status_of(nodes)[PREAVIS_SECTION] == STATUS_KEPT

    async def test_a_malformed_anchor_lands_nowhere(self):
        record = investigation([attempt("not-an-anchor", outcome=AttemptOutcome.BAD_ANCHOR)])
        nodes, _ = await project(record)
        assert nodes == []


class TestStatus:
    @pytest.mark.parametrize(
        ("outcome", "expected"),
        [
            (AttemptOutcome.KEPT, STATUS_KEPT),
            (AttemptOutcome.QUOTE_DRIFT, STATUS_REJECTED),
            (AttemptOutcome.EMPTY_ELEMENT, STATUS_REJECTED),
            (None, STATUS_VISITED),
        ],
    )
    async def test_outcome_maps_to_status(self, outcome, expected):
        record = investigation([attempt(anchor_uri(PREAVIS_REF), outcome=outcome)])
        nodes, _ = await project(record)
        assert status_of(nodes)[PREAVIS_SECTION] == expected

    async def test_kept_wins_over_rejected_on_the_same_node(self):
        """A section that eventually answered is not a dead end."""
        record = investigation(
            [
                attempt(anchor_uri(PREAVIS_REF), outcome=AttemptOutcome.QUOTE_DRIFT, ordinal=1),
                attempt(anchor_uri(PREAVIS_REF), outcome=AttemptOutcome.KEPT, ordinal=2),
            ]
        )
        nodes, _ = await project(record)
        assert status_of(nodes)[PREAVIS_SECTION] == STATUS_KEPT

    async def test_every_step_that_reached_a_node_is_recorded(self):
        record = investigation(
            [attempt(anchor_uri(PREAVIS_REF), step_id="s1")],
            [attempt(anchor_uri(PREAVIS_REF), step_id="s2")],
        )
        nodes, _ = await project(record)
        node = next(n for n in nodes if n.ref == PREAVIS_SECTION)
        assert node.step_ids == ["s1", "s2"]


class TestOrderAndShape:
    async def test_nodes_come_back_in_document_order(self):
        record = investigation(
            [attempt(anchor_uri("#/texts/7"), step_id="s1")],
            [attempt(anchor_uri(PREAVIS_REF), step_id="s2")],
        )
        nodes, _ = await project(record)
        assert [node.ref for node in nodes] == [
            TITLE,
            ARTICLE_12,
            PREAVIS_SECTION,
            ARTICLE_13,
        ]

    async def test_entries_carry_the_anchor_the_outline_stamped(self):
        nodes, _ = await project(investigation([attempt(anchor_uri(PREAVIS_REF))]))
        node = next(n for n in nodes if n.ref == PREAVIS_SECTION)
        assert node.uri == anchor_uri(PREAVIS_SECTION)
        assert node.title == "12.2 Préavis"

    async def test_an_empty_investigation_maps_to_nothing(self):
        nodes, _ = await project(investigation([]))
        assert nodes == []


class TestHeadlessDocument:
    """A scanned PDF has no headings, so the map is made of virtual pages."""

    async def test_an_element_is_attributed_to_its_page(self):
        navigation = make_navigation_service(job=make_job(FLAT))
        outline = await navigation.get_outline(DOC_ID, depth=6)
        parse = await navigation._parses.load(DOC_ID)
        record = investigation([attempt(anchor_uri("#/texts/1"))])

        nodes = build_navigation_map(outline, record, parse.index)
        assert outline.mode == "pages"
        assert status_of(nodes) == {"#/pages/1": STATUS_KEPT}

    async def test_a_virtual_page_ref_maps_to_itself(self):
        navigation = make_navigation_service(job=make_job(FLAT))
        outline = await navigation.get_outline(DOC_ID, depth=6)
        parse = await navigation._parses.load(DOC_ID)
        record = investigation([attempt(anchor_uri("#/pages/2"))])

        nodes = build_navigation_map(outline, record, parse.index)
        assert status_of(nodes) == {"#/pages/2": STATUS_KEPT}

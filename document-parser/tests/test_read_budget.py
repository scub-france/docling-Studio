"""Reading under a token budget — `domain.read_budget`, without a service.

`read_element` end to end (ceilings, anchors, errors as the agent sees them)
is pinned in `test_navigation_service.py`; these pin the rules themselves on
the shared fixtures: which refs a read covers, the cursor grammar, where the
budget cuts, and when a read may hand back a span.
"""

from __future__ import annotations

import pytest

from domain.element_reader import resolve
from domain.navigation import CLIP_MARKER, read_cost
from domain.parse_index import build_index
from domain.read_budget import (
    READ_MODES,
    InvalidCursorError,
    pick_within_budget,
    read_span_ref,
    refs_to_read,
)
from infra.docling_tree import DoclingTreeReader
from tests.navigation_fixtures import FLAT, PREAVIS_REF, PREAVIS_TEXT, SECTIONED

ARTICLE_12 = "#/texts/1"
ARTICLE_12_SECTION = ["#/texts/1", "#/texts/2", "#/texts/3", PREAVIS_REF, "#/tables/0"]
ARTICLE_12_SECTION += ["#/pictures/0"]


def _index(payload=None):
    return build_index(payload or SECTIONED, DoclingTreeReader())


class TestRefsToRead:
    def test_the_modes_are_self_and_section(self):
        assert READ_MODES == ("self", "section")

    def test_a_section_read_covers_everything_the_heading_opens(self):
        assert refs_to_read(_index(), ARTICLE_12, include="section", cursor=None) == (
            ARTICLE_12_SECTION,
            0,
        )

    def test_a_self_read_covers_the_element_alone(self):
        assert refs_to_read(_index(), ARTICLE_12, include="self", cursor=None) == ([ARTICLE_12], 0)

    def test_a_page_reads_the_whole_page_in_either_mode(self):
        index = _index(FLAT)
        assert refs_to_read(index, "#/pages/1", include="self", cursor=None) == refs_to_read(
            index, "#/pages/1", include="section", cursor=None
        )

    def test_a_ref_outside_reading_order_still_reads_itself(self):
        # The caption hangs off the picture: it resolves, but no section holds it.
        assert refs_to_read(_index(), "#/texts/5", include="section", cursor=None) == (
            ["#/texts/5"],
            0,
        )

    def test_a_cursor_resumes_at_its_element(self):
        refs, start = refs_to_read(_index(), ARTICLE_12, include="section", cursor="#/texts/3")
        assert refs == ARTICLE_12_SECTION[2:]
        assert start == 0

    def test_a_cursor_with_an_offset_resumes_inside_its_element(self):
        refs, start = refs_to_read(
            _index(), ARTICLE_12, include="section", cursor=f"{PREAVIS_REF}@5"
        )
        assert refs[0] == PREAVIS_REF
        assert start == 5

    @pytest.mark.parametrize(
        "cursor",
        ["#/texts/7", f"{PREAVIS_REF}@0", f"{PREAVIS_REF}@{len(PREAVIS_TEXT)}", f"{PREAVIS_REF}@x"],
    )
    def test_a_cursor_from_elsewhere_is_refused_with_what_to_pass(self, cursor):
        with pytest.raises(InvalidCursorError, match="pass back the `next_cursor`"):
            refs_to_read(_index(), ARTICLE_12, include="section", cursor=cursor)


class TestPickWithinBudget:
    def test_everything_fits_in_a_large_budget(self):
        read = pick_within_budget(_index(), ARTICLE_12_SECTION, 10_000)
        assert [e.ref for e in read.elements] == ARTICLE_12_SECTION
        assert read.truncated is False
        assert read.next_cursor is None

    def test_the_budget_stops_at_an_element_boundary_and_says_where(self):
        index = _index()
        first_three = sum(read_cost(resolve(index, r).text) for r in ARTICLE_12_SECTION[:3])
        read = pick_within_budget(index, ARTICLE_12_SECTION, first_three)
        assert [e.ref for e in read.elements] == ARTICLE_12_SECTION[:3]
        assert read.spent == first_three
        assert read.truncated is True
        assert read.next_cursor == ARTICLE_12_SECTION[3]

    def test_an_element_larger_than_the_budget_is_cut_and_resumed_inside(self):
        read = pick_within_budget(_index(), [PREAVIS_REF], 70)
        [element] = read.elements
        assert element.text.endswith(CLIP_MARKER)
        assert read.truncated is True
        assert read.next_cursor == f"{PREAVIS_REF}@29"
        assert PREAVIS_TEXT[29:].startswith("à compter")

    def test_a_resumed_read_starts_at_the_offset(self):
        read = pick_within_budget(_index(), [PREAVIS_REF], 10_000, start=29)
        assert [e.text for e in read.elements] == [PREAVIS_TEXT[29:]]

    def test_textless_elements_cost_nothing_and_are_skipped(self):
        # Running headers and footers carry no readable text.
        index = _index(FLAT)
        refs, _ = refs_to_read(index, "#/pages/1", include="section", cursor=None)
        read = pick_within_budget(index, refs, 10_000)
        assert [e.ref for e in read.elements] == ["#/texts/0", "#/texts/1"]


class TestReadSpanRef:
    def test_a_read_of_several_elements_offers_the_span_over_them(self):
        index = _index()
        picked = [resolve(index, r) for r in ARTICLE_12_SECTION[:3]]
        assert read_span_ref(index, ARTICLE_12_SECTION, picked) == "#/texts/1..#/texts/3"

    def test_a_single_element_offers_no_span(self):
        index = _index()
        assert read_span_ref(index, [PREAVIS_REF], [resolve(index, PREAVIS_REF)]) is None

    def test_no_span_covers_an_element_the_read_skipped(self):
        index = _index()
        refs = ["#/texts/2", PREAVIS_REF]
        picked = [resolve(index, r) for r in refs]
        # #/texts/3 sits between them in reading order and was not read.
        assert read_span_ref(index, refs, picked) is None

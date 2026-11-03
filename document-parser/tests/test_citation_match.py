"""Where a quote sits in a parse — `domain.citation_match`, without a service.

The end-to-end verdicts (`verify_citation`'s statuses and details) are pinned
in `test_navigation_service.py`; these pin the matching rules themselves, on
the shared `SECTIONED` parse, with no repository and no loader.
"""

from __future__ import annotations

from domain.anchors import normalise_quote
from domain.citation_match import MIN_QUOTE_CHARS, _trim_left, locate_quote
from domain.element_reader import resolve
from domain.parse_index import build_index
from infra.docling_tree import DoclingTreeReader
from tests.navigation_fixtures import PREAVIS_REF, SECTIONED

ARTICLE_12 = "#/texts/1"
PREAVIS_HEADING = "#/texts/3"


def _locate(ref: str, quote: str):
    index = build_index(SECTIONED, DoclingTreeReader())
    element = resolve(index, ref)
    assert element is not None
    return locate_quote(index, ref, element, normalise_quote(quote))


class TestOneElement:
    def test_a_quote_inside_the_anchor_is_the_anchor(self):
        found = _locate(PREAVIS_REF, "trois mois à compter")
        assert found is not None
        assert found.ref == PREAVIS_REF

    def test_a_quote_nowhere_is_none(self):
        assert _locate(PREAVIS_REF, "six mois à compter") is None

    def test_reflowed_typography_still_matches(self):
        found = _locate(PREAVIS_REF, "Le  préavis\nest de trois mois")
        assert found is not None
        assert found.ref == PREAVIS_REF


class TestInsideASection:
    def test_a_section_anchor_answers_with_the_element_that_holds_the_quote(self):
        found = _locate(ARTICLE_12, "trois mois à compter de la notification")
        assert found is not None
        assert found.ref == PREAVIS_REF

    def test_a_quote_from_another_section_is_none(self):
        assert _locate(ARTICLE_12, "Les factures sont émises mensuellement.") is None

    def test_a_span_is_narrowed_to_its_member_rather_than_answered_whole(self):
        found = _locate(f"{ARTICLE_12}..{PREAVIS_REF}", "trois mois à compter")
        assert found is not None
        assert found.ref == PREAVIS_REF


class TestAcrossElements:
    def test_a_quote_running_into_the_next_element_is_a_span(self):
        found = _locate(ARTICLE_12, "Chaque partie peut résilier le contrat. 12.2 Préavis")
        assert found is not None
        assert found.ref == "#/texts/2..#/texts/3"
        assert found.label == "span"

    def test_the_span_does_not_open_on_a_heading_the_quote_does_not_reach(self):
        # The scan's leftmost start would be Article 12's own heading.
        found = _locate(ARTICLE_12, "12.2 Préavis Le préavis est de trois mois")
        assert found is not None
        assert found.ref == f"{PREAVIS_HEADING}..{PREAVIS_REF}"

    def test_widening_never_invents_a_quote(self):
        assert _locate(ARTICLE_12, "Chaque partie peut résilier le bail. 12.2 Préavis") is None

    def test_a_quote_longer_than_the_whole_section_is_none(self):
        assert _locate(PREAVIS_HEADING, "Le préavis est de trois mois. " * 20) is None


_TEXTS = [("a", "Article 12"), ("b", "le préavis"), ("c", "de trois mois")]


class TestTrimLeft:
    def test_drops_leading_elements_the_quote_does_not_reach(self):
        assert _trim_left(_TEXTS, 0, 2, "préavis de trois") == 1

    def test_keeps_a_start_the_quote_reaches_into(self):
        assert _trim_left(_TEXTS, 0, 2, "12 le préavis de trois") == 0

    def test_never_moves_past_the_end(self):
        assert _trim_left(_TEXTS, 0, 2, "trois") == 2


def test_a_quote_must_carry_at_least_ten_characters():
    assert MIN_QUOTE_CHARS == 10

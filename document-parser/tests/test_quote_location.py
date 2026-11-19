"""The pure reading rules moved into the domain: quote location and the read budget."""

from __future__ import annotations

from domain.anchors import normalise_quote
from domain.element_reader import resolve
from domain.navigation import ANCHOR_TOKENS, pick_within_budget, read_cost
from domain.parse_index import build_index
from domain.quote_location import locate_quote
from domain.spans import is_span
from infra.docling_tree import DoclingTreeReader
from tests.navigation_fixtures import PREAVIS_REF, PREAVIS_TEXT, SECTIONED

ARTICLE_12 = "#/texts/1"


def _index():
    return build_index(SECTIONED, DoclingTreeReader())


def _locate(ref: str, quote: str):
    index = _index()
    return locate_quote(index, ref, resolve(index, ref), normalise_quote(quote))


class TestLocateQuote:
    def test_the_anchor_itself(self):
        assert _locate(PREAVIS_REF, "trois mois").ref == PREAVIS_REF

    def test_an_element_the_section_covers(self):
        assert _locate(ARTICLE_12, "trois mois à compter").ref == PREAVIS_REF

    def test_a_quote_across_two_paragraphs_answers_with_a_span(self):
        found = _locate(ARTICLE_12, "résilier le contrat. 12.2 Préavis")
        assert is_span(found.ref)
        # Trimmed on the left: the section's own heading is not part of the span.
        assert not found.ref.startswith(ARTICLE_12)

    def test_a_quote_nowhere_under_the_anchor(self):
        assert _locate(ARTICLE_12, "Les factures sont émises mensuellement") is None


class TestPickWithinBudget:
    def test_everything_fits(self):
        picked, spent, truncated, cursor = pick_within_budget(_index(), [PREAVIS_REF], 1000)
        assert [e.text for e in picked] == [PREAVIS_TEXT]
        assert spent == read_cost(PREAVIS_TEXT)
        assert (truncated, cursor) == (False, None)

    def test_stops_before_the_element_that_overflows(self):
        refs = ["#/texts/2", PREAVIS_REF]
        budget = read_cost("Chaque partie peut résilier le contrat.")
        picked, _, truncated, cursor = pick_within_budget(_index(), refs, budget)
        assert [e.ref for e in picked] == ["#/texts/2"]
        assert (truncated, cursor) == (True, PREAVIS_REF)

    def test_one_element_larger_than_the_budget_is_cut_with_a_cursor_inside_it(self):
        picked, _, truncated, cursor = pick_within_budget(
            _index(), [PREAVIS_REF], ANCHOR_TOKENS + 6
        )
        assert truncated
        assert len(picked) == 1 and picked[0].text != PREAVIS_TEXT
        assert cursor.startswith(f"{PREAVIS_REF}@")

    def test_resumes_from_the_cursor_offset(self):
        picked, *_ = pick_within_budget(_index(), [PREAVIS_REF], 1000, start=3)
        assert picked[0].text == PREAVIS_TEXT[3:]

"""Where a quote sits on its page, line by line (`domain.quote_marks`).

Pages here are drawn by hand: each line of text is a row of glyphs 0.01 of
the page wide, so a glyph's place reads off its index.
"""

from __future__ import annotations

from domain.page_regions import PageRegion
from domain.quote_marks import Glyph, quote_marks

CHAR_W = 0.01
LINE_H = 0.015


def line(text: str, *, top: float, left: float = 0.1) -> list[Glyph]:
    """One line of glyphs; a space has no ink, so no box."""
    glyphs = []
    for n, char in enumerate(text):
        x = left + n * CHAR_W
        box = None if char == " " else (x, top, x + CHAR_W, top + LINE_H)
        glyphs.append(Glyph(char, box))
    # The text layer's own line break, inkless.
    glyphs.append(Glyph("\n", None))
    return glyphs


def edges(mark: PageRegion):
    return tuple(round(v, 4) for v in (mark.left, mark.top, mark.right, mark.bottom))


class TestLines:
    def test_a_quote_over_two_lines_is_two_marks_from_its_first_letter_to_its_last(self):
        page = line("The notice is three months", top=0.2) + line(
            "from the notification.", top=0.22
        )
        marks = quote_marks(page, "three months from the", page=4)
        assert [m.page for m in marks] == [4, 4]
        # "three" starts at index 14 of the first line; "the" ends at index 7.
        assert edges(marks[0]) == (0.24, 0.2, 0.36, 0.215)
        assert edges(marks[1]) == (0.1, 0.22, 0.18, 0.235)

    def test_spaces_hyphens_ligatures_and_quote_marks_do_not_matter(self):
        ffi, apostrophe = chr(0xFB03), chr(0x2019)  # a ligature, a curly quote
        page = line(f"an e{ffi}cient mo-", top=0.2) + line(f"del{apostrophe}s weights", top=0.22)
        marks = quote_marks(page, "efficient model's", page=1)
        assert len(marks) == 2

    def test_a_ligature_the_parse_lost_still_matches(self):
        """Docling read "fits" as "ts" and "files" as "les" on a paper whose
        font maps no text to its ligatures; the PDF's text layer kept them."""
        page = line("Where the larger model fits our files", top=0.2)
        [mark] = quote_marks(page, "larger model ts our les", page=1)
        assert round(mark.left, 4) == 0.2  # "larger" starts at index 10

    def test_case_does_not_matter(self):
        assert quote_marks(line("Trois Mois", top=0.5), "trois mois", page=1)

    def test_a_quote_that_is_not_on_the_page_marks_nothing(self):
        assert quote_marks(line("The notice is three months", top=0.2), "six months", page=1) == []

    def test_too_short_to_place_marks_nothing(self):
        assert quote_marks(line("4B and 8B", top=0.2), "4B", page=1) == []

    def test_a_long_quote_is_capped(self):
        page = [g for n in range(60) for g in line("same words", top=n * 0.016)]
        marks = quote_marks(page, "same words " * 60, page=1)
        assert len(marks) == 40


class TestWithinThePassage:
    def test_only_the_passages_blocks_are_searched(self):
        page = line("weights plus that cache", top=0.2)
        elsewhere = PageRegion(1, 0.1, 0.6, 0.9, 0.7)
        assert quote_marks(page, "weights plus", page=1, within=[elsewhere]) == []

    def test_a_sentence_on_the_page_twice_is_marked_where_the_passage_is(self):
        page = line("the cache takes 2.59 GB", top=0.2) + line("the cache takes 2.59 GB", top=0.6)
        passage = PageRegion(1, 0.1, 0.59, 0.9, 0.62)
        [mark] = quote_marks(page, "cache takes 2.59 GB", page=1, within=[passage])
        assert mark.top == 0.6


class TestTables:
    def test_cells_quoted_apart_are_found_apart(self):
        """The row's other cells sit between the quoted ones on the page."""
        row = line("AWQ w4g128, vLLM 5.96 73.79 9.42", top=0.3)
        marks = quote_marks(row, "AWQ w4g128, vLLM | 73.79", page=1)
        assert len(marks) == 2
        assert round(marks[1].left, 4) == 0.32  # "73.79" starts at index 22

    def test_cells_in_a_row_are_found_whole(self):
        row = line("14B 29.54 9.39", top=0.3)
        [mark] = quote_marks(row, "29.54 | 9.39", page=1)
        assert (round(mark.left, 4), round(mark.right, 4)) == (0.14, 0.24)

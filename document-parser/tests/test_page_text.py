"""The PDF text layer adapter (`infra.page_text`), on PDFs made here.

pdfium writes them with real text objects, so the boxes read back are the
ones a born-digital PDF carries.
"""

from __future__ import annotations

import ctypes

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest

from domain.quote_marks import quote_marks
from infra.page_text import PdfPageTextReader


def text_pdf(path, lines, *, size=(600, 800), rotation=0) -> str:
    """One page; `lines` are `(x, baseline_y, text)` in PDF points, 12 pt."""
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(*size)
    for x, y, text in lines:
        obj = pdfium_c.FPDFPageObj_NewTextObj(pdf, b"Helvetica", ctypes.c_float(12))
        buffer = ctypes.create_string_buffer((text + "\x00").encode("utf-16-le"))
        pdfium_c.FPDFText_SetText(obj, ctypes.cast(buffer, ctypes.POINTER(pdfium_c.FPDF_WCHAR)))
        pdfium_c.FPDFPageObj_Transform(obj, 1, 0, 0, 1, x, y)
        pdfium_c.FPDFPage_InsertObject(page, obj)
    pdfium_c.FPDFPage_GenerateContent(page)
    if rotation:
        page.set_rotation(rotation)
    pdf.save(str(path))
    pdf.close()
    return str(path)


@pytest.fixture
def notice(tmp_path):
    return text_pdf(
        tmp_path / "notice.pdf",
        [(100, 700, "The notice period is three months"), (100, 685, "from the notification.")],
    )


class TestGlyphs:
    def test_every_character_with_its_box_from_the_top_left(self, notice):
        glyphs = PdfPageTextReader().glyphs(notice, page=1)
        text = "".join(g.char for g in glyphs)
        assert "The notice period is three months" in text
        first = glyphs[0]
        assert first.char == "T"
        left, top, _, bottom = first.box
        assert left == pytest.approx(100 / 600, abs=0.002)
        # Near the top of the page, not the bottom: the y axis is flipped.
        assert 0.1 < top < bottom < 0.14

    def test_found_quotes_land_on_their_lines(self, notice):
        glyphs = PdfPageTextReader().glyphs(notice, page=1)
        marks = quote_marks(glyphs, "three months from the", page=1)
        assert len(marks) == 2
        assert marks[0].top < marks[1].top
        assert marks[1].left == pytest.approx(100 / 600, abs=0.002)

    def test_a_page_past_the_end_has_no_glyphs(self, notice):
        assert PdfPageTextReader().glyphs(notice, page=2) == []

    def test_a_rotated_page_has_none_rather_than_wrong_ones(self, tmp_path):
        path = text_pdf(tmp_path / "turned.pdf", [(100, 700, "Turned page")], rotation=90)
        assert PdfPageTextReader().glyphs(path, page=1) == []

    def test_a_page_without_text_has_none(self, tmp_path):
        pdf = pdfium.PdfDocument.new()
        pdf.new_page(600, 800)
        path = tmp_path / "blank.pdf"
        pdf.save(str(path))
        pdf.close()
        assert PdfPageTextReader().glyphs(str(path), page=1) == []

"""PDF text layer — the `PageTextReader` port's adapter.

pdfium knows where every character of a born-digital PDF sits; this reads
them off one page and hands them up as page fractions, so the domain can find
a quote among them without knowing what a PDF is.

pdfium is not thread-safe. Docling drives it from its own threads during an
analysis and guards it with one process-wide lock; this takes the same lock
when Docling is installed, and a lock of its own when it is not.
"""

from __future__ import annotations

import threading

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from domain.quote_marks import Glyph

try:  # pragma: no cover - which branch runs depends on the image
    from docling.utils.locks import pypdfium2_lock as _pdfium_lock
except ImportError:  # pragma: no cover
    _pdfium_lock = threading.Lock()


class PdfPageTextReader:
    """Stateless adapter for the `PageTextReader` port."""

    def glyphs(self, storage_path: str, *, page: int) -> list[Glyph]:
        with _pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                if not 1 <= page <= len(pdf):
                    return []
                return _read(pdf[page - 1])
            finally:
                pdf.close()


def _read(page: pdfium.PdfPage) -> list[Glyph]:
    # Character boxes come in the unrotated page's space; a rotated page's
    # raster does not, and a highlight off by a quarter turn is worse than
    # none.
    if page.get_rotation() % 360:
        return []
    left, bottom, right, top = page.get_cropbox()
    width, height = right - left, top - bottom
    if width <= 0 or height <= 0:
        return []
    text = page.get_textpage()
    try:
        glyphs: list[Glyph] = []
        for index in range(text.count_chars()):
            code = pdfium_c.FPDFText_GetUnicode(text, index)
            # Loose boxes span the line height, so a line's highlight is one
            # even band rather than the outline of its letters.
            x0, y0, x1, y1 = text.get_charbox(index, loose=True)
            box = (
                ((x0 - left) / width, (top - y1) / height, (x1 - left) / width, (top - y0) / height)
                if x1 > x0 and y1 > y0
                else None
            )
            glyphs.append(Glyph(chr(code) if code else "", box))
        return glyphs
    finally:
        text.close()

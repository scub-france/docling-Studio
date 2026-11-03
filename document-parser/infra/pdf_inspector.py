"""PDF geometry — the `PdfInspector` port's adapter.

pdfium opens the stored file by its path, so counting pages or reading their
sizes never loads the whole document into memory (pdfium reads the parts it
needs). Every call holds the process-wide pdfium lock (`infra.pdfium_lock`):
the library is not thread-safe, and Docling may be using it from another
thread during a local analysis.
"""

from __future__ import annotations

import pypdfium2 as pdfium

from domain.value_objects import PageDetail
from infra.pdfium_lock import pdfium_lock


class PdfiumInspector:
    """Stateless adapter for the `PdfInspector` port.

    pdfium itself raises `FileNotFoundError` for a missing file and
    `pypdfium2.PdfiumError` for one it cannot read as a PDF.
    """

    def page_count(self, storage_path: str) -> int:
        with pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                return len(pdf)
            finally:
                pdf.close()

    def page_sizes(self, storage_path: str) -> list[PageDetail]:
        with pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                sizes: list[PageDetail] = []
                for index in range(len(pdf)):
                    page = pdf[index]
                    try:
                        width, height = page.get_size()
                    finally:
                        page.close()
                    sizes.append(PageDetail(page_number=index + 1, width=width, height=height))
                return sizes
            finally:
                pdf.close()

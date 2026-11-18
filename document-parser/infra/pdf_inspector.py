"""PDF page geometry — the `PdfInspector` port's adapter.

pdfium opens the file by path, so the PDF is never read whole into memory
(#398). pdfium is not thread-safe and these reads run in worker threads, next
to a Docling conversion that drives pdfium from its own threads: every call
takes the process-wide lock the text-layer reader already shares with Docling.
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from domain.value_objects import PageDetail
from infra.pdfium_lock import pdfium_lock


class PdfiumInspector:
    """Stateless adapter for the `PdfInspector` port."""

    def page_sizes(self, storage_path: str) -> list[PageDetail]:
        if not Path(storage_path).is_file():
            raise FileNotFoundError(storage_path)
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

    def page_count(self, storage_path: str) -> int:
        with pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                return len(pdf)
            finally:
                pdf.close()

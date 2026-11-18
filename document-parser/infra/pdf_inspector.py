"""PDF page geometry — the `PdfInspector` port's adapter.

pdfium opens the file by path, so the PDF is never read whole into memory
(#398). pdfium is not thread-safe and these reads run in worker threads, next
to a Docling conversion that drives pdfium from its own threads: every call
takes the process-wide lock the text-layer reader already shares with Docling.
Counting an upload's pages from its bytes goes through poppler instead.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pypdfium2 as pdfium
from pdf2image import pdfinfo_from_bytes

from domain.value_objects import PageDetail
from infra.pdfium_lock import pdfium_lock

logger = logging.getLogger(__name__)


class PdfiumInspector:
    """Stateless adapter for the `PdfInspector` port."""

    def read_page_sizes(self, storage_path: str) -> list[PageDetail]:
        if not Path(storage_path).is_file():
            raise FileNotFoundError(storage_path)
        with pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                # Sizes come from the document's page table: loading each page
                # would hold the lock, and so stall a running conversion, about
                # forty times longer on a long PDF.
                sizes: list[PageDetail] = []
                for index in range(len(pdf)):
                    width, height = pdf.get_page_size(index)
                    sizes.append(PageDetail(page_number=index + 1, width=width, height=height))
                return sizes
            finally:
                pdf.close()

    def count_pages(self, storage_path: str) -> int:
        with pdfium_lock:
            pdf = pdfium.PdfDocument(storage_path)
            try:
                return len(pdf)
            finally:
                pdf.close()

    def count_pages_in_bytes(self, content: bytes) -> int | None:
        # The upload's page limit has always counted with poppler's pdfinfo:
        # keep it, so what an upload accepts or rejects does not change.
        try:
            info = pdfinfo_from_bytes(content)
            return info.get("Pages")
        except (FileNotFoundError, OSError) as exc:
            logger.warning("Could not count pages: %s", exc)
            return None
        except Exception:
            logger.warning("Unexpected error counting pages", exc_info=True)
            return None

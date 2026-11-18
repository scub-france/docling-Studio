"""Tests for the `PdfInspector` adapter — page geometry read by path (#352, #398)."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pypdfium2 as pdfium
import pytest

from infra.pdf_inspector import PdfiumInspector
from infra.pdfium_lock import pdfium_lock
from tests.test_document_service import pdf_with_pages


class TestPageSizes:
    def test_reads_the_size_of_every_page(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))

        pages = PdfiumInspector().page_sizes(str(pdf))

        assert [(p.page_number, p.width, p.height) for p in pages] == [
            (1, 612, 792),
            (2, 842, 595),
        ]
        assert all(p.elements == [] for p in pages)

    def test_opens_the_pdf_by_path_not_by_bytes(self, tmp_path):
        """pdfium gets the path, so the PDF is never read whole into memory (#398)."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))

        target = "infra.pdf_inspector.pdfium.PdfDocument"
        with patch(target, wraps=pdfium.PdfDocument) as opened:
            PdfiumInspector().page_sizes(str(pdf))

        assert opened.call_args.args == (str(pdf),)

    def test_raises_on_a_file_that_is_not_a_pdf(self, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")

        with pytest.raises(pdfium.PdfiumError):
            PdfiumInspector().page_sizes(str(broken))

    def test_raises_file_not_found_on_a_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PdfiumInspector().page_sizes(str(tmp_path / "gone.pdf"))


class TestPageCount:
    def test_counts_the_pages(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (612, 792), (612, 792)))

        assert PdfiumInspector().page_count(str(pdf)) == 3

    def test_raises_on_a_file_that_is_not_a_pdf(self, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")

        with pytest.raises(pdfium.PdfiumError):
            PdfiumInspector().page_count(str(broken))


class TestPdfiumLock:
    """pdfium is not thread-safe: every read holds the lock Docling shares."""

    @pytest.mark.parametrize("read", ["page_sizes", "page_count"])
    def test_reads_hold_the_shared_lock(self, tmp_path, read):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))
        held: list[bool] = []
        real_document = pdfium.PdfDocument

        def opened(path):
            held.append(pdfium_lock.locked())
            return real_document(path)

        with patch("infra.pdf_inspector.pdfium.PdfDocument", side_effect=opened):
            getattr(PdfiumInspector(), read)(str(pdf))

        assert held == [True]

    def test_waits_while_another_thread_holds_the_lock(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))
        done = threading.Event()

        def read():
            PdfiumInspector().page_count(str(pdf))
            done.set()

        with pdfium_lock:
            worker = threading.Thread(target=read)
            worker.start()
            assert not done.wait(0.1)
        worker.join(timeout=5)
        assert done.is_set()

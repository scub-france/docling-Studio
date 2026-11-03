"""The PDF geometry adapter (`infra.pdf_inspector`), on PDFs made here."""

from __future__ import annotations

import threading

import pypdfium2 as pdfium
import pytest

from domain.ports import PdfInspector
from infra import pdf_inspector
from infra.pdf_inspector import PdfiumInspector
from infra.pdfium_lock import pdfium_lock


def write_pdf(path, *sizes: tuple[float, float]) -> str:
    pdf = pdfium.PdfDocument.new()
    for width, height in sizes:
        pdf.new_page(width, height).close()
    pdf.save(str(path))
    pdf.close()
    return str(path)


@pytest.fixture
def two_pages(tmp_path) -> str:
    return write_pdf(tmp_path / "two.pdf", (612, 792), (842, 595))


def test_it_is_a_pdf_inspector():
    assert isinstance(PdfiumInspector(), PdfInspector)


class TestPageCount:
    def test_counts_the_pages(self, two_pages):
        assert PdfiumInspector().page_count(two_pages) == 2

    def test_a_missing_file_is_a_file_not_found_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PdfiumInspector().page_count(str(tmp_path / "gone.pdf"))

    def test_a_file_that_is_not_a_pdf_is_refused(self, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-1.4 fake pdf content")

        with pytest.raises(pdfium.PdfiumError):
            PdfiumInspector().page_count(str(broken))


class TestPageSizes:
    def test_reads_the_size_of_every_page_in_points(self, two_pages):
        pages = PdfiumInspector().page_sizes(two_pages)

        assert [(p.page_number, p.width, p.height) for p in pages] == [
            (1, 612, 792),
            (2, 842, 595),
        ]
        assert all(p.elements == [] for p in pages)

    def test_a_missing_file_is_a_file_not_found_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PdfiumInspector().page_sizes(str(tmp_path / "gone.pdf"))


class TestWiring:
    """The composition root hands the PDF ports to the services that read PDFs."""

    def test_document_service_gets_both_pdf_ports(self):
        from unittest.mock import AsyncMock

        from bootstrap.factories import build_document_service
        from domain.ports import PageRasterizer

        service = build_document_service(AsyncMock(), AsyncMock())

        assert isinstance(service._rasterizer, PageRasterizer)
        assert isinstance(service._pdf, PdfiumInspector)

    def test_analysis_service_counts_pages_with_the_inspector(self, monkeypatch):
        """Without it the page count is unknown and batching never starts."""
        from unittest.mock import MagicMock

        from bootstrap import factories

        monkeypatch.setattr(factories, "build_converter", MagicMock)
        monkeypatch.setattr(factories, "build_chunker", MagicMock)

        service = factories.build_analysis_service(MagicMock(), MagicMock(), None)

        assert isinstance(service._pdf_inspector, PdfiumInspector)


class TestLock:
    """pdfium is not thread-safe: the adapter opens nothing while another
    holder (Docling, the text-layer reader) has the shared lock."""

    @pytest.mark.parametrize("method", ["page_count", "page_sizes"])
    def test_waits_for_the_shared_pdfium_lock(self, two_pages, method, monkeypatch):
        opened = threading.Event()
        real = pdfium.PdfDocument

        def spy(*args, **kwargs):
            opened.set()
            return real(*args, **kwargs)

        monkeypatch.setattr(pdf_inspector.pdfium, "PdfDocument", spy)
        worker = threading.Thread(target=getattr(PdfiumInspector(), method), args=(two_pages,))
        with pdfium_lock:
            worker.start()
            assert not opened.wait(0.2), "pdfium was opened while the lock was held"
        worker.join(timeout=5)
        assert opened.is_set()

"""Tests for `PreviewService` on its ports, and the rasterizer's image formats."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from api.errors import to_http_error
from domain.models import Document
from domain.ports import DocumentFileStore, PageRasterizer, PdfInspector
from domain.value_objects import PageDetail
from infra.document_file_store import LocalDocumentFileStore
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from infra.preview_cache import PreviewCache
from services.errors import ServiceError
from services.preview_service import (
    PreviewDocumentNotFoundError,
    PreviewFileNotFoundError,
    PreviewFileUnreadableError,
    PreviewPageNotFoundError,
    PreviewPageOutOfRangeError,
    PreviewService,
)


def _files() -> MagicMock:
    """A `DocumentFileStore` double: a path resolves to itself, and every file
    has the same fingerprint."""
    files = MagicMock()
    files.resolve.side_effect = lambda storage_path: storage_path
    files.read_fingerprint.return_value = (9, 1)
    return files


def _service(
    document: Document | None, *, rasterizer=None, inspector=None, files=None, cache=None
) -> PreviewService:
    documents = MagicMock()
    documents.find_by_id = AsyncMock(return_value=document)
    return PreviewService(
        documents=documents,
        files=files or _files(),
        rasterizer=rasterizer or MagicMock(),
        inspector=inspector or MagicMock(),
        cache=cache or PreviewCache(),
    )


def test_adapters_satisfy_their_ports(tmp_path):
    assert isinstance(PdfPageRasterizer(), PageRasterizer)
    assert isinstance(PdfiumInspector(), PdfInspector)
    assert isinstance(LocalDocumentFileStore(str(tmp_path)), DocumentFileStore)


class TestGetPreview:
    async def test_renders_through_the_port_in_the_requested_format(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        rasterizer = MagicMock()
        rasterizer.render_page.return_value = b"webp"
        service = _service(Document(id="d1", storage_path=str(pdf)), rasterizer=rasterizer)

        image = await service.get_preview("d1", page=2, dpi=96, image_format="webp")

        assert image == b"webp"
        rasterizer.render_page.assert_called_once_with(str(pdf), page=2, dpi=96, fmt="WEBP")

    async def test_page_poppler_does_not_render_is_a_404_without_the_path(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        rasterizer = MagicMock()
        rasterizer.render_page.side_effect = ValueError(f"Page 4 not found in {pdf}")
        service = _service(Document(id="d1", storage_path=str(pdf)), rasterizer=rasterizer)

        with pytest.raises(PreviewPageNotFoundError) as caught:
            await service.get_preview("d1", page=4, dpi=96, image_format="png")

        http = to_http_error(caught.value)
        assert (http.status_code, http.detail) == (404, "Page 4 not found")

    async def test_unknown_document(self):
        with pytest.raises(PreviewDocumentNotFoundError) as caught:
            await _service(None).get_preview("nope", page=1, dpi=96, image_format="png")

        http = to_http_error(caught.value)
        assert (http.status_code, http.detail) == (404, "Document not found")

    async def test_page_beyond_the_known_count(self):
        service = _service(Document(id="d1", page_count=3, storage_path="/tmp/x.pdf"))

        with pytest.raises(PreviewPageOutOfRangeError) as caught:
            await service.get_preview("d1", page=10, dpi=96, image_format="png")

        http = to_http_error(caught.value)
        assert http.status_code == 400
        assert http.detail == "Page 10 out of range (document has 3 pages)"


class TestPageSizes:
    async def test_reads_through_the_inspector_with_the_resolved_path(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        inspector = MagicMock()
        inspector.read_page_sizes.return_value = [PageDetail(page_number=1, width=612, height=792)]
        service = _service(Document(id="d1", storage_path=str(pdf)), inspector=inspector)

        pages = await service.read_page_sizes("d1")

        assert [(p.page_number, p.width, p.height) for p in pages] == [(1, 612, 792)]
        inspector.read_page_sizes.assert_called_once_with(str(pdf))

    async def test_unknown_document(self):
        with pytest.raises(PreviewDocumentNotFoundError):
            await _service(None).read_page_sizes("nope")


def test_preview_errors_share_the_service_base():
    for family in (
        PreviewDocumentNotFoundError,
        PreviewPageOutOfRangeError,
        PreviewPageNotFoundError,
        PreviewFileNotFoundError,
        PreviewFileUnreadableError,
    ):
        assert issubclass(family, ServiceError)


class TestRasterizerFormats:
    """Moved from the former `DocumentService.generate_preview` tests."""

    @pytest.fixture
    def pdf_path(self, tmp_path):
        path = tmp_path / "doc.pdf"
        path.write_bytes(b"%PDF-fake")
        return path

    def test_png_is_the_default(self, pdf_path):
        image = Image.new("RGB", (8, 8), "white")
        with patch("infra.page_raster.convert_from_path", return_value=[image]):
            result = PdfPageRasterizer().render_page(str(pdf_path), page=1, dpi=72)

        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_returns_lossless_webp_at_the_same_page_size(self, pdf_path):
        image = Image.new("RGB", (32, 48), "white")
        with patch("infra.page_raster.convert_from_path", return_value=[image]):
            result = PdfPageRasterizer().render_page(str(pdf_path), page=1, dpi=150, fmt="WEBP")

        assert result[:4] == b"RIFF"
        assert result[8:12] == b"WEBP"
        with Image.open(io.BytesIO(result)) as decoded:
            assert decoded.size == (32, 48)
            assert decoded.convert("RGB").tobytes() == image.tobytes()


def _http(error: ServiceError) -> tuple[int, str]:
    http = to_http_error(error)
    return http.status_code, http.detail


class TestPdfReadErrors:
    """What the adapters raise while reading the PDF becomes a preview error;
    anything else stays unexpected, so the API answers 500."""

    _DOC = Document(id="d1", storage_path="/srv/uploads/doc.pdf")

    async def test_missing_file_at_the_fingerprint_is_a_404(self):
        files = _files()
        files.read_fingerprint.side_effect = FileNotFoundError("/srv/uploads/doc.pdf")

        with pytest.raises(PreviewFileNotFoundError) as caught:
            await _service(self._DOC, files=files).get_preview(
                "d1", page=1, dpi=96, image_format="png"
            )

        assert _http(caught.value) == (404, "PDF file not found on disk")

    async def test_missing_file_at_the_render_is_a_404(self):
        rasterizer = MagicMock()
        rasterizer.render_page.side_effect = FileNotFoundError("/srv/uploads/doc.pdf")

        with pytest.raises(PreviewFileNotFoundError):
            await _service(self._DOC, rasterizer=rasterizer).get_preview(
                "d1", page=1, dpi=96, image_format="png"
            )

    async def test_io_error_at_the_render_is_a_422(self):
        rasterizer = MagicMock()
        rasterizer.render_page.side_effect = OSError("disk")

        with pytest.raises(PreviewFileUnreadableError) as caught:
            await _service(self._DOC, rasterizer=rasterizer).get_preview(
                "d1", page=1, dpi=96, image_format="png"
            )

        assert _http(caught.value) == (422, "Failed to read PDF file")

    async def test_render_failure_is_a_422(self):
        rasterizer = MagicMock()
        rasterizer.render_page.side_effect = RuntimeError("poppler")

        with pytest.raises(PreviewFileUnreadableError) as caught:
            await _service(self._DOC, rasterizer=rasterizer).get_preview(
                "d1", page=1, dpi=96, image_format="png"
            )

        assert _http(caught.value) == (422, "Failed to generate preview")

    async def test_cache_failure_is_not_a_pdf_read_error(self):
        cache = MagicMock()
        cache.get.side_effect = RuntimeError("cache")

        with pytest.raises(RuntimeError):
            await _service(self._DOC, cache=cache).get_preview(
                "d1", page=1, dpi=96, image_format="png"
            )

    async def test_lookup_failure_is_not_a_pdf_read_error(self):
        service = _service(self._DOC)
        service._documents.find_by_id.side_effect = RuntimeError("database")

        with pytest.raises(RuntimeError):
            await service.get_preview("d1", page=1, dpi=96, image_format="png")
        with pytest.raises(RuntimeError):
            await service.read_page_sizes("d1")

    async def test_missing_file_for_the_page_sizes_is_a_404(self):
        inspector = MagicMock()
        inspector.read_page_sizes.side_effect = FileNotFoundError("/srv/uploads/doc.pdf")

        with pytest.raises(PreviewFileNotFoundError):
            await _service(self._DOC, inspector=inspector).read_page_sizes("d1")

    @pytest.mark.parametrize("error", [OSError("disk"), RuntimeError("pdfium")])
    async def test_unreadable_pdf_for_the_page_sizes_is_a_422(self, error):
        inspector = MagicMock()
        inspector.read_page_sizes.side_effect = error

        with pytest.raises(PreviewFileUnreadableError) as caught:
            await _service(self._DOC, inspector=inspector).read_page_sizes("d1")

        assert _http(caught.value) == (422, "Failed to read PDF file")

    async def test_the_cache_key_carries_the_resolved_path_and_fingerprint(self):
        cache = MagicMock()
        cache.get.return_value = b"cached"

        await _service(self._DOC, cache=cache).get_preview(
            "d1", page=2, dpi=96, image_format="webp"
        )

        cache.get.assert_called_once_with(("/srv/uploads/doc.pdf", 9, 1, 2, 96, "webp"))

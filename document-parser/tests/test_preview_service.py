"""Tests for `PreviewService` on its ports, and the rasterizer's image formats."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from api.errors import http_error
from domain.models import Document
from domain.ports import PageRasterizer, PdfInspector
from domain.value_objects import PageDetail
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from infra.preview_cache import PreviewCache
from services.errors import ServiceError
from services.preview_service import (
    PreviewDocumentNotFoundError,
    PreviewPageNotFoundError,
    PreviewPageOutOfRangeError,
    PreviewService,
)


def _service(document: Document | None, *, rasterizer=None, inspector=None) -> PreviewService:
    documents = MagicMock()
    documents.find_by_id = AsyncMock(return_value=document)
    documents.resolve_storage_path.side_effect = Path
    return PreviewService(
        documents=documents,
        rasterizer=rasterizer or MagicMock(),
        inspector=inspector or MagicMock(),
        cache=PreviewCache(),
    )


def test_adapters_satisfy_their_ports():
    assert isinstance(PdfPageRasterizer(), PageRasterizer)
    assert isinstance(PdfiumInspector(), PdfInspector)


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

        http = http_error(caught.value)
        assert (http.status_code, http.detail) == (404, "Page 4 not found")

    async def test_unknown_document(self):
        with pytest.raises(PreviewDocumentNotFoundError) as caught:
            await _service(None).get_preview("nope", page=1, dpi=96, image_format="png")

        http = http_error(caught.value)
        assert (http.status_code, http.detail) == (404, "Document not found")

    async def test_page_beyond_the_known_count(self):
        service = _service(Document(id="d1", page_count=3, storage_path="/tmp/x.pdf"))

        with pytest.raises(PreviewPageOutOfRangeError) as caught:
            await service.get_preview("d1", page=10, dpi=96, image_format="png")

        http = http_error(caught.value)
        assert http.status_code == 400
        assert http.detail == "Page 10 out of range (document has 3 pages)"


class TestPageSizes:
    async def test_reads_through_the_inspector_with_the_resolved_path(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        inspector = MagicMock()
        inspector.page_sizes.return_value = [PageDetail(page_number=1, width=612, height=792)]
        service = _service(Document(id="d1", storage_path=str(pdf)), inspector=inspector)

        pages = await service.page_sizes("d1")

        assert [(p.page_number, p.width, p.height) for p in pages] == [(1, 612, 792)]
        inspector.page_sizes.assert_called_once_with(str(pdf))

    async def test_unknown_document(self):
        with pytest.raises(PreviewDocumentNotFoundError):
            await _service(None).page_sizes("nope")


def test_preview_errors_share_the_service_base():
    for family in (
        PreviewDocumentNotFoundError,
        PreviewPageOutOfRangeError,
        PreviewPageNotFoundError,
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

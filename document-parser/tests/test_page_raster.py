"""Tests for the `PdfPageRasterizer` adapter — page rendering by path (#398)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from infra.page_raster import PdfPageRasterizer

_CONVERT = "infra.page_raster.convert_from_path"


def _image(payload: bytes = b"PNG") -> MagicMock:
    image = MagicMock()
    image.save = MagicMock(side_effect=lambda buf, format: buf.write(payload))
    return image


class TestRenderPage:
    def test_opens_the_pdf_by_path_and_renders_one_page(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with patch(_CONVERT, return_value=[_image(b"PNG-DATA")]) as convert:
            png = PdfPageRasterizer().render_page(str(pdf), page=2, dpi=110)

        assert png == b"PNG-DATA"
        convert.assert_called_once_with(str(pdf), first_page=2, last_page=2, dpi=110)

    def test_raises_value_error_when_the_page_is_missing(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with (
            patch(_CONVERT, return_value=[]),
            pytest.raises(ValueError, match="Page 9 not found"),
        ):
            PdfPageRasterizer().render_page(str(pdf), page=9, dpi=72)

    def test_raises_file_not_found_without_calling_poppler(self, tmp_path):
        with (
            patch(_CONVERT) as convert,
            pytest.raises(FileNotFoundError),
        ):
            PdfPageRasterizer().render_page(str(tmp_path / "gone.pdf"), page=1, dpi=72)

        convert.assert_not_called()

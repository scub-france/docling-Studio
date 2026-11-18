"""Real poppler rendering through the `PageRasterizer` adapter, unmocked.

Every other preview test patches `convert_from_path`; this one renders page 1
of a real PDF so a broken poppler install, a pdf2image upgrade or a PIL build
without WebP shows up in pytest rather than only in the e2e API suite.
"""

from __future__ import annotations

import io
import shutil

import pypdfium2 as pdfium
import pytest
from PIL import Image

from infra.page_raster import PdfPageRasterizer

pytestmark = pytest.mark.skipif(
    shutil.which("pdftoppm") is None,
    reason="poppler (pdftoppm) is not installed; real rasterisation cannot run",
)

# US Letter in points: at 72 dpi one point is one pixel.
WIDTH_PT, HEIGHT_PT = 612, 792
DPI = 72


@pytest.fixture
def pdf_path(tmp_path):
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(WIDTH_PT, HEIGHT_PT).close()
    pdf.new_page(WIDTH_PT, HEIGHT_PT).close()
    path = tmp_path / "two-pages.pdf"
    pdf.save(str(path))
    pdf.close()
    return str(path)


def _assert_page_sized(data: bytes, expected_format: str) -> None:
    image = Image.open(io.BytesIO(data))
    assert image.format == expected_format
    # Poppler rounds the page box to whole pixels; allow one pixel either way.
    assert abs(image.width - WIDTH_PT) <= 1
    assert abs(image.height - HEIGHT_PT) <= 1


def test_renders_page_one_to_png(pdf_path):
    data = PdfPageRasterizer().render_page(pdf_path, page=1, dpi=DPI, fmt="PNG")

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    _assert_page_sized(data, "PNG")


def test_renders_page_one_to_webp(pdf_path):
    data = PdfPageRasterizer().render_page(pdf_path, page=1, dpi=DPI, fmt="WEBP")

    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"
    _assert_page_sized(data, "WEBP")


def test_dpi_scales_the_raster(pdf_path):
    data = PdfPageRasterizer().render_page(pdf_path, page=1, dpi=DPI * 2, fmt="PNG")

    image = Image.open(io.BytesIO(data))
    assert abs(image.width - WIDTH_PT * 2) <= 2
    assert abs(image.height - HEIGHT_PT * 2) <= 2


def test_a_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        PdfPageRasterizer().render_page(str(tmp_path / "absent.pdf"), page=1, dpi=DPI)

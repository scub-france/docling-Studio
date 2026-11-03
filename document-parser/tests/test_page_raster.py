"""The page rasteriser adapter (`infra.page_raster`), on PDFs made here.

The services above it are tested against a blank fake
(`tests/navigation_fixtures.py`); these run the real poppler pipeline, so a
change in how the adapter reaches the file shows up here first.
"""

from __future__ import annotations

import io

import pypdfium2 as pdfium
import pytest
from pdf2image.exceptions import PDFPageCountError
from PIL import Image

from infra.page_raster import PdfPageRasterizer


def write_pdf(path, *sizes: tuple[float, float]) -> str:
    """A real PDF whose pages have the given (width, height), in points."""
    pdf = pdfium.PdfDocument.new()
    for width, height in sizes:
        pdf.new_page(width, height).close()
    pdf.save(str(path))
    pdf.close()
    return str(path)


def png_size(png: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(png)) as image:
        assert image.format == "PNG"
        return image.size


@pytest.fixture
def two_pages(tmp_path) -> str:
    # Portrait letter, then landscape A4: the page asked for is the one rendered.
    return write_pdf(tmp_path / "two.pdf", (612, 792), (842, 595))


class TestRenderPage:
    def test_renders_the_page_asked_for_as_png(self, two_pages):
        rasterizer = PdfPageRasterizer()

        assert png_size(rasterizer.render_page(two_pages, page=1, dpi=72)) == (612, 792)
        assert png_size(rasterizer.render_page(two_pages, page=2, dpi=72)) == (842, 595)

    def test_scales_with_the_dpi(self, two_pages):
        png = PdfPageRasterizer().render_page(two_pages, page=1, dpi=144)

        assert png_size(png) == (1224, 1584)

    def test_a_page_past_the_last_one_is_a_value_error(self, two_pages):
        with pytest.raises(ValueError, match="Page 3 not found"):
            PdfPageRasterizer().render_page(two_pages, page=3, dpi=72)

    def test_a_missing_file_is_a_file_not_found_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PdfPageRasterizer().render_page(str(tmp_path / "gone.pdf"), page=1, dpi=72)

    def test_reads_the_stored_file_in_place(self, two_pages, monkeypatch):
        # Copying the PDF to a temporary file (what `convert_from_bytes` does)
        # cost a full read and a full write of the document per page.
        import pdf2image.pdf2image

        def no_copy(*_args, **_kwargs):
            raise AssertionError("the PDF was copied to a temporary file")

        monkeypatch.setattr(pdf2image.pdf2image.tempfile, "mkstemp", no_copy)

        assert png_size(PdfPageRasterizer().render_page(two_pages, page=1, dpi=72)) == (612, 792)

    def test_a_file_that_is_not_a_pdf_is_refused(self, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")

        with pytest.raises(PDFPageCountError):
            PdfPageRasterizer().render_page(str(broken), page=1, dpi=72)


class TestCrop:
    @pytest.fixture
    def page_png(self, two_pages) -> bytes:
        return PdfPageRasterizer().render_page(two_pages, page=1, dpi=72)

    def test_crops_to_the_box(self, page_png):
        crop = PdfPageRasterizer().crop(page_png, (10, 20, 110, 70))

        assert (crop.width, crop.height) == (100, 50)
        assert png_size(crop.png) == (100, 50)

    def test_clamps_a_box_that_falls_off_the_page(self, page_png):
        crop = PdfPageRasterizer().crop(page_png, (600, 780, 700, 900))

        assert (crop.width, crop.height) == (12, 12)

    def test_reencodes_as_webp_when_asked(self, page_png):
        crop = PdfPageRasterizer().crop(page_png, (0, 0, 64, 32), fmt="WEBP")

        with Image.open(io.BytesIO(crop.png)) as image:
            assert image.format == "WEBP"
            assert image.size == (64, 32)

"""Tests for DocumentService — upload, preview, page counting, and deletion."""

from __future__ import annotations

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pypdfium2 as pdfium
import pytest
from PIL import Image

from domain.models import Document
from services.document_service import DocumentConfig, DocumentService, _count_pages


def _make_service(
    upload_dir: str = "/tmp/uploads",
    max_file_size_mb: int = 50,
    max_page_count: int = 0,
) -> DocumentService:
    """Create a DocumentService with mock repos for testing."""
    config = DocumentConfig(
        upload_dir=upload_dir,
        max_file_size_mb=max_file_size_mb,
        max_page_count=max_page_count,
    )
    return DocumentService(
        document_repo=AsyncMock(),
        analysis_repo=AsyncMock(),
        config=config,
    )


class TestUploadValidation:
    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        service = _make_service(max_file_size_mb=1)
        content = b"x" * (1 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="File too large"):
            await service.upload("big.pdf", "application/pdf", content)

    @pytest.mark.asyncio
    async def test_rejects_non_pdf(self):
        service = _make_service()
        content = b"NOT-A-PDF-FILE"
        with pytest.raises(ValueError, match="not a PDF"):
            await service.upload("fake.pdf", "application/pdf", content)

    @pytest.mark.asyncio
    async def test_rejects_too_many_pages(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), max_page_count=20)

        with patch("services.document_service._count_pages", return_value=40):
            content = b"%PDF-1.4 fake pdf content"
            with pytest.raises(ValueError, match="Too many pages"):
                await service.upload("big.pdf", "application/pdf", content)

        # Verify temp file was cleaned up
        assert len(os.listdir(tmp_path)) == 0

    @pytest.mark.asyncio
    async def test_allows_pdf_under_page_limit(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), max_page_count=20)

        with patch("services.document_service._count_pages", return_value=15):
            content = b"%PDF-1.4 fake pdf content"
            doc = await service.upload("ok.pdf", "application/pdf", content)

        assert doc.page_count == 15
        service._document_repo.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlimited_pages_when_zero(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), max_page_count=0)

        with patch("services.document_service._count_pages", return_value=100):
            content = b"%PDF-1.4 fake pdf content"
            doc = await service.upload("big.pdf", "application/pdf", content)

        assert doc.page_count == 100

    @pytest.mark.asyncio
    async def test_accepts_valid_pdf(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))

        with patch("services.document_service._count_pages", return_value=5):
            content = b"%PDF-1.4 fake pdf content"
            doc = await service.upload("test.pdf", "application/pdf", content)

        assert doc.filename == "test.pdf"
        assert doc.file_size == len(content)
        assert doc.page_count == 5
        service._document_repo.insert.assert_called_once()

        # Verify file was actually written to disk
        assert os.path.exists(doc.storage_path)
        with open(doc.storage_path, "rb") as f:
            assert f.read() == content


def pdf_with_pages(*sizes: tuple[float, float]) -> bytes:
    """A real PDF whose pages have the given (width, height), in points."""
    pdf = pdfium.PdfDocument.new()
    for width, height in sizes:
        pdf.new_page(width, height).close()
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


class TestPageSizes:
    def test_resolves_docker_upload_path_from_local_worktree(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        local_file = tmp_path / "stored.pdf"
        local_file.write_bytes(b"%PDF-1.4")

        assert service.resolve_storage_path("/app/uploads/stored.pdf") == local_file

    def test_reads_the_size_of_every_page(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))

        pages = DocumentService.page_sizes(pdf)

        assert [(p.page_number, p.width, p.height) for p in pages] == [
            (1, 612, 792),
            (2, 842, 595),
        ]
        assert all(p.elements == [] for p in pages)

    def test_opens_the_pdf_by_path_not_by_bytes(self, tmp_path):
        """pdfium gets the path, so the PDF is never read whole into memory (#398)."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))

        target = "services.document_service.pdfium.PdfDocument"
        with patch(target, wraps=pdfium.PdfDocument) as opened:
            DocumentService.page_sizes(pdf)

        assert opened.call_args.args == (str(pdf),)

    def test_raises_on_a_file_that_is_not_a_pdf(self, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")

        with pytest.raises(pdfium.PdfiumError):
            DocumentService.page_sizes(broken)

    def test_raises_file_not_found_on_a_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DocumentService.page_sizes(tmp_path / "gone.pdf")


class TestGeneratePreview:
    @pytest.fixture
    def pdf_path(self, tmp_path):
        path = tmp_path / "doc.pdf"
        path.write_bytes(b"%PDF-fake")
        return path

    def test_raises_on_invalid_page(self, pdf_path):
        """generate_preview should raise ValueError when page is out of range."""
        with (
            patch("services.document_service.convert_from_path", return_value=[]),
            pytest.raises(ValueError, match="Page 1 not found"),
        ):
            DocumentService.generate_preview(pdf_path, page=1)

    def test_returns_png_bytes(self, pdf_path):
        """generate_preview should return PNG bytes from pdf2image."""
        mock_image = MagicMock()
        mock_image.save = MagicMock(side_effect=lambda buf, format: buf.write(b"PNG-DATA"))

        with patch("services.document_service.convert_from_path", return_value=[mock_image]):
            result = DocumentService.generate_preview(pdf_path, page=1, dpi=72)

        assert result == b"PNG-DATA"

    def test_renders_only_the_requested_page_from_the_path(self, pdf_path):
        """Poppler opens the file by path, one page at a time (#398)."""
        mock_image = MagicMock()
        mock_image.save = MagicMock(side_effect=lambda buf, format: buf.write(b"PNG"))

        target = "services.document_service.convert_from_path"
        with patch(target, return_value=[mock_image]) as convert:
            DocumentService.generate_preview(pdf_path, page=3, dpi=96)

        convert.assert_called_once_with(pdf_path, first_page=3, last_page=3, dpi=96)

    def test_raises_file_not_found_on_a_missing_file(self, tmp_path):
        with (
            patch("services.document_service.convert_from_path") as convert,
            pytest.raises(FileNotFoundError),
        ):
            DocumentService.generate_preview(tmp_path / "gone.pdf", page=1)

        convert.assert_not_called()

    def test_returns_webp_bytes_at_the_same_page_size(self, pdf_path):
        image = Image.new("RGB", (32, 48), "white")
        with patch("services.document_service.convert_from_path", return_value=[image]):
            result = DocumentService.generate_preview(
                pdf_path, page=1, dpi=150, image_format="WEBP"
            )

        assert result[:4] == b"RIFF"
        assert result[8:12] == b"WEBP"
        with Image.open(io.BytesIO(result)) as decoded:
            assert decoded.size == (32, 48)
            assert decoded.convert("RGB").tobytes() == image.tobytes()


class TestCountPages:
    def test_returns_page_count(self):
        with patch(
            "services.document_service.pdfinfo_from_bytes",
            return_value={"Pages": 42},
        ):
            assert _count_pages(b"pdf") == 42

    def test_returns_none_on_error(self):
        with patch(
            "services.document_service.pdfinfo_from_bytes",
            side_effect=FileNotFoundError("poppler not found"),
        ):
            assert _count_pages(b"pdf") is None


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_file_and_records(self, tmp_path):
        # Create a fake file
        fake_file = tmp_path / "test.pdf"
        fake_file.write_bytes(b"content")

        doc = Document(
            id="doc-1",
            filename="test.pdf",
            storage_path=str(fake_file),
        )

        service = _make_service(upload_dir=str(tmp_path))
        service._document_repo.find_by_id = AsyncMock(return_value=doc)
        service._document_repo.delete = AsyncMock(return_value=True)
        service._analysis_repo.delete_by_document = AsyncMock(return_value=2)

        result = await service.delete("doc-1")

        assert result is True
        assert not fake_file.exists()

    @pytest.mark.asyncio
    async def test_delete_refuses_file_outside_upload_dir(self, tmp_path):
        """Files outside upload dir should not be deleted (path traversal protection)."""
        uploads = tmp_path / "uploads"
        os.makedirs(uploads, exist_ok=True)

        # File is outside the upload dir
        outside_file = tmp_path / "secret.txt"
        outside_file.write_bytes(b"secret")

        doc = Document(id="doc-1", filename="x.pdf", storage_path=str(outside_file))

        service = _make_service(upload_dir=str(uploads))
        service._document_repo.find_by_id = AsyncMock(return_value=doc)
        service._document_repo.delete = AsyncMock(return_value=True)
        service._analysis_repo.delete_by_document = AsyncMock(return_value=0)

        await service.delete("doc-1")

        # File should NOT have been deleted
        assert outside_file.exists()

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_false(self):
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=None)

        result = await service.delete("missing")
        assert result is False

"""Tests for DocumentService — upload, preview, page counting, and deletion."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.models import Document
from domain.value_objects import InputFileType
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


# Minimal valid ZIP header — every .docx is a ZIP archive
DOCX_BYTES = b"PK\x03\x04" + b"\x00" * 26


class TestUploadValidation:
    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        service = _make_service(max_file_size_mb=1)
        content = b"x" * (1 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="File too large"):
            await service.upload("big.pdf", "application/pdf", content)

    @pytest.mark.asyncio
    async def test_rejects_unsupported_extension(self):
        service = _make_service()
        content = b"some content"
        with pytest.raises(ValueError, match="Invalid file type"):
            await service.upload("fake.xlsx", "application/vnd.ms-excel", content)

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

    @pytest.mark.asyncio
    async def test_upload_docx_accepted(self, tmp_path):
        """DOCX files must pass validation and be stored with a .docx extension."""
        service = _make_service(upload_dir=str(tmp_path))

        doc = await service.upload(
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DOCX_BYTES,
        )

        assert doc.filename == "report.docx"
        assert doc.file_size == len(DOCX_BYTES)
        assert doc.page_count is None  # not counted at upload time for DOCX
        assert doc.storage_path.endswith(".docx"), (
            f"expected .docx extension, got {doc.storage_path}"
        )
        assert os.path.exists(doc.storage_path)
        service._document_repo.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_docx_file_extension_stored_correctly(self, tmp_path):
        """Stored filename must include the dot before the extension (regression: missing dot bug)."""
        service = _make_service(upload_dir=str(tmp_path))

        doc = await service.upload("test.docx", "application/octet-stream", DOCX_BYTES)

        # The stored file must have .docx as its suffix — not e.g. "uuid4docx"
        stored = os.path.basename(doc.storage_path)
        assert "." in stored, f"Stored filename has no extension: {stored}"
        assert stored.endswith(".docx"), f"Wrong extension in stored filename: {stored}"


class TestGeneratePreview:
    def test_raises_on_invalid_page(self):
        """generate_preview should raise ValueError when page is out of range."""
        with (
            patch("services.document_service.convert_from_bytes", return_value=[]),
            pytest.raises(ValueError, match="Page 1 not found"),
        ):
            DocumentService.generate_preview(b"%PDF-fake", page=1)

    def test_returns_png_bytes(self):
        """generate_preview should return PNG bytes from pdf2image."""
        mock_image = MagicMock()
        mock_image.save = MagicMock(side_effect=lambda buf, format: buf.write(b"PNG-DATA"))

        with patch("services.document_service.convert_from_bytes", return_value=[mock_image]):
            result = DocumentService.generate_preview(b"%PDF-fake", page=1, dpi=72)

        assert result == b"PNG-DATA"

    def test_docx_preview_converts_via_libreoffice(self):
        """DOCX preview must call _docx_to_pdf_bytes before pdf2image."""
        mock_image = MagicMock()
        mock_image.save = MagicMock(side_effect=lambda buf, format: buf.write(b"PNG-DOCX"))

        with (
            patch(
                "services.document_service._docx_to_pdf_bytes",
                return_value=b"%PDF-converted",
            ) as mock_lo,
            patch("services.document_service.convert_from_bytes", return_value=[mock_image]),
        ):
            result = DocumentService.generate_preview(
                DOCX_BYTES, page=1, file_type=InputFileType.DOCX
            )

        mock_lo.assert_called_once_with(DOCX_BYTES)
        assert result == b"PNG-DOCX"

    def test_docx_preview_raises_when_libreoffice_missing(self):
        """If LibreOffice is not installed, generate_preview must propagate FileNotFoundError."""
        with (
            patch(
                "services.document_service._docx_to_pdf_bytes",
                side_effect=FileNotFoundError("libreoffice not found"),
            ),
            pytest.raises(FileNotFoundError, match="libreoffice not found"),
        ):
            DocumentService.generate_preview(DOCX_BYTES, page=1, file_type=InputFileType.DOCX)


class TestCountPages:
    def test_returns_page_count(self):
        with patch(
            "services.document_service.pdfinfo_from_bytes",
            return_value={"Pages": 42},
        ):
            assert _count_pages(b"pdf", InputFileType.PDF) == 42

    def test_returns_none_on_error(self):
        with patch(
            "services.document_service.pdfinfo_from_bytes",
            side_effect=FileNotFoundError("poppler not found"),
        ):
            assert _count_pages(b"pdf", InputFileType.PDF) is None

    def test_returns_none_for_docx(self):
        assert _count_pages(b"docx-bytes", InputFileType.DOCX) is None


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

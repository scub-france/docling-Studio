"""Tests for DocumentService — upload, path resolution, page counting, and deletion."""

from __future__ import annotations

import io
import os
from unittest.mock import AsyncMock, patch

import pypdfium2 as pdfium
import pytest

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


class TestResolveStoragePath:
    def test_resolves_docker_upload_path_from_local_worktree(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        local_file = tmp_path / "stored.pdf"
        local_file.write_bytes(b"%PDF-1.4")

        assert service.resolve_storage_path("/app/uploads/stored.pdf") == local_file


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

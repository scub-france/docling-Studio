"""Tests for DocumentService — upload, preview, page counting, and deletion."""

from __future__ import annotations

import io
import os
from unittest.mock import AsyncMock, MagicMock

import pypdfium2 as pdfium
import pytest

from domain.models import Document
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from services.document_service import (
    DocumentConfig,
    DocumentFileError,
    DocumentService,
    PageNotFoundError,
    PageOutOfRangeError,
)


def _counting(pages: int) -> MagicMock:
    """A `PdfInspector` that says every PDF has `pages` pages."""
    inspector = MagicMock()
    inspector.page_count.return_value = pages
    return inspector


def _make_service(
    upload_dir: str = "/tmp/uploads",
    max_file_size_mb: int = 50,
    max_page_count: int = 0,
    *,
    rasterizer=None,
    pdf=None,
) -> DocumentService:
    """Create a DocumentService with mock repos for testing.

    The PDF ports default to the real adapters: the tests that care about
    them write real PDFs, the others never reach them.
    """
    config = DocumentConfig(
        upload_dir=upload_dir,
        max_file_size_mb=max_file_size_mb,
        max_page_count=max_page_count,
    )
    return DocumentService(
        document_repo=AsyncMock(),
        analysis_repo=AsyncMock(),
        config=config,
        rasterizer=rasterizer or PdfPageRasterizer(),
        pdf=pdf or PdfiumInspector(),
    )


def pdf_with_pages(*sizes: tuple[float, float]) -> bytes:
    """A real PDF whose pages have the given (width, height), in points."""
    pdf = pdfium.PdfDocument.new()
    for width, height in sizes:
        pdf.new_page(width, height).close()
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


def _stored(service: DocumentService, path, **fields) -> Document:
    """Make the service's repository return a document stored at `path`."""
    doc = Document(id="doc-1", filename="test.pdf", storage_path=str(path), **fields)
    service._document_repo.find_by_id = AsyncMock(return_value=doc)
    return doc


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
        service = _make_service(upload_dir=str(tmp_path), max_page_count=20, pdf=_counting(40))

        content = b"%PDF-1.4 fake pdf content"
        with pytest.raises(ValueError, match="Too many pages"):
            await service.upload("big.pdf", "application/pdf", content)

        # Verify temp file was cleaned up
        assert len(os.listdir(tmp_path)) == 0

    @pytest.mark.asyncio
    async def test_allows_pdf_under_page_limit(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), max_page_count=20, pdf=_counting(15))

        content = b"%PDF-1.4 fake pdf content"
        doc = await service.upload("ok.pdf", "application/pdf", content)

        assert doc.page_count == 15
        service._document_repo.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlimited_pages_when_zero(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), max_page_count=0, pdf=_counting(100))

        content = b"%PDF-1.4 fake pdf content"
        doc = await service.upload("big.pdf", "application/pdf", content)

        assert doc.page_count == 100

    @pytest.mark.asyncio
    async def test_accepts_valid_pdf(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), pdf=_counting(5))

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
        # ...and its pages counted from there, not from a copy in memory.
        service._pdf.page_count.assert_called_once_with(doc.storage_path)


class TestCountPages:
    """The page count at upload, on real files (the real `PdfiumInspector`)."""

    @pytest.mark.asyncio
    async def test_counts_the_pages_of_a_real_pdf(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))

        content = pdf_with_pages((612, 792), (612, 792), (842, 595))
        doc = await service.upload("three.pdf", "application/pdf", content)

        assert doc.page_count == 3

    @pytest.mark.asyncio
    async def test_keeps_a_pdf_whose_pages_cannot_be_counted(self, tmp_path):
        """A file that starts like a PDF but cannot be read as one is stored
        with an unknown page count, not refused — and the page limit, which
        cannot apply, does not refuse it either."""
        service = _make_service(upload_dir=str(tmp_path), max_page_count=20)

        content = b"%PDF-1.4 fake pdf content"
        doc = await service.upload("broken.pdf", "application/pdf", content)

        assert doc.page_count is None
        assert os.path.exists(doc.storage_path)
        service._document_repo.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_counts_a_pdf_with_a_damaged_tail(self, tmp_path):
        """A PDF cut short of its trailer still opens: its xref is rebuilt."""
        service = _make_service(upload_dir=str(tmp_path))

        content = pdf_with_pages((612, 792), (612, 792))[:-10]
        doc = await service.upload("cut.pdf", "application/pdf", content)

        assert doc.page_count == 2


class TestPageSizes:
    def test_resolves_docker_upload_path_from_local_worktree(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        local_file = tmp_path / "stored.pdf"
        local_file.write_bytes(b"%PDF-1.4")

        assert service.resolve_storage_path("/app/uploads/stored.pdf") == local_file

    @pytest.mark.asyncio
    async def test_reads_the_size_of_every_page(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))
        _stored(service, pdf)

        pages = await service.page_sizes("doc-1")

        assert [(p.page_number, p.width, p.height) for p in pages] == [
            (1, 612, 792),
            (2, 842, 595),
        ]
        assert all(p.elements == [] for p in pages)

    @pytest.mark.asyncio
    async def test_reads_a_docker_path_from_the_local_upload_dir(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        (tmp_path / "stored.pdf").write_bytes(pdf_with_pages((612, 792)))
        _stored(service, "/app/uploads/stored.pdf")

        pages = await service.page_sizes("doc-1")

        assert len(pages) == 1

    @pytest.mark.asyncio
    async def test_unknown_document_is_none(self):
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=None)

        assert await service.page_sizes("missing") is None

    @pytest.mark.asyncio
    async def test_a_missing_file_is_a_file_not_found_error(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        _stored(service, tmp_path / "gone.pdf")

        with pytest.raises(FileNotFoundError):
            await service.page_sizes("doc-1")

    @pytest.mark.asyncio
    async def test_a_file_that_is_not_a_pdf_is_a_document_file_error(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")
        _stored(service, broken)

        with pytest.raises(DocumentFileError):
            await service.page_sizes("doc-1")


class TestRenderPreview:
    @pytest.mark.asyncio
    async def test_renders_the_page_through_the_rasterizer(self, tmp_path):
        rasterizer = MagicMock()
        rasterizer.render_page.return_value = b"PNG-DATA"
        service = _make_service(upload_dir=str(tmp_path), rasterizer=rasterizer)
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        _stored(service, pdf, page_count=3)

        result = await service.render_preview("doc-1", page=2, dpi=72)

        assert result == b"PNG-DATA"
        rasterizer.render_page.assert_called_once_with(str(pdf), page=2, dpi=72)

    @pytest.mark.asyncio
    async def test_renders_a_real_page_as_png(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))
        _stored(service, pdf, page_count=1)

        result = await service.render_preview("doc-1", page=1, dpi=72)

        assert result.startswith(b"\x89PNG")

    @pytest.mark.asyncio
    async def test_unknown_document_is_none(self):
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=None)

        assert await service.render_preview("missing", page=1, dpi=72) is None

    @pytest.mark.asyncio
    async def test_refuses_a_page_past_the_known_page_count(self, tmp_path):
        rasterizer = MagicMock()
        service = _make_service(rasterizer=rasterizer)
        _stored(service, tmp_path / "test.pdf", page_count=3)

        with pytest.raises(PageOutOfRangeError, match=r"Page 10 out of range \(document has 3"):
            await service.render_preview("doc-1", page=10, dpi=72)
        rasterizer.render_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_page_the_pdf_does_not_have_is_page_not_found(self, tmp_path):
        """Without a stored page count, the PDF itself says the page is not there."""
        service = _make_service(upload_dir=str(tmp_path))
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))
        _stored(service, pdf, page_count=None)

        with pytest.raises(PageNotFoundError, match=r"^Page 4 not found$"):
            await service.render_preview("doc-1", page=4, dpi=72)

    @pytest.mark.asyncio
    async def test_a_missing_file_is_a_file_not_found_error(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        _stored(service, tmp_path / "gone.pdf", page_count=1)

        with pytest.raises(FileNotFoundError):
            await service.render_preview("doc-1", page=1, dpi=72)

    @pytest.mark.asyncio
    async def test_a_read_failure_stays_an_os_error(self, tmp_path):
        rasterizer = MagicMock()
        rasterizer.render_page.side_effect = PermissionError("denied")
        service = _make_service(upload_dir=str(tmp_path), rasterizer=rasterizer)
        _stored(service, tmp_path / "test.pdf", page_count=1)

        with pytest.raises(PermissionError):
            await service.render_preview("doc-1", page=1, dpi=72)

    @pytest.mark.asyncio
    async def test_a_file_that_is_not_a_pdf_is_a_document_file_error(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path))
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")
        _stored(service, broken, page_count=1)

        with pytest.raises(DocumentFileError):
            await service.render_preview("doc-1", page=1, dpi=72)


class TestFindWithStoreLinks:
    @pytest.mark.asyncio
    async def test_unknown_document_is_none(self):
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=None)

        assert await service.find_with_store_links("missing") is None

    @pytest.mark.asyncio
    async def test_without_links_the_stores_are_not_read(self, tmp_path):
        stores, links = AsyncMock(), AsyncMock()
        links.find_for_document.return_value = []
        service = DocumentService(
            document_repo=AsyncMock(),
            analysis_repo=AsyncMock(),
            config=DocumentConfig(),
            rasterizer=PdfPageRasterizer(),
            pdf=PdfiumInspector(),
            store_repo=stores,
            link_repo=links,
        )
        doc = _stored(service, tmp_path / "test.pdf")

        assert await service.find_with_store_links("doc-1") == (doc, [])
        stores.find_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_without_the_store_repositories_it_is_pushed_nowhere(self, tmp_path):
        service = _make_service()
        doc = _stored(service, tmp_path / "test.pdf")

        assert await service.find_with_store_links("doc-1") == (doc, [])


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

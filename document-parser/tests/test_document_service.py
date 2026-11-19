"""Tests for DocumentService — upload, page counting, and deletion."""

from __future__ import annotations

import io
import os
import shutil
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pypdfium2 as pdfium
import pytest

from domain.models import Document, DocumentStoreLink, Store
from domain.value_objects import DocumentStoreLinkState
from infra.document_file_store import LocalDocumentFileStore
from infra.pdf_inspector import PdfiumInspector
from services.document_service import DocumentConfig, DocumentService, DocumentStoreLinkView


def _counting(pages: int | None) -> MagicMock:
    """A `PdfInspector` double whose upload count is `pages`."""
    inspector = MagicMock()
    inspector.count_pages_in_bytes.return_value = pages
    return inspector


def _make_service(
    upload_dir: str = "/tmp/uploads",
    max_file_size_mb: int = 50,
    max_page_count: int = 0,
    pdf_inspector=None,
) -> DocumentService:
    """Create a DocumentService with mock repos and a file store rooted at `upload_dir`."""
    config = DocumentConfig(
        max_file_size_mb=max_file_size_mb,
        max_page_count=max_page_count,
    )
    return DocumentService(
        document_repo=AsyncMock(),
        analysis_repo=AsyncMock(),
        config=config,
        link_repo=AsyncMock(),
        store_repo=AsyncMock(),
        pdf_inspector=pdf_inspector or _counting(None),
        # The real store: these tests check what lands on, and leaves, the disk.
        file_store=LocalDocumentFileStore(upload_dir),
        current_analysis=AsyncMock(),
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
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=20, pdf_inspector=_counting(40)
        )

        content = b"%PDF-1.4 fake pdf content"
        with pytest.raises(ValueError, match="Too many pages"):
            await service.upload("big.pdf", "application/pdf", content)

        # Verify temp file was cleaned up
        assert len(os.listdir(tmp_path)) == 0

    @pytest.mark.asyncio
    async def test_allows_pdf_under_page_limit(self, tmp_path):
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=20, pdf_inspector=_counting(15)
        )

        content = b"%PDF-1.4 fake pdf content"
        doc = await service.upload("ok.pdf", "application/pdf", content)

        assert doc.page_count == 15
        service._document_repo.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlimited_pages_when_zero(self, tmp_path):
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=0, pdf_inspector=_counting(100)
        )

        content = b"%PDF-1.4 fake pdf content"
        doc = await service.upload("big.pdf", "application/pdf", content)

        assert doc.page_count == 100

    @pytest.mark.asyncio
    async def test_accepts_valid_pdf(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), pdf_inspector=_counting(5))

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


_NO_PDFINFO = shutil.which("pdfinfo") is None


@pytest.mark.skipif(_NO_PDFINFO, reason="poppler's pdfinfo is not installed")
class TestUploadThroughTheRealInspector:
    """The upload's page count and page limit on a real PDF, through poppler."""

    async def test_counts_the_pages_of_a_real_pdf(self, tmp_path):
        service = _make_service(upload_dir=str(tmp_path), pdf_inspector=PdfiumInspector())

        doc = await service.upload(
            "three.pdf", "application/pdf", pdf_with_pages((612, 792), (612, 792), (842, 595))
        )

        assert doc.page_count == 3
        service._document_repo.insert.assert_called_once()

    async def test_rejects_a_real_pdf_over_the_page_limit(self, tmp_path):
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=2, pdf_inspector=PdfiumInspector()
        )

        with pytest.raises(ValueError, match=r"^Too many pages \(3\)\. Maximum allowed: 2$"):
            await service.upload("three.pdf", "application/pdf", pdf_with_pages(*[(612, 792)] * 3))

        assert os.listdir(tmp_path) == []
        service._document_repo.insert.assert_not_called()

    async def test_accepts_a_damaged_pdf_without_a_page_count(self, tmp_path):
        """An unreadable PDF has never been rejected at upload: it is stored
        without a page count, and the page limit cannot apply."""
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=2, pdf_inspector=PdfiumInspector()
        )

        doc = await service.upload("broken.pdf", "application/pdf", b"%PDF-1.4 truncated")

        assert doc.page_count is None


class TestUploadCountsThroughTheInspector:
    async def test_counts_the_uploaded_bytes(self, tmp_path):
        inspector = _counting(2)
        service = _make_service(upload_dir=str(tmp_path), pdf_inspector=inspector)
        content = b"%PDF-1.4 fake pdf content"

        await service.upload("ok.pdf", "application/pdf", content)

        inspector.count_pages_in_bytes.assert_called_once_with(content)

    async def test_no_count_skips_the_page_limit(self, tmp_path):
        service = _make_service(
            upload_dir=str(tmp_path), max_page_count=1, pdf_inspector=_counting(None)
        )

        doc = await service.upload("ok.pdf", "application/pdf", b"%PDF-1.4 fake pdf content")

        assert doc.page_count is None


class TestFindWithStoreLinks:
    async def test_missing_document_returns_none(self):
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=None)

        assert await service.find_with_store_links("missing") is None
        service._link_repo.find_for_document.assert_not_called()

    async def test_no_links_skips_the_store_lookup(self):
        doc = Document(id="d1", filename="a.pdf", storage_path="/tmp/a.pdf")
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=doc)
        service._link_repo.find_for_document = AsyncMock(return_value=[])

        assert await service.find_with_store_links("d1") == (doc, [])
        service._store_repo.find_all.assert_not_called()

    async def test_names_each_link_by_its_store_slug(self):
        doc = Document(id="d1", filename="a.pdf", storage_path="/tmp/a.pdf")
        pushed = datetime(2026, 11, 1, 12, 0, 0)
        service = _make_service()
        service._document_repo.find_by_id = AsyncMock(return_value=doc)
        service._link_repo.find_for_document = AsyncMock(
            return_value=[
                DocumentStoreLink(document_id="d1", store_id="s-1", last_push_at=pushed),
                DocumentStoreLink(
                    document_id="d1", store_id="s-gone", state=DocumentStoreLinkState.STALE
                ),
            ]
        )
        service._store_repo.find_all = AsyncMock(return_value=[Store(id="s-1", slug="legal-v1")])

        assert await service.find_with_store_links("d1") == (
            doc,
            [
                DocumentStoreLinkView("legal-v1", DocumentStoreLinkState.INGESTED, pushed),
                # An unknown store keeps its id, as before.
                DocumentStoreLinkView("s-gone", DocumentStoreLinkState.STALE, None),
            ],
        )


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


class TestFilesGoThroughTheStore:
    """The service hands every file operation to its `DocumentFileStore`."""

    def _service(self, *, pages: int | None, max_page_count: int = 0):
        store = MagicMock()
        store.save.return_value = "/srv/uploads/stored.pdf"
        service = DocumentService(
            document_repo=AsyncMock(),
            analysis_repo=AsyncMock(),
            config=DocumentConfig(max_page_count=max_page_count),
            link_repo=AsyncMock(),
            store_repo=AsyncMock(),
            pdf_inspector=_counting(pages),
            file_store=store,
            current_analysis=AsyncMock(),
        )
        return service, store

    async def test_upload_saves_under_a_fresh_pdf_name_and_keeps_the_stored_path(self):
        service, store = self._service(pages=3)
        content = b"%PDF-1.4 fake pdf content"

        doc = await service.upload("report.pdf", "application/pdf", content)

        file_name, saved = store.save.call_args.args
        assert file_name.endswith(".pdf")
        assert file_name != "report.pdf"
        assert saved == content
        assert doc.storage_path == "/srv/uploads/stored.pdf"
        store.discard.assert_not_called()

    async def test_page_limit_discards_the_saved_file_before_the_insert(self):
        service, store = self._service(pages=5, max_page_count=2)

        with pytest.raises(ValueError, match="Too many pages"):
            await service.upload("big.pdf", "application/pdf", b"%PDF-1.4 fake pdf content")

        store.discard.assert_called_once_with("/srv/uploads/stored.pdf")
        service._document_repo.insert.assert_not_called()

    async def test_rejected_content_never_reaches_the_store(self):
        service, store = self._service(pages=1)

        with pytest.raises(ValueError, match="not a PDF"):
            await service.upload("fake.pdf", "application/pdf", b"NOT-A-PDF-FILE")

        store.save.assert_not_called()

    async def test_delete_removes_the_analyses_and_asks_the_store(self):
        service, store = self._service(pages=None)
        doc = Document(id="doc-1", filename="x.pdf", storage_path="/srv/uploads/x.pdf")
        service._document_repo.find_by_id = AsyncMock(return_value=doc)
        service._document_repo.delete = AsyncMock(return_value=True)

        assert await service.delete("doc-1") is True

        service._analysis_repo.delete_by_document.assert_awaited_once_with("doc-1")
        store.delete.assert_called_once_with("/srv/uploads/x.pdf")

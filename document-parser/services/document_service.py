"""Document service — file upload, storage, and preview orchestration.

Reaches the PDF through two ports: `PageRasterizer` renders a page,
`PdfInspector` counts pages and reads their sizes. The service decides which
page may be asked for and what an unreadable file means; the adapters open
the stored file by its path.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from domain.models import Document

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        DocumentRepository,
        PageRasterizer,
        PdfInspector,
    )
    from domain.value_objects import PageDetail

logger = logging.getLogger(__name__)


# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"

_UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming writes


class PageOutOfRangeError(Exception):
    """The page asked for is past the document's last page."""

    def __init__(self, page: int, page_count: int):
        super().__init__(f"Page {page} out of range (document has {page_count} pages)")


class PageNotFoundError(Exception):
    """The stored PDF has no such page (its page count was not known)."""

    def __init__(self, page: int):
        super().__init__(f"Page {page} not found")


class DocumentFileError(Exception):
    """The stored PDF could not be rendered or read.

    A missing file stays a `FileNotFoundError` and an I/O failure an
    `OSError`; this wraps whatever else the PDF library raised.
    """


@dataclass
class DocumentConfig:
    """Configuration values needed by DocumentService, extracted from settings."""

    upload_dir: str = "uploads"
    max_file_size_mb: int = 0
    max_page_count: int = 0


class DocumentService:
    """Orchestrates document upload, storage, and preview."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        config: DocumentConfig,
        *,
        rasterizer: PageRasterizer,
        pdf: PdfInspector,
    ):
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._config = config
        self._rasterizer = rasterizer
        self._pdf = pdf
        self._upload_dir = config.upload_dir
        self._max_file_size = (
            config.max_file_size_mb * 1024 * 1024 if config.max_file_size_mb > 0 else 0
        )
        self._max_page_count = config.max_page_count

    @property
    def max_file_size(self) -> int:
        return self._max_file_size

    @property
    def max_file_size_mb(self) -> int:
        return self._config.max_file_size_mb

    async def upload(self, filename: str, content_type: str, file_content: bytes) -> Document:
        """Save uploaded file to disk and persist metadata.

        Writes the file in fixed-size chunks to keep peak memory usage low,
        then counts the pages of the written file. Both are blocking and run
        in a worker thread so the FastAPI event loop stays free for other
        requests during large uploads. A PDF whose pages cannot be counted is
        still accepted, with an unknown page count.
        """
        if self._max_file_size > 0 and len(file_content) > self._max_file_size:
            raise ValueError(f"File too large (max {self._config.max_file_size_mb} MB)")

        if not file_content[:4].startswith(_PDF_MAGIC):
            raise ValueError("Invalid file: not a PDF document")

        ext = ".pdf"  # Content already validated as PDF
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(self._upload_dir, safe_name)

        # Disk write + page count — both blocking. Offload together so we
        # cross the thread boundary once instead of twice.
        page_count = await asyncio.to_thread(self._persist_and_count, file_path, file_content)

        if (
            self._max_page_count > 0
            and page_count is not None
            and page_count > self._max_page_count
        ):
            await asyncio.to_thread(os.unlink, file_path)
            raise ValueError(
                f"Too many pages ({page_count}). Maximum allowed: {self._max_page_count}"
            )

        doc = Document(
            filename=filename,
            content_type=content_type,
            file_size=len(file_content),
            page_count=page_count,
            storage_path=os.path.abspath(file_path),
        )
        await self._document_repo.insert(doc)
        return doc

    async def find_all(self) -> list[Document]:
        """Return all documents, newest first."""
        return await self._document_repo.find_all()

    async def find_by_id(self, doc_id: str) -> Document | None:
        """Find a document by its ID, or return None."""
        return await self._document_repo.find_by_id(doc_id)

    def resolve_storage_path(self, storage_path: str) -> Path:
        """Resolve a persisted upload path in either Docker or host development.

        Docker records `/app/uploads/...`, while a worktree started directly
        on the host stores the copied files under its configured upload dir.
        Keep the original path when it exists; otherwise only fall back to its
        basename inside that directory.
        """
        path = Path(storage_path)
        if path.is_file():
            return path
        fallback = Path(self._upload_dir).resolve() / path.name
        return fallback if fallback.is_file() else path

    async def delete(self, doc_id: str) -> bool:
        """Delete document file, associated analyses, and database record."""
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            return False

        # Delete associated analyses first (cascade)
        await self._analysis_repo.delete_by_document(doc_id)

        # Delete file from disk (only if inside upload dir)
        try:
            real_path = os.path.realpath(doc.storage_path)
            real_upload_dir = os.path.realpath(self._upload_dir)
            if real_path.startswith(real_upload_dir + os.sep) and os.path.exists(real_path):
                os.unlink(real_path)
            elif os.path.exists(doc.storage_path):
                logger.warning("Refused to delete file outside upload dir: %s", doc.storage_path)
        except FileNotFoundError:
            logger.info("File already removed: %s", doc.storage_path)
        except PermissionError:
            logger.error("Permission denied deleting file: %s", doc.storage_path)
        except OSError:
            logger.warning("Could not delete file: %s", doc.storage_path, exc_info=True)

        return await self._document_repo.delete(doc_id)

    async def render_preview(self, doc_id: str, *, page: int, dpi: int) -> bytes | None:
        """PNG of one page of a document, or None for an unknown document.

        Raises `PageOutOfRangeError` past the last page when the page count is
        known, `PageNotFoundError` when the PDF has no such page,
        `FileNotFoundError` when the file is gone, `OSError` when it cannot be
        read, and `DocumentFileError` when it cannot be rendered.
        """
        doc = await self._document_repo.find_by_id(doc_id)
        if doc is None:
            return None
        if doc.page_count and page > doc.page_count:
            raise PageOutOfRangeError(page, doc.page_count)
        try:
            # Resolving the path stats the disk and rendering runs poppler:
            # both off the event loop.
            return await asyncio.to_thread(self._render, doc.storage_path, page, dpi)
        except ValueError as exc:
            raise PageNotFoundError(page) from exc
        except OSError:
            raise
        except Exception as exc:
            raise DocumentFileError(f"Could not render page {page} of {doc_id}") from exc

    async def page_sizes(self, doc_id: str) -> list[PageDetail] | None:
        """Size of each page of a document's PDF, in points, without its
        elements (#352), or None for an unknown document.

        Lets the page preview reserve each page's box before any analysis.
        Raises `FileNotFoundError` when the file is gone, `OSError` when it
        cannot be read, and `DocumentFileError` when it is not a readable PDF.
        """
        doc = await self._document_repo.find_by_id(doc_id)
        if doc is None:
            return None
        try:
            return await asyncio.to_thread(self._read_page_sizes, doc.storage_path)
        except OSError:
            raise
        except Exception as exc:
            raise DocumentFileError(f"Could not read the pages of {doc_id}") from exc

    def _render(self, storage_path: str, page: int, dpi: int) -> bytes:
        path = str(self.resolve_storage_path(storage_path))
        return self._rasterizer.render_page(path, page=page, dpi=dpi)

    def _read_page_sizes(self, storage_path: str) -> list[PageDetail]:
        return self._pdf.page_sizes(str(self.resolve_storage_path(storage_path)))

    def _persist_and_count(self, file_path: str, file_content: bytes) -> int | None:
        """Write the uploaded bytes to disk and return the page count.

        Synchronous helper meant to be invoked through `asyncio.to_thread` so
        the chunked write loop and the PDF read never block the FastAPI event
        loop.
        """
        os.makedirs(self._upload_dir, exist_ok=True)
        with open(file_path, "wb") as f:
            for offset in range(0, len(file_content), _UPLOAD_CHUNK_SIZE):
                f.write(file_content[offset : offset + _UPLOAD_CHUNK_SIZE])
        return self._count_pages(file_path)

    def _count_pages(self, file_path: str) -> int | None:
        """Page count of the written file, None when the PDF cannot be read."""
        try:
            return self._pdf.page_count(file_path)
        except Exception as exc:
            logger.warning("Could not count the pages of %s: %s", file_path, exc)
            return None

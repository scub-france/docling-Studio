"""Document service — file upload, storage, and preview orchestration.

Reaches the uploaded file through `FileStorage`, which writes it, finds it
again and removes it, and the PDF through two ports: `PageRasterizer`
renders a page, `PdfInspector` counts pages and reads their sizes. The
service decides what may be stored, which page may be asked for, and what an
unreadable or unremovable file means; the adapters touch the disk.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.models import Document

if TYPE_CHECKING:
    from datetime import datetime

    from domain.ports import (
        AnalysisRepository,
        DocumentRepository,
        DocumentStoreLinkRepository,
        FileStorage,
        PageRasterizer,
        PdfInspector,
        StoreRepository,
    )
    from domain.value_objects import DocumentStoreLinkState, PageDetail

logger = logging.getLogger(__name__)


# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"


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
    """Configuration values needed by DocumentService, extracted from settings.

    Where the files go is the `FileStorage` adapter's business.
    """

    max_file_size_mb: int = 0
    max_page_count: int = 0


@dataclass(frozen=True)
class StoreLinkView:
    """A document's presence in one store (#283), named by the store's slug —
    its stable identity — or by its id when the store row is gone."""

    store: str
    state: DocumentStoreLinkState
    pushed_at: datetime | None


class DocumentService:
    """Orchestrates document upload, storage, and preview."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        config: DocumentConfig,
        *,
        files: FileStorage,
        rasterizer: PageRasterizer,
        pdf: PdfInspector,
        store_repo: StoreRepository | None = None,
        link_repo: DocumentStoreLinkRepository | None = None,
    ):
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._config = config
        self._files = files
        self._rasterizer = rasterizer
        self._pdf = pdf
        # Stores and their links (deprecated ingestion surface): without them
        # a document reads as pushed nowhere.
        self._store_repo = store_repo
        self._link_repo = link_repo
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
        """Store the uploaded file and persist its metadata.

        Stores the file under a fresh name, then counts the pages of the
        stored file. Both are blocking and run in a worker thread so the
        FastAPI event loop stays free for other requests during large
        uploads. A PDF whose pages cannot be counted is still accepted, with
        an unknown page count.
        """
        if self._max_file_size > 0 and len(file_content) > self._max_file_size:
            raise ValueError(f"File too large (max {self._config.max_file_size_mb} MB)")

        if not file_content[:4].startswith(_PDF_MAGIC):
            raise ValueError("Invalid file: not a PDF document")

        # Disk write + page count — both blocking. Offload together so we
        # cross the thread boundary once instead of twice.
        storage_path, page_count = await asyncio.to_thread(self._store_and_count, file_content)

        if (
            self._max_page_count > 0
            and page_count is not None
            and page_count > self._max_page_count
        ):
            await asyncio.to_thread(self._files.delete, storage_path)
            raise ValueError(
                f"Too many pages ({page_count}). Maximum allowed: {self._max_page_count}"
            )

        doc = Document(
            filename=filename,
            content_type=content_type,
            file_size=len(file_content),
            page_count=page_count,
            storage_path=storage_path,
        )
        await self._document_repo.insert(doc)
        return doc

    async def find_all(self) -> list[Document]:
        """Return all documents, newest first."""
        return await self._document_repo.find_all()

    async def find_by_id(self, doc_id: str) -> Document | None:
        """Find a document by its ID, or return None."""
        return await self._document_repo.find_by_id(doc_id)

    async def find_with_store_links(
        self, doc_id: str
    ) -> tuple[Document, list[StoreLinkView]] | None:
        """A document with the stores it was pushed to, or None if unknown."""
        doc = await self._document_repo.find_by_id(doc_id)
        if doc is None:
            return None
        return doc, await self._store_links(doc_id)

    async def _store_links(self, doc_id: str) -> list[StoreLinkView]:
        """Join `document_store_links` with `stores` so each link carries the
        store's slug rather than its opaque id. Empty when there is none."""
        if self._link_repo is None or self._store_repo is None:
            return []
        links = await self._link_repo.find_for_document(doc_id)
        if not links:
            return []
        # Resolve store_id → slug in one shot. `find_all()` is fine here —
        # store rows are O(1-10) in practice.
        slug_by_id = {store.id: store.slug for store in await self._store_repo.find_all()}
        return [
            StoreLinkView(
                store=slug_by_id.get(link.store_id, link.store_id),
                state=link.state,
                pushed_at=link.last_push_at,
            )
            for link in links
        ]

    async def delete(self, doc_id: str) -> bool:
        """Delete document file, associated analyses, and database record."""
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            return False

        # Delete associated analyses first (cascade)
        await self._analysis_repo.delete_by_document(doc_id)

        # Delete the file. The storage removes only what lies inside it; a
        # file that cannot be removed does not keep the record alive.
        try:
            await asyncio.to_thread(self._files.delete, doc.storage_path)
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
        path = self._files.resolve(storage_path)
        return self._rasterizer.render_page(path, page=page, dpi=dpi)

    def _read_page_sizes(self, storage_path: str) -> list[PageDetail]:
        return self._pdf.page_sizes(self._files.resolve(storage_path))

    def _store_and_count(self, file_content: bytes) -> tuple[str, int | None]:
        """Store the uploaded bytes; return their storage path and page count.

        Synchronous helper meant to be invoked through `asyncio.to_thread` so
        the write and the PDF read never block the FastAPI event loop. The
        content was checked to be a PDF, hence the suffix.
        """
        storage_path = self._files.save(file_content, suffix=".pdf")
        return storage_path, self._count_pages(storage_path)

    def _count_pages(self, file_path: str) -> int | None:
        """Page count of the written file, None when the PDF cannot be read."""
        try:
            return self._pdf.page_count(file_path)
        except Exception as exc:
            logger.warning("Could not count the pages of %s: %s", file_path, exc)
            return None

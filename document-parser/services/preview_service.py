"""Render and cache PDF previews, and read page sizes, behind ports."""

from __future__ import annotations

import asyncio
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING

from services.errors import ServiceError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from domain.ports import (
        DocumentFileStore,
        DocumentRepository,
        PageRasterizer,
        PdfInspector,
        PreviewImageCache,
    )
    from domain.value_objects import PageDetail

logger = logging.getLogger(__name__)


class PreviewDocumentNotFoundError(ServiceError):
    """The requested document does not exist."""

    http_status = 404

    def __init__(self) -> None:
        super().__init__("Document not found")


class PreviewPageOutOfRangeError(ServiceError):
    """The requested page exceeds the document's known page count."""

    http_status = 400


class PreviewPageNotFoundError(ServiceError):
    """Poppler rendered nothing for the requested page."""

    http_status = 404


class PreviewFileNotFoundError(ServiceError):
    """The document exists, but its PDF is not on disk."""

    http_status = 404

    def __init__(self) -> None:
        super().__init__("PDF file not found on disk")


class PreviewFileUnreadableError(ServiceError):
    """The PDF is on disk, but it could not be read or rendered."""

    http_status = 422


class PreviewService:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        files: DocumentFileStore,
        rasterizer: PageRasterizer,
        inspector: PdfInspector,
        cache: PreviewImageCache,
    ) -> None:
        self._documents = documents
        self._files = files
        self._rasterizer = rasterizer
        self._inspector = inspector
        self._cache = cache

    async def get_preview(self, doc_id: str, *, page: int, dpi: int, image_format: str) -> bytes:
        document = await self._documents.find_by_id(doc_id)
        if document is None:
            raise PreviewDocumentNotFoundError()
        if document.page_count and page > document.page_count:
            raise PreviewPageOutOfRangeError(
                f"Page {page} out of range (document has {document.page_count} pages)"
            )

        with _translate_pdf_read_errors(doc_id, failure="Failed to generate preview"):
            path = self._files.resolve(document.storage_path)
            size, mtime_ns = await asyncio.to_thread(self._files.read_fingerprint, path)
        key = (path, size, mtime_ns, page, dpi, image_format)
        image = self._cache.get(key)
        if image is None:
            with _translate_pdf_read_errors(doc_id, failure="Failed to generate preview"):
                image = await self._render(path, page=page, dpi=dpi, fmt=image_format.upper())
            self._cache.put(key, image)
        return image

    async def read_page_sizes(self, doc_id: str) -> list[PageDetail]:
        """Size of each page of the PDF, so the preview can lay out its pages
        before any analysis (#352)."""
        document = await self._documents.find_by_id(doc_id)
        if document is None:
            raise PreviewDocumentNotFoundError()
        with _translate_pdf_read_errors(doc_id, failure="Failed to read PDF file"):
            path = self._files.resolve(document.storage_path)
            return await asyncio.to_thread(self._inspector.read_page_sizes, path)

    async def _render(self, path: str, *, page: int, dpi: int, fmt: str) -> bytes:
        # Poppler opens the PDF by path: the file is never read whole (#398).
        try:
            return await asyncio.to_thread(
                self._rasterizer.render_page, path, page=page, dpi=dpi, fmt=fmt
            )
        except ValueError as exc:
            # The adapter's message names the server path: keep it out of the
            # HTTP detail.
            raise PreviewPageNotFoundError(f"Page {page} not found") from exc


@contextmanager
def _translate_pdf_read_errors(doc_id: str, *, failure: str) -> Iterator[None]:
    """Turn what the file store, rasterizer or inspector raise while reading
    `doc_id`'s PDF into the preview errors, `failure` being the detail of an
    unexpected one. Errors raised outside such a block are not PDF read
    errors: they stay unexpected, and the API answers 500."""
    try:
        yield
    except ServiceError:
        raise
    except FileNotFoundError as exc:
        raise PreviewFileNotFoundError() from exc
    except OSError as exc:
        logger.exception("I/O error reading the PDF of %s", doc_id)
        raise PreviewFileUnreadableError("Failed to read PDF file") from exc
    except Exception as exc:
        logger.exception("Unexpected error reading the PDF of %s", doc_id)
        raise PreviewFileUnreadableError(failure) from exc

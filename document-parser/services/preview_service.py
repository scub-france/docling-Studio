"""Render and cache PDF previews, and read page sizes, behind ports."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from services.errors import ServiceError

if TYPE_CHECKING:
    from pathlib import Path

    from domain.ports import DocumentFileLocator, PageRasterizer, PdfInspector, PreviewImageCache
    from domain.value_objects import PageDetail


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


class PreviewService:
    def __init__(
        self,
        *,
        documents: DocumentFileLocator,
        rasterizer: PageRasterizer,
        inspector: PdfInspector,
        cache: PreviewImageCache,
    ) -> None:
        self._documents = documents
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

        path = self._documents.resolve_storage_path(document.storage_path)
        stat = await asyncio.to_thread(path.stat)
        key = (str(path), stat.st_size, stat.st_mtime_ns, page, dpi, image_format)
        image = self._cache.get(key)
        if image is None:
            image = await self._render(path, page=page, dpi=dpi, fmt=image_format.upper())
            self._cache.put(key, image)
        return image

    async def read_page_sizes(self, doc_id: str) -> list[PageDetail]:
        """Size of each page of the PDF, so the preview can lay out its pages
        before any analysis (#352)."""
        document = await self._documents.find_by_id(doc_id)
        if document is None:
            raise PreviewDocumentNotFoundError()
        path = self._documents.resolve_storage_path(document.storage_path)
        return await asyncio.to_thread(self._inspector.read_page_sizes, str(path))

    async def _render(self, path: Path, *, page: int, dpi: int, fmt: str) -> bytes:
        # Poppler opens the PDF by path: the file is never read whole (#398).
        try:
            return await asyncio.to_thread(
                self._rasterizer.render_page, str(path), page=page, dpi=dpi, fmt=fmt
            )
        except ValueError as exc:
            # The adapter's message names the server path: keep it out of the
            # HTTP detail.
            raise PreviewPageNotFoundError(f"Page {page} not found") from exc

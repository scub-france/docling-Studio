"""Render and cache PDF previews behind one application operation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from services.document_service import DocumentService

if TYPE_CHECKING:
    from domain.ports import PreviewImageCache


class PreviewDocumentNotFoundError(Exception):
    """The requested document does not exist."""


class PreviewPageOutOfRangeError(ValueError):
    """The requested page exceeds the document's known page count."""


class PreviewService:
    def __init__(self, documents: DocumentService, cache: PreviewImageCache) -> None:
        self._documents = documents
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
            content = await asyncio.to_thread(path.read_bytes)
            image = await asyncio.to_thread(
                DocumentService.generate_preview,
                content,
                page=page,
                dpi=dpi,
                image_format=image_format.upper(),
            )
            self._cache.put(key, image)
        return image

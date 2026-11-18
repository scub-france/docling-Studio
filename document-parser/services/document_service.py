"""Document service — file upload, storage, and lookup."""

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
    from collections.abc import Callable
    from datetime import datetime

    from domain.ports import (
        AnalysisRepository,
        DocumentRepository,
        DocumentStoreLinkRepository,
        PdfInspector,
        StoreRepository,
    )
    from domain.value_objects import DocumentStoreLinkState

logger = logging.getLogger(__name__)


# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"

_UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming writes


@dataclass
class DocumentConfig:
    """Configuration values needed by DocumentService, extracted from settings."""

    upload_dir: str = "uploads"
    max_file_size_mb: int = 0
    max_page_count: int = 0


@dataclass(frozen=True)
class DocumentStoreLinkView:
    """A document's link to one store, named by the store's slug (#283)."""

    store: str
    state: DocumentStoreLinkState
    last_push_at: datetime | None


class DocumentService:
    """Orchestrates document upload, storage, and lookup."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        config: DocumentConfig,
        *,
        link_repo: DocumentStoreLinkRepository,
        store_repo: StoreRepository,
        pdf_inspector: PdfInspector,
    ):
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._link_repo = link_repo
        self._store_repo = store_repo
        self._pdf_inspector = pdf_inspector
        self._config = config
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

        Writes the file in fixed-size chunks to keep peak memory usage low.
        The blocking disk write and the page count (a poppler subprocess
        behind the inspector) are offloaded to a worker thread so the FastAPI
        event loop stays free for other requests during large uploads.
        """
        if self._max_file_size > 0 and len(file_content) > self._max_file_size:
            raise ValueError(f"File too large (max {self._config.max_file_size_mb} MB)")

        if not file_content[:4].startswith(_PDF_MAGIC):
            raise ValueError("Invalid file: not a PDF document")

        ext = ".pdf"  # Content already validated as PDF
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(self._upload_dir, safe_name)

        # Disk write + page count — both blocking. Offload together
        # so we cross the thread boundary once instead of twice.
        page_count = await asyncio.to_thread(
            _persist_and_count,
            self._upload_dir,
            file_path,
            file_content,
            self._pdf_inspector.count_pages_in_bytes,
        )

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

    async def find_with_store_links(
        self, doc_id: str
    ) -> tuple[Document, list[DocumentStoreLinkView]] | None:
        """A document with its per-store links, or None when it does not exist.

        Each link carries the store slug, the frontend's stable identity for a
        store, rather than the opaque store_id. No links gives an empty list.
        """
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            return None
        links = await self._link_repo.find_for_document(doc_id)
        if not links:
            return doc, []
        # Store rows are O(1-10) in practice: one `find_all` resolves every slug.
        stores = await self._store_repo.find_all()
        slug_by_id = {s.id: s.slug for s in stores}
        return doc, [
            DocumentStoreLinkView(
                store=slug_by_id.get(link.store_id, link.store_id),
                state=link.state,
                last_push_at=link.last_push_at,
            )
            for link in links
        ]

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


def _persist_and_count(
    upload_dir: str,
    file_path: str,
    file_content: bytes,
    count_pages: Callable[[bytes], int | None],
) -> int | None:
    """Write the uploaded bytes to disk and return the page count.

    Synchronous helper meant to be invoked through `asyncio.to_thread` so
    the chunked write loop and the page count never block the FastAPI
    event loop.
    """
    os.makedirs(upload_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        for offset in range(0, len(file_content), _UPLOAD_CHUNK_SIZE):
            f.write(file_content[offset : offset + _UPLOAD_CHUNK_SIZE])
    return count_pages(file_content)

"""Document service — file upload, storage, and lookup."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.models import Document

if TYPE_CHECKING:
    from datetime import datetime

    from domain.ports import (
        AnalysisRepository,
        CurrentAnalysisReader,
        DocumentFileStore,
        DocumentRepository,
        DocumentStoreLinkRepository,
        PdfInspector,
        StoreRepository,
    )
    from domain.value_objects import DocumentStoreLinkState


# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"


@dataclass
class DocumentConfig:
    """Configuration values needed by DocumentService, extracted from settings."""

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
        file_store: DocumentFileStore,
        current_analysis: CurrentAnalysisReader,
    ):
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._current = current_analysis
        self._link_repo = link_repo
        self._store_repo = store_repo
        self._pdf_inspector = pdf_inspector
        self._file_store = file_store
        self._config = config
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

        The file store writes the file in fixed-size chunks to keep peak
        memory usage low. The blocking disk write and the page count (a
        poppler subprocess behind the inspector) are offloaded to a worker
        thread so the FastAPI event loop stays free for other requests during
        large uploads.
        """
        if self._max_file_size > 0 and len(file_content) > self._max_file_size:
            raise ValueError(f"File too large (max {self._config.max_file_size_mb} MB)")

        if not file_content[:4].startswith(_PDF_MAGIC):
            raise ValueError("Invalid file: not a PDF document")

        ext = ".pdf"  # Content already validated as PDF
        safe_name = f"{uuid.uuid4()}{ext}"

        # Disk write + page count — both blocking. Offload together
        # so we cross the thread boundary once instead of twice.
        storage_path, page_count = await asyncio.to_thread(
            self._save_and_count, safe_name, file_content
        )

        if (
            self._max_page_count > 0
            and page_count is not None
            and page_count > self._max_page_count
        ):
            await asyncio.to_thread(self._file_store.discard, storage_path)
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

    async def find_current_analysis_id(self, doc_id: str) -> str | None:
        """The id of the document's current analysis (its active selection), or None."""
        return await self._current.find_current_analysis_id(doc_id)

    async def delete(self, doc_id: str) -> bool:
        """Delete document file, associated analyses, and database record."""
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            return False

        # Delete associated analyses first (cascade)
        await self._analysis_repo.delete_by_document(doc_id)

        # Delete file from disk (the store only deletes inside the upload dir)
        self._file_store.delete(doc.storage_path)

        return await self._document_repo.delete(doc_id)

    def _save_and_count(self, file_name: str, file_content: bytes) -> tuple[str, int | None]:
        """Write the uploaded bytes to disk and return where, with the page count.

        Synchronous helper meant to be invoked through `asyncio.to_thread` so
        the chunked write and the page count never block the FastAPI event
        loop.
        """
        storage_path = self._file_store.save(file_name, file_content)
        return storage_path, self._pdf_inspector.count_pages_in_bytes(file_content)

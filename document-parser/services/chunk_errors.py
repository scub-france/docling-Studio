"""Typed rejections of the chunk services, and the guard they all open with.

Shared by `ChunkService` (editing the chunkset), `ChunkPushService` (pushing
it to a store) and `DocumentTreeService` (the outline beside it), so they
live below all three rather than inside whichever needed them first — the
reason `navigation_errors` exists too. Each error carries the HTTP status
the API answers it with (`ServiceError`); an unknown document is the
backend's one `DocumentNotFoundError` (404).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from domain import chunk_editing
from services.errors import ServiceError
from services.navigation_errors import DocumentNotFoundError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from domain.models import Document
    from domain.ports import DocumentRepository


class ChunkServiceError(ServiceError):
    http_status = 400


class ChunkNotFoundError(ChunkServiceError):
    http_status = 404


class ChunkConflictError(ChunkServiceError):
    http_status = 409


class ChunkValidationError(ChunkServiceError):
    http_status = 400


# Why the domain refused an edit → the error the API answers it with.
_REFUSALS: dict[type[chunk_editing.ChunkEditingError], type[ChunkServiceError]] = {
    chunk_editing.InvalidChunkEditError: ChunkValidationError,
    chunk_editing.UnknownChunkError: ChunkNotFoundError,
    chunk_editing.NonContiguousMergeError: ChunkConflictError,
}


@contextmanager
def refusals_as_service_errors() -> Iterator[None]:
    """Answer a refusal of `domain.chunk_editing` with its chunk error."""
    try:
        yield
    except chunk_editing.ChunkEditingError as exc:
        raise _REFUSALS[type(exc)](str(exc)) from exc


async def require_document(documents: DocumentRepository, document_id: str) -> Document:
    """The document, or the shared 404 — the guard every chunk use case opens with."""
    doc = await documents.find_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document not found: {document_id}")
    return doc

"""Errors of the document chunk services, and the document guard they share.

`ChunkService`, `ChunkPushService` and `DocumentTreeService` answer the same
routes (`/api/documents/{id}/chunks/*`), so they raise one error family: the
router maps `ChunkServiceError` once. Kept apart from the services so none of
them imports another to reach it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.errors import ServiceError

if TYPE_CHECKING:
    from domain.ports import DocumentRepository


# `ServiceError` carries the http_status hint (#396).


class ChunkServiceError(ServiceError):
    http_status: int = 400


class ChunkNotFoundError(ChunkServiceError):
    http_status = 404


class DocumentNotFoundError(ChunkServiceError):
    http_status = 404


class ChunkConflictError(ChunkServiceError):
    http_status = 409


class ChunkValidationError(ChunkServiceError):
    http_status = 400


async def require_document(documents: DocumentRepository, document_id: str) -> None:
    """Raise `DocumentNotFoundError` when the document does not exist."""
    doc = await documents.find_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

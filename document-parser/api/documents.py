"""Document API router — upload, list, get, delete, preview."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from api.schemas import DocumentResponse
from services.document_service import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

_READ_CHUNK_SIZE = 64 * 1024  # 64 KB


def _get_service(request: Request) -> DocumentService:
    return request.app.state.document_service


ServiceDep = Annotated[DocumentService, Depends(_get_service)]


def _to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        created_at=str(doc.created_at),
        lifecycle_state=doc.lifecycle_state.value,
        lifecycle_state_at=(str(doc.lifecycle_state_at) if doc.lifecycle_state_at else None),
    )


@router.post("/upload", response_model=DocumentResponse, status_code=200)
async def upload(file: UploadFile, service: ServiceDep) -> DocumentResponse:
    """Upload a PDF document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Reject early if Content-Length exceeds limit (before reading body)
    _max = service.max_file_size
    _detail = f"File too large (max {service.max_file_size_mb} MB)"
    if _max > 0 and file.size and file.size > _max:
        raise HTTPException(status_code=413, detail=_detail)

    # Read in chunks to avoid holding the full upload in a single allocation
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_READ_CHUNK_SIZE):
        total += len(chunk)
        if _max > 0 and total > _max:
            raise HTTPException(status_code=413, detail=_detail)
        chunks.append(chunk)
    content = b"".join(chunks)

    try:
        doc = await service.upload(
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
            file_content=content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _to_response(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(service: ServiceDep) -> list[DocumentResponse]:
    """List all documents."""
    docs = await service.find_all()
    return [_to_response(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, service: ServiceDep) -> DocumentResponse:
    """Get a single document."""
    doc = await service.find_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_response(doc)


@router.delete("/{doc_id}", status_code=204, response_model=None)
async def delete_document(doc_id: str, service: ServiceDep) -> None:
    """Delete a document and its file."""
    deleted = await service.delete(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{doc_id}/preview")
async def preview(
    doc_id: str,
    service: ServiceDep,
    page: int = Query(1, ge=1),
    dpi: int = Query(150, ge=72, le=300),
) -> Response:
    """Generate a PNG preview of a specific PDF page."""
    doc = await service.find_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.page_count and page > doc.page_count:
        raise HTTPException(
            status_code=400,
            detail=f"Page {page} out of range (document has {doc.page_count} pages)",
        )

    try:
        # File read + PDF rasterisation are both blocking; offload to a
        # worker thread so the event loop stays free for other requests.
        file_content = await asyncio.to_thread(Path(doc.storage_path).read_bytes)
        png_bytes = await asyncio.to_thread(
            DocumentService.generate_preview, file_content, page=page, dpi=dpi
        )
        return Response(content=png_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="PDF file not found on disk") from exc
    except OSError as exc:
        logger.exception("I/O error generating preview for %s", doc_id)
        raise HTTPException(status_code=422, detail="Failed to read PDF file") from exc
    except Exception as exc:
        logger.exception("Unexpected error generating preview for %s", doc_id)
        raise HTTPException(status_code=422, detail="Failed to generate preview") from exc

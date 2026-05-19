"""Document chunks API router (#256).

Exposes the canonical doc-centric chunkset (CRUD + tree + rechunk + diff
+ push). Distinct from `/api/analyses/{id}/...` which operates on
ephemeral analysis runs (StudioPage / OCR Debug).

All routes mount under `/api/documents/{doc_id}/...`. The router
delegates to `ChunkService` — no direct repo / persistence access.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.schemas import (
    AddChunkRequest,
    ChunkBboxResponse,
    ChunkDiffResponse,
    ChunkDocItemResponse,
    ChunkPushEntryResponse,
    ChunkPushListResponse,
    DocChunkResponse,
    DocRechunkRequest,
    DocTreeNodeResponse,
    MergeChunksRequest,
    PushChunksRequest,
    PushChunksResponse,
    SplitChunkRequest,
    UpdateChunkRequest,
)
from services.chunk_service import (
    ChunkService,
    ChunkServiceError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_service(request: Request) -> ChunkService:
    svc = getattr(request.app.state, "chunk_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Chunk service not available")
    return svc


ServiceDep = Annotated[ChunkService, Depends(_get_service)]


def _to_response(chunk) -> DocChunkResponse:
    return DocChunkResponse(
        id=chunk.id,
        doc_id=chunk.document_id,
        sequence=chunk.sequence,
        text=chunk.text,
        headings=list(chunk.headings),
        source_page=chunk.source_page,
        token_count=chunk.token_count,
        bboxes=[ChunkBboxResponse(page=b.page, bbox=list(b.bbox)) for b in chunk.bboxes],
        doc_items=[
            ChunkDocItemResponse(self_ref=di.self_ref, label=di.label) for di in chunk.doc_items
        ],
        created_at=str(chunk.created_at),
        updated_at=str(chunk.updated_at),
    )


def _raise_for(error: ChunkServiceError) -> None:
    raise HTTPException(status_code=error.http_status, detail=str(error))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("/{doc_id}/chunks", response_model=list[DocChunkResponse])
async def list_chunks(doc_id: str, service: ServiceDep) -> list[DocChunkResponse]:
    """List the canonical chunkset for a document, ordered by sequence."""
    try:
        chunks = await service.list_chunks(doc_id)
    except ChunkServiceError as e:
        _raise_for(e)
    return [_to_response(c) for c in chunks]


@router.post("/{doc_id}/chunks", response_model=DocChunkResponse, status_code=201)
async def add_chunk(doc_id: str, body: AddChunkRequest, service: ServiceDep) -> DocChunkResponse:
    """Insert a new chunk (optionally after `afterId`)."""
    if not body.text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        chunk = await service.add_chunk(doc_id, text=body.text, after_id=body.after_id)
    except ChunkServiceError as e:
        _raise_for(e)
    return _to_response(chunk)


@router.patch("/{doc_id}/chunks/{chunk_id}", response_model=DocChunkResponse)
async def update_chunk(
    doc_id: str,
    chunk_id: str,
    body: UpdateChunkRequest,
    service: ServiceDep,
) -> DocChunkResponse:
    """Update a chunk's text or title (mapped to first heading)."""
    if body.text is None and body.title is None:
        raise HTTPException(status_code=400, detail="text or title is required")
    headings: list[str] | None = None
    if body.title is not None:
        headings = [body.title] if body.title else []
    try:
        chunk = await service.update_chunk(doc_id, chunk_id, text=body.text, headings=headings)
    except ChunkServiceError as e:
        _raise_for(e)
    return _to_response(chunk)


@router.delete("/{doc_id}/chunks/{chunk_id}", status_code=204, response_model=None)
async def delete_chunk(doc_id: str, chunk_id: str, service: ServiceDep) -> None:
    """Soft-delete a chunk."""
    try:
        await service.delete_chunk(doc_id, chunk_id)
    except ChunkServiceError as e:
        _raise_for(e)


@router.post("/{doc_id}/chunks/{chunk_id}/split", response_model=list[DocChunkResponse])
async def split_chunk(
    doc_id: str,
    chunk_id: str,
    body: SplitChunkRequest,
    service: ServiceDep,
) -> list[DocChunkResponse]:
    """Split a chunk in two at `cursorOffset` characters."""
    try:
        chunks = await service.split_chunk(doc_id, chunk_id, body.cursor_offset)
    except ChunkServiceError as e:
        _raise_for(e)
    return [_to_response(c) for c in chunks]


@router.post("/{doc_id}/chunks/merge", response_model=DocChunkResponse)
async def merge_chunks(
    doc_id: str, body: MergeChunksRequest, service: ServiceDep
) -> DocChunkResponse:
    """Merge contiguous chunks into one. Order in `ids` is irrelevant — the
    service sorts by sequence."""
    try:
        merged = await service.merge_chunks(doc_id, body.ids)
    except ChunkServiceError as e:
        _raise_for(e)
    return _to_response(merged)


# ---------------------------------------------------------------------------
# Rechunk + tree + diff + push
# ---------------------------------------------------------------------------


@router.post("/{doc_id}/rechunk", response_model=list[DocChunkResponse])
async def rechunk_document(
    doc_id: str,
    body: DocRechunkRequest | None,
    service: ServiceDep,
) -> list[DocChunkResponse]:
    """Re-run the chunker on the latest analysis JSON; replace canonical."""
    options = body.chunking_options.model_dump() if body and body.chunking_options else None
    try:
        chunks = await service.rechunk_document(doc_id, options)
    except ChunkServiceError as e:
        _raise_for(e)
    return [_to_response(c) for c in chunks]


@router.get("/{doc_id}/tree", response_model=list[DocTreeNodeResponse])
async def get_tree(doc_id: str, service: ServiceDep) -> list[DocTreeNodeResponse]:
    """Outline of the document built from the latest completed analysis.

    Returns `[]` if no analysis is available yet.
    """
    try:
        tree = await service.get_tree(doc_id)
    except ChunkServiceError as e:
        _raise_for(e)
    return [DocTreeNodeResponse(**node) for node in tree]


@router.get("/{doc_id}/diff", response_model=list[ChunkDiffResponse])
async def diff_against_store(
    doc_id: str,
    service: ServiceDep,
    store: str = Query(..., min_length=1),
) -> list[ChunkDiffResponse]:
    """Diff the canonical chunkset against the last push to `store`."""
    try:
        diffs = await service.diff_against_store(doc_id, store)
    except ChunkServiceError as e:
        _raise_for(e)
    return [ChunkDiffResponse(**d) for d in diffs]


@router.post("/{doc_id}/chunks/push", response_model=PushChunksResponse)
async def push_chunks(
    doc_id: str,
    body: PushChunksRequest,
    service: ServiceDep,
) -> PushChunksResponse:
    """Push the canonical chunkset to a store and record a `ChunkPush`."""
    try:
        result = await service.push_to_store(doc_id, body.store)
    except ChunkServiceError as e:
        _raise_for(e)
    return PushChunksResponse(
        job_id=result["jobId"],
        summary=result["summary"],
    )


@router.get("/{doc_id}/chunks/pushes", response_model=ChunkPushListResponse)
async def list_chunk_pushes(
    doc_id: str,
    service: ServiceDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ChunkPushListResponse:
    """Newest-first push history for the document (#283).

    Drives the Ingest tab's history list. Pagination is conservative
    (`limit<=200`) — the UI lists 20-50 entries per page; larger pulls
    are unusual and cap the response size anyway.
    """
    try:
        payload = await service.list_pushes(doc_id, limit=limit, offset=offset)
    except ChunkServiceError as e:
        _raise_for(e)
    return ChunkPushListResponse(
        items=[ChunkPushEntryResponse(**entry) for entry in payload["items"]],
        total=payload["total"],
        limit=payload["limit"],
        offset=payload["offset"],
    )

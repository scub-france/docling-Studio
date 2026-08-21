"""Ingestion API router — trigger and manage vector ingestion pipeline."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from api import deps  # noqa: TC001
from api.schemas import (
    IngestionResponse,
    IngestionStatusResponse,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/{analysis_id}", response_model=IngestionResponse)
async def ingest_analysis(
    analysis_id: str,
    ingestion: deps.IngestionServiceDep,
    analysis: deps.AnalysisServiceDep,
) -> IngestionResponse:
    """Ingest a completed analysis into the vector index.

    Takes the chunks from an existing analysis, embeds them,
    and indexes them into OpenSearch.
    """
    job = await analysis.find_by_id(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if job.status.value != "COMPLETED":
        raise HTTPException(status_code=400, detail="Analysis is not completed")
    if not job.chunks_json:
        raise HTTPException(status_code=400, detail="Analysis has no chunks — run chunking first")

    try:
        result = await ingestion.ingest(
            doc_id=job.document_id,
            filename=job.document_filename or "unknown",
            chunks_json=job.chunks_json,
        )
    except Exception as e:
        logger.exception("Ingestion failed for analysis %s", analysis_id)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}") from e

    return IngestionResponse(
        doc_id=result.doc_id,
        chunks_indexed=result.chunks_indexed,
        embedding_dimension=result.embedding_dimension,
    )


@router.delete("/{doc_id}", status_code=204, response_model=None)
async def delete_ingested_document(doc_id: str, ingestion: deps.IngestionServiceDep) -> None:
    """Delete all indexed chunks for a document."""
    await ingestion.delete_document(doc_id)


@router.get("/status", response_model=IngestionStatusResponse)
async def ingestion_status(state: deps.AppStateDep) -> IngestionStatusResponse:
    """Check if the ingestion pipeline is available and OpenSearch is connected."""
    # Reads the slot directly rather than through `IngestionServiceDep`: this
    # endpoint reports absence as `available: false`, it does not 503 on it.
    svc = state.ingestion_service
    if svc is None:
        return IngestionStatusResponse(available=False, opensearch_connected=False)

    connected = await svc.ping()
    return IngestionStatusResponse(available=True, opensearch_connected=connected)


@router.get("/search", response_model=SearchResponse)
async def search_chunks(
    ingestion: deps.IngestionServiceDep,
    q: str = Query(..., min_length=1, description="Search query"),
    doc_id: str | None = Query(None, description="Filter by document ID"),
    k: int = Query(20, ge=1, le=100, description="Max results"),
) -> SearchResponse:
    """Full-text search across indexed chunks.

    Returns matching chunks with content and metadata.
    Optionally filter by document ID.
    """
    results = await ingestion.search_fulltext(q, k=k, doc_id=doc_id)
    items = [
        SearchResultItem(
            doc_id=r.chunk.doc_id,
            filename=r.chunk.filename,
            content=r.chunk.content,
            chunk_index=r.chunk.chunk_index,
            page_number=r.chunk.page_number,
            score=r.score,
            headings=r.chunk.headings,
        )
        for r in results
    ]
    return SearchResponse(results=items, total=len(items), query=q)

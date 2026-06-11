"""Shared FastAPI dependencies backed by `app.state`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from domain.ports import (
    AnalysisRepository,
    DocumentStoreLinkRepository,
    ReasoningRunner,
    StoreRepository,
)
from services.analysis_service import AnalysisService
from services.chunk_service import ChunkService
from services.document_service import DocumentService
from services.graph_service import GraphService
from services.ingestion_service import IngestionService
from services.store_service import StoreService
from services.version_service import VersionService


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


def get_store_service(request: Request) -> StoreService:
    return request.app.state.store_service


StoreServiceDep = Annotated[StoreService, Depends(get_store_service)]


def get_chunk_service(request: Request) -> ChunkService:
    svc = getattr(request.app.state, "chunk_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Chunk service not available")
    return svc


ChunkServiceDep = Annotated[ChunkService, Depends(get_chunk_service)]


def get_version_service(request: Request) -> VersionService:
    svc = getattr(request.app.state, "version_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Version service not available")
    return svc


VersionServiceDep = Annotated[VersionService, Depends(get_version_service)]


def get_ingestion_service(request: Request) -> IngestionService:
    svc = request.app.state.ingestion_service
    if svc is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion not available (EMBEDDING_URL and OPENSEARCH_URL required)",
        )
    return svc


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_graph_service(request: Request) -> GraphService:
    svc = getattr(request.app.state, "graph_service", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="GraphService not wired")
    return svc


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]


def get_reasoning_runner(request: Request) -> ReasoningRunner | None:
    return getattr(request.app.state, "reasoning_runner", None)


ReasoningRunnerDep = Annotated[ReasoningRunner | None, Depends(get_reasoning_runner)]


def get_analysis_repo(request: Request) -> AnalysisRepository:
    return request.app.state.analysis_repo


AnalysisRepoDep = Annotated[AnalysisRepository, Depends(get_analysis_repo)]


def get_store_repo(request: Request) -> StoreRepository:
    return request.app.state.store_repo


StoreRepoDep = Annotated[StoreRepository, Depends(get_store_repo)]


def get_document_store_link_repo(request: Request) -> DocumentStoreLinkRepository:
    return request.app.state.document_store_link_repo


DocumentStoreLinkRepoDep = Annotated[
    DocumentStoreLinkRepository, Depends(get_document_store_link_repo)
]

"""Shared FastAPI dependencies, resolved from the typed `AppState` container.

Each accessor narrows one optional slot of `api.state.AppState` and raises the
status that endpoint documents when the subsystem is not wired — so routers
receive a non-optional service and never touch `app.state` themselves.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from api.state import AppState, get_app_state, require
from domain.ports import DocumentStoreLinkRepository, StoreRepository
from services.analysis_edit_service import AnalysisEditService
from services.analysis_service import AnalysisService
from services.app_config_service import AppConfigService
from services.chunk_service import ChunkService
from services.document_service import DocumentService
from services.export_service import ExportService
from services.graph_service import GraphService
from services.ingestion_service import IngestionService
from services.reasoning_service import ReasoningService
from services.store_service import StoreService
from services.version_service import VersionService

AppStateDep = Annotated[AppState, Depends(get_app_state)]


def get_document_service(state: AppStateDep) -> DocumentService:
    return require(state.document_service, detail="Document service not available")


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_analysis_service(state: AppStateDep) -> AnalysisService:
    return require(state.analysis_service, detail="Analysis service not available")


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


def get_analysis_edit_service(state: AppStateDep) -> AnalysisEditService:
    return require(state.analysis_edit_service, detail="Analysis editor not available")


AnalysisEditServiceDep = Annotated[AnalysisEditService, Depends(get_analysis_edit_service)]


def get_store_service(state: AppStateDep) -> StoreService:
    return require(state.store_service, detail="Store service not available")


StoreServiceDep = Annotated[StoreService, Depends(get_store_service)]


def get_chunk_service(state: AppStateDep) -> ChunkService:
    return require(state.chunk_service, detail="Chunk service not available")


ChunkServiceDep = Annotated[ChunkService, Depends(get_chunk_service)]


def get_version_service(state: AppStateDep) -> VersionService:
    return require(state.version_service, detail="Version service not available")


VersionServiceDep = Annotated[VersionService, Depends(get_version_service)]


def get_ingestion_service(state: AppStateDep) -> IngestionService:
    return require(
        state.ingestion_service,
        detail="Ingestion not available (EMBEDDING_URL and OPENSEARCH_URL required)",
    )


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_graph_service(state: AppStateDep) -> GraphService:
    return require(state.graph_service, detail="GraphService not wired", status_code=500)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]


def get_export_service(state: AppStateDep) -> ExportService:
    return require(state.export_service, detail="Export service not available")


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]


def get_store_repo(state: AppStateDep) -> StoreRepository:
    return require(state.store_repo, detail="Store repository not available")


StoreRepoDep = Annotated[StoreRepository, Depends(get_store_repo)]


def get_document_store_link_repo(state: AppStateDep) -> DocumentStoreLinkRepository:
    return require(
        state.document_store_link_repo, detail="Document/store link repository not available"
    )


DocumentStoreLinkRepoDep = Annotated[
    DocumentStoreLinkRepository, Depends(get_document_store_link_repo)
]


def get_reasoning_service(state: AppStateDep) -> ReasoningService:
    return require(state.reasoning_service, detail="ReasoningService not wired", status_code=500)


ReasoningServiceDep = Annotated[ReasoningService, Depends(get_reasoning_service)]


def get_app_config_service(state: AppStateDep) -> AppConfigService:
    return require(state.app_config_service, detail="App config service not available")


AppConfigServiceDep = Annotated[AppConfigService, Depends(get_app_config_service)]

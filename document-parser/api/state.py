"""Typed application state container (#306 review).

FastAPI's `app.state` is an untyped namespace: every read is a `getattr` that
returns `Any`, so a typo surfaces as an `AttributeError` at request time and no
checker can help. This module replaces that with a single frozen `AppState`
holding the wired services, published once on `app.state.container` by
`bootstrap.AppStateBuilder`, and read through the typed `get_app_state`
dependency.

Fields are `X | None` because state is legitimately partial: the container is
absent before wiring (tests that mount one router), and some subsystems are
genuinely optional at runtime (`ingestion_service` without `EMBEDDING_URL`,
`reasoning_runner` when reasoning is off). `api.deps` narrows each one and
raises the endpoint's documented status when it is missing, so routers keep
receiving non-optional services.

The container is immutable on purpose: runtime rewiring (#317's hot reasoning
rebuild) publishes a *new* container via `dataclasses.replace`, a single atomic
rebind. In-flight requests keep the container they resolved and finish on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        DocumentStoreLinkRepository,
        ReasoningRunner,
        StoreRepository,
    )
    from services.analysis_service import AnalysisService
    from services.app_config_service import AppConfigService
    from services.chunk_service import ChunkService
    from services.document_service import DocumentService
    from services.document_tools import DocumentTools
    from services.export_service import ExportService
    from services.graph_service import GraphService
    from services.ingestion_service import IngestionService
    from services.reasoning_service import ReasoningService
    from services.store_service import StoreService
    from services.version_service import VersionService


@dataclass(frozen=True)
class AppState:
    """Everything the HTTP layer may reach for, wired at boot.

    Only what is consumed outside the composition root lives here — pure
    wiring intermediates (converter, chunker, tree reader, graph driver,
    backend resolver) stay locals of the builder.
    """

    # Repositories reached directly by the API layer.
    analysis_repo: AnalysisRepository | None = None
    store_repo: StoreRepository | None = None
    document_store_link_repo: DocumentStoreLinkRepository | None = None

    # Use-case services.
    document_service: DocumentService | None = None
    analysis_service: AnalysisService | None = None
    export_service: ExportService | None = None
    store_service: StoreService | None = None
    chunk_service: ChunkService | None = None
    graph_service: GraphService | None = None
    version_service: VersionService | None = None
    ingestion_service: IngestionService | None = None
    # Document navigation (map / read / cite / show) — consumed by the MCP
    # adapter, and by the HTTP layer the day it grows an outline route.
    document_tools: DocumentTools | None = None
    reasoning_service: ReasoningService | None = None
    app_config_service: AppConfigService | None = None

    # Reasoning runner — read by `/api/health` and swapped by the runtime
    # config service (#317); kept beside the service it backs.
    reasoning_runner: ReasoningRunner | None = None


def get_app_state(request: Request) -> AppState:
    """Typed accessor for the wired container.

    Raises 503 when nothing was published — the app is being served before (or
    without) `AppStateBuilder`, which is a wiring bug rather than a user error.
    """
    state = getattr(request.app.state, "container", None)
    if state is None:
        raise HTTPException(status_code=503, detail="Application state not wired")
    return state


def require[T](value: T | None, *, detail: str, status_code: int = 503) -> T:
    """Narrow an optional slot to its service, or fail with the documented status."""
    if value is None:
        raise HTTPException(status_code=status_code, detail=detail)
    return value

"""Docling Studio — unified FastAPI backend.

Single service providing document management (upload, CRUD), analysis
orchestration (async Docling processing), and PDF preview — all backed
by SQLite.

Conversion engine is selected via CONVERSION_ENGINE env var:
- "local"  → Docling runs in-process as a Python library (default)
- "remote" → delegates to a Docling Serve instance via HTTP

Wiring lives in `bootstrap.AppStateBuilder`, which publishes the typed
`AppState` container this module's lifespan installs on `app.state`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.analyses import router as analyses_router
from api.config import router as config_router
from api.document_chunks import router as document_chunks_router
from api.document_versions import router as document_versions_router
from api.documents import router as documents_router
from api.graph import router as graph_router
from api.ingestion import router as ingestion_router
from api.reasoning import router as reasoning_router
from api.schemas import HealthResponse
from api.state import AppState
from api.stores import router as stores_router
from bootstrap import AppStateBuilder
from bootstrap.mcp_mount import mount_mcp_server
from infra.rate_limiter import RateLimiterMiddleware
from infra.settings import settings
from persistence.database import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    builder = AppStateBuilder(publish=lambda state: setattr(app.state, "container", state))
    state = await builder.build()

    # Mounted conditionally: without an ingestion service every route would
    # 503, so the surface stays out of OpenAPI entirely.
    if state.ingestion_service is not None:
        app.include_router(ingestion_router)
        logger.info("Ingestion router mounted")

    async with AsyncExitStack() as stack:
        # The MCP streamable-HTTP transport needs its session manager running
        # for the lifetime of the app. It is created at import time (see the
        # `mount_mcp_server` call below) because the ASGI route must exist
        # before the first request; entering it here is what starts it.
        if _mcp_session is not None:
            await stack.enter_async_context(_mcp_session)
        try:
            yield
        finally:
            # Drain both backend pools (#279). `close_driver` drains the Neo4j
            # pool (every (uri, user) entry, not just the env-based one); the
            # OpenSearch pool is drained explicitly.
            from infra.neo4j import close_driver
            from infra.opensearch_pool import get_pool as get_opensearch_pool

            await close_driver()
            await get_opensearch_pool().close_all()


app = FastAPI(
    title="Docling Studio",
    description="Document analysis studio powered by Docling",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
if settings.rate_limit_rpm > 0:
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_window=settings.rate_limit_rpm,
        window_seconds=60,
    )

app.include_router(documents_router)
app.include_router(document_chunks_router)
app.include_router(analyses_router)
app.include_router(stores_router)
# Document versions (#267) — workspace History timeline.
app.include_router(document_versions_router)
# Graph view — mounted regardless; individual requests 503 if Neo4j is absent.
app.include_router(graph_router)
# Live reasoning (#303). Mounted unconditionally so the route is
# introspectable in OpenAPI; the handler 503s when reasoning is off.
app.include_router(reasoning_router)
# Runtime config (#317) — admin panel read/write over the reasoning knobs.
app.include_router(config_router)

# MCP document server (read-only agent surface) — mounted at import time so
# the ASGI route and its session manager exist before the first request; the
# lifespan above enters the returned context. `None` when MCP_ENABLED is off
# or the optional SDK is absent, in which case nothing is mounted at all.
_mcp_session = mount_mcp_server(app)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint — verifies database connectivity."""
    db_status = "ok"
    try:
        async with get_connection() as db:
            await db.execute("SELECT 1")
    except Exception:
        db_status = "error"
        logger.warning("Health check: database unreachable", exc_info=True)

    # Tolerates a missing container: the app is importable (and this endpoint
    # answerable) before lifespan has run, which is how the API tests mount it.
    state: AppState = getattr(app.state, "container", None) or AppState()
    runner = state.reasoning_runner
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=settings.app_version,
        engine=settings.conversion_engine,
        deployment_mode=settings.deployment_mode,
        database=db_status,
        max_page_count=settings.max_page_count if settings.max_page_count > 0 else None,
        max_file_size_mb=settings.max_file_size_mb if settings.max_file_size_mb > 0 else None,
        max_paste_image_size_mb=(
            settings.max_paste_image_size_mb if settings.max_paste_image_size_mb > 0 else None
        ),
        paste_allowed_image_types=settings.paste_allowed_image_types,
        ingestion_available=state.ingestion_service is not None,
        # True when the runner is wired and reports itself available. Actual
        # Ollama reachability is checked lazily at call time so health checks
        # never block on the LLM host. Follows #317 runtime rebuilds.
        reasoning_available=runner is not None and runner.is_available,
        # 0.6.1 — Surface flags (#257).
        studio_mode_enabled=settings.studio_mode_enabled,
        rag_pipeline_enabled=settings.rag_pipeline_enabled,
        # 0.6.0 — RAG-pipeline sub-flags (#210, renamed in #257).
        inspect_mode_enabled=settings.inspect_mode_enabled,
        linked_mode_enabled=settings.linked_mode_enabled,
    )

"""Docling Studio — unified FastAPI backend.

Single service providing document management (upload, CRUD), analysis
orchestration (async Docling processing), and PDF preview — all backed
by SQLite.

Conversion engine is selected via CONVERSION_ENGINE env var:
- "local"  → Docling runs in-process as a Python library (default)
- "remote" → delegates to a Docling Serve instance via HTTP
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.analyses import router as analyses_router
from api.documents import router as documents_router
from api.ingestion import router as ingestion_router
from api.schemas import HealthResponse
from infra.rate_limiter import RateLimiterMiddleware
from infra.settings import settings
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.database import get_connection, init_db
from persistence.document_repo import SqliteDocumentRepository
from services.analysis_service import AnalysisConfig, AnalysisService
from services.document_service import DocumentConfig, DocumentService
from services.ingestion_service import IngestionConfig, IngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _build_converter():
    """Build the converter adapter based on configuration."""
    if settings.conversion_engine == "remote":
        from infra.serve_converter import ServeConverter

        logger.info("Using remote Docling Serve at %s", settings.docling_serve_url)
        return ServeConverter(
            base_url=settings.docling_serve_url,
            api_key=settings.docling_serve_api_key,
            timeout=settings.conversion_timeout,
        )
    else:
        from infra.local_converter import LocalConverter

        logger.info("Using local Docling converter")
        return LocalConverter()


def _build_chunker():
    """Build the chunker adapter.

    Uses LocalChunker in all modes — in remote mode it chunks the
    DoclingDocument JSON returned by Docling Serve, so docling-core
    (lightweight) is the only local dependency needed.
    """
    from infra.local_chunker import LocalChunker

    return LocalChunker()


def _build_repos() -> tuple[SqliteDocumentRepository, SqliteAnalysisRepository]:
    return SqliteDocumentRepository(), SqliteAnalysisRepository()


def _build_analysis_service(
    document_repo: SqliteDocumentRepository,
    analysis_repo: SqliteAnalysisRepository,
    neo4j_driver=None,
) -> AnalysisService:
    converter = _build_converter()
    chunker = _build_chunker()
    config = AnalysisConfig(
        default_table_mode=settings.default_table_mode,
        batch_page_size=settings.batch_page_size,
    )
    return AnalysisService(
        converter=converter,
        analysis_repo=analysis_repo,
        document_repo=document_repo,
        chunker=chunker,
        conversion_timeout=settings.conversion_timeout,
        max_concurrent=settings.max_concurrent_analyses,
        config=config,
        neo4j_driver=neo4j_driver,
    )


async def _init_neo4j():
    """Initialize the Neo4j driver and bootstrap schema — skip if not configured."""
    if not settings.neo4j_uri:
        logger.info("Neo4j disabled (NEO4J_URI not set)")
        return None

    if settings.neo4j_password == "changeme":
        # The dev compose stack ships with "changeme" so `docker compose up`
        # works immediately. Anyone running the backend against a non-dev
        # Neo4j with this password almost certainly forgot to override it.
        logger.warning(
            "Neo4j is configured with the dev default password 'changeme'. "
            "Override NEO4J_PASSWORD before deploying outside localhost."
        )

    from infra.neo4j import bootstrap_schema, get_driver

    try:
        neo = await get_driver(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        await bootstrap_schema(neo)
        logger.info("Neo4j ready (uri=%s)", settings.neo4j_uri)
        return neo
    except Exception:
        logger.exception("Neo4j init failed — continuing without graph storage")
        return None


def _build_ingestion_service(neo4j_driver=None) -> IngestionService | None:
    """Build the ingestion service — only if embedding + opensearch are configured."""
    if not settings.embedding_url or not settings.opensearch_url:
        logger.info("Ingestion disabled (EMBEDDING_URL or OPENSEARCH_URL not set)")
        return None

    from infra.embedding_client import EmbeddingClient
    from infra.opensearch_store import OpenSearchStore

    embedding = EmbeddingClient(settings.embedding_url)
    vector_store = OpenSearchStore(
        settings.opensearch_url,
        default_limit=settings.opensearch_default_limit,
    )
    config = IngestionConfig(
        embedding_dimension=settings.embedding_dimension,
    )
    logger.info(
        "Ingestion enabled (embedding=%s, opensearch=%s)",
        settings.embedding_url,
        settings.opensearch_url,
    )
    return IngestionService(embedding, vector_store, config, neo4j_driver=neo4j_driver)


def _build_document_service(
    document_repo: SqliteDocumentRepository,
    analysis_repo: SqliteAnalysisRepository,
) -> DocumentService:
    config = DocumentConfig(
        upload_dir=settings.upload_dir,
        max_file_size_mb=settings.max_file_size_mb,
        max_page_count=settings.max_page_count,
    )
    return DocumentService(
        document_repo=document_repo,
        analysis_repo=analysis_repo,
        config=config,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    document_repo, analysis_repo = _build_repos()
    # Exposed on app.state so routers that need direct repo access (e.g. the
    # reasoning-graph endpoint, which reads `document_json` from SQLite to
    # build the graph without touching Neo4j) can reach them without going
    # through a service.
    app.state.analysis_repo = analysis_repo
    app.state.document_repo = document_repo
    app.state.neo4j = await _init_neo4j()
    app.state.analysis_service = _build_analysis_service(
        document_repo, analysis_repo, neo4j_driver=app.state.neo4j
    )
    app.state.document_service = _build_document_service(document_repo, analysis_repo)
    ingestion_service = _build_ingestion_service(neo4j_driver=app.state.neo4j)
    app.state.ingestion_service = ingestion_service
    if ingestion_service is not None:
        app.include_router(ingestion_router)
        logger.info("Ingestion router mounted")
    logger.info("Docling Studio backend ready (engine=%s)", settings.conversion_engine)
    try:
        yield
    finally:
        if app.state.neo4j is not None:
            from infra.neo4j import close_driver

            await close_driver()


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
app.include_router(analyses_router)

# Graph view — mounted regardless; individual requests 503 if Neo4j is absent.
from api.graph import router as graph_router  # noqa: E402

app.include_router(graph_router)

# Live reasoning (docling-agent runner). Router is mounted unconditionally so
# the route is introspectable in OpenAPI; the handler itself 503s when
# `REASONING_ENABLED` is off or the deps aren't installed.
from api.reasoning import router as reasoning_router  # noqa: E402
from infra.docling_agent_reasoning import DoclingAgentReasoningRunner  # noqa: E402
from infra.docling_agent_reasoning import deps_present as _reasoning_deps_present  # noqa: E402
from infra.llm.ollama_provider import OllamaProvider  # noqa: E402

app.include_router(reasoning_router)


def _build_reasoning_runner() -> DoclingAgentReasoningRunner | None:
    """Wire the reasoning runner if `REASONING_ENABLED=true` and deps are
    importable. Today only `LLM_PROVIDER_TYPE=ollama` is supported (cf.
    `LLMProvider` docstring); other values fall through to a logged warning
    + None so the rest of the app boots cleanly.
    """
    if not settings.reasoning_enabled:
        return None
    if not _reasoning_deps_present():
        logger.warning(
            "REASONING_ENABLED=true but docling-agent / mellea not importable — "
            "reasoning runner disabled"
        )
        return None
    if settings.llm_provider_type != "ollama":
        logger.warning(
            "Unsupported LLM_PROVIDER_TYPE=%s — reasoning runner disabled (only "
            "'ollama' is realizable today, see "
            "https://github.com/docling-project/docling-agent/issues/26)",
            settings.llm_provider_type,
        )
        return None

    provider = OllamaProvider(
        host=settings.ollama_host,
        default_model_id=settings.reasoning_model_id,
    )
    return DoclingAgentReasoningRunner(provider=provider)


app.state.reasoning_runner = _build_reasoning_runner()


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

    status = "ok" if db_status == "ok" else "degraded"
    runner = getattr(app.state, "reasoning_runner", None)
    return HealthResponse(
        status=status,
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
        ingestion_available=getattr(app.state, "ingestion_service", None) is not None,
        # True when the runner is wired and reports itself available. The
        # actual Ollama reachability is checked lazily at call-time to avoid
        # blocking health checks on the LLM host.
        reasoning_available=runner is not None and runner.is_available,
        # 0.6.0 — Doc workspace mode flags (#210).
        inspect_mode_enabled=settings.inspect_mode_enabled,
        chunks_mode_enabled=settings.chunks_mode_enabled,
        ask_mode_enabled=settings.ask_mode_enabled,
    )

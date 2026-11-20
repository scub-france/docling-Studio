"""`AppStateBuilder` — the boot sequence that produces the typed `AppState`.

`main.py` used to build every repository, adapter and service inline in
`lifespan`, publishing each onto the untyped `app.state` as it went: ~150 lines
where the order of assignments was load-bearing and nothing was checked. The
builder owns that sequence instead and hands back a single typed container
(`api.state.AppState`).

It outlives boot on purpose: it keeps the published container so runtime
rewiring — #317's reasoning hot-rebuild — is a `dataclasses.replace` plus one
atomic rebind, rather than a scatter of `app.state.x = y` writes.

This package is the only place allowed to reach across every layer (infra +
persistence + services + domain); the architecture tests scope their rules to
the layer packages, and a composition root is by definition outside them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from api.state import AppState
from bootstrap.factories import (
    build_analysis_service,
    build_backend_resolver,
    build_chunker,
    build_document_file_store,
    build_document_service,
    build_document_tools,
    build_env_mcp_config,
    build_env_reasoning_config,
    build_ingestion_service,
    build_parse_loader,
    build_reasoning_runner,
    check_store_secret_key,
    init_neo4j,
)
from bootstrap.mcp_mount import describe_mcp_server
from domain.app_config import ReasoningConfig, ReasoningDiagnostics
from infra.docling_agent_reasoning import describe_deps_provenance, has_usable_deps
from infra.docling_analysis_engine import DoclingAnalysisEngine
from infra.docling_tree import DoclingTreeReader
from infra.llm.ollama_probe import OllamaProbe
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from infra.preview_cache import PreviewCache
from infra.settings import settings
from persistence.analysis_edit_repo import SqliteAnalysisEditRepository
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.app_settings_repo import SqliteAppSettingsRepository
from persistence.chunk_push_repo import SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from persistence.store_repo import SqliteStoreRepository
from services.analysis_edit_service import AnalysisEditService
from services.app_config_service import AppConfigService
from services.chunk_push_service import ChunkPushService
from services.chunk_service import ChunkService
from services.current_analysis import CurrentAnalysisResolver
from services.document_tree_service import DocumentTreeService
from services.export_service import ExportService
from services.graph_service import GraphService
from services.mcp_config_service import McpConfigService
from services.preview_service import PreviewService
from services.reasoning_service import ReasoningService
from services.store_service import StoreService
from services.version_service import VersionService

if TYPE_CHECKING:
    from collections.abc import Callable

    from bootstrap.mcp_mount import MountedMcpServer
    from domain.mcp_config import McpRuntimeConfig, McpServerStatus
    from services.analysis_service import AnalysisService
    from services.document_service import DocumentService
    from services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


class AppStateBuilder:
    """Builds — and then owns — the application's typed state container.

    `build()` runs the boot sequence once. Afterwards the builder stays alive
    behind the runtime-config service so a reasoning rebuild can publish a new
    container through `_update()`.
    """

    def __init__(
        self,
        *,
        publish: Callable[[AppState], None],
        mcp_server: MountedMcpServer | None = None,
    ) -> None:
        self._publish = publish
        self._mcp_server = mcp_server
        self._state = AppState(analysis_editor_enabled=settings.analysis_editor_enabled)

    @property
    def state(self) -> AppState:
        return self._state

    def _update(self, **changes) -> AppState:
        """Publish a new container with `changes` applied — one atomic rebind."""
        self._state = replace(self._state, **changes)
        self._publish(self._state)
        return self._state

    async def build(self) -> AppState:
        await init_db()
        await check_store_secret_key()
        repos = _build_repositories()
        graph_writer, graph_reader = await self._build_graph_adapters()
        ingestion_service = build_ingestion_service(graph_writer)
        backend_resolver = build_backend_resolver(repos.store_repo)
        current_analysis = _build_current_analysis(repos)
        core = _build_analysis_services(repos, current_analysis, graph_writer)
        files = _build_file_services(repos, core.analysis_edit_service)
        stores = _build_store_services(repos, backend_resolver, ingestion_service)
        structure = _build_structure_services(repos, core.analysis_edit_service, graph_reader)
        self._update(
            current_analysis=current_analysis,
            document_service=files.document_service,
            preview_service=files.preview_service,
            analysis_service=core.analysis_service,
            analysis_edit_service=core.analysis_edit_service,
            export_service=files.export_service,
            store_service=stores.store_service,
            chunk_service=core.chunk_service,
            chunk_push_service=stores.chunk_push_service,
            document_tree_service=structure.document_tree_service,
            graph_service=structure.graph_service,
            version_service=core.version_service,
            ingestion_service=ingestion_service,
        )
        await self._wire_reasoning(current_analysis)
        await self._wire_mcp(repos.document_repo, repos.analysis_repo, current_analysis)
        logger.info("Docling Studio backend ready (engine=%s)", settings.conversion_engine)
        return self._state

    # ------------------------------------------------------------------
    # Wiring steps
    # ------------------------------------------------------------------

    async def _build_graph_adapters(self):
        """Wrap the env-based Neo4j driver in its port adapters (#audit-01) so
        the service layer never touches the raw driver. `(None, None)` when
        Neo4j isn't wired — both consumers keep their soft-fail behavior."""
        driver = await init_neo4j()
        if driver is None:
            return None, None
        from infra.neo4j.graph_adapter import Neo4jGraphReader, Neo4jGraphWriter

        logger.info("Neo4j ready (uri=%s)", settings.neo4j_uri)
        return Neo4jGraphWriter(driver), Neo4jGraphReader(driver)

    async def _wire_reasoning(self, current_analysis) -> None:
        """Reasoning runtime config (#317) + reasoning service (#303).

        Env vars are bootstrap defaults; `app_settings` rows override them and
        writes rebuild the runner + service in place, with no restart. Services
        may not import infra, so the infra bindings (runner build, Ollama probe,
        diagnostics) are injected from here.
        """

        def apply_config(config: ReasoningConfig) -> None:
            runner = build_reasoning_runner(config)
            self._update(
                reasoning_runner=runner,
                reasoning_service=ReasoningService(
                    runner=runner,
                    current_analysis=current_analysis,
                    default_model_id=config.model_id,
                ),
            )

        self._update(
            app_config_service=AppConfigService(
                repo=SqliteAppSettingsRepository(),
                env_defaults=build_env_reasoning_config(),
                provider_type=settings.llm_provider_type,
                read_only=settings.deployment_mode == "huggingface",
                probe=OllamaProbe(),
                apply_config=apply_config,
                diagnostics_provider=self._read_reasoning_diagnostics,
            )
        )
        # Applies persisted overrides on top of the env defaults — this is what
        # actually builds the runner and the ReasoningService.
        await self._state.app_config_service.apply_effective()

    def _read_reasoning_diagnostics(self) -> ReasoningDiagnostics:
        """What the admin panel shows about the reasoning runner now in place."""
        runner = self._state.reasoning_runner
        return ReasoningDiagnostics(
            deps_present=has_usable_deps(),
            provenance=describe_deps_provenance(),
            available=runner is not None and runner.is_available,
        )

    async def _wire_mcp(self, document_repo, analysis_repo, current_analysis) -> None:
        """MCP runtime config (#364) + the document-agent services it budgets.

        Same shape as `_wire_reasoning`: env vars are bootstrap defaults,
        `app_settings` rows override them, and a write rebuilds the services in
        place. The MCP tools resolve `document_tools` on every call, so the
        next call runs on the new budgets. The parse index is built once, here,
        and survives every rebuild.
        """
        parses = build_parse_loader(document_repo, analysis_repo, current_analysis)
        mounted = self._mcp_server

        def apply_config(config: McpRuntimeConfig) -> None:
            # One rebind: the next request sees the new budgets and the switch
            # together.
            self._update(
                document_tools=build_document_tools(parses, config),
                mcp_serving=config.enabled,
            )

        async def get_server_status() -> McpServerStatus:
            return await describe_mcp_server(mounted)

        self._update(
            mcp_config_service=McpConfigService(
                repo=SqliteAppSettingsRepository(),
                env_defaults=build_env_mcp_config(),
                read_only=settings.deployment_mode == "huggingface",
                apply_config=apply_config,
                status_provider=get_server_status,
                mounted=mounted is not None,
            )
        )
        # Builds the first DocumentTools, with persisted overrides applied.
        await self._state.mcp_config_service.apply_effective()


# ----------------------------------------------------------------------
# Boot steps, in dependency order
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Repositories:
    """The SQLite repositories, one instance of each, shared by every service."""

    document_repo: SqliteDocumentRepository
    document_analysis_repo: SqliteDocumentAnalysisRepository
    analysis_repo: SqliteAnalysisRepository
    store_repo: SqliteStoreRepository
    link_repo: SqliteDocumentStoreLinkRepository
    chunk_repo: SqliteChunkRepository


def _build_repositories() -> _Repositories:
    return _Repositories(
        document_repo=SqliteDocumentRepository(),
        document_analysis_repo=SqliteDocumentAnalysisRepository(),
        analysis_repo=SqliteAnalysisRepository(),
        store_repo=SqliteStoreRepository(),
        link_repo=SqliteDocumentStoreLinkRepository(),
        chunk_repo=SqliteChunkRepository(),
    )


def _build_current_analysis(repos: _Repositories) -> CurrentAnalysisResolver:
    # One rule for "the document's current analysis", shared by every
    # reader below (02-2.3.1).
    return CurrentAnalysisResolver(
        state_repo=repos.document_analysis_repo,
        analysis_repo=repos.analysis_repo,
    )


@dataclass(frozen=True)
class _AnalysisServices:
    """The services over a document's analysis: run it, edit it, chunk it, version it."""

    analysis_service: AnalysisService
    analysis_edit_service: AnalysisEditService
    chunk_service: ChunkService
    version_service: VersionService


def _build_analysis_services(
    repos: _Repositories, current_analysis: CurrentAnalysisResolver, graph_writer
) -> _AnalysisServices:
    analysis_service = build_analysis_service(
        repos.document_repo,
        repos.analysis_repo,
        graph_writer,
    )
    analysis_edit_service = _build_analysis_edit_service(repos, current_analysis, graph_writer)
    # Doc-centric chunks (#256), their pushes to stores, and the tree.
    chunk_service = ChunkService(
        chunk_repo=repos.chunk_repo,
        document_repo=repos.document_repo,
        active_result_service=analysis_edit_service,
        chunker=build_chunker(),
    )
    version_service = _build_version_service(repos, current_analysis)

    # 0.6.1 — Document versions (#267): frozen (analysis, chunks)
    # snapshots written on each version-creating trigger.
    analysis_service.set_version_recorder(version_service)
    chunk_service.set_version_recorder(version_service)
    return _AnalysisServices(
        analysis_service=analysis_service,
        analysis_edit_service=analysis_edit_service,
        chunk_service=chunk_service,
        version_service=version_service,
    )


def _build_analysis_edit_service(
    repos: _Repositories, current_analysis: CurrentAnalysisResolver, graph_writer
) -> AnalysisEditService:
    return AnalysisEditService(
        analysis_repo=repos.analysis_repo,
        document_repo=repos.document_repo,
        analysis_state_repo=repos.document_analysis_repo,
        current_analysis=current_analysis,
        edit_repo=SqliteAnalysisEditRepository(),
        engine=DoclingAnalysisEngine(),
        graph_writer=graph_writer,
        chunk_repo=repos.chunk_repo,
    )


def _build_version_service(
    repos: _Repositories, current_analysis: CurrentAnalysisResolver
) -> VersionService:
    return VersionService(
        version_repo=SqliteDocumentVersionRepository(),
        chunk_repo=repos.chunk_repo,
        document_repo=repos.document_repo,
        analysis_repo=repos.analysis_repo,
        analysis_state_repo=repos.document_analysis_repo,
        current_analysis=current_analysis,
    )


@dataclass(frozen=True)
class _FileServices:
    """The services that touch an uploaded file, over one shared file store."""

    document_service: DocumentService
    preview_service: PreviewService
    export_service: ExportService


def _build_file_services(
    repos: _Repositories, active_result_service: AnalysisEditService
) -> _FileServices:
    # One file store for every service that touches an uploaded file.
    file_store = build_document_file_store()
    return _FileServices(
        document_service=build_document_service(
            repos.document_repo,
            repos.analysis_repo,
            repos.link_repo,
            repos.store_repo,
            file_store=file_store,
        ),
        preview_service=PreviewService(
            documents=repos.document_repo,
            files=file_store,
            rasterizer=PdfPageRasterizer(),
            inspector=PdfiumInspector(),
            cache=PreviewCache(),
        ),
        export_service=ExportService(
            document_repo=repos.document_repo,
            analysis_repo=repos.analysis_repo,
            active_result_service=active_result_service,
            file_store=file_store,
        ),
    )


@dataclass(frozen=True)
class _StoreServices:
    """The services over the vector and graph stores a document is pushed to."""

    store_service: StoreService
    chunk_push_service: ChunkPushService


def _build_store_services(
    repos: _Repositories, backend_resolver, ingestion_service: IngestionService | None
) -> _StoreServices:
    return _StoreServices(
        store_service=StoreService(
            store_repo=repos.store_repo,
            link_repo=repos.link_repo,
            document_repo=repos.document_repo,
            backend_resolver=backend_resolver,
        ),
        chunk_push_service=ChunkPushService(
            chunk_repo=repos.chunk_repo,
            chunk_push_repo=SqliteChunkPushRepository(),
            document_repo=repos.document_repo,
            ingestion_service=ingestion_service,
            store_repo=repos.store_repo,
            link_repo=repos.link_repo,
            backend_resolver=backend_resolver,
        ),
    )


@dataclass(frozen=True)
class _StructureServices:
    """The document's structure: its element tree, and its graph when Neo4j is wired."""

    document_tree_service: DocumentTreeService
    graph_service: GraphService


def _build_structure_services(
    repos: _Repositories, active_result_service: AnalysisEditService, graph_reader
) -> _StructureServices:
    return _StructureServices(
        document_tree_service=DocumentTreeService(
            document_repo=repos.document_repo,
            analysis_repo=repos.analysis_repo,
            tree_reader=DoclingTreeReader(),
            active_result_service=active_result_service,
        ),
        # 0.6.1 (#audit-01) — GraphService serves /graph so api/graph.py
        # stops reaching into infra. Reader is None without Neo4j (503).
        graph_service=GraphService(graph_reader=graph_reader),
    )

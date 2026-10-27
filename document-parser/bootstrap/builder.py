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
from dataclasses import replace
from typing import TYPE_CHECKING

from api.state import AppState
from bootstrap.factories import (
    build_analysis_service,
    build_backend_resolver,
    build_chunk_service,
    build_document_service,
    build_document_tools,
    build_ingestion_service,
    build_reasoning_runner,
    check_store_secret_key,
    env_reasoning_config,
    init_neo4j,
)
from domain.app_config import ReasoningConfig, ReasoningDiagnostics
from infra.docling_agent_reasoning import deps_present, deps_provenance
from infra.llm.ollama_probe import OllamaProbe
from infra.settings import settings
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.app_settings_repo import SqliteAppSettingsRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository, SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from persistence.store_repo import SqliteStoreRepository
from services.app_config_service import AppConfigService
from services.export_service import ExportService
from services.graph_service import GraphService
from services.reasoning_service import ReasoningService
from services.store_service import StoreService
from services.version_service import VersionService

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class AppStateBuilder:
    """Builds — and then owns — the application's typed state container.

    `build()` runs the boot sequence once. Afterwards the builder stays alive
    behind the runtime-config service so a reasoning rebuild can publish a new
    container through `_update()`.
    """

    def __init__(self, *, publish: Callable[[AppState], None]) -> None:
        self._publish = publish
        self._state = AppState()

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

        document_repo = SqliteDocumentRepository()
        analysis_repo = SqliteAnalysisRepository()
        store_repo = SqliteStoreRepository()
        link_repo = SqliteDocumentStoreLinkRepository()
        chunk_repo = SqliteChunkRepository()
        chunk_edit_repo = SqliteChunkEditRepository()
        chunk_push_repo = SqliteChunkPushRepository()

        graph_writer, graph_reader = await self._build_graph_adapters()
        ingestion_service = build_ingestion_service(graph_writer)
        backend_resolver = build_backend_resolver(store_repo)

        analysis_service = build_analysis_service(document_repo, analysis_repo, graph_writer)
        chunk_service = build_chunk_service(
            document_repo=document_repo,
            analysis_repo=analysis_repo,
            chunk_repo=chunk_repo,
            chunk_edit_repo=chunk_edit_repo,
            chunk_push_repo=chunk_push_repo,
            store_repo=store_repo,
            link_repo=link_repo,
            ingestion_service=ingestion_service,
            backend_resolver=backend_resolver,
        )
        version_service = VersionService(
            version_repo=SqliteDocumentVersionRepository(),
            chunk_repo=chunk_repo,
            chunk_edit_repo=chunk_edit_repo,
            document_repo=document_repo,
        )

        # The analysis service still carries the chunk promoter wiring for
        # legacy callers / tests, but the analysis flow no longer invokes it
        # (decoupling from #266). Chunks are explicit — produced via the
        # `+ Generate chunks` action on the Chunk view.
        analysis_service.set_chunk_promoter(chunk_service)
        # 0.6.1 — Document versions (#267): frozen (analysis, chunks)
        # snapshots written on each version-creating trigger.
        analysis_service.set_version_recorder(version_service)
        chunk_service.set_version_recorder(version_service)

        self._update(
            analysis_repo=analysis_repo,
            store_repo=store_repo,
            document_store_link_repo=link_repo,
            document_service=build_document_service(document_repo, analysis_repo),
            analysis_service=analysis_service,
            export_service=ExportService(document_repo=document_repo, analysis_repo=analysis_repo),
            store_service=StoreService(
                store_repo=store_repo,
                link_repo=link_repo,
                document_repo=document_repo,
                backend_resolver=backend_resolver,
            ),
            chunk_service=chunk_service,
            # 0.6.1 (#audit-01) — GraphService serves /graph so api/graph.py
            # stops reaching into infra. Reader is None without Neo4j (503).
            graph_service=GraphService(graph_reader=graph_reader),
            version_service=version_service,
            ingestion_service=ingestion_service,
            document_tools=build_document_tools(document_repo, analysis_repo),
        )

        await self._wire_reasoning(analysis_repo)
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

    async def _wire_reasoning(self, analysis_repo) -> None:
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
                    analysis_repo=analysis_repo,
                    default_model_id=config.model_id,
                ),
            )

        def diagnostics() -> ReasoningDiagnostics:
            runner = self._state.reasoning_runner
            return ReasoningDiagnostics(
                deps_present=deps_present(),
                provenance=deps_provenance(),
                available=runner is not None and runner.is_available,
            )

        self._update(
            app_config_service=AppConfigService(
                repo=SqliteAppSettingsRepository(),
                env_defaults=env_reasoning_config(),
                provider_type=settings.llm_provider_type,
                read_only=settings.deployment_mode == "huggingface",
                probe=OllamaProbe(),
                apply_config=apply_config,
                diagnostics_provider=diagnostics,
            )
        )
        # Applies persisted overrides on top of the env defaults — this is what
        # actually builds the runner and the ReasoningService.
        await self._state.app_config_service.apply_effective()

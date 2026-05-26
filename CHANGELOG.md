# Changelog

All notable changes to Docling Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.6.1] - 2026-05-25

### Added

- **Per-document workspace** (#263, #264, #265, #266, #267, #268): `DocWorkspacePage` shell with a Parse / Chunk / Inspect / Compare tab switcher replaces the legacy `/studio` single-page editor. Parse view (#264) introduces LAYERS filters, focus mode, tree color-coding and centered scroll; Properties panel (#265) plus inline chunk edit; Strategy popover (#268) for inline rechunk from the Chunk view; dedicated "Generate chunks" button decouples chunk creation from the analysis run.
- **Version history** (#267): paired `(analysis, chunks)` version snapshots with a History drawer for switching the active analysis. Race on new-analysis creation closed and pre-existing data backfilled.
- **Chunk service + routes** (#256, #269): backend `ChunkService` exposing 9 DDD-granular routes under `/api/documents/{id}/chunks/*`. Every existing `/api/*` route classified against the no-UX-shaped-routes rule (`docs/design/269-backend-ddd-audit.md`).
- **Ingest tab redesign** (#225, #283, #285): workspace Ingest view with CTA + history-driven shell, push-history endpoint `GET /api/documents/{id}/chunks/pushes`, pending-push badge on the launch CTA, hierarchical doc tree with per-tab CTAs and ingest-targets popover.
- **Store connection credentials** (#279): per-store backend dispatch through a resolver + pool layer, Neo4j driver pool keyed by `(uri, user)`, OpenSearch client pool with basic-auth, Neo4j as a connectable store backend. Store form gets a connection sub-form + test-connection button; `/api/stores/*` exposes connection fields and a test-connection endpoint.
- **Sealing-at-rest for store passwords** (#279): new `FernetBox` adapter (`infra/secrets/fernet_box.py`) sealing store credentials before persistence; `STORE_SECRET_KEY` env var required as soon as any store row holds a sealed value (boot fails otherwise — see `main.py:_check_store_secret_key`).
- **Master surface flags** (#257): `STUDIO_MODE_ENABLED` and `RAG_PIPELINE_ENABLED` env vars gate the legacy Studio mode and the reasoning pipeline respectively (default off in production; e2e suite opts in via `STUDIO_MODE_ENABLED=true` for `@critical` tests).
- **Karate UI e2e suite** (#256, #266): regression coverage for Doc tab chunk mode and rechunk flow, scaffold under `e2e/`.

### Changed

- **Push-chunks wire vocabulary**: `POST /api/documents/{id}/chunks/push` response field `jobId` renamed to `pushId`; corresponding i18n keys `chunks.pushedJob`, `chunks.stale.jobDispatched`, `docs.jobDispatched` renamed to `chunks.pushDispatched`, `chunks.stale.pushDispatched`, `docs.pushDispatched` and rephrased from "Job lance/dispatched" to "Push enregistre/recorded" — aligns the wire on the `ChunkPush` domain aggregate (#audit-02).
- **Backend DDD audit** (#269): the no-UX-shaped-routes rule is now documented in `document-parser/CLAUDE.md` and codified in `docs/design/269-backend-ddd-audit.md`. Every `/api/*` route classified as either a single domain op or a named atomicity exception.
- **Workspace navigation polish** (`0c98645`): per-tab CTAs, hierarchical doc tree, ingest-targets popover.
- **Backend uploads non-blocking** (#audit-12): `DocumentService.upload` and `ServeConverter.convert` offload their sync disk I/O + poppler subprocess to worker threads (`asyncio.to_thread`), mirroring the 0.5.0 pattern applied to `/preview`.
- **Architecture test makes pytestarch optional at collect-time** (#audit-09): `tests/test_architecture.py` now uses `pytest.importorskip` so the file collects cleanly even without test deps installed; CI installs `requirements-test.txt` and runs the rules normally.

### Fixed

- **Re-chunk preserves chunker `doc_items`** (#266): bbox ↔ chunk linking no longer breaks after a rechunk; structure tree reloads on active-analysis change.
- **Document-store-links upsert on push** (#225): per-store state was never updated — `chunk_pushes` now FK-resolves store slug → id first.
- **Ingest view refresh after push** (#225): stale count aligned with the push that just landed.
- **Neo4j Document node merged in `chunk_writer`** (#225): silent-fail after a graph wipe.
- **Ingestion availability decoupled from OpenSearch** (#199): Neo4j-only ingest no longer requires OpenSearch to be reachable.
- **Cross-doc bbox leak in analyses list** (`fa2c7d7`): list endpoint filters by `documentId`.
- **Frontend feature-flag race** (`5df009a`, `825e7d7`): flags load before mount; router guard awaits the load; idempotent.
- **Docker dev proxy** (`c43aced`, `f56ead5`): Vite dev frontend correctly targets the backend.
- **Push-chunks duplicate dropped** (#256, `b4ad874`): `pushDocumentToStore` removed; rechunk return shape aligned.
- **Backend test collection unblocked** (#audit-09): dead `test_local_converter.py` deleted (the SUT `_encode_picture_b64` was removed); was hidden behind `.gitignore` rather than fixed.
- **CI auto-close hardened** (#audit-10): commits payload moved into the `env:` block of the workflow to avoid shell interpolation of commit messages with quotes/backticks.
- **Frontend package version bumped to 0.6.1** (#audit-11): was stuck at 0.5.0.
- **Remote-mode bbox overlay restored** (#audit-remote-bbox): `ServeConverter` was silently dropping `self_ref` on every element parsed from the Docling Serve response, leaving the Linked-view canvas overlay empty for every document converted through Docling Serve. Local-mode parity was already correct (`LocalConverter` carries it); the remote path now does too.

### Security

- **CVE-2026-7598 (libssh2)**: ignored — not reachable from any code path in the image and no Debian backport available (`858c3a9`).
- **`STORE_SECRET_KEY` plumbed end-to-end** (#audit-08): `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml` now document the variable with the key-generation one-liner and ship it with no default — boot fails if sealed rows exist without a key. Closes the "operator seals with an ephemeral key" foot-gun.

### BREAKING CHANGES

- **`POST /api/documents/{id}/chunks/push` response field**: `jobId` → `pushId`. Frontend consumers must update.
- **Surface flags default off in production**: `STUDIO_MODE_ENABLED` and `RAG_PIPELINE_ENABLED` were implicitly on before 0.6.1. Operators relying on the legacy `/studio` page or the RAG pipeline must explicitly set them to `true`.
- **`STORE_SECRET_KEY` required for sealed stores**: any 0.6.0 deployment that already created store rows with sealed passwords will fail the boot on 0.6.1 until `STORE_SECRET_KEY` is provided. Generate a Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) and pin it in the environment before upgrading. Rotating the key invalidates every existing sealed value.
- **i18n keys renamed** (`chunks.pushedJob`, `chunks.stale.jobDispatched`, `docs.jobDispatched` → `chunks.pushDispatched`, `chunks.stale.pushDispatched`, `docs.pushDispatched`) and their placeholder `{jobId}` → `{pushId}`. Any external translation override file must be updated.

## [0.6.0] - 2026-05-19

### Added

- **Doc-centric data model + routing** (#202, #203, #204, #205, #206, #207, #208, #209, #210, #211, #216): `Document` lifecycle state machine, per-`(document, store)` ingestion state, deterministic chunkset hash for auto-stale detection, chunks promoted to first-class entities with an audit trail. URL scheme migrated from analysis-centric (`/analysis/:id`) to document-centric (`/docs/:id/...`); reworked sidebar nav (Home / Docs / Stores / Runs / Settings); breadcrumb; feature-flag mode gating with deep-link redirect.
- **Document Library** (#211): `/docs` page with filters, bulk actions, multi-file import, `StatusBadge`.
- **Doc workspace tabs**: `DocInspectTab` (#240, #241) for Markdown / Elements / Images from the Docling analysis; `DocAskTab` (#242) for the reasoning trace integrated into the workspace.
- **Stores CRUD UI + API** (#243, #244, #245, #251): `StoresListPage`, `StoreDetailPage`, `StoreForm`, `QueryPage`. Backend gets `/api/stores` router + `StoreService` orchestrator + `SqliteStoreRepository` with full CRUD; per-kind config validation; Neo4j added as a `StoreKind`. Typed API client; backend error detail surfaced through `apiFetch`.

### Changed

- **Vocabulary rename `index` → `ingest`** (#224, #225) across UI labels, route names and i18n keys. Stale stores strip on the workspace.
- **Workspace shell refactor** (#216): `DocWorkspacePage` (`DocTreeRail`, `DocWorkspaceHeader`, editable chunks editor) replaces the legacy single-page studio for doc-centric flows.
- **Doc state reset on navigation** (`53d28c2`): bbox / analysis state leak between docs fixed.
- **SQLite schema bootstrap clean-slate** (#279, `db145ca`): drop the incremental migration machinery and rewrite `_SCHEMA` from scratch — fresh installs only from 0.6.x onward.

### Fixed

- **CI**: install `pytestarch` in `docling-compat` workflow (`c3d4b11`); nginx template moved outside `sites-enabled` to avoid raw-load (`2807cc3`).

### BREAKING CHANGES

- **URL scheme migration**: paths under `/analysis/:id` are gone; the workspace lives under `/docs/:id/...`. The legacy `/studio` page remains accessible only when `STUDIO_MODE_ENABLED=true` (and only until 0.7.0 ships its rewrite).
- **Vocabulary `index` → `ingest`**: any external tooling parsing the public UI / API surface for the `index` keyword must update.
- **No auto-migration from 0.5.x**: the SQLite schema is bootstrapped fresh from `_SCHEMA`. Upgrading from a 0.5.x database requires either (a) re-importing your documents into a fresh DB, or (b) hand-rolling the catch-up DDL — there is no migration path shipped.

## [0.5.1] - 2026-04-30

### Fixed

- Nginx upload body cap raised from 5 MB to 200 MB (`NGINX_MAX_BODY_SIZE`, default `200M`); uploads larger than 5 MB no longer returned 413 before reaching the backend.

## [0.5.0] - 2026-04-28

### Added

- Reasoning-trace viewer: SQLite-backed graph built from `document_json`, iteration-by-iteration overlay on the document outline (StructureViewer + GraphView), bidirectional PDF ↔ graph focus
- Live reasoning runner via [docling-agent](https://github.com/docling-project/docling-agent) (Ollama backend): `POST /api/documents/:id/reasoning` returns answer + iteration trace + convergence flag (gated by `REASONING_ENABLED`, off by default)
- `LLMProvider` port abstraction with `OllamaProvider` adapter — opens the door to alternate LLM backends once docling-agent supports them
- Neo4j graph storage pipeline: `TreeWriter` + `ChunkWriter` adapters, schema bootstrap, graph fetch endpoint, `Maintain` step with cytoscape-based graph visualization
- Architecture decision record (ADR-001): graph visualization library choice and 200-page endpoint cap
- Remote chunking: enabled in Docling Serve mode (previously local-only)
- Hexagonal architecture tests powered by `pytestarch` (CI-enforced)
- Centralized magic numbers for page dimensions, limits, and timeouts
- Paste image size/type limits (env vars `MAX_PASTE_IMAGE_SIZE_MB`, `PASTE_ALLOWED_IMAGE_TYPES`); surfaced in `/api/health`

### Changed

- **Breaking — `RAG_*` env vars renamed to `REASONING_*`**: `RAG_ENABLED` → `REASONING_ENABLED`, `RAG_MODEL_ID` → `REASONING_MODEL_ID`. Health response field `ragAvailable` → `reasoningAvailable`. New `LLM_PROVIDER_TYPE` env var (default `ollama`) materializes the LLM-provider abstraction.
- **Breaking — reasoning endpoint renamed `/rag` → `/reasoning`**: `POST /api/documents/:id/rag` is now `POST /api/documents/:id/reasoning`. Aligns with frontend `reasoning` feature naming.
- `api/reasoning.py` refactored to depend on `ReasoningRunnerPort`; concrete `docling-agent` integration moved to `infra/docling_agent_reasoning.py` (clean architecture)
- Frontend `reasoning` feature flag now reads `reasoningAvailable` from `/api/health`; sidebar entry hides when the backend is not wired (instead of failing with 503 on click)
- Documented that `docker-compose.yml` ships dev-only defaults (Neo4j `changeme` password, OpenSearch `DISABLE_SECURITY_PLUGIN=true`); operators must harden their own production deployments
- Backend logs a loud warning at boot if Neo4j is wired (`NEO4J_URI` set) with the default `changeme` password, so prod operators can't silently inherit it
- `DocumentConverter` port exposes `supports_page_batching: bool` so the analysis service no longer relies on `isinstance(converter, ServeConverter)` (LSP fix)
- `VectorStore` port gains a `ping()` method; `IngestionService.ping()` now goes through the port instead of reaching into `_vector_store._client` (encapsulation)
- API path parameters renamed `{job_id}` → `{analysis_id}` across `api/analyses.py` and `api/ingestion.py` to align the OpenAPI surface with the user-facing terminology (URL paths unchanged)
- Centralised `localStorage` keys (`docling-theme`, `docling-locale`) into `frontend/src/shared/storage/keys.ts` (`STORAGE_KEYS`)
- Removed the dead `apiUrl` ref from the settings store and its orphan `settings.apiUrl` i18n entries
- Document-status string `"uploaded"` extracted to `DOCUMENT_STATUS_UPLOADED` in `api/schemas.py`
- PDF preview endpoint (`GET /api/documents/{id}/preview`) now offloads the synchronous file read + rasterisation to a worker thread (`asyncio.to_thread`), unblocking the FastAPI event loop

### Fixed

- Graph: collapse Docling `InlineGroup` and `Picture` children to avoid empty leaf nodes (#197)
- Neo4j: rewrite `fetch_graph` using `CALL` subqueries for proper relationship traversal
- CI: install `pytestarch` in backend tests job (#177)
- CI: ignore CVE-2026-40393 (Mesa) with expiry — Debian has no backport (#190)
- Reasoning: re-scroll PDF when re-clicking the active iteration
- `infra/docling_tree.py:101` migrated `isinstance(bbox, (list, tuple))` to PEP 604 union (Ruff UP038)
- Cross-feature integration test moved out of `features/history/` into `src/__tests__/integration/` so feature folders stay self-contained
- Tightened terminal `assert X is not None` checks in domain/repo/service tests to compare the value (e.g. `isinstance(.., datetime)` after `mark_running()`/`mark_completed()`)

## [0.4.0] - 2026-04-13

### Added

- Inline chunk text editing: double-click or edit button to modify chunk text, with save/cancel and "modified" badge
- Docker Compose dev stack (`docker-compose.dev.yml`) with OpenSearch, Dashboards, hot-reload backend and Vite frontend
- Soft-delete chunks: delete button with confirmation dialog, chunks hidden from UI but preserved in data
- Vector index metadata schema: `IndexedChunk` domain model, OpenSearch mapping builder, configurable embedding dimension
- `VectorStore` port (Protocol): `ensure_index`, `index_chunks`, `search_similar`, `get_chunks`, `delete_document`
- OpenSearch adapter (`OpenSearchStore`): kNN vector search, full-text search, bulk indexing, document CRUD
- Embedding microservice (`embedding-service/`): sentence-transformers REST API with batch processing and Dockerfile
- `EmbeddingService` port and `EmbeddingClient` HTTP adapter for remote embedding generation
- Orchestrated ingestion pipeline: Docling → chunking → embedding → OpenSearch indexing (idempotent)
- Ingestion REST API: `POST /api/ingestion/{jobId}`, `DELETE /api/ingestion/{docId}`, `GET /api/ingestion/status`
- Production docker-compose with OpenSearch and embedding service
- E2E Karate test for full ingestion workflow (PDF → chunks in OpenSearch)
- My Documents screen: search, filter (all/indexed/not indexed), sort (name/date), ingestion status badges
- Ingest button in Studio: one-click ingestion from completed analysis with progress feedback

### Fixed

### Changed

## [0.3.1] - 2026-04-09

### Added

- Batch conversion progress: segmented progress bar with ring indicator and per-batch visual feedback
- Inline mini progress bar in the top banner during analysis
- Informational notice in Prepare mode when chunking is unavailable (batch mode)
- `BATCH_PAGE_SIZE` environment variable forwarded in Docker Compose

### Fixed

- Batch progress reset to null on completion (progress_current/progress_total overwritten by stale in-memory job object)
- Regression test for batch progress preservation in `_run_analysis_inner` flow
- E2E assertion on final progress values in batch-progress feature

## [0.3.0] - 2026-04-07

### Added

- Chunking support: domain objects, persistence, API endpoints, and frontend Prepare mode
- Chunk-to-bbox hover highlighting in Prepare mode
- Page filtering and collapsible config in Prepare mode
- Feature flipping mechanism
- Reusable pagination composable and PaginationBar component
- Version display in sidebar, settings page, and health endpoint

### Fixed

- Feature flag health check blocked by CORS
- Zombie jobs and unprotected JSON parse
- Upload error not displayed in DocumentUpload component
- Serve API contract: send `to_formats` as repeated form fields
- Audit findings: security, robustness, dead code, domain-infra violation

### Changed

- Refactored backend to hexagonal architecture for converter extensibility
- Added ServeConverter adapter for remote Docling Serve integration
- Moved `@vitest/mocker` from dependencies to devDependencies

## [0.2.0] - 2025-05-14

### Added

- Multi-arch Docker image release pipeline (GitHub Actions)
- Docker image published to `ghcr.io/scub-france/Docling-Studio`

## [0.1.0] - 2025-01-01

### Added

- Initial release of Docling Studio
- PDF upload and document management
- Configurable Docling pipeline (OCR, tables, code, formulas, images)
- Bounding box visualization with color-coded overlays
- Per-page results synchronized with PDF viewer
- Markdown and HTML export
- Analysis history with re-visit capability
- Dark/Light theme support
- French and English localization
- Docker and Docker Compose deployment
- CI/CD with GitHub Actions (tests + multi-arch Docker build)
- Health check endpoint (`/health`)
- SQLite-backed persistence

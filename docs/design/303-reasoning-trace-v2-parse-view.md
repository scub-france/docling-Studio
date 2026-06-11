# Design: Reasoning Trace v2 — Parse-view trace timeline + Ask panel

<!--
Design doc template for Docling Studio.

One design doc per tracked issue. File path convention:
  docs/design/<issue-number>-<kebab-slug>.md

Status lifecycle: Draft → In review → Accepted → Implemented (or Superseded).
Bump the Status line as the doc progresses; do not delete sections on the way.

This template is tailored to the project's architecture and conventions:
  - Backend Hexagonal Architecture / ports & adapters
    (domain → api/services/persistence/infra)
    see docs/architecture.md
  - Backend coding standards (FastAPI + Pydantic camelCase, aiosqlite,
    Python snake_case internal, max 300 lines/file, 30 lines/function)
    see docs/architecture/coding-standards.md
  - Frontend feature-based organization (Vue 3 + Pinia, one store per
    feature, Composition API, TypeScript strict, data-e2e selectors)
  - E2E with Karate UI (NOT Playwright) — see e2e/CONVENTIONS.md
  - Audit dimensions used at release gate — see docs/audit/master.md
  - ADR process for load-bearing decisions — see docs/architecture/adr-guide.md

The `/conception` command pre-fills the header block and §1 / §2 / §12 from
the linked issue. Everything else is on the author.
-->

- **Issue:** #303
- **Title on issue:** [FEATURE] Reasoning Trace v2 — Parse-view trace timeline + Ask panel
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-06-10
- **Status:** Accepted
- **Target milestone:** 0.7.0 — UI Redesign Maquette
- **Impacted layers:** backend: domain · services · api · infra · frontend: `features/reasoning` (rebuilt) · `features/document` · `features/analysis` (decouple) · `app/router` · e2e · infra/CI (uv source + `WITH_REASONING` image)
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Decoupling · DRY · Tests · Performance · CI/Build · Documentation
- **ADR spawned?:** proposed — ADR: consume `docling-agent` from the `pjmalandrino` fork via `[tool.uv.sources]` git rev; supersede when upstream PR docling-project/docling-agent#39 merges

---

## 1. Problem

The current Reasoning Trace feature (v1) is an overlay grafted onto the analysis GraphView (Cytoscape): the trace is rendered by painting visited nodes on the document graph, from a standalone `/reasoning` workspace. This view predates the doc-centric workspace rework (#207/#209/#263) and no longer matches the product direction: the reasoning experience must live **inside the Parse view**, linked to the PDF preview, the structure tree, and the properties panel.

Today, `POST /api/documents/{id}/reasoning` returns a snake_case mirror of docling-agent 0.1.0's `RAGResult` (no timing, no model id, no step kinds), produced via the private `agent._rag_loop()` with an `IndexError` workaround. The trace is only visible on the standalone `/reasoning` page as orange rings + synthetic `REASONING_NEXT` edges over the document graph; trace state is lost on reload; the Parse view has no reasoning surface (`AskRunner.vue` is an orphan since #264 deleted DocAskTab).

A richer trace model was designed and validated in **docling-lens** (standalone agent debugger): kind-tagged steps (`plan/retrieve/rerank/read/verify/answer/map`), per-step durations, citations, backend-side trace projection — backed by the public `run_with_trace()` API added to docling-agent (fork `pjmalandrino/docling-agent@dev/rag-run-with-trace`, upstream PR docling-project/docling-agent#39). A high-fidelity UI/UX design handoff exists and is **binding**.

## 2. Goals

- [ ] Domain VOs + `trace_builder` ported with tests (title truncation, insufficient summary, duration/model preference, wall-clock fallback)
- [ ] Adapter rewritten on `run_with_trace()` (fork 0.5.0 constructor surface, `BackendConfig`/`create_backend`), defensive on missing `duration_ms`/`model_id`, `IndexError → ReasoningParseError` kept, tests rewritten
- [ ] `POST /api/documents/{id}/reasoning` returns camelCase `ReasoningTraceResponse` (status codes preserved: 503/400/404/502/500), wall-clock captured server-side
- [ ] `docling-agent` pinned to fork git rev via `[tool.uv.sources]`; `uv sync --group reasoning` resolves; mellea pin verified
- [ ] Ask tab + ConversationPanel + Composer per handoff (disabled-reason states, plain-text answers, turn cards with status dot/time/stats)
- [ ] TraceTimeline per handoff (kind palette from `elementColors.ts`, shared axis, degraded timing state, internal scroll, auto-select first step after run)
- [ ] Step ↔ document linking through shared document store (`focusedRef`/`focusTick`); tree scroll-into-view + ancestor auto-expand; bbox highlight + page flip; reverse selection
- [ ] Old reasoning surface removed (frontend feature files, `/reasoning` routes with redirect, GraphView decoupled from `reasoningOverlayStyles`, `/reasoning-graph` endpoint + projector + port + tests)
- [ ] Fork timing commit landed on `dev/rag-run-with-trace` (`RAGIteration.duration_ms`, `RAGResult.duration_ms`/`model_id` + tests); Studio pinned to its SHA — real per-step Gantt bars day one
- [ ] New Karate UI e2e for Ask tab gating + trace interaction; stale `reasoning-feature-flag.feature` replaced; new `e2e-ui-reasoning` CI job (`WITH_REASONING` image, `@reasoning-on` tag) green
- [ ] i18n (fr/en) for all new strings; `data-e2e` hooks on interactive elements; design tokens only (no hardcoded handoff hexes); dark mode unbroken
- [ ] Frontend pipeline green: lint:fix → format → lint → format:check → type-check → test:run; backend pytest green

## 3. Non-goals

- **SSE / streaming of steps during a run.** The UI and store are shaped so steps *can* append incrementally (the handoff shows live streaming), but the transport in this issue stays a single blocking POST. Consequences for the during-run UI are specced in §5.6 (warming state; the handoff's live append / auto-scroll / "N steps so far" counter are dropped with this non-goal). Streaming is a follow-up issue (transport + cancellation + fork-side hooks).
- **Compact density (248px / 28px rows).** The handoff exposes a Comfortable/Compact density option; this issue ships the 308px Comfortable layout only. Follow-up if requested.
- **Trace persistence.** Conversation turns and traces are session state (Pinia); they vanish on reload. Persisting runs (SQLite or Neo4j) is a separate design.
- **Real token counts.** `tokensIn` / `tokensOut` ship as `0` until mellea exposes usage stats; the UI hides token meta when `tokenCount === 0` (per handoff). Fork/upstream concern.
- **Multi-document reasoning.** `run_with_trace(sources=[...])` supports several documents with a merged `final_answer`; Studio keeps the single-document assumption and reads `per_document[0]`.
- **Reasoning against a pinned/older analysis version.** Runs target the latest completed analysis (existing semantics). An `analysisId` request parameter is a follow-up if the History-drawer mismatch (§8) proves painful in practice.
- **The legacy `/studio` surface.** `GET /api/documents/{id}/graph` (Neo4j), `GraphView.vue` and `features/analysis/graphApi.ts` stay — only GraphView's reasoning-purposed surface is removed (see §5.6). Retiring `/studio` is a separate decision.
- **Markdown answers.** The handoff mandates plain text (no `v-html`, no `marked`/`DOMPurify`). Models do emit markdown markers; they will show literally. A prompt-side or sanctioned-rendering fix is out of scope.
- **Orphan cleanup beyond the feature.** `InspectResultTabs.vue` (zero importers) and `StructureViewer.vue`'s reasoning props are left untouched; tracked as a separate chore.

## 4. Context & constraints

### Existing code surface

Backend (`document-parser/`):

- `domain/value_objects.py:164-201` — `ReasoningIteration` (180-191), `ReasoningResult` (194-201), `LLMProviderType` (167-177); `GraphPayload` docstring (216-220) names the deleted projector — stale-docstring sweep
- `domain/ports.py` — `ReasoningRunner` (413-442), `ReasoningParseError` (37), `LLMProvider` (280), `DocumentGraphProjector` (394, to delete)
- `infra/docling_agent_reasoning.py` — adapter on the 0.1.0 private surface (`_rag_loop`, `ModelIdentifier`, `OLLAMA_HOST` env mutation) — rewrite
- `api/reasoning.py` — router with router-local snake_case DTOs, talks to `analysis_repo` directly (bypasses services) — rewrite
- `api/graph.py:85-96` — `GET /reasoning-graph` route (delete); the rest of the file serves `/graph` (keep)
- `services/graph_service.py` — `project_reasoning_graph` (delete) **and** the required `graph_projector` constructor param (77-88, drop) + module docstring rewrite (1-14); `fetch_document_graph` (keep)
- `infra/docling_graph.py` — SQLite-backed graph projector (delete)
- `api/schemas.py:19-31` — `_to_camel` + `_CamelModel` (the repo's camelCase DTO base; reuse)
- `infra/settings.py` — `reasoning_enabled` (45), `ollama_host` (51), `reasoning_model_id` (52) (keep); `ask_mode_enabled` (75, env parsed at 187) (delete)
- `main.py` — `_build_reasoning_runner()` wiring (423-464, adapt); GraphService wiring loses the projector import/arg (340-347); `analysis_repo` app.state comment (251-254) updated — the router no longer reads it directly once ReasoningService exists
- `infra/docling_tree.py:6,283` — stale comments advertising the reasoning-trace viewer (shared tree walker — keep, comment fix only)
- `pyproject.toml:43-46` — `[dependency-groups] reasoning = ["docling-agent==0.1.0", "mellea==0.4.2"]` (change)
- Tests: `tests/test_reasoning_api.py`, `tests/test_docling_agent_reasoning.py` (rewrite); `tests/test_docling_graph.py` (398 lines, delete); `tests/test_graph_api.py` — delete the `TestReasoningGraph` class + fix the fixture that injects `graph_projector` (18, 69-73); keep `TestPrimeEndpointRemoved` (move into `tests/test_api_endpoints.py` if the file empties); `tests/test_api_endpoints.py:87,91` — `askModeEnabled` health assertions (remove)

Frontend (`frontend/src/`):

- `features/reasoning/**` — 14 files, ~3 274 lines (full rebuild, see §5.6)
- `pages/ReasoningPage.vue`, `app/router/routes.ts` REASONING/REASONING_DOC entries (47-55, delete + redirect), `shared/routing/names.ts:19-20` (ROUTES constants, delete), `app/router/router.test.ts:42-43` (route assertions → redirect assertions)
- `features/analysis/ui/GraphView.vue` — full reasoning-purposed surface removed (see §5.6): `reasoningOverlayStyles` import (67) + spread (330-331), `fetcher` prop (73-84), `nodeFocus` emit (85-91), `cy` defineExpose + `selectBySelfRef` (99-102, 537) — sole survivor `StudioPage.vue:502` uses none of them; stale comments rewritten (74, 89, 99, 140, 477, 537)
- `pages/DocParseTab.vue` — hosts the new dock + tabbed right panel; local `selectedNodeRef` (162) migrates to the shared focus
- `features/document/store.ts` — gains `focusedRef`/`focusTick`
- `features/document/ui/PagePreviewWithOverlay.vue` — `focusTick` prop + anchor option on `centerHighlighted()` (159-191)
- `features/document/ui/DocTreeRail.vue` + `DocTreeNode.vue` — gain reveal (auto-expand) + scroll-to-center
- `features/document/elementColors.ts` — source of the step-kind palette
- `shared/i18n.ts` — `ask.*` rewritten, `reasoning.*`/`nav.reasoning` purged, new `trace.*`
- `features/feature-flags/store.ts:100-103, 121` + `store.test.ts:188-220` + `HealthResponse.askModeEnabled` (26) — zombie flag removal

E2E: `e2e/ui/src/test/resources/navigation/reasoning-feature-flag.feature` (stale — waits on `nav-studio`/`nav-documents` removed by #209; delete) → replaced by `e2e/ui/src/test/resources/documents/doc-ask-trace.feature` (the `documents/` folder is where doc-workspace features live, `doc-*` prefix convention).

R&D: `experiments/reasoning-trace/` (sidecar scripts) — kept, README updated: the sidecar JSON import UI is gone and the wire format changed.

### Hexagonal Architecture constraints (backend)

- New value objects and the **pure projection** `trace_builder` live in `domain/` — zero imports from api/persistence/infra (architecture tests must stay green). docling-lens kept its builder in `infra/`; Studio promotes it to domain because it is a pure function over domain VOs.
- The `ReasoningRunner` port keeps its signature (returns an *enriched* `ReasoningResult`); only the adapter behind it changes.
- The `DocumentGraphProjector` port is **deleted** with its lone adapter — a port without a consumer is dead weight.
- The router currently calls `app.state.analysis_repo` directly; this design introduces `services/reasoning_service.py` so API → services → (persistence, infra) holds, mirroring `GraphService` conventions (typed errors carrying `http_status`). Services may not import infra (`tests/test_architecture.py:131-141`) — settings values are constructor-injected from `main.py`, as every existing service does.

### Deployment modes

Reasoning is orthogonal to `CONVERSION_ENGINE`: it works on both `latest-local` and `latest-remote` **iff** the image was built with `--build-arg WITH_REASONING=true` (dependency group), `REASONING_ENABLED=true`, and `OLLAMA_HOST` reaches an Ollama instance. HF Space has no Ollama → runner unwired → `/api/health` reports `reasoningAvailable: false` → the Ask tab and the trace dock simply don't render (Parse view identical to today). `chunking`/`disclaimer` flags unaffected.

### Hard constraints

- **The UI/UX handoff is binding** (layout, states, interactions, type scale). Colors are mapped to the codebase's canonical tokens — see §5.6; the handoff itself says "prefer the codebase's canonical tokens". Declared deviations from the handoff are listed in §3 and inline in §5.6 (grid widths, no-document state).
- **No persistence change** — no SQLite schema delta, no migration.
- **Wire contract break is internal-only**: the lone consumer of the old snake_case response is the v1 frontend deleted in the same change.
- Coding standards: ≤300 lines/file, ≤30 lines/function — the old `ReasoningPanel.vue` (485 lines) style of monolith must not reappear; the component tree in §5.6 is pre-split so the limit holds by construction.
- The fork dependency makes the `WITH_REASONING` image heavier (docling-agent 0.5.0 hard-depends on full `docling`, `boto3`, `pandas`, `pyarrow`, `fastparquet`) — acceptable for an opt-in image, called out in §8.

## 5. Proposed design

Data flow (target state):

```
DocParseTab (Ask tab)                    document-parser
┌─────────────────────┐   POST /api/documents/{id}/reasoning
│ Composer.run(q, m?) ├──────────────────────────────────────┐
└─────────────────────┘                                      ▼
                                              ReasoningService.run(doc_id, q, m?)
                                                │ empty query → 400 (typed error)
                                                │ analysis_repo.find_latest_completed_by_document → 404
                                                │ t0 = perf_counter()
                                                │ runner.run(document_json, q, m?)   (port)
                                                │   └ DoclingAgentReasoningRunner
                                                │       └ to_thread(agent.run_with_trace, task=q, document=doc)
                                                │           → RAGTrace.per_document[0] → ReasoningResult
                                                │ wall_ms = perf_counter() - t0
                                                │ build_trace(result, model_id, wall_ms)  (domain, pure)
                                                ▼
                                  ReasoningTraceResponse (camelCase)
┌─────────────────────┐
│ reasoning store     │  turns[] / selectedStepId
│ TraceTimeline       │──selectStep──► documentStore.focusElement(ref)  (focusedRef + focusTick++)
│ ConversationPanel   │                   │
└─────────────────────┘                   ├─► PagePreviewWithOverlay  (bbox highlight + page flip + top-anchor scroll)
        ▲                                 ├─► DocTreeRail             (reveal ancestors + scroll-to-center)
        └──selectStepByCitation(ref)──────┴─► ElementProperties       (cited element)
                 (reverse: bbox/tree click)
```

### 5.1 Domain

`domain/value_objects.py` — extend (defaults keep both shapes backward-compatible):

```python
@dataclass(frozen=True)
class ReasoningIteration:
    iteration: int
    section_ref: str
    reason: str
    section_text_length: int
    can_answer: bool
    response: str
    duration_ms: int = 0          # NEW — 0 when upstream didn't capture timing

@dataclass(frozen=True)
class ReasoningResult:
    answer: str
    iterations: list[ReasoningIteration]
    converged: bool
    duration_ms: int = 0          # NEW — agent-side LLM time, 0 if unknown
    model_id: str = ""            # NEW — self-description, "" if unknown

class ReasoningStepKind(StrEnum):  # NEW — mirrors the TS union 1:1
    PLAN = "plan"; RETRIEVE = "retrieve"; RERANK = "rerank"; READ = "read"
    VERIFY = "verify"; ANSWER = "answer"; MAP = "map"
    # docling-agent's RAG loop only emits READ today; the other kinds are
    # reserved so future agent phases don't break the wire contract.

@dataclass(frozen=True)
class ReasoningStep:               # NEW — debugger-facing step
    id: str                        # "s1", "s2", …
    kind: ReasoningStepKind
    title: str                     # LLM's stated reason, ≤96 chars
    summary: str                   # answer attempt or "Insufficient — …"
    duration_ms: int = 0
    token_count: int = 0           # reserved (mellea usage stats)
    citations: list[str] = field(default_factory=list)   # docling self_refs
    payload: dict = field(default_factory=dict)          # wire-destined, camelCase keys (§7)

@dataclass(frozen=True)
class ReasoningTrace:              # NEW — what the API serves
    answer: str
    converged: bool
    steps: list[ReasoningStep]
    total_duration_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    model_id: str = ""
```

`domain/trace_builder.py` — **new pure module** (ported from docling-lens, tests included):

```python
def build_trace(*, result: ReasoningResult, model_id: str,
                total_duration_ms: int = 0) -> ReasoningTrace: ...
```

Projection rules (locked by tests):

- one `READ` step per iteration; `id = f"s{iteration}"`
- `title = reason.strip() or f"Read {section_ref}"` — *deliberate divergence from lens* (`if it.reason else …`), so a whitespace-only reason also falls back; edge case covered in tests
- if `len(title) > 96` → `title[:93].rstrip() + "…"`
- `summary = response.strip()` when `can_answer`, else `"Insufficient — {n} chars read, agent moved on."` (char count omitted when 0)
- `citations = [section_ref] if section_ref else []`
- `payload` = the iteration's fields **with camelCase keys** (`iteration`, `sectionRef`, `reason`, `sectionTextLength`, `canAnswer`, `response`, `durationMs`) — the handoff binds the payload contract (`payload.canAnswer` drives the answered/explored chip) and Pydantic does not alias dict contents, so the builder constructs the keys; this diverges from lens, which stashes raw snake_case
- duration preference: `result.duration_ms if > 0 else total_duration_ms` (agent LLM-time wins over API wall-clock)
- model preference: `result.model_id or model_id` (self-description wins over the request arg)

Ports: `ReasoningRunner` unchanged. `DocumentGraphProjector` deleted.

### 5.2 Persistence

Untouched. No schema change, no migration. (`analysis_repo.find_latest_completed_by_document` is reused as-is — note it is **shared** with `ChunkService`; its reasoning-only docstring gets fixed.)

### 5.3 Infra adapters

`infra/docling_agent_reasoning.py` — rewritten for the fork 0.5.0 surface:

- Build per-instance backend (no more `OLLAMA_HOST` env mutation — concurrency win):
  `create_backend(BackendConfig(type="ollama", base_url=provider.host, models=ModelConfig(reasoning=raw_model_id, writing=raw_model_id)))`
- `DoclingRAGAgent(tools=[], backend=backend)` (the 0.1.0 `model_id=ModelIdentifier(...)` constructor is gone)
- `run_result = await asyncio.to_thread(agent.run_with_trace, task=query, document=doc)` → `RAGTrace`; take `rag_result = run_result.per_document[0]`
- **Defensive mapping** (the fork at `32622b4` has no timing fields):
  `duration_ms=getattr(it, "duration_ms", 0)`, `duration_ms=getattr(rag_result, "duration_ms", 0)`, `model_id=getattr(rag_result, "model_id", "") or raw_model_id`
- Keep `IndexError → ReasoningParseError`: the fork's `_attempt_answer` still ends with an unguarded `find_json_dicts(answer)[0]` (`rag.py:437`); only `_select_section` gained a fallback
- `deps_present()` keeps probing the import surface (now `docling_agent.agents`; mellea stays a hard transitive dep of the fork)

**Fork timing extension (decided at design review, 2026-06-10 — real Gantt bars day one):** implementation starts by landing a **second fork-only commit** on `dev/rag-run-with-trace` adding timing capture inside `_rag_loop` — `RAGIteration.duration_ms` (per-iteration wall-clock around section selection + answer attempt) and `RAGResult.duration_ms`/`model_id` — with tests. This commit stays **out of upstream PR #39** (scope validated by Peter = the trace API only); it rides the fork until merge, then gets re-proposed upstream separately. Studio pins the SHA of that commit. The adapter's defensive `getattr` mapping stays regardless — it is what makes the upstream-merge swap safe even if the released models don't carry the fields yet.

Dependency declaration (`pyproject.toml`):

```toml
[dependency-groups]
reasoning = ["docling-agent", "mellea>=0.5,<0.7"]

[tool.uv.sources]
docling-agent = { git = "https://github.com/pjmalandrino/docling-agent.git", rev = "<SHA of the fork timing commit — 32622b4 + 1>" }
```

HTTPS URL (not the ssh remote) so Docker `WITH_REASONING` builds and CI fetch anonymously; a SHA `rev` for reproducibility (uv.lock records it either way). **Refactor at upstream merge of PR #39**: swap the source for the released PyPI version — one-line change, captured in the proposed ADR. The mellea range is validated by a real resolve: a CI step in the existing backend job runs `uv sync --frozen --group reasoning` + smoke import (`python -c "import docling_agent.agents, mellea.stdlib.requirements"`) so the pin cannot silently rot (§9).

Env vars: unchanged (`REASONING_ENABLED` default `false`, `OLLAMA_HOST`, `REASONING_MODEL_ID`). `ASK_MODE_ENABLED` is **removed** end-to-end (env → settings → health → frontend registry + the three test files asserting it, §4): it has gated nothing since #263.

### 5.4 Services

New `services/reasoning_service.py`, mirroring `GraphService` conventions:

- Constructor-injected: `runner: ReasoningRunner | None`, `analysis_repo`, `default_model_id: str` (wired from `settings.reasoning_model_id` in `main.py` — services may not import infra)
- Typed errors with `http_status` hints: `ReasoningUnavailableError(503)` (runner unwired or `is_available` false), `ReasoningEmptyQueryError(400)` (`query.strip()` check moves here from the router — preserves today's 400 contract, which DTO `min_length` could not: Pydantic returns 422 and accepts whitespace), `ReasoningNoAnalysisError(404)`; `ReasoningParseError` passes through (router maps → 502)
- `async def run(self, doc_id: str, query: str, model_id: str | None) -> ReasoningTrace`:
  1. validate query (strip) → 400; resolve latest completed analysis with `document_json` → 404
  2. `t0 = time.perf_counter()`; `result = await runner.run(document_json=…, query=…, model_id=…)`; `wall_ms = int((perf_counter() - t0) * 1000)`
  3. `return build_trace(result=result, model_id=model_id or self._default_model_id, total_duration_ms=wall_ms)`
- Concurrency: the runner thread-offloads a 20–40 s blocking call; this is **outside** the `MAX_CONCURRENT_ANALYSES` budget. No new semaphore in this issue — the frontend enforces single-flight per client (`running` state), and the risk is logged in §8.

The router slims down to DTO mapping + error translation; `main.py` wires `app.state.reasoning_service` (keeps `_build_reasoning_runner()` internals).

### 5.5 API

| Method | Path | Change |
|--------|------|--------|
| POST | `/api/documents/{doc_id}/reasoning` | response shape replaced (snake_case `ReasoningResultResponse` → camelCase `ReasoningTraceResponse`); status codes preserved 503/400/404/502/500 (the 400 empty-query check moves to the service as a typed error, same wire behavior) |
| GET | `/api/documents/{doc_id}/reasoning-graph` | **deleted** (with `GraphService.project_reasoning_graph`, the `graph_projector` ctor param, `DocumentGraphProjector`, `infra/docling_graph.py`, tests). `GET /graph` and the shared `GraphNode/GraphEdge/GraphResponse` DTOs stay |

DTOs move to `api/schemas.py` on `_CamelModel` (repo convention — the old router-local snake_case models were a documented outlier). See §7 for the wire contract. Rate limiting: unchanged (not excluded). Wall-clock timing is captured in the service, not the router.

### 5.6 Frontend — feature module

`features/reasoning/` is **rebuilt** (the 14 v1 files are deleted, including `graphReasoningOverlay.ts`, `ReasoningWorkspace.vue`, `ReasoningPanel.vue`, `ImportTraceDialog.vue`, `RunReasoningDialog.vue`, `DocumentView.vue`, `ReasoningDocPicker.vue`, `IterationCard.vue` and the orphaned `AskRunner.vue`):

```
features/reasoning/
├── types.ts            # camelCase wire mirrors: ReasoningStepKind union,
│                       # ReasoningStep, ReasoningTrace, ConversationTurn
├── api.ts              # runReasoning(docId, query, modelId?) → ReasoningTrace
├── store.ts            # Pinia setup store (see below)
├── timeline.logic.ts   # pure: bar geometry, hasTiming, axis ticks, fmtDur
├── kindColors.ts       # ReasoningStepKind → ELEMENT_COLORS mapping + tint derivation
├── *.test.ts           # store / logic / api tests (vitest, node env)
└── ui/
    ├── TraceTimeline.vue      # docked panel: header, axis, states, scroll host
    ├── TraceRow.vue           # one step row (badge / title+chips / bar / meta)
    ├── TraceEmptyState.vue    # numbered-badge onboarding (shared pattern w/ Ask)
    ├── ConversationPanel.vue  # turn list + empty state
    ├── TurnCard.vue           # question/answer/status-dot/meta
    └── Composer.vue           # textarea + model override + Run + disabled reason
```

(The split is deliberate: header + axis + rows + three states + scoped CSS in one SFC would bust the 300-line rule — v1's `ReasoningPanel.vue` hit 485.)

**Store** (survives Parse↔Chunk remounts — DocParseTab is remounted on every mode switch, so trace state must live here, not in the tab):

```ts
// state
docId: string | null            // reset(docId) clears turns when the doc changes (decided; per-doc map = follow-up)
turns: ConversationTurn[]       // { id, time, status: 'running'|'converged'|'error',
                                //   question, trace: ReasoningTrace | null, errorMessage }
selectedTurnId / selectedStepId: string | null
running: boolean
// actions
run(docId, query, modelOverride?)   // push running turn → await api → finalize → auto-select first step
selectTurn(id)                      // load trace into timeline, auto-select first step
selectStep(id)                      // set selectedStepId + documentStore.focusElement(citations[0])
selectStepByCitation(ref)           // reverse path: no-op when no step cites ref
reset(docId)
```

**Shared citation focus** (the handoff's binding constraint — owned by `features/document/store.ts`):

- `focusedRef: string | null`, `focusTick: number`
- `focusElement(ref)` sets the ref **and bumps the tick** — re-clicking the same step re-fires scrolling everywhere (the v1 trap documented in `ReasoningWorkspace.vue:132-146`: same-value watches no-op)
- `DocParseTab` replaces its local `selectedNodeRef` with the store focus; its existing wiring is preserved: tree `@select` and bbox `@click-element` now call `documentStore.focusElement(ref)` **and** `reasoningStore.selectStepByCitation(ref)`; a `focusTick` watcher flips `currentPage` via the existing `findPageOfRef`
- **PDF scroll**: `PagePreviewWithOverlay.vue` gains an optional `focusTick: number` prop included in its scroll watch (less invasive than `defineExpose` through `<Suspense>`), and `centerHighlighted()` gains an anchor option — citation focus anchors the cited bbox **~90 px from the top of the stage** (handoff-binding: README `el.offsetTop - 90`), while direct user clicks keep today's centering
- **Tree reveal (new capability)**: `DocParseTab` computes the ancestor chain of `focusedRef` from the loaded tree and passes a `revealedRefs: Set<string>` + `revealTick` down `DocTreeRail` → `DocTreeNode`; a node whose ref is in the set forces itself open; the rail scrolls the focused row **to vertical center** via container-offset math (à la `PagePreviewWithOverlay.centerHighlighted()`, `offsetTop − clientHeight/2` — **not** `scrollIntoView`, which is the `ChunksPanel.vue:134-141` pattern the handoff rejects; ChunksPanel remains the exemplar only for the ref-map + watch registration); the focused row gets `--accent-muted` background + 600-weight label
- Citations that don't resolve in the displayed analysis version (History drawer pinned an older version) render the ref chip but the click is a graceful no-op with a muted state — never a crash

**TraceTimeline** (docked in the Parse center column):

- Placement: second child of `.parse-stage`; `flex: 0 0 308px`; the preview gets wrapped in `flex: 1 1 auto; min-height: 0` (today `PagePreviewWithOverlay` is `height: 100%` and would clip the dock). Tree and right panel keep full height — the dock spans the center cell only. *Declared deviation:* Studio keeps its existing `320px / minmax / 360px` grid columns over the handoff's sampled 300/372 — covered by the handoff's "prefer canonical" escape hatch.
- Rendered **only when** `reasoningAvailable`; the Parse view is pixel-identical to today when the flag is off.
- Header: "Reasoning" title, model chip, pulsing running indicator, right-aligned `N steps · 7.05s` stats. Pulse animation per handoff: 1.1 s ease-in-out infinite, opacity 1→.35, scale 1→.75, guarded by `prefers-reduced-motion: reduce`.
- Grid rows per handoff (`TraceRow.vue`): `84px | minmax(220px,1.45fr) | minmax(220px,1fr) | 104px` — kind badge / title + chips (`answered` / `explored` / citation ref) / duration bar on shared axis / meta (`2.21s · 489 tok`; token part hidden when 0). `explored` rows at opacity .62, restored on hover/active; active row uses the citation highlight tint (`--accent-muted`); the bar track carries a faint vertical gridline every 25 % matching the axis.
- All geometry/formatting in `timeline.logic.ts` (pure, unit-tested): cumulative bar offsets when any `durationMs > 0`, uniform distribution otherwise; bar `min-width: 3px` (`max(W%, 3px)`); 5 axis ticks (`ms` under 5 s total, else `s`); `fmtDur` (`Nms` < 1 s, `N.NNs` ≥ 1 s).
- **During a run (single-shot transport, §3)**: header keeps the pulsing "running…" indicator; the body shows the warming row "⟳ Waiting for the first step…" (pulsing dot) for the running turn — steps arrive all at once on completion. The handoff's live append, auto-scroll-to-bottom, and "N steps so far" counter are dropped with the streaming non-goal (store keeps an `appendStep`-shaped path so SSE can light them up later). Selecting an older turn during a run still shows that turn's full trace.
- Degraded timing state (per handoff — a **fallback**, not the expected state: the fork timing commit in §5.3 delivers real per-step durations day one; the degraded path covers older traces and an upstream merge without the fields): uniform bars, per-row durations hidden, axis label `step order`, footnote `ⓘ Per-step timing not available for this run…`. Never render identical fake durations.
- Empty state (`TraceEmptyState.vue`): centered badge "3" (`--accent` on `--accent-muted`), headline "The reasoning steps will appear here after a run", onboarding strip `① Load a document ✓ → ② Ask a question → ③ Inspect the trace` — ① renders checked/`--success` (always satisfied in Studio's doc-scoped route, kept for handoff fidelity), ③ emphasized `--accent`.
- Auto-select first step after a run completes; internal scroll (a 100-step run never pushes the PDF off-screen).

**Right panel — Properties | Ask tabs** (in `DocParseTab`):

- Tab bar copies the `ResultTabs.vue` orange-underline pattern (`.tabs-header`/`.tab-btn` scoped CSS — per repo convention, duplicated not extracted); Ask tab shows a count pill (`turns.length`, rendered only when > 0).
- **Default tab: Properties** (design-review decision, 2026-06-10 — Ask is optional, opt-in by click; amends the handoff prototype, which opened on Ask). Tab order: Properties first, Ask second. Element focus never auto-switches the active tab.
- When `reasoningAvailable` is false → no tab bar, `ElementProperties` alone (today's view).
- `ConversationPanel`: scrollable turn list + pinned `Composer`. Turn card (`TurnCard.vue`) per handoff: question 12.5px/600; plain-text answer clamped to 4 lines unless selected; **while running, the answer area shows the placeholder "Reading the document…" (italic, muted — i18n `ask.readingPlaceholder`)**; status dot `--success` / `--error` / pulsing `--accent`; mono time + `4 steps · 6.76s · model` stats. Selecting a turn loads its trace into the timeline. Hover/selected treatments map to `--bg-elevated` hover and `--accent` border + `--accent-muted` background when selected.
- Empty state: centered badge "2" (same `TraceEmptyState` badge pattern), title "Ask a question about this document" + one explanatory sub-line — step ② of the shared ①②③ onboarding.
- `Composer`: 2-row textarea (Enter submits, Shift+Enter newline), model-override input (mono), Run button. Disabled Run always explains why — exactly one of the three handoff reasons (i18n), with the handoff's precedence: document not ready → *Load a document first*; else `running` → *A run is already in progress*; else blank/whitespace query → *Type a question…*. *Adaptation note:* in Studio's doc-scoped Parse route a document is structurally present; "Load a document first" maps to "parsed pages not yet loaded" (`workspacePages` empty) and is kept for handoff fidelity — tests don't need to reach it.
- **Plain-text answers**: `{{ }}` interpolation + `white-space: pre-wrap`. No `marked`, no `DOMPurify`, no `v-html` anywhere in the feature.

**Design tokens** (no raw handoff hexes — dark mode must keep working; the app defaults to dark):

| Handoff | Canonical token |
|---|---|
| `#f97316` / `#ea580c` | `--accent` / `--accent-hover` |
| `#fff7ed`, `#ffedd5` (tints: selected turn, active row, badges) | `--accent-muted` |
| `#fdba74` (disabled Run) | `--accent` at reduced opacity (`opacity: .55` on the button) |
| focus rings `rgba(249,115,22,.18/.25)` | `color-mix(in srgb, var(--accent) 20%, transparent)` |
| hovers `#f9fafb` / `#fafafa`, borders `#d1d5db` | `--bg-elevated` / `--border` |
| `#1f2328` / `#6b7280` / `#9ca3af` | `--text` / `--text-secondary` / `--text-muted` |
| `#e5e7eb` / `#f1f2f4` | `--border` / `--bg-elevated` |
| `#16a34a` / `#dc2626` / `#2563eb` | `--success` / `--error` / `--info` |
| canvas `#ececef` | existing `.parse-stage` background (unchanged) |
| mono | `'IBM Plex Mono', monospace` (repo convention) |

Step-kind palette (`kindColors.ts`): base hex per kind from `ELEMENT_COLORS` (`features/document/elementColors.ts`) — `plan→table(#8B5CF6)` *(canonical violet over the handoff's #a855f7 — declared)*, `retrieve→text(#3B82F6)`, `rerank→caption(#EAB308)`, `read→section_header(#F97316)`, `verify→list(#06B6D4)`, `answer→picture(#22C55E)`, `map→formula(#EC4899)`. Badge text + bar use the base hex; badge background derives as a theme-safe tint — `color-mix(in srgb, <base> 15%, transparent)` — instead of the handoff's light-only pastel hexes. Single source of truth, matches the handoff's "derived from Studio's layer-chip palette" intent.

**Routing**: `ROUTES.REASONING`/`REASONING_DOC` removed (incl. `shared/routing/names.ts:19-20`); redirects added — `/reasoning` → `/docs`, `/reasoning/:docId` → `/docs/:docId` (mode defaults to parse); `router.test.ts` assertions flip to redirect expectations. The routes.ts comment suggests these deep links circulate among teammates — a 404 soft-fail is avoidable for one redirect line.

**`data-e2e` attributes** (Karate hooks): `ask-tab`, `props-tab`, `ask-turn-list`, `ask-turn-card`, `ask-composer-input`, `ask-composer-model`, `ask-run-btn`, `ask-run-reason`, `trace-panel`, `trace-row`, `trace-empty`, `trace-footnote`, `trace-model-chip`, `trace-stats`.

### 5.7 Cross-cutting (feature flags, i18n, shared types)

- **Feature flag**: `REASONING_ENABLED` (backend) → `/api/health` `reasoningAvailable` (already exists) → frontend gates the Ask tab + trace dock. The zombie `ASK_MODE_ENABLED`/`askModeEnabled` is removed end-to-end.
- **i18n** (`shared/i18n.ts`, fr + en): rewrite `ask.*` (composer, the three disabled reasons, running placeholder, empty state badge-2 title + sub-line, turn meta), add `trace.*` (header, chips, warming row, degraded footnote, empty-state headline + onboarding steps), purge dead `reasoning.*` + `nav.reasoning`.
- **Shared types**: none added to `shared/types.ts` — the trace contract is feature-local (`features/reasoning/types.ts`). `ReasoningStep.payload` is camelCase end-to-end (§5.1) — no casing exception needed.
- **Docs**: `docs/design/reasoning-trace.md` status → `Superseded by #303`; `experiments/reasoning-trace/README.md` notes the import UI removal + new wire shape; CHANGELOG entries (Added/Changed/Removed/BREAKING for the response shape + route removal).

## 6. Alternatives considered

### Alternative A — Keep the graph overlay as a secondary view

- **Summary:** Port the new trace contract but keep `/reasoning` + `graphReasoningOverlay` alive next to the Parse-view timeline, as a "graph lens" on the same trace.
- **Why not:** It preserves exactly what this redesign retires: the Cytoscape coupling, the `elem::{section_ref}` magic string (two source files plus their tests: `graphReasoningOverlay.ts`, `sectionParenting.ts`), the `/reasoning-graph` projection chain, and a second focus-sync implementation to maintain. The graph view answered "where in the document graph did the agent walk" — the Parse view answers it better (real page, real bboxes) with zero extra infrastructure.

### Alternative B — Project the trace in the frontend

- **Summary:** Keep the API returning raw snake_case iterations; port docling-lens's `trace_builder` to TypeScript and build `ReasoningTrace` client-side.
- **Why not:** That is v1's documented smell (duplicated parsing in `store.ts` + Pydantic schemas, drift detected at runtime). Backend projection yields one canonical, versionable contract, pytest-locked rules (truncation, duration preference), and matches the lens-validated layering. The frontend keeps zero knowledge of `RAGIteration`.

### Alternative C — Wait for upstream docling-agent (no fork pin)

- **Summary:** Block this issue on docling-project/docling-agent#39 merging and a release, then consume `run_with_trace()` from PyPI.
- **Why not:** The merge timeline is not ours. The fork pin via `[tool.uv.sources]` git rev is reproducible (uv.lock records the SHA), CI-fetchable over HTTPS, and the exit is a one-line source swap. This is the load-bearing choice captured in the proposed ADR. *(Decision made with the issue: keep the fork dependency, light refactor at merge.)*

### Alternative D — Do nothing (keep v1)

- **Summary:** Leave the graph-overlay workspace as-is.
- **Why not:** v1 is built on a retired navigation model (#209 explicitly planned "Reasoning collapses into the doc workspace"), on a private upstream API (`_rag_loop`), and on a trace model with no timing/kinds. The binding handoff exists because the product direction already moved.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| POST | `/api/documents/{docId}/reasoning` | `{ query: string, modelId?: string }` | `ReasoningTraceResponse` (below) | **Yes** — response shape replaced (internal consumer only) |
| GET | `/api/documents/{docId}/reasoning-graph` | — | — | **Removed** (only consumer was the deleted v1 frontend) |

`ReasoningTraceResponse` (camelCase via `_CamelModel`; `steps[].payload` keys are camelCase **by construction** in `trace_builder` — Pydantic does not alias dict contents):

```json
{
  "answer": "Cast Swiftmend on cooldown…",
  "converged": true,
  "totalDurationMs": 6760,
  "tokensIn": 0,
  "tokensOut": 0,
  "modelId": "granite3.3:8b",
  "steps": [
    {
      "id": "s1",
      "kind": "read",
      "title": "Scan \"Core Spells and Buffs\" for Swiftmend guidance",
      "summary": "Insufficient — 412 chars read, agent moved on.",
      "durationMs": 0,
      "tokenCount": 0,
      "citations": ["#/texts/70"],
      "payload": { "iteration": 1, "sectionRef": "#/texts/70", "reason": "…",
                   "sectionTextLength": 412, "canAnswer": false,
                   "response": "…", "durationMs": 0 }
    }
  ]
}
```

Errors (unchanged on the wire): `503` runner unwired/unavailable · `400` empty/whitespace query (typed service error preserves the current contract — DTO `min_length` would return 422 and accept whitespace) · `404` no completed analysis with `document_json` · `502` `ReasoningParseError` (model produced no parseable answer) · `500` other (e.g. Ollama unreachable). Error body: FastAPI `{"detail": "..."}`.

### Persistence schema

```sql
-- No change.
```

### Env vars / config

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `REASONING_ENABLED` | `false` | bool | unchanged; gates runner wiring → `reasoningAvailable` |
| `OLLAMA_HOST` | `http://localhost:11434` | URL | unchanged; now consumed per-backend-instance (no `os.environ` mutation) |
| `REASONING_MODEL_ID` | `gpt-oss:20b` | str | unchanged default model; injected into `ReasoningService` |
| `ASK_MODE_ENABLED` | — | — | **removed** (zombie since #263) |

### Breaking changes

1. `POST /reasoning` response: snake_case `{answer, iterations[], converged}` → camelCase `{answer, converged, steps[], totalDurationMs, tokensIn, tokensOut, modelId}`. Only consumer (v1 frontend) is deleted in the same change.
2. `GET /reasoning-graph` removed.
3. Frontend routes `/reasoning`, `/reasoning/:docId` removed — **redirects** to `/docs(/:docId)` preserve circulating deep links.
4. `askModeEnabled` disappears from `/api/health` (was never consumed; its three test assertions are removed in the same change).
5. `experiments/reasoning-trace` sidecar JSON can no longer be imported in the UI (import dialog removed).

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Fork timing commit (§5.3) slips or regresses → per-step bars degraded | Decoupling | Low | Low | Timeline shows the designed degraded state + footnote; run log prints `duration_ms=0` | Adapter reads fields via `getattr` defaults; degraded UI state is fully specced; the commit is the first implementation step, before the pin |
| mellea `0.4.2 → >=0.5` skew: `mellea.stdlib.requirements` imports / `retry_budget=` kwarg unverified | CI/Build | Medium | High (runner broken) | New CI step: `uv sync --frozen --group reasoning` + smoke import fails the backend job | Validate the resolve before committing the pin; `WITH_REASONING=false` default image unaffected |
| Fork pin re-resolves the **universal `uv.lock`** — fork 0.5.0's hard deps (full docling, boto3, pandas, pyarrow) participate in the shared resolution and can shift pins outside the reasoning group; large lock diff for every in-flight 0.7.0 branch | CI/Build | High | Medium | Lock diff touches non-reasoning packages; backend CI / docling-compat checks move | Review the lock diff for out-of-group movements; land the pin early in the 0.7.0 cycle; consider `[tool.uv]` conflict isolation if docling pins collide |
| Fork 0.5.0 drags full `docling`/torch + boto3/pandas/pyarrow into the reasoning group | CI/Build · Performance | Certain | Medium (image size, build time) | Docker build metrics on `WITH_REASONING=true` | Opt-in image only; document the delta; revisit at upstream merge (extras may slim) |
| 20–40 s blocking call per run ties a thread; no timeout/cancel; concurrent users stack threads | Performance | Medium | Medium | Slow `/reasoning` responses, thread-pool pressure in logs | Frontend single-flight (`running`); log run duration; follow-up issue for server-side semaphore/timeout |
| New `WITH_REASONING` CI job (decided in scope, §9) lengthens CI and adds a second image build; if it flakes it blocks unrelated PRs | CI/Build | Medium | Medium | CI duration metrics; job failure rate | Job builds with `--build-arg WITH_REASONING=true` but **without Ollama** (gating/empty-state scenarios only — deterministic); scoped to the `@reasoning-on` tag; can be made non-blocking (`continue-on-error`) if flaky while stabilizing |
| Trace refs don't resolve when History drawer pinned an older analysis (run targets latest) | Decoupling | Medium | Low | Citation chip click no-ops (muted state) | Graceful no-op + muted chip; `analysisId` param is a named follow-up (§3) |
| Surgical `GraphView.vue` decouple breaks the legacy `/studio` surface | Decoupling | Low | Medium | `vue-tsc` + `@critical` e2e (STUDIO_MODE) fail | Remove only reasoning-purposed surface (import/spread, `fetcher`, `nodeFocus`, `cy` expose — StudioPage uses none); run the studio e2e suite in the PR |
| Dock layout clips the preview (`height:100%` root inside `overflow:hidden`) on small viewports | Clean Code | Medium | Medium | Manual QA at 1280×800; preview unusable | Re-flex wrapper (`flex:1 1 auto; min-height:0`) + min-height floor on the preview region |
| Same-value re-click doesn't re-scroll (v1 trap regression) | Tests | Medium | Low | e2e re-click scenario fails | `focusTick` bump on every `focusElement`; tick included in all watchers; store test locks it |
| Dark-mode regression from light-only handoff palette | Documentation | Medium | Medium | Manual QA in dark theme | Tokens-only rule + tint derivation via `color-mix` (§5.6); no raw hexes; QA checklist includes dark pass |
| Plain-text mandate shows literal `**`/`1.` markdown markers in answers | Documentation | Certain | Low | Visible in answers | Accepted (binding spec); prompt-side fix tracked fork-side |
| Deleting projector tests removes incidental coverage; `GET /graph` has **no unit tests today** (covered only via `tests/neo4j/` integration) | Tests | Low | Medium | `tests/neo4j/` integration (e.g. `test_chunk_writer.py:82-113`) + `vue-tsc` + `@critical` studio e2e | Delete precisely: `test_docling_graph.py` (398 lines) + the `TestReasoningGraph` class; keep `TestPrimeEndpointRemoved`; **add** one `GET /graph` happy-path unit test with a stubbed `GraphReader` to replace the lost incidental coverage |
| New store/focus wiring leaks between docs (turns shown for another doc) | DDD | Low | Medium | Store test on `reset(docId)` | `reset` on docId change (workspace remount is keyed by id already) |

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`, flat layout — the repo convention)

- `tests/test_trace_builder.py` (ported from lens + Studio additions): iteration→READ mapping (title/summary/citations/payload **camelCase keys**), insufficient summary with/without char count, title truncation (≤96, `…`), whitespace-only reason → `Read {ref}` fallback (the declared lens divergence), per-iteration `duration_ms` on step **and** payload, `result.duration_ms` preferred over wall-clock, `result.model_id` preferred over arg, zero/empty fallbacks.
- `tests/test_docling_agent_reasoning.py` — **rewritten** for the fork surface: stub `docling_agent.agents` (`run_with_trace` returning a fake `RAGTrace`); assert constructor kwargs (`tools=[]`, backend built from `BackendConfig(type="ollama", base_url=provider.host)`); `run_with_trace(task=…, document=…)` call shape; `IndexError → ReasoningParseError`; **defensive mapping when `duration_ms`/`model_id` are absent** (the pinned-SHA reality) and present (post-fork-extension); no `os.environ` mutation.
- `tests/test_reasoning_service.py` — new: 400 (whitespace query), 404 path, wall-clock capture feeds `build_trace`, default-model injection, parse-error passthrough.
- `tests/test_reasoning_api.py` — updated: camelCase response keys (`totalDurationMs`, `steps[].durationMs`, `modelId`, `payload.canAnswer`), service wiring via `app.state`, status codes 503/400/404/502/500, model override.
- New: one `GET /graph` happy-path test with stubbed `GraphReader` (replaces incidental coverage lost with the projector tests, §8).
- Delete/adjust: `tests/test_docling_graph.py` (delete), `tests/test_graph_api.py` (`TestReasoningGraph` out, fixture loses `graph_projector`, `TestPrimeEndpointRemoved` kept), `tests/test_api_endpoints.py:87,91` (`askModeEnabled` asserts out). Architecture tests stay green (`domain/trace_builder.py` imports domain only).
- CI: the existing backend job gains `uv sync --frozen --group reasoning` + `python -c "import docling_agent.agents, mellea.stdlib.requirements"` (the §8 mellea-skew detection signal).

### Frontend — Vitest (`frontend/src/**/*.test.ts`, node env — logic in `.ts` modules, no component mounting)

- `features/reasoning/store.test.ts`: run lifecycle (running turn appended with `Reading the document…` placeholder semantics → finalized with trace/status), error path (`status: 'error'`, `errorMessage`), `selectTurn` auto-selects first step, `selectStep` drives `documentStore.focusElement` (mocked), `selectStepByCitation` reverse path + no-op, `reset(docId)` isolation.
- `features/reasoning/timeline.logic.test.ts`: cumulative offsets, uniform fallback when no timing, `hasTiming` detection, tick formatting (ms under 5 s, else s), `fmtDur` thresholds, 3px min-width floor.
- `features/reasoning/api.test.ts`: call shape (`POST /api/documents/:id/reasoning`, body `{query, modelId}`), error bubbling (apiFetch mocked).
- `features/document/store.test.ts` (extended): `focusElement` bumps `focusTick` on same-ref re-call.
- `app/router/router.test.ts`: `/reasoning(/:docId)` resolve to redirects.

### E2E — Karate UI (`e2e/ui/src/test/resources/documents/doc-ask-trace.feature`)

- Delete the stale `navigation/reasoning-feature-flag.feature` (waits on `data-e2e` hooks removed by #209).
- Scenario `@critical` — flag **off** (default CI image, runs in CI): open `/docs/:id?mode=parse`, assert `[data-e2e=ask-tab]` and `[data-e2e=trace-panel]` **absent**, `ElementProperties` rendered.
- Scenario `@critical` — redirect: navigating `/reasoning/<docId>` lands on `/docs/<docId>` parse.
- Scenario `@reasoning-on` — flag **on**: Ask tab present (Properties active by default), onboarding empty states (badge 2/3), composer Run disabled with reason `Type a question…`, enabled once text present. No live agent run (Ollama-dependent paths stay manual QA — the scenarios are deterministic without it).
- **New CI job (decided in scope, 2026-06-10)**: `ci.yml` gains an `e2e-ui-reasoning` job — builds the image with `--build-arg WITH_REASONING=true`, starts compose with `REASONING_ENABLED=true` (no Ollama service), runs the UI suite with `--tags @reasoning-on`. This is the CI executor for the flag-on scenarios (the mellea smoke-import step stays in the existing backend job, §5.3 — it needs no image).
- Conventions: `data-e2e` selectors only, `retry()`/`waitFor()`, setup via API, **never Playwright**.

### Manual QA

1. `docker compose -f docker-compose.dev.yml up` with `WITH_REASONING=true`, `REASONING_ENABLED=true`, local Ollama + `granite3.3:8b` (or `REASONING_MODEL_ID`).
2. Open a parsed doc → Parse: ask a question; verify running states (pulsing dots, "Reading the document…" placeholder, warming row, composer disabled with reason), then answer + steps.
3. Click steps: bbox highlight + page flip + ~90px top-anchored scroll; tree expands + scrolls focused row to center; Properties shows the cited element; re-click the same step → re-scrolls.
4. Click a bbox cited by a step → step selected in the timeline (reverse).
5. Dark theme pass on all new surfaces (badges, tints, kind colors); reduced-motion check (pulse off); 1280×800 viewport (dock + preview both usable).
6. Flag-off pass: Parse view identical to 0.6.2.

### Performance / load

No new hot-path work. The 20–40 s run is thread-offloaded (no event-loop blocking) — verified by the adapter test asserting `asyncio.to_thread` usage; run duration logged for observation (§10).

## 10. Rollout & observability

### Release branch

`release/0.7.0` (milestone *0.7.0 — UI Redesign Maquette*). Implementation order: **(1)** fork timing commit on `dev/rag-run-with-trace` (tests included) → **(2)** Studio pins that SHA — land the pin early in the cycle because of the universal `uv.lock` re-resolution (§8) → **(3)** backend port → **(4)** frontend + e2e + CI job. The upstream-merge refactor (PR #39) is explicitly out of this release.

### Feature flag / staged rollout

`REASONING_ENABLED=false` default → `/api/health.reasoningAvailable=false` → Ask tab + trace dock don't render; Parse is unchanged. HF Space stays off (no Ollama). Enabling = env flip + `WITH_REASONING` image; no frontend rebuild needed (flag-driven).

### Observability

- INFO log per run: `doc_id`, iteration count, `converged`, wall-clock ms, agent `duration_ms` (0 = no upstream timing — measurable signal for the fork extension)
- WARNING on `ReasoningParseError` with `model_id`
- No new metrics/counters; no `analysis_jobs` interaction (reasoning is read-only on analyses)

### Rollback plan

- **Env flip**: `REASONING_ENABLED=false` disables the feature without redeploy (UI hides, endpoint 503s).
- **No migration** to revert; no data cleanup.
- Dependency revert = restore `docling-agent==0.1.0` pin + previous adapter (single revert commit; the old code path is preserved in git history; the uv.lock diff reverts with it).
- Route redirects are additive and safe to keep even after a revert.

## 11. Open questions

All design-review questions were resolved on 2026-06-10 (decisions folded into §3/§5.3/§5.6/§9/§10):

- ~~Fork timing extension~~ → **in scope**: second fork-only commit (real Gantt bars day one), kept out of upstream PR #39; Studio pins its SHA (§5.3, §10).
- ~~`WITH_REASONING` CI job~~ → **in scope**: dedicated `e2e-ui-reasoning` job in `ci.yml` running the `@reasoning-on` tag (§9).
- ~~`experiments/reasoning-trace/` sidecar~~ → **kept**, with a README note on the import-UI removal + new wire shape (§5.7).
- ~~Default right-panel tab~~ → **Properties default**; Ask is optional, opt-in by click — amends the handoff prototype (§5.6).
- ~~Compact-density drop~~ → confirmed: ship Comfortable-only, Compact is a follow-up (§3).

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/303
- **Related PRs / commits:**
  - Upstream: https://github.com/docling-project/docling-agent/pull/39 — `run_with_trace()` (fork `pjmalandrino/docling-agent@dev/rag-run-with-trace`, pinned SHA `32622b4be90bd4247ee602e607ff316be76738ec`)
  - History: #242 (DocAskTab, deleted by #264) · #263 (ask mode dropped) · #209 (nav rework: "Reasoning collapses into the doc workspace")
- **ADRs:** proposed — "docling-agent from fork via uv git source" (file alongside the implementation PR)
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
  - Superseded design: `docs/design/reasoning-trace.md` (v1)
- **External:**
  - **Binding UI/UX handoff**: `~/Downloads/design_handoff_reasoning_trace/` (README.md = behavioral spec; prototype HTML = visual reference)
  - Reference implementation: docling-lens (`~/Documents/Pro/workspace/docling-lens`) — domain trace model, `trace_builder`, camelCase schemas

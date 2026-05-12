# Design: Linked view — preview + chunks panel + LAYERS filters

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

- **Issue:** #264
- **Title on issue:** [FEAT] Linked view — preview + chunks panel + LAYERS filters
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-05-12
- **Status:** Accepted
- **Target milestone:** 0.6.1 — Stabilisation
- **Impacted layers:** frontend (`features/document`, `features/chunks`, `pages/Doc*`, `shared/ui/PaginationBar`) · e2e
- **Audit dimensions likely touched:** Decoupling · DRY · KISS · Tests · Performance
- **ADR spawned?:** no  *(write an ADR when choosing a library, moving a boundary, or deciding **not** to do something — see `docs/architecture/adr-guide.md`)*

---

## 1. Problem

The Linked view is the default workspace view in the 0.6.1 mockup: a page preview with bbox overlays on the left, and the canonical chunk list aligned to the current page on the right. It supersedes the previous `DocChunksTab`.

This view exists to show — at a glance — the relationship between OCR elements (bboxes coloured by element type, filterable via the `LAYERS` chip row) and the canonical chunkset that drives downstream ingestion. Today, users have no way to visually correlate an OCR element with the chunk it ended up in; the chunks tab lists chunks in isolation, and the bbox overlays live elsewhere in the legacy Studio.

## 2. Goals

<!--
Concrete, verifiable outcomes. Convert the issue's acceptance criteria into
checkboxes here; the design is "done" when all are satisfied. Keep the list
small — five or fewer goals is a good smell.
-->

- [ ] Preview renders bboxes overlaid on the page image, colored per type
- [ ] LAYERS chips filter bbox visibility, with correct counts per current page
- [ ] `Show labels` toggle shows/hides the type label on each bbox
- [ ] Paginator + zoom work
- [ ] Right panel lists chunks for the active page only
- [ ] Hover chunk → highlight bbox; click bbox → scroll/highlight chunk
- [ ] LAYERS filter state survives page change
- [ ] Stale-store strip (#224) preserved
- [ ] CI green, new component tests, e2e scenario for the link interaction

## 3. Non-goals

- **Zoom control above the preview** — visible in the mockup top-right, deferred (open question §11). The first cut renders the image at container width; zoom lands once we know the interaction model (slider? wheel? +/-?).
- **`Strategy` popover internals** — wired as an inert button in T3; tracked separately as **T7 / #268**.
- **`History` / `+ New analysis` / `Export` right-side action buttons** — slot stub only; tracked as **T6 / #267** (History), **T5 / #266** (New analysis), and out-of-scope chore (Export).
- **Replacing `ChunksEditor` and its bulk-merge / split / push / diff toolbar** — kept on disk and referenced by **#91 / #92 / #95** for follow-up; the Linked view only mounts the slimmer `ChunksPanel`.
- **Consolidating `BboxCanvas` with the existing `BboxOverlay` / `StructureViewer`** — explicitly deferred until T4 ships so the consolidation is informed by two real callers, not one. Tracked as a follow-up cleanup ticket to file *after* T4.
- **Inspect view** — its `Structure` rail + `Properties` panel are **T4 / #265**; the Linked view does not render a tree.
- **Backend changes** — none. The design rejects a "workspace aggregate" route on purpose (P2/P3 rule).

## 4. Context & constraints

### 4.1 Existing code surface — audit

The Linked view is a **frontend-only** refactor (no backend changes). Endpoints, DTOs, and services it needs already exist on `release/0.6.1`. The audit below classifies the existing surface as **keep / refactor / supersede / leave-alone**.

#### Backend (audit only — nothing to change)

| Endpoint | Status | Why |
|---|---|---|
| `GET /api/documents/{id}` | keep | Doc metadata for the header |
| `GET /api/documents/{id}/preview?page=N&dpi=150` | keep | Page image source |
| `GET /api/documents/{id}/chunks` | keep | Canonical chunkset (`DocChunkResponse[]`, carries `sourcePage`) |
| `GET /api/documents/{id}/tree` | keep but **unused by Linked** | Used by Inspect (T4), not Linked |
| `GET /api/analyses?documentId=X` | keep | Source of `pages_json` → element bboxes by type (the chips' counts) |

No new endpoint, no new service. Per the project's P2/P3 rule: the orchestration "fetch doc + fetch chunks + fetch latest analysis" lives in the **frontend store**, not in a new "DocumentWorkspaceService" on the backend.

#### Frontend — feature `features/document/`

| File | Status | Action |
|---|---|---|
| `api.ts` (41 lines) | keep | Already exposes `fetchDocument`, `getPreviewUrl`, `fetchDocumentTree`, `rechunkDocument` |
| `store.ts` (105 lines) | **refactor** | Add a `loadWorkspace(docId)` action that orchestrates doc + latest-analysis + chunks load |
| `ui/PagePreview.vue` (124 lines) | **leave-alone** | Used by Studio (`AnalysisPanel`) — keep its surface stable. Linked view introduces a new composite (preview + overlay + paginator + zoom) rather than extending this one. |
| `ui/DocTreeRail.vue` + `DocTreeNode.vue` | **leave-alone for T3** | Used by current `DocChunksTab`. T3 *drops* it from the Linked layout; T4 reuses it in Inspect. The components themselves don't change. |
| `ui/DocWorkspaceHeader.vue` | keep, slot-extended in T2 already | T3 will inject more actions in the `actions` slot (History / Export / + New analysis), but those land via T5 / T6. For now: switcher only (T2). |

#### Frontend — feature `features/chunks/`

| File | Status | Action |
|---|---|---|
| `api.ts` (60 lines) | keep | Full chunk CRUD + diff + push already wired |
| `store.ts` (175 lines) | **refactor** | Add a derived getter `chunksOnPage(page)` (pure filter on `sourcePage`). No state change. |
| `ui/ChunksEditor.vue` (618 lines) | **supersede in Linked, keep for now** | Today's chunks tab uses it as the right pane. Linked view ships a slimmer `ChunksPanel.vue` (page-scoped cards, inline edit). `ChunksEditor` is **not deleted in this PR** — it still hosts the bulk-merge / split / push / diff toolbar that #91 / #92 / #95 will refactor. We mark it as "no longer mounted by the doc workspace" and let the dedicated tickets decide its fate. |
| `ui/ChunkItem.vue` (382 lines) | keep, **refactor** | Already the card primitive (type badge, seq, `edited`, token count, inline editor). T3 reuses it inside `ChunksPanel`. |
| `ui/StaleStoresStrip.vue` | keep | #224 — Linked view keeps the strip above the chunks panel |

#### Frontend — feature `features/analysis/`

This whole feature is the Studio surface today, gated by `studioMode` (#257). For T3 we **lift the bbox-canvas primitive out** without coupling Linked to the Studio shell.

| File | Status | Action |
|---|---|---|
| `bboxScaling.ts` (54 lines) | keep, **reuse** | Pure helpers (`computeScale`, `bboxToRect`, `pointInRect`). Move out of `features/analysis/` to `features/document/` (or `shared/`) since it is consumed by both surfaces. **Refactor: relocate + update imports.** |
| `ui/BboxOverlay.vue` (323 lines) | **leave-alone** | Studio-only component. Has its own embedded legend, coupled to Studio's `pageData` shape — too opinionated to share. |
| `ui/StructureViewer.vue` (447 lines) | **leave-alone** | Used by `InspectResultTabs` (Studio's Inspect tab, behind `studioMode`). Also includes reasoning-trace overlays — heavy, off-topic. **Do not import in Linked.** Will be replaced by T4's new Inspect layout (mockup-driven). |
| `ui/AnalysisPanel.vue`, `ResultTabs.vue`, `MarkdownViewer.vue`, `ImageGallery.vue`, `GraphView.vue`, `NodeDetailsPanel.vue`, `InspectResultTabs.vue` | **leave-alone** | All Studio surface. Not touched. |
| `legendFilters.ts` (108 lines) | **leave-alone** | Cytoscape graph legend chips — different concept than LAYERS bar (which counts OCR element types). Do not reuse. |
| `api.ts`, `store.ts` | keep | Linked view's orchestrator calls `fetchAnalysesByDoc(docId)` to obtain `pages_json` → element bboxes |

**Why a new `BboxCanvas` instead of reusing `BboxOverlay` / `StructureViewer`:** both existing canvases embed a legend, own their own hidden-types state, and are coupled to specific data shapes (Studio's `Page` with `elements`, reasoning's `visitedBySelfRef`). Linked needs an **externally-controlled** canvas — chip state lives in the LAYERS bar, hover/click events bubble up to the page. Trying to bend the legacy components to also serve the new shape would be cheaper short-term but leaves two divergent canvases. We accept the duplication cost in this PR and revisit consolidation **after** T4 ships (when both new views exist and the shared shape is observable from real callers).

#### Frontend — shared

| File | Status | Action |
|---|---|---|
| `shared/ui/PaginationBar.vue` (135 lines) | **reuse** | Already provides the chip-paginator pattern (Page X of Y, numeric chips). Used by `DocsLibraryPage`. T3 mounts it above the preview. |
| `shared/composables/usePagination.ts` (71 lines) | **reuse** | Pure pagination state composable |
| `shared/types.ts` | keep | `Page`, `PageElement`, `ChunkBbox`, `DocChunk` already defined |
| `shared/i18n.ts` | extend | Add `linked.*` keys (chips, "Show labels", counts, Strategy placeholder) |

#### Page level

| File | Status | Action |
|---|---|---|
| `pages/DocChunksTab.vue` (139 lines) | **rename + restructure** → `pages/DocLinkedTab.vue` | Mount the new Linked layout (LAYERS bar + preview-with-overlay + paginator + ChunksPanel). Drop the `DocTreeRail` from this page (moves to T4's Inspect). Update the import in `DocWorkspacePage.vue`. |
| `pages/DocWorkspacePage.vue` | minor edit | Switch the `v-if="activeMode === 'linked'"` block from `<DocChunksTab>` to `<DocLinkedTab>` |
| `pages/DocAskTab.vue` | **delete** | Unimported since T2 (dropped from the workspace). Per "no dead code left after" — remove the file. Ask logic lives in the standalone `/reasoning` page; nothing else references this tab. |

### 4.2 Hexagonal Architecture constraints (backend)

Not touched. No new ports, no new adapters, no service changes. The frontend orchestrates the existing services through their HTTP boundary.

### 4.3 Deployment modes

- `latest-local` and `latest-remote`: both supported. The view consumes `pages_json` which is produced by both engines (the converter is the only difference upstream).
- HuggingFace Space: supported. No new env var, no rate-limited endpoint.
- Studio surface (`STUDIO_MODE_ENABLED`): the Linked view is part of the RAG pipeline surface (`RAG_PIPELINE_ENABLED=true`) and is gated by `linkedModeEnabled` (sub-flag of RAG pipeline, default `true`).

### 4.4 Hard constraints

- **Bookmark stability**: `?mode=chunks` must continue to resolve to the Linked view (alias landed in T2 via `parseMode`).
- **SQLite schema**: no changes.
- **API contract**: no breaking change — only consumes existing endpoints with their existing shape.
- **File-size budget**: per `docs/architecture/coding-standards.md`, target ≤ 300 lines/file. The new components (`BboxCanvas`, `LayersBar`, `PagePreviewWithOverlay`, `ChunksPanel`) each fit in ≤ 200 lines.
- **Performance budget**: bbox redraw must run inside one `requestAnimationFrame` on a typical page (≤ 200 elements). Re-draw triggers: page change, zoom change, hidden-types change, hovered-chunk change.

## 5. Proposed design

<!--
The recommended approach, in enough detail that a competent engineer
outside the immediate context can implement it. Describe contracts, not
code — the PR is where code lives.

Structure this section by layer. Skip a layer if it is genuinely untouched;
do not pad.

### 5.1 Domain
New or changed dataclasses / value objects / ports in `document-parser/domain/`.
No HTTP or DB concerns here. If you are adding a port (`Protocol`), give its
full signature.

### 5.2 Persistence
Schema changes (table, columns, indexes), migration plan, aiosqlite query
shape. Note whether existing rows need a backfill.

### 5.3 Infra adapters
New or changed adapters in `document-parser/infra/` (converter, chunker,
rate limiter, settings). For new env vars, give name / default / allowed
values.

### 5.4 Services
Use-case orchestration in `document-parser/services/`. Services do NOT
implement — they delegate. Describe the call sequence, error handling,
and concurrency (how does this interact with `MAX_CONCURRENT_ANALYSES`?).

### 5.5 API
Endpoint additions / changes in `document-parser/api/`. For each:
  - Method + path
  - Request DTO (Pydantic, camelCase via alias_generator)
  - Response DTO (camelCase; remember `pages_json` stays snake_case)
  - Error responses (status codes, shape)
  - Whether it is excluded from the rate limiter (like `/api/health`)

### 5.6 Frontend — feature module
Which `frontend/src/features/<name>/` folder, which Pinia store actions,
which API client calls in `api.ts`, which Vue components in `ui/`. Name
new `data-e2e` attributes here (Karate needs them).

### 5.7 Cross-cutting
Feature flags (how the backend advertises capability via `/api/health` and
how the frontend reacts), i18n strings (`shared/i18n.ts`), shared types
(`shared/types.ts`).

Prefer mermaid / ASCII for sequence and data flow. Interfaces are more
valuable than pseudocode.
-->

### 5.1 Domain

Not touched.

### 5.2 Persistence

Not touched.

### 5.3 Infra adapters

Not touched.

### 5.4 Services

Not touched. Existing services (`ChunkService.list_chunks`, `ChunkService.get_tree`, `AnalysisService.find_latest_completed_by_document`) are consumed as-is.

### 5.5 API

Not touched. The Linked view composes existing routes:

```
GET /api/documents/{id}                  → DocumentResponse
GET /api/documents/{id}/preview?page=N   → image/jpeg
GET /api/documents/{id}/chunks           → DocChunkResponse[]
GET /api/analyses?documentId={id}        → AnalysisResponse[]   (frontend picks the latest completed)
```

No new endpoint. The "compose them in one shot" temptation is explicitly rejected — per the project's P3 rule, multi-call orchestration belongs in the frontend store, not in a UX-shaped backend route.

### 5.6 Frontend — feature module

#### 5.6.1 Orchestration (`features/document/store.ts`)

Add a single workspace-load action that fetches the three concerns and exposes them as refs. Nothing fancy; sequencing is parallel.

```ts
// new action
async function loadWorkspace(docId: string) {
  workspaceLoading.value = true
  workspaceError.value = null
  try {
    const [doc, analyses] = await Promise.all([
      api.fetchDocument(docId),
      analysisApi.fetchAnalysesByDoc(docId),
    ])
    workspaceDoc.value = doc
    workspaceLatestAnalysis.value =
      analyses.find((a) => a.status === 'completed') ?? null
    // Chunks load is triggered separately by the chunks store —
    // keeps the two stores independently testable.
  } catch (e) {
    workspaceError.value = (e as Error).message
  } finally {
    workspaceLoading.value = false
  }
}
```

New refs on the store: `workspaceDoc`, `workspaceLatestAnalysis`, `workspaceLoading`, `workspaceError`. The existing `documents` / `loading` / `selectedId` refs (library listing) stay untouched.

`pages_json` is parsed lazily via a computed `workspacePages = computed(() => parsePages(workspaceLatestAnalysis.value?.pagesJson))` so the page array is memoized and the parse error is non-fatal.

#### 5.6.2 Chunks store extension (`features/chunks/store.ts`)

Add one pure getter:

```ts
const chunksOnPage = computed(() => (page: number) =>
  chunks.value.filter((c) => c.sourcePage === page),
)
```

That's it. No new state, no new action.

#### 5.6.3 New shared helper — relocate `bboxScaling.ts`

Move `frontend/src/features/analysis/bboxScaling.ts` → `frontend/src/features/document/bboxScaling.ts`. Update imports in `BboxOverlay.vue` and `StructureViewer.vue` (Studio surface) to point at the new path. No behavioral change.

Rationale: the helper is pure and consumed by both surfaces — keeping it under `features/analysis/` made sense when Studio was the only consumer. With the Linked view it becomes a `document/`-feature concern.

#### 5.6.4 New components

All under `frontend/src/features/document/ui/` unless noted.

**`BboxCanvas.vue`** (~150 lines) — pure canvas overlay.

Props:
- `imageEl: HTMLImageElement | null` — measured target
- `elements: PageElement[]` — bboxes to draw
- `hiddenTypes: ReadonlySet<string>` — externally controlled (no internal state)
- `highlightedRefs?: ReadonlySet<string>` — element `self_ref`s to emphasize (chunk-hover linking)
- `showLabels: boolean`
- `colors: Readonly<Record<string, string>>` — type → CSS color

Emits:
- `hoverElement: [el: PageElement | null]`
- `clickElement: [el: PageElement]`

No legend, no hidden-types reactive state, no tooltips (tooltip is the parent's job). The whole component is one canvas + draw routine + hit-test routine.

**`LayersBar.vue`** (~120 lines) — chips + `Show labels` toggle.

Props:
- `elements: PageElement[]` — current page (for counts)
- `hiddenTypes: ReadonlySet<string>` (v-model)
- `showLabels: boolean` (v-model)
- `colors: Readonly<Record<string, string>>`

Emits `update:hiddenTypes`, `update:showLabels`. Renders one chip per type (including the zero-count ones from the mockup — `formula 0`, `caption 0`), with the type swatch + count + a dimmed state when hidden. Toggle button on the right.

The `ELEMENT_COLORS` constant lives in a tiny `frontend/src/features/document/elementColors.ts` module so `BboxCanvas`, `LayersBar`, and `ChunksPanel` (for the type badge) share one source of truth.

**`PagePreviewWithOverlay.vue`** (~180 lines) — composite: paginator + image + canvas.

Props:
- `documentId: string`
- `pages: Page[]`
- `currentPage: number` (v-model)
- `hiddenTypes: ReadonlySet<string>`
- `showLabels: boolean`
- `highlightedRefs?: ReadonlySet<string>`

Emits: `update:currentPage`, plus pass-through `hoverElement` / `clickElement` from the canvas.

Composes `PaginationBar` (top), `<img>` + `BboxCanvas` (center, absolute-positioned over the image). Does *not* embed the zoom control yet — zoom is **out of scope** for the first cut (open question §11). For now the image fills its container width with `width: 100%`, mirroring the existing `PagePreview` behavior.

**`ChunksPanel.vue`** (~150 lines) — under `frontend/src/features/chunks/ui/`.

Props:
- `docId: string`
- `currentPage: number`
- `availableStores: string[]` (passed through for the inline `Push` reuse later)
- `hoveredChunkId?: string | null` (v-model — when a chunk card is hovered, the parent uses this to drive `highlightedRefs` on the canvas)
- `selectedChunkId?: string | null` (v-model — when a bbox is clicked, the parent scrolls the matching chunk into view)

Renders a header (`N of M on page X`, `Strategy` placeholder button) + a scrollable list of `ChunkItem` cards filtered to `chunksOnPage(currentPage)`. The `Strategy` button is wired but inert (T7 fills it in). Edit, save, drop call into the existing `chunksStore` actions — no new wire-up.

#### 5.6.5 New page — `DocLinkedTab.vue`

Replaces `DocChunksTab.vue`. Roughly 200 lines.

Layout:

```
┌──────────────────────────────────────────────────────────────┐
│ <LayersBar v-model:hiddenTypes v-model:showLabels …>         │
├───────────────────────────────────────────────┬──────────────┤
│ <PagePreviewWithOverlay                       │ <StaleStores │
│   v-model:currentPage                         │  Strip>      │
│   :hidden-types :show-labels                  │ <ChunksPanel │
│   :highlighted-refs                           │   :doc-id    │
│   @hover-element @click-element               │   :current-  │
│ />                                            │   page       │
│                                               │   v-model:   │
│                                               │   hovered    │
│                                               │   v-model:   │
│                                               │   selected   │
│                                               │ />           │
└───────────────────────────────────────────────┴──────────────┘
```

The page owns the cross-linking state: `hoveredChunkId`, `selectedChunkId`, `hoveredElementRef`. Two small mapping helpers (pure, in a new `linkedView.ts` module next to the page or under `features/document/`) compute:
- `chunkForElement(element, chunks): DocChunk | null` — finds the chunk whose bboxes intersect with the element's bbox
- `elementsForChunk(chunk, page): PageElement[]` — finds elements whose `self_ref` matches, or whose bbox overlaps

These two helpers are the entire "two-way linking" logic and are unit-tested in isolation.

#### 5.6.6 File renames / deletions in this PR

| Action | Path | Reason |
|---|---|---|
| Rename | `pages/DocChunksTab.vue` → `pages/DocLinkedTab.vue` | Match the mode |
| Restructure | (the file above) | Drop `DocTreeRail`, replace `ChunksEditor` with new `ChunksPanel` |
| Delete | `pages/DocAskTab.vue` | Unimported since T2, no other reference — per user rule "no dead code left" |
| Move | `features/analysis/bboxScaling.ts` → `features/document/bboxScaling.ts` (+ `.test.ts`) | Consumer parity (Studio + Linked) |
| Update import | `features/analysis/ui/BboxOverlay.vue`, `features/analysis/ui/StructureViewer.vue` | Follow the relocation |
| Update import | `pages/DocWorkspacePage.vue` | `DocChunksTab` → `DocLinkedTab` |

`ChunksEditor.vue` and `DocTreeRail.vue` / `DocTreeNode.vue` are **kept** — they have other planned consumers (T4 Inspect for the tree; #91 / #92 / #95 for the editor). Documenting that decision in §3 prevents follow-up auditors from flagging them as orphans.

### 5.7 Cross-cutting (feature flags, i18n, shared types)

#### Feature flags

Already covered by T1 / T2:
- `RAG_PIPELINE_ENABLED` (master) — gates the whole RAG surface
- `LINKED_MODE_ENABLED` (sub-flag) — gates the Linked view inside the workspace
- No new flag introduced by T3.

#### i18n

Add to `frontend/src/shared/i18n.ts` (en + fr):

```
linked.showLabels       'Show labels' / 'Afficher les libellés'
linked.layersTitle      'LAYERS' / 'LAYERS'                          (uppercased label, language-neutral)
linked.chunks.header    '{n} of {total} on page {page}' / '{n} sur {total} en page {page}'
linked.chunks.strategy  'Strategy' / 'Stratégie'                     (button label; popover is T7)
linked.empty            'No analysis yet — run a parse first.' / 'Aucune analyse — lancez une analyse.'
```

Element-type chip labels are kept raw (`section_header`, `text`, `table`, etc.) to match the mockup and the canonical OCR vocabulary; not translated.

#### Shared types

No new shape — `Page`, `PageElement`, `ChunkBbox`, `DocChunk` already cover the data.

## 6. Alternatives considered

<!--
At least two genuine alternatives, each with a one-paragraph description
and the reason it was rejected. "Do nothing" is often a legitimate
alternative — name it if it is. Reviewers use this section to sanity-check
that the recommended design was a choice and not the first thing that
came to mind.

If one of the alternatives represents a significant architectural fork
(e.g. introducing a new service, replacing a library), spawn an ADR under
`docs/architecture/adrs/` and link it in §12 — the design doc captures the
local decision, the ADR captures the cross-cutting one.
-->

### Alternative A — <name>

- **Summary:**
- **Why not:**

### Alternative B — <name>

- **Summary:**
- **Why not:**

## 7. API & data contract

<!--
Make the wire contract explicit — this is what the frontend, e2e tests,
and any external consumer will code against.

### Endpoints
| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
|        |      |         |          |           |

Remember:
  - API serialization is camelCase (Pydantic `alias_generator`).
  - Backend internals stay snake_case.
  - `pages_json` is the documented exception — it carries raw
    `dataclasses.asdict()` output (snake_case).
  - Health endpoint (`/api/health`) may need new fields if this design adds
    a feature flag.

### Persistence schema
```sql
-- ALTER TABLE / CREATE TABLE statements, with reasoning
```

### Env vars / config
| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
|      |         |         |       |

### Breaking changes
Enumerate anything a consumer must change. If there are none, say so
explicitly — "additive only" is a useful commitment.
-->

## 8. Risks & mitigations

<!--
One row per non-trivial risk. Map each to an audit dimension so the
release-gate audit has a clear hook:

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|-----------|--------|---------------|------------------------|
|      | Security        |           |        |               |                        |
|      | Performance     |           |        |               |                        |
|      | Decoupling      |           |        |               |                        |

Common families to scan for:
  - **Hexagonal Architecture:** cross-layer imports, leaking HTTP into domain, adapter bypassing its port
  - **Security:** rate limiter bypass, path traversal on uploads, SSRF via
    the remote converter, unauthenticated data exposure
  - **Performance:** synchronous work on the FastAPI event loop,
    unbounded queries, new work inside `MAX_CONCURRENT_ANALYSES` budget
  - **Tests:** coverage gap on a critical path
  - **Documentation:** missing README / env var / i18n entry

A design with "no risks identified" is a design that has not been read
carefully.
-->

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Bbox redraw janks on docs with many elements per page (≥ 500) | Performance | Med | Med | Visible lag on hover/page change | Throttle redraw to one `requestAnimationFrame`; precompute scaled rects on page change; skip the second pass when no highlight |
| Two bbox-canvas implementations coexist (new `BboxCanvas` + legacy `BboxOverlay`/`StructureViewer`) | DRY · Decoupling | High | Low | Audit follow-up | Documented in §3 as a deliberate deferral; consolidation ticket filed after T4 |
| Chunk↔element mapping (`chunkForElement`) is heuristic (bbox overlap) and may pick the wrong chunk when bboxes nest | Clean Code · Tests | Med | Med | Hovering a multi-bbox chunk highlights the wrong element | Prefer exact `self_ref` match when available on `chunk.bboxes`; fall back to overlap with a min-coverage threshold; unit-test corner cases |
| Latest-analysis fetch on every workspace mount adds a round-trip vs the old chunks tab | Performance | Low | Low | Network panel; perceived load time | Parallelize with the doc fetch (`Promise.all` already in §5.6.1); memoize on the store keyed by `docId` |
| `pages_json` parse failure leaves the overlay empty without a clear message | Documentation · Tests | Low | Low | Empty canvas, no error toast | The store catches `JSON.parse` and exposes `workspaceError`; `LayersBar` shows an empty state when `pages.length === 0`; covered by unit test |
| Bookmark `?mode=chunks` regresses after the rename to `linked` | Tests | Low | Med | A user reports a stale bookmark fails | Alias already landed in T2 (`parseMode`); covered by `router.test.ts` |
| Deleting `DocAskTab.vue` strands a test or unused import | Clean Code · Tests | Low | Low | CI fails or grep finds a reference | Grep before deletion (verified during this scaffold; only the workspace imported it, dropped in T2); run full test suite |

## 9. Testing strategy

### Backend — pytest

Not touched. Existing suites for `ChunkService`, `AnalysisService`, `/api/documents/{id}/chunks` (#256), and `/api/analyses` cover the contracts this design consumes.

### Frontend — Vitest

| Scope | File | Coverage |
|---|---|---|
| Pure helper | `features/document/bboxScaling.test.ts` (existing, relocated) | Already covered |
| New pure helper | `features/document/linkedView.test.ts` (new) | `chunkForElement` exact-match + overlap fallback; `elementsForChunk` |
| Store | `features/document/store.test.ts` (extend) | `loadWorkspace` parallel fetch, error path, `workspacePages` computed parse |
| Store | `features/chunks/store.test.ts` (extend) | `chunksOnPage` getter — empty page, multi-page split, `sourcePage: null` chunks |
| Component | `features/document/ui/LayersBar.test.ts` (new) | Chip count math, hidden-types v-model, `Show labels` toggle |
| Component | `features/document/ui/BboxCanvas.test.ts` (new) | Hit-test (`pointInRect` integration), hover emit, hidden-types filtering |
| Component | `features/chunks/ui/ChunksPanel.test.ts` (new) | Page-scoped filter, hover/select v-model |

Mocks: `apiFetch` mocked at module boundary as in the existing suite; canvas operations covered by hit-test arithmetic, not by snapshotting pixels.

### E2E — Karate UI

New scenario in `e2e/ui/src/test/resources/documents/doc-linked-view.feature`:

- **Setup via API:** upload PDF + run analysis + assert chunks exist (existing helpers).
- **Verify via UI:**
  1. Navigate to `/docs/{id}?mode=linked` → `data-e2e="layers-bar"` visible, `data-e2e="chunks-panel"` visible
  2. Click a `data-e2e="layer-chip-text"` → `data-e2e="bbox-canvas"` re-rendered with no `text` rectangles (assertion via screenshot diff or by checking the chip's `aria-pressed`)
  3. Hover `data-e2e="chunk-card-{id}"` → expect the linked element bbox to carry `data-highlighted` (synthetic attr we toggle for testability)
  4. Click on the `Show labels` toggle → labels visible / hidden
- **Cleanup via API:** delete the doc.

Tag `@critical @ui` per `e2e/CONVENTIONS.md`. No Playwright.

### Manual QA

1. `docker-compose.dev.yml up` (or `uvicorn` + `npm run dev`).
2. Upload a multi-page PDF, wait for `Parsed`.
3. Open `/docs/{id}` — defaults to Linked view.
4. Toggle each LAYERS chip — confirm bbox visibility + chip count match.
5. Toggle `Show labels` — labels appear/disappear on each bbox.
6. Click pagination chips — preview + chunks panel both follow the page.
7. Hover a chunk card — its element bboxes get the highlight stroke.
8. Click a bbox on the preview — the matching chunk card scrolls into view + selects.
9. Open `/docs/{id}?mode=chunks` (legacy bookmark) — same view loads, URL gets normalized to `mode=linked`.

### Performance / load

Manual smoke on a 50-page doc with ~150 elements/page. Acceptance: page-change → first paint < 250 ms on a warm cache; hover-redraw < 16 ms. No automated perf gate in this PR.

## 10. Rollout & observability

<!--
How this change gets to production safely.

### Release branch
Which `release/X.Y.Z` is the target? Any coordination with a parallel
release (e.g. R&D branch)?

### Feature flag / staged rollout
Does the change hide behind a flag surfaced via `/api/health`? If so, what
flips the flag, and what is the default? HF Space deployments often need
`deploymentMode === 'huggingface'` gating.

### Observability
  - Logs to add / extend (structured, low-cardinality keys)
  - Metrics / counters (if added — call out any new Prometheus names)
  - New error modes to watch for in `analysis_jobs.status = FAILED`

### Rollback plan
The revert that is safe to apply at any time:
  - Which migration is reversible? Which is not?
  - Which env var flip disables the feature without a redeploy?
  - Any data cleanup needed after rollback?

Link to the existing release / ops playbooks:
  - Deployment: `docs/release/*` (also surfaced via `/release:deploy`)
  - Rollback: also surfaced via `/release:rollback`
  - Incident: `docs/operations/*` (also surfaced via `/ops:incident`)
-->

## 11. Open questions

- **Zoom control** — the mockup shows `100%` on the top-right. Slider, +/- buttons, or wheel-zoom? Defer the interaction model to a follow-up; first cut ships without zoom.
- **Chunk↔element mapping data source** — is `chunk.bboxes[].self_ref` populated upstream by the chunker today, or do we have to fall back to bbox overlap unconditionally? **Action:** verify on a real doc before §5.6.5's `chunkForElement` lands; the test fixture under `e2e/` is the cheapest way to check.
- **Color palette** — current `ELEMENT_COLORS` in `BboxOverlay` covers `title, section_header, text, table, picture, list, formula, code, caption`. Mockup uses similar hues but the exact mapping isn't pinned. **Action:** match the mockup screenshot in code-review; track a Figma export if it diverges.
- **`Strategy` button affordance** — does the inert state in T3 render as a disabled button, a tooltip-only icon, or a normal-looking button that opens a "coming in T7" toast? Lean toward disabled button with a tooltip, mirroring T2's Compare treatment.

## 12. References

<!--
Links to everything a future reader would want.
-->

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/264
- **Related PRs / commits:**
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
- **External:** Mockup PDF `Docling Studio — Document Detail (Light).pdf` (page 1)

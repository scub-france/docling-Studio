# Design: Document-centric routing

- **Issue:** #207
- **Title on issue:** [FEATURE] Document-centric routing (/docs, /docs/:id?mode=, /index/:store, /runs)
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** frontend: app/router · pages · shared
- **Audit dimensions likely touched:** Clean Code · Tests · Documentation
- **ADR spawned?:** no

---

## 1. Problem

The current Vue Router (`frontend/src/app/router/index.ts`) is **analysis-centric**: routes are `/studio`, `/documents`, `/search`, `/reasoning`, `/history`. The selected document is held in a Pinia store, not in the URL — so two engineers cannot share a link to "the chunks editor for doc X". This breaks the killer flow ("paste this URL → fix the chunks → re-ingest") that 0.6.0 promises.

The 0.6.0 sitemap puts the document at the centre of every URL: `/docs`, `/docs/:id?mode=ask|inspect|chunks`, plus `/index/:store` for stores and `/runs` for the run history. Mode is a query param so a doc URL stays stable across mode switches.

This issue ships the routing skeleton. The actual page contents come in E3 (`/docs` library — #211), E4 (workspace shell — #216), E5 (chunks editor — #218 onward).

## 2. Goals

- [ ] Add `/docs`, `/docs/new`, `/docs/:id`, `/index`, `/index/:store`, `/index/:store/query`, `/runs`, `/runs/:id` routes.
- [ ] On `/docs/:id`, `?mode=ask|inspect|chunks` is parsed; default = `ask`.
- [ ] Each new route renders a placeholder page (clear "Coming in 0.6.0" message) until E3/E4/E5 implement them.
- [ ] Legacy routes (`/studio`, `/documents`, `/history`, `/search`, `/reasoning`) keep working — no breaking redirect in this issue.
- [ ] Smoke test: each new route renders without error.

## 3. Non-goals

- Building the actual pages — that is E3 / E4 / E5.
- Migrating users from old routes — kept functional in parallel; deprecation comes when the new pages are ready.
- Server-side route enforcement — backend exposes its API on `/api/*`; the routing here is client-side only.
- A site map / generated nav — the sidebar nav rework is **#209**.
- Feature-flag-aware redirection (e.g. mode disabled → redirect to default) — that is **#210**.

## 4. Context & constraints

### Existing code surface

- `frontend/src/app/router/index.ts` — current Vue Router setup (history mode, lazy-loaded pages).
- `frontend/src/pages/` — existing pages (`HomePage.vue`, `StudioPage.vue`, `DocumentsPage.vue`, `HistoryPage.vue`, `SearchPage.vue`, `ReasoningPage.vue`, `SettingsPage.vue`).
- `frontend/src/app/App.vue` — shell with topbar + sidebar + `<RouterView />`.
- `frontend/src/features/feature-flags/` — flag store and `useFeatureFlag` composable.

### Hard constraints

- TypeScript strict — every new route needs a typed `name`.
- No regression on existing routes — old URLs keep returning their current pages until #211 / #216 explicitly replace them.
- Lazy loading is preserved — every new page goes through `() => import(...)`.

### Deployment modes

Same routing for both `latest-local` and `latest-remote`. No HF Space-specific concern.

## 5. Proposed design

### 5.1 Router additions

Append to `frontend/src/app/router/index.ts`:

```ts
{ path: '/docs', name: 'docs-library',
  component: () => import('@/pages/DocsLibraryPage.vue') },
{ path: '/docs/new', name: 'docs-new',
  component: () => import('@/pages/DocsNewPage.vue') },
{ path: '/docs/:id', name: 'doc-workspace',
  component: () => import('@/pages/DocWorkspacePage.vue'),
  props: route => ({ id: route.params.id, mode: parseMode(route.query.mode) }) },
{ path: '/index', name: 'stores-list',
  component: () => import('@/pages/StoresListPage.vue') },
{ path: '/index/:store', name: 'store-detail',
  component: () => import('@/pages/StoreDetailPage.vue'),
  props: true },
{ path: '/index/:store/query', name: 'store-query',
  component: () => import('@/pages/StoreQueryPage.vue'),
  props: true },
{ path: '/runs', name: 'runs',
  component: () => import('@/pages/RunsPage.vue') },
{ path: '/runs/:id', name: 'run-detail',
  component: () => import('@/pages/RunDetailPage.vue'),
  props: true },
```

### 5.2 Mode parser

A pure helper in `frontend/src/shared/routing/modes.ts`:

```ts
export type DocMode = 'ask' | 'inspect' | 'chunks'
const DEFAULT_MODE: DocMode = 'ask'

export function parseMode(raw: unknown): DocMode {
  return raw === 'inspect' || raw === 'chunks' ? raw : DEFAULT_MODE
}
```

This is intentionally tiny and testable. #210 will extend it with feature-flag-aware redirection.

### 5.3 Placeholder pages

Each new page is ~30 lines of Vue: a centered card with the page title, a "Coming in 0.6.0" tagline, and a link back to home. They use the existing `useI18n()` strings under a new `comingSoon.*` namespace.

### 5.4 Router types

`frontend/src/shared/routing/names.ts` exports a typed union of route names so callers do `router.push({ name: ROUTES.DOC_WORKSPACE, params: { id } })` instead of stringly-typed names.

```ts
export const ROUTES = {
  HOME: 'home',
  DOCS_LIBRARY: 'docs-library',
  DOCS_NEW: 'docs-new',
  DOC_WORKSPACE: 'doc-workspace',
  STORES_LIST: 'stores-list',
  STORE_DETAIL: 'store-detail',
  STORE_QUERY: 'store-query',
  RUNS: 'runs',
  RUN_DETAIL: 'run-detail',
  // ...legacy names kept as-is
} as const
export type RouteName = (typeof ROUTES)[keyof typeof ROUTES]
```

### 5.5 i18n

New keys under `comingSoon.*` in `frontend/src/shared/i18n.ts` (fr + en):

- `comingSoon.title`
- `comingSoon.subtitle.docsLibrary`
- `comingSoon.subtitle.docsNew`
- `comingSoon.subtitle.docWorkspace`
- `comingSoon.subtitle.stores`
- `comingSoon.subtitle.storeDetail`
- `comingSoon.subtitle.storeQuery`
- `comingSoon.subtitle.runs`
- `comingSoon.subtitle.runDetail`
- `comingSoon.backHome`

## 6. Alternatives considered

### Alternative A — Replace existing routes immediately

- **Summary:** Make `/studio` and `/documents` redirect to the new routes in this issue.
- **Why not:** The new pages do not exist yet. Redirecting now means the user lands on a "Coming soon" page where they used to have a working app.

### Alternative B — Hash-mode routing

- **Summary:** Switch to `createWebHashHistory` for the new doc-centric routes.
- **Why not:** History mode is the existing convention and SPA deep-linking still works behind Nginx (already configured). No reason to mix modes.

## 7. API & data contract

No backend changes. The routes are entirely client-side. No env vars.

### Breaking changes

None. Additive.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Placeholder pages confuse users who land on them via shared links | Documentation | Medium | Low | Support tickets | Clear "Coming soon" copy + back-home link |
| Route name collisions with legacy ones | Clean Code | Low | Low | TS error / runtime warning | Use a `ROUTES` constant; legacy names kept |
| Broken nav from sidebar to legacy routes after rename | Decoupling | Low | Medium | Smoke test catches | The sidebar update is explicitly **#209**, not this issue |

## 9. Testing strategy

### Frontend — Vitest

- `app/router/router.test.ts` — every new route resolves to its component (smoke).
- `shared/routing/modes.test.ts` — `parseMode` returns `ask` for `undefined` / `null` / unknown values; respects `inspect` / `chunks`.

### E2E — Karate UI

Out of scope for this issue (placeholder pages only). E2E coverage lands with #211 (library) and #216 (workspace).

### Manual QA

1. Visit each new URL in the browser → "Coming soon" shell renders without 404.
2. Visit `/docs/abc?mode=chunks` → page receives `mode === 'chunks'`.
3. Visit `/docs/abc?mode=garbage` → page receives `mode === 'ask'` (default).
4. Old routes (`/studio`, `/documents`) still load their existing pages.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

None. The placeholder pages are visible to anyone; they explain themselves.

### Observability

No new logs. Existing router-error handling unchanged.

### Rollback plan

Revert the router and pages — old setup is untouched.

## 11. Open questions

- Should `/docs/:id` 404 if the doc id is unknown, or render the workspace shell with an error state? **Decision for 0.6.0:** the workspace handles the "doc not found" case in #216; this issue ships the placeholder which always renders.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/207
- **Related issues:** #208 (breadcrumb), #209 (nav), #210 (FF mode gating), #211 (library page), #216 (workspace), #218+ (modes)
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Frontend conventions: `frontend/CLAUDE.md`

# Design: Feature flags hide entire mode tabs (and redirect deep links)

- **Issue:** #210
- **Title on issue:** [ENHANCEMENT] Feature flags hide entire mode tabs instead of routing to 404
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** frontend: features/feature-flags · app/router · pages · shared · backend: api/health
- **Audit dimensions likely touched:** Clean Code · Tests · Security · Documentation
- **ADR spawned?:** no

---

## 1. Problem

Studio gates `Inspect` / `Chunks` / `Ask` per tenant via feature flags. Without explicit handling, a disabled mode is still reachable by URL — a deep link like `/docs/abc?mode=chunks` lands on a half-broken page or 404 when chunks are disabled. The user experience is "the link my colleague sent me is broken".

The fix has three pieces:

1. **Routing-level redirect**: `?mode=<disabled>` rewrites to the first enabled mode, preserving the doc id.
2. **Tab-level visibility**: when E4 builds the workspace tabs (#216), disabled modes are hidden from the tab strip.
3. **Server-side guard**: even if a client sends a request for a disabled mode, the API rejects writes (read-only is OK so the user can still view).

This issue ships **piece 1** (routing redirect) plus the **flag declarations** on `/api/health` and **frontend exposure** that pieces 2 + 3 will consume. Tab visibility (piece 2) is wired in #216. Server-side write guard (piece 3) is wired by the chunks-edit endpoints from #205's follow-up.

## 2. Goals

- [ ] `/api/health` exposes three new booleans: `inspectModeEnabled`, `chunksModeEnabled`, `askModeEnabled`.
- [ ] `useFeatureFlag('inspectMode' | 'chunksMode' | 'askMode')` returns the live value.
- [ ] Routing redirects `/docs/:id?mode=<disabled>` to the first enabled mode, in this priority: `ask` → `chunks` → `inspect`. If none are enabled, redirect to `/docs` with a flash message.
- [ ] No 404 on a disabled mode — only redirects.
- [ ] Server-side: nothing yet (the actual write endpoints land elsewhere).
- [ ] E2E (Karate UI): toggle a flag (via env var) → deep link redirects correctly.

## 3. Non-goals

- Tab strip visibility — that is **#216** (workspace).
- Server-side write rejection — that lands on the chunks-edit endpoints (#205 follow-up).
- Per-user flags (vs per-tenant) — out of scope; flags are global to the deployment.
- A flag UI to toggle modes at runtime — operator-only via env vars.

## 4. Context & constraints

### Existing code surface

- `document-parser/api/schemas.py` — `HealthResponse` already exposes `chunking`, `disclaimer`, `ingestion_available`, `reasoning_available`.
- `document-parser/api/health.py` — endpoint that builds `HealthResponse`.
- `document-parser/infra/settings.py` — env-var driven settings.
- `frontend/src/features/feature-flags/store.ts` — flag map + `isEnabled(name)`.
- `frontend/src/features/feature-flags/useFeatureFlag.ts` — composable.
- `frontend/src/app/router/index.ts` — Vue Router (extended in #207).

### Hexagonal Architecture constraints (backend)

The flag values are read from env vars in `infra/settings.py` (existing pattern). The API layer translates them into the `HealthResponse` DTO. No domain change.

### Hard constraints

- `/api/health` stays additive — three new fields, no breaking renames.
- Frontend behaviour falls back gracefully when fields are absent (older backend version).
- Default for all three flags = `true` (enabled). That preserves current behaviour for existing deployments.

## 5. Proposed design

### 5.1 Backend

`document-parser/infra/settings.py` adds three booleans:

```python
INSPECT_MODE_ENABLED  = os.getenv("INSPECT_MODE_ENABLED",  "true").lower() == "true"
CHUNKS_MODE_ENABLED   = os.getenv("CHUNKS_MODE_ENABLED",   "true").lower() == "true"
ASK_MODE_ENABLED      = os.getenv("ASK_MODE_ENABLED",      "true").lower() == "true"
```

`document-parser/api/schemas.py` — `HealthResponse` gains:

```python
inspect_mode_enabled: bool = True
chunks_mode_enabled:  bool = True
ask_mode_enabled:     bool = True
```

`document-parser/api/health.py` populates them from settings.

### 5.2 Frontend — flag store

`frontend/src/features/feature-flags/store.ts` adds three keys to the flag map:

```ts
inspectMode: this.health.inspectModeEnabled ?? true,
chunksMode:  this.health.chunksModeEnabled  ?? true,
askMode:     this.health.askModeEnabled     ?? true,
```

`useFeatureFlag('inspectMode' | 'chunksMode' | 'askMode')` returns a `ComputedRef<boolean>`. No new composable; the existing one works on these new keys.

### 5.3 Frontend — routing redirect

A pure helper `frontend/src/shared/routing/resolveMode.ts`:

```ts
export const MODE_PRIORITY: DocMode[] = ['ask', 'chunks', 'inspect']

export function resolveMode(
  requested: DocMode | undefined,
  enabled: Record<DocMode, boolean>,
): DocMode | null {
  if (requested && enabled[requested]) return requested
  return MODE_PRIORITY.find(m => enabled[m]) ?? null
}
```

Wired in the router's `beforeEach` guard for `doc-workspace`:

```ts
router.beforeEach((to) => {
  if (to.name !== ROUTES.DOC_WORKSPACE) return true
  const requested = parseMode(to.query.mode)
  const enabled = featureStore.modeFlags()  // returns Record<DocMode, boolean>
  const resolved = resolveMode(requested, enabled)
  if (resolved === null) {
    return { name: ROUTES.DOCS_LIBRARY, query: { reason: 'no-mode-enabled' } }
  }
  if (resolved !== requested) {
    return { ...to, query: { ...to.query, mode: resolved } }
  }
  return true
})
```

Pure helper is unit-testable; the `beforeEach` hook is integration-tested via `router.test.ts`.

### 5.4 i18n

A flash message displayed on `/docs` if `?reason=no-mode-enabled` is present:

- `flags.allModesDisabled` (fr + en).

The flash is rendered by `DocsLibraryPage.vue` (placeholder from #207) on mount; #211 will polish the rendering.

## 6. Alternatives considered

### Alternative A — 404 on disabled mode

- **Summary:** Show a "this mode is not available" 404.
- **Why not:** A deep link sent by a colleague becomes a dead end. Redirect is more graceful.

### Alternative B — Render the workspace and disable the tab

- **Summary:** No redirect; the workspace renders with the disabled mode replaced by a "disabled" placeholder.
- **Why not:** The URL still shows the disabled mode. A user copying it shares the same broken link.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET | `/api/health` | — | now includes `inspectModeEnabled`, `chunksModeEnabled`, `askModeEnabled` | No (additive) |

### Env vars

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `INSPECT_MODE_ENABLED` | `true` | `true` / `false` | gates the Inspect mode end-to-end |
| `CHUNKS_MODE_ENABLED`  | `true` | `true` / `false` | gates the Chunks mode |
| `ASK_MODE_ENABLED`     | `true` | `true` / `false` | gates the Ask mode |

### Breaking changes

None.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| All three flags off → user lands on `/docs` with a confusing flash | Clean Code | Low | Low | Visual smoke | The flash explicitly names the cause; admins should never set all three off |
| Frontend caches old flag values across navigation | Decoupling | Low | Medium | Stale UI | The flag store loads on app boot and exposes a `reload()` for support flows; revisit if needed |
| Backend default change breaks existing deployments | Security / Tests | Low | High | E2E catches | Defaults = `true` (enabled). Existing behaviour preserved unless operator opts out |
| Server-side write protection missing in 0.6.0 | Security | Medium | Medium | Manual / next audit | Documented as a follow-up; client-side gating is enough until chunks-edit endpoints land |

## 9. Testing strategy

### Backend — pytest

- `tests/test_schemas.py` — `HealthResponse` round-trip with the three new fields, defaults preserved.
- `tests/test_settings.py` (or equivalent) — env-var parsing for the three flags.

### Frontend — Vitest

- `shared/routing/resolveMode.test.ts` — full table over `(requested, enabled)` combinations including all-disabled, all-enabled, requested disabled, requested enabled.
- `app/router/router.test.ts` — `beforeEach` redirect scenarios via a mocked store.
- `features/feature-flags/store.test.ts` — three new flags exposed; falls back to `true` when health response is missing them.

### E2E — Karate UI

A focused smoke under `e2e/api/`: set `CHUNKS_MODE_ENABLED=false` in the test env, hit `/docs/abc?mode=chunks`, expect a redirect to `/docs/abc?mode=ask` (default).

### Manual QA

1. Default deploy → all three modes work.
2. Set `CHUNKS_MODE_ENABLED=false`, restart, visit `/docs/abc?mode=chunks` → redirected to `/docs/abc?mode=ask`.
3. Set all three to `false` → `/docs/abc?mode=ask` redirects to `/docs?reason=no-mode-enabled`.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

This issue **is** the feature flag work. Defaults preserve current behaviour.

### Observability

- A single `INFO` log line on the server at boot: `feature_flags inspect=<true/false> chunks=<true/false> ask=<true/false>`.
- A `WARN` log when all three are off (operator misconfiguration smell).

### Rollback plan

Set all three env vars to `true` (or unset them) → defaults restore the old behaviour.

## 11. Open questions

- Per-tenant flags (multi-tenant deployments) — explicitly punted to post-0.6.0.
- Should the flash message be a banner or a toast? **Decision:** banner, dismissible, persistent until the user navigates away.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/210
- **Related issues:** #207 (routing), #216 (workspace tabs), #205 follow-up (chunks-edit endpoints + server-side guard)
- **ADRs:** none planned
- **Project docs:** Architecture (`docs/architecture.md`), Frontend conventions (`frontend/CLAUDE.md`), Backend conventions (`document-parser/CLAUDE.md`)

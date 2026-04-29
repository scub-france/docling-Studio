# Design: Navigation rework — Home / Docs / Stores / Runs / Settings

- **Issue:** #209
- **Title on issue:** [ENHANCEMENT] Rework top navigation (Home / Docs / Stores / Runs / Settings)
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** frontend: shared/ui · app
- **Audit dimensions likely touched:** Clean Code · Tests · Documentation
- **ADR spawned?:** no

---

## 1. Problem

The existing nav is a **left sidebar** (`AppSidebar.vue`) with seven entries: `Home`, `Studio`, `Documents`, `Search`, `Reasoning`, `History`, `Settings`. It mirrors the current execution-centric IA: `Studio` (an analysis), `Documents` (a list), `History` (past runs).

The doc-centric pivot wants a tighter five-entry nav reflecting the new IA: **Home, Docs, Stores, Runs, Settings**. `Docs` is the new primary action (replaces `Documents` + `Studio`). `Stores` is new. `Runs` replaces `History` (same data, new framing). `Search` and `Reasoning` collapse into the doc workspace modes (#216 + #224).

The original PM sitemap called this a "top nav" — the project's actual nav is a **sidebar**. We keep the sidebar (existing convention, established interaction) and rework its entries.

## 2. Goals

- [ ] `AppSidebar.vue` shows five entries in this order: Home, Docs (★ primary), Stores, Runs, Settings.
- [ ] `Docs` visually emphasised — bold label or accent colour token.
- [ ] Active state correctly highlights `Docs` on `/docs`, `/docs/new`, `/docs/:id`.
- [ ] Active state for `Stores` on `/index`, `/index/:store`, `/index/:store/query`.
- [ ] Active state for `Runs` on `/runs`, `/runs/:id`.
- [ ] Legacy entries (`Studio`, `Documents`, `Search`, `Reasoning`, `History`) removed from the sidebar.
- [ ] Legacy URLs still functional (we did not redirect in #207).

## 3. Non-goals

- Removing the legacy *pages* — they keep working; this issue removes them only from the sidebar.
- Mobile hamburger redesign — the existing burger toggle stays.
- Sidebar collapse animation — unchanged.
- Top breadcrumb — that is **#208**.
- A "what's new" tooltip explaining the change — out of scope; release notes cover it.

## 4. Context & constraints

### Existing code surface

- `frontend/src/shared/ui/AppSidebar.vue` — the file to edit. Currently 145 lines.
- `frontend/src/app/App.vue` — embeds `<AppSidebar>`.
- `frontend/src/shared/i18n.ts` — flat keys under `nav.*`.
- `frontend/src/features/feature-flags/store.ts` — flags currently gating `Search` and `Reasoning`.

### Hard constraints

- No new dependencies.
- TypeScript strict — every nav item is typed.
- Existing burger / collapse interaction stays untouched.

## 5. Proposed design

### 5.1 Nav model

A typed array driving the render:

```ts
type NavItem = {
  key: string                           // for v-for and active match
  to: RouteLocationRaw                  // typed via ROUTES
  labelKey: string                      // i18n key
  iconKey: string                       // icon name token
  primary?: boolean                     // visual emphasis (Docs)
  matchPrefixes: string[]               // prefixes for active-state match
}

const items: NavItem[] = [
  { key: 'home',     to: { name: ROUTES.HOME },         labelKey: 'nav.home',     iconKey: 'home',     matchPrefixes: ['/'] },
  { key: 'docs',     to: { name: ROUTES.DOCS_LIBRARY }, labelKey: 'nav.docs',     iconKey: 'docs',     primary: true, matchPrefixes: ['/docs'] },
  { key: 'stores',   to: { name: ROUTES.STORES_LIST },  labelKey: 'nav.stores',   iconKey: 'stores',   matchPrefixes: ['/index'] },
  { key: 'runs',     to: { name: ROUTES.RUNS },         labelKey: 'nav.runs',     iconKey: 'runs',     matchPrefixes: ['/runs'] },
  { key: 'settings', to: { name: ROUTES.SETTINGS },     labelKey: 'nav.settings', iconKey: 'settings', matchPrefixes: ['/settings'] },
]
```

### 5.2 Active match

`isActive(item, route)`:

- For `/`, the home entry is active only on exact match.
- For all other items, active when the route path **starts with** any of `item.matchPrefixes`.
- Implemented in a tiny pure helper, tested.

### 5.3 Primary emphasis

The `primary: true` item gets an extra CSS class `nav-item--primary` adding a subtle accent (left bar in the sidebar's accent colour, bolder label). No new colour tokens.

### 5.4 i18n

New keys (fr + en):

- `nav.docs`
- `nav.stores`
- `nav.runs`

Removed (or kept around for the legacy pages that still exist): `nav.studio`, `nav.documents`, `nav.history`, `nav.search`, `nav.reasoning`. We **keep** them in `i18n.ts` since the legacy pages still render headings using them. They are no longer surfaced in the sidebar.

### 5.5 Footer

The sidebar footer (OpenSearch dot, GitHub stars, version) stays. The OpenSearch dot moves to be visible regardless of `ingestion` flag — it now reflects the default store's reachability (#203's seed). For 0.6.0 we keep the existing wiring (gated by `ingestion` flag) and revisit when stores get their own page (#231 in 0.7.0).

## 6. Alternatives considered

### Alternative A — Keep all old entries, add the new ones

- **Summary:** Show 10 entries; let the user discover.
- **Why not:** Defeats the point. The pivot is about reducing cognitive load, not adding entries.

### Alternative B — Move the nav to the top bar

- **Summary:** Implement the design doc's literal "top nav".
- **Why not:** The shell is sidebar-driven; switching layout is a much bigger lift and out of scope for E2.

## 7. API & data contract

No backend change. No env vars.

### Breaking changes

None at the API level. UX-level: legacy entries disappear from the sidebar. Their URLs remain valid.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Users of legacy pages think the app removed features | Documentation | Medium | Medium | Support tickets | Release notes; legacy pages still work via direct URL; eventually #211/#216 replace them entirely |
| Active state misfires because two entries match the same prefix | Clean Code | Low | Low | Visual regression | `matchPrefixes` is explicit, longest-prefix wins via simple precedence in the helper |
| Missing icons for Docs / Stores / Runs in the existing icon set | Clean Code | Medium | Low | Visible during review | Audit `iconKey` strings against the icon component before merge; fall back to a sane default if missing |

## 9. Testing strategy

### Frontend — Vitest

- `shared/ui/AppSidebar.test.ts` — renders 5 entries in order; `Docs` carries the primary class; active state correct on each `matchPrefix`.
- `shared/ui/navActive.test.ts` — pure helper unit tests over `isActive(item, path)`.

### Manual QA

1. Visit `/`, `/docs`, `/index/foo`, `/runs`, `/settings` → exactly one entry highlighted.
2. Visit `/docs/abc?mode=chunks` → `Docs` highlighted.
3. Visit a legacy route `/studio` → no nav entry highlighted (page still loads).

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

None.

### Observability

None.

### Rollback plan

Revert. The legacy nav returns; legacy pages were never broken.

## 11. Open questions

- Do we add a `Help` entry now or wait? **Decision:** wait. The five-entry nav is part of the value proposition.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/209
- **Related issues:** #207 (routing), #208 (breadcrumb), #210 (FF gating), #211 (library), #216 (workspace)
- **ADRs:** none planned
- **Project docs:** Architecture (`docs/architecture.md`), Frontend conventions (`frontend/CLAUDE.md`)

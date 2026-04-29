# Design: Doc workspace breadcrumb

- **Issue:** #208
- **Title on issue:** [ENHANCEMENT] Refactor breadcrumb to Studio › <doc> › <mode>
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** frontend: shared/ui · app
- **Audit dimensions likely touched:** Clean Code · Tests · Documentation
- **ADR spawned?:** no

---

## 1. Problem

There is no breadcrumb component today. The user lands on `/docs/:id?mode=chunks` and has no orientation: which doc, which mode, how to step back. With the new doc-centric URLs introduced in #207, the user navigates between modes on the same doc — a breadcrumb anchors them in the IA.

The shape `Studio › <doc title> › <mode>` is the agreed pattern: each segment is a link except the last, the doc title is truncated with ellipsis (full title on hover), and the mode segment updates as the user switches tabs without a page reload.

## 2. Goals

- [ ] New `<AppBreadcrumb>` component renders three segments on doc workspace pages: `Studio › <doc title> › <mode>`.
- [ ] Each non-last segment is clickable: `Studio` → `/`, `<doc title>` → `/docs/:id` (default mode).
- [ ] Doc title truncates beyond ~40 chars with ellipsis; full title shown via `title` attribute on hover.
- [ ] Mode segment reflects current `?mode=` and updates without remount.
- [ ] On non-doc routes (`/`, `/runs`, `/index`), the breadcrumb is empty / hidden — no fake breadcrumbs invented.
- [ ] Component is data-driven: takes a `Crumb[]` prop so future routes can supply their own.

## 3. Non-goals

- Auto-deriving the breadcrumb from the route — for 0.6.0 the doc workspace page passes its crumbs explicitly. Auto-derivation is a follow-up if more pages need it.
- Mobile-specific breadcrumb collapsing — a single-line ellipsis is enough for the layout.
- Breadcrumbs on store / run pages — those land in 0.7.0 with their own page work.

## 4. Context & constraints

### Existing code surface

- `frontend/src/app/App.vue` — the shell. The breadcrumb slot will live in the topbar (between the logo and the right-side actions).
- `frontend/src/pages/DocWorkspacePage.vue` (created by #207, placeholder). Will be the first consumer.
- `frontend/src/shared/ui/` — home for shared UI primitives. The new component lives here.
- `frontend/src/shared/routing/names.ts` (created by #207) — typed route names.
- `frontend/src/shared/i18n.ts` — strings.

### Hard constraints

- TypeScript strict — `Crumb` is a discriminated union (link vs leaf).
- Accessibility — `<nav aria-label="breadcrumb">` + `<ol>` + `aria-current="page"` on the leaf.
- No CSS framework lock-in — uses existing token classes from `App.vue` styles, no new lib.

## 5. Proposed design

### 5.1 Component contract

`frontend/src/shared/ui/AppBreadcrumb.vue`:

```ts
type LinkCrumb = { kind: 'link'; label: string; to: RouteLocationRaw }
type LeafCrumb = { kind: 'leaf'; label: string }
type Crumb = LinkCrumb | LeafCrumb

defineProps<{ crumbs: Crumb[] }>()
```

The component renders nothing when `crumbs.length === 0`.

### 5.2 Doc workspace integration

The doc workspace page (placeholder from #207) builds its crumbs:

```ts
const crumbs = computed<Crumb[]>(() => [
  { kind: 'link', label: t('breadcrumb.studio'), to: { name: ROUTES.HOME } },
  {
    kind: 'link',
    label: truncate(doc.value?.filename ?? '...', 40),
    to: { name: ROUTES.DOC_WORKSPACE, params: { id: docId.value } },
  },
  { kind: 'leaf', label: t(`breadcrumb.mode.${mode.value}`) },
])
```

A small helper `truncate(text, max)` in `shared/ui/text.ts` adds the ellipsis.

### 5.3 Slot wiring in the shell

`App.vue` reserves a slot just under the topbar:

```vue
<slot name="breadcrumb">
  <AppBreadcrumb :crumbs="[]" />
</slot>
```

For pages that do not opt in (which is most of them in 0.6.0), nothing renders.

The doc workspace page provides its slot via a `<teleport to="#breadcrumb-slot">` or — simpler — the `App.vue` consults a tiny Pinia store `useBreadcrumbStore()` that pages set via `setCrumbs([...])` on mount and clear on unmount. Goes with the "data-driven" goal.

We pick the **store approach**: zero teleport, plays well with route-level transitions, and the consumer lives in the page (no shell coupling).

### 5.4 i18n

New keys under `breadcrumb.*`:

- `breadcrumb.studio`
- `breadcrumb.mode.ask`
- `breadcrumb.mode.inspect`
- `breadcrumb.mode.chunks`

## 6. Alternatives considered

### Alternative A — Auto-derive crumbs from the route

- **Summary:** A central function that maps each `RouteLocationNormalized` to a `Crumb[]`.
- **Why not:** Doc workspace needs the doc title which is async — the function would need to fetch it. Page-driven is cleaner for now; auto-derivation can layer on top later for static pages.

### Alternative B — Use the page meta object (`route.meta.breadcrumb`)

- **Summary:** Each route declares a static `meta.breadcrumb` array.
- **Why not:** Same async-doc-title problem. Plus it scatters crumb config across the router.

## 7. API & data contract

No backend change. No env vars.

### Breaking changes

None.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Pages forget to clear crumbs on unmount → stale breadcrumb on next route | Clean Code | Medium | Low | Visual regression | The `useBreadcrumbStore` exposes `useCrumbs(crumbs)` composable that auto-clears on unmount via `onBeforeUnmount` |
| Long doc titles break the topbar layout | Clean Code | Low | Low | Visual regression | Truncate at 40 chars + CSS `text-overflow: ellipsis` as a belt-and-braces |
| Accessibility regression | Tests / Documentation | Low | Medium | Audit | `<nav aria-label="breadcrumb">` + `aria-current="page"` on leaf; tested |

## 9. Testing strategy

### Frontend — Vitest

- `shared/ui/AppBreadcrumb.test.ts` — renders nothing when empty; renders 3 crumbs with correct roles; `aria-current="page"` on leaf.
- `shared/ui/text.test.ts` — `truncate` boundary cases.
- `shared/state/breadcrumbStore.test.ts` — `setCrumbs` / `clear`; `useCrumbs` composable auto-clears on unmount.

### Manual QA

1. Visit `/docs/abc?mode=ask` → `Studio › abc.pdf › Ask`.
2. Switch to chunks mode (when E4 lands) → leaf updates without page flicker.
3. Visit `/runs` → no breadcrumb visible.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

None.

### Observability

None.

### Rollback plan

Revert; pages stop providing crumbs and the slot stays empty.

## 11. Open questions

- Should we render the breadcrumb on `/docs/new` as `Studio › Import`? **Decision:** yes, the page provides 2 crumbs (`Studio › Import`). Implemented as a tiny tweak in #214.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/208
- **Related issues:** #207 (routing), #211 (library), #216 (workspace), #218+ (modes)
- **ADRs:** none planned
- **Project docs:** Architecture (`docs/architecture.md`), Frontend conventions (`frontend/CLAUDE.md`)

import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'

import { parseMode } from '../../shared/routing/modes'
import { ROUTES } from '../../shared/routing/names'

/**
 * Route table used by the production router and by tests.
 *
 * Lives in its own file so importing the router definition doesn't
 * trigger `createWebHistory()` (which needs `window` and breaks the
 * default node-environment vitest tests). Tests build a router with
 * `createMemoryHistory()` over this same table.
 */
export const routes: RouteRecordRaw[] = [
  // ---------------------------------------------------------------------------
  // Legacy routes — kept functional during the 0.6.0 transition.
  // ---------------------------------------------------------------------------
  {
    path: '/',
    name: ROUTES.HOME,
    component: () => import('../../pages/HomePage.vue'),
  },
  {
    path: '/studio',
    name: ROUTES.STUDIO,
    component: () => import('../../pages/StudioPage.vue'),
  },
  {
    path: '/history',
    name: ROUTES.HISTORY,
    component: () => import('../../pages/HistoryPage.vue'),
  },
  {
    path: '/analyses',
    name: ROUTES.ANALYSES,
    component: () => import('../../pages/AnalysesPage.vue'),
  },
  {
    path: '/analyses/:id',
    name: ROUTES.ANALYSIS_DETAIL,
    component: () => import('../../pages/AnalysisDetailPage.vue'),
    props: true,
  },
  {
    path: '/documents',
    name: ROUTES.DOCUMENTS,
    component: () => import('../../pages/DocumentsPage.vue'),
  },
  {
    path: '/search',
    name: ROUTES.SEARCH,
    component: () => import('../../pages/SearchPage.vue'),
  },
  {
    // Reasoning-trace tunnel. Route is always registered; the page shows
    // an empty state when the `reasoning` feature flag is off (same pattern
    // as /search does for ingestion).
    path: '/reasoning',
    name: ROUTES.REASONING,
    component: () => import('../../pages/ReasoningPage.vue'),
  },
  {
    // Deep-link into a specific document's reasoning workspace, e.g. shared
    // by Peter to a teammate.
    path: '/reasoning/:docId',
    name: ROUTES.REASONING_DOC,
    component: () => import('../../pages/ReasoningPage.vue'),
    props: true,
  },
  {
    path: '/settings',
    name: ROUTES.SETTINGS,
    component: () => import('../../pages/SettingsPage.vue'),
  },

  // ---------------------------------------------------------------------------
  // 0.6.0 — Document-centric routes (#207). Placeholder pages until E3/E4/E5
  // implement them; the legacy routes above keep working in parallel.
  // ---------------------------------------------------------------------------
  {
    path: '/docs',
    name: ROUTES.DOCS_LIBRARY,
    component: () => import('../../pages/DocsLibraryPage.vue'),
  },
  {
    path: '/docs/new',
    name: ROUTES.DOCS_NEW,
    component: () => import('../../pages/DocsNewPage.vue'),
  },
  {
    path: '/docs/:id',
    name: ROUTES.DOC_WORKSPACE,
    component: () => import('../../pages/DocWorkspacePage.vue'),
    props: (route: RouteLocationNormalized) => ({
      id: String(route.params.id),
      mode: parseMode(route.query.mode),
    }),
  },
  {
    path: '/runs',
    name: ROUTES.RUNS,
    component: () => import('../../pages/RunsPage.vue'),
  },
  {
    path: '/runs/:id',
    name: ROUTES.RUN_DETAIL,
    component: () => import('../../pages/RunDetailPage.vue'),
    props: true,
  },

  // ---------------------------------------------------------------------------
  // 404 — must come last.
  // ---------------------------------------------------------------------------
  {
    path: '/:pathMatch(.*)*',
    name: ROUTES.NOT_FOUND,
    redirect: '/',
  },
]

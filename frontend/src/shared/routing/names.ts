/**
 * Canonical route name constants — typed to keep callers honest.
 *
 * Use:
 *
 *   router.push({ name: ROUTES.DOC_WORKSPACE, params: { id } })
 *
 * instead of stringly-typed names. Adding a route requires touching
 * exactly two places: the router definition and this file.
 */

export const ROUTES = {
  // Existing legacy routes — kept until E3/E4/E5 replace them.
  HOME: 'home',
  STUDIO: 'studio',
  HISTORY: 'history',
  DOCUMENTS: 'documents',
  SEARCH: 'search',
  REASONING: 'reasoning',
  REASONING_DOC: 'reasoning-doc',
  SETTINGS: 'settings',
  NOT_FOUND: 'not-found',

  // 0.6.0 — Document-centric routes (#207).
  DOCS_LIBRARY: 'docs-library',
  DOCS_NEW: 'docs-new',
  DOC_WORKSPACE: 'doc-workspace',
  STORES_LIST: 'stores-list',
  STORE_CREATE: 'store-create',
  STORE_DETAIL: 'store-detail',
  STORE_EDIT: 'store-edit',
  STORE_QUERY: 'store-query',
  RUNS: 'runs',
  RUN_DETAIL: 'run-detail',
} as const

export type RouteName = (typeof ROUTES)[keyof typeof ROUTES]

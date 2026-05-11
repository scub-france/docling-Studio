import { ROUTES } from './names'

/**
 * Surface gating (#257).
 *
 * Two master flags select which UI surface is exposed:
 * - `studioMode` gates the legacy Studio surface
 * - `ragPipeline` gates the new doc-centric RAG pipeline
 *
 * `resolveSurface` is a pure helper consumed by the router's `beforeEach`
 * guard. Returns the target route name to redirect to, or `null` when
 * the requested route is allowed.
 */

export const STUDIO_SURFACE_ROUTES: ReadonlySet<string> = new Set([
  ROUTES.STUDIO,
  ROUTES.HISTORY,
  ROUTES.DOCUMENTS,
  ROUTES.SEARCH,
])

export const RAG_SURFACE_ROUTES: ReadonlySet<string> = new Set([
  ROUTES.DOCS_LIBRARY,
  ROUTES.DOCS_NEW,
  ROUTES.DOC_WORKSPACE,
  ROUTES.STORES_LIST,
  ROUTES.STORE_CREATE,
  ROUTES.STORE_DETAIL,
  ROUTES.STORE_EDIT,
  ROUTES.STORE_QUERY,
  ROUTES.RUNS,
  ROUTES.RUN_DETAIL,
])

export interface SurfaceFlags {
  studio: boolean
  rag: boolean
}

export function resolveSurface(routeName: string, flags: SurfaceFlags): string | null {
  if (STUDIO_SURFACE_ROUTES.has(routeName) && !flags.studio) {
    return flags.rag ? ROUTES.DOCS_LIBRARY : ROUTES.HOME
  }
  if (RAG_SURFACE_ROUTES.has(routeName) && !flags.rag) {
    return flags.studio ? ROUTES.STUDIO : ROUTES.HOME
  }
  return null
}

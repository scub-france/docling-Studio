import { createRouter, createWebHistory } from 'vue-router'

import { useFeatureFlagStore } from '../../features/feature-flags/store'
import { isDocMode } from '../../shared/routing/modes'
import { ROUTES } from '../../shared/routing/names'
import { resolveMode } from '../../shared/routing/resolveMode'
import { resolveSurface } from '../../shared/routing/resolveSurface'
import { routes } from './routes'

export { routes }

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Surface gating (#257) + mode gating (#210).
 *
 * Surface: two master flags select which UI surface is exposed. When a
 * route from a disabled surface is requested, redirect to the other
 * surface's landing page — or to `/` if both are off (defensive net;
 * backend refuses to start in that state).
 *
 * Mode: inside the doc workspace, the requested mode falls back to the
 * first enabled mode when the deep-linked one is off.
 *
 * Why the guard is async: this guard reads `studioModeEnabled` /
 * `ragPipelineEnabled` which come from `/api/health`. main.ts kicks off
 * `load()` eagerly so it's typically in flight (or done) by the time the
 * first navigation hits this guard, but on a cold cache the navigation
 * still needs to wait — otherwise the guard reads the store's defaults
 * (`studio=false, rag=true`) and the legacy `/studio` deep-link gets
 * silently redirected to `/docs` on first load. `load()` is idempotent
 * (single in-flight promise, no-op when already loaded) so awaiting it
 * here costs nothing after the first nav, and avoids a timing race
 * without a magic timeout.
 */
router.beforeEach(async (to) => {
  const flagStore = useFeatureFlagStore()
  await flagStore.load()
  const name = String(to.name ?? '')

  const surfaceRedirect = resolveSurface(name, {
    studio: flagStore.studioModeEnabled,
    rag: flagStore.ragPipelineEnabled,
  })
  if (surfaceRedirect !== null) return { name: surfaceRedirect }

  if (to.name !== ROUTES.DOC_WORKSPACE) return true

  const flags = flagStore.getModeFlags()
  const requestedRaw = Array.isArray(to.query.mode) ? to.query.mode[0] : to.query.mode
  const requested = isDocMode(requestedRaw) ? requestedRaw : undefined
  const resolved = resolveMode(requested, flags)

  if (resolved === null) {
    return {
      name: ROUTES.DOCS_LIBRARY,
      query: { reason: 'no-mode-enabled' },
    }
  }
  if (resolved !== requested) {
    return {
      ...to,
      query: { ...to.query, mode: resolved },
    }
  }
  return true
})

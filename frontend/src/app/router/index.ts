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
 */
router.beforeEach((to) => {
  const flagStore = useFeatureFlagStore()
  const name = String(to.name ?? '')

  const surfaceRedirect = resolveSurface(name, {
    studio: flagStore.studioModeEnabled,
    rag: flagStore.ragPipelineEnabled,
  })
  if (surfaceRedirect !== null) return { name: surfaceRedirect }

  if (to.name !== ROUTES.DOC_WORKSPACE) return true

  const flags = flagStore.modeFlags()
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

import { createRouter, createWebHistory } from 'vue-router'

import { useFeatureFlagStore } from '../../features/feature-flags/store'
import { isDocMode } from '../../shared/routing/modes'
import { ROUTES } from '../../shared/routing/names'
import { resolveMode } from '../../shared/routing/resolveMode'
import { routes } from './routes'

export { routes }

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Doc workspace mode guard (#210).
 *
 * - `/docs/:id?mode=<disabled>` → redirect with the same id but the
 *   first enabled mode (ask > chunks > inspect priority).
 * - All three modes off → redirect to `/docs?reason=no-mode-enabled`.
 * - Any other route is left untouched.
 *
 * Pure resolution lives in `resolveMode`; the guard is just the
 * router-level wiring.
 */
router.beforeEach((to) => {
  if (to.name !== ROUTES.DOC_WORKSPACE) return true

  const flags = useFeatureFlagStore().modeFlags()
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

import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import { routes } from './routes'
import { ROUTES } from '../../shared/routing/names'

/**
 * Router test — uses `createMemoryHistory` so we don't need `window`
 * (vitest defaults to the node environment for performance). The
 * production router builds the same `routes` table on top of
 * `createWebHistory` in `index.ts`.
 */
const buildRouter = () => createRouter({ history: createMemoryHistory(), routes })

describe('router', () => {
  it('resolves every doc-centric route to a component', () => {
    const router = buildRouter()
    const cases: Array<{ path: string; name: string }> = [
      { path: '/docs', name: ROUTES.DOCS_LIBRARY },
      { path: '/docs/new', name: ROUTES.DOCS_NEW },
      { path: '/docs/abc', name: ROUTES.DOC_WORKSPACE },
      { path: '/analyses', name: ROUTES.ANALYSIS_LIBRARY },
      { path: '/analyses/abc', name: ROUTES.ANALYSIS_DETAIL },
      { path: '/runs', name: ROUTES.RUNS },
      { path: '/runs/run-42', name: ROUTES.RUN_DETAIL },
    ]
    for (const c of cases) {
      const resolved = router.resolve(c.path)
      expect(resolved.name, `route ${c.path}`).toBe(c.name)
      expect(resolved.matched.length, `route ${c.path} has a component`).toBeGreaterThan(0)
    }
  })

  it('keeps legacy routes functional', () => {
    const router = buildRouter()
    expect(router.resolve('/').name).toBe(ROUTES.HOME)
    expect(router.resolve('/studio').name).toBe(ROUTES.STUDIO)
    expect(router.resolve('/documents').name).toBe(ROUTES.DOCUMENTS)
    expect(router.resolve('/history').name).toBe(ROUTES.HISTORY)
    expect(router.resolve('/search').name).toBe(ROUTES.SEARCH)
    expect(router.resolve('/settings').name).toBe(ROUTES.SETTINGS)
  })

  it('redirects the retired /reasoning links into the doc workspace (#303)', () => {
    const router = buildRouter()
    // Static redirect to /docs.
    expect(router.resolve('/reasoning').matched[0]?.redirect).toBe('/docs')
    // /reasoning/:docId → /docs/:docId via a redirect function.
    const fn = router.resolve('/reasoning/abc').matched[0]?.redirect as
      | ((to: { params: { docId: string } }) => string)
      | undefined
    expect(typeof fn).toBe('function')
    expect(fn?.({ params: { docId: 'abc' } })).toBe('/docs/abc')
  })

  it('passes the document id to the doc workspace as a prop', () => {
    const router = buildRouter()
    const route = router.resolve({
      name: ROUTES.DOC_WORKSPACE,
      params: { id: 'abc' },
    })
    const propsFn = route.matched[0]?.props as
      | { default?: (r: typeof route) => unknown }
      | undefined
    const computed = (propsFn?.default ?? (() => null))(route) as { id: string }
    expect(computed.id).toBe('abc')
  })

  it('redirects unknown paths to /', () => {
    const router = buildRouter()
    const resolved = router.resolve('/nope/this/does/not/exist')
    expect(resolved.matched[0]?.redirect).toBeDefined()
  })
})

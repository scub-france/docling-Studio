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
  it('resolves every 0.6.0 doc-centric route to a component', () => {
    const router = buildRouter()
    const cases: Array<{ path: string; name: string }> = [
      { path: '/docs', name: ROUTES.DOCS_LIBRARY },
      { path: '/docs/new', name: ROUTES.DOCS_NEW },
      { path: '/docs/abc', name: ROUTES.DOC_WORKSPACE },
      { path: '/index', name: ROUTES.STORES_LIST },
      { path: '/index/foo', name: ROUTES.STORE_DETAIL },
      { path: '/index/foo/query', name: ROUTES.STORE_QUERY },
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
    expect(router.resolve('/reasoning').name).toBe(ROUTES.REASONING)
    expect(router.resolve('/reasoning/abc').name).toBe(ROUTES.REASONING_DOC)
    expect(router.resolve('/settings').name).toBe(ROUTES.SETTINGS)
  })

  it('passes id and parsed mode to the doc workspace as props', () => {
    const router = buildRouter()
    const route = router.resolve({
      name: ROUTES.DOC_WORKSPACE,
      params: { id: 'abc' },
      query: { mode: 'inspect' },
    })
    const propsFn = route.matched[0]?.props as
      | { default?: (r: typeof route) => unknown }
      | undefined
    const computed = (propsFn?.default ?? (() => null))(route) as { id: string; mode: string }
    expect(computed.id).toBe('abc')
    expect(computed.mode).toBe('inspect')
  })

  it('falls back to linked when mode is unknown', () => {
    const router = buildRouter()
    const route = router.resolve({
      name: ROUTES.DOC_WORKSPACE,
      params: { id: 'abc' },
      query: { mode: 'garbage' },
    })
    const propsFn = route.matched[0]?.props as
      | { default?: (r: typeof route) => unknown }
      | undefined
    const computed = (propsFn?.default ?? (() => null))(route) as { mode: string }
    expect(computed.mode).toBe('linked')
  })

  it('maps the legacy ?mode=chunks alias to linked', () => {
    const router = buildRouter()
    const route = router.resolve({
      name: ROUTES.DOC_WORKSPACE,
      params: { id: 'abc' },
      query: { mode: 'chunks' },
    })
    const propsFn = route.matched[0]?.props as
      | { default?: (r: typeof route) => unknown }
      | undefined
    const computed = (propsFn?.default ?? (() => null))(route) as { mode: string }
    expect(computed.mode).toBe('linked')
  })

  it('redirects unknown paths to /', () => {
    const router = buildRouter()
    const resolved = router.resolve('/nope/this/does/not/exist')
    expect(resolved.matched[0]?.redirect).toBeDefined()
  })
})

import { describe, expect, it } from 'vitest'

import { ROUTES } from './names'
import { getRouteLabel } from './routeLabel'

describe('getRouteLabel', () => {
  it('shows the route name', () => {
    expect(getRouteLabel({ name: ROUTES.ANALYSIS_LIBRARY, path: '/analyses' })).toBe(
      'analysis-library',
    )
  })

  it('stringifies a symbol name', () => {
    expect(getRouteLabel({ name: Symbol('dev'), path: '/x' })).toBe('Symbol(dev)')
  })

  it('falls back to the path when the route has no name', () => {
    expect(getRouteLabel({ name: undefined, path: '/docs/abc' })).toBe('/docs/abc')
  })
})

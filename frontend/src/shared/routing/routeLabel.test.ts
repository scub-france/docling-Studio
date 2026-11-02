import { describe, expect, it } from 'vitest'

import { ROUTES } from './names'
import { routeLabel } from './routeLabel'

describe('routeLabel', () => {
  it('shows the route name', () => {
    expect(routeLabel({ name: ROUTES.ANALYSIS_LIBRARY, path: '/analyses' })).toBe(
      'analysis-library',
    )
  })

  it('stringifies a symbol name', () => {
    expect(routeLabel({ name: Symbol('dev'), path: '/x' })).toBe('Symbol(dev)')
  })

  it('falls back to the path when the route has no name', () => {
    expect(routeLabel({ name: undefined, path: '/docs/abc' })).toBe('/docs/abc')
  })
})

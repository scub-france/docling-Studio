import { describe, expect, it } from 'vitest'

import { ROUTES } from './names'
import { resolveSurface } from './resolveSurface'

describe('resolveSurface', () => {
  it('allows studio routes when studio surface is enabled', () => {
    expect(resolveSurface(ROUTES.STUDIO, { studio: true, rag: false })).toBeNull()
    expect(resolveSurface(ROUTES.HISTORY, { studio: true, rag: true })).toBeNull()
  })

  it('allows rag routes when rag surface is enabled', () => {
    expect(resolveSurface(ROUTES.DOCS_LIBRARY, { studio: false, rag: true })).toBeNull()
    expect(resolveSurface(ROUTES.DOC_WORKSPACE, { studio: true, rag: true })).toBeNull()
  })

  it('redirects studio routes to docs library when studio off and rag on', () => {
    expect(resolveSurface(ROUTES.STUDIO, { studio: false, rag: true })).toBe(ROUTES.DOCS_LIBRARY)
    expect(resolveSurface(ROUTES.HISTORY, { studio: false, rag: true })).toBe(ROUTES.DOCS_LIBRARY)
    expect(resolveSurface(ROUTES.DOCUMENTS, { studio: false, rag: true })).toBe(ROUTES.DOCS_LIBRARY)
    expect(resolveSurface(ROUTES.SEARCH, { studio: false, rag: true })).toBe(ROUTES.DOCS_LIBRARY)
  })

  it('redirects rag routes to studio when rag off and studio on', () => {
    expect(resolveSurface(ROUTES.DOCS_LIBRARY, { studio: true, rag: false })).toBe(ROUTES.STUDIO)
    expect(resolveSurface(ROUTES.STORES_LIST, { studio: true, rag: false })).toBe(ROUTES.STUDIO)
    expect(resolveSurface(ROUTES.RUNS, { studio: true, rag: false })).toBe(ROUTES.STUDIO)
  })

  it('falls back to home when both surfaces are off', () => {
    // Defensive case — backend refuses to start in this state.
    expect(resolveSurface(ROUTES.STUDIO, { studio: false, rag: false })).toBe(ROUTES.HOME)
    expect(resolveSurface(ROUTES.DOCS_LIBRARY, { studio: false, rag: false })).toBe(ROUTES.HOME)
  })

  it('leaves surface-neutral routes untouched', () => {
    expect(resolveSurface(ROUTES.HOME, { studio: false, rag: true })).toBeNull()
    expect(resolveSurface(ROUTES.SETTINGS, { studio: false, rag: true })).toBeNull()
    expect(resolveSurface(ROUTES.REASONING, { studio: false, rag: true })).toBeNull()
  })
})

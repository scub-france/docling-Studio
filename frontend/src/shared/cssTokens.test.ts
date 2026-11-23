// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createCssTokenReader } from './cssTokens'

describe('createCssTokenReader', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads the computed style once and returns trimmed token values', () => {
    const values: Record<string, string> = { '--accent': ' #123456 ', '--text': '#fff' }
    const spy = vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (name: string) => values[name] ?? '',
    } as unknown as CSSStyleDeclaration)
    const readToken = createCssTokenReader(document.createElement('canvas'))

    expect(readToken('--accent')).toBe('#123456')
    expect(readToken('--text')).toBe('#fff')
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('returns an empty string for an unknown token', () => {
    const readToken = createCssTokenReader(document.createElement('canvas'))

    expect(readToken('--not-a-token')).toBe('')
  })
})

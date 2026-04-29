import { describe, expect, it } from 'vitest'

import { matchesActive } from './navActive'

describe('matchesActive', () => {
  it('matches Home only on the exact / path', () => {
    expect(matchesActive('/', ['/'])).toBe(true)
    expect(matchesActive('/docs', ['/'])).toBe(false)
    expect(matchesActive('/anything', ['/'])).toBe(false)
  })

  it('matches a non-root prefix on exact, segment, and query boundaries', () => {
    expect(matchesActive('/docs', ['/docs'])).toBe(true)
    expect(matchesActive('/docs/abc', ['/docs'])).toBe(true)
    expect(matchesActive('/docs/abc/123', ['/docs'])).toBe(true)
    expect(matchesActive('/docs?foo=bar', ['/docs'])).toBe(true)
  })

  it('does not match prefixes that are part of a longer segment', () => {
    expect(matchesActive('/documents', ['/docs'])).toBe(false)
    expect(matchesActive('/docsy', ['/docs'])).toBe(false)
  })

  it('returns true if any prefix in the list matches', () => {
    expect(matchesActive('/runs/abc', ['/index', '/runs'])).toBe(true)
    expect(matchesActive('/index/foo/query', ['/index', '/runs'])).toBe(true)
    expect(matchesActive('/somewhere-else', ['/index', '/runs'])).toBe(false)
  })

  it('returns false on empty prefix list', () => {
    expect(matchesActive('/docs', [])).toBe(false)
  })
})

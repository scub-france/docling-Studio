import { describe, expect, it } from 'vitest'

import { ALL_MODES, DEFAULT_MODE, isDocMode, parseMode } from './modes'

describe('isDocMode', () => {
  it.each(['inspect', 'linked'])('accepts %s', (value) => {
    expect(isDocMode(value)).toBe(true)
  })

  it.each([undefined, null, '', 'foo', 'ask', 'chunks', 42, {}, []])('rejects %s', (value) => {
    expect(isDocMode(value)).toBe(false)
  })
})

describe('parseMode', () => {
  it('returns the default for missing or unknown values', () => {
    expect(parseMode(undefined)).toBe(DEFAULT_MODE)
    expect(parseMode(null)).toBe(DEFAULT_MODE)
    expect(parseMode('garbage')).toBe(DEFAULT_MODE)
    expect(parseMode(['linked'])).toBe(DEFAULT_MODE) // arrays not accepted
  })

  it.each(['linked', 'inspect'] as const)('respects %s', (mode) => {
    expect(parseMode(mode)).toBe(mode)
  })

  it('maps the legacy ?mode=chunks alias to linked', () => {
    expect(parseMode('chunks')).toBe('linked')
  })
})

describe('ALL_MODES', () => {
  it('lists every mode exactly once', () => {
    expect(new Set(ALL_MODES).size).toBe(ALL_MODES.length)
    expect(ALL_MODES).toContain('linked')
    expect(ALL_MODES).toContain('inspect')
  })

  it('puts linked first (default view)', () => {
    expect(ALL_MODES[0]).toBe('linked')
  })
})

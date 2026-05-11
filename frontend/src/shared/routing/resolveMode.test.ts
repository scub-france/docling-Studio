import { describe, expect, it } from 'vitest'

import type { DocMode } from './modes'
import { MODE_PRIORITY, resolveMode } from './resolveMode'

const allEnabled: Record<DocMode, boolean> = { linked: true, inspect: true }
const allDisabled: Record<DocMode, boolean> = { linked: false, inspect: false }

describe('resolveMode', () => {
  it('returns the requested mode when it is enabled', () => {
    expect(resolveMode('linked', allEnabled)).toBe('linked')
    expect(resolveMode('inspect', allEnabled)).toBe('inspect')
  })

  it('falls back to the highest-priority enabled mode when the requested one is disabled', () => {
    expect(resolveMode('linked', { linked: false, inspect: true })).toBe('inspect')
    expect(resolveMode('inspect', { linked: true, inspect: false })).toBe('linked')
  })

  it('honours the priority order linked > inspect', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('linked')
    expect(resolveMode(undefined, { linked: false, inspect: true })).toBe('inspect')
  })

  it('returns null when no mode is enabled', () => {
    expect(resolveMode('linked', allDisabled)).toBeNull()
    expect(resolveMode(undefined, allDisabled)).toBeNull()
  })

  it('handles missing requested gracefully', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('linked')
  })

  it('exposes the priority in the right order', () => {
    expect(MODE_PRIORITY).toEqual(['linked', 'inspect'])
  })
})

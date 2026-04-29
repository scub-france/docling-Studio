import { describe, expect, it } from 'vitest'

import type { DocMode } from './modes'
import { MODE_PRIORITY, resolveMode } from './resolveMode'

const allEnabled: Record<DocMode, boolean> = { ask: true, chunks: true, inspect: true }
const allDisabled: Record<DocMode, boolean> = { ask: false, chunks: false, inspect: false }

describe('resolveMode', () => {
  it('returns the requested mode when it is enabled', () => {
    expect(resolveMode('ask', allEnabled)).toBe('ask')
    expect(resolveMode('chunks', allEnabled)).toBe('chunks')
    expect(resolveMode('inspect', allEnabled)).toBe('inspect')
  })

  it('falls back to the highest-priority enabled mode when the requested one is disabled', () => {
    expect(resolveMode('chunks', { ...allEnabled, chunks: false })).toBe('ask')
    expect(resolveMode('chunks', { ask: false, chunks: false, inspect: true })).toBe('inspect')
  })

  it('honours the priority order ask > chunks > inspect', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('ask')
    expect(resolveMode(undefined, { ask: false, chunks: true, inspect: true })).toBe('chunks')
    expect(resolveMode(undefined, { ask: false, chunks: false, inspect: true })).toBe('inspect')
  })

  it('returns null when no mode is enabled', () => {
    expect(resolveMode('ask', allDisabled)).toBeNull()
    expect(resolveMode(undefined, allDisabled)).toBeNull()
  })

  it('handles missing requested gracefully', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('ask')
  })

  it('exposes the priority in the right order', () => {
    expect(MODE_PRIORITY).toEqual(['ask', 'chunks', 'inspect'])
  })
})

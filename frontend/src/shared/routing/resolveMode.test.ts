import { describe, expect, it } from 'vitest'

import type { DocMode } from './modes'
import { MODE_PRIORITY, resolveMode } from './resolveMode'

const allEnabled: Record<DocMode, boolean> = { parse: true }
const allDisabled: Record<DocMode, boolean> = { parse: false }

describe('resolveMode', () => {
  it('returns the requested mode when it is enabled', () => {
    expect(resolveMode('parse', allEnabled)).toBe('parse')
    expect(resolveMode('chunk', allEnabled)).toBe('parse')
    expect(resolveMode('ingest', allEnabled)).toBe('parse')
  })

  it('falls back to the highest-priority enabled mode when the requested one is disabled', () => {
    expect(resolveMode('parse', allDisabled)).toBeNull()
    expect(resolveMode('chunk', allDisabled)).toBeNull()
    expect(resolveMode('ingest', allDisabled)).toBeNull()
  })

  it('uses parse as the only available mode', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('parse')
    expect(resolveMode(undefined, allDisabled)).toBeNull()
  })

  it('returns null when no mode is enabled', () => {
    expect(resolveMode('parse', allDisabled)).toBeNull()
    expect(resolveMode(undefined, allDisabled)).toBeNull()
  })

  it('handles missing requested gracefully', () => {
    expect(resolveMode(undefined, allEnabled)).toBe('parse')
  })

  it('exposes the priority in the right order', () => {
    expect(MODE_PRIORITY).toEqual(['parse'])
  })
})

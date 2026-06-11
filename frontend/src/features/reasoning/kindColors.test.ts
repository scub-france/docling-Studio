import { describe, expect, it } from 'vitest'
import { kindBaseColor, kindColor } from './kindColors'
import type { ReasoningStepKind } from './types'

const ALL_KINDS: ReasoningStepKind[] = [
  'plan',
  'retrieve',
  'rerank',
  'read',
  'verify',
  'answer',
  'map',
]

describe('kindBaseColor', () => {
  it('maps each kind to its canonical element hex', () => {
    expect(kindBaseColor('read')).toBe('#F97316') // section_header
    expect(kindBaseColor('plan')).toBe('#8B5CF6') // table
    expect(kindBaseColor('retrieve')).toBe('#3B82F6') // text
    expect(kindBaseColor('answer')).toBe('#22C55E') // picture
    expect(kindBaseColor('map')).toBe('#EC4899') // formula
  })

  it('resolves a defined colour for every kind', () => {
    for (const k of ALL_KINDS) {
      expect(kindBaseColor(k)).toMatch(/^#[0-9A-Fa-f]{6}$/)
    }
  })
})

describe('kindColor', () => {
  it('uses the base hex for text and a color-mix tint for the background', () => {
    const c = kindColor('read')
    expect(c.fg).toBe('#F97316')
    expect(c.bg).toBe('color-mix(in srgb, #F97316 15%, transparent)')
  })
})

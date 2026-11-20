import { describe, expect, it } from 'vitest'

import type { GraphNode } from './graphApi'
import { LEGEND_CHIPS, findChip } from './legendFilters'

function node(overrides: Partial<GraphNode>): GraphNode {
  return {
    id: overrides.id ?? 'n1',
    group: overrides.group ?? 'element',
    ...overrides,
  }
}

describe('LEGEND_CHIPS matching', () => {
  it('section matches only SectionHeader elements', () => {
    const chip = findChip('section')!
    expect(chip.match(node({ group: 'element', label: 'SectionHeader' }))).toBe(true)
    expect(chip.match(node({ group: 'element', label: 'Paragraph' }))).toBe(false)
    // An element with no label should NOT match section.
    expect(chip.match(node({ group: 'element' }))).toBe(false)
  })

  it('paragraph matches Paragraph and TextElement (fallback)', () => {
    const chip = findChip('paragraph')!
    expect(chip.match(node({ group: 'element', label: 'Paragraph' }))).toBe(true)
    // TextElement is the generic fallback Docling-labels that don't have a
    // specific mapping end up with. It's visually rendered in the paragraph
    // color, so the chip covers both.
    expect(chip.match(node({ group: 'element', label: 'TextElement' }))).toBe(true)
    expect(chip.match(node({ group: 'element', label: 'Table' }))).toBe(false)
  })

  it('group-based chips use `group` not `label`', () => {
    expect(findChip('document')!.match(node({ group: 'document' }))).toBe(true)
    expect(findChip('page')!.match(node({ group: 'page', page_no: 1 }))).toBe(true)
    expect(findChip('chunk')!.match(node({ group: 'chunk' }))).toBe(true)
    // document chip must NOT match elements that happen to have label===undefined
    expect(findChip('document')!.match(node({ group: 'element' }))).toBe(false)
  })

  it('exposes a stable list of chips', () => {
    // The sidebar CSS targets `.legend-${key}` — renaming a key here would
    // silently break the styles. Pin the expected order + keys.
    expect(LEGEND_CHIPS.map((c) => c.key)).toEqual([
      'document',
      'section',
      'paragraph',
      'table',
      'figure',
      'page',
      'chunk',
    ])
  })
})

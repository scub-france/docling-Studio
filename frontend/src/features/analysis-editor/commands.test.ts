import { describe, expect, it } from 'vitest'
import { canMerge, coalesceCommands } from './commands'
import type { EditorElement } from './types'

const text = (id: string, parentId = 'parent'): EditorElement => ({
  id,
  selfRef: `#/texts/${id}`,
  parentId,
  type: 'text',
  text: id,
  headingLevel: null,
  children: [],
  provenance: [],
  editable: true,
  supportedOperations: ['replaceText', 'mergeText', 'moveElement'],
  nonEditableReason: null,
})

describe('analysis editor commands', () => {
  it('coalesces text and heading changes without removing structural commands', () => {
    expect(
      coalesceCommands([
        { type: 'replaceText', elementId: 'a', text: 'one' },
        { type: 'replaceText', elementId: 'a', text: 'two' },
        { type: 'moveElement', elementId: 'a', beforeElementId: null },
      ]),
    ).toEqual([
      { type: 'replaceText', elementId: 'a', text: 'two' },
      { type: 'moveElement', elementId: 'a', beforeElementId: null },
    ])
  })

  it('only permits adjacent text siblings to merge', () => {
    expect(canMerge([text('a'), text('b'), text('c')], ['a', 'b'])).toBe(true)
    expect(canMerge([text('a'), text('b'), text('c')], ['a', 'c'])).toBe(false)
    expect(canMerge([text('a'), text('b', 'other')], ['a', 'b'])).toBe(false)
  })
})

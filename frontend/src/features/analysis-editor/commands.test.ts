import { describe, expect, it } from 'vitest'
import { canMerge, coalesceCommands, mergeValidationMessage } from './commands'
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
        { type: 'moveElement', elementId: 'a', targetElementId: 'b', placement: 'after' },
      ]),
    ).toEqual([
      { type: 'replaceText', elementId: 'a', text: 'two' },
      { type: 'moveElement', elementId: 'a', targetElementId: 'b', placement: 'after' },
    ])
  })

  it('permits compatible text regardless of its original parent or position', () => {
    expect(canMerge([text('a'), text('b'), text('c')], ['a', 'b'])).toBe(true)
    expect(canMerge([text('a'), text('b'), text('c')], ['a', 'c'])).toBe(true)
    expect(canMerge([text('a'), text('b', 'other')], ['a', 'b'])).toBe(true)
  })

  it('explains invalid merge selections', () => {
    expect(mergeValidationMessage([text('a')], ['a'])).toBe(
      'Select at least two elements to merge.',
    )
    expect(mergeValidationMessage([{ ...text('a'), type: 'table' }, text('b')], ['a', 'b'])).toBe(
      'Only text and paragraph elements can be merged.',
    )
  })
})

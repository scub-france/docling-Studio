import { describe, expect, it } from 'vitest'
import { canMerge, coalesceCommands, inReadingOrder, mergeValidationMessage } from './commands'
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

  it('keeps an edit made after a merge after that merge (#392)', () => {
    const queue = coalesceCommands([
      { type: 'replaceText', elementId: 'a', text: 'a1' },
      { type: 'mergeText', elementIds: ['a', 'b'], separator: ' ' },
      { type: 'replaceText', elementId: 'a', text: 'a1 b edited' },
    ])

    expect(queue).toEqual([
      { type: 'replaceText', elementId: 'a', text: 'a1' },
      { type: 'mergeText', elementIds: ['a', 'b'], separator: ' ' },
      { type: 'replaceText', elementId: 'a', text: 'a1 b edited' },
    ])
  })

  it('still folds edits across structural commands on other elements', () => {
    expect(
      coalesceCommands([
        { type: 'replaceText', elementId: 'a', text: 'one' },
        { type: 'deleteElement', elementId: 'c' },
        { type: 'mergeText', elementIds: ['d', 'e'], separator: ' ' },
        { type: 'replaceText', elementId: 'a', text: 'two' },
      ]),
    ).toEqual([
      { type: 'replaceText', elementId: 'a', text: 'two' },
      { type: 'deleteElement', elementId: 'c' },
      { type: 'mergeText', elementIds: ['d', 'e'], separator: ' ' },
    ])
  })

  it('stops folding at a move or delete of the same element', () => {
    const afterMove = coalesceCommands([
      { type: 'setHeadingLevel', elementId: 'a', level: 1 },
      { type: 'moveElement', elementId: 'a', targetElementId: 'b', placement: 'after' },
      { type: 'setHeadingLevel', elementId: 'a', level: 2 },
    ])
    expect(afterMove).toHaveLength(3)
    const afterDelete = coalesceCommands([
      { type: 'replaceText', elementId: 'a', text: 'one' },
      { type: 'deleteElements', elementIds: ['a', 'b'] },
      { type: 'replaceText', elementId: 'a', text: 'two' },
    ])
    expect(afterDelete).toHaveLength(3)
  })

  it('orders merge ids by reading order, not click order (#392)', () => {
    expect(inReadingOrder(['c', 'a', 'b'], ['a', 'b', 'c'])).toEqual(['a', 'b', 'c'])
    expect(inReadingOrder(['x', 'b', 'y', 'a'], ['a', 'b'])).toEqual(['a', 'b', 'x', 'y'])
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

import { describe, expect, it } from 'vitest'

import sampleDoclingDocument from './__fixtures__/sample-docling-document.json'
import {
  buildDoclingIndex,
  createDoclingGroup,
  deleteDoclingItem,
  type DoclingDocument,
  DoclingEditError,
  editDoclingText,
  exportDoclingDocument,
  getDoclingItem,
  insertDoclingText,
  mergeAdjacentDoclingTexts,
  moveDoclingItem,
  parseDoclingDocument,
  splitDoclingText,
} from './editing'
import { DoclingDraftSession } from './session'

function makeDocument(): DoclingDocument {
  return parseDoclingDocument(sampleDoclingDocument)
}

describe('docling editing core', () => {
  it('builds an index over a realistic fixture', () => {
    const doc = makeDocument()
    const index = buildDoclingIndex(doc)

    expect(index.itemsByRef.has('#/body')).toBe(true)
    expect(index.itemsByRef.has('#/groups/0')).toBe(true)
    expect(index.textRefs.has('#/texts/4')).toBe(true)
    expect(index.childrenByParentRef.get('#/groups/0')?.map((item) => item.$ref)).toEqual([
      '#/texts/2',
      '#/texts/3',
    ])
  })

  it('edits text immutably and updates charspan', () => {
    const doc = makeDocument()

    const edited = editDoclingText(doc, '#/texts/2', 'First paragraph updated.')

    expect(edited.texts[2].text).toBe('First paragraph updated.')
    expect(edited.texts[2].orig).toBe('First paragraph updated.')
    expect(edited.texts[2].prov?.[0]?.charspan).toEqual([0, 24])
    expect(doc.texts[2].text).toBe('First paragraph.')
  })

  it('splits a text node and renormalizes refs', () => {
    const doc = makeDocument()

    const split = splitDoclingText(doc, '#/texts/2', 5)

    expect(split.texts).toHaveLength(6)
    expect(split.texts[2].text).toBe('First')
    expect(split.texts[3].text).toBe(' paragraph.')
    expect(split.groups[0].children.map((item) => item.$ref)).toEqual(['#/texts/2', '#/texts/3', '#/texts/4'])
    expect(split.texts[4].self_ref).toBe('#/texts/4')
    expect(split.body.children.at(-1)?.$ref).toBe('#/texts/5')
  })

  it('merges adjacent text nodes and renormalizes trailing refs away', () => {
    const doc = splitDoclingText(makeDocument(), '#/texts/2', 5)

    const merged = mergeAdjacentDoclingTexts(doc, '#/texts/2', '#/texts/3')

    expect(merged.texts).toHaveLength(5)
    expect(merged.texts[2].text).toBe('First paragraph.')
    expect(merged.groups[0].children.map((item) => item.$ref)).toEqual(['#/texts/2', '#/texts/3'])
    expect(merged.texts[3].text).toBe('Second paragraph.')
  })

  it('moves an item into a group at a precise position', () => {
    const doc = makeDocument()

    const moved = moveDoclingItem(doc, '#/texts/4', '#/groups/0', 1)
    const movedText = getDoclingItem(moved, '#/texts/4')

    expect(movedText?.parent?.$ref).toBe('#/groups/0')
    expect(moved.groups[0].children.map((item) => item.$ref)).toEqual([
      '#/texts/2',
      '#/texts/4',
      '#/texts/3',
    ])
    expect(moved.body.children.map((item) => item.$ref)).toEqual([
      '#/texts/0',
      '#/texts/1',
      '#/groups/0',
    ])
  })

  it('creates a group, inserts text into it, and keeps the document valid', () => {
    const doc = makeDocument()

    const withGroup = createDoclingGroup(doc, {
      parentRef: '#/body',
      index: 1,
      name: 'notes',
      label: 'inline',
    })
    const inserted = insertDoclingText(withGroup, {
      parentRef: '#/groups/1',
      text: 'Inserted note',
      label: 'paragraph',
    })

    expect(inserted.groups).toHaveLength(2)
    expect(inserted.groups[1].self_ref).toBe('#/groups/1')
    expect(inserted.groups[1].children.map((item) => item.$ref)).toEqual(['#/texts/5'])
    expect(inserted.texts[5].text).toBe('Inserted note')
    expect(inserted.body.children[1]?.$ref).toBe('#/groups/1')
  })

  it('deletes a group recursively and renormalizes surviving refs', () => {
    const doc = makeDocument()

    const deleted = deleteDoclingItem(doc, '#/groups/0')

    expect(deleted.groups).toHaveLength(0)
    expect(deleted.texts).toHaveLength(3)
    expect(deleted.texts.map((item) => item.self_ref)).toEqual(['#/texts/0', '#/texts/1', '#/texts/2'])
    expect(deleted.body.children.map((item) => item.$ref)).toEqual(['#/texts/0', '#/texts/1', '#/texts/2'])
  })

  it('rejects invalid structures during parse', () => {
    const broken = structuredClone(sampleDoclingDocument)
    broken.groups[0].children.push({ $ref: '#/texts/999' })

    expect(() => parseDoclingDocument(broken)).toThrow(DoclingEditError)
  })

  it('tracks undo/redo/reset/checkpoint in the draft session', () => {
    const session = new DoclingDraftSession(sampleDoclingDocument)

    session.apply({ type: 'edit-text', itemRef: '#/texts/2', text: 'Edited paragraph.' })
    session.apply({ type: 'split-text', itemRef: '#/texts/2', offset: 6 })

    expect(session.hasChanges).toBe(true)
    expect(session.canUndo).toBe(true)
    expect(session.document.texts).toHaveLength(6)

    session.undo()
    expect(session.document.texts).toHaveLength(5)

    session.redo()
    expect(session.document.texts).toHaveLength(6)

    session.checkpoint()
    expect(session.hasChanges).toBe(false)
    expect(session.canUndo).toBe(false)

    session.apply({ type: 'delete-item', itemRef: '#/groups/0' })
    expect(session.hasChanges).toBe(true)

    session.reset()
    expect(session.hasChanges).toBe(false)
    expect(session.document.groups).toHaveLength(1)
  })

  it('keeps stable draft refs and renormalizes only on export', () => {
    const session = new DoclingDraftSession(sampleDoclingDocument)

    session.apply({
      type: 'insert-text',
      parentRef: '#/groups/0',
      index: 1,
      text: 'Inserted in session',
      label: 'paragraph',
    })

    const stableDraftRefs = session.document.groups[0].children.map((item) => item.$ref)
    expect(stableDraftRefs.some((ref) => ref.includes('__temp_'))).toBe(true)

    const exported = session.exportDocument()
    expect(exported.groups[0].children.every((ref) => !ref.$ref.includes('__temp_'))).toBe(true)
    expect(exported.texts.every((item, index) => item.self_ref === `#/texts/${index}`)).toBe(true)
  })

  it('exports canonical refs from direct non-normalized edits', () => {
    const draft = insertDoclingText(
      makeDocument(),
      {
        parentRef: '#/body',
        text: 'Tail note',
        label: 'paragraph',
      },
      { normalizeRefs: false },
    )

    expect(draft.texts.some((item) => item.self_ref.includes('__temp_'))).toBe(true)

    const exported = exportDoclingDocument(draft)
    expect(exported.texts.at(-1)?.self_ref).toBe(`#/texts/${exported.texts.length - 1}`)
  })
})

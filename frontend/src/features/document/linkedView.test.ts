import { describe, expect, it } from 'vitest'

import type { DocChunk, PageElement } from '../../shared/types'
import { chunkBboxesOnPage, chunkForElement, elementRefsForChunk } from './linkedView'

const makeChunk = (id: string, overrides: Partial<DocChunk> = {}): DocChunk => ({
  id,
  docId: 'd1',
  sequence: 0,
  text: '',
  headings: [],
  sourcePage: null,
  tokenCount: null,
  bboxes: [],
  docItems: [],
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  ...overrides,
})

const makeElement = (overrides: Partial<PageElement> = {}): PageElement => ({
  type: 'text',
  bbox: [0, 0, 100, 100],
  content: '',
  level: 0,
  ...overrides,
})

describe('chunkForElement', () => {
  it('returns the chunk whose docItems carry the element self_ref', () => {
    const chunks = [
      makeChunk('a', { docItems: [{ selfRef: '#/texts/1', label: 'text' }] }),
      makeChunk('b', { docItems: [{ selfRef: '#/texts/2', label: 'text' }] }),
    ]
    const el = makeElement({ self_ref: '#/texts/2' })
    expect(chunkForElement(el, 1, chunks)?.id).toBe('b')
  })

  it('falls back to bbox overlap when no self_ref match is found', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 100, 100] }] }),
      makeChunk('b', { bboxes: [{ page: 1, bbox: [500, 500, 600, 600] }] }),
    ]
    const el = makeElement({ bbox: [10, 10, 90, 90] }) // ~64% covered by 'a'
    expect(chunkForElement(el, 1, chunks)?.id).toBe('a')
  })

  it('ignores chunk bboxes on other pages during overlap fallback', () => {
    const chunks = [makeChunk('a', { bboxes: [{ page: 2, bbox: [0, 0, 100, 100] }] })]
    const el = makeElement()
    expect(chunkForElement(el, 1, chunks)).toBeNull()
  })

  it('returns null when overlap is below the coverage threshold', () => {
    const chunks = [makeChunk('a', { bboxes: [{ page: 1, bbox: [80, 80, 120, 120] }] })]
    const el = makeElement({ bbox: [0, 0, 100, 100] }) // 4% covered
    expect(chunkForElement(el, 1, chunks)).toBeNull()
  })

  it('picks the highest-coverage chunk on ambiguous overlap', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 60, 100] }] }), // 60%
      makeChunk('b', { bboxes: [{ page: 1, bbox: [0, 0, 90, 100] }] }), // 90%
    ]
    const el = makeElement({ bbox: [0, 0, 100, 100] })
    expect(chunkForElement(el, 1, chunks)?.id).toBe('b')
  })

  it('prefers exact self_ref over a higher-coverage overlap', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 100, 100] }] }), // overlap wins on bbox
      makeChunk('b', { docItems: [{ selfRef: '#/texts/3', label: 'text' }] }),
    ]
    const el = makeElement({ self_ref: '#/texts/3', bbox: [10, 10, 90, 90] })
    expect(chunkForElement(el, 1, chunks)?.id).toBe('b')
  })
})

describe('elementRefsForChunk', () => {
  it('extracts the self_ref strings from docItems', () => {
    const c = makeChunk('a', {
      docItems: [
        { selfRef: '#/texts/1', label: 'text' },
        { selfRef: '#/tables/0', label: 'table' },
      ],
    })
    expect(elementRefsForChunk(c, 1)).toEqual(new Set(['#/texts/1', '#/tables/0']))
  })

  it('returns an empty set when the chunk has no docItems', () => {
    expect(elementRefsForChunk(makeChunk('a'), 1)).toEqual(new Set())
  })

  it('skips empty self_ref entries', () => {
    const c = makeChunk('a', { docItems: [{ selfRef: '', label: 'text' }] })
    expect(elementRefsForChunk(c, 1)).toEqual(new Set())
  })
})

describe('chunkBboxesOnPage', () => {
  it('filters bboxes by page', () => {
    const c = makeChunk('a', {
      bboxes: [
        { page: 1, bbox: [0, 0, 10, 10] },
        { page: 2, bbox: [0, 0, 20, 20] },
        { page: 1, bbox: [0, 0, 30, 30] },
      ],
    })
    expect(chunkBboxesOnPage(c, 1)).toHaveLength(2)
    expect(chunkBboxesOnPage(c, 2)).toHaveLength(1)
    expect(chunkBboxesOnPage(c, 3)).toHaveLength(0)
  })
})

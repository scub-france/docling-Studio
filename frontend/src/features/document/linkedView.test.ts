import { describe, expect, it } from 'vitest'

import type { DocChunk, PageElement } from '../../shared/types'
import { findChunkForElement } from './linkedView'

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

describe('findChunkForElement', () => {
  it('returns the chunk whose docItems carry the element self_ref', () => {
    const chunks = [
      makeChunk('a', { docItems: [{ selfRef: '#/texts/1', label: 'text' }] }),
      makeChunk('b', { docItems: [{ selfRef: '#/texts/2', label: 'text' }] }),
    ]
    const el = makeElement({ self_ref: '#/texts/2' })
    expect(findChunkForElement(el, 1, chunks)?.id).toBe('b')
  })

  it('falls back to bbox overlap when no self_ref match is found', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 100, 100] }] }),
      makeChunk('b', { bboxes: [{ page: 1, bbox: [500, 500, 600, 600] }] }),
    ]
    const el = makeElement({ bbox: [10, 10, 90, 90] }) // ~64% covered by 'a'
    expect(findChunkForElement(el, 1, chunks)?.id).toBe('a')
  })

  it('ignores chunk bboxes on other pages during overlap fallback', () => {
    const chunks = [makeChunk('a', { bboxes: [{ page: 2, bbox: [0, 0, 100, 100] }] })]
    const el = makeElement()
    expect(findChunkForElement(el, 1, chunks)).toBeNull()
  })

  it('returns null when overlap is below the coverage threshold', () => {
    const chunks = [makeChunk('a', { bboxes: [{ page: 1, bbox: [80, 80, 120, 120] }] })]
    const el = makeElement({ bbox: [0, 0, 100, 100] }) // 4% covered
    expect(findChunkForElement(el, 1, chunks)).toBeNull()
  })

  it('picks the highest-coverage chunk on ambiguous overlap', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 60, 100] }] }), // 60%
      makeChunk('b', { bboxes: [{ page: 1, bbox: [0, 0, 90, 100] }] }), // 90%
    ]
    const el = makeElement({ bbox: [0, 0, 100, 100] })
    expect(findChunkForElement(el, 1, chunks)?.id).toBe('b')
  })

  it('prefers exact self_ref over a higher-coverage overlap', () => {
    const chunks = [
      makeChunk('a', { bboxes: [{ page: 1, bbox: [0, 0, 100, 100] }] }), // overlap wins on bbox
      makeChunk('b', { docItems: [{ selfRef: '#/texts/3', label: 'text' }] }),
    ]
    const el = makeElement({ self_ref: '#/texts/3', bbox: [10, 10, 90, 90] })
    expect(findChunkForElement(el, 1, chunks)?.id).toBe('b')
  })
})

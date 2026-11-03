/**
 * Tests for the selection of the docs library (#354).
 *
 * Pure-function tests only — the frontend doesn't ship a DOM test
 * environment, so `DocsLibraryPage.vue` is not mountable.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  SUMMARIES_PAGE,
  countDocumentAnalyses,
  keepListed,
  selectionState,
  toggleListed,
  toggleOne,
} from './DocsLibraryPage.logic'

const LISTED = ['d1', 'd2', 'd3']

describe('selectionState', () => {
  it('tells none, some or all of the listed documents apart', () => {
    expect(selectionState(new Set(), LISTED)).toBe('none')
    expect(selectionState(new Set(['d2']), LISTED)).toBe('some')
    expect(selectionState(new Set(LISTED), LISTED)).toBe('all')
  })

  it('is none on an empty list', () => {
    expect(selectionState(new Set(), [])).toBe('none')
  })
})

describe('toggleListed', () => {
  it('selects every listed document when some are not', () => {
    expect(toggleListed(new Set(['d2']), LISTED)).toEqual(new Set(LISTED))
  })

  it('clears the selection once every listed document is selected', () => {
    expect(toggleListed(new Set(LISTED), LISTED)).toEqual(new Set())
  })
})

describe('toggleOne', () => {
  it('adds a document, then removes it', () => {
    const once = toggleOne(new Set(), 'd1')
    expect(once).toEqual(new Set(['d1']))
    expect(toggleOne(once, 'd1')).toEqual(new Set())
  })

  it('returns a new set rather than mutating the current one', () => {
    const selected = new Set(['d1'])
    toggleOne(selected, 'd2')
    expect(selected).toEqual(new Set(['d1']))
  })
})

describe('keepListed', () => {
  it('drops the documents the filter or a deletion took off the list', () => {
    expect(keepListed(new Set(['d1', 'gone']), LISTED)).toEqual(new Set(['d1']))
  })
})

describe('countDocumentAnalyses', () => {
  const rows = (...documentIds: string[]) => documentIds.map((documentId) => ({ documentId }))

  it("counts the document's analyses from the summaries alone", async () => {
    const lookup = {
      summaries: vi.fn().mockResolvedValue(rows('d1', 'd2', 'd1')),
      ofDocument: vi.fn(),
    }

    expect(await countDocumentAnalyses('d1', lookup)).toBe(2)
    expect(await countDocumentAnalyses('d3', lookup)).toBe(0)
    expect(lookup.ofDocument).not.toHaveBeenCalled()
  })

  it("asks for the document's own list when the summaries may be cut short", async () => {
    const full = rows(...Array.from({ length: SUMMARIES_PAGE }, () => 'other'))
    const lookup = {
      summaries: vi.fn().mockResolvedValue(full),
      ofDocument: vi.fn().mockResolvedValue([{}, {}, {}]),
    }

    expect(await countDocumentAnalyses('d1', lookup)).toBe(3)
    expect(lookup.ofDocument).toHaveBeenCalledWith('d1')
  })

  it('lets a failed lookup reach the caller, which cancels the deletion', async () => {
    const lookup = {
      summaries: vi.fn().mockRejectedValue(new Error('network')),
      ofDocument: vi.fn(),
    }

    await expect(countDocumentAnalyses('d1', lookup)).rejects.toThrow('network')
  })
})

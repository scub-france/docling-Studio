import { describe, expect, it } from 'vitest'
import { parseAnalysisPages } from './analysisPages'

describe('parseAnalysisPages', () => {
  it('returns the pages of the analysis', () => {
    const pages = [{ page_number: 1, width: 612, height: 792, elements: [] }]

    expect(parseAnalysisPages({ pagesJson: JSON.stringify(pages) })).toEqual(pages)
  })

  it('returns no page when there is no analysis or no pagesJson', () => {
    expect(parseAnalysisPages(null)).toEqual([])
    expect(parseAnalysisPages(undefined)).toEqual([])
    expect(parseAnalysisPages({ pagesJson: null })).toEqual([])
    expect(parseAnalysisPages({ pagesJson: '' })).toEqual([])
  })

  it('returns no page when pagesJson is not valid JSON', () => {
    expect(parseAnalysisPages({ pagesJson: '{not json' })).toEqual([])
  })
})

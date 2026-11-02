import { describe, expect, it } from 'vitest'

import {
  centeredScrollPosition,
  isFocusScrollRequest,
  isRectVisible,
  mostVisiblePage,
  pageFrameGeometry,
  pageTopScrollPosition,
} from './previewScroll'

describe('mostVisiblePage', () => {
  it('selects the highest ratio from the complete visibility snapshot', () => {
    expect(
      mostVisiblePage(
        new Map([
          [1, 0.25],
          [2, 0.75],
          [3, 0.5],
        ]),
      ),
    ).toBe(2)
  })

  it('ignores pages whose stored ratio is zero', () => {
    expect(
      mostVisiblePage(
        new Map([
          [1, 0],
          [2, 0.4],
        ]),
      ),
    ).toBe(2)
    expect(mostVisiblePage(new Map([[1, 0]]))).toBeNull()
  })
})

describe('isRectVisible', () => {
  const viewport = { top: 10, right: 210, bottom: 210, left: 10 }

  it('accepts a rectangle fully inside the viewport', () => {
    expect(isRectVisible({ top: 20, right: 100, bottom: 100, left: 20 }, viewport)).toBe(true)
  })

  it('rejects a rectangle clipped by an edge', () => {
    expect(isRectVisible({ top: 5, right: 100, bottom: 100, left: 20 }, viewport)).toBe(false)
  })
})

describe('centeredScrollPosition', () => {
  it('centers viewport-relative element geometry in scroll space', () => {
    expect(
      centeredScrollPosition(
        { scrollTop: 300, scrollLeft: 100, clientWidth: 400, clientHeight: 600 },
        { top: 50, left: 20 },
        { x: 220, y: 450, w: 40, h: 100 },
      ),
    ).toEqual({ left: 120, top: 450 })
  })

  it('clamps positions at the scroll origin', () => {
    expect(
      centeredScrollPosition(
        { scrollTop: 0, scrollLeft: 0, clientWidth: 400, clientHeight: 600 },
        { top: 0, left: 0 },
        { x: 10, y: 10, w: 20, h: 20 },
      ),
    ).toEqual({ left: 0, top: 0 })
  })
})

describe('pageFrameGeometry', () => {
  it('reserves the page box from its point dimensions and the raster density', () => {
    // A4 at 150 dpi: 595pt / 72 * 150 ≈ 1240px of natural raster width.
    expect(pageFrameGeometry({ width: 595, height: 842 }, 150)).toEqual({
      aspectRatio: '595 / 842',
      maxWidth: '1240px',
    })
  })

  it('caps a narrow page at its own raster width rather than the column', () => {
    expect(pageFrameGeometry({ width: 144, height: 144 }, 72)).toEqual({
      aspectRatio: '144 / 144',
      maxWidth: '144px',
    })
  })

  it('declines to reserve a box for a degenerate page or density', () => {
    expect(pageFrameGeometry({ width: 0, height: 842 }, 150)).toBeNull()
    expect(pageFrameGeometry({ width: 595, height: -1 }, 150)).toBeNull()
    expect(pageFrameGeometry({ width: 595, height: 842 }, 0)).toBeNull()
  })
})

describe('pageTopScrollPosition', () => {
  it('brings a card below the fold up to the top of the viewport', () => {
    expect(pageTopScrollPosition(300, 50, 420)).toBe(670)
  })

  it('clamps at the scroll origin for a card above the viewport', () => {
    expect(pageTopScrollPosition(0, 80, 20)).toBe(0)
  })
})

describe('isFocusScrollRequest', () => {
  it('asks to scroll when an element is focused', () => {
    expect(isFocusScrollRequest(new Set(['#/texts/3']))).toBe(true)
  })

  it('does not scroll when the focus is cleared (Show all)', () => {
    expect(isFocusScrollRequest(new Set())).toBe(false)
  })

  it('does not scroll when the preview has no highlight at all', () => {
    expect(isFocusScrollRequest(undefined)).toBe(false)
  })
})

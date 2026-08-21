import { describe, expect, it } from 'vitest'

import { centeredScrollPosition, isRectVisible, mostVisiblePage } from './previewScroll'

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

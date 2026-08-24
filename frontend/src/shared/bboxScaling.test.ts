import { describe, it, expect } from 'vitest'
import { computeScale, bboxToRect, pointInRect, EMPTY_RECT } from './bboxScaling'

// ---------------------------------------------------------------------------
// computeScale
// ---------------------------------------------------------------------------

describe('computeScale', () => {
  it('returns 1:1 when display matches page', () => {
    const s = computeScale(612, 792, 612, 792)
    expect(s.sx).toBe(1)
    expect(s.sy).toBe(1)
  })

  it('scales proportionally', () => {
    const s = computeScale(306, 396, 612, 792)
    expect(s.sx).toBeCloseTo(0.5)
    expect(s.sy).toBeCloseTo(0.5)
  })

  it('sx equals sy when aspect ratio is preserved', () => {
    const pageW = 612,
      pageH = 792
    const displayW = 700
    const displayH = (displayW * pageH) / pageW
    const s = computeScale(displayW, displayH, pageW, pageH)
    expect(s.sx).toBeCloseTo(s.sy, 5)
  })

  it('handles A4 page dimensions', () => {
    const s = computeScale(595.28, 841.89, 595.28, 841.89)
    expect(s.sx).toBeCloseTo(1)
    expect(s.sy).toBeCloseTo(1)
  })

  it('returns 1:1 fallback when pageWidth is zero', () => {
    const s = computeScale(600, 800, 0, 792)
    expect(s.sx).toBe(1)
    expect(s.sy).toBe(1)
  })

  it('returns 1:1 fallback when pageHeight is zero', () => {
    const s = computeScale(600, 800, 612, 0)
    expect(s.sx).toBe(1)
    expect(s.sy).toBe(1)
  })

  it('returns 1:1 fallback when page dimensions are negative', () => {
    const s = computeScale(600, 800, -612, -792)
    expect(s.sx).toBe(1)
    expect(s.sy).toBe(1)
  })

  it('handles very large scale factors', () => {
    const s = computeScale(6120, 7920, 612, 792)
    expect(s.sx).toBeCloseTo(10)
    expect(s.sy).toBeCloseTo(10)
  })

  it('handles very small scale factors', () => {
    const s = computeScale(61.2, 79.2, 612, 792)
    expect(s.sx).toBeCloseTo(0.1)
    expect(s.sy).toBeCloseTo(0.1)
  })
})

// ---------------------------------------------------------------------------
// bboxToRect
// ---------------------------------------------------------------------------

describe('bboxToRect', () => {
  it('maps page coordinates to pixel rect at scale 1', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([10, 20, 110, 80], scale)
    expect(rect).toEqual({ x: 10, y: 20, w: 100, h: 60 })
  })

  it('scales correctly at 2x', () => {
    const scale = { sx: 2, sy: 2 }
    const rect = bboxToRect([10, 20, 60, 70], scale)
    expect(rect).toEqual({ x: 20, y: 40, w: 100, h: 100 })
  })

  it('handles fractional scales', () => {
    const scale = { sx: 0.5, sy: 0.5 }
    const rect = bboxToRect([100, 200, 300, 400], scale)
    expect(rect.x).toBeCloseTo(50)
    expect(rect.y).toBeCloseTo(100)
    expect(rect.w).toBeCloseTo(100)
    expect(rect.h).toBeCloseTo(100)
  })

  it('end-to-end: full page bbox fills display', () => {
    const scale = computeScale(700, 907.84, 612, 792)
    const rect = bboxToRect([0, 0, 612, 792], scale)
    expect(rect.x).toBeCloseTo(0)
    expect(rect.y).toBeCloseTo(0)
    expect(rect.w).toBeCloseTo(700)
    expect(rect.h).toBeCloseTo(907.84, 0)
  })

  it('returns EMPTY_RECT for zero-width bbox', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([100, 20, 100, 80], scale)
    expect(rect).toEqual(EMPTY_RECT)
  })

  it('returns EMPTY_RECT for zero-height bbox', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([10, 50, 100, 50], scale)
    expect(rect).toEqual(EMPTY_RECT)
  })

  it('returns EMPTY_RECT for inverted bbox (l > r)', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([200, 20, 100, 80], scale)
    expect(rect).toEqual(EMPTY_RECT)
  })

  it('returns EMPTY_RECT for inverted bbox (t > b)', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([10, 100, 200, 50], scale)
    expect(rect).toEqual(EMPTY_RECT)
  })

  it('returns EMPTY_RECT for all-zero bbox', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([0, 0, 0, 0], scale)
    expect(rect).toEqual(EMPTY_RECT)
  })

  it('handles tiny but valid bbox', () => {
    const scale = { sx: 1, sy: 1 }
    const rect = bboxToRect([100, 200, 100.5, 200.5], scale)
    expect(rect.w).toBeCloseTo(0.5)
    expect(rect.h).toBeCloseTo(0.5)
  })

  it('each EMPTY_RECT return is a fresh object', () => {
    const scale = { sx: 1, sy: 1 }
    const r1 = bboxToRect([100, 20, 100, 80], scale)
    const r2 = bboxToRect([100, 20, 100, 80], scale)
    expect(r1).toEqual(r2)
    expect(r1).not.toBe(r2) // different instances
  })

  it('handles non-uniform scale (sx != sy)', () => {
    const scale = { sx: 2, sy: 0.5 }
    const rect = bboxToRect([10, 20, 60, 120], scale)
    expect(rect.x).toBe(20)
    expect(rect.y).toBe(10)
    expect(rect.w).toBe(100)
    expect(rect.h).toBe(50)
  })
})

// ---------------------------------------------------------------------------
// pointInRect
// ---------------------------------------------------------------------------

describe('pointInRect', () => {
  const rect = { x: 10, y: 20, w: 100, h: 60 }

  it('returns true for point inside', () => {
    expect(pointInRect(50, 50, rect)).toBe(true)
  })

  it('returns true for point on edge', () => {
    expect(pointInRect(10, 20, rect)).toBe(true) // top-left
    expect(pointInRect(110, 80, rect)).toBe(true) // bottom-right
    expect(pointInRect(10, 80, rect)).toBe(true) // bottom-left
    expect(pointInRect(110, 20, rect)).toBe(true) // top-right
  })

  it('returns false for point outside', () => {
    expect(pointInRect(5, 50, rect)).toBe(false) // left
    expect(pointInRect(50, 15, rect)).toBe(false) // above
    expect(pointInRect(115, 50, rect)).toBe(false) // right
    expect(pointInRect(50, 85, rect)).toBe(false) // below
  })

  it('returns false for EMPTY_RECT (degenerate bbox not hoverable)', () => {
    expect(pointInRect(0, 0, EMPTY_RECT)).toBe(true) // edge: (0,0) is on the boundary
    expect(pointInRect(1, 1, { x: 0, y: 0, w: 0, h: 0 })).toBe(false)
  })

  it('returns true for point at center of rect', () => {
    const center = { x: 10 + 100 / 2, y: 20 + 60 / 2 }
    expect(pointInRect(center.x, center.y, rect)).toBe(true)
  })

  it('handles rect at origin', () => {
    const originRect = { x: 0, y: 0, w: 50, h: 30 }
    expect(pointInRect(0, 0, originRect)).toBe(true)
    expect(pointInRect(25, 15, originRect)).toBe(true)
    expect(pointInRect(-1, 0, originRect)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Integration: full pipeline bbox → rect → hit test
// ---------------------------------------------------------------------------

describe('integration: bbox pipeline', () => {
  it('full A4 page: element is clickable at correct position', () => {
    // Simulate: A4 page rendered at 700px wide
    const pageW = 595.28,
      pageH = 841.89
    const displayW = 700,
      displayH = (700 * pageH) / pageW

    const scale = computeScale(displayW, displayH, pageW, pageH)
    // Element at center of page in PDF points
    const bbox: [number, number, number, number] = [200, 350, 400, 500]
    const rect = bboxToRect(bbox, scale)

    // Center of the element in display pixels
    const cx = ((200 + 400) / 2) * scale.sx
    const cy = ((350 + 500) / 2) * scale.sy

    expect(pointInRect(cx, cy, rect)).toBe(true)
  })

  it('degenerate bbox is not clickable', () => {
    const scale = computeScale(700, 900, 612, 792)
    const rect = bboxToRect([100, 100, 100, 200], scale) // zero width
    expect(pointInRect(100, 150, rect)).toBe(false)
  })

  it('two adjacent elements have correct non-overlapping rects', () => {
    const scale = computeScale(612, 792, 612, 792) // 1:1
    const rect1 = bboxToRect([0, 0, 100, 50], scale)
    const rect2 = bboxToRect([0, 50, 100, 100], scale)

    // Point between them (y=50) is on edge of both
    expect(pointInRect(50, 50, rect1)).toBe(true)
    expect(pointInRect(50, 50, rect2)).toBe(true)

    // Point clearly in first only
    expect(pointInRect(50, 25, rect1)).toBe(true)
    expect(pointInRect(50, 25, rect2)).toBe(false)

    // Point clearly in second only
    expect(pointInRect(50, 75, rect1)).toBe(false)
    expect(pointInRect(50, 75, rect2)).toBe(true)
  })
})

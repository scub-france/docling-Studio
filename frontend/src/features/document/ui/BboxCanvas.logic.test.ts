import { describe, expect, it } from 'vitest'
import { computeBadgeRect } from './BboxCanvas.logic'

describe('computeBadgeRect', () => {
  const bounds = { width: 200, height: 100 }

  it('sits 2px inside the top-left corner of the box', () => {
    expect(computeBadgeRect({ x: 10, y: 20 }, 3, bounds)).toEqual({ x: 12, y: 22, w: 18, h: 18 })
  })

  it('widens with the number of digits', () => {
    expect(computeBadgeRect({ x: 0, y: 0 }, 42, bounds).w).toBe(24)
    expect(computeBadgeRect({ x: 0, y: 0 }, 123, bounds).w).toBe(31)
  })

  it('stays inside the canvas', () => {
    expect(computeBadgeRect({ x: 195, y: 95 }, 1, bounds)).toEqual({ x: 182, y: 82, w: 18, h: 18 })
    expect(computeBadgeRect({ x: -50, y: -50 }, 1, bounds)).toEqual({ x: 0, y: 0, w: 18, h: 18 })
  })
})

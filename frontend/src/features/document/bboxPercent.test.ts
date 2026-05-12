import { describe, expect, it } from 'vitest'

import { bboxToPercent } from './bboxPercent'

describe('bboxToPercent', () => {
  it('maps a bbox to one-decimal percentages of the page size', () => {
    expect(bboxToPercent([100, 200, 700, 600], 1000, 800)).toEqual({
      x: '10.0',
      y: '25.0',
      w: '60.0',
      h: '50.0',
    })
  })

  it('rounds to one decimal place', () => {
    expect(bboxToPercent([0, 0, 333, 333], 1000, 1000)).toEqual({
      x: '0.0',
      y: '0.0',
      w: '33.3',
      h: '33.3',
    })
  })

  it('returns zeros on a zero-width page', () => {
    expect(bboxToPercent([0, 0, 10, 10], 0, 800)).toEqual({
      x: '0.0',
      y: '0.0',
      w: '0.0',
      h: '0.0',
    })
  })

  it('returns zeros on a zero-height page', () => {
    expect(bboxToPercent([0, 0, 10, 10], 1000, 0)).toEqual({
      x: '0.0',
      y: '0.0',
      w: '0.0',
      h: '0.0',
    })
  })

  it('returns zeros on a negative page dimension (defensive)', () => {
    expect(bboxToPercent([0, 0, 10, 10], -1, 800)).toEqual({
      x: '0.0',
      y: '0.0',
      w: '0.0',
      h: '0.0',
    })
  })
})

import { describe, expect, it } from 'vitest'
import { axisTicks, computeBars, fmtDur, fmtTick, hasTiming, totalDuration } from './timeline.logic'
import type { ReasoningStep } from './types'

function step(durationMs: number, id = `s${durationMs}`): ReasoningStep {
  return {
    id,
    kind: 'read',
    title: 't',
    summary: 's',
    durationMs,
    tokenCount: 0,
    citations: [],
    payload: { canAnswer: false, iteration: 1 },
  }
}

describe('fmtDur', () => {
  it('renders an em dash for null/undefined', () => {
    expect(fmtDur(null)).toBe('—')
    expect(fmtDur(undefined)).toBe('—')
  })

  it('renders ms under 1s', () => {
    expect(fmtDur(760)).toBe('760ms')
    expect(fmtDur(999)).toBe('999ms')
    expect(fmtDur(0)).toBe('0ms')
  })

  it('renders seconds with one trailing zero stripped above 1s', () => {
    expect(fmtDur(2230)).toBe('2.23s')
    expect(fmtDur(7050)).toBe('7.05s')
    expect(fmtDur(2200)).toBe('2.2s')
    expect(fmtDur(7000)).toBe('7.0s')
  })
})

describe('fmtTick', () => {
  it('uses ms while total is under 5s', () => {
    expect(fmtTick(0, 4000)).toBe('0')
    expect(fmtTick(1000, 4000)).toBe('1000ms')
  })

  it('uses seconds once total reaches 5s', () => {
    expect(fmtTick(0, 7000)).toBe('0')
    expect(fmtTick(3500, 7000)).toBe('3.5s')
  })
})

describe('hasTiming', () => {
  it('is false when every step has zero duration', () => {
    expect(hasTiming([step(0), step(0, 'a')])).toBe(false)
  })

  it('is true when at least one step has a positive duration', () => {
    expect(hasTiming([step(0), step(5, 'a')])).toBe(true)
  })
})

describe('totalDuration', () => {
  it('sums step durations', () => {
    expect(totalDuration([step(100), step(300, 'a')])).toBe(400)
  })
})

describe('computeBars', () => {
  it('lays bars cumulatively when timing is present', () => {
    const bars = computeBars([step(100), step(300, 'a')])
    expect(bars[0].left).toBeCloseTo(0)
    expect(bars[0].width).toBeCloseTo(25)
    expect(bars[1].left).toBeCloseTo(25)
    expect(bars[1].width).toBeCloseTo(75)
  })

  it('distributes bars uniformly when timing is absent', () => {
    const bars = computeBars([step(0), step(0, 'a'), step(0, 'b')])
    expect(bars.map((b) => b.left)).toEqual([0, (1 / 3) * 100, (2 / 3) * 100])
    expect(bars.every((b) => Math.abs(b.width - (1 / 3) * 100) < 1e-9)).toBe(true)
  })
})

describe('axisTicks', () => {
  it('returns 5 ticks across the total when timing is present', () => {
    // total 8000ms (>=5s) → seconds
    const ticks = axisTicks([step(2000), step(6000, 'a')])
    expect(ticks).toEqual(['0', '2.0s', '4.0s', '6.0s', '8.0s'])
  })

  it('uses ms ticks under 5s total', () => {
    const ticks = axisTicks([step(1000), step(3000, 'a')])
    expect(ticks).toEqual(['0', '1000ms', '2000ms', '3000ms', '4000ms'])
  })

  it('returns a single "step order" label in the degraded state', () => {
    expect(axisTicks([step(0), step(0, 'a')])).toEqual(['step order'])
  })
})

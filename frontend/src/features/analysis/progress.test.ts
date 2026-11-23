import { describe, expect, it } from 'vitest'

import { computeAnalysisProgress, formatElapsed } from './progress'

const STARTED = '2026-09-28T12:00:00+00:00'
const at = (seconds: number) => Date.parse(STARTED) + seconds * 1000

function run(overrides: Partial<Parameters<typeof computeAnalysisProgress>[0]> = {}) {
  return {
    progressCurrent: null,
    progressTotal: null,
    startedAt: STARTED,
    createdAt: '2026-09-28T11:59:58+00:00',
    ...overrides,
  }
}

describe('computeAnalysisProgress', () => {
  it('shows the pages done when the conversion runs in batches', () => {
    expect(computeAnalysisProgress(run({ progressCurrent: 10, progressTotal: 25 }), at(5))).toEqual(
      {
        kind: 'pages',
        percent: 40,
        done: 10,
        total: 25,
      },
    )
  })

  it('starts batched progress at 0 % before the first batch ends', () => {
    expect(computeAnalysisProgress(run({ progressCurrent: 0, progressTotal: 25 }), at(5))).toEqual({
      kind: 'pages',
      percent: 0,
      done: 0,
      total: 25,
    })
  })

  it('never goes past 100 %', () => {
    const progress = computeAnalysisProgress(run({ progressCurrent: 30, progressTotal: 25 }), at(5))
    expect(progress).toMatchObject({ percent: 100, done: 25 })
  })

  it('falls back to the time elapsed without batch progress', () => {
    expect(computeAnalysisProgress(run(), at(83))).toEqual({ kind: 'elapsed', seconds: 83 })
  })

  it('counts from the creation while the analysis waits for a slot', () => {
    expect(computeAnalysisProgress(run({ startedAt: null }), at(0))).toEqual({
      kind: 'elapsed',
      seconds: 2,
    })
  })

  it('never shows a negative time when the clocks disagree', () => {
    expect(computeAnalysisProgress(run(), at(-3))).toEqual({ kind: 'elapsed', seconds: 0 })
  })
})

describe('formatElapsed', () => {
  it('writes minutes and seconds under an hour', () => {
    expect(formatElapsed(0)).toBe('0:00')
    expect(formatElapsed(83)).toBe('1:23')
    expect(formatElapsed(3599)).toBe('59:59')
  })

  it('adds the hours from there', () => {
    expect(formatElapsed(3600)).toBe('1:00:00')
    expect(formatElapsed(3725)).toBe('1:02:05')
  })
})

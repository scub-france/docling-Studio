// Pure geometry + formatting for the trace timeline (#303). No Vue, no DOM —
// unit-tested in isolation. Ported from the handoff prototype's `reasoning.jsx`
// (fmtDur / fmtTick / bar geometry / axis ticks), kept byte-faithful to the
// binding spec.

import type { ReasoningStep } from './types'

/** Duration label: `Nms` under 1s, `N.NNs` above (one trailing zero stripped). */
export function fmtDur(ms: number | null | undefined): string {
  if (ms == null) return '—'
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2).replace(/0$/, '')}s`
}

/** Axis tick label: ms while the run is under 5s total, else seconds. */
export function fmtTick(ms: number, totalMs: number): string {
  if (totalMs < 5000) return `${Math.round(ms)}${ms === 0 ? '' : 'ms'}`
  return ms === 0 ? '0' : `${(ms / 1000).toFixed(1)}s`
}

/**
 * True when at least one step carries a real per-step duration. When false the
 * timeline renders the degraded state (uniform bars + "step order" axis +
 * footnote) — never fake identical durations.
 */
export function hasTiming(steps: ReasoningStep[]): boolean {
  return steps.some((s) => s.durationMs > 0)
}

/** Cumulative sum of step durations (the shared time axis total). */
export function totalDuration(steps: ReasoningStep[]): number {
  return steps.reduce((acc, s) => acc + (s.durationMs || 0), 0)
}

export interface TraceBar {
  step: ReasoningStep
  /** Bar left offset, as a percentage of the total. */
  left: number
  /** Bar width, as a percentage of the total (the row clamps to >= 3px). */
  width: number
}

/**
 * Bar geometry per step. With real timing, bars are laid cumulatively along the
 * shared axis (`left = cumStart/total`, `width = duration/total`). Without it,
 * bars are distributed uniformly (`left = i/n`, `width = 1/n`).
 */
export function computeBars(steps: ReasoningStep[]): TraceBar[] {
  const timed = hasTiming(steps)
  const total = timed ? totalDuration(steps) : 0
  let cum = 0
  return steps.map((s, i) => {
    let left: number
    let width: number
    if (timed && total > 0) {
      left = (cum / total) * 100
      width = ((s.durationMs || 0) / total) * 100
      cum += s.durationMs || 0
    } else {
      left = (i / steps.length) * 100
      width = (1 / steps.length) * 100
    }
    return { step: s, left, width }
  })
}

/**
 * The 5 axis tick labels (0/25/50/75/100% of total) when timing is available,
 * or a single `step order` label for the degraded state.
 */
export function axisTicks(steps: ReasoningStep[]): string[] {
  if (!hasTiming(steps)) return ['step order']
  const total = totalDuration(steps)
  return [0, 0.25, 0.5, 0.75, 1].map((f) => fmtTick(total * f, total))
}

/**
 * Convert a [left, top, right, bottom] bbox (in page points) to a
 * relative-to-page percentage rect. Used by the Properties panel (#265)
 * so the displayed x/y/width/height match the maquette's `14%`-style
 * notation regardless of the rendered image's display size.
 *
 * Returns zeros on degenerate inputs (zero or negative page dimensions),
 * so callers can render `0.0%` instead of crashing on bad data.
 */

export interface BboxPercent {
  x: string
  y: string
  w: string
  h: string
}

const ZERO: BboxPercent = { x: '0.0', y: '0.0', w: '0.0', h: '0.0' }

export function bboxToPercent(
  bbox: readonly [number, number, number, number],
  pageWidth: number,
  pageHeight: number,
): BboxPercent {
  if (pageWidth <= 0 || pageHeight <= 0) return { ...ZERO }
  const [l, t, r, b] = bbox
  return {
    x: ((l / pageWidth) * 100).toFixed(1),
    y: ((t / pageHeight) * 100).toFixed(1),
    w: (((r - l) / pageWidth) * 100).toFixed(1),
    h: (((b - t) / pageHeight) * 100).toFixed(1),
  }
}

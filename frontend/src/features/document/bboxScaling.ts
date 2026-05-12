import type { Scale, Rect } from '../../shared/types'

/** Sentinel rect for degenerate bboxes — zero area, ignored by hit-testing. */
export const EMPTY_RECT: Rect = { x: 0, y: 0, w: 0, h: 0 }

/**
 * Compute scale factors to map page coordinates (PDF points) to display pixels.
 * Returns { sx: 1, sy: 1 } if page dimensions are zero to avoid division by zero.
 */
export function computeScale(
  displayWidth: number,
  displayHeight: number,
  pageWidth: number,
  pageHeight: number,
): Scale {
  // Guard: avoid division by zero when page dimensions are missing.
  if (pageWidth <= 0 || pageHeight <= 0) {
    return { sx: 1, sy: 1 }
  }
  return {
    sx: displayWidth / pageWidth,
    sy: displayHeight / pageHeight,
  }
}

/**
 * Convert a [l, t, r, b] bbox (in page points) to a pixel Rect using the given scale.
 * Returns EMPTY_RECT for degenerate bboxes (zero or negative dimensions).
 */
export function bboxToRect(bbox: [number, number, number, number], scale: Scale): Rect {
  const [l, t, r, b] = bbox
  const w = (r - l) * scale.sx
  const h = (b - t) * scale.sy

  // Degenerate bbox: the backend should filter these, but guard here too.
  if (w <= 0 || h <= 0) {
    return { ...EMPTY_RECT }
  }

  return {
    x: l * scale.sx,
    y: t * scale.sy,
    w,
    h,
  }
}

/**
 * Check if a point (px, py) is inside a Rect.
 * Returns false for EMPTY_RECT (w=0, h=0) — degenerate bboxes are not hoverable.
 */
export function pointInRect(px: number, py: number, rect: Rect): boolean {
  return px >= rect.x && px <= rect.x + rect.w && py >= rect.y && py <= rect.y + rect.h
}

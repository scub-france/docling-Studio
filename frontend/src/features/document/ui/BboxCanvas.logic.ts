import type { Rect } from '@/shared/types'

/** Canvas pixel size; an `HTMLCanvasElement` fits. */
export interface CanvasBounds {
  width: number
  height: number
}

const BADGE_HEIGHT = 18
const BADGE_MIN_WIDTH = 18

/**
 * Rect of the reading-order badge drawn at the top-left corner of an element
 * box: wide enough for the number, kept inside the canvas.
 */
export function computeBadgeRect(
  rect: { x: number; y: number },
  order: number,
  bounds: CanvasBounds,
): Rect {
  const w = Math.max(BADGE_MIN_WIDTH, String(order).length * 7 + 10)
  const h = BADGE_HEIGHT
  return {
    x: Math.max(0, Math.min(rect.x + 2, bounds.width - w)),
    y: Math.max(0, Math.min(rect.y + 2, bounds.height - h)),
    w,
    h,
  }
}

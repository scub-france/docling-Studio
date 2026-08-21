import type { Rect } from '../../shared/types'

interface ViewportRect {
  top: number
  right: number
  bottom: number
  left: number
}

interface ScrollState {
  scrollTop: number
  scrollLeft: number
  clientWidth: number
  clientHeight: number
}

export function mostVisiblePage(ratios: ReadonlyMap<number, number>): number | null {
  let bestPage: number | null = null
  let bestRatio = 0
  for (const [page, ratio] of ratios) {
    if (ratio > bestRatio) {
      bestPage = page
      bestRatio = ratio
    }
  }
  return bestPage
}

export function isRectVisible(rect: ViewportRect, viewport: ViewportRect): boolean {
  return (
    rect.top >= viewport.top &&
    rect.bottom <= viewport.bottom &&
    rect.left >= viewport.left &&
    rect.right <= viewport.right
  )
}

export function centeredScrollPosition(
  state: ScrollState,
  viewport: Pick<ViewportRect, 'top' | 'left'>,
  rect: Rect,
): { top: number; left: number } {
  return {
    left: Math.max(
      0,
      state.scrollLeft + rect.x - viewport.left + rect.w / 2 - state.clientWidth / 2,
    ),
    top: Math.max(
      0,
      state.scrollTop + rect.y - viewport.top + rect.h / 2 - state.clientHeight / 2,
    ),
  }
}

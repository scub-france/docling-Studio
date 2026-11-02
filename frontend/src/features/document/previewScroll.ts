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
    top: Math.max(0, state.scrollTop + rect.y - viewport.top + rect.h / 2 - state.clientHeight / 2),
  }
}

/** PDF page geometry is expressed in points; rasters are requested in DPI. */
const POINTS_PER_INCH = 72

/**
 * Displayed geometry of a page card, derived from the page's own point
 * dimensions instead of a decoded raster.
 *
 * The stacked preview only mounts the `<img>` of pages inside the render
 * window, so without this a card off-window collapses to its header and
 * re-inflates when its image decodes. That layout shift is what made the
 * preview flicker and what invalidated every scroll target computed while it
 * was in flight (#336). Reserving the box up front removes both.
 *
 * `maxWidth` reproduces the natural width of the raster (`page.width` points
 * at `dpi`), so a page smaller than the column keeps rendering at its own
 * size rather than being upscaled.
 *
 * Returns `null` for a degenerate page — the caller then falls back to
 * sizing the card from the image, as before.
 */
export function pageFrameGeometry(
  page: { width: number; height: number },
  dpi: number,
): { aspectRatio: string; maxWidth: string } | null {
  if (page.width <= 0 || page.height <= 0 || dpi <= 0) return null
  return {
    aspectRatio: `${page.width} / ${page.height}`,
    maxWidth: `${Math.round((page.width / POINTS_PER_INCH) * dpi)}px`,
  }
}

/**
 * Scroll offset that brings a page card to the top of the stage viewport.
 * Viewport-relative inputs, scroll-space output — same convention as
 * `centeredScrollPosition`.
 */
export function pageTopScrollPosition(
  scrollTop: number,
  viewportTop: number,
  cardTop: number,
): number {
  return Math.max(0, scrollTop + cardTop - viewportTop)
}

/**
 * Whether a focus change asks the preview to scroll.
 *
 * Clearing the focus (the Parse view's "Show all", #338) leaves an empty
 * highlight set: there is nothing to centre on, and the focus fallback would
 * jump to the page top — away from where the reader is. So a cleared focus is
 * not a scroll request at all; a focus whose element cannot be placed still is.
 */
export function isFocusScrollRequest(highlightedRefs: ReadonlySet<string> | undefined): boolean {
  return (highlightedRefs?.size ?? 0) > 0
}

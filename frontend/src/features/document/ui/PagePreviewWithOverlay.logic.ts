export const DEFAULT_PAGE_INPUT_SIZE = 4

export function clampPageInput(raw: string, totalPages: number): number | null {
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed)) return null
  return Math.min(totalPages, Math.max(1, parsed))
}

export function computePageInputWidthCh(totalPages: number, min = DEFAULT_PAGE_INPUT_SIZE): number {
  return Math.max(min, String(totalPages).length)
}

/** Where the preview stands: the page shown, the mode, the page targeted, whether the shown page has settled. */
export interface PreviewViewState {
  currentPage: number
  viewMode: 'page' | 'scroll'
  focusedPage: number | null
  currentPageSettled: boolean
}

/** Bound image requests independently of page dimensions and viewport width. */
export function isPageInRenderWindow(
  pageNumber: number,
  view: PreviewViewState,
  alreadyRequested: boolean,
): boolean {
  const { currentPage, viewMode, focusedPage, currentPageSettled } = view
  return (
    viewMode === 'page' ||
    pageNumber === focusedPage ||
    pageNumber === currentPage ||
    (pageNumber >= currentPage - 1 &&
      pageNumber <= currentPage + 2 &&
      (alreadyRequested || (currentPageSettled && pageNumber > currentPage)))
  )
}

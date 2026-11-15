export const DEFAULT_PAGE_INPUT_SIZE = 4

export function clampPageInput(raw: string, totalPages: number): number | null {
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed)) return null
  return Math.min(totalPages, Math.max(1, parsed))
}

export function pageInputWidthCh(totalPages: number, min = DEFAULT_PAGE_INPUT_SIZE): number {
  return Math.max(min, String(totalPages).length)
}

/** Bound image requests independently of page dimensions and viewport width. */
export function pageInRenderWindow(
  pageNumber: number,
  currentPage: number,
  viewMode: 'page' | 'scroll',
  focusedPage: number | null,
  currentPageSettled: boolean,
  alreadyRequested: boolean,
): boolean {
  return (
    viewMode === 'page' ||
    pageNumber === focusedPage ||
    pageNumber === currentPage ||
    (pageNumber >= currentPage - 1 &&
      pageNumber <= currentPage + 2 &&
      (alreadyRequested || (currentPageSettled && pageNumber > currentPage)))
  )
}

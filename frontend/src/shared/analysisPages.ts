import type { Analysis, Page } from './types'

/** Pages of an analysis, from its `pagesJson`; empty when absent or unreadable. */
export function parseAnalysisPages(
  analysis: Pick<Analysis, 'pagesJson'> | null | undefined,
): Page[] {
  if (!analysis?.pagesJson) return []
  try {
    return JSON.parse(analysis.pagesJson) as Page[]
  } catch {
    return []
  }
}

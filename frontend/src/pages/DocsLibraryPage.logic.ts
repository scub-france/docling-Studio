/**
 * Pure helpers for the docs library: the selection (#354) and the analysis
 * count shown before a deletion.
 *
 * Only listed documents stay selected, so the count and **Analyze** always
 * match the rows the user sees. Extracted from `DocsLibraryPage.vue` to be
 * unit-tested without a DOM; every selection helper returns a new set.
 */
import type { AnalysisSummary } from '../shared/types'

/**
 * The most rows `GET /api/analyses/summaries` returns, newest first: the
 * default page of `find_all_summaries` in
 * `document-parser/persistence/analysis_repo.py`. A list this long may leave
 * out older analyses.
 */
export const SUMMARIES_PAGE = 200

/** Where `countDocumentAnalyses` reads the analyses. */
export interface AnalysisLookup {
  /** Every analysis without its content. */
  summaries: () => Promise<readonly Pick<AnalysisSummary, 'documentId'>[]>
  /** The document's analyses, with their content. */
  ofDocument: (documentId: string) => Promise<readonly unknown[]>
}

/**
 * How many analyses deleting `documentId` also deletes, for the warning.
 *
 * Counted from the summaries, which carry no markdown, HTML, pages or chunks.
 * When the summaries may be cut short, the document's own list gives the
 * exact count instead: the warning never says fewer than the deletion takes.
 */
export async function countDocumentAnalyses(
  documentId: string,
  lookup: AnalysisLookup,
): Promise<number> {
  const summaries = await lookup.summaries()
  if (summaries.length < SUMMARIES_PAGE) {
    return summaries.filter((s) => s.documentId === documentId).length
  }
  return (await lookup.ofDocument(documentId)).length
}

export type SelectionState = 'none' | 'some' | 'all'

/** How much of the listed documents the selection covers. */
export function selectionState(
  selected: ReadonlySet<string>,
  listed: readonly string[],
): SelectionState {
  const count = listed.filter((id) => selected.has(id)).length
  if (count === 0) return 'none'
  return count === listed.length ? 'all' : 'some'
}

/** Select every listed document, or none once they all are. */
export function toggleListed(
  selected: ReadonlySet<string>,
  listed: readonly string[],
): Set<string> {
  return selectionState(selected, listed) === 'all' ? new Set() : new Set(listed)
}

export function toggleOne(selected: ReadonlySet<string>, id: string): Set<string> {
  const next = new Set(selected)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}

/** Drop what the filter or a deletion took off the list. */
export function keepListed(selected: ReadonlySet<string>, listed: readonly string[]): Set<string> {
  return new Set(listed.filter((id) => selected.has(id)))
}

import type { AnalysisEditCommand } from './types'

/**
 * Unsaved editor commands kept in `sessionStorage`, so a reload can offer to
 * restore them. A draft is only valid against the saved stream it was built
 * on, hence the sequence stored next to the commands.
 */
export interface PendingDraft {
  expectedAppliedThroughSequence: number
  commands: AnalysisEditCommand[]
}

/** One draft per document and base analysis; null until both are known. */
export function buildPendingDraftKey(
  documentId: string | null,
  baseAnalysisId: string | null,
): string | null {
  if (!documentId || !baseAnalysisId) return null
  return `analysis-editor-pending:${documentId}:${baseAnalysisId}`
}

/** Store the draft, or remove it when there is nothing pending. */
export function writePendingDraft(key: string, draft: PendingDraft): void {
  try {
    if (!draft.commands.length) {
      window.sessionStorage.removeItem(key)
      return
    }
    window.sessionStorage.setItem(key, JSON.stringify(draft))
  } catch {
    // Browser storage can be unavailable in private or restricted contexts.
  }
}

/**
 * The stored commands when the draft still matches the saved sequence. A
 * stale draft is removed, and malformed or unavailable storage reads as none.
 */
export function readPendingDraft(
  key: string,
  appliedThroughSequence: number | undefined,
): AnalysisEditCommand[] | null {
  try {
    const value = window.sessionStorage.getItem(key)
    if (!value) return null
    const draft = JSON.parse(value) as {
      expectedAppliedThroughSequence?: unknown
      commands?: unknown
    }
    if (
      draft.expectedAppliedThroughSequence === appliedThroughSequence &&
      Array.isArray(draft.commands) &&
      draft.commands.length
    ) {
      return draft.commands as AnalysisEditCommand[]
    }
    window.sessionStorage.removeItem(key)
  } catch {
    // Ignore malformed and unavailable browser storage.
  }
  return null
}

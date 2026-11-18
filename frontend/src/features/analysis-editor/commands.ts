import type { AnalysisEditCommand, EditorElement } from './types'

type FoldableCommand = Extract<AnalysisEditCommand, { type: 'replaceText' | 'setHeadingLevel' }>

function isFoldable(command: AnalysisEditCommand): command is FoldableCommand {
  return command.type === 'replaceText' || command.type === 'setHeadingLevel'
}

/** Element ids a structural command reads or changes. */
function listStructuralElementIds(command: AnalysisEditCommand): string[] {
  switch (command.type) {
    case 'mergeText':
    case 'deleteElements':
      return command.elementIds
    case 'moveElement':
    case 'deleteElement':
      return [command.elementId]
    default:
      return []
  }
}

/**
 * Fold a text or heading edit into the previous edit of the same kind on the
 * same element, so the queue stays short while the user types.
 *
 * The search stops at a structural command involving that element (#392): an
 * edit made after a merge must stay after it, or replaying the queue applies
 * the merge on top of text that already contains the merged continuation.
 */
export function coalesceCommands(commands: AnalysisEditCommand[]): AnalysisEditCommand[] {
  const result: AnalysisEditCommand[] = []
  for (const command of commands) {
    const index = isFoldable(command) ? findFoldTarget(result, command) : -1
    if (index >= 0) result[index] = command
    else result.push(command)
  }
  return result
}

function findFoldTarget(queue: AnalysisEditCommand[], command: FoldableCommand): number {
  for (let index = queue.length - 1; index >= 0; index--) {
    const candidate = queue[index]
    if (isFoldable(candidate)) {
      if (candidate.type === command.type && candidate.elementId === command.elementId) return index
    } else if (listStructuralElementIds(candidate).includes(command.elementId)) {
      return -1
    }
  }
  return -1
}

/**
 * The ids in reading order (#392): a merge keeps the document's text order,
 * whatever order the user clicked in. Ids missing from `readingOrder` keep
 * their relative order after the others.
 */
export function inReadingOrder(ids: string[], readingOrder: string[]): string[] {
  const position = new Map(readingOrder.map((id, index) => [id, index]))
  return ids
    .map((id, clickIndex) => ({ id, clickIndex, rank: position.get(id) ?? Infinity }))
    .sort((a, b) => a.rank - b.rank || a.clickIndex - b.clickIndex)
    .map(({ id }) => id)
}

/** i18n keys (`shared/i18n.ts`) explaining why a merge selection is refused. */
export type MergeValidationKey =
  | 'analysisEditor.merge.needTwo'
  | 'analysisEditor.merge.unavailable'
  | 'analysisEditor.merge.textOnly'
  | 'analysisEditor.merge.sameType'

export function canMerge(elements: EditorElement[], ids: string[]): boolean {
  return validateMerge(elements, ids) === null
}

/** The i18n key of the first rule the selection breaks, or null when it can be merged. */
export function validateMerge(elements: EditorElement[], ids: string[]): MergeValidationKey | null {
  if (ids.length < 2) return 'analysisEditor.merge.needTwo'
  const selected = ids
    .map((id) => elements.find((element) => element.id === id))
    .filter((element): element is EditorElement => !!element)
  if (selected.length !== ids.length) return 'analysisEditor.merge.unavailable'
  if (selected.some((element) => element.type !== 'text' && element.type !== 'paragraph')) {
    return 'analysisEditor.merge.textOnly'
  }
  // The backend merges one Docling label at a time (#395): text with
  // paragraph would enable the button and then fail with a 400.
  if (new Set(selected.map((element) => element.type)).size > 1) {
    return 'analysisEditor.merge.sameType'
  }
  return null
}

import type { AnalysisEditCommand, EditorElement } from './types'

type FoldableCommand = Extract<AnalysisEditCommand, { type: 'replaceText' | 'setHeadingLevel' }>

function isFoldable(command: AnalysisEditCommand): command is FoldableCommand {
  return command.type === 'replaceText' || command.type === 'setHeadingLevel'
}

/** Element ids a structural command reads or changes. */
function structuralElementIds(command: AnalysisEditCommand): string[] {
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
    const index = isFoldable(command) ? foldTargetIndex(result, command) : -1
    if (index >= 0) result[index] = command
    else result.push(command)
  }
  return result
}

function foldTargetIndex(queue: AnalysisEditCommand[], command: FoldableCommand): number {
  for (let index = queue.length - 1; index >= 0; index--) {
    const candidate = queue[index]
    if (isFoldable(candidate)) {
      if (candidate.type === command.type && candidate.elementId === command.elementId)
        return index
    } else if (structuralElementIds(candidate).includes(command.elementId)) {
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

export function canMerge(elements: EditorElement[], ids: string[]): boolean {
  return mergeValidationMessage(elements, ids) === null
}

export function mergeValidationMessage(elements: EditorElement[], ids: string[]): string | null {
  if (ids.length < 2) return 'Select at least two elements to merge.'
  const selected = ids
    .map((id) => elements.find((element) => element.id === id))
    .filter((element): element is EditorElement => !!element)
  if (selected.length !== ids.length)
    return 'One or more selected elements are no longer available.'
  if (selected.some((element) => element.type !== 'text' && element.type !== 'paragraph')) {
    return 'Only text and paragraph elements can be merged.'
  }
  return null
}

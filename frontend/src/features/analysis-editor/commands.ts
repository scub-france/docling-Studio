import type { AnalysisEditCommand, EditorElement } from './types'

export function coalesceCommands(commands: AnalysisEditCommand[]): AnalysisEditCommand[] {
  const result: AnalysisEditCommand[] = []
  for (const command of commands) {
    if (command.type === 'replaceText' || command.type === 'setHeadingLevel') {
      const index = result.findIndex(
        (candidate) => candidate.type === command.type && candidate.elementId === command.elementId,
      )
      if (index >= 0) result[index] = command
      else result.push(command)
    } else {
      result.push(command)
    }
  }
  return result
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

import type { AnalysisEditCommand, EditorElement } from './types'

export function coalesceCommands(commands: AnalysisEditCommand[]): AnalysisEditCommand[] {
  const result: AnalysisEditCommand[] = []
  for (const command of commands) {
    if (command.type === 'replaceText' || command.type === 'setHeadingLevel') {
      const index = result.findIndex(
        (candidate) =>
          candidate.type === command.type && candidate.elementId === command.elementId,
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
  if (ids.length < 2) return false
  const selected = ids
    .map((id) => elements.find((element) => element.id === id))
    .filter((element): element is EditorElement => !!element)
  if (selected.length !== ids.length || selected.some((element) => element.type !== 'text')) return false
  if (selected.some((element) => !element.parentId)) return false
  if (new Set(selected.map((element) => element.parentId)).size !== 1) return false
  const order = elements.map((element) => element.id)
  const positions = selected.map((element) => order.indexOf(element.id)).sort((a, b) => a - b)
  return positions.every((position, index) => index === 0 || position === positions[index - 1] + 1)
}

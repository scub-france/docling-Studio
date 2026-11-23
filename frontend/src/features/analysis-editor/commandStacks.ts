import { coalesceCommands } from './commands'
import type { AnalysisEditCommand, AnalysisEditHistoryEntry } from './types'

/**
 * Undo/redo bookkeeping of the editor, as pure functions.
 *
 * Unsaved commands live in two stacks: `pending` (applied to the preview, in
 * order) and `redo` (undone, next one first). Once nothing is pending, undo and
 * redo act on the saved history instead, by toggling a saved command.
 */
export interface CommandStacks {
  pending: AnalysisEditCommand[]
  redo: AnalysisEditCommand[]
}

/** A new command is coalesced into the pending stack and drops the redo stack. */
export function queueCommand(
  pending: AnalysisEditCommand[],
  command: AnalysisEditCommand,
): CommandStacks {
  return { pending: coalesceCommands([...pending, command]), redo: [] }
}

/** Move the last pending command onto the redo stack; null when nothing is pending. */
export function undoPending({ pending, redo }: CommandStacks): CommandStacks | null {
  const command = pending.at(-1)
  if (!command) return null
  return { pending: pending.slice(0, -1), redo: [command, ...redo] }
}

/** Re-apply the next undone command; null when there is nothing to redo. */
export function redoPending({ pending, redo }: CommandStacks): CommandStacks | null {
  const command = redo[0]
  if (!command) return null
  return { pending: coalesceCommands([...pending, command]), redo: redo.slice(1) }
}

/** Latest saved command still active: the one a saved undo deactivates. */
export function findSavedUndoTarget(
  history: AnalysisEditHistoryEntry[],
): AnalysisEditHistoryEntry | undefined {
  return [...history].reverse().find((entry) => entry.active === true)
}

/** Latest saved command deactivated: the one a saved redo reactivates. */
export function findSavedRedoTarget(
  history: AnalysisEditHistoryEntry[],
): AnalysisEditHistoryEntry | undefined {
  return [...history].reverse().find((entry) => entry.active === false)
}

import { describe, expect, it } from 'vitest'
import {
  findSavedRedoTarget,
  findSavedUndoTarget,
  queueCommand,
  redoPending,
  undoPending,
} from './commandStacks'
import type { AnalysisEditCommand, AnalysisEditHistoryEntry } from './types'

const del = (elementId: string): AnalysisEditCommand => ({ type: 'deleteElement', elementId })
const text = (value: string): AnalysisEditCommand => ({
  type: 'replaceText',
  elementId: 'a',
  text: value,
})

const entry = (sequence: number, active: boolean | null): AnalysisEditHistoryEntry => ({
  id: `edit-${sequence}`,
  sequence,
  commandVersion: 1,
  commandType: 'deleteElement',
  payload: {},
  commandHash: `hash-${sequence}`,
  createdAt: '2026-01-01T00:00:00Z',
  active,
})

describe('command stacks', () => {
  it('queues a command coalesced into pending and drops the redo stack', () => {
    expect(queueCommand([text('one')], text('two'))).toEqual({
      pending: [text('two')],
      redo: [],
    })
  })

  it('undoes the last pending command onto the front of the redo stack', () => {
    expect(undoPending({ pending: [del('a'), del('b')], redo: [del('c')] })).toEqual({
      pending: [del('a')],
      redo: [del('b'), del('c')],
    })
    expect(undoPending({ pending: [], redo: [del('c')] })).toBeNull()
  })

  it('redoes the next undone command, coalesced into pending', () => {
    expect(redoPending({ pending: [text('one')], redo: [text('two'), del('c')] })).toEqual({
      pending: [text('two')],
      redo: [del('c')],
    })
    expect(redoPending({ pending: [del('a')], redo: [] })).toBeNull()
  })

  it('targets the latest active saved command for undo and the latest inactive for redo', () => {
    const history = [entry(1, true), entry(2, false), entry(3, true), entry(4, false)]
    expect(findSavedUndoTarget(history)?.sequence).toBe(3)
    expect(findSavedRedoTarget(history)?.sequence).toBe(4)
    expect(findSavedUndoTarget([])).toBeUndefined()
  })
})

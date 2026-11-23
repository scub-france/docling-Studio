import type { Analysis } from '../../shared/types'

export interface EditorProvenance {
  page: number
  bbox: [number, number, number, number]
}

export type AnalysisEditCommand =
  | { type: 'replaceText'; elementId: string; text: string }
  | { type: 'mergeText'; elementIds: string[]; separator: string }
  | { type: 'setHeadingLevel'; elementId: string; level: number }
  | {
      type: 'moveElement'
      elementId: string
      targetElementId: string
      placement: 'before' | 'after' | 'inside'
    }
  | { type: 'deleteElement'; elementId: string }
  | { type: 'deleteElements'; elementIds: string[] }

export interface EditorElement {
  id: string
  selfRef: string
  parentId: string | null
  type: string
  text: string | null
  headingLevel: number | null
  children: string[]
  provenance: EditorProvenance[]
  editable: boolean
  supportedOperations: string[]
  nonEditableReason: string | null
}

export interface EditorTreeNode {
  elementId: string
  type: string
  label: string
  children: EditorTreeNode[]
}

export interface AnalysisEditorModel {
  baseAnalysisId: string
  elements: EditorElement[]
}

export interface AnalysisEditorResponse {
  model: AnalysisEditorModel
  tree: EditorTreeNode[]
  readingOrder: string[]
  result: Analysis
  appliedThroughSequence: number
  chunksStale: boolean
}

export interface AnalysisEditSaveResponse {
  result: Analysis
  baseAnalysisId: string
  appliedThroughSequence: number
  chunksStale: boolean
}

export interface AnalysisEditHistoryEntry {
  id: string
  sequence: number
  commandVersion: number
  commandType: string
  payload: Record<string, unknown>
  commandHash: string
  createdAt: string
  active: boolean | null
}

export interface AnalysisEditRequest {
  commands: AnalysisEditCommand[]
  expectedAppliedThroughSequence: number
}

/** Revert (`active: false`) or reapply a saved edit, checked against the stream head. */
export interface AnalysisEditActiveChange {
  sequence: number
  active: boolean
  expectedAppliedThroughSequence: number
}

export { parseAnalysisPages } from '../../shared/analysisPages'

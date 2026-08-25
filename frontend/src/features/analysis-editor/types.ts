import type { Analysis, Page } from '../../shared/types'

export interface EditorProvenance {
  page: number
  bbox: [number, number, number, number]
}

export type AnalysisEditCommand =
  | { type: 'replaceText'; elementId: string; text: string }
  | { type: 'mergeText'; elementIds: string[]; separator: string }
  | { type: 'setHeadingLevel'; elementId: string; level: number }
  | { type: 'moveElement'; elementId: string; beforeElementId: string | null }
  | { type: 'deleteElement'; elementId: string }

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
  warnings: string[]
  referenceChanges: Record<string, string>
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
}

export interface AnalysisEditRequest {
  commands: AnalysisEditCommand[]
  expectedAppliedThroughSequence: number
}

export function pagesFromAnalysis(analysis: Analysis | null): Page[] {
  if (!analysis?.pagesJson) return []
  try {
    return JSON.parse(analysis.pagesJson) as Page[]
  } catch {
    return []
  }
}

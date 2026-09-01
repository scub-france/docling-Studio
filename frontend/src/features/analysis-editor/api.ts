import { apiFetch } from '../../shared/api/http'
import type {
  AnalysisEditRequest,
  AnalysisEditSaveResponse,
  AnalysisEditorResponse,
  AnalysisEditHistoryEntry,
} from './types'

export function fetchAnalysisEditor(
  documentId: string,
  signal?: AbortSignal,
  analysisId?: string,
): Promise<AnalysisEditorResponse> {
  const query = analysisId ? `?analysisId=${encodeURIComponent(analysisId)}` : ''
  return apiFetch<AnalysisEditorResponse>(
    `/api/documents/${documentId}/analysis-editor${query}`,
    { signal },
  )
}

export function previewAnalysisEdits(
  documentId: string,
  body: AnalysisEditRequest,
  signal?: AbortSignal,
  analysisId?: string,
): Promise<AnalysisEditorResponse> {
  const query = analysisId ? `?analysisId=${encodeURIComponent(analysisId)}` : ''
  return apiFetch<AnalysisEditorResponse>(
    `/api/documents/${documentId}/analysis-edits/preview${query}`,
    { method: 'POST', body: JSON.stringify(body), signal },
  )
}

export function saveAnalysisEdits(
  documentId: string,
  body: AnalysisEditRequest,
  analysisId?: string,
): Promise<AnalysisEditSaveResponse> {
  const query = analysisId ? `?analysisId=${encodeURIComponent(analysisId)}` : ''
  return apiFetch<AnalysisEditSaveResponse>(`/api/documents/${documentId}/analysis-edits${query}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function fetchAnalysisEditHistory(
  documentId: string,
  analysisId?: string,
): Promise<AnalysisEditHistoryEntry[]> {
  const query = analysisId ? `?analysisId=${encodeURIComponent(analysisId)}` : ''
  return apiFetch<AnalysisEditHistoryEntry[]>(
    `/api/documents/${documentId}/analysis-edits/history${query}`,
  )
}

export function rebuildAnalysisEdits(
  documentId: string,
  analysisId?: string,
): Promise<AnalysisEditorResponse> {
  const query = analysisId ? `?analysisId=${encodeURIComponent(analysisId)}` : ''
  return apiFetch<AnalysisEditorResponse>(`/api/documents/${documentId}/analysis-edits/rebuild${query}`, {
    method: 'POST',
  })
}

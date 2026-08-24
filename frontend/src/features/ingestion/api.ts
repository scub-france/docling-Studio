import { apiFetch } from '@/shared/api/http'

export interface IngestionResult {
  docId: string
  chunksIndexed: number
  embeddingDimension: number
}

export interface IngestionStatus {
  available: boolean
  opensearchConnected: boolean
}

export function ingestAnalysis(jobId: string): Promise<IngestionResult> {
  return apiFetch<IngestionResult>(`/api/ingestion/${jobId}`, {
    method: 'POST',
  })
}

export function deleteIngested(docId: string): Promise<unknown> {
  return apiFetch(`/api/ingestion/${docId}`, { method: 'DELETE' })
}

export function fetchIngestionStatus(): Promise<IngestionStatus> {
  return apiFetch<IngestionStatus>('/api/ingestion/status')
}

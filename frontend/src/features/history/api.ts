import type { AnalysisSummary } from '../../shared/types'
import { apiFetch } from '@/shared/api/http'

export function fetchHistory(): Promise<AnalysisSummary[]> {
  return apiFetch<AnalysisSummary[]>('/api/analyses/summaries')
}

export function deleteHistoryEntry(id: string): Promise<unknown> {
  return apiFetch(`/api/analyses/${id}`, { method: 'DELETE' })
}

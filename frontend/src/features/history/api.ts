import type { AnalysisSummary } from '../../shared/types'
import { apiFetch } from '@/shared/api/http'

/**
 * Every analysis without its content (#354): the history shows file, status
 * and dates, never the markdown, HTML, pages or chunks the full list carries.
 */
export function fetchHistory(): Promise<AnalysisSummary[]> {
  return apiFetch<AnalysisSummary[]>('/api/analyses/summaries')
}

export function deleteHistoryEntry(id: string): Promise<unknown> {
  return apiFetch(`/api/analyses/${id}`, { method: 'DELETE' })
}

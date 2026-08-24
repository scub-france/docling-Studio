import type { Analysis } from '../../shared/types'
import { apiFetch } from '@/shared/api/http'

export function fetchHistory(): Promise<Analysis[]> {
  return apiFetch<Analysis[]>('/api/analyses')
}

export function deleteHistoryEntry(id: string): Promise<unknown> {
  return apiFetch(`/api/analyses/${id}`, { method: 'DELETE' })
}

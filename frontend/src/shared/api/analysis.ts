import type { Analysis } from '../types'
import { apiFetch } from './http'

/** Import a completed analysis represented by a serialized DoclingDocument. */
export function importAnalysis(
  documentId: string,
  document: Record<string, unknown>,
): Promise<Analysis> {
  return apiFetch<Analysis>('/api/analyses/import', {
    method: 'POST',
    body: JSON.stringify({ documentId, document }),
  })
}

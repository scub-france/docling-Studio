import { apiFetch } from '../../shared/api/http'
import type { DocumentLifecycleState } from '../../shared/types'

export interface StoreInfo {
  name: string
  type: string
  connected: boolean
  documentCount: number
  chunkCount: number
  errorMessage?: string
}

export interface StoreDocEntry {
  docId: string
  filename: string
  state: DocumentLifecycleState
  chunkCount: number
  pushedAt: string
}

export interface QueryResult {
  chunkId: string
  docId: string
  filename: string
  text: string
  score: number
  pageRange?: [number, number]
}

export function fetchStores(): Promise<StoreInfo[]> {
  return apiFetch<StoreInfo[]>('/api/stores')
}

export function fetchStoreDocuments(store: string): Promise<StoreDocEntry[]> {
  return apiFetch<StoreDocEntry[]>(`/api/stores/${encodeURIComponent(store)}/documents`)
}

export function removeDocumentFromStore(store: string, docId: string): Promise<void> {
  return apiFetch<void>(
    `/api/stores/${encodeURIComponent(store)}/documents/${encodeURIComponent(docId)}`,
    { method: 'DELETE' },
  )
}

export function queryStore(store: string, query: string, topK = 5): Promise<QueryResult[]> {
  return apiFetch<QueryResult[]>(`/api/stores/${encodeURIComponent(store)}/query`, {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  })
}

import { apiFetch } from '../../shared/api/http'
import type { DocumentLifecycleState } from '../../shared/types'

export interface StoreInfo {
  name: string
  slug: string
  type: string
  embedder: string
  isDefault: boolean
  connected: boolean
  documentCount: number
  chunkCount: number
  errorMessage?: string
}

export interface StoreDetail {
  id: string
  name: string
  slug: string
  kind: string
  embedder: string
  isDefault: boolean
  config: Record<string, unknown>
  // Connection identity (#279). The password itself never crosses
  // the wire on a GET — only the boolean indicator does. The form
  // renders "•••• (unchanged — type to replace)" when this is true.
  connectionUri?: string | null
  connectionUsername?: string | null
  hasConnectionPassword?: boolean
  createdAt: string
}

export interface StoreCreatePayload {
  name: string
  slug: string
  kind: string
  embedder: string
  config: Record<string, unknown>
  isDefault?: boolean
  // #279 — write-only on create. Empty string == "no password set".
  connectionUri?: string | null
  connectionUsername?: string | null
  connectionPassword?: string | null
}

export interface StoreUpdatePayload {
  name?: string
  slug?: string
  kind?: string
  embedder?: string
  config?: Record<string, unknown>
  isDefault?: boolean
  // #279 — write-only on update. Tri-state on password:
  //   - undefined / missing → leave the existing seal alone
  //   - ""                  → clear the seal
  //   - "value"             → seal and persist
  connectionUri?: string | null
  connectionUsername?: string | null
  connectionPassword?: string | null
}

export interface StoreTestConnectionResult {
  ok: boolean
  errorMessage?: string | null
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

export function fetchStore(slug: string): Promise<StoreDetail> {
  return apiFetch<StoreDetail>(`/api/stores/${encodeURIComponent(slug)}`)
}

export function createStore(payload: StoreCreatePayload): Promise<StoreDetail> {
  return apiFetch<StoreDetail>('/api/stores', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateStore(slug: string, payload: StoreUpdatePayload): Promise<StoreDetail> {
  return apiFetch<StoreDetail>(`/api/stores/${encodeURIComponent(slug)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteStore(slug: string): Promise<void> {
  return apiFetch<void>(`/api/stores/${encodeURIComponent(slug)}`, { method: 'DELETE' })
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

export function testStoreConnection(slug: string): Promise<StoreTestConnectionResult> {
  return apiFetch<StoreTestConnectionResult>(
    `/api/stores/${encodeURIComponent(slug)}/test-connection`,
    { method: 'POST' },
  )
}

export function queryStore(store: string, query: string, topK = 5): Promise<QueryResult[]> {
  return apiFetch<QueryResult[]>(`/api/stores/${encodeURIComponent(store)}/query`, {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  })
}

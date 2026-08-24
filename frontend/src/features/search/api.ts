import { apiFetch } from '@/shared/api/http'

export interface SearchResultItem {
  docId: string
  filename: string
  content: string
  chunkIndex: number
  pageNumber: number
  score: number
  headings: string[]
}

export interface SearchResponse {
  results: SearchResultItem[]
  total: number
  query: string
}

export function searchChunks(
  query: string,
  options: { docId?: string; k?: number } = {},
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query })
  if (options.docId) params.set('doc_id', options.docId)
  if (options.k) params.set('k', String(options.k))
  return apiFetch<SearchResponse>(`/api/ingestion/search?${params}`)
}

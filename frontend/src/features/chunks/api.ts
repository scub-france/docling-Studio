import type { DocChunk, ChunkDiff, PushSummary } from '../../shared/types'
import { apiFetch } from '../../shared/api/http'

export function fetchChunks(docId: string): Promise<DocChunk[]> {
  return apiFetch<DocChunk[]>(`/api/documents/${docId}/chunks`)
}

export function updateChunk(
  docId: string,
  chunkId: string,
  patch: { text?: string; title?: string },
): Promise<DocChunk> {
  return apiFetch<DocChunk>(`/api/documents/${docId}/chunks/${chunkId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}

export function mergeChunks(docId: string, ids: string[]): Promise<DocChunk[]> {
  return apiFetch<DocChunk[]>(`/api/documents/${docId}/chunks/merge`, {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export function splitChunk(
  docId: string,
  chunkId: string,
  cursorOffset: number,
): Promise<DocChunk[]> {
  return apiFetch<DocChunk[]>(`/api/documents/${docId}/chunks/${chunkId}/split`, {
    method: 'POST',
    body: JSON.stringify({ cursorOffset }),
  })
}

export function dropChunk(docId: string, chunkId: string): Promise<void> {
  return apiFetch(`/api/documents/${docId}/chunks/${chunkId}`, { method: 'DELETE' })
}

export function addChunk(docId: string, text: string, afterId?: string): Promise<DocChunk> {
  return apiFetch<DocChunk>(`/api/documents/${docId}/chunks`, {
    method: 'POST',
    body: JSON.stringify({ text, afterId }),
  })
}

export function fetchChunkDiff(docId: string, store: string): Promise<ChunkDiff[]> {
  return apiFetch<ChunkDiff[]>(`/api/documents/${docId}/diff?store=${encodeURIComponent(store)}`)
}

export function pushChunksToStore(
  docId: string,
  store: string,
): Promise<{ jobId: string; summary: PushSummary }> {
  return apiFetch<{ jobId: string; summary: PushSummary }>(`/api/documents/${docId}/chunks/push`, {
    method: 'POST',
    body: JSON.stringify({ store }),
  })
}

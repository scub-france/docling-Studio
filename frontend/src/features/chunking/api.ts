import type { Chunk, ChunkingOptions } from '../../shared/types'
import { apiFetch } from '@/shared/api/http'

export function rechunkAnalysis(jobId: string, chunkingOptions: ChunkingOptions): Promise<Chunk[]> {
  return apiFetch<Chunk[]>(`/api/analyses/${jobId}/rechunk`, {
    method: 'POST',
    body: JSON.stringify({ chunkingOptions }),
  })
}

export function updateChunkText(jobId: string, chunkIndex: number, text: string): Promise<Chunk[]> {
  return apiFetch<Chunk[]>(`/api/analyses/${jobId}/chunks/${chunkIndex}`, {
    method: 'PATCH',
    body: JSON.stringify({ text }),
  })
}

export function deleteChunk(jobId: string, chunkIndex: number): Promise<Chunk[]> {
  return apiFetch<Chunk[]>(`/api/analyses/${jobId}/chunks/${chunkIndex}`, {
    method: 'DELETE',
  })
}

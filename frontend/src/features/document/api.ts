import type { DocChunk, Document, DocTreeNode, DocumentVersion } from '../../shared/types'
import { apiFetch } from '../../shared/api/http'

export function fetchDocuments(): Promise<Document[]> {
  return apiFetch<Document[]>('/api/documents')
}

export function fetchDocument(id: string): Promise<Document> {
  return apiFetch<Document>(`/api/documents/${id}`)
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<Document>('/api/documents/upload', {
    method: 'POST',
    body: formData,
    skipContentType: true,
  })
}

export function deleteDocument(id: string): Promise<unknown> {
  return apiFetch(`/api/documents/${id}`, { method: 'DELETE' })
}

export function getPreviewUrl(id: string, page = 1, dpi = 150): string {
  return `/api/documents/${id}/preview?page=${page}&dpi=${dpi}`
}

/**
 * Camel-case chunking options for the rechunk endpoint (#268). The
 * backend `ChunkingOptionsRequest` accepts both snake_case and camelCase
 * via `AliasChoices`; the rest of the API contract is camelCase, so the
 * new Linked/Chunk view sticks to camelCase too.
 */
export interface RechunkOptions {
  chunkerType?: 'hybrid' | 'hierarchical'
  maxTokens?: number
  mergePeers?: boolean
  repeatTableHeader?: boolean
}

/** Rechunk the canonical chunkset. Backend runs synchronously and returns
 * the new chunks — there is no async job to poll. */
export function rechunkDocument(id: string, options?: RechunkOptions): Promise<DocChunk[]> {
  const body = options ? { chunkingOptions: options } : {}
  return apiFetch<DocChunk[]>(`/api/documents/${id}/rechunk`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function fetchDocumentTree(id: string): Promise<DocTreeNode[]> {
  return apiFetch<DocTreeNode[]>(`/api/documents/${id}/tree`)
}

/** Workspace History timeline (#267) — frozen pairs newest-first. */
export function fetchDocumentVersions(id: string): Promise<DocumentVersion[]> {
  return apiFetch<DocumentVersion[]>(`/api/documents/${id}/versions`)
}

/** Restore a version — overwrites the live chunkset with the snapshot. */
export function restoreDocumentVersion(docId: string, versionId: string): Promise<DocumentVersion> {
  return apiFetch<DocumentVersion>(`/api/documents/${docId}/versions/${versionId}/restore`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

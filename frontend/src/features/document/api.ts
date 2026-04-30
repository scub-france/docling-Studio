import type { Document, DocTreeNode } from '../../shared/types'
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

export function rechunkDocument(id: string): Promise<{ jobId: string }> {
  return apiFetch<{ jobId: string }>(`/api/documents/${id}/rechunk`, { method: 'POST' })
}

export function pushDocumentToStore(id: string, store: string): Promise<{ jobId: string }> {
  return apiFetch<{ jobId: string }>(`/api/documents/${id}/push`, {
    method: 'POST',
    body: JSON.stringify({ store }),
  })
}

export function fetchDocumentTree(id: string): Promise<DocTreeNode[]> {
  return apiFetch<DocTreeNode[]>(`/api/documents/${id}/tree`)
}

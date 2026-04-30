import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchDocuments,
  fetchDocument,
  uploadDocument,
  deleteDocument,
  getPreviewUrl,
  rechunkDocument,
  pushDocumentToStore,
  fetchDocumentTree,
} from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('document API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchDocuments calls GET /api/documents', async () => {
    const docs = [{ id: '1', filename: 'a.pdf' }]
    apiFetch.mockResolvedValue(docs)

    const result = await fetchDocuments()

    expect(apiFetch).toHaveBeenCalledWith('/api/documents')
    expect(result).toEqual(docs)
  })

  it('fetchDocument calls GET /api/documents/:id', async () => {
    const doc = { id: '42', filename: 'test.pdf' }
    apiFetch.mockResolvedValue(doc)

    const result = await fetchDocument('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/42')
    expect(result).toEqual(doc)
  })

  it('uploadDocument sends file via FormData with skipContentType', async () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    const response = { id: '1', filename: 'test.pdf' }
    apiFetch.mockResolvedValue(response)

    const result = await uploadDocument(file)

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/upload', {
      method: 'POST',
      body: expect.any(FormData),
      skipContentType: true,
    })
    expect(result).toEqual(response)
  })

  it('deleteDocument calls DELETE /api/documents/:id', async () => {
    apiFetch.mockResolvedValue(null)

    await deleteDocument('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/42', { method: 'DELETE' })
  })

  it('getPreviewUrl builds correct URL with defaults', () => {
    expect(getPreviewUrl('abc')).toBe('/api/documents/abc/preview?page=1&dpi=150')
  })

  it('getPreviewUrl accepts custom page and dpi', () => {
    expect(getPreviewUrl('abc', 3, 300)).toBe('/api/documents/abc/preview?page=3&dpi=300')
  })

  it('rechunkDocument calls POST /api/documents/:id/rechunk', async () => {
    apiFetch.mockResolvedValue({ jobId: 'job-1' })

    const result = await rechunkDocument('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/42/rechunk', { method: 'POST' })
    expect(result).toEqual({ jobId: 'job-1' })
  })

  it('pushDocumentToStore calls POST /api/documents/:id/push with store', async () => {
    apiFetch.mockResolvedValue({ jobId: 'job-2' })

    const result = await pushDocumentToStore('42', 'my-store')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/42/push', {
      method: 'POST',
      body: JSON.stringify({ store: 'my-store' }),
    })
    expect(result).toEqual({ jobId: 'job-2' })
  })

  it('fetchDocumentTree calls GET /api/documents/:id/tree', async () => {
    const tree = [{ ref: '#/body', type: 'body', label: 'Body', children: [] }]
    apiFetch.mockResolvedValue(tree)

    const result = await fetchDocumentTree('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/42/tree')
    expect(result).toEqual(tree)
  })
})

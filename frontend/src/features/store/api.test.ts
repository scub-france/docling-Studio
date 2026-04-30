import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchStores, fetchStoreDocuments, removeDocumentFromStore, queryStore } from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('store API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchStores calls GET /api/stores', async () => {
    const stores = [{ name: 'my-store', type: 'opensearch', connected: true }]
    apiFetch.mockResolvedValue(stores)

    const result = await fetchStores()

    expect(apiFetch).toHaveBeenCalledWith('/api/stores')
    expect(result).toEqual(stores)
  })

  it('fetchStoreDocuments calls GET /api/stores/:store/documents', async () => {
    const docs = [{ docId: 'doc-1', filename: 'test.pdf', state: 'Ingested', chunkCount: 12 }]
    apiFetch.mockResolvedValue(docs)

    const result = await fetchStoreDocuments('my-store')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/documents')
    expect(result).toEqual(docs)
  })

  it('removeDocumentFromStore calls DELETE /api/stores/:store/documents/:docId', async () => {
    apiFetch.mockResolvedValue(undefined)

    await removeDocumentFromStore('my-store', 'doc-1')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/documents/doc-1', {
      method: 'DELETE',
    })
  })

  it('queryStore calls POST /api/stores/:store/query with body', async () => {
    const results = [{ chunkId: 'c1', docId: 'd1', filename: 'a.pdf', text: 'hi', score: 0.9 }]
    apiFetch.mockResolvedValue(results)

    const result = await queryStore('my-store', 'what is X?', 3)

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/query', {
      method: 'POST',
      body: JSON.stringify({ query: 'what is X?', top_k: 3 }),
    })
    expect(result).toEqual(results)
  })
})

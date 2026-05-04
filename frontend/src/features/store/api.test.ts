import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createStore,
  deleteStore,
  fetchStore,
  fetchStores,
  fetchStoreDocuments,
  queryStore,
  removeDocumentFromStore,
  updateStore,
} from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('store API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchStores calls GET /api/stores', async () => {
    const stores = [
      {
        name: 'my-store',
        slug: 'my-store',
        type: 'opensearch',
        embedder: 'bge-m3',
        isDefault: true,
        connected: true,
        documentCount: 0,
        chunkCount: 0,
      },
    ]
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(stores)

    const result = await fetchStores()

    expect(apiFetch).toHaveBeenCalledWith('/api/stores')
    expect(result).toEqual(stores)
  })

  it('fetchStore calls GET /api/stores/:slug', async () => {
    const store = { id: 's-1', slug: 'rh', name: 'rh', kind: 'opensearch' }
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(store)

    const result = await fetchStore('rh')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/rh')
    expect(result).toEqual(store)
  })

  it('createStore POSTs the payload', async () => {
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ slug: 'rh' })

    await createStore({
      name: 'rh',
      slug: 'rh',
      kind: 'opensearch',
      embedder: 'bge-m3',
      config: { indexName: 'rh' },
    })

    expect(apiFetch).toHaveBeenCalledWith('/api/stores', {
      method: 'POST',
      body: JSON.stringify({
        name: 'rh',
        slug: 'rh',
        kind: 'opensearch',
        embedder: 'bge-m3',
        config: { indexName: 'rh' },
      }),
    })
  })

  it('updateStore PATCHes the payload', async () => {
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ slug: 'rh' })

    await updateStore('rh', { embedder: 'bge-large' })

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/rh', {
      method: 'PATCH',
      body: JSON.stringify({ embedder: 'bge-large' }),
    })
  })

  it('deleteStore calls DELETE /api/stores/:slug', async () => {
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)

    await deleteStore('rh')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/rh', { method: 'DELETE' })
  })

  it('fetchStoreDocuments calls GET /api/stores/:store/documents', async () => {
    const docs = [{ docId: 'doc-1', filename: 'test.pdf', state: 'Ingested', chunkCount: 12 }]
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(docs)

    const result = await fetchStoreDocuments('my-store')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/documents')
    expect(result).toEqual(docs)
  })

  it('removeDocumentFromStore calls DELETE /api/stores/:store/documents/:docId', async () => {
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)

    await removeDocumentFromStore('my-store', 'doc-1')

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/documents/doc-1', {
      method: 'DELETE',
    })
  })

  it('queryStore calls POST /api/stores/:store/query with body', async () => {
    const results = [{ chunkId: 'c1', docId: 'd1', filename: 'a.pdf', text: 'hi', score: 0.9 }]
    ;(apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(results)

    const result = await queryStore('my-store', 'what is X?', 3)

    expect(apiFetch).toHaveBeenCalledWith('/api/stores/my-store/query', {
      method: 'POST',
      body: JSON.stringify({ query: 'what is X?', top_k: 3 }),
    })
    expect(result).toEqual(results)
  })
})

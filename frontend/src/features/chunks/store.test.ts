import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChunksStore } from './store'

vi.mock('./api', () => ({
  fetchChunks: vi.fn(),
  updateChunk: vi.fn(),
  mergeChunks: vi.fn(),
  splitChunk: vi.fn(),
  dropChunk: vi.fn(),
  addChunk: vi.fn(),
  fetchChunkDiff: vi.fn(),
  pushChunksToStore: vi.fn(),
}))

vi.mock('../document/api', () => ({
  rechunkDocument: vi.fn(),
}))

import * as api from './api'
import * as documentApi from '../document/api'

const makeChunk = (id: string, text = 'text', overrides: Record<string, unknown> = {}) => ({
  id,
  docId: 'd1',
  sequence: 0,
  text,
  headings: [],
  sourcePage: null,
  tokenCount: null,
  bboxes: [],
  docItems: [],
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  ...overrides,
})

describe('useChunksStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('load — sets chunks and clears loading', async () => {
    const chunks = [makeChunk('c1'), makeChunk('c2')]
    api.fetchChunks.mockResolvedValue(chunks)

    const store = useChunksStore()
    const loadPromise = store.load('d1')
    expect(store.loading).toBe(true)
    await loadPromise
    expect(store.loading).toBe(false)
    expect(store.chunks).toEqual(chunks)
  })

  it('load — sets error on failure', async () => {
    api.fetchChunks.mockRejectedValue(new Error('boom'))
    const store = useChunksStore()
    await store.load('d1')
    expect(store.error).toBe('boom')
    expect(store.chunks).toEqual([])
  })

  it('chunksOnPage — filters by sourcePage', async () => {
    const chunks = [
      makeChunk('c1', 'a', { sourcePage: 1 }),
      makeChunk('c2', 'b', { sourcePage: 2 }),
      makeChunk('c3', 'c', { sourcePage: 1 }),
      makeChunk('c4', 'd', { sourcePage: null }),
    ]
    api.fetchChunks.mockResolvedValue(chunks)
    const store = useChunksStore()
    await store.load('d1')
    expect(store.chunksOnPage(1).map((c) => c.id)).toEqual(['c1', 'c3'])
    expect(store.chunksOnPage(2).map((c) => c.id)).toEqual(['c2'])
    expect(store.chunksOnPage(3)).toEqual([])
  })

  it('updateText — replaces chunk in list', async () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1', 'original')]
    const updated = makeChunk('c1', 'changed')
    api.updateChunk.mockResolvedValue(updated)

    await store.updateText('d1', 'c1', 'changed')

    expect(store.chunks[0].text).toBe('changed')
  })

  it('updateTitle — replaces chunk in list', async () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1')]
    const updated = makeChunk('c1', 'text', { headings: ['New title'] })
    api.updateChunk.mockResolvedValue(updated)

    await store.updateTitle('d1', 'c1', 'New title')

    expect(store.chunks[0].headings[0]).toBe('New title')
  })

  it('drop — removes chunk from list', async () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1'), makeChunk('c2')]
    api.dropChunk.mockResolvedValue(undefined)

    await store.drop('d1', 'c1')

    expect(store.chunks).toHaveLength(1)
    expect(store.chunks[0].id).toBe('c2')
  })

  it('add — appends at end when no afterId', async () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1')]
    const created = makeChunk('cnew', 'new text')
    api.addChunk.mockResolvedValue(created)

    await store.add('d1', 'new text')

    expect(store.chunks).toHaveLength(2)
    expect(store.chunks[1].id).toBe('cnew')
  })

  it('add — inserts after given chunk', async () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1'), makeChunk('c2')]
    const created = makeChunk('cnew', 'new text')
    api.addChunk.mockResolvedValue(created)

    await store.add('d1', 'new text', 'c1')

    expect(store.chunks[1].id).toBe('cnew')
    expect(store.chunks[2].id).toBe('c2')
  })

  it('loadDiff — sets diff', async () => {
    const diffs = [{ chunkId: 'c1', status: 'modified' as const, textDiff: 'x' }]
    api.fetchChunkDiff.mockResolvedValue(diffs)
    const store = useChunksStore()

    await store.loadDiff('d1', 'my-store')

    expect(store.diff).toEqual(diffs)
  })

  it('push — returns jobId on success', async () => {
    api.pushChunksToStore.mockResolvedValue({ jobId: 'j1', summary: { embeds: 3, tokens: 500 } })
    const store = useChunksStore()

    const jobId = await store.push('d1', 'my-store')

    expect(jobId).toBe('j1')
  })

  it('push — returns null on failure', async () => {
    api.pushChunksToStore.mockRejectedValue(new Error('network'))
    const store = useChunksStore()

    const jobId = await store.push('d1', 'my-store')

    expect(jobId).toBeNull()
    expect(store.error).toBe('network')
  })

  // ---------------------------------------------------------------------------
  // rechunk + hasManualEdits (#268)
  // ---------------------------------------------------------------------------

  it('rechunk — replaces chunks with the API response and returns true', async () => {
    const next = [makeChunk('c1'), makeChunk('c2')]
    documentApi.rechunkDocument.mockResolvedValue(next)
    const store = useChunksStore()
    store.chunks = [makeChunk('old')]

    const ok = await store.rechunk('d1', { chunkerType: 'hybrid', maxTokens: 256 })

    expect(documentApi.rechunkDocument).toHaveBeenCalledWith('d1', {
      chunkerType: 'hybrid',
      maxTokens: 256,
    })
    expect(ok).toBe(true)
    expect(store.chunks.map((c) => c.id)).toEqual(['c1', 'c2'])
    expect(store.rechunking).toBe(false)
  })

  it('rechunk — returns false on failure and keeps existing chunks', async () => {
    documentApi.rechunkDocument.mockRejectedValue(new Error('boom'))
    const store = useChunksStore()
    store.chunks = [makeChunk('old')]

    const ok = await store.rechunk('d1')

    expect(ok).toBe(false)
    expect(store.error).toBe('boom')
    expect(store.chunks.map((c) => c.id)).toEqual(['old'])
    expect(store.rechunking).toBe(false)
  })

  it('hasManualEdits — false when updatedAt equals createdAt for every chunk', () => {
    const store = useChunksStore()
    store.chunks = [makeChunk('c1'), makeChunk('c2')]
    expect(store.hasManualEdits).toBe(false)
  })

  it('hasManualEdits — true as soon as one chunk has been touched', () => {
    const store = useChunksStore()
    store.chunks = [
      makeChunk('c1'),
      makeChunk('c2', 'edited', { updatedAt: '2025-02-01T00:00:00Z' }),
    ]
    expect(store.hasManualEdits).toBe(true)
  })
})

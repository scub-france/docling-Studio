import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchChunks,
  updateChunk,
  mergeChunks,
  splitChunk,
  dropChunk,
  addChunk,
  fetchChunkDiff,
  pushChunksToStore,
} from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('chunks API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchChunks calls GET /api/documents/:id/chunks', async () => {
    const chunks = [{ id: 'c1', docId: 'd1', text: 'hello' }]
    apiFetch.mockResolvedValue(chunks)

    const result = await fetchChunks('d1')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks')
    expect(result).toEqual(chunks)
  })

  it('updateChunk calls PATCH with patch body', async () => {
    const chunk = { id: 'c1', docId: 'd1', text: 'updated' }
    apiFetch.mockResolvedValue(chunk)

    const result = await updateChunk('d1', 'c1', { text: 'updated' })

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks/c1', {
      method: 'PATCH',
      body: JSON.stringify({ text: 'updated' }),
    })
    expect(result).toEqual(chunk)
  })

  it('mergeChunks calls POST /chunks/merge with ids', async () => {
    const merged = [{ id: 'cm', docId: 'd1', text: 'merged' }]
    apiFetch.mockResolvedValue(merged)

    const result = await mergeChunks('d1', ['c1', 'c2'])

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks/merge', {
      method: 'POST',
      body: JSON.stringify({ ids: ['c1', 'c2'] }),
    })
    expect(result).toEqual(merged)
  })

  it('splitChunk calls POST /chunks/:id/split with cursorOffset', async () => {
    const split = [
      { id: 'c1a', docId: 'd1', text: 'part1' },
      { id: 'c1b', docId: 'd1', text: 'part2' },
    ]
    apiFetch.mockResolvedValue(split)

    const result = await splitChunk('d1', 'c1', 10)

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks/c1/split', {
      method: 'POST',
      body: JSON.stringify({ cursorOffset: 10 }),
    })
    expect(result).toEqual(split)
  })

  it('dropChunk calls DELETE /api/documents/:id/chunks/:chunkId', async () => {
    apiFetch.mockResolvedValue(undefined)

    await dropChunk('d1', 'c1')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks/c1', { method: 'DELETE' })
  })

  it('addChunk calls POST /chunks with text and afterId', async () => {
    const newChunk = { id: 'cnew', docId: 'd1', text: 'new' }
    apiFetch.mockResolvedValue(newChunk)

    const result = await addChunk('d1', 'new', 'c1')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks', {
      method: 'POST',
      body: JSON.stringify({ text: 'new', afterId: 'c1' }),
    })
    expect(result).toEqual(newChunk)
  })

  it('addChunk works without afterId', async () => {
    const newChunk = { id: 'cnew', docId: 'd1', text: 'new' }
    apiFetch.mockResolvedValue(newChunk)

    await addChunk('d1', 'new')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks', {
      method: 'POST',
      body: JSON.stringify({ text: 'new', afterId: undefined }),
    })
  })

  it('fetchChunkDiff calls GET /diff with encoded store param', async () => {
    const diffs = [{ chunkId: 'c1', status: 'modified', textDiff: 'diff' }]
    apiFetch.mockResolvedValue(diffs)

    const result = await fetchChunkDiff('d1', 'my store')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/diff?store=my%20store')
    expect(result).toEqual(diffs)
  })

  it('pushChunksToStore calls POST /chunks/push with store', async () => {
    const response = { jobId: 'j1', summary: { embeds: 5, tokens: 1000 } }
    apiFetch.mockResolvedValue(response)

    const result = await pushChunksToStore('d1', 'my-store')

    expect(apiFetch).toHaveBeenCalledWith('/api/documents/d1/chunks/push', {
      method: 'POST',
      body: JSON.stringify({ store: 'my-store' }),
    })
    expect(result).toEqual(response)
  })
})

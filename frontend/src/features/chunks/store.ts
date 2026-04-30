import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DocChunk, ChunkDiff } from '../../shared/types'
import * as api from './api'

export const useChunksStore = defineStore('chunks', () => {
  const chunks = ref<DocChunk[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const diffing = ref(false)
  const diff = ref<ChunkDiff[]>([])
  const error = ref<string | null>(null)

  function clearError(): void {
    error.value = null
  }

  async function load(docId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      chunks.value = await api.fetchChunks(docId)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load chunks'
      console.error('Failed to load chunks', e)
    } finally {
      loading.value = false
    }
  }

  async function updateText(docId: string, chunkId: string, text: string): Promise<void> {
    saving.value = true
    try {
      const updated = await api.updateChunk(docId, chunkId, { text })
      const idx = chunks.value.findIndex((c) => c.id === chunkId)
      if (idx !== -1) chunks.value = chunks.value.with(idx, updated)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to save chunk'
      console.error('Failed to save chunk', e)
    } finally {
      saving.value = false
    }
  }

  async function updateTitle(docId: string, chunkId: string, title: string): Promise<void> {
    saving.value = true
    try {
      const updated = await api.updateChunk(docId, chunkId, { title })
      const idx = chunks.value.findIndex((c) => c.id === chunkId)
      if (idx !== -1) chunks.value = chunks.value.with(idx, updated)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to retitle chunk'
      console.error('Failed to retitle chunk', e)
    } finally {
      saving.value = false
    }
  }

  async function merge(docId: string, ids: string[]): Promise<void> {
    saving.value = true
    try {
      const updated = await api.mergeChunks(docId, ids)
      const idSet = new Set(ids)
      const kept = chunks.value.filter((c) => !idSet.has(c.id))
      const firstIdx = chunks.value.findIndex((c) => idSet.has(c.id))
      chunks.value = [...kept.slice(0, firstIdx), ...updated, ...kept.slice(firstIdx)]
    } catch (e) {
      error.value = (e as Error).message || 'Failed to merge chunks'
      console.error('Failed to merge chunks', e)
    } finally {
      saving.value = false
    }
  }

  async function split(docId: string, chunkId: string, cursorOffset: number): Promise<void> {
    saving.value = true
    try {
      const produced = await api.splitChunk(docId, chunkId, cursorOffset)
      const idx = chunks.value.findIndex((c) => c.id === chunkId)
      if (idx !== -1) {
        chunks.value = [...chunks.value.slice(0, idx), ...produced, ...chunks.value.slice(idx + 1)]
      }
    } catch (e) {
      error.value = (e as Error).message || 'Failed to split chunk'
      console.error('Failed to split chunk', e)
    } finally {
      saving.value = false
    }
  }

  async function drop(docId: string, chunkId: string): Promise<void> {
    saving.value = true
    try {
      await api.dropChunk(docId, chunkId)
      chunks.value = chunks.value.filter((c) => c.id !== chunkId)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to drop chunk'
      console.error('Failed to drop chunk', e)
    } finally {
      saving.value = false
    }
  }

  async function add(docId: string, text: string, afterId?: string): Promise<void> {
    saving.value = true
    try {
      const created = await api.addChunk(docId, text, afterId)
      if (afterId) {
        const idx = chunks.value.findIndex((c) => c.id === afterId)
        if (idx !== -1) {
          chunks.value = [
            ...chunks.value.slice(0, idx + 1),
            created,
            ...chunks.value.slice(idx + 1),
          ]
          return
        }
      }
      chunks.value = [...chunks.value, created]
    } catch (e) {
      error.value = (e as Error).message || 'Failed to add chunk'
      console.error('Failed to add chunk', e)
    } finally {
      saving.value = false
    }
  }

  async function loadDiff(docId: string, store: string): Promise<void> {
    diffing.value = true
    error.value = null
    try {
      diff.value = await api.fetchChunkDiff(docId, store)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load diff'
      console.error('Failed to load diff', e)
    } finally {
      diffing.value = false
    }
  }

  function clearDiff(): void {
    diff.value = []
  }

  async function push(docId: string, store: string): Promise<string | null> {
    try {
      const res = await api.pushChunksToStore(docId, store)
      return res.jobId
    } catch (e) {
      error.value = (e as Error).message || 'Failed to push chunks'
      console.error('Failed to push chunks', e)
      return null
    }
  }

  return {
    chunks,
    loading,
    saving,
    diffing,
    diff,
    error,
    clearError,
    load,
    updateText,
    updateTitle,
    merge,
    split,
    drop,
    add,
    loadDiff,
    clearDiff,
    push,
  }
})

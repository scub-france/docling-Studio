import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { DocChunk, ChunkDiff } from '../../shared/types'
import { rechunkDocument, type RechunkOptions } from '../document/api'
import * as api from './api'

export const useChunksStore = defineStore('chunks', () => {
  const chunks = ref<DocChunk[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const rechunking = ref(false)
  const diffing = ref(false)
  const diff = ref<ChunkDiff[]>([])
  const error = ref<string | null>(null)
  // 0.6.1 — Strategy popover open state (#268). Lifted to the store so
  // either the in-panel `⚙ Strategy` button or the workspace-level
  // `Generate chunks` button can open the same popover.
  const strategyOpen = ref(false)

  function clearError(): void {
    error.value = null
  }

  function openStrategy(): void {
    strategyOpen.value = true
  }

  function closeStrategy(): void {
    strategyOpen.value = false
  }

  /** Pure derived getter — chunks whose `sourcePage` matches the given page. */
  const chunksOnPage = computed(
    () => (page: number) => chunks.value.filter((c) => c.sourcePage === page),
  )

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

  /**
   * Rechunk the canonical chunkset with the given options (#268). The
   * backend replaces the whole chunkset and returns the new list; the
   * store overwrites `chunks` so the UI reflects the new layout in
   * one render pass.
   */
  async function rechunk(docId: string, options?: RechunkOptions): Promise<boolean> {
    rechunking.value = true
    error.value = null
    try {
      chunks.value = await rechunkDocument(docId, options)
      return true
    } catch (e) {
      error.value = (e as Error).message || 'Failed to rechunk'
      console.error('Failed to rechunk', e)
      return false
    } finally {
      rechunking.value = false
    }
  }

  /** True when at least one chunk has been hand-edited (#264 — chunks
   *  where `updatedAt !== createdAt` are flagged with the `edited`
   *  badge). The Strategy popover uses this to gate a confirm step. */
  const hasManualEdits = computed(() =>
    chunks.value.some((c) => c.updatedAt && c.createdAt && c.updatedAt !== c.createdAt),
  )

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
      return res.pushId
    } catch (e) {
      error.value = (e as Error).message || 'Failed to push chunks'
      console.error('Failed to push chunks', e)
      return null
    }
  }

  return {
    chunks,
    chunksOnPage,
    hasManualEdits,
    loading,
    saving,
    rechunking,
    diffing,
    diff,
    error,
    strategyOpen,
    clearError,
    openStrategy,
    closeStrategy,
    load,
    rechunk,
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

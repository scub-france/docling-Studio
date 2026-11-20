import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Analysis, Document, Page } from '../../shared/types'
import { appMaxFileSizeMb } from '../../shared/appConfig'
import { parseAnalysisPages } from '../../shared/analysisPages'
import { pushChunksToStore } from '@/features/chunks'
import * as api from './api'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const selectedId = ref<string | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  // The analysis the Parse view shows, set by the page that loaded it.
  const workspaceActiveAnalysis = ref<Analysis | null>(null)

  // #303 — Citation focus, shared across the Parse-view surfaces. The
  // reasoning feature writes it (clicking a trace step); the PDF preview,
  // the structure tree and the properties panel read it. `focusTick` bumps
  // on every `focusElement` call — including re-clicking the same ref — so
  // same-value watchers re-fire and "re-click to re-scroll" works (the v1
  // trap was watching `focusedRef` alone, which no-ops on an unchanged value).
  const focusedRef = ref<string | null>(null)
  const focusTick = ref(0)

  function focusElement(ref_: string | null): void {
    focusedRef.value = ref_
    focusTick.value += 1
  }

  /** Pages parsed lazily from the active analysis's `pagesJson`. */
  const workspacePages = computed<Page[]>(() => parseAnalysisPages(workspaceActiveAnalysis.value))

  function clearError(): void {
    error.value = null
  }

  async function load(): Promise<void> {
    loading.value = true
    try {
      error.value = null
      documents.value = await api.fetchDocuments()
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load documents'
      console.error('Failed to load documents', e)
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File): Promise<Document> {
    const maxMb = appMaxFileSizeMb.value
    if (maxMb > 0 && file.size > maxMb * 1024 * 1024) {
      error.value = `File too large (max ${maxMb} MB)`
      throw new Error(error.value)
    }
    uploading.value = true
    error.value = null
    try {
      const doc = await api.uploadDocument(file)
      documents.value.unshift(doc)
      selectedId.value = doc.id
      return doc
    } catch (e) {
      error.value = (e as Error).message || 'Failed to upload document'
      console.error('Failed to upload document', e)
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function remove(id: string): Promise<void> {
    try {
      await api.deleteDocument(id)
      documents.value = documents.value.filter((d) => d.id !== id)
      if (selectedId.value === id) selectedId.value = null
    } catch (e) {
      error.value = (e as Error).message || 'Failed to delete document'
      console.error('Failed to delete document', e)
    }
  }

  function select(id: string): void {
    selectedId.value = id
  }

  async function rechunk(id: string): Promise<number | null> {
    try {
      const chunks = await api.rechunkDocument(id)
      return chunks.length
    } catch (e) {
      error.value = (e as Error).message || 'Failed to rechunk'
      console.error('Rechunk failed', e)
      return null
    }
  }

  async function pushToStore(id: string, store: string): Promise<string | null> {
    try {
      const res = await pushChunksToStore(id, store)
      return res.pushId
    } catch (e) {
      error.value = (e as Error).message || 'Failed to push to store'
      console.error('Push to store failed', e)
      return null
    }
  }

  return {
    documents,
    selectedId,
    loading,
    uploading,
    error,
    workspacePages,
    setWorkspaceAnalysis(analysis: Analysis | null): void {
      workspaceActiveAnalysis.value = analysis
    },
    focusedRef,
    focusTick,
    focusElement,
    clearError,
    load,
    upload,
    remove,
    select,
    rechunk,
    pushToStore,
  }
})

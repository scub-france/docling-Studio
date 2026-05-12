import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Analysis, Document, Page } from '../../shared/types'
import { appMaxFileSizeMb } from '../../shared/appConfig'
import { fetchDocumentAnalyses } from '../analysis/api'
import { pushChunksToStore } from '../chunks/api'
import * as api from './api'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const selectedId = ref<string | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  // 0.6.1 (#264) — Linked view workspace orchestration. Independent from
  // the library listing above (documents/loading) so the two surfaces can
  // be tested in isolation.
  const workspaceDoc = ref<Document | null>(null)
  const workspaceLatestAnalysis = ref<Analysis | null>(null)
  const workspaceLoading = ref(false)
  const workspaceError = ref<string | null>(null)

  /** Pages parsed lazily from `workspaceLatestAnalysis.pagesJson`. Returns
   *  an empty array on missing data or parse error — non-fatal. */
  const workspacePages = computed<Page[]>(() => {
    const raw = workspaceLatestAnalysis.value?.pagesJson
    if (!raw) return []
    try {
      return JSON.parse(raw) as Page[]
    } catch {
      return []
    }
  })

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

  /**
   * Doc workspace orchestration (#264). Fetches the doc metadata and the
   * latest completed analysis in parallel — chunks are loaded by the
   * chunks store independently so the two stores stay testable in
   * isolation.
   */
  async function loadWorkspace(docId: string): Promise<void> {
    workspaceLoading.value = true
    workspaceError.value = null
    workspaceDoc.value = null
    workspaceLatestAnalysis.value = null
    try {
      const [doc, analyses] = await Promise.all([
        api.fetchDocument(docId),
        fetchDocumentAnalyses(docId),
      ])
      workspaceDoc.value = doc
      workspaceLatestAnalysis.value =
        analyses
          .filter((a) => a.status === 'COMPLETED')
          .sort((a, b) => (b.completedAt ?? '').localeCompare(a.completedAt ?? ''))[0] ?? null
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to load workspace'
    } finally {
      workspaceLoading.value = false
    }
  }

  async function pushToStore(id: string, store: string): Promise<string | null> {
    try {
      const res = await pushChunksToStore(id, store)
      return res.jobId
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
    workspaceDoc,
    workspaceLatestAnalysis,
    workspacePages,
    workspaceLoading,
    workspaceError,
    clearError,
    load,
    loadWorkspace,
    upload,
    remove,
    select,
    rechunk,
    pushToStore,
  }
})

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
  // 0.6.1 (#264, #267) — Doc workspace orchestration. Independent from
  // the library listing above (documents/loading) so the two surfaces can
  // be tested in isolation.
  const workspaceDoc = ref<Document | null>(null)
  // Full analyses history for the current doc (#267). Sorted newest-first
  // by completedAt (falling back to createdAt for non-completed entries).
  const workspaceAnalyses = ref<Analysis[]>([])
  // Currently-selected analysis id. Defaults to the latest COMPLETED on
  // load; the History drawer (#267) can pin a different one.
  const workspaceCurrentAnalysisId = ref<string | null>(null)
  const workspaceLoading = ref(false)
  const workspaceError = ref<string | null>(null)

  /** The selected analysis for this workspace — auto-picked latest, or
   *  the one the user pinned via the History drawer. */
  const workspaceLatestAnalysis = computed<Analysis | null>(() => {
    if (!workspaceCurrentAnalysisId.value) return null
    return workspaceAnalyses.value.find((a) => a.id === workspaceCurrentAnalysisId.value) ?? null
  })

  /** Pages parsed lazily from the selected analysis's `pagesJson`. Returns
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
   * Doc workspace orchestration (#264, extended #267). Fetches the doc
   * metadata and the doc's analyses in parallel — chunks are loaded by
   * the chunks store independently so the two stores stay testable in
   * isolation. Defaults the active analysis to the latest COMPLETED one;
   * the History drawer can pin a different one via `setWorkspaceAnalysis`.
   *
   * Idempotent across view switches: if the workspace is already loaded
   * for `docId`, returns immediately. This preserves a user-pinned
   * analysis when the user switches between Parse and Chunk tabs.
   * Reloading the analyses list is a separate concern handled by
   * `reloadAnalyses(docId)`.
   */
  async function loadWorkspace(docId: string): Promise<void> {
    if (workspaceDoc.value?.id === docId) return
    workspaceLoading.value = true
    workspaceError.value = null
    workspaceDoc.value = null
    workspaceAnalyses.value = []
    workspaceCurrentAnalysisId.value = null
    try {
      const [doc, analyses] = await Promise.all([
        api.fetchDocument(docId),
        fetchDocumentAnalyses(docId),
      ])
      workspaceDoc.value = doc
      // Newest-first sort. Falls back to createdAt when completedAt is
      // null (PENDING / RUNNING / FAILED entries still belong to history).
      workspaceAnalyses.value = [...analyses].sort((a, b) =>
        (b.completedAt ?? b.createdAt).localeCompare(a.completedAt ?? a.createdAt),
      )
      // Auto-pick the latest COMPLETED analysis as the active one. If
      // none is completed yet, leave the workspace empty — Parse / Chunk
      // already render an "Aucune analyse" state in that case.
      workspaceCurrentAnalysisId.value =
        workspaceAnalyses.value.find((a) => a.status === 'COMPLETED')?.id ?? null
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to load workspace'
    } finally {
      workspaceLoading.value = false
    }
  }

  /**
   * Switch the active analysis without re-fetching the analyses list
   * (#267). Caller code (DocParseTab / DocChunkTab) is responsible for
   * reloading the chunks tied to the new analysis.
   */
  function setWorkspaceAnalysis(analysisId: string): void {
    if (!workspaceAnalyses.value.some((a) => a.id === analysisId)) return
    workspaceCurrentAnalysisId.value = analysisId
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
    workspaceAnalyses,
    workspaceCurrentAnalysisId,
    workspaceLatestAnalysis,
    workspacePages,
    workspaceLoading,
    workspaceError,
    clearError,
    load,
    loadWorkspace,
    setWorkspaceAnalysis,
    upload,
    remove,
    select,
    rechunk,
    pushToStore,
  }
})

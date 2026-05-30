import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  Analysis,
  Document,
  DocumentEditCommand,
  DocumentEditCommandInput,
  DocumentEditCommitResult,
  DocTreeNode,
  DocumentVersion,
  PageElement,
  Page,
} from '../../shared/types'
import { appMaxFileSizeMb } from '../../shared/appConfig'
import { fetchAnalysis } from '../analysis/api'
import { pushChunksToStore } from '../chunks/api'
import * as api from './api'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const selectedId = ref<string | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  // 0.6.1 (#264, refactored #267) — Doc workspace orchestration. The
  // workspace's History timeline is now versioned (frozen pairs of
  // analysis + chunks snapshot). The active version drives the OCR
  // side of the workspace (pagesJson, treeJson) — the chunks side is
  // owned by `chunksStore`.
  const workspaceDoc = ref<Document | null>(null)
  const workspaceVersions = ref<DocumentVersion[]>([])
  const workspaceCurrentVersionId = ref<string | null>(null)
  // Cached analysis row for the active version (analysisId resolution).
  const workspaceActiveAnalysis = ref<Analysis | null>(null)
  const workspaceDraftPages = ref<Page[] | null>(null)
  const workspaceDraftTree = ref<DocTreeNode[] | null>(null)
  const pendingDocumentCommands = ref<DocumentEditCommand[]>([])
  const documentEditSaving = ref(false)
  const documentEditCommitting = ref(false)
  const workspaceLoading = ref(false)
  const workspaceError = ref<string | null>(null)

  const workspaceCurrentVersion = computed<DocumentVersion | null>(() => {
    if (!workspaceCurrentVersionId.value) return null
    return workspaceVersions.value.find((v) => v.id === workspaceCurrentVersionId.value) ?? null
  })

  /** Backwards-compatible alias kept for existing consumers
   * (DocParseTab, DocChunkTab) — semantically "the analysis row that
   * powers the workspace right now". Resolved from the active version. */
  const workspaceLatestAnalysis = computed<Analysis | null>(() => workspaceActiveAnalysis.value)

  /** Pages parsed lazily from the active analysis's `pagesJson`. */
  const workspaceBasePages = computed<Page[]>(() => {
    const raw = workspaceActiveAnalysis.value?.pagesJson
    if (!raw) return []
    try {
      return JSON.parse(raw) as Page[]
    } catch {
      return []
    }
  })

  const workspacePages = computed<Page[]>(() => workspaceDraftPages.value ?? workspaceBasePages.value)

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
   * Workspace orchestration (#267). Loads the doc + the versions
   * timeline, auto-pins the most recent version, and resolves its
   * analysis row so Parse / Chunk render the right OCR side.
   *
   * Idempotent across view switches: if the workspace is already loaded
   * for `docId`, returns immediately. This preserves a user-pinned
   * version when the user switches between Parse and Chunk tabs.
   */
  async function loadWorkspace(docId: string): Promise<void> {
    if (workspaceDoc.value?.id === docId) return
    workspaceLoading.value = true
    workspaceError.value = null
    workspaceDoc.value = null
    workspaceVersions.value = []
    workspaceCurrentVersionId.value = null
    workspaceActiveAnalysis.value = null
    workspaceDraftPages.value = null
    workspaceDraftTree.value = null
    pendingDocumentCommands.value = []
    try {
      const [doc, versions] = await Promise.all([
        api.fetchDocument(docId),
        api.fetchDocumentVersions(docId),
      ])
      workspaceDoc.value = doc
      workspaceVersions.value = versions
      const latest = versions[0] ?? null
      workspaceCurrentVersionId.value = latest?.id ?? null
      if (latest?.analysisId) {
        workspaceActiveAnalysis.value = await fetchAnalysis(latest.analysisId)
        await hydrateDocumentEditSession(docId)
      }
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to load workspace'
    } finally {
      workspaceLoading.value = false
    }
  }

  /**
   * Refresh the versions list without resetting the doc (#266 / #267).
   * Called after a `+ New analysis` or `+ Generate chunks` completes —
   * the backend appended a fresh version, we pin it as active.
   */
  async function reloadWorkspaceVersions(docId: string): Promise<void> {
    if (workspaceDoc.value?.id !== docId) return
    try {
      const versions = await api.fetchDocumentVersions(docId)
      workspaceVersions.value = versions
      const latest = versions[0] ?? null
      if (latest) {
        workspaceCurrentVersionId.value = latest.id
        if (latest.analysisId) {
          workspaceActiveAnalysis.value = await fetchAnalysis(latest.analysisId)
          await hydrateDocumentEditSession(docId)
        }
      }
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to reload versions'
    }
  }

  /**
   * Pin a different version as the active one — calls the backend
   * restore endpoint (which rewrites the live chunkset from the
   * version's snapshot) and refreshes the active analysis row.
   * Returns `true` on success so callers can update sibling state
   * (e.g. reload the chunks store, scroll, close the drawer).
   */
  async function setWorkspaceVersion(versionId: string): Promise<boolean> {
    const docId = workspaceDoc.value?.id
    if (!docId) return false
    const version = workspaceVersions.value.find((v) => v.id === versionId)
    if (!version) return false
    try {
      await api.restoreDocumentVersion(docId, versionId)
      workspaceCurrentVersionId.value = versionId
      workspaceActiveAnalysis.value = version.analysisId
        ? await fetchAnalysis(version.analysisId)
        : null
      await hydrateDocumentEditSession(docId)
      return true
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to restore version'
      return false
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

  async function hydrateDocumentEditSession(docId: string): Promise<void> {
    pendingDocumentCommands.value = []
    workspaceDraftPages.value = null
    workspaceDraftTree.value = null
    if (!workspaceActiveAnalysis.value?.hasDocumentJson) return
    try {
      const session = await api.fetchDocumentEditSession(docId)
      pendingDocumentCommands.value = session.pendingCommands
      workspaceDraftPages.value = session.pendingCommands.length ? session.pages : null
      workspaceDraftTree.value = session.pendingCommands.length ? session.tree : null
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to load document edit session'
    }
  }

  async function updatePageElement(
    docId: string,
    targetRef: string,
    payload: DocumentEditCommandInput['payload'],
  ): Promise<void> {
    const previousDraft = clonePages(workspaceDraftPages.value ?? workspaceBasePages.value)
    const previousDraftTree = cloneTree(workspaceDraftTree.value)
    workspaceDraftPages.value = updatePageElementLocally(previousDraft, targetRef, payload)
    documentEditSaving.value = true
    try {
      const session = await api.applyDocumentEditCommands(docId, [
        {
          action: 'update_page_element',
          targetRef,
          payload,
        },
      ])
      workspaceDraftPages.value = session.pages
      workspaceDraftTree.value = session.tree
      pendingDocumentCommands.value = session.pendingCommands
    } catch (e) {
      workspaceDraftPages.value = pendingDocumentCommands.value.length ? previousDraft : null
      workspaceDraftTree.value = pendingDocumentCommands.value.length ? previousDraftTree : null
      workspaceError.value = (e as Error).message || 'Failed to update page element'
      throw e
    } finally {
      documentEditSaving.value = false
    }
  }

  async function commitPendingDocumentEdits(docId: string): Promise<DocumentEditCommitResult | null> {
    if (!workspaceDraftPages.value) return null
    documentEditCommitting.value = true
    try {
      const result = await api.commitDocumentEdits(docId, workspaceDraftPages.value)
      workspaceDraftPages.value = result.committed ? null : result.pages
      workspaceDraftTree.value = result.committed ? null : result.tree
      if (result.committed && workspaceActiveAnalysis.value) {
        workspaceActiveAnalysis.value = await fetchAnalysis(workspaceActiveAnalysis.value.id)
        pendingDocumentCommands.value = []
      }
      return result
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to commit document edits'
      throw e
    } finally {
      documentEditCommitting.value = false
    }
  }

  async function discardPendingDocumentEdits(docId: string): Promise<void> {
    try {
      await api.discardDocumentEdits(docId)
      workspaceDraftPages.value = null
      workspaceDraftTree.value = null
      pendingDocumentCommands.value = []
    } catch (e) {
      workspaceError.value = (e as Error).message || 'Failed to discard document edits'
      throw e
    }
  }

  return {
    documents,
    selectedId,
    loading,
    uploading,
    error,
    workspaceDoc,
    workspaceVersions,
    workspaceCurrentVersionId,
    workspaceCurrentVersion,
    workspaceActiveAnalysis,
    workspaceDraftPages,
    workspaceDraftTree,
    pendingDocumentCommands,
    documentEditSaving,
    documentEditCommitting,
    workspaceLatestAnalysis,
    workspaceBasePages,
    workspacePages,
    workspaceLoading,
    workspaceError,
    clearError,
    load,
    loadWorkspace,
    reloadWorkspaceVersions,
    setWorkspaceVersion,
    hydrateDocumentEditSession,
    updatePageElement,
    commitPendingDocumentEdits,
    discardPendingDocumentEdits,
    upload,
    remove,
    select,
    rechunk,
    pushToStore,
  }
})

function clonePages(pages: Page[]): Page[] {
  return pages.map((page) => ({
    ...page,
    elements: page.elements.map((element) => ({ ...element })),
  }))
}

function cloneTree(tree: DocTreeNode[] | null): DocTreeNode[] | null {
  if (!tree) return null
  return tree.map((node) => ({
    ...node,
    children: cloneTree(node.children) ?? [],
  }))
}

function updatePageElementLocally(
  pages: Page[],
  targetRef: string,
  payload: DocumentEditCommandInput['payload'],
): Page[] {
  return pages.map((page) => ({
    ...page,
    elements: page.elements.map((element) =>
      element.self_ref === targetRef ? applyElementPayload(element, payload) : element,
    ),
  }))
}

function applyElementPayload(
  element: PageElement,
  payload: DocumentEditCommandInput['payload'],
): PageElement {
  return {
    ...element,
    content: payload.content ?? element.content,
    bbox: payload.bbox ?? element.bbox,
    type: payload.type ?? element.type,
  }
}

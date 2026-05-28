import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Analysis, Document, DocumentVersion, Page } from '../../shared/types'
import { appMaxFileSizeMb } from '../../shared/appConfig'
import { useI18n } from '../../shared/i18n'
import { useToastStore } from '../../shared/toast/store'
import { fetchAnalysis } from '../analysis/api'
import { pushChunksToStore } from '../chunks/api'
import {
  DoclingDraftSession,
  getDoclingItem,
  projectDoclingPages,
  projectDoclingTree,
  stringifyDoclingDocument,
} from './docling'
import type { DoclingDocument, DoclingRef, DoclingTextItem } from './docling'
import * as api from './api'

export const useDocumentStore = defineStore('document', () => {
  const { t } = useI18n()
  const toastStore = useToastStore()
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
  const workspaceSourceAnalysis = ref<Analysis | null>(null)
  const workspaceDraftSession = ref<DoclingDraftSession | null>(null)
  const workspaceLoading = ref(false)
  const workspaceError = ref<string | null>(null)
  const warnedProjectionMismatchIds = new Set<string>()

  const workspaceCurrentVersion = computed<DocumentVersion | null>(() => {
    if (!workspaceCurrentVersionId.value) return null
    return workspaceVersions.value.find((v) => v.id === workspaceCurrentVersionId.value) ?? null
  })

  const workspaceDraftDirty = computed<boolean>(() => workspaceDraftSession.value?.hasChanges ?? false)

  /** Backwards-compatible alias kept for existing consumers
   * (DocParseTab, DocChunkTab) — semantically "the analysis row that
   * powers the workspace right now". Resolved from the active version. */
  const workspaceLatestAnalysis = computed<Analysis | null>(() => workspaceActiveAnalysis.value)

  /** Pages parsed lazily from the active analysis's `pagesJson`. */
  const workspacePages = computed<Page[]>(() => {
    const draftDoc = workspaceDraftSession.value?.document
    if (draftDoc) {
      return projectDoclingPages(draftDoc)
    }

    const raw = workspaceActiveAnalysis.value?.pagesJson
    if (!raw) return []
    try {
      return JSON.parse(raw) as Page[]
    } catch {
      return []
    }
  })

  const workspaceTree = computed(() => {
    const draftDoc = workspaceDraftSession.value?.document
    if (draftDoc) {
      return projectDoclingTree(draftDoc)
    }

    const raw = workspaceActiveAnalysis.value?.documentJson
    if (!raw) return []
    try {
      return projectDoclingTree(JSON.parse(raw) as DoclingDocument)
    } catch {
      return []
    }
  })

  function createWorkspaceDraftSession(analysis: Analysis | null): DoclingDraftSession | null {
    if (!analysis?.documentJson) {
      return null
    }

    return new DoclingDraftSession(JSON.parse(analysis.documentJson) as DoclingDocument)
  }

  function syncWorkspaceAnalysis(analysis: Analysis | null, options: { replaceSource?: boolean } = {}): void {
    if (options.replaceSource ?? true) {
      workspaceSourceAnalysis.value = analysis
    }
    workspaceDraftSession.value = null
    workspaceActiveAnalysis.value = analysis
    if (!analysis?.documentJson) {
      return
    }

    try {
      workspaceDraftSession.value = createWorkspaceDraftSession(analysis)
      maybeWarnPagesProjectionMismatch(analysis, workspaceDraftSession.value?.document ?? null)
    } catch (e) {
      workspaceError.value =
        (e as Error).message || 'Failed to initialize local document editing for this analysis'
    }
  }

  function maybeWarnPagesProjectionMismatch(
    analysis: Analysis,
    document: DoclingDocument | null,
  ): void {
    if (!document || !analysis.id || warnedProjectionMismatchIds.has(analysis.id)) {
      return
    }
    if (!analysis.pagesJson) {
      return
    }

    let backendPages: Page[] | null = null
    let projectedPages: Page[] | null = null

    try {
      backendPages = JSON.parse(analysis.pagesJson) as Page[]
      projectedPages = projectDoclingPages(document)
      if (JSON.stringify(backendPages) === JSON.stringify(projectedPages)) {
        return
      }
    } catch {
      // Treat parse failures as parity failures: the server payload cannot be
      // compared to the frontend projection, so callers should know.
    }

    warnedProjectionMismatchIds.add(analysis.id)
    const debugKey = savePagesProjectionDebugPayload(analysis.id, analysis.pagesJson, projectedPages)
    const detail = formatPagesProjectionDiff(backendPages, projectedPages, debugKey)
    toastStore.push('warning', t('parse.pagesParityMismatch'), 10000, detail)
  }

  function savePagesProjectionDebugPayload(
    analysisId: string,
    backendPagesJson: string | null,
    projectedPages: Page[] | null,
  ): string {
    const key = `docling-pages-parity:${analysisId}`
    try {
      globalThis.localStorage?.setItem(
        key,
        JSON.stringify(
          {
            analysisId,
            backendPagesJson,
            frontendProjectedPages: projectedPages,
            createdAt: new Date().toISOString(),
          },
          null,
          2,
        ),
      )
    } catch {
      // localStorage is best-effort only.
    }
    return key
  }

  function formatPagesProjectionDiff(
    backendPages: Page[] | null,
    projectedPages: Page[] | null,
    debugKey: string,
  ): string {
    if (!backendPages || !projectedPages) {
      return `${t('parse.pagesParityDebugKey')}: ${debugKey}\nUnable to parse one side of the comparison.`
    }

    const diff = summarizePagesDiff(backendPages, projectedPages)
    return `${diff}\n${t('parse.pagesParityDebugKey')}: ${debugKey}`
  }

  function summarizePagesDiff(backendPages: Page[], projectedPages: Page[]): string {
    if (backendPages.length !== projectedPages.length) {
      return `Page count mismatch: backend=${backendPages.length}, frontend=${projectedPages.length}`
    }

    for (let pageIndex = 0; pageIndex < backendPages.length; pageIndex += 1) {
      const backendPage = backendPages[pageIndex]
      const projectedPage = projectedPages[pageIndex]
      if (!projectedPage) {
        return `Missing frontend page at index ${pageIndex}`
      }
      if (backendPage.page_number !== projectedPage.page_number) {
        return `Page number mismatch at index ${pageIndex}: backend=${backendPage.page_number}, frontend=${projectedPage.page_number}`
      }
      if (backendPage.width !== projectedPage.width || backendPage.height !== projectedPage.height) {
        return `Page size mismatch on page ${backendPage.page_number}: backend=${backendPage.width}x${backendPage.height}, frontend=${projectedPage.width}x${projectedPage.height}`
      }
      if (backendPage.elements.length !== projectedPage.elements.length) {
        return `Element count mismatch on page ${backendPage.page_number}: backend=${backendPage.elements.length}, frontend=${projectedPage.elements.length}`
      }

      for (let elementIndex = 0; elementIndex < backendPage.elements.length; elementIndex += 1) {
        const backendElement = backendPage.elements[elementIndex]
        const projectedElement = projectedPage.elements[elementIndex]
        if (!projectedElement) {
          return `Missing frontend element ${elementIndex} on page ${backendPage.page_number}`
        }
        if (JSON.stringify(backendElement) !== JSON.stringify(projectedElement)) {
          return [
            `First mismatch on page ${backendPage.page_number}, element ${elementIndex}`,
            `backend: ${compactJson(backendElement)}`,
            `frontend: ${compactJson(projectedElement)}`,
          ].join('\n')
        }
      }
    }

    return 'Mismatch detected but no summarized difference could be isolated.'
  }

  function compactJson(value: unknown): string {
    const raw = JSON.stringify(value)
    return raw.length <= 220 ? raw : `${raw.slice(0, 217)}...`
  }

  function guardWorkspaceDraftReplacement(): boolean {
    if (!workspaceDraftDirty.value) return true
    workspaceError.value = 'parse.localDraftBlocked'
    return false
  }

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
    workspaceSourceAnalysis.value = null
    syncWorkspaceAnalysis(null)
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
        syncWorkspaceAnalysis(await fetchAnalysis(latest.analysisId))
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
        if (!guardWorkspaceDraftReplacement()) {
          return
        }
        workspaceCurrentVersionId.value = latest.id
        if (latest.analysisId) {
          syncWorkspaceAnalysis(await fetchAnalysis(latest.analysisId))
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
    if (!guardWorkspaceDraftReplacement()) return false
    try {
      await api.restoreDocumentVersion(docId, versionId)
      workspaceCurrentVersionId.value = versionId
      syncWorkspaceAnalysis(version.analysisId ? await fetchAnalysis(version.analysisId) : null)
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

  function getNextMergeableWorkspaceText(ref: string): string | null {
    const session = workspaceDraftSession.value
    if (!session) return null

    const item = getDoclingItem(session.document, ref)
    if (!item || !("text" in item)) return null

    const parentRef = item.parent?.$ref ?? '#/body'
    const siblings = getParentChildren(session.document, parentRef)
    const index = siblings.findIndex((child) => child.$ref === ref)
    if (index === -1) return null
    const nextRef = siblings[index + 1]?.$ref
    if (!nextRef) return null
    const nextItem = getDoclingItem(session.document, nextRef)
    return nextItem && "text" in nextItem ? nextRef : null
  }

  function mergeWorkspaceTexts(
    leadingRef: string,
    trailingRef: string,
  ): { leadingRef: string; trailingRef: string; mergedText: string } {
    const analysis = workspaceActiveAnalysis.value
    const session = workspaceDraftSession.value
    if (!analysis || !session) {
      throw new Error('No editable workspace analysis is loaded')
    }

    session.apply({ type: 'merge-texts', leadingRef, trailingRef })
    const mergedItem = getDoclingItem(session.document, leadingRef)
    if (!mergedItem || !("text" in mergedItem)) {
      throw new Error(`Merged text item not found: ${leadingRef}`)
    }

    const mergedText = (mergedItem as DoclingTextItem).text
    const nextAnalysis: Analysis = {
      ...analysis,
      documentJson: stringifyDoclingDocument(session.document),
      pagesJson: JSON.stringify(projectDoclingPages(session.document)),
    }
    workspaceActiveAnalysis.value = nextAnalysis

    return { leadingRef, trailingRef, mergedText }
  }

  function discardWorkspaceDraft(): boolean {
    const analysis = workspaceSourceAnalysis.value
    if (!analysis) return false

    workspaceError.value = null
    syncWorkspaceAnalysis(analysis, { replaceSource: false })
    return true
  }

  function getParentChildren(doc: DoclingDocument, parentRef: string): DoclingRef[] {
    if (parentRef === '#/body') return doc.body.children
    if (parentRef === '#/furniture') return doc.furniture.children
    const parent = getDoclingItem(doc, parentRef)
    return parent?.children ?? []
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
    workspaceSourceAnalysis,
    workspaceDraftSession,
    workspaceLatestAnalysis,
    workspaceDraftDirty,
    workspacePages,
    workspaceTree,
    workspaceLoading,
    workspaceError,
    clearError,
    load,
    loadWorkspace,
    reloadWorkspaceVersions,
    setWorkspaceVersion,
    getNextMergeableWorkspaceText,
    mergeWorkspaceTexts,
    discardWorkspaceDraft,
    upload,
    remove,
    select,
    rechunk,
    pushToStore,
  }
})

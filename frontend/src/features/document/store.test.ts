import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDocumentStore } from './store'

vi.mock('./api', () => ({
  fetchDocument: vi.fn(),
  fetchDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  rechunkDocument: vi.fn(),
  fetchDocumentVersions: vi.fn(),
  restoreDocumentVersion: vi.fn(),
}))

vi.mock('../chunks/api', () => ({
  pushChunksToStore: vi.fn(),
}))

vi.mock('../analysis/api', () => ({
  fetchAnalysis: vi.fn(),
}))

import * as api from './api'
import * as chunksApi from '../chunks/api'
import * as analysisApi from '../analysis/api'

describe('useDocumentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts with empty state', () => {
    const store = useDocumentStore()
    expect(store.documents).toEqual([])
    expect(store.selectedId).toBeNull()
    expect(store.uploading).toBe(false)
  })

  it('load() fetches and sets documents', async () => {
    const docs = [
      { id: '1', filename: 'a.pdf' },
      { id: '2', filename: 'b.pdf' },
    ]
    api.fetchDocuments.mockResolvedValue(docs)

    const store = useDocumentStore()
    await store.load()

    expect(store.documents).toEqual(docs)
  })

  it('load() handles errors gracefully', async () => {
    api.fetchDocuments.mockRejectedValue(new Error('network'))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const store = useDocumentStore()
    await store.load()

    expect(store.documents).toEqual([])
    spy.mockRestore()
  })

  it('upload() adds document to front of list and selects it', async () => {
    const newDoc = { id: 'new', filename: 'new.pdf' }
    api.uploadDocument.mockResolvedValue(newDoc)

    const store = useDocumentStore()
    store.documents = [{ id: 'old', filename: 'old.pdf' }]

    const result = await store.upload(new File([], 'new.pdf'))

    expect(result).toEqual(newDoc)
    expect(store.documents[0]).toEqual(newDoc)
    expect(store.selectedId).toBe('new')
    expect(store.uploading).toBe(false)
  })

  it('upload() sets uploading to true during upload', async () => {
    let resolveUpload
    api.uploadDocument.mockImplementation(
      () =>
        new Promise((r) => {
          resolveUpload = r
        }),
    )

    const store = useDocumentStore()
    const promise = store.upload(new File([], 'test.pdf'))

    expect(store.uploading).toBe(true)
    resolveUpload({ id: '1', filename: 'test.pdf' })
    await promise
    expect(store.uploading).toBe(false)
  })

  it('upload() resets uploading on error', async () => {
    api.uploadDocument.mockRejectedValue(new Error('fail'))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const store = useDocumentStore()

    await expect(store.upload(new File([], 'test.pdf'))).rejects.toThrow('fail')
    expect(store.uploading).toBe(false)
  })

  it('remove() deletes document and clears selection if needed', async () => {
    api.deleteDocument.mockResolvedValue(null)

    const store = useDocumentStore()
    store.documents = [{ id: '1' }, { id: '2' }]
    store.selectedId = '1'

    await store.remove('1')

    expect(store.documents).toEqual([{ id: '2' }])
    expect(store.selectedId).toBeNull()
  })

  it('remove() does not clear selection for other documents', async () => {
    api.deleteDocument.mockResolvedValue(null)

    const store = useDocumentStore()
    store.documents = [{ id: '1' }, { id: '2' }]
    store.selectedId = '2'

    await store.remove('1')

    expect(store.selectedId).toBe('2')
  })

  it('select() sets selectedId', () => {
    const store = useDocumentStore()
    store.select('42')
    expect(store.selectedId).toBe('42')
  })

  it('load() sets loading to false after success', async () => {
    api.fetchDocuments.mockResolvedValue([])
    const store = useDocumentStore()
    await store.load()
    expect(store.loading).toBe(false)
  })

  it('load() sets loading to false after error', async () => {
    api.fetchDocuments.mockRejectedValue(new Error('fail'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const store = useDocumentStore()
    await store.load()
    expect(store.loading).toBe(false)
  })

  it('rechunk() returns chunk count on success', async () => {
    api.rechunkDocument.mockResolvedValue([{ id: 'c1' }, { id: 'c2' }, { id: 'c3' }])
    const store = useDocumentStore()
    const result = await store.rechunk('42')
    expect(api.rechunkDocument).toHaveBeenCalledWith('42')
    expect(result).toBe(3)
  })

  it('rechunk() returns null on error', async () => {
    api.rechunkDocument.mockRejectedValue(new Error('fail'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const store = useDocumentStore()
    const result = await store.rechunk('42')
    expect(result).toBeNull()
  })

  it('pushToStore() delegates to chunks/api.pushChunksToStore and returns jobId', async () => {
    chunksApi.pushChunksToStore.mockResolvedValue({
      jobId: 'j2',
      summary: { embeds: 5, tokens: 50 },
    })
    const store = useDocumentStore()
    const result = await store.pushToStore('42', 'my-store')
    expect(chunksApi.pushChunksToStore).toHaveBeenCalledWith('42', 'my-store')
    expect(result).toBe('j2')
  })

  it('pushToStore() returns null on error', async () => {
    chunksApi.pushChunksToStore.mockRejectedValue(new Error('fail'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const store = useDocumentStore()
    const result = await store.pushToStore('42', 'my-store')
    expect(result).toBeNull()
  })

  // ---------------------------------------------------------------------------
  // loadWorkspace (#264 / #267) — versioned (analysis, chunks) timeline
  // ---------------------------------------------------------------------------

  const mkVersion = (overrides = {}) => ({
    id: 'v1',
    documentId: 'd1',
    kind: 'analysis' as const,
    analysisId: 'a1',
    chunksSnapshotSize: 0,
    summary: 'Analysis run',
    createdAt: '2025-02-01T00:00:00Z',
    ...overrides,
  })

  const mkAnalysis = (overrides = {}) => ({
    id: 'a1',
    documentId: 'd1',
    documentFilename: 'a.pdf',
    status: 'COMPLETED' as const,
    contentMarkdown: null,
    contentHtml: null,
    pagesJson: '[]',
    chunksJson: null,
    hasDocumentJson: true,
    errorMessage: null,
    progressCurrent: null,
    progressTotal: null,
    startedAt: null,
    completedAt: '2025-02-01T00:00:00Z',
    createdAt: '2025-02-01T00:00:00Z',
    ...overrides,
  })

  it('loadWorkspace() loads doc + auto-pins the latest version + fetches its analysis', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([
      mkVersion({ id: 'v-new', createdAt: '2025-02-01T00:00:00Z' }),
      mkVersion({ id: 'v-old', createdAt: '2025-01-01T00:00:00Z' }),
    ])
    analysisApi.fetchAnalysis.mockResolvedValue(mkAnalysis())

    const store = useDocumentStore()
    await store.loadWorkspace('d1')

    expect(store.workspaceDoc?.id).toBe('d1')
    expect(store.workspaceCurrentVersionId).toBe('v-new')
    expect(store.workspaceVersions.map((v) => v.id)).toEqual(['v-new', 'v-old'])
    expect(store.workspaceLatestAnalysis?.id).toBe('a1')
    expect(store.workspaceLoading).toBe(false)
    expect(store.workspaceError).toBeNull()
  })

  it('loadWorkspace() exposes null active analysis when no versions exist', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([])
    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    expect(store.workspaceCurrentVersionId).toBeNull()
    expect(store.workspaceLatestAnalysis).toBeNull()
    expect(store.workspacePages).toEqual([])
  })

  it('loadWorkspace() sets workspaceError on failure', async () => {
    api.fetchDocument.mockRejectedValue(new Error('boom'))
    api.fetchDocumentVersions.mockResolvedValue([])
    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    expect(store.workspaceError).toBe('boom')
    expect(store.workspaceLoading).toBe(false)
  })

  it('workspacePages parses pages_json lazily, empty on parse error', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([mkVersion()])
    analysisApi.fetchAnalysis.mockResolvedValue(
      mkAnalysis({
        pagesJson: '[{"page_number":1,"width":600,"height":800,"elements":[]}]',
      }),
    )
    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    expect(store.workspacePages).toHaveLength(1)
    expect(store.workspacePages[0].page_number).toBe(1)
  })

  // ---------------------------------------------------------------------------
  // setWorkspaceVersion — restore path
  // ---------------------------------------------------------------------------

  it('setWorkspaceVersion() POSTs restore + swaps the active version + analysis', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([
      mkVersion({ id: 'v-new', analysisId: 'a-new' }),
      mkVersion({ id: 'v-old', analysisId: 'a-old' }),
    ])
    analysisApi.fetchAnalysis.mockImplementation((id: string) =>
      Promise.resolve(mkAnalysis({ id })),
    )
    api.restoreDocumentVersion.mockResolvedValue(mkVersion({ id: 'v-old' }))

    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    expect(store.workspaceCurrentVersionId).toBe('v-new')

    const ok = await store.setWorkspaceVersion('v-old')
    expect(ok).toBe(true)
    expect(api.restoreDocumentVersion).toHaveBeenCalledWith('d1', 'v-old')
    expect(store.workspaceCurrentVersionId).toBe('v-old')
    expect(store.workspaceActiveAnalysis?.id).toBe('a-old')
  })

  it('setWorkspaceVersion() returns false for unknown ids and leaves state intact', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([mkVersion({ id: 'v1' })])
    analysisApi.fetchAnalysis.mockResolvedValue(mkAnalysis())

    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    const ok = await store.setWorkspaceVersion('nope')
    expect(ok).toBe(false)
    expect(store.workspaceCurrentVersionId).toBe('v1')
  })

  it('loadWorkspace() is idempotent — pinned version survives a second call for the same doc', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValue([
      mkVersion({ id: 'v-new', analysisId: 'a-new' }),
      mkVersion({ id: 'v-old', analysisId: 'a-old' }),
    ])
    analysisApi.fetchAnalysis.mockImplementation((id: string) =>
      Promise.resolve(mkAnalysis({ id })),
    )
    api.restoreDocumentVersion.mockResolvedValue(mkVersion({ id: 'v-old' }))

    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    await store.setWorkspaceVersion('v-old')
    // Mimics switching tabs — second loadWorkspace must be a no-op.
    await store.loadWorkspace('d1')
    expect(store.workspaceCurrentVersionId).toBe('v-old')
    expect(api.fetchDocument).toHaveBeenCalledTimes(1)
  })

  // ---------------------------------------------------------------------------
  // reloadWorkspaceVersions — post-completion refresh
  // ---------------------------------------------------------------------------

  it('reloadWorkspaceVersions() refreshes the list + auto-pins the newest', async () => {
    api.fetchDocument.mockResolvedValue({ id: 'd1', filename: 'a.pdf' })
    api.fetchDocumentVersions.mockResolvedValueOnce([mkVersion({ id: 'v1', analysisId: 'a1' })])
    analysisApi.fetchAnalysis.mockResolvedValue(mkAnalysis({ id: 'a1' }))

    const store = useDocumentStore()
    await store.loadWorkspace('d1')
    expect(store.workspaceCurrentVersionId).toBe('v1')

    api.fetchDocumentVersions.mockResolvedValueOnce([
      mkVersion({ id: 'v2', analysisId: 'a2', createdAt: '2025-03-01T00:00:00Z' }),
      mkVersion({ id: 'v1', analysisId: 'a1' }),
    ])
    analysisApi.fetchAnalysis.mockResolvedValue(mkAnalysis({ id: 'a2' }))

    await store.reloadWorkspaceVersions('d1')
    expect(store.workspaceCurrentVersionId).toBe('v2')
    expect(store.workspaceActiveAnalysis?.id).toBe('a2')
  })
})

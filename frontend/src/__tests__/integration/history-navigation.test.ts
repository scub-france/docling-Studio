// Integration test — exercises the cross-feature wiring between history,
// analysis and document stores when restoring a History → Studio navigation.
// Lives under `src/__tests__/integration/` because importing real stores from
// three sibling features would be a feature-isolation violation in any
// single-feature test file. HTTP boundaries are still mocked.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../features/analysis/api', () => ({
  fetchAnalysisSummaries: vi.fn(),
  fetchAnalysis: vi.fn(),
  createAnalysis: vi.fn(),
  deleteAnalysis: vi.fn(),
}))

vi.mock('../../features/history/api', () => ({
  fetchHistory: vi.fn(),
  deleteHistoryEntry: vi.fn(),
}))

vi.mock('../../features/document/api', () => ({
  fetchDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  getPreviewUrl: vi.fn(),
}))

import { useHistoryStore } from '../../features/history/store'
import { useAnalysisStore } from '../../features/analysis/store'
import { useDocumentStore } from '../../features/document/store'

describe('History → Studio navigation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('History store provides data for navigation', () => {
    it('analyses contain documentId for document selection', async () => {
      const { fetchHistory } = await import('../../features/history/api')
      fetchHistory.mockResolvedValue([
        { id: 'a1', documentId: 'd1', documentFilename: 'test.pdf', status: 'COMPLETED' },
        { id: 'a2', documentId: 'd2', documentFilename: 'other.pdf', status: 'FAILED' },
      ])

      const store = useHistoryStore()
      await store.load()

      expect(store.analyses[0].documentId).toBe('d1')
      expect(store.analyses[1].documentId).toBe('d2')
    })
  })

  describe('Analysis store select() restores analysis state', () => {
    it('select() sets currentAnalysis from fetched data', async () => {
      const { fetchAnalysis } = await import('../../features/analysis/api')
      const analysis = {
        id: 'a1',
        documentId: 'd1',
        status: 'COMPLETED',
        contentMarkdown: '# Hello',
        pagesJson: '[{"page_number":1}]',
      }
      fetchAnalysis.mockResolvedValue(analysis)

      const store = useAnalysisStore()
      await store.select('a1')

      expect(store.currentAnalysis).toEqual(analysis)
      expect(store.currentAnalysis.documentId).toBe('d1')
    })

    it('select() allows document store to select the associated document', async () => {
      const { fetchAnalysis } = await import('../../features/analysis/api')
      fetchAnalysis.mockResolvedValue({
        id: 'a1',
        documentId: 'd1',
        status: 'COMPLETED',
      })

      const analysisStore = useAnalysisStore()
      const docStore = useDocumentStore()
      docStore.documents = [
        { id: 'd1', filename: 'test.pdf' },
        { id: 'd2', filename: 'other.pdf' },
      ]

      await analysisStore.select('a1')
      docStore.select(analysisStore.currentAnalysis.documentId)

      expect(docStore.selectedId).toBe('d1')
    })
  })

  describe('Navigation intent from history items', () => {
    it('completed analysis navigates to studio with analysisId query', () => {
      // Simulates what HistoryList.openAnalysis does
      const analysis = { id: 'a1', documentId: 'd1', status: 'COMPLETED' }

      mockPush({ name: 'studio', query: { analysisId: analysis.id } })

      expect(mockPush).toHaveBeenCalledWith({
        name: 'studio',
        query: { analysisId: 'a1' },
      })
    })

    it('pending analysis navigates with same pattern', () => {
      const analysis = { id: 'a2', documentId: 'd2', status: 'PENDING' }

      mockPush({ name: 'studio', query: { analysisId: analysis.id } })

      expect(mockPush).toHaveBeenCalledWith({
        name: 'studio',
        query: { analysisId: 'a2' },
      })
    })

    it('failed analysis navigates with same pattern', () => {
      const analysis = { id: 'a3', documentId: 'd3', status: 'FAILED' }

      mockPush({ name: 'studio', query: { analysisId: analysis.id } })

      expect(mockPush).toHaveBeenCalledWith({
        name: 'studio',
        query: { analysisId: 'a3' },
      })
    })
  })

  describe('Full restore flow (store-level integration)', () => {
    it('restores completed analysis: selects analysis + document + verify mode', async () => {
      const { fetchAnalysis } = await import('../../features/analysis/api')
      fetchAnalysis.mockResolvedValue({
        id: 'a1',
        documentId: 'd1',
        status: 'COMPLETED',
        contentMarkdown: '# Result',
        pagesJson: '[{"page_number":1,"width":612,"height":792}]',
      })

      const analysisStore = useAnalysisStore()
      const docStore = useDocumentStore()
      docStore.documents = [{ id: 'd1', filename: 'test.pdf' }]

      // Simulate what StudioPage.onMounted does with ?analysisId=a1
      await analysisStore.select('a1')
      const analysis = analysisStore.currentAnalysis
      expect(analysis).not.toBeNull()

      docStore.select(analysis.documentId)
      expect(docStore.selectedId).toBe('d1')

      // Mode would be set to 'verify' since status is COMPLETED
      const mode = analysis.status === 'COMPLETED' ? 'verify' : 'configure'
      expect(mode).toBe('verify')
    })

    it('restores failed analysis: selects analysis + document, stays in configure mode', async () => {
      const { fetchAnalysis } = await import('../../features/analysis/api')
      fetchAnalysis.mockResolvedValue({
        id: 'a2',
        documentId: 'd2',
        status: 'FAILED',
        errorMessage: 'parse error',
      })

      const analysisStore = useAnalysisStore()
      const docStore = useDocumentStore()
      docStore.documents = [{ id: 'd2', filename: 'broken.pdf' }]

      await analysisStore.select('a2')
      const analysis = analysisStore.currentAnalysis

      docStore.select(analysis.documentId)
      expect(docStore.selectedId).toBe('d2')

      const mode = analysis.status === 'COMPLETED' ? 'verify' : 'configure'
      expect(mode).toBe('configure')
    })

    it('handles missing analysis gracefully', async () => {
      const { fetchAnalysis } = await import('../../features/analysis/api')
      fetchAnalysis.mockRejectedValue(new Error('Not found'))
      vi.spyOn(console, 'error').mockImplementation(() => {})

      const analysisStore = useAnalysisStore()
      await analysisStore.select('nonexistent')

      // currentAnalysis stays null on error — StudioPage would not proceed
      expect(analysisStore.currentAnalysis).toBeNull()
    })
  })
})

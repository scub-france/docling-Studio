// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisDetailPage from './AnalysisDetailPage.vue'
import { fetchAnalysis, fetchAnalysisSummaries } from '../features/analysis/api'
import { fetchDocumentPages } from '../features/document/api'
import { useFeatureFlagStore } from '../features/feature-flags/store'

vi.mock('../features/analysis/api', () => ({
  fetchAnalysis: vi.fn(),
  fetchAnalysisSummaries: vi.fn(),
}))
vi.mock('../features/document/api', () => ({ fetchDocumentPages: vi.fn() }))
vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  onBeforeRouteLeave: vi.fn(),
}))

describe('AnalysisDetailPage analysis editor flag', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(fetchAnalysisSummaries).mockResolvedValue([])
    vi.mocked(fetchDocumentPages).mockResolvedValue([])
    vi.mocked(fetchAnalysis).mockResolvedValue({
      id: 'analysis-1',
      documentId: 'doc-1',
      documentFilename: 'fixture.pdf',
      status: 'COMPLETED',
      hasDocumentJson: true,
      createdAt: '2025-01-01T00:00:00Z',
    } as never)
  })

  async function render(): Promise<ReturnType<typeof mount>> {
    const wrapper = mount(AnalysisDetailPage, {
      props: { id: 'analysis-1' },
      global: { stubs: ['AnalysisEditor', 'DocParseTab', 'DownloadDropdown'] },
    })
    await flushPromises()
    return wrapper
  }

  it('hides editor action and editor when the flag is disabled', async () => {
    const flags = useFeatureFlagStore()
    flags.loaded = true
    flags.analysisEditorEnabled = false

    const wrapper = await render()
    expect(wrapper.find('[data-e2e="analysis-edit-toggle"]').exists()).toBe(false)
    expect(wrapper.find('[data-e2e="analysis-inspect-toggle"]').exists()).toBe(false)
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the editor action and opens editor when enabled', async () => {
    const flags = useFeatureFlagStore()
    flags.loaded = true
    flags.analysisEditorEnabled = true

    const wrapper = await render()
    expect(wrapper.get('download-dropdown-stub').attributes('edited')).toBe('false')
    await wrapper.get('[data-e2e="analysis-edit-toggle"]').trigger('click')
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(true)
    expect(wrapper.get('download-dropdown-stub').attributes('edited')).toBe('true')
    flags.analysisEditorEnabled = false
    await flushPromises()
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(false)
    wrapper.unmount()
  })

  it('mounts sized PDF pages before the full Docling analysis resolves', async () => {
    const flags = useFeatureFlagStore()
    flags.loaded = true
    flags.analysisEditorEnabled = true
    let resolveAnalysis!: (value: Awaited<ReturnType<typeof fetchAnalysis>>) => void
    vi.mocked(fetchAnalysis).mockReturnValue(
      new Promise((resolve) => {
        resolveAnalysis = resolve
      }),
    )
    vi.mocked(fetchAnalysisSummaries).mockResolvedValue([
      {
        id: 'analysis-1',
        documentId: 'doc-1',
        documentFilename: 'fixture.pdf',
        status: 'COMPLETED',
        createdAt: '2025-01-01T00:00:00Z',
      } as never,
    ])
    vi.mocked(fetchDocumentPages).mockResolvedValue([
      {
        page_number: 1,
        width: 612,
        height: 792,
        elements: [],
      },
    ])

    const wrapper = mount(AnalysisDetailPage, {
      props: { id: 'analysis-1' },
      global: { stubs: ['AnalysisEditor', 'DocParseTab', 'DownloadDropdown'] },
    })
    await flushPromises()
    const parse = wrapper.findComponent({ name: 'DocParseTab' })
    expect((parse.props('analysis') as { pagesJson: string }).pagesJson).toContain('page_number')
    resolveAnalysis({
      id: 'analysis-1',
      documentId: 'doc-1',
      documentFilename: 'fixture.pdf',
      status: 'COMPLETED',
      hasDocumentJson: true,
      createdAt: '2025-01-01T00:00:00Z',
      pagesJson: '[{"page_number":1,"width":612,"height":792,"elements":[]}]',
    } as never)
    await flushPromises()
    expect(wrapper.get('[data-e2e="analysis-edit-toggle"]').attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })

  it('shows an error when the full analysis fails after the page manifest loads', async () => {
    vi.mocked(fetchAnalysisSummaries).mockResolvedValue([
      {
        id: 'analysis-1',
        documentId: 'doc-1',
        documentFilename: 'fixture.pdf',
        status: 'COMPLETED',
        createdAt: '2025-01-01T00:00:00Z',
      } as never,
    ])
    vi.mocked(fetchDocumentPages).mockResolvedValue([
      { page_number: 1, width: 612, height: 792, elements: [] },
    ])
    vi.mocked(fetchAnalysis).mockRejectedValue(new Error('failed'))

    const wrapper = await render()
    expect(wrapper.find('.state--error').exists()).toBe(true)
    expect(wrapper.find('doc-parse-tab-stub').exists()).toBe(false)
    wrapper.unmount()
  })
  it('opens the full analysis when the summary list cannot be loaded', async () => {
    vi.mocked(fetchAnalysisSummaries).mockRejectedValue(new Error('offline'))

    const wrapper = await render()
    expect(wrapper.find('.state--error').exists()).toBe(false)
    expect(wrapper.find('doc-parse-tab-stub').exists()).toBe(true)
    expect(fetchDocumentPages).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('opens the full analysis when the page manifest cannot be loaded', async () => {
    vi.mocked(fetchAnalysisSummaries).mockResolvedValue([
      { id: 'analysis-1', documentId: 'doc-1', status: 'COMPLETED' } as never,
    ])
    vi.mocked(fetchDocumentPages).mockRejectedValue(new Error('missing'))

    const wrapper = await render()
    expect(wrapper.find('doc-parse-tab-stub').exists()).toBe(true)
    expect(fetchAnalysis).toHaveBeenCalledWith('analysis-1')
    wrapper.unmount()
  })

  it('shows an error when the analysis is neither summarised nor loadable', async () => {
    vi.mocked(fetchAnalysis).mockRejectedValue(new Error('not found'))

    const wrapper = await render()
    expect(wrapper.find('.state--error').exists()).toBe(true)
    expect(fetchDocumentPages).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})

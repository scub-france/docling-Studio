// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisDetailPage from './AnalysisDetailPage.vue'
import { fetchAnalysis } from '../features/analysis/api'
import { useFeatureFlagStore } from '../features/feature-flags/store'

vi.mock('../features/analysis/api', () => ({ fetchAnalysis: vi.fn() }))
vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  onBeforeRouteLeave: vi.fn(),
}))

describe('AnalysisDetailPage analysis editor flag', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the editor action and opens editor when enabled', async () => {
    const flags = useFeatureFlagStore()
    flags.loaded = true
    flags.analysisEditorEnabled = true

    const wrapper = await render()
    await wrapper.get('[data-e2e="analysis-edit-toggle"]').trigger('click')
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(true)
    flags.analysisEditorEnabled = false
    await flushPromises()
    expect(wrapper.find('analysis-editor-stub').exists()).toBe(false)
    wrapper.unmount()
  })
})

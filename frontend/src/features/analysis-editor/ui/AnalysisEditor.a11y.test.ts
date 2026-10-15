// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import axe from 'axe-core'
import AnalysisEditor from './AnalysisEditor.vue'
import { fetchAnalysisEditHistory, fetchAnalysisEditor } from '../api'

vi.mock('../api', () => ({
  fetchAnalysisEditor: vi.fn(),
  fetchAnalysisEditHistory: vi.fn(),
  previewAnalysisEdits: vi.fn(),
  saveAnalysisEdits: vi.fn(),
}))
vi.mock('vue-router', () => ({ onBeforeRouteLeave: vi.fn() }))

const editorResponse = {
  model: {
    baseAnalysisId: 'analysis-1',
    elements: [
      {
        id: 'analysis-1:#/texts/0',
        selfRef: '#/texts/0',
        parentId: null,
        type: 'text',
        text: 'Accessible paragraph',
        headingLevel: null,
        children: [],
        provenance: [],
        editable: true,
        supportedOperations: ['replaceText', 'mergeText', 'moveElement', 'deleteElement'],
        nonEditableReason: null,
      },
    ],
  },
  tree: [
    {
      elementId: 'analysis-1:#/texts/0',
      type: 'text',
      label: 'Accessible paragraph',
      children: [],
    },
  ],
  result: { contentMarkdown: 'Accessible paragraph', pagesJson: '[]' },
  appliedThroughSequence: 0,
  chunksStale: false,
  warnings: [],
  referenceChanges: {},
}

describe('AnalysisEditor accessibility', () => {
  afterEach(() => vi.clearAllMocks())

  it('has no detectable Axe violations in its core editor controls', async () => {
    vi.mocked(fetchAnalysisEditor).mockResolvedValue(editorResponse as never)
    vi.mocked(fetchAnalysisEditHistory).mockResolvedValue([])
    const wrapper = mount(AnalysisEditor, {
      props: { documentId: 'doc-1', analysisId: 'analysis-1' },
      global: {
        plugins: [createPinia()],
        stubs: { PagePreviewWithOverlay: true },
      },
      attachTo: document.body,
    })

    await flushPromises()
    const results = await axe.run(wrapper.element, {
      rules: { 'color-contrast': { enabled: false } },
    })

    expect(results.violations).toEqual([])
    wrapper.unmount()
  })
})

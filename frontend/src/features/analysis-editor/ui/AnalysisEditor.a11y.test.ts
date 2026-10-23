// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import axe from 'axe-core'
import AnalysisEditor from './AnalysisEditor.vue'
import { fetchAnalysisEditHistory, fetchAnalysisEditor } from '../api'
import { useAnalysisEditorStore } from '../store'

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

  it('adds and toggles paragraphs with Cmd/Ctrl-click in the reading order tree', async () => {
    const second = {
      ...editorResponse.model.elements[0],
      id: 'analysis-1:#/texts/1',
      selfRef: '#/texts/1',
      text: 'Second paragraph',
    }
    vi.mocked(fetchAnalysisEditor).mockResolvedValue({
      ...editorResponse,
      model: { ...editorResponse.model, elements: [...editorResponse.model.elements, second] },
      tree: [
        ...editorResponse.tree,
        { elementId: second.id, type: 'text', label: second.text, children: [] },
      ],
    } as never)
    vi.mocked(fetchAnalysisEditHistory).mockResolvedValue([])
    const pinia = createPinia()
    const wrapper = mount(AnalysisEditor, {
      props: { documentId: 'doc-1', analysisId: 'analysis-1' },
      global: { plugins: [pinia], stubs: { PagePreviewWithOverlay: true } },
    })
    await flushPromises()
    const store = useAnalysisEditorStore(pinia)
    const rows = wrapper.findAll('[role="treeitem"]')

    await rows[0].trigger('click')
    await rows[1].trigger('click', { metaKey: true })
    expect(store.mergeSelection).toEqual([editorResponse.model.elements[0].id, second.id])
    await rows[1].trigger('click', { ctrlKey: true })
    expect(store.mergeSelection).toEqual([editorResponse.model.elements[0].id])
    wrapper.unmount()
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAnalysisEditorStore } from './store'
import {
  fetchAnalysisEditHistory,
  fetchAnalysisEditor,
  previewAnalysisEdits,
  saveAnalysisEdits,
} from './api'

vi.mock('./api', () => ({
  fetchAnalysisEditor: vi.fn(),
  fetchAnalysisEditHistory: vi.fn(),
  previewAnalysisEdits: vi.fn(),
  saveAnalysisEdits: vi.fn(),
}))

describe('analysis editor selection state', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('keeps focus on a moved element', () => {
    const store = useAnalysisEditorStore()

    store.moveElement('moved', 'target', 'after')

    expect(store.selectedElementId).toBe('moved')
    expect(store.hasUnsavedChanges).toBe(true)
    store.discard()
  })

  it('clears focus when a selected element is deleted as part of a range', () => {
    const store = useAnalysisEditorStore()
    store.selectedElementId = 'selected'
    store.mergeSelection = ['selected', 'other']

    store.queueDeleteElements(store.mergeSelection)

    expect(store.selectedElementId).toBeNull()
    expect(store.mergeSelection).toEqual([])
    expect(store.hasUnsavedChanges).toBe(true)
    store.discard()
  })

  it('persists pending commands with their saved sequence and clears them on discard', () => {
    const values = new Map<string, string>()
    vi.stubGlobal('window', {
      sessionStorage: {
        setItem: (key: string, value: string) => values.set(key, value),
        getItem: (key: string) => values.get(key) ?? null,
        removeItem: (key: string) => values.delete(key),
      },
    })
    const store = useAnalysisEditorStore()
    store.documentId = 'doc-1'
    store.baseAnalysisId = 'analysis-1'
    store.saved = { appliedThroughSequence: 3 } as never

    store.moveElement('moved', 'target', 'after')

    expect(JSON.parse(values.get('analysis-editor-pending:doc-1:analysis-1') ?? '')).toEqual({
      expectedAppliedThroughSequence: 3,
      commands: [
        { type: 'moveElement', elementId: 'moved', targetElementId: 'target', placement: 'after' },
      ],
    })
    store.discard()
    expect(values.has('analysis-editor-pending:doc-1:analysis-1')).toBe(false)
  })

  it('offers recovery only when the saved sequence still matches', async () => {
    const values = new Map<string, string>([
      [
        'analysis-editor-pending:doc-1:analysis-1',
        JSON.stringify({
          expectedAppliedThroughSequence: 3,
          commands: [{ type: 'deleteElement', elementId: 'element-1' }],
        }),
      ],
    ])
    vi.stubGlobal('window', {
      sessionStorage: {
        setItem: (key: string, value: string) => values.set(key, value),
        getItem: (key: string) => values.get(key) ?? null,
        removeItem: (key: string) => values.delete(key),
      },
    })
    vi.mocked(fetchAnalysisEditor).mockResolvedValue({
      model: { baseAnalysisId: 'analysis-1', elements: [] },
      tree: [],
      result: {},
      appliedThroughSequence: 3,
    } as never)
    vi.mocked(fetchAnalysisEditHistory).mockResolvedValue([])
    const store = useAnalysisEditorStore()

    await store.load('doc-1')

    expect(store.recoveredPendingCount).toBe(1)
    expect(store.hasUnsavedChanges).toBe(false)
    store.restoreRecoveredPending()
    expect(store.hasUnsavedChanges).toBe(true)
  })

  it('discards a recovered draft when the saved sequence changed', async () => {
    const values = new Map<string, string>([
      [
        'analysis-editor-pending:doc-1:analysis-1',
        JSON.stringify({
          expectedAppliedThroughSequence: 2,
          commands: [{ type: 'deleteElement', elementId: 'element-1' }],
        }),
      ],
    ])
    vi.stubGlobal('window', {
      sessionStorage: {
        setItem: (key: string, value: string) => values.set(key, value),
        getItem: (key: string) => values.get(key) ?? null,
        removeItem: (key: string) => values.delete(key),
      },
    })
    vi.mocked(fetchAnalysisEditor).mockResolvedValue({
      model: { baseAnalysisId: 'analysis-1', elements: [] },
      tree: [],
      result: {},
      appliedThroughSequence: 3,
    } as never)
    vi.mocked(fetchAnalysisEditHistory).mockResolvedValue([])
    const store = useAnalysisEditorStore()

    await store.load('doc-1')

    expect(store.recoveredPendingCount).toBe(0)
    expect(values.has('analysis-editor-pending:doc-1:analysis-1')).toBe(false)
  })

  it('preserves pending edits and exposes a conflict when save returns 409', async () => {
    const store = useAnalysisEditorStore()
    store.documentId = 'doc-1'
    store.baseAnalysisId = 'analysis-1'
    store.saved = { appliedThroughSequence: 3 } as never
    store.moveElement('moved', 'target', 'after')
    vi.mocked(saveAnalysisEdits).mockRejectedValue(new Error('409: The editor stream changed'))

    await store.save()

    expect(store.conflict).toContain('409:')
    expect(store.error).toBeNull()
    expect(store.hasUnsavedChanges).toBe(true)
    expect(store.conflictDetails).toContain('moveElement')
    store.discard()
  })

  it('ignores an in-flight preview after discarding edits', async () => {
    let resolvePreview!: (value: never) => void
    vi.mocked(previewAnalysisEdits).mockImplementation(
      () => new Promise((resolve) => (resolvePreview = resolve)),
    )
    const store = useAnalysisEditorStore()
    store.documentId = 'doc-1'
    store.baseAnalysisId = 'analysis-1'
    store.saved = { appliedThroughSequence: 0 } as never
    store.queueReplaceText('element-1', 'Pending')
    const request = store.previewNow()

    store.discard()
    resolvePreview({ result: { contentMarkdown: 'Pending' } } as never)
    await request

    expect(store.preview).toBeNull()
    expect(store.effective).toBe(store.saved)
    expect(store.previewing).toBe(false)
  })
})

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from './api'
import { canMerge, coalesceCommands } from './commands'
import type {
  AnalysisEditCommand,
  AnalysisEditHistoryEntry,
  AnalysisEditorResponse,
  EditorElement,
  EditorTreeNode,
} from './types'
import { pagesFromAnalysis } from './types'

export const useAnalysisEditorStore = defineStore('analysis-editor', () => {
  const documentId = ref<string | null>(null)
  const baseAnalysisId = ref<string | null>(null)
  const saved = ref<AnalysisEditorResponse | null>(null)
  const history = ref<AnalysisEditHistoryEntry[]>([])
  const preview = ref<AnalysisEditorResponse | null>(null)
  const pendingCommands = ref<AnalysisEditCommand[]>([])
  const selectedElementId = ref<string | null>(null)
  const mergeSelection = ref<string[]>([])
  const loading = ref(false)
  const previewing = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const previewError = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)
  let previewTimer: ReturnType<typeof setTimeout> | null = null

  const effective = computed(() => preview.value ?? saved.value)
  const elements = computed(() => effective.value?.model.elements ?? [])
  const tree = computed<EditorTreeNode[]>(() => effective.value?.tree ?? [])
  const pages = computed(() => pagesFromAnalysis(effective.value?.result ?? null))
  const selectedElement = computed<EditorElement | null>(
    () => elements.value.find((element) => element.id === selectedElementId.value) ?? null,
  )
  const hasUnsavedChanges = computed(() => pendingCommands.value.length > 0)
  const mergeAllowed = computed(() => canMerge(elements.value, mergeSelection.value))

  async function load(id: string, analysisId?: string): Promise<void> {
    documentId.value = id
    baseAnalysisId.value = analysisId ?? null
    loading.value = true
    error.value = null
    try {
      saved.value = await api.fetchAnalysisEditor(id, undefined, analysisId)
      baseAnalysisId.value = saved.value.model.baseAnalysisId
      history.value = await api.fetchAnalysisEditHistory(id, baseAnalysisId.value)
      preview.value = null
      pendingCommands.value = []
      mergeSelection.value = []
      selectedElementId.value = saved.value.model.elements.find((element) => element.editable)?.id ?? null
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load analysis editor'
    } finally {
      loading.value = false
    }
  }

  function queue(command: AnalysisEditCommand): void {
    pendingCommands.value = coalesceCommands([...pendingCommands.value, command])
    previewError.value = null
    if (previewTimer) clearTimeout(previewTimer)
    previewTimer = setTimeout(() => void previewNow(), 400)
  }

  function queueReplaceText(elementId: string, text: string): void {
    queue({ type: 'replaceText', elementId, text })
  }

  function queueHeadingLevel(elementId: string, level: number): void {
    queue({ type: 'setHeadingLevel', elementId, level })
  }

  function queueDelete(elementId: string): void {
    queue({ type: 'deleteElement', elementId })
  }

  function toggleMergeSelection(elementId: string): void {
    mergeSelection.value = mergeSelection.value.includes(elementId)
      ? mergeSelection.value.filter((id) => id !== elementId)
      : [...mergeSelection.value, elementId]
  }

  function toggleMergeSelectionMany(elementIds: string[]): void {
    if (!elementIds.length) return
    const allSelected = elementIds.every((id) => mergeSelection.value.includes(id))
    mergeSelection.value = allSelected
      ? mergeSelection.value.filter((id) => !elementIds.includes(id))
      : [...new Set([...mergeSelection.value, ...elementIds])]
  }

  function mergeSelected(separator = ' '): void {
    if (!mergeAllowed.value) return
    queue({ type: 'mergeText', elementIds: [...mergeSelection.value], separator })
    mergeSelection.value = [mergeSelection.value[0]]
  }

  function moveElement(elementId: string, beforeElementId: string | null): void {
    queue({ type: 'moveElement', elementId, beforeElementId })
  }

  async function previewNow(): Promise<void> {
    if (!documentId.value || !saved.value || pendingCommands.value.length === 0) return
    abortController.value?.abort()
    const controller = new AbortController()
    abortController.value = controller
    previewing.value = true
    previewError.value = null
    try {
      preview.value = await api.previewAnalysisEdits(
        documentId.value,
        {
          commands: pendingCommands.value,
          expectedAppliedThroughSequence: saved.value.appliedThroughSequence,
        },
        controller.signal,
        baseAnalysisId.value ?? undefined,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') previewError.value = (e as Error).message
    } finally {
      if (abortController.value === controller) previewing.value = false
    }
  }

  async function save(): Promise<void> {
    if (!documentId.value || !saved.value || pendingCommands.value.length === 0) return
    saving.value = true
    if (previewTimer) clearTimeout(previewTimer)
    error.value = null
    try {
      await api.saveAnalysisEdits(documentId.value, {
        commands: pendingCommands.value,
        expectedAppliedThroughSequence: saved.value.appliedThroughSequence,
      }, baseAnalysisId.value ?? undefined)
      const next = await api.fetchAnalysisEditor(
        documentId.value,
        undefined,
        baseAnalysisId.value ?? undefined,
      )
      saved.value = next
      history.value = await api.fetchAnalysisEditHistory(
        documentId.value,
        baseAnalysisId.value ?? undefined,
      )
      preview.value = null
      pendingCommands.value = []
      mergeSelection.value = []
    } catch (e) {
      error.value = (e as Error).message || 'Failed to save analysis edits'
    } finally {
      saving.value = false
    }
  }

  function discard(): void {
    if (previewTimer) clearTimeout(previewTimer)
    pendingCommands.value = []
    preview.value = null
    mergeSelection.value = []
  }

  return {
    documentId,
    baseAnalysisId,
    saved,
    history,
    preview,
    effective,
    elements,
    tree,
    pages,
    selectedElement,
    selectedElementId,
    mergeSelection,
    mergeAllowed,
    hasUnsavedChanges,
    loading,
    previewing,
    saving,
    error,
    previewError,
    load,
    queueReplaceText,
    queueHeadingLevel,
    queueDelete,
    toggleMergeSelection,
    toggleMergeSelectionMany,
    mergeSelected,
    moveElement,
    previewNow,
    save,
    discard,
  }
})

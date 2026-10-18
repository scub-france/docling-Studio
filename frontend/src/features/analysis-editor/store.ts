import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from './api'
import { canMerge, coalesceCommands, mergeValidationMessage } from './commands'
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
  const redoCommands = ref<AnalysisEditCommand[]>([])
  const recoveredPendingCommands = ref<AnalysisEditCommand[] | null>(null)
  const selectedElementId = ref<string | null>(null)
  const mergeSelection = ref<string[]>([])
  const loading = ref(false)
  const previewing = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const conflict = ref<string | null>(null)
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
  const recoveredPendingCount = computed(() => recoveredPendingCommands.value?.length ?? 0)
  const conflictDetails = computed(() => JSON.stringify(pendingCommands.value, null, 2))
  const canUndo = computed(() => pendingCommands.value.length > 0)
  const canRedo = computed(() => redoCommands.value.length > 0)
  const mergeAllowed = computed(() => canMerge(elements.value, mergeSelection.value))
  const mergeValidationError = computed(() =>
    mergeValidationMessage(elements.value, mergeSelection.value),
  )

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
      redoCommands.value = []
      mergeSelection.value = []
      recoveredPendingCommands.value = readRecoveredPendingCommands()
      conflict.value = null
      selectedElementId.value =
        saved.value.model.elements.find((element) => element.editable)?.id ?? null
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load analysis editor'
    } finally {
      loading.value = false
    }
  }

  function queue(command: AnalysisEditCommand): void {
    pendingCommands.value = coalesceCommands([...pendingCommands.value, command])
    redoCommands.value = []
    conflict.value = null
    persistPendingCommands()
    previewError.value = null
    if (previewTimer) clearTimeout(previewTimer)
    previewTimer = setTimeout(() => void previewNow(), 400)
  }

  function refreshPreview(): void {
    abortController.value?.abort()
    preview.value = null
    previewError.value = null
    if (previewTimer) clearTimeout(previewTimer)
    if (pendingCommands.value.length) void previewNow()
  }

  function undo(): void {
    const command = pendingCommands.value.at(-1)
    if (!command) return
    pendingCommands.value = pendingCommands.value.slice(0, -1)
    redoCommands.value = [command, ...redoCommands.value]
    persistPendingCommands()
    refreshPreview()
  }

  function redo(): void {
    const command = redoCommands.value[0]
    if (!command) return
    redoCommands.value = redoCommands.value.slice(1)
    pendingCommands.value = coalesceCommands([...pendingCommands.value, command])
    persistPendingCommands()
    refreshPreview()
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

  function queueDeleteElements(elementIds: string[]): void {
    if (!elementIds.length) return
    queue({ type: 'deleteElements', elementIds })
    if (selectedElementId.value && elementIds.includes(selectedElementId.value))
      selectedElementId.value = null
    mergeSelection.value = []
  }

  function toggleMergeSelection(elementId: string): void {
    mergeSelection.value = mergeSelection.value.includes(elementId)
      ? mergeSelection.value.filter((id) => id !== elementId)
      : [...mergeSelection.value, elementId]
  }

  function selectMergeSelection(elementId: string): void {
    mergeSelection.value = [elementId]
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
    const targetId = mergeSelection.value[0]
    queue({ type: 'mergeText', elementIds: [...mergeSelection.value], separator })
    selectedElementId.value = targetId
    mergeSelection.value = [targetId]
  }

  function moveElement(
    elementId: string,
    targetElementId: string,
    placement: 'before' | 'after' | 'inside',
  ): void {
    queue({ type: 'moveElement', elementId, targetElementId, placement })
    selectedElementId.value = elementId
  }

  async function previewNow(): Promise<void> {
    if (!documentId.value || !saved.value || pendingCommands.value.length === 0) return
    abortController.value?.abort()
    const controller = new AbortController()
    abortController.value = controller
    previewing.value = true
    previewError.value = null
    try {
      const result = await api.previewAnalysisEdits(
        documentId.value,
        {
          commands: pendingCommands.value,
          expectedAppliedThroughSequence: saved.value.appliedThroughSequence,
        },
        controller.signal,
        baseAnalysisId.value ?? undefined,
      )
      if (abortController.value === controller && !controller.signal.aborted) preview.value = result
    } catch (e) {
      if (abortController.value === controller && (e as Error).name !== 'AbortError')
        previewError.value = (e as Error).message
    } finally {
      if (abortController.value === controller) previewing.value = false
    }
  }

  async function save(): Promise<void> {
    if (!documentId.value || !saved.value || pendingCommands.value.length === 0) return
    saving.value = true
    if (previewTimer) clearTimeout(previewTimer)
    error.value = null
    conflict.value = null
    try {
      await api.saveAnalysisEdits(
        documentId.value,
        {
          commands: pendingCommands.value,
          expectedAppliedThroughSequence: saved.value.appliedThroughSequence,
        },
        baseAnalysisId.value ?? undefined,
      )
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
      redoCommands.value = []
      mergeSelection.value = []
      persistPendingCommands()
    } catch (e) {
      const message = (e as Error).message || 'Failed to save analysis edits'
      if (message.startsWith('409:')) conflict.value = message
      else error.value = message
    } finally {
      saving.value = false
    }
  }

  function discard(): void {
    if (previewTimer) clearTimeout(previewTimer)
    abortController.value?.abort()
    abortController.value = null
    previewing.value = false
    previewError.value = null
    pendingCommands.value = []
    redoCommands.value = []
    preview.value = null
    mergeSelection.value = []
    recoveredPendingCommands.value = null
    persistPendingCommands()
  }

  function restoreRecoveredPending(): void {
    if (!recoveredPendingCommands.value) return
    pendingCommands.value = recoveredPendingCommands.value
    recoveredPendingCommands.value = null
    persistPendingCommands()
    refreshPreview()
  }

  function discardRecoveredPending(): void {
    recoveredPendingCommands.value = null
    persistPendingCommands()
  }

  async function reloadAfterConflict(): Promise<void> {
    if (!documentId.value) return
    await load(documentId.value, baseAnalysisId.value ?? undefined)
  }

  function discardConflict(): void {
    conflict.value = null
    discard()
  }

  function pendingStorageKey(): string | null {
    if (!documentId.value || !baseAnalysisId.value) return null
    return `analysis-editor-pending:${documentId.value}:${baseAnalysisId.value}`
  }

  function persistPendingCommands(): void {
    const key = pendingStorageKey()
    if (!key) return
    try {
      if (!pendingCommands.value.length) {
        window.sessionStorage.removeItem(key)
        return
      }
      window.sessionStorage.setItem(
        key,
        JSON.stringify({
          expectedAppliedThroughSequence: saved.value?.appliedThroughSequence ?? 0,
          commands: pendingCommands.value,
        }),
      )
    } catch {
      // Browser storage can be unavailable in private or restricted contexts.
    }
  }

  function readRecoveredPendingCommands(): AnalysisEditCommand[] | null {
    const key = pendingStorageKey()
    if (!key) return null
    try {
      const value = window.sessionStorage.getItem(key)
      if (!value) return null
      const draft = JSON.parse(value) as {
        expectedAppliedThroughSequence?: unknown
        commands?: unknown
      }
      if (
        draft.expectedAppliedThroughSequence === saved.value?.appliedThroughSequence &&
        Array.isArray(draft.commands) &&
        draft.commands.length
      ) {
        return draft.commands as AnalysisEditCommand[]
      }
      window.sessionStorage.removeItem(key)
    } catch {
      // Ignore malformed and unavailable browser storage.
    }
    return null
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
    mergeValidationError,
    hasUnsavedChanges,
    recoveredPendingCount,
    canUndo,
    canRedo,
    loading,
    previewing,
    saving,
    error,
    conflict,
    conflictDetails,
    previewError,
    load,
    queueReplaceText,
    queueHeadingLevel,
    queueDelete,
    queueDeleteElements,
    undo,
    redo,
    toggleMergeSelection,
    selectMergeSelection,
    toggleMergeSelectionMany,
    mergeSelected,
    moveElement,
    previewNow,
    save,
    discard,
    restoreRecoveredPending,
    discardRecoveredPending,
    reloadAfterConflict,
    discardConflict,
  }
})

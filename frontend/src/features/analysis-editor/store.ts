import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from './api'
import {
  findSavedRedoTarget,
  findSavedUndoTarget,
  queueCommand,
  redoPending,
  undoPending,
  type CommandStacks,
} from './commandStacks'
import { canMerge, sortInReadingOrder, validateMerge } from './commands'
import { toggleSelectedId, toggleSelectedIds } from './mergeSelection'
import { buildPendingDraftKey, readPendingDraft, writePendingDraft } from './pendingDraft'
import { createPreviewScheduler } from './previewScheduler'
import type {
  AnalysisEditCommand,
  AnalysisEditHistoryEntry,
  AnalysisEditorResponse,
  EditorElement,
  EditorTreeNode,
} from './types'
import { parseAnalysisPages } from './types'

const PREVIEW_DEBOUNCE_MS = 400

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
  /** A save the server refused (not a 409): the pending edits stay on screen. */
  const saveError = ref<string | null>(null)
  const historyError = ref<string | null>(null)
  const previewScheduler = createPreviewScheduler(PREVIEW_DEBOUNCE_MS)

  const effective = computed(() => preview.value ?? saved.value)
  const elements = computed(() => effective.value?.model.elements ?? [])
  const tree = computed<EditorTreeNode[]>(() => effective.value?.tree ?? [])
  const pages = computed(() => parseAnalysisPages(effective.value?.result ?? null))
  const selectedElement = computed<EditorElement | null>(
    () => elements.value.find((element) => element.id === selectedElementId.value) ?? null,
  )
  const hasUnsavedChanges = computed(() => pendingCommands.value.length > 0)
  const recoveredPendingCount = computed(() => recoveredPendingCommands.value?.length ?? 0)
  const conflictDetails = computed(() => JSON.stringify(pendingCommands.value, null, 2))
  const savedUndoTarget = computed(() => findSavedUndoTarget(history.value))
  const savedRedoTarget = computed(() => findSavedRedoTarget(history.value))
  const canChangeSavedHistory = computed(
    () =>
      !saving.value &&
      !loading.value &&
      !pendingCommands.value.length &&
      !redoCommands.value.length &&
      !recoveredPendingCommands.value?.length,
  )
  const canUndo = computed(
    () =>
      !saving.value &&
      (pendingCommands.value.length > 0 ||
        (canChangeSavedHistory.value && !!savedUndoTarget.value)),
  )
  const canRedo = computed(
    () =>
      !saving.value &&
      (redoCommands.value.length > 0 || (canChangeSavedHistory.value && !!savedRedoTarget.value)),
  )
  const mergeAllowed = computed(() => canMerge(elements.value, mergeSelection.value))
  const mergeValidationKey = computed(() => validateMerge(elements.value, mergeSelection.value))

  async function load(id: string, analysisId?: string): Promise<void> {
    documentId.value = id
    baseAnalysisId.value = analysisId ?? null
    loading.value = true
    error.value = null
    historyError.value = null
    saveError.value = null
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
    if (saving.value) return
    setCommandStacks(queueCommand(pendingCommands.value, command))
    conflict.value = null
    persistPendingCommands()
    previewError.value = null
    previewScheduler.debounce(() => void previewNow())
  }

  function refreshPreview(): void {
    previewScheduler.abort()
    preview.value = null
    previewError.value = null
    previewScheduler.clearDebounce()
    if (pendingCommands.value.length) void previewNow()
  }

  function setCommandStacks(stacks: CommandStacks): void {
    pendingCommands.value = stacks.pending
    redoCommands.value = stacks.redo
    saveError.value = null
  }

  async function undo(): Promise<void> {
    if (saving.value) return
    const stacks = undoPending({ pending: pendingCommands.value, redo: redoCommands.value })
    if (!stacks) {
      if (canChangeSavedHistory.value && savedUndoTarget.value)
        await setSavedCommandActive(savedUndoTarget.value.sequence, false)
      return
    }
    setCommandStacks(stacks)
    persistPendingCommands()
    refreshPreview()
  }

  async function redo(): Promise<void> {
    if (saving.value) return
    const stacks = redoPending({ pending: pendingCommands.value, redo: redoCommands.value })
    if (!stacks) {
      if (canChangeSavedHistory.value && savedRedoTarget.value)
        await setSavedCommandActive(savedRedoTarget.value.sequence, true)
      return
    }
    setCommandStacks(stacks)
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
    mergeSelection.value = toggleSelectedId(mergeSelection.value, elementId)
  }

  function selectMergeSelection(elementId: string): void {
    mergeSelection.value = [elementId]
  }

  function toggleMergeSelectionMany(elementIds: string[]): void {
    mergeSelection.value = toggleSelectedIds(mergeSelection.value, elementIds)
  }

  function mergeSelected(separator = ' '): void {
    if (!mergeAllowed.value) return
    const elementIds = sortInReadingOrder(
      mergeSelection.value,
      effective.value?.readingOrder ?? elements.value.map((element) => element.id),
    )
    const targetId = elementIds[0]
    queue({ type: 'mergeText', elementIds, separator })
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
    const controller = previewScheduler.begin()
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
      if (previewScheduler.isCurrent(controller) && !controller.signal.aborted)
        preview.value = result
    } catch (e) {
      if (previewScheduler.isCurrent(controller) && (e as Error).name !== 'AbortError')
        previewError.value = (e as Error).message
    } finally {
      if (previewScheduler.isCurrent(controller)) previewing.value = false
    }
  }

  async function save(): Promise<void> {
    if (!documentId.value || !saved.value || pendingCommands.value.length === 0) return
    saving.value = true
    previewScheduler.clearDebounce()
    saveError.value = null
    historyError.value = null
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
      else saveError.value = message
    } finally {
      saving.value = false
    }
  }

  async function setSavedCommandActive(sequence: number, active: boolean): Promise<void> {
    if (!documentId.value || !saved.value || !canChangeSavedHistory.value) return
    saving.value = true
    historyError.value = null
    conflict.value = null
    previewScheduler.abort()
    preview.value = null
    try {
      const next = await api.setAnalysisEditActive(
        documentId.value,
        { sequence, active, expectedAppliedThroughSequence: saved.value.appliedThroughSequence },
        baseAnalysisId.value ?? undefined,
      )
      saved.value = next
      history.value = await api.fetchAnalysisEditHistory(
        documentId.value,
        baseAnalysisId.value ?? undefined,
      )
      mergeSelection.value = []
      if (!next.model.elements.some((element) => element.id === selectedElementId.value)) {
        selectedElementId.value =
          next.model.elements.find((element) => element.editable)?.id ?? null
      }
    } catch (e) {
      const message = (e as Error).message || 'Failed to change saved edit history'
      if (message.startsWith('409:')) conflict.value = message
      else historyError.value = message
    } finally {
      saving.value = false
    }
  }

  /** Stop the debounced and in-flight preview, e.g. when the editor closes. */
  function cancelPreview(): void {
    previewScheduler.cancel()
    previewing.value = false
  }

  function discard(): void {
    cancelPreview()
    previewError.value = null
    saveError.value = null
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

  function persistPendingCommands(): void {
    const key = buildPendingDraftKey(documentId.value, baseAnalysisId.value)
    if (!key) return
    writePendingDraft(key, {
      expectedAppliedThroughSequence: saved.value?.appliedThroughSequence ?? 0,
      commands: pendingCommands.value,
    })
  }

  function readRecoveredPendingCommands(): AnalysisEditCommand[] | null {
    const key = buildPendingDraftKey(documentId.value, baseAnalysisId.value)
    if (!key) return null
    return readPendingDraft(key, saved.value?.appliedThroughSequence)
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
    mergeValidationKey,
    hasUnsavedChanges,
    recoveredPendingCount,
    canUndo,
    canRedo,
    canChangeSavedHistory,
    loading,
    previewing,
    saving,
    error,
    conflict,
    conflictDetails,
    previewError,
    saveError,
    historyError,
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
    setSavedCommandActive,
    cancelPreview,
    discard,
    restoreRecoveredPending,
    discardRecoveredPending,
    reloadAfterConflict,
    discardConflict,
  }
})

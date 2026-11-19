<template>
  <section class="analysis-editor" data-e2e="parse-tab" data-editor="analysis-editor">
    <header class="editor-toolbar">
      <div class="toolbar-title">
        <span class="eyebrow">{{ t('analysisEditor.title') }}</span>
        <span v-if="store.hasUnsavedChanges" class="unsaved" data-e2e="analysis-editor-unsaved">{{
          t('analysisEditor.unsaved')
        }}</span>
        <span
          class="selection-status"
          data-e2e="analysis-editor-selection-count"
          aria-live="polite"
        >
          {{ t('analysisEditor.selectedCount', { n: selectionCount }) }}
        </span>
      </div>
      <div class="toolbar-actions">
        <button
          type="button"
          data-e2e="analysis-editor-undo"
          :disabled="!store.canUndo"
          :title="t('analysisEditor.undoHint')"
          @click="store.undo()"
        >
          {{ t('analysisEditor.undo') }}
        </button>
        <button
          type="button"
          data-e2e="analysis-editor-redo"
          :disabled="!store.canRedo"
          :title="t('analysisEditor.redoHint')"
          @click="store.redo()"
        >
          {{ t('analysisEditor.redo') }}
        </button>
        <button
          type="button"
          class="history-button"
          data-e2e="analysis-editor-history"
          :class="{ active: historyOpen }"
          @click="historyOpen = !historyOpen"
        >
          {{ t('analysisEditor.history', { n: store.history.length }) }}
        </button>
        <button
          v-if="store.mergeSelection.length"
          data-e2e="analysis-editor-merge"
          type="button"
          class="merge-toolbar-button"
          :disabled="!store.mergeAllowed"
          :title="store.mergeValidationKey ? t(store.mergeValidationKey) : undefined"
          @click="store.mergeSelected()"
        >
          {{ t('analysisEditor.mergeSelected', { n: store.mergeSelection.length }) }}
        </button>
        <span v-if="store.mergeValidationKey" class="operation-feedback">{{
          t(store.mergeValidationKey)
        }}</span>
        <button
          v-if="store.mergeSelection.length > 1"
          data-e2e="analysis-editor-delete-range"
          type="button"
          class="delete-range-button"
          @click="store.queueDeleteElements(store.mergeSelection)"
        >
          {{ t('analysisEditor.deleteSelected', { n: store.mergeSelection.length }) }}
        </button>
        <button
          v-if="store.selectedElement && isMovable(store.selectedElement.id)"
          type="button"
          data-e2e="analysis-editor-choose-move"
          :aria-pressed="Boolean(draggedId)"
          @click="toggleMoveDestination"
        >
          {{
            draggedId ? t('analysisEditor.cancelMove') : t('analysisEditor.chooseMoveDestination')
          }}
        </button>
        <button
          type="button"
          :disabled="!store.hasUnsavedChanges || store.previewing"
          data-e2e="analysis-editor-preview"
          @click="store.previewNow()"
        >
          {{ store.previewing ? t('analysisEditor.previewing') : t('analysisEditor.preview') }}
        </button>
        <button
          data-e2e="analysis-editor-discard"
          type="button"
          :disabled="!store.hasUnsavedChanges"
          @click="discard"
        >
          {{ t('analysisEditor.discard') }}
        </button>
        <button
          type="button"
          class="primary"
          data-e2e="analysis-editor-save"
          :disabled="!store.hasUnsavedChanges || store.saving"
          @click="save"
        >
          {{ store.saving ? t('analysisEditor.saving') : t('analysisEditor.save') }}
        </button>
      </div>
    </header>
    <div v-if="store.loading" class="editor-loading-preview">
      <PagePreviewWithOverlay
        v-if="previewPages?.length"
        :document-id="documentId"
        :pages="previewPages"
        :current-page="currentPage"
        :hidden-types="new Set<string>()"
        :show-labels="false"
        @update:current-page="currentPage = $event"
      />
      <div class="state">{{ t('analysisEditor.loading') }}</div>
    </div>
    <div v-else-if="store.error" class="state error">{{ store.error }}</div>
    <template v-else>
      <EditorBanners
        :preview-error="store.previewError"
        :history-error="store.historyError"
        :conflict="store.conflict"
        :recovered-count="store.recoveredPendingCount"
        :save-notice="saveNotice"
        :chunks-stale="Boolean(store.effective?.chunksStale)"
        @reload-conflict="store.reloadAfterConflict()"
        @copy-conflict="copyConflictDetails"
        @discard-conflict="store.discardConflict()"
        @restore-draft="store.restoreRecoveredPending()"
        @discard-draft="store.discardRecoveredPending()"
      />
      <AnalysisEditHistoryPanel
        v-if="historyOpen"
        :history="store.history"
        :can-change="store.canChangeSavedHistory"
        @set-active="(sequence, active) => store.setSavedCommandActive(sequence, active)"
      />
      <div class="editor-grid">
        <aside class="structure-column">
          <div class="column-heading">
            <span>{{ t('analysisEditor.readingOrder') }}</span>
            <button type="button" class="tree-fold-button" @click="toggleTreeOpen">
              {{
                treeDefaultOpen ? t('analysisEditor.collapseAll') : t('analysisEditor.expandAll')
              }}
            </button>
          </div>
          <div role="tree" :aria-label="t('analysisEditor.readingOrder')">
            <EditableStructureNode
              v-for="node in store.tree"
              :key="`${node.elementId}-${treeRemountKey}`"
              :node="node"
              :selected-id="store.selectedElementId"
              :checked-ids="store.mergeSelection"
              :is-text="isMergeable"
              :is-movable="isMovable"
              :dragging="Boolean(draggedId)"
              :default-open="treeDefaultOpen"
              :order-index-by-id="showReadingOrder ? orderIndexById : undefined"
              :next-id="showReadingOrder ? nextElementId : null"
              @select="select"
              @extend-selection="extendSelection"
              @toggle-merge="toggleMerge"
              @toggle-subtree="toggleMergeSubtree"
              @drag-start="(id) => (draggedId = id)"
              @drop="drop"
            />
          </div>
        </aside>
        <main class="preview-column">
          <div class="preview-tabs">
            <button :class="{ active: previewMode === 'page' }" @click="previewMode = 'page'">
              {{ t('analysisEditor.pdfLayout') }}
            </button>
            <button
              :class="{ active: previewMode === 'markdown' }"
              data-e2e="analysis-editor-markdown-tab"
              @click="previewMode = 'markdown'"
            >
              {{ t('analysisEditor.markdown') }}
            </button>
            <button
              v-if="previewMode === 'page' && store.pages.length"
              type="button"
              class="reading-order-toggle"
              :aria-pressed="showReadingOrder"
              :title="t('analysisEditor.readingOrderHint')"
              data-e2e="analysis-editor-reading-order-toggle"
              @click="showReadingOrder = !showReadingOrder"
            >
              {{
                showReadingOrder
                  ? t('analysisEditor.hideReadingOrder')
                  : t('analysisEditor.showReadingOrder')
              }}
            </button>
          </div>
          <div v-if="previewMode === 'page'" class="page-preview">
            <PagePreviewWithOverlay
              v-if="store.pages.length"
              :document-id="documentId"
              :pages="store.pages"
              :current-page="currentPage"
              :hidden-types="new Set<string>()"
              :highlighted-refs="highlightedRefs"
              :show-labels="!showReadingOrder"
              :reading-order-by-ref="showReadingOrder ? orderIndexByRef : undefined"
              :selected-ref="showReadingOrder ? selectedRef : null"
              :next-ref="showReadingOrder ? nextRef : null"
              @update:current-page="currentPage = $event"
              @click-element="onPageElement"
            />
            <div v-else class="state">{{ t('analysisEditor.noPages') }}</div>
          </div>
          <pre v-else class="markdown-preview" data-e2e="analysis-editor-markdown">{{
            store.effective?.result.contentMarkdown
          }}</pre>
        </main>
        <aside class="properties-column">
          <ElementEditPanel
            :element="store.selectedElement"
            @replace-text="store.queueReplaceText(store.selectedElementId!, $event)"
            @heading-level="store.queueHeadingLevel(store.selectedElementId!, $event)"
            @delete-element="store.queueDelete(store.selectedElementId!)"
          />
        </aside>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import type { Page, PageElement } from '../../../shared/types'
import { useAnalysisEditorStore } from '../store'
import { useI18n } from '../../../shared/i18n'
import AnalysisEditHistoryPanel from './AnalysisEditHistoryPanel.vue'
import EditableStructureNode from './EditableStructureNode.vue'
import EditorBanners from './EditorBanners.vue'
import ElementEditPanel from './ElementEditPanel.vue'
import { PagePreviewWithOverlay } from '../../document'

const props = defineProps<{ documentId: string; analysisId?: string; previewPages?: Page[] }>()
const emit = defineEmits<{ discard: []; saved: [] }>()
const store = useAnalysisEditorStore()
const { t } = useI18n()
const currentPage = ref(1)
const previewMode = ref<'page' | 'markdown'>('page')
const showReadingOrder = ref(false)
const historyOpen = ref(false)
const draggedId = ref<string | null>(null)
const treeDefaultOpen = ref(true)
const treeRemountKey = ref(0)
const saveNotice = ref<string | null>(null)
let saveNoticeTimer: ReturnType<typeof setTimeout> | null = null
const selectionCount = computed(
  () => store.mergeSelection.length || (store.selectedElementId ? 1 : 0),
)
const elementsById = computed(() => new Map(store.elements.map((element) => [element.id, element])))
const orderedVisibleIds = computed(() => {
  const refsOnPages = new Set(
    store.pages.flatMap((page) => page.elements.map((item) => item.self_ref)),
  )
  return (store.effective?.readingOrder ?? []).filter((id) => {
    const ref = elementsById.value.get(id)?.selfRef
    return Boolean(ref && refsOnPages.has(ref))
  })
})
const orderIndexById = computed(
  () => new Map(orderedVisibleIds.value.map((id, index) => [id, index + 1])),
)
const orderIndexByRef = computed(
  () =>
    new Map(
      orderedVisibleIds.value.map((id, index) => [elementsById.value.get(id)!.selfRef, index + 1]),
    ),
)
const nextElementId = computed(() => {
  const index = orderedVisibleIds.value.indexOf(store.selectedElementId ?? '')
  return index >= 0 ? (orderedVisibleIds.value[index + 1] ?? null) : null
})
const selectedRef = computed(() =>
  store.selectedElementId
    ? (elementsById.value.get(store.selectedElementId)?.selfRef ?? null)
    : null,
)
const nextRef = computed(() =>
  nextElementId.value ? (elementsById.value.get(nextElementId.value)?.selfRef ?? null) : null,
)
const isMergeable = (id: string) => {
  const type = elementsById.value.get(id)?.type
  return type === 'text' || type === 'paragraph'
}
const isMovable = (id: string) =>
  elementsById.value.get(id)?.supportedOperations.includes('moveElement') ?? false
const highlightedRefs = computed(() => {
  const ids = new Set(
    store.mergeSelection.length
      ? store.mergeSelection
      : store.selectedElementId
        ? [store.selectedElementId]
        : [],
  )
  return new Set(
    store.elements.filter((element) => ids.has(element.id)).map((element) => element.selfRef),
  )
})

function focusPage(id: string): void {
  const element = store.elements.find((candidate) => candidate.id === id)
  const page = element?.provenance[0]?.page
  if (page) currentPage.value = page
}
/** Select one element and clear the merge selection. */
function select(id: string): void {
  store.mergeSelection = []
  store.selectedElementId = id
  focusPage(id)
}
/** Cmd/Ctrl-click: add the element to (or remove it from) the merge selection. */
function extendSelection(id: string): void {
  if (!isMergeable(id)) {
    select(id)
    return
  }
  if (!store.mergeSelection.length && store.selectedElementId && store.selectedElementId !== id) {
    if (isMergeable(store.selectedElementId)) store.selectMergeSelection(store.selectedElementId)
  }
  store.toggleMergeSelection(id)
  store.selectedElementId = id
  focusPage(id)
}
function toggleMerge(id: string): void {
  store.toggleMergeSelection(id)
  store.selectedElementId = id
  focusPage(id)
}
function toggleMergeSubtree(ids: string[]): void {
  store.toggleMergeSelectionMany(ids)
}
function toggleTreeOpen(): void {
  treeDefaultOpen.value = !treeDefaultOpen.value
  treeRemountKey.value += 1
}
function discard(): void {
  store.discard()
  saveNotice.value = null
  emit('discard')
}
async function copyConflictDetails(): Promise<void> {
  try {
    await navigator.clipboard.writeText(store.conflictDetails)
  } catch {
    // Clipboard access is unavailable in some browser contexts.
  }
}
async function save(): Promise<void> {
  await store.save()
  if (!store.error && !store.conflict) {
    saveNotice.value = t('analysisEditor.saved')
    if (saveNoticeTimer) clearTimeout(saveNoticeTimer)
    saveNoticeTimer = setTimeout(() => (saveNotice.value = null), 4000)
    emit('saved')
  }
}
function drop(targetId: string, placement: 'before' | 'after' | 'inside'): void {
  if (draggedId.value && draggedId.value !== targetId) {
    store.moveElement(draggedId.value, targetId, placement)
  }
  draggedId.value = null
}
function toggleMoveDestination(): void {
  draggedId.value = draggedId.value ? null : store.selectedElementId
}
function onPageElement(element: PageElement, _pageNumber: number, event?: MouseEvent): void {
  const match = store.elements.find((candidate) => candidate.selfRef === element.self_ref)
  if (!match) return
  if (event?.metaKey || event?.ctrlKey) {
    extendSelection(match.id)
    return
  }
  select(match.id)
  if (isMergeable(match.id)) store.selectMergeSelection(match.id)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && draggedId.value) {
    event.preventDefault()
    draggedId.value = null
    return
  }
  if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'z') return
  if (
    event.target instanceof HTMLElement &&
    event.target.closest('input, textarea, [contenteditable="true"]')
  )
    return
  event.preventDefault()
  if (event.shiftKey) void store.redo()
  else void store.undo()
}

function confirmLeave(): boolean {
  return !store.hasUnsavedChanges || window.confirm(t('analysisEditor.leaveConfirm'))
}

function onBeforeUnload(event: BeforeUnloadEvent): void {
  if (!store.hasUnsavedChanges) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('beforeunload', onBeforeUnload)
  store.load(props.documentId, props.analysisId)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('beforeunload', onBeforeUnload)
  if (saveNoticeTimer) clearTimeout(saveNoticeTimer)
  store.cancelPreview()
})
onBeforeRouteLeave(() => confirmLeave())
watch(
  () => store.elements.length,
  (count, previous) => {
    if (count > 1000 && previous <= 1000) {
      // Avoid mounting thousands of nested tree rows before the editor is usable.
      treeDefaultOpen.value = false
      treeRemountKey.value += 1
    }
  },
  { flush: 'sync' },
)
watch(
  () => [props.documentId, props.analysisId] as const,
  ([id, analysisId], [oldId, oldAnalysisId]) => {
    if (id !== oldId || analysisId !== oldAnalysisId) store.load(id, analysisId)
  },
)
</script>

<style scoped src="./editorButton.css"></style>

<style scoped>
.analysis-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-surface);
}
.editor-loading-preview {
  position: relative;
  flex: 1;
  min-height: 0;
}
.editor-loading-preview :deep(.preview-with-overlay) {
  height: 100%;
}
.editor-loading-preview > .state {
  position: absolute;
  right: 16px;
  bottom: 16px;
  padding: 8px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}
.toolbar-title,
.toolbar-actions,
.preview-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
}
.eyebrow,
.column-heading {
  color: var(--text-muted);
  font:
    11px 'IBM Plex Mono',
    monospace;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.unsaved {
  color: var(--warning);
  font-size: 11px;
}
.selection-status {
  color: var(--text-muted);
  font-size: 11px;
}
button.primary {
  border-color: var(--accent);
  background: var(--accent-muted);
  color: var(--accent);
}
.merge-toolbar-button {
  border-color: var(--accent);
  color: var(--accent);
}
.operation-feedback {
  max-width: 220px;
  color: var(--warning);
  font-size: 11px;
}
.delete-range-button {
  border-color: var(--error);
  color: var(--error);
}
.history-button.active {
  border-color: var(--accent);
  color: var(--accent);
}
.tree-fold-button {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
}
.error {
  color: var(--error);
}
.editor-grid {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 280px;
  flex: 1;
  min-height: 0;
}
.structure-column,
.properties-column {
  min-width: 0;
  overflow: auto;
  padding: 12px;
  border-right: 1px solid var(--border);
}
.properties-column {
  border-right: 0;
  border-left: 1px solid var(--border);
  padding: 0;
}
.column-heading {
  margin-bottom: 10px;
}
.preview-column {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.preview-tabs {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}
.preview-tabs button.active {
  color: var(--accent);
  border-color: var(--accent);
}
.reading-order-toggle {
  margin-left: auto;
}
.reading-order-toggle[aria-pressed='true'] {
  color: var(--accent);
  border-color: var(--accent);
}
.page-preview {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
}
.markdown-preview {
  flex: 1;
  overflow: auto;
  margin: 0;
  padding: 18px;
  white-space: pre-wrap;
  color: var(--text-secondary);
  font:
    13px/1.6 'IBM Plex Mono',
    monospace;
}
.merge-button {
  width: 100%;
  margin-top: 12px;
  color: var(--accent);
}
.state {
  display: grid;
  place-items: center;
  flex: 1;
  color: var(--text-muted);
  font-size: 13px;
}
@media (max-width: 900px) {
  .editor-grid {
    grid-template-columns: 220px minmax(0, 1fr);
  }
  .properties-column {
    grid-column: 1 / -1;
    border-top: 1px solid var(--border);
    height: 220px;
  }
}
</style>

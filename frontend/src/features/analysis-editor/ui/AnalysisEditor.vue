<template>
  <section class="analysis-editor" data-e2e="parse-tab" data-editor="analysis-editor">
    <header class="editor-toolbar">
      <div class="toolbar-title">
        <span class="eyebrow">{{ t('analysisEditor.title') }}</span>
        <span v-if="store.hasUnsavedChanges" class="unsaved">{{ t('analysisEditor.unsaved') }}</span>
      </div>
      <div class="toolbar-actions">
        <button
          type="button"
          class="history-button"
          :class="{ active: historyOpen }"
          @click="historyOpen = !historyOpen"
        >
          {{ t('analysisEditor.history', { n: store.history.length }) }}
        </button>
        <button
          v-if="store.mergeSelection.length"
          type="button"
          class="merge-toolbar-button"
          :disabled="!store.mergeAllowed"
          @click="store.mergeSelected()"
        >
          {{ t('analysisEditor.mergeSelected', { n: store.mergeSelection.length }) }}
        </button>
        <button type="button" :disabled="!store.hasUnsavedChanges || store.previewing" @click="store.previewNow()">
          {{ store.previewing ? t('analysisEditor.previewing') : t('analysisEditor.preview') }}
        </button>
        <button type="button" :disabled="!store.hasUnsavedChanges" @click="discard">{{ t('analysisEditor.discard') }}</button>
        <button type="button" class="primary" :disabled="!store.hasUnsavedChanges || store.saving" @click="save">
          {{ store.saving ? t('analysisEditor.saving') : t('analysisEditor.save') }}
        </button>
      </div>
    </header>
    <div v-if="store.loading" class="state">{{ t('analysisEditor.loading') }}</div>
    <div v-else-if="store.error" class="state error">{{ store.error }}</div>
    <template v-else>
      <div v-if="store.previewError" class="editor-error">{{ store.previewError }}</div>
      <div v-if="store.effective?.chunksStale" class="editor-warning">{{ t('analysisEditor.chunksStale') }}</div>
      <section v-if="historyOpen" class="history-panel" data-e2e="analysis-edit-history">
        <div v-if="!store.history.length" class="history-empty">{{ t('analysisEditor.historyEmpty') }}</div>
        <article v-for="entry in [...store.history].reverse()" :key="entry.id" class="history-entry">
          <div class="history-entry-head">
            <strong>#{{ entry.sequence }} {{ entry.commandType }}</strong>
            <time>{{ formatHistoryDate(entry.createdAt) }}</time>
          </div>
          <code>{{ formatHistoryPayload(entry.payload) }}</code>
        </article>
      </section>
      <div class="editor-grid">
        <aside class="structure-column">
          <div class="column-heading">
            <span>{{ t('analysisEditor.readingOrder') }}</span>
            <button type="button" class="tree-fold-button" @click="toggleTreeOpen">
              {{ treeDefaultOpen ? t('analysisEditor.collapseAll') : t('analysisEditor.expandAll') }}
            </button>
          </div>
          <EditableStructureNode
            v-for="node in store.tree"
            :key="`${node.elementId}-${treeRemountKey}`"
            :node="node"
            :selected-id="store.selectedElementId"
            :checked-ids="store.mergeSelection"
            :is-text="isMergeable"
            :default-open="treeDefaultOpen"
            @select="select"
            @toggle-merge="toggleMerge"
            @toggle-subtree="toggleMergeSubtree"
            @drag-start="(id) => (draggedId = id)"
            @drop="dropBefore"
          />
        </aside>
        <main class="preview-column">
          <div class="preview-tabs">
            <button :class="{ active: previewMode === 'page' }" @click="previewMode = 'page'">{{ t('analysisEditor.pdfLayout') }}</button>
            <button :class="{ active: previewMode === 'markdown' }" @click="previewMode = 'markdown'">{{ t('analysisEditor.markdown') }}</button>
          </div>
          <div v-if="previewMode === 'page'" class="page-preview">
            <PagePreviewWithOverlay
              v-if="store.pages.length"
              :document-id="documentId"
              :pages="store.pages"
              :current-page="currentPage"
              :hidden-types="new Set<string>()"
              :highlighted-refs="highlightedRefs"
              :show-labels="true"
              @update:current-page="currentPage = $event"
              @click-element="onPageElement"
            />
            <div v-else class="state">{{ t('analysisEditor.noPages') }}</div>
          </div>
          <pre v-else class="markdown-preview">{{ store.effective?.result.contentMarkdown }}</pre>
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
import { computed, onMounted, ref, watch } from 'vue'
import type { PageElement } from '../../../shared/types'
import { useAnalysisEditorStore } from '../store'
import { useI18n } from '../../../shared/i18n'
import EditableStructureNode from './EditableStructureNode.vue'
import ElementEditPanel from './ElementEditPanel.vue'
import PagePreviewWithOverlay from '../../document/ui/PagePreviewWithOverlay.vue'

const props = defineProps<{ documentId: string; analysisId?: string }>()
const emit = defineEmits<{ discard: []; saved: [] }>()
const store = useAnalysisEditorStore()
const { t } = useI18n()
const currentPage = ref(1)
const previewMode = ref<'page' | 'markdown'>('page')
const historyOpen = ref(false)
const draggedId = ref<string | null>(null)
const treeDefaultOpen = ref(true)
const treeRemountKey = ref(0)
const isMergeable = (id: string) => store.elements.find((element) => element.id === id)?.type === 'text'
const highlightedRefs = computed(() => {
  const ids = new Set(store.mergeSelection.length ? store.mergeSelection : store.selectedElementId ? [store.selectedElementId] : [])
  return new Set(store.elements.filter((element) => ids.has(element.id)).map((element) => element.selfRef))
})

function focusPage(id: string): void {
  const element = store.elements.find((candidate) => candidate.id === id)
  const page = element?.provenance[0]?.page
  if (page) currentPage.value = page
}
function select(id: string): void {
  store.selectedElementId = id
  store.mergeSelection = []
  focusPage(id)
}
function formatHistoryDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}
function formatHistoryPayload(payload: Record<string, unknown>): string {
  const values = Object.entries(payload)
    .filter(([key]) => key !== 'elementId' && key !== 'elementIds')
    .map(([key, value]) => `${key}: ${String(value)}`)
  return values.join(' · ') || 'Structural change'
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
  emit('discard')
}
async function save(): Promise<void> {
  await store.save()
  if (!store.error) emit('saved')
}
function dropBefore(beforeId: string): void {
  if (draggedId.value && draggedId.value !== beforeId) store.moveElement(draggedId.value, beforeId)
  draggedId.value = null
}
function onPageElement(element: PageElement, _pageNumber: number, event: MouseEvent): void {
  const match = store.elements.find((candidate) => candidate.selfRef === element.self_ref)
  if (!match) return
  if (event.shiftKey || event.metaKey || event.ctrlKey) toggleMerge(match.id)
  else select(match.id)
}

onMounted(() => store.load(props.documentId, props.analysisId))
watch(
  () => [props.documentId, props.analysisId] as const,
  ([id, analysisId], [oldId, oldAnalysisId]) => {
    if (id !== oldId || analysisId !== oldAnalysisId) store.load(id, analysisId)
  },
)
</script>

<style scoped>
.analysis-editor { display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; background: var(--bg-surface); }
.editor-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--border); }
.toolbar-title, .toolbar-actions, .preview-tabs { display: flex; align-items: center; gap: 8px; }
.eyebrow, .column-heading { color: var(--text-muted); font: 11px 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: .06em; }
.unsaved { color: var(--warning, #d97706); font-size: 11px; }
button { border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-elevated); color: var(--text-secondary); padding: 6px 10px; cursor: pointer; font-size: 12px; }
button:disabled { opacity: .45; cursor: default; }
button.primary { border-color: var(--accent); background: var(--accent-muted); color: var(--accent); }
.merge-toolbar-button { border-color: var(--accent); color: var(--accent); }
.history-button.active { border-color: var(--accent); color: var(--accent); }
.editor-warning, .editor-error { padding: 8px 16px; font-size: 12px; }
.editor-warning { color: var(--warning, #d97706); background: color-mix(in srgb, var(--warning, #d97706) 10%, transparent); }
.history-panel { max-height: 220px; overflow: auto; padding: 8px 16px; border-bottom: 1px solid var(--border); background: var(--bg-elevated); }
.history-entry { padding: 8px 0; border-bottom: 1px solid var(--border); }
.history-entry:last-child { border-bottom: 0; }
.history-entry-head { display: flex; justify-content: space-between; gap: 12px; color: var(--text-secondary); font-size: 11px; }
.history-entry time { color: var(--text-muted); white-space: nowrap; }
.history-entry code { display: block; margin-top: 4px; color: var(--text-muted); font: 10px 'IBM Plex Mono', monospace; white-space: pre-wrap; }
.history-empty { padding: 12px 0; color: var(--text-muted); font-size: 12px; }
.tree-fold-button { margin-left: auto; border: 0; background: transparent; color: var(--text-muted); cursor: pointer; font-size: 11px; }
.editor-error, .error { color: var(--error); }
.editor-grid { display: grid; grid-template-columns: 260px minmax(0, 1fr) 280px; flex: 1; min-height: 0; }
.structure-column, .properties-column { min-width: 0; overflow: auto; padding: 12px; border-right: 1px solid var(--border); }
.properties-column { border-right: 0; border-left: 1px solid var(--border); padding: 0; }
.column-heading { margin-bottom: 10px; }
.preview-column { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.preview-tabs { padding: 8px 12px; border-bottom: 1px solid var(--border); }
.preview-tabs button.active { color: var(--accent); border-color: var(--accent); }
.page-preview { flex: 1; min-height: 0; overflow: auto; padding: 12px; }
.markdown-preview { flex: 1; overflow: auto; margin: 0; padding: 18px; white-space: pre-wrap; color: var(--text-secondary); font: 13px/1.6 'IBM Plex Mono', monospace; }
.merge-button { width: 100%; margin-top: 12px; color: var(--accent); }
.state { display: grid; place-items: center; flex: 1; color: var(--text-muted); font-size: 13px; }
@media (max-width: 900px) { .editor-grid { grid-template-columns: 220px minmax(0, 1fr); } .properties-column { grid-column: 1 / -1; border-top: 1px solid var(--border); height: 220px; } }
</style>

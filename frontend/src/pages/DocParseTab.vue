<template>
  <div class="parse-tab" data-e2e="parse-tab">
    <LayersBar
      :elements="allPageElements"
      :hidden-types="hiddenTypes"
      @update:hidden-types="(next) => (hiddenTypes = next)"
    >
      <template #action>
        <button
          v-if="showNewAnalysis"
          type="button"
          class="tab-action-cta"
          :disabled="analysisStore.running"
          :title="t('newAnalysis.title')"
          data-e2e="parse-new-analysis"
          @click="onLaunchAnalysis"
        >
          <span v-if="analysisStore.running" class="tab-action-spinner" />
          <span v-else>+</span>
          {{ analysisStore.running ? t('newAnalysis.running') : t('newAnalysis.title') }}
        </button>
      </template>
    </LayersBar>
    <div class="parse-body" :class="{ 'properties-open': propertiesOpen }">
      <aside class="parse-structure" :class="{ 'parse-drawer--closed': !structureOpen }">
        <header class="parse-structure-header">
          <h2 v-if="structureOpen" class="parse-structure-title">
            {{ t('parse.structureTitle') }}
          </h2>
          <button
            class="drawer-toggle"
            :aria-label="t('parse.structureTitle')"
            @click="structureOpen = !structureOpen"
          >
            {{ structureOpen ? '‹' : '›' }}
          </button>
          <span v-if="structureOpen" class="parse-structure-count">
            {{ t('parse.structureNodes', { n: nodeCount }) }}
          </span>
          <div v-if="structureOpen" class="parse-structure-actions">
            <button
              type="button"
              class="tree-action-btn"
              :title="treeDefaultOpen ? t('parse.collapseAll') : t('parse.expandAll')"
              :aria-label="treeDefaultOpen ? t('parse.collapseAll') : t('parse.expandAll')"
              data-e2e="tree-toggle-all"
              @click="treeDefaultOpen ? onCollapseAll() : onExpandAll()"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path d="M3 4h14M6 10h8M8 16h4" />
              </svg>
            </button>
          </div>
        </header>
        <input
          v-if="structureOpen"
          v-model="filter"
          type="text"
          class="parse-structure-filter"
          :placeholder="t('parse.filterPlaceholder')"
          data-e2e="structure-filter"
        />
        <DocTreeRail
          v-if="structureOpen"
          :key="treeRemountKey"
          :nodes="filteredNodes"
          :loading="treeLoading"
          :error="treeError"
          :selected="selectedRefs"
          :highlight="documentStore.focusedRef"
          :default-open="treeDefaultOpen"
          :revealed-refs="revealedRefs"
          :focused-ref="documentStore.focusedRef"
          :reveal-tick="documentStore.focusTick"
          @select="onTreeSelect"
          @reload="loadTree"
        />
      </aside>
      <div class="parse-stage">
        <div class="parse-preview">
          <PagePreviewWithOverlay
            v-if="documentStore.workspacePages.length"
            :document-id="docId"
            :pages="documentStore.workspacePages"
            :current-page="currentPage"
            :hidden-types="hiddenTypes"
            :show-labels="true"
            :highlighted-refs="highlightedRefs"
            :focus-tick="documentStore.focusTick"
            @update:current-page="(p) => (currentPage = p)"
            @hover-element="onHoverElement"
            @click-element="onClickElement"
          />
          <div v-else-if="documentStore.workspaceLoading" class="parse-state">
            <span class="spinner" />
          </div>
          <div v-else class="parse-state parse-state--empty">
            <p>{{ t('parse.noAnalysis') }}</p>
          </div>
        </div>
        <TraceTimeline
          v-if="reasoningAvailable && rightTab === 'ask'"
          class="parse-trace-dock"
          :trace="reasoningStore.activeTrace"
          :running="reasoningStore.running"
          :selected-step-id="reasoningStore.selectedStepId"
          :doc-loaded="docLoaded"
          @select-step="reasoningStore.selectStep"
        />
      </div>
      <aside class="properties-drawer" :class="{ 'properties-drawer--closed': !propertiesOpen }">
        <button
          class="drawer-toggle properties-toggle"
          :aria-label="t('parse.propertiesTitle')"
          @click="propertiesOpen = !propertiesOpen"
        >
          {{ propertiesOpen ? '›' : '‹' }}
        </button>
        <div v-if="propertiesOpen && reasoningAvailable" class="parse-tabs">
          <button
            type="button"
            class="parse-tab-btn"
            :class="{ active: rightTab === 'props' }"
            data-e2e="props-tab"
            @click="rightTab = 'props'"
          >
            {{ t('props.tab') }}
          </button>
          <button
            type="button"
            class="parse-tab-btn"
            :class="{ active: rightTab === 'ask' }"
            data-e2e="ask-tab"
            @click="rightTab = 'ask'"
          >
            {{ t('ask.tab') }}
            <span v-if="reasoningStore.turns.length" class="parse-tab-pill">{{
              reasoningStore.turns.length
            }}</span>
          </button>
        </div>
        <ConversationPanel
          v-if="propertiesOpen && reasoningAvailable && rightTab === 'ask'"
          :turns="reasoningStore.turns"
          :selected-turn-id="reasoningStore.selectedTurnId"
          :doc-loaded="docLoaded"
          :running="reasoningStore.running"
          @select-turn="reasoningStore.selectTurn"
          @run="onRunReasoning"
        />
        <ElementProperties
          v-else-if="propertiesOpen"
          :element="selectedElementData?.element ?? null"
          :page-width="selectedElementPage?.width ?? 0"
          :page-height="selectedElementPage?.height ?? 0"
          :page-number="selectedElementData?.pageNumber ?? currentPage"
          :linked-chunk="linkedChunk"
          :saving="chunksStore.saving"
          :editable="!analysisId"
          @save-chunk="onSaveChunk"
        />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Parse view (#264). Shows the Docling extraction graph for a document:
 *
 *   - LAYERS bar (chip filters per element type + Show labels toggle)
 *   - Structure tree (left rail — element hierarchy per page)
 *   - Page preview with bbox overlay (center)
 *
 * Two-way link between tree and overlay:
 *   - Selecting a node in the tree → highlight its bbox on the preview
 *   - Clicking a bbox → select the matching node in the tree
 */
import { computed, onMounted, ref, watch } from 'vue'
import type { Analysis, Chunk, DocChunk, DocTreeNode, PageElement } from '../shared/types'
import { useAnalysisStore } from '../features/analysis/store'
import { fetchAnalysis } from '../features/analysis/api'
import { useChunksStore } from '../features/chunks/store'
import { fetchDocumentTree } from '../features/document/api'
import { useDocumentStore } from '../features/document/store'
import { chunkForElement } from '../features/document/linkedView'
import { ancestorRefs } from '../features/document/treeReveal'
import DocTreeRail from '../features/document/ui/DocTreeRail.vue'
import ElementProperties from '../features/document/ui/ElementProperties.vue'
import LayersBar from '../features/document/ui/LayersBar.vue'
import PagePreviewWithOverlay from '../features/document/ui/PagePreviewWithOverlay.vue'
import { useFeatureFlagStore } from '../features/feature-flags/store'
import { useReasoningStore } from '../features/reasoning/store'
import ConversationPanel from '../features/reasoning/ui/ConversationPanel.vue'
import TraceTimeline from '../features/reasoning/ui/TraceTimeline.vue'
import { useI18n } from '../shared/i18n'

const props = withDefaults(defineProps<{ docId: string; analysisId?: string; showNewAnalysis?: boolean }>(), {
  showNewAnalysis: true,
})
const showNewAnalysis = computed(() => props.showNewAnalysis)

const { t } = useI18n()
const documentStore = useDocumentStore()
const chunksStore = useChunksStore()
const analysisStore = useAnalysisStore()
const reasoningStore = useReasoningStore()
const featureFlags = useFeatureFlagStore()

// Reasoning is backend-gated (REASONING_ENABLED + docling-agent importable).
// When off, the Parse view is pixel-identical to before: no Ask tab, no dock.
const reasoningAvailable = computed(() => featureFlags.isEnabled('reasoning'))
// Right panel defaults to Properties; Ask is opt-in (#303 design decision).
const rightTab = ref<'props' | 'ask'>('props')
const docLoaded = computed(() => documentStore.workspacePages.length > 0)

function onRunReasoning(query: string, model: string | undefined): void {
  void reasoningStore.run(props.docId, query, model)
}

function analysisChunks(analysis: Analysis): DocChunk[] {
  if (!analysis.chunksJson) return []
  try {
    return (JSON.parse(analysis.chunksJson) as Chunk[]).map((chunk, sequence) => ({
      id: `analysis-${analysis.id}-${sequence}`,
      docId: analysis.documentId,
      sequence,
      text: chunk.text,
      headings: chunk.headings,
      sourcePage: chunk.sourcePage,
      tokenCount: chunk.tokenCount,
      bboxes: chunk.bboxes,
      docItems: [],
      createdAt: analysis.createdAt,
      updatedAt: analysis.createdAt,
    }))
  } catch {
    return []
  }
}

async function onLaunchAnalysis(): Promise<void> {
  if (analysisStore.running) return
  await analysisStore.run(props.docId)
}

const currentPage = ref(1)
const structureOpen = ref(true)
const propertiesOpen = ref(true)
const hiddenTypes = ref<Set<string>>(new Set())

// Expand/Collapse all — bumping `treeRemountKey` re-keys the rail so every
// DocTreeNode mounts fresh and picks up the new `treeDefaultOpen` value.
const treeRemountKey = ref(0)
const treeDefaultOpen = ref<boolean | null>(null)
function onExpandAll(): void {
  treeDefaultOpen.value = true
  treeRemountKey.value++
}
function onCollapseAll(): void {
  treeDefaultOpen.value = false
  treeRemountKey.value++
}

const tree = ref<DocTreeNode[]>([])
const selectedRefs = ref<string[]>([])
const treeLoading = ref(false)
const treeError = ref<string | null>(null)
const filter = ref('')

const allPageElements = computed<PageElement[]>(() =>
  documentStore.workspacePages.flatMap((page) => page.elements),
)

const selectedElementData = computed<{ element: PageElement; pageNumber: number } | null>(() => {
  // `focusedRef` is the single source of truth for selection (#303); the
  // page number comes along so the panel can render an element that lives
  // on a page other than the one currently shown (#309 cross-page preview).
  const ref = documentStore.focusedRef
  if (!ref) return null
  // Search every page — the focused ref may point to an element on a
  // different page than the one currently rendered (the click also
  // triggers a page change, but until that lands the panel still wants
  // to show the element's data).
  for (const page of documentStore.workspacePages) {
    const el = page.elements.find((e) => e.self_ref === ref)
    if (el) return { element: el, pageNumber: page.page_number }
  }
  return null
})

const selectedElementPage = computed(() => {
  if (!selectedElementData.value) return null
  return (
    documentStore.workspacePages.find(
      (page) => page.page_number === selectedElementData.value?.pageNumber,
    ) ?? null
  )
})

const linkedChunk = computed<DocChunk | null>(() => {
  if (!selectedElementData.value) return null
  return chunkForElement(
    selectedElementData.value.element,
    selectedElementData.value.pageNumber,
    activeChunks.value,
  )
})

const activeChunks = computed<DocChunk[]>(() => {
  const analysis = documentStore.workspaceActiveAnalysis
  return props.analysisId && analysis ? analysisChunks(analysis) : chunksStore.chunks
})

const nodeCount = computed(() => countNodes(tree.value))

const filteredNodes = computed<DocTreeNode[]>(() => {
  const needle = filter.value.trim().toLowerCase()
  if (!needle) return tree.value
  return filterTree(tree.value, needle)
})

const highlightedRefs = computed<ReadonlySet<string>>(() => {
  const ref = documentStore.focusedRef
  if (!ref) return new Set()
  return new Set([ref])
})

// #303 (design §337) — ancestor chain of the focused element; the tree forces
// these nodes open so the focused row is revealed before the rail scrolls to it.
const revealedRefs = computed<Set<string>>(() => ancestorRefs(tree.value, documentStore.focusedRef))

async function loadTree(): Promise<void> {
  treeLoading.value = true
  treeError.value = null
  try {
    tree.value = await fetchDocumentTree(props.docId, props.analysisId)
  } catch (e) {
    treeError.value = (e as Error).message || 'Failed to load tree'
  } finally {
    treeLoading.value = false
  }
}

function onTreeSelect(ref: string): void {
  // Route through the shared focus (drives the bbox highlight, page flip and
  // Properties via the focusTick watcher) and reverse-select a citing step.
  selectedRefs.value = [ref]
  documentStore.focusElement(ref)
  reasoningStore.selectStepByCitation(ref)
}

function onHoverElement(_el: PageElement | null): void {
  // Hover is informational only — selection drives the tree highlight.
}

function onClickElement(el: PageElement, _pageNumber: number, event?: MouseEvent): void {
  if (!el.self_ref) return
  selectedRefs.value = event?.ctrlKey || event?.metaKey
    ? selectedRefs.value.includes(el.self_ref)
      ? selectedRefs.value.filter((ref) => ref !== el.self_ref)
      : [...selectedRefs.value, el.self_ref]
    : [el.self_ref]
  documentStore.focusElement(el.self_ref)
  reasoningStore.selectStepByCitation(el.self_ref)
}

async function onSaveChunk(chunkId: string, text: string): Promise<void> {
  if (props.analysisId) return
  await chunksStore.updateText(props.docId, chunkId, text)
}

onMounted(async () => {
  reasoningStore.reset(props.docId)
  if (props.analysisId) {
    documentStore.setWorkspaceAnalysis(await fetchAnalysis(props.analysisId))
    await loadTree()
  } else {
    await Promise.all([
      documentStore.loadWorkspace(props.docId),
      chunksStore.load(props.docId),
      loadTree(),
    ])
  }
  const first = documentStore.workspacePages[0]?.page_number
  if (first) currentPage.value = first
})

watch(
  () => props.docId,
  async (id) => {
    filter.value = ''
    rightTab.value = 'props'
    reasoningStore.reset(id)
    documentStore.focusElement(null)
    selectedRefs.value = []
    if (props.analysisId) {
      documentStore.setWorkspaceAnalysis(await fetchAnalysis(props.analysisId))
      await loadTree()
    } else {
      await Promise.all([documentStore.loadWorkspace(id), chunksStore.load(id), loadTree()])
    }
    const first = documentStore.workspacePages[0]?.page_number
    if (first) currentPage.value = first
  },
)

// #303 — citation focus bridge. `focusedRef` is the single source of truth for
// selection: the tree/bbox highlight, the Properties panel and `highlightedRefs`
// all read it directly. This watcher's only job is the side effect those
// computeds can't express — flipping the page when the focused element lives on
// another one. The PDF scroll and tree reveal are driven by `focusTick` inside
// their own components, so a same-ref re-click still re-scrolls. Never switches
// the active right-panel tab.
watch(
  () => documentStore.focusTick,
  () => {
    const ref = documentStore.focusedRef
    if (!ref) return
    const pageOfRef = findPageOfRef(documentStore.workspacePages, ref)
    if (pageOfRef !== null && pageOfRef !== currentPage.value) {
      currentPage.value = pageOfRef
    }
  },
)

// Refetch the tree when the active analysis changes (#266 / #267).
// Triggered after an in-place analysis completes or after the user
// restores a different version from the History drawer — the tree
// is built server-side from the active analysis's `document_json`,
// so it has to be reloaded.
watch(
  () => documentStore.workspaceActiveAnalysis?.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      documentStore.focusElement(null)
      loadTree()
    }
  },
)

// --- pure helpers ----------------------------------------------------------

function countNodes(nodes: readonly DocTreeNode[]): number {
  let n = 0
  for (const node of nodes) {
    n += 1 + countNodes(node.children)
  }
  return n
}

function filterTree(nodes: readonly DocTreeNode[], needle: string): DocTreeNode[] {
  const out: DocTreeNode[] = []
  for (const node of nodes) {
    const childMatches = filterTree(node.children, needle)
    const selfMatch =
      node.label.toLowerCase().includes(needle) || node.type.toLowerCase().includes(needle)
    if (selfMatch || childMatches.length > 0) {
      out.push({ ...node, children: childMatches })
    }
  }
  return out
}

function findPageOfRef(
  pages: readonly { page_number: number; elements: readonly { self_ref?: string }[] }[],
  ref: string,
): number | null {
  for (const page of pages) {
    if (page.elements.some((e) => e.self_ref === ref)) return page.page_number
  }
  return null
}
</script>

<style scoped>
.parse-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.parse-body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}

.parse-drawer--closed {
  width: 38px;
}

.parse-structure {
  width: 320px;
  transition: width 180ms ease;
}

.parse-structure.parse-drawer--closed {
  width: 38px;
}

.drawer-toggle {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  margin-left: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 16px;
}

.drawer-toggle:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.properties-drawer {
  position: relative;
  grid-column: 3;
  grid-row: 1;
  width: 360px;
  min-width: 0;
  /* #303 — the drawer stacks the toggle, the Properties|Ask tab strip and
     the active panel, so it drives the column layout itself. */
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  border-left: 1px solid var(--border);
  background: var(--bg-surface);
  transition: width 180ms ease;
}

/* The drawer already draws the separator and owns the height budget — the
   panels inside it must not redeclare either. */
.properties-drawer :deep(.element-properties),
.properties-drawer :deep(.convo) {
  flex: 1;
  min-height: 0;
  height: auto;
  border-left: none;
}

.properties-drawer--closed {
  width: 38px;
}

.parse-body.properties-open {
  grid-template-columns: auto minmax(0, 1fr) 360px;
}

.properties-toggle {
  margin: 10px;
}

.properties-drawer:not(.properties-drawer--closed) .properties-toggle {
  left: 8px;
}

.parse-structure {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--bg-surface);
  min-height: 0;
  overflow: hidden;
  width: 320px;
  transition: width 180ms ease;
}

.parse-structure-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.parse-structure.parse-drawer--closed .parse-structure-header {
  justify-content: center;
  padding: 10px 0;
}

.parse-structure.parse-drawer--closed .drawer-toggle {
  margin-left: 0;
}

.parse-structure-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.parse-structure-count {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.parse-structure-actions {
  margin-left: auto;
  display: inline-flex;
  gap: 4px;
}

.tree-action-btn {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  line-height: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.tree-action-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.tree-action-btn svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}

.parse-structure-filter {
  margin: 8px 14px;
  padding: 6px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 12px;
}

.parse-stage {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
  min-height: 0;
}

/* #303 — preview takes the flexible space; the trace dock is a fixed 308px
   strip below it (Comfortable density). Both scroll internally. */
.parse-preview {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.parse-trace-dock {
  flex: 0 0 308px;
  margin-top: 12px;
}

/* #303 — right panel is now tabbed (Properties | Ask), inside the
   collapsible properties drawer. */
.parse-tabs {
  display: flex;
  gap: 2px;
  padding: 0 8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.parse-tab-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  padding: 10px 12px;
  font-size: 12.5px;
  color: var(--text-secondary);
  cursor: pointer;
}

.parse-tab-btn:hover {
  color: var(--text);
}

.parse-tab-btn.active {
  color: var(--text);
  font-weight: 600;
}

.parse-tab-btn.active::after {
  content: '';
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: -1px;
  height: 2px;
  background: var(--accent);
}

.parse-tab-pill {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  background: var(--accent-muted);
  color: var(--accent-hover);
  border-radius: 999px;
  padding: 0 6px;
  min-width: 16px;
  text-align: center;
}

.parse-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.parse-state--empty {
  flex-direction: column;
  gap: 12px;
}

.tab-action-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: white;
  font-size: 12px;
  cursor: pointer;
  transition: filter var(--transition);
}

.tab-action-cta:hover:not(:disabled) {
  filter: brightness(1.1);
}

.tab-action-cta:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.tab-action-spinner {
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

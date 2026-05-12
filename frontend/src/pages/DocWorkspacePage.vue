<template>
  <div class="workspace-page">
    <!-- Loading doc -->
    <div v-if="loadingDoc" class="workspace-loading">
      <span class="spinner" />
    </div>

    <!-- Doc error -->
    <div v-else-if="docError" class="workspace-error">
      <p>{{ docError }}</p>
      <RouterLink :to="{ name: ROUTES.DOCS_LIBRARY }" class="back-link">
        ← {{ t('workspace.backToLibrary') }}
      </RouterLink>
    </div>

    <template v-else-if="doc">
      <!-- Sticky header (#218) -->
      <DocWorkspaceHeader :doc="doc">
        <template #actions>
          <!-- View switcher (#263) — Parse / Chunk / Compare. Compare is
               rendered as a disabled placeholder until #270 (0.9.0). -->
          <div class="view-switcher" role="tablist" data-e2e="view-switcher">
            <button
              v-for="view in VIEWS"
              :key="view.key"
              class="view-btn"
              :class="{
                active: !view.disabled && activeMode === view.key,
                disabled: view.disabled || !isModeEnabled(view.key),
              }"
              role="tab"
              :aria-selected="!view.disabled && activeMode === view.key"
              :disabled="view.disabled || !isModeEnabled(view.key)"
              :title="viewTooltip(view)"
              :data-e2e="`view-${view.key}`"
              @click="onViewClick(view)"
            >
              {{ t(`workspace.tabs.${view.key}`) }}
            </button>
          </div>
          <!-- History drawer trigger (#267) — visible on every view. -->
          <button
            type="button"
            class="header-action-btn"
            :title="t('history.title')"
            data-e2e="history-btn"
            @click="historyOpen = true"
          >
            ↻ {{ t('history.title') }}
          </button>
          <!-- + New analysis (#266) — runs the analysis in place. Polls
               via analysisStore.run; the watcher below refreshes the
               workspace when status flips to COMPLETED. -->
          <button
            type="button"
            class="header-action-btn header-action-btn--primary"
            :disabled="analysisStore.running"
            :title="t('newAnalysis.title')"
            data-e2e="new-analysis-btn"
            @click="onNewAnalysis"
          >
            <span v-if="analysisStore.running" class="header-spinner" />
            <span v-else>+</span>
            {{ analysisStore.running ? t('newAnalysis.running') : t('newAnalysis.title') }}
          </button>
        </template>
      </DocWorkspaceHeader>

      <!-- History drawer (#267) — teleported to body. -->
      <HistoryDrawer
        :open="historyOpen"
        :analyses="documentStore.workspaceAnalyses"
        :current-id="documentStore.workspaceCurrentAnalysisId"
        @close="historyOpen = false"
        @set-current="onSetCurrentAnalysis"
      />

      <!-- View content — lazy loaded (#216). :key on docId forces a clean
           remount when navigating to a different doc, preventing stale state
           (bbox, selectedPage, etc.) from leaking. -->
      <div class="tab-content" role="tabpanel" data-e2e="tab-content">
        <Suspense>
          <DocParseTab v-if="activeMode === 'parse'" :key="id" :doc-id="id" />
          <DocChunkTab
            v-else-if="activeMode === 'chunk'"
            :key="id"
            :doc-id="id"
            :available-stores="doc.stores ?? []"
            :store-links="doc.storeLinks"
          />
        </Suspense>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import type { Document } from '../shared/types'
import { useAnalysisStore } from '../features/analysis/store'
import { useChunksStore } from '../features/chunks/store'
import { fetchDocument } from '../features/document/api'
import { useDocumentStore } from '../features/document/store'
import { useFeatureFlagStore } from '../features/feature-flags/store'
import { type DocMode } from '../shared/routing/modes'
import { resolveMode } from '../shared/routing/resolveMode'
import { useCrumbs } from '../shared/breadcrumb/store'
import { truncate } from '../shared/breadcrumb/text'
import type { Crumb } from '../shared/breadcrumb/types'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import DocWorkspaceHeader from '../features/document/ui/DocWorkspaceHeader.vue'
import HistoryDrawer from '../features/document/ui/HistoryDrawer.vue'
import DocParseTab from './DocParseTab.vue'
import DocChunkTab from './DocChunkTab.vue'

const props = defineProps<{ id: string; mode: DocMode }>()

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const flagStore = useFeatureFlagStore()
const documentStore = useDocumentStore()
const chunksStore = useChunksStore()
const analysisStore = useAnalysisStore()

const historyOpen = ref(false)

async function onSetCurrentAnalysis(analysisId: string): Promise<void> {
  documentStore.setWorkspaceAnalysis(analysisId)
  // The chunks tied to the canonical chunkset don't change with the
  // analysis pointer, but reload them anyway so any backend-side side
  // effect of the switch (e.g. a re-promotion) is reflected.
  await chunksStore.load(props.id)
  historyOpen.value = false
}

/**
 * In-place analysis launch (#266). Fires `analysisStore.run`, which
 * POSTs to /api/analyses and starts polling. The watcher below picks
 * up the COMPLETED transition and refreshes the workspace.
 */
async function onNewAnalysis(): Promise<void> {
  if (analysisStore.running) return
  await analysisStore.run(props.id)
}

// Watch analysisStore.running: when the in-place launch wraps up and
// the polling sees a COMPLETED status, refresh the workspace analyses
// list (the new run shows up in History + becomes the active one) and
// reload the chunks (the analysis promoter on the backend just wrote
// the canonical chunkset for the first analysis).
watch(
  () => analysisStore.running,
  async (now, prev) => {
    if (prev && !now) {
      const finished = analysisStore.currentAnalysis
      if (finished?.status === 'COMPLETED' && finished.documentId === props.id) {
        await documentStore.reloadWorkspaceAnalyses(props.id)
        await chunksStore.load(props.id)
      }
    }
  },
)

const doc = ref<Document | null>(null)
const loadingDoc = ref(true)
const docError = ref<string | null>(null)

const activeMode = ref<DocMode>(props.mode)

// Switcher entries. Compare is intentionally disabled — the view ships
// in 0.9.0; the button is kept visible so users can see the roadmap.
interface ViewEntry {
  key: DocMode | 'compare'
  disabled: boolean
}
const VIEWS: readonly ViewEntry[] = [
  { key: 'parse', disabled: false },
  { key: 'chunk', disabled: false },
  { key: 'compare', disabled: true },
]

const crumbs = computed<Crumb[]>(() => [
  { kind: 'link', label: t('breadcrumb.studio'), to: { name: ROUTES.HOME } },
  {
    kind: 'link',
    label: doc.value ? truncate(doc.value.filename, 40) : truncate(props.id, 40),
    to: { name: ROUTES.DOC_WORKSPACE, params: { id: props.id } },
  },
  { kind: 'leaf', label: t(`breadcrumb.mode.${activeMode.value}`) },
])
useCrumbs(crumbs)

function isModeEnabled(key: DocMode | 'compare'): boolean {
  if (key === 'compare') return false
  return flagStore.modeFlags()[key]
}

function viewTooltip(view: ViewEntry): string | undefined {
  if (view.disabled) return t('workspace.compareSoon')
  if (!isModeEnabled(view.key)) return t('workspace.modeDisabled')
  return undefined
}

function onViewClick(view: ViewEntry): void {
  if (view.disabled || view.key === 'compare') return
  switchMode(view.key)
}

function switchMode(m: DocMode): void {
  if (!isModeEnabled(m)) return
  activeMode.value = m
  router.replace({ query: { ...route.query, mode: m } })
}

async function loadDoc(): Promise<void> {
  loadingDoc.value = true
  docError.value = null
  doc.value = null
  const requestedId = props.id
  try {
    const fetched = await fetchDocument(requestedId)
    if (requestedId !== props.id) return
    doc.value = fetched
  } catch (e) {
    if (requestedId !== props.id) return
    docError.value = (e as Error).message || 'Failed to load document'
  } finally {
    if (requestedId === props.id) loadingDoc.value = false
  }
}

onMounted(async () => {
  await flagStore.load()

  const flags = flagStore.modeFlags()
  const resolved = resolveMode(props.mode, flags)
  if (!resolved) {
    router.replace({ name: ROUTES.DOCS_LIBRARY, query: { reason: 'no-mode-enabled' } })
    return
  }
  if (resolved !== props.mode) {
    router.replace({ query: { ...route.query, mode: resolved } })
  }
  activeMode.value = resolved

  await loadDoc()
})

watch(
  () => props.mode,
  (m) => {
    const flags = flagStore.modeFlags()
    const resolved = resolveMode(m, flags)
    if (resolved) activeMode.value = resolved
  },
)

watch(
  () => props.id,
  (newId, oldId) => {
    if (newId !== oldId) loadDoc()
  },
)
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.workspace-loading,
.workspace-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.workspace-error {
  color: var(--error);
}

.back-link {
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
}

.back-link:hover {
  color: var(--text);
}

.view-switcher {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-surface);
}

.view-btn {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-right: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.view-btn:last-child {
  border-right: none;
}

.view-btn:hover:not(.disabled) {
  color: var(--text);
  background: var(--bg-hover);
}

.view-btn.active {
  color: var(--accent);
  background: var(--bg-active);
}

.view-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.header-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.header-action-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.header-action-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.header-action-btn--primary:hover:not(:disabled) {
  filter: brightness(1.1);
  color: white;
  border-color: var(--accent);
}

.header-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.header-spinner {
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.tab-content {
  flex: 1;
  overflow: hidden;
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

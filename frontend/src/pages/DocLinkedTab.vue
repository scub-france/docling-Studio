<template>
  <div class="linked-tab" data-e2e="linked-tab">
    <LayersBar
      :elements="currentPageElements"
      :hidden-types="hiddenTypes"
      :show-labels="showLabels"
      @update:hidden-types="(next) => (hiddenTypes = next)"
      @update:show-labels="(next) => (showLabels = next)"
    />
    <div class="linked-body">
      <div class="linked-stage">
        <PagePreviewWithOverlay
          v-if="documentStore.workspacePages.length"
          :document-id="docId"
          :pages="documentStore.workspacePages"
          :current-page="currentPage"
          :hidden-types="hiddenTypes"
          :show-labels="showLabels"
          :highlighted-refs="highlightedRefs"
          @update:current-page="(p) => (currentPage = p)"
          @hover-element="onHoverElement"
          @click-element="onClickElement"
        />
        <div v-else-if="documentStore.workspaceLoading" class="linked-state">
          <span class="spinner" />
        </div>
        <div v-else class="linked-state">
          {{ t('linked.noAnalysis') }}
        </div>
      </div>
      <aside class="linked-aside">
        <StaleStoresStrip v-if="storeLinks?.length" :doc-id="docId" :store-links="storeLinks" />
        <ChunksPanel
          :doc-id="docId"
          :current-page="currentPage"
          :selected-chunk-id="selectedChunkId"
          :hovered-chunk-id="hoveredChunkId"
          @update:selected-chunk-id="(id) => (selectedChunkId = id)"
          @update:hovered-chunk-id="(id) => (hoveredChunkId = id)"
        />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Linked view (#264). Composes:
 *   - LAYERS bar (chip filters + Show labels)
 *   - Page preview with bbox overlay + paginator
 *   - StaleStoresStrip (#224)
 *   - Page-scoped chunks panel (read-mostly)
 *
 * Owns the cross-linking state between bbox hover/click and chunk
 * hover/selection — keeps `BboxCanvas` and `ChunksPanel` decoupled.
 */
import { computed, onMounted, ref, watch } from 'vue'
import type { DocStoreLink, PageElement } from '../shared/types'
import { useChunksStore } from '../features/chunks/store'
import { useDocumentStore } from '../features/document/store'
import { chunkForElement, elementRefsForChunk } from '../features/document/linkedView'
import LayersBar from '../features/document/ui/LayersBar.vue'
import PagePreviewWithOverlay from '../features/document/ui/PagePreviewWithOverlay.vue'
import ChunksPanel from '../features/chunks/ui/ChunksPanel.vue'
import StaleStoresStrip from '../features/chunks/ui/StaleStoresStrip.vue'
import { useI18n } from '../shared/i18n'

const props = defineProps<{
  docId: string
  availableStores: string[]
  storeLinks?: DocStoreLink[]
}>()

const { t } = useI18n()
const documentStore = useDocumentStore()
const chunksStore = useChunksStore()

const currentPage = ref(1)
const hiddenTypes = ref<Set<string>>(new Set())
const showLabels = ref(false)
const hoveredChunkId = ref<string | null>(null)
const selectedChunkId = ref<string | null>(null)

const currentPageElements = computed<PageElement[]>(() => {
  const page = documentStore.workspacePages.find((p) => p.page_number === currentPage.value)
  return page?.elements ?? []
})

const highlightedRefs = computed<ReadonlySet<string>>(() => {
  const id = hoveredChunkId.value ?? selectedChunkId.value
  if (!id) return new Set()
  const chunk = chunksStore.chunks.find((c) => c.id === id)
  if (!chunk) return new Set()
  return elementRefsForChunk(chunk, currentPage.value)
})

function onHoverElement(el: PageElement | null): void {
  // Element hover does not change chunk selection — only the reverse
  // direction is reactive. This avoids competing highlight sources.
  void el
}

function onClickElement(el: PageElement): void {
  const chunk = chunkForElement(el, currentPage.value, chunksStore.chunks)
  if (chunk) selectedChunkId.value = chunk.id
}

onMounted(async () => {
  await Promise.all([documentStore.loadWorkspace(props.docId), chunksStore.load(props.docId)])
  const first = documentStore.workspacePages[0]?.page_number
  if (first) currentPage.value = first
})

// availableStores is passed through to satisfy the existing prop contract
// from DocWorkspacePage; nothing in the Linked view consumes it directly
// (Push is owned by the legacy ChunksEditor for now — see design doc §3).
void props.availableStores

watch(
  () => props.docId,
  async (id) => {
    selectedChunkId.value = null
    hoveredChunkId.value = null
    await Promise.all([documentStore.loadWorkspace(id), chunksStore.load(id)])
    const first = documentStore.workspacePages[0]?.page_number
    if (first) currentPage.value = first
  },
)
</script>

<style scoped>
.linked-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.linked-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  flex: 1;
  min-height: 0;
}

.linked-stage {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
  min-height: 0;
}

.linked-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.linked-aside {
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border);
  min-height: 0;
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

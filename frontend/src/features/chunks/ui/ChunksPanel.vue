<template>
  <section class="chunks-panel" data-e2e="chunks-panel">
    <header class="chunks-panel-header">
      <h2 class="chunks-panel-title">{{ t('linked.chunks.title') }}</h2>
      <span class="chunks-panel-count">
        {{
          t('linked.chunks.count', {
            n: pageChunks.length,
            total: chunksStore.chunks.length,
            page: currentPage,
          })
        }}
      </span>
      <button
        type="button"
        class="strategy-btn"
        :disabled="true"
        :title="t('linked.strategySoon')"
        data-e2e="strategy-btn"
      >
        ⚙ {{ t('linked.strategy') }}
      </button>
    </header>

    <div v-if="chunksStore.loading" class="chunks-panel-state">
      <span class="spinner" />
    </div>
    <div v-else-if="chunksStore.error" class="chunks-panel-state chunks-panel-error">
      {{ chunksStore.error }}
    </div>
    <div v-else-if="!pageChunks.length" class="chunks-panel-state">
      {{ t('linked.chunks.emptyOnPage', { page: currentPage }) }}
    </div>

    <ul v-else class="chunks-panel-list" data-e2e="chunks-panel-list">
      <li
        v-for="chunk in pageChunks"
        :key="chunk.id"
        class="chunk-card"
        :class="{
          active: chunk.id === selectedChunkId,
          hovered: chunk.id === hoveredChunkId,
        }"
        :data-e2e="`chunk-card-${chunk.id}`"
        :ref="(el) => registerCard(chunk.id, el as HTMLElement | null)"
        @click="$emit('update:selectedChunkId', chunk.id)"
        @mouseenter="$emit('update:hoveredChunkId', chunk.id)"
        @mouseleave="$emit('update:hoveredChunkId', null)"
      >
        <div class="chunk-card-head">
          <span
            class="type-badge"
            :style="{
              background: colorFor(chunkBadgeType(chunk)) + '22',
              color: colorFor(chunkBadgeType(chunk)),
            }"
          >
            {{ chunkBadgeType(chunk) }}
          </span>
          <span class="chunk-seq">#{{ chunk.sequence }}</span>
          <span v-if="chunk.sourcePage !== null" class="chunk-page">p.{{ chunk.sourcePage }}</span>
          <span v-if="isEdited(chunk)" class="edited-badge">{{ t('linked.chunks.edited') }}</span>
          <span v-if="chunk.tokenCount" class="chunk-tokens">{{ chunk.tokenCount }}t</span>
        </div>
        <div class="chunk-card-body">
          {{ chunkTitle(chunk) || chunk.text }}
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * Page-scoped chunks panel for the Linked view (#264).
 *
 * Read-mostly: cards show the canonical chunk metadata and a brief text
 * preview. Selection / hover are exposed via v-model so the parent can
 * sync the bbox highlight on the preview. Inline edit, bulk actions,
 * push-to-store, and diff toggle remain in the legacy `ChunksEditor`
 * until #91 / #92 / #95 refactor them — by design we ship the Linked
 * view with a minimal read-only-ish surface.
 *
 * The Strategy button is rendered as disabled with a tooltip until
 * T7 (#268) wires the rechunk popover.
 */
import { computed, watch } from 'vue'
import type { DocChunk } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { colorFor } from '../../document/elementColors'
import { useChunksStore } from '../store'

const props = defineProps<{
  docId: string
  currentPage: number
  selectedChunkId?: string | null
  hoveredChunkId?: string | null
}>()

defineEmits<{
  'update:selectedChunkId': [id: string | null]
  'update:hoveredChunkId': [id: string | null]
}>()

const { t } = useI18n()
const chunksStore = useChunksStore()

const pageChunks = computed<DocChunk[]>(() => chunksStore.chunksOnPage(props.currentPage))

const cardRefs = new Map<string, HTMLElement>()

function registerCard(id: string, el: HTMLElement | null): void {
  if (el) cardRefs.set(id, el)
  else cardRefs.delete(id)
}

watch(
  () => props.selectedChunkId,
  (id) => {
    if (!id) return
    const el = cardRefs.get(id)
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  },
)

// --- formatting helpers ----------------------------------------------------

function chunkTitle(c: DocChunk): string {
  return c.headings[0] ?? ''
}

/**
 * Best-effort type for the badge. The doc-centric chunk doesn't carry an
 * element type — we use the *first* docItem's label as a proxy ("section
 * header", "table", etc.), falling back to "chunk" when none is set.
 */
function chunkBadgeType(c: DocChunk): string {
  const label = c.docItems[0]?.label
  if (!label) return 'chunk'
  return label.toLowerCase().replace(/[^a-z]+/g, '_')
}

function isEdited(c: DocChunk): boolean {
  return c.updatedAt !== c.createdAt
}

// Silence the linter for the docId prop — used by the parent in the
// v-model contract via $emit, the panel itself only reads chunks via the
// store (already loaded for this doc).
void props.docId
</script>

<style scoped>
.chunks-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  overflow: hidden;
}

.chunks-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.chunks-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.chunks-panel-count {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-right: auto;
}

.strategy-btn {
  font-size: 11px;
  padding: 3px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: not-allowed;
  opacity: 0.5;
}

.chunks-panel-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 20px;
}

.chunks-panel-error {
  color: var(--error);
}

.chunks-panel-list {
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow-y: auto;
  flex: 1;
}

.chunk-card {
  padding: 10px 12px;
  margin-bottom: 6px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.chunk-card:hover,
.chunk-card.hovered {
  border-color: var(--accent);
}

.chunk-card.active {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.chunk-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  margin-bottom: 6px;
  font-family: 'IBM Plex Mono', monospace;
}

.type-badge {
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 0.04em;
}

.chunk-seq,
.chunk-page,
.chunk-tokens {
  color: var(--text-muted);
}

.edited-badge {
  background: var(--accent-muted);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 4px;
}

.chunk-card-body {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.spinner {
  width: 24px;
  height: 24px;
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

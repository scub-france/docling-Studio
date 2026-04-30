<template>
  <div class="chunks-editor" data-e2e="chunks-editor">
    <!-- Toolbar -->
    <div class="chunks-toolbar">
      <div class="toolbar-left">
        <span class="chunk-count">{{ t('chunks.count', { n: chunksStore.chunks.length }) }}</span>
        <span v-if="chunksStore.saving" class="toolbar-saving">{{ t('chunks.saving') }}</span>
      </div>
      <div class="toolbar-right">
        <!-- Diff toggle (#221) -->
        <button
          class="toolbar-btn"
          :class="{ active: showDiff }"
          :disabled="!availableStores.length"
          @click="toggleDiff"
        >
          {{ showDiff ? t('chunks.diffClose') : t('chunks.diffToggle') }}
        </button>
        <!-- Push to store (#222) -->
        <button class="toolbar-btn toolbar-btn--primary" @click="openPushModal">
          {{ t('chunks.pushTitle') }}
        </button>
      </div>
    </div>

    <!-- Diff store selector -->
    <div v-if="showDiff" class="diff-bar">
      <label class="diff-label">{{ t('chunks.diffRef') }}</label>
      <select v-model="diffStore" class="diff-store-select" @change="reloadDiff">
        <option v-for="s in availableStores" :key="s" :value="s">{{ s }}</option>
      </select>
      <span v-if="chunksStore.diffing" class="diff-loading">…</span>
      <span v-else class="diff-counts">
        <span class="diff-added">+{{ diffSummary.added }}</span>
        <span class="diff-modified">~{{ diffSummary.modified }}</span>
        <span class="diff-removed">-{{ diffSummary.removed }}</span>
      </span>
    </div>

    <!-- Bulk selection bar -->
    <div v-if="selectedIds.size > 0" class="bulk-bar" data-e2e="bulk-bar">
      <span class="bulk-count">{{ t('chunks.selected', { n: selectedIds.size }) }}</span>
      <button class="bulk-btn" @click="bulkDrop">{{ t('chunks.bulkDrop') }}</button>
      <button class="bulk-btn" :disabled="selectedIds.size < 2" @click="bulkMerge">
        {{ t('chunks.bulkMerge') }}
      </button>
      <button class="bulk-btn bulk-btn--cancel" @click="selectedIds = new Set()">
        {{ t('chunks.bulkCancel') }}
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-if="!chunksStore.loading && !chunksStore.chunks.length"
      class="chunks-empty"
      data-e2e="chunks-empty"
    >
      <p>{{ t('chunks.empty') }}</p>
    </div>

    <!-- Loading -->
    <div v-else-if="chunksStore.loading" class="chunks-loading">
      <span class="spinner" />
    </div>

    <!-- Chunk list -->
    <div v-else class="chunk-list" data-e2e="chunk-list">
      <ChunkItem
        v-for="(chunk, idx) in chunksStore.chunks"
        :key="chunk.id"
        :chunk="chunk"
        :selected="selectedIds.has(chunk.id)"
        :saving-this="savingId === chunk.id"
        :is-first="idx === 0"
        :is-last="idx === chunksStore.chunks.length - 1"
        :diff-entry="diffMap.get(chunk.id) ?? null"
        @select-chunk="onSelectChunk"
        @toggle-select="onToggleSelect"
        @text-change="onTextChange"
        @title-change="onTitleChange"
        @merge-prev="(id) => onMerge(id, 'prev')"
        @merge-next="(id) => onMerge(id, 'next')"
        @split="onSplit"
        @drop="onDrop"
        @add="onAdd"
      />
      <!-- Add chunk at end -->
      <button class="add-chunk-end" @click="onAdd(undefined)">+ {{ t('chunks.add') }}</button>
    </div>

    <!-- Push to store modal (#222) -->
    <div v-if="pushModalOpen" class="modal-backdrop" @click.self="closePushModal">
      <div class="modal" role="dialog" :aria-label="t('chunks.pushTitle')" aria-modal="true">
        <h2 class="modal-title">{{ t('chunks.pushTitle') }}</h2>
        <label class="modal-label">{{ t('chunks.pushStore') }}</label>
        <input
          ref="pushInput"
          v-model="pushStoreName"
          class="modal-input"
          list="push-store-datalist"
          :placeholder="t('chunks.pushPlaceholder')"
          @keydown.enter.prevent="confirmPush"
          @keydown.escape.prevent="closePushModal"
        />
        <datalist id="push-store-datalist">
          <option v-for="s in availableStores" :key="s" :value="s" />
        </datalist>
        <div v-if="pushSummary" class="push-summary">
          {{ t('chunks.pushSummary', { embeds: pushSummary.embeds, tokens: pushSummary.tokens }) }}
        </div>
        <div class="modal-actions">
          <button class="modal-btn modal-btn--cancel" @click="closePushModal">
            {{ t('chunks.pushCancel') }}
          </button>
          <button
            class="modal-btn modal-btn--primary"
            :disabled="!pushStoreName.trim() || pushing"
            @click="confirmPush"
          >
            {{ pushing ? '…' : t('chunks.pushConfirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { useChunksStore } from '../store'
import { useI18n } from '../../../shared/i18n'
import type { ChunkDiff } from '../../../shared/types'
import ChunkItem from './ChunkItem.vue'

const props = defineProps<{
  docId: string
  availableStores: string[]
}>()

const emit = defineEmits<{
  nodeHighlight: [ref: string | null]
}>()

const { t } = useI18n()
const chunksStore = useChunksStore()

const selectedIds = ref<Set<string>>(new Set())
const savingId = ref<string | null>(null)

// --- Diff state (#221) ---
const showDiff = ref(false)
const diffStore = ref(props.availableStores[0] ?? '')

const diffMap = computed<Map<string, ChunkDiff>>(() => {
  const m = new Map<string, ChunkDiff>()
  if (!showDiff.value) return m
  for (const d of chunksStore.diff) m.set(d.chunkId, d)
  return m
})

const diffSummary = computed(() => {
  const counts = { added: 0, modified: 0, removed: 0 }
  for (const d of chunksStore.diff) {
    if (d.status === 'added') counts.added++
    else if (d.status === 'modified') counts.modified++
    else if (d.status === 'removed') counts.removed++
  }
  return counts
})

async function toggleDiff(): Promise<void> {
  if (showDiff.value) {
    showDiff.value = false
    chunksStore.clearDiff()
    return
  }
  if (!diffStore.value) diffStore.value = props.availableStores[0] ?? ''
  showDiff.value = true
  await chunksStore.loadDiff(props.docId, diffStore.value)
}

async function reloadDiff(): Promise<void> {
  if (showDiff.value && diffStore.value) {
    await chunksStore.loadDiff(props.docId, diffStore.value)
  }
}

// --- Push to store (#222) ---
const pushModalOpen = ref(false)
const pushStoreName = ref('')
const pushing = ref(false)
const pushSummary = ref<{ embeds: number; tokens: number } | null>(null)
const pushInput = ref<HTMLInputElement | null>(null)

function openPushModal(): void {
  pushStoreName.value = props.availableStores[0] ?? ''
  pushSummary.value = null
  pushModalOpen.value = true
  nextTick(() => pushInput.value?.focus())
}

function closePushModal(): void {
  pushModalOpen.value = false
  pushing.value = false
}

async function confirmPush(): Promise<void> {
  const store = pushStoreName.value.trim()
  if (!store || pushing.value) return
  pushing.value = true
  const jobId = await chunksStore.push(props.docId, store)
  pushing.value = false
  if (jobId) {
    closePushModal()
    alert(t('chunks.pushedJob', { jobId }))
  }
}

// --- Chunk interactions (#219 / #220) ---
function onSelectChunk(id: string): void {
  const chunk = chunksStore.chunks.find((c) => c.id === id)
  emit('nodeHighlight', chunk?.sourceNodeRef ?? null)
}

function onToggleSelect(id: string): void {
  const next = new Set(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

let saveTimer: ReturnType<typeof setTimeout> | null = null

function onTextChange(id: string, text: string): void {
  if (saveTimer) clearTimeout(saveTimer)
  savingId.value = id
  saveTimer = setTimeout(async () => {
    await chunksStore.updateText(props.docId, id, text)
    savingId.value = null
    saveTimer = null
  }, 600)
}

async function onTitleChange(id: string, title: string): Promise<void> {
  await chunksStore.updateTitle(props.docId, id, title)
}

async function onMerge(id: string, dir: 'prev' | 'next'): Promise<void> {
  const idx = chunksStore.chunks.findIndex((c) => c.id === id)
  if (idx === -1) return
  const other = dir === 'prev' ? chunksStore.chunks[idx - 1] : chunksStore.chunks[idx + 1]
  if (!other) return
  const ids = dir === 'prev' ? [other.id, id] : [id, other.id]
  await chunksStore.merge(props.docId, ids)
}

async function onSplit(id: string, cursorOffset: number): Promise<void> {
  await chunksStore.split(props.docId, id, cursorOffset)
}

async function onDrop(id: string): Promise<void> {
  await chunksStore.drop(props.docId, id)
  const next = new Set(selectedIds.value)
  next.delete(id)
  selectedIds.value = next
}

async function onAdd(afterId: string | undefined): Promise<void> {
  await chunksStore.add(props.docId, '', afterId)
}

// --- Bulk actions (#220) ---
async function bulkDrop(): Promise<void> {
  const ids = [...selectedIds.value]
  for (const id of ids) await chunksStore.drop(props.docId, id)
  selectedIds.value = new Set()
}

async function bulkMerge(): Promise<void> {
  const ids = [...selectedIds.value]
  if (ids.length < 2) return
  const ordered = chunksStore.chunks.filter((c) => selectedIds.value.has(c.id)).map((c) => c.id)
  await chunksStore.merge(props.docId, ordered)
  selectedIds.value = new Set()
}

onMounted(() => {
  chunksStore.load(props.docId)
})
</script>

<style scoped>
.chunks-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.chunks-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-count {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
}

.toolbar-saving {
  font-size: 11px;
  color: var(--accent);
}

.toolbar-btn {
  padding: 4px 10px;
  font-size: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition);
}

.toolbar-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.toolbar-btn.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.toolbar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.toolbar-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.toolbar-btn--primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
  color: white;
}

/* Diff bar */
.diff-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  background: color-mix(in srgb, var(--warning) 5%, var(--bg-surface));
  border-bottom: 1px solid var(--warning);
  font-size: 12px;
  flex-shrink: 0;
}

.diff-label {
  color: var(--text-muted);
  font-size: 11px;
}

.diff-store-select {
  font-size: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
  color: var(--text);
}

.diff-loading {
  color: var(--text-muted);
}

.diff-counts {
  display: flex;
  gap: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
}

.diff-added {
  color: var(--success);
}

.diff-modified {
  color: var(--warning);
}

.diff-removed {
  color: var(--error);
}

/* Bulk bar */
.bulk-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--accent-muted);
  border-bottom: 1px solid var(--accent);
  flex-shrink: 0;
}

.bulk-count {
  font-size: 12px;
  color: var(--accent);
  font-weight: 500;
  flex: 1;
}

.bulk-btn {
  padding: 3px 10px;
  font-size: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition);
}

.bulk-btn:hover:not(:disabled) {
  border-color: var(--error);
  color: var(--error);
}

.bulk-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.bulk-btn--cancel:hover {
  border-color: var(--border);
  color: var(--text-muted);
}

/* States */
.chunks-empty,
.chunks-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-muted);
  font-size: 13px;
}

/* List */
.chunk-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.add-chunk-end {
  padding: 8px;
  font-size: 12px;
  color: var(--text-muted);
  background: none;
  border: 1px dashed var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.add-chunk-end:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* Push modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  width: 380px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.modal-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.modal-input {
  width: 100%;
  font-size: 13px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  color: var(--text);
  outline: none;
  transition: border-color var(--transition);
  box-sizing: border-box;
}

.modal-input:focus {
  border-color: var(--accent);
}

.push-summary {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.modal-btn {
  padding: 6px 14px;
  font-size: 13px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.modal-btn--cancel {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.modal-btn--cancel:hover {
  border-color: var(--text-muted);
}

.modal-btn--primary {
  background: var(--accent);
  border: 1px solid var(--accent);
  color: white;
}

.modal-btn--primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.modal-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

<template>
  <div class="chunk-panel" data-e2e="chunk-panel">
    <!-- Chunking config — collapsible -->
    <div class="chunk-config">
      <button class="config-toggle" data-e2e="config-toggle" @click="configOpen = !configOpen">
        <svg
          class="config-chevron"
          data-e2e="config-chevron"
          :class="{ open: configOpen }"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="config-label">{{ t('chunking.settings') }}</span>
      </button>

      <div v-if="configOpen" class="config-body" data-e2e="config-body">
        <div class="config-row">
          <label class="config-label-sm">{{ t('chunking.chunkerType') }}</label>
          <select class="config-select" data-e2e="config-select" v-model="options.chunker_type">
            <option value="hybrid">Hybrid</option>
            <option value="hierarchical">Hierarchical</option>
          </select>
        </div>

        <div class="config-row">
          <label class="config-label-sm">{{ t('chunking.maxTokens') }}</label>
          <input
            type="number"
            class="config-input"
            data-e2e="config-input"
            v-model.number="options.max_tokens"
            min="64"
            max="8192"
            step="64"
          />
        </div>

        <div class="config-toggle-row" v-if="options.chunker_type === 'hybrid'">
          <label class="toggle-label">
            <input type="checkbox" v-model="options.merge_peers" class="toggle-input" />
            <span class="toggle-switch" />
            <span class="toggle-text">{{ t('chunking.mergePeers') }}</span>
          </label>
        </div>

        <div class="config-toggle-row" v-if="options.chunker_type === 'hybrid'">
          <label class="toggle-label">
            <input type="checkbox" v-model="options.repeat_table_header" class="toggle-input" />
            <span class="toggle-switch" />
            <span class="toggle-text">{{ t('chunking.repeatTableHeader') }}</span>
          </label>
        </div>

        <button
          class="chunk-btn primary"
          data-e2e="chunk-btn"
          :disabled="!canRechunk || chunkingStore.rechunking"
          @click="doRechunk"
        >
          <div v-if="chunkingStore.rechunking" class="spinner-sm" />
          {{ chunkingStore.rechunking ? t('chunking.chunking') : t('chunking.run') }}
        </button>

        <!-- Batch mode notice -->
        <div v-if="isBatchedAnalysis" class="batch-notice" data-e2e="batch-notice">
          <svg viewBox="0 0 20 20" fill="currentColor" class="batch-notice-icon">
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clip-rule="evenodd"
            />
          </svg>
          <span>{{ t('chunking.batchNotice') }}</span>
        </div>
      </div>
    </div>

    <!-- Chunks list -->
    <div class="chunk-results" data-e2e="chunk-results" v-if="pageChunks.length">
      <div class="chunk-summary" data-e2e="chunk-summary">
        {{ activeChunks.length }} {{ t('chunking.chunks') }}
      </div>
      <div class="chunk-list">
        <div
          class="chunk-card"
          data-e2e="chunk-card"
          v-for="(chunk, localIdx) in pagination.paginatedItems.value"
          :key="globalIndex(localIdx)"
          :class="{ highlighted: hoveredChunkIdx === globalIndex(localIdx) }"
          @mouseenter="onChunkHover(chunk, localIdx)"
          @mouseleave="onChunkLeave"
        >
          <div class="chunk-header">
            <span class="chunk-index" data-e2e="chunk-index">#{{ globalIndex(localIdx) + 1 }}</span>
            <span class="chunk-tokens" data-e2e="chunk-tokens" v-if="chunk.tokenCount">
              {{ chunk.tokenCount }} tokens
            </span>
            <span class="chunk-page" v-if="chunk.sourcePage"> p.{{ chunk.sourcePage }} </span>
            <span v-if="chunk.modified" class="chunk-modified" data-e2e="chunk-modified">
              {{ t('chunking.modified') }}
            </span>
            <button
              v-if="editingIdx !== globalIndex(localIdx)"
              class="chunk-edit-icon"
              data-e2e="chunk-edit-btn"
              :title="t('chunking.edit')"
              @click.stop="startEdit(globalIndex(localIdx), chunk.text)"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                <path
                  d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                />
              </svg>
            </button>
            <button
              class="chunk-delete-icon"
              data-e2e="chunk-delete-btn"
              :title="t('chunking.delete')"
              @click.stop="confirmDelete(globalIndex(localIdx))"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                <path
                  fill-rule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
          <div class="chunk-headings" v-if="chunk.headings.length">
            <span class="chunk-heading" v-for="h in chunk.headings" :key="h">{{ h }}</span>
          </div>

          <!-- Edit mode -->
          <div v-if="editingIdx === globalIndex(localIdx)" class="chunk-edit">
            <textarea
              ref="editTextarea"
              class="chunk-edit-textarea"
              data-e2e="chunk-edit-textarea"
              v-model="editText"
              rows="6"
            />
            <div class="chunk-edit-actions">
              <button
                class="chunk-edit-btn save"
                data-e2e="chunk-edit-save"
                :disabled="chunkingStore.saving"
                @click="saveEdit(globalIndex(localIdx))"
              >
                {{ chunkingStore.saving ? t('chunking.saving') : t('chunking.save') }}
              </button>
              <button
                class="chunk-edit-btn cancel"
                data-e2e="chunk-edit-cancel"
                @click="cancelEdit"
              >
                {{ t('chunking.cancel') }}
              </button>
            </div>
          </div>

          <!-- Read mode -->
          <div
            v-else
            class="chunk-text"
            data-e2e="chunk-text"
            @dblclick="startEdit(globalIndex(localIdx), chunk.text)"
          >
            {{ chunk.text }}
          </div>
        </div>
      </div>
    </div>

    <!-- Delete confirmation dialog -->
    <div v-if="deleteConfirmIdx !== -1" class="chunk-confirm-overlay" data-e2e="chunk-confirm">
      <div class="chunk-confirm-dialog">
        <p class="chunk-confirm-text">{{ t('chunking.deleteConfirm') }}</p>
        <div class="chunk-confirm-actions">
          <button
            class="chunk-confirm-btn danger"
            data-e2e="chunk-confirm-yes"
            :disabled="chunkingStore.deleting"
            @click="doDelete"
          >
            {{ chunkingStore.deleting ? t('chunking.deleting') : t('chunking.delete') }}
          </button>
          <button
            class="chunk-confirm-btn cancel"
            data-e2e="chunk-confirm-no"
            @click="deleteConfirmIdx = -1"
          >
            {{ t('chunking.cancel') }}
          </button>
        </div>
      </div>
    </div>

    <div
      class="chunk-empty"
      v-if="!pageChunks.length && !chunkingStore.rechunking && deleteConfirmIdx === -1"
    >
      <p>
        {{ chunks.length ? t('chunking.noChunksOnPage') : t('chunking.noChunks') }}
      </p>
    </div>

    <!-- Pagination -->
    <PaginationBar
      :page="pagination.page.value"
      :page-count="pagination.pageCount.value"
      :page-size="pagination.pageSize.value"
      @update:page="pagination.goTo($event)"
      @update:page-size="pagination.setPageSize($event)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useChunkingStore } from '../store'
import { useAnalysisStore } from '@/features/analysis'
import { useI18n } from '../../../shared/i18n'
import { usePagination } from '../../../shared/composables/usePagination'
import { PaginationBar } from '../../../shared/ui'
import type { Chunk, ChunkBbox, ChunkingOptions } from '../../../shared/types'

const props = defineProps<{
  currentPage: number
  analysisId: string | null
  analysisStatus: string | null
  hasDocumentJson: boolean
  chunks: Chunk[]
}>()

const emit = defineEmits<{
  'highlight-bboxes': [bboxes: ChunkBbox[]]
}>()

const chunkingStore = useChunkingStore()
const analysisStore = useAnalysisStore()
const { t } = useI18n()

const configOpen = ref(true)

const options = reactive<Required<ChunkingOptions>>({
  chunker_type: 'hybrid',
  max_tokens: 512,
  merge_peers: true,
  repeat_table_header: true,
})

const canRechunk = computed(() => {
  return props.analysisStatus === 'COMPLETED' && props.hasDocumentJson
})

/** True when the analysis was batched (document_json unavailable). */
const isBatchedAnalysis = computed(() => {
  return props.analysisStatus === 'COMPLETED' && !props.hasDocumentJson
})

const activeChunks = computed(() => props.chunks.filter((c) => !c.deleted))
const pageChunks = computed(() =>
  activeChunks.value.filter((c) => c.sourcePage === props.currentPage),
)
const pagination = usePagination(pageChunks, { pageSize: 20 })

function globalIndex(localIdx: number): number {
  const pageLocalIdx = (pagination.page.value - 1) * pagination.pageSize.value + localIdx
  const pageChunk = pageChunks.value[pageLocalIdx]
  return props.chunks.indexOf(pageChunk)
}

const deleteConfirmIdx = ref(-1)

function confirmDelete(chunkIndex: number) {
  deleteConfirmIdx.value = chunkIndex
}

async function doDelete() {
  if (!props.analysisId || deleteConfirmIdx.value === -1) return
  const chunks = await chunkingStore.deleteChunk(props.analysisId, deleteConfirmIdx.value)
  deleteConfirmIdx.value = -1
  analysisStore.updateChunks(chunks)
}

const editingIdx = ref(-1)
const editText = ref('')

function startEdit(idx: number, text: string) {
  editingIdx.value = idx
  editText.value = text
}

function cancelEdit() {
  editingIdx.value = -1
  editText.value = ''
}

async function saveEdit(chunkIndex: number) {
  if (!props.analysisId) return
  const allChunks = props.chunks
  const originalText = allChunks[chunkIndex]?.text
  if (editText.value === originalText) {
    cancelEdit()
    return
  }
  const chunks = await chunkingStore.updateChunkText(props.analysisId, chunkIndex, editText.value)
  analysisStore.updateChunks(chunks)
  cancelEdit()
}

const hoveredChunkIdx = ref(-1)

function onChunkHover(chunk: Chunk, localIdx: number) {
  hoveredChunkIdx.value = globalIndex(localIdx)
  const pageBboxes = chunk.bboxes.filter((b) => b.page === props.currentPage)
  emit('highlight-bboxes', pageBboxes)
}

function onChunkLeave() {
  hoveredChunkIdx.value = -1
  emit('highlight-bboxes', [])
}

async function doRechunk() {
  if (!props.analysisId) return
  const chunks = await chunkingStore.rechunk(props.analysisId, { ...options })
  analysisStore.updateChunks(chunks)
}
</script>

<style scoped>
.chunk-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.chunk-config {
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.config-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 16px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
}

.config-toggle:hover {
  color: var(--text);
}

.config-chevron {
  width: 14px;
  height: 14px;
  transition: transform 0.2s;
  transform: rotate(0deg);
}

.config-chevron.open {
  transform: rotate(90deg);
}

.config-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px 16px;
}

.config-label-sm {
  font-size: 12px;
  color: var(--text-secondary);
}

.config-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-select,
.config-input {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text);
  width: 100%;
}

.config-toggle-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
}

.toggle-input {
  display: none;
}

.toggle-switch {
  width: 32px;
  height: 18px;
  background: var(--bg-tertiary);
  border-radius: 9px;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: white;
  border-radius: 50%;
  transition: transform 0.2s;
}

.toggle-input:checked + .toggle-switch {
  background: var(--accent);
}

.toggle-input:checked + .toggle-switch::after {
  transform: translateX(14px);
}

.chunk-btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 4px;
}

.chunk-btn.primary {
  background: var(--accent);
  color: white;
}

.chunk-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chunk-results {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  min-height: 0;
}

.chunk-summary {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  cursor: default;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.chunk-card:hover {
  border-color: #f59e0b;
}

.chunk-card.highlighted {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.chunk-index {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
}

.chunk-tokens,
.chunk-page {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 1px 6px;
  border-radius: 4px;
}

.chunk-headings {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.chunk-heading {
  font-size: 11px;
  color: var(--accent);
  background: var(--accent-bg, rgba(99, 102, 241, 0.1));
  padding: 1px 6px;
  border-radius: 4px;
}

.chunk-modified {
  font-size: 10px;
  font-weight: 600;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.chunk-edit-icon {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.chunk-delete-icon {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.chunk-card:hover .chunk-edit-icon {
  opacity: 1;
}

.chunk-edit-icon:hover {
  color: var(--accent);
  background: var(--bg-tertiary);
}

.chunk-card:hover .chunk-delete-icon {
  opacity: 1;
}

.chunk-delete-icon:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.chunk-edit {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-edit-textarea {
  width: 100%;
  font-size: 12px;
  font-family: inherit;
  line-height: 1.5;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm, 4px);
  padding: 8px;
  resize: vertical;
  box-sizing: border-box;
}

.chunk-edit-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.chunk-edit-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.chunk-edit-btn {
  padding: 4px 12px;
  border: none;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.chunk-edit-btn.save {
  background: var(--accent);
  color: white;
}

.chunk-edit-btn.save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chunk-edit-btn.cancel {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.chunk-edit-btn.cancel:hover {
  color: var(--text);
}

.chunk-confirm-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.chunk-confirm-dialog {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  max-width: 300px;
  width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chunk-confirm-text {
  font-size: 13px;
  color: var(--text);
  margin: 0 0 16px;
  line-height: 1.5;
}

.chunk-confirm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.chunk-confirm-btn {
  padding: 6px 14px;
  border: none;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.chunk-confirm-btn.danger {
  background: #ef4444;
  color: white;
}

.chunk-confirm-btn.danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chunk-confirm-btn.cancel {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.chunk-confirm-btn.cancel:hover {
  color: var(--text);
}

.chunk-text {
  font-size: 12px;
  color: var(--text);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
  cursor: text;
}

.chunk-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-secondary);
  font-size: 13px;
}

/* Batch mode info notice */
.batch-notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 4px;
  padding: 10px 12px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}
.batch-notice-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--info);
  margin-top: 1px;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

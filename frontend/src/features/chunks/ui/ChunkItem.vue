<template>
  <div
    class="chunk-item"
    :class="[
      `chunk-item--${diffStatus}`,
      { 'chunk-item--selected': selected, 'chunk-item--editing': editing },
    ]"
    data-e2e="chunk-item"
    @click="$emit('selectChunk', chunk.id)"
  >
    <!-- Selection checkbox -->
    <input
      type="checkbox"
      class="chunk-select"
      :checked="selected"
      @change.stop="$emit('toggleSelect', chunk.id)"
      @click.stop
    />

    <!-- Body -->
    <div class="chunk-body">
      <!-- Title row -->
      <div class="chunk-title-row">
        <span
          v-if="!editingTitle"
          class="chunk-title"
          :class="{ 'chunk-title--empty': !chunk.title }"
          @dblclick.stop="startEditTitle"
        >
          {{ chunk.title || t('chunks.noTitle') }}
        </span>
        <input
          v-else
          ref="titleInput"
          v-model="draftTitle"
          class="chunk-title-input"
          @blur="commitTitle"
          @keydown.enter.prevent="commitTitle"
          @keydown.escape.prevent="cancelTitle"
          @click.stop
        />
        <span class="chunk-meta">
          <span v-if="chunk.pageRange">p.{{ chunk.pageRange[0] }}–{{ chunk.pageRange[1] }}</span>
          <span v-if="chunk.tokenCount">{{ chunk.tokenCount }}t</span>
          <span v-if="savingThis" class="saving-indicator">{{ t('chunks.saving') }}</span>
        </span>
      </div>

      <!-- Text -->
      <textarea
        v-if="editing"
        ref="textArea"
        v-model="draftText"
        class="chunk-text-edit"
        :placeholder="t('chunks.editPlaceholder')"
        rows="4"
        @blur="commitText"
        @click.stop
        @keydown.escape.prevent="cancelText"
      />
      <p
        v-else
        class="chunk-text"
        :class="{ 'chunk-text--removed': diffStatus === 'removed' }"
        @dblclick.stop="startEdit"
      >
        {{ chunk.text }}
      </p>

      <!-- Diff inline text diff -->
      <div v-if="diffStatus === 'modified' && chunk.id && diffEntry?.textDiff" class="chunk-diff">
        <code class="diff-text">{{ diffEntry.textDiff }}</code>
      </div>
    </div>

    <!-- Actions menu -->
    <div class="chunk-actions" @click.stop>
      <button
        class="chunk-action-btn"
        :title="t('chunks.mergePrev')"
        :disabled="isFirst"
        @click="$emit('mergePrev', chunk.id)"
      >
        ↑
      </button>
      <button
        class="chunk-action-btn"
        :title="t('chunks.mergeNext')"
        :disabled="isLast"
        @click="$emit('mergeNext', chunk.id)"
      >
        ↓
      </button>
      <button class="chunk-action-btn" :title="t('chunks.split')" @click="splitAtCurrentCursor">
        ⎀
      </button>
      <button class="chunk-action-btn" :title="t('chunks.add')" @click="$emit('add', chunk.id)">
        +
      </button>
      <button
        class="chunk-action-btn chunk-action-btn--danger"
        :title="t('chunks.drop')"
        @click="$emit('drop', chunk.id)"
      >
        ✕
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { DocChunk, ChunkDiff, ChunkDiffStatus } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  chunk: DocChunk
  selected?: boolean
  savingThis?: boolean
  isFirst?: boolean
  isLast?: boolean
  diffEntry?: ChunkDiff | null
}>()

const emit = defineEmits<{
  selectChunk: [id: string]
  toggleSelect: [id: string]
  textChange: [id: string, text: string]
  titleChange: [id: string, title: string]
  mergePrev: [id: string]
  mergeNext: [id: string]
  split: [id: string, cursorOffset: number]
  drop: [id: string]
  add: [afterId: string]
}>()

const { t } = useI18n()

const editing = ref(false)
const editingTitle = ref(false)
const draftText = ref('')
const draftTitle = ref('')
const textArea = ref<HTMLTextAreaElement | null>(null)
const titleInput = ref<HTMLInputElement | null>(null)

const diffStatus = computed<ChunkDiffStatus>(() => props.diffEntry?.status ?? 'unchanged')

function startEdit(): void {
  draftText.value = props.chunk.text
  editing.value = true
  nextTick(() => textArea.value?.focus())
}

function commitText(): void {
  if (draftText.value !== props.chunk.text) {
    emit('textChange', props.chunk.id, draftText.value)
  }
  editing.value = false
}

function cancelText(): void {
  editing.value = false
}

function startEditTitle(): void {
  draftTitle.value = props.chunk.title ?? ''
  editingTitle.value = true
  nextTick(() => titleInput.value?.focus())
}

function commitTitle(): void {
  if (draftTitle.value !== (props.chunk.title ?? '')) {
    emit('titleChange', props.chunk.id, draftTitle.value)
  }
  editingTitle.value = false
}

function cancelTitle(): void {
  editingTitle.value = false
}

function splitAtCurrentCursor(): void {
  if (!textArea.value) {
    emit('split', props.chunk.id, Math.floor(props.chunk.text.length / 2))
    return
  }
  emit('split', props.chunk.id, textArea.value.selectionStart)
}
</script>

<style scoped>
.chunk-item {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  transition:
    border-color var(--transition),
    background var(--transition);
  cursor: default;
}

.chunk-item:hover {
  border-color: var(--border-hover, var(--border));
}

.chunk-item--selected {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.chunk-item--added {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 8%, transparent);
}

.chunk-item--modified {
  border-color: var(--warning);
  background: color-mix(in srgb, var(--warning) 8%, transparent);
}

.chunk-item--removed {
  border-color: var(--error);
  background: color-mix(in srgb, var(--error) 8%, transparent);
  opacity: 0.7;
}

.chunk-select {
  margin-top: 2px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: var(--accent);
}

.chunk-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chunk-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: text;
}

.chunk-title--empty {
  color: var(--text-muted);
  font-style: italic;
  font-weight: 400;
}

.chunk-title-input {
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-surface);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  color: var(--text);
  flex: 1;
  outline: none;
}

.chunk-meta {
  display: flex;
  gap: 6px;
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
  flex-shrink: 0;
}

.saving-indicator {
  color: var(--accent);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0.4;
  }
}

.chunk-text {
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  cursor: text;
  margin: 0;
}

.chunk-text--removed {
  text-decoration: line-through;
  color: var(--error);
}

.chunk-text-edit {
  width: 100%;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: var(--bg-surface);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  resize: vertical;
  outline: none;
  line-height: 1.6;
}

.chunk-diff {
  padding: 4px 8px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--warning);
}

.diff-text {
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.chunk-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity var(--transition);
}

.chunk-item:hover .chunk-actions,
.chunk-item--selected .chunk-actions {
  opacity: 1;
}

.chunk-action-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition);
}

.chunk-action-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.chunk-action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.chunk-action-btn--danger:hover:not(:disabled) {
  border-color: var(--error);
  color: var(--error);
}
</style>

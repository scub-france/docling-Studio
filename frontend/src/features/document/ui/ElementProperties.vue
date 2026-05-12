<template>
  <aside class="element-properties" data-e2e="element-properties">
    <header class="element-properties-header">
      <h2 class="element-properties-title">{{ t('properties.title') }}</h2>
      <span v-if="element" class="element-properties-type" :style="typeStyle">
        {{ element.type }}
      </span>
    </header>

    <div v-if="!element" class="element-properties-empty" data-e2e="element-properties-empty">
      {{ t('properties.empty') }}
    </div>

    <div v-else class="element-properties-body">
      <!-- Identity -->
      <section class="props-section">
        <h3 class="props-section-title">{{ t('properties.identity') }}</h3>
        <dl class="props-list">
          <dt>{{ t('properties.id') }}</dt>
          <dd class="mono">{{ element.self_ref || '—' }}</dd>
          <dt>{{ t('properties.type') }}</dt>
          <dd>{{ element.type }}</dd>
          <dt>{{ t('properties.level') }}</dt>
          <dd>{{ element.level }}</dd>
          <dt>{{ t('properties.page') }}</dt>
          <dd>{{ pageNumber }}</dd>
        </dl>
      </section>

      <!-- Bounding box -->
      <section class="props-section">
        <h3 class="props-section-title">{{ t('properties.bbox') }}</h3>
        <dl class="props-list">
          <dt>x</dt>
          <dd class="mono">{{ bboxPct.x }}%</dd>
          <dt>y</dt>
          <dd class="mono">{{ bboxPct.y }}%</dd>
          <dt>{{ t('properties.width') }}</dt>
          <dd class="mono">{{ bboxPct.w }}%</dd>
          <dt>{{ t('properties.height') }}</dt>
          <dd class="mono">{{ bboxPct.h }}%</dd>
        </dl>
      </section>

      <!-- Extracted text -->
      <section class="props-section">
        <h3 class="props-section-title">{{ t('properties.extractedText') }}</h3>
        <p class="props-text" data-e2e="properties-extracted-text">
          {{ element.content || t('properties.noText') }}
        </p>
      </section>

      <!-- Linked chunk -->
      <section v-if="linkedChunk" class="props-section">
        <h3 class="props-section-title">{{ t('properties.linkedChunk') }}</h3>
        <p class="props-linked-chunk" data-e2e="properties-linked-chunk">
          <span class="mono">#c{{ linkedChunk.sequence }}</span>
          <span v-if="linkedChunk.tokenCount" class="props-linked-tokens"
            >{{ linkedChunk.tokenCount }}t</span
          >
        </p>

        <!-- Edit mode -->
        <div v-if="editing" class="props-edit" data-e2e="properties-edit">
          <textarea
            ref="textareaRef"
            v-model="draftText"
            class="props-edit-textarea"
            rows="6"
            :disabled="saving"
            @keydown.escape.prevent="cancel"
          />
          <div class="props-edit-actions">
            <button class="props-btn props-btn--cancel" :disabled="saving" @click="cancel">
              {{ t('properties.cancel') }}
            </button>
            <button
              class="props-btn props-btn--primary"
              :disabled="saving || draftText === linkedChunk.text"
              data-e2e="properties-save-btn"
              @click="save"
            >
              {{ saving ? t('properties.saving') : t('properties.save') }}
            </button>
          </div>
        </div>
        <button
          v-else
          type="button"
          class="props-edit-btn"
          data-e2e="properties-edit-btn"
          @click="startEdit"
        >
          ✎ {{ t('properties.editChunk') }}
        </button>
      </section>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * Right-side Properties panel of the Parse view (#265).
 *
 * Driven by the currently selected element on the canvas / tree. When
 * the element has a linked chunk (computed by the parent via
 * `chunkForElement`), an inline-edit affordance is shown — pressing it
 * swaps the chunk metadata block for a textarea bound to the chunk's
 * text. Save calls back through `@save-chunk` so the parent owns the
 * actual `chunksStore.updateText` invocation.
 *
 * OCR confidence / lang / model are intentionally omitted in this first
 * cut: the domain `PageElement` does not carry them today. A follow-up
 * issue can extend the domain + DTO when the data becomes available.
 */
import { computed, nextTick, ref, watch } from 'vue'
import type { DocChunk, PageElement } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { bboxToPercent } from '../bboxPercent'
import { colorFor } from '../elementColors'

const props = defineProps<{
  element: PageElement | null
  pageWidth: number
  pageHeight: number
  pageNumber: number
  linkedChunk: DocChunk | null
  saving?: boolean
}>()

const emit = defineEmits<{
  saveChunk: [chunkId: string, text: string]
}>()

const { t } = useI18n()

const editing = ref(false)
const draftText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const typeStyle = computed(() => {
  if (!props.element) return {}
  const c = colorFor(props.element.type)
  return { background: c + '22', color: c }
})

const bboxPct = computed(() => {
  if (!props.element) return { x: '0.0', y: '0.0', w: '0.0', h: '0.0' }
  return bboxToPercent(props.element.bbox, props.pageWidth, props.pageHeight)
})

function startEdit(): void {
  if (!props.linkedChunk) return
  draftText.value = props.linkedChunk.text
  editing.value = true
  nextTick(() => textareaRef.value?.focus())
}

function cancel(): void {
  editing.value = false
  draftText.value = ''
}

function save(): void {
  if (!props.linkedChunk) return
  if (draftText.value === props.linkedChunk.text) {
    cancel()
    return
  }
  emit('saveChunk', props.linkedChunk.id, draftText.value)
}

// Exit edit mode when the parent reports the save is done (saving goes
// back to false after being true) and the chunk text matches the draft.
watch(
  () => props.saving,
  (now, prev) => {
    if (prev && !now && props.linkedChunk?.text === draftText.value) {
      editing.value = false
    }
  },
)

// Switching to a different element discards the in-progress edit. The
// design call (#265 acceptance §11): drop the draft silently to keep
// the interaction snappy; users can re-open Edit chunk if needed.
watch(
  () => props.element?.self_ref,
  () => {
    if (editing.value) cancel()
  },
)
</script>

<style scoped>
.element-properties {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  overflow: hidden;
}

.element-properties-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.element-properties-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.element-properties-type {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.04em;
}

.element-properties-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 12px;
  padding: 20px;
  text-align: center;
}

.element-properties-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 16px;
}

.props-section + .props-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.props-section-title {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: 'IBM Plex Mono', monospace;
  margin: 0 0 8px;
}

.props-list {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 12px;
  margin: 0;
  font-size: 12px;
}

.props-list dt {
  color: var(--text-muted);
  font-weight: 400;
}

.props-list dd {
  margin: 0;
  color: var(--text);
  text-align: right;
}

.mono {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
}

.props-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.props-linked-chunk {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 12px;
}

.props-linked-tokens {
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
}

.props-edit {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.props-edit-textarea {
  width: 100%;
  padding: 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
  font-family: inherit;
}

.props-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.props-btn {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  cursor: pointer;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  transition: all var(--transition);
}

.props-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.props-btn--cancel:hover:not(:disabled) {
  color: var(--text);
}

.props-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.props-btn--primary:hover:not(:disabled) {
  filter: brightness(1.1);
}

.props-edit-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition);
}

.props-edit-btn:hover {
  background: var(--bg-hover);
  color: var(--accent);
  border-color: var(--accent);
}
</style>

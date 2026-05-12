<template>
  <div
    v-if="open"
    class="strategy-popover-backdrop"
    data-e2e="strategy-backdrop"
    @click.self="onClose"
  >
    <div
      class="strategy-popover"
      role="dialog"
      :aria-label="t('strategy.title')"
      data-e2e="strategy-popover"
    >
      <header class="strategy-popover-header">
        <h2 class="strategy-popover-title">{{ t('strategy.title') }}</h2>
        <button
          type="button"
          class="strategy-close"
          :aria-label="t('strategy.close')"
          @click="onClose"
        >
          ×
        </button>
      </header>

      <!-- Form -->
      <div v-if="step === 'form'" class="strategy-popover-body" data-e2e="strategy-form">
        <p class="strategy-popover-hint">{{ t('strategy.hint') }}</p>
        <div class="strategy-field">
          <label class="strategy-label" for="strategy-chunker-type">{{
            t('strategy.chunkerType')
          }}</label>
          <select
            id="strategy-chunker-type"
            v-model="draft.chunkerType"
            class="strategy-select"
            data-e2e="strategy-chunker-type"
          >
            <option value="hybrid">hybrid</option>
            <option value="hierarchical">hierarchical</option>
          </select>
        </div>

        <div class="strategy-field">
          <label class="strategy-label" for="strategy-max-tokens">{{
            t('strategy.maxTokens')
          }}</label>
          <input
            id="strategy-max-tokens"
            v-model.number="draft.maxTokens"
            type="number"
            min="64"
            max="8192"
            class="strategy-input"
            data-e2e="strategy-max-tokens"
          />
          <span class="strategy-hint">{{ t('strategy.maxTokensHint') }}</span>
        </div>

        <div v-if="draft.chunkerType === 'hybrid'" class="strategy-toggle-row">
          <label class="strategy-toggle">
            <input v-model="draft.mergePeers" type="checkbox" data-e2e="strategy-merge-peers" />
            <span>{{ t('strategy.mergePeers') }}</span>
          </label>
        </div>

        <div v-if="draft.chunkerType === 'hybrid'" class="strategy-toggle-row">
          <label class="strategy-toggle">
            <input
              v-model="draft.repeatTableHeader"
              type="checkbox"
              data-e2e="strategy-repeat-table-header"
            />
            <span>{{ t('strategy.repeatTableHeader') }}</span>
          </label>
        </div>

        <footer class="strategy-popover-actions">
          <button class="strategy-btn strategy-btn--secondary" @click="onClose">
            {{ t('strategy.cancel') }}
          </button>
          <button
            class="strategy-btn strategy-btn--primary"
            data-e2e="strategy-apply"
            :disabled="rechunking"
            @click="onApplyClick"
          >
            {{ rechunking ? t('strategy.rechunking') : t('strategy.apply') }}
          </button>
        </footer>
      </div>

      <!-- Confirm step (manual edits would be lost) -->
      <div v-else-if="step === 'confirm'" class="strategy-popover-body" data-e2e="strategy-confirm">
        <p class="strategy-popover-warning">⚠ {{ t('strategy.confirmWarning') }}</p>
        <p class="strategy-popover-hint">{{ t('strategy.confirmHint') }}</p>
        <footer class="strategy-popover-actions">
          <button class="strategy-btn strategy-btn--secondary" @click="step = 'form'">
            {{ t('strategy.confirmBack') }}
          </button>
          <button
            class="strategy-btn strategy-btn--danger"
            data-e2e="strategy-confirm-apply"
            :disabled="rechunking"
            @click="commitApply"
          >
            {{ rechunking ? t('strategy.rechunking') : t('strategy.confirmApply') }}
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Strategy popover (#268) — inline rechunk-options form anchored to the
 * Chunks panel header. Mirrors the domain `ChunkingOptions` (chunker
 * type, max tokens, merge peers, repeat table header). Apply triggers
 * `chunksStore.rechunk(docId, draft)`.
 *
 * Confirm step: when at least one chunk has been hand-edited
 * (`updatedAt !== createdAt`, surfaced via `hasManualEdits`), the apply
 * button routes through a warning screen first so the user does not
 * silently lose their edits.
 */
import { reactive, ref, watch } from 'vue'
import type { RechunkOptions } from '../../document/api'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  open: boolean
  hasManualEdits: boolean
  rechunking: boolean
}>()

const emit = defineEmits<{
  close: []
  apply: [options: RechunkOptions]
}>()

const { t } = useI18n()

type Step = 'form' | 'confirm'
const step = ref<Step>('form')

const DEFAULT_OPTIONS: Required<RechunkOptions> = {
  chunkerType: 'hybrid',
  maxTokens: 512,
  mergePeers: true,
  repeatTableHeader: true,
}

const draft = reactive<Required<RechunkOptions>>({ ...DEFAULT_OPTIONS })

// Reset the form + step every time the popover is (re-)opened.
watch(
  () => props.open,
  (now) => {
    if (now) {
      Object.assign(draft, DEFAULT_OPTIONS)
      step.value = 'form'
    }
  },
)

function onClose(): void {
  if (props.rechunking) return
  emit('close')
}

function onApplyClick(): void {
  // Gate behind a confirm step only when manual edits exist.
  if (props.hasManualEdits) {
    step.value = 'confirm'
    return
  }
  commitApply()
}

function commitApply(): void {
  emit('apply', sanitize(draft))
}

function sanitize(options: Required<RechunkOptions>): RechunkOptions {
  // Hierarchical chunker ignores merge / table-header options on the
  // backend; drop them client-side to keep the wire request honest.
  if (options.chunkerType === 'hierarchical') {
    return { chunkerType: options.chunkerType, maxTokens: options.maxTokens }
  }
  return { ...options }
}
</script>

<style scoped>
.strategy-popover-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.strategy-popover {
  width: 380px;
  max-width: 92vw;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.strategy-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}

.strategy-popover-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.strategy-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}

.strategy-close:hover {
  color: var(--text);
}

.strategy-popover-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-popover-hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.strategy-popover-warning {
  margin: 0;
  padding: 8px 10px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.4);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text);
  line-height: 1.5;
}

.strategy-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.strategy-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: 'IBM Plex Mono', monospace;
}

.strategy-select,
.strategy-input {
  padding: 6px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 12px;
  font-family: inherit;
}

.strategy-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.strategy-toggle-row {
  display: flex;
  align-items: center;
}

.strategy-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.strategy-popover-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  margin: 8px -14px -14px;
  padding: 10px 14px;
}

.strategy-btn {
  padding: 5px 14px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.strategy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-btn--secondary {
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.strategy-btn--secondary:hover:not(:disabled) {
  color: var(--text);
}

.strategy-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.strategy-btn--primary:hover:not(:disabled) {
  filter: brightness(1.1);
}

.strategy-btn--danger {
  background: #b91c1c;
  border-color: #b91c1c;
  color: white;
}

.strategy-btn--danger:hover:not(:disabled) {
  filter: brightness(1.15);
}
</style>

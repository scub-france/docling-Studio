<template>
  <div class="launch-modal-backdrop" data-e2e="ingest-launch-modal" @click.self="onCloseAttempt">
    <div
      class="launch-modal"
      role="dialog"
      aria-modal="true"
      :aria-label="t('ingest.launch.title')"
    >
      <div class="launch-modal-header">
        <h3>{{ t('ingest.launch.title') }}</h3>
        <button
          class="launch-modal-close"
          :aria-label="t('ingest.launch.close')"
          :disabled="running"
          data-e2e="ingest-launch-close"
          @click="onCloseAttempt"
        >
          ✕
        </button>
      </div>

      <p class="launch-modal-hint">{{ t('ingest.launch.hint') }}</p>

      <div v-if="!rows.length" class="launch-empty" data-e2e="ingest-launch-empty">
        {{ t('ingest.launch.empty') }}
      </div>

      <ul v-else class="launch-list">
        <li
          v-for="row in rows"
          :key="row.slug"
          class="launch-row"
          :class="{
            'launch-row--running': row.status === 'running',
            'launch-row--ok': row.status === 'success',
            'launch-row--err': row.status === 'failed',
          }"
          :data-e2e="`ingest-launch-row-${row.slug}`"
        >
          <label class="launch-check">
            <input
              v-model="row.selected"
              type="checkbox"
              :disabled="running || !row.connected"
              :data-e2e="`ingest-launch-check-${row.slug}`"
            />
            <span class="launch-store">
              <span
                class="launch-dot"
                :class="row.connected ? 'launch-dot--on' : 'launch-dot--off'"
              />
              <span class="launch-name">{{ row.name }}</span>
              <span class="launch-kind">{{ row.kind }}</span>
            </span>
          </label>

          <span class="launch-state" :class="`launch-state--${stateBucket(row.state)}`">
            {{ t(stateLabelKey(row.state)) }}
          </span>

          <span v-if="row.status === 'running'" class="launch-spinner-wrap">
            <span class="launch-spinner" />
          </span>
          <span v-else-if="row.status === 'success'" class="launch-result launch-result--ok">
            ✓ {{ t('ingest.launch.rowOk') }}
          </span>
          <span
            v-else-if="row.status === 'failed'"
            class="launch-result launch-result--err"
            :title="row.errorMessage ?? ''"
          >
            ✗ {{ row.errorMessage ?? t('ingest.launch.rowFailed') }}
          </span>
        </li>
      </ul>

      <div class="launch-modal-actions">
        <button
          class="launch-ghost"
          :disabled="running"
          data-e2e="ingest-launch-cancel"
          @click="onCloseAttempt"
        >
          {{ done ? t('ingest.launch.closeAction') : t('ingest.launch.cancel') }}
        </button>
        <button
          class="launch-primary"
          :disabled="!canConfirm"
          data-e2e="ingest-launch-confirm"
          @click="onConfirm"
        >
          <span v-if="running" class="launch-spinner launch-spinner--btn" />
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Launch-ingest modal (#283).
 *
 * Replaces the per-row push action that lived inline in the table —
 * the modal lets the user pick targets explicitly and shows per-row
 * progress as the pushes run sequentially.
 *
 * Sequencing: the modal pushes one store at a time to keep network /
 * driver-pool pressure predictable. Failures don't abort the loop;
 * each row carries its own status + error message.
 */
import { computed, reactive } from 'vue'
import type { DocStoreLink } from '../shared/types'
import type { StoreInfo } from '../features/store/api'
import { pushChunksToStore } from '../features/chunks/api'
import { useI18n } from '../shared/i18n'
import {
  type LaunchRow,
  buildRows,
  defaultLaunchSelection,
  hasSelection,
  isLaunchDone,
  selectedSlugs,
  stateBucket,
  stateLabelKey,
} from './DocIngestTab.logic'

const props = defineProps<{
  docId: string
  stores: readonly StoreInfo[]
  storeLinks?: readonly DocStoreLink[]
}>()

const emit = defineEmits<{
  /** Modal closed — parent reflects "any push succeeded" via @done. */
  close: []
  /** Emitted when the modal session ended and at least one push succeeded. */
  done: []
}>()

const { t } = useI18n()

const rows = reactive<LaunchRow[]>(
  defaultLaunchSelection(buildRows(props.stores, props.storeLinks)),
)

const running = computed(() => rows.some((r) => r.status === 'running'))
const done = computed(() => isLaunchDone(rows) && rows.some((r) => r.status !== 'idle'))

const canConfirm = computed(() => !running.value && hasSelection(rows) && !done.value)

const confirmLabel = computed(() => {
  if (done.value) return t('ingest.launch.closeAction')
  if (running.value) return t('ingest.launch.running')
  return t('ingest.launch.confirm')
})

function onCloseAttempt(): void {
  if (running.value) return
  emit('close')
  if (rows.some((r) => r.status === 'success')) emit('done')
}

async function onConfirm(): Promise<void> {
  // Done state → confirm button doubles as "Close" so the user gets
  // back to the Ingest tab without an extra click.
  if (done.value) {
    onCloseAttempt()
    return
  }
  const slugs = selectedSlugs(rows)
  for (const slug of slugs) {
    const row = rows.find((r) => r.slug === slug)
    if (!row) continue
    row.status = 'running'
    row.errorMessage = null
    try {
      await pushChunksToStore(props.docId, slug)
      row.status = 'success'
    } catch (e) {
      row.status = 'failed'
      row.errorMessage = (e as Error).message || t('ingest.launch.rowFailed')
    }
  }
}
</script>

<style scoped>
.launch-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.launch-modal {
  background: var(--bg-surface, #fff);
  border-radius: 8px;
  width: min(560px, 90vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  gap: 0.75rem;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
}
.launch-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}
.launch-modal-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}
.launch-modal-close {
  background: none;
  border: none;
  font-size: 1.1rem;
  cursor: pointer;
  color: var(--text-muted, #6b7280);
}
.launch-modal-close:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.launch-modal-hint {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted, #6b7280);
}
.launch-empty {
  padding: 1.5rem 0.5rem;
  text-align: center;
  color: var(--text-muted, #6b7280);
  font-size: 0.85rem;
}
.launch-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  overflow-y: auto;
}
.launch-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 6px;
  background: var(--bg-elevated, #f9fafb);
}
.launch-row--running {
  background: rgba(59, 130, 246, 0.06);
}
.launch-row--ok {
  border-color: rgba(34, 197, 94, 0.45);
  background: rgba(34, 197, 94, 0.06);
}
.launch-row--err {
  border-color: rgba(220, 38, 38, 0.45);
  background: rgba(220, 38, 38, 0.06);
}
.launch-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.launch-store {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.launch-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.launch-dot--on {
  background: #22c55e;
}
.launch-dot--off {
  background: #94a3b8;
}
.launch-name {
  font-weight: 500;
  color: var(--text, #111827);
}
.launch-kind {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
}
.launch-state {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.launch-state--notPushed {
  background: rgba(148, 163, 184, 0.15);
  color: #6b7280;
}
.launch-state--upToDate {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}
.launch-state--stale {
  background: rgba(234, 179, 8, 0.15);
  color: #b45309;
}
.launch-state--failed {
  background: rgba(220, 38, 38, 0.15);
  color: #dc2626;
}
.launch-spinner-wrap {
  display: flex;
  justify-content: center;
}
.launch-result {
  font-size: 0.75rem;
  font-family: 'IBM Plex Mono', monospace;
  white-space: nowrap;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.launch-result--ok {
  color: #16a34a;
}
.launch-result--err {
  color: #dc2626;
}
.launch-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.launch-ghost {
  padding: 0.45rem 1rem;
  border-radius: 5px;
  background: white;
  border: 1px solid var(--color-border, #d1d5db);
  cursor: pointer;
  font-size: 0.85rem;
}
.launch-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.launch-primary {
  padding: 0.45rem 1rem;
  border-radius: 5px;
  background: var(--accent, #2563eb);
  border: 1px solid var(--accent, #2563eb);
  color: white;
  cursor: pointer;
  font-size: 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.launch-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.launch-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(0, 0, 0, 0.2);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: launch-spin 0.6s linear infinite;
}
.launch-spinner--btn {
  border-color: rgba(255, 255, 255, 0.4);
  border-top-color: white;
}
@keyframes launch-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="history-backdrop"
      data-e2e="history-backdrop"
      @click.self="$emit('close')"
    >
      <aside
        class="history-drawer"
        role="dialog"
        :aria-label="t('history.title')"
        data-e2e="history-drawer"
      >
        <header class="history-header">
          <h2 class="history-title">{{ t('history.title') }}</h2>
          <button
            type="button"
            class="history-close"
            :aria-label="t('history.close')"
            @click="$emit('close')"
          >
            ×
          </button>
        </header>

        <div v-if="!analyses.length" class="history-empty" data-e2e="history-empty">
          {{ t('history.empty') }}
        </div>

        <ul v-else class="history-list" data-e2e="history-list">
          <li
            v-for="a in analyses"
            :key="a.id"
            class="history-item"
            :class="{ active: a.id === currentId }"
            :data-e2e="`history-item-${a.id}`"
          >
            <div class="history-item-head">
              <span class="history-status" :class="`history-status--${a.status.toLowerCase()}`">
                {{ a.status }}
              </span>
              <span class="history-time" :title="a.completedAt ?? a.createdAt">
                {{ formatRelativeTime(a.completedAt ?? a.createdAt) }}
              </span>
            </div>
            <div class="history-item-id">{{ a.id }}</div>
            <div class="history-item-actions">
              <span v-if="a.id === currentId" class="history-current-flag">
                {{ t('history.current') }}
              </span>
              <button
                v-else
                type="button"
                class="history-set-current"
                :disabled="a.status !== 'COMPLETED'"
                :title="a.status !== 'COMPLETED' ? t('history.notCompleted') : undefined"
                :data-e2e="`history-set-current-${a.id}`"
                @click="$emit('setCurrent', a.id)"
              >
                {{ t('history.setCurrent') }}
              </button>
            </div>
          </li>
        </ul>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * History drawer (#267) — right-side panel listing every analysis run
 * on the current document, newest first. Lets the user pin a different
 * analysis as the workspace's active one via "Set as current".
 *
 * Set-as-current is disabled on non-COMPLETED analyses (PENDING,
 * RUNNING, FAILED) — Parse / Chunk views can only render a completed
 * analysis's pages_json.
 *
 * The actual switch is handled by the parent: this component only
 * emits `setCurrent` with the analysis id.
 */
import type { Analysis } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { formatRelativeTime } from '../../../shared/format'

defineProps<{
  open: boolean
  analyses: readonly Analysis[]
  currentId: string | null
}>()

defineEmits<{
  close: []
  setCurrent: [analysisId: string]
}>()

const { t } = useI18n()
</script>

<style scoped>
.history-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.history-drawer {
  width: 400px;
  max-width: 92vw;
  height: 100%;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.history-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}

.history-close:hover {
  color: var(--text);
}

.history-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 12px;
  padding: 20px;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow-y: auto;
  flex: 1;
}

.history-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item.active {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.history-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.04em;
}

.history-status--completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.history-status--pending,
.history-status--running {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.history-status--failed {
  background: rgba(220, 38, 38, 0.15);
  color: #dc2626;
}

.history-time {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.history-item-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-actions {
  display: flex;
  justify-content: flex-end;
}

.history-current-flag {
  font-size: 11px;
  color: var(--accent);
  font-style: italic;
}

.history-set-current {
  padding: 4px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition);
}

.history-set-current:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.history-set-current:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>

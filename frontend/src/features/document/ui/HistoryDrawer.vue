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

        <div v-if="!versions.length" class="history-empty" data-e2e="history-empty">
          {{ t('history.empty') }}
        </div>

        <ul v-else class="history-list" data-e2e="history-list">
          <li
            v-for="v in versions"
            :key="v.id"
            class="history-item"
            :class="{ active: v.id === currentId }"
            :data-e2e="`history-item-${v.id}`"
          >
            <div class="history-item-head">
              <span class="history-kind" :class="`history-kind--${v.kind}`">
                {{ t(`history.kind.${v.kind}`) }}
              </span>
              <span class="history-time" :title="v.createdAt">
                {{ formatRelativeTime(v.createdAt) }}
              </span>
            </div>
            <div class="history-item-meta">
              <span class="history-meta-line">{{ v.summary }}</span>
              <span class="history-meta-line history-meta-mono">
                {{ t('history.chunksCount', { n: v.chunksSnapshotSize }) }}
              </span>
            </div>
            <div class="history-item-actions">
              <span v-if="v.id === currentId" class="history-current-flag">
                {{ t('history.current') }}
              </span>
              <button
                v-else
                type="button"
                class="history-set-current"
                :data-e2e="`history-set-current-${v.id}`"
                @click="$emit('setCurrent', v.id)"
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
 * History drawer (#267) — right-side panel listing every frozen
 * (analysis, chunks) version of the current document, newest first.
 * Lets the user pin a different version via "Set as current", which
 * routes to the backend restore endpoint (rewrites the live chunkset
 * from the version's snapshot).
 *
 * The actual switch is handled by the parent: this component only
 * emits `setCurrent` with the version id.
 */
import type { DocumentVersion } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { formatRelativeTime } from '../../../shared/format'

defineProps<{
  open: boolean
  versions: readonly DocumentVersion[]
  currentId: string | null
}>()

defineEmits<{
  close: []
  setCurrent: [versionId: string]
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
  text-align: center;
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

.history-kind {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.history-kind--analysis {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.history-kind--chunks {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.history-time {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.history-item-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-meta-line {
  font-size: 11px;
  color: var(--text-secondary);
}

.history-meta-mono {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
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

.history-set-current:hover {
  color: var(--accent);
  border-color: var(--accent);
}
</style>

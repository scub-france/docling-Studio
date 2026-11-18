<template>
  <div class="history-list">
    <div v-if="store.analyses.length === 0" class="history-empty">
      {{ t('history.empty') }}
    </div>
    <div v-else class="history-items">
      <div
        v-for="analysis in store.analyses"
        :key="analysis.id"
        class="history-item"
        @click="openAnalysis(analysis)"
      >
        <div class="item-main">
          <div class="item-header">
            <span class="item-filename">{{ analysis.documentFilename }}</span>
            <span
              v-if="analysis.status === 'COMPLETED'"
              class="item-status status-completed"
              :title="analysis.status"
            >
              <svg class="status-dot" viewBox="0 0 8 8" fill="currentColor">
                <circle cx="4" cy="4" r="4" />
              </svg>
            </span>
            <span v-else class="item-status" :class="statusClass(analysis.status)">
              {{ analysis.status }}
            </span>
          </div>
          <div class="item-meta">
            <span>{{ formatDate(analysis.createdAt) }}</span>
            <span v-if="analysis.completedAt"> — {{ duration(analysis) }}</span>
          </div>
        </div>
        <button class="item-delete" @click.stop="store.remove(analysis.id)" title="Delete">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useHistoryStore } from '../store'
import { useI18n } from '../../../shared/i18n'
import type { AnalysisSummary } from '../../../shared/types'

const store = useHistoryStore()
const router = useRouter()
const { t } = useI18n()

function openAnalysis(analysis: AnalysisSummary) {
  router.push({ name: 'studio', query: { analysisId: analysis.id } })
}

function statusClass(status: string) {
  return {
    'status-pending': status === 'PENDING',
    'status-running': status === 'RUNNING',
    'status-completed': status === 'COMPLETED',
    'status-failed': status === 'FAILED',
  }
}

function formatDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

function duration(analysis: AnalysisSummary) {
  if (!analysis.startedAt || !analysis.completedAt) return ''
  const ms = new Date(analysis.completedAt!).getTime() - new Date(analysis.startedAt!).getTime()
  const secs = Math.round(ms / 1000)
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`
}
</script>

<style scoped>
.history-list {
  padding: 0;
}

.history-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 60px 20px;
  font-size: 14px;
}

.history-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: all 150ms ease;
  cursor: pointer;
}

.history-item:hover {
  border-color: var(--accent);
  background: var(--bg-elevated);
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.item-filename {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-status {
  font-size: 11px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
}

.status-pending {
  background: rgba(234, 179, 8, 0.15);
  color: var(--warning);
}
.status-running {
  background: rgba(59, 130, 246, 0.15);
  color: var(--info);
}
.status-completed {
  background: none;
  color: var(--success);
  padding: 0;
}
.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error);
}

.item-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  font-family: 'IBM Plex Mono', monospace;
}

.item-delete {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 4px;
  display: flex;
  opacity: 0;
  transition: all var(--transition);
}

.history-item:hover .item-delete {
  opacity: 1;
}
.item-delete:hover {
  color: var(--error);
  background: rgba(239, 68, 68, 0.1);
}
.item-delete svg {
  width: 16px;
  height: 16px;
}
</style>

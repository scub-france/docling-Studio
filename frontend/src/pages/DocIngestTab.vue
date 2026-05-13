<template>
  <div class="ingest-tab" data-e2e="ingest-tab">
    <header class="ingest-header">
      <h2 class="ingest-title">{{ t('ingest.title') }}</h2>
      <button
        v-if="staleStoreCount > 0"
        type="button"
        class="ingest-push-all"
        :disabled="pushingAll"
        data-e2e="ingest-push-all"
        @click="onPushAll"
      >
        <span v-if="pushingAll" class="ingest-spinner" />
        <span v-else>↑</span>
        {{ t('ingest.pushAll') }} ({{ staleStoreCount }})
      </button>
    </header>

    <div v-if="loading" class="ingest-state">
      <span class="ingest-spinner ingest-spinner--lg" />
    </div>
    <div v-else-if="error" class="ingest-state ingest-state--error" data-e2e="ingest-error">
      {{ error }}
    </div>
    <div v-else-if="!stores.length" class="ingest-state" data-e2e="ingest-no-stores">
      {{ t('ingest.noStores') }}
    </div>
    <table v-else class="ingest-table" data-e2e="ingest-table">
      <thead>
        <tr>
          <th>{{ t('ingest.colStore') }}</th>
          <th>{{ t('ingest.colKind') }}</th>
          <th>{{ t('ingest.colLastPush') }}</th>
          <th>{{ t('ingest.colState') }}</th>
          <th class="ingest-col-actions">{{ t('ingest.colActions') }}</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in rows" :key="row.slug">
          <tr
            :class="{ 'ingest-row--stale': row.state === 'Stale' }"
            :data-e2e="`ingest-row-${row.slug}`"
          >
            <td class="ingest-store-name">
              <span
                class="ingest-store-dot"
                :class="{ connected: row.connected, disconnected: !row.connected }"
              />
              {{ row.name }}
            </td>
            <td class="mono">{{ row.kind }}</td>
            <td class="mono">{{ row.pushedAt ? formatRelativeTime(row.pushedAt) : '—' }}</td>
            <td>
              <span
                class="ingest-state-badge"
                :class="`ingest-state-badge--${stateBucket(row.state)}`"
              >
                {{ t(stateLabelKey(row.state)) }}
              </span>
            </td>
            <td class="ingest-col-actions">
              <button
                type="button"
                class="ingest-diff-btn"
                :class="{ active: expandedSlug === row.slug }"
                :disabled="!row.pushedAt"
                :data-e2e="`ingest-diff-${row.slug}`"
                @click="toggleDiff(row.slug)"
              >
                {{ expandedSlug === row.slug ? t('ingest.diffHide') : t('ingest.diffShow') }}
              </button>
              <button
                type="button"
                class="ingest-push-btn"
                :disabled="pushingSlug === row.slug || !row.connected"
                :data-e2e="`ingest-push-${row.slug}`"
                @click="onPush(row.slug)"
              >
                <span v-if="pushingSlug === row.slug" class="ingest-spinner" />
                <span v-else>↑</span>
                {{ pushingSlug === row.slug ? t('ingest.pushBtn.running') : t('ingest.pushBtn') }}
              </button>
            </td>
          </tr>
          <tr v-if="expandedSlug === row.slug" class="ingest-diff-row">
            <td colspan="5">
              <div v-if="diffLoading" class="ingest-diff-loading">
                <span class="ingest-spinner" />
              </div>
              <div v-else-if="diffError" class="ingest-state--error">{{ diffError }}</div>
              <div v-else class="ingest-diff-counts" :data-e2e="`ingest-diff-counts-${row.slug}`">
                <span class="ingest-diff-added">
                  {{ t('ingest.diffAdded', { n: diffSummary.added }) }}
                </span>
                <span class="ingest-diff-modified">
                  {{ t('ingest.diffModified', { n: diffSummary.modified }) }}
                </span>
                <span class="ingest-diff-removed">
                  {{ t('ingest.diffRemoved', { n: diffSummary.removed }) }}
                </span>
                <span class="ingest-diff-unchanged">
                  {{ t('ingest.diffUnchanged', { n: diffSummary.unchanged }) }}
                </span>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
/**
 * Ingest view (#225) — per-store push state for the current document.
 *
 * Replaces the deferred "Compare" slot in the workspace switcher
 * (Parse | Chunk | Ingest). Lists every configured store, surfaces
 * the document's ingestion state per store (never pushed / up-to-date
 * / stale / failed), and offers a one-click push action. Diff is
 * expand-on-click per row.
 *
 * Backend orchestration stays granular (#269 audit rule): this view
 * sequences `GET /api/stores`, `GET /api/documents/{id}/diff?store=`
 * and `POST /api/documents/{id}/chunks/push` from the frontend.
 */
import { computed, onMounted, ref } from 'vue'
import type { ChunkDiff, DocStoreLink } from '../shared/types'
import { fetchChunkDiff, pushChunksToStore } from '../features/chunks/api'
import { fetchStores, type StoreInfo } from '../features/store/api'
import { formatRelativeTime } from '../shared/format'
import { useI18n } from '../shared/i18n'
import {
  type IngestRow,
  buildRows,
  countStalePushable,
  stateBucket,
  stateLabelKey,
  summarizeDiff,
} from './DocIngestTab.logic'

const props = defineProps<{
  docId: string
  storeLinks?: DocStoreLink[]
}>()

// Emitted when at least one push succeeded — the parent
// (DocWorkspacePage) refetches the document so `storeLinks` reflect
// the new push state immediately, instead of staying stale until
// navigation. Required for the "Stale → Up-to-date" transition to be
// visible in the row right after the action.
const emit = defineEmits<{ pushed: [] }>()

const { t } = useI18n()

const stores = ref<StoreInfo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const pushingSlug = ref<string | null>(null)
const pushingAll = ref(false)
const expandedSlug = ref<string | null>(null)
const diffLoading = ref(false)
const diffError = ref<string | null>(null)
const diffEntries = ref<ChunkDiff[]>([])

const rows = computed<IngestRow[]>(() => buildRows(stores.value, props.storeLinks))

const staleStoreCount = computed(() => countStalePushable(rows.value))

const diffSummary = computed(() => summarizeDiff(diffEntries.value))

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    stores.value = await fetchStores()
  } catch (e) {
    error.value = (e as Error).message || 'Failed to load stores'
  } finally {
    loading.value = false
  }
}

async function toggleDiff(slug: string): Promise<void> {
  if (expandedSlug.value === slug) {
    expandedSlug.value = null
    return
  }
  expandedSlug.value = slug
  diffLoading.value = true
  diffError.value = null
  diffEntries.value = []
  try {
    diffEntries.value = await fetchChunkDiff(props.docId, slug)
  } catch (e) {
    diffError.value = (e as Error).message || 'Failed to load diff'
  } finally {
    diffLoading.value = false
  }
}

async function onPush(slug: string): Promise<void> {
  if (pushingSlug.value) return
  pushingSlug.value = slug
  let succeeded = false
  try {
    await pushChunksToStore(props.docId, slug)
    succeeded = true
    // Refresh the stores list so connected / counts re-render.
    await load()
    // If the row was expanded with a diff, refresh it too.
    if (expandedSlug.value === slug) {
      const slugToRefresh = slug
      expandedSlug.value = null
      await toggleDiff(slugToRefresh)
    }
  } catch (e) {
    error.value = (e as Error).message || 'Push failed'
  } finally {
    pushingSlug.value = null
  }
  // Ask the parent to refetch the doc so `storeLinks` (and thus the
  // per-row state) reflect this push immediately. Emitted AFTER the
  // local refresh so the parent's `loadDoc` doesn't race with our
  // own `load()`.
  if (succeeded) emit('pushed')
}

async function onPushAll(): Promise<void> {
  if (pushingAll.value) return
  pushingAll.value = true
  let anySucceeded = false
  try {
    const stale = rows.value.filter((r) => r.state === 'Stale' && r.connected)
    for (const r of stale) {
      pushingSlug.value = r.slug
      try {
        await pushChunksToStore(props.docId, r.slug)
        anySucceeded = true
      } catch (e) {
        error.value = (e as Error).message || `Push failed for ${r.slug}`
        // Don't break the loop — keep pushing the rest.
      }
    }
    await load()
  } finally {
    pushingSlug.value = null
    pushingAll.value = false
  }
  if (anySucceeded) emit('pushed')
}

onMounted(load)
</script>

<style scoped>
.ingest-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 16px 20px;
  background: var(--bg-surface);
}

.ingest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.ingest-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.ingest-push-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: white;
  font-size: 12px;
  cursor: pointer;
  transition: filter var(--transition);
}

.ingest-push-all:hover:not(:disabled) {
  filter: brightness(1.1);
}

.ingest-push-all:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.ingest-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 40px 20px;
  text-align: center;
}

.ingest-state--error {
  color: var(--error);
}

.ingest-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.ingest-table thead th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.ingest-table tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.ingest-table tbody tr:hover:not(.ingest-diff-row) {
  background: var(--bg-elevated);
}

.ingest-row--stale {
  background: rgba(234, 179, 8, 0.05);
}

.ingest-store-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--text);
}

.ingest-store-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ingest-store-dot.connected {
  background: #22c55e;
}

.ingest-store-dot.disconnected {
  background: #94a3b8;
}

.mono {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
}

.ingest-col-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  white-space: nowrap;
}

.ingest-state-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.ingest-state-badge--notPushed {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.ingest-state-badge--upToDate {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.ingest-state-badge--stale {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.ingest-state-badge--failed {
  background: rgba(220, 38, 38, 0.15);
  color: #dc2626;
}

.ingest-diff-btn,
.ingest-push-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition);
}

.ingest-diff-btn:hover:not(:disabled),
.ingest-push-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.ingest-diff-btn.active {
  border-color: var(--accent);
  color: var(--accent);
}

.ingest-diff-btn:disabled,
.ingest-push-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ingest-diff-row td {
  padding: 8px 24px 16px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.ingest-diff-loading {
  display: flex;
  justify-content: center;
  padding: 8px;
}

.ingest-diff-counts {
  display: flex;
  gap: 16px;
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
}

.ingest-diff-added {
  color: #22c55e;
}

.ingest-diff-modified {
  color: #eab308;
}

.ingest-diff-removed {
  color: #dc2626;
}

.ingest-diff-unchanged {
  color: var(--text-muted);
}

.ingest-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.ingest-spinner--lg {
  width: 24px;
  height: 24px;
  border-width: 2px;
  color: var(--accent);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

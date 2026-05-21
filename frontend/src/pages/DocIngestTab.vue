<template>
  <div class="ingest-tab" data-e2e="ingest-tab">
    <header class="ingest-header">
      <h2 class="ingest-title">{{ t('ingest.title') }}</h2>
      <button
        type="button"
        class="ingest-launch-cta"
        :disabled="!hasStores || loading"
        data-e2e="ingest-launch-cta"
        @click="onLaunchClick"
      >
        <span class="ingest-launch-icon">↑</span>
        {{ t('ingest.launchCta')
        }}<span
          v-if="pendingPushCount > 0"
          class="ingest-launch-badge"
          data-e2e="ingest-launch-badge"
        >
          {{ pendingPushCount }}
        </span>
      </button>
    </header>

    <div v-if="loading" class="ingest-state">
      <span class="ingest-spinner ingest-spinner--lg" />
    </div>
    <div v-else-if="error" class="ingest-state ingest-state--error" data-e2e="ingest-error">
      {{ error }}
    </div>
    <div v-else-if="!hasStores" class="ingest-state" data-e2e="ingest-no-stores">
      <p>{{ t('ingest.noStores') }}</p>
      <RouterLink :to="{ name: ROUTES.STORES_LIST }" class="ingest-no-stores-link">
        {{ t('ingest.noStoresAction') }}
      </RouterLink>
    </div>
    <div v-else-if="!history.length" class="ingest-state" data-e2e="ingest-no-history">
      <p>{{ t('ingest.noHistory') }}</p>
      <p class="ingest-no-history-hint">{{ t('ingest.noHistoryHint') }}</p>
    </div>

    <section v-else class="ingest-history" data-e2e="ingest-history">
      <header class="ingest-history-header">
        <h3 class="ingest-history-title">{{ t('ingest.historyTitle') }}</h3>
        <span class="ingest-history-total">
          {{ t('ingest.historyCount', { n: total }) }}
        </span>
      </header>
      <div class="ingest-history-headers" aria-hidden="true">
        <span class="ingest-col ingest-col-when">{{ t('ingest.colWhen') }}</span>
        <span class="ingest-col ingest-col-store">{{ t('ingest.colTarget') }}</span>
        <span class="ingest-col ingest-col-count">{{ t('ingest.colChunks') }}</span>
        <span class="ingest-col ingest-col-hash">{{ t('ingest.colVersion') }}</span>
      </div>
      <ul class="ingest-history-list">
        <li
          v-for="entry in history"
          :key="entry.id"
          class="ingest-history-row"
          :data-e2e="`ingest-history-row-${entry.id}`"
        >
          <div class="ingest-col ingest-col-when ingest-history-when">
            <span
              class="ingest-history-when-rel"
              :title="entry.pushedAt ? formatAbsolute(entry.pushedAt) : ''"
            >
              {{ entry.pushedAt ? formatRelativeTime(entry.pushedAt) : '—' }}
            </span>
          </div>
          <div class="ingest-col ingest-col-store ingest-history-target">
            <span class="ingest-history-store">{{ entry.displayName }}</span>
            <span v-if="entry.storeKind" class="ingest-history-kind">{{ entry.storeKind }}</span>
            <span v-if="entry.storeDeleted" class="ingest-history-tag">
              {{ t('ingest.storeDeleted') }}
            </span>
          </div>
          <div class="ingest-col ingest-col-count ingest-history-count">
            {{ entry.chunkCount }}
          </div>
          <div class="ingest-col ingest-col-hash ingest-history-hash">
            <code :title="entry.chunksetHash">{{ entry.chunksetHash.slice(0, 8) }}</code>
          </div>
        </li>
      </ul>
      <div v-if="hasMore" class="ingest-history-more">
        <button
          type="button"
          class="ingest-more-btn"
          :disabled="loadingMore"
          data-e2e="ingest-history-load-more"
          @click="loadMore"
        >
          <span v-if="loadingMore" class="ingest-spinner" />
          {{ t('ingest.loadMore') }}
        </button>
      </div>
    </section>

    <IngestLaunchDialog
      v-if="dialogOpen"
      :doc-id="docId"
      :stores="stores"
      :store-links="storeLinks"
      @close="dialogOpen = false"
      @done="onLaunchDone"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * Ingest view (#225, redesigned in #283).
 *
 * Replaces the per-store table from #225 with the launch-CTA +
 * history-list shell. Rationale captured in #283:
 *
 *   - The action (push) deserves a primary CTA, not a buried table
 *     cell.
 *   - The timeline of "what was actually ingested when" matters more
 *     than the current per-store state — the live state is one
 *     click away (the modal lists it).
 *
 * Per-store state lives inside `IngestLaunchDialog` now. The data
 * source for the history is `GET /api/documents/{id}/chunks/pushes`,
 * a newest-first paginated feed of `chunk_pushes` rows joined with
 * their store identity.
 */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { DocStoreLink } from '../shared/types'
import { fetchChunkPushes, type ChunkPushEntry } from '../features/chunks/api'
import { fetchStores, type StoreInfo } from '../features/store/api'
import { formatAbsolute, formatRelativeTime } from '../shared/format'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import IngestLaunchDialog from './IngestLaunchDialog.vue'
import { type HistoryDisplayEntry, buildRows, toHistoryEntry } from './DocIngestTab.logic'

const props = defineProps<{
  docId: string
  storeLinks?: DocStoreLink[]
}>()

// Emitted when at least one push completed successfully — the
// parent (DocWorkspacePage) refetches the document so `storeLinks`
// reflects the new push state.
const emit = defineEmits<{ pushed: [] }>()

const { t } = useI18n()

const PAGE_SIZE = 50

const stores = ref<StoreInfo[]>([])
const history = ref<HistoryDisplayEntry[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref<string | null>(null)
const dialogOpen = ref(false)

const hasStores = computed(() => stores.value.length > 0)
const hasMore = computed(() => history.value.length < total.value)

// Pending-push hint on the CTA: count of connected stores that are
// Stale or NotPushed — same set the launch modal pre-checks. Surfaces
// at-a-glance "there's work to do" without forcing the user to open
// the modal first.
const pendingPushCount = computed(() => {
  const rows = buildRows(stores.value, props.storeLinks)
  return rows.filter((r) => r.connected && (r.state === 'Stale' || r.state === 'NotPushed')).length
})

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [storeList, pushList] = await Promise.all([
      fetchStores(),
      fetchChunkPushes(props.docId, { limit: PAGE_SIZE, offset: 0 }),
    ])
    stores.value = storeList
    history.value = pushList.items.map(toHistoryEntry)
    total.value = pushList.total
  } catch (e) {
    error.value = (e as Error).message || t('ingest.loadError')
  } finally {
    loading.value = false
  }
}

async function loadMore(): Promise<void> {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    const offset = history.value.length
    const page = await fetchChunkPushes(props.docId, { limit: PAGE_SIZE, offset })
    history.value = [...history.value, ...(page.items as ChunkPushEntry[]).map(toHistoryEntry)]
    total.value = page.total
  } catch (e) {
    error.value = (e as Error).message || t('ingest.loadError')
  } finally {
    loadingMore.value = false
  }
}

function onLaunchClick(): void {
  dialogOpen.value = true
}

async function onLaunchDone(): Promise<void> {
  // The modal already ran the pushes; we just refresh our own
  // history list to reflect them. The parent gets notified so it
  // can refetch the document for storeLinks updates.
  dialogOpen.value = false
  emit('pushed')
  await load()
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
  margin-bottom: 16px;
  flex-shrink: 0;
}

.ingest-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.ingest-launch-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: filter var(--transition);
}

.ingest-launch-cta:hover:not(:disabled) {
  filter: brightness(1.1);
}

.ingest-launch-cta:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ingest-launch-icon {
  font-size: 14px;
}

.ingest-launch-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  margin-left: 8px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.02em;
}

.ingest-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 40px 20px;
  text-align: center;
  gap: 8px;
}

.ingest-state--error {
  color: var(--error);
}

.ingest-no-stores-link {
  font-size: 12px;
  color: var(--accent);
  text-decoration: underline;
}

.ingest-no-history-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
}

.ingest-history {
  flex: 1;
  overflow-y: auto;
}

.ingest-history-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}

.ingest-history-title {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin: 0;
  font-family: 'IBM Plex Mono', monospace;
}

.ingest-history-total {
  font-size: 10px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.ingest-history-headers,
.ingest-history-row {
  display: grid;
  grid-template-columns: 120px 1fr 80px 100px;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
}

.ingest-history-headers {
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.ingest-col {
  font-size: 11px;
}

/* Column header labels. */
.ingest-history-headers .ingest-col {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.ingest-col-count {
  text-align: right;
}

.ingest-col-hash {
  text-align: left;
}

.ingest-history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.ingest-history-row {
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  transition: background var(--transition);
}

.ingest-history-row:last-child {
  border-bottom: none;
}

.ingest-history-row:hover {
  background: var(--bg-elevated);
}

.ingest-history-when {
  color: var(--text-muted);
}

.ingest-history-when-rel {
  cursor: help;
}

.ingest-history-target {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.ingest-history-store {
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ingest-history-kind {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 1px 5px;
  background: var(--bg-elevated);
  border-radius: 3px;
  flex-shrink: 0;
}

.ingest-history-tag {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
  padding: 1px 5px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.ingest-history-count {
  color: var(--text-secondary);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  text-align: right;
}

.ingest-history-hash code {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  background: var(--bg-elevated);
  color: var(--text-muted);
  padding: 1px 5px;
  border-radius: 3px;
  cursor: help;
}

.ingest-history-more {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.ingest-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}

.ingest-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ingest-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(0, 0, 0, 0.15);
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

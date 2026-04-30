<template>
  <div class="library-page">
    <!-- Flash: redirected here because all workspace modes are disabled (#210) -->
    <div v-if="showFlashAllModesDisabled" class="flash flash--warning" role="alert">
      {{ t('flags.allModesDisabled') }}
    </div>

    <!-- Page header -->
    <div class="library-header">
      <h1 class="library-title">{{ t('docs.title') }}</h1>
      <RouterLink :to="{ name: ROUTES.DOCS_NEW }" class="btn-primary">
        {{ t('docs.import') }}
      </RouterLink>
    </div>

    <!-- Filter bar (#212) -->
    <div v-if="docStore.documents.length" class="filter-bar">
      <!-- Status pills -->
      <div class="filter-group">
        <button
          v-for="state in ALL_STATES"
          :key="state"
          class="filter-pill"
          :class="{ active: statusFilter.has(state) }"
          @click="toggleStatus(state)"
        >
          <StatusBadge :state="state" compact />
          {{ t(`status.${state}`) }}
        </button>
      </div>

      <!-- Store pills (shown only when at least one doc has stores) -->
      <div v-if="allStores.length" class="filter-group">
        <button
          v-for="store in allStores"
          :key="store"
          class="filter-pill filter-pill--store"
          :class="{ active: storeFilter.has(store) }"
          @click="toggleStore(store)"
        >
          {{ store }}
        </button>
      </div>

      <!-- Search -->
      <input
        v-model="searchInput"
        type="search"
        class="filter-search"
        :placeholder="t('docs.filterSearch')"
      />

      <!-- Clear -->
      <button v-if="hasActiveFilters" class="filter-clear" @click="clearFilters">
        {{ t('docs.filterClear') }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="docStore.loading" class="loading-state">
      <div class="spinner" />
    </div>

    <!-- Table (#211) -->
    <div v-else-if="docStore.documents.length" class="table-wrapper">
      <table class="doc-table" data-e2e="docs-table">
        <thead>
          <tr>
            <th class="col-check">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                :aria-label="t('docs.selected', { n: filteredDocs.length })"
                @change="toggleAll"
              />
            </th>
            <th>{{ t('docs.colName') }}</th>
            <th>{{ t('docs.colStatus') }}</th>
            <th>{{ t('docs.colStores') }}</th>
            <th class="col-updated">{{ t('docs.colUpdated') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="doc in filteredDocs"
            :key="doc.id"
            class="doc-row"
            data-e2e="doc-row"
            @click="openDoc(doc.id)"
          >
            <td class="col-check" @click.stop>
              <input
                type="checkbox"
                :checked="selectedIds.has(doc.id)"
                @change="toggleDoc(doc.id)"
              />
            </td>
            <td class="col-name">
              <svg class="doc-icon" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="doc-filename" :title="doc.filename">{{ doc.filename }}</span>
            </td>
            <td class="col-status">
              <StatusBadge :state="doc.lifecycleState" />
            </td>
            <td class="col-stores">
              <span v-if="doc.stores?.length" class="store-chips">
                <span v-for="s in doc.stores" :key="s" class="store-chip">{{ s }}</span>
              </span>
              <span v-else class="no-value">—</span>
            </td>
            <td class="col-updated">
              <span class="updated-time">{{ formatUpdated(doc) }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Filtered empty state -->
      <div v-if="!filteredDocs.length" class="empty-state empty-state--filtered">
        <p class="empty-title">{{ t('docs.emptyFiltered') }}</p>
        <button class="btn-secondary" @click="clearFilters">{{ t('docs.filterClear') }}</button>
      </div>
    </div>

    <!-- Empty corpus state -->
    <div v-else-if="!docStore.loading" class="empty-state" data-e2e="docs-empty">
      <svg
        class="empty-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1"
      >
        <path
          d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
        />
      </svg>
      <p class="empty-title">{{ t('docs.emptyTitle') }}</p>
      <p class="empty-subtitle">{{ t('docs.emptySubtitle') }}</p>
      <RouterLink :to="{ name: ROUTES.DOCS_NEW }" class="btn-primary">
        {{ t('docs.emptyAction') }}
      </RouterLink>
    </div>

    <!-- Sticky bulk action bar (#213) -->
    <div v-if="selectedIds.size > 0" class="bulk-bar" data-e2e="bulk-bar">
      <span class="bulk-count">{{ t('docs.selected', { n: selectedIds.size }) }}</span>
      <div class="bulk-actions">
        <button class="btn-sm" @click="bulkRechunk">{{ t('docs.bulkRechunk') }}</button>
        <button class="btn-sm" @click="openPushModal">{{ t('docs.bulkPush') }}</button>
        <button class="btn-sm btn-sm--danger" @click="bulkDelete">
          {{ t('docs.bulkDelete') }}
        </button>
        <button class="btn-sm btn-sm--ghost" @click="clearSelection">
          {{ t('docs.bulkCancel') }}
        </button>
      </div>
    </div>

    <!-- Push to store modal -->
    <div
      v-if="showPushModal"
      class="modal-overlay"
      role="dialog"
      :aria-label="t('docs.pushTitle')"
      @click.self="showPushModal = false"
    >
      <div class="modal">
        <h3 class="modal-title">{{ t('docs.pushTitle') }}</h3>
        <label class="modal-label" for="push-store-input">{{ t('docs.pushLabel') }}</label>
        <input
          id="push-store-input"
          v-model="pushStoreName"
          class="modal-input"
          list="store-datalist"
          :placeholder="t('docs.pushPlaceholder')"
          @keyup.enter="confirmPush"
          @keyup.escape="showPushModal = false"
        />
        <datalist id="store-datalist">
          <option v-for="s in availableStores" :key="s" :value="s" />
        </datalist>
        <div class="modal-footer">
          <button class="btn-primary" :disabled="!pushStoreName.trim()" @click="confirmPush">
            {{ t('docs.pushSubmit') }}
          </button>
          <button class="btn-secondary" @click="showPushModal = false">
            {{ t('docs.pushCancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useDocumentStore } from '../features/document/store'
import StatusBadge from '../features/document/ui/StatusBadge.vue'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import type { Document, DocumentLifecycleState } from '../shared/types'
import { formatRelativeTime } from '../shared/format'
import { appLocale } from '../shared/appConfig'

const ALL_STATES: DocumentLifecycleState[] = [
  'Uploaded',
  'Parsed',
  'Chunked',
  'Ingested',
  'Stale',
  'Failed',
]

const docStore = useDocumentStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

// ---------------------------------------------------------------------------
// Flash for "no-mode-enabled" redirect (#210)
// ---------------------------------------------------------------------------
const showFlashAllModesDisabled = computed(() => route.query.reason === 'no-mode-enabled')

// ---------------------------------------------------------------------------
// Filters — init from URL query params (#212)
// ---------------------------------------------------------------------------
function parseSetParam(raw: unknown): Set<string> {
  const str = typeof raw === 'string' ? raw : ''
  return new Set(str.split(',').filter(Boolean))
}

const statusFilter = ref<Set<DocumentLifecycleState>>(
  parseSetParam(route.query.status) as Set<DocumentLifecycleState>,
)
const storeFilter = ref<Set<string>>(parseSetParam(route.query.store))
const searchInput = ref<string>(typeof route.query.q === 'string' ? route.query.q : '')
const debouncedSearch = ref<string>(searchInput.value)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchInput, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    debouncedSearch.value = val
    syncUrl()
  }, 300)
})

function syncUrl(): void {
  const query: Record<string, string> = {}
  if (statusFilter.value.size) query.status = [...statusFilter.value].join(',')
  if (storeFilter.value.size) query.store = [...storeFilter.value].join(',')
  if (debouncedSearch.value) query.q = debouncedSearch.value
  router.replace({ query })
}

function toggleStatus(state: DocumentLifecycleState): void {
  const next = new Set(statusFilter.value)
  if (next.has(state)) next.delete(state)
  else next.add(state)
  statusFilter.value = next
  syncUrl()
}

function toggleStore(store: string): void {
  const next = new Set(storeFilter.value)
  if (next.has(store)) next.delete(store)
  else next.add(store)
  storeFilter.value = next
  syncUrl()
}

const hasActiveFilters = computed(
  () => statusFilter.value.size > 0 || storeFilter.value.size > 0 || !!debouncedSearch.value,
)

function clearFilters(): void {
  statusFilter.value = new Set()
  storeFilter.value = new Set()
  searchInput.value = ''
  debouncedSearch.value = ''
  router.replace({ query: {} })
}

// ---------------------------------------------------------------------------
// Derived store list for store-filter chips and push modal datalist
// ---------------------------------------------------------------------------
const allStores = computed(() => {
  const acc = new Set<string>()
  docStore.documents.forEach((d) => d.stores?.forEach((s) => acc.add(s)))
  return [...acc].sort()
})

const availableStores = allStores

// ---------------------------------------------------------------------------
// Filtered documents
// ---------------------------------------------------------------------------
const filteredDocs = computed(() => {
  const q = debouncedSearch.value.toLowerCase()
  return docStore.documents.filter((doc) => {
    if (statusFilter.value.size && !statusFilter.value.has(doc.lifecycleState)) return false
    if (storeFilter.value.size && !doc.stores?.some((s) => storeFilter.value.has(s))) return false
    if (q && !doc.filename.toLowerCase().includes(q)) return false
    return true
  })
})

// ---------------------------------------------------------------------------
// Table helpers
// ---------------------------------------------------------------------------
function formatUpdated(doc: Document): string {
  return formatRelativeTime(doc.lifecycleStateAt ?? doc.createdAt, appLocale.value)
}

function openDoc(id: string): void {
  router.push({ name: ROUTES.DOC_WORKSPACE, params: { id } })
}

// ---------------------------------------------------------------------------
// Multi-select (#213)
// ---------------------------------------------------------------------------
const selectedIds = ref<Set<string>>(new Set())

const allSelected = computed(
  () =>
    filteredDocs.value.length > 0 && filteredDocs.value.every((d) => selectedIds.value.has(d.id)),
)

const someSelected = computed(
  () => filteredDocs.value.some((d) => selectedIds.value.has(d.id)) && !allSelected.value,
)

function toggleDoc(id: string): void {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function toggleAll(): void {
  if (allSelected.value) {
    const next = new Set(selectedIds.value)
    filteredDocs.value.forEach((d) => next.delete(d.id))
    selectedIds.value = next
  } else {
    const next = new Set(selectedIds.value)
    filteredDocs.value.forEach((d) => next.add(d.id))
    selectedIds.value = next
  }
}

function clearSelection(): void {
  selectedIds.value = new Set()
}

// ---------------------------------------------------------------------------
// Bulk actions
// ---------------------------------------------------------------------------
async function bulkRechunk(): Promise<void> {
  const ids = [...selectedIds.value]
  clearSelection()
  const jobs = await Promise.all(ids.map((id) => docStore.rechunk(id)))
  const dispatched = jobs.filter(Boolean)
  if (dispatched.length) {
    // Surface job ids as a brief toast via window.alert for now
    // E9 (RunsPage) will provide proper job tracking
    window.alert(t('docs.jobDispatched', { jobId: dispatched.join(', ') }))
  }
}

const showPushModal = ref(false)
const pushStoreName = ref('')

function openPushModal(): void {
  pushStoreName.value = availableStores.value[0] ?? ''
  showPushModal.value = true
}

async function confirmPush(): Promise<void> {
  const target = pushStoreName.value.trim()
  if (!target) return
  showPushModal.value = false
  const ids = [...selectedIds.value]
  clearSelection()
  const jobs = await Promise.all(ids.map((id) => docStore.pushToStore(id, target)))
  const dispatched = jobs.filter(Boolean)
  if (dispatched.length) {
    window.alert(t('docs.jobDispatched', { jobId: dispatched.join(', ') }))
  }
}

async function bulkDelete(): Promise<void> {
  const n = selectedIds.value.size
  if (!window.confirm(t('docs.deleteConfirm', { n }))) return
  const ids = [...selectedIds.value]
  clearSelection()
  await Promise.all(ids.map((id) => docStore.remove(id)))
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
onMounted(() => {
  docStore.load()
})
</script>

<style scoped>
.library-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* Header */
.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.library-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

/* Flash */
.flash {
  margin: 12px 24px 0;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  flex-shrink: 0;
}

.flash--warning {
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fde68a;
}

/* Filter bar */
.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.filter-pill:hover {
  border-color: var(--accent);
  color: var(--text);
}

.filter-pill.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.filter-search {
  flex: 1;
  min-width: 180px;
  max-width: 300px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color var(--transition);
}

.filter-search:focus {
  border-color: var(--accent);
}

.filter-clear {
  padding: 4px 10px;
  font-size: 12px;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  transition: color var(--transition);
}

.filter-clear:hover {
  color: var(--text);
}

/* Loading */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Table */
.table-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 80px; /* 80px bottom pad for bulk bar */
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.doc-table thead {
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}

.doc-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
}

.col-check {
  width: 40px;
}

.col-updated {
  width: 130px;
  white-space: nowrap;
}

.doc-row {
  cursor: pointer;
  transition: background var(--transition);
  border-bottom: 1px solid var(--border);
}

.doc-row:hover {
  background: var(--bg-hover);
}

.doc-table td {
  padding: 12px 12px;
  vertical-align: middle;
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.doc-icon {
  width: 14px;
  height: 14px;
  color: var(--accent);
  flex-shrink: 0;
}

.doc-filename {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--text);
}

.store-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.store-chip {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  color: var(--text-secondary);
  white-space: nowrap;
}

.no-value {
  color: var(--text-muted);
}

.updated-time {
  color: var(--text-muted);
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
}

/* Empty states */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 24px;
  text-align: center;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--text-muted);
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.empty-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

.empty-state--filtered {
  padding: 40px 24px;
}

/* Bulk action bar */
.bulk-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
  gap: 12px;
}

.bulk-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}

.bulk-actions {
  display: flex;
  gap: 8px;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  color: white;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-decoration: none;
  transition: background var(--transition);
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.btn-sm:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.btn-sm--danger {
  color: var(--error);
  border-color: rgba(239, 68, 68, 0.3);
}

.btn-sm--danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

.btn-sm--ghost {
  border-color: transparent;
  background: transparent;
}

/* Push modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.modal-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.modal-input {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text);
  font-size: 13px;
  outline: none;
  width: 100%;
  transition: border-color var(--transition);
}

.modal-input:focus {
  border-color: var(--accent);
}

.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}
</style>

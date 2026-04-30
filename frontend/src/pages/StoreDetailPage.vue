<template>
  <div class="detail-page">
    <div class="detail-header">
      <RouterLink :to="{ name: ROUTES.STORES_LIST }" class="back-link">
        ← {{ t('storeDetail.back') }}
      </RouterLink>
      <h1 class="detail-title">{{ store }}</h1>
      <RouterLink :to="{ name: ROUTES.STORE_QUERY, params: { store } }" class="btn-primary">
        {{ t('storeDetail.query') }}
      </RouterLink>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-text">{{ error }}</p>
      <button class="btn-secondary" @click="load">Retry</button>
    </div>

    <div v-else-if="docs.length" class="table-wrapper">
      <table class="detail-table">
        <thead>
          <tr>
            <th class="col-check">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                @change="toggleAll"
              />
            </th>
            <th>{{ t('storeDetail.colDoc') }}</th>
            <th>{{ t('storeDetail.colState') }}</th>
            <th class="col-num">{{ t('storeDetail.colChunks') }}</th>
            <th>{{ t('storeDetail.colIngested') }}</th>
            <th class="col-action" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in docs" :key="doc.docId" class="doc-row" @click="openDoc(doc.docId)">
            <td class="col-check" @click.stop>
              <input
                type="checkbox"
                :checked="selectedIds.has(doc.docId)"
                @change="toggleDoc(doc.docId)"
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
            <td>
              <StatusBadge :state="doc.state" />
            </td>
            <td class="col-num">{{ doc.chunkCount }}</td>
            <td class="col-date">{{ doc.pushedAt ? formatDate(doc.pushedAt) : '—' }}</td>
            <td class="col-action" @click.stop>
              <button class="btn-sm btn-sm--danger" @click="removeDoc(doc)">
                {{ t('storeDetail.remove') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty-state">
      <p class="empty-title">{{ t('storeDetail.empty') }}</p>
    </div>

    <!-- Bulk action bar -->
    <div v-if="selectedIds.size > 0" class="bulk-bar">
      <span class="bulk-count">{{ t('storeDetail.selected', { n: selectedIds.size }) }}</span>
      <div class="bulk-actions">
        <button class="btn-sm btn-sm--danger" @click="bulkRemove">
          {{ t('storeDetail.bulkRemove') }}
        </button>
        <button class="btn-sm btn-sm--ghost" @click="clearSelection">
          {{ t('storeDetail.bulkCancel') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import {
  fetchStoreDocuments,
  removeDocumentFromStore,
  type StoreDocEntry,
} from '../features/store/api'
import StatusBadge from '../features/document/ui/StatusBadge.vue'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import { appLocale } from '../shared/appConfig'

const props = defineProps<{ store: string }>()

const router = useRouter()
const { t } = useI18n()

const docs = ref<StoreDocEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedIds = ref<Set<string>>(new Set())

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    docs.value = await fetchStoreDocuments(props.store)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(appLocale.value === 'fr' ? 'fr-FR' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function openDoc(docId: string): void {
  router.push({ name: ROUTES.DOC_WORKSPACE, params: { id: docId } })
}

async function removeDoc(doc: StoreDocEntry): Promise<void> {
  if (!window.confirm(t('storeDetail.removeConfirm', { doc: doc.filename }))) return
  await removeDocumentFromStore(props.store, doc.docId)
  docs.value = docs.value.filter((d) => d.docId !== doc.docId)
  const next = new Set(selectedIds.value)
  next.delete(doc.docId)
  selectedIds.value = next
}

const allSelected = computed(
  () => docs.value.length > 0 && docs.value.every((d) => selectedIds.value.has(d.docId)),
)

const someSelected = computed(
  () => docs.value.some((d) => selectedIds.value.has(d.docId)) && !allSelected.value,
)

function toggleDoc(id: string): void {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function toggleAll(): void {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(docs.value.map((d) => d.docId))
  }
}

function clearSelection(): void {
  selectedIds.value = new Set()
}

async function bulkRemove(): Promise<void> {
  const n = selectedIds.value.size
  if (!window.confirm(t('storeDetail.bulkConfirm', { n }))) return
  const ids = [...selectedIds.value]
  clearSelection()
  await Promise.all(ids.map((id) => removeDocumentFromStore(props.store, id)))
  docs.value = docs.value.filter((d) => !ids.includes(d.docId))
}

onMounted(load)
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.back-link {
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
  transition: color var(--transition);
  white-space: nowrap;
}

.back-link:hover {
  color: var(--text);
}

.detail-title {
  flex: 1;
  font-size: 20px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 24px;
}

.error-text {
  font-size: 13px;
  color: var(--error);
}

.table-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 80px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.detail-table thead {
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}

.detail-table th {
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

.col-num {
  width: 80px;
  text-align: right;
}

.detail-table td.col-num {
  text-align: right;
}

.col-action {
  width: 80px;
  text-align: right;
}

.doc-row {
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}

.doc-row:hover {
  background: var(--bg-hover);
}

.detail-table td {
  padding: 12px;
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

.col-date {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
  white-space: nowrap;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 24px;
  text-align: center;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

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
  white-space: nowrap;
}

.btn-primary:hover {
  background: var(--accent-hover);
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
  padding: 5px 10px;
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
</style>

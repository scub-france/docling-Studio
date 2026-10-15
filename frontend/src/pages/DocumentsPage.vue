<template>
  <div class="documents-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('nav.documents') }}</h1>
      <div class="header-actions">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          :placeholder="t('ingestion.search')"
        />
        <div v-if="ingestionEnabled" class="filter-group">
          <button
            v-for="f in filters"
            :key="f.value"
            class="filter-btn"
            :class="{ active: activeFilter === f.value }"
            @click="activeFilter = f.value"
          >
            {{ f.label }}
          </button>
        </div>
        <div class="sort-group">
          <button class="sort-btn" :class="{ active: sortBy === 'name' }" @click="sortBy = 'name'">
            {{ t('ingestion.sortName') }}
          </button>
          <button class="sort-btn" :class="{ active: sortBy === 'date' }" @click="sortBy = 'date'">
            {{ t('ingestion.sortDate') }}
          </button>
        </div>
      </div>
    </div>
    <div class="page-content">
      <div v-if="filteredDocs.length === 0" class="tab-empty">
        {{ t('history.emptyDocs') }}
      </div>
      <div v-else class="doc-items">
        <div v-for="doc in filteredDocs" :key="doc.id" class="doc-row">
          <div class="doc-row-info">
            <svg class="doc-row-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                clip-rule="evenodd"
              />
            </svg>
            <div class="doc-row-meta">
              <span class="doc-row-name">{{ doc.filename }}</span>
              <span class="doc-row-detail">
                {{ formatSize(doc.fileSize) }}
                <template v-if="doc.pageCount"> — {{ doc.pageCount }} pages</template>
                <template v-if="doc.createdAt"> — {{ formatDate(doc.createdAt) }}</template>
              </span>
            </div>
          </div>
          <div class="doc-row-actions">
            <template v-if="ingestionEnabled">
              <span
                v-if="ingestionStore.ingestedDocs[doc.id]"
                class="status-badge indexed"
                :title="t('ingestion.chunksIndexed', { n: ingestionStore.ingestedDocs[doc.id] })"
              >
                {{ t('ingestion.indexed') }}
                <span class="badge-count">{{ ingestionStore.ingestedDocs[doc.id] }}</span>
              </span>
              <span v-else class="status-badge not-indexed">
                {{ t('ingestion.notIndexed') }}
              </span>
            </template>
            <button
              class="action-btn"
              :title="t('ingestion.openInStudio')"
              @click="openInStudio(doc)"
            >
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838l-2.727 1.17 1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3z"
                />
              </svg>
            </button>
            <button
              class="action-btn"
              :disabled="analysisStore.running"
              :title="t('newAnalysis.title')"
              :aria-label="t('newAnalysis.title')"
              @click="startAnalysis(doc.id)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="11" cy="11" r="6" />
                <path d="m16 16 5 5" />
              </svg>
            </button>
            <AnalysisImportButton icon-only :document-id="doc.id" @imported="onAnalysisImported" />
            <button
              v-if="ingestionEnabled && ingestionStore.ingestedDocs[doc.id]"
              class="action-btn unindex"
              :title="t('ingestion.deleteIndex')"
              @click="confirmRemoveFromIndex(doc.id)"
            >
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
            <button class="action-btn delete" @click="handleDelete(doc.id)">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentStore } from '../features/document/store'
import { useFeatureFlagStore } from '../features/feature-flags/store'
import { useIngestionStore } from '../features/ingestion/store'
import { AnalysisImportButton, useAnalysisStore } from '../features/analysis'
import { useI18n } from '../shared/i18n'
import { formatSize } from '../shared/format'
import type { Document } from '../shared/types'

const docStore = useDocumentStore()
const featureStore = useFeatureFlagStore()
const ingestionStore = useIngestionStore()
const analysisStore = useAnalysisStore()
const ingestionEnabled = computed(() => featureStore.isEnabled('ingestion'))
const router = useRouter()
const { t } = useI18n()

const searchQuery = ref('')
const activeFilter = ref<'all' | 'indexed' | 'not-indexed'>('all')
const sortBy = ref<'name' | 'date'>('date')

const filters = computed(() => [
  { value: 'all' as const, label: t('ingestion.filterAll') },
  { value: 'indexed' as const, label: t('ingestion.filterIndexed') },
  { value: 'not-indexed' as const, label: t('ingestion.filterNotIndexed') },
])

const filteredDocs = computed(() => {
  let docs = [...docStore.documents]

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    docs = docs.filter((d) => d.filename.toLowerCase().includes(q))
  }

  // Status filter
  if (activeFilter.value === 'indexed') {
    docs = docs.filter((d) => ingestionStore.ingestedDocs[d.id])
  } else if (activeFilter.value === 'not-indexed') {
    docs = docs.filter((d) => !ingestionStore.ingestedDocs[d.id])
  }

  // Sort
  if (sortBy.value === 'name') {
    docs.sort((a, b) => a.filename.localeCompare(b.filename))
  } else {
    docs.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
  }

  return docs
})

function formatDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

function openInStudio(doc: Document) {
  docStore.select(doc.id)
  router.push('/studio')
}

async function startAnalysis(documentId: string) {
  const analysis = await analysisStore.run(documentId)
  router.push({ name: 'analysis-detail', params: { id: analysis.id } })
}

function onAnalysisImported(analysisId: string) {
  router.push({ name: 'analysis-detail', params: { id: analysisId } })
}

function confirmRemoveFromIndex(docId: string) {
  if (confirm(t('ingestion.deleteConfirm'))) {
    ingestionStore.deleteIngested(docId)
  }
}

async function handleDelete(docId: string) {
  if (ingestionEnabled.value && ingestionStore.ingestedDocs[docId]) {
    await ingestionStore.deleteIngested(docId)
  }
  await docStore.remove(docId)
}

onMounted(() => {
  docStore.load()
  if (ingestionEnabled.value) {
    ingestionStore.checkAvailability()
  }
})
</script>

<style scoped>
.documents-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.page-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  width: 180px;
  outline: none;
  transition: border-color var(--transition);
}

.search-input:focus {
  border-color: var(--accent);
}

.filter-group,
.sort-group {
  display: flex;
  gap: 2px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  padding: 2px;
  border: 1px solid var(--border);
}

.filter-btn,
.sort-btn {
  padding: 4px 10px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all var(--transition);
}

.filter-btn.active,
.sort-btn.active {
  background: var(--accent);
  color: white;
}

.page-content {
  flex: 1;
  overflow-y: auto;
}

.tab-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 60px 20px;
  font-size: 14px;
}

.doc-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.doc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: all 150ms ease;
}

.doc-row:hover {
  border-color: var(--accent);
  background: var(--bg-elevated);
}

.doc-row-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.doc-row-icon {
  width: 18px;
  height: 18px;
  color: var(--accent);
  flex-shrink: 0;
}

.doc-row-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.doc-row-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-row-detail {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  font-family: 'IBM Plex Mono', monospace;
}

.doc-row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.status-badge.indexed {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-badge.not-indexed {
  background: rgba(156, 163, 175, 0.15);
  color: var(--text-muted);
}

.badge-count {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
}

.action-btn {
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

.doc-row:hover .action-btn {
  opacity: 1;
}

.action-btn:hover {
  color: var(--accent);
  background: rgba(249, 115, 22, 0.1);
}

.action-btn.delete:hover {
  color: var(--error);
  background: rgba(239, 68, 68, 0.1);
}

.action-btn.unindex:hover {
  color: var(--warning, #f59e0b);
  background: rgba(245, 158, 11, 0.1);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}
</style>

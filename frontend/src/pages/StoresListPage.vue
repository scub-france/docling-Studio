<template>
  <div class="stores-page">
    <div class="stores-header">
      <h1 class="stores-title">{{ t('stores.title') }}</h1>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-text">{{ error }}</p>
      <button class="btn-secondary" @click="load">Retry</button>
    </div>

    <div v-else-if="stores.length" class="table-wrapper">
      <table class="stores-table">
        <thead>
          <tr>
            <th>{{ t('stores.colName') }}</th>
            <th>{{ t('stores.colType') }}</th>
            <th>{{ t('stores.colStatus') }}</th>
            <th class="col-num">{{ t('stores.colDocs') }}</th>
            <th class="col-num">{{ t('stores.colChunks') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="store in stores"
            :key="store.name"
            class="store-row"
            @click="openStore(store.name)"
          >
            <td class="col-name">
              <svg class="store-icon" viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z"
                />
                <path
                  d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z"
                />
                <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
              </svg>
              <span class="store-name">{{ store.name }}</span>
            </td>
            <td>
              <span class="store-type">{{ store.type }}</span>
            </td>
            <td>
              <span
                class="status-badge"
                :class="store.connected ? 'status-badge--ok' : 'status-badge--err'"
              >
                {{ store.connected ? t('stores.connected') : t('stores.disconnected') }}
              </span>
              <span v-if="store.errorMessage" class="error-hint" :title="store.errorMessage">
                {{ store.errorMessage }}
              </span>
            </td>
            <td class="col-num">{{ store.documentCount }}</td>
            <td class="col-num">{{ store.chunkCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty-state">
      <svg
        class="empty-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1"
      >
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.657-4.03 3-9 3S3 13.657 3 12" />
        <path d="M3 5v14c0 1.657 4.03 3 9 3s9-1.343 9-3V5" />
      </svg>
      <p class="empty-title">{{ t('stores.empty') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchStores, type StoreInfo } from '../features/store/api'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'

const router = useRouter()
const { t } = useI18n()

const stores = ref<StoreInfo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    stores.value = await fetchStores()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function openStore(name: string): void {
  router.push({ name: ROUTES.STORE_DETAIL, params: { store: name } })
}

onMounted(load)
</script>

<style scoped>
.stores-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.stores-header {
  display: flex;
  align-items: center;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.stores-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
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
  padding: 0 24px 24px;
}

.stores-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.stores-table thead {
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}

.stores-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
}

.col-num {
  width: 100px;
  text-align: right;
}

.stores-table td.col-num {
  text-align: right;
}

.store-row {
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}

.store-row:hover {
  background: var(--bg-hover);
}

.stores-table td {
  padding: 12px;
  vertical-align: middle;
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.store-icon {
  width: 14px;
  height: 14px;
  color: var(--accent);
  flex-shrink: 0;
}

.store-name {
  font-weight: 500;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text);
}

.store-type {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 2px 7px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge--ok {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.status-badge--err {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.error-hint {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--error);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
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
</style>

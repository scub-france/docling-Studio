<template>
  <div class="query-page">
    <div class="query-header">
      <RouterLink :to="{ name: ROUTES.STORE_DETAIL, params: { store } }" class="back-link">
        ← {{ t('storeQuery.back') }}
      </RouterLink>
      <h1 class="query-title">{{ store }}</h1>
    </div>

    <div class="query-form">
      <div class="form-row">
        <label class="form-label" for="query-input">{{ t('storeQuery.queryLabel') }}</label>
        <div class="query-input-group">
          <textarea
            id="query-input"
            v-model="queryText"
            class="query-textarea"
            :placeholder="t('storeQuery.queryPlaceholder')"
            rows="3"
            @keydown.ctrl.enter="run"
            @keydown.meta.enter="run"
          />
          <button class="btn-primary" :disabled="running || !queryText.trim()" @click="run">
            {{ running ? t('storeQuery.running') : t('storeQuery.run') }}
          </button>
        </div>
      </div>
      <div class="form-row form-row--inline">
        <label class="form-label" for="topk-input">{{ t('storeQuery.topKLabel') }}</label>
        <input
          id="topk-input"
          v-model.number="topK"
          type="number"
          class="topk-input"
          min="1"
          max="50"
        />
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div v-if="results !== null" class="results-section">
      <div v-if="results.length === 0" class="empty-results">
        {{ t('storeQuery.empty') }}
      </div>
      <table v-else class="results-table">
        <thead>
          <tr>
            <th class="col-score">{{ t('storeQuery.colScore') }}</th>
            <th>{{ t('storeQuery.colDoc') }}</th>
            <th>{{ t('storeQuery.colText') }}</th>
            <th class="col-page">{{ t('storeQuery.colPage') }}</th>
            <th class="col-view" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, idx) in results" :key="idx" class="result-row">
            <td class="col-score">
              <span class="score-badge">{{ r.score.toFixed(3) }}</span>
            </td>
            <td class="col-doc">
              <span class="doc-name" :title="r.filename">{{ r.filename }}</span>
            </td>
            <td class="col-text">
              <span class="excerpt">{{ r.text }}</span>
            </td>
            <td class="col-page">
              <span v-if="r.pageRange" class="page-range">
                {{ r.pageRange[0] }}–{{ r.pageRange[1] }}
              </span>
              <span v-else class="no-value">—</span>
            </td>
            <td class="col-view">
              <RouterLink
                :to="{ name: ROUTES.DOC_WORKSPACE, params: { id: r.docId } }"
                class="view-link"
              >
                {{ t('storeQuery.viewDoc') }}
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import { queryStore, type QueryResult } from '../features/store/api'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'

const props = defineProps<{ store: string }>()

const { t } = useI18n()

const queryText = ref('')
const topK = ref(5)
const running = ref(false)
const error = ref<string | null>(null)
const results = ref<QueryResult[] | null>(null)

async function run(): Promise<void> {
  const q = queryText.value.trim()
  if (!q || running.value) return
  running.value = true
  error.value = null
  results.value = null
  try {
    results.value = await queryStore(props.store, q, topK.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.query-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.query-header {
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

.query-title {
  font-size: 20px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.query-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row--inline {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.form-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.query-input-group {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.query-textarea {
  flex: 1;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  resize: vertical;
  transition: border-color var(--transition);
}

.query-textarea:focus {
  border-color: var(--accent);
}

.topk-input {
  width: 80px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color var(--transition);
}

.topk-input:focus {
  border-color: var(--accent);
}

.error-banner {
  margin: 12px 24px 0;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--error);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  flex-shrink: 0;
}

.results-section {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 24px;
}

.empty-results {
  padding: 40px;
  text-align: center;
  font-size: 14px;
  color: var(--text-muted);
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.results-table thead {
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}

.results-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
}

.col-score {
  width: 80px;
}

.col-page {
  width: 80px;
  text-align: right;
}

.results-table td.col-page {
  text-align: right;
}

.col-view {
  width: 60px;
  text-align: right;
}

.result-row {
  border-bottom: 1px solid var(--border);
}

.results-table td {
  padding: 12px;
  vertical-align: top;
}

.score-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  background: var(--accent-muted);
  color: var(--accent);
}

.col-doc {
  max-width: 200px;
}

.doc-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.col-text {
  min-width: 0;
}

.excerpt {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.page-range {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
}

.no-value {
  color: var(--text-muted);
}

.view-link {
  font-size: 12px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--transition);
}

.view-link:hover {
  color: var(--accent-hover);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
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

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>

<template>
  <div class="analysis-panel">
    <div class="panel-section">
      <DocumentUpload />
    </div>

    <div class="panel-section" v-if="documentStore.documents.length">
      <label class="section-label">Documents</label>
      <DocumentList />
    </div>

    <div class="panel-section" v-if="selectedDoc">
      <label class="section-label">Preview</label>
      <PagePreview
        :document-id="selectedDoc.id"
        :page="currentPage"
        :page-count="selectedDoc.pageCount ?? undefined"
        @update:page="currentPage = $event"
      />
    </div>

    <div class="panel-actions" v-if="selectedDoc">
      <button class="btn-analyze" :disabled="analysisStore.running" @click="runAnalysis">
        <div v-if="analysisStore.running" class="spinner" />
        <svg v-else viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
            clip-rule="evenodd"
          />
        </svg>
        {{ analysisStore.running ? 'Analyzing...' : 'Analyze' }}
      </button>
    </div>

    <div class="panel-section" v-if="analysisStore.currentAnalysis">
      <label class="section-label">Status</label>
      <div class="status-row">
        <span class="status-badge" :class="statusClass">
          {{ analysisStore.currentAnalysis.status }}
          <template
            v-if="
              analysisStore.currentAnalysis.status === 'RUNNING' &&
              analysisStore.currentAnalysis.progressTotal &&
              analysisStore.currentAnalysis.progressTotal > 0
            "
          >
            ({{ analysisStore.currentAnalysis.progressCurrent ?? 0 }}/{{
              analysisStore.currentAnalysis.progressTotal
            }}
            pages)
          </template>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDocumentStore, DocumentUpload, DocumentList, PagePreview } from '@/features/document'
import { useAnalysisStore } from '../store'

const documentStore = useDocumentStore()
const analysisStore = useAnalysisStore()
const currentPage = ref(1)

const selectedDoc = computed(() => {
  return documentStore.documents.find((d) => d.id === documentStore.selectedId)
})

const statusClass = computed(() => {
  const status = analysisStore.currentAnalysis?.status
  return {
    'status-pending': status === 'PENDING',
    'status-running': status === 'RUNNING',
    'status-completed': status === 'COMPLETED',
    'status-failed': status === 'FAILED',
  }
})

async function runAnalysis() {
  if (!documentStore.selectedId) return
  await analysisStore.run(documentStore.selectedId)
}
</script>

<style scoped>
.analysis-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  overflow-y: auto;
  height: 100%;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.panel-actions {
  padding-top: 4px;
}

.btn-analyze {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
}

.btn-analyze:hover:not(:disabled) {
  background: var(--accent-hover);
}
.btn-analyze:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-icon {
  width: 18px;
  height: 18px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.status-row {
  display: flex;
  align-items: center;
}

.status-badge {
  font-size: 12px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  padding: 4px 10px;
  border-radius: 12px;
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
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}
.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error);
}
</style>

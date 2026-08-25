<template>
  <section class="analysis-detail">
    <div v-if="loading" class="state">{{ t('analyses.loading') }}</div>
    <div v-else-if="error || !analysis" class="state state--error">{{ t('analyses.failed') }}</div>
    <template v-else>
      <header class="detail-header">
        <RouterLink :to="{ name: ROUTES.ANALYSIS_LIBRARY }" class="back-link">
          ← {{ t('analyses.title') }}
        </RouterLink>
        <div>
          <p class="eyebrow">{{ analysis.status }}</p>
          <h1>{{ analysis.documentFilename || analysis.documentId }}</h1>
          <p class="meta">{{ analysis.id }} · {{ formatDate(analysis.createdAt) }}</p>
        </div>
        <div class="detail-actions">
          <button
            v-if="!editMode"
            class="edit-analysis-btn"
            :disabled="!analysis.hasDocumentJson"
            :title="analysis.hasDocumentJson ? t('workspace.editAnalysis') : t('workspace.analysisEditingUnavailable')"
            @click="editMode = true"
          >
            {{ t('workspace.editAnalysis') }}
          </button>
          <button v-else class="edit-analysis-btn" @click="editMode = false">
            {{ t('workspace.inspectAnalysis') }}
          </button>
          <DownloadDropdown :doc-id="analysis.documentId" />
        </div>
      </header>
      <AnalysisEditor
        v-if="editMode"
        :document-id="analysis.documentId"
        :analysis-id="analysis.id"
      />
      <DocParseTab
        v-else
        :doc-id="analysis.documentId"
        :analysis-id="analysis.id"
        :show-new-analysis="false"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAnalysis } from '../features/analysis/api'
import type { Analysis } from '../shared/types'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import DocParseTab from './DocParseTab.vue'
import DownloadDropdown from '../features/document/ui/DownloadDropdown.vue'
import { AnalysisEditor } from '../features/analysis-editor'

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const analysis = ref<Analysis | null>(null)
const loading = ref(true)
const error = ref(false)
// Analysis details open on the immutable source projection. Editing is an
// explicit action from the detail header.
const editMode = ref(false)

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  )
}

onMounted(async () => {
  try {
    analysis.value = await fetchAnalysis(props.id)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.analysis-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex-shrink: 0;
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--border);
}
.back-link {
  display: inline-block;
  margin-bottom: 14px;
  color: var(--accent);
  font-size: 12px;
  text-decoration: none;
}
.eyebrow {
  color: var(--accent);
  font:
    500 11px 'IBM Plex Mono',
    monospace;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
h1 {
  margin-top: 3px;
  font-size: 20px;
}
.meta {
  margin-top: 3px;
  color: var(--text-muted);
  font:
    11px 'IBM Plex Mono',
    monospace;
}
.detail-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.edit-analysis-btn {
  padding: 7px 12px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  background: var(--accent-muted);
  color: var(--accent);
  cursor: pointer;
  font-size: 12px;
}
.edit-analysis-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.analysis-detail :deep(.parse-tab) {
  min-height: 0;
  flex: 1;
}
.state {
  padding: 56px 24px;
  color: var(--text-secondary);
}
.state--error {
  color: var(--error);
}
</style>

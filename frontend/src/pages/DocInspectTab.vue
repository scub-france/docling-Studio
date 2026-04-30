<template>
  <div class="inspect-tab" data-e2e="inspect-tab">
    <!-- Loading -->
    <div v-if="loading" class="inspect-state">
      <span class="spinner" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="inspect-state inspect-state--error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="load">{{ t('inspect.retry') }}</button>
    </div>

    <!-- No analysis yet -->
    <div v-else-if="!analysis" class="inspect-state">
      <p class="inspect-empty-title">{{ t('inspect.noAnalysis') }}</p>
      <p class="inspect-empty-sub">{{ t('inspect.noAnalysisSub') }}</p>
      <RouterLink :to="{ name: ROUTES.STUDIO }" class="inspect-cta">
        {{ t('inspect.goToStudio') }}
      </RouterLink>
    </div>

    <!-- Result -->
    <InspectResultTabs v-else :analysis="analysis" :doc-id="docId" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import type { Analysis } from '../shared/types'
import { fetchDocumentAnalyses } from '../features/analysis/api'
import InspectResultTabs from '../features/analysis/ui/InspectResultTabs.vue'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'

const props = defineProps<{ docId: string }>()

const { t } = useI18n()

const loading = ref(false)
const error = ref<string | null>(null)
const analysis = ref<Analysis | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const analyses = await fetchDocumentAnalyses(props.docId)
    analysis.value = analyses.find((a) => a.status === 'COMPLETED') ?? null
  } catch (e) {
    error.value = (e as Error).message || 'Failed to load analysis'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.inspect-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.inspect-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.inspect-state--error {
  color: var(--error);
}

.inspect-empty-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin: 0;
}

.inspect-empty-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.inspect-cta {
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
  border: 1px solid var(--accent);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  transition: all var(--transition);
}

.inspect-cta:hover {
  background: var(--accent-muted);
}

.retry-btn {
  font-size: 13px;
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.retry-btn:hover {
  border-color: var(--text-secondary);
  color: var(--text);
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
</style>

<template>
  <div class="ask-tab" data-e2e="ask-tab">
    <!-- Loading analysis -->
    <div v-if="loading" class="ask-state">
      <span class="spinner" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="ask-state ask-state--error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="loadAnalysis">{{ t('inspect.retry') }}</button>
    </div>

    <!-- No analysis -->
    <div v-else-if="pages.length === 0" class="ask-state">
      <p class="ask-empty-title">{{ t('ask.noAnalysis') }}</p>
      <p class="ask-empty-sub">{{ t('ask.noAnalysisSub') }}</p>
      <RouterLink :to="{ name: ROUTES.STUDIO }" class="ask-cta">
        {{ t('inspect.goToStudio') }}
      </RouterLink>
    </div>

    <!-- Split layout: document left + ask panel right -->
    <template v-else>
      <div class="ask-doc-pane">
        <StructureViewer
          ref="structureViewerRef"
          :pages="pages"
          :document-id="docId"
          :visited-by-self-ref="visitedBySelfRef"
          :focused-self-ref="focusedSelfRef"
          selectable
        />
      </div>
      <div class="ask-panel-pane">
        <AskRunner :doc-id="docId" @section-focus="onSectionFocus" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import type { Analysis, Page } from '../shared/types'
import { fetchDocumentAnalyses } from '../features/analysis/api'
import StructureViewer from '../features/analysis/ui/StructureViewer.vue'
import AskRunner from '../features/reasoning/ui/AskRunner.vue'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'

const props = defineProps<{ docId: string }>()

const { t } = useI18n()

const loading = ref(false)
const error = ref<string | null>(null)
const analysis = ref<Analysis | null>(null)
const focusedSelfRef = ref<string | null>(null)
const structureViewerRef = ref<InstanceType<typeof StructureViewer> | null>(null)

const pages = computed<Page[]>(() => {
  if (!analysis.value?.pagesJson) return []
  try {
    return JSON.parse(analysis.value.pagesJson) as Page[]
  } catch {
    return []
  }
})

const visitedBySelfRef = computed<Map<string, number>>(() => new Map())

async function loadAnalysis(): Promise<void> {
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

function onSectionFocus(sectionRef: string): void {
  if (focusedSelfRef.value === sectionRef) {
    structureViewerRef.value?.scrollToFocused(sectionRef)
  } else {
    focusedSelfRef.value = sectionRef
  }
}

onMounted(loadAnalysis)
</script>

<style scoped>
.ask-tab {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.ask-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.ask-state--error {
  color: var(--error);
}

.ask-empty-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin: 0;
}

.ask-empty-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.ask-cta {
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
  border: 1px solid var(--accent);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  transition: all var(--transition);
}

.ask-cta:hover {
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

.ask-doc-pane {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  padding: 16px 20px;
}

.ask-panel-pane {
  width: 360px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--bg-surface);
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

<template>
  <div class="workspace-page">
    <!-- Loading doc -->
    <div v-if="loadingDoc" class="workspace-loading">
      <span class="spinner" />
    </div>

    <!-- Doc error -->
    <div v-else-if="docError" class="workspace-error">
      <p>{{ docError }}</p>
      <RouterLink :to="{ name: ROUTES.DOCS_LIBRARY }" class="back-link">
        ← {{ t('workspace.backToLibrary') }}
      </RouterLink>
    </div>

    <template v-else-if="doc">
      <!-- Sticky header (#218) -->
      <DocWorkspaceHeader :doc="doc" />

      <!-- Tab strip (#216) -->
      <div class="tab-strip" role="tablist" data-e2e="tab-strip">
        <button
          v-for="m in ALL_MODES"
          :key="m"
          class="tab-btn"
          :class="{ active: activeMode === m, disabled: !modeEnabled(m) }"
          role="tab"
          :aria-selected="activeMode === m"
          :disabled="!modeEnabled(m)"
          :title="!modeEnabled(m) ? t('workspace.modeDisabled') : undefined"
          @click="switchMode(m)"
        >
          {{ t(`workspace.tabs.${m}`) }}
        </button>
      </div>

      <!-- Tab content — lazy loaded (#216) -->
      <div class="tab-content" role="tabpanel" data-e2e="tab-content">
        <Suspense>
          <DocChunksTab
            v-if="activeMode === 'chunks'"
            :doc-id="id"
            :available-stores="doc.stores ?? []"
          />
          <DocInspectTab v-else-if="activeMode === 'inspect'" :doc-id="id" />
          <DocAskTab v-else-if="activeMode === 'ask'" :doc-id="id" />
        </Suspense>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import type { Document } from '../shared/types'
import { fetchDocument } from '../features/document/api'
import { useFeatureFlagStore } from '../features/feature-flags/store'
import { ALL_MODES, type DocMode } from '../shared/routing/modes'
import { resolveMode } from '../shared/routing/resolveMode'
import { useCrumbs } from '../shared/breadcrumb/store'
import { truncate } from '../shared/breadcrumb/text'
import type { Crumb } from '../shared/breadcrumb/types'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import DocWorkspaceHeader from '../features/document/ui/DocWorkspaceHeader.vue'
import DocChunksTab from './DocChunksTab.vue'
import DocInspectTab from './DocInspectTab.vue'
import DocAskTab from './DocAskTab.vue'

const props = defineProps<{ id: string; mode: DocMode }>()

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const flagStore = useFeatureFlagStore()

const doc = ref<Document | null>(null)
const loadingDoc = ref(true)
const docError = ref<string | null>(null)

const activeMode = ref<DocMode>(props.mode)

const crumbs = computed<Crumb[]>(() => [
  { kind: 'link', label: t('breadcrumb.studio'), to: { name: ROUTES.HOME } },
  {
    kind: 'link',
    label: doc.value ? truncate(doc.value.filename, 40) : truncate(props.id, 40),
    to: { name: ROUTES.DOC_WORKSPACE, params: { id: props.id } },
  },
  { kind: 'leaf', label: t(`breadcrumb.mode.${activeMode.value}`) },
])
useCrumbs(crumbs)

function modeEnabled(m: DocMode): boolean {
  return flagStore.modeFlags()[m]
}

function switchMode(m: DocMode): void {
  if (!modeEnabled(m)) return
  activeMode.value = m
  router.replace({ query: { ...route.query, mode: m } })
}

async function loadDoc(): Promise<void> {
  loadingDoc.value = true
  docError.value = null
  try {
    doc.value = await fetchDocument(props.id)
  } catch (e) {
    docError.value = (e as Error).message || 'Failed to load document'
  } finally {
    loadingDoc.value = false
  }
}

onMounted(async () => {
  await flagStore.load()

  const flags = flagStore.modeFlags()
  const resolved = resolveMode(props.mode, flags)
  if (!resolved) {
    router.replace({ name: ROUTES.DOCS_LIBRARY, query: { reason: 'no-mode-enabled' } })
    return
  }
  if (resolved !== props.mode) {
    router.replace({ query: { ...route.query, mode: resolved } })
  }
  activeMode.value = resolved

  await loadDoc()
})

watch(
  () => props.mode,
  (m) => {
    const flags = flagStore.modeFlags()
    const resolved = resolveMode(m, flags)
    if (resolved) activeMode.value = resolved
  },
)
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.workspace-loading,
.workspace-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.workspace-error {
  color: var(--error);
}

.back-link {
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
}

.back-link:hover {
  color: var(--text);
}

.tab-strip {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  padding: 0 20px;
  flex-shrink: 0;
}

.tab-btn {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition);
  margin-bottom: -1px;
}

.tab-btn:hover:not(.disabled) {
  color: var(--text);
}

.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-btn.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.tab-content {
  flex: 1;
  overflow: hidden;
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

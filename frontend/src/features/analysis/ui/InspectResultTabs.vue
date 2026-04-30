<template>
  <div class="inspect-result-tabs">
    <div class="irt-tab-strip">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        class="irt-tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ t(tab.labelKey) }}
      </button>
    </div>

    <div class="irt-content">
      <!-- Markdown — full document -->
      <div v-if="activeTab === 'markdown'" class="irt-markdown">
        <MarkdownViewer :content="analysis.contentMarkdown ?? undefined" />
      </div>

      <!-- Elements — StructureViewer (page images + bbox overlay) -->
      <div v-else-if="activeTab === 'elements'" class="irt-elements">
        <div v-if="pages.length === 0" class="irt-empty">
          {{ t('inspect.noElements') }}
        </div>
        <StructureViewer v-else :pages="pages" :document-id="docId" />
      </div>

      <!-- Images — picture elements extracted from all pages -->
      <div v-else-if="activeTab === 'images'" class="irt-images">
        <ImageGallery :pages="pages" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Analysis, Page } from '../../../shared/types'
import MarkdownViewer from './MarkdownViewer.vue'
import StructureViewer from './StructureViewer.vue'
import ImageGallery from './ImageGallery.vue'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  analysis: Analysis
  docId: string
}>()

const { t } = useI18n()

const TABS = [
  { id: 'markdown', labelKey: 'inspect.tabMarkdown' },
  { id: 'elements', labelKey: 'inspect.tabElements' },
  { id: 'images', labelKey: 'inspect.tabImages' },
] as const

type TabId = (typeof TABS)[number]['id']

const activeTab = ref<TabId>('elements')

const pages = computed<Page[]>(() => {
  if (!props.analysis.pagesJson) return []
  try {
    return JSON.parse(props.analysis.pagesJson) as Page[]
  } catch {
    return []
  }
})
</script>

<style scoped>
.inspect-result-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.irt-tab-strip {
  display: flex;
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  flex-shrink: 0;
  background: var(--bg-surface);
}

.irt-tab-btn {
  padding: 10px 14px;
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

.irt-tab-btn:hover {
  color: var(--text-secondary);
}

.irt-tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.irt-content {
  flex: 1;
  overflow: hidden;
}

.irt-markdown,
.irt-elements,
.irt-images {
  height: 100%;
  overflow-y: auto;
  padding: 16px 20px;
}

.irt-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 13px;
}
</style>

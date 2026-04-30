<template>
  <div class="chunks-tab" data-e2e="chunks-tab">
    <!-- Tree rail -->
    <div class="tree-pane" :class="{ 'tree-pane--collapsed': treeCollapsed }">
      <button
        class="tree-toggle"
        :title="treeCollapsed ? t('tree.expand') : t('tree.collapse')"
        @click="treeCollapsed = !treeCollapsed"
      >
        <span class="tree-toggle-icon" :class="{ 'tree-toggle-icon--collapsed': treeCollapsed }"
          >‹</span
        >
      </button>
      <DocTreeRail
        v-if="!treeCollapsed"
        :nodes="treeNodes"
        :loading="treeLoading"
        :error="treeError"
        :selected="selectedNodeRef"
        :highlight="highlightRef"
        @select="onTreeSelect"
        @reload="loadTree"
      />
    </div>

    <!-- Chunks editor -->
    <div class="editor-pane">
      <ChunksEditor
        :doc-id="docId"
        :available-stores="availableStores"
        @node-highlight="highlightRef = $event"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { DocTreeNode } from '../shared/types'
import { fetchDocumentTree } from '../features/document/api'
import DocTreeRail from '../features/document/ui/DocTreeRail.vue'
import ChunksEditor from '../features/chunks/ui/ChunksEditor.vue'
import { useI18n } from '../shared/i18n'

const props = defineProps<{
  docId: string
  availableStores: string[]
}>()

const { t } = useI18n()

const treeNodes = ref<DocTreeNode[]>([])
const treeLoading = ref(false)
const treeError = ref<string | null>(null)
const treeCollapsed = ref(false)
const selectedNodeRef = ref<string | null>(null)
const highlightRef = ref<string | null>(null)

async function loadTree(): Promise<void> {
  treeLoading.value = true
  treeError.value = null
  try {
    treeNodes.value = await fetchDocumentTree(props.docId)
  } catch (e) {
    treeError.value = (e as Error).message || 'Failed to load tree'
  } finally {
    treeLoading.value = false
  }
}

function onTreeSelect(ref: string): void {
  selectedNodeRef.value = ref
  highlightRef.value = ref
}

onMounted(loadTree)
</script>

<style scoped>
.chunks-tab {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.tree-pane {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  position: relative;
  transition: width 0.2s;
}

.tree-pane--collapsed {
  width: 24px;
}

.tree-toggle {
  position: absolute;
  top: 12px;
  right: -1px;
  z-index: 1;
  width: 18px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: none;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 14px;
}

.tree-toggle-icon {
  transition: transform 0.2s;
}

.tree-toggle-icon--collapsed {
  transform: rotate(180deg);
}

.editor-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>

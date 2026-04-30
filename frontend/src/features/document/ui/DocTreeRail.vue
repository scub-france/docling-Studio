<template>
  <div class="tree-rail" data-e2e="tree-rail">
    <div v-if="loading" class="tree-rail-placeholder">
      <span class="spinner" />
    </div>
    <div v-else-if="error" class="tree-rail-placeholder tree-rail-error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="$emit('reload')">↺</button>
    </div>
    <div v-else-if="!nodes.length" class="tree-rail-placeholder">
      <span class="tree-rail-empty">{{ t('tree.empty') }}</span>
    </div>
    <ul v-else class="tree-list" role="tree">
      <TreeNode
        v-for="node in nodes"
        :key="node.ref"
        :node="node"
        :selected="selected"
        :highlight="highlight"
        @select="(ref) => $emit('select', ref)"
      />
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { DocTreeNode } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import TreeNode from './DocTreeNode.vue'

defineProps<{
  nodes: DocTreeNode[]
  loading?: boolean
  error?: string | null
  selected?: string | null
  highlight?: string | null
}>()

defineEmits<{
  select: [ref: string]
  reload: []
}>()

const { t } = useI18n()
</script>

<style scoped>
.tree-rail {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
}

.tree-rail-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  padding: 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.tree-rail-error {
  color: var(--error);
}

.tree-list {
  list-style: none;
  padding: 8px 0;
}

.retry-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}

.spinner {
  width: 20px;
  height: 20px;
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

.tree-rail-empty {
  font-size: 12px;
  color: var(--text-muted);
}
</style>

<template>
  <li class="tree-node" role="treeitem" :aria-expanded="hasChildren ? open : undefined">
    <button
      class="tree-node-row"
      :class="{
        'tree-node-row--selected': selected === node.ref,
        'tree-node-row--highlight': highlight === node.ref,
      }"
      @click="onRowClick"
    >
      <span class="tree-node-indent" :style="{ width: `${depth * 12}px` }" />
      <span v-if="hasChildren" class="tree-node-toggle" :class="{ open }" @click.stop="open = !open"
        >›</span
      >
      <span v-else class="tree-node-toggle-placeholder" />
      <span class="tree-node-type">{{ node.type }}</span>
      <span class="tree-node-label" :title="node.label">{{ node.label }}</span>
    </button>
    <ul v-if="hasChildren && open" class="tree-list" role="group">
      <DocTreeNode
        v-for="child in node.children"
        :key="child.ref"
        :node="child"
        :depth="depth + 1"
        :selected="selected"
        :highlight="highlight"
        @select="$emit('select', $event)"
      />
    </ul>
  </li>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DocTreeNode } from '../../../shared/types'

const props = withDefaults(
  defineProps<{
    node: DocTreeNode
    depth?: number
    selected?: string | null
    highlight?: string | null
  }>(),
  { depth: 0 },
)

const emit = defineEmits<{
  select: [ref: string]
}>()

const open = ref(props.depth < 2)

const hasChildren = computed(() => props.node.children.length > 0)

function onRowClick(): void {
  emit('select', props.node.ref)
}
</script>

<style scoped>
.tree-node {
  list-style: none;
}

.tree-list {
  list-style: none;
}

.tree-node-row {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 3px 8px 3px 4px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  text-align: left;
  border-radius: 0;
  transition: background var(--transition);
}

.tree-node-row:hover {
  background: var(--bg-elevated);
  color: var(--text);
}

.tree-node-row--selected {
  background: var(--accent-muted);
  color: var(--accent);
}

.tree-node-row--highlight {
  background: var(--warning-muted, rgba(234, 179, 8, 0.1));
  color: var(--text);
}

.tree-node-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  font-size: 12px;
  color: var(--text-muted);
  transform: rotate(0deg);
  transition: transform 0.15s;
  flex-shrink: 0;
}

.tree-node-toggle.open {
  transform: rotate(90deg);
}

.tree-node-toggle-placeholder {
  width: 14px;
  flex-shrink: 0;
}

.tree-node-type {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 0 4px;
  flex-shrink: 0;
  white-space: nowrap;
}

.tree-node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

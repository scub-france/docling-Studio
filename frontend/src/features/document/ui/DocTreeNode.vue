<template>
  <li class="tree-node" role="treeitem" :aria-expanded="hasChildren ? isOpen : undefined">
    <button
      :ref="(el) => registerRow?.(node.ref, el as HTMLElement | null)"
      class="tree-node-row"
      :class="{
        'tree-node-row--selected': Array.isArray(selected) ? selected.includes(node.ref) : selected === node.ref,
        'tree-node-row--highlight': highlight === node.ref,
      }"
      @click="onRowClick"
    >
      <span class="tree-node-indent" :style="{ width: `${depth * 12}px` }" />
      <span
        v-if="hasChildren"
        class="tree-node-toggle"
        :class="{ open: isOpen }"
        @click.stop="toggle"
        >›</span
      >
      <span v-else class="tree-node-toggle-placeholder" />
      <span
        class="tree-node-dot"
        :style="{ background: nodeColor }"
        :title="node.type"
        aria-hidden="true"
      />
      <span class="tree-node-type" :style="{ color: nodeColor, borderColor: nodeColor + '55' }">{{
        node.type
      }}</span>
      <span class="tree-node-label" :title="node.label">{{ node.label }}</span>
    </button>
    <ul v-if="hasChildren && isOpen" class="tree-list" role="group">
      <DocTreeNode
        v-for="child in node.children"
        :key="child.ref"
        :node="child"
        :depth="depth + 1"
        :selected="selected"
        :highlight="highlight"
        :default-open="defaultOpen"
        :revealed-refs="revealedRefs"
        :register-row="registerRow"
        @select="$emit('select', $event)"
      />
    </ul>
  </li>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DocTreeNode } from '../../../shared/types'
import { colorFor } from '@/shared/elementColors'

const props = withDefaults(
  defineProps<{
    node: DocTreeNode
    depth?: number
    selected?: string | string[] | null
    highlight?: string | null
    /** When set, every node mounts in that state (used by Expand/Collapse-all). */
    defaultOpen?: boolean | null
    /** #303 — ancestor refs of the focused element; a node on the path forces open. */
    revealedRefs?: ReadonlySet<string>
    /** #303 — registers this node's row element in the rail's ref-map for scroll. */
    registerRow?: (ref: string, el: HTMLElement | null) => void
  }>(),
  { depth: 0, defaultOpen: null },
)

const emit = defineEmits<{
  select: [ref: string]
}>()

const open = ref(props.defaultOpen ?? props.depth < 3)

// #303 (design §337) — a node forces itself open when it sits on the reveal
// path (its ref is in the focused element's ancestor set), otherwise it honours
// the user's manual toggle / depth default. The rail owns the actual scroll.
const isOpen = computed(() => open.value || (props.revealedRefs?.has(props.node.ref) ?? false))

const hasChildren = computed(() => props.node.children.length > 0)

const nodeColor = computed(() => colorFor(props.node.type))

function onRowClick(): void {
  emit('select', props.node.ref)
}

function toggle(): void {
  open.value = !open.value
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

/* #303 — the focused row reads as the anchor: accent tint + bold label. */
.tree-node-row--selected .tree-node-label,
.tree-node-row--highlight .tree-node-label {
  font-weight: 600;
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

.tree-node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tree-node-type {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
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

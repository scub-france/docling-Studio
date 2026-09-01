<template>
  <div class="editor-node" :class="{ 'editor-node--root': depth === 0 }">
    <div
      class="editor-node-row"
      :class="{
        selected: selectedId === node.elementId,
        checked: checkedIds.includes(node.elementId),
        heading: isHeading,
      }"
      draggable="true"
      @click="$emit('select', node.elementId)"
      @dragstart="$emit('drag-start', node.elementId)"
      @dragover.prevent
      @drop.prevent="$emit('drop', node.elementId)"
    >
      <button
        v-if="node.children.length"
        class="disclosure"
        type="button"
        :aria-label="open ? 'Collapse section' : 'Expand section'"
        :aria-expanded="open"
        @click.stop="open = !open"
      >
        <span :class="{ rotated: open }">›</span>
      </button>
      <span v-else class="disclosure disclosure--empty" />
      <input
        v-if="isText(node.elementId)"
        type="checkbox"
        :checked="checkedIds.includes(node.elementId)"
        @click.stop
        @change="$emit('toggle-merge', node.elementId)"
      />
      <span class="drag-handle" title="Reorder">::</span>
      <span class="node-type">{{ isHeading ? '§' : node.type }}</span>
      <span class="node-label" :title="node.label">{{ node.label }}</span>
      <input
        v-if="node.children.length"
        class="section-selector"
        type="checkbox"
        :checked="descendantTextIds.every((id) => checkedIds.includes(id))"
        :indeterminate="Boolean(descendantTextIds.some((id) => checkedIds.includes(id)) && !descendantTextIds.every((id) => checkedIds.includes(id)))"
        aria-label="Select section children"
        @click.stop
        @change="$emit('toggle-subtree', descendantTextIds)"
      />
    </div>
    <div v-if="node.children.length && open" class="editor-node-children">
      <EditableStructureNode
        v-for="child in node.children"
        :key="child.elementId"
        :node="child"
        :selected-id="selectedId"
        :checked-ids="checkedIds"
        :is-text="isText"
        :default-open="defaultOpen"
        :depth="depth + 1"
        @select="$emit('select', $event)"
        @toggle-merge="$emit('toggle-merge', $event)"
        @toggle-subtree="$emit('toggle-subtree', $event)"
        @drag-start="$emit('drag-start', $event)"
        @drop="$emit('drop', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EditorTreeNode } from '../types'

const props = defineProps<{
  node: EditorTreeNode
  selectedId: string | null
  checkedIds: string[]
  isText: (id: string) => boolean
  defaultOpen?: boolean
  depth?: number
}>()

const open = ref(props.defaultOpen ?? true)
const depth = computed(() => props.depth ?? 0)
const isHeading = computed(() => props.node.type === 'title' || props.node.type === 'section_header')
const descendantTextIds = computed(() => {
  const ids: string[] = []
  const visit = (node: EditorTreeNode): void => {
    if (props.isText(node.elementId)) ids.push(node.elementId)
    node.children.forEach(visit)
  }
  props.node.children.forEach(visit)
  return ids
})

defineEmits<{
  select: [id: string]
  'toggle-merge': [id: string]
  'toggle-subtree': [ids: string[]]
  'drag-start': [id: string]
  drop: [beforeId: string]
}>()
</script>

<style scoped>
.editor-node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 4px 7px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: grab;
  font-size: 12px;
  position: relative;
}
.section-selector { margin-left: auto; }
.editor-node-row:hover,
.editor-node-row.selected {
  background: var(--bg-elevated);
  border-color: var(--border);
}
.editor-node-row.selected { color: var(--accent); }
.editor-node-row.heading .node-label { font-weight: 600; color: var(--text); }
.editor-node-row.checked { border-left: 2px solid var(--accent); }
.editor-node-children { margin-left: 16px; border-left: 1px solid var(--border); padding-left: 5px; }
.disclosure {
  display: grid;
  width: 16px;
  height: 18px;
  flex: 0 0 16px;
  place-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 17px;
  line-height: 1;
}
.disclosure span { transform: rotate(0deg); transition: transform 120ms ease; }
.disclosure span.rotated { transform: rotate(90deg); }
.disclosure--empty { cursor: default; }
.drag-handle { color: var(--text-muted); letter-spacing: -2px; }
.node-type { color: var(--accent); font: 10px 'IBM Plex Mono', monospace; }
.node-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>

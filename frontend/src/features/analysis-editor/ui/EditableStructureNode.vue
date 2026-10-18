<template>
  <div
    class="editor-node"
    :class="{ 'editor-node--root': depth === 0 }"
    :data-e2e="`analysis-editor-item-${itemToken(node.label)}`"
  >
    <div
      class="editor-node-row"
      role="treeitem"
      :data-e2e="`analysis-editor-tree-item-${itemToken(node.label)}`"
      :aria-label="node.label"
      tabindex="0"
      :aria-selected="selectedId === node.elementId"
      :aria-expanded="node.children.length ? open : undefined"
      :class="{
        selected: selectedId === node.elementId,
        checked: checkedIds.includes(node.elementId),
        heading: isHeading,
      }"
      :draggable="isMovable(node.elementId)"
      @click="$emit('select', node.elementId)"
      @keydown.enter.prevent="$emit('select', node.elementId)"
      @keydown.space.prevent="$emit('select', node.elementId)"
      @keydown.right.prevent="open = true"
      @keydown.left.prevent="open = false"
      @dragstart="$emit('drag-start', node.elementId)"
      @dragover.prevent
      @drop.prevent="$emit('drop', node.elementId, 'before')"
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
        data-e2e="analysis-editor-merge-select"
        :checked="checkedIds.includes(node.elementId)"
        :aria-label="t('analysisEditor.selectForMerge', { label: node.label })"
        @click.stop
        @change="$emit('toggle-merge', node.elementId)"
      />
      <span v-if="isMovable(node.elementId)" class="drag-handle" title="Reorder">::</span>
      <span class="node-type">{{ isHeading ? '§' : node.type }}</span>
      <span class="node-label" :title="node.label">{{ node.label }}</span>
      <input
        v-if="node.children.length"
        class="section-selector"
        type="checkbox"
        :checked="descendantIds.every((id) => checkedIds.includes(id))"
        :indeterminate="
          Boolean(
            descendantIds.some((id) => checkedIds.includes(id)) &&
            !descendantIds.every((id) => checkedIds.includes(id)),
          )
        "
        aria-label="Select section children"
        @click.stop
        @change="$emit('toggle-subtree', descendantIds)"
      />
    </div>
    <div v-if="dragging" class="drop-targets">
      <button
        type="button"
        data-e2e="analysis-editor-move-before"
        @dragover.prevent
        @drop.prevent="$emit('drop', node.elementId, 'before')"
        @click="$emit('drop', node.elementId, 'before')"
      >
        {{ t('analysisEditor.dropBefore') }}
      </button>
      <button
        type="button"
        data-e2e="analysis-editor-move-after"
        @dragover.prevent
        @drop.prevent="$emit('drop', node.elementId, 'after')"
        @click="$emit('drop', node.elementId, 'after')"
      >
        {{ t('analysisEditor.dropAfter') }}
      </button>
      <button
        v-if="isHeading"
        type="button"
        data-e2e="analysis-editor-move-inside"
        @dragover.prevent
        @drop.prevent="$emit('drop', node.elementId, 'inside')"
        @click="$emit('drop', node.elementId, 'inside')"
      >
        {{ t('analysisEditor.dropInside') }}
      </button>
    </div>
    <div v-if="node.children.length && open" class="editor-node-children">
      <EditableStructureNode
        v-for="child in node.children"
        :key="child.elementId"
        :node="child"
        :selected-id="selectedId"
        :checked-ids="checkedIds"
        :is-text="isText"
        :is-movable="isMovable"
        :dragging="dragging"
        :default-open="defaultOpen"
        :depth="depth + 1"
        @select="$emit('select', $event)"
        @toggle-merge="$emit('toggle-merge', $event)"
        @toggle-subtree="$emit('toggle-subtree', $event)"
        @drag-start="$emit('drag-start', $event)"
        @drop="(id, placement) => $emit('drop', id, placement)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EditorTreeNode } from '../types'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  node: EditorTreeNode
  selectedId: string | null
  checkedIds: string[]
  isText: (id: string) => boolean
  isMovable: (id: string) => boolean
  dragging: boolean
  defaultOpen?: boolean
  depth?: number
}>()

const open = ref(props.defaultOpen ?? true)
const { t } = useI18n()
function itemToken(label: string): string {
  return (
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'node'
  )
}
const depth = computed(() => props.depth ?? 0)
const isHeading = computed(
  () => props.node.type === 'title' || props.node.type === 'section_header',
)
const descendantIds = computed(() => {
  const ids: string[] = []
  const visit = (node: EditorTreeNode): void => {
    ids.push(node.elementId)
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
  drop: [targetId: string, placement: 'before' | 'after' | 'inside']
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
.section-selector {
  margin-left: auto;
}
.editor-node-row:hover,
.editor-node-row.selected {
  background: var(--bg-elevated);
  border-color: var(--border);
}
.editor-node-row.selected {
  color: var(--accent);
}
.editor-node-row:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.editor-node-row.heading .node-label {
  font-weight: 600;
  color: var(--text);
}
.editor-node-row.checked {
  border-left: 2px solid var(--accent);
}
.editor-node-children {
  margin-left: 16px;
  border-left: 1px solid var(--border);
  padding-left: 5px;
}
.drop-targets {
  display: flex;
  gap: 4px;
  padding: 2px 7px 5px 29px;
}
.drop-targets button {
  border: 1px dashed var(--accent);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent);
  padding: 2px 5px;
  font-size: 10px;
}
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
.disclosure span {
  transform: rotate(0deg);
  transition: transform 120ms ease;
}
.disclosure span.rotated {
  transform: rotate(90deg);
}
.disclosure--empty {
  cursor: default;
}
.drag-handle {
  color: var(--text-muted);
  letter-spacing: -2px;
}
.node-type {
  color: var(--accent);
  font:
    10px 'IBM Plex Mono',
    monospace;
}
.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

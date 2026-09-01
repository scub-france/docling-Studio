<template>
  <div ref="railEl" class="tree-rail" data-e2e="tree-rail">
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
        :default-open="defaultOpen"
        :revealed-refs="revealedRefs"
        :register-row="registerRow"
        @select="(ref) => $emit('select', ref)"
      />
    </ul>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { DocTreeNode } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import TreeNode from './DocTreeNode.vue'

const props = defineProps<{
  nodes: DocTreeNode[]
  loading?: boolean
  error?: string | null
  selected?: string | string[] | null
  highlight?: string | null
  /** Forwarded to every node — null lets each node use its depth-based default. */
  defaultOpen?: boolean | null
  /** #303 — ancestor refs of the focused element; nodes on the path force open. */
  revealedRefs?: ReadonlySet<string>
  /** #303 — the focused element's ref (the row to scroll to). */
  focusedRef?: string | null
  /** #303 — bumps on every focus (even a same-ref re-click) to re-fire the scroll. */
  revealTick?: number
}>()

defineEmits<{
  select: [ref: string]
  reload: []
}>()

const { t } = useI18n()

const railEl = ref<HTMLDivElement | null>(null)

// #303 (design §337) — ref-map of ref → row element (the ChunksPanel pattern),
// populated by each DocTreeNode's function ref. The rail (not the node) owns
// the scroll so it can center the focused row in *its* viewport via offset math
// — deliberately not `scrollIntoView`, which jumps ancestor scroll containers.
const rowRefs = new Map<string, HTMLElement>()

function registerRow(ref: string, el: HTMLElement | null): void {
  if (el) rowRefs.set(ref, el)
  else rowRefs.delete(ref)
}

function scrollFocusedToCenter(): void {
  const rail = railEl.value
  const ref = props.focusedRef
  if (!rail || !ref) return
  const el = rowRefs.get(ref)
  if (!el) return
  // Center the focused row in the rail's viewport via bounding-rect math —
  // robust to offset-parent quirks, and deliberately not `scrollIntoView`
  // (which would also jump ancestor scroll containers like the page).
  const railRect = rail.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  const delta = elRect.top - railRect.top - (rail.clientHeight - elRect.height) / 2
  rail.scrollTo({ top: Math.max(0, rail.scrollTop + delta), behavior: 'smooth' })
}

// Re-fire on every focus pulse — `revealTick` bumps even when `focusedRef` is
// unchanged (re-clicking the same step), and `nextTick` lets the just-revealed
// ancestors mount their rows before we look them up.
watch(
  () => props.revealTick,
  () => nextTick(scrollFocusedToCenter),
)
</script>

<style scoped>
.tree-rail {
  position: relative;
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

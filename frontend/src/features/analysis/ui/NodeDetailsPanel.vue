<template>
  <aside
    v-if="node"
    class="nd-panel"
    data-e2e="node-details-panel"
    role="complementary"
    :aria-label="t('graph.nodeDetails')"
  >
    <header class="nd-header">
      <span class="nd-kind-chip" :style="{ background: kindColor }">{{ kindLabel }}</span>
      <button class="nd-close" :aria-label="t('graph.close')" @click="$emit('close')">✕</button>
    </header>

    <dl class="nd-fields">
      <template v-if="selfRef">
        <dt>self_ref</dt>
        <dd class="nd-mono">{{ selfRef }}</dd>
      </template>

      <template v-if="doclingLabel">
        <dt>docling_label</dt>
        <dd class="nd-mono">{{ doclingLabel }}</dd>
      </template>

      <template v-if="level != null">
        <dt>level</dt>
        <dd class="nd-mono">{{ level }}</dd>
      </template>

      <template v-if="pageNo != null">
        <dt>{{ t('graph.page') }}</dt>
        <dd class="nd-mono">p.{{ pageNo }}</dd>
      </template>

      <template v-if="chunkIndex != null">
        <dt>chunk index</dt>
        <dd class="nd-mono">#{{ chunkIndex }}</dd>
      </template>
    </dl>

    <section v-if="text" class="nd-text-block">
      <h4 class="nd-section-title">{{ t('graph.text') }}</h4>
      <p class="nd-text">{{ text }}</p>
    </section>

    <section v-if="provs.length > 0" class="nd-provs-block">
      <h4 class="nd-section-title">
        {{ t('graph.provenances').replace('{n}', String(provs.length)) }}
      </h4>
      <ul class="nd-provs">
        <li v-for="(p, i) in provs" :key="i" class="nd-prov">
          <span class="nd-prov-page">p.{{ p.page_no ?? '?' }}</span>
          <span class="nd-prov-bbox">
            [{{ formatCoord(p.bbox_l) }}, {{ formatCoord(p.bbox_t) }}, {{ formatCoord(p.bbox_r) }},
            {{ formatCoord(p.bbox_b) }}]
          </span>
          <span v-if="p.coord_origin" class="nd-prov-origin">{{ p.coord_origin }}</span>
        </li>
      </ul>
    </section>

    <section v-if="contents && contents.length > 0" class="nd-contents-block">
      <h4 class="nd-section-title">
        {{ t('graph.contains').replace('{n}', String(contents.length)) }}
      </h4>
      <ul class="nd-contents">
        <li v-for="child in contents" :key="child.id">
          <button
            type="button"
            class="nd-child"
            :data-e2e="`node-details-child-${child.id}`"
            @click="$emit('navigate', child)"
          >
            <span
              class="nd-child-chip"
              :style="{ background: getKindColor(child) }"
              :title="child.label ?? child.group"
            >
              {{ getKindLabel(child) }}
            </span>
            <span class="nd-child-text">{{ formatPreviewText(child) }}</span>
          </button>
        </li>
      </ul>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useI18n } from '../../../shared/i18n'
import type { GraphNode, GraphProvenance } from '../graphApi'

const props = defineProps<{
  node: GraphNode | null
  /**
   * Nodes whose compound parent (PARENT_OF or synthetic section scope) is the
   * currently-selected node. Computed upstream in GraphView so we don't have
   * to re-walk the whole edge list here. Empty or null for leaf nodes.
   */
  contents?: readonly GraphNode[] | null
}>()
defineEmits<{
  close: []
  /** User clicked a child row — GraphView pans + swaps selection. */
  navigate: [node: GraphNode]
}>()

const { t } = useI18n()

// Centralised colour map, mirrors NODE_COLORS in GraphView — keeping a copy
// here avoids coupling the detail panel to GraphView's internal state.
const KIND_COLORS: Record<string, string> = {
  document: '#1E293B',
  SectionHeader: '#F97316',
  Paragraph: '#3B82F6',
  TextElement: '#3B82F6',
  Table: '#8B5CF6',
  Figure: '#22C55E',
  List: '#06B6D4',
  ListItem: '#06B6D4',
  Formula: '#EC4899',
  Code: '#14B8A6',
  Caption: '#EAB308',
  PageHeader: '#64748B',
  PageFooter: '#64748B',
  KeyValueArea: '#D946EF',
  FormArea: '#D946EF',
  DocumentIndex: '#0EA5E9',
  Page: '#94A3B8',
  Chunk: '#DC2626',
}

const kindLabel = computed<string>(() => {
  const n = props.node
  if (!n) return ''
  if (n.group === 'document') return 'Document'
  if (n.group === 'page') return 'Page'
  if (n.group === 'chunk') return 'Chunk'
  return n.label ?? 'Element'
})

const kindColor = computed<string>(() => {
  const n = props.node
  if (!n) return '#64748B'
  if (n.group === 'document') return KIND_COLORS.document
  if (n.group === 'page') return KIND_COLORS.Page
  if (n.group === 'chunk') return KIND_COLORS.Chunk
  return KIND_COLORS[n.label ?? ''] || KIND_COLORS.TextElement
})

const selfRef = computed(() => props.node?.self_ref ?? null)
const doclingLabel = computed(() => (props.node?.docling_label as string | undefined) ?? null)
const level = computed<number | null>(() => {
  const v = props.node?.level
  return typeof v === 'number' ? v : null
})
const pageNo = computed<number | null>(() => {
  const v = props.node?.page_no ?? props.node?.prov_page
  return typeof v === 'number' ? v : null
})
const chunkIndex = computed<number | null>(() => {
  const v = props.node?.chunk_index
  return typeof v === 'number' ? v : null
})
const text = computed<string>(() => (props.node?.text as string | undefined) ?? '')
const provs = computed<GraphProvenance[]>(() => (props.node?.provs as GraphProvenance[]) ?? [])

function formatCoord(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toFixed(1)
}

// Label + color helpers factored so they work for children too, not just the
// currently-selected node. Keep them consistent with the chips above.
function getKindLabel(n: GraphNode): string {
  if (n.group === 'document') return 'Document'
  if (n.group === 'page') return 'Page'
  if (n.group === 'chunk') return 'Chunk'
  return n.label ?? 'Element'
}

function getKindColor(n: GraphNode): string {
  if (n.group === 'document') return KIND_COLORS.document
  if (n.group === 'page') return KIND_COLORS.Page
  if (n.group === 'chunk') return KIND_COLORS.Chunk
  return KIND_COLORS[n.label ?? ''] || KIND_COLORS.TextElement
}

/**
 * Short label for a child row. Prefer the node's own text (truncated), fall
 * back to its self_ref so users can still recognise / debug missing text.
 */
function formatPreviewText(n: GraphNode): string {
  const raw = (n.text as string | undefined) ?? ''
  const clean = raw.replace(/\s+/g, ' ').trim()
  if (clean) return clean.length > 80 ? clean.slice(0, 80) + '…' : clean
  if (n.group === 'page') return `p.${n.page_no ?? '?'}`
  if (n.group === 'chunk') return `chunk #${n.chunk_index ?? '?'}`
  return n.self_ref ?? n.id
}
</script>

<style scoped>
.nd-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 320px;
  flex: 0 0 320px;
  padding: 14px 16px;
  background: var(--bg);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  height: 100%;
}

.nd-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nd-kind-chip {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  color: #f8fafc;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.nd-close {
  background: transparent;
  border: 0;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.nd-close:hover {
  background: var(--border-light);
  color: var(--text);
}

.nd-fields {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 6px 10px;
  margin: 0;
  font-size: 12px;
}

.nd-fields dt {
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.4px;
  align-self: center;
}

.nd-fields dd {
  margin: 0;
  color: var(--text);
}

.nd-mono {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
}

.nd-section-title {
  margin: 0 0 6px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.nd-text-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
}

.nd-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text);
  white-space: pre-wrap;
}

.nd-provs-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
}

.nd-provs {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nd-prov {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: 6px;
  align-items: baseline;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  padding: 4px 6px;
  background: var(--border-light);
  border-radius: var(--radius-sm);
}

.nd-prov-page {
  font-weight: 700;
  color: var(--text);
}

.nd-prov-bbox {
  color: var(--text-secondary);
}

.nd-prov-origin {
  color: var(--text-muted);
  font-size: 9px;
  text-transform: lowercase;
}

.nd-contents-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
}

.nd-contents {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  /* Cap the list height so a section with hundreds of paragraphs doesn't
   * blow the panel out. Scroll internally above that. */
  max-height: 340px;
  overflow-y: auto;
}

.nd-child {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: 5px 8px;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: all var(--transition);
}

.nd-child:hover {
  background: var(--border-light);
  border-color: var(--border);
}

.nd-child-chip {
  flex: 0 0 auto;
  display: inline-block;
  padding: 1px 7px;
  border-radius: 8px;
  color: #f8fafc;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.nd-child-text {
  flex: 1 1 auto;
  font-size: 12px;
  line-height: 1.4;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>

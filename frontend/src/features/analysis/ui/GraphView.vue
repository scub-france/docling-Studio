<template>
  <div class="graph-view" data-e2e="graph-view">
    <div v-if="loading" class="graph-placeholder">
      <div class="spinner-large" />
      <span>{{ t('results.graphLoading') }}</span>
    </div>
    <div v-else-if="error" class="graph-placeholder error" data-e2e="graph-error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="load">{{ t('results.retry') }}</button>
    </div>
    <div v-else-if="empty" class="graph-placeholder">
      <span>{{ t('results.graphEmpty') }}</span>
    </div>
    <template v-else>
      <div class="graph-toolbar">
        <span class="graph-stats">
          {{ payload?.node_count }} nodes · {{ payload?.edge_count }} edges ·
          {{ payload?.page_count }} pages
        </span>
        <span class="graph-legend">
          <button
            v-for="chip in visibleChips"
            :key="chip.key"
            type="button"
            class="legend-chip"
            :class="[`legend-${chip.key}`, { 'legend-off': hiddenChips.has(chip.key) }]"
            :data-e2e="`legend-${chip.key}`"
            :title="
              hiddenChips.has(chip.key) ? `Show ${chip.label} nodes` : `Hide ${chip.label} nodes`
            "
            :aria-pressed="!hiddenChips.has(chip.key)"
            @click="toggleChip(chip.key)"
          >
            {{ chip.label }}
          </button>
        </span>
      </div>
      <div class="graph-body">
        <div class="graph-canvas-wrap">
          <div ref="containerRef" class="graph-canvas" data-e2e="graph-canvas" />
          <!-- Hover tooltip, positioned inside the canvas wrap so its
               coords match cy.renderedPosition() exactly. -->
          <div
            v-if="tooltip"
            class="graph-tooltip"
            data-e2e="graph-tooltip"
            :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
          >
            {{ tooltip.text }}
          </div>
        </div>
        <NodeDetailsPanel
          :node="selectedNode"
          :contents="selectedNodeContents"
          @close="closeDetails"
          @navigate="navigateToNode"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Core } from 'cytoscape'
import { computed, onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { useI18n } from '../../../shared/i18n'
import { fetchDocumentGraph, type GraphNode, type GraphPayload } from '../graphApi'
import { LEGEND_CHIPS, findChip } from '../legendFilters'
import { computeSectionParents, explicitParentMap, mergeParentMaps } from '../sectionParenting'
import NodeDetailsPanel from './NodeDetailsPanel.vue'

const props = defineProps<{
  docId: string | null
}>()
const { t } = useI18n()

const containerRef = ref<HTMLDivElement | null>(null)
const payload = ref<GraphPayload | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const empty = ref(false)
// The live Cytoscape instance — null while the graph is loading / empty /
// unmounted. Internal to this component.
const cy = ref<Core | null>(null)

// Legend-driven visibility: user clicks a chip → its key lands here and the
// matching nodes get the `.hidden` Cytoscape class. Reset to empty every time
// the doc changes (see the `watch(() => props.docId)` below) — kept as a Set
// because order doesn't matter and membership checks are the hot path.
const hiddenChips = ref<Set<string>>(new Set())

// Click → details panel. Null = panel hidden.
const selectedNode = ref<GraphNode | null>(null)

// Compound parenting map (childId → parentId), kept in sync with the
// Cytoscape render so the details panel can show "this section contains …".
// Updated at the end of `renderGraph` — before that it's empty.
const parentMap = ref<Map<string, string>>(new Map())

// Inverse index of parentMap: parentId → childId[]. Enables the
// NodeDetailsPanel "contents" section (click a section → see what's in it).
const childrenByParent = computed<Map<string, GraphNode[]>>(() => {
  const out = new Map<string, GraphNode[]>()
  const byId = new Map<string, GraphNode>()
  for (const n of payload.value?.nodes ?? []) byId.set(n.id, n)
  for (const [childId, parentId] of parentMap.value) {
    const child = byId.get(childId)
    if (!child) continue
    if (!out.has(parentId)) out.set(parentId, [])
    out.get(parentId)!.push(child)
  }
  return out
})

const selectedNodeContents = computed<GraphNode[]>(() => {
  const id = selectedNode.value?.id
  if (!id) return []
  return childrenByParent.value.get(id) ?? []
})

// Only surface chips that actually have matching nodes in the current
// payload. Keeps the legend in sync with the source (e.g. Reasoning view
// never emits Chunk nodes, so the Chunk chip would dangle) without
// hardcoding per-view chip lists.
const visibleChips = computed(() => {
  const nodes = payload.value?.nodes ?? []
  if (nodes.length === 0) return []
  return LEGEND_CHIPS.filter((chip) => nodes.some((n) => chip.match(n)))
})

// Hover tooltip: position (px within .graph-canvas) + text. Null hides it.
const tooltip = ref<{ x: number; y: number; text: string } | null>(null)

const NODE_COLORS: Record<string, string> = {
  document: '#1E293B',
  SectionHeader: '#F97316',
  Paragraph: '#3B82F6',
  TextElement: '#3B82F6',
  Table: '#8B5CF6',
  Figure: '#22C55E',
  ListItem: '#06B6D4',
  Formula: '#EC4899',
  Code: '#14B8A6',
  Caption: '#EAB308',
  Page: '#94A3B8',
  Chunk: '#DC2626',
}

function nodeColor(n: GraphPayload['nodes'][number]): string {
  if (n.group === 'document') return NODE_COLORS.document
  if (n.group === 'page') return NODE_COLORS.Page
  if (n.group === 'chunk') return NODE_COLORS.Chunk
  return NODE_COLORS[n.label || 'TextElement'] || NODE_COLORS.TextElement
}

function nodeLabel(n: GraphPayload['nodes'][number]): string {
  if (n.group === 'document') return n.title || n.id
  if (n.group === 'page') return `p.${n.page_no}`
  if (n.group === 'chunk') return `chunk #${n.chunk_index}`
  const txt = (n.text || '').slice(0, 40)
  return txt || n.label || n.docling_label || n.self_ref || n.id
}

async function load(): Promise<void> {
  if (!props.docId) {
    empty.value = true
    return
  }
  loading.value = true
  error.value = null
  empty.value = false
  try {
    payload.value = await fetchDocumentGraph(props.docId)
    if (!payload.value.nodes.length) {
      empty.value = true
      return
    }
    // Flip loading off so the canvas <div> mounts, then wait a tick before init.
    loading.value = false
    await nextTick()
    await renderGraph()
    // Re-apply any chips the user had toggled before this load (e.g. they
    // hid Pages on doc A, then navigated to doc B — keep Pages hidden).
    applyHiddenChips()
  } catch (e) {
    error.value = (e as Error).message || 'Failed to load graph'
    console.error('Failed to load graph', e)
  } finally {
    loading.value = false
  }
}

async function renderGraph(): Promise<void> {
  if (!containerRef.value || !payload.value) return
  // Dynamic imports keep the heavy Cytoscape bundle out of the main chunk.
  const [{ default: cytoscape }, { default: dagre }, ecMod] = await Promise.all([
    import('cytoscape'),
    import('cytoscape-dagre'),
    import('cytoscape-expand-collapse'),
  ])

  const C = cytoscape as any
  C.use(dagre)
  // Plugin registration is idempotent — calling use() twice is a no-op.
  C.use((ecMod as any).default ?? ecMod)

  if (cy.value) {
    cy.value.destroy()
    cy.value = null
  }

  // Compute compound parenting: merge docling-native PARENT_OF with the
  // synthetic section-scope parents so every non-root element sits inside
  // its section visually (enables per-section collapse via the legend chips
  // and the expand-collapse plugin). Also persisted on `parentMap` so the
  // NodeDetailsPanel can list what a given section contains.
  const computedParentMap = mergeParentMaps(
    explicitParentMap(payload.value.edges),
    computeSectionParents(payload.value.nodes, payload.value.edges),
  )
  parentMap.value = computedParentMap

  const elements = [
    ...payload.value.nodes.map((n) => ({
      data: {
        id: n.id,
        label: nodeLabel(n),
        // `kindLabel` is the specific Neo4j label (SectionHeader, Paragraph,
        // Figure, …) — kept as a data attribute so legend filters can match
        // on it. `label` above is the human display string for Cytoscape.
        kindLabel: n.label ?? null,
        bg: nodeColor(n),
        group: n.group,
        // Compound-node parent: used by the expand-collapse plugin to
        // fold/unfold a section's scope. `undefined` = this node is a root
        // of the compound hierarchy (Documents, unparented sections, etc.).
        parent: computedParentMap.get(n.id),
        raw: n,
      },
    })),
    ...payload.value.edges.map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
      },
    })),
  ]

  cy.value = cytoscape({
    container: containerRef.value,
    elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(bg)',
          label: 'data(label)',
          color: '#0F172A',
          'font-size': 10,
          'text-wrap': 'ellipsis',
          'text-max-width': '140px',
          'text-valign': 'center',
          'text-halign': 'center',
          width: 28,
          height: 28,
          'border-width': 1,
          'border-color': '#0F172A',
        },
      },
      {
        selector: 'node[group = "document"]',
        style: { shape: 'round-rectangle', width: 60, height: 36, color: '#F8FAFC' },
      },
      {
        selector: 'node[group = "page"]',
        style: { shape: 'round-rectangle', width: 40, height: 24 },
      },
      {
        selector: 'node[group = "chunk"]',
        style: { shape: 'diamond', color: '#F8FAFC' },
      },
      {
        selector: 'edge',
        style: {
          width: 1,
          'line-color': '#94A3B8',
          'target-arrow-color': '#94A3B8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'font-size': 8,
          color: '#64748B',
        },
      },
      {
        selector: 'edge[type = "PARENT_OF"]',
        style: { 'line-color': '#1E293B', 'target-arrow-color': '#1E293B', width: 1.5 },
      },
      {
        selector: 'edge[type = "NEXT"]',
        style: { 'line-style': 'dashed', 'line-color': '#64748B' },
      },
      {
        selector: 'edge[type = "ON_PAGE"]',
        style: { 'line-color': '#CBD5E1', width: 1 },
      },
      {
        selector: 'edge[type = "DERIVED_FROM"]',
        style: { 'line-color': '#DC2626', 'target-arrow-color': '#DC2626' },
      },
      // Legend-driven visibility: chips toggle the `.hidden` class on
      // matching nodes. `display: none` cascades to connected edges for free.
      { selector: 'node.hidden', style: { display: 'none' } },
      // Compound nodes (section scope + explicit PARENT_OF containers). A
      // node with :parent children is rendered as a bounding box here —
      // visually groups the section's content together. Minimal padding so
      // the layout stays compact.
      {
        selector: ':parent',
        style: {
          'background-opacity': 0.08,
          'background-color': '#F97316',
          'border-color': '#FDBA74',
          'border-width': 1,
          'padding-top': '12px',
          'padding-bottom': '12px',
          'padding-left': '12px',
          'padding-right': '12px',
          'text-valign': 'top',
          'text-halign': 'center',
          'text-margin-y': -4,
          shape: 'round-rectangle',
        },
      },
      // Click-selected node: stronger border so the user sees which one
      // populated the details panel.
      {
        selector: 'node.nd-selected',
        style: {
          'border-width': 4,
          'border-color': '#0EA5E9',
          'overlay-color': '#0EA5E9',
          'overlay-opacity': 0.12,
          'overlay-padding': 4,
          'z-index': 60,
        },
      },
    ],

    layout: {
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 30,
      edgeSep: 10,
      rankSep: 40,
    } as any,
    wheelSensitivity: 0.15,
  })

  // --- Plugin activation ---------------------------------------------------
  // Expand/collapse on compound nodes. `layoutBy` re-runs dagre after each
  // toggle so the graph stays tidy. Don't animate — on big docs the per-node
  // tween is choppy and the user just wants the end state.
  ;(cy.value as any).expandCollapse({
    layoutBy: { name: 'dagre', rankDir: 'TB', nodeSep: 30, rankSep: 40 },
    fisheye: false,
    animate: false,
    undoable: false,
    cueEnabled: true, // shows the +/- cue on compound nodes
    expandCollapseCuePosition: 'top-left',
    expandCollapseCueSize: 12,
  })

  // --- Interactions --------------------------------------------------------
  cy.value.on('tap', 'node', (evt) => {
    const raw = evt.target.data('raw') as GraphNode | undefined
    if (!raw) return
    selectedNode.value = raw
    // Visual feedback — clear previous selection class first.
    cy.value?.nodes('.nd-selected').removeClass('nd-selected')
    evt.target.addClass('nd-selected')
  })
  // Click on background → close details panel.
  cy.value.on('tap', (evt) => {
    if (evt.target === cy.value) {
      selectedNode.value = null
      cy.value?.nodes('.nd-selected').removeClass('nd-selected')
    }
  })

  // Hover tooltip — shows the full node text (backend truncates to 200 chars).
  cy.value.on('mouseover', 'node', (evt) => {
    const raw = evt.target.data('raw') as GraphNode | undefined
    if (!raw) return
    const text = tooltipTextFor(raw)
    if (!text) return
    const pos = evt.target.renderedPosition()
    tooltip.value = { x: pos.x, y: pos.y, text }
  })
  cy.value.on('mouseout', 'node', () => {
    tooltip.value = null
  })
  cy.value.on('pan zoom', () => {
    // Tooltip coordinates are in rendered space; on pan/zoom they're stale.
    tooltip.value = null
  })
}

/**
 * What to show on hover: prefer the node's full text, then title, then ref.
 * Keeps the tooltip useful across node kinds (Document/Page/Chunk too).
 */
function tooltipTextFor(n: GraphNode): string {
  if (n.group === 'document') return (n.title as string | undefined) ?? n.id
  if (n.group === 'page') return `Page ${n.page_no ?? '?'}`
  if (n.group === 'chunk') {
    const head = ((n.text as string | undefined) ?? '').slice(0, 160)
    return head ? `chunk #${n.chunk_index ?? '?'}\n${head}` : `chunk #${n.chunk_index ?? '?'}`
  }
  const text = (n.text as string | undefined) ?? ''
  const ref = n.self_ref ?? ''
  if (text) return text
  return ref || n.label || ''
}

function closeDetails(): void {
  selectedNode.value = null
  cy.value?.nodes('.nd-selected').removeClass('nd-selected')
}

/**
 * Triggered when the user clicks a child row inside the NodeDetailsPanel
 * (e.g. the "Contents" list of a section). Switch the selection, center the
 * viewport on the target, and flash the node briefly so the eye can catch it.
 */
function navigateToNode(target: GraphNode): void {
  selectedNode.value = target
  if (!cy.value) return
  cy.value.nodes('.nd-selected').removeClass('nd-selected')
  const el = cy.value.getElementById(target.id)
  if (el && el.length > 0) {
    el.addClass('nd-selected')
    cy.value.animate({ center: { eles: el }, duration: 250 })
  }
}

function disposeGraph(): void {
  if (cy.value) {
    cy.value.destroy()
    cy.value = null
  }
  selectedNode.value = null
  tooltip.value = null
}

/**
 * Apply the current `hiddenChips` set to the Cytoscape instance — marks
 * every node whose chip is in the set with the `.hidden` class, and clears
 * the class from nodes whose chip is no longer hidden.
 *
 * Called after every re-render (so chip state survives a doc reload) and
 * whenever the user toggles a chip.
 */
function applyHiddenChips(): void {
  const c = cy.value
  if (!c) return

  c.nodes().forEach((n: any) => {
    const raw = n.data('raw')
    if (!raw) return
    const hiddenByChip = [...hiddenChips.value].some((key) => {
      const chip = findChip(key)
      return chip?.match(raw) ?? false
    })
    if (hiddenByChip) n.addClass('hidden')
    else n.removeClass('hidden')
  })
}

function toggleChip(key: string): void {
  const next = new Set(hiddenChips.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  hiddenChips.value = next
  applyHiddenChips()
}

onMounted(load)
onBeforeUnmount(disposeGraph)
watch(
  () => props.docId,
  () => {
    disposeGraph()
    load()
  },
)

// Let parent components observe the live Cytoscape instance (e.g. the
// reasoning-trace overlay reads it via `graphViewRef.value?.cy`).
defineExpose({ load })
</script>

<style scoped>
.graph-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  gap: 12px;
  flex-wrap: wrap;
}

.graph-stats {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.graph-legend {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.legend-chip {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  color: #f8fafc;
  border: 0;
  cursor: pointer;
  font-family: inherit;
  transition: opacity var(--transition);
}

.legend-chip:hover {
  filter: brightness(1.12);
}

/* Inactive (user clicked the chip to hide that node kind). */
.legend-chip.legend-off {
  opacity: 0.32;
  text-decoration: line-through;
  filter: saturate(0.4);
}

.legend-document {
  background: #1e293b;
}
.legend-section {
  background: #f97316;
}
.legend-paragraph {
  background: #3b82f6;
}
.legend-table {
  background: #8b5cf6;
}
.legend-figure {
  background: #22c55e;
}
.legend-page {
  background: #94a3b8;
  color: #0f172a;
}
.legend-chunk {
  background: #dc2626;
}

.graph-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

.graph-canvas-wrap {
  flex: 1 1 auto;
  min-width: 0;
  position: relative;
  overflow: hidden;
}

.graph-canvas {
  position: absolute;
  inset: 0;
  background: var(--bg);
}

.graph-tooltip {
  position: absolute;
  transform: translate(-50%, calc(-100% - 14px));
  max-width: 280px;
  padding: 6px 10px;
  background: rgba(15, 23, 42, 0.94);
  color: #f8fafc;
  font-size: 11px;
  line-height: 1.4;
  border-radius: var(--radius-sm);
  pointer-events: none;
  white-space: pre-wrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 20;
}

.graph-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
  padding: 32px;
  text-align: center;
}

.graph-placeholder.error {
  color: var(--error);
}

.retry-btn {
  background: var(--accent);
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
}

.spinner-large {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

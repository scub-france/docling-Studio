<template>
  <div class="structure-viewer">
    <!-- Page selector -->
    <div class="page-selector" v-if="pages.length > 1">
      <button
        v-for="p in pages"
        :key="p.page_number"
        class="page-btn"
        :class="{ active: selectedPage === p.page_number }"
        @click="selectedPage = p.page_number"
      >
        {{ p.page_number }}
      </button>
    </div>

    <!-- Legend -->
    <div class="legend">
      <button
        v-for="[type, color] in Object.entries(ELEMENT_COLORS)"
        :key="type"
        class="legend-item"
        :class="{ dimmed: hiddenTypes.has(type) }"
        @click="toggleType(type)"
      >
        <span class="legend-dot" :style="{ background: color }" />
        <span>{{ type }}</span>
        <span class="legend-count">{{ countElements(type) }}</span>
      </button>
    </div>

    <!-- Canvas overlay -->
    <div class="canvas-container" ref="containerRef">
      <img
        v-if="documentId"
        :src="previewUrl ?? undefined"
        class="page-image"
        ref="imageRef"
        @load="onImageLoad"
      />
      <canvas
        ref="canvasRef"
        class="overlay-canvas"
        :class="{ selectable }"
        @mousemove="onMouseMove"
        @mouseleave="hoveredElement = null"
        @click="onCanvasClick"
      />
      <!-- Tooltip -->
      <div v-if="hoveredElement" class="tooltip" :style="tooltipStyle">
        <span
          class="tooltip-type"
          :style="{ color: ELEMENT_COLORS[hoveredElement.type] || ELEMENT_COLORS.text }"
        >
          {{ hoveredElement.type }}
        </span>
        <span class="tooltip-content">{{ hoveredElement.content?.substring(0, 150) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, reactive } from 'vue'
import { getPreviewUrl } from '../../document/api'
import { computeScale, bboxToRect, pointInRect } from '../../document/bboxScaling'
import type { Page, PageElement } from '../../../shared/types'

const ELEMENT_COLORS: Record<string, string> = {
  section_header: '#F97316',
  text: '#3B82F6',
  table: '#8B5CF6',
  picture: '#22C55E',
  list: '#06B6D4',
  formula: '#EC4899',
  caption: '#EAB308',
}

const props = defineProps({
  pages: { type: Array as () => Page[], default: () => [] },
  documentId: String,
  /**
   * Reasoning-trace integration hooks. Optional — when unset, StructureViewer
   * renders like before (Studio "Structure" tab). When set, enables overlays
   * for the reasoning viewer without forking the component:
   *
   * - `visitedBySelfRef`: elements whose `self_ref` is in this map render in
   *   the reasoning accent color with a numbered badge (the visit order).
   * - `focusedSelfRef`: when it changes, auto-scroll to the page of that
   *   element and pulse its bbox briefly.
   * - `selectable`: when true, clicking a bbox emits `elementFocus` so a
   *   parent can sync the selection with the graph view.
   */
  visitedBySelfRef: {
    type: Object as () => Map<string, number> | null,
    default: null,
  },
  focusedSelfRef: { type: String as () => string | null, default: null },
  selectable: { type: Boolean, default: false },
  /**
   * When true AND `visitedBySelfRef` is set, non-visited elements are drawn
   * with reduced alpha so the visited ones pop. Matches the reasoning
   * panel's "Focus" toggle behavior on the graph.
   */
  dimNonVisited: { type: Boolean, default: false },
})

const emit = defineEmits<{
  /** Fired when the user clicks a bbox — only if `selectable` is true. */
  elementFocus: [selfRef: string]
}>()

const REASONING_COLOR = '#EA580C'

const selectedPage = ref(1)
const hiddenTypes = reactive(new Set<string>())
const containerRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hoveredElement = ref<PageElement | null>(null)
const tooltipStyle = ref<Record<string, string>>({})
const imageSize = ref({ width: 0, height: 0 })

const currentPageData = computed(() => {
  return props.pages.find((p) => p.page_number === selectedPage.value)
})

const visibleElements = computed(() => {
  if (!currentPageData.value) return []
  return currentPageData.value.elements.filter((e) => !hiddenTypes.has(e.type))
})

const previewUrl = computed(() => {
  if (!props.documentId) return null
  return getPreviewUrl(props.documentId, selectedPage.value)
})

function toggleType(type: string) {
  if (hiddenTypes.has(type)) hiddenTypes.delete(type)
  else hiddenTypes.add(type)
  drawOverlay()
}

function countElements(type: string) {
  if (!currentPageData.value) return 0
  return currentPageData.value.elements.filter((e) => e.type === type).length
}

function onImageLoad() {
  const img = imageRef.value
  if (!img) return
  imageSize.value = { width: img.naturalWidth, height: img.naturalHeight }
  nextTick(drawOverlay)
}

function drawOverlay() {
  const canvas = canvasRef.value
  const img = imageRef.value
  if (!canvas || !img) return

  canvas.width = img.clientWidth
  canvas.height = img.clientHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const page = currentPageData.value
  if (!page) return

  const scale = computeScale(img.clientWidth, img.clientHeight, page.width, page.height)

  // Two-pass draw so reasoning overlays (highlight + pulse) sit on top of
  // the base element strokes without being painted over by subsequent
  // elements. First pass = base, second pass = accents.
  for (const el of visibleElements.value) {
    const rect = bboxToRect(el.bbox, scale)
    const baseColor = ELEMENT_COLORS[el.type] || ELEMENT_COLORS.text
    const isVisited =
      props.visitedBySelfRef !== null && !!el.self_ref && props.visitedBySelfRef.has(el.self_ref)

    if (isVisited) {
      // Reasoning-visited element — reasoning accent color, bolder stroke,
      // more saturated fill than the base element. The visit-order badge
      // is drawn in the second pass below.
      ctx.strokeStyle = REASONING_COLOR
      ctx.lineWidth = 3
      ctx.strokeRect(rect.x, rect.y, rect.w, rect.h)
      ctx.fillStyle = REASONING_COLOR + '33'
      ctx.fillRect(rect.x, rect.y, rect.w, rect.h)
    } else {
      // Dim non-visited when focus mode is on and a visited set is present,
      // so visited bboxes pop. Otherwise keep the regular styling.
      const dim = props.dimNonVisited && props.visitedBySelfRef !== null
      ctx.strokeStyle = baseColor + (dim ? '22' : '')
      ctx.lineWidth = dim ? 1 : 2
      ctx.strokeRect(rect.x, rect.y, rect.w, rect.h)
      ctx.fillStyle = baseColor + (dim ? '08' : '20')
      ctx.fillRect(rect.x, rect.y, rect.w, rect.h)
    }
  }

  // Second pass — numbered badges on visited elements + focus pulse ring.
  for (const el of visibleElements.value) {
    const rect = bboxToRect(el.bbox, scale)
    const order =
      props.visitedBySelfRef !== null && el.self_ref
        ? props.visitedBySelfRef.get(el.self_ref)
        : undefined
    if (order !== undefined) {
      drawVisitBadge(ctx, rect.x, rect.y, order)
    }
    if (props.focusedSelfRef && el.self_ref === props.focusedSelfRef) {
      ctx.strokeStyle = REASONING_COLOR
      ctx.lineWidth = 2
      ctx.setLineDash([6, 4])
      ctx.strokeRect(rect.x - 4, rect.y - 4, rect.w + 8, rect.h + 8)
      ctx.setLineDash([])
    }
  }
}

function drawVisitBadge(ctx: CanvasRenderingContext2D, x: number, y: number, order: number): void {
  const radius = 10
  const cx = x
  const cy = y
  ctx.fillStyle = REASONING_COLOR
  ctx.beginPath()
  ctx.arc(cx, cy, radius, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 11px -apple-system, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(String(order), cx, cy + 0.5)
}

function elementAt(e: MouseEvent): PageElement | null {
  const canvas = canvasRef.value
  const page = currentPageData.value
  const img = imageRef.value
  if (!canvas || !page || !img) return null
  const canvasRect = canvas.getBoundingClientRect()
  const mx = e.clientX - canvasRect.left
  const my = e.clientY - canvasRect.top
  const scale = computeScale(img.clientWidth, img.clientHeight, page.width, page.height)
  for (const el of visibleElements.value) {
    if (pointInRect(mx, my, bboxToRect(el.bbox, scale))) return el
  }
  return null
}

function onMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return
  const canvasRect = canvas.getBoundingClientRect()
  const mx = e.clientX - canvasRect.left
  const my = e.clientY - canvasRect.top

  const found = elementAt(e)
  hoveredElement.value = found
  if (found) {
    tooltipStyle.value = {
      left: `${Math.min(mx + 12, canvas.width - 250)}px`,
      top: `${my + 12}px`,
    }
  }
}

function onCanvasClick(e: MouseEvent): void {
  if (!props.selectable) return
  const el = elementAt(e)
  if (el?.self_ref) emit('elementFocus', el.self_ref)
}

watch([() => props.pages, selectedPage, hiddenTypes], () => {
  nextTick(drawOverlay)
})

watch(
  () => [props.visitedBySelfRef, props.dimNonVisited],
  () => nextTick(drawOverlay),
)

// When the caller sets a focused self_ref (e.g. the user clicked a node in
// the graph), find which page that element lives on and jump to it. The
// overlay redraw will then show the dashed focus ring around its bbox.
function scrollToFocused(ref: string | null): void {
  if (!ref) {
    nextTick(drawOverlay)
    return
  }
  for (const page of props.pages) {
    if (page.elements.some((e) => e.self_ref === ref)) {
      if (selectedPage.value !== page.page_number) {
        selectedPage.value = page.page_number
        // Let <img> reload before drawing — drawOverlay runs on @load.
      } else {
        nextTick(drawOverlay)
      }
      return
    }
  }
  // Ref not on any page (e.g. a #/body node) — just redraw to clear the
  // previous focus ring.
  nextTick(drawOverlay)
}

watch(() => props.focusedSelfRef, scrollToFocused)

// Imperative entry point so callers can re-trigger a scroll on the same
// self_ref (the watch above only fires on value change). Used by the
// reasoning workspace when the user re-clicks the active iteration card.
defineExpose({ scrollToFocused })
</script>

<style scoped>
.structure-viewer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-selector {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.page-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  cursor: pointer;
  transition: all var(--transition);
}

.page-btn:hover {
  background: var(--bg-hover);
}
.page-btn.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.legend-item:hover {
  background: var(--bg-hover);
}
.legend-item.dimmed {
  opacity: 0.4;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-count {
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.canvas-container {
  position: relative;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.page-image {
  width: 100%;
  display: block;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: auto;
}

.overlay-canvas.selectable {
  cursor: pointer;
}

.tooltip {
  position: absolute;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  max-width: 250px;
  pointer-events: none;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.tooltip-type {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.tooltip-content {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  word-break: break-word;
}
</style>

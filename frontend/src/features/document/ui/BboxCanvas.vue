<template>
  <div class="bbox-canvas-wrapper" data-e2e="bbox-canvas">
    <canvas
      ref="canvasRef"
      class="bbox-canvas"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
      @click="onClick"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * Pure canvas overlay for OCR element bboxes (#264).
 *
 * Externally controlled — no embedded legend, no internal hidden-types
 * state, no tooltip. The parent (LinkedTab / PagePreviewWithOverlay) owns
 * those concerns. Re-uses `bboxScaling` for the coordinate math.
 *
 * Re-draws on: image resize, page change, hidden-types change, highlight
 * change. Draw runs inside one `requestAnimationFrame` to stay smooth on
 * pages with many elements.
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import type { PageElement } from '../../../shared/types'
import { bboxToRect, computeScale, pointInRect } from '../bboxScaling'
import { colorFor, UNKNOWN_ELEMENT_COLOR } from '../elementColors'

const props = defineProps<{
  imageEl: HTMLImageElement | null
  pageWidth: number
  pageHeight: number
  elements: readonly PageElement[]
  hiddenTypes: ReadonlySet<string>
  highlightedRefs?: ReadonlySet<string>
  showLabels?: boolean
}>()

const emit = defineEmits<{
  hoverElement: [el: PageElement | null]
  clickElement: [el: PageElement]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let rafId: number | null = null
let resizeObserver: ResizeObserver | null = null

function scheduleDraw(): void {
  if (rafId !== null) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    draw()
  })
}

function visibleElements(): PageElement[] {
  return props.elements.filter((e) => !props.hiddenTypes.has(e.type))
}

function draw(): void {
  const canvas = canvasRef.value
  const img = props.imageEl
  if (!canvas || !img) return

  // Match canvas pixel size to the image's displayed size — keeps drawing
  // crisp under CSS scaling without dealing with devicePixelRatio
  // (acceptable for this UI; bumped to DPR later if blur becomes visible).
  canvas.width = img.clientWidth
  canvas.height = img.clientHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const scale = computeScale(img.clientWidth, img.clientHeight, props.pageWidth, props.pageHeight)
  const highlighted = props.highlightedRefs ?? new Set<string>()
  const showLabels = props.showLabels ?? false

  const focusMode = highlighted.size > 0
  // Two-pass draw so the highlighted element ends up on top, fully crisp.
  for (const el of visibleElements()) {
    const rect = bboxToRect(el.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) continue
    const color = colorFor(el.type)
    const isHighlight = !!el.self_ref && highlighted.has(el.self_ref)
    if (isHighlight) continue // drawn in the second pass

    // Dim everything else when a focus target is set, so the highlight pops.
    const strokeAlpha = focusMode ? '22' : 'CC'
    const fillAlpha = focusMode ? '06' : '14'
    ctx.lineWidth = 1
    ctx.strokeStyle = color + strokeAlpha
    ctx.strokeRect(rect.x, rect.y, rect.w, rect.h)
    ctx.fillStyle = color + fillAlpha
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h)

    if (showLabels && !focusMode) {
      ctx.font = '10px -apple-system, sans-serif'
      ctx.fillStyle = color
      ctx.fillText(el.type, rect.x + 2, Math.max(10, rect.y - 2))
    }
  }

  // Second pass — focused element, drawn on top with a bold stroke and a
  // dashed halo so it pops over the dimmed neighbours.
  if (focusMode) {
    for (const el of visibleElements()) {
      if (!el.self_ref || !highlighted.has(el.self_ref)) continue
      const rect = bboxToRect(el.bbox, scale)
      if (rect.w <= 0 || rect.h <= 0) continue
      const color = colorFor(el.type)

      // Halo (dashed outline a few px outside the rect).
      ctx.setLineDash([5, 3])
      ctx.lineWidth = 1.5
      ctx.strokeStyle = color + '88'
      ctx.strokeRect(rect.x - 4, rect.y - 4, rect.w + 8, rect.h + 8)
      ctx.setLineDash([])

      // Bold stroke + saturated fill on the rect itself.
      ctx.lineWidth = 3
      ctx.strokeStyle = color
      ctx.strokeRect(rect.x, rect.y, rect.w, rect.h)
      ctx.fillStyle = color + '33'
      ctx.fillRect(rect.x, rect.y, rect.w, rect.h)

      if (showLabels) {
        ctx.font = 'bold 11px -apple-system, sans-serif'
        ctx.fillStyle = color
        ctx.fillText(el.type, rect.x + 2, Math.max(11, rect.y - 2))
      }
    }
  }
}

function elementAt(e: MouseEvent): PageElement | null {
  const canvas = canvasRef.value
  const img = props.imageEl
  if (!canvas || !img) return null
  const r = canvas.getBoundingClientRect()
  const mx = e.clientX - r.left
  const my = e.clientY - r.top
  const scale = computeScale(img.clientWidth, img.clientHeight, props.pageWidth, props.pageHeight)
  for (const el of visibleElements()) {
    if (pointInRect(mx, my, bboxToRect(el.bbox, scale))) return el
  }
  return null
}

function onMouseMove(e: MouseEvent): void {
  emit('hoverElement', elementAt(e))
}
function onMouseLeave(): void {
  emit('hoverElement', null)
}
function onClick(e: MouseEvent): void {
  const el = elementAt(e)
  if (el) emit('clickElement', el)
}

watch(
  () => [
    props.imageEl,
    props.pageWidth,
    props.pageHeight,
    props.elements,
    props.hiddenTypes,
    props.highlightedRefs,
    props.showLabels,
  ],
  scheduleDraw,
  { deep: true, immediate: true },
)

// Re-draw when the image resizes (window resize / container width change).
watch(
  () => props.imageEl,
  (img, _old, onCleanup) => {
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
    if (!img) return
    resizeObserver = new ResizeObserver(scheduleDraw)
    resizeObserver.observe(img)
    onCleanup(() => {
      resizeObserver?.disconnect()
      resizeObserver = null
    })
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (rafId !== null) cancelAnimationFrame(rafId)
  resizeObserver?.disconnect()
})

// Quieten lint about unused import (kept for color fallback semantics).
void UNKNOWN_ELEMENT_COLOR
</script>

<style scoped>
.bbox-canvas-wrapper {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bbox-canvas {
  width: 100%;
  height: 100%;
  pointer-events: auto;
  display: block;
}
</style>

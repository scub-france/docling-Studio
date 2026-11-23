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
import type { PageElement, Scale } from '../../../shared/types'
import { bboxToRect, computeScale, isPointInRect } from '@/shared/bboxScaling'
import { createCssTokenReader, type CssTokenReader } from '@/shared/cssTokens'
import { getElementColor } from '@/shared/elementColors'
import { computeBadgeRect } from './BboxCanvas.logic'

const props = defineProps<{
  imageEl: HTMLElement | null
  pageNumber: number
  pageWidth: number
  pageHeight: number
  elements: readonly PageElement[]
  hiddenTypes: ReadonlySet<string>
  highlightedRefs?: ReadonlySet<string>
  showLabels?: boolean
  readingOrderByRef?: ReadonlyMap<string, number>
  selectedRef?: string | null
  nextRef?: string | null
}>()

const emit = defineEmits<{
  hoverElement: [el: PageElement | null]
  clickElement: [el: PageElement, pageNumber: number, event: MouseEvent]
}>()

/** What every drawing step needs: the context, its canvas and the page scale. */
interface DrawFrame {
  ctx: CanvasRenderingContext2D
  canvas: HTMLCanvasElement
  scale: Scale
}

/** Theme colours of the reading-order badges. */
interface BadgeColors {
  accent: string
  success: string
  background: string
  foreground: string
  border: string
  onBright: string
}

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

function listVisibleElements(): PageElement[] {
  return props.elements.filter((e) => !props.hiddenTypes.has(e.type))
}

function draw(): void {
  const canvas = canvasRef.value
  const img = props.imageEl
  if (!canvas || !img) return

  const ctx = prepareCanvas(canvas, img)
  if (!ctx) return

  const scale = computeScale(img.clientWidth, img.clientHeight, props.pageWidth, props.pageHeight)
  const frame: DrawFrame = { ctx, canvas, scale }
  const highlighted = props.highlightedRefs ?? new Set<string>()

  drawElementBoxes(frame, highlighted)
  // Second pass so the highlighted element ends up on top, fully crisp.
  if (highlighted.size > 0) drawHighlightedBoxes(frame, highlighted)

  drawReadingOrderMarkers(frame)
}

/** Next-element marker and reading-order badges, drawn over the element boxes. */
function drawReadingOrderMarkers(frame: DrawFrame): void {
  // Theme colours come from the design tokens in app/App.vue (no literal
  // copies here), so the overlay follows the light/dark theme.
  const order = props.readingOrderByRef
  const readToken: CssTokenReader =
    props.nextRef || order?.size ? createCssTokenReader(frame.canvas) : () => ''
  const success = readToken('--success')
  if (props.nextRef) drawNextElementMarker(frame, props.nextRef, success)
  if (order?.size) {
    drawReadingOrderBadges(frame, order, {
      accent: readToken('--accent'),
      success,
      background: readToken('--bg-elevated'),
      foreground: readToken('--text'),
      border: readToken('--border-light'),
      onBright: readToken('--on-bright'),
    })
  }
}

/** Sizes the canvas to the page and clears it; null when 2D is unavailable. */
function prepareCanvas(
  canvas: HTMLCanvasElement,
  img: HTMLElement,
): CanvasRenderingContext2D | null {
  // Match canvas pixel size to the image's displayed size — keeps drawing
  // crisp under CSS scaling without dealing with devicePixelRatio
  // (acceptable for this UI; bumped to DPR later if blur becomes visible).
  canvas.width = img.clientWidth
  canvas.height = img.clientHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  return ctx
}

/** First pass: every visible box but the highlighted ones, dimmed in focus mode. */
function drawElementBoxes({ ctx, scale }: DrawFrame, highlighted: ReadonlySet<string>): void {
  const showLabels = props.showLabels ?? false
  const focusMode = highlighted.size > 0
  for (const el of listVisibleElements()) {
    const rect = bboxToRect(el.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) continue
    const color = getElementColor(el.type)
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
}

/**
 * Second pass: the focused elements, drawn on top with a bold stroke and a
 * dashed halo so they pop over the dimmed neighbours.
 */
function drawHighlightedBoxes({ ctx, scale }: DrawFrame, highlighted: ReadonlySet<string>): void {
  const showLabels = props.showLabels ?? false
  for (const el of listVisibleElements()) {
    if (!el.self_ref || !highlighted.has(el.self_ref)) continue
    const rect = bboxToRect(el.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) continue
    const color = getElementColor(el.type)

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

/** Dashed outline around the element the next reading-order click will target. */
function drawNextElementMarker({ ctx, scale }: DrawFrame, nextRef: string, color: string): void {
  for (const el of listVisibleElements()) {
    if (el.self_ref !== nextRef) continue
    const rect = bboxToRect(el.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) continue
    ctx.setLineDash([4, 3])
    ctx.lineWidth = 2
    ctx.strokeStyle = color
    ctx.strokeRect(rect.x - 2, rect.y - 2, rect.w + 4, rect.h + 4)
    ctx.setLineDash([])
  }
}

/** Numbered reading-order badge on each ordered element; selected and next stand out. */
function drawReadingOrderBadges(
  { ctx, canvas, scale }: DrawFrame,
  order: ReadonlyMap<string, number>,
  colors: BadgeColors,
): void {
  ctx.save()
  ctx.font = '600 11px "IBM Plex Mono", monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (const el of listVisibleElements()) {
    if (!el.self_ref) continue
    const number = order.get(el.self_ref)
    if (number === undefined) continue
    const rect = bboxToRect(el.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) continue
    const badge = computeBadgeRect(rect, number, canvas)
    const selected = el.self_ref === props.selectedRef
    const next = el.self_ref === props.nextRef
    ctx.fillStyle = selected ? colors.accent : next ? colors.success : colors.background
    ctx.fillRect(badge.x, badge.y, badge.w, badge.h)
    ctx.lineWidth = 1
    ctx.strokeStyle = selected ? colors.accent : next ? colors.success : colors.border
    ctx.strokeRect(badge.x, badge.y, badge.w, badge.h)
    ctx.fillStyle = selected || next ? colors.onBright : colors.foreground
    ctx.fillText(String(number), badge.x + badge.w / 2, badge.y + badge.h / 2 + 0.5)
  }
  ctx.restore()
}

function findElementAt(e: MouseEvent): PageElement | null {
  const canvas = canvasRef.value
  const img = props.imageEl
  if (!canvas || !img) return null
  const r = canvas.getBoundingClientRect()
  const mx = e.clientX - r.left
  const my = e.clientY - r.top
  const scale = computeScale(img.clientWidth, img.clientHeight, props.pageWidth, props.pageHeight)
  if (props.readingOrderByRef?.size) {
    for (const el of [...listVisibleElements()].reverse()) {
      if (!el.self_ref) continue
      const number = props.readingOrderByRef.get(el.self_ref)
      if (number === undefined) continue
      const rect = bboxToRect(el.bbox, scale)
      if (rect.w <= 0 || rect.h <= 0) continue
      if (isPointInRect(mx, my, computeBadgeRect(rect, number, canvas))) return el
    }
  }
  for (const el of listVisibleElements()) {
    if (isPointInRect(mx, my, bboxToRect(el.bbox, scale))) return el
  }
  return null
}

function onMouseMove(e: MouseEvent): void {
  emit('hoverElement', findElementAt(e))
}
function onMouseLeave(): void {
  emit('hoverElement', null)
}
function onClick(e: MouseEvent): void {
  const el = findElementAt(e)
  if (el) emit('clickElement', el, props.pageNumber, e)
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
    props.readingOrderByRef,
    props.selectedRef,
    props.nextRef,
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

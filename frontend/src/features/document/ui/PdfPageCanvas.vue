<template>
  <canvas ref="canvasRef" class="pdf-page-canvas" :aria-label="`Page ${pageNumber}`" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'

const props = defineProps<{
  document: PDFDocumentProxy | null
  pageNumber: number
}>()
const emit = defineEmits<{
  ready: [canvas: HTMLCanvasElement]
  error: []
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let renderTask: RenderTask | null = null
let resizeObserver: ResizeObserver | null = null
let generation = 0
let renderedWidth = 0

async function render(): Promise<void> {
  const canvas = canvasRef.value
  const document = props.document
  if (!canvas || !document || !canvas.clientWidth) return
  const width = canvas.clientWidth
  if (Math.abs(width - renderedWidth) < 2) return
  const current = ++generation
  const previous = renderTask
  renderTask = null
  if (previous) {
    previous.cancel()
    // PDF.js cannot render twice into the same canvas until cancellation has
    // settled, even when the first render was interrupted by a resize.
    try {
      await previous.promise
    } catch {
      // RenderingCancelledException is expected here.
    }
  }
  if (current !== generation) return
  try {
    const page = await document.getPage(props.pageNumber)
    if (current !== generation) return
    const viewport = page.getViewport({ scale: 1 })
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
    const scaled = page.getViewport({ scale: (width / viewport.width) * pixelRatio })
    canvas.width = Math.round(scaled.width)
    canvas.height = Math.round(scaled.height)
    renderTask = page.render({ canvas, viewport: scaled })
    await renderTask.promise
    if (current !== generation) return
    renderedWidth = width
    emit('ready', canvas)
  } catch (error) {
    if (current !== generation || (error as Error).name === 'RenderingCancelledException') return
    emit('error')
  }
}

watch(
  () => [props.document, props.pageNumber],
  () => {
    renderedWidth = 0
    void render()
  },
)

watch(canvasRef, (canvas) => {
  resizeObserver?.disconnect()
  if (!canvas) return
  resizeObserver = new ResizeObserver(() => void render())
  resizeObserver.observe(canvas)
  void render()
})

onBeforeUnmount(() => {
  generation += 1
  renderTask?.cancel()
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.pdf-page-canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>

<template>
  <PdfPageCanvas
    v-if="document && !failed"
    :document="document"
    :page-number="pageNumber"
    @ready="(canvas) => emit('ready', canvas, 'pdf')"
    @error="emit('error', 'pdf')"
  />
  <img
    v-else-if="failed"
    :src="getPreviewUrl(documentId, pageNumber)"
    :alt="`Page ${pageNumber}`"
    class="preview-image"
    data-e2e="preview-fallback-image"
    :fetchpriority="priority"
    decoding="async"
    @load="(event) => emit('ready', event.target as HTMLImageElement, 'image')"
    @error="emit('error', 'image')"
  />
</template>

<script setup lang="ts">
/**
 * The raster of one page inside a preview frame: the PDF.js canvas, or the
 * server-rendered PNG once the PDF could not be loaded or rendered.
 *
 * Both paths report through the same two events, tagged with the path that
 * fired them, so the owner of the frame keeps a single set of handlers.
 */
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { getPreviewUrl } from '../api'
import PdfPageCanvas from './PdfPageCanvas.vue'

/** Which of the two render paths produced an event. */
type PageRasterSource = 'pdf' | 'image'

defineProps<{
  documentId: string
  document: PDFDocumentProxy | null
  /** The PDF is unusable: draw the PNG fallback instead of the canvas. */
  failed: boolean
  pageNumber: number
  /** Fetch priority of the PNG fallback. */
  priority: 'high' | 'low'
}>()

const emit = defineEmits<{
  ready: [raster: HTMLElement, source: PageRasterSource]
  error: [source: PageRasterSource]
}>()
</script>

<style scoped>
/* Fills the reserved box exactly, so the bbox scale derived from the frame
 * maps onto the raster one-to-one. */
.preview-image {
  display: block;
  width: 100%;
  height: 100%;
}
</style>

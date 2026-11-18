<template>
  <div class="pdf-page-preview" data-e2e="pdf-page-preview">
    <PdfPageCanvas
      v-if="document && !failed"
      :key="page"
      :document="document"
      :page-number="page"
      :fill-frame="false"
      @ready="(canvas) => emit('ready', canvas)"
      @error="failed = true"
    />
    <img
      v-else-if="failed"
      :src="getPreviewUrl(documentId, page)"
      :alt="`Page ${page}`"
      class="fallback-image"
      @load="(event) => emit('ready', event.target as HTMLImageElement)"
    />
  </div>
</template>

<script setup lang="ts">
import { toRef, watch } from 'vue'
import { getPreviewUrl } from '../api'
import PdfPageCanvas from './PdfPageCanvas.vue'
import { usePdfDocument } from './usePdfDocument'

const props = defineProps<{ documentId: string; page: number }>()
const emit = defineEmits<{ ready: [element: HTMLElement | null] }>()
const { document, failed } = usePdfDocument(toRef(props, 'documentId'))

watch(
  () => [props.documentId, props.page],
  () => emit('ready', null),
  { flush: 'sync' },
)
</script>

<style scoped>
.pdf-page-preview,
.fallback-image {
  display: block;
  width: 100%;
}
.fallback-image {
  height: auto;
}
</style>

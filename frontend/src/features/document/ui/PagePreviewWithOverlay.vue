<template>
  <div class="preview-with-overlay" data-e2e="preview-with-overlay">
    <div v-if="totalPages > 1" class="page-paginator" data-e2e="page-paginator">
      <button
        v-for="p in totalPages"
        :key="p"
        class="page-pill"
        :class="{ active: p === currentPage }"
        :data-e2e="`page-pill-${p}`"
        @click="onPageChange(p)"
      >
        {{ p }}
      </button>
      <span class="page-paginator-meta">
        {{ t('linked.pageOf', { page: currentPage, total: totalPages }) }}
      </span>
    </div>
    <div class="preview-stage" ref="stageRef">
      <img
        v-if="previewUrl"
        ref="imageRef"
        :src="previewUrl"
        :alt="`Page ${currentPage}`"
        class="preview-image"
        @load="onImageLoad"
      />
      <BboxCanvas
        v-if="imageEl && currentPageData"
        :image-el="imageEl"
        :page-width="currentPageData.width"
        :page-height="currentPageData.height"
        :elements="currentPageData.elements"
        :hidden-types="hiddenTypes"
        :highlighted-refs="highlightedRefs"
        :show-labels="showLabels"
        @hover-element="(el) => emit('hoverElement', el)"
        @click-element="(el) => emit('clickElement', el)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Composite of preview image + bbox overlay canvas + paginator (#264).
 *
 * Zoom is intentionally out of scope for this first cut (open question in
 * design doc §11); the image fills the container width. Adding zoom later
 * is contained to this component.
 */
import { computed, ref } from 'vue'
import type { Page, PageElement } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { getPreviewUrl } from '../api'
import BboxCanvas from './BboxCanvas.vue'

const { t } = useI18n()

const props = defineProps<{
  documentId: string
  pages: readonly Page[]
  currentPage: number
  hiddenTypes: ReadonlySet<string>
  showLabels: boolean
  highlightedRefs?: ReadonlySet<string>
}>()

const emit = defineEmits<{
  'update:currentPage': [page: number]
  hoverElement: [el: PageElement | null]
  clickElement: [el: PageElement]
}>()

const stageRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const imageEl = ref<HTMLImageElement | null>(null)

const totalPages = computed(() => props.pages.length)

const currentPageData = computed<Page | null>(() => {
  return props.pages.find((p) => p.page_number === props.currentPage) ?? null
})

const previewUrl = computed(() => {
  if (!props.documentId) return null
  return getPreviewUrl(props.documentId, props.currentPage)
})

function onImageLoad(): void {
  imageEl.value = imageRef.value
}

function onPageChange(page: number): void {
  // Reset the image ref so BboxCanvas hides until the new image loads;
  // prevents drawing stale element coords over a different page image.
  imageEl.value = null
  emit('update:currentPage', page)
}
</script>

<style scoped>
.preview-with-overlay {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  overflow: hidden;
}

.page-paginator {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  flex-shrink: 0;
  padding: 4px 0;
}

.page-pill {
  min-width: 24px;
  padding: 2px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.page-pill:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.page-pill.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.page-paginator-meta {
  margin-left: 8px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.preview-stage {
  position: relative;
  flex: 1;
  overflow-y: auto;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: center;
}

.preview-image {
  width: 100%;
  height: auto;
  display: block;
}
</style>

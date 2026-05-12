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
        {{ t('workspace.pageOf', { page: currentPage, total: totalPages }) }}
      </span>
    </div>
    <div class="preview-stage" ref="stageRef">
      <div class="preview-frame" ref="frameRef">
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
import { computed, nextTick, ref, watch } from 'vue'
import type { Page, PageElement } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { bboxToRect, computeScale } from '../bboxScaling'
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
const frameRef = ref<HTMLDivElement | null>(null)
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
  // Center the highlighted element if one is already pending (e.g. the
  // user clicked a tree node that triggered a page change — the canvas
  // wasn't mounted yet).
  nextTick(centerHighlighted)
}

function onPageChange(page: number): void {
  // Reset the image ref so BboxCanvas hides until the new image loads;
  // prevents drawing stale element coords over a different page image.
  imageEl.value = null
  emit('update:currentPage', page)
}

/**
 * Scroll the preview stage so the first highlighted element sits at the
 * vertical and horizontal center of the viewport. No-op when no
 * highlight is set, the image is not loaded yet, or the highlight
 * doesn't resolve to an element on the current page.
 */
function centerHighlighted(): void {
  const refs = props.highlightedRefs
  const page = currentPageData.value
  const img = imageEl.value
  const stage = stageRef.value
  const frame = frameRef.value
  if (!refs || refs.size === 0 || !page || !img || !stage || !frame) return

  const target = page.elements.find((e) => !!e.self_ref && refs.has(e.self_ref))
  if (!target) return

  const scale = computeScale(img.clientWidth, img.clientHeight, page.width, page.height)
  const rect = bboxToRect(target.bbox, scale)
  if (rect.w <= 0 || rect.h <= 0) return

  // Position of the bbox center inside the stage's scrollable space.
  // The frame is centered horizontally (`margin: 0 auto`) inside the
  // stage's padding box, so we offset by the frame's position relative
  // to the stage.
  const frameLeft = frame.offsetLeft
  const frameTop = frame.offsetTop
  const cx = frameLeft + rect.x + rect.w / 2
  const cy = frameTop + rect.y + rect.h / 2

  const targetLeft = cx - stage.clientWidth / 2
  const targetTop = cy - stage.clientHeight / 2

  stage.scrollTo({
    left: Math.max(0, targetLeft),
    top: Math.max(0, targetTop),
    behavior: 'smooth',
  })
}

watch(
  () => props.highlightedRefs,
  () => {
    nextTick(centerHighlighted)
  },
  { deep: true },
)
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
  flex: 1;
  overflow: auto;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px;
  min-height: 0;
}

.preview-frame {
  position: relative;
  display: block;
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
}

.preview-image {
  display: block;
  max-width: 100%;
  height: auto;
}
</style>

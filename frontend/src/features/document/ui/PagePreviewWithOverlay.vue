<template>
  <div class="preview-with-overlay" data-e2e="preview-with-overlay">
    <div class="preview-toolbar">
      <div v-if="totalPages > 1" class="preview-mode-switch" data-e2e="preview-mode-switch">
        <button
          type="button"
          class="preview-mode-btn"
          :class="{ active: viewMode === 'page' }"
          data-e2e="preview-mode-page"
          @click="viewMode = 'page'"
        >
          {{ t('workspace.previewMode.page') }}
        </button>
        <button
          type="button"
          class="preview-mode-btn"
          :class="{ active: viewMode === 'scroll' }"
          data-e2e="preview-mode-scroll"
          @click="viewMode = 'scroll'"
        >
          {{ t('workspace.previewMode.scroll') }}
        </button>
      </div>
      <div v-if="totalPages > 1" class="page-paginator" data-e2e="page-paginator">
        <div class="page-paginator-nav">
          <button
            type="button"
            class="page-nav-btn"
            :disabled="currentPage <= 1"
            :title="t('workspace.pagePrev')"
            :aria-label="t('workspace.pagePrev')"
            data-e2e="page-prev"
            @click="onPageChange(currentPage - 1)"
          >
            ‹
          </button>
          <label class="page-input-group">
            <input
              v-model="pageInput"
              type="text"
              inputmode="numeric"
              class="page-input"
              :style="{ width: `${pageInputSize}ch` }"
              :aria-label="t('workspace.pageNumber')"
              data-e2e="page-input"
              @blur="commitPageInput"
              @keydown.enter.prevent="commitPageInput"
              @keydown.esc.prevent="resetPageInput"
            />
            <span class="page-input-separator">/</span>
            <span class="page-input-total">{{ totalPages }}</span>
          </label>
          <button
            type="button"
            class="page-nav-btn"
            :disabled="currentPage >= totalPages"
            :title="t('workspace.pageNext')"
            :aria-label="t('workspace.pageNext')"
            data-e2e="page-next"
            @click="onPageChange(currentPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </div>
        <button
          type="button"
          class="page-nav-btn"
          :disabled="currentPage <= 1"
          :title="t('workspace.pagePrev')"
          :aria-label="t('workspace.pagePrev')"
          data-e2e="page-prev"
          @click="onPageChange(currentPage - 1)"
        >
          ‹
        </button>
        <label class="page-input-group">
          <input
            v-model="pageInput"
            type="text"
            inputmode="numeric"
            class="page-input"
            :style="{ width: `${pageInputSize}ch` }"
            :aria-label="t('workspace.pageNumber')"
            data-e2e="page-input"
            @blur="commitPageInput"
            @keydown.enter.prevent="commitPageInput"
            @keydown.esc.prevent="resetPageInput"
          />
          <span class="page-input-separator">/</span>
          <span class="page-input-total">{{ totalPages }}</span>
        </label>
        <button
          type="button"
          class="page-nav-btn"
          :disabled="currentPage >= totalPages"
          :title="t('workspace.pageNext')"
          :aria-label="t('workspace.pageNext')"
          data-e2e="page-next"
          @click="onPageChange(currentPage + 1)"
        >
          ›
        </button>
      </div>
      </div>
    </div>

    <div class="preview-stage" ref="stageRef">
      <section
        v-for="page in renderedPages"
        :key="page.page_number"
        class="preview-page"
        :data-e2e="`preview-page-${page.page_number}`"
        :ref="(el) => registerPageCard(page.page_number, el as HTMLElement | null)"
      >
        <header class="preview-page-header">
          <span class="preview-page-label">Page {{ page.page_number }}</span>
          <span class="preview-page-meta">{{ Math.round(page.width) }} x {{ Math.round(page.height) }}</span>
        </header>
        <div class="preview-frame">
          <img
            :src="getPreviewUrl(documentId, page.page_number)"
            :alt="`Page ${page.page_number}`"
            class="preview-image"
            :ref="(el) => registerImage(page.page_number, el as HTMLImageElement | null)"
            @load="onImageLoad(page.page_number)"
          />
          <BboxCanvas
            v-if="loadedImages[page.page_number]"
            :image-el="loadedImages[page.page_number] ?? null"
            :page-width="page.width"
            :page-height="page.height"
            :elements="page.elements"
            :hidden-types="hiddenTypes"
            :highlighted-refs="highlightedRefs"
            :show-labels="showLabels"
            @hover-element="(el) => emit('hoverElement', el)"
            @click-element="(el) => emit('clickElement', el)"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Composite of page preview + stacked preview modes with bbox overlays (#264).
 *
 * Supports both a classic single-page view and a stacked scroll view.
 * `currentPage` remains the external selection source for side panels.
 * In scroll mode it is synchronized to the page mostly visible in the viewport.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { Page, PageElement } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { bboxToRect, computeScale } from '../bboxScaling'
import { getPreviewUrl } from '../api'
import BboxCanvas from './BboxCanvas.vue'

const { t } = useI18n()
const DEFAULT_PAGE_INPUT_SIZE = 4

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
const imageRefs = reactive<Record<number, HTMLImageElement | null>>({})
const loadedImages = reactive<Record<number, HTMLImageElement | null>>({})
const pageCardRefs = reactive<Record<number, HTMLElement | null>>({})
const visiblePage = ref<number | null>(null)
const viewMode = ref<'page' | 'scroll'>('scroll')
const pageInput = ref('1')

let pageObserver: IntersectionObserver | null = null

const totalPages = computed(() => props.pages.length)
const pageInputSize = computed(() => Math.max(DEFAULT_PAGE_INPUT_SIZE, String(totalPages.value).length))

const currentPageData = computed<Page | null>(() => {
  return props.pages.find((page) => page.page_number === props.currentPage) ?? null
})
const renderedPages = computed<Page[]>(() => {
  if (viewMode.value === 'scroll') return [...props.pages]
  return currentPageData.value ? [currentPageData.value] : []
})

function registerImage(pageNumber: number, el: HTMLImageElement | null): void {
  imageRefs[pageNumber] = el
  if (!el) loadedImages[pageNumber] = null
}

function resetPageInput(): void {
  pageInput.value = String(props.currentPage)
}

function commitPageInput(): void {
  const parsed = Number.parseInt(pageInput.value, 10)
  if (!Number.isFinite(parsed)) {
    resetPageInput()
    return
  }
  const nextPage = Math.min(totalPages.value, Math.max(1, parsed))
  pageInput.value = String(nextPage)
  if (nextPage !== props.currentPage) onPageChange(nextPage)
}

function registerPageCard(pageNumber: number, el: HTMLElement | null): void {
  pageCardRefs[pageNumber] = el
}

function onImageLoad(pageNumber: number): void {
  loadedImages[pageNumber] = imageRefs[pageNumber] ?? null
  nextTick(centerHighlighted)
}

function onPageChange(page: number): void {
  if (page < 1 || page > totalPages.value) return
  emit('update:currentPage', page)
  if (viewMode.value === 'scroll') scrollToPage(page)
}

function scrollToPage(pageNumber: number): void {
  const card = pageCardRefs[pageNumber]
  if (!card) return
  card.scrollIntoView({ block: 'start', behavior: 'smooth' })
}

function setupObserver(): void {
  if (viewMode.value !== 'scroll') {
    pageObserver?.disconnect()
    pageObserver = null
    return
  }
  pageObserver?.disconnect()
  const stage = stageRef.value
  if (!stage) return

  pageObserver = new IntersectionObserver(
    (entries) => {
      let best: { page: number; ratio: number } | null = null
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        const page = Number((entry.target as HTMLElement).dataset.pageNumber)
        if (!page || (best && entry.intersectionRatio <= best.ratio)) continue
        best = { page, ratio: entry.intersectionRatio }
      }
      if (!best || best.page === visiblePage.value) return
      visiblePage.value = best.page
      emit('update:currentPage', best.page)
    },
    {
      root: stage,
      threshold: [0.25, 0.5, 0.75],
    },
  )

  for (const page of props.pages) {
    if (viewMode.value !== 'scroll' && page.page_number !== props.currentPage) continue
    const card = pageCardRefs[page.page_number]
    if (!card) continue
    card.dataset.pageNumber = String(page.page_number)
    pageObserver.observe(card)
  }
}

/**
 * Scroll the preview stage so the first highlighted element sits near the
 * center of the viewport. No-op when no highlight is set or the target page
 * image is not loaded yet.
 */
function centerHighlighted(): void {
  const refs = props.highlightedRefs
  const stage = stageRef.value
  if (!refs || refs.size === 0 || !stage) return

  for (const page of props.pages) {
    const target = page.elements.find((element) => !!element.self_ref && refs.has(element.self_ref))
    if (!target) continue

    if (viewMode.value === 'page' && page.page_number !== props.currentPage) {
      emit('update:currentPage', page.page_number)
      return
    }

    const img = loadedImages[page.page_number]
    const card = pageCardRefs[page.page_number]
    if (!img || !card) return

    const scale = computeScale(img.clientWidth, img.clientHeight, page.width, page.height)
    const rect = bboxToRect(target.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) return

    const targetLeft = card.offsetLeft + rect.x + rect.w / 2 - stage.clientWidth / 2
    const targetTop = card.offsetTop + rect.y + rect.h / 2 - stage.clientHeight / 2

    stage.scrollTo({
      left: Math.max(0, targetLeft),
      top: Math.max(0, targetTop),
      behavior: 'smooth',
    })
    return
  }
}

watch(
  () => props.currentPage,
  (page) => {
    resetPageInput()
    if (!page || viewMode.value !== 'scroll' || page === visiblePage.value) return
    nextTick(() => scrollToPage(page))
  },
  { immediate: true },
)

watch(
  () => props.pages,
  async () => {
    await nextTick()
    setupObserver()
  },
  { deep: true },
)

watch(viewMode, async (mode) => {
  await nextTick()
  setupObserver()
  if (mode === 'scroll' && props.currentPage) scrollToPage(props.currentPage)
})

watch(
  () => props.highlightedRefs,
  () => {
    nextTick(centerHighlighted)
  },
  { deep: true },
)

onMounted(() => {
  nextTick(() => {
    setupObserver()
    if (props.currentPage) scrollToPage(props.currentPage)
  })
})

onBeforeUnmount(() => {
  pageObserver?.disconnect()
})
</script>

<style scoped>
.preview-with-overlay {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  overflow: hidden;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-mode-switch {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.preview-mode-btn {
  padding: 4px 10px;
  background: transparent;
  border: 0;
  border-radius: calc(var(--radius-sm) - 2px);
  color: var(--text-secondary);
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  cursor: pointer;
  transition: all var(--transition);
}

.preview-mode-btn:hover {
  color: var(--text);
}

.preview-mode-btn.active {
  background: var(--accent-muted);
  color: var(--accent);
}

.page-paginator {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
  padding: 4px 0;
}

.page-paginator-nav {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.page-paginator-nav--compact {
  margin-left: 0;
}

.page-input-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
}

.page-input-group:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.page-input {
  min-width: 0;
  padding: 0;
  background: transparent;
  border: 0;
  color: var(--text);
  font: inherit;
  text-align: right;
}

.page-input:focus {
  outline: none;
}

.page-input-separator,
.page-input-total {
  color: var(--text-muted);
}

.page-nav-btn {
  min-width: 24px;
  padding: 2px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  line-height: 1;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.page-nav-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--accent);
}

.page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.preview-stage {
  flex: 1;
  overflow: auto;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
  min-height: 0;
}

.preview-page {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-page + .preview-page {
  margin-top: 18px;
}

.preview-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.preview-page-label,
.preview-page-meta {
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
}

.preview-page-label {
  color: var(--text);
}

.preview-page-meta {
  color: var(--text-muted);
}

.preview-frame {
  position: relative;
  display: block;
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-surface);
}

.preview-image {
  display: block;
  max-width: 100%;
  height: auto;
}
</style>

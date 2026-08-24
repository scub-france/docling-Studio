<template>
  <div class="preview-with-overlay" data-e2e="preview-with-overlay">
    <div class="preview-toolbar">
      <div
        v-if="totalPages > 1"
        class="preview-mode-switch"
        role="group"
        :aria-label="t('workspace.previewMode.label')"
        data-e2e="preview-mode-switch"
      >
        <button
          type="button"
          class="preview-mode-btn"
          :class="{ active: viewMode === 'page' }"
          :aria-pressed="viewMode === 'page'"
          data-e2e="preview-mode-page"
          @click="viewMode = 'page'"
        >
          {{ t('workspace.previewMode.page') }}
        </button>
        <button
          type="button"
          class="preview-mode-btn"
          :class="{ active: viewMode === 'scroll' }"
          :aria-pressed="viewMode === 'scroll'"
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
              @focus="pageInputFocused = true"
              @blur="onPageInputBlur"
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
            v-if="shouldRenderPage(page.page_number)"
            :src="getPreviewUrl(documentId, page.page_number)"
            :alt="`Page ${page.page_number}`"
            class="preview-image"
            loading="lazy"
            decoding="async"
            :ref="(el) => registerImage(page.page_number, el as HTMLImageElement | null)"
            @load="onImageLoad(page.page_number)"
          />
          <BboxCanvas
            v-if="loadedImages[page.page_number]"
            :image-el="loadedImages[page.page_number] ?? null"
            :page-number="page.page_number"
            :page-width="page.width"
            :page-height="page.height"
            :elements="page.elements"
            :hidden-types="hiddenTypes"
            :highlighted-refs="highlightedRefs"
            :show-labels="showLabels"
            @hover-element="(el) => emit('hoverElement', el)"
            @click-element="onClickElement"
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
import { bboxToRect, computeScale } from '@/shared/bboxScaling'
import { getPreviewUrl } from '../api'
import BboxCanvas from './BboxCanvas.vue'
import { clampPageInput, pageInputWidthCh } from './PagePreviewWithOverlay.logic'
import { centeredScrollPosition, isRectVisible, mostVisiblePage } from '../previewScroll'

const { t } = useI18n()

const props = defineProps<{
  documentId: string
  pages: readonly Page[]
  currentPage: number
  hiddenTypes: ReadonlySet<string>
  showLabels: boolean
  highlightedRefs?: ReadonlySet<string>
  /**
   * Bumped by the document store on every `focusElement` call (#303). The
   * highlight watcher below only fires when the *set* changes, so re-selecting
   * the trace step that is already highlighted would not re-scroll without it.
   */
  focusTick?: number
}>()

const emit = defineEmits<{
  'update:currentPage': [page: number]
  hoverElement: [el: PageElement | null]
  clickElement: [el: PageElement, pageNumber: number]
}>()

const stageRef = ref<HTMLDivElement | null>(null)
const imageRefs = reactive<Record<number, HTMLImageElement | null>>({})
const loadedImages = reactive<Record<number, HTMLImageElement | null>>({})
const pageCardRefs = reactive<Record<number, HTMLElement | null>>({})
const visiblePage = ref<number | null>(null)
const renderedPageNumbers = reactive(new Set<number>())
const viewMode = ref<'page' | 'scroll'>('scroll')
const pageInput = ref('1')
const pageInputFocused = ref(false)

let pageObserver: IntersectionObserver | null = null
let renderObserver: IntersectionObserver | null = null
const visibilityRatios = new Map<number, number>()

const totalPages = computed(() => props.pages.length)
const pageInputSize = computed(() => pageInputWidthCh(totalPages.value))

let pendingClickRef: string | null = null

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
  const nextPage = clampPageInput(pageInput.value, totalPages.value)
  if (nextPage === null) {
    resetPageInput()
    return
  }
  pageInput.value = String(nextPage)
  if (nextPage !== props.currentPage) onPageChange(nextPage)
}

function onPageInputBlur(): void {
  pageInputFocused.value = false
  commitPageInput()
}

function registerPageCard(pageNumber: number, el: HTMLElement | null): void {
  pageCardRefs[pageNumber] = el
}

function onImageLoad(pageNumber: number): void {
  loadedImages[pageNumber] = imageRefs[pageNumber] ?? null
  if (highlightTarget()?.page.page_number === pageNumber) nextTick(centerHighlighted)
}

function onClickElement(el: PageElement, pageNumber: number): void {
  pendingClickRef = el.self_ref ?? null
  emit('clickElement', el, pageNumber)
}

function shouldRenderPage(pageNumber: number): boolean {
  return viewMode.value === 'page' || renderedPageNumbers.has(pageNumber)
}

function onPageChange(page: number): void {
  if (page < 1 || page > totalPages.value) return
  emit('update:currentPage', page)
  if (viewMode.value === 'scroll') scrollToPage(page)
}

function scrollToPage(pageNumber: number): void {
  const card = pageCardRefs[pageNumber]
  const stage = stageRef.value
  if (!card || !stage) return

  const cardRect = card.getBoundingClientRect()
  const stageRect = stage.getBoundingClientRect()

  // Avoid jumping if the page is already reasonably visible
  const isVisible =
    cardRect.top >= stageRect.top && cardRect.bottom <= stageRect.bottom

  if (isVisible) return
  stage.scrollTo({
    top: Math.max(0, stage.scrollTop + cardRect.top - stageRect.top),
    behavior: 'smooth',
  })
}

function setupObserver(): void {
  if (viewMode.value !== 'scroll') {
    pageObserver?.disconnect()
    renderObserver?.disconnect()
    pageObserver = null
    renderObserver = null
    renderedPageNumbers.clear()
    return
  }
  pageObserver?.disconnect()
  renderObserver?.disconnect()
  visibilityRatios.clear()
  const stage = stageRef.value
  if (!stage) return
  renderedPageNumbers.add(props.currentPage)

  pageObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const page = Number((entry.target as HTMLElement).dataset.pageNumber)
        if (!page) continue
        visibilityRatios.set(page, entry.isIntersecting ? entry.intersectionRatio : 0)
      }
      const bestPage = mostVisiblePage(visibilityRatios)
      if (!bestPage || bestPage === visiblePage.value) return
      visiblePage.value = bestPage
      emit('update:currentPage', bestPage)
    },
    {
      root: stage,
      threshold: [0, 0.25, 0.5, 0.75],
    },
  )

  renderObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const page = Number((entry.target as HTMLElement).dataset.pageNumber)
        if (page) updateRenderWindow(page, entry.isIntersecting)
      }
    },
    { root: stage, rootMargin: '100% 0px' },
  )

  for (const page of props.pages) {
    if (viewMode.value !== 'scroll' && page.page_number !== props.currentPage) continue
    const card = pageCardRefs[page.page_number]
    if (!card) continue
    card.dataset.pageNumber = String(page.page_number)
    pageObserver.observe(card)
    renderObserver.observe(card)
  }
}

function updateRenderWindow(pageNumber: number, isIntersecting: boolean): void {
  if (isIntersecting) {
    renderedPageNumbers.add(pageNumber)
    return
  }
  renderedPageNumbers.delete(pageNumber)
  loadedImages[pageNumber] = null
}

function highlightTarget(): { page: Page; element: PageElement } | null {
  const refs = props.highlightedRefs
  if (!refs?.size) return null
  const pages = viewMode.value === 'page' ? renderedPages.value : props.pages
  for (const page of pages) {
    const element = page.elements.find((el) => !!el.self_ref && refs.has(el.self_ref))
    if (element) return { page, element }
  }
  return null
}

/**
 * Scroll the preview stage so the first highlighted element sits near the
 * center of the viewport. No-op when no highlight is set or the target page
 * image is not loaded yet.
 */
function centerHighlighted(): void {
  const stage = stageRef.value
  const target = highlightTarget()
  if (!target || !stage) return

    const img = loadedImages[target.page.page_number]
    if (!img) return

    const scale = computeScale(
      img.clientWidth,
      img.clientHeight,
      target.page.width,
      target.page.height,
    )
    const rect = bboxToRect(target.element.bbox, scale)
    if (rect.w <= 0 || rect.h <= 0) return

    const imgRect = img.getBoundingClientRect()
    const stageRect = stage.getBoundingClientRect()
    const bboxLeft = imgRect.left + rect.x
    const bboxTop = imgRect.top + rect.y

    const bboxViewportRect = {
      top: bboxTop,
      right: bboxLeft + rect.w,
      bottom: bboxTop + rect.h,
      left: bboxLeft,
    }
    if (isRectVisible(bboxViewportRect, stageRect)) return

    const position = centeredScrollPosition(
      stage,
      stageRect,
      { x: bboxLeft, y: bboxTop, w: rect.w, h: rect.h },
    )

    stage.scrollTo({
      left: position.left,
      top: position.top,
      behavior: 'smooth',
    })
}

watch(
  () => props.currentPage,
  (page) => {
    if (!pageInputFocused.value) resetPageInput()
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
  () => Array.from(props.highlightedRefs ?? []).sort().join('|'),
  () => {
    const refs = props.highlightedRefs
    if (pendingClickRef && refs?.has(pendingClickRef)) {
      pendingClickRef = null
      return
    }
    pendingClickRef = null
    nextTick(centerHighlighted)
  },
)

// Re-centre on an explicit focus even when the highlighted set is unchanged —
// clicking the same citation twice must scroll back to it (#303).
watch(
  () => props.focusTick,
  () => {
    pendingClickRef = null
    nextTick(centerHighlighted)
  },
)

onMounted(() => {
  nextTick(() => {
    setupObserver()
    if (props.currentPage) scrollToPage(props.currentPage)
  })
})

onBeforeUnmount(() => {
  pageObserver?.disconnect()
  renderObserver?.disconnect()
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

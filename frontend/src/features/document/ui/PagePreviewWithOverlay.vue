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
          <span class="preview-page-meta"
            >{{ Math.round(page.width) }} x {{ Math.round(page.height) }}</span
          >
        </header>
        <div
          class="preview-frame"
          :style="frameStyle(page)"
          :ref="(el) => registerFrame(page.page_number, el as HTMLElement | null)"
        >
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
import { getPreviewUrl, PREVIEW_DPI } from '../api'
import BboxCanvas from './BboxCanvas.vue'
import { clampPageInput, pageInputWidthCh } from './PagePreviewWithOverlay.logic'
import {
  centeredScrollPosition,
  isFocusScrollRequest,
  isRectVisible,
  mostVisiblePage,
  pageFrameGeometry,
  pageTopScrollPosition,
} from '../previewScroll'

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
// The frame is the page's *reserved* box (#336): unlike the image it exists
// and measures correctly whether or not the raster has been mounted, so it is
// what the focus scroll uses to place a bbox.
const frameRefs = reactive<Record<number, HTMLElement | null>>({})
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

/**
 * One scroll per user action (#336).
 *
 * A focus (`focusElement`) rewrites `highlightedRefs`, bumps `focusTick` and
 * flips `currentPage` — three props landing in the same flush, each with its
 * own watcher below. They all funnel into `requestScroll`, which coalesces
 * them into a single `scrollTo` on the next tick, once the props have settled.
 * `focus` outranks `page` because the bbox target is strictly more precise
 * than the page top, and a focus changes the page only as a side effect.
 */
type ScrollIntent = 'focus' | 'page'
let pendingIntent: ScrollIntent | null = null
let scrollScheduled = false

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

function registerFrame(pageNumber: number, el: HTMLElement | null): void {
  frameRefs[pageNumber] = el
}

/** Inline geometry that makes a card hold its height with no image mounted. */
function frameStyle(page: Page): Record<string, string> {
  return pageFrameGeometry(page, PREVIEW_DPI) ?? {}
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
  // With the box reserved, decoding shifts no layout and the focus scroll has
  // already run against the final geometry. Only a page we could *not* reserve
  // (degenerate dimensions) still grows on load and needs a second pass.
  const page = props.pages.find((p) => p.page_number === pageNumber)
  if (!page || pageFrameGeometry(page, PREVIEW_DPI)) return
  if (highlightTarget()?.page.page_number === pageNumber) requestScroll('focus')
}

function onClickElement(el: PageElement, pageNumber: number): void {
  // No re-scroll guard needed: a bbox the user just clicked is on screen, and
  // `centerHighlighted` leaves an already-visible target alone.
  emit('clickElement', el, pageNumber)
}

function shouldRenderPage(pageNumber: number): boolean {
  return (
    viewMode.value === 'page' ||
    renderedPageNumbers.has(pageNumber) ||
    pageNumber === focusedPage.value
  )
}

function onPageChange(page: number): void {
  if (page < 1 || page > totalPages.value) return
  emit('update:currentPage', page)
  requestScroll('page')
}

/**
 * Queue the one scroll this flush is allowed. See the `ScrollIntent` note
 * above: several watchers fire for a single user action, and running each of
 * their `scrollTo` calls in turn made them read stale rects from one another's
 * in-flight smooth scroll.
 */
function requestScroll(intent: ScrollIntent): void {
  // A cleared focus leaves the reader where they are (#338) — dropped here
  // rather than in `runPendingScroll`, so a page change in the same flush
  // still gets its scroll.
  if (intent === 'focus' && !isFocusScrollRequest(props.highlightedRefs)) return
  if (intent === 'focus' || pendingIntent === null) pendingIntent = intent
  if (scrollScheduled) return
  scrollScheduled = true
  void nextTick(runPendingScroll)
}

function runPendingScroll(): void {
  const intent = pendingIntent
  pendingIntent = null
  scrollScheduled = false
  if (!intent) return
  // A focus falls back to the page top when the element's geometry cannot be
  // resolved — an unknown ref, or a page we could not reserve a box for.
  if (intent === 'focus' && centerHighlighted()) return
  // Page-top scrolling belongs to the stacked view only; single-page mode
  // renders just the current page, so there is nothing to scroll *to*.
  if (viewMode.value !== 'scroll') return
  scrollToPage(props.currentPage)
}

function scrollToPage(pageNumber: number): void {
  const card = pageCardRefs[pageNumber]
  const stage = stageRef.value
  if (!card || !stage) return

  const cardRect = card.getBoundingClientRect()
  const stageRect = stage.getBoundingClientRect()

  // Avoid jumping if the page is already reasonably visible
  const isVisible = cardRect.top >= stageRect.top && cardRect.bottom <= stageRect.bottom

  if (isVisible) return
  stage.scrollTo({
    top: pageTopScrollPosition(stage.scrollTop, stageRect.top, cardRect.top),
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
  // Hold on to the raster of the page carrying the highlight (#336): the focus
  // scroll may still be travelling towards it, and dropping it mid-flight would
  // take the bbox overlay down with it. `shouldRenderPage` keeps the `<img>`
  // mounted for exactly as long, so the page is released — image and overlay
  // together — as soon as the focus moves on.
  if (pageNumber !== focusedPage.value) loadedImages[pageNumber] = null
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

/** Page the highlight sits on — the one page the render window may not evict. */
const focusedPage = computed<number | null>(() => highlightTarget()?.page.page_number ?? null)

/**
 * Scroll the preview stage so the first highlighted element sits near the
 * center of the viewport.
 *
 * Measures the page *frame*, not the image (#336): the frame carries the
 * reserved box, so it is positioned and sized correctly even for a page whose
 * raster has not been mounted — which is exactly the case when the focus lands
 * on a page far outside the render window.
 *
 * Returns `false` when the target's geometry cannot be resolved, so the caller
 * can fall back to scrolling to the page top.
 */
function centerHighlighted(): boolean {
  const stage = stageRef.value
  const target = highlightTarget()
  if (!target || !stage) return false

  const frame = frameRefs[target.page.page_number]
  if (!frame || !frame.clientWidth || !frame.clientHeight) return false

  const scale = computeScale(
    frame.clientWidth,
    frame.clientHeight,
    target.page.width,
    target.page.height,
  )
  const rect = bboxToRect(target.element.bbox, scale)
  if (rect.w <= 0 || rect.h <= 0) return false

  // `getBoundingClientRect` measures the border box; `clientLeft`/`clientTop`
  // are the border widths, so adding them lands on the raster's own origin.
  const frameRect = frame.getBoundingClientRect()
  const stageRect = stage.getBoundingClientRect()
  const bboxLeft = frameRect.left + frame.clientLeft + rect.x
  const bboxTop = frameRect.top + frame.clientTop + rect.y

  const bboxViewportRect = {
    top: bboxTop,
    right: bboxLeft + rect.w,
    bottom: bboxTop + rect.h,
    left: bboxLeft,
  }
  if (isRectVisible(bboxViewportRect, stageRect)) return true

  const position = centeredScrollPosition(stage, stageRect, {
    x: bboxLeft,
    y: bboxTop,
    w: rect.w,
    h: rect.h,
  })

  stage.scrollTo({
    left: position.left,
    top: position.top,
    behavior: 'smooth',
  })
  return true
}

watch(
  () => props.currentPage,
  (page) => {
    if (!pageInputFocused.value) resetPageInput()
    // `page === visiblePage` is the observer's own echo coming back through
    // the parent: the page changed *because* we scrolled there, so re-scrolling
    // would fight the animation still in flight.
    if (!page || page === visiblePage.value) return
    requestScroll('page')
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

watch(viewMode, async () => {
  await nextTick()
  setupObserver()
  if (props.currentPage) requestScroll('page')
})

watch(
  () =>
    Array.from(props.highlightedRefs ?? [])
      .sort()
      .join('|'),
  () => requestScroll('focus'),
)

// Re-centre on an explicit focus even when the highlighted set is unchanged —
// clicking the same citation twice must scroll back to it (#303).
watch(
  () => props.focusTick,
  () => requestScroll('focus'),
)

onMounted(() => {
  void nextTick(() => {
    setupObserver()
    if (props.currentPage) requestScroll('page')
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

/* Sized from the page's own dimensions via the inline `aspect-ratio` /
 * `max-width` set by `frameStyle` (#336) — the box is therefore correct before
 * the raster mounts, and stays put when it is evicted. `max-width` reproduces
 * the raster's natural width, so a page narrower than the column is not
 * upscaled; `width: 100%` is what the old `fit-content` resolved to for every
 * page wider than it. */
.preview-frame {
  position: relative;
  display: block;
  width: 100%;
  margin: 0 auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-surface);
}

/* Fills the reserved box exactly, so the bbox scale derived from the frame
 * maps onto the raster one-to-one. */
.preview-image {
  display: block;
  width: 100%;
  height: 100%;
}
</style>

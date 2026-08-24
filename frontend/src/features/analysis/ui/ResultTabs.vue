<template>
  <div
    class="result-tabs"
    data-e2e="result-tabs"
    v-if="store.currentAnalysis?.status === 'COMPLETED'"
  >
    <div class="tabs-header" data-e2e="tabs-header">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        data-e2e="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Page chip -->
    <div class="page-indicator" data-e2e="page-indicator" v-if="totalPages > 0">
      <span class="page-chip">{{
        t('results.pageOf', { current: currentPage, total: totalPages })
      }}</span>
    </div>

    <div class="tab-content">
      <!-- ELEMENTS VIEW — each bbox as a separate card -->
      <div v-if="activeTab === 'elements'" class="elements-list" data-e2e="elements-list">
        <div v-if="!currentElements.length" class="elements-empty">
          {{ t('results.noElements') }}
        </div>
        <div
          v-for="(el, idx) in currentElements"
          :key="idx"
          class="element-card"
          data-e2e="element-card"
          :class="{ highlighted: highlightedIndex === idx }"
          @mouseenter="$emit('highlight-element', idx)"
          @mouseleave="$emit('highlight-element', -1)"
        >
          <div class="element-header">
            <span
              class="element-type"
              :style="{ color: ELEMENT_COLORS[el.type] || ELEMENT_COLORS.text }"
            >
              {{ el.type }}
            </span>
            <span class="element-level" v-if="el.level">L{{ el.level }}</span>
            <button
              v-if="el.content"
              class="copy-btn copy-btn-element"
              :title="t('results.copy')"
              @click.stop="copyElement(idx, el.content)"
            >
              <svg
                v-if="!copiedElements[idx]"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="copy-icon"
              >
                <path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z" />
                <path
                  d="M3 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L10.414 13H15v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5zM15 11h2a1 1 0 110 2h-2v-2z"
                />
              </svg>
              <svg v-else viewBox="0 0 20 20" fill="currentColor" class="copy-icon copied">
                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
          <div class="element-content" v-if="el.content">
            <MarkdownViewer v-if="el.type === 'table'" :content="el.content" />
            <pre v-else-if="el.type === 'code'" class="element-code">{{ el.content }}</pre>
            <span v-else>{{ el.content }}</span>
          </div>
          <div class="element-bbox">
            {{ el.bbox.map((v) => Math.round(v)).join(', ') }}
          </div>
        </div>
      </div>

      <!-- RAW MARKDOWN -->
      <div v-else-if="activeTab === 'markdown'" class="raw-markdown" data-e2e="raw-markdown">
        <button class="copy-btn copy-btn-block" :title="t('results.copy')" @click="copyMarkdown">
          <svg v-if="!copiedMarkdown" viewBox="0 0 20 20" fill="currentColor" class="copy-icon">
            <path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z" />
            <path
              d="M3 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L10.414 13H15v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5zM15 11h2a1 1 0 110 2h-2v-2z"
            />
          </svg>
          <svg v-else viewBox="0 0 20 20" fill="currentColor" class="copy-icon copied">
            <path
              fill-rule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
        <pre class="raw-content" data-e2e="raw-content">{{ pageMarkdown }}</pre>
      </div>

      <!-- IMAGES -->
      <ImageGallery v-else-if="activeTab === 'images'" :pages="currentPageAsArray" />
    </div>
  </div>
  <div v-else-if="store.currentAnalysis?.status === 'RUNNING'" class="result-placeholder">
    <!-- Batch progress: segmented bar -->
    <div
      v-if="store.currentAnalysis.progressTotal && store.currentAnalysis.progressTotal > 0"
      class="batch-progress"
    >
      <div class="batch-progress-ring">
        <svg viewBox="0 0 48 48" class="progress-ring-svg">
          <circle cx="24" cy="24" r="20" fill="none" stroke="var(--border)" stroke-width="3" />
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke="var(--accent)"
            stroke-width="3"
            stroke-linecap="round"
            :stroke-dasharray="125.66"
            :stroke-dashoffset="125.66 - (125.66 * progressPercent) / 100"
            class="progress-ring-fill"
          />
        </svg>
        <span class="progress-ring-label">{{ progressPercent }}%</span>
      </div>
      <div class="batch-progress-detail">
        <span class="batch-progress-title">{{ t('studio.analysisRunning') }}</span>
        <div class="batch-segments">
          <div
            v-for="i in batchSegments"
            :key="i"
            class="batch-segment"
            :class="{
              filled: i <= filledSegments,
              active: i === filledSegments + 1,
            }"
          />
        </div>
        <span class="batch-progress-sub">
          <span class="batch-progress-pages">{{ store.currentAnalysis.progressCurrent ?? 0 }}</span>
          <span class="batch-progress-sep">/</span>
          <span>{{ store.currentAnalysis.progressTotal }} pages</span>
        </span>
      </div>
    </div>
    <!-- Fallback: no batch info -->
    <template v-else>
      <div class="spinner-large" />
      <span>{{ t('studio.analysisRunning') }}</span>
    </template>
  </div>
  <div
    v-else-if="store.currentAnalysis?.status === 'FAILED'"
    class="result-placeholder error"
    data-e2e="result-error"
  >
    <svg viewBox="0 0 20 20" fill="currentColor" class="error-icon">
      <path
        fill-rule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
        clip-rule="evenodd"
      />
    </svg>
    <span>{{ store.currentAnalysis.errorMessage || t('results.analysisFailed') }}</span>
  </div>
  <div v-else class="result-placeholder">
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      class="empty-icon"
    >
      <path
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
      />
    </svg>
    <span>{{ t('results.runAnalysis') }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useAnalysisStore } from '../store'
import MarkdownViewer from '@/shared/ui/MarkdownViewer.vue'
import ImageGallery from './ImageGallery.vue'
import { useI18n } from '../../../shared/i18n'
import type { PageElement } from '../../../shared/types'
import { ELEMENT_COLORS } from '@/shared/elementColors'

const props = defineProps({
  currentPage: { type: Number, default: 1 },
  highlightedIndex: { type: Number, default: -1 },
})

defineEmits(['highlight-element'])

const store = useAnalysisStore()
const { t } = useI18n()
const activeTab = ref('elements')

const tabs = computed(() => [
  { id: 'elements', label: t('results.elements') },
  { id: 'markdown', label: t('results.markdown') },
  { id: 'images', label: t('results.images') },
])

const totalPages = computed(() => store.currentPages.length)

const progressPercent = computed(() => {
  const a = store.currentAnalysis
  if (!a?.progressTotal || a.progressTotal <= 0) return 0
  return Math.min(100, Math.round(((a.progressCurrent ?? 0) / a.progressTotal) * 100))
})

/** Number of batch segments to render in the segmented progress bar. */
const batchSegments = computed(() => {
  const a = store.currentAnalysis
  if (!a?.progressTotal || a.progressTotal <= 0) return 0
  // Each segment = batch_page_size pages. We infer count from total & current.
  // Backend updates progressCurrent in increments, so we derive segment count.
  const current = a.progressCurrent ?? 0
  if (current <= 0) return 0
  // Guess batch size from the first non-zero progressCurrent value.
  // Fallback: assume ~5 segments for a clean visual.
  const total = a.progressTotal
  // We can't know batch_page_size on frontend, so compute a clean segment count
  // by aiming for 3-8 segments (visually optimal).
  let count = Math.round(total / Math.max(1, current || total / 5))
  if (count < 2) count = Math.ceil(total / Math.ceil(total / 5))
  return Math.max(2, Math.min(8, count))
})

/** How many segments are "filled" (completed batches). */
const filledSegments = computed(() => {
  const total = batchSegments.value
  if (total <= 0) return 0
  return Math.round((progressPercent.value / 100) * total)
})

const currentPageData = computed(() => {
  return store.currentPages.find((p) => p.page_number === props.currentPage) || null
})

const currentElements = computed(() => {
  return (currentPageData.value?.elements || []).filter((el) => el.content)
})

const currentPageAsArray = computed(() => {
  return currentPageData.value ? [currentPageData.value] : []
})

/** Build raw markdown content from page elements */
const pageMarkdown = computed(() => {
  const page = currentPageData.value
  if (!page) return ''

  return (page.elements || [])
    .map((el) => formatElement(el))
    .filter(Boolean)
    .join('\n\n')
})

function formatElement(el: PageElement) {
  if (!el.content) return ''
  const indent = '  '.repeat(Math.max(0, (el.level || 0) - 1))
  switch (el.type) {
    case 'title':
      return `# ${el.content}`
    case 'section_header': {
      const depth = Math.min(Math.max(el.level || 2, 2), 4)
      return `${'#'.repeat(depth)} ${el.content}`
    }
    case 'caption':
      return `${indent}*${el.content}*`
    case 'table':
      return el.content
    case 'formula':
      return `${indent}$$${el.content}$$`
    case 'code':
      return `${indent}\`\`\`\n${el.content}\n\`\`\``
    case 'list':
      return `${indent}- ${el.content}`
    default:
      return `${indent}${el.content}`
  }
}

// --- Copy to clipboard ---
const copiedMarkdown = ref(false)
const copiedElements: Record<number, boolean> = reactive({})

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(pageMarkdown.value)
    copiedMarkdown.value = true
    setTimeout(() => {
      copiedMarkdown.value = false
    }, 1500)
  } catch {
    /* clipboard not available */
  }
}

async function copyElement(idx: number, content: string) {
  try {
    await navigator.clipboard.writeText(content)
    copiedElements[idx] = true
    setTimeout(() => {
      copiedElements[idx] = false
    }, 1500)
  } catch {
    /* clipboard not available */
  }
}
</script>

<style scoped>
.result-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.tabs-header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  flex-shrink: 0;
  background: var(--bg);
}

.tab-btn {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.tab-btn:hover {
  color: var(--text-secondary);
}
.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.page-indicator {
  padding: 8px 16px;
  flex-shrink: 0;
}

.page-chip {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-muted);
  padding: 3px 10px;
  border-radius: 10px;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

/* --- Elements list --- */
.elements-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.elements-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
  font-size: 14px;
}

.element-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all var(--transition);
  cursor: default;
}

.element-card:hover {
  border-color: var(--border-light);
  background: var(--bg-elevated);
}

.element-card.highlighted {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.element-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.element-type {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.element-level {
  font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 1px 5px;
  border-radius: 3px;
}

.element-content {
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.element-code {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
  margin: 0;
  overflow-x: auto;
}

.element-bbox {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
}

/* --- Copy button --- */
.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition);
  padding: 4px;
}

.copy-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-muted);
}

.copy-icon {
  width: 14px;
  height: 14px;
}
.copy-icon.copied {
  color: var(--success);
}

.copy-btn-element {
  margin-left: auto;
  opacity: 0;
  transition: opacity var(--transition);
}

.element-card:hover .copy-btn-element {
  opacity: 1;
}

.copy-btn-block {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  background: var(--bg-surface);
  opacity: 0;
  transition: opacity var(--transition);
}

.raw-markdown:hover .copy-btn-block {
  opacity: 1;
}

/* --- Raw markdown --- */
.raw-markdown {
  height: 100%;
  position: relative;
}

.raw-content {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* --- Placeholders --- */
.result-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.result-placeholder.error {
  color: var(--error);
}
.error-icon {
  width: 32px;
  height: 32px;
}
.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--border-light);
}

.spinner-large {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Batch progress: ring + segmented bar ── */
.batch-progress {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Circular ring */
.batch-progress-ring {
  position: relative;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
}
.progress-ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.progress-ring-fill {
  transition: stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 0 4px rgba(249, 115, 22, 0.4));
}
.progress-ring-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text);
}

/* Right side: text + segments */
.batch-progress-detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.batch-progress-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

/* Segmented bar */
.batch-segments {
  display: flex;
  gap: 3px;
}
.batch-segment {
  width: 28px;
  height: 5px;
  border-radius: 2.5px;
  background: var(--border);
  transition:
    background 0.4s ease,
    box-shadow 0.4s ease;
}
.batch-segment.filled {
  background: var(--accent);
  box-shadow: 0 0 6px rgba(249, 115, 22, 0.3);
}
.batch-segment.active {
  background: var(--accent-muted);
  animation: segment-pulse 1.5s ease-in-out infinite;
}
@keyframes segment-pulse {
  0%,
  100% {
    background: var(--accent-muted);
  }
  50% {
    background: var(--accent);
    box-shadow: 0 0 8px rgba(249, 115, 22, 0.35);
  }
}

/* Page counter */
.batch-progress-sub {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
}
.batch-progress-pages {
  color: var(--accent);
  font-weight: 600;
}
.batch-progress-sep {
  margin: 0 2px;
  opacity: 0.4;
}
</style>

<template>
  <!-- STATE 1: No document selected — Import view -->
  <div v-if="!selectedDoc" class="import-page">
    <div class="import-center">
      <img src="/logo.png" alt="Docling Studio" class="import-logo-img" />
      <h1 class="import-title">{{ t('studio.title') }}</h1>
      <p class="import-subtitle">{{ t('studio.subtitle') }}</p>
      <DocumentUpload />
      <div class="import-docs" v-if="documentStore.documents.length">
        <label class="section-label">{{ t('studio.recentDocs') }}</label>
        <DocumentList />
      </div>
    </div>
  </div>

  <!-- STATE 2 & 3: Document selected — Configurer / V&eacute;rifier -->
  <div v-else class="studio-page">
    <!-- Top bar -->
    <div class="studio-topbar">
      <div class="topbar-left">
        <h1 class="topbar-title">{{ t('studio.title') }}</h1>
        <div class="mode-toggle">
          <button
            class="toggle-btn"
            data-e2e="toggle-btn configure-btn"
            :class="{ active: mode === 'configure' }"
            @click="mode = 'configure'"
          >
            <svg class="toggle-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clip-rule="evenodd"
              />
            </svg>
            {{ t('studio.configure') }}
          </button>
          <button
            class="toggle-btn"
            data-e2e="toggle-btn verify-btn"
            :class="{ active: mode === 'verify' }"
            @click="mode = 'verify'"
            :disabled="!analysisStore.currentAnalysis"
          >
            <svg class="toggle-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clip-rule="evenodd"
              />
            </svg>
            {{ t('studio.verify') }}
          </button>
          <button
            v-if="chunkingEnabled"
            class="toggle-btn"
            data-e2e="toggle-btn prepare-btn"
            :class="{ active: mode === 'prepare' }"
            @click="mode = 'prepare'"
            :disabled="!analysisStore.currentAnalysis"
          >
            <svg class="toggle-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
            {{ t('studio.prepare') }}
          </button>
          <button
            v-if="chunkingEnabled && ingestionEnabled && ingestionStore.available"
            class="toggle-btn"
            data-e2e="toggle-btn"
            :class="{ active: mode === 'ingest' }"
            @click="mode = 'ingest'"
            :disabled="!canIngest"
            :title="!canIngest ? t('ingestion.unavailable') : ''"
          >
            <svg class="toggle-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
                clip-rule="evenodd"
              />
            </svg>
            {{ t('studio.ingest') }}
          </button>
          <button
            v-if="chunkingEnabled && ingestionEnabled && ingestionStore.available"
            class="toggle-btn"
            data-e2e="toggle-btn maintain-btn"
            :class="{ active: mode === 'maintain' }"
            @click="mode = 'maintain'"
            :disabled="!analysisStore.currentAnalysis"
          >
            <svg class="toggle-icon" viewBox="0 0 20 20" fill="currentColor">
              <path
                d="M10 3.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM6 10a4 4 0 118 0 4 4 0 01-8 0zm4-2a2 2 0 100 4 2 2 0 000-4z"
              />
              <path
                d="M10 1v2M10 17v2M1 10h2M17 10h2M3.5 3.5l1.4 1.4M15.1 15.1l1.4 1.4M3.5 16.5l1.4-1.4M15.1 4.9l1.4-1.4"
                stroke="currentColor"
                stroke-width="1.5"
                fill="none"
              />
            </svg>
            {{ t('studio.maintain') }}
          </button>
        </div>
      </div>
      <div class="topbar-actions">
        <button class="topbar-btn" @click="addMore">
          <svg viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
            <path
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
            />
          </svg>
          {{ t('studio.addFiles') }}
        </button>
        <button
          class="topbar-btn primary"
          data-e2e="run-btn"
          :disabled="analysisStore.running"
          @click="runAnalysis"
          v-if="mode === 'configure'"
        >
          <div v-if="analysisStore.running" class="spinner-sm" />
          <svg v-else viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
              clip-rule="evenodd"
            />
          </svg>
          {{ analysisStore.running ? t('studio.analyzing') : t('studio.run') }}
        </button>
      </div>
    </div>

    <!-- Document info bar -->
    <div class="doc-infobar">
      <div class="doc-info-left">
        <svg class="doc-icon" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="doc-filename">{{ selectedDoc.filename }}</span>
        <span class="doc-status-chip loaded">{{ t('studio.loaded') }}</span>
      </div>
      <div class="doc-info-right" v-if="analysisStore.currentAnalysis">
        <span class="info-badge" v-if="analysisStore.currentAnalysis.status === 'COMPLETED'">
          <span class="info-dot success" />
          {{ selectedDoc.pageCount || '?' }} pages
        </span>
        <span class="info-badge" v-if="analysisStore.currentAnalysis.status === 'RUNNING'">
          <div class="spinner-xs" />
          {{ t('studio.analysisRunning') }}
          <span
            v-if="
              analysisStore.currentAnalysis.progressTotal &&
              analysisStore.currentAnalysis.progressTotal > 0
            "
            class="info-badge-progress"
          >
            <span class="info-badge-bar">
              <span
                class="info-badge-fill"
                :style="{
                  width:
                    Math.min(
                      100,
                      Math.round(
                        ((analysisStore.currentAnalysis.progressCurrent ?? 0) /
                          analysisStore.currentAnalysis.progressTotal) *
                          100,
                      ),
                    ) + '%',
                }"
              />
            </span>
            <span class="info-badge-count"
              >{{ analysisStore.currentAnalysis.progressCurrent ?? 0 }}/{{
                analysisStore.currentAnalysis.progressTotal
              }}</span
            >
          </span>
        </span>
        <span class="info-badge error" v-if="analysisStore.currentAnalysis.status === 'FAILED'">
          <span class="info-dot error" />
          {{ t('studio.failed') }}
        </span>
      </div>
    </div>

    <!-- Main content area -->
    <div class="studio-main">
      <!-- Left: PDF Viewer -->
      <div class="pdf-viewer-panel">
        <div class="pdf-nav-bar">
          <button class="pdf-nav-btn" :disabled="currentPage <= 1" @click="currentPage--">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
          <div class="pdf-page-input-wrap">
            <input
              type="number"
              class="pdf-page-input"
              :value="currentPage"
              @change="onPageInput"
              min="1"
              :max="selectedDoc.pageCount || 1"
            />
          </div>
          <span class="pdf-page-total">/ {{ selectedDoc.pageCount || '?' }}</span>
          <button
            class="pdf-nav-btn"
            :disabled="!selectedDoc.pageCount || currentPage >= selectedDoc.pageCount"
            @click="currentPage++"
          >
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
          <span class="pdf-separator" />
          <span class="pdf-zoom">100%</span>
          <template v-if="hasAnalysisResults">
            <span class="pdf-separator" />
            <button
              class="visual-toggle"
              :class="{ active: visualMode }"
              @click="visualMode = !visualMode"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
                <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                <path
                  fill-rule="evenodd"
                  d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                  clip-rule="evenodd"
                />
              </svg>
              {{ t('studio.visual') }}
            </button>
          </template>
        </div>
        <div class="pdf-image-area">
          <div class="pdf-image-wrapper">
            <img
              v-if="previewUrl"
              ref="pdfImageRef"
              :src="previewUrl"
              :alt="`Page ${currentPage}`"
              class="pdf-image"
              data-e2e="pdf-image"
              @load="onPdfImageLoad"
            />
            <BboxOverlay
              v-if="(visualMode || mode === 'prepare') && hasAnalysisResults"
              ref="bboxOverlayRef"
              :image-el="pdfImageRef"
              :page-data="currentPageData"
              :highlighted-index="highlightedElementIndex"
              :highlighted-bboxes="highlightedChunkBboxes"
              @highlight-element="highlightedElementIndex = $event"
            />
          </div>
        </div>
      </div>

      <!-- Resize handle -->
      <div class="resize-handle" @mousedown="onResizeStart">
        <div class="resize-grip" />
      </div>

      <!-- Right: Config or Results panel -->
      <div class="right-panel" :style="{ width: rightPanelWidth + 'px' }">
        <!-- CONFIGURER MODE -->
        <div v-if="mode === 'configure'" class="config-panel" data-e2e="config-panel">
          <div class="config-section">
            <label class="config-label">
              {{ t('config.model') }}
            </label>
            <div class="config-select-display">
              <span class="config-model-name">Docling</span>
              <span class="config-model-sub">docling-latest</span>
            </div>
          </div>

          <!-- Pipeline options -->
          <div class="config-section">
            <label class="config-label">{{ t('config.pipeline') }}</label>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input type="checkbox" v-model="pipelineOptions.do_ocr" class="toggle-input" />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.ocr') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.ocrHint') }}</span
                >?</span
              >
            </div>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.do_table_structure"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.tableStructure') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.tableStructureHint') }}</span
                >?</span
              >
            </div>

            <div class="config-sub-option" v-if="pipelineOptions.do_table_structure">
              <label class="config-label-sm">{{ t('config.tableMode') }}</label>
              <select
                class="config-select"
                data-e2e="config-select"
                v-model="pipelineOptions.table_mode"
              >
                <option value="accurate">{{ t('config.tableModeAccurate') }}</option>
                <option value="fast">{{ t('config.tableModeFast') }}</option>
              </select>
            </div>
          </div>

          <!-- Enrichment options -->
          <div class="config-section">
            <label class="config-label">{{ t('config.enrichment') }}</label>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.do_code_enrichment"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.codeEnrichment') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.codeEnrichmentHint') }}</span
                >?</span
              >
            </div>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.do_formula_enrichment"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.formulaEnrichment') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.formulaEnrichmentHint') }}</span
                >?</span
              >
            </div>
          </div>

          <!-- Picture options -->
          <div class="config-section">
            <label class="config-label">{{ t('config.pictures') }}</label>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.do_picture_classification"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.pictureClassification') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.pictureClassificationHint') }}</span
                >?</span
              >
            </div>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.do_picture_description"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.pictureDescription') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.pictureDescriptionHint') }}</span
                >?</span
              >
            </div>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.generate_picture_images"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.generatePictureImages') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.generatePictureImagesHint') }}</span
                >?</span
              >
            </div>

            <div class="config-toggle-row">
              <label class="toggle-label" data-e2e="toggle-label">
                <input
                  type="checkbox"
                  v-model="pipelineOptions.generate_page_images"
                  class="toggle-input"
                />
                <span class="toggle-switch" data-e2e="toggle-switch" />
                <span class="toggle-text">{{ t('config.generatePageImages') }}</span>
              </label>
              <span class="config-hint"
                ><span class="config-tooltip">{{ t('config.generatePageImagesHint') }}</span
                >?</span
              >
            </div>

            <div
              class="config-sub-option"
              v-if="pipelineOptions.generate_picture_images || pipelineOptions.generate_page_images"
            >
              <label class="config-label-sm">{{ t('config.imagesScale') }}</label>
              <select class="config-select" v-model.number="pipelineOptions.images_scale">
                <option :value="0.5">0.5x</option>
                <option :value="1.0">1.0x</option>
                <option :value="1.5">1.5x</option>
                <option :value="2.0">2.0x</option>
              </select>
            </div>
          </div>

          <!-- Documents list at bottom -->
          <div class="config-section config-docs">
            <label class="config-label">{{ t('config.documents') }}</label>
            <DocumentList />
          </div>
        </div>

        <!-- VERIFIER MODE -->
        <div v-if="mode === 'verify'" class="verify-panel">
          <ResultTabs
            :current-page="currentPage"
            :highlighted-index="highlightedElementIndex"
            @highlight-element="highlightedElementIndex = $event"
          />
        </div>

        <!-- PREPARER MODE (feature-flipped) -->
        <div v-if="mode === 'prepare' && chunkingEnabled" class="prepare-panel">
          <ChunkPanel
            :current-page="currentPage"
            :analysis-id="analysisStore.currentAnalysis?.id ?? null"
            :analysis-status="analysisStore.currentAnalysis?.status ?? null"
            :has-document-json="analysisStore.currentAnalysis?.hasDocumentJson ?? false"
            :chunks="analysisStore.currentChunks"
            @highlight-bboxes="highlightedChunkBboxes = $event"
          />
        </div>

        <!-- INGEST MODE -->
        <div v-if="mode === 'ingest'" class="ingest-panel-wrapper">
          <IngestPanel
            :analysis-id="analysisStore.currentAnalysis?.id ?? null"
            :document-name="selectedDoc?.filename ?? ''"
            :chunk-count="analysisStore.currentChunks?.length ?? 0"
          />
        </div>

        <!-- MAINTAIN MODE -->
        <div v-if="mode === 'maintain'" class="maintain-panel">
          <GraphView :doc-id="analysisStore.currentAnalysis?.documentId ?? null" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentStore } from '../features/document/store'
import { useAnalysisStore } from '../features/analysis/store'
import { useIngestionStore } from '../features/ingestion/store'
import { DocumentUpload, DocumentList } from '../features/document/index'
import { ResultTabs } from '../features/analysis/index'
import BboxOverlay from '../features/analysis/ui/BboxOverlay.vue'
import GraphView from '../features/analysis/ui/GraphView.vue'
import { ChunkPanel } from '../features/chunking'
import { IngestPanel } from '../features/ingestion'
import { useFeatureFlag } from '../features/feature-flags'
import { getPreviewUrl } from '../features/document/api'
import { useI18n } from '../shared/i18n'
import type { ChunkBbox, PipelineOptions } from '../shared/types'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()
const analysisStore = useAnalysisStore()
const ingestionStore = useIngestionStore()
const { t } = useI18n()
const chunkingEnabled = useFeatureFlag('chunking')
const ingestionEnabled = useFeatureFlag('ingestion')

const mode = ref('configure')
const currentPage = ref(1)
const visualMode = ref(false)
const highlightedElementIndex = ref(-1)
const highlightedChunkBboxes = ref<ChunkBbox[]>([])
const pdfImageRef = ref<HTMLImageElement | null>(null)
const bboxOverlayRef = ref<InstanceType<typeof BboxOverlay> | null>(null)

// --- Resizable right panel ---
const RIGHT_PANEL_MIN = 280
const RIGHT_PANEL_MAX_RATIO = 0.7
const rightPanelWidth = ref(380)
let resizing = false

function onResizeStart(e: MouseEvent) {
  e.preventDefault()
  resizing = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}

function onResizeMove(e: MouseEvent) {
  if (!resizing) return
  const maxWidth = window.innerWidth * RIGHT_PANEL_MAX_RATIO
  const newWidth = window.innerWidth - e.clientX
  rightPanelWidth.value = Math.max(RIGHT_PANEL_MIN, Math.min(newWidth, maxWidth))
}

function onResizeEnd() {
  resizing = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  // Redraw bbox overlay after resize
  nextTick(() => bboxOverlayRef.value?.draw())
}

const pipelineOptions = reactive<PipelineOptions>({
  do_ocr: true,
  do_table_structure: true,
  table_mode: 'accurate',
  do_code_enrichment: false,
  do_formula_enrichment: false,
  do_picture_classification: false,
  do_picture_description: false,
  generate_picture_images: false,
  generate_page_images: false,
  images_scale: 1.0,
})

const canIngest = computed(() => {
  return (
    ingestionStore.available &&
    analysisStore.currentAnalysis?.status === 'COMPLETED' &&
    analysisStore.currentAnalysis?.chunksJson != null
  )
})

const hasAnalysisResults = computed(() => {
  return (
    analysisStore.currentAnalysis?.status === 'COMPLETED' && analysisStore.currentPages?.length > 0
  )
})

const currentPageData = computed(() => {
  if (!analysisStore.currentPages) return null
  return analysisStore.currentPages.find((p) => p.page_number === currentPage.value) || null
})

function onPdfImageLoad() {
  nextTick(() => bboxOverlayRef.value?.draw())
}

const selectedDoc = computed(() => {
  return documentStore.documents.find((d) => d.id === documentStore.selectedId)
})

const previewUrl = computed(() => {
  if (!selectedDoc.value) return null
  return getPreviewUrl(selectedDoc.value.id, currentPage.value)
})

function onPageInput(e: Event) {
  const val = parseInt((e.target as HTMLInputElement).value)
  if (!val || val < 1) return
  const max = selectedDoc.value?.pageCount || val
  currentPage.value = Math.min(val, max)
}

async function runAnalysis() {
  if (!documentStore.selectedId) return
  await analysisStore.run(documentStore.selectedId, { ...pipelineOptions })
}

function addMore() {
  documentStore.selectedId = null
}

// Clear highlights when switching modes or pages
watch(mode, () => {
  highlightedElementIndex.value = -1
  highlightedChunkBboxes.value = []
})
watch(currentPage, () => {
  highlightedElementIndex.value = -1
  highlightedChunkBboxes.value = []
})

// Auto-switch to verify when analysis completes + refresh document data (pageCount)
watch(
  () => analysisStore.currentAnalysis?.status,
  (status) => {
    if (status === 'COMPLETED') {
      mode.value = 'verify'
      documentStore.load()
    }
  },
)

onMounted(async () => {
  await documentStore.load()
  analysisStore.load()
  if (ingestionEnabled.value) {
    ingestionStore.checkAvailability()
  }

  // Restore analysis from history via query param
  const analysisId = route.query.analysisId
  if (analysisId) {
    await analysisStore.select(analysisId as string)
    const analysis = analysisStore.currentAnalysis
    if (analysis) {
      documentStore.select(analysis.documentId)
      if (analysis.status === 'COMPLETED') {
        mode.value = 'verify'
      }
    }
    // Clean query param from URL
    router.replace({ query: {} })
  }
})

onBeforeUnmount(() => {
  analysisStore.stopPolling()
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
})
</script>

<style scoped>
/* ===== IMPORT PAGE ===== */
.import-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
}

.import-center {
  max-width: 480px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.import-logo-img {
  width: 64px;
  height: 64px;
  object-fit: contain;
  margin-bottom: 8px;
  border-radius: var(--radius);
}

.import-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  text-align: center;
}

.import-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: 8px;
}

.import-docs {
  width: 100%;
  margin-top: 16px;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

/* ===== STUDIO PAGE ===== */
.studio-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Top bar */
.studio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg-surface);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 0;
}

.topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.mode-toggle {
  display: flex;
  gap: 2px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  padding: 3px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-sm) - 2px);
  cursor: pointer;
  transition: all 200ms ease;
}

.toggle-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity 200ms ease;
}

.toggle-btn:hover:not(:disabled) {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.toggle-btn:hover:not(:disabled) .toggle-icon {
  opacity: 0.8;
}

.toggle-btn.active {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.toggle-btn.active .toggle-icon {
  opacity: 1;
}

.toggle-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.topbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.topbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.topbar-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.topbar-btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.topbar-btn.primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.topbar-btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.topbar-btn .btn-icon {
  width: 16px;
  height: 16px;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* Doc info bar */
.doc-infobar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg);
}

.doc-info-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-icon {
  width: 16px;
  height: 16px;
  color: var(--error);
}

.doc-filename {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

.doc-status-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.doc-status-chip.loaded {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.doc-info-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'IBM Plex Mono', monospace;
}

.info-badge.error {
  color: var(--error);
}

.info-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.info-dot.success {
  background: var(--success);
}
.info-dot.error {
  background: var(--error);
}

.spinner-xs {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* Inline mini progress in top bar */
.info-badge-progress {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
}
.info-badge-bar {
  width: 48px;
  height: 3px;
  background: var(--border);
  border-radius: 1.5px;
  overflow: hidden;
}
.info-badge-fill {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 1.5px;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.info-badge-count {
  font-size: 11px;
  color: var(--text-muted);
}

/* Main content */
.studio-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* PDF Viewer fills remaining space */
.pdf-viewer-panel {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Resize handle */
.resize-handle {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 5;
  transition: background var(--transition);
}

.resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2px;
  width: 1px;
  background: var(--border);
  transition: background var(--transition);
}

.resize-handle:hover::before,
.resize-handle:active::before {
  background: var(--accent);
}

.resize-handle:hover,
.resize-handle:active {
  background: var(--accent-muted);
}

.resize-grip {
  width: 3px;
  height: 24px;
  border-radius: 2px;
  background: var(--border-light);
  opacity: 0;
  transition: opacity var(--transition);
}

.resize-handle:hover .resize-grip {
  opacity: 1;
  background: var(--accent);
}

/* PDF Viewer — flex: 1 set above in .studio-main context */

.pdf-nav-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg-surface);
}

.pdf-nav-btn {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  transition: all var(--transition);
}

.pdf-nav-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text);
}
.pdf-nav-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.pdf-nav-btn svg {
  width: 16px;
  height: 16px;
}

.pdf-page-input-wrap {
  display: flex;
}

.pdf-page-input {
  width: 40px;
  text-align: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
  font-family: 'IBM Plex Mono', monospace;
  padding: 3px;
  -moz-appearance: textfield;
}

.pdf-page-input::-webkit-outer-spin-button,
.pdf-page-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.pdf-page-total {
  font-size: 13px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-right: 8px;
}

.pdf-separator {
  width: 1px;
  height: 20px;
  background: var(--border);
  margin: 0 8px;
}

.pdf-zoom {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: 'IBM Plex Mono', monospace;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 10px;
}

.visual-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all var(--transition);
}

.visual-toggle .btn-icon {
  width: 14px;
  height: 14px;
}

.visual-toggle:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.visual-toggle.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.pdf-image-area {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  background: var(--bg-elevated);
  padding: 20px;
}

.pdf-image-wrapper {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.pdf-image {
  max-width: 100%;
  height: auto;
  display: block;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.4);
  border-radius: 2px;
}

/* Right panel — width set via inline style */
.right-panel {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  flex-shrink: 0;
  min-width: 280px;
  max-width: 70vw;
  border-left: 1px solid var(--border);
}

/* Config panel */
.config-panel {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.config-hint {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid var(--border-light);
  font-size: 10px;
  color: var(--text-muted);
  cursor: help;
  flex-shrink: 0;
}

.config-hint:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.config-tooltip {
  display: none;
  position: absolute;
  bottom: calc(100% + 8px);
  right: -8px;
  width: 240px;
  padding: 8px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  pointer-events: none;
}

.config-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  right: 12px;
  border: 5px solid transparent;
  border-top-color: var(--border-light);
}

.config-hint:hover .config-tooltip {
  display: block;
}

.config-select-display {
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

.config-model-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.config-model-sub {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.config-input {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  transition: border-color var(--transition);
}

.config-input::placeholder {
  color: var(--text-muted);
}

.config-input:focus {
  outline: none;
  border-color: var(--accent);
}

.config-select {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23A1A1AA' viewBox='0 0 20 20'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.config-select:focus {
  outline: none;
  border-color: var(--accent);
}

.config-select option {
  background: var(--bg-surface);
  color: var(--text);
}

/* Toggle rows */
.config-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-switch {
  position: relative;
  width: 36px;
  height: 20px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: all var(--transition);
  flex-shrink: 0;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: all var(--transition);
}

.toggle-input:checked + .toggle-switch {
  background: var(--accent);
  border-color: var(--accent);
}

.toggle-input:checked + .toggle-switch::after {
  left: 18px;
  background: white;
}

.toggle-text {
  font-size: 13px;
  color: var(--text);
}

.config-sub-option {
  padding-left: 46px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-label-sm {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
}

.config-docs {
  margin-top: auto;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

/* Verify / Prepare / Ingest / Maintain panels */
.verify-panel,
.prepare-panel,
.ingest-panel-wrapper,
.maintain-panel {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

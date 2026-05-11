<template>
  <aside
    v-if="store.hasTrace || store.importDialogOpen"
    class="reasoning-panel"
    data-e2e="reasoning-panel"
  >
    <header class="rp-header">
      <h3>{{ t('reasoning.panelTitle') }}</h3>
      <div class="rp-header-actions">
        <button
          class="rp-btn-ghost rp-btn-toggle"
          :class="{ active: store.focusMode }"
          :aria-pressed="store.focusMode"
          data-e2e="reasoning-focus-toggle"
          :title="t('reasoning.focusHint')"
          @click="store.toggleFocusMode()"
        >
          <span class="rp-dot" />
          {{ t('reasoning.focus') }}
        </button>
        <button class="rp-btn-ghost" @click="store.openImportDialog()">
          {{ t('reasoning.reimport') }}
        </button>
        <button class="rp-btn-ghost" @click="onClear">{{ t('reasoning.clear') }}</button>
      </div>
    </header>

    <section v-if="envelope" class="rp-meta">
      <div v-if="envelope.query" class="rp-query">
        <span class="rp-meta-label">{{ t('reasoning.query') }}</span>
        <span class="rp-meta-value">{{ envelope.query }}</span>
      </div>
      <div class="rp-meta-row">
        <span v-if="envelope.filename" class="rp-meta-chip">{{ envelope.filename }}</span>
        <span v-if="envelope.model?.ollama_name" class="rp-meta-chip">
          {{ envelope.model.ollama_name }}
        </span>
      </div>
    </section>

    <section v-if="result" class="rp-answer">
      <div class="rp-answer-header">
        <span class="rp-answer-label">{{ t('reasoning.answerLabel') }}</span>
        <span class="rp-answer-actions">
          <span class="rp-converged" :class="{ yes: result.converged, no: !result.converged }">
            {{ result.converged ? t('reasoning.converged') : t('reasoning.notConverged') }}
          </span>
          <button
            class="rp-copy-btn"
            :title="t('reasoning.copyAnswer')"
            data-e2e="reasoning-copy-answer"
            @click="copyAnswer"
          >
            {{ copied ? t('reasoning.copied') : t('reasoning.copy') }}
          </button>
        </span>
      </div>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify -->
      <div class="rp-answer-body markdown-body" v-html="renderedAnswer" />
      <div class="rp-answer-footer">
        <span class="rp-stats">
          {{ store.presentCount }} / {{ store.iterations.length }} {{ t('reasoning.resolved') }}
        </span>
      </div>
    </section>

    <section v-if="store.missingCount > 0" class="rp-warn" data-e2e="reasoning-missing-warn">
      {{ missingWarning }}
    </section>

    <section class="rp-iterations">
      <h4 class="rp-section-title">{{ t('reasoning.iterationsTitle') }}</h4>
      <div v-if="store.iterations.length === 0" class="rp-empty">
        {{ t('reasoning.noIterations') }}
      </div>
      <div v-else class="rp-iteration-list">
        <IterationCard
          v-for="it in store.iterations"
          :key="it.iteration"
          :iteration="it"
          :active="store.activeIteration === it.iteration"
          @focus="(n) => emit('iterationFocus', n)"
        />
      </div>
    </section>
  </aside>

  <ImportTraceDialog />
</template>

<script setup lang="ts">
import type { Core } from 'cytoscape'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref, watch } from 'vue'

import { useI18n } from '../../../shared/i18n'
import {
  applyReasoningOverlay,
  buildDegradedOverlay,
  clearReasoningOverlay,
} from '../graphReasoningOverlay'
import { useReasoningStore } from '../store'
import IterationCard from './IterationCard.vue'
import ImportTraceDialog from './ImportTraceDialog.vue'

const props = defineProps<{
  /**
   * The live Cytoscape instance from the GraphView. May be `null` while the
   * graph is loading or if Maintain hasn't been run for this document.
   * Passed down by the host page via `graphViewRef.cy`.
   */
  cy: Core | null
}>()

// Iteration clicks bubble up to the workspace, which dispatches focus to
// both the graph and the PDF directly — keeping the panel ignorant of its
// siblings and avoiding watch-based plumbing that misfires on repeat clicks.
const emit = defineEmits<{ iterationFocus: [iteration: number] }>()

const store = useReasoningStore()
const { t } = useI18n()

const result = computed(() => store.rawResult)
const envelope = computed(() => store.envelope)

// Render the answer as markdown so numbered lists, bold, etc. render properly.
// Models tend to produce markdown-formatted answers (numbered lists especially),
// and plain-text `pre-wrap` made them near-unreadable.
const renderedAnswer = computed(() => {
  const raw = result.value?.answer ?? ''
  if (!raw.trim()) return ''
  return DOMPurify.sanitize(marked.parse(raw, { async: false }) as string)
})

const copied = ref(false)
let copyResetTimer: ReturnType<typeof setTimeout> | null = null

async function copyAnswer(): Promise<void> {
  const text = result.value?.answer
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    if (copyResetTimer) clearTimeout(copyResetTimer)
    copyResetTimer = setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch (e) {
    console.warn('Copy failed', e)
  }
}

const missingWarning = computed(() => {
  // Full miss + no cy → the graph simply isn't loaded. Different message
  // than "N sections are actually missing from the graph".
  if (!props.cy && store.missingCount > 0 && store.presentCount === 0) {
    return t('reasoning.graphNotLoadedWarn')
  }
  return t('reasoning.missingWarn').replace('{n}', String(store.missingCount))
})

function reapplyOverlay(): void {
  if (!store.rawResult) {
    if (props.cy) clearReasoningOverlay(props.cy)
    store.setOverlay(null)
    return
  }
  // When the Cytoscape instance is available (graph loaded for this doc) we
  // run the full overlay: mark visited nodes, draw REASONING_NEXT arrows.
  // Otherwise (404 on the graph endpoint, or Maintain not run yet) we still
  // build the iteration list in "degraded" mode so the user can read the
  // reasoning — they just won't see nodes highlighted.
  const out = props.cy
    ? applyReasoningOverlay(props.cy, store.rawResult, { focusMode: store.focusMode })
    : buildDegradedOverlay(store.rawResult)
  store.setOverlay(out)
}

// Reapply whenever cy, rawResult, or focusMode changes. This handles:
//  - User imports trace after graph loaded (rawResult changes).
//  - User navigates to a different doc which swaps cy (cy changes).
//  - Graph loads AFTER the trace was already imported (cy null → non-null).
//  - User toggles focus mode (focusMode changes) — dim in, dim out.
//  - User clears the trace (rawResult → null → clearReasoningOverlay).
watch(
  () => [props.cy, store.rawResult, store.focusMode] as const,
  () => reapplyOverlay(),
  { immediate: true },
)

function onClear(): void {
  if (props.cy) clearReasoningOverlay(props.cy)
  store.reset()
}
</script>

<style scoped>
.reasoning-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 340px;
  flex: 0 0 340px;
  padding: 16px;
  border-left: 1px solid var(--border);
  background: var(--bg);
  overflow-y: auto;
  height: 100%;
}

.rp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.rp-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.rp-header-actions {
  display: flex;
  gap: 4px;
}

.rp-btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  padding: 4px 8px;
  font-size: 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.rp-btn-ghost:hover {
  background: var(--border-light);
  color: var(--text);
}

.rp-btn-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.rp-btn-toggle .rp-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  transition: background var(--transition);
}

.rp-btn-toggle.active {
  border-color: #ea580c;
  color: #ea580c;
  background: rgba(234, 88, 12, 0.08);
}

.rp-btn-toggle.active .rp-dot {
  background: #ea580c;
}

.rp-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.rp-meta-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  display: block;
  margin-bottom: 2px;
}

.rp-meta-value {
  font-size: 12px;
  color: var(--text);
  line-height: 1.4;
}

.rp-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rp-meta-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--border-light);
  color: var(--text-secondary);
  font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
}

.rp-answer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: var(--bg);
  border: 1px solid #ea580c;
  border-radius: var(--radius);
  box-shadow: 0 1px 3px rgba(234, 88, 12, 0.08);
}

.rp-answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.rp-answer-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #ea580c;
}

.rp-answer-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.rp-converged {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rp-converged.yes {
  background: rgba(22, 163, 74, 0.15);
  color: #15803d;
}

.rp-converged.no {
  background: rgba(234, 179, 8, 0.15);
  color: #a16207;
}

.rp-copy-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 2px 8px;
  font-size: 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.rp-copy-btn:hover {
  background: var(--border-light);
  color: var(--text);
}

.rp-stats {
  font-size: 10px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.rp-answer-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border-light);
  padding-top: 6px;
}

/* Markdown-rendered answer body. Mirrors a subset of MarkdownViewer styles,
 * tuned for a narrow right-rail context (tighter sizes than the full viewer). */
.rp-answer-body {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text);
}

.rp-answer-body :deep(p) {
  margin: 0 0 8px;
}

.rp-answer-body :deep(p:last-child) {
  margin-bottom: 0;
}

.rp-answer-body :deep(ol),
.rp-answer-body :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 22px;
}

.rp-answer-body :deep(li) {
  margin: 2px 0;
}

.rp-answer-body :deep(strong) {
  color: var(--text);
  font-weight: 600;
}

.rp-answer-body :deep(code) {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  background: var(--border-light);
  padding: 1px 5px;
  border-radius: 3px;
}

.rp-answer-body :deep(pre) {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  background: var(--border-light);
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 6px 0;
}

.rp-answer-body :deep(h1),
.rp-answer-body :deep(h2),
.rp-answer-body :deep(h3),
.rp-answer-body :deep(h4) {
  margin: 10px 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.rp-answer-body :deep(a) {
  color: #ea580c;
  text-decoration: underline;
}

.rp-warn {
  padding: 8px 10px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: var(--radius-sm);
  color: #a16207;
  font-size: 12px;
}

.rp-section-title {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.rp-iteration-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rp-empty {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}
</style>

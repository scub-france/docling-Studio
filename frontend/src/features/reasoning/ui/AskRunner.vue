<template>
  <div class="ask-runner" data-e2e="ask-runner">
    <!-- Form -->
    <form class="ask-form" @submit.prevent="run">
      <label class="ask-label">{{ t('ask.questionLabel') }}</label>
      <textarea
        v-model="query"
        class="ask-textarea"
        :placeholder="t('ask.questionPlaceholder')"
        :disabled="running"
        rows="3"
      />
      <details class="ask-model-details">
        <summary class="ask-model-summary">{{ t('ask.modelConfig') }}</summary>
        <input
          v-model="modelId"
          class="ask-model-input"
          :placeholder="t('ask.modelPlaceholder')"
          :disabled="running"
        />
        <p class="ask-model-hint">{{ t('ask.modelHint') }}</p>
      </details>
      <button class="ask-submit" type="submit" :disabled="!query.trim() || running">
        <span v-if="running" class="ask-spinner" />
        <span>{{ running ? t('ask.running') : t('ask.run') }}</span>
      </button>
    </form>

    <!-- Error -->
    <div v-if="error" class="ask-error" data-e2e="ask-error">{{ error }}</div>

    <!-- Result -->
    <div v-if="result" class="ask-result" data-e2e="ask-result">
      <!-- Answer -->
      <div class="ask-answer">
        <div class="ask-answer-header">
          <span class="ask-answer-label">{{ t('ask.answerLabel') }}</span>
          <span class="ask-converged" :class="{ yes: result.converged, no: !result.converged }">
            {{ result.converged ? t('reasoning.converged') : t('reasoning.notConverged') }}
          </span>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify -->
        <div class="ask-answer-body" v-html="renderedAnswer" />
      </div>

      <!-- Iterations -->
      <div class="ask-iterations">
        <h4 class="ask-section-title">{{ t('reasoning.iterationsTitle') }}</h4>
        <IterationCard
          v-for="it in resolvedIterations"
          :key="it.iteration"
          :iteration="it"
          :active="activeIteration === it.iteration"
          @focus="onIterationFocus"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { runReasoning } from '../api'
import type { ReasoningResult, ReasoningIteration, ResolvedIteration } from '../types'
import IterationCard from './IterationCard.vue'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{ docId: string }>()

const emit = defineEmits<{ sectionFocus: [sectionRef: string] }>()

const { t } = useI18n()

const query = ref('')
const modelId = ref('')
const running = ref(false)
const error = ref<string | null>(null)
const result = ref<ReasoningResult | null>(null)
const activeIteration = ref<number | null>(null)

const renderedAnswer = computed(() => {
  const raw = result.value?.answer ?? ''
  if (!raw.trim()) return ''
  return DOMPurify.sanitize(marked.parse(raw, { async: false }) as string)
})

function toResolved(it: ReasoningIteration): ResolvedIteration {
  return {
    iteration: it.iteration,
    sectionRef: it.section_ref,
    nodeId: it.section_ref,
    present: true,
    reason: it.reason,
    canAnswer: it.can_answer,
    response: it.response,
    sectionTextLength: it.section_text_length,
  }
}

const resolvedIterations = computed<ResolvedIteration[]>(() =>
  (result.value?.iterations ?? []).map(toResolved),
)

async function run(): Promise<void> {
  if (!query.value.trim()) return
  running.value = true
  error.value = null
  result.value = null
  activeIteration.value = null
  try {
    result.value = await runReasoning(props.docId, query.value, modelId.value || undefined)
  } catch (e) {
    error.value = (e as Error).message || t('reasoning.runErrUnknown')
  } finally {
    running.value = false
  }
}

function onIterationFocus(n: number): void {
  activeIteration.value = n
  const it = resolvedIterations.value.find((r) => r.iteration === n)
  if (it?.sectionRef) emit('sectionFocus', it.sectionRef)
}
</script>

<style scoped>
.ask-runner {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  overflow-y: auto;
  height: 100%;
}

.ask-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ask-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.ask-textarea {
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  resize: vertical;
  transition: border-color var(--transition);
}

.ask-textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.ask-textarea:disabled {
  opacity: 0.6;
}

.ask-model-details {
  font-size: 12px;
}

.ask-model-summary {
  cursor: pointer;
  color: var(--text-secondary);
  padding: 2px 0;
  user-select: none;
}

.ask-model-input {
  width: 100%;
  margin-top: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  box-sizing: border-box;
}

.ask-model-input:focus {
  outline: none;
  border-color: var(--accent);
}

.ask-model-hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--text-muted);
}

.ask-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition);
}

.ask-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ask-submit:hover:not(:disabled) {
  opacity: 0.9;
}

.ask-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.ask-error {
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error);
  border-radius: var(--radius-sm);
  color: var(--error);
  font-size: 12px;
}

.ask-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ask-answer {
  background: var(--bg);
  border: 1px solid #ea580c;
  border-radius: var(--radius);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(234, 88, 12, 0.08);
}

.ask-answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.ask-answer-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #ea580c;
}

.ask-converged {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ask-converged.yes {
  background: rgba(22, 163, 74, 0.15);
  color: #15803d;
}

.ask-converged.no {
  background: rgba(234, 179, 8, 0.15);
  color: #a16207;
}

.ask-answer-body {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text);
}

.ask-answer-body :deep(p) {
  margin: 0 0 8px;
}

.ask-answer-body :deep(p:last-child) {
  margin-bottom: 0;
}

.ask-answer-body :deep(ol),
.ask-answer-body :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 22px;
}

.ask-answer-body :deep(li) {
  margin: 2px 0;
}

.ask-answer-body :deep(strong) {
  font-weight: 600;
}

.ask-answer-body :deep(code) {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  background: var(--border-light);
  padding: 1px 5px;
  border-radius: 3px;
}

.ask-section-title {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.ask-iterations {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>

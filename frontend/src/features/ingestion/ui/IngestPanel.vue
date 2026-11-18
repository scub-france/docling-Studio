<template>
  <div class="ingest-panel" data-e2e="ingest-panel">
    <!-- Unavailable state -->
    <div v-if="!ingestionStore.available" class="ingest-empty">
      <svg class="empty-icon" viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clip-rule="evenodd"
        />
      </svg>
      <p class="empty-text">{{ t('ingestion.unavailable') }}</p>
    </div>

    <!-- Ready to ingest -->
    <template v-else>
      <!-- Summary -->
      <div class="ingest-summary">
        <div class="summary-row">
          <span class="summary-label">{{ t('ingestion.document') }}</span>
          <span class="summary-value">{{ documentName }}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">{{ t('ingestion.chunkCount') }}</span>
          <span class="summary-value summary-mono">{{ chunkCount }}</span>
        </div>
      </div>

      <!-- Stepper -->
      <div v-if="ingestionStore.currentStep" class="ingestion-stepper">
        <div
          class="step"
          :class="{
            active: ingestionStore.currentStep === 'embedding',
            done:
              ingestionStore.currentStep === 'indexing' || ingestionStore.currentStep === 'done',
          }"
        >
          <span class="step-dot" />
          <span class="step-label">{{ t('ingestion.stepEmbedding') }}</span>
        </div>
        <div
          class="step-line"
          :class="{
            done:
              ingestionStore.currentStep === 'indexing' || ingestionStore.currentStep === 'done',
          }"
        />
        <div
          class="step"
          :class="{
            active: ingestionStore.currentStep === 'indexing',
            done: ingestionStore.currentStep === 'done',
          }"
        >
          <span class="step-dot" />
          <span class="step-label">{{ t('ingestion.stepIndexing') }}</span>
        </div>
        <div class="step-line" :class="{ done: ingestionStore.currentStep === 'done' }" />
        <div
          class="step"
          :class="{
            active: ingestionStore.currentStep === 'done',
            done: ingestionStore.currentStep === 'done',
          }"
        >
          <span class="step-dot" />
          <span class="step-label">{{ t('ingestion.stepDone') }}</span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="ingestionStore.error" class="ingest-error">
        {{ ingestionStore.error }}
      </div>

      <!-- Success -->
      <div v-if="ingestionStore.currentStep === 'done'" class="ingest-success">
        <svg class="success-icon" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clip-rule="evenodd"
          />
        </svg>
        <span>{{ t('ingestion.successMessage') }}</span>
      </div>

      <!-- Action -->
      <button
        class="ingest-btn"
        data-e2e="ingest-btn"
        :disabled="ingestionStore.ingesting || !analysisId"
        @click="runIngestion"
      >
        <div v-if="ingestionStore.ingesting" class="spinner-sm" />
        <svg v-else viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
          <path
            fill-rule="evenodd"
            d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
            clip-rule="evenodd"
          />
        </svg>
        {{ ingestionStore.ingesting ? t('ingestion.ingesting') : t('ingestion.ingest') }}
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useIngestionStore } from '../store'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  analysisId: string | null
  documentName: string
  chunkCount: number
}>()

const ingestionStore = useIngestionStore()
const { t } = useI18n()

async function runIngestion() {
  if (!props.analysisId) return
  await ingestionStore.ingest(props.analysisId)
}
</script>

<style scoped>
.ingest-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.ingest-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  flex: 1;
}

.empty-icon {
  width: 32px;
  height: 32px;
  color: var(--text-muted);
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: var(--text-muted);
  text-align: center;
}

/* Summary */
.ingest-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.summary-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.summary-value {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.summary-mono {
  font-family: 'IBM Plex Mono', monospace;
}

/* Stepper */
.ingestion-stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 12px 0;
}

.step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border);
  transition: all 0.3s ease;
}

.step.active .step-dot {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
  animation: pulse-dot 1s ease-in-out infinite;
}

.step.done .step-dot {
  background: var(--success);
}

.step-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--accent);
}

.step.done .step-label {
  color: var(--success);
}

.step-line {
  width: 40px;
  height: 2px;
  background: var(--border);
  transition: background 0.3s ease;
}

.step-line.done {
  background: var(--success);
}

@keyframes pulse-dot {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.7;
  }
}

/* Error */
.ingest-error {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  color: var(--error);
  font-size: 13px;
}

/* Success */
.ingest-success {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-sm);
  color: var(--success);
  font-size: 13px;
  font-weight: 500;
}

.success-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Action button */
.ingest-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  color: white;
  background: var(--success);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.ingest-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}

.ingest-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ingest-btn .btn-icon {
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

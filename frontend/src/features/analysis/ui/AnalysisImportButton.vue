<template>
  <span class="analysis-import">
    <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="onSelect" />
    <button
      class="analysis-import-button"
      type="button"
      :disabled="importing"
      :class="{ 'analysis-import-button--icon': iconOnly }"
      :title="t('analysisImport.button')"
      :aria-label="t('analysisImport.button')"
      @click="fileInput?.click()"
    >
      <svg v-if="iconOnly" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 12V5h7M8.5 8.5 12 5l3.5 3.5M12 5v10" />
        <circle cx="16.5" cy="16.5" r="4" />
        <path d="m19.5 19.5 2.5 2.5" />
      </svg>
      <template v-else>{{
        importing ? t('analysisImport.importing') : t('analysisImport.button')
      }}</template>
    </button>
    <span v-if="error" class="analysis-import-error" role="alert">{{ error }}</span>
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { importAnalysis } from '../api'
import { useI18n } from '@/shared/i18n'

const props = withDefaults(defineProps<{ documentId: string; iconOnly?: boolean }>(), {
  iconOnly: false,
})
const emit = defineEmits<{ imported: [analysisId: string] }>()
const { t } = useI18n()
const fileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const error = ref<string | null>(null)

async function onSelect(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  importing.value = true
  error.value = null
  try {
    const document = JSON.parse(await file.text()) as Record<string, unknown>
    const analysis = await importAnalysis(props.documentId, document)
    emit('imported', analysis.id)
  } catch (e) {
    error.value = (e as Error).message || t('analysisImport.failed')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.analysis-import {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.analysis-import-button {
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
}

.analysis-import-button:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.analysis-import-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.analysis-import-button--icon {
  width: 28px;
  height: 28px;
  padding: 5px;
}

.analysis-import-button--icon svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.analysis-import-error {
  max-width: 220px;
  color: var(--error);
  font-size: 11px;
}
</style>

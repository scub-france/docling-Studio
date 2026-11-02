<template>
  <div ref="menuRef" class="document-actions">
    <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="onImport" />
    <button
      type="button"
      class="document-actions-trigger"
      :title="t('documentActions.title')"
      :aria-label="t('documentActions.title')"
      :aria-expanded="open"
      aria-haspopup="menu"
      @click="open = !open"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="5" cy="12" r="1.5" />
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="19" cy="12" r="1.5" />
      </svg>
    </button>
    <div
      v-if="open"
      class="document-actions-menu"
      role="menu"
      :aria-label="t('documentActions.title')"
    >
      <button type="button" role="menuitem" :disabled="startDisabled" @click="start">
        {{ t('newAnalysis.title') }}
      </button>
      <button type="button" role="menuitem" :disabled="importing" @click="fileInput?.click()">
        {{ importing ? t('analysisImport.importing') : t('analysisImport.button') }}
      </button>
      <button type="button" role="menuitem" class="document-actions-delete" @click="remove">
        {{ t('docs.delete') }}
      </button>
    </div>
    <span v-if="error" class="document-actions-error" role="alert">{{ error }}</span>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { importAnalysis } from '@/features/analysis'
import { useI18n } from '@/shared/i18n'

const props = defineProps<{ documentId: string; startDisabled?: boolean }>()
const emit = defineEmits<{
  start: []
  imported: [analysisId: string]
  delete: []
}>()
const { t } = useI18n()
const open = ref(false)
const importing = ref(false)
const error = ref<string | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function start(): void {
  open.value = false
  emit('start')
}

function remove(): void {
  open.value = false
  emit('delete')
}

async function onImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  importing.value = true
  error.value = null
  try {
    const document = JSON.parse(await file.text()) as Record<string, unknown>
    const analysis = await importAnalysis(props.documentId, document)
    open.value = false
    emit('imported', analysis.id)
  } catch (e) {
    error.value = (e as Error).message || t('analysisImport.failed')
  } finally {
    importing.value = false
  }
}

function onClickOutside(event: MouseEvent): void {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) open.value = false
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.document-actions {
  position: relative;
}
.document-actions-trigger {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
}
.document-actions-trigger:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.document-actions-trigger svg {
  width: 18px;
  fill: currentColor;
}
.document-actions-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  right: 0;
  min-width: 172px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  box-shadow: var(--shadow-lg);
}
.document-actions-menu button {
  display: block;
  width: 100%;
  padding: 7px 9px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  font-size: 12px;
  text-align: left;
}
.document-actions-menu button:hover:not(:disabled) {
  background: var(--bg-hover);
}
.document-actions-menu button:disabled {
  cursor: wait;
  opacity: 0.6;
}
.document-actions-menu .document-actions-delete {
  color: var(--error);
}
.document-actions-error {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 220px;
  color: var(--error);
  font-size: 11px;
}
</style>

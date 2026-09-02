<template>
  <div
    class="upload-zone"
    data-e2e="upload-zone"
    :class="{ dragging, uploading: store.uploading }"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
    @click="openFilePicker"
  >
    <input ref="fileInput" type="file" accept=".pdf,.docx" hidden @change="onFileSelect" />
    <div v-if="store.uploading" class="upload-state">
      <div class="spinner" />
      <span>{{ t('upload.uploading') }}</span>
    </div>
    <div v-else class="upload-state">
      <svg
        class="upload-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <path d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a1 1 0 001 1h14a1 1 0 001-1v-2" />
      </svg>
      <span class="upload-text">{{ t('upload.drop') }}</span>
      <span class="upload-hint" data-e2e="upload-hint">{{ uploadHint }}</span>
      <span v-if="store.error" class="upload-error" data-e2e="upload-error">{{ store.error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDocumentStore } from '../store'
import { useI18n } from '../../../shared/i18n'
import { appMaxFileSizeMb, appMaxPageCount } from '../../../shared/appConfig'
import { isAcceptedFormat } from '../../../shared/format'

const emit = defineEmits<{ uploaded: [docId: string] }>()

const store = useDocumentStore()
const { t } = useI18n()
const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

const uploadHint = computed(() => {
  const parts: string[] = []
  if (appMaxFileSizeMb.value > 0) {
    parts.push(t('upload.maxSize').replace('{n}', String(appMaxFileSizeMb.value)))
  }
  if (appMaxPageCount.value > 0) {
    parts.push(t('upload.maxPages').replace('{n}', String(appMaxPageCount.value)))
  }
  return parts.join(' · ')
})

function openFilePicker() {
  fileInput.value?.click()
}

async function handleFile(file: File) {
  store.clearError()
  if (!isAcceptedFormat(file)) {
    store.error = t('upload.invalidFormat')
    return
  }
  try {
    const doc = await store.upload(file)
    if (doc) emit('uploaded', doc.id)
  } catch {
    // error is already set in store.upload
  }
}

async function onFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) await handleFile(file)
  target.value = ''
}

async function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) await handleFile(file)
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed var(--border-light);
  border-radius: var(--radius);
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
}

.upload-zone:hover,
.upload-zone.dragging {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.upload-zone.uploading {
  pointer-events: none;
  opacity: 0.7;
}

.upload-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  width: 36px;
  height: 36px;
  color: var(--text-muted);
}

.upload-text {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.upload-error {
  font-size: 13px;
  color: var(--error, #e53e3e);
  font-weight: 500;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

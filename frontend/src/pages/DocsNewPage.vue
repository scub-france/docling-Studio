<template>
  <div class="docs-new-page">
    <!-- Header -->
    <div class="page-header">
      <RouterLink :to="{ name: ROUTES.DOCS_LIBRARY }" class="back-link">
        <svg viewBox="0 0 20 20" fill="currentColor" class="back-icon">
          <path
            fill-rule="evenodd"
            d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
            clip-rule="evenodd"
          />
        </svg>
        {{ t('docsNew.backToLibrary') }}
      </RouterLink>
      <h1 class="page-title">{{ t('docsNew.title') }}</h1>
    </div>

    <!-- Drop zone -->
    <div
      class="drop-zone"
      :class="{ dragging, disabled: isUploading }"
      data-e2e="drop-zone"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="openPicker"
    >
      <input ref="fileInput" type="file" multiple accept=".pdf" hidden @change="onFileSelect" />
      <svg
        class="drop-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <path d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a1 1 0 001 1h14a1 1 0 001-1v-2" />
      </svg>
      <p class="drop-text">{{ t('docsNew.drop') }}</p>
      <p class="drop-hint">{{ t('docsNew.dropHint') }}</p>
    </div>

    <!-- Per-file upload list -->
    <ul v-if="uploads.length" class="upload-list" data-e2e="upload-list">
      <li
        v-for="(item, idx) in uploads"
        :key="idx"
        class="upload-item"
        :class="`upload-item--${item.status}`"
        data-e2e="upload-item"
      >
        <svg class="upload-item-icon" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="upload-item-name" :title="item.file.name">{{ item.file.name }}</span>
        <span class="upload-item-status">{{ statusLabel(item.status) }}</span>
        <span v-if="item.status === 'uploading'" class="upload-spinner" />
        <RouterLink
          v-if="item.status === 'done' && item.docId"
          :to="{ name: ROUTES.DOC_WORKSPACE, params: { id: item.docId } }"
          class="upload-item-link"
        >
          {{ t('docsNew.viewDoc') }}
        </RouterLink>
        <span v-if="item.status === 'failed'" class="upload-item-error">{{ item.error }}</span>
      </li>
    </ul>

    <!-- All done state -->
    <div v-if="allDone && uploads.length" class="done-state" data-e2e="done-state">
      <p class="done-msg">{{ t('docsNew.allDone') }}</p>
      <RouterLink :to="{ name: ROUTES.DOCS_LIBRARY }" class="btn-primary">
        {{ t('docsNew.viewLibrary') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { uploadDocument } from '../features/document/api'
import { useI18n } from '../shared/i18n'
import { ROUTES } from '../shared/routing/names'
import { appMaxFileSizeMb } from '../shared/appConfig'

type UploadStatus = 'queued' | 'uploading' | 'done' | 'failed'

interface UploadItem {
  file: File
  status: UploadStatus
  docId?: string
  error?: string
}

const { t } = useI18n()

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const uploads = ref<UploadItem[]>([])

const isUploading = computed(() => uploads.value.some((u) => u.status === 'uploading'))
const allDone = computed(
  () =>
    uploads.value.length > 0 &&
    uploads.value.every((u) => u.status === 'done' || u.status === 'failed'),
)

function statusLabel(status: UploadStatus): string {
  return t(`docsNew.${status}`)
}

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

function openPicker(): void {
  if (isUploading.value) return
  fileInput.value?.click()
}

function onDragOver(): void {
  if (!isUploading.value) dragging.value = true
}

function onFileSelect(e: Event): void {
  dragging.value = false
  const target = e.target as HTMLInputElement
  const files = target.files ? [...target.files] : []
  target.value = ''
  enqueue(files)
}

function onDrop(e: DragEvent): void {
  dragging.value = false
  const files = e.dataTransfer?.files ? [...e.dataTransfer.files] : []
  enqueue(files)
}

function enqueue(files: File[]): void {
  const pdfs = files.filter(isPdf)
  if (!pdfs.length) return

  const newItems: UploadItem[] = pdfs.map((f) => ({ file: f, status: 'queued' }))
  uploads.value = [...uploads.value, ...newItems]

  // Upload sequentially to avoid overloading the backend
  processQueue()
}

async function processQueue(): Promise<void> {
  for (const item of uploads.value) {
    if (item.status !== 'queued') continue
    await uploadOne(item)
  }
}

async function uploadOne(item: UploadItem): Promise<void> {
  const maxMb = appMaxFileSizeMb.value
  if (maxMb > 0 && item.file.size > maxMb * 1024 * 1024) {
    item.status = 'failed'
    item.error = t('upload.tooLarge').replace('{n}', String(maxMb))
    return
  }

  item.status = 'uploading'
  try {
    const doc = await uploadDocument(item.file)
    item.status = 'done'
    item.docId = doc.id
  } catch (e) {
    item.status = 'failed'
    item.error = (e as Error).message || 'Upload failed'
  }
}
</script>

<style scoped>
.docs-new-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

/* Header */
.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--transition);
}

.back-link:hover {
  color: var(--text);
}

.back-icon {
  width: 14px;
  height: 14px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--border-light);
  border-radius: var(--radius);
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all var(--transition);
  text-align: center;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.drop-zone.disabled {
  pointer-events: none;
  opacity: 0.5;
}

.drop-icon {
  width: 40px;
  height: 40px;
  color: var(--text-muted);
}

.drop-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary);
}

.drop-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* Upload list */
.upload-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  font-size: 13px;
}

.upload-item-icon {
  width: 14px;
  height: 14px;
  color: var(--accent);
  flex-shrink: 0;
}

.upload-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--text);
}

.upload-item-status {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  flex-shrink: 0;
}

.upload-item--done .upload-item-status {
  color: var(--success);
}

.upload-item--failed .upload-item-status {
  color: var(--error);
}

.upload-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.upload-item-link {
  font-size: 12px;
  color: var(--accent);
  text-decoration: none;
  flex-shrink: 0;
}

.upload-item-link:hover {
  text-decoration: underline;
}

.upload-item-error {
  font-size: 11px;
  color: var(--error);
  flex-shrink: 0;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Done state */
.done-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  text-align: center;
}

.done-msg {
  font-size: 14px;
  color: var(--success);
  font-weight: 500;
}

/* Shared button */
.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  color: white;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-decoration: none;
  transition: background var(--transition);
}

.btn-primary:hover {
  background: var(--accent-hover);
}
</style>

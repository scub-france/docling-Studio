<template>
  <div class="page-preview" v-if="documentId">
    <div class="preview-header">
      <span class="preview-label">Page {{ page }}</span>
      <div class="preview-nav">
        <button class="nav-btn" :disabled="page <= 1" @click="$emit('update:page', page - 1)">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
        <button
          class="nav-btn"
          :disabled="!!(pageCount && page >= pageCount)"
          @click="$emit('update:page', page + 1)"
        >
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
    <div class="preview-image-wrapper">
      <PdfPagePreview :document-id="documentId" :page="page" @ready="onReady" />
    </div>
  </div>
</template>

<script setup lang="ts">
import PdfPagePreview from './PdfPagePreview.vue'

defineProps({
  documentId: String,
  page: { type: Number, default: 1 },
  pageCount: Number,
})

const emit = defineEmits(['update:page', 'imageLoaded'])

function onReady(element: HTMLElement | null): void {
  if (element) emit('imageLoaded', element)
}
</script>

<style scoped>
.page-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-label {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.preview-nav {
  display: flex;
  gap: 4px;
}

.nav-btn {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  transition: all var(--transition);
}

.nav-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text);
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.nav-btn svg {
  width: 16px;
  height: 16px;
}

.preview-image-wrapper {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.preview-image-wrapper :deep(.pdf-page-preview) {
  width: 100%;
}
</style>

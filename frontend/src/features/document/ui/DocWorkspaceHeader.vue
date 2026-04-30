<template>
  <header class="workspace-header" data-e2e="workspace-header">
    <div class="workspace-header-main">
      <svg class="doc-icon" viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
          clip-rule="evenodd"
        />
      </svg>
      <h1 class="workspace-title" :title="doc.filename">{{ doc.filename }}</h1>
      <StatusBadge :state="doc.lifecycleState" />
    </div>
    <div class="workspace-header-meta">
      <div v-if="doc.stores?.length" class="workspace-stores">
        <RouterLink
          v-for="store in doc.stores"
          :key="store"
          :to="{ name: ROUTES.STORE_DETAIL, params: { store } }"
          class="store-chip"
          :title="store"
        >
          {{ store }}
        </RouterLink>
      </div>
      <span v-if="doc.fileSize" class="meta-item">{{ formatSize(doc.fileSize) }}</span>
      <span class="meta-item">{{ formatRelativeTime(doc.lifecycleStateAt ?? doc.createdAt) }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Document } from '../../../shared/types'
import { formatSize, formatRelativeTime } from '../../../shared/format'
import { ROUTES } from '../../../shared/routing/names'
import StatusBadge from './StatusBadge.vue'

defineProps<{
  doc: Document
}>()
</script>

<style scoped>
.workspace-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.workspace-header-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.doc-icon {
  width: 16px;
  height: 16px;
  color: var(--accent);
  flex-shrink: 0;
}

.workspace-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.workspace-header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.workspace-stores {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.store-chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 100px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition);
  white-space: nowrap;
  overflow: hidden;
  max-width: 120px;
  text-overflow: ellipsis;
}

.store-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.meta-item {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}
</style>

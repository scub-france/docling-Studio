<template>
  <Teleport to="body">
    <div class="table-modal-backdrop" data-e2e="table-modal" @click.self="emit('close')">
      <div class="table-modal" role="dialog" aria-modal="true" :aria-label="title">
        <header class="table-modal-header">
          <h3 class="table-modal-title">{{ title }}</h3>
          <button
            type="button"
            class="table-modal-close"
            :aria-label="t('tableModal.close')"
            data-e2e="table-modal-close"
            @click="emit('close')"
          >
            ✕
          </button>
        </header>
        <div class="table-modal-body">
          <MarkdownViewer :content="content" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * Full-size table viewer (#303 demo polish).
 *
 * The Properties panel is narrow (~360px), so wide extracted tables are
 * cramped even with horizontal scroll. This modal renders the same table
 * markdown via `MarkdownViewer` in a large, centred surface. Closes on
 * backdrop click, the ✕ button, or Escape.
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { useI18n } from '../../../shared/i18n'
import MarkdownViewer from '../../analysis/ui/MarkdownViewer.vue'

defineProps<{ content: string; title: string }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.table-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.table-modal {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  width: min(960px, 92vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  overflow: hidden;
}

.table-modal-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.table-modal-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.table-modal-close {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color var(--transition);
}

.table-modal-close:hover {
  color: var(--text);
}

.table-modal-body {
  overflow: auto;
  padding: 8px 16px 16px;
}
</style>

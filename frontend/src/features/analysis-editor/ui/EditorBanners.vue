<template>
  <div v-if="previewError" class="editor-error" role="alert">
    {{ previewError }}
  </div>
  <div v-if="historyError" class="editor-error" role="alert">
    {{ historyError }}
  </div>
  <div v-if="conflict" class="editor-conflict" role="alert">
    <span>{{ t('analysisEditor.conflict') }}</span>
    <button type="button" @click="emit('reloadConflict')">
      {{ t('analysisEditor.conflictReload') }}
    </button>
    <button type="button" @click="emit('copyConflict')">
      {{ t('analysisEditor.conflictCopy') }}
    </button>
    <button type="button" @click="emit('discardConflict')">
      {{ t('analysisEditor.conflictDiscard') }}
    </button>
  </div>
  <div
    v-if="recoveredCount"
    class="editor-recovery"
    data-e2e="analysis-editor-recovered"
    role="status"
  >
    <span>{{ t('analysisEditor.recoveredDraft', { n: recoveredCount }) }}</span>
    <button type="button" data-e2e="analysis-editor-restore-draft" @click="emit('restoreDraft')">
      {{ t('analysisEditor.restoreDraft') }}
    </button>
    <button type="button" data-e2e="analysis-editor-discard-draft" @click="emit('discardDraft')">
      {{ t('analysisEditor.discardDraft') }}
    </button>
  </div>
  <div v-if="saveNotice" class="editor-success" data-e2e="analysis-editor-saved" role="status">
    {{ saveNotice }}
  </div>
  <div v-if="chunksStale" class="editor-warning">
    {{ t('analysisEditor.chunksStale') }}
  </div>
</template>

<script setup lang="ts">
/**
 * The editor's status banners, in display order: preview and history errors,
 * the save conflict, the recovered draft, the save notice and the stale-chunks
 * warning. Rendered as siblings (no wrapper) inside the editor's column.
 */
import { useI18n } from '../../../shared/i18n'

defineProps<{
  previewError: string | null
  historyError: string | null
  /** The 409 message of a save that lost the race, if any. */
  conflict: string | null
  /** Number of unsaved commands found in session storage. */
  recoveredCount: number
  saveNotice: string | null
  chunksStale: boolean
}>()

const emit = defineEmits<{
  reloadConflict: []
  copyConflict: []
  discardConflict: []
  restoreDraft: []
  discardDraft: []
}>()

const { t } = useI18n()
</script>

<style scoped src="./editorButton.css"></style>

<style scoped>
.editor-warning,
.editor-error,
.editor-success,
.editor-recovery,
.editor-conflict {
  padding: 8px 16px;
  font-size: 12px;
}
.editor-warning {
  color: var(--warning);
  background: color-mix(in srgb, var(--warning) 10%, transparent);
}
.editor-success {
  color: var(--success);
  background: color-mix(in srgb, var(--success) 10%, transparent);
}
.editor-recovery {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  background: var(--bg-elevated);
}
.editor-conflict {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--error);
  background: color-mix(in srgb, var(--error) 10%, transparent);
}
.editor-error {
  color: var(--error);
}
</style>

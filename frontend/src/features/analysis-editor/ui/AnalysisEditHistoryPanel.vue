<template>
  <section class="history-panel" data-e2e="analysis-edit-history">
    <div v-if="!history.length" class="history-empty">
      {{ t('analysisEditor.historyEmpty') }}
    </div>
    <article
      v-for="entry in [...history].reverse()"
      :key="entry.id"
      class="history-entry"
      :class="{ 'history-entry--reverted': entry.active === false }"
    >
      <div class="history-entry-head">
        <strong v-if="entry.commandType === 'setCommandActive'">
          #{{ entry.sequence }}
          {{ entry.payload.active ? t('analysisEditor.reapplied') : t('analysisEditor.reverted') }}
          #{{ entry.payload.targetSequence }}
        </strong>
        <strong v-else>#{{ entry.sequence }} {{ describeCommand(entry.commandType) }}</strong>
        <time>{{ formatHistoryDate(entry.createdAt) }}</time>
      </div>
      <code v-if="entry.commandType !== 'setCommandActive'">{{
        formatHistoryPayload(entry.payload)
      }}</code>
      <div v-if="entry.active !== null" class="history-entry-actions">
        <span>{{
          entry.active ? t('analysisEditor.activeEdit') : t('analysisEditor.revertedEdit')
        }}</span>
        <button
          type="button"
          :data-e2e="`analysis-editor-history-toggle-${entry.sequence}`"
          :disabled="!canChange"
          :aria-label="
            entry.active
              ? t('analysisEditor.revertEditNumber', { n: entry.sequence })
              : t('analysisEditor.reapplyEditNumber', { n: entry.sequence })
          "
          :title="canChange ? undefined : t('analysisEditor.resolveDraftFirst')"
          @click="emit('setActive', entry.sequence, !entry.active)"
        >
          {{ entry.active ? t('analysisEditor.revertEdit') : t('analysisEditor.reapplyEdit') }}
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
/** The saved edits of the analysis, newest first, each one revertible or reapplicable. */
import { useI18n } from '../../../shared/i18n'
import type { AnalysisEditHistoryEntry } from '../types'

defineProps<{
  history: AnalysisEditHistoryEntry[]
  /** Saved edits can be toggled only with no draft pending and nothing saving. */
  canChange: boolean
}>()

const emit = defineEmits<{
  setActive: [sequence: number, active: boolean]
}>()

const { t } = useI18n()

/** The translated command type, or the raw type when no translation exists. */
function describeCommand(commandType: string): string {
  const key = `analysisEditor.commandType.${commandType}`
  const label = t(key)
  return label === key ? commandType : label
}
function formatHistoryDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(value),
  )
}
function formatHistoryPayload(payload: Record<string, unknown>): string {
  const values = Object.entries(payload)
    .filter(([key]) => key !== 'elementId' && key !== 'elementIds')
    .map(([key, value]) => `${key}: ${String(value)}`)
  return values.join(' · ') || t('analysisEditor.structuralChange')
}
</script>

<style scoped src="./editorButton.css"></style>

<style scoped>
.history-panel {
  max-height: 220px;
  overflow: auto;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}
.history-entry {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}
.history-entry:last-child {
  border-bottom: 0;
}
.history-entry--reverted {
  opacity: 0.7;
}
.history-entry-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 11px;
}
.history-entry time {
  color: var(--text-muted);
  white-space: nowrap;
}
.history-entry code {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font:
    10px 'IBM Plex Mono',
    monospace;
  white-space: pre-wrap;
}
.history-entry-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 11px;
}
.history-entry-actions button {
  padding: 3px 8px;
}
.history-empty {
  padding: 12px 0;
  color: var(--text-muted);
  font-size: 12px;
}
</style>

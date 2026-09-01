<template>
  <section class="edit-panel">
    <div v-if="!element" class="empty">{{ t('analysisEditor.selectElement') }}</div>
    <template v-else>
      <div class="panel-heading">
        <span class="eyebrow">{{ element.type }}</span>
        <span class="ref">{{ element.selfRef }}</span>
      </div>
      <label v-if="element.editable" class="field">
        <span>{{ t('analysisEditor.text') }}</span>
        <textarea v-model="draft" rows="8" @blur="commitText" />
      </label>
      <button
        v-if="element.supportedOperations.includes('deleteElement')"
        type="button"
        class="delete-button"
        @click="emit('deleteElement')"
      >
        {{ t('analysisEditor.deleteElement') }}
      </button>
      <label v-if="element.supportedOperations.includes('setHeadingLevel')" class="field">
        <span>{{ t('analysisEditor.headingLevel') }}</span>
        <select :value="element.headingLevel ?? 1" @change="changeLevel">
          <option value="-1">{{ t('analysisEditor.bodyText') }}</option>
          <option value="0">{{ t('analysisEditor.titleText') }}</option>
          <option v-for="level in 6" :key="level" :value="level">{{ level }}</option>
        </select>
      </label>
      <p v-if="!element.editable" class="muted">{{ element.nonEditableReason }}</p>
      <div v-if="element.provenance.length" class="provenance">
        <span v-for="source in element.provenance" :key="`${source.page}-${source.bbox.join(',')}`">
          p{{ source.page }}: {{ source.bbox.map((value) => Math.round(value)).join(', ') }}
        </span>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { EditorElement } from '../types'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{ element: EditorElement | null }>()
const { t } = useI18n()
const emit = defineEmits<{
  replaceText: [text: string]
  headingLevel: [level: number]
  deleteElement: []
}>()
const draft = ref('')
watch(() => props.element, (element) => { draft.value = element?.text ?? '' }, { immediate: true })
function commitText(): void {
  if (props.element?.editable && draft.value !== (props.element.text ?? '')) emit('replaceText', draft.value)
}
function changeLevel(event: Event): void {
  emit('headingLevel', Number((event.target as HTMLSelectElement).value))
}
</script>

<style scoped>
.edit-panel { height: 100%; overflow: auto; padding: 16px; }
.empty, .muted { color: var(--text-muted); font-size: 12px; }
.panel-heading { display: flex; flex-direction: column; gap: 4px; margin-bottom: 18px; }
.eyebrow { color: var(--accent); font: 11px 'IBM Plex Mono', monospace; text-transform: uppercase; }
.ref { color: var(--text-muted); font: 10px 'IBM Plex Mono', monospace; overflow-wrap: anywhere; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; color: var(--text-secondary); font-size: 12px; }
textarea, select { border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--text); padding: 8px; font: inherit; }
textarea { resize: vertical; line-height: 1.45; }
.provenance { display: flex; flex-direction: column; gap: 5px; color: var(--text-muted); font: 10px 'IBM Plex Mono', monospace; }
.delete-button { margin-top: 4px; padding: 7px 10px; border: 1px solid var(--error); border-radius: var(--radius-sm); background: transparent; color: var(--error); cursor: pointer; font: inherit; }
</style>

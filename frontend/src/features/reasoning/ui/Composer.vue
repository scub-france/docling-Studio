<template>
  <div class="composer">
    <textarea
      v-model="query"
      class="composer-input"
      rows="2"
      :placeholder="t('ask.placeholder')"
      data-e2e="ask-composer-input"
      @keydown.enter.exact.prevent="submit"
    />
    <div class="composer-row">
      <input
        v-model="model"
        class="composer-model"
        :placeholder="t('ask.modelPlaceholder')"
        data-e2e="ask-composer-model"
      />
      <button
        class="btn-run"
        :disabled="!!reason"
        :title="reason || t('ask.run')"
        data-e2e="ask-run-btn"
        @click="submit"
      >
        {{ t('ask.run') }}
      </button>
    </div>
    <div v-if="reason" class="composer-reason" data-e2e="ask-run-reason">{{ reason }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  docLoaded: boolean
  running: boolean
}>()

const emit = defineEmits<{ run: [query: string, model: string | undefined] }>()

const { t } = useI18n()

const query = ref('')
const model = ref('')

// Disabled-reason precedence (handoff-binding): document not ready → run in
// progress → blank query. Exactly one reason is shown; null means enabled.
const reason = computed<string | null>(() => {
  if (!props.docLoaded) return t('ask.reasonNoDoc')
  if (props.running) return t('ask.reasonRunning')
  if (!query.value.trim()) return t('ask.reasonEmpty')
  return null
})

function submit(): void {
  if (reason.value) return
  emit('run', query.value.trim(), model.value.trim() || undefined)
  query.value = ''
}
</script>

<style scoped>
.composer {
  border-top: 1px solid var(--border);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.composer-input {
  width: 100%;
  resize: none;
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 8px 10px;
  font-size: 12.5px;
  font-family: inherit;
  color: var(--text);
  background: var(--bg);
  box-sizing: border-box;
}

.composer-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 20%, transparent);
}

.composer-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.composer-model {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: var(--text);
  background: var(--bg);
}

.composer-model:focus {
  outline: none;
  border-color: var(--accent);
}

.btn-run {
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 12.5px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  cursor: pointer;
  transition: background var(--transition);
}

.btn-run:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-run:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.composer-reason {
  font-size: 11px;
  color: var(--text-muted);
}
</style>

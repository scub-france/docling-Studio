<template>
  <div class="config-form">
    <div class="field">
      <label class="field-label" for="store-neo4j-index">{{
        t('storeForm.neo4j.indexName')
      }}</label>
      <input
        id="store-neo4j-index"
        v-model="indexName"
        class="field-input"
        type="text"
        placeholder="chunks-vec"
        :aria-invalid="showError && !indexName.trim()"
        @input="emitChange"
      />
      <p v-if="showError && !indexName.trim()" class="field-error">
        {{ t('storeForm.required') }}
      </p>
      <p v-else class="field-help">{{ t('storeForm.neo4j.indexNameHelp') }}</p>
    </div>

    <div class="field">
      <label class="field-label" for="store-neo4j-db">{{ t('storeForm.neo4j.database') }}</label>
      <input
        id="store-neo4j-db"
        v-model="database"
        class="field-input"
        type="text"
        placeholder="neo4j"
        @input="emitChange"
      />
      <p class="field-help">{{ t('storeForm.neo4j.databaseHelp') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from '../../../shared/i18n'

const props = defineProps<{
  modelValue: Record<string, unknown>
  showError?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void
  (e: 'valid', value: boolean): void
}>()

const { t } = useI18n()

const indexName = ref(String(props.modelValue.indexName ?? props.modelValue.index_name ?? ''))
const database = ref(String(props.modelValue.database ?? ''))

function emitChange() {
  emit('update:modelValue', {
    indexName: indexName.value,
    database: database.value || undefined,
  })
  emit('valid', indexName.value.trim().length > 0)
}

watch(
  () => props.modelValue,
  (next) => {
    const incomingIndex = String(next.indexName ?? next.index_name ?? '')
    if (incomingIndex !== indexName.value) indexName.value = incomingIndex
    const incomingDb = String(next.database ?? '')
    if (incomingDb !== database.value) database.value = incomingDb
  },
)

emit('valid', indexName.value.trim().length > 0)
</script>

<style scoped>
.config-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field-label {
  font-weight: 500;
  font-size: 0.875rem;
}
.field-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-light);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: var(--text);
  background: var(--bg-surface);
}
.field-input[aria-invalid='true'] {
  border-color: var(--error);
}
.field-help {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.field-error {
  font-size: 0.75rem;
  color: var(--error);
}
</style>

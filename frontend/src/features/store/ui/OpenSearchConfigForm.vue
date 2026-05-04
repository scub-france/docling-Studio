<template>
  <div class="config-form">
    <div class="field">
      <label class="field-label" for="store-os-index">{{
        t('storeForm.opensearch.indexName')
      }}</label>
      <input
        id="store-os-index"
        v-model="indexName"
        class="field-input"
        type="text"
        :placeholder="'rh-corpus-v3'"
        :aria-invalid="showError && !indexName.trim()"
        @input="emitChange"
      />
      <p v-if="showError && !indexName.trim()" class="field-error">
        {{ t('storeForm.required') }}
      </p>
      <p v-else class="field-help">{{ t('storeForm.opensearch.indexNameHelp') }}</p>
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

function emitChange() {
  emit('update:modelValue', { indexName: indexName.value })
  emit('valid', indexName.value.trim().length > 0)
}

watch(
  () => props.modelValue,
  (next) => {
    const incoming = String(next.indexName ?? next.index_name ?? '')
    if (incoming !== indexName.value) {
      indexName.value = incoming
    }
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
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
.field-input[aria-invalid='true'] {
  border-color: #dc2626;
}
.field-help {
  font-size: 0.75rem;
  color: var(--color-text-muted, #6b7280);
}
.field-error {
  font-size: 0.75rem;
  color: #dc2626;
}
</style>

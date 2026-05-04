<template>
  <form class="store-form" @submit.prevent="onSubmit">
    <div class="field">
      <label class="field-label" for="store-name">{{ t('storeForm.fieldName') }}</label>
      <input
        id="store-name"
        v-model="form.name"
        class="field-input"
        type="text"
        autocomplete="off"
        :aria-invalid="showError && !form.name.trim()"
      />
      <p v-if="showError && !form.name.trim()" class="field-error">
        {{ t('storeForm.required') }}
      </p>
      <p v-else class="field-help">{{ t('storeForm.fieldNameHelp') }}</p>
    </div>

    <div class="field">
      <label class="field-label" for="store-slug">{{ t('storeForm.fieldSlug') }}</label>
      <input
        id="store-slug"
        v-model="form.slug"
        class="field-input"
        type="text"
        autocomplete="off"
        :disabled="lockSlug"
        :aria-invalid="showError && !slugIsValid"
      />
      <p v-if="showError && !form.slug.trim()" class="field-error">
        {{ t('storeForm.required') }}
      </p>
      <p v-else-if="showError && !slugIsValid" class="field-error">
        {{ t('storeForm.invalidSlug') }}
      </p>
      <p v-else class="field-help">{{ t('storeForm.fieldSlugHelp') }}</p>
    </div>

    <div class="field">
      <label class="field-label" for="store-kind">{{ t('storeForm.fieldKind') }}</label>
      <select id="store-kind" v-model="form.kind" class="field-input">
        <option v-for="opt in kindOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </div>

    <div class="field">
      <label class="field-label" for="store-embedder">{{ t('storeForm.fieldEmbedder') }}</label>
      <input
        id="store-embedder"
        v-model="form.embedder"
        class="field-input"
        type="text"
        autocomplete="off"
        :placeholder="'bge-m3'"
        :aria-invalid="showError && !form.embedder.trim()"
      />
      <p v-if="showError && !form.embedder.trim()" class="field-error">
        {{ t('storeForm.required') }}
      </p>
      <p v-else class="field-help">{{ t('storeForm.fieldEmbedderHelp') }}</p>
    </div>

    <div class="field field--checkbox">
      <label class="checkbox-label">
        <input v-model="form.isDefault" type="checkbox" />
        <span>{{ t('storeForm.fieldIsDefault') }}</span>
      </label>
      <p class="field-help">{{ t('storeForm.fieldIsDefaultHelp') }}</p>
    </div>

    <fieldset class="config-section">
      <legend>{{ t('storeForm.sectionConfig') }}</legend>
      <StoreConfigForm
        v-model="form.config"
        :kind="form.kind"
        :show-error="showError"
        @valid="onConfigValid"
      />
    </fieldset>

    <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

    <div class="actions">
      <button type="button" class="btn-secondary" :disabled="submitting" @click="emit('cancel')">
        {{ t('storeForm.cancel') }}
      </button>
      <button type="submit" class="btn-primary" :disabled="submitting">
        {{ submitLabel }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { StoreCreatePayload, StoreDetail } from '../api'
import { useI18n } from '../../../shared/i18n'
import StoreConfigForm from './StoreConfigForm.vue'

const SLUG_PATTERN = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/

const props = defineProps<{
  initialValue?: Partial<StoreDetail>
  mode: 'create' | 'edit'
  submitting?: boolean
  errorMessage?: string | null
  /** When true, the slug input is disabled (typically in edit mode for the seeded default). */
  lockSlug?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', payload: StoreCreatePayload): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()

const kindOptions = [{ value: 'opensearch', label: 'OpenSearch' }]

const form = reactive<StoreCreatePayload>({
  name: props.initialValue?.name ?? '',
  slug: props.initialValue?.slug ?? '',
  kind: props.initialValue?.kind ?? 'opensearch',
  embedder: props.initialValue?.embedder ?? '',
  config: { ...(props.initialValue?.config ?? {}) },
  isDefault: props.initialValue?.isDefault ?? false,
})

const showError = ref(false)
const configValid = ref(false)

watch(
  () => props.initialValue,
  (next) => {
    if (!next) return
    form.name = next.name ?? form.name
    form.slug = next.slug ?? form.slug
    form.kind = next.kind ?? form.kind
    form.embedder = next.embedder ?? form.embedder
    form.config = { ...(next.config ?? {}) }
    form.isDefault = next.isDefault ?? form.isDefault
  },
  { deep: true },
)

const slugIsValid = computed(() => SLUG_PATTERN.test(form.slug.trim()))

const submitLabel = computed(() =>
  props.mode === 'create' ? t('storeForm.create') : t('storeForm.save'),
)

function onConfigValid(valid: boolean) {
  configValid.value = valid
}

function onSubmit() {
  showError.value = true
  if (!form.name.trim() || !form.embedder.trim() || !slugIsValid.value || !configValid.value) {
    return
  }
  emit('submit', { ...form, slug: form.slug.trim().toLowerCase() })
}
</script>

<style scoped>
.store-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 640px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field--checkbox {
  flex-direction: column;
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
.field-input:disabled {
  background: var(--color-bg-muted, #f3f4f6);
}
.field-help {
  font-size: 0.75rem;
  color: var(--color-text-muted, #6b7280);
}
.field-error {
  font-size: 0.75rem;
  color: #dc2626;
}
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}
.config-section {
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 0.5rem;
  padding: 1rem;
}
.config-section legend {
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0 0.5rem;
}
.form-error {
  background: #fee2e2;
  color: #991b1b;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
.btn-primary {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  background: var(--color-primary, #2563eb);
  color: white;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-secondary {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  background: white;
  color: var(--color-text, #111827);
  border: 1px solid var(--color-border, #d1d5db);
  font-size: 0.875rem;
  cursor: pointer;
}
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

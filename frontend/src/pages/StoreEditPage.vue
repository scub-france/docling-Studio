<template>
  <div class="store-edit-page">
    <header class="header">
      <h1 class="title">{{ t('storeForm.titleEdit') }}</h1>
    </header>

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
    </div>

    <div v-else-if="loadError" class="error-state">
      <p class="error-text">{{ loadError }}</p>
    </div>

    <StoreForm
      v-else-if="initial"
      mode="edit"
      :initial-value="initial"
      :submitting="submitting"
      :error-message="errorMessage"
      :lock-slug="initial.slug === 'default'"
      @submit="onSubmit"
      @cancel="onCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StoreForm from '../features/store/ui/StoreForm.vue'
import {
  fetchStore,
  updateStore,
  type StoreCreatePayload,
  type StoreDetail,
} from '../features/store/api'
import { ROUTES } from '../shared/routing/names'
import { useI18n } from '../shared/i18n'

const props = defineProps<{ store: string }>()

const { t } = useI18n()
const router = useRouter()

const initial = ref<StoreDetail | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  try {
    initial.value = await fetchStore(props.store)
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
})

async function onSubmit(payload: StoreCreatePayload) {
  submitting.value = true
  errorMessage.value = null
  try {
    const updated = await updateStore(props.store, payload)
    if (updated.slug !== props.store) {
      router.push({ name: ROUTES.STORE_DETAIL, params: { store: updated.slug } })
    } else {
      router.push({ name: ROUTES.STORE_DETAIL, params: { store: updated.slug } })
    }
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    submitting.value = false
  }
}

function onCancel() {
  router.push({ name: ROUTES.STORES_LIST })
}
</script>

<style scoped>
.store-edit-page {
  padding: 1.5rem 2rem;
}
.header {
  margin-bottom: 1.5rem;
}
.title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}
.loading-state,
.error-state {
  padding: 2rem;
  display: flex;
  justify-content: center;
}
.error-text {
  color: #dc2626;
}
.spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

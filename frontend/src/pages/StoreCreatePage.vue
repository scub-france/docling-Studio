<template>
  <div class="store-edit-page">
    <header class="header">
      <h1 class="title">{{ t('storeForm.titleCreate') }}</h1>
    </header>
    <StoreForm
      mode="create"
      :submitting="submitting"
      :error-message="errorMessage"
      @submit="onSubmit"
      @cancel="onCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import StoreForm from '../features/store/ui/StoreForm.vue'
import { createStore, type StoreCreatePayload } from '../features/store/api'
import { ROUTES } from '../shared/routing/names'
import { useI18n } from '../shared/i18n'

const { t } = useI18n()
const router = useRouter()
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

async function onSubmit(payload: StoreCreatePayload) {
  submitting.value = true
  errorMessage.value = null
  try {
    await createStore(payload)
    router.push({ name: ROUTES.STORES_LIST })
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
</style>

import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import {
  getReasoningConfig,
  putReasoningConfig,
  resetReasoningConfig,
  testReasoningConnection,
} from './api'
import type { ReasoningConfigView, ReasoningProbeResult } from './types'
import { useFeatureFlagStore } from '@/features/feature-flags'

/**
 * Admin runtime-config store (#317). Holds the server view plus an editable
 * form copy; `save`/`reset` re-sync the `feature-flags` store afterwards so
 * the sidebar and the Ask tab follow the reasoning toggle without a reload.
 */
export const useAdminConfigStore = defineStore('admin-config', () => {
  const view = ref<ReasoningConfigView | null>(null)
  const form = reactive({
    enabled: false,
    ollamaHost: '',
    modelId: '',
    maxIterations: 5,
  })
  const loading = ref(false)
  const saving = ref(false)
  const testing = ref(false)
  const loadError = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  const testResult = ref<ReasoningProbeResult | null>(null)

  const dirty = computed(() => {
    if (!view.value) return false
    return (
      form.enabled !== view.value.enabled ||
      form.ollamaHost !== view.value.ollamaHost ||
      form.modelId !== view.value.modelId ||
      form.maxIterations !== view.value.maxIterations
    )
  })

  function applyView(next: ReasoningConfigView): void {
    view.value = next
    form.enabled = next.enabled
    form.ollamaHost = next.ollamaHost
    form.modelId = next.modelId
    form.maxIterations = next.maxIterations
  }

  async function load(): Promise<void> {
    loading.value = true
    loadError.value = null
    try {
      applyView(await getReasoningConfig())
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : 'Failed to load reasoning config'
    } finally {
      loading.value = false
    }
  }

  async function save(): Promise<boolean> {
    saving.value = true
    saveError.value = null
    try {
      applyView(
        await putReasoningConfig({
          enabled: form.enabled,
          ollamaHost: form.ollamaHost.trim(),
          modelId: form.modelId.trim(),
          maxIterations: form.maxIterations,
        }),
      )
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : 'Failed to save reasoning config'
      return false
    } finally {
      saving.value = false
    }
    await useFeatureFlagStore().reload()
    return true
  }

  async function reset(): Promise<boolean> {
    saving.value = true
    saveError.value = null
    try {
      applyView(await resetReasoningConfig())
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : 'Failed to reset reasoning config'
      return false
    } finally {
      saving.value = false
    }
    await useFeatureFlagStore().reload()
    return true
  }

  async function testConnection(): Promise<void> {
    testing.value = true
    testResult.value = null
    try {
      testResult.value = await testReasoningConnection(form.ollamaHost.trim())
    } catch (e) {
      testResult.value = {
        reachable: false,
        models: [],
        error: e instanceof Error ? e.message : 'probe failed',
      }
    } finally {
      testing.value = false
    }
  }

  return {
    view,
    form,
    dirty,
    loading,
    saving,
    testing,
    loadError,
    saveError,
    testResult,
    load,
    save,
    reset,
    testConnection,
  }
})

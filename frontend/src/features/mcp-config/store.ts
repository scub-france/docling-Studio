import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { getMcpConfig, getMcpServer, putMcpConfig, resetMcpConfig } from './api'
import type { McpConfigView, McpServerView } from './types'

/**
 * MCP admin store (#364). Chains the two reads the section needs — the
 * runtime budgets and the running server — client-side, as #269 asks, and
 * keeps an editable copy of the budgets. `save`/`reset` only touch the
 * budgets: the server's facts change with the environment and a restart.
 */
export const useMcpConfigStore = defineStore('mcp-config', () => {
  const view = ref<McpConfigView | null>(null)
  const server = ref<McpServerView | null>(null)
  const form = reactive({ maxRounds: 5, maxReadTokens: 4000, studioBaseUrl: '' })
  const loading = ref(false)
  const saving = ref(false)
  const loadError = ref<string | null>(null)
  const saveError = ref<string | null>(null)

  const dirty = computed(() => {
    if (!view.value) return false
    return (
      form.maxRounds !== view.value.maxRounds ||
      form.maxReadTokens !== view.value.maxReadTokens ||
      form.studioBaseUrl.trim() !== view.value.studioBaseUrl
    )
  })

  function applyView(next: McpConfigView): void {
    view.value = next
    form.maxRounds = next.maxRounds
    form.maxReadTokens = next.maxReadTokens
    form.studioBaseUrl = next.studioBaseUrl
  }

  function message(e: unknown, fallback: string): string {
    return e instanceof Error ? e.message : fallback
  }

  async function load(): Promise<void> {
    loading.value = true
    loadError.value = null
    try {
      const [config, status] = await Promise.all([getMcpConfig(), getMcpServer()])
      applyView(config)
      server.value = status
    } catch (e) {
      loadError.value = message(e, 'Failed to load MCP config')
    } finally {
      loading.value = false
    }
  }

  async function write(run: () => Promise<McpConfigView>, fallback: string): Promise<boolean> {
    saving.value = true
    saveError.value = null
    try {
      applyView(await run())
      return true
    } catch (e) {
      saveError.value = message(e, fallback)
      return false
    } finally {
      saving.value = false
    }
  }

  function save(): Promise<boolean> {
    return write(
      () =>
        putMcpConfig({
          maxRounds: form.maxRounds,
          maxReadTokens: form.maxReadTokens,
          studioBaseUrl: form.studioBaseUrl.trim(),
        }),
      'Failed to save MCP config',
    )
  }

  function reset(): Promise<boolean> {
    return write(resetMcpConfig, 'Failed to reset MCP config')
  }

  return { view, server, form, dirty, loading, saving, loadError, saveError, load, save, reset }
})

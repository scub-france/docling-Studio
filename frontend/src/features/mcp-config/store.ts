import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { getMcpConfig, getMcpServer, putMcpConfig, resetMcpConfig } from './api'
import type { McpConfigView, McpServerView } from './types'

/**
 * MCP admin store (#364). Chains the two reads the section needs — the
 * runtime budgets and the running server — client-side, as #269 asks, and
 * keeps an editable copy of the budgets. `save` touches the budgets,
 * `setEnabled` the on/off switch, which applies at once; `reset` drops both.
 * The server's other facts change with the environment and a restart.
 */
export const useMcpConfigStore = defineStore('mcp-config', () => {
  const view = ref<McpConfigView | null>(null)
  const server = ref<McpServerView | null>(null)
  const form = reactive({ maxRounds: 5, maxReadTokens: 4000, studioBaseUrl: '' })
  const loading = ref(false)
  const saving = ref(false)
  const loadError = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  const switchError = ref<string | null>(null)

  /** `/mcp` answers right now: mounted at boot, and not turned off here. */
  const serving = computed(() => Boolean(server.value?.enabled && view.value?.enabled))

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
          enabled: view.value?.enabled ?? true,
        }),
      'Failed to save MCP config',
    )
  }

  /**
   * Turn the mounted server on or off. Applies at once, with the saved
   * budgets, and leaves unsaved edits in the form as they are.
   */
  async function setEnabled(on: boolean): Promise<boolean> {
    const current = view.value
    if (!current) return false
    if (current.enabled === on) return true
    saving.value = true
    switchError.value = null
    try {
      view.value = await putMcpConfig({
        maxRounds: current.maxRounds,
        maxReadTokens: current.maxReadTokens,
        studioBaseUrl: current.studioBaseUrl,
        enabled: on,
      })
      return true
    } catch (e) {
      switchError.value = message(e, 'Failed to switch the MCP server')
      return false
    } finally {
      saving.value = false
    }
  }

  function reset(): Promise<boolean> {
    return write(resetMcpConfig, 'Failed to reset MCP config')
  }

  return {
    view,
    server,
    form,
    dirty,
    serving,
    loading,
    saving,
    loadError,
    saveError,
    switchError,
    load,
    save,
    setEnabled,
    reset,
  }
})

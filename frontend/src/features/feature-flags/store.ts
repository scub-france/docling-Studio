import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '../../shared/api/http'
import { appMaxFileSizeMb, appMaxPageCount } from '../../shared/appConfig'

type ConversionEngine = 'local' | 'remote'
type DeploymentMode = 'self-hosted' | 'huggingface'

interface HealthResponse {
  status: string
  version?: string
  engine: ConversionEngine
  deploymentMode?: DeploymentMode
  maxPageCount?: number
  maxFileSizeMb?: number
  ingestionAvailable?: boolean
  reasoningAvailable?: boolean
  // 0.6.0 — Doc workspace mode flags (#210). Optional so an older backend
  // image without these fields keeps working: missing → fall back to true.
  inspectModeEnabled?: boolean
  chunksModeEnabled?: boolean
  askModeEnabled?: boolean
}

export type FeatureFlag =
  | 'chunking'
  | 'disclaimer'
  | 'ingestion'
  | 'reasoning'
  | 'inspectMode'
  | 'chunksMode'
  | 'askMode'

interface FeatureFlagDef {
  description: string
  isEnabled: (ctx: FeatureFlagContext) => boolean
}

interface FeatureFlagContext {
  engine: ConversionEngine | null
  deploymentMode: DeploymentMode | null
  ingestionAvailable: boolean
  reasoningAvailable: boolean
  inspectModeEnabled: boolean
  chunksModeEnabled: boolean
  askModeEnabled: boolean
}

const featureRegistry: Record<FeatureFlag, FeatureFlagDef> = {
  chunking: {
    description: 'Document chunking for RAG preparation',
    isEnabled: (ctx) => ctx.engine !== null,
  },
  disclaimer: {
    description: 'Show shared-instance disclaimer banner',
    isEnabled: (ctx) => ctx.deploymentMode === 'huggingface',
  },
  ingestion: {
    description: 'OpenSearch ingestion pipeline (embedding + vector indexing)',
    isEnabled: (ctx) => ctx.ingestionAvailable,
  },
  reasoning: {
    // Backend-gated: `reasoningAvailable` is true on `/api/health` only when
    // `REASONING_ENABLED=true` AND docling-agent + mellea are importable.
    // Hides the sidebar entry when the runner isn't wired, instead of
    // letting the user click through to a 503.
    description: 'Reasoning trace tunnel (docling-agent ReasoningResult viewer)',
    isEnabled: (ctx) => ctx.reasoningAvailable,
  },
  // 0.6.0 — Doc workspace mode flags (#210). Each one gates a tab in the
  // doc workspace (#216 / E4) and triggers a router-level redirect when a
  // disabled mode is requested via deep link. Defaults: enabled.
  inspectMode: {
    description: 'Doc workspace Inspect mode (tree + bbox debug view)',
    isEnabled: (ctx) => ctx.inspectModeEnabled,
  },
  chunksMode: {
    description: 'Doc workspace Chunks mode (editable chunkset + push to store)',
    isEnabled: (ctx) => ctx.chunksModeEnabled,
  },
  askMode: {
    description: 'Doc workspace Ask mode (agentic reasoning over the doc)',
    isEnabled: (ctx) => ctx.askModeEnabled,
  },
}

export const useFeatureFlagStore = defineStore('feature-flags', () => {
  const engine = ref<ConversionEngine | null>(null)
  const deploymentMode = ref<DeploymentMode | null>(null)
  const maxPageCount = ref<number>(0)
  const maxFileSizeMb = ref<number>(0)
  const ingestionAvailable = ref(false)
  const reasoningAvailable = ref(false)
  // 0.6.0 — Doc workspace mode flags (#210). Default true so a backend
  // that hasn't shipped the new fields yet behaves like the legacy one.
  const inspectModeEnabled = ref(true)
  const chunksModeEnabled = ref(true)
  const askModeEnabled = ref(true)
  const appVersion = ref<string>(__APP_VERSION__)
  const loaded = ref(false)
  const error = ref<string | null>(null)

  const context = computed<FeatureFlagContext>(() => ({
    engine: engine.value,
    deploymentMode: deploymentMode.value,
    ingestionAvailable: ingestionAvailable.value,
    reasoningAvailable: reasoningAvailable.value,
    inspectModeEnabled: inspectModeEnabled.value,
    chunksModeEnabled: chunksModeEnabled.value,
    askModeEnabled: askModeEnabled.value,
  }))

  function isEnabled(flag: FeatureFlag): boolean {
    if (!loaded.value) return false
    const def = featureRegistry[flag]
    return def.isEnabled(context.value)
  }

  async function load(): Promise<void> {
    try {
      const data = await apiFetch<HealthResponse>('/api/health')
      engine.value = data.engine
      deploymentMode.value = data.deploymentMode ?? 'self-hosted'
      maxPageCount.value = data.maxPageCount ?? 0
      maxFileSizeMb.value = data.maxFileSizeMb ?? 0
      ingestionAvailable.value = data.ingestionAvailable ?? false
      reasoningAvailable.value = data.reasoningAvailable ?? false
      // 0.6.0 — fall back to true when the field is missing so a frontend
      // pointed at an older backend keeps every mode visible.
      inspectModeEnabled.value = data.inspectModeEnabled ?? true
      chunksModeEnabled.value = data.chunksModeEnabled ?? true
      askModeEnabled.value = data.askModeEnabled ?? true
      appMaxFileSizeMb.value = maxFileSizeMb.value
      appMaxPageCount.value = maxPageCount.value
      if (data.version) appVersion.value = data.version
      loaded.value = true
      error.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load feature flags'
      loaded.value = true
    }
  }

  /**
   * Convenience accessor for `resolveMode` — returns the three doc
   * workspace mode flags as a `Record<DocMode, boolean>` so the routing
   * guard does not need to know about the FeatureFlag union.
   */
  function modeFlags(): { ask: boolean; inspect: boolean; chunks: boolean } {
    return {
      ask: askModeEnabled.value,
      inspect: inspectModeEnabled.value,
      chunks: chunksModeEnabled.value,
    }
  }

  return {
    engine,
    deploymentMode,
    maxPageCount,
    maxFileSizeMb,
    ingestionAvailable,
    reasoningAvailable,
    inspectModeEnabled,
    chunksModeEnabled,
    askModeEnabled,
    appVersion,
    loaded,
    error,
    isEnabled,
    modeFlags,
    load,
  }
})

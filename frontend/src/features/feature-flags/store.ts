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
  // 0.6.1 — Surface master flags (#257). Optional for backward compat:
  // studio defaults to false (production target), rag pipeline to true.
  studioModeEnabled?: boolean
  ragPipelineEnabled?: boolean
  // 0.6.0 — RAG-pipeline sub-flags (#210, renamed in #257). Optional so an
  // older backend image without these fields keeps working: missing → true.
  inspectModeEnabled?: boolean
  linkedModeEnabled?: boolean
  askModeEnabled?: boolean
}

export type FeatureFlag =
  | 'chunking'
  | 'disclaimer'
  | 'ingestion'
  | 'reasoning'
  | 'studioMode'
  | 'ragPipeline'
  | 'inspectMode'
  | 'linkedMode'
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
  studioModeEnabled: boolean
  ragPipelineEnabled: boolean
  inspectModeEnabled: boolean
  linkedModeEnabled: boolean
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
  // 0.6.1 — Surface master flags (#257). Select which UI surface(s) are
  // exposed; at least one must be on (validated server-side too).
  studioMode: {
    description: 'Legacy Studio surface (OCR debug, original 0.5.x UI)',
    isEnabled: (ctx) => ctx.studioModeEnabled,
  },
  ragPipeline: {
    description: 'New doc-centric RAG ingestion + visualization pipeline',
    isEnabled: (ctx) => ctx.ragPipelineEnabled,
  },
  // 0.6.0 — RAG-pipeline sub-flags (#210, renamed in #257). Each gates a
  // mode inside the doc workspace and triggers a router-level redirect
  // when a disabled mode is requested via deep link. Effective only when
  // ragPipeline is enabled.
  inspectMode: {
    description: 'Doc workspace Inspect mode (tree + bbox debug view)',
    isEnabled: (ctx) => ctx.ragPipelineEnabled && ctx.inspectModeEnabled,
  },
  linkedMode: {
    description: 'Doc workspace Linked mode (preview + aligned chunks panel)',
    isEnabled: (ctx) => ctx.ragPipelineEnabled && ctx.linkedModeEnabled,
  },
  askMode: {
    description: 'Doc workspace Ask mode (agentic reasoning over the doc)',
    isEnabled: (ctx) => ctx.ragPipelineEnabled && ctx.askModeEnabled,
  },
}

export const useFeatureFlagStore = defineStore('feature-flags', () => {
  const engine = ref<ConversionEngine | null>(null)
  const deploymentMode = ref<DeploymentMode | null>(null)
  const maxPageCount = ref<number>(0)
  const maxFileSizeMb = ref<number>(0)
  const ingestionAvailable = ref(false)
  const reasoningAvailable = ref(false)
  // 0.6.1 — Surface master flags (#257). Defaults match production target:
  // legacy Studio off, new RAG pipeline on.
  const studioModeEnabled = ref(false)
  const ragPipelineEnabled = ref(true)
  // 0.6.0 — RAG-pipeline sub-flags (#210, renamed in #257). Default true
  // so a backend without these fields behaves like the legacy one.
  const inspectModeEnabled = ref(true)
  const linkedModeEnabled = ref(true)
  const askModeEnabled = ref(true)
  const appVersion = ref<string>(__APP_VERSION__)
  const loaded = ref(false)
  const error = ref<string | null>(null)

  const context = computed<FeatureFlagContext>(() => ({
    engine: engine.value,
    deploymentMode: deploymentMode.value,
    ingestionAvailable: ingestionAvailable.value,
    reasoningAvailable: reasoningAvailable.value,
    studioModeEnabled: studioModeEnabled.value,
    ragPipelineEnabled: ragPipelineEnabled.value,
    inspectModeEnabled: inspectModeEnabled.value,
    linkedModeEnabled: linkedModeEnabled.value,
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
      // 0.6.1 — surface flags. Backward compat: missing studio → false
      // (production target), missing rag pipeline → true (legacy behaviour).
      studioModeEnabled.value = data.studioModeEnabled ?? false
      ragPipelineEnabled.value = data.ragPipelineEnabled ?? true
      // Sub-flags: fall back to true so an older backend keeps every mode
      // visible.
      inspectModeEnabled.value = data.inspectModeEnabled ?? true
      linkedModeEnabled.value = data.linkedModeEnabled ?? true
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
  function modeFlags(): { inspect: boolean; linked: boolean } {
    return {
      inspect: inspectModeEnabled.value,
      linked: linkedModeEnabled.value,
    }
  }

  return {
    engine,
    deploymentMode,
    maxPageCount,
    maxFileSizeMb,
    ingestionAvailable,
    reasoningAvailable,
    studioModeEnabled,
    ragPipelineEnabled,
    inspectModeEnabled,
    linkedModeEnabled,
    askModeEnabled,
    appVersion,
    loaded,
    error,
    isEnabled,
    modeFlags,
    load,
  }
})

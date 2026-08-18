/** Where an effective config value comes from: env bootstrap default or DB override. */
export type ConfigSource = 'env' | 'db'

export type ReasoningConfigField = 'enabled' | 'ollamaHost' | 'modelId' | 'maxIterations'

/** Read-only reasoning-stack diagnostics surfaced by the admin panel (#317). */
export interface ReasoningDiagnostics {
  depsPresent: boolean
  provenance: string
  available: boolean
}

/** Wire shape of GET/PUT/DELETE `/api/config/reasoning`. */
export interface ReasoningConfigView {
  enabled: boolean
  ollamaHost: string
  modelId: string
  maxIterations: number
  sources: Record<ReasoningConfigField, ConfigSource>
  providerType: string
  readOnly: boolean
  diagnostics: ReasoningDiagnostics
}

/** Body of PUT `/api/config/reasoning` — full-state replace by design (§6-B). */
export interface ReasoningConfigUpdate {
  enabled: boolean
  ollamaHost: string
  modelId: string
  maxIterations: number
}

/** Outcome of POST `/api/config/reasoning/test` — unreachable is a value, not an error. */
export interface ReasoningProbeResult {
  reachable: boolean
  models: string[]
  error: string | null
}

/** Bounds mirrored from the backend contract (`domain/app_config.py`). */
export const MAX_ITERATIONS_MIN = 1
export const MAX_ITERATIONS_MAX = 20

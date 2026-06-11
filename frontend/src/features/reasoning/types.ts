// Wire mirrors for the reasoning trace contract (#303). camelCase end-to-end
// — the backend serializes via `_CamelModel`, and `steps[].payload` keys are
// camelCase by construction in the domain `trace_builder` (the UI binds
// `payload.canAnswer`). See docs/design/303-reasoning-trace-v2-parse-view.md §7.

export type ReasoningStepKind =
  | 'plan'
  | 'retrieve'
  | 'rerank'
  | 'read'
  | 'verify'
  | 'answer'
  | 'map'

/**
 * Raw iteration fields carried alongside a step. The agent's chunkless RAG
 * loop only emits `read` steps today; `canAnswer` drives the answered/explored
 * chip, `sectionRef` is the cited element. The remaining fields are present on
 * backend-produced traces but optional here so partial fixtures stay valid.
 */
export interface ReasoningStepPayload {
  canAnswer: boolean
  iteration: number
  sectionRef?: string
  reason?: string
  sectionTextLength?: number
  response?: string
  durationMs?: number
}

export interface ReasoningStep {
  id: string
  kind: ReasoningStepKind
  title: string
  summary: string
  durationMs: number
  tokenCount: number
  citations: string[]
  payload: ReasoningStepPayload
}

export interface ReasoningTrace {
  answer: string
  converged: boolean
  steps: ReasoningStep[]
  totalDurationMs: number
  tokensIn: number
  tokensOut: number
  modelId: string
}

export type TurnStatus = 'running' | 'converged' | 'error'

/**
 * A conversation turn — the user's question plus the trace it produced.
 * `trace` is null while a turn is `running` (single-shot transport; the store
 * keeps an append-shaped path so SSE can light steps up incrementally later).
 */
export interface ConversationTurn {
  id: string
  time: string
  status: TurnStatus
  question: string
  trace: ReasoningTrace | null
  errorMessage?: string
}

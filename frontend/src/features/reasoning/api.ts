import { apiFetch } from '@/shared/api/http'
import type { ReasoningTrace } from './types'

/**
 * Run a reasoning question against a document and resolve the projected
 * `ReasoningTrace` (#303). Single-shot — the backend blocks on the agent's
 * `run_with_trace` loop and returns once it converges or hits max iterations.
 *
 * Runs typically take 20–40s depending on the model + Ollama latency; the
 * caller shows a running state.
 *
 * Errors (surfaced as thrown `Error`s by `apiFetch`):
 *  - 503 if `REASONING_ENABLED=false` server-side or docling-agent isn't installed
 *  - 400 on an empty/whitespace query
 *  - 404 if no completed analysis with `document_json` exists for the doc
 *  - 502 if the model produced no parseable answer
 *  - 500 on other failures (Ollama unreachable, model missing, …)
 */
export function runReasoning(
  docId: string,
  query: string,
  modelId?: string,
): Promise<ReasoningTrace> {
  return apiFetch<ReasoningTrace>(`/api/documents/${encodeURIComponent(docId)}/reasoning`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // camelCase wire contract — the backend DTO is `_CamelModel`.
    body: JSON.stringify({ query, modelId: modelId || undefined }),
  })
}

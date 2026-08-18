import { apiFetch } from '../../shared/api/http'
import type { ReasoningConfigUpdate, ReasoningConfigView, ReasoningProbeResult } from './types'

/**
 * Runtime reasoning config API (#317). Env vars are bootstrap defaults; the
 * backend persists overrides in SQLite and rebuilds the reasoning runner in
 * place on every write — no restart involved.
 *
 * Errors (thrown as `Error` by `apiFetch`):
 *  - 400 on invalid values (malformed host URL, empty model, out-of-bounds iterations)
 *  - 403 on a read-only deployment (`DEPLOYMENT_MODE=huggingface`)
 */

/** Effective config + per-field source (`env`/`db`) + diagnostics. */
export function getReasoningConfig(): Promise<ReasoningConfigView> {
  return apiFetch<ReasoningConfigView>('/api/config/reasoning')
}

/** Replace the override set (full-state PUT) and hot-rebuild the runner. */
export function putReasoningConfig(body: ReasoningConfigUpdate): Promise<ReasoningConfigView> {
  return apiFetch<ReasoningConfigView>('/api/config/reasoning', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

/** Drop the persisted overrides — environment defaults become effective again. */
export function resetReasoningConfig(): Promise<ReasoningConfigView> {
  return apiFetch<ReasoningConfigView>('/api/config/reasoning', { method: 'DELETE' })
}

/**
 * Probe an Ollama host. An unreachable host resolves normally with
 * `reachable: false` — only a malformed URL rejects (400), or 403 read-only.
 */
export function testReasoningConnection(host: string): Promise<ReasoningProbeResult> {
  return apiFetch<ReasoningProbeResult>('/api/config/reasoning/test', {
    method: 'POST',
    body: JSON.stringify({ host }),
  })
}

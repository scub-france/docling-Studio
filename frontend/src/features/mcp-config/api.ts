import { apiFetch } from '@/shared/api/http'
import type { McpConfigUpdate, McpConfigView, McpServerView } from './types'

/**
 * MCP admin API (#364). Two aggregates, one route family each (#269): the
 * runtime budgets under `/api/config/mcp` (env defaults, SQLite overrides,
 * applied on the next tool call) and the running server under `/api/mcp/server`
 * (read-only, fixed until the next start).
 *
 * Errors (thrown as `Error` by `apiFetch`):
 *  - 400 on invalid values (out-of-bounds caps, malformed base URL)
 *  - 403 on a read-only deployment (`DEPLOYMENT_MODE=huggingface`)
 */

/** Effective budgets + per-field source (`env`/`db`). */
export function getMcpConfig(): Promise<McpConfigView> {
  return apiFetch<McpConfigView>('/api/config/mcp')
}

/** Replace the override set (full-state PUT); the next tool call uses it. */
export function putMcpConfig(body: McpConfigUpdate): Promise<McpConfigView> {
  return apiFetch<McpConfigView>('/api/config/mcp', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

/** Drop the persisted overrides — environment defaults become effective again. */
export function resetMcpConfig(): Promise<McpConfigView> {
  return apiFetch<McpConfigView>('/api/config/mcp', { method: 'DELETE' })
}

/** What the running MCP transport publishes. */
export function getMcpServer(): Promise<McpServerView> {
  return apiFetch<McpServerView>('/api/mcp/server')
}

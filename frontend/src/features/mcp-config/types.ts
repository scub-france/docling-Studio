import type { ConfigSource } from '@/features/admin-config'

export type McpConfigField = 'maxRounds' | 'maxReadTokens' | 'studioBaseUrl'

/** Wire shape of GET/PUT/DELETE `/api/config/mcp` (#364). */
export interface McpConfigView {
  maxRounds: number
  maxReadTokens: number
  studioBaseUrl: string
  sources: Record<McpConfigField, ConfigSource>
  readOnly: boolean
}

/** Body of PUT `/api/config/mcp` — full-state replace, like reasoning. */
export interface McpConfigUpdate {
  maxRounds: number
  maxReadTokens: number
  studioBaseUrl: string
}

/** Who may call a tool: the model, a card's own fetch (`app`), or both. */
export type McpVisibility = 'model' | 'app'

export interface McpTool {
  name: string
  visibility: McpVisibility[]
  /** True when the tool renders an MCP Apps card. */
  card: boolean
}

/** Wire shape of GET `/api/mcp/server` — the transport as mounted at boot. */
export interface McpServerView {
  enabled: boolean
  path: string
  allowedHosts: string[]
  appsEnabled: boolean
  citationCard: boolean
  tools: McpTool[]
  prompts: string[]
}

/** Bounds mirrored from the backend contract (`domain/mcp_config.py`). */
export const MAX_ROUNDS_MIN = 1
export const MAX_ROUNDS_MAX = 20
export const READ_TOKENS_MIN = 100
export const READ_TOKENS_MAX = 32000

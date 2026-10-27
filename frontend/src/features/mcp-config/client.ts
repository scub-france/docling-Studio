import type { McpTool } from './types'

/**
 * Client-side helpers for the MCP section (#364): the URL a client should use
 * and the config blocks to paste. Built here rather than served by the backend
 * — they are a rendering of two facts the API already gives (#269).
 */

/** The server name clients register Docling Studio under. */
export const MCP_SERVER_NAME = 'docling-studio'

/**
 * The URL a client should connect to. The UI's own origin is right: Vite and
 * nginx both proxy `/mcp` to the backend and keep the Host header.
 */
export function mcpClientUrl(origin: string, path: string): string {
  return origin.replace(/\/+$/, '') + path
}

/**
 * `claude_desktop_config.json` through `mcp-remote`, which bridges Claude
 * Desktop's stdio to the HTTP transport. `--allow-http` only for a plain-http
 * URL: mcp-remote refuses one otherwise.
 */
export function claudeDesktopConfig(url: string): string {
  const args = ['-y', 'mcp-remote', url]
  if (url.startsWith('http://')) args.push('--allow-http')
  args.push('--transport', 'http-only')
  return JSON.stringify({ mcpServers: { [MCP_SERVER_NAME]: { command: 'npx', args } } }, null, 2)
}

export function claudeCodeCommand(url: string): string {
  return `claude mcp add --transport http ${MCP_SERVER_NAME} ${url}`
}

/**
 * Whether `host` (`hostname:port`) passes the backend's allow-list — the same
 * rule as the MCP SDK's DNS-rebinding check: an exact match, or `name:*` for
 * any port. `*` alone disables the check.
 */
export function hostAllowed(host: string, allowedHosts: string[]): boolean {
  return allowedHosts.some((allowed) => {
    if (allowed === '*' || allowed === host) return true
    return allowed.endsWith(':*') && host.startsWith(allowed.slice(0, -1))
  })
}

export interface ToolGroups {
  /** What the model calls to read and cite. */
  loop: McpTool[]
  /** Model-callable tools that render a card. */
  cards: McpTool[]
  /** Fetches a card makes for itself; the model never sees them. */
  cardOnly: McpTool[]
}

export function groupTools(tools: McpTool[]): ToolGroups {
  const forModel = (tool: McpTool) => tool.visibility.includes('model')
  return {
    loop: tools.filter((tool) => forModel(tool) && !tool.card),
    cards: tools.filter((tool) => forModel(tool) && tool.card),
    cardOnly: tools.filter((tool) => !forModel(tool)),
  }
}

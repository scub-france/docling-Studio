import { describe, it, expect } from 'vitest'
import {
  buildClaudeCodeCommand,
  buildClaudeDesktopConfig,
  groupTools,
  isHostAllowed,
  buildMcpClientUrl,
} from './client'
import type { McpTool } from './types'

describe('buildMcpClientUrl', () => {
  it('joins the UI origin and the server path', () => {
    expect(buildMcpClientUrl('http://localhost:3000', '/mcp')).toBe('http://localhost:3000/mcp')
    expect(buildMcpClientUrl('http://localhost:3000/', '/mcp')).toBe('http://localhost:3000/mcp')
  })
})

describe('buildClaudeDesktopConfig', () => {
  it('bridges through mcp-remote, allowing plain http', () => {
    const config = JSON.parse(buildClaudeDesktopConfig('http://127.0.0.1:8000/mcp'))
    expect(config).toEqual({
      mcpServers: {
        'docling-studio': {
          command: 'npx',
          args: [
            '-y',
            'mcp-remote',
            'http://127.0.0.1:8000/mcp',
            '--allow-http',
            '--transport',
            'http-only',
          ],
        },
      },
    })
  })

  it('does not allow http for an https URL', () => {
    const args = JSON.parse(buildClaudeDesktopConfig('https://studio.example/mcp')).mcpServers[
      'docling-studio'
    ].args
    expect(args).not.toContain('--allow-http')
  })
})

describe('buildClaudeCodeCommand', () => {
  it('adds the server over http', () => {
    expect(buildClaudeCodeCommand('http://localhost:3000/mcp')).toBe(
      'claude mcp add --transport http docling-studio http://localhost:3000/mcp',
    )
  })
})

describe('isHostAllowed', () => {
  const shipped = ['127.0.0.1:*', 'localhost:*', '[::1]:*']

  it('accepts any port of a wildcard entry', () => {
    expect(isHostAllowed('localhost:3000', shipped)).toBe(true)
    expect(isHostAllowed('[::1]:8000', shipped)).toBe(true)
  })

  it('refuses a host outside the list', () => {
    expect(isHostAllowed('studio.example:3000', shipped)).toBe(false)
    expect(isHostAllowed('localhost.evil.com:3000', shipped)).toBe(false)
  })

  it('accepts an exact entry and the "*" escape hatch', () => {
    expect(isHostAllowed('studio.example', ['studio.example'])).toBe(true)
    expect(isHostAllowed('anything:1', ['*'])).toBe(true)
  })
})

describe('groupTools', () => {
  const tool = (name: string, visibility: McpTool['visibility'], card: boolean): McpTool => ({
    name,
    visibility,
    card,
  })

  it('splits loop tools, cards and card-only fetches', () => {
    const groups = groupTools([
      tool('read_element', ['model', 'app'], false),
      tool('show_sources', ['model'], true),
      tool('get_source_page', ['app'], true),
    ])
    expect(groups.loop.map((t) => t.name)).toEqual(['read_element'])
    expect(groups.cards.map((t) => t.name)).toEqual(['show_sources'])
    expect(groups.cardOnly.map((t) => t.name)).toEqual(['get_source_page'])
  })
})

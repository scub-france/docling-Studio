import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMcpConfigStore } from './store'
import type { McpConfigView, McpServerView } from './types'

const mockGet = vi.fn()
const mockPut = vi.fn()
const mockReset = vi.fn()
const mockServer = vi.fn()
vi.mock('./api', () => ({
  getMcpConfig: (...args: unknown[]) => mockGet(...args),
  putMcpConfig: (...args: unknown[]) => mockPut(...args),
  resetMcpConfig: (...args: unknown[]) => mockReset(...args),
  getMcpServer: (...args: unknown[]) => mockServer(...args),
}))

function makeView(overrides: Partial<McpConfigView> = {}): McpConfigView {
  return {
    maxRounds: 5,
    maxReadTokens: 4000,
    studioBaseUrl: '',
    sources: { maxRounds: 'env', maxReadTokens: 'env', studioBaseUrl: 'env' },
    readOnly: false,
    ...overrides,
  }
}

const SERVER: McpServerView = {
  enabled: true,
  path: '/mcp',
  allowedHosts: ['localhost:*'],
  appsEnabled: true,
  citationCard: false,
  tools: [{ name: 'read_element', visibility: ['model', 'app'], card: false }],
  prompts: ['chunkless_rag'],
}

describe('useMcpConfigStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    for (const mock of [mockGet, mockPut, mockReset, mockServer]) mock.mockReset()
    mockServer.mockResolvedValue(SERVER)
  })

  describe('load', () => {
    it('loads the budgets and the server, and mirrors the budgets into the form', async () => {
      mockGet.mockResolvedValue(makeView({ maxRounds: 3 }))
      const store = useMcpConfigStore()

      await store.load()

      expect(store.view?.maxRounds).toBe(3)
      expect(store.form.maxRounds).toBe(3)
      expect(store.server).toEqual(SERVER)
      expect(store.dirty).toBe(false)
      expect(store.loadError).toBeNull()
    })

    it('reports a failure of either read', async () => {
      mockGet.mockResolvedValue(makeView())
      mockServer.mockRejectedValue(new Error('503: MCP config service not available'))
      const store = useMcpConfigStore()

      await store.load()

      expect(store.loadError).toBe('503: MCP config service not available')
      expect(store.loading).toBe(false)
    })
  })

  describe('dirty', () => {
    it('ignores surrounding spaces in the base URL', async () => {
      mockGet.mockResolvedValue(makeView({ studioBaseUrl: 'http://h' }))
      const store = useMcpConfigStore()
      await store.load()

      store.form.studioBaseUrl = '  http://h  '
      expect(store.dirty).toBe(false)

      store.form.maxReadTokens = 1500
      expect(store.dirty).toBe(true)
    })
  })

  describe('save', () => {
    it('sends the full form, trimmed, and adopts the answer', async () => {
      mockGet.mockResolvedValue(makeView())
      const saved = makeView({
        maxReadTokens: 1500,
        studioBaseUrl: 'http://h',
        sources: { maxRounds: 'db', maxReadTokens: 'db', studioBaseUrl: 'db' },
      })
      mockPut.mockResolvedValue(saved)
      const store = useMcpConfigStore()
      await store.load()
      store.form.maxReadTokens = 1500
      store.form.studioBaseUrl = ' http://h '

      expect(await store.save()).toBe(true)

      expect(mockPut).toHaveBeenCalledWith({
        maxRounds: 5,
        maxReadTokens: 1500,
        studioBaseUrl: 'http://h',
      })
      expect(store.view).toEqual(saved)
      expect(store.dirty).toBe(false)
    })

    it('keeps the form and reports the refusal', async () => {
      mockGet.mockResolvedValue(makeView())
      mockPut.mockRejectedValue(new Error('400: max_rounds must be between 1 and 20 (got 0)'))
      const store = useMcpConfigStore()
      await store.load()
      store.form.maxRounds = 0

      expect(await store.save()).toBe(false)

      expect(store.saveError).toContain('max_rounds')
      expect(store.form.maxRounds).toBe(0)
      expect(store.saving).toBe(false)
    })
  })

  describe('reset', () => {
    it('adopts the environment values', async () => {
      mockGet.mockResolvedValue(makeView({ maxRounds: 3 }))
      mockReset.mockResolvedValue(makeView())
      const store = useMcpConfigStore()
      await store.load()

      expect(await store.reset()).toBe(true)

      expect(store.form.maxRounds).toBe(5)
      expect(store.view?.sources.maxRounds).toBe('env')
    })

    it('reports a read-only refusal', async () => {
      mockGet.mockResolvedValue(makeView({ readOnly: true }))
      mockReset.mockRejectedValue(new Error('403: read-only'))
      const store = useMcpConfigStore()
      await store.load()

      expect(await store.reset()).toBe(false)
      expect(store.saveError).toBe('403: read-only')
    })
  })
})

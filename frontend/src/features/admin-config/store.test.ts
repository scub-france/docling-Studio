import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAdminConfigStore } from './store'
import type { ReasoningConfigView } from './types'

const mockGet = vi.fn()
const mockPut = vi.fn()
const mockReset = vi.fn()
const mockTest = vi.fn()
vi.mock('./api', () => ({
  getReasoningConfig: (...args: unknown[]) => mockGet(...args),
  putReasoningConfig: (...args: unknown[]) => mockPut(...args),
  resetReasoningConfig: (...args: unknown[]) => mockReset(...args),
  testReasoningConnection: (...args: unknown[]) => mockTest(...args),
}))

const mockReload = vi.fn()
vi.mock('../feature-flags/store', () => ({
  useFeatureFlagStore: () => ({ reload: mockReload }),
}))

function makeView(overrides: Partial<ReasoningConfigView> = {}): ReasoningConfigView {
  return {
    enabled: false,
    ollamaHost: 'http://env-host:11434',
    modelId: 'env-model:7b',
    maxIterations: 5,
    sources: { enabled: 'env', ollamaHost: 'env', modelId: 'env', maxIterations: 'env' },
    providerType: 'ollama',
    readOnly: false,
    diagnostics: { depsPresent: true, provenance: 'docling-agent 0.6.0 from /x', available: false },
    ...overrides,
  }
}

describe('useAdminConfigStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
    mockPut.mockReset()
    mockReset.mockReset()
    mockTest.mockReset()
    mockReload.mockReset()
    mockReload.mockResolvedValue(undefined)
  })

  describe('load', () => {
    it('populates the view and mirrors it into the form', async () => {
      mockGet.mockResolvedValue(makeView({ enabled: true, modelId: 'granite3.3:8b' }))
      const store = useAdminConfigStore()

      await store.load()

      expect(store.view?.modelId).toBe('granite3.3:8b')
      expect(store.form.enabled).toBe(true)
      expect(store.form.modelId).toBe('granite3.3:8b')
      expect(store.loadError).toBeNull()
      expect(store.dirty).toBe(false)
    })

    it('surfaces a load error and keeps the view empty', async () => {
      mockGet.mockRejectedValue(new Error('503: down'))
      const store = useAdminConfigStore()

      await store.load()

      expect(store.view).toBeNull()
      expect(store.loadError).toBe('503: down')
    })
  })

  describe('dirty', () => {
    it('is false without a view, true once the form diverges', async () => {
      const store = useAdminConfigStore()
      expect(store.dirty).toBe(false)

      mockGet.mockResolvedValue(makeView())
      await store.load()
      expect(store.dirty).toBe(false)

      store.form.maxIterations = 9
      expect(store.dirty).toBe(true)
    })
  })

  describe('save', () => {
    it('PUTs the trimmed form, applies the response, reloads feature flags', async () => {
      mockGet.mockResolvedValue(makeView())
      const saved = makeView({
        enabled: true,
        ollamaHost: 'http://new:11434',
        sources: { enabled: 'db', ollamaHost: 'db', modelId: 'db', maxIterations: 'db' },
      })
      mockPut.mockResolvedValue(saved)
      const store = useAdminConfigStore()
      await store.load()

      store.form.enabled = true
      store.form.ollamaHost = '  http://new:11434  '
      const ok = await store.save()

      expect(ok).toBe(true)
      expect(mockPut).toHaveBeenCalledWith({
        enabled: true,
        ollamaHost: 'http://new:11434',
        modelId: 'env-model:7b',
        maxIterations: 5,
      })
      expect(store.view?.sources.enabled).toBe('db')
      expect(mockReload).toHaveBeenCalledTimes(1)
      expect(store.saveError).toBeNull()
    })

    it('surfaces the save error and does not reload feature flags', async () => {
      mockGet.mockResolvedValue(makeView())
      mockPut.mockRejectedValue(new Error('400: max_iterations must be between 1 and 20'))
      const store = useAdminConfigStore()
      await store.load()

      const ok = await store.save()

      expect(ok).toBe(false)
      expect(store.saveError).toContain('max_iterations')
      expect(mockReload).not.toHaveBeenCalled()
    })
  })

  describe('reset', () => {
    it('applies the env view and reloads feature flags', async () => {
      mockGet.mockResolvedValue(
        makeView({
          enabled: true,
          sources: { enabled: 'db', ollamaHost: 'db', modelId: 'db', maxIterations: 'db' },
        }),
      )
      mockReset.mockResolvedValue(makeView())
      const store = useAdminConfigStore()
      await store.load()

      const ok = await store.reset()

      expect(ok).toBe(true)
      expect(store.form.enabled).toBe(false)
      expect(store.view?.sources.enabled).toBe('env')
      expect(mockReload).toHaveBeenCalledTimes(1)
    })

    it('surfaces a 403 on read-only deployments', async () => {
      mockGet.mockResolvedValue(makeView({ readOnly: true }))
      mockReset.mockRejectedValue(new Error('403: read-only'))
      const store = useAdminConfigStore()
      await store.load()

      const ok = await store.reset()

      expect(ok).toBe(false)
      expect(store.saveError).toContain('403')
      expect(mockReload).not.toHaveBeenCalled()
    })
  })

  describe('testConnection', () => {
    it('probes the trimmed form host and stores the result', async () => {
      mockGet.mockResolvedValue(makeView())
      mockTest.mockResolvedValue({ reachable: true, models: ['a:7b', 'b:8b'], error: null })
      const store = useAdminConfigStore()
      await store.load()

      store.form.ollamaHost = ' http://probe:11434 '
      await store.testConnection()

      expect(mockTest).toHaveBeenCalledWith('http://probe:11434')
      expect(store.testResult?.reachable).toBe(true)
      expect(store.testResult?.models).toEqual(['a:7b', 'b:8b'])
    })

    it('maps a thrown probe error onto an unreachable result', async () => {
      mockTest.mockRejectedValue(new Error('400: ollama_host must be an http(s) URL'))
      const store = useAdminConfigStore()

      await store.testConnection()

      expect(store.testResult?.reachable).toBe(false)
      expect(store.testResult?.error).toContain('http(s)')
    })
  })
})

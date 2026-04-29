import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFeatureFlagStore } from './store'

const mockApiFetch = vi.fn()
vi.mock('../../shared/api/http', () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}))

describe('useFeatureFlagStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockApiFetch.mockReset()
  })

  it('starts unloaded with flags disabled', () => {
    const store = useFeatureFlagStore()
    expect(store.loaded).toBe(false)
    expect(store.isEnabled('chunking')).toBe(false)
    expect(store.isEnabled('disclaimer')).toBe(false)
  })

  it('enables chunking when engine is local', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.engine).toBe('local')
    expect(store.loaded).toBe(true)
    expect(store.isEnabled('chunking')).toBe(true)
  })

  it('enables chunking when engine is remote', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'remote' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.engine).toBe('remote')
    expect(store.isEnabled('chunking')).toBe(true)
  })

  it('enables disclaimer when deploymentMode is huggingface', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      deploymentMode: 'huggingface',
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.deploymentMode).toBe('huggingface')
    expect(store.isEnabled('disclaimer')).toBe(true)
  })

  it('disables disclaimer when deploymentMode is self-hosted', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      deploymentMode: 'self-hosted',
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('disclaimer')).toBe(false)
  })

  it('defaults deploymentMode to self-hosted when missing', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.deploymentMode).toBe('self-hosted')
    expect(store.isEnabled('disclaimer')).toBe(false)
  })

  it('reads maxFileSizeMb from health response', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local', maxFileSizeMb: 100 })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.maxFileSizeMb).toBe(100)
  })

  it('defaults maxFileSizeMb to 0 when missing', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.maxFileSizeMb).toBe(0)
  })

  it('enables ingestion when ingestionAvailable is true', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      ingestionAvailable: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.ingestionAvailable).toBe(true)
    expect(store.isEnabled('ingestion')).toBe(true)
  })

  it('disables ingestion when ingestionAvailable is false', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      ingestionAvailable: false,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.ingestionAvailable).toBe(false)
    expect(store.isEnabled('ingestion')).toBe(false)
  })

  it('defaults ingestionAvailable to false when missing', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.ingestionAvailable).toBe(false)
    expect(store.isEnabled('ingestion')).toBe(false)
  })

  it('enables reasoning when reasoningAvailable is true', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      reasoningAvailable: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.reasoningAvailable).toBe(true)
    expect(store.isEnabled('reasoning')).toBe(true)
  })

  it('disables reasoning when reasoningAvailable is false', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      reasoningAvailable: false,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.reasoningAvailable).toBe(false)
    expect(store.isEnabled('reasoning')).toBe(false)
  })

  it('defaults reasoningAvailable to false when missing', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.reasoningAvailable).toBe(false)
    expect(store.isEnabled('reasoning')).toBe(false)
  })

  it('handles health endpoint failure gracefully', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'))
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.loaded).toBe(true)
    expect(store.error).toBe('Network error')
    expect(store.isEnabled('chunking')).toBe(false)
    expect(store.isEnabled('disclaimer')).toBe(false)
  })

  // 0.6.0 — Doc workspace mode flags (#210).
  it('exposes inspectMode / chunksMode / askMode flags from /api/health', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      inspectModeEnabled: false,
      chunksModeEnabled: true,
      askModeEnabled: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('inspectMode')).toBe(false)
    expect(store.isEnabled('chunksMode')).toBe(true)
    expect(store.isEnabled('askMode')).toBe(true)
  })

  it('falls back to all-modes-enabled when /api/health omits the new fields', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('inspectMode')).toBe(true)
    expect(store.isEnabled('chunksMode')).toBe(true)
    expect(store.isEnabled('askMode')).toBe(true)
  })

  it('modeFlags() returns the three flags in a Record<DocMode, boolean>', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      inspectModeEnabled: true,
      chunksModeEnabled: false,
      askModeEnabled: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.modeFlags()).toEqual({ ask: true, chunks: false, inspect: true })
  })
})

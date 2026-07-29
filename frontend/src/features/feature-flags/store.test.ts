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

  // 0.6.1 — Surface master flags (#257).
  it('exposes studioMode / ragPipeline master flags from /api/health', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      studioModeEnabled: true,
      ragPipelineEnabled: false,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('studioMode')).toBe(true)
    expect(store.isEnabled('ragPipeline')).toBe(false)
  })

  it('defaults studio off, rag pipeline on when /api/health omits the fields', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('studioMode')).toBe(false)
    expect(store.isEnabled('ragPipeline')).toBe(true)
  })

  it('sub-flags require ragPipeline enabled', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      ragPipelineEnabled: false,
      inspectModeEnabled: true,
      linkedModeEnabled: true,
      askModeEnabled: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('inspectMode')).toBe(false)
    expect(store.isEnabled('linkedMode')).toBe(false)
    expect(store.isEnabled('askMode')).toBe(false)
  })

  // 0.6.0 — RAG-pipeline sub-flags (#210, renamed in #257).
  it('exposes inspectMode / linkedMode / askMode flags from /api/health', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      ragPipelineEnabled: true,
      inspectModeEnabled: false,
      linkedModeEnabled: true,
      askModeEnabled: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('inspectMode')).toBe(false)
    expect(store.isEnabled('linkedMode')).toBe(true)
    expect(store.isEnabled('askMode')).toBe(true)
  })

  it('falls back to all-modes-enabled when /api/health omits the new fields', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(store.isEnabled('inspectMode')).toBe(true)
    expect(store.isEnabled('linkedMode')).toBe(true)
    expect(store.isEnabled('askMode')).toBe(true)
  })

  it('modeFlags() maps backend flags to current DocMode keys (#264 / #225)', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      inspectModeEnabled: true,
      linkedModeEnabled: false,
      ingestionAvailable: true,
    })
    const store = useFeatureFlagStore()
    await store.load()
    // inspect_mode_enabled gates Parse, linked_mode_enabled gates Chunk.
    // Ingest is always navigable (#225) — the view itself surfaces
    // whether push actions are available.
    expect(store.modeFlags()).toEqual({ parse: true })
  })

  it('modeFlags() only exposes the Parse workspace mode', async () => {
    mockApiFetch.mockResolvedValue({
      status: 'ok',
      engine: 'local',
      inspectModeEnabled: true,
      linkedModeEnabled: true,
      ingestionAvailable: false,
    })
    const store = useFeatureFlagStore()
    await store.load()
    // The tab opens regardless; the empty-state inside informs the user.
    expect(store.modeFlags()).toEqual({ parse: true })
  })

  // load() is now called from two places — main.ts (eager warm-up) and
  // the router beforeEach guard. They must share one in-flight HTTP call
  // and a fully-loaded store must short-circuit subsequent load() calls
  // entirely. Without the dedupe each first navigation would race a
  // second /api/health fetch.
  it('dedupes concurrent load() calls — single in-flight /api/health', async () => {
    let resolveHealth: (value: unknown) => void = () => {}
    mockApiFetch.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveHealth = resolve
        }),
    )
    const store = useFeatureFlagStore()
    const p1 = store.load()
    const p2 = store.load()
    expect(mockApiFetch).toHaveBeenCalledTimes(1)
    resolveHealth({ status: 'ok', engine: 'local' })
    await Promise.all([p1, p2])
    expect(store.loaded).toBe(true)
  })

  it('returns immediately without re-fetching once loaded', async () => {
    mockApiFetch.mockResolvedValue({ status: 'ok', engine: 'local' })
    const store = useFeatureFlagStore()
    await store.load()
    expect(mockApiFetch).toHaveBeenCalledTimes(1)
    await store.load()
    expect(mockApiFetch).toHaveBeenCalledTimes(1)
  })
})

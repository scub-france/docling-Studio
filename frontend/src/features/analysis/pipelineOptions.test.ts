import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAnalysisStore } from './store'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('./api', () => ({
  fetchAnalysisSummaries: vi.fn(),
  fetchAnalysis: vi.fn(),
  createAnalysis: vi.fn(),
  deleteAnalysis: vi.fn(),
}))

import * as api from './api'

// ---------------------------------------------------------------------------
// API layer — body construction with pipeline options
// ---------------------------------------------------------------------------

describe('createAnalysis — pipeline options body construction', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset the real module to get the unmocked version
    vi.doUnmock('./api')
  })

  // We test the mock integration (store → api) separately below.
  // Here we verify the raw apiFetch call shape.

  it('sends body without pipelineOptions when null', async () => {
    const { apiFetch: realApiFetch } = await import('../../shared/api/http')
    realApiFetch.mockResolvedValue({ id: '1', status: 'PENDING' })

    const { createAnalysis: real } = await import('./api')
    await real('doc-1', null)

    expect(realApiFetch).toHaveBeenCalledWith('/api/analyses', {
      method: 'POST',
      body: JSON.stringify({ documentId: 'doc-1' }),
    })
  })

  it('sends body without pipelineOptions when undefined', async () => {
    const { apiFetch: realApiFetch } = await import('../../shared/api/http')
    realApiFetch.mockResolvedValue({ id: '1', status: 'PENDING' })

    const { createAnalysis: real } = await import('./api')
    await real('doc-1')

    expect(realApiFetch).toHaveBeenCalledWith('/api/analyses', {
      method: 'POST',
      body: JSON.stringify({ documentId: 'doc-1' }),
    })
  })

  it('includes pipelineOptions in body when provided', async () => {
    const { apiFetch: realApiFetch } = await import('../../shared/api/http')
    realApiFetch.mockResolvedValue({ id: '1', status: 'PENDING' })

    const opts = {
      do_ocr: false,
      do_table_structure: true,
      table_mode: 'fast',
      do_code_enrichment: true,
      do_formula_enrichment: false,
      do_picture_classification: false,
      do_picture_description: false,
      generate_picture_images: false,
      generate_page_images: false,
      images_scale: 1.0,
    }

    const { createAnalysis: real } = await import('./api')
    await real('doc-1', opts)

    const sentBody = JSON.parse(realApiFetch.mock.calls[0][1].body)
    expect(sentBody.documentId).toBe('doc-1')
    expect(sentBody.pipelineOptions).toEqual(opts)
  })

  it('includes only specified fields in partial options', async () => {
    const { apiFetch: realApiFetch } = await import('../../shared/api/http')
    realApiFetch.mockResolvedValue({ id: '1', status: 'PENDING' })

    const opts = { do_ocr: false }

    const { createAnalysis: real } = await import('./api')
    await real('doc-1', opts)

    const sentBody = JSON.parse(realApiFetch.mock.calls[0][1].body)
    expect(sentBody.pipelineOptions).toEqual({ do_ocr: false })
  })

  it('does not include pipelineOptions key when options is empty object treated as falsy', async () => {
    const { apiFetch: realApiFetch } = await import('../../shared/api/http')
    realApiFetch.mockResolvedValue({ id: '1', status: 'PENDING' })

    // Empty object is truthy in JS, so it SHOULD be included
    const { createAnalysis: real } = await import('./api')
    await real('doc-1', {})

    const sentBody = JSON.parse(realApiFetch.mock.calls[0][1].body)
    expect(sentBody.pipelineOptions).toEqual({})
  })
})

// ---------------------------------------------------------------------------
// Store → API integration — pipeline options forwarding
// ---------------------------------------------------------------------------

describe('useAnalysisStore — pipeline options forwarding', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('run() passes null when no options provided', async () => {
    const job = { id: 'j1', status: 'PENDING', documentId: 'd1' }
    api.createAnalysis.mockResolvedValue(job)
    api.fetchAnalysis.mockResolvedValue({ ...job, status: 'COMPLETED' })

    const store = useAnalysisStore()
    await store.run('d1')

    expect(api.createAnalysis).toHaveBeenCalledWith('d1', null, null)
    store.stopPolling()
  })

  it('run() forwards full pipeline options object', async () => {
    const job = { id: 'j1', status: 'PENDING', documentId: 'd1' }
    api.createAnalysis.mockResolvedValue(job)
    api.fetchAnalysis.mockResolvedValue({ ...job, status: 'COMPLETED' })

    const store = useAnalysisStore()
    const opts = {
      do_ocr: false,
      do_table_structure: true,
      table_mode: 'fast',
      do_code_enrichment: true,
      do_formula_enrichment: false,
      do_picture_classification: false,
      do_picture_description: true,
      generate_picture_images: true,
      generate_page_images: false,
      images_scale: 2.0,
    }
    await store.run('d1', opts)

    expect(api.createAnalysis).toHaveBeenCalledWith('d1', opts, null)
    store.stopPolling()
  })

  it('run() forwards partial pipeline options', async () => {
    const job = { id: 'j1', status: 'PENDING', documentId: 'd1' }
    api.createAnalysis.mockResolvedValue(job)
    api.fetchAnalysis.mockResolvedValue({ ...job, status: 'COMPLETED' })

    const store = useAnalysisStore()
    const opts = { do_ocr: false }
    await store.run('d1', opts)

    expect(api.createAnalysis).toHaveBeenCalledWith('d1', { do_ocr: false }, null)
    store.stopPolling()
  })

  it('run() sets running state even with pipeline options', async () => {
    const job = { id: 'j1', status: 'PENDING', documentId: 'd1' }
    api.createAnalysis.mockResolvedValue(job)

    const store = useAnalysisStore()
    const opts = { do_ocr: false, table_mode: 'fast' }
    await store.run('d1', opts)

    expect(store.running).toBe(true)
    expect(store.currentAnalysis).toEqual(job)
    store.stopPolling()
  })

  it('run() with options still triggers polling', async () => {
    const job = { id: 'j1', status: 'PENDING', documentId: 'd1' }
    api.createAnalysis.mockResolvedValue(job)
    api.fetchAnalysis.mockResolvedValue({ ...job, status: 'RUNNING' })

    const store = useAnalysisStore()
    await store.run('d1', { do_ocr: false })

    // After 2s polling should fire
    await vi.advanceTimersByTimeAsync(2000)
    expect(api.fetchAnalysis).toHaveBeenCalledWith('j1')

    // Still running
    expect(store.running).toBe(true)

    // Now complete
    api.fetchAnalysis.mockResolvedValue({ ...job, status: 'COMPLETED' })
    await vi.advanceTimersByTimeAsync(2000)
    expect(store.running).toBe(false)

    store.stopPolling()
  })

  it('run() with options handles API error gracefully', async () => {
    api.createAnalysis.mockRejectedValue(new Error('Server error'))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const store = useAnalysisStore()
    await expect(store.run('d1', { do_ocr: false })).rejects.toThrow('Server error')

    expect(store.running).toBe(false)
    expect(store.currentAnalysis).toBeNull()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createAnalysis,
  importAnalysis,
  fetchAnalysis,
  deleteAnalysis,
  fetchDocumentAnalysisSummaries,
} from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('analysis API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('createAnalysis sends POST with documentId only', async () => {
    const job = { id: '1', documentId: 'doc-1', status: 'PENDING' }
    apiFetch.mockResolvedValue(job)

    const result = await createAnalysis('doc-1')

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses', {
      method: 'POST',
      body: JSON.stringify({ documentId: 'doc-1' }),
    })
    expect(result).toEqual(job)
  })

  it('createAnalysis sends POST with pipeline options', async () => {
    const job = { id: '2', documentId: 'doc-1', status: 'PENDING' }
    apiFetch.mockResolvedValue(job)

    const options = { do_ocr: false, table_mode: 'fast', do_code_enrichment: true }
    const result = await createAnalysis('doc-1', options)

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses', {
      method: 'POST',
      body: JSON.stringify({ documentId: 'doc-1', pipelineOptions: options }),
    })
    expect(result).toEqual(job)
  })

  it('importAnalysis sends the Docling document for the selected document', async () => {
    const analysis = { id: 'imported', documentId: 'doc-1', status: 'COMPLETED' }
    const document = { schema_name: 'DoclingDocument' }
    apiFetch.mockResolvedValue(analysis)

    const result = await importAnalysis('doc-1', document)

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/import', {
      method: 'POST',
      body: JSON.stringify({ documentId: 'doc-1', document }),
    })
    expect(result).toEqual(analysis)
  })

  it('fetchAnalysis calls GET /api/analyses/:id', async () => {
    const job = { id: '42', status: 'RUNNING' }
    apiFetch.mockResolvedValue(job)

    const result = await fetchAnalysis('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/42')
    expect(result).toEqual(job)
  })

  it('deleteAnalysis calls DELETE /api/analyses/:id', async () => {
    apiFetch.mockResolvedValue(null)

    await deleteAnalysis('42')

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/42', { method: 'DELETE' })
  })

  it('fetchDocumentAnalysisSummaries filters the summaries by document', async () => {
    const summaries = [{ id: '1', documentId: 'doc 42', status: 'COMPLETED' }]
    apiFetch.mockResolvedValue(summaries)

    const result = await fetchDocumentAnalysisSummaries('doc 42')

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/summaries?documentId=doc%2042')
    expect(result).toEqual(summaries)
  })
})

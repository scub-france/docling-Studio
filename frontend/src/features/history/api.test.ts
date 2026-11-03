import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchHistory, deleteHistoryEntry } from './api'

vi.mock('../../shared/api/http', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../shared/api/http'

describe('history API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchHistory lists the summaries, not the analyses with their content', async () => {
    const summaries = [{ id: 'a1', documentFilename: 'a.pdf', status: 'COMPLETED' }]
    vi.mocked(apiFetch).mockResolvedValue(summaries)

    const result = await fetchHistory()

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/summaries')
    expect(result).toEqual(summaries)
  })

  it('deleteHistoryEntry calls DELETE /api/analyses/:id', async () => {
    vi.mocked(apiFetch).mockResolvedValue(null)

    await deleteHistoryEntry('a1')

    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/a1', { method: 'DELETE' })
  })
})

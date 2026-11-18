import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '@/shared/api/http'
import { fetchHistory } from './api'

vi.mock('@/shared/api/http', () => ({ apiFetch: vi.fn() }))

describe('history API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads lightweight analysis summaries for the list', async () => {
    const summaries = [{ id: 'a1', documentId: 'd1', status: 'COMPLETED' }]
    vi.mocked(apiFetch).mockResolvedValue(summaries)

    expect(await fetchHistory()).toEqual(summaries)
    expect(apiFetch).toHaveBeenCalledWith('/api/analyses/summaries')
  })
})

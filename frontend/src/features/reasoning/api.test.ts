import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as http from '../../shared/api/http'
import { runReasoning } from './api'

vi.mock('../../shared/api/http', () => ({ apiFetch: vi.fn() }))

describe('runReasoning', () => {
  beforeEach(() => vi.clearAllMocks())

  it('POSTs to the reasoning endpoint with a camelCase body', async () => {
    vi.mocked(http.apiFetch).mockResolvedValue({})
    await runReasoning('doc 1', 'why?', 'granite:8b')

    expect(http.apiFetch).toHaveBeenCalledTimes(1)
    const [url, opts] = vi.mocked(http.apiFetch).mock.calls[0]
    expect(url).toBe('/api/documents/doc%201/reasoning')
    expect(opts?.method).toBe('POST')
    expect(JSON.parse(opts?.body as string)).toEqual({ query: 'why?', modelId: 'granite:8b' })
  })

  it('omits modelId when not provided', async () => {
    vi.mocked(http.apiFetch).mockResolvedValue({})
    await runReasoning('d', 'q')
    const [, opts] = vi.mocked(http.apiFetch).mock.calls[0]
    expect(JSON.parse(opts?.body as string)).toEqual({ query: 'q' })
  })

  it('bubbles apiFetch errors', async () => {
    vi.mocked(http.apiFetch).mockRejectedValue(new Error('503 unavailable'))
    await expect(runReasoning('d', 'q')).rejects.toThrow('503 unavailable')
  })
})

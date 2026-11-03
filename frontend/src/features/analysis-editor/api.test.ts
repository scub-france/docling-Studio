import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../../shared/api/http'
import { previewAnalysisEdits, saveAnalysisEdits } from './api'

vi.mock('../../shared/api/http', () => ({ apiFetch: vi.fn() }))

describe('analysis editor API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('previews commands against the document editor endpoint', async () => {
    vi.mocked(apiFetch).mockResolvedValue({} as never)
    await previewAnalysisEdits('doc/1', {
      commands: [{ type: 'replaceText', elementId: 'e1', text: 'Edited' }],
      expectedAppliedThroughSequence: 3,
    })
    expect(apiFetch).toHaveBeenCalledWith('/api/documents/doc/1/analysis-edits/preview', {
      method: 'POST',
      body: JSON.stringify({
        commands: [{ type: 'replaceText', elementId: 'e1', text: 'Edited' }],
        expectedAppliedThroughSequence: 3,
      }),
      signal: undefined,
    })
  })

  it('saves commands without using the legacy analysis endpoint', async () => {
    vi.mocked(apiFetch).mockResolvedValue({} as never)
    await saveAnalysisEdits('doc-1', {
      commands: [{ type: 'moveElement', elementId: 'e1', beforeElementId: null }],
      expectedAppliedThroughSequence: 0,
    })
    expect(apiFetch).toHaveBeenCalledWith('/api/documents/doc-1/analysis-edits', {
      method: 'POST',
      body: JSON.stringify({
        commands: [{ type: 'moveElement', elementId: 'e1', beforeElementId: null }],
        expectedAppliedThroughSequence: 0,
      }),
    })
  })
})

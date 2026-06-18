import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { watch } from 'vue'
import { useDocumentStore } from '../document/store'
import * as api from './api'
import { useReasoningStore } from './store'
import type { ReasoningTrace, TurnStatus } from './types'

vi.mock('./api', () => ({ runReasoning: vi.fn() }))

function trace(overrides: Partial<ReasoningTrace> = {}): ReasoningTrace {
  return {
    answer: 'a',
    converged: true,
    totalDurationMs: 100,
    tokensIn: 0,
    tokensOut: 0,
    modelId: 'm',
    steps: [
      {
        id: 's1',
        kind: 'read',
        title: 't1',
        summary: 'x',
        durationMs: 50,
        tokenCount: 0,
        citations: ['#/texts/1'],
        payload: { canAnswer: true, iteration: 1, sectionRef: '#/texts/1' },
      },
      {
        id: 's2',
        kind: 'read',
        title: 't2',
        summary: 'y',
        durationMs: 50,
        tokenCount: 0,
        citations: ['#/texts/2'],
        payload: { canAnswer: false, iteration: 2, sectionRef: '#/texts/2' },
      },
    ],
    ...overrides,
  }
}

describe('reasoning store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('appends a running turn then finalizes with the trace and auto-selects the first step', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    const doc = useDocumentStore()

    const p = store.run('doc-1', 'q')
    expect(store.turns.length).toBe(1)
    expect(store.turns[0].status).toBe('running')
    expect(store.running).toBe(true)

    await p

    expect(store.running).toBe(false)
    expect(store.turns[0].status).toBe('converged')
    expect(store.turns[0].trace?.answer).toBe('a')
    expect(store.selectedStepId).toBe('s1')
    expect(doc.focusedRef).toBe('#/texts/1')
    expect(doc.focusTick).toBeGreaterThan(0)
  })

  it('reactively publishes the finalized status to subscribers (regression: a raw-ref turn mutation bypassed the proxy and froze the card on "running")', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    const statuses: (TurnStatus | undefined)[] = []
    // flush: 'sync' so each reactive trigger fires the callback immediately —
    // with the raw-ref bug the finalize never triggers, so 'converged' is never
    // observed even though store.turns[0].status reads back as 'converged'.
    const stop = watch(
      () => store.turns[0]?.status,
      (s) => statuses.push(s),
      { flush: 'sync' },
    )

    await store.run('doc-1', 'q')
    stop()

    expect(statuses).toContain('running')
    expect(statuses).toContain('converged')
  })

  it('sets error status + message when the run throws', async () => {
    vi.mocked(api.runReasoning).mockRejectedValue(new Error('boom'))
    const store = useReasoningStore()
    await store.run('doc-1', 'q')
    expect(store.turns[0].status).toBe('error')
    expect(store.turns[0].errorMessage).toBe('boom')
    expect(store.running).toBe(false)
  })

  it('finalizes a non-converged trace as error', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace({ converged: false }))
    const store = useReasoningStore()
    await store.run('doc-1', 'q')
    expect(store.turns[0].status).toBe('error')
  })

  it('ignores empty queries and never calls the API', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    await store.run('doc-1', '   ')
    expect(store.turns.length).toBe(0)
    expect(api.runReasoning).not.toHaveBeenCalled()
  })

  it('ignores a second run while one is already in flight (running guard)', async () => {
    let resolveFirst!: (t: ReasoningTrace) => void
    vi.mocked(api.runReasoning).mockReturnValueOnce(
      new Promise<ReasoningTrace>((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useReasoningStore()

    const first = store.run('doc-1', 'q1') // in flight — running stays true
    await store.run('doc-1', 'q2') // guarded — returns immediately, no-op

    expect(store.turns.length).toBe(1)
    expect(api.runReasoning).toHaveBeenCalledTimes(1)

    resolveFirst(trace())
    await first
    expect(store.running).toBe(false)
  })

  it('re-fires focus (tick bumps) on every selectStep, including a repeat', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    const doc = useDocumentStore()
    await store.run('doc-1', 'q')

    const t0 = doc.focusTick
    store.selectStep('s2')
    expect(doc.focusedRef).toBe('#/texts/2')
    expect(doc.focusTick).toBe(t0 + 1)

    store.selectStep('s2') // re-click the same step
    expect(doc.focusTick).toBe(t0 + 2)
  })

  it('selectTurn loads the trace and auto-selects its first step', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    await store.run('doc-1', 'q1')
    await store.run('doc-1', 'q2')
    store.selectStep('s2')

    store.selectTurn(store.turns[0].id)
    expect(store.selectedTurnId).toBe(store.turns[0].id)
    expect(store.selectedStepId).toBe('s1')
  })

  it('selectStepByCitation reverse-selects the citing step, no-op otherwise', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    await store.run('doc-1', 'q')

    store.selectStepByCitation('#/texts/2')
    expect(store.selectedStepId).toBe('s2')

    store.selectStepByCitation('#/nonexistent')
    expect(store.selectedStepId).toBe('s2') // unchanged
  })

  it('reset clears turns on doc change but not on the same doc', async () => {
    vi.mocked(api.runReasoning).mockResolvedValue(trace())
    const store = useReasoningStore()
    await store.run('doc-1', 'q')

    store.reset('doc-1')
    expect(store.turns.length).toBe(1)

    store.reset('doc-2')
    expect(store.turns.length).toBe(0)
    expect(store.selectedTurnId).toBeNull()
  })
})

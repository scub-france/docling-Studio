import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useDocumentStore } from '../document/store'
import { runReasoning } from './api'
import type { ConversationTurn, ReasoningTrace } from './types'

let turnSeq = 0

function nowHHMM(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/**
 * Reasoning feature store (#303). Owns the conversation (turns) and the step
 * selection; citation focus is delegated to the shared document store so the
 * PDF preview, structure tree and properties panel all react. Lives outside
 * `DocParseTab` (which remounts on every Parse↔Chunk switch) so trace state
 * survives mode switches.
 */
export const useReasoningStore = defineStore('reasoning', () => {
  const documentStore = useDocumentStore()

  const docId = ref<string | null>(null)
  const turns = ref<ConversationTurn[]>([])
  const selectedTurnId = ref<string | null>(null)
  const selectedStepId = ref<string | null>(null)
  const running = ref(false)

  /** Trace of the currently-selected turn (what the timeline renders). */
  const activeTrace = computed<ReasoningTrace | null>(
    () => turns.value.find((t) => t.id === selectedTurnId.value)?.trace ?? null,
  )

  /** Reset conversation state when the workspace document changes. No-op when
   * the doc is unchanged, so Parse↔Chunk remounts keep the history. */
  function reset(id: string | null): void {
    if (docId.value === id) return
    docId.value = id
    turns.value = []
    selectedTurnId.value = null
    selectedStepId.value = null
    running.value = false
  }

  /** Select a step and focus its first citation through the shared store. The
   * focus tick bumps on every call, so re-clicking the same step re-scrolls. */
  function selectStep(stepId: string | null): void {
    selectedStepId.value = stepId
    if (!stepId) {
      documentStore.focusElement(null)
      return
    }
    const step = activeTrace.value?.steps.find((s) => s.id === stepId)
    documentStore.focusElement(step?.citations[0] ?? null)
  }

  /** Load a turn's trace into the timeline and auto-select its first step. */
  function selectTurn(id: string): void {
    const turn = turns.value.find((t) => t.id === id)
    if (!turn) return
    selectedTurnId.value = id
    const first = turn.trace?.steps[0]
    selectStep(first ? first.id : null)
  }

  /** Reverse path: a bbox/tree click selects the step in the active trace that
   * cites `ref_`. No-op (keeps the current selection) when none cites it. */
  function selectStepByCitation(ref_: string | null): void {
    if (!ref_) return
    const step = activeTrace.value?.steps.find((s) => s.citations.includes(ref_))
    if (step) selectedStepId.value = step.id
  }

  /** Run a question: append a running turn, await the trace, finalize, and
   * auto-select the first step so the PDF/tree/properties light up. */
  async function run(id: string, query: string, modelOverride?: string): Promise<void> {
    const q = query.trim()
    if (!q || running.value) return
    docId.value = id
    const turn: ConversationTurn = {
      id: `turn-${++turnSeq}`,
      time: nowHHMM(),
      status: 'running',
      question: q,
      trace: null,
    }
    turns.value.push(turn)
    selectedTurnId.value = turn.id
    selectedStepId.value = null
    running.value = true
    try {
      const trace = await runReasoning(id, q, modelOverride)
      turn.trace = trace
      turn.status = trace.converged ? 'converged' : 'error'
      const first = trace.steps[0]
      selectStep(first ? first.id : null)
    } catch (e) {
      turn.status = 'error'
      turn.errorMessage = (e as Error).message || 'Reasoning run failed'
    } finally {
      running.value = false
    }
  }

  return {
    docId,
    turns,
    selectedTurnId,
    selectedStepId,
    running,
    activeTrace,
    reset,
    run,
    selectTurn,
    selectStep,
    selectStepByCitation,
  }
})

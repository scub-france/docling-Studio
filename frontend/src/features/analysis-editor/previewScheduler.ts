/**
 * Timing of the editor preview: one debounced run waiting at a time, and one
 * request in flight, which a newer request or a cancel aborts.
 *
 * The scheduler only owns the timer and the abort controller; the store keeps
 * the preview state and decides when to run.
 */
export interface PreviewScheduler {
  /** Run `task` after the delay, replacing a run still waiting. */
  debounce(task: () => void): void
  /** Drop the waiting run, if any. */
  clearDebounce(): void
  /** Abort the request in flight and hand out the controller of a new one. */
  begin(): AbortController
  /** Whether `controller` belongs to the latest request, i.e. its result still counts. */
  isCurrent(controller: AbortController): boolean
  /** Abort the request in flight, if any. */
  abort(): void
  /** Drop the waiting run and abort the request in flight. */
  cancel(): void
}

interface SchedulerState {
  timer: ReturnType<typeof setTimeout> | null
  controller: AbortController | null
}

function clearTimer(state: SchedulerState): void {
  if (state.timer) clearTimeout(state.timer)
  state.timer = null
}

function scheduleRun(state: SchedulerState, task: () => void, delayMs: number): void {
  clearTimer(state)
  state.timer = setTimeout(() => {
    state.timer = null
    task()
  }, delayMs)
}

function startRequest(state: SchedulerState): AbortController {
  state.controller?.abort()
  state.controller = new AbortController()
  return state.controller
}

function cancelAll(state: SchedulerState): void {
  clearTimer(state)
  state.controller?.abort()
  state.controller = null
}

export function createPreviewScheduler(delayMs: number): PreviewScheduler {
  const state: SchedulerState = { timer: null, controller: null }

  return {
    debounce: (task) => scheduleRun(state, task, delayMs),
    clearDebounce: () => clearTimer(state),
    begin: () => startRequest(state),
    isCurrent: (candidate) => state.controller === candidate,
    abort: () => state.controller?.abort(),
    cancel: () => cancelAll(state),
  }
}

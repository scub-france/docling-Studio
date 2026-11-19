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

export function createPreviewScheduler(delayMs: number): PreviewScheduler {
  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null

  function clearDebounce(): void {
    if (timer) clearTimeout(timer)
    timer = null
  }

  function abort(): void {
    controller?.abort()
  }

  return {
    debounce(task) {
      clearDebounce()
      timer = setTimeout(() => {
        timer = null
        task()
      }, delayMs)
    },
    clearDebounce,
    begin() {
      abort()
      controller = new AbortController()
      return controller
    },
    isCurrent(candidate) {
      return controller === candidate
    },
    abort,
    cancel() {
      clearDebounce()
      abort()
      controller = null
    },
  }
}

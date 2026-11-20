/**
 * Timing of the editor preview: one debounced run waiting at a time, and one
 * request in flight, which a newer request or a cancel aborts.
 *
 * The scheduler only owns the timer and the abort controller; the store keeps
 * the preview state and decides when to run.
 */
export class PreviewScheduler {
  private timer: ReturnType<typeof setTimeout> | null = null
  private controller: AbortController | null = null

  constructor(private readonly delayMs: number) {}

  /** Run `task` after the delay, replacing a run still waiting. */
  debounce(task: () => void): void {
    this.clearDebounce()
    this.timer = setTimeout(() => {
      this.timer = null
      task()
    }, this.delayMs)
  }

  /** Drop the waiting run, if any. */
  clearDebounce(): void {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
  }

  /** Abort the request in flight and hand out the controller of a new one. */
  begin(): AbortController {
    this.abort()
    this.controller = new AbortController()
    return this.controller
  }

  /** Whether `controller` belongs to the latest request, i.e. its result still counts. */
  isCurrent(controller: AbortController): boolean {
    return this.controller === controller
  }

  /** Abort the request in flight, if any. */
  abort(): void {
    this.controller?.abort()
  }

  /** Drop the waiting run and abort the request in flight. */
  cancel(): void {
    this.clearDebounce()
    this.abort()
    this.controller = null
  }
}

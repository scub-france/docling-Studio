import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PreviewScheduler } from './previewScheduler'

describe('preview scheduler', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('runs only the last debounced task, after the delay', () => {
    const scheduler = new PreviewScheduler(400)
    const first = vi.fn()
    const second = vi.fn()

    scheduler.debounce(first)
    vi.advanceTimersByTime(300)
    scheduler.debounce(second)
    vi.advanceTimersByTime(399)
    expect(second).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)

    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
  })

  it('drops a waiting task', () => {
    const scheduler = new PreviewScheduler(400)
    const task = vi.fn()

    scheduler.debounce(task)
    scheduler.clearDebounce()
    vi.advanceTimersByTime(1000)

    expect(task).not.toHaveBeenCalled()
  })

  it('aborts the previous request when a new one begins', () => {
    const scheduler = new PreviewScheduler(400)
    const first = scheduler.begin()
    const second = scheduler.begin()

    expect(first.signal.aborted).toBe(true)
    expect(scheduler.isCurrent(first)).toBe(false)
    expect(second.signal.aborted).toBe(false)
    expect(scheduler.isCurrent(second)).toBe(true)
  })

  it('keeps an aborted request current, but forgets it once cancelled', () => {
    const scheduler = new PreviewScheduler(400)
    const controller = scheduler.begin()

    scheduler.abort()
    expect(controller.signal.aborted).toBe(true)
    expect(scheduler.isCurrent(controller)).toBe(true)

    const task = vi.fn()
    scheduler.debounce(task)
    scheduler.cancel()
    vi.advanceTimersByTime(1000)
    expect(scheduler.isCurrent(controller)).toBe(false)
    expect(task).not.toHaveBeenCalled()
  })
})

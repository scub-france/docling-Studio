import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatRelativeTime, formatSize } from './format'

describe('formatSize', () => {
  it('returns empty string for falsy value', () => {
    expect(formatSize(null)).toBe('')
    expect(formatSize(undefined)).toBe('')
    expect(formatSize(0)).toBe('')
  })

  it('formats bytes below 1MB as KB', () => {
    expect(formatSize(512 * 1024)).toBe('512 KB')
  })

  it('formats bytes above 1MB as MB', () => {
    expect(formatSize(2.5 * 1024 * 1024)).toBe('2.5 MB')
  })
})

describe('formatRelativeTime', () => {
  const now = new Date('2025-01-01T12:00:00Z').getTime()

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(now)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns em-dash for null', () => {
    expect(formatRelativeTime(null)).toBe('—')
    expect(formatRelativeTime(undefined)).toBe('—')
  })

  it('uses seconds for recent timestamps', () => {
    const iso = new Date(now - 30_000).toISOString()
    const result = formatRelativeTime(iso, 'en')
    expect(result).toMatch(/30 seconds ago/)
  })

  it('uses minutes for timestamps 2–59 min ago', () => {
    const iso = new Date(now - 5 * 60_000).toISOString()
    const result = formatRelativeTime(iso, 'en')
    expect(result).toMatch(/5 minutes ago/)
  })

  it('uses hours for timestamps 1–23h ago', () => {
    const iso = new Date(now - 3 * 3_600_000).toISOString()
    const result = formatRelativeTime(iso, 'en')
    expect(result).toMatch(/3 hours ago/)
  })

  it('uses days for timestamps < 30 days ago', () => {
    const iso = new Date(now - 7 * 86_400_000).toISOString()
    const result = formatRelativeTime(iso, 'en')
    expect(result).toMatch(/7 days ago/)
  })

  it('uses months for older timestamps', () => {
    const iso = new Date(now - 60 * 86_400_000).toISOString()
    const result = formatRelativeTime(iso, 'en')
    expect(result).toMatch(/2 months ago/)
  })
})

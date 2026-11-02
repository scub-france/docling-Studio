import { describe, it, expect } from 'vitest'
import { createAccordion } from './accordion'

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial))
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value)
    },
  }
}

const KEY = 'docling-settings-collapsed'

function withSections(storage = memoryStorage(), defaultClosed: string[] = []) {
  const accordion = createAccordion({ storageKey: KEY, storage, defaultClosed })
  for (const id of ['general', 'mcp', 'advanced']) accordion.register(id)
  return { accordion, storage }
}

describe('createAccordion', () => {
  it('opens every section but the default-closed ones', () => {
    const { accordion } = withSections(memoryStorage(), ['advanced'])
    expect(accordion.isOpen('general')).toBe(true)
    expect(accordion.isOpen('advanced')).toBe(false)
    expect(accordion.allClosed.value).toBe(false)
  })

  it('folds and unfolds one section, and remembers it', () => {
    const { accordion, storage } = withSections()
    accordion.toggle('mcp')
    expect(accordion.isOpen('mcp')).toBe(false)
    expect(JSON.parse(storage.data.get(KEY) ?? '[]')).toEqual(['mcp'])
    accordion.toggle('mcp')
    expect(accordion.isOpen('mcp')).toBe(true)
  })

  it('folds everything, then unfolds everything', () => {
    const { accordion } = withSections(memoryStorage(), ['advanced'])
    accordion.toggleAll()
    expect(accordion.allClosed.value).toBe(true)
    expect(['general', 'mcp', 'advanced'].some((id) => accordion.isOpen(id))).toBe(false)
    accordion.toggleAll()
    expect(['general', 'mcp', 'advanced'].every((id) => accordion.isOpen(id))).toBe(true)
  })

  it('restores what the viewer folded last time over the defaults', () => {
    const storage = memoryStorage({ [KEY]: JSON.stringify(['general']) })
    const { accordion } = withSections(storage, ['advanced'])
    expect(accordion.isOpen('general')).toBe(false)
    expect(accordion.isOpen('advanced')).toBe(true)
  })

  it('falls back to the defaults on a stored value it cannot read', () => {
    const storage = memoryStorage({ [KEY]: '{"not": "a list"}' })
    const { accordion } = withSections(storage, ['advanced'])
    expect(accordion.isOpen('advanced')).toBe(false)
    expect(accordion.isOpen('general')).toBe(true)
  })

  it('works without storage, and when storage throws', () => {
    const failing = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {
        throw new Error('blocked')
      },
    }
    for (const storage of [null, failing]) {
      const accordion = createAccordion({ storageKey: KEY, storage })
      accordion.register('general')
      accordion.toggle('general')
      expect(accordion.isOpen('general')).toBe(false)
    }
  })

  it('is not all closed before any section registers', () => {
    const accordion = createAccordion({ storageKey: KEY, storage: null, defaultClosed: ['x'] })
    expect(accordion.allClosed.value).toBe(false)
  })

  it('forgets a section that unregisters', () => {
    const { accordion } = withSections()
    accordion.unregister('advanced')
    accordion.toggle('general')
    accordion.toggle('mcp')
    expect(accordion.allClosed.value).toBe(true)
  })
})

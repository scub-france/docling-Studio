import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildPendingDraftKey, readPendingDraft, writePendingDraft } from './pendingDraft'

const KEY = 'analysis-editor-pending:doc-1:analysis-1'

function stubSessionStorage(entries: [string, string][] = []): Map<string, string> {
  const values = new Map(entries)
  vi.stubGlobal('window', {
    sessionStorage: {
      setItem: (key: string, value: string) => values.set(key, value),
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
    },
  })
  return values
}

describe('pending draft storage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('keys a draft by document and base analysis, once both are known', () => {
    expect(buildPendingDraftKey('doc-1', 'analysis-1')).toBe(KEY)
    expect(buildPendingDraftKey(null, 'analysis-1')).toBeNull()
    expect(buildPendingDraftKey('doc-1', null)).toBeNull()
  })

  it('writes the commands with their sequence, and removes the draft once empty', () => {
    const values = stubSessionStorage()
    const commands = [{ type: 'deleteElement' as const, elementId: 'element-1' }]

    writePendingDraft(KEY, { expectedAppliedThroughSequence: 3, commands })
    expect(JSON.parse(values.get(KEY) ?? '')).toEqual({
      expectedAppliedThroughSequence: 3,
      commands,
    })

    writePendingDraft(KEY, { expectedAppliedThroughSequence: 3, commands: [] })
    expect(values.has(KEY)).toBe(false)
  })

  it('reads a draft only while the saved sequence matches, and drops a stale one', () => {
    const commands = [{ type: 'deleteElement', elementId: 'element-1' }]
    const values = stubSessionStorage([
      [KEY, JSON.stringify({ expectedAppliedThroughSequence: 3, commands })],
    ])

    expect(readPendingDraft(KEY, 3)).toEqual(commands)
    expect(values.has(KEY)).toBe(true)

    expect(readPendingDraft(KEY, 4)).toBeNull()
    expect(values.has(KEY)).toBe(false)
  })

  it('reads nothing from malformed or unavailable storage', () => {
    stubSessionStorage([[KEY, '{not json']])
    expect(readPendingDraft(KEY, 3)).toBeNull()

    vi.unstubAllGlobals()
    vi.stubGlobal('window', {})
    expect(readPendingDraft(KEY, 3)).toBeNull()
    const commands = [{ type: 'deleteElement' as const, elementId: 'element-1' }]
    const draft = { expectedAppliedThroughSequence: 0, commands }
    expect(() => writePendingDraft(KEY, draft)).not.toThrow()
  })
})

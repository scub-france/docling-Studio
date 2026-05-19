/**
 * Tests for the connection sub-form helpers (#279).
 *
 * Critical invariants pinned by these tests:
 *   - URI scheme validation matches the backend's contract per kind.
 *   - On edit, blank password = "keep" (undefined on the wire), not
 *     "clear" (the backend uses `""` for clear).
 *   - On create, blank password = "no password" (also undefined,
 *     because empty-string on a fresh row would seal an empty
 *     password — useless but technically distinct from null).
 *   - Empty URI / username collapse to undefined so the backend
 *     falls back to env-var defaults rather than persisting an
 *     empty string that would mask the fallback.
 */
import { describe, expect, it } from 'vitest'

import {
  buildConnectionPayloadForCreate,
  buildConnectionPayloadForUpdate,
  connectionFormFromStore,
  emptyConnectionFormState,
  validateConnectionUri,
} from './connectionForm.logic'

describe('validateConnectionUri', () => {
  it('accepts empty values regardless of kind (env fallback)', () => {
    expect(validateConnectionUri('', 'neo4j')).toBeNull()
    expect(validateConnectionUri('', 'opensearch')).toBeNull()
    expect(validateConnectionUri(null, 'neo4j')).toBeNull()
    expect(validateConnectionUri(undefined, 'opensearch')).toBeNull()
    expect(validateConnectionUri('   ', 'neo4j')).toBeNull()
  })

  it.each([
    ['bolt://x:7687', 'neo4j'],
    ['bolt+s://x:7687', 'neo4j'],
    ['bolt+ssc://x:7687', 'neo4j'],
    ['neo4j://x:7687', 'neo4j'],
    ['neo4j+s://x:7687', 'neo4j'],
    ['neo4j+ssc://x:7687', 'neo4j'],
  ] as const)('accepts Neo4j scheme %s', (uri, kind) => {
    expect(validateConnectionUri(uri, kind)).toBeNull()
  })

  it.each([
    ['http://x:9200', 'opensearch'],
    ['https://x:9200', 'opensearch'],
  ] as const)('accepts OpenSearch scheme %s', (uri, kind) => {
    expect(validateConnectionUri(uri, kind)).toBeNull()
  })

  it('rejects a bolt:// URI on an OpenSearch store', () => {
    expect(validateConnectionUri('bolt://wrong:9200', 'opensearch')).toBe(
      'invalid-opensearch-scheme',
    )
  })

  it('rejects an http:// URI on a Neo4j store', () => {
    expect(validateConnectionUri('http://wrong:7687', 'neo4j')).toBe('invalid-neo4j-scheme')
  })

  it('is case-insensitive on the scheme', () => {
    expect(validateConnectionUri('BOLT://X:7687', 'neo4j')).toBeNull()
    expect(validateConnectionUri('HTTPS://X:9200', 'opensearch')).toBeNull()
  })
})

describe('emptyConnectionFormState', () => {
  it('produces a blank state ready for the create dialog', () => {
    expect(emptyConnectionFormState()).toEqual({
      uri: '',
      username: '',
      password: '',
      clearPassword: false,
    })
  })
})

describe('connectionFormFromStore', () => {
  it('hydrates URI + username, leaves password blank', () => {
    const state = connectionFormFromStore({
      connectionUri: 'bolt://x:7687',
      connectionUsername: 'neo4j',
    })
    // Password is never echoed by the API — the field stays empty
    // until the user explicitly types or clears.
    expect(state).toEqual({
      uri: 'bolt://x:7687',
      username: 'neo4j',
      password: '',
      clearPassword: false,
    })
  })

  it('treats nulls as empty', () => {
    const state = connectionFormFromStore({
      connectionUri: null,
      connectionUsername: null,
    })
    expect(state.uri).toBe('')
    expect(state.username).toBe('')
  })
})

describe('buildConnectionPayloadForCreate', () => {
  it('forwards trimmed values', () => {
    const payload = buildConnectionPayloadForCreate({
      uri: '  bolt://x:7687  ',
      username: '  neo4j  ',
      password: 'secret',
      clearPassword: false,
    })
    expect(payload).toEqual({
      connectionUri: 'bolt://x:7687',
      connectionUsername: 'neo4j',
      connectionPassword: 'secret',
    })
  })

  it('collapses empty fields to undefined (env fallback wins)', () => {
    const payload = buildConnectionPayloadForCreate({
      uri: '',
      username: '   ',
      password: '',
      clearPassword: false,
    })
    expect(payload).toEqual({
      connectionUri: undefined,
      connectionUsername: undefined,
      connectionPassword: undefined,
    })
  })

  it('ignores clearPassword in create mode', () => {
    // Cannot "clear" a password on a store that doesn't exist yet —
    // `clearPassword: true` with no plaintext is just "no password".
    const payload = buildConnectionPayloadForCreate({
      uri: '',
      username: '',
      password: '',
      clearPassword: true,
    })
    expect(payload.connectionPassword).toBeUndefined()
  })
})

describe('buildConnectionPayloadForUpdate', () => {
  it('sends undefined for blank password (= keep existing seal)', () => {
    const payload = buildConnectionPayloadForUpdate({
      uri: 'bolt://x:7687',
      username: 'neo4j',
      password: '',
      clearPassword: false,
    })
    // No `connectionPassword` key on the wire — the backend leaves
    // the sealed column untouched.
    expect(payload.connectionPassword).toBeUndefined()
  })

  it('sends "" when clearPassword is set (= clear the seal)', () => {
    const payload = buildConnectionPayloadForUpdate({
      uri: 'bolt://x:7687',
      username: 'neo4j',
      password: '',
      clearPassword: true,
    })
    expect(payload.connectionPassword).toBe('')
  })

  it('sends the plaintext when the user typed a new value', () => {
    const payload = buildConnectionPayloadForUpdate({
      uri: 'bolt://x:7687',
      username: 'neo4j',
      password: 'rotated',
      clearPassword: false,
    })
    expect(payload.connectionPassword).toBe('rotated')
  })

  it('plaintext typed wins over clearPassword (rotation > erase)', () => {
    // Defensive: if both signals are set, the user clearly wants a
    // new password — the typed value is explicit intent, the
    // checkbox might be stale.
    const payload = buildConnectionPayloadForUpdate({
      uri: '',
      username: '',
      password: 'new-value',
      clearPassword: true,
    })
    expect(payload.connectionPassword).toBe('new-value')
  })
})

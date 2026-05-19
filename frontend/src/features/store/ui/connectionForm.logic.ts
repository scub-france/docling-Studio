/**
 * Pure helpers for the store connection sub-form (#279).
 *
 * Extracted from `StoreForm.vue` so the URI-scheme validation and
 * the tri-state password marshalling are testable without a DOM
 * (project does not ship `@vue/test-utils` / `happy-dom`).
 */
import type { StoreCreatePayload, StoreUpdatePayload } from '../api'

export const NEO4J_URI_SCHEMES = [
  'bolt://',
  'bolt+s://',
  'bolt+ssc://',
  'neo4j://',
  'neo4j+s://',
  'neo4j+ssc://',
] as const

export const OPENSEARCH_URI_SCHEMES = ['http://', 'https://'] as const

export type StoreKind = 'opensearch' | 'neo4j'

/**
 * Validate the URI against the store kind. Empty string is allowed —
 * the backend falls back to env-var defaults when the store has no
 * URI of its own. Returns null on valid input, or a short
 * machine-readable error code that the template renders via i18n.
 */
export function validateConnectionUri(
  uri: string | null | undefined,
  kind: StoreKind,
): 'invalid-neo4j-scheme' | 'invalid-opensearch-scheme' | null {
  const trimmed = (uri ?? '').trim()
  if (!trimmed) return null
  const lower = trimmed.toLowerCase()
  if (kind === 'neo4j') {
    if (!NEO4J_URI_SCHEMES.some((s) => lower.startsWith(s))) {
      return 'invalid-neo4j-scheme'
    }
  } else if (kind === 'opensearch') {
    if (!OPENSEARCH_URI_SCHEMES.some((s) => lower.startsWith(s))) {
      return 'invalid-opensearch-scheme'
    }
  }
  return null
}

export interface ConnectionFormState {
  uri: string
  username: string
  /**
   * Plaintext input. Empty in edit mode = "keep existing seal" when
   * the store has `hasConnectionPassword: true`. The marshaller
   * below translates that to undefined on the wire.
   */
  password: string
  /**
   * True when the user has explicitly cleared the password (e.g.
   * clicked a "Remove password" toggle). Distinct from "left empty"
   * because the wire contract uses `""` for clear vs undefined for
   * keep.
   */
  clearPassword: boolean
}

export function emptyConnectionFormState(): ConnectionFormState {
  return { uri: '', username: '', password: '', clearPassword: false }
}

export function connectionFormFromStore(detail: {
  connectionUri?: string | null
  connectionUsername?: string | null
}): ConnectionFormState {
  return {
    uri: detail.connectionUri ?? '',
    username: detail.connectionUsername ?? '',
    password: '',
    clearPassword: false,
  }
}

/**
 * Convert the form state into the wire payload contribution.
 *
 * Modes:
 *   - `create`: empty string → undefined (the backend defaults).
 *     Non-empty values flow as-is. `clearPassword` is ignored
 *     (create can't clear something that doesn't exist yet).
 *   - `edit`:
 *     * URI / username: trimmed value if set; undefined when blank
 *       and not explicitly cleared. The component decides when to
 *       send `null` vs undefined — we always send trimmed strings
 *       or undefined here.
 *     * password tri-state (rotation wins over erase — a typed value
 *       is intent, a checkbox might be stale):
 *         - password non-empty → send the value (replace seal)
 *         - clearPassword=true → `""` (clear the seal)
 *         - otherwise → undefined (keep existing seal)
 */
export function buildConnectionPayloadForCreate(
  state: ConnectionFormState,
): Pick<StoreCreatePayload, 'connectionUri' | 'connectionUsername' | 'connectionPassword'> {
  const uri = state.uri.trim()
  const username = state.username.trim()
  const password = state.password
  return {
    connectionUri: uri || undefined,
    connectionUsername: username || undefined,
    connectionPassword: password || undefined,
  }
}

export function buildConnectionPayloadForUpdate(
  state: ConnectionFormState,
): Pick<StoreUpdatePayload, 'connectionUri' | 'connectionUsername' | 'connectionPassword'> {
  const uri = state.uri.trim()
  const username = state.username.trim()
  let password: string | undefined
  // Rotation wins over erase: a typed value is explicit intent.
  if (state.password) {
    password = state.password
  } else if (state.clearPassword) {
    password = ''
  } else {
    password = undefined
  }
  return {
    connectionUri: uri || undefined,
    connectionUsername: username || undefined,
    connectionPassword: password,
  }
}

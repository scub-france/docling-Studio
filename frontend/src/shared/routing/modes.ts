/**
 * Doc workspace mode parsing.
 *
 * The doc workspace at `/docs/:id` exposes its content via the `?mode=`
 * query param. Anything missing or unknown resolves to the default,
 * `linked`, so a malformed URL never produces a broken page.
 *
 * #210 layers feature-flag-aware redirection on top: if the requested
 * mode is disabled for the current tenant, the router replaces it with
 * the first enabled mode (priority `linked` > `inspect`).
 *
 * #263 renames the legacy `chunks` mode to `linked` and drops `ask` from
 * the workspace (Ask is handled separately via the standalone
 * `/reasoning` page). The Compare view (#263) is rendered as a disabled
 * button in the switcher — no mode value, no route segment.
 *
 * Backward compatibility: `?mode=chunks` is accepted and silently mapped
 * to `linked` so existing bookmarks keep working.
 */

export type DocMode = 'inspect' | 'linked'

export const DEFAULT_MODE: DocMode = 'linked'
export const ALL_MODES: readonly DocMode[] = ['linked', 'inspect'] as const

const LEGACY_CHUNKS_ALIAS = 'chunks'

export function isDocMode(value: unknown): value is DocMode {
  return value === 'inspect' || value === 'linked'
}

export function parseMode(raw: unknown): DocMode {
  if (raw === LEGACY_CHUNKS_ALIAS) return 'linked'
  return isDocMode(raw) ? raw : DEFAULT_MODE
}

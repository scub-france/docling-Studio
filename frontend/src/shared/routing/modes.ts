/**
 * Doc workspace mode parsing.
 *
 * The doc workspace at `/docs/:id` exposes its content via the `?mode=`
 * query param. Anything missing or unknown resolves to the default,
 * `parse`, so a malformed URL never produces a broken page.
 *
 * #210 layers feature-flag-aware redirection on top: if the requested
 * mode is disabled for the current tenant, the router replaces it with
 * the first enabled mode (`parse`).
 *
 * Naming history:
 *   - #263 renamed `chunks` to `linked` and dropped `ask`.
 *   - #264 reshuffled views: `parse` shows the Docling extraction graph,
 *     `chunk` the chunk-centric editor.
 *   - #225 drops `compare` (was a placeholder, never shipped) and adds
 *     `ingest` (per-store push state + push-to-store actions).
 *
 * Backward compatibility: `?mode=chunks`, `?mode=linked`,
 * `?mode=inspect`, and `?mode=compare` are accepted and silently
 * mapped to their current equivalents so existing bookmarks keep
 * working.
 */

export type DocMode = 'parse'

export const DEFAULT_MODE: DocMode = 'parse'
export const ALL_MODES: readonly DocMode[] = ['parse'] as const

const LEGACY_ALIASES: Readonly<Record<string, DocMode>> = {
  // Pre-#264 names and removed workspace modes resolve to Parse.
  linked: 'parse',
  chunks: 'parse',
  inspect: 'parse',
  compare: 'parse',
  chunk: 'parse',
  ingest: 'parse',
}

export function isDocMode(value: unknown): value is DocMode {
  return value === 'parse'
}

export function parseMode(raw: unknown): DocMode {
  if (typeof raw === 'string' && raw in LEGACY_ALIASES) {
    return LEGACY_ALIASES[raw]
  }
  return isDocMode(raw) ? raw : DEFAULT_MODE
}

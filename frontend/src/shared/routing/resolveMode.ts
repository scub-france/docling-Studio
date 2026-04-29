import { type DocMode } from './modes'

/**
 * Doc workspace mode resolution under feature flags (#210).
 *
 * The router consults this when a user opens `/docs/:id?mode=<mode>`:
 *
 *   - If the requested mode is enabled, return it.
 *   - Otherwise, return the first enabled mode in `MODE_PRIORITY`.
 *   - If no mode is enabled, return `null` (the router redirects to
 *     the docs library with a flash message).
 */
export const MODE_PRIORITY: readonly DocMode[] = ['ask', 'chunks', 'inspect'] as const

export function resolveMode(
  requested: DocMode | undefined,
  enabled: Record<DocMode, boolean>,
): DocMode | null {
  if (requested && enabled[requested]) return requested
  return MODE_PRIORITY.find((m) => enabled[m]) ?? null
}

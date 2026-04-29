/**
 * Active-state matching for the sidebar.
 *
 * `Home` is active only on the exact `/` route — otherwise visiting
 * any sub-page would also light up Home. For every other entry, a
 * prefix match is used so `/docs/abc?mode=chunks` highlights `Docs`.
 *
 * Pure helper so the component file stays tiny and the rule is
 * unit-testable.
 */
export function matchesActive(path: string, prefixes: readonly string[]): boolean {
  for (const prefix of prefixes) {
    if (prefix === '/') {
      if (path === '/') return true
      continue
    }
    if (path === prefix || path.startsWith(prefix + '/') || path.startsWith(prefix + '?')) {
      return true
    }
  }
  return false
}

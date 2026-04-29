/**
 * Truncate `text` to at most `max` characters, replacing the tail with
 * an ellipsis when shortened. Returns the original string if it
 * already fits.
 *
 * Used by the breadcrumb to keep the topbar tidy when document
 * filenames are long. The full title stays available via the `title`
 * attribute on the segment so the user can hover to read it whole.
 */
export function truncate(text: string, max: number): string {
  if (max <= 0 || text.length <= max) return text
  // Reserve one character for the ellipsis so the visible length is `max`.
  return text.slice(0, Math.max(0, max - 1)).trimEnd() + '…'
}

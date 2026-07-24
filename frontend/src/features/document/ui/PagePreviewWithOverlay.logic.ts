/**
 * Pure helpers for the compact page-navigation control (#309).
 *
 * Extracted from `PagePreviewWithOverlay.vue` so the parse/clamp and
 * input-width logic is testable without a DOM (project does not ship
 * `@vue/test-utils` / `happy-dom`).
 */

/** Minimum width, in `ch`, of the editable page-number input. */
export const DEFAULT_PAGE_INPUT_SIZE = 4

/**
 * Parse and clamp a raw page-input string to a valid 1-based page index.
 *
 * Returns `null` when the input is not a finite integer (empty, blank, or
 * non-numeric) — the caller resets the field to the current page rather than
 * navigating. Otherwise the value is clamped into `[1, totalPages]`.
 *
 * Follows `Number.parseInt` semantics: a leading integer with trailing junk
 * (`'7x'`) parses to `7`, and decimals truncate (`'4.9'` → `4`).
 */
export function clampPageInput(raw: string, totalPages: number): number | null {
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed)) return null
  return Math.min(totalPages, Math.max(1, parsed))
}

/**
 * Width, in `ch`, for the page-number input: wide enough for the largest page
 * number but never below {@link DEFAULT_PAGE_INPUT_SIZE} so the field keeps a
 * stable, tap-friendly footprint on low-page documents.
 */
export function pageInputWidthCh(totalPages: number, min = DEFAULT_PAGE_INPUT_SIZE): number {
  return Math.max(min, String(totalPages).length)
}

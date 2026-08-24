/**
 * Single source of truth for OCR element type → swatch color.
 *
 * Consumed by `BboxCanvas`, `LayersBar`, and `ChunksPanel` (for the type
 * badge on chunk cards). The palette mirrors the legacy `BboxOverlay`
 * mapping (Studio surface) so the same document looks consistent
 * across both surfaces.
 *
 * The "Unknown" / fallback color is exposed separately so callers can
 * decide whether to render unknown types at all (e.g. ignore them in
 * the LAYERS bar, but still draw the bbox in muted gray).
 */

export const ELEMENT_COLORS: Readonly<Record<string, string>> = Object.freeze({
  title: '#EF4444',
  section_header: '#F97316',
  text: '#3B82F6',
  table: '#8B5CF6',
  picture: '#22C55E',
  list: '#06B6D4',
  formula: '#EC4899',
  code: '#14B8A6',
  caption: '#EAB308',
})

export const UNKNOWN_ELEMENT_COLOR = '#94A3B8'

/**
 * Lookup helper — returns the palette color for `type`, falling back to
 * `UNKNOWN_ELEMENT_COLOR` so callers never have to handle `undefined`.
 */
export function colorFor(type: string): string {
  return ELEMENT_COLORS[type] ?? UNKNOWN_ELEMENT_COLOR
}

/**
 * Layer order shown in the LAYERS bar (mockup-driven). Types not in
 * this list are appended in insertion order from the page's elements.
 */
export const LAYER_ORDER: readonly string[] = [
  'section_header',
  'text',
  'table',
  'picture',
  'list',
  'formula',
  'caption',
] as const

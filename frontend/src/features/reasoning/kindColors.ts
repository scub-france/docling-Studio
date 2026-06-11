// Step-kind palette for the trace timeline (#303).
//
// Single source of truth: the canonical OCR element palette in
// `features/document/elementColors.ts`. Each reasoning kind borrows the base
// hex of the element type whose colour the handoff sampled for it. The badge
// text and the duration bar use the base hex; the badge background derives as
// a theme-safe tint via `color-mix` (works in both light and dark themes,
// unlike the handoff's light-only pastel hexes).

import { ELEMENT_COLORS } from '../document/elementColors'
import type { ReasoningStepKind } from './types'

// kind → the element type whose canonical colour it inherits.
const KIND_TO_ELEMENT: Readonly<Record<ReasoningStepKind, string>> = {
  plan: 'table', // violet  #8B5CF6
  retrieve: 'text', // blue    #3B82F6
  rerank: 'caption', // amber   #EAB308
  read: 'section_header', // orange  #F97316
  verify: 'list', // cyan    #06B6D4
  answer: 'picture', // green   #22C55E
  map: 'formula', // pink    #EC4899
}

export interface KindColor {
  /** Badge text + duration bar — the base hex. */
  fg: string
  /** Badge background — a theme-safe tint of the base hex. */
  bg: string
}

/** Base hex for a kind (badge text / bar). */
export function kindBaseColor(kind: ReasoningStepKind): string {
  return ELEMENT_COLORS[KIND_TO_ELEMENT[kind]] ?? ELEMENT_COLORS.section_header
}

/** Full colour pair for a kind badge. */
export function kindColor(kind: ReasoningStepKind): KindColor {
  const base = kindBaseColor(kind)
  return {
    fg: base,
    bg: `color-mix(in srgb, ${base} 15%, transparent)`,
  }
}

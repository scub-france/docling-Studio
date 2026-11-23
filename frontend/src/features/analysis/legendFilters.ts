/**
 * Declarative definition of GraphView's legend chips.
 *
 * Each chip maps to (a) a swatch color shown in the toolbar, and (b) a
 * predicate that decides whether a given node is "of that kind". Clicking a
 * chip toggles the matching nodes' visibility via the `.hidden` Cytoscape
 * class — pure function kept here so it's unit-testable without mounting
 * the component or spinning up Cytoscape.
 */

import type { GraphNode } from './graphApi'

export interface LegendChip {
  /** Stable ID used as the key in the `hiddenChips` Set + as a CSS slug. */
  key: string
  /** Display label shown in the chip. Kept English for now — matches
   * existing `legend-*` class names that the design stylesheet targets. */
  label: string
  /** Swatch color (also used for the CSS class `legend-${key}`). */
  color: string
  /** Returns true when a node belongs to this chip's category. */
  match: (node: GraphNode) => boolean
}

/**
 * Legend order matches the chips currently rendered in GraphView's toolbar,
 * so swapping to this source of truth is a drop-in replacement.
 *
 * `kindLabel` is the specific Neo4j label returned by `fetch_graph`
 * (e.g. `SectionHeader`, `Paragraph`, `Table`, …). Group-based chips target
 * the `group` attribute (document / page / chunk) — only `element` nodes
 * have a useful `kindLabel`.
 */
export const LEGEND_CHIPS: LegendChip[] = [
  {
    key: 'document',
    label: 'Document',
    color: '#1E293B',
    match: (n) => n.group === 'document',
  },
  {
    key: 'section',
    label: 'Section',
    color: '#F97316',
    match: (n) => n.group === 'element' && n.label === 'SectionHeader',
  },
  {
    key: 'paragraph',
    label: 'Paragraph',
    color: '#3B82F6',
    match: (n) => n.group === 'element' && (n.label === 'Paragraph' || n.label === 'TextElement'),
  },
  {
    key: 'table',
    label: 'Table',
    color: '#8B5CF6',
    match: (n) => n.group === 'element' && n.label === 'Table',
  },
  {
    key: 'figure',
    label: 'Figure',
    color: '#22C55E',
    match: (n) => n.group === 'element' && n.label === 'Figure',
  },
  {
    key: 'page',
    label: 'Page',
    color: '#94A3B8',
    match: (n) => n.group === 'page',
  },
  {
    key: 'chunk',
    label: 'Chunk',
    color: '#DC2626',
    match: (n) => n.group === 'chunk',
  },
]

/** Lookup by key — tiny helper to keep GraphView concise. */
export function findChip(key: string): LegendChip | undefined {
  return LEGEND_CHIPS.find((c) => c.key === key)
}

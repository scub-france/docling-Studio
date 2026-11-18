/**
 * Synthesize "section scope" compound-node parents for GraphView.
 *
 * The Docling graph is structurally flat — most elements are direct children
 * of `#/body` (HAS_ROOT) with no explicit parent relationship to the section
 * header that "owns" them in the reader's mental model. To enable the
 * expand-collapse UX per section, we derive that ownership here, at render
 * time, from the NEXT reading-order chain:
 *
 *   - Walk NEXT from the head of the chain.
 *   - Every time we hit a SectionHeader, it becomes the "current section".
 *   - Every non-SectionHeader node thereafter — unless it has an explicit
 *     PARENT_OF edge (e.g. list_item → list) — gets that section as its
 *     compound parent.
 *
 * The function returns a `Map<childId, parentId>` where both ids are full
 * Cytoscape node ids (`elem::<self_ref>`). The caller merges this with any
 * existing PARENT_OF to produce the final `data.parent` on each node.
 *
 * Edge cases handled:
 *   - No SectionHeader in the doc → returns an empty map (nothing to collapse).
 *   - Multiple disconnected NEXT chains → each is walked independently.
 *   - Explicit PARENT_OF on a child → never overridden.
 *   - SectionHeader that is itself a list_item or nested → its descendants
 *     still use it as their section anchor; the SectionHeader keeps its own
 *     explicit parent.
 */

import type { GraphEdge, GraphNode } from './graphApi'

export function computeSectionParents(
  nodes: readonly GraphNode[],
  edges: readonly GraphEdge[],
): Map<string, string> {
  const elementIds = new Set<string>()
  const kindById = new Map<string, string | undefined>()
  for (const n of nodes) {
    if (n.group !== 'element') continue
    elementIds.add(n.id)
    kindById.set(n.id, n.label)
  }
  if (elementIds.size === 0) return new Map()

  const explicitParentOf = new Set<string>()
  const nextMap = new Map<string, string>()
  const hasIncomingNext = new Set<string>()

  for (const e of edges) {
    if (!elementIds.has(e.source) || !elementIds.has(e.target)) continue
    if (e.type === 'PARENT_OF') {
      explicitParentOf.add(e.target)
    } else if (e.type === 'NEXT') {
      // Preserve first-seen NEXT edge per source (should be unique anyway).
      if (!nextMap.has(e.source)) nextMap.set(e.source, e.target)
      hasIncomingNext.add(e.target)
    }
  }

  // Walk heads deterministically (sorted) so the same graph always produces
  // the same parenting map — useful for tests and reproducible debugging.
  const heads = [...elementIds].filter((id) => !hasIncomingNext.has(id)).sort()

  const parents = new Map<string, string>()
  const visited = new Set<string>()

  for (const head of heads) {
    let currentSection: string | null = null
    let node: string | undefined = head

    while (node && !visited.has(node)) {
      visited.add(node)
      const kind = kindById.get(node)

      if (kind === 'SectionHeader') {
        currentSection = node
        // The SectionHeader itself does NOT get a synthetic parent — it is
        // the anchor. If it has an explicit PARENT_OF, that one remains
        // authoritative downstream (the merger respects it).
      } else if (currentSection && !explicitParentOf.has(node)) {
        parents.set(node, currentSection)
      }

      node = nextMap.get(node)
    }
  }

  return parents
}

/**
 * Merge an explicit PARENT_OF map with synthetic section parents. Explicit
 * wins. Produces the final `childId → parentId` map that callers set as
 * `data.parent` on Cytoscape nodes.
 */
export function mergeParentMaps(
  explicit: ReadonlyMap<string, string>,
  synthetic: ReadonlyMap<string, string>,
): Map<string, string> {
  const out = new Map(synthetic)
  for (const [child, parent] of explicit) out.set(child, parent)
  return out
}

/** Extract the explicit PARENT_OF map from the edge list — convenience. */
export function buildExplicitParentMap(edges: readonly GraphEdge[]): Map<string, string> {
  const out = new Map<string, string>()
  for (const e of edges) {
    if (e.type === 'PARENT_OF') out.set(e.target, e.source)
  }
  return out
}

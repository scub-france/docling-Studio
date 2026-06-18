import type { DocTreeNode } from '../../shared/types'

/**
 * Reveal-on-select helper for the structure tree (#303, design §337).
 *
 * When a trace step (or a bbox click) focuses an element, the tree must expand
 * the collapsed path down to it. `DocParseTab` computes the ancestor chain of
 * the focused ref once and passes it down as a `revealedRefs` set; a node forces
 * itself open when its ref is in the set. Kept pure (no Vue, no DOM) so it is
 * unit-testable — the repo has no component-mount harness, so the scroll/`open`
 * wiring lives in the components and the path computation lives here.
 */

/**
 * Refs of every *ancestor* of `targetRef` within `nodes` (the target itself is
 * excluded — it doesn't need to open to be revealed). Returns an empty set when
 * `targetRef` is null or absent from the tree.
 */
export function ancestorRefs(nodes: readonly DocTreeNode[], targetRef: string | null): Set<string> {
  const out = new Set<string>()
  if (!targetRef) return out

  const path: string[] = []
  function walk(list: readonly DocTreeNode[]): boolean {
    for (const node of list) {
      if (node.ref === targetRef) return true
      path.push(node.ref)
      if (walk(node.children)) return true
      path.pop()
    }
    return false
  }

  if (walk(nodes)) for (const ref of path) out.add(ref)
  return out
}

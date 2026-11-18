import { describe, expect, it } from 'vitest'
import type { DocTreeNode } from '../../shared/types'
import { collectAncestorRefs } from './treeReveal'

function node(ref: string, children: DocTreeNode[] = []): DocTreeNode {
  return { ref, type: 'text', label: ref, children }
}

// #/body
//   ├─ #/texts/1
//   └─ #/groups/0
//        └─ #/texts/2
//             └─ #/texts/3
const tree = [
  node('#/body', [node('#/texts/1'), node('#/groups/0', [node('#/texts/2', [node('#/texts/3')])])]),
]

describe('collectAncestorRefs', () => {
  it('returns the full ancestor chain of a deeply nested ref (target excluded)', () => {
    expect(collectAncestorRefs(tree, '#/texts/3')).toEqual(
      new Set(['#/body', '#/groups/0', '#/texts/2']),
    )
  })

  it('returns the single parent for a shallow ref', () => {
    expect(collectAncestorRefs(tree, '#/texts/1')).toEqual(new Set(['#/body']))
  })

  it('returns an empty set for a root node (no ancestors)', () => {
    expect(collectAncestorRefs(tree, '#/body')).toEqual(new Set())
  })

  it('returns an empty set for an unknown ref', () => {
    expect(collectAncestorRefs(tree, '#/tables/9')).toEqual(new Set())
  })

  it('returns an empty set for a null target', () => {
    expect(collectAncestorRefs(tree, null)).toEqual(new Set())
  })

  it('does not include sibling-branch refs', () => {
    // #/texts/1 is a sibling of #/groups/0 — must not leak into the chain.
    expect(collectAncestorRefs(tree, '#/texts/2')).not.toContain('#/texts/1')
  })
})

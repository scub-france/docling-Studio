import { describe, expect, it } from 'vitest'

import type { GraphEdge, GraphNode } from './graphApi'
import { computeSectionParents, buildExplicitParentMap, mergeParentMaps } from './sectionParenting'

function el(selfRef: string, label: string): GraphNode {
  return {
    id: `elem::${selfRef}`,
    group: 'element',
    label,
    self_ref: selfRef,
  }
}

function nextEdge(from: string, to: string): GraphEdge {
  return {
    id: `NEXT::elem::${from}::elem::${to}`,
    source: `elem::${from}`,
    target: `elem::${to}`,
    type: 'NEXT',
  }
}

function parentEdge(parent: string, child: string): GraphEdge {
  return {
    id: `PARENT_OF::elem::${parent}::elem::${child}`,
    source: `elem::${parent}`,
    target: `elem::${child}`,
    type: 'PARENT_OF',
  }
}

describe('computeSectionParents', () => {
  it('returns empty when no SectionHeader exists', () => {
    const nodes = [el('#/texts/0', 'Paragraph'), el('#/texts/1', 'Paragraph')]
    const edges = [nextEdge('#/texts/0', '#/texts/1')]
    expect(computeSectionParents(nodes, edges)).toEqual(new Map())
  })

  it('parents every element to the preceding SectionHeader', () => {
    // SH ─▶ P ─▶ P ─▶ SH ─▶ P
    const nodes = [
      el('#/texts/0', 'SectionHeader'),
      el('#/texts/1', 'Paragraph'),
      el('#/texts/2', 'Paragraph'),
      el('#/texts/3', 'SectionHeader'),
      el('#/texts/4', 'Paragraph'),
    ]
    const edges = [
      nextEdge('#/texts/0', '#/texts/1'),
      nextEdge('#/texts/1', '#/texts/2'),
      nextEdge('#/texts/2', '#/texts/3'),
      nextEdge('#/texts/3', '#/texts/4'),
    ]
    const parents = computeSectionParents(nodes, edges)
    expect(parents.get('elem::#/texts/1')).toBe('elem::#/texts/0')
    expect(parents.get('elem::#/texts/2')).toBe('elem::#/texts/0')
    expect(parents.get('elem::#/texts/4')).toBe('elem::#/texts/3')
    // Headers are never themselves synthetically parented.
    expect(parents.has('elem::#/texts/0')).toBe(false)
    expect(parents.has('elem::#/texts/3')).toBe(false)
  })

  it('does not override an explicit PARENT_OF', () => {
    // SH ─▶ List ─▶ ListItem, with PARENT_OF(List, ListItem)
    const nodes = [
      el('#/texts/0', 'SectionHeader'),
      el('#/groups/0', 'List'),
      el('#/texts/1', 'ListItem'),
    ]
    const edges: GraphEdge[] = [
      nextEdge('#/texts/0', '#/groups/0'),
      nextEdge('#/groups/0', '#/texts/1'),
      parentEdge('#/groups/0', '#/texts/1'),
    ]
    const parents = computeSectionParents(nodes, edges)
    // The List falls under the section…
    expect(parents.get('elem::#/groups/0')).toBe('elem::#/texts/0')
    // …but the ListItem keeps its explicit List parent, not the section.
    expect(parents.has('elem::#/texts/1')).toBe(false)
  })

  it('leaves elements preceding the first SectionHeader unparented', () => {
    // Page-header stuff can come before any SectionHeader — don't force-parent it.
    const nodes = [
      el('#/texts/0', 'PageHeader'),
      el('#/texts/1', 'SectionHeader'),
      el('#/texts/2', 'Paragraph'),
    ]
    const edges = [nextEdge('#/texts/0', '#/texts/1'), nextEdge('#/texts/1', '#/texts/2')]
    const parents = computeSectionParents(nodes, edges)
    expect(parents.has('elem::#/texts/0')).toBe(false)
    expect(parents.get('elem::#/texts/2')).toBe('elem::#/texts/1')
  })

  it('handles multiple disconnected NEXT chains deterministically', () => {
    // Two chains, each with its own section. Heads are sorted by id so the
    // walk order is stable run-to-run.
    const nodes = [
      el('#/texts/10', 'SectionHeader'),
      el('#/texts/11', 'Paragraph'),
      el('#/texts/20', 'SectionHeader'),
      el('#/texts/21', 'Paragraph'),
    ]
    const edges = [nextEdge('#/texts/10', '#/texts/11'), nextEdge('#/texts/20', '#/texts/21')]
    const parents = computeSectionParents(nodes, edges)
    expect(parents.get('elem::#/texts/11')).toBe('elem::#/texts/10')
    expect(parents.get('elem::#/texts/21')).toBe('elem::#/texts/20')
  })
})

describe('buildExplicitParentMap + mergeParentMaps', () => {
  it('extracts explicit PARENT_OF into a child→parent map', () => {
    const edges = [parentEdge('#/groups/0', '#/texts/1')]
    const m = buildExplicitParentMap(edges)
    expect(m.get('elem::#/texts/1')).toBe('elem::#/groups/0')
  })

  it('explicit wins over synthetic when both map the same child', () => {
    const synthetic = new Map([['c', 'synthetic-parent']])
    const explicit = new Map([['c', 'real-parent']])
    const merged = mergeParentMaps(explicit, synthetic)
    expect(merged.get('c')).toBe('real-parent')
  })

  it('preserves synthetic entries that have no explicit counterpart', () => {
    const synthetic = new Map([
      ['c1', 'section-1'],
      ['c2', 'section-1'],
    ])
    const explicit = new Map([['c2', 'list-a']])
    const merged = mergeParentMaps(explicit, synthetic)
    expect(merged.get('c1')).toBe('section-1')
    expect(merged.get('c2')).toBe('list-a')
  })
})

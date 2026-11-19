import { describe, expect, it } from 'vitest'
import { toggleSelectedId, toggleSelectedIds } from './mergeSelection'

describe('merge selection', () => {
  it('toggles one id, keeping the selection order', () => {
    expect(toggleSelectedId(['a'], 'b')).toEqual(['a', 'b'])
    expect(toggleSelectedId(['a', 'b'], 'a')).toEqual(['b'])
  })

  it('adds the missing ids of a group, without duplicates', () => {
    expect(toggleSelectedIds(['a'], ['a', 'b', 'c'])).toEqual(['a', 'b', 'c'])
  })

  it('deselects a group whose ids are all selected', () => {
    expect(toggleSelectedIds(['a', 'b', 'c'], ['a', 'c'])).toEqual(['b'])
  })

  it('leaves the selection as is for an empty group', () => {
    const selection = ['a']
    expect(toggleSelectedIds(selection, [])).toBe(selection)
  })
})

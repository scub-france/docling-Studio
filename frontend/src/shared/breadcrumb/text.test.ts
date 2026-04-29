import { describe, expect, it } from 'vitest'

import { truncate } from './text'

describe('truncate', () => {
  it('returns the input unchanged when shorter than the limit', () => {
    expect(truncate('short', 10)).toBe('short')
    expect(truncate('exactly10!', 10)).toBe('exactly10!')
  })

  it('truncates and adds an ellipsis when longer than the limit', () => {
    expect(truncate('this is a long title', 10)).toBe('this is a…')
  })

  it('trims trailing whitespace before the ellipsis', () => {
    expect(truncate('foo bar baz qux', 8)).toBe('foo bar…')
  })

  it('returns the input untouched for non-positive limits', () => {
    expect(truncate('hello', 0)).toBe('hello')
    expect(truncate('hello', -5)).toBe('hello')
  })

  it('handles empty strings', () => {
    expect(truncate('', 10)).toBe('')
  })
})

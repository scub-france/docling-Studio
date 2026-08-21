import { describe, expect, it } from 'vitest'

import {
  DEFAULT_PAGE_INPUT_SIZE,
  clampPageInput,
  pageInputWidthCh,
} from './PagePreviewWithOverlay.logic'

describe('clampPageInput', () => {
  it('returns an in-range page unchanged', () => {
    expect(clampPageInput('3', 10)).toBe(3)
  })

  it('keeps the inclusive boundaries', () => {
    expect(clampPageInput('1', 10)).toBe(1)
    expect(clampPageInput('10', 10)).toBe(10)
  })

  it('clamps below 1 up to the first page', () => {
    expect(clampPageInput('0', 10)).toBe(1)
    expect(clampPageInput('-5', 10)).toBe(1)
  })

  it('clamps beyond the total down to the last page', () => {
    expect(clampPageInput('99', 10)).toBe(10)
  })

  it.each([
    ['', 'empty'],
    ['   ', 'blank'],
    ['abc', 'non-numeric'],
    ['x7', 'leading junk'],
  ])('returns null for %s input (%s)', (raw) => {
    expect(clampPageInput(raw, 10)).toBeNull()
  })

  it('follows parseInt semantics: trailing junk and decimals', () => {
    expect(clampPageInput('7x', 10)).toBe(7)
    expect(clampPageInput('4.9', 10)).toBe(4)
    expect(clampPageInput('42abc', 10)).toBe(10)
  })
})

describe('pageInputWidthCh', () => {
  it('floors at the default width for low-page documents', () => {
    expect(pageInputWidthCh(1)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(pageInputWidthCh(9)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(pageInputWidthCh(999)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(pageInputWidthCh(1000)).toBe(DEFAULT_PAGE_INPUT_SIZE)
  })

  it('grows to fit the digit count past the default', () => {
    expect(pageInputWidthCh(10000)).toBe(5)
    expect(pageInputWidthCh(123456)).toBe(6)
  })
})

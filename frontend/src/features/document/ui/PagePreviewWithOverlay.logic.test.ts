import { describe, expect, it } from 'vitest'

import {
  DEFAULT_PAGE_INPUT_SIZE,
  clampPageInput,
  isPageInRenderWindow,
  computePageInputWidthCh,
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

describe('computePageInputWidthCh', () => {
  it('floors at the default width for low-page documents', () => {
    expect(computePageInputWidthCh(1)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(computePageInputWidthCh(9)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(computePageInputWidthCh(999)).toBe(DEFAULT_PAGE_INPUT_SIZE)
    expect(computePageInputWidthCh(1000)).toBe(DEFAULT_PAGE_INPUT_SIZE)
  })

  it('grows to fit the digit count past the default', () => {
    expect(computePageInputWidthCh(10000)).toBe(5)
    expect(computePageInputWidthCh(123456)).toBe(6)
  })
})

describe('isPageInRenderWindow', () => {
  it('requests only the foreground page until it has settled', () => {
    const mounted = Array.from({ length: 411 }, (_, index) => index + 1).filter((page) =>
      isPageInRenderWindow(page, 50, 'scroll', null, false, false),
    )
    expect(mounted).toEqual([50])
  })

  it('preloads two pages ahead after the foreground page settles', () => {
    const mounted = Array.from({ length: 411 }, (_, index) => index + 1).filter((page) =>
      isPageInRenderWindow(page, 50, 'scroll', null, true, false),
    )
    expect(mounted).toEqual([50, 51, 52])
  })

  it('keeps requested nearby pages while moving to a page still loading', () => {
    const mounted = Array.from({ length: 411 }, (_, index) => index + 1).filter((page) =>
      isPageInRenderWindow(page, 50, 'scroll', null, false, [49, 51, 52].includes(page)),
    )
    expect(mounted).toEqual([49, 50, 51, 52])
  })

  it('keeps a distant focused page mounted during a focus scroll', () => {
    expect(isPageInRenderWindow(300, 1, 'scroll', 300, false, false)).toBe(true)
    expect(isPageInRenderWindow(301, 1, 'scroll', 300, false, false)).toBe(false)
  })
})

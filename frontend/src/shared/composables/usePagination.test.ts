import { describe, it, expect } from 'vitest'
import { ref, nextTick } from 'vue'
import { usePagination } from './usePagination'

function makeItems(n: number): string[] {
  return Array.from({ length: n }, (_, i) => `item-${i + 1}`)
}

describe('usePagination', () => {
  it('returns all items when total fits in one page', () => {
    const items = ref(makeItems(5))
    const { paginatedItems, pageCount, page } = usePagination(items, { pageSize: 20 })

    expect(paginatedItems.value).toHaveLength(5)
    expect(pageCount.value).toBe(1)
    expect(page.value).toBe(1)
  })

  it('slices items according to page size', () => {
    const items = ref(makeItems(25))
    const { paginatedItems, pageCount } = usePagination(items, { pageSize: 10 })

    expect(paginatedItems.value).toHaveLength(10)
    expect(paginatedItems.value[0]).toBe('item-1')
    expect(pageCount.value).toBe(3)
  })

  it('navigates with next and prev', () => {
    const items = ref(makeItems(30))
    const { paginatedItems, page, goNext, goPrev } = usePagination(items, { pageSize: 10 })

    goNext()
    expect(page.value).toBe(2)
    expect(paginatedItems.value[0]).toBe('item-11')

    goNext()
    expect(page.value).toBe(3)
    expect(paginatedItems.value[0]).toBe('item-21')

    goPrev()
    expect(page.value).toBe(2)
    expect(paginatedItems.value[0]).toBe('item-11')
  })

  it('clamps page within valid range', () => {
    const items = ref(makeItems(10))
    const { page, goPrev, goNext, goTo } = usePagination(items, { pageSize: 5 })

    goPrev()
    expect(page.value).toBe(1)

    goNext()
    goNext()
    expect(page.value).toBe(2)

    goTo(99)
    expect(page.value).toBe(2)

    goTo(0)
    expect(page.value).toBe(1)
  })

  it('goTo navigates to a specific page', () => {
    const items = ref(makeItems(50))
    const { page, paginatedItems, goTo } = usePagination(items, { pageSize: 10 })

    goTo(3)
    expect(page.value).toBe(3)
    expect(paginatedItems.value[0]).toBe('item-21')

    goTo(5)
    expect(page.value).toBe(5)
    expect(paginatedItems.value[0]).toBe('item-41')
  })

  it('resets to page 1 when items change', async () => {
    const items = ref(makeItems(30))
    const { page, goNext } = usePagination(items, { pageSize: 10 })

    goNext()
    goNext()
    expect(page.value).toBe(3)

    items.value = makeItems(5)
    await nextTick()
    expect(page.value).toBe(1)
  })

  it('resets to page 1 when page size changes', async () => {
    const items = ref(makeItems(50))
    const { page, goNext, setPageSize } = usePagination(items, { pageSize: 10 })

    goNext()
    goNext()
    expect(page.value).toBe(3)

    setPageSize(20)
    await nextTick()
    expect(page.value).toBe(1)
  })

  it('handles last page with fewer items', () => {
    const items = ref(makeItems(23))
    const { paginatedItems, goTo } = usePagination(items, { pageSize: 10 })

    goTo(3)
    expect(paginatedItems.value).toHaveLength(3)
    expect(paginatedItems.value[0]).toBe('item-21')
  })

  it('handles empty items', () => {
    const items = ref<string[]>([])
    const { paginatedItems, pageCount, totalItems } = usePagination(items)

    expect(paginatedItems.value).toHaveLength(0)
    expect(pageCount.value).toBe(1)
    expect(totalItems.value).toBe(0)
  })

  it('exposes totalItems as reactive count', async () => {
    const items = ref(makeItems(10))
    const { totalItems } = usePagination(items)

    expect(totalItems.value).toBe(10)

    items.value = makeItems(42)
    await nextTick()
    expect(totalItems.value).toBe(42)
  })

  it('defaults page size to 20', () => {
    const items = ref(makeItems(50))
    const { pageSize, paginatedItems } = usePagination(items)

    expect(pageSize.value).toBe(20)
    expect(paginatedItems.value).toHaveLength(20)
  })

  it('ignores invalid page size', () => {
    const items = ref(makeItems(10))
    const { pageSize, setPageSize } = usePagination(items, { pageSize: 5 })

    setPageSize(0)
    expect(pageSize.value).toBe(5)

    setPageSize(-10)
    expect(pageSize.value).toBe(5)
  })
})

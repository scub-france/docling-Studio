import { ref, computed, watch, type Ref } from 'vue'

export interface PaginationOptions {
  pageSize?: number
}

export interface PaginationReturn<T> {
  page: Ref<number>
  pageSize: Ref<number>
  pageCount: Ref<number>
  paginatedItems: Ref<T[]>
  totalItems: Ref<number>
  goNext: () => void
  goPrev: () => void
  goTo: (target: number) => void
  setPageSize: (size: number) => void
}

export function usePagination<T>(
  items: Ref<T[]>,
  options: PaginationOptions = {},
): PaginationReturn<T> {
  const page = ref(1)
  const pageSize = ref(options.pageSize ?? 20)

  const totalItems = computed(() => items.value.length)

  const pageCount = computed(() => Math.max(1, Math.ceil(totalItems.value / pageSize.value)))

  const paginatedItems = computed(() => {
    const start = (page.value - 1) * pageSize.value
    return items.value.slice(start, start + pageSize.value)
  })

  // Reset to page 1 when source data or page size changes
  watch([items, pageSize], () => {
    page.value = 1
  })

  function clamp(target: number): number {
    return Math.max(1, Math.min(target, pageCount.value))
  }

  function goTo(target: number): void {
    page.value = clamp(target)
  }

  function goNext(): void {
    goTo(page.value + 1)
  }

  function goPrev(): void {
    goTo(page.value - 1)
  }

  function setPageSize(size: number): void {
    if (size > 0) pageSize.value = size
  }

  return {
    page,
    pageSize,
    pageCount,
    paginatedItems,
    totalItems,
    goNext,
    goPrev,
    goTo,
    setPageSize,
  }
}

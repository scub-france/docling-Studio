import { defineStore } from 'pinia'
import { onBeforeUnmount, watch, type Ref, type ComputedRef } from 'vue'

import type { Crumb } from './types'

/**
 * Store the current breadcrumb segments. Pages set them on mount via
 * `useCrumbs(crumbs)` and clear them on unmount automatically.
 *
 * The shell (`App.vue`) reads `crumbs` and renders `<AppBreadcrumb>` —
 * empty array → component renders nothing.
 */
export const useBreadcrumbStore = defineStore('breadcrumb', {
  state: () => ({
    crumbs: [] as Crumb[],
  }),
  actions: {
    setCrumbs(crumbs: Crumb[]) {
      this.crumbs = crumbs
    },
    clear() {
      this.crumbs = []
    },
  },
})

/**
 * Composable for pages to declare their breadcrumb. Auto-clears on
 * unmount so a stale breadcrumb never leaks to the next route.
 *
 * Accepts a static array OR a reactive ref / computed so pages with
 * async data (e.g. doc workspace fetching the doc title) can rebuild
 * crumbs as the data lands.
 */
export function useCrumbs(source: Crumb[] | Ref<Crumb[]> | ComputedRef<Crumb[]>) {
  const store = useBreadcrumbStore()

  if (Array.isArray(source)) {
    store.setCrumbs(source)
  } else {
    watch(
      source,
      (next) => {
        store.setCrumbs(next)
      },
      { immediate: true },
    )
  }

  onBeforeUnmount(() => {
    store.clear()
  })
}

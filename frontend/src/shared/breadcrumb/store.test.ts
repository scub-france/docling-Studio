import { createPinia, setActivePinia } from 'pinia'
import { ref, type Ref } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'

import { useBreadcrumbStore, useCrumbs } from './store'
import type { Crumb } from './types'

/**
 * The composable side of `useCrumbs` registers `onBeforeUnmount` which
 * requires a component lifecycle context. The project does not have
 * `@vue/test-utils`, so we test the store API directly. The composable
 * lifecycle is exercised end-to-end by the integration tests landing
 * in #211 / #216.
 *
 * We DO test the reactive-input behaviour by calling `useCrumbs` with
 * a ref inside a setup-style scope; the watch fires synchronously
 * thanks to `immediate: true`.
 */
describe('useBreadcrumbStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts empty', () => {
    const store = useBreadcrumbStore()
    expect(store.crumbs).toEqual([])
  })

  it('setCrumbs replaces the segments', () => {
    const store = useBreadcrumbStore()
    const next: Crumb[] = [{ kind: 'leaf', label: 'a' }]
    store.setCrumbs(next)
    expect(store.crumbs).toEqual(next)
  })

  it('clear empties the segments', () => {
    const store = useBreadcrumbStore()
    store.setCrumbs([{ kind: 'leaf', label: 'a' }])
    store.clear()
    expect(store.crumbs).toEqual([])
  })
})

describe('useCrumbs (reactive source path)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('seeds the store from a ref synchronously', () => {
    const store = useBreadcrumbStore()
    const dynamic: Ref<Crumb[]> = ref([{ kind: 'leaf', label: 'first' }])
    // Note: `useCrumbs` calls `onBeforeUnmount` which is a no-op when
    // there is no current component — Vue logs a warning but the watch
    // path still installs.
    useCrumbs(dynamic)
    expect(store.crumbs).toEqual([{ kind: 'leaf', label: 'first' }])

    dynamic.value = [{ kind: 'leaf', label: 'second' }]
    // The watch is `immediate: true`; for subsequent updates it runs
    // on the next microtask.
    return Promise.resolve().then(() => {
      expect(store.crumbs).toEqual([{ kind: 'leaf', label: 'second' }])
    })
  })

  it('seeds the store from a static array', () => {
    const store = useBreadcrumbStore()
    useCrumbs([{ kind: 'leaf', label: 'static' }])
    expect(store.crumbs).toEqual([{ kind: 'leaf', label: 'static' }])
  })
})

// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { Page } from '../../../shared/types'
import PagePreviewWithOverlay from './PagePreviewWithOverlay.vue'

const pages: Page[] = Array.from({ length: 6 }, (_, index) => ({
  page_number: index + 1,
  width: 612,
  height: 792,
  elements: [],
}))

class ObserverStub {
  observe(): void {}
  disconnect(): void {}
}

describe('PagePreviewWithOverlay image scheduling', () => {
  beforeEach(() => vi.stubGlobal('IntersectionObserver', ObserverStub))
  afterEach(() => vi.unstubAllGlobals())

  it('loads the current page first, then keeps nearby requests as the reader advances', async () => {
    const wrapper = shallowMount(PagePreviewWithOverlay, {
      props: {
        documentId: 'doc-1',
        pages,
        currentPage: 1,
        hiddenTypes: new Set<string>(),
        showLabels: true,
      },
    })
    await nextTick()

    const mountedPages = () =>
      wrapper.findAll('img.preview-image').map((image) => Number(image.attributes('alt')?.slice(5)))

    expect(mountedPages()).toEqual([1])
    await wrapper.get('img.preview-image').trigger('load')
    expect(mountedPages()).toEqual([1, 2, 3])

    await wrapper.setProps({ currentPage: 2 })
    expect(mountedPages()).toEqual([1, 2, 3])
    await wrapper.findAll('img.preview-image')[1].trigger('load')
    expect(mountedPages()).toEqual([1, 2, 3, 4])

    await wrapper.setProps({ currentPage: 6 })
    expect(mountedPages()).toEqual([6])

    await wrapper.setProps({ documentId: 'doc-2', currentPage: 1 })
    expect(mountedPages()).toEqual([1])
    expect(wrapper.get('img.preview-image').attributes('src')).toContain('/documents/doc-2/')
    wrapper.unmount()
  })
})

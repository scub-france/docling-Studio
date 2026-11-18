// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { Page } from '../../../shared/types'
import PagePreviewWithOverlay from './PagePreviewWithOverlay.vue'
import PdfPageCanvas from './PdfPageCanvas.vue'

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: vi.fn(() => ({ promise: Promise.resolve({}), destroy: vi.fn() })),
}))

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

describe('PagePreviewWithOverlay PDF scheduling', () => {
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
    await flushPromises()
    await nextTick()

    const mountedPages = () =>
      wrapper
        .findAll('pdf-page-canvas-stub')
        .map((canvas) => Number(canvas.attributes('pagenumber')))

    expect(mountedPages()).toEqual([1])
    wrapper.getComponent(PdfPageCanvas).vm.$emit('ready', document.createElement('canvas'))
    await nextTick()
    expect(mountedPages()).toEqual([1, 2, 3])

    await wrapper.setProps({ currentPage: 2 })
    expect(mountedPages()).toEqual([1, 2, 3])
    wrapper.findAllComponents(PdfPageCanvas)[1].vm.$emit('ready', document.createElement('canvas'))
    await nextTick()
    expect(mountedPages()).toEqual([1, 2, 3, 4])

    await wrapper.setProps({ currentPage: 6 })
    expect(mountedPages()).toEqual([6])

    await wrapper.setProps({ documentId: 'doc-2', currentPage: 1 })
    await flushPromises()
    expect(mountedPages()).toEqual([1])
    expect(wrapper.find('img.preview-image').exists()).toBe(false)
    wrapper.unmount()
  })
})

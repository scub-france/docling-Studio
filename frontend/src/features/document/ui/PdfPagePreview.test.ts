// @vitest-environment jsdom
import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getDocument } from 'pdfjs-dist'
import PdfPagePreview from './PdfPagePreview.vue'
import PdfPageCanvas from './PdfPageCanvas.vue'

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: vi.fn(),
}))

describe('PdfPagePreview', () => {
  beforeEach(() => {
    vi.mocked(getDocument).mockReset()
    vi.mocked(getDocument).mockImplementation(
      () =>
        ({
          promise: Promise.resolve({}),
          destroy: vi.fn(),
        }) as never,
    )
  })
  afterEach(() => vi.clearAllMocks())

  it('reuses the loaded PDF when changing pages and emits the ready canvas', async () => {
    const wrapper = shallowMount(PdfPagePreview, {
      props: { documentId: 'doc-1', page: 1 },
    })
    await flushPromises()
    expect(wrapper.getComponent(PdfPageCanvas).props('pageNumber')).toBe(1)
    const canvas = document.createElement('canvas')
    wrapper.getComponent(PdfPageCanvas).vm.$emit('ready', canvas)
    expect(wrapper.emitted('ready')?.at(-1)).toEqual([canvas])

    await wrapper.setProps({ page: 20 })
    expect(wrapper.getComponent(PdfPageCanvas).props('pageNumber')).toBe(20)
    expect(getDocument).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('ready')?.at(-1)).toEqual([null])
    wrapper.unmount()
  })

  it('falls back to a page image when PDF loading fails', async () => {
    vi.mocked(getDocument).mockImplementation(
      () =>
        ({
          promise: Promise.reject(new Error('PDF unavailable')),
          destroy: vi.fn(),
        }) as never,
    )
    const wrapper = shallowMount(PdfPagePreview, {
      props: { documentId: 'doc-2', page: 5 },
    })
    await flushPromises()
    expect(wrapper.find('img.fallback-image').attributes('src')).toContain(
      '/api/documents/doc-2/preview?page=5',
    )
    wrapper.unmount()
  })
})

// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import PageRaster from './PageRaster.vue'
import PdfPageCanvas from './PdfPageCanvas.vue'

const pdf = {} as PDFDocumentProxy

function mountRaster(props: { document: PDFDocumentProxy | null; failed: boolean }) {
  return shallowMount(PageRaster, {
    props: { documentId: 'doc-1', pageNumber: 3, priority: 'high' as const, ...props },
  })
}

describe('PageRaster', () => {
  it('renders the PDF page and tags its events with the pdf path', () => {
    const wrapper = mountRaster({ document: pdf, failed: false })
    const canvasComponent = wrapper.getComponent(PdfPageCanvas)
    expect(canvasComponent.props('pageNumber')).toBe(3)
    expect(wrapper.find('img').exists()).toBe(false)

    const canvas = document.createElement('canvas')
    canvasComponent.vm.$emit('ready', canvas)
    canvasComponent.vm.$emit('error')

    expect(wrapper.emitted('ready')).toEqual([[canvas, 'pdf']])
    expect(wrapper.emitted('error')).toEqual([['pdf']])
  })

  it('falls back to the page image and tags its events with the image path', async () => {
    const wrapper = mountRaster({ document: pdf, failed: true })
    expect(wrapper.findComponent(PdfPageCanvas).exists()).toBe(false)
    const img = wrapper.get('img.preview-image')
    expect(img.attributes('src')).toContain('/api/documents/doc-1/preview?page=3')
    expect(img.attributes('fetchpriority')).toBe('high')

    await img.trigger('load')
    await img.trigger('error')

    expect(wrapper.emitted('ready')).toEqual([[img.element, 'image']])
    expect(wrapper.emitted('error')).toEqual([['image']])
  })

  it('renders nothing while the PDF is still loading', () => {
    const wrapper = mountRaster({ document: null, failed: false })
    expect(wrapper.findComponent(PdfPageCanvas).exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
  })
})

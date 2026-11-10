// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BboxCanvas from './BboxCanvas.vue'

describe('BboxCanvas reading order badges', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('draws order numbers and selects a badge above an overlapping box', async () => {
    const context = {
      clearRect: vi.fn(),
      strokeRect: vi.fn(),
      fillRect: vi.fn(),
      fillText: vi.fn(),
      setLineDash: vi.fn(),
      save: vi.fn(),
      restore: vi.fn(),
    }
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
      context as unknown as CanvasRenderingContext2D,
    )
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      },
    )
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) =>
      window.setTimeout(() => callback(0), 0),
    )
    vi.stubGlobal('cancelAnimationFrame', (id: number) => window.clearTimeout(id))
    const image = document.createElement('img')
    Object.defineProperties(image, {
      clientWidth: { value: 100 },
      clientHeight: { value: 100 },
    })
    const first = {
      type: 'text',
      bbox: [0, 0, 100, 100],
      content: 'First',
      level: 0,
      self_ref: '#/texts/0',
    }
    const second = {
      type: 'text',
      bbox: [10, 10, 30, 30],
      content: 'Second',
      level: 0,
      self_ref: '#/texts/1',
    }
    const wrapper = mount(BboxCanvas, {
      props: {
        imageEl: image,
        pageNumber: 1,
        pageWidth: 100,
        pageHeight: 100,
        elements: [first, second],
        hiddenTypes: new Set<string>(),
        readingOrderByRef: new Map([
          ['#/texts/0', 1],
          ['#/texts/1', 2],
        ]),
        selectedRef: '#/texts/0',
        nextRef: '#/texts/1',
      },
    })
    await new Promise((resolve) => window.setTimeout(resolve, 0))

    expect(context.fillText).toHaveBeenCalledWith('1', expect.any(Number), expect.any(Number))
    expect(context.fillText).toHaveBeenCalledWith('2', expect.any(Number), expect.any(Number))
    await wrapper.get('canvas').trigger('click', { clientX: 13, clientY: 13 })
    expect(wrapper.emitted('clickElement')?.[0]?.[0]).toEqual(second)
    wrapper.unmount()
  })
})

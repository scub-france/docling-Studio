// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PdfPageCanvas from './PdfPageCanvas.vue'

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (error: Error) => void
}

function deferred<T = void>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function cancelled(): Error {
  const error = new Error('Rendering cancelled')
  error.name = 'RenderingCancelledException'
  return error
}

/** A PDF.js render task whose outcome each test settles by hand. */
function fakeTask() {
  const done = deferred()
  return { promise: done.promise, cancel: vi.fn(), done }
}

function fakePage(tasks: ReturnType<typeof fakeTask>[]) {
  return {
    getViewport: ({ scale }: { scale: number }) => ({ width: 100 * scale, height: 200 * scale }),
    render: vi.fn(() => {
      const task = fakeTask()
      tasks.push(task)
      return task
    }),
  }
}

class FakeResizeObserver {
  observe = vi.fn()
  disconnect = vi.fn()
}

describe('PdfPageCanvas', () => {
  let tasks: ReturnType<typeof fakeTask>[]
  let page: ReturnType<typeof fakePage>
  let pdf: { getPage: ReturnType<typeof vi.fn> }

  beforeEach(() => {
    tasks = []
    page = fakePage(tasks)
    pdf = { getPage: vi.fn(async () => page) }
    vi.stubGlobal('ResizeObserver', FakeResizeObserver)
    // jsdom has no layout: give the canvas a width so a render can start.
    Object.defineProperty(HTMLCanvasElement.prototype, 'clientWidth', {
      configurable: true,
      get: () => 300,
    })
  })

  afterEach(() => {
    delete (HTMLCanvasElement.prototype as { clientWidth?: number }).clientWidth
    vi.unstubAllGlobals()
  })

  async function render(pageNumber = 3) {
    const wrapper = mount(PdfPageCanvas, { props: { document: pdf as never, pageNumber } })
    await flushPromises()
    return wrapper
  }

  it('renders the requested page at the canvas width and reports the canvas', async () => {
    const wrapper = await render(3)

    expect(pdf.getPage).toHaveBeenCalledWith(3)
    const canvas = wrapper.get('canvas').element as HTMLCanvasElement
    expect(page.render).toHaveBeenCalledWith({
      canvas,
      viewport: { width: 300, height: 600 },
    })
    expect(canvas.width).toBe(300)
    expect(canvas.height).toBe(600)

    tasks[0]!.done.resolve()
    await flushPromises()
    expect(wrapper.emitted('ready')).toEqual([[canvas]])
    expect(wrapper.emitted('error')).toBeUndefined()
    wrapper.unmount()
  })

  it('cancels the running render and waits for it before drawing another page', async () => {
    const wrapper = await render(3)
    pdf.getPage.mockClear()

    await wrapper.setProps({ pageNumber: 4 })
    await flushPromises()
    expect(tasks[0]!.cancel).toHaveBeenCalled()
    // The canvas is still held by the cancelled render.
    expect(pdf.getPage).not.toHaveBeenCalled()

    tasks[0]!.done.reject(cancelled())
    await flushPromises()
    expect(pdf.getPage).toHaveBeenCalledWith(4)
    tasks[1]!.done.resolve()
    await flushPromises()
    expect(wrapper.emitted('ready')).toHaveLength(1)
    expect(wrapper.emitted('error')).toBeUndefined()
    wrapper.unmount()
  })

  it('cancels the running render on unmount', async () => {
    const wrapper = await render()

    wrapper.unmount()

    expect(tasks[0]!.cancel).toHaveBeenCalled()
    tasks[0]!.done.reject(cancelled())
    await flushPromises()
    expect(wrapper.emitted('ready')).toBeUndefined()
    expect(wrapper.emitted('error')).toBeUndefined()
  })

  it('reports a failed render so the caller can fall back', async () => {
    const wrapper = await render()

    tasks[0]!.done.reject(new Error('broken page'))
    await flushPromises()

    expect(wrapper.emitted('error')).toHaveLength(1)
    expect(wrapper.emitted('ready')).toBeUndefined()
    wrapper.unmount()
  })

  it('reports a page that cannot be loaded', async () => {
    pdf.getPage.mockRejectedValue(new Error('invalid page'))

    const wrapper = await render()

    expect(wrapper.emitted('error')).toHaveLength(1)
    wrapper.unmount()
  })

  it('keeps the newest page when an older page resolves late', async () => {
    const slowPage = deferred<typeof page>()
    pdf.getPage.mockImplementation((n: number) => (n === 1 ? slowPage.promise : page))
    const wrapper = await render(1)

    await wrapper.setProps({ pageNumber: 2 })
    await flushPromises()
    tasks[0]!.done.resolve()
    await flushPromises()
    slowPage.resolve(page)
    await flushPromises()

    expect(page.render).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('ready')).toHaveLength(1)
    expect(wrapper.emitted('error')).toBeUndefined()
    wrapper.unmount()
  })
})

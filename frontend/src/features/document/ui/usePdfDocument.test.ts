// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref, type Ref } from 'vue'
import { getDocument } from 'pdfjs-dist'
import { usePdfDocument } from './usePdfDocument'

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: vi.fn(),
}))

interface FakeLoadingTask {
  promise: Promise<unknown>
  destroy: ReturnType<typeof vi.fn>
  resolve: (pdf: unknown) => void
}

function loadingTask(): FakeLoadingTask {
  let resolve!: (pdf: unknown) => void
  const promise = new Promise((res) => (resolve = res))
  return { promise, resolve, destroy: vi.fn(async () => {}) }
}

function mountWith(documentId: Ref<string | undefined>) {
  let state!: ReturnType<typeof usePdfDocument>
  const wrapper = mount(
    defineComponent({
      setup() {
        state = usePdfDocument(documentId)
        return () => null
      },
    }),
  )
  return { wrapper, state: () => state }
}

describe('usePdfDocument', () => {
  afterEach(() => vi.mocked(getDocument).mockReset())

  it('loads the PDF by ranges from the export route', async () => {
    const task = loadingTask()
    vi.mocked(getDocument).mockReturnValue(task as never)
    const { wrapper, state } = mountWith(ref('doc-1'))
    await flushPromises()

    expect(getDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        url: expect.stringContaining('doc-1'),
        disableAutoFetch: true,
        rangeChunkSize: 256 * 1024,
      }),
    )
    task.resolve({ numPages: 2 })
    await flushPromises()
    expect(state().document.value).toEqual({ numPages: 2 })
    wrapper.unmount()
  })

  it('destroys the previous PDF and ignores its late result on document change', async () => {
    const first = loadingTask()
    const second = loadingTask()
    vi.mocked(getDocument)
      .mockReturnValueOnce(first as never)
      .mockReturnValueOnce(second as never)
    const id = ref<string | undefined>('doc-1')
    const { wrapper, state } = mountWith(id)
    await flushPromises()

    id.value = 'doc-2'
    await flushPromises()
    expect(first.destroy).toHaveBeenCalledTimes(1)
    expect(getDocument).toHaveBeenCalledTimes(2)

    // The stale PDF resolves last: without the generation guard it would win.
    second.resolve({ id: 'doc-2' })
    await flushPromises()
    first.resolve({ id: 'doc-1' })
    await flushPromises()
    expect(state().document.value).toEqual({ id: 'doc-2' })
    expect(state().failed.value).toBe(false)
    wrapper.unmount()
  })

  it('destroys the loading task on unmount', async () => {
    const task = loadingTask()
    vi.mocked(getDocument).mockReturnValue(task as never)
    const { wrapper } = mountWith(ref('doc-1'))
    await flushPromises()

    wrapper.unmount()

    expect(task.destroy).toHaveBeenCalledTimes(1)
  })
})

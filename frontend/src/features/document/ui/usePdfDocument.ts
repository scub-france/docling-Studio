import { onBeforeUnmount, ref, shallowRef, watch, type Ref } from 'vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?worker&url'
import { getExportUrl } from '../api'

// 256 KiB ranges: a page is fetched in a few requests instead of the whole file.
const PDF_RANGE_CHUNK_BYTES = 256 * 1024

/** Load one PDF per viewer, leaving page selection to the caller. */
export function usePdfDocument(documentId: Ref<string | undefined>) {
  const document = shallowRef<PDFDocumentProxy | null>(null)
  const failed = ref(false)
  let task: PDFDocumentLoadingTask | null = null
  let generation = 0

  async function load(id: string | undefined): Promise<void> {
    const current = ++generation
    const previous = task
    task = null
    document.value = null
    failed.value = false
    try {
      if (previous) await previous.destroy()
      if (!id || current !== generation) return
      const pdfjs = await import('pdfjs-dist')
      if (current !== generation) return
      pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
      const loadingTask = pdfjs.getDocument({
        url: getExportUrl(id, 'pdf'),
        disableStream: true,
        disableAutoFetch: true,
        rangeChunkSize: PDF_RANGE_CHUNK_BYTES,
      })
      task = loadingTask
      const loaded = await loadingTask.promise
      if (current !== generation) return
      document.value = loaded
    } catch {
      if (current === generation) failed.value = true
    }
  }

  watch(documentId, (id) => void load(id), { immediate: true })
  onBeforeUnmount(() => {
    generation += 1
    void task?.destroy()
  })

  return { document, failed }
}

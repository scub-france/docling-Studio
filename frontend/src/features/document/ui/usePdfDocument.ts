import { onBeforeUnmount, ref, shallowRef, watch, type Ref, type ShallowRef } from 'vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?worker&url'
import { getExportUrl } from '../api'

// 256 KiB ranges: a page is fetched in a few requests instead of the whole file.
const PDF_RANGE_CHUNK_BYTES = 256 * 1024

interface PdfLoaderState {
  document: ShallowRef<PDFDocumentProxy | null>
  failed: Ref<boolean>
  task: PDFDocumentLoadingTask | null
  generation: number
}

function openPdfTask(pdfjs: typeof import('pdfjs-dist'), id: string): PDFDocumentLoadingTask {
  pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
  return pdfjs.getDocument({
    url: getExportUrl(id, 'pdf'),
    disableStream: true,
    disableAutoFetch: true,
    rangeChunkSize: PDF_RANGE_CHUNK_BYTES,
  })
}

async function loadPdf(state: PdfLoaderState, id: string | undefined): Promise<void> {
  const current = ++state.generation
  const previous = state.task
  state.task = null
  state.document.value = null
  state.failed.value = false
  try {
    if (previous) await previous.destroy()
    if (!id || current !== state.generation) return
    const pdfjs = await import('pdfjs-dist')
    if (current !== state.generation) return
    const loadingTask = openPdfTask(pdfjs, id)
    state.task = loadingTask
    const loaded = await loadingTask.promise
    if (current !== state.generation) return
    state.document.value = loaded
  } catch {
    if (current === state.generation) state.failed.value = true
  }
}

/** Load one PDF per viewer, leaving page selection to the caller. */
export function usePdfDocument(documentId: Ref<string | undefined>) {
  const state: PdfLoaderState = {
    document: shallowRef<PDFDocumentProxy | null>(null),
    failed: ref(false),
    task: null,
    generation: 0,
  }

  watch(documentId, (id) => void loadPdf(state, id), { immediate: true })
  onBeforeUnmount(() => {
    state.generation += 1
    void state.task?.destroy()
  })

  return { document: state.document, failed: state.failed }
}

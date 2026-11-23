/**
 * Pure helper for the Linked view's chunk ↔ element mapping (#264).
 *
 * findChunkForElement(element, chunks): which chunk does this OCR element
 * belong to? Used when the user clicks a bbox on the preview → scroll to
 * the matching chunk card.
 *
 * Strategy: prefer the **exact** `self_ref` link carried by
 * `chunk.docItems` (set upstream by the chunker). When the chunk has no
 * `docItems` (legacy or hand-edited chunk), fall back to **bbox overlap**
 * with a minimum coverage threshold to avoid false positives on touching
 * neighbours.
 */

import type { DocChunk, PageElement, Rect } from '../../shared/types'

const OVERLAP_MIN_COVERAGE = 0.5

/**
 * Returns the chunk whose `docItems` contain `element.self_ref`, or — when
 * that link is unavailable — the chunk whose `bboxes` overlap the element
 * by at least `OVERLAP_MIN_COVERAGE` of the element's area on the same
 * page. Returns `null` if no chunk satisfies either criterion.
 */
export function findChunkForElement(
  element: PageElement,
  pageNumber: number,
  chunks: readonly DocChunk[],
): DocChunk | null {
  // Exact path: self_ref match.
  if (element.self_ref) {
    const exact = chunks.find((c) => c.docItems.some((di) => di.selfRef === element.self_ref))
    if (exact) return exact
  }
  // Fallback: bbox overlap on the same page.
  const elRect = bboxToRect(element.bbox)
  let best: { chunk: DocChunk; coverage: number } | null = null
  for (const chunk of chunks) {
    for (const cb of chunk.bboxes) {
      if (cb.page !== pageNumber) continue
      const coverage = computeOverlapCoverage(elRect, bboxToRect(cb.bbox))
      if (coverage >= OVERLAP_MIN_COVERAGE && (!best || coverage > best.coverage)) {
        best = { chunk, coverage }
      }
    }
  }
  return best?.chunk ?? null
}

// --- internals ---------------------------------------------------------------

function bboxToRect(bbox: readonly [number, number, number, number]): Rect {
  const [l, t, r, b] = bbox
  return { x: l, y: t, w: Math.max(0, r - l), h: Math.max(0, b - t) }
}

/** Fraction of `a`'s area that overlaps with `b`. Zero on no overlap. */
function computeOverlapCoverage(a: Rect, b: Rect): number {
  if (a.w <= 0 || a.h <= 0) return 0
  const xOverlap = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x))
  const yOverlap = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y))
  return (xOverlap * yOverlap) / (a.w * a.h)
}

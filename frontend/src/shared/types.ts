/**
 * Canonical document lifecycle state — mirrors the backend enum
 * `DocumentLifecycleState` (see `domain/value_objects.py`).
 *
 * - `Uploaded` raw file persisted, no parse yet
 * - `Parsed`   conversion produced a document tree
 * - `Chunked`  chunker produced a draft chunkset
 * - `Ingested` chunkset has been embedded into at least one store
 * - `Stale`    chunkset edited after a successful push (per-store concept)
 * - `Failed`   a pipeline step failed; recoverable by retry
 */
export type DocumentLifecycleState =
  | 'Uploaded'
  | 'Parsed'
  | 'Chunked'
  | 'Ingested'
  | 'Stale'
  | 'Failed'

export interface Document {
  id: string
  filename: string
  contentType: string | null
  fileSize: number | null
  pageCount: number | null
  createdAt: string
  /** Canonical lifecycle state. Drives the status badge in `/docs`. */
  lifecycleState: DocumentLifecycleState
  /** ISO timestamp of the last lifecycle transition (UTC). */
  lifecycleStateAt: string | null
  /** Stores this document has been pushed to (added in E1 #203). */
  stores?: string[]
}

export interface PipelineOptions {
  do_ocr?: boolean
  do_table_structure?: boolean
  table_mode?: 'accurate' | 'fast'
  do_code_enrichment?: boolean
  do_formula_enrichment?: boolean
  do_picture_classification?: boolean
  do_picture_description?: boolean
  generate_picture_images?: boolean
  generate_page_images?: boolean
  images_scale?: number
}

export type AnalysisStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface Analysis {
  id: string
  documentId: string
  documentFilename: string | null
  status: AnalysisStatus
  contentMarkdown: string | null
  contentHtml: string | null
  pagesJson: string | null
  chunksJson: string | null
  hasDocumentJson: boolean
  errorMessage: string | null
  progressCurrent: number | null
  progressTotal: number | null
  startedAt: string | null
  completedAt: string | null
  createdAt: string
}

export interface ChunkingOptions {
  chunker_type?: 'hybrid' | 'hierarchical'
  max_tokens?: number
  merge_peers?: boolean
  repeat_table_header?: boolean
}

export interface ChunkBbox {
  page: number
  bbox: [number, number, number, number]
}

export interface Chunk {
  text: string
  headings: string[]
  sourcePage: number | null
  tokenCount: number
  bboxes: ChunkBbox[]
  modified?: boolean
  deleted?: boolean
}

export interface PageElement {
  type: string
  bbox: [number, number, number, number]
  content: string
  level: number
  /** Docling `self_ref` — "#/texts/12", "#/tables/3", etc. Empty string for
   * items that don't have one (rare). Lets callers correlate a bbox with
   * the matching graph node without fuzzy bbox matching. */
  self_ref?: string
}

// Backend serializes with snake_case (dataclasses.asdict)
export interface Page {
  page_number: number
  width: number
  height: number
  elements: PageElement[]
}

export type ElementType =
  | 'title'
  | 'section_header'
  | 'text'
  | 'table'
  | 'picture'
  | 'list'
  | 'formula'
  | 'code'
  | 'caption'
  | 'floating'

export interface Scale {
  sx: number
  sy: number
}

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export type Locale = 'fr' | 'en'
export type Theme = 'dark' | 'light'

// ---------------------------------------------------------------------------
// E4/E5 — Doc workspace tree + chunks (#216–#222)
// ---------------------------------------------------------------------------

/** Node in the parsed document tree returned by GET /api/documents/:id/tree */
export interface DocTreeNode {
  ref: string
  type: string
  label: string
  children: DocTreeNode[]
}

/** Doc-centric chunk (distinct from legacy analysis Chunk). */
export interface DocChunk {
  id: string
  docId: string
  text: string
  title?: string
  sourceNodeRef?: string
  pageRange?: [number, number]
  tokenCount?: number
  createdAt: string
  updatedAt: string
}

export type ChunkDiffStatus = 'added' | 'modified' | 'removed' | 'unchanged'

export interface ChunkDiff {
  chunkId: string
  status: ChunkDiffStatus
  textDiff?: string
}

export interface PushSummary {
  embeds: number
  tokens: number
}

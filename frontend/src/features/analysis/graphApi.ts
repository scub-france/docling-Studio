import { apiFetch } from '@/shared/api/http'

/**
 * A single provenance entry for an element — matches Docling's
 * `ProvenanceItem`. One element may have multiple (e.g. a paragraph that
 * spans a page break has two entries, one per page).
 */
export interface GraphProvenance {
  order: number
  page_no: number | null
  bbox_l: number
  bbox_t: number
  bbox_r: number
  bbox_b: number
  coord_origin: string
  charspan_start: number | null
  charspan_end: number | null
}

export interface GraphNode {
  id: string
  group: 'document' | 'element' | 'page' | 'chunk'
  label?: string
  docling_label?: string
  self_ref?: string
  text?: string
  prov_page?: number | null
  /** Full list of provenances (page + bbox) — used by the bbox-highlight UI. */
  provs?: GraphProvenance[]
  level?: number | null
  page_no?: number
  chunk_index?: number
  title?: string
  doc_id?: string
  token_count?: number
  [key: string]: unknown
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: 'HAS_ROOT' | 'PARENT_OF' | 'NEXT' | 'ON_PAGE' | 'HAS_CHUNK' | 'DERIVED_FROM'
  order?: number | null
}

export interface GraphPayload {
  doc_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  node_count: number
  edge_count: number
  truncated: boolean
  page_count: number
}

export function fetchDocumentGraph(docId: string): Promise<GraphPayload> {
  return apiFetch<GraphPayload>(`/api/documents/${encodeURIComponent(docId)}/graph`)
}

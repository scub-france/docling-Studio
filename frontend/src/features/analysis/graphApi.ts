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

/**
 * One node, as the backend's `GraphNode` types it: a node carries only its
 * own group's keys.
 */
export interface GraphNode {
  id: string
  group: 'document' | 'element' | 'page' | 'chunk'
  /** An element's Neo4j label (SectionHeader, Paragraph, …). */
  label?: string
  /** document, element, page */
  doc_id?: string
  /** document */
  title?: string | null
  stages_applied?: string[] | null
  /** element */
  docling_label?: string
  self_ref?: string
  level?: number | null
  prov_page?: number | null
  /** Full list of provenances (page + bbox) — used by the bbox-highlight UI. */
  provs?: GraphProvenance[]
  /** element, chunk (cut to 200 characters) */
  text?: string
  /** page */
  page_no?: number
  width?: number | null
  height?: number | null
  /** chunk */
  chunk_index?: number
  token_count?: number
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

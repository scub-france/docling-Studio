/**
 * Pure helpers for the Ingest view (#225).
 *
 * Extracted from `DocIngestTab.vue` so the row-state derivation,
 * stale-count, and diff-summary logic can be unit-tested without a
 * DOM environment (the frontend doesn't ship `@vue/test-utils` /
 * `happy-dom` today). The component imports these directly — keep
 * them dependency-free (no Vue, no i18n, no HTTP).
 */
import type {
  ChunkDiff,
  ChunkDiffStatus,
  DocStoreLink,
  DocumentLifecycleState,
} from '../shared/types'
import type { StoreInfo } from '../features/store/api'

export type RowState = DocumentLifecycleState | 'NotPushed'

export interface IngestRow {
  slug: string
  name: string
  kind: string
  connected: boolean
  state: RowState
  pushedAt: string | null
}

export type StateBucket = 'notPushed' | 'upToDate' | 'stale' | 'failed'

/** i18n key for each bucket. The component consumes these via `t(...)`. */
export const STATE_LABEL_KEYS: Record<StateBucket, string> = {
  notPushed: 'ingest.stateNotPushed',
  upToDate: 'ingest.stateUpToDate',
  stale: 'ingest.stateStale',
  failed: 'ingest.stateFailed',
}

export function stateBucket(state: RowState): StateBucket {
  if (state === 'Ingested') return 'upToDate'
  if (state === 'Stale') return 'stale'
  if (state === 'Failed') return 'failed'
  return 'notPushed'
}

export function stateLabelKey(state: RowState): string {
  return STATE_LABEL_KEYS[stateBucket(state)]
}

/**
 * Join the live stores list with the document's per-store links.
 * Order follows the stores list (alphabetic from the API). Missing
 * links default to `NotPushed`.
 */
export function buildRows(
  stores: readonly StoreInfo[],
  storeLinks: readonly DocStoreLink[] | undefined,
): IngestRow[] {
  const linkBySlug = new Map<string, DocStoreLink>((storeLinks ?? []).map((l) => [l.store, l]))
  return stores.map((s) => {
    const link = linkBySlug.get(s.slug)
    return {
      slug: s.slug,
      name: s.name,
      kind: s.type,
      connected: s.connected,
      state: link?.state ?? 'NotPushed',
      pushedAt: link?.pushedAt ?? null,
    }
  })
}

/**
 * Number of stale rows that are also push-eligible (connected). This
 * is what the "Ingest into N stale stores" button shows AND what
 * `onPushAll` actually iterates over — the two must agree, otherwise
 * the button claims to push more than it does.
 */
export function countStalePushable(rows: readonly IngestRow[]): number {
  return rows.filter((r) => r.state === 'Stale' && r.connected).length
}

export interface DiffSummary {
  added: number
  modified: number
  removed: number
  unchanged: number
}

/** Tally diff entries by status. Unknown statuses are silently ignored. */
export function summarizeDiff(diffs: readonly ChunkDiff[]): DiffSummary {
  const tally: Record<ChunkDiffStatus, number> = {
    added: 0,
    modified: 0,
    removed: 0,
    unchanged: 0,
  }
  for (const d of diffs) tally[d.status] += 1
  return tally
}

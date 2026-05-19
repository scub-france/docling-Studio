/**
 * Pure helpers for the Ingest view (#225, redesigned in #283).
 *
 * Extracted from `DocIngestTab.vue` so the row-state derivation,
 * stale-count, diff-summary, and modal-default-selection logic can
 * be unit-tested without a DOM environment (the frontend doesn't
 * ship `@vue/test-utils` / `happy-dom` today). The component imports
 * these directly — keep them dependency-free (no Vue, no i18n, no
 * HTTP).
 */
import type {
  ChunkDiff,
  ChunkDiffStatus,
  DocStoreLink,
  DocumentLifecycleState,
} from '../shared/types'
import type { StoreInfo } from '../features/store/api'
import type { ChunkPushEntry } from '../features/chunks/api'

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

// ---------------------------------------------------------------------------
// Launch dialog (#283)
// ---------------------------------------------------------------------------

export type IngestLaunchStatus = 'idle' | 'running' | 'success' | 'failed'

/**
 * Per-row state inside the modal. Mirrors `IngestRow` for the rows
 * but also tracks the multi-select state + per-row push outcome
 * while the modal runs.
 */
export interface LaunchRow extends IngestRow {
  selected: boolean
  status: IngestLaunchStatus
  errorMessage: string | null
}

/**
 * Initial selection rule: a row is pre-selected when it's a real
 * push candidate — connected AND in a state that warrants pushing
 * (Stale or NotPushed). Up-to-date and disconnected rows start
 * unchecked; the user can opt-in.
 */
export function defaultLaunchSelection(rows: readonly IngestRow[]): LaunchRow[] {
  return rows.map((row) => ({
    ...row,
    selected: row.connected && (row.state === 'Stale' || row.state === 'NotPushed'),
    status: 'idle',
    errorMessage: null,
  }))
}

/** Whether the Confirm button should be enabled — at least one row selected. */
export function hasSelection(rows: readonly LaunchRow[]): boolean {
  return rows.some((r) => r.selected)
}

/** Slugs the modal will push to, in stable order (stores list order). */
export function selectedSlugs(rows: readonly LaunchRow[]): string[] {
  return rows.filter((r) => r.selected).map((r) => r.slug)
}

/** Whether the modal can close cleanly (no still-running rows). */
export function isLaunchDone(rows: readonly LaunchRow[]): boolean {
  return rows.every((r) => r.status !== 'running')
}

/**
 * Did the launch leave at least one store successfully pushed?
 * Drives whether the parent should refetch the document
 * (storeLinks update + history feed refresh).
 */
export function anyLaunchSucceeded(rows: readonly LaunchRow[]): boolean {
  return rows.some((r) => r.status === 'success')
}

// ---------------------------------------------------------------------------
// History list (#283)
// ---------------------------------------------------------------------------

/**
 * Display-ready shape for a row of the Ingest tab history list.
 * Resolved fields come from the backend join (storeName / storeKind);
 * the `displayName` falls back to the immutable storeId if the store
 * was deleted after the push.
 */
export interface HistoryDisplayEntry {
  id: string
  displayName: string
  storeKind: string | null
  chunkCount: number
  pushedAt: string | null
  chunksetHash: string
  /** True when the store row was removed after this push landed. */
  storeDeleted: boolean
}

export function toHistoryEntry(entry: ChunkPushEntry): HistoryDisplayEntry {
  const storeDeleted = entry.storeName === null && entry.storeSlug === null
  return {
    id: entry.id,
    displayName: entry.storeName ?? entry.storeSlug ?? entry.storeId,
    storeKind: entry.storeKind,
    chunkCount: entry.chunkCount,
    pushedAt: entry.pushedAt,
    chunksetHash: entry.chunksetHash,
    storeDeleted,
  }
}

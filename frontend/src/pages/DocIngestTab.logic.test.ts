/**
 * Tests for the Ingest view's pure helpers (#225).
 *
 * Pure-function tests only — the frontend doesn't ship a DOM test
 * environment today (no `@vue/test-utils` / `happy-dom`), so the
 * full `DocIngestTab.vue` is not mountable. Instead, the
 * row-building, stale-count, and diff-summary logic was extracted
 * into `DocIngestTab.logic.ts` and covered here.
 *
 * Critical invariants pinned by these tests:
 *   - `countStalePushable` matches what `onPushAll` actually iterates
 *     over (stale AND connected). The button label and the action
 *     must agree.
 *   - Missing store-links default to `NotPushed`, not crash.
 *   - The diff tally never returns NaN / undefined counts.
 */
import { describe, expect, it } from 'vitest'

import type { ChunkDiff, DocStoreLink } from '../shared/types'
import type { StoreInfo } from '../features/store/api'

import {
  STATE_LABEL_KEYS,
  buildRows,
  countStalePushable,
  stateBucket,
  stateLabelKey,
  summarizeDiff,
} from './DocIngestTab.logic'

function makeStore(overrides: Partial<StoreInfo> = {}): StoreInfo {
  return {
    name: 'Store',
    slug: 'store',
    type: 'OpenSearch',
    embedder: 'bge-m3',
    isDefault: false,
    connected: true,
    documentCount: 0,
    chunkCount: 0,
    ...overrides,
  }
}

describe('stateBucket', () => {
  it.each([
    ['Ingested', 'upToDate'],
    ['Stale', 'stale'],
    ['Failed', 'failed'],
    ['NotPushed', 'notPushed'],
    // Any unknown / not-yet-pushed state collapses to notPushed.
    ['Uploaded', 'notPushed'],
    ['Parsed', 'notPushed'],
  ] as const)('maps %s → %s', (state, bucket) => {
    expect(stateBucket(state)).toBe(bucket)
  })
})

describe('stateLabelKey', () => {
  it('returns the i18n key for the matching bucket', () => {
    expect(stateLabelKey('Ingested')).toBe('ingest.stateUpToDate')
    expect(stateLabelKey('Stale')).toBe('ingest.stateStale')
    expect(stateLabelKey('Failed')).toBe('ingest.stateFailed')
    expect(stateLabelKey('NotPushed')).toBe('ingest.stateNotPushed')
  })

  it('STATE_LABEL_KEYS covers every bucket', () => {
    expect(Object.keys(STATE_LABEL_KEYS).sort()).toEqual([
      'failed',
      'notPushed',
      'stale',
      'upToDate',
    ])
  })
})

describe('buildRows', () => {
  it('joins stores with their per-doc links', () => {
    const stores: StoreInfo[] = [
      makeStore({ slug: 'rh', name: 'RH', type: 'OpenSearch' }),
      makeStore({ slug: 'neo', name: 'Neo4j Local', type: 'Neo4j' }),
    ]
    const links: DocStoreLink[] = [
      { store: 'rh', state: 'Stale', pushedAt: '2026-05-01T00:00:00Z' },
    ]
    const rows = buildRows(stores, links)
    expect(rows).toEqual([
      {
        slug: 'rh',
        name: 'RH',
        kind: 'OpenSearch',
        connected: true,
        state: 'Stale',
        pushedAt: '2026-05-01T00:00:00Z',
      },
      {
        slug: 'neo',
        name: 'Neo4j Local',
        kind: 'Neo4j',
        connected: true,
        state: 'NotPushed',
        pushedAt: null,
      },
    ])
  })

  it('treats missing storeLinks as no links (every row NotPushed)', () => {
    const stores: StoreInfo[] = [makeStore({ slug: 'a' }), makeStore({ slug: 'b' })]
    const rows = buildRows(stores, undefined)
    expect(rows.map((r) => r.state)).toEqual(['NotPushed', 'NotPushed'])
    expect(rows.every((r) => r.pushedAt === null)).toBe(true)
  })

  it('preserves the stores order (the API decides ordering, not the doc)', () => {
    const stores: StoreInfo[] = [
      makeStore({ slug: 'b' }),
      makeStore({ slug: 'a' }),
      makeStore({ slug: 'c' }),
    ]
    const rows = buildRows(stores, [])
    expect(rows.map((r) => r.slug)).toEqual(['b', 'a', 'c'])
  })

  it('forwards the connected flag from the store, not the link', () => {
    // The link tells us "the doc was pushed once" — it says nothing
    // about whether the store is reachable right now.
    const stores: StoreInfo[] = [makeStore({ slug: 'down', connected: false })]
    const links: DocStoreLink[] = [
      { store: 'down', state: 'Ingested', pushedAt: '2026-04-01T00:00:00Z' },
    ]
    const rows = buildRows(stores, links)
    expect(rows[0].connected).toBe(false)
    expect(rows[0].state).toBe('Ingested')
  })
})

describe('countStalePushable', () => {
  it('counts only Stale + connected rows', () => {
    const rows = buildRows(
      [
        makeStore({ slug: 'a', connected: true }),
        makeStore({ slug: 'b', connected: true }),
        // disconnected — Stale but not pushable
        makeStore({ slug: 'c', connected: false }),
        // connected but not Stale
        makeStore({ slug: 'd', connected: true }),
      ],
      [
        { store: 'a', state: 'Stale', pushedAt: '2026-04-01T00:00:00Z' },
        { store: 'b', state: 'Stale', pushedAt: '2026-04-01T00:00:00Z' },
        { store: 'c', state: 'Stale', pushedAt: '2026-04-01T00:00:00Z' },
        { store: 'd', state: 'Ingested', pushedAt: '2026-04-01T00:00:00Z' },
      ],
    )
    // 2 stale + connected. `c` is stale but unreachable; `d` is up-to-date.
    expect(countStalePushable(rows)).toBe(2)
  })

  it('is 0 when nothing is stale', () => {
    const rows = buildRows([makeStore({ slug: 'a' })], [])
    expect(countStalePushable(rows)).toBe(0)
  })
})

describe('summarizeDiff', () => {
  it('tallies the four statuses', () => {
    const diffs: ChunkDiff[] = [
      { chunkId: '1', status: 'added' },
      { chunkId: '2', status: 'added' },
      { chunkId: '3', status: 'modified' },
      { chunkId: '4', status: 'removed' },
      { chunkId: '5', status: 'unchanged' },
      { chunkId: '6', status: 'unchanged' },
      { chunkId: '7', status: 'unchanged' },
    ]
    expect(summarizeDiff(diffs)).toEqual({
      added: 2,
      modified: 1,
      removed: 1,
      unchanged: 3,
    })
  })

  it('returns zeros for an empty diff (never undefined)', () => {
    expect(summarizeDiff([])).toEqual({
      added: 0,
      modified: 0,
      removed: 0,
      unchanged: 0,
    })
  })
})

// ---------------------------------------------------------------------------
// Launch modal (#283)
// ---------------------------------------------------------------------------

import {
  anyLaunchSucceeded,
  defaultLaunchSelection,
  hasSelection,
  isLaunchDone,
  selectedSlugs,
  toHistoryEntry,
  type LaunchRow,
} from './DocIngestTab.logic'
import type { ChunkPushEntry } from '../features/chunks/api'

describe('defaultLaunchSelection', () => {
  it('preselects connected + (stale OR not pushed) rows only', () => {
    const rows = buildRows(
      [
        makeStore({ slug: 'a', connected: true }),
        makeStore({ slug: 'b', connected: true }),
        // disconnected but stale — NOT preselected (can't push to it)
        makeStore({ slug: 'c', connected: false }),
        // connected + up-to-date — NOT preselected (nothing to do)
        makeStore({ slug: 'd', connected: true }),
      ],
      [
        { store: 'a', state: 'Stale', pushedAt: '2026-05-01T00:00:00Z' },
        { store: 'b', state: 'NotPushed', pushedAt: null }, // hypothetical
        { store: 'c', state: 'Stale', pushedAt: '2026-05-01T00:00:00Z' },
        { store: 'd', state: 'Ingested', pushedAt: '2026-05-01T00:00:00Z' },
      ],
    )
    const launch = defaultLaunchSelection(rows)
    const selected = launch.filter((r) => r.selected).map((r) => r.slug)
    // `b` defaults to NotPushed via the missing-link path (no
    // storeLinks row); included here for completeness.
    expect(selected.sort()).toEqual(['a', 'b'])
  })

  it('every row starts idle with no error', () => {
    const rows = buildRows([makeStore({ slug: 'a' })], [])
    const launch = defaultLaunchSelection(rows)
    expect(launch[0].status).toBe('idle')
    expect(launch[0].errorMessage).toBeNull()
  })
})

describe('hasSelection', () => {
  it('is true when at least one row is selected', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'NotPushed',
        pushedAt: null,
        selected: false,
        status: 'idle',
        errorMessage: null,
      },
      {
        slug: 'b',
        name: 'b',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'idle',
        errorMessage: null,
      },
    ]
    expect(hasSelection(rows)).toBe(true)
  })

  it('is false when nothing is selected', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'NotPushed',
        pushedAt: null,
        selected: false,
        status: 'idle',
        errorMessage: null,
      },
    ]
    expect(hasSelection(rows)).toBe(false)
  })
})

describe('selectedSlugs', () => {
  it('preserves the row order', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'c',
        name: 'c',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'idle',
        errorMessage: null,
      },
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: false,
        status: 'idle',
        errorMessage: null,
      },
      {
        slug: 'b',
        name: 'b',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'idle',
        errorMessage: null,
      },
    ]
    expect(selectedSlugs(rows)).toEqual(['c', 'b'])
  })
})

describe('isLaunchDone', () => {
  it('is true when no row is in running state', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'success',
        errorMessage: null,
      },
      {
        slug: 'b',
        name: 'b',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'failed',
        errorMessage: 'down',
      },
    ]
    expect(isLaunchDone(rows)).toBe(true)
  })

  it('is false while at least one row is running', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'running',
        errorMessage: null,
      },
    ]
    expect(isLaunchDone(rows)).toBe(false)
  })
})

describe('anyLaunchSucceeded', () => {
  it('is true on at least one success row', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'failed',
        errorMessage: 'x',
      },
      {
        slug: 'b',
        name: 'b',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'success',
        errorMessage: null,
      },
    ]
    expect(anyLaunchSucceeded(rows)).toBe(true)
  })

  it('is false when every run failed', () => {
    const rows: LaunchRow[] = [
      {
        slug: 'a',
        name: 'a',
        kind: 'os',
        connected: true,
        state: 'Stale',
        pushedAt: null,
        selected: true,
        status: 'failed',
        errorMessage: 'x',
      },
    ]
    expect(anyLaunchSucceeded(rows)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// History list (#283)
// ---------------------------------------------------------------------------

describe('toHistoryEntry', () => {
  function makeEntry(overrides: Partial<ChunkPushEntry> = {}): ChunkPushEntry {
    return {
      id: 'push-1',
      documentId: 'd-1',
      storeId: 's-1',
      storeSlug: 'rh-corpus',
      storeName: 'RH Corpus',
      storeKind: 'opensearch',
      chunksetHash: 'abc123def456',
      chunkCount: 11,
      pushedAt: '2026-05-19T14:32:00+00:00',
      ...overrides,
    }
  }

  it('uses storeName when present', () => {
    const display = toHistoryEntry(makeEntry())
    expect(display.displayName).toBe('RH Corpus')
    expect(display.storeDeleted).toBe(false)
  })

  it('falls back to storeSlug when name is null', () => {
    const display = toHistoryEntry(makeEntry({ storeName: null }))
    expect(display.displayName).toBe('rh-corpus')
    expect(display.storeDeleted).toBe(false)
  })

  it('flags storeDeleted when both name and slug are null', () => {
    const display = toHistoryEntry(makeEntry({ storeName: null, storeSlug: null, storeKind: null }))
    expect(display.displayName).toBe('s-1')
    expect(display.storeDeleted).toBe(true)
  })

  it('forwards all the metric fields', () => {
    const display = toHistoryEntry(makeEntry())
    expect(display.chunkCount).toBe(11)
    expect(display.chunksetHash).toBe('abc123def456')
    expect(display.pushedAt).toBe('2026-05-19T14:32:00+00:00')
  })
})

# Design: Backend audit — enforce DDD granularity, strip UX-shaped routes

<!--
Status lifecycle: Draft → In review → Accepted → Implemented (or Superseded).
This document is the audit report itself — its conclusions get applied
in the same PR that lands it (CLAUDE.md update, route classification,
follow-up issues for legacy retirements).
-->

- **Issue:** #269
- **Title on issue:** [CHORE] Backend audit — enforce DDD granularity, strip UX-shaped routes
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-05-12
- **Status:** Accepted
- **Target milestone:** 0.6.1 — Stabilisation
- **Impacted layers:** backend: `api/` (audit only — no routes added/removed in this PR)
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Decoupling · Documentation
- **ADR spawned?:** no

---

## 1. Problem

Throughout 0.6.0 and 0.6.1, several backend routes were added under
`/api/*` to support specific UI flows: the doc workspace (Parse / Chunk
views), the Strategy popover, the History drawer, the in-place
`+ New analysis` trigger. The architectural rule for Docling Studio is
explicit:

> **The backend exposes DDD-granular services, not screens.** Any
> cross-call orchestration belongs in the frontend's lower layers
> (`features/*/api.ts` and `features/*/store.ts`), never in the backend.

This audit walks every route currently mounted under `/api/*`, classifies
it, and decides what — if anything — needs to be split, removed, or
re-justified.

## 2. Goals

- [x] Inventory every route under `/api/*` introduced or modified during
      0.6.0 / 0.6.1.
- [x] Classify each route as DDD-correct / UX-shaped / Exception.
- [x] For UX-shaped routes: justify, split, or file a follow-up.
- [x] Encode the rule in `docs/architecture.md` (and mirror it in
      `document-parser/CLAUDE.md`, which is local-only / gitignored
      but consumed by Claude Code on every session).
- [x] CI green (no functional changes — audit-only PR).

## 3. Non-goals

- Refactoring routes added **before** 0.6.0 (Studio surface — gated
  behind `studio_mode_enabled` since #257, scheduled for retirement
  separately).
- Adding new functionality.
- Deleting legacy `/api/analyses/{id}/rechunk` &  `/api/analyses/{id}/chunks/*`
  endpoints (Studio-only consumers; tracked as a separate retirement
  ticket — see §10 follow-ups).

## 4. Context & constraints

### 4.1 Reference rule

From the project's coding standards + the agreed direction in the 0.6.1
plan (T7 / #268, T6 / #267, T5 / #266):

- **Granularity:** one route ≈ one domain operation. CRUD on the
  canonical chunkset is *chunks/*; CRUD on stores is *stores/*; etc.
- **Orchestration:** if a UI screen needs to call N routes to render or
  submit, those N calls are sequenced **client-side** (in a Pinia
  store action). The backend never grows a "screen-shaped" aggregate
  route just because it would shorten one frontend function.
- **Exception clause:** a route may legitimately bundle several
  operations if the bundling provides an **atomicity / transactional**
  guarantee the client cannot achieve by chaining calls (e.g. "merge
  these N chunks → audit row + INSERT + DELETEs, all-or-nothing").

### 4.2 Inventory method

`grep -rn "@router\.(get|post|patch|delete|put)" document-parser/api/`
on `release/0.6.1` HEAD as of this commit. 41 routes total, grouped by
top-level prefix.

## 5. Audit findings — classification

Each row carries: method · path · classification · introduced (issue#) ·
notes. **DDD-correct** = single domain concept, no UX coupling.
**Atomicity exception** = bundle justified by transactional guarantee.
**Legacy** = pre-0.6.0 Studio-specific, gated behind `studio_mode_enabled`,
to be retired separately.

### 5.1 `/api/health`

| Method | Path | Class | Notes |
|---|---|---|---|
| GET | `/api/health` | **DDD-correct** | Status + feature-flag surface. Excluded from rate limiter. |

### 5.2 `/api/documents/*` (mounted by `documents.py`, `document_chunks.py`, `document_versions.py`, `graph.py`, `reasoning.py`)

| Method | Path | Class | Notes |
|---|---|---|---|
| GET | `/api/documents` | DDD-correct | List |
| POST | `/api/documents/upload` | DDD-correct | Multipart upload |
| GET | `/api/documents/{id}` | DDD-correct | Detail |
| DELETE | `/api/documents/{id}` | DDD-correct | Delete |
| GET | `/api/documents/{id}/preview` | DDD-correct | Generates page image — single artefact, side-effect free |
| GET | `/api/documents/{id}/tree` | DDD-correct | Returns the Docling extraction tree projected from the latest completed analysis. Read-only projection — not a screen-shape. |
| GET | `/api/documents/{id}/chunks` | DDD-correct | List canonical chunkset |
| POST | `/api/documents/{id}/chunks` | DDD-correct | Add chunk |
| PATCH | `/api/documents/{id}/chunks/{chunkId}` | DDD-correct | Update chunk |
| DELETE | `/api/documents/{id}/chunks/{chunkId}` | DDD-correct | Soft-delete + audit |
| POST | `/api/documents/{id}/chunks/{chunkId}/split` | **Atomicity exception** | Single SPLIT writes two new chunks + an audit row atomically. Splitting client-side (delete + 2× insert) would race the audit log. |
| POST | `/api/documents/{id}/chunks/merge` | **Atomicity exception** | N→1 merge with atomic audit row. Same rationale as split. |
| POST | `/api/documents/{id}/rechunk` | **Atomicity exception** | Replaces the whole chunkset against the latest analysis JSON. Sequencing this in the frontend (delete N + insert M + audit) would leak partial states. The version-recording side hook (#267) also runs atomically here. |
| GET | `/api/documents/{id}/diff?store=` | DDD-correct | Read-only comparison projection. |
| POST | `/api/documents/{id}/chunks/push` | DDD-correct | Push as a single command — the chunkset hash + the push row are written atomically. |
| GET | `/api/documents/{id}/versions` | DDD-correct | List version snapshots (#267) |
| POST | `/api/documents/{id}/versions/{vid}/restore` | **Atomicity exception** | Wipes live chunks + reinserts from snapshot + audit rows, all in one transaction. Doing this client-side would split the audit log. |
| GET | `/api/documents/{id}/graph` | DDD-correct | Graph projection from Neo4j |
| GET | `/api/documents/{id}/reasoning-graph` | DDD-correct | Variant of the above, scoped to reasoning |
| POST | `/api/documents/{id}/reasoning` | DDD-correct | Trigger an agent run — single command |

### 5.3 `/api/analyses/*`

| Method | Path | Class | Notes |
|---|---|---|---|
| POST | `/api/analyses` | DDD-correct | Create analysis job |
| GET | `/api/analyses` (with optional `?documentId=`) | DDD-correct | List analyses |
| GET | `/api/analyses/{id}` | DDD-correct | Detail |
| POST | `/api/analyses/{id}/rechunk` | **Legacy** | Studio-only chunking; replaced by `/api/documents/{id}/rechunk` (#256). Kept for the gated Studio surface. |
| PATCH | `/api/analyses/{id}/chunks/{chunkIndex}` | **Legacy** | Studio-only chunk edit; replaced by `/api/documents/{id}/chunks/{chunkId}` PATCH. |
| DELETE | `/api/analyses/{id}/chunks/{chunkIndex}` | **Legacy** | Same — replaced. |
| DELETE | `/api/analyses/{id}` | DDD-correct | Delete analysis |

### 5.4 `/api/stores/*`

| Method | Path | Class | Notes |
|---|---|---|---|
| GET | `/api/stores` | DDD-correct | List + per-store connection probe |
| POST | `/api/stores` | DDD-correct | Create |
| GET | `/api/stores/{slug}` | DDD-correct | Detail |
| PATCH | `/api/stores/{slug}` | DDD-correct | Update config |
| DELETE | `/api/stores/{slug}` | DDD-correct | Delete |
| GET | `/api/stores/{slug}/documents` | DDD-correct | Docs in store with last-push state |
| DELETE | `/api/stores/{slug}/documents/{docId}` | DDD-correct | Unlink |

### 5.5 `/api/ingestion/*`

| Method | Path | Class | Notes |
|---|---|---|---|
| POST | `/api/ingestion/{analysisId}` | **Legacy** | Takes `analysisId`, predates the doc-centric pipeline. Should migrate to `POST /api/documents/{id}/chunks/push` (already exists). Studio still uses it; retirement tracked in §10. |
| DELETE | `/api/ingestion/{docId}` | DDD-correct | Remove from index |
| GET | `/api/ingestion/status` | DDD-correct | Service status |
| GET | `/api/ingestion/search` | DDD-correct | RAG playground search |

## 6. Conclusion

**No UX-shaped routes** were found. Every route maps to a single domain
concept or is an atomicity exception (split / merge / rechunk / restore
of the chunkset). The three legacy `/api/analyses/{id}/*` chunk-edition
endpoints are pre-0.6.0 Studio remnants gated behind `studio_mode_enabled`
and tracked for retirement separately. `POST /api/ingestion/{analysisId}`
falls in the same bucket.

The atomicity exceptions are documented in their respective service
docstrings; the audit rule is encoded in `docs/architecture.md`
(tracked) and mirrored in `document-parser/CLAUDE.md` (local-only,
fed to Claude Code on every session).

## 7. API & data contract

No wire changes. Audit-only PR.

## 8. Risks & mitigations

| Risk | Audit dimension | Mitigation |
|---|---|---|
| Future PRs introduce a UX-shaped route under time pressure | Decoupling | The rule is now in `CLAUDE.md`, surfaced on every onboarding read |
| Legacy `/api/analyses/{id}/*` retirement is forgotten | Decoupling · Documentation | Tracked as a follow-up issue (§10), explicit retirement criterion |

## 9. Testing strategy

No code changes. Existing backend suite (622 passing) covers the routes
classified above. The audit doc itself is the deliverable.

## 10. Rollout & follow-ups

### Follow-up issues

To be filed after this PR merges:

- **[CHORE] Retire `/api/analyses/{id}/{rechunk,chunks/*}`** — once
  the Studio surface stops shipping (final `STUDIO_MODE_ENABLED=false`
  rollout in production), drop these three endpoints.
- **[CHORE] Migrate `POST /api/ingestion/{analysisId}` to a
  doc-centric route** — collapse with the existing
  `POST /api/documents/{id}/chunks/push`.

These are out of scope for #269 (audit-only).

## 11. Open questions

None — the audit is conclusive.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/269
- **Related design docs:** `docs/design/256-doc-tab-chunk-mode-404.md` (the 9-route plan that introduced most of the doc-centric chunks routes), `docs/design/264-linked-view-preview-chunks-layers.md` (P2/P3 rule — orchestration in the frontend, not the backend)
- **Coding standards:** `document-parser/CLAUDE.md`
- **Architecture:** `docs/architecture.md`

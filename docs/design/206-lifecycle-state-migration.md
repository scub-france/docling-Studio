# Design: Migrate existing documents to the new lifecycle state model

- **Issue:** #206
- **Title on issue:** [CHORE] Migrate existing documents to the new lifecycle state model
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: persistence · services · infra (CLI) · frontend (none)
- **Audit dimensions likely touched:** CI/Build · Tests · Documentation · Security
- **ADR spawned?:** no

---

## 1. Problem

#202, #203, and #205 introduce four new tables / columns: `documents.lifecycle_state`, `stores`, `document_store_links`, `chunks`, `chunk_edits`, `chunk_pushes`. Existing tenants already have documents, analysis jobs, and chunks living in `analysis_jobs.chunks_json` plus rows in OpenSearch. After deploy, these documents must appear in `/docs` with sensible state — otherwise the page looks broken (every doc shows `Uploaded` or unknown).

This issue ships an idempotent migration that backfills:
- `documents.lifecycle_state` and `lifecycle_state_at`.
- One `stores` row (the `default` seeded by #203, no-op if already present).
- One `document_store_links` row per document already represented in OpenSearch under the legacy index.
- `chunks` rows materialized from existing `analysis_jobs.chunks_json`.
- `chunk_pushes` rows reconstructed for documents currently indexed.

It also reindexes from `docling-studio-chunks` to `docling-studio-default` if needed, so the new store-aware code can read them.

## 2. Goals

- [ ] Idempotent CLI command `python -m document_parser.tools.migrate_06` (re-runs safely; second run is a no-op).
- [ ] `--dry-run` flag prints what would change without writing.
- [ ] Inference rules below produce a sensible state for every existing document.
- [ ] Per-tenant counts logged at the end (parsed=N, chunked=N, ingested=N, failed=N).
- [ ] Documented in `docs/runbooks/release-0.6.0-migration.md`.
- [ ] Tested on a snapshot DB representing the three relevant pre-states (no analysis, completed analysis, indexed in OpenSearch).

## 3. Non-goals

- Re-running ingestion. The migration only touches metadata; it does not re-embed.
- A web UI for migration progress — operator-only, run via CLI.
- Migrating tenants on environments that have already adopted parts of the new schema (e.g. a partial pre-release deploy) — out of scope; an emergency hotfix path is documented separately.
- Moving to a new vector backend — out of scope.

## 4. Context & constraints

### Existing code surface

- `document-parser/persistence/database.py` — `_run_migrations()` runs schema DDL on app start.
- `document-parser/persistence/document_repo.py`, `analysis_repo.py` — read paths.
- `document-parser/infra/opensearch_store.py` — read access to existing OpenSearch index.
- New repos from #203 / #205: `store_repo.py`, `document_store_link_repo.py`, `chunk_repo.py`, `chunk_edit_repo.py`.

### Hexagonal Architecture constraints

- The migration is a **CLI script** in `document-parser/tools/migrate_06.py`. It uses repositories only — never raw SQL outside of repo modules. This keeps the upgrade path testable like any service.
- The reindex helper (`docling-studio-chunks → docling-studio-default`) lives in `infra/opensearch_store.py` as a method, called by the script.

### Hard constraints

- Idempotent: re-running on an already-migrated DB makes zero writes.
- Resumable: a crash mid-run can be restarted; checkpoints stored in a tiny `migration_progress` table (rows: `(name, completed_at)`).
- No assumption about uptime: the script must work on a quiesced DB OR a live one (transactions short, single-row scope).
- Read-only on OpenSearch by default; write happens only when the operator explicitly passes `--reindex-default-store`.

### Deployment modes

Run once per environment (`local`, `staging`, `prod`). HF Space deployments — same script, run by the deploy step before the new image starts serving traffic.

## 5. Proposed design

### 5.1 Domain

No new domain code. The migration is a coordinator over existing repos.

### 5.2 Persistence

The schema additions ship in #202 / #203 / #205 migrations (already applied at app start). This issue contributes:

```sql
CREATE TABLE IF NOT EXISTS migration_progress (
    name        TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL
);
```

This is the only new table. It records each migration step's completion to enable resumability.

### 5.3 Infra adapters

`OpenSearchStore.copy_legacy_to_default(*, dry_run: bool) -> int` —
1. If `docling-studio-chunks` exists and `docling-studio-default` does not, create the new index with the same mapping.
2. Reindex via `_reindex_op` (OpenSearch reindex API) from legacy → default.
3. Add a read-only alias `docling-studio-chunks → docling-studio-default`.
4. Returns the number of documents copied.

### 5.4 Services

`document-parser/services/migration_06_service.py` — orchestrator with one method per step. Each step is bracketed by:

```python
if not progress.is_done(step_name):
    do_step(...)
    progress.mark_done(step_name)
```

Steps:

1. **`seed_default_store`** — `INSERT OR IGNORE INTO stores (...) VALUES ('default', ...)`. (Already in #203's migration; this step is a guard for older deploys that skipped the seed.)
2. **`backfill_document_lifecycle_state`** — for each document, infer state:
   - Has at least one `analysis_jobs` row with `status=COMPLETED` and a non-null `chunks_json` → `Chunked` (refined below).
   - Has at least one row indexed in OpenSearch (legacy or default index) → `Ingested`.
   - Has only `analysis_jobs` rows with `status=COMPLETED` and no `chunks_json` → `Parsed`.
   - Has only `analysis_jobs` rows with `status=FAILED` → `Failed`.
   - Else → `Uploaded`.
3. **`materialize_chunks_from_chunks_json`** — for each `analysis_jobs` row with non-null `chunks_json`, parse and insert rows into `chunks` table. Stable id derivation: `f"chunk-{document_id}-{sequence:05d}-{sha256(text)[:8]}"` so re-runs are deterministic.
4. **`backfill_links_from_opensearch`** — for each document, query OpenSearch (default index, then legacy as fallback) for the count of indexed chunks. If non-zero:
   - Insert `document_store_links` row (state = `Ingested`).
   - Compute the chunkset hash via #204's function over the materialized `chunks`.
   - Set `link.chunkset_hash`.
   - Insert a `chunk_pushes` row with the materialized chunk ids (best-effort: ordered by sequence).
5. **`reaggregate_document_lifecycle`** — recompute the doc state by combining the link states (#203's aggregation rule) and update `documents.lifecycle_state` accordingly. This may upgrade or downgrade the value set in step 2 (e.g. `Chunked → Ingested`).
6. **`copy_legacy_index`** *(optional, behind `--reindex-default-store`)* — call `OpenSearchStore.copy_legacy_to_default()`.

Each step is wrapped in its own transaction; partial failure leaves earlier steps committed.

### 5.5 API

None. CLI only.

### 5.6 Frontend

None.

### 5.7 Cross-cutting

- Logging: structured at `INFO` per step, at `ERROR` per failed item with `doc_id`. End summary printed to stdout in a fixed table.
- Configuration via CLI flags only (no env vars introduced for this script):

```
python -m document_parser.tools.migrate_06 \
   [--dry-run] \
   [--reindex-default-store] \
   [--limit N] \
   [--only-step <step_name>]
```

- Documentation: `docs/runbooks/release-0.6.0-migration.md` describes the operator flow (backup → run dry-run → run real → validate via `/api/documents`).

## 6. Alternatives considered

### Alternative A — Schema migration applies everything at app boot

- **Summary:** Embed inference logic in `_run_migrations()` so the app starts and self-heals.
- **Why not:** Migration is observable and debuggable as a CLI; baking it into boot time risks slow startup and silent failures. Operators want to run it during a maintenance window with a dry-run first.

### Alternative B — Migrate on demand (lazy)

- **Summary:** Add a "needs migration" check at runtime, materialize chunks for a doc only on first read.
- **Why not:** Surfaces the partial state in the API (`stores: []` for unmigrated docs even if they are indexed). The library page (#211) becomes a half-true representation of reality. Eager migration is simpler.

### Alternative C — Run only the schema; let users re-ingest manually

- **Summary:** Skip backfill; users re-trigger ingestion from the UI as needed.
- **Why not:** A tenant with 10k docs cannot click 10k re-ingest buttons. The killer flow promises "your existing corpus already has state".

## 7. API & data contract

No API changes.

### Persistence schema

See §5.2 (one new table: `migration_progress`).

### CLI

```
python -m document_parser.tools.migrate_06 [flags]
```

All flags are documented in `--help`.

### Breaking changes

None.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Migration crashes mid-run | CI/Build | Medium | Medium | Error logs | Resumable via `migration_progress`; re-run picks up where it left off |
| Wrong inference for a doc edge case (e.g. multiple stores already) | DDD | Low | Medium | Operator validation (sample 10 docs by hand) | Dry-run lists changes; operator can `--only-step` to redo a single step |
| OpenSearch reindex copies bad data | Decoupling | Low | High | Diff in document counts | Reindex is opt-in (`--reindex-default-store`); operator runs it deliberately; alias keeps legacy reads working |
| Hash mismatch after migration (chunks materialized differ from what was indexed) | DDD | Medium | Medium | Newly-migrated link shows `Stale` immediately | Acceptable behaviour: it correctly tells the user "your indexed chunks may not match the current source"; operator can choose to re-ingest or leave as-is |
| Missing analysis-job rows for a doc | Tests | Low | Low | Doc shows `Uploaded` despite being indexed | Inference falls back to OpenSearch presence; if both empty, `Uploaded` is correct |

## 9. Testing strategy

### Backend — pytest

- **Unit (services):** `test_migration_inference.py` — table-driven: every `(analysis_state, has_chunks_json, indexed)` tuple → expected `lifecycle_state`.
- **Integration:** `test_migration_idempotency.py` — run twice → second run zero writes; mid-run abort + restart → final state matches one-shot run.
- **Persistence:** `test_chunks_materialization.py` — `chunks_json` → rows; ids deterministic (re-running produces same ids).

### Snapshot fixture

`document-parser/tests/fixtures/db_pre_06.sqlite` — handcrafted SQLite DB with three documents (uploaded only, completed analysis, indexed in OpenSearch via fake adapter). Migration runs against it and the resulting state is asserted.

### Manual QA

1. Snapshot prod DB.
2. Run `--dry-run` on the snapshot → review the printed plan.
3. Run for real on the snapshot → validate via `/api/documents` that every doc has a sensible `lifecycleState` and (where applicable) `stores`.
4. Run the same against prod during the maintenance window.

### Performance

The script is O(N_docs + N_chunks). For 10k docs / 500k chunks: target < 5 minutes on a single-node SQLite. No parallelism needed in 0.6.0.

## 10. Rollout & observability

### Release branch

`release/0.6.0`. The migration ships in the same release as #202 / #203 / #204 / #205 — operators run it after deploying the new code and before sending traffic.

### Feature flag

None.

### Observability

- Stdout summary table at the end:

  ```
  step                                   wrote   skipped
  seed_default_store                         0         1
  backfill_document_lifecycle_state         87         0
  materialize_chunks_from_chunks_json    14502         0
  backfill_links_from_opensearch            73        14
  reaggregate_document_lifecycle            73         0
  copy_legacy_index                          —         —
  total                                  14735        15
  ```

- Logs: per-step start / finish; per-error row.

### Rollback plan

- `migration_progress` rows can be deleted to force re-run a specific step.
- The new tables can be truncated or dropped (data is recoverable from `analysis_jobs.chunks_json` and OpenSearch).
- Reverting application code: the new tables stay populated but unused; safe.

## 11. Open questions

- Should the script open a *long* SQLite transaction or many small ones? **Decision:** many small (per-doc), to keep the DB writeable for the live app if the operator chooses to run the script while traffic is on.
- Hash mismatch on freshly-migrated docs (chunks materialized may differ from what was indexed) — should we *force-mark* them `Stale`, or trust the hash compare to do it implicitly? **Decision:** trust the compare. The result is identical and the path is uniform.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/206
- **Related issues:** #202 (lifecycle), #203 (per-store), #204 (hash), #205 (audit + chunks table)
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - Operations playbooks: `docs/operations/`

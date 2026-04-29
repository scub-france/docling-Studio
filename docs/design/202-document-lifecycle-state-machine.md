# Design: Document lifecycle state machine

- **Issue:** #202
- **Title on issue:** [FEATURE] Introduce Document lifecycle state machine
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: domain · persistence · services · api · frontend: features/document · shared
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Tests · Documentation
- **ADR spawned?:** no

---

## 1. Problem

Studio today tracks ingestion as a side-effect of an `AnalysisJob`. The only "state" a document carries is implicit — derived by joining the document with its latest analysis job (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`) and, separately, by checking whether OpenSearch holds rows for `doc_id`. There is no explicit, persisted lifecycle of the document itself.

This blocks the 0.6.0 doc-centric pivot: we cannot show a document library `/docs` with status badges, we cannot tell the user "this doc is ingested but stale on store X", and we cannot drive a chunks editor that knows whether its draft is committed. Every later feature in E3, E4, and E5 reads or transitions a document state.

This design introduces a first-class **document lifecycle** as a domain concept: a single canonical state on each document, validated transitions, persisted, and surfaced via the API.

## 2. Goals

- [ ] Add a `DocumentLifecycleState` enum to the domain with six states: `Uploaded`, `Parsed`, `Chunked`, `Ingested`, `Stale`, `Failed`.
- [ ] `Document` carries `lifecycle_state` (current state) + `lifecycle_state_at` (last transition timestamp).
- [ ] State transitions are validated in the domain layer; invalid transitions raise `InvalidLifecycleTransition`.
- [ ] State changes emit a domain event `DocumentLifecycleChanged(previous, current, at)`.
- [ ] Persisted via aiosqlite migration; existing rows default to `Uploaded` (refined by #206).
- [ ] Surfaced on the document API DTO (camelCase: `lifecycleState`, `lifecycleStateAt`).

## 3. Non-goals

- Per-`(doc, store)` state — that is **#203** and uses a different table.
- Auto-stale detection via hash — that is **#204**; this issue only declares the `Stale` state value.
- UI rendering of the badge — that is **#215**.
- Migrating production data — that is **#206**; this issue ships the schema + default value only.
- Refactoring `AnalysisJob.status`. The two concepts coexist: `AnalysisJob.status` describes **a single conversion attempt**; `Document.lifecycle_state` describes **the doc as a whole**.

## 4. Context & constraints

### Existing code surface

- `document-parser/domain/models.py` — `Document` dataclass (line 27), `AnalysisJob` (line 38), `AnalysisStatus` enum.
- `document-parser/domain/value_objects.py` — value objects.
- `document-parser/persistence/database.py` — `_MIGRATIONS` list and `_run_migrations()` checking PRAGMA `table_info()`.
- `document-parser/persistence/document_repo.py` — `DocumentRepository` (aiosqlite).
- `document-parser/api/documents.py` — REST endpoints.
- `document-parser/api/schemas.py` — Pydantic DTOs with `alias_generator=_to_camel`.
- `frontend/src/features/document/store.ts` and `api.ts`.

### Hexagonal Architecture constraints (backend)

- `DocumentLifecycleState` is a **value object** — it lives in `domain/value_objects.py` with zero imports from `api`/`persistence`/`infra`.
- The transition rules are domain logic — they live as methods on `Document` (or a small `DocumentLifecycle` policy module in `domain/`). No HTTP, no DB.
- `DocumentRepository` (the port) gains a write path for the new fields. The aiosqlite adapter is the only place that knows about the column.
- API layer translates the enum to camelCase string via Pydantic.

### Deployment modes

Both `latest-local` and `latest-remote` images use the same SQLite schema → migration applies to both. No HF Space-specific concern. No feature flag (the lifecycle is always on; only UI surfaces are flagged).

### Hard constraints

- SQLite schema additive only. No column drops, no rename. New column has a `DEFAULT` so existing rows do not break on read.
- API contract additive only. New fields appear; nothing is removed.
- `pages_json` stays snake_case (existing exception).

## 5. Proposed design

### 5.1 Domain

Add to `document-parser/domain/value_objects.py`:

```python
from enum import StrEnum

class DocumentLifecycleState(StrEnum):
    UPLOADED  = "Uploaded"
    PARSED    = "Parsed"
    CHUNKED   = "Chunked"
    INGESTED  = "Ingested"
    STALE     = "Stale"
    FAILED    = "Failed"
```

Allowed transitions (a directed graph; `* → Failed` always allowed):

```
Uploaded  → Parsed | Failed
Parsed    → Chunked | Failed
Chunked   → Ingested | Chunked | Failed       # re-chunking is allowed
Ingested  → Stale | Chunked | Failed          # re-ingest stays Ingested via 203
Stale     → Ingested | Chunked | Failed
Failed    → Uploaded | Parsed | Chunked       # explicit retry sets the new target
```

`Stale` is set by the auto-detect logic (#204) — never reached as a result of a manual action.

Add to `document-parser/domain/models.py`:

```python
@dataclass
class Document:
    ...
    lifecycle_state: DocumentLifecycleState = DocumentLifecycleState.UPLOADED
    lifecycle_state_at: datetime | None = None

    def transition_to(self, target: DocumentLifecycleState, *, now: datetime) -> "DocumentLifecycleChanged":
        if not _is_allowed(self.lifecycle_state, target):
            raise InvalidLifecycleTransition(self.lifecycle_state, target)
        previous = self.lifecycle_state
        self.lifecycle_state = target
        self.lifecycle_state_at = now
        return DocumentLifecycleChanged(self.id, previous, target, now)
```

`InvalidLifecycleTransition` lives in `domain/exceptions.py` (create if missing). `_is_allowed` is a pure function over a static transition table.

`DocumentLifecycleChanged` is a frozen dataclass in `domain/events.py`. No event bus is wired in 0.6.0 — the event is *returned* from the transition call so services can log / persist / publish later. This avoids introducing infra in this issue.

### 5.2 Persistence

Schema migration appended to `_MIGRATIONS` in `document-parser/persistence/database.py`:

```sql
ALTER TABLE documents ADD COLUMN lifecycle_state TEXT NOT NULL DEFAULT 'Uploaded';
ALTER TABLE documents ADD COLUMN lifecycle_state_at TEXT;
CREATE INDEX IF NOT EXISTS idx_documents_lifecycle_state ON documents(lifecycle_state);
```

The `_run_migrations()` PRAGMA check ensures idempotency — re-running on an already-migrated DB is a no-op. The index supports the `/docs` library filter by status (#212).

`DocumentRepository.save(doc)` and `update_lifecycle(doc_id, state, at)` are the two write paths. Read returns the columns directly populated into the dataclass.

### 5.3 Infra adapters

None. The lifecycle is database-only.

### 5.4 Services

`DocumentService` and `AnalysisService` are the two callers that drive transitions.

| Trigger | From | To | Caller |
|---|---|---|---|
| Upload completes | — | `Uploaded` | `DocumentService.upload()` |
| Parse succeeds | `Uploaded` (or `Failed` retry) | `Parsed` | `AnalysisService` |
| Chunking succeeds | `Parsed` (or `Chunked` re-chunk) | `Chunked` | `AnalysisService` |
| Ingestion succeeds | `Chunked` (or `Stale`) | `Ingested` | `IngestionService` (touched in #203) |
| Failure on any pipeline step | any | `Failed` | the failing service |

Transition calls are atomic with the underlying write (e.g., chunking writes `chunks_json` *and* transitions to `Chunked` in the same SQL transaction).

### 5.5 API

`DocumentResponse` (in `document-parser/api/schemas.py`) gains:

```python
class DocumentResponse(BaseModel):
    ...
    lifecycle_state: str = Field(serialization_alias="lifecycleState")
    lifecycle_state_at: datetime | None = Field(default=None, serialization_alias="lifecycleStateAt")
```

No new endpoint. The existing `GET /api/documents` and `GET /api/documents/{id}` start returning the two fields. No 4xx removal — purely additive.

`POST /api/documents/{id}/lifecycle` is **not** added in this issue; transitions are driven by pipeline events, not by the user.

### 5.6 Frontend — feature module

Touched: `frontend/src/features/document/`.

- `api.ts` — bump the `Document` type with `lifecycleState: DocumentLifecycleState` and `lifecycleStateAt: string | null`.
- `store.ts` — store retains the new fields as-is.
- No UI work — that is #211 / #215. This issue ships the typed surface only so #211 can render against it.

`shared/types.ts` gains a re-exported `DocumentLifecycleState` union literal type matching the backend enum.

### 5.7 Cross-cutting

- No feature flag. The lifecycle is permanent infrastructure.
- i18n: tooltip strings for the six states are added in `shared/i18n.ts`, keyed `lifecycle.<state>`. Used by #215.

## 6. Alternatives considered

### Alternative A — Reuse `AnalysisJob.status`

- **Summary:** Promote `AnalysisJob.status` to the document's state, removing the separate `Document.lifecycle_state`.
- **Why not:** `AnalysisJob` has a 1:N relationship with `Document` (a doc can be re-analyzed). The status of the *latest* job is not the same thing as the lifecycle of the *document*. It also conflates parse/chunk/ingest into one state machine, which #202–#205 explicitly want to separate.

### Alternative B — Computed state, no column

- **Summary:** Derive the state on-the-fly from analysis-job rows + OpenSearch presence.
- **Why not:** Joining + remote calls on every document list query is too expensive for `/docs` with 1k+ rows. A persisted column lets us index it for the filter (#212). The cost of denormalisation is one extra write per pipeline step.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET | `/api/documents` | — | `DocumentResponse[]` (now with `lifecycleState`, `lifecycleStateAt`) | No (additive) |
| GET | `/api/documents/{id}` | — | `DocumentResponse` (now with `lifecycleState`, `lifecycleStateAt`) | No (additive) |

### Persistence schema

```sql
ALTER TABLE documents ADD COLUMN lifecycle_state TEXT NOT NULL DEFAULT 'Uploaded';
ALTER TABLE documents ADD COLUMN lifecycle_state_at TEXT;
CREATE INDEX IF NOT EXISTS idx_documents_lifecycle_state ON documents(lifecycle_state);
```

Existing rows default to `Uploaded`; #206 refines them.

### Env vars / config

None.

### Breaking changes

Additive only.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Drift between `lifecycle_state` and the actual pipeline state (e.g. crash mid-write leaves `Chunked` recorded but no chunks) | DDD | Medium | Medium | Failed `/docs` rendering; tests catch on integration | Wrap the data write + transition in a single SQL transaction; never write the transition before the data |
| Existing migrations break on environments mid-flight | CI/Build | Low | High | Migration test on a snapshot DB | The migration is purely additive (`ADD COLUMN ... DEFAULT`) — safe to apply on any version |
| Confusion between `AnalysisJob.status` and `Document.lifecycle_state` for newcomers | Documentation | High | Low | Reviews ask | A short paragraph in `docs/architecture.md` describing the two concepts side by side |
| `Failed` state without a known reason makes debugging harder | Tests / Documentation | Medium | Medium | Operator complaints | The transition payload carries an optional `reason: str` persisted in a small JSON column or in the analysis-job's `error_message` |

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`)

- **Unit (`tests/domain/`):**
  - `test_lifecycle_transitions.py` — table-driven test of every (from, to) pair: allowed → updates state, disallowed → raises `InvalidLifecycleTransition`.
  - `test_lifecycle_event.py` — successful transition returns the right `DocumentLifecycleChanged` event.
- **Persistence (`tests/persistence/`):**
  - `test_document_repo_lifecycle.py` — write a doc, read it back, lifecycle fields round-trip; default value is `Uploaded`; index exists.
- **Services / integration:**
  - `test_analysis_service_transitions.py` — parse pipeline drives `Uploaded → Parsed`; chunking drives `Parsed → Chunked`; failure → `Failed`.

### Frontend — Vitest

- `features/document/api.test.ts` — DTO parses `lifecycleState` correctly into the typed enum.
- `features/document/store.test.ts` — store exposes `lifecycleState` on the cached document.

### E2E — Karate UI

Out of scope for this issue. E2E coverage lands with #211 (the library page that renders the badge).

### Manual QA

1. `docker compose -f docker-compose.dev.yml up`.
2. Upload a doc → `GET /api/documents/{id}` returns `"lifecycleState": "Uploaded"`.
3. Run analysis → state becomes `"Parsed"` then `"Chunked"`.
4. Force a failure (corrupt PDF) → state becomes `"Failed"`.

## 10. Rollout & observability

### Release branch

`release/0.6.0` (this work).

### Feature flag / staged rollout

None. Lifecycle persistence is always on; UI surfaces are flagged separately (per #210).

### Observability

- Each transition is logged at `INFO` with structured keys: `event=lifecycle_changed doc_id=<id> from=<state> to=<state>`.
- No new Prometheus counter in this issue (added in #211 if useful for the library page).

### Rollback plan

The migration is additive. Reverting the code (without dropping the column) leaves the column populated but unused — safe. If the column itself must go, write a follow-up migration; SQLite supports column drop since 3.35 and we run a recent enough version.

## 11. Open questions

- Should we record the `reason` for `Failed` transitions on the document directly, or rely on the linked `AnalysisJob.error_message`? **Decision for 0.6.0:** rely on `AnalysisJob.error_message`; revisit if multiple non-analysis sources of failure emerge.
- Do we want a typed `DocumentLifecycleEvent` table for audit, or are logs enough? **Decision:** logs only in 0.6.0; #205's `chunk_edits` table is the audit substrate, doc-level events can be added later if needed.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/202
- **Related issues:** #203 (per-store state), #204 (auto-stale), #205 (audit trail), #206 (migration), #211 (library), #215 (status badges)
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - Audit master: `docs/audit/master.md`

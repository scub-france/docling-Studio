# Design: Per (document, store) ingestion state

- **Issue:** #203
- **Title on issue:** [FEATURE] Track ingestion state per (document, store) pair
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: domain · persistence · services · api · infra · frontend: features/ingestion · features/document · shared
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Decoupling · Tests · Documentation
- **ADR spawned?:** ADR-NNN — "Multiple vector stores as first-class entities"

---

## 1. Problem

In the current architecture, "the vector store" is a single OpenSearch index hard-coded to `docling-studio-chunks`. Documents either are or are not indexed in that one place. The new doc-centric model assumes documents can live in **multiple stores** simultaneously — `rh-corpus-v3`, `legal-v1`, a snapshot for a customer A/B — and each `(doc, store)` pair has its own state.

This is also where the killer flow lives: a customer reports bad answers from a specific store; the eng opens the doc, sees that it is `Ingested` in `rh-corpus-v3` and `Stale` in `rh-corpus-v2`, fixes the chunks, and re-ingests **the right one**. Without a per-pair state, that flow is impossible.

## 2. Goals

- [ ] Introduce a `Store` entity in the domain (id, name, kind, config, embedder).
- [ ] Introduce a `DocumentStoreLink` entity tying a document to a store with its own state and metadata.
- [ ] States on the link: `Ingested`, `Stale`, `Failed`. (No `Uploaded`/`Parsed`/`Chunked` — those are doc-level only.)
- [ ] The `Document.lifecycle_state` (#202) aggregates the per-store states by a documented rule.
- [ ] API exposes the per-store list on the document DTO.
- [ ] One default `Store` row is seeded on first migration so existing single-index deployments keep working.

## 3. Non-goals

- Auto-stale detection logic — that is **#204**; this issue ships the schema slot for the content hash but not the detection.
- Multi-tenant isolation between stores — the existing tenant model (if any) is not changed; stores are global today.
- A UI to create/manage stores — that is a follow-up. For 0.6.0 we ship the data model and the seed; a single store is enough for the killer flow on a single tenant.
- Cross-doc bulk re-ingest — that is **#213**; this issue exposes the per-link state needed by it.

## 4. Context & constraints

### Existing code surface

- `document-parser/domain/ports.py` — `VectorStore` protocol (line 124).
- `document-parser/infra/opensearch_store.py` — `OpenSearchStore` adapter.
- `document-parser/services/ingestion_service.py` — `IngestionService.ingest()` and `ensure_index()`.
- `document-parser/persistence/database.py` — schema + migrations.
- `document-parser/api/ingestion.py` — endpoints.
- `frontend/src/features/ingestion/` — Pinia store + API client.

### Hexagonal Architecture constraints (backend)

- `Store` and `DocumentStoreLink` are domain entities (`domain/models.py`). Pure data + invariants. No ORM concern.
- `StoreRepository` and `DocumentStoreLinkRepository` are ports (`domain/ports.py`).
- aiosqlite adapters live in `persistence/store_repo.py` and `persistence/document_store_link_repo.py`.
- The existing `VectorStore` port stays — it represents the **technology** (OpenSearch). The new `Store` entity represents the **logical store** (a named, configurable target). One `VectorStore` adapter can serve many `Store` entities by namespacing the index name.

### Deployment modes

- Single `OpenSearchStore` adapter handles all stores via per-store `index_name = f"docling-studio-{store.slug}"`. Existing default index gets migrated to `docling-studio-default` (with a redirect alias to keep backwards-compatible reads).
- HF Space deployment ships with the same one-store seed.

### Hard constraints

- Existing OpenSearch index must remain readable during migration; reads against the legacy name are aliased.
- API is additive: existing `/api/ingestion/{analysis_id}` keeps working with an implicit default-store target until the UI explicitly picks one (#222).
- Tests must not require a real OpenSearch instance for the link layer — repo tests stub the adapter.

## 5. Proposed design

### 5.1 Domain

`document-parser/domain/value_objects.py`:

```python
class StoreKind(StrEnum):
    OPENSEARCH = "opensearch"
    # future: PINECONE, QDRANT, …

class DocumentStoreLinkState(StrEnum):
    INGESTED = "Ingested"
    STALE    = "Stale"
    FAILED   = "Failed"
```

`document-parser/domain/models.py`:

```python
@dataclass
class Store:
    id: str
    name: str            # "rh-corpus-v3"
    slug: str            # "rh-corpus-v3"  (URL-safe; usually = name)
    kind: StoreKind
    embedder: str        # e.g. "bge-m3" — record the embedder used for this store
    config: dict         # adapter-specific config (index_name override, etc.)
    created_at: datetime
    is_default: bool

@dataclass
class DocumentStoreLink:
    id: str
    document_id: str
    store_id: str
    state: DocumentStoreLinkState
    chunkset_hash: str | None    # set by #204 on push
    last_push_at: datetime | None
    last_run_id: str | None      # FK to a future runs table; nullable in 0.6.0
    error_message: str | None    # populated on FAILED state

    def mark_ingested(self, *, hash_: str, at: datetime, run_id: str | None) -> None: ...
    def mark_stale(self, *, at: datetime) -> None: ...
    def mark_failed(self, *, at: datetime, error: str) -> None: ...
```

Aggregation rule for `Document.lifecycle_state` (defined as a pure function in `domain/lifecycle_aggregation.py`):

```
if any link state == FAILED         → Document is FAILED
elif any link state == STALE        → Document is STALE
elif any link state == INGESTED     → Document is INGESTED
elif chunks present (state Chunked) → Document keeps its current state
else                                → keep current state
```

The aggregation runs as a side effect of any link write. The doc's own state column (#202) is the materialized result; it is not recomputed at read time.

### 5.2 Persistence

```sql
CREATE TABLE IF NOT EXISTS stores (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL,
    embedder    TEXT NOT NULL,
    config      TEXT NOT NULL DEFAULT '{}',  -- JSON
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_store_links (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    store_id        TEXT NOT NULL REFERENCES stores(id)    ON DELETE CASCADE,
    state           TEXT NOT NULL,
    chunkset_hash   TEXT,
    last_push_at    TEXT,
    last_run_id     TEXT,
    error_message   TEXT,
    UNIQUE (document_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_dsl_doc      ON document_store_links(document_id);
CREATE INDEX IF NOT EXISTS idx_dsl_store    ON document_store_links(store_id);
CREATE INDEX IF NOT EXISTS idx_dsl_state    ON document_store_links(state);
```

Seed migration inserts one row in `stores`:

```sql
INSERT OR IGNORE INTO stores (id, name, slug, kind, embedder, is_default, created_at)
VALUES ('default', 'default', 'default', 'opensearch',
        '<env: DEFAULT_EMBEDDER, fallback bge-m3>',
        1, datetime('now'));
```

The OpenSearch index name for `slug=default` is `docling-studio-default`. To keep existing data readable, an alias migration in `OpenSearchStore.ensure_index()` adds `docling-studio-chunks` as a read-only alias to `docling-studio-default` if the legacy index exists with rows. Operators with non-trivial data trigger a one-shot reindex via #206.

### 5.3 Infra adapters

`OpenSearchStore` is parameterised by store slug:

```python
class OpenSearchStore(VectorStore):
    def __init__(self, client, index_prefix: str = "docling-studio") -> None: ...
    def _index_for(self, store_slug: str) -> str:
        return f"{self.index_prefix}-{store_slug}"
```

Calls become `index_chunks(store_slug, doc_id, chunks, embeddings)` etc. The protocol in `domain/ports.py` is updated to take `store_slug` as an explicit argument.

### 5.4 Services

New: `StoreService` (`document-parser/services/store_service.py`) — list, get, create (admin only — locked behind a future flag; for 0.6.0 only seeded rows exist).

`IngestionService.ingest(analysis_id, store_slug = "default")`:
1. Read chunks from `analysis_jobs.chunks_json`.
2. Compute embeddings.
3. Call adapter `index_chunks(store_slug, ...)`.
4. Upsert link via `DocumentStoreLinkRepository.upsert(doc_id, store_id, state=Ingested, chunkset_hash=..., at=now)`.
5. Recompute document aggregate state via the rule in §5.1.

If any step fails: link is marked `Failed` with the error; doc state aggregates to `Failed`.

### 5.5 API

`schemas.py`:

```python
class StoreLinkResponse(BaseModel):
    storeId: str
    storeName: str
    state: str                        # DocumentStoreLinkState value
    chunksetHash: str | None
    lastPushAt: datetime | None
    lastRunId: str | None

class DocumentResponse(BaseModel):
    ...                               # from #202
    stores: list[StoreLinkResponse] = Field(default_factory=list)
```

`stores` is a read-side aggregate computed by `DocumentService.find_by_id()` joining the link table.

New endpoint `GET /api/stores` returns the list of stores (id, name, slug, embedder). Used by #222's target picker.

### 5.6 Frontend — feature module

- `frontend/src/features/ingestion/` — `Ingestion.run()` accepts an optional `storeSlug`; defaults to "default" if not supplied.
- New `frontend/src/features/stores/` — Pinia store, API client, types.
- `frontend/src/features/document/api.ts` — `Document` type gains `stores: StoreLink[]`.

### 5.7 Cross-cutting

- Feature flag: none.
- i18n: `stores.state.<state>` keys in `shared/i18n.ts`.
- New env var documented in `.env.example`: `DEFAULT_EMBEDDER` (existing implicitly; now formalised in the seed).

## 6. Alternatives considered

### Alternative A — One row per (doc, store) embedded in the analysis job

- **Summary:** Add a JSON column `stores_json` on `analysis_jobs`.
- **Why not:** Conflates an *analysis attempt* with a *long-lived ingestion link*. Re-analysis would erase per-store state. The relational shape is necessary for filters, indexes, and idempotent updates.

### Alternative B — One adapter per store (parallel `VectorStore` instances)

- **Summary:** Hold a registry of `VectorStore` adapters keyed by store id.
- **Why not:** Duplicates connection pools, breaks singleton pattern in FastAPI's dependency wiring, and forces N OpenSearch clients for what is logically one client serving N indexes. Parameterising the existing single adapter is cheaper.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET | `/api/documents/{id}` | — | now includes `stores: StoreLinkResponse[]` | No (additive) |
| GET | `/api/stores` | — | `StoreResponse[]` | No (new) |
| POST | `/api/ingestion/{analysis_id}` | `{ "storeSlug": "default" }` (optional) | unchanged | No (additive) |

### Persistence schema

See §5.2.

### Env vars / config

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `DEFAULT_EMBEDDER` | `bge-m3` | any registered embedder slug | recorded on the seeded `default` store |
| `DOCLING_STUDIO_INDEX_PREFIX` | `docling-studio` | URL-safe slug | adapter-level prefix for OpenSearch indexes |

### Breaking changes

Additive.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Existing OpenSearch data invisible after rename | Decoupling | Medium | High | Smoke test on staging | Read alias `docling-studio-chunks → docling-studio-default` set in `ensure_index()`; explicit reindex documented in runbook |
| Multiple stores with conflicting embedders mixed at search time | Security/Performance | Low | Medium | Mismatched dim error from OpenSearch | Embedder is recorded per store; queries route by store; cross-store search is out of scope for 0.6.0 |
| Link table grows large over time on prod corpus | Performance | Medium | Medium | Slow `/api/documents/{id}` join | Index on `document_id` and `store_id`; pagination on the doc list (#211) |
| Aggregation rule drifts from per-store reality on partial writes | DDD | Medium | High | Tests fail | Aggregation runs in the same transaction as the link write |

## 9. Testing strategy

### Backend — pytest

- **Unit (domain):** `test_store_link_transitions.py`, `test_lifecycle_aggregation.py` (table-driven over per-store state combinations).
- **Persistence:** `test_store_repo.py`, `test_document_store_link_repo.py` (round-trip; UNIQUE constraint enforced; cascade delete works).
- **Services / integration:** `test_ingestion_service_with_store.py` (default store path), `test_ingestion_service_two_stores.py` (push to two stores → two links).
- **Architecture:** import-boundary test ensures `domain/` does not import `infra/opensearch_store.py`.

### Frontend — Vitest

- `features/stores/api.test.ts` — list endpoint round-trip.
- `features/document/store.test.ts` — `Document.stores` populated from API.

### E2E — Karate UI

Out of scope here. Lands with #211 / #218.

### Manual QA

1. Boot. `GET /api/stores` returns the seeded `default`.
2. Upload a doc, run ingestion → `GET /api/documents/{id}` returns `stores[0].state == "Ingested"`.
3. Inspect SQLite: `document_store_links` has the row.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

None for the data; #222 will gate the multi-store UI.

### Observability

- Log `store_link_changed` with `doc_id`, `store_id`, `from`, `to`, `at`.
- Counter (Prometheus, future): `ingestion_links_total{state}`. Optional in 0.6.0.

### Rollback plan

The migration is additive. To roll back the code: revert; the unused tables stay empty for new docs but contain rows for already-pushed docs — harmless (no read path uses them after revert). For full cleanup, a follow-up migration drops the two tables.

## 11. Open questions

- Should `Store.config` be typed in the domain (via a discriminated union on `kind`)? **Decision for 0.6.0:** keep as opaque `dict`; introduce a typed wrapper when we add a second `kind`.
- Cross-store search (single query → many stores) — **explicitly punted** to a later release.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/203
- **Related issues:** #202 (lifecycle), #204 (hash), #205 (audit), #206 (migration), #211 (library), #213 (bulk push), #222 (push UI), #223 (diff-aware ingest)
- **ADRs:** ADR — "Multiple vector stores as first-class entities" (to be drafted alongside the implementation PR)
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide: `docs/architecture/adr-guide.md`

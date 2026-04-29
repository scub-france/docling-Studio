# Design: Audit trail for chunk edits

- **Issue:** #205
- **Title on issue:** [FEATURE] Audit trail for chunk edits (who, when, before/after)
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: domain · persistence · services · api · frontend: features/chunking · shared
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Tests · Security · Documentation
- **ADR spawned?:** ADR-NNN — "Chunks become a first-class persisted entity"

---

## 1. Problem

Once chunks become editable in 0.6.0 (E5), production teams will need to answer "who changed what, when, and why is the answer suddenly different?". Without an audit trail, a regression caused by a chunk edit is impossible to investigate.

Today the architecture makes this hard because **chunks are not persisted as first-class records**. They live as a JSON blob inside `analysis_jobs.chunks_json` and as derived rows in OpenSearch. There is no chunk identity that survives a re-parse, no row to attach an audit record to, and no way to retrieve "the version of these chunks at the last push".

This issue elevates chunks to a first-class persisted entity (with stable IDs and content versioning), introduces an immutable `chunk_edits` table, and exposes a snapshot API consumed by the visual diff (#221).

## 2. Goals

- [ ] Promote chunks to a first-class persisted entity with stable IDs across edits.
- [ ] Every chunk operation (create / update / delete / merge / split) writes an immutable `chunk_edits` record with: actor, timestamp, action, before-state, after-state, optional reason.
- [ ] API: `GET /api/documents/{id}/chunks/history` returns the edit timeline.
- [ ] API: `GET /api/documents/{id}/chunks?at=<push_id>` returns the chunkset snapshot at a given push.
- [ ] Backwards compatible: existing reads of `analysis_jobs.chunks_json` keep working until #206 finishes the migration.

## 3. Non-goals

- Undo / redo UI — out of scope (the audit trail is the substrate; UI comes later).
- Rollback to an arbitrary past state — not in 0.6.0; use the snapshot API for read-only inspection.
- A diff *view* — that is **#221**.
- Per-chunk content hash — that is part of **#223**, not this issue. (#204's `chunkset_hash` is at the link granularity.)
- Authentication / authorization model rework — `actor` defaults to a hard-coded `"system"` until the auth layer is ready.

## 4. Context & constraints

### Existing code surface

- `document-parser/domain/value_objects.py` — `ChunkResult` (transient).
- `document-parser/domain/models.py` — `AnalysisJob.chunks_json` (current chunkset storage).
- `document-parser/services/analysis_service.py` — chunking pipeline.
- `document-parser/persistence/database.py` — schema + migrations.
- `document-parser/api/` — no chunks endpoint today; needs creation.
- `frontend/src/features/chunking/` — Pinia store + API client.

### Hexagonal Architecture constraints

- New domain entities `Chunk` and `ChunkEdit` live in `domain/models.py`.
- `ChunkRepository` and `ChunkEditRepository` are ports (`domain/ports.py`).
- aiosqlite adapters in `persistence/chunk_repo.py` and `persistence/chunk_edit_repo.py`.
- A new `ChunkEditingService` in `services/` orchestrates the operations and writes audit records atomically with the chunk write.
- The existing `analysis_jobs.chunks_json` becomes a **legacy fallback** — read by `ChunkRepository.list_for_doc()` if no rows exist in the new `chunks` table. #206 backfills.

### Hard constraints

- Stable `chunk.id` across edits. A chunk that was split into two creates two new ids; merging two chunks produces a third new id. The "lineage" is recorded in `chunk_edits`. (No "ship the same id" hack.)
- Immutable audit table. Once written, never updated.
- No PII leak in audit records — `actor` is whatever the auth layer hands us; `before`/`after` payloads are the chunk text and metadata only.
- Atomicity: an edit + its audit row are written in the same SQL transaction.

## 5. Proposed design

### 5.1 Domain

`document-parser/domain/models.py`:

```python
@dataclass
class Chunk:
    id: str                       # uuid4 hex
    document_id: str
    sequence: int                 # ordering within the doc; gaps allowed
    text: str
    headings: list[str]
    source_page: int | None
    bboxes: list[Bbox]            # carried for rendering; not part of identity
    doc_items: list[str]
    token_count: int | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None   # soft delete

class ChunkEditAction(StrEnum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    MERGE  = "merge"
    SPLIT  = "split"

@dataclass(frozen=True)
class ChunkEdit:
    id: str
    document_id: str
    chunk_id: str | None          # null on MERGE result row (uses children_ids)
    action: ChunkEditAction
    actor: str                    # "system" until auth lands
    at: datetime
    before: dict | None           # JSON snapshot — None for INSERT
    after: dict | None            # JSON snapshot — None for DELETE
    parents: list[str]            # for SPLIT result rows: source chunk id; for MERGE: source ids
    children: list[str]           # inverse links
    reason: str | None
```

Domain operations on a chunkset (`domain/chunk_editing.py`):

```python
def insert(chunks: list[Chunk], at_position: int, new_chunk: Chunk) -> list[Chunk]: ...
def update(chunks: list[Chunk], chunk_id: str, *, text: str, headings: list[str]) -> list[Chunk]: ...
def delete(chunks: list[Chunk], chunk_id: str) -> list[Chunk]: ...
def merge(chunks: list[Chunk], chunk_ids: list[str]) -> tuple[list[Chunk], Chunk]:
    """Returns the updated list and the new merged chunk."""
def split(chunks: list[Chunk], chunk_id: str, at_offset: int) -> tuple[list[Chunk], Chunk, Chunk]:
    """Returns the updated list and the two new chunks."""
```

These are pure. The service wraps each call with audit-record generation.

### 5.2 Persistence

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    sequence      INTEGER NOT NULL,
    text          TEXT NOT NULL,
    headings      TEXT NOT NULL DEFAULT '[]',  -- JSON
    source_page   INTEGER,
    bboxes        TEXT NOT NULL DEFAULT '[]',  -- JSON
    doc_items     TEXT NOT NULL DEFAULT '[]',  -- JSON
    token_count   INTEGER,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    deleted_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc       ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_seq   ON chunks(document_id, sequence);

CREATE TABLE IF NOT EXISTS chunk_edits (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id      TEXT,
    action        TEXT NOT NULL,
    actor         TEXT NOT NULL DEFAULT 'system',
    at            TEXT NOT NULL,
    before_json   TEXT,
    after_json    TEXT,
    parents_json  TEXT NOT NULL DEFAULT '[]',
    children_json TEXT NOT NULL DEFAULT '[]',
    reason        TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunk_edits_doc_at ON chunk_edits(document_id, at);
CREATE INDEX IF NOT EXISTS idx_chunk_edits_chunk  ON chunk_edits(chunk_id);

-- Snapshot table — captures the chunkset hash at every successful push.
CREATE TABLE IF NOT EXISTS chunk_pushes (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    store_id      TEXT NOT NULL REFERENCES stores(id)    ON DELETE CASCADE,
    chunkset_hash TEXT NOT NULL,
    chunk_ids     TEXT NOT NULL,           -- JSON array of chunk ids in order at push time
    pushed_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunk_pushes_doc_store ON chunk_pushes(document_id, store_id);
```

Note: `chunk_pushes.chunk_ids` materialises the chunkset at push time. Combined with the immutable `chunk_edits` history, we can reconstruct any past chunkset by replay (slower) — but `chunk_ids` is the cheap path.

### 5.3 Infra adapters

None.

### 5.4 Services

`document-parser/services/chunk_editing_service.py`:

```python
class ChunkEditingService:
    def __init__(self, chunks: ChunkRepository, edits: ChunkEditRepository, ...): ...

    async def insert(self, doc_id, at_position, payload, *, actor, reason=None) -> Chunk: ...
    async def update(self, doc_id, chunk_id, payload, *, actor, reason=None) -> Chunk: ...
    async def delete(self, doc_id, chunk_id, *, actor, reason=None) -> None: ...
    async def merge(self, doc_id, chunk_ids, *, actor, reason=None) -> Chunk: ...
    async def split(self, doc_id, chunk_id, at_offset, *, actor, reason=None) -> tuple[Chunk, Chunk]: ...

    async def history(self, doc_id) -> list[ChunkEdit]: ...
    async def chunkset_at(self, doc_id, push_id) -> list[Chunk]: ...
```

Every mutating method runs in a single SQL transaction:
1. Apply the domain operation.
2. Persist chunk rows (insert / update / soft-delete).
3. Insert `chunk_edits` row with full before/after snapshot.
4. Trigger #204's stale detection on the doc.

`history()` — paginated (default 50, max 500), ordered `at DESC`.

`chunkset_at(push_id)` — read `chunk_pushes.chunk_ids`, return the matching `chunks` rows in that order.

`IngestionService.ingest()` (touched in #203) writes a row to `chunk_pushes` on success.

### 5.5 API

New router `document-parser/api/chunks.py`:

```
GET    /api/documents/{id}/chunks                         List current chunks
GET    /api/documents/{id}/chunks?at=<push_id>            Snapshot at push
GET    /api/documents/{id}/chunks/history                 Edit timeline (paginated)
POST   /api/documents/{id}/chunks                         Insert chunk
PATCH  /api/documents/{id}/chunks/{chunk_id}              Update chunk
DELETE /api/documents/{id}/chunks/{chunk_id}              Soft-delete chunk
POST   /api/documents/{id}/chunks/merge                   { chunkIds: [...], reason? } → new chunk
POST   /api/documents/{id}/chunks/{chunk_id}/split        { atOffset, reason? }        → two new chunks
```

DTOs (`schemas.py`, camelCase via alias):

```python
class ChunkResponse(BaseModel):
    id: str
    sequence: int
    text: str
    headings: list[str]
    sourcePage: int | None
    tokenCount: int | None
    bboxes: list[BboxDto]
    docItems: list[str]
    updatedAt: datetime

class ChunkEditResponse(BaseModel):
    id: str
    chunkId: str | None
    action: str
    actor: str
    at: datetime
    before: dict | None
    after: dict | None
    parents: list[str]
    children: list[str]
    reason: str | None
```

### 5.6 Frontend — feature module

Touched: `frontend/src/features/chunking/`.

- `api.ts` — clients for the seven endpoints above.
- `store.ts` — Pinia store holds `chunks`, `history`, and a draft layer for optimistic updates with rollback on failure.
- `ui/` — primitives only in this issue (`ChunkRow.vue`, `ChunkActionsMenu.vue`); the full editor is built in #219 / #220 / #221 on top.
- `data-e2e` selectors named upfront: `chunk-row`, `chunk-actions-menu`, `chunk-action-merge`, etc.

### 5.7 Cross-cutting

- Feature flag: existing `chunking` flag (in `/api/health`) gates the editing endpoints. When `false`, the endpoints return `403`.
- i18n: `chunks.action.*`, `chunks.reason.placeholder` keys.
- Shared types: `DocumentChunk`, `ChunkEdit` re-exported from `shared/types.ts`.

## 6. Alternatives considered

### Alternative A — Keep chunks in `analysis_jobs.chunks_json`, version the JSON

- **Summary:** Add a `version` column on `analysis_jobs` and a `chunk_edits` table referencing JSON paths inside `chunks_json`.
- **Why not:** No chunk identity → `before`/`after` lookups become regex on JSON. Splits and merges have nowhere to record lineage. Reviewers and customer support cannot navigate the audit. The architectural cost is paid sooner or later — pay it now while the data is small.

### Alternative B — Use OpenSearch as the source of truth for chunks

- **Summary:** Treat the OpenSearch document as the authoritative chunk; record audit metadata there.
- **Why not:** OpenSearch is a derived index. It is the *projection* of the corpus, not its source. Replacing OpenSearch (Pinecone, Qdrant) would lose history. Source of truth belongs in SQLite.

### Alternative C — Event-sourcing only (no current-state table)

- **Summary:** Drop `chunks` table; replay `chunk_edits` to compute current state.
- **Why not:** Replay cost on every read is unacceptable for chunks-editor latency and for #221's diff. Hybrid (current state + immutable history) is the standard pragmatic shape.

## 7. API & data contract

### Endpoints

See §5.5 — eight new endpoints, all behind the existing `chunking` feature flag.

### Persistence schema

See §5.2.

### Env vars / config

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `CHUNK_HISTORY_PAGE_DEFAULT` | `50` | int 1–500 | default page size for history |
| `CHUNK_HISTORY_PAGE_MAX` | `500` | int | hard cap |

### Breaking changes

None. Existing chunks in `chunks_json` remain accessible via the legacy fallback in `ChunkRepository.list_for_doc()` until #206 finishes the migration.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Audit table growth on heavy editing customers | Performance | Medium | Medium | Slow `chunk_edits` queries | Indexed by (doc, at). Pagination on the API. Future: archival job. |
| Race between two parallel edits on the same chunk | DDD | Low | Medium | Lost update | All mutations go through `ChunkEditingService` which serialises via the SQL transaction; client sends `If-Match` with `updatedAt` for optimistic concurrency on `PATCH` / `DELETE` |
| Audit before/after reveals sensitive content if shared | Security | Medium | Medium | Audit export shared accidentally | The audit endpoint is gated by the same auth as chunk edits; export does not include audit by default; admin-only flag in a future release |
| Schema drift: `chunks_json` and `chunks` table diverge during migration window | DDD | Medium | High | Diff between the two on the same doc | #206 is the single source of truth; new edits write to `chunks` only; reads prefer `chunks` and fall back to `chunks_json` |

## 9. Testing strategy

### Backend — pytest

- **Unit (domain):**
  - `test_chunk_editing_pure.py` — insert / update / delete / merge / split on in-memory lists; properties verified (lengths, sequences, identity rules).
- **Persistence:**
  - `test_chunk_repo.py` — round-trip, soft delete, ordering by sequence.
  - `test_chunk_edit_repo.py` — write + read history; immutability (UPDATE on `chunk_edits` is rejected by a CHECK constraint or service-level guard).
- **Services / integration:**
  - `test_chunk_editing_service_audit_atomicity.py` — failure mid-write rolls back both chunk and audit.
  - `test_chunkset_at_snapshot.py` — `chunkset_at(push_id)` returns the right snapshot after edits.
  - `test_legacy_fallback.py` — read chunks for a doc that has only `chunks_json` (pre-migration).

### Frontend — Vitest

- `features/chunking/api.test.ts` — eight endpoints round-trip.
- `features/chunking/store.test.ts` — optimistic update + rollback on API failure; history pagination.

### E2E — Karate UI

Out of scope here; the editor lands in #219 / #220 with E2E tags `@critical @ui`.

### Manual QA

1. Trigger an INSERT / UPDATE / DELETE / MERGE / SPLIT.
2. `GET /api/documents/{id}/chunks/history` shows the action with `before`/`after`.
3. After a successful push, `GET /api/documents/{id}/chunks?at=<push_id>` returns the chunkset captured at push.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

The existing `chunking` flag (in `/api/health`) controls whether the editing endpoints accept writes. Reads (`GET`) are always allowed (consistent with the chunks tab being read-only when the flag is off).

### Observability

- Each mutation logs: `INFO event=chunk_edit doc_id=<id> chunk_id=<id> action=<action> actor=<actor>`.
- Counter (Prometheus, future): `chunk_edits_total{action}`.

### Rollback plan

The migration is additive. Reverting the code leaves the new tables but no writers. Reads from the chunks tab fall back to the legacy `chunks_json`. Editing endpoints disappear (404). If a clean rollback is needed, drop the three new tables.

## 11. Open questions

- Should `actor` carry a structured object (id, name, role) or stay as a free-form string? **Decision for 0.6.0:** free-form string (`"system"` today; whatever auth provides later). Structured upgrade is non-breaking thanks to JSON-friendly columns.
- Should we generate a *human-readable* diff in the audit row (line-level), or only store before/after JSON? **Decision:** store JSON; render the diff client-side in #221.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/205
- **Related issues:** #202 (lifecycle), #203 (per-store), #204 (auto-stale), #206 (migration), #219 (editor view), #220 (edit actions), #221 (visual diff), #222 (push)
- **ADRs:** ADR — "Chunks become a first-class persisted entity"
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide: `docs/architecture/adr-guide.md`

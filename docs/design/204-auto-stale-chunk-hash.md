# Design: Auto-detect Stale state via chunk content hash

- **Issue:** #204
- **Title on issue:** [FEATURE] Auto-detect Stale state via chunk content hash
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-04-29
- **Status:** Accepted
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: domain · persistence · services · frontend (read-only)
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Performance · Tests · Security
- **ADR spawned?:** no

---

## 1. Problem

Without auto-detection, a user who edits a chunk has to remember which stores hold the doc and click "re-ingest" everywhere. They will forget. The next query against the stale store returns the old embedding, and the customer reports "I fixed it yesterday and it's still wrong". Manual flagging is a bug factory.

The detection contract is: **the system, not the user, knows when a stored chunkset diverges from the current draft chunkset.** Implementation = a deterministic hash recorded at push time and compared on read or on chunk write.

## 2. Goals

- [ ] Define a deterministic `chunkset_hash(chunks: list[ChunkResult])` function.
- [ ] Store the hash on each `DocumentStoreLink` at push time (#203 ships the column slot).
- [ ] On any chunk modification, recompute the current chunkset hash and compare against each link; if mismatch, mark the link `Stale` and re-aggregate the document state.
- [ ] On document read (single-doc API), compare on the fly as a safety net so older drift is caught.
- [ ] Unit tests prove: edit a chunk → link state becomes `Stale`; re-push → link state becomes `Ingested` with the new hash.

## 3. Non-goals

- Per-chunk change tracking — that's the audit trail (#205); this issue cares about the *aggregate* hash only.
- Background sweeper job that scans the whole corpus for drift — for 0.6.0, detection is event-driven (on chunk write) + on-read; a sweeper can come later.
- Diff-aware re-ingest at the chunk granularity — that's #223; this issue tells you *whether* a re-ingest is needed, not which chunks to re-embed.
- A user-facing toggle to "force stale" — out of scope.

## 4. Context & constraints

### Existing code surface

- `document-parser/domain/value_objects.py` — `ChunkResult` (line 93).
- `document-parser/services/analysis_service.py` — chunking pipeline.
- `document-parser/persistence/database.py` — `analysis_jobs.chunks_json` (the canonical chunkset today).
- `document-parser/services/ingestion_service.py` — push pipeline.
- `document-parser/api/ingestion.py` — push endpoint.
- `document-parser/persistence/document_store_link_repo.py` (created by #203).

### Hexagonal Architecture constraints

- `chunkset_hash` is a **pure domain function** — lives in `domain/hashing.py`. No I/O. No timestamps. Deterministic over the input.
- Detection (compare + transition) is orchestrated in services. Persistence reads the stored hash via the link repo.
- The hash is opaque to API/frontend in 0.6.0; surfaced only as a debug field on `StoreLinkResponse` (#203 added it).

### Hard constraints

- Hash function must be **stable across processes / machines / Python versions** — so SHA-256 (`hashlib`), not Python `hash()`. No salt.
- Must be cheap on a 500-chunk doc — a single linear pass, no JSON re-parse on hot path.
- Result is a hex string, length 64. Stored as `TEXT` in SQLite.

## 5. Proposed design

### 5.1 Domain

`document-parser/domain/hashing.py`:

```python
import hashlib
import json
from collections.abc import Iterable
from .value_objects import ChunkResult

def chunkset_hash(chunks: Iterable[ChunkResult]) -> str:
    """
    Deterministic hash over a chunkset.

    Hashed inputs (per chunk, in chunkset order):
      - text             (str)
      - source_page      (int | None)
      - headings         (list[str], preserved order)

    Excluded:
      - bboxes / doc_items (rendering artefacts; do not affect retrieval semantics)
      - token_count        (derived; unstable across tokenizers)
    """
    h = hashlib.sha256()
    for chunk in chunks:
        payload = {
            "t": chunk.text,
            "p": chunk.source_page,
            "h": list(chunk.headings or []),
        }
        h.update(b"\x1f")
        h.update(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    return h.hexdigest()
```

Notes:
- The `\x1f` (Unit Separator) byte between chunks defends against the "join attack" where chunk A's tail and chunk B's head produce the same hash as chunk A+B merged.
- `separators=(",", ":")` is the canonical compact JSON form.
- The exclusion list is intentional and documented inline — changing it bumps every doc to `Stale` once and is a deliberate one-time event (covered in §10 Rollback).

`detect_stale_links(current_hash, links) -> list[DocumentStoreLink]` — pure helper returning the subset of links whose `chunkset_hash != current_hash`.

### 5.2 Persistence

No new schema. The `chunkset_hash` column was added by #203 on `document_store_links`.

A new index supports the on-read safety net:

```sql
CREATE INDEX IF NOT EXISTS idx_dsl_doc_state ON document_store_links(document_id, state);
```

### 5.3 Infra adapters

None. Hashing is in-memory.

### 5.4 Services

Two call sites:

**A. On chunk write (event-driven detection)**

`AnalysisService.persist_chunks(doc_id, chunks)`:
1. Persist chunks (existing path: `analysis_jobs.chunks_json`).
2. Compute `current_hash = chunkset_hash(chunks)`.
3. Read all `DocumentStoreLink` rows for `doc_id`.
4. For each link with `chunkset_hash != current_hash` and `state in (Ingested,)`:
   - `link.mark_stale(at=now)` and persist.
5. Re-aggregate the document state (#202).

This runs in the same transaction as the chunk write. The full pass is O(N_links) which is small (a doc rarely lives in more than a handful of stores).

**B. On push completion (set the new hash)**

Already covered by #203's `IngestionService.ingest`. Add the `current_hash` argument when calling `link.mark_ingested(hash_=current_hash, at=now, run_id=...)`.

**C. On read (safety net)**

`DocumentService.find_by_id(id)`:
1. Fetch document + links (existing).
2. Compute `current_hash` (cheap; cached per request).
3. Mark any `Ingested` link with mismatched hash as `Stale` and persist (best-effort, swallowed if write fails — log).

This guards against drift caused by direct DB writes / restored backups / older deploys.

### 5.5 API

No new endpoint. `StoreLinkResponse.chunksetHash` (already added by #203) is now actually populated.

### 5.6 Frontend — feature module

No changes in this issue. #224 (stale indicator) reads the existing field.

### 5.7 Cross-cutting

- Feature flag: none.
- Logs: `INFO event=stale_detected doc_id=<id> store_id=<id> previous_hash=<8> current_hash=<8>` (truncated for privacy / log volume).
- ADR: not required. The choice of SHA-256 + canonical JSON is documented inline in `hashing.py`.

## 6. Alternatives considered

### Alternative A — Per-chunk hashes only (no chunkset hash)

- **Summary:** Skip the aggregate hash; track each chunk's hash and detect "any per-chunk hash drift".
- **Why not:** Per-chunk hashing is needed for #223 (diff-aware re-embed) but not for "is this link stale at all?". A single `chunkset_hash` is one-comparison cheap; per-chunk is N-comparisons. Both will exist after #223 lands; this issue ships the cheap top-level signal.

### Alternative B — Store updated_at instead of hash

- **Summary:** Compare `chunks.updated_at > link.last_push_at`.
- **Why not:** Brittle. Re-running a pipeline on identical input bumps `updated_at` without semantic change. Hash is content-addressed and survives idempotent rewrites.

### Alternative C — MD5 / xxHash

- **Summary:** Use a faster non-cryptographic hash.
- **Why not:** SHA-256 is fast enough on the volumes in scope (`<500 chunks`, microseconds in CPython hashlib via OpenSSL bindings). The cryptographic hash also gives us collision resistance for free. xxHash would require an extra dependency.

## 7. API & data contract

### Endpoints

No additions. Existing `StoreLinkResponse.chunksetHash` becomes populated.

### Persistence schema

```sql
CREATE INDEX IF NOT EXISTS idx_dsl_doc_state ON document_store_links(document_id, state);
```

### Env vars / config

None.

### Breaking changes

None.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Hash function changes (e.g. someone adds `bboxes` to the input) silently invalidates every link | DDD | Medium | High | Every doc flips to `Stale` post-deploy | Hash function is in a single file with a docstring listing the canonical inputs; CI fixture asserts a fixed hash for a known chunkset. Bumping requires updating the fixture deliberately. |
| Read-side detection updates state under a GET (write-on-read) | Performance / Decoupling | Low | Medium | Slow / unexpected SQL in read paths | Best-effort, swallowed write; only triggered when the API actually serves the doc detail page (already a write-allowed code path). Disabled if a query param `?refresh=false` is set (future). |
| Unicode normalization issues (NFC vs NFD) produce different hashes for "the same" text | Tests | Low | Medium | Drift after a copy-paste from a Mac | Document the policy: text is stored as-is, no normalization; if drift appears, normalize at write time, not at hash time. |
| JSON ordering instability across Python versions | Tests | Low | High | Hash mismatch on different prod nodes | `separators=(",", ":")` + `ensure_ascii=False` + explicit key order in the dict literal. Reviewer checklist mentions this. |

## 9. Testing strategy

### Backend — pytest

- **Unit (domain):**
  - `test_chunkset_hash_determinism.py` — same input → same output across multiple invocations.
  - `test_chunkset_hash_sensitivity.py` — every input field in the canonical list changes the hash; excluded fields (`bboxes`, `token_count`) do not.
  - `test_chunkset_hash_join_attack.py` — separating into different chunks must produce different hash from concatenation.
  - **Locked fixture** `test_chunkset_hash_fixture.py` — a hand-built 3-chunk input whose hash is hard-coded; CI fails if anyone changes the function silently.
- **Services:**
  - `test_stale_detection_on_edit.py` — edit a chunk → link state becomes `Stale`.
  - `test_stale_clears_on_repush.py` — re-push → link state becomes `Ingested` with the new hash.
  - `test_stale_safety_net_on_read.py` — direct DB tampering → next read flips state to `Stale`.

### Frontend — Vitest

None new in this issue.

### E2E — Karate UI

Out of scope here; lands with #224.

### Manual QA

1. Push a doc to the default store → `chunksetHash` populated, `state == "Ingested"`.
2. Edit a chunk via API → `state == "Stale"`.
3. Re-push → `state == "Ingested"`, new hash.

## 10. Rollout & observability

### Release branch

`release/0.6.0`.

### Feature flag

None. Detection is always on; cheap; correctness improvement.

### Observability

- Log lines as in §5.7.
- One-time bump scenario: if we ever change the canonical input list, every link will flip to `Stale` once. That is a deliberate decision; the operator must be informed via release notes, and a one-shot reindex job is recommended (out of scope here).

### Rollback plan

The migration is additive (a new index). Reverting the code leaves the existing `chunkset_hash` column populated but unused — harmless. The index can be dropped in a follow-up.

## 11. Open questions

- Should the safety-net read-side check be opt-in via a query param? **Decision:** always-on for 0.6.0; revisit if the cost shows up in profiles.
- Should headings include the *path* (parent → leaf) or just the leaf? **Decision:** the full ordered list as it sits on `ChunkResult.headings`. If the source mutates the list semantics, that is a separate domain concern.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/204
- **Related issues:** #202 (lifecycle), #203 (per-store state), #205 (audit), #206 (migration), #223 (diff-aware re-ingest), #224 (stale indicator)
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`

# Design: Doc tab: chunk mode returns 404

<!--
Design doc template for Docling Studio.

One design doc per tracked issue. File path convention:
  docs/design/<issue-number>-<kebab-slug>.md

Status lifecycle: Draft → In review → Accepted → Implemented (or Superseded).
Bump the Status line as the doc progresses; do not delete sections on the way.

This template is tailored to the project's architecture and conventions:
  - Backend Hexagonal Architecture / ports & adapters
    (domain → api/services/persistence/infra)
    see docs/architecture.md
  - Backend coding standards (FastAPI + Pydantic camelCase, aiosqlite,
    Python snake_case internal, max 300 lines/file, 30 lines/function)
    see docs/architecture/coding-standards.md
  - Frontend feature-based organization (Vue 3 + Pinia, one store per
    feature, Composition API, TypeScript strict, data-e2e selectors)
  - E2E with Karate UI (NOT Playwright) — see e2e/CONVENTIONS.md
  - Audit dimensions used at release gate — see docs/audit/master.md
  - ADR process for load-bearing decisions — see docs/architecture/adr-guide.md

The `/conception` command pre-fills the header block and §1 / §2 / §12 from
the linked issue. Everything else is on the author.
-->

- **Issue:** #256
- **Title on issue:** [BUG] Doc tab: chunk mode returns 404
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-05-07
- **Status:** Implemented (shipped in 0.6.1)
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** backend: api · services · (persistence read-only — déjà en place) · frontend: features/chunks (zéro changement attendu, déjà aligné sur le contrat) · e2e: nouveau scénario Karate
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Decoupling · Tests · Documentation
- **ADR spawned?:** no — le modèle canonical `Chunk` (port + repository) existe déjà depuis #205, on ne fait que combler une couche service + API absente.

---

## 1. Problem

<!--
What hurts today, and for whom. Pull from the issue's Context + Current
behavior sections — keep the user's voice, do not paraphrase aggressively.
Two or three short paragraphs is usually enough. If you can't state the
problem in plain language, you are not ready to design a solution.
-->

Dans l'onglet **Doc** (`DocWorkspacePage` → `DocChunksTab`), l'activation du mode **chunk** déclenche un **HTTP 404**.

L'investigation a montré que ce n'est pas un endpoint isolé qui manque, mais **9 routes complètes côté `/api/documents/{id}/...`** qui sont appelées depuis le front mais n'existent pas côté backend. La couche frontend a été développée sur la cible 0.6.0 (doc-centric) avant que la couche API correspondante ne soit posée.

Le domain et la persistence du modèle canonical `Chunk` (entité de première classe, audit log via `ChunkEdit`, snapshots `ChunkPush`) existent **déjà** depuis l'issue #205 (`document-parser/domain/models.py`, `domain/ports.py`, `persistence/chunk_repo.py`, `persistence/chunk_edit_repo.py`). Ce qui manque, c'est la couche **service** et la couche **API** qui les exposent au front.

Note importante: le mode **OCR Debug** de `StudioPage` (`/api/analyses/*`) doit rester intact. Il opère sur des `AnalysisJob` éphémères avec pipeline options variables, ce qui est conceptuellement différent des chunks canonical d'un document. Les deux flux partagent le service de chunking sous-jacent (port `DocumentChunker`) mais exposent des ressources distinctes — pas de duplication d'endpoints.

## 2. Goals

<!--
Concrete, verifiable outcomes. Convert the issue's acceptance criteria into
checkboxes here; the design is "done" when all are satisfied. Keep the list
small — five or fewer goals is a good smell.
-->

- [ ] Mode chunk de l'onglet Doc renvoie la liste des chunks canonical sans 404 (endpoint `GET /api/documents/{id}/chunks` opérationnel).
- [ ] Toutes les actions d'édition fonctionnent: add, edit, delete, split, merge, rechunk (endpoints `POST/PATCH/DELETE` correspondants).
- [ ] Le push vers un store et le diff par store fonctionnent (`POST /push`, `GET /diff?store=…`).
- [ ] L'arbre structurel s'affiche sur l'onglet Inspect (`GET /tree`).
- [ ] Le mode OCR Debug (`StudioPage` → `/api/analyses/*`) reste totalement fonctionnel — non-régression.
- [ ] Promotion automatique: à la première analyse réussie d'un document, ses chunks deviennent canonical (peuplent `chunks` table via `ChunkRepository`).
- [ ] Tests: unit Vitest sur les nouveaux appels, pytest sur le service + router, e2e Karate sur le flow `Doc tab → mode chunk`.

## 3. Non-goals

<!--
What this design explicitly does NOT try to solve — and, for each, where it
*should* be solved (follow-up issue, next milestone, different audit area).
This is the section that saves the review: naming the off-ramps up front
prevents scope creep. If you leave this empty, reviewers will fill it in
for you, badly.
-->

- **Pas de refonte du modèle de données.** Le domain `Chunk` / `ChunkEdit` / `ChunkPush` est déjà posé (#205). On ne touche ni aux dataclasses ni au schéma SQLite.
- **Pas de refonte de StudioPage / OCR Debug.** Le flux `/api/analyses/*` reste tel quel; aucun port ni service de l'AnalysisService n'est modifié au-delà du hook de promotion canonical.
- **Pas de fusion `features/chunking/` ↔ `features/chunks/` côté front.** Ce sont deux features sémantiquement distinctes (acte de chunking debug vs état canonical persistant).
- **Pas de refactor des fichiers > 300 lignes** identifiés dans l'audit (StudioPage, GraphView, ChunksEditor) — sera traité dans des issues séparées du milestone 0.7.0.
- **Pas d'ajout de nouvelle table** ni de nouvelles colonnes — tout est déjà présent.
- **Pas de versioning d'API** — première exposition de ces routes, pas de breaking change.

## 4. Context & constraints

### Cartographie des 9 routes manquantes

Côté front (déjà écrit, fonctionne dès que le back répond):

| Méthode | URL | Front caller |
|---|---|---|
| `GET` | `/api/documents/{id}/chunks` | `features/chunks/api.ts:5` |
| `POST` | `/api/documents/{id}/chunks` | `features/chunks/api.ts:42` |
| `PATCH` | `/api/documents/{id}/chunks/{chunkId}` | `features/chunks/api.ts:13` |
| `DELETE` | `/api/documents/{id}/chunks/{chunkId}` | `features/chunks/api.ts:38` |
| `POST` | `/api/documents/{id}/chunks/{chunkId}/split` | `features/chunks/api.ts:31` |
| `POST` | `/api/documents/{id}/chunks/merge` | `features/chunks/api.ts:20` |
| `POST` | `/api/documents/{id}/rechunk` | `features/document/api.ts:31` |
| `GET` | `/api/documents/{id}/diff?store={name}` | `features/chunks/api.ts:49` |
| `POST` | `/api/documents/{id}/chunks/push` | `features/chunks/api.ts:56` |
| `POST` | `/api/documents/{id}/push` | `features/document/api.ts:35` (alias par doc — voir §5) |
| `GET` | `/api/documents/{id}/tree` | `features/document/api.ts:42` |

### Surface de code touchée

- **Backend (à créer)**:
  - `document-parser/services/chunk_service.py` (nouveau)
  - `document-parser/api/document_chunks.py` (nouveau router)
  - `document-parser/api/schemas.py` (DTOs camelCase)
  - `document-parser/main.py` (registration du router + injection du service)
  - `document-parser/services/analysis_service.py` (hook de promotion canonical)
  - `document-parser/tests/services/test_chunk_service.py` (nouveau)
  - `document-parser/tests/api/test_document_chunks.py` (nouveau)

- **Backend (existant, lecture seule)**:
  - `document-parser/domain/models.py` — `Chunk`, `ChunkEdit`, `ChunkPush` ✅
  - `document-parser/domain/ports.py` — `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `DocumentChunker` ✅
  - `document-parser/persistence/chunk_repo.py`, `chunk_edit_repo.py` ✅
  - `document-parser/services/ingestion_service.py` (réutilisé pour push)
  - `document-parser/services/store_service.py` (réutilisé pour diff par store)

- **Frontend (zéro changement attendu)**:
  - `frontend/src/features/chunks/api.ts` — déjà aligné sur le contrat
  - `frontend/src/features/document/api.ts` — déjà aligné

- **E2E (à créer)**:
  - `e2e/ui/src/test/resources/documents/doc-tab-chunk-mode.feature`

### Hexagonal Architecture

- Le domain ne change pas. Aucun nouveau port n'est ajouté: tous les besoins sont déjà couverts (`ChunkRepository`, `ChunkEditRepository`, `DocumentChunker`).
- Le nouveau `ChunkService` orchestre des ports existants et délègue à `AnalysisService.rechunk` pour le rechunk du doc canonical (DRY: la mécanique chunk-via-Docling est une seule implémentation).
- L'API ne franchit pas de couche: le router `document_chunks.py` parle uniquement aux services, jamais à `chunk_repo` directement.
- Conséquence: zéro nouvelle dépendance entre couches.

### Deployment modes

- Supporté: `latest-local` et `latest-remote` à l'identique. Aucun comportement spécifique au `CONVERSION_ENGINE` — `ChunkService` ne touche pas au converter, seulement au chunker (port `DocumentChunker` qui a une seule implémentation).
- HF Space: identique à `latest-remote`. Pas de feature flag à ajouter dans `/api/health` — les chunks canonical font partie du flow doc-centric standard.

### Hard constraints

- Pas de migration SQLite (tables existent déjà).
- Pas de breaking change API (premières routes exposées).
- Performance: les opérations chunk lisent/écrivent ≤ N chunks pour un doc (typiquement < 200). Aucune requête non-bornée. Le rechunk lance Docling chunker en thread (`asyncio.to_thread`), comme `analysis_service.rechunk` actuel.

## 5. Proposed design

<!--
The recommended approach, in enough detail that a competent engineer
outside the immediate context can implement it. Describe contracts, not
code — the PR is where code lives.

Structure this section by layer. Skip a layer if it is genuinely untouched;
do not pad.

### 5.1 Domain
New or changed dataclasses / value objects / ports in `document-parser/domain/`.
No HTTP or DB concerns here. If you are adding a port (`Protocol`), give its
full signature.

### 5.2 Persistence
Schema changes (table, columns, indexes), migration plan, aiosqlite query
shape. Note whether existing rows need a backfill.

### 5.3 Infra adapters
New or changed adapters in `document-parser/infra/` (converter, chunker,
rate limiter, settings). For new env vars, give name / default / allowed
values.

### 5.4 Services
Use-case orchestration in `document-parser/services/`. Services do NOT
implement — they delegate. Describe the call sequence, error handling,
and concurrency (how does this interact with `MAX_CONCURRENT_ANALYSES`?).

### 5.5 API
Endpoint additions / changes in `document-parser/api/`. For each:
  - Method + path
  - Request DTO (Pydantic, camelCase via alias_generator)
  - Response DTO (camelCase; remember `pages_json` stays snake_case)
  - Error responses (status codes, shape)
  - Whether it is excluded from the rate limiter (like `/api/health`)

### 5.6 Frontend — feature module
Which `frontend/src/features/<name>/` folder, which Pinia store actions,
which API client calls in `api.ts`, which Vue components in `ui/`. Name
new `data-e2e` attributes here (Karate needs them).

### 5.7 Cross-cutting
Feature flags (how the backend advertises capability via `/api/health` and
how the frontend reacts), i18n strings (`shared/i18n.ts`), shared types
(`shared/types.ts`).

Prefer mermaid / ASCII for sequence and data flow. Interfaces are more
valuable than pseudocode.
-->

### 5.1 Domain

**Aucun changement.** Tout est en place depuis #205:

- `Chunk(id, document_id, sequence, text, headings, source_page, bboxes, doc_items, token_count, created_at, updated_at, deleted_at)`
- `ChunkEdit(id, document_id, chunk_id, action ∈ INSERT|UPDATE|DELETE|MERGE|SPLIT, actor, at, before, after, parents, children, reason)`
- `ChunkPush(id, document_id, store_id, chunkset_hash, chunk_ids, …)`
- Ports: `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `DocumentChunker`.

### 5.2 Persistence

**Aucun changement.** `chunk_repo.py` et `chunk_edit_repo.py` couvrent CRUD + audit. Le schéma SQLite existe déjà (vérifier `database.py`). Si une colonne ou un index manque pour les nouvelles requêtes (par ex. lookup chunks d'un doc ordonnés par `sequence`), ajouter dans la PR via un script idempotent.

### 5.3 Infra adapters

**Aucun changement.** `DocumentChunker` est déjà implémenté (le même qui sert `analysis_service.rechunk`).

### 5.4 Services

#### Nouveau: `ChunkService` — `document-parser/services/chunk_service.py`

Orchestre toutes les opérations sur le chunkset canonical d'un document. Délègue aux ports existants. Écrit les `ChunkEdit` en transaction avec chaque mutation.

```python
class ChunkService:
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_edit_repo: ChunkEditRepository,
        chunker: DocumentChunker,
        document_repo: DocumentRepository,
        analysis_service: AnalysisService,  # pour le rechunk
    ): ...

    async def list_chunks(self, doc_id: str) -> list[Chunk]: ...
    async def add_chunk(self, doc_id: str, text: str, after_id: str | None) -> Chunk: ...
    async def update_chunk(self, doc_id: str, chunk_id: str, *, text: str | None, headings: list[str] | None) -> Chunk: ...
    async def delete_chunk(self, doc_id: str, chunk_id: str) -> None: ...
    async def split_chunk(self, doc_id: str, chunk_id: str, cursor_offset: int) -> list[Chunk]: ...
    async def merge_chunks(self, doc_id: str, ids: list[str]) -> Chunk: ...
    async def rechunk_document(self, doc_id: str, opts: ChunkingOptions | None) -> list[Chunk]: ...
    async def get_tree(self, doc_id: str) -> list[DocTreeNode]: ...
    async def diff_against_store(self, doc_id: str, store: str) -> list[ChunkDiff]: ...
    async def push_to_store(self, doc_id: str, store: str) -> ChunkPush: ...
```

Règles d'invariants:
- `sequence` des chunks reste dense ascendant. `add_chunk` insère et incrémente les suivants. `delete_chunk` est soft (marque `deleted_at`) pour préserver l'audit; les listings filtrent.
- Toute mutation produit **une ligne `ChunkEdit`** atomiquement.
- `rechunk_document`: appelle `analysis_service.rechunk_for_document(doc_id, opts)` (helper public à exposer dans `AnalysisService` si pas déjà), récupère la liste de chunks, **remplace** le chunkset canonical (delete soft de l'ancien + insert nouveau), enregistre un `ChunkEdit` `RESET`.
- `get_tree`: dérive de la dernière `AnalysisJob` réussie (lecture de `pages_json` / `document_json`). Pas de calcul nouveau.
- `push_to_store` et `diff_against_store`: délèguent à `ingestion_service` / `store_service` existants. Aucune logique dupliquée; le service expose juste l'interface "doc-centric".

#### Hook de promotion canonical — `AnalysisService.create`

À la fin d'une analyse réussie, si le document n'a pas encore de chunkset canonical (`chunk_repo.count_for_document(doc_id) == 0`), peupler depuis `job.chunks_json`:

```python
async def create(self, ...) -> AnalysisJob:
    job = await self._run_analysis(...)
    if job.status == AnalysisStatus.COMPLETED and job.chunks_json:
        if await self._chunk_repo.count_for_document(job.document_id) == 0:
            await self._promote_to_canonical(job)  # nouveau private method
    return job
```

Promotion = parse `chunks_json` → instancie `Chunk(document_id=…)` → `chunk_repo.bulk_insert(chunks)` → `chunk_edit_repo.insert(ChunkEdit(action=INSERT, actor='system:initial-analysis'))`.

C'est le **seul** point qui croise les deux contextes (analyse → doc canonical). Reste local à `AnalysisService`.

### 5.5 API

#### Nouveau router: `document-parser/api/document_chunks.py`

Préfixe `/api/documents/{doc_id}`, tag `documents`. Toutes les routes injectent `ChunkService` via `Depends`.

```python
@router.get("/{doc_id}/chunks", response_model=list[ChunkResponse])
@router.post("/{doc_id}/chunks", response_model=ChunkResponse)                 # body: AddChunkRequest
@router.patch("/{doc_id}/chunks/{chunk_id}", response_model=ChunkResponse)     # body: UpdateChunkRequest
@router.delete("/{doc_id}/chunks/{chunk_id}", status_code=204)
@router.post("/{doc_id}/chunks/{chunk_id}/split", response_model=list[ChunkResponse])  # body: SplitChunkRequest { cursorOffset }
@router.post("/{doc_id}/chunks/merge", response_model=ChunkResponse)           # body: MergeChunksRequest { ids }
@router.post("/{doc_id}/rechunk", response_model=list[ChunkResponse])          # body: RechunkRequest (optionnel)
@router.get("/{doc_id}/tree", response_model=list[DocTreeNodeResponse])
@router.get("/{doc_id}/diff", response_model=list[ChunkDiffResponse])          # query: store
@router.post("/{doc_id}/chunks/push", response_model=PushSummaryResponse)      # body: PushRequest { store }
```

Note: deux URLs présentes côté front pour push (`/{id}/push` dans `document/api.ts` et `/{id}/chunks/push` dans `chunks/api.ts`). Une seule route doit exister côté backend pour respecter la directive "no duplicate". **Choix**: garder `/{id}/chunks/push` (sémantiquement plus juste — c'est bien des chunks qu'on pousse). Mettre à jour `features/document/api.ts:34-39` pour cibler la même URL et virer la duplication.

DTOs Pydantic: tous camelCase (alias_generator), `chunkId` au lieu de `chunk_id` côté wire, `sourcePage` etc.

Erreurs:
- `404` si doc inexistant ou chunk inexistant
- `409` si `merge_chunks` reçoit des ids non contigus (invariant `sequence`)
- `400` si `split` reçoit un `cursorOffset` hors range

### 5.6 Frontend — feature module

**Zéro changement attendu.** `features/chunks/api.ts` et `features/document/api.ts` sont déjà alignés.

Une seule correction à apporter pour respecter "no duplicate endpoints": modifier `features/document/api.ts:35` pour pointer sur `/api/documents/${id}/chunks/push` au lieu de `/api/documents/${id}/push`. Ensuite cette fonction `pushDocumentToStore` peut être supprimée et le caller (`document/store.ts`) bascule sur `pushChunksToStore` de `features/chunks/api.ts`.

Bug latents identifiés par l'audit, à corriger dans la même PR (scope #256):
- `ChunksEditor.vue:235` — `saveTimer` non clearé sur `onUnmounted`. Ajouter `onBeforeUnmount(() => clearTimeout(saveTimer))`.
- `ChunksEditor.vue:215` — remplacer `alert(...)` natif par le pattern toast partagé.

### 5.7 Cross-cutting (feature flags, i18n, shared types)

- **Feature flags**: aucun. Le mode chunk est un flow standard du doc-centric, pas optionnel.
- **i18n**: aucune nouvelle clé requise; les strings existent déjà côté `chunks.*`.
- **Shared types**: `DocChunk`, `ChunkDiff`, `PushSummary`, `DocTreeNode` existent déjà dans `frontend/src/shared/types.ts`. Vérifier la correspondance camelCase avec les nouveaux DTOs Pydantic; aucun champ nouveau attendu.

## 6. Alternatives considered

<!--
At least two genuine alternatives, each with a one-paragraph description
and the reason it was rejected. "Do nothing" is often a legitimate
alternative — name it if it is. Reviewers use this section to sanity-check
that the recommended design was a choice and not the first thing that
came to mind.

If one of the alternatives represents a significant architectural fork
(e.g. introducing a new service, replacing a library), spawn an ADR under
`docs/architecture/adrs/` and link it in §12 — the design doc captures the
local decision, the ADR captures the cross-cutting one.
-->

### Alternative A — Recâbler le front sur `/api/analyses/*`

- **Summary:** Côté front, résoudre `docId → latest analysis jobId` dans `DocWorkspacePage`, puis appeler les endpoints `/api/analyses/{jobId}/...` existants (rechunk, chunks/{idx}, etc.). Aucun nouveau endpoint backend.
- **Why not:** Conceptuellement faux. Une analyse est une run éphémère avec ses propres pipeline options; un document a un état chunk canonical persistant édité dans le temps. Identifier les deux casserait le modèle 0.6.0 doc-centric et empêcherait d'avoir plusieurs analyses parallèles d'un doc (ce que StudioPage permet) sans muter l'état canonical. Casse aussi l'audit log par chunk (`ChunkEdit`) qui est par doc, pas par job.

### Alternative B — Fusion `Analysis` ↔ `Document chunks`

- **Summary:** Supprimer `analysis_jobs.chunks_json`, faire que toute analyse écrive directement dans la table `chunks` du doc. StudioPage devient une UI de re-chunking d'un doc.
- **Why not:** Casse l'usage debug de StudioPage (plusieurs runs avec pipeline options ≠ ne peuvent pas coexister). Refactor majeur, hors scope d'un bug fix. Pourrait être envisagé en 0.7.0+ si l'usage de StudioPage évolue.

## 7. API & data contract

### Endpoints (tous nouveaux, additifs)

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET    | `/api/documents/{id}/chunks` | — | `ChunkResponse[]` | additive |
| POST   | `/api/documents/{id}/chunks` | `AddChunkRequest` `{text, afterId?}` | `ChunkResponse` | additive |
| PATCH  | `/api/documents/{id}/chunks/{chunkId}` | `UpdateChunkRequest` `{text?, headings?}` | `ChunkResponse` | additive |
| DELETE | `/api/documents/{id}/chunks/{chunkId}` | — | 204 | additive |
| POST   | `/api/documents/{id}/chunks/{chunkId}/split` | `SplitChunkRequest` `{cursorOffset}` | `ChunkResponse[]` | additive |
| POST   | `/api/documents/{id}/chunks/merge` | `MergeChunksRequest` `{ids}` | `ChunkResponse` | additive |
| POST   | `/api/documents/{id}/rechunk` | `RechunkRequest` `{chunkingOptions?}` | `ChunkResponse[]` | additive |
| GET    | `/api/documents/{id}/tree` | — | `DocTreeNodeResponse[]` | additive |
| GET    | `/api/documents/{id}/diff?store={name}` | — | `ChunkDiffResponse[]` | additive |
| POST   | `/api/documents/{id}/chunks/push` | `PushRequest` `{store}` | `PushSummaryResponse` | additive |

Sérialisation **camelCase** côté wire (Pydantic `alias_generator`), snake_case interne. `pages_json` reste l'exception documentée si réutilisé.

### Persistence schema

```sql
-- Aucune migration. Tables existantes (issue #205):
-- chunks(id, document_id, sequence, text, headings_json, source_page, bboxes_json,
--        doc_items_json, token_count, created_at, updated_at, deleted_at)
-- chunk_edits(id, document_id, chunk_id, action, actor, at, before_json, after_json,
--             parents_json, children_json, reason)
-- chunk_pushes(id, document_id, store_id, chunkset_hash, chunk_ids_json, ...)
```

### Env vars / config

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| _(aucune)_ | | | Le `ChunkService` ne lit aucune nouvelle config. |

### Breaking changes

**Aucun.** Toutes les routes sont additives, premier passage live. Côté front, suppression de l'alias `pushDocumentToStore` (URL `/push`) au profit de `pushChunksToStore` (URL `/chunks/push`) — pas exposé externement.

<!--
Make the wire contract explicit — this is what the frontend, e2e tests,
and any external consumer will code against.

### Endpoints
| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
|        |      |         |          |           |

Remember:
  - API serialization is camelCase (Pydantic `alias_generator`).
  - Backend internals stay snake_case.
  - `pages_json` is the documented exception — it carries raw
    `dataclasses.asdict()` output (snake_case).
  - Health endpoint (`/api/health`) may need new fields if this design adds
    a feature flag.

### Persistence schema
```sql
-- ALTER TABLE / CREATE TABLE statements, with reasoning
```

### Env vars / config
| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
|      |         |         |       |

### Breaking changes
Enumerate anything a consumer must change. If there are none, say so
explicitly — "additive only" is a useful commitment.
-->

## 8. Risks & mitigations

<!--
One row per non-trivial risk. Map each to an audit dimension so the
release-gate audit has a clear hook:

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|-----------|--------|---------------|------------------------|
|      | Security        |           |        |               |                        |
|      | Performance     |           |        |               |                        |
|      | Decoupling      |           |        |               |                        |

Common families to scan for:
  - **Hexagonal Architecture:** cross-layer imports, leaking HTTP into domain, adapter bypassing its port
  - **Security:** rate limiter bypass, path traversal on uploads, SSRF via
    the remote converter, unauthenticated data exposure
  - **Performance:** synchronous work on the FastAPI event loop,
    unbounded queries, new work inside `MAX_CONCURRENT_ANALYSES` budget
  - **Tests:** coverage gap on a critical path
  - **Documentation:** missing README / env var / i18n entry

A design with "no risks identified" is a design that has not been read
carefully.
-->

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Promotion canonical s'exécute deux fois (race) sur deux analyses simultanées d'un doc neuf, dupliquant le chunkset | DDD / Decoupling | basse | élevée (corruption canonical) | tests d'intégration concurrent + count_for_document inattendu en prod | Garde idempotente dans `_promote_to_canonical` (vérif count + insert sous transaction unique) |
| Régression OCR Debug si `analysis_service.create` modifié maladroitement | Tests / Decoupling | moyenne | élevée (StudioPage cassé) | non-régression e2e Karate `full-happy-path.feature` | Hook de promotion isolé en méthode privée, tests pytest qui couvrent les deux cas (analyse 1ère, analyse N) |
| Endpoint `/diff` lent si beaucoup de chunks × store comparé | Performance | basse | moyenne | logs de durée > 1s | Borne dure (max 500 chunks par doc), pagination si dépassé en 0.7 |
| `ChunkEdit` audit log non écrit en cas d'erreur partielle (ex: split crash après insert chunk 1/2) | Hexagonal Architecture / DDD | moyenne | moyenne (audit incohérent) | tests intégration + assert chunk_edit count après chaque mutation | Toutes les mutations en transaction aiosqlite unique chunk + edit |
| `pushDocumentToStore` (URL legacy `/push`) encore appelé quelque part en prod | Decoupling | basse | basse (404 silencieux) | grep + e2e | Suppression complète de la fonction TS, pas d'alias |
| Test e2e Karate flaky si l'analyse initiale n'a pas eu le temps de promouvoir | Tests | moyenne | basse | flaky en CI | E2E poll sur `lifecycle_state == 'parsed'` avant de cliquer sur l'onglet chunk |

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`)

- **Unit `tests/services/test_chunk_service.py`**:
  - `list_chunks` filtre les `deleted_at` non null
  - `add_chunk` insert + audit `INSERT` + recale les `sequence` suivants
  - `update_chunk` modifie + audit `UPDATE` avec `before/after` correctement remplis
  - `delete_chunk` soft-delete + audit `DELETE`
  - `split_chunk` produit 2 chunks + 2 audit `SPLIT` avec `parents = [source_id]`
  - `merge_chunks` produit 1 chunk + 1 audit `MERGE` avec `parents = [ids]`
  - `merge_chunks` rejette ids non contigus (409)
  - `rechunk_document` remplace canonical et écrit un audit `RESET`
  - `push_to_store` délègue à `ingestion_service` (mock)
  - `diff_against_store` délègue à `store_service` (mock)
- **Unit `tests/services/test_analysis_service.py` (existant, à étendre)**:
  - `create()` peuple chunks canonical à la 1ère analyse réussie
  - `create()` ne touche PAS au canonical aux analyses suivantes (idempotence)
  - `create()` ne crée rien si l'analyse échoue
- **Integration `tests/api/test_document_chunks.py`**:
  - Chaque route → 200 happy path
  - Chaque route → 404 si doc inexistant
  - Chaque route mutante → 404 si chunk inexistant
  - `merge` → 409 si non contigus
  - `split` → 400 si offset hors range
  - DTOs camelCase respectés sur input ET output
- **Architecture tests**: vérifier que `api/document_chunks.py` n'importe pas `persistence/*` directement.

### Frontend — Vitest

- **`features/chunks/api.test.ts` (existant, à étendre)**:
  - Tests d'erreur HTTP (404, 500) sur `fetchChunks`, `updateChunk`, `mergeChunks`, `splitChunk`, `dropChunk`, `addChunk`, `fetchChunkDiff`, `pushChunksToStore`
- **`features/chunks/store.test.ts` (existant, à étendre)**: `$reset` à chaque changement de `docId` (corrige le bug latent identifié dans l'audit).
- **`features/document/api.test.ts`**: ajouter tests pour `fetchDocumentTree`, `rechunkDocument`. Supprimer `pushDocumentToStore` (réécriture vers `pushChunksToStore`).
- **`features/document/store.test.ts`**: idem.

### E2E — Karate UI (`e2e/`)

- **Nouveau `e2e/ui/src/test/resources/documents/doc-tab-chunk-mode.feature`**:
  - Setup via API: upload doc → wait `lifecycle_state == 'parsed'`
  - UI: ouvrir `/docs/{id}` → cliquer onglet **Doc** → activer mode `chunk`
  - Assert: liste de chunks visible, **pas** de bannière 404, count > 0
  - Edit un chunk → assert persistence après reload
  - Cleanup via API: delete doc
  - Tags: `@critical @ui`
- **Non-régression sur OCR Debug**: vérifier que `e2e/ui/src/test/resources/full-happy-path.feature` (StudioPage) reste vert après les modifications.

### Manual QA

1. `docker-compose -f docker-compose.dev.yml up`
2. Upload un PDF via `/docs/new`, attendre status `parsed`
3. Ouvrir `/docs/{id}` → onglet **Doc** → bouton **chunk** → vérifier liste affichée
4. Ouvrir `/studio` → upload + run analyse OCR → vérifier que c'est inchangé
5. Push doc vers un store → vérifier `/api/documents/{id}/diff?store=…`

### Performance / load

Pas d'objectif chiffré particulier. Surveiller: `rechunk_document` doit rester sous le budget `MAX_CONCURRENT_ANALYSES` (réutilise le même mécanisme que `analysis_service.rechunk`).

<!--
How this design will be verified. Be specific — name files / suites.

### Backend — pytest (`document-parser/tests/`)
  - Unit: per-layer (`tests/domain/`, `tests/persistence/`, `tests/services/`)
  - Integration: services wired with real aiosqlite + real adapters
  - Architecture tests (if applicable): enforce import boundaries

### Frontend — Vitest (`frontend/src/**/*.test.ts`)
  - Stores: actions / getters / mocked API
  - Pure helpers (e.g. `bboxScaling.ts`-style modules): deterministic
  - Components only when behavior is non-trivial; do not test markup

### E2E — Karate UI (`e2e/`)
  - Use `data-e2e` selectors — never CSS classes (see e2e/CONVENTIONS.md)
  - `retry()` / `waitFor()` — never `Thread.sleep()` / `delay()`
  - Setup via API, verify via UI, cleanup via API
  - Tag appropriately: `@critical` / `@ui` / `@smoke` / `@regression` / `@e2e`
  - **Never Playwright** — Karate is the tool here.

### Manual QA
Steps the reviewer can run locally (`docker-compose.dev.yml` up, scenario
to reproduce). Keep it short — if the manual list is long, automate more.

### Performance / load
Required when the design claims a latency / throughput / memory property,
or touches the conversion hot path.
-->

## 10. Rollout & observability

### Release branch

`release/0.6.0` — c'est l'objet du milestone "Doc-centric ingest". Branche de travail: `fix/256-doc-tab-chunk-mode-404`.

### Feature flag / staged rollout

**Aucun flag.** Le mode chunk fait partie du flow standard 0.6.0; pas de fallback derrière un toggle. La promotion canonical des chunks à la 1ère analyse est inconditionnelle.

### Observability

- Logs structurés à ajouter dans `ChunkService`:
  - `chunk.add docId=… chunkId=… sequence=…`
  - `chunk.update docId=… chunkId=…`
  - `chunk.delete docId=… chunkId=…`
  - `chunk.split docId=… sourceId=… newIds=…`
  - `chunk.merge docId=… sourceIds=… newId=…`
  - `chunk.rechunk docId=… count=… durationMs=…`
  - `chunk.push docId=… store=… count=…`
  - `chunk.promote docId=… count=… (initial-analysis)`
- Pas de nouvelle métrique Prometheus.
- Erreurs: les `HTTPException` 4xx ne loggent pas (normal); les 5xx loggent avec stack via `logger.exception` (pattern existant dans `documents.py:131`).

### Rollback plan

- Le déploiement est entièrement additif (nouvelles routes + nouveau service). Rollback = revert du commit / image précédente. Aucun changement de schéma à défaire.
- Si un bug critique apparaît côté promotion canonical: désactiver le hook dans `analysis_service.create` via revert ciblé; les analyses continuent de fonctionner sans canonical (l'onglet chunk redeviendrait 404, état antérieur). Pas de perte de données.
- Si un bug critique apparaît côté API chunks: revert du router suffit; l'onglet chunk redevient 404, le reste de l'app reste fonctionnel.

Liens:
- Deployment: `docs/release/*` (`/release:deploy`)
- Rollback: `/release:rollback`
- Incident: `docs/operations/*` (`/ops:incident`)

<!--
How this change gets to production safely.

### Release branch
Which `release/X.Y.Z` is the target? Any coordination with a parallel
release (e.g. R&D branch)?

### Feature flag / staged rollout
Does the change hide behind a flag surfaced via `/api/health`? If so, what
flips the flag, and what is the default? HF Space deployments often need
`deploymentMode === 'huggingface'` gating.

### Observability
  - Logs to add / extend (structured, low-cardinality keys)
  - Metrics / counters (if added — call out any new Prometheus names)
  - New error modes to watch for in `analysis_jobs.status = FAILED`

### Rollback plan
The revert that is safe to apply at any time:
  - Which migration is reversible? Which is not?
  - Which env var flip disables the feature without a redeploy?
  - Any data cleanup needed after rollback?

Link to the existing release / ops playbooks:
  - Deployment: `docs/release/*` (also surfaced via `/release:deploy`)
  - Rollback: also surfaced via `/release:rollback`
  - Incident: `docs/operations/*` (also surfaced via `/ops:incident`)
-->

## 11. Open questions

- Le port `DocumentChunker` accepte-t-il `cursor_offset` pour `split`, ou faut-il l'implémenter manuellement dans `ChunkService.split_chunk` (split textuel basique sans repasser dans Docling) ? À vérifier au moment de l'implémentation.
- Faut-il enregistrer un `ChunkEdit` `RESET` lors du `rechunk_document`, ou un `DELETE` par chunk + `INSERT` par nouveau chunk ? Décision: une seule entrée `RESET` (lisibilité audit), avec `parents = [old_ids]`, `children = [new_ids]`.
- `get_tree`: lit-on `pages_json` ou `document_json` ? À confirmer en lisant `analysis_service.find_by_id` — probablement `document_json` qui contient la structure docling complète.

## 12. References

<!--
Links to everything a future reader would want.
-->

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/256
- **Related PRs / commits:**
- **ADRs:** <ADR-NNN or "none planned">
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
- **External:** <specs, upstream issues, dashboards, third-party docs>

# Rapport d'audit : Domain-Driven Design (DDD)

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 16 / 18 |
| Score | 92 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

---

## Ecarts constates

### [MAJ] Ubiquitous language — "job" vs "push" sur l'endpoint push-chunks

- **Localisation** :
  - `document-parser/api/schemas.py:437-439` (`PushChunksResponse.job_id`)
  - `document-parser/api/document_chunks.py:206-220` (route `POST /chunks/push`, mapping `job_id=result["jobId"]`)
  - `document-parser/services/chunk_service.py:649-685` (construction `ChunkPush` + retour `{"jobId": push.id, ...}`)
  - `frontend/src/shared/types.ts:190-193` (`PushSummary` — pas de "job")
  - `frontend/src/features/chunks/ui/ChunksEditor.vue:211-216` (`const jobId = await chunksStore.push(...)` + `alert(t('chunks.pushedJob', { jobId }))`)
  - `frontend/src/shared/i18n.ts:534` (FR : `'chunks.pushedJob': 'Job lance : {jobId}'`)
  - `frontend/src/shared/i18n.ts:1161` (EN : `'chunks.pushedJob': 'Job dispatched: {jobId}'`)
- **Constat** : Le concept metier modelise dans le domaine est `ChunkPush` (`document-parser/domain/models.py:285-298`) — une ligne d'audit immuable representant un push d'un chunkset vers un store. L'API HTTP, la couche service et le frontend exposent pourtant cet identifiant sous le nom `jobId` / `job_id`. Le terme "job" n'apparait nulle part dans le domaine pour ce concept ; le seul `Job` du modele est `AnalysisJob` (un objet completement different — execution asynchrone de conversion). Le wording user-facing ("Job dispatched / Job lance") renforce la confusion : l'utilisateur voit "Job" alors que la mecanique sous-jacente est un evenement de push (`ChunkPush` insere dans `chunk_pushes`). C'est exactement le meme type de derive que l'ecart 2.3.1 de la release 0.5.0 (cette fois localise sur l'API push au lieu de l'API ingestion).
- **Regle violee** : 2.3.1 — Vocabulaire metier coherent entre domain, services, API et frontend
- **Remediation** : Renommer le champ wire `job_id` -> `push_id` (camelCase `pushId`) dans `PushChunksResponse`, le payload du service `push_to_store`, et tous les usages frontend (`ChunksEditor.vue`, store `chunks/store.ts:195`, tests). Renommer la cle i18n `chunks.pushedJob` -> `chunks.pushRecorded` avec un libelle "Push enregistre : {pushId}" / "Push recorded: {pushId}". Le concept reste un `ChunkPush`, pas un job — l'API doit refleter le vocabulaire du domaine.

### [MIN] AnalysisJob et Chunk restent mutables hors du service

- **Localisation** :
  - `document-parser/domain/models.py:78-139` (`@dataclass AnalysisJob`, mutable)
  - `document-parser/domain/models.py:226-253` (`@dataclass Chunk`, mutable)
- **Constat** : Identique a l'ecart MIN de la release 0.5.0, non remediee. `AnalysisJob` et `Chunk` sont des dataclasses non gelees. Les methodes `mark_running()`, `mark_completed()`, `update_progress()`, `mark_failed()` (lignes 98-139) verifient les transitions d'etat, mais une fois un `AnalysisJob` retourne hors du service un appelant externe peut toujours modifier directement `job.status = ...` ou `chunk.text = ...`. L'invariant "PENDING -> COMPLETED interdit" reste applique par la logique metier mais pas par le systeme de types. `Chunk` (introduit pour #205) presente le meme profil — `chunk.deleted_at = None` peut etre re-arme depuis l'exterieur, contournant la verification d'idempotence dans `chunk_editing.delete()`.
- **Regle violee** : 2.4.2 — Les invariants metier sont proteges dans le domaine
- **Remediation** : Considerer de geler les entites (`@dataclass(frozen=True)`) et passer par des methodes qui retournent une nouvelle instance (style event-sourcing leger comme `ChunkEdit`). Acceptable en l'etat car le service controle les mutations ; recommande pour 0.7.x dans le cadre d'un effort plus large autour des invariants metier.

---

## Points positifs

- **MAJ 0.5.0 remediee** (2.3.1 partiel) : L'endpoint `/api/ingestion/{analysis_id}` (`document-parser/api/ingestion.py:41-68`) utilise desormais `analysis_id` partout — path param, docstring ("Takes the chunks from an existing analysis"), parametre client. La derive `job_id` / "analysis job" dans cette route est corrigee. Variables Python internes (`job = await analysis.find_by_id(...)`) restent acceptables comme note dans le rapport 0.5.0.
- **Bounded contexts elargis et clairs** (2.1.1 ✓) : Six contextes metier explicites — `document`, `analysis`, `chunks` (canonical + edits + pushes), `stores`, `versions`, `ingestion` — chacun avec ses propres modeles, services et repositories. Le frontend (`frontend/src/features/`) mirroite cette decoupe avec ses 10 features.
- **Pas de god object** (2.1.2 ✓) : `domain/models.py` fait 331 lignes mais reparties en 9 entites distinctes (Document, AnalysisJob, Store, DocumentStoreLink, Chunk, ChunkEdit, ChunkPush, DocumentVersion, DocumentVersionKind). Aucune classe ne depasse 70 lignes. La logique pure du chunkset est isolee dans `domain/chunk_editing.py` (216 lignes, fonctions pures).
- **Separation par ports** (2.1.3 ✓) : `domain/ports.py` definit 12 protocoles abstraits (`DocumentConverter`, `DocumentChunker`, `DocumentRepository`, `StoreRepository`, `DocumentStoreLinkRepository`, `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `AnalysisRepository`, `EmbeddingService`, `VectorStore`, `LLMProvider`, `ReasoningRunner`). Aucune dependance inverse de l'infrastructure dans le domaine.
- **Value objects correctement immutables** (2.2.2 ✓) : Tous les VO sont `@dataclass(frozen=True)` : `PageElement`, `PageDetail`, `ConversionOptions`, `ConversionResult`, `ChunkingOptions`, `ChunkBbox`, `ChunkDocItem`, `ChunkResult`, `ChunkEdit`, `ChunkPush`, `ReasoningIteration`, `ReasoningResult`, `ChunkBboxEntry`, `DocItemRef`, `ChunkOrigin`, `IndexedChunk`, `SearchResult`, `DocumentLifecycleChanged`. Aucun setter detecte.
- **Anti-corruption layer efficace** (2.5.2, 2.5.3 ✓) : `grep -rn "from docling\|import docling" document-parser/services/` retourne ZERO match. Les adaptateurs infra (`local_converter.py`, `serve_converter.py`, `docling_tree.py`, `docling_agent_reasoning.py`) transforment les types Docling en value objects domaine. Les schemas Pydantic (`api/schemas.py`) traduisent les payloads camelCase HTTP en objets domaine.
- **Repositories manipulent des entites domaine** (2.5.1 ✓) : `SqliteAnalysisRepository`, `SqliteDocumentRepository`, `SqliteChunkRepository`, `SqliteChunkEditRepository`, `SqliteChunkPushRepository`, `SqliteStoreRepository`, `SqliteDocumentStoreLinkRepository`, `SqliteDocumentVersionRepository` travaillent tous avec des entites typees — jamais avec des Row objects bruts.
- **State machine domaine explicite** (2.4.2 ✓ partiel) : `domain/lifecycle.py` definit `_TRANSITIONS` (table de transitions admises) + `assert_transition()` qui leve `InvalidLifecycleTransitionError`. `Document.transition_to()` (`models.py:49-75`) est la seule porte de mutation et emet un evenement `DocumentLifecycleChanged`. L'aggregation lifecycle multi-stores (`domain/lifecycle_aggregation.py`) est une fonction pure.
- **Audit log immuable** (2.4.2 ✓) : `ChunkEdit` est `@dataclass(frozen=True)` — chaque mutation de chunkset emet une ligne d'audit immutable. `SqliteChunkEditRepository` n'expose ni update ni delete (commentaire explicite ligne 50-56 : "The audit log is append-only").
- **Statuts metier explicites avec enums type-safe** (2.3.3 ✓) : `AnalysisStatus` (PENDING/RUNNING/COMPLETED/FAILED), `DocumentLifecycleState` (Uploaded/Parsed/Chunked/Ingested/Stale/Failed), `DocumentStoreLinkState` (Ingested/Stale/Failed), `ChunkEditAction` (insert/update/delete/merge/split), `StoreKind` (opensearch/neo4j), `DocumentVersionKind` (analysis/chunks), `LLMProviderType` (ollama). Tous derives de `StrEnum`.
- **Frontend respecte les bounded contexts** (2.1.4 ✓) : `frontend/src/shared/types.ts` mirroite exactement le vocabulaire backend (`Document`, `DocumentLifecycleState`, `DocStoreLink`, `Analysis`, `DocChunk`, `ChunkDiff`, `DocumentVersion`, `DocumentVersionKind`). Les features sont alignees sur les bounded contexts (`/analysis`, `/document`, `/chunks`, `/chunking`, `/ingestion`, `/store`, `/history`, `/reasoning`, `/search`, `/settings`, `/feature-flags`).
- **Pas de termes generiques** (2.3.2 ✓) : `grep "Manager\|Handler\|Processor"` dans `domain/` + `services/` ne retourne aucun match. Tous les noms refletent le vocabulaire metier (`AnalysisService`, `ChunkService`, `StoreService`, `VersionService`, `IngestionService`, `DocumentService`, `StoreBackendResolver`).
- **DDD-granular API** (regle architecturale documentee dans `document-parser/CLAUDE.md`) : Documentation explicite "no UX-shaped routes" + `docs/design/269-backend-ddd-audit.md` cite — l'audit DDD est explicitement integre dans la regle de design.
- **Aggregats lies par identites** (2.4.1, 2.4.3 ✓) : `DocumentStoreLink.mark_ingested/mark_stale/mark_failed`, `Document.transition_to`, `AnalysisJob.mark_*` — toutes les mutations passent par la racine de l'aggregat.

---

## Verdict partiel : GO

**Justification** :
- Score 92/100 (>= 80) ✓
- 0 ecarts CRITICAL ✓
- 1 seul ecart MAJOR (derive ubiquitous language sur push/job, miroir de l'ecart 0.5.0 sur ingestion/analysis) — corrigeable en post-release
- 1 ecart MINOR carry-over de 0.5.0 (immutabilite additionnelle des entites, amelioration plutot que violation)

L'architecture DDD reste solide : bounded contexts plus nombreux qu'en 0.5.0 (stores, versions, chunks-canonical ajoutes) et toujours bien isoles, anti-corruption layer efficace (zero leak Docling vers services), invariants maintenus via methodes de transition et state machine explicite. Le nouveau MAJ est de meme nature que celui de 0.5.0 (vocabulaire wire qui s'ecarte du domaine) — un seul endroit affecte, fix mecanique (rename `jobId` -> `pushId`).

**Delta vs 0.5.0** :
- MAJ 0.5.0 (ingestion `job_id`) -> **remediee** ✓
- MIN 0.5.0 (AnalysisJob mutable) -> **non remediee**, etendue a `Chunk` (introduit en 0.6.x)
- NOUVEAU MAJ 0.6.1 : `PushChunksResponse.job_id` / `jobId` cote frontend pour designer un `ChunkPush`

**Conditions pour GO** :
- Le MAJ est non-bloquant en 0.6.1 (release deja en branche).
- Recommandation : inclure le rename `jobId` -> `pushId` dans la branche 0.6.2 (effort < 1h : 3 fichiers backend, 5 fichiers frontend, 2 cles i18n). Verifier qu'aucun autre wire field ne reutilise le pattern "job" pour designer un evenement metier (search `grep -rn "job_id\b" document-parser/api/schemas.py`).

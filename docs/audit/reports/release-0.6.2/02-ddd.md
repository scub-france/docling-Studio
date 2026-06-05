# Rapport d'audit : Domain-Driven Design (DDD)

**Release** : 0.6.2 (branche `release/0.6.2`, HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.6.1-reaudit/02-ddd.md` (97/100, GO, 1 MIN)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 17 / 18 |
| Score | 97 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

Detail du calcul (poids totaux = 35) :

- Items poids 3 (CRIT si non conforme) : 2.1.1, 2.1.2, 2.2.3, 2.4.2, 2.5.3 — tous conformes (15/15).
- Items poids 2 (MAJ si non conforme) : 2.1.3, 2.1.4, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.3, 2.5.1, 2.5.2 — tous conformes (18/18).
- Items poids 1 (MIN si non conforme) : 2.2.4, 2.3.2, 2.3.3 — tous conformes (3/3).
- Carry-over 0.5.0 / 0.6.1 / 0.6.1-reaudit sur 2.4.2 (immutabilite type-system des entites `AnalysisJob`, `Chunk`, `DocumentStoreLink`, `Document`, `Store`, `DocumentVersion`) : meme observation degradee en MIN car l'invariant *est* protege par les methodes de transition. Calcul aligne sur le rapport 0.6.1-reaudit.

```
score = (35 - 1) / 35 * 100 ≈ 97.1 → 97
```

---

## Perimetre du diff vs 0.6.1-reaudit

Entre `f9e5619` (HEAD 0.6.1-reaudit) et `051ac4a` (HEAD 0.6.2), **aucun fichier de `domain/`, `services/`, `api/`, `persistence/` ni `frontend/src/` n'a ete modifie**. La branche 0.6.2 ne touche que :

- `document-parser/.dockerignore`, `document-parser/Dockerfile`
- `document-parser/pyproject.toml`, `document-parser/uv.lock`, `document-parser/requirements*.txt` (migration vers uv, #254)
- `document-parser/infra/serve_converter.py` (carry de `self_ref` dans `ServeConverter`, commit `3936166`)
- `document-parser/tests/test_architecture.py`, `document-parser/tests/test_serve_converter.py`

Le seul touch fonctionnel relevant pour DDD est `infra/serve_converter.py` qui propage `self_ref` jusqu'aux `PageElement` du domaine — cela renforce 2.5.3 (les value objects domain restent la sortie, aucune fuite Docling vers `services/`) plutot que de le degrader.

---

## Verification par item

### 2.1 Bounded Contexts

| # | Item | Poids | Statut | Citation |
|---|------|-------|--------|----------|
| 2.1.1 | Contextes metier identifies et isoles | 3 | OK | Six contextes : `document`, `analysis`, `chunks`, `stores`, `versions`, `ingestion` — chacun avec ses propres entites dans `document-parser/domain/models.py` et son service dedie dans `document-parser/services/` (un fichier par contexte) |
| 2.1.2 | Pas de god object partage entre contextes | 3 | OK | `document-parser/domain/models.py` 331 lignes, 9 entites distinctes < 70 lignes chacune. Chunk editing isole dans `document-parser/domain/chunk_editing.py:1-216` |
| 2.1.3 | Frontieres entre contextes explicites (DTOs / ports) | 2 | OK | `document-parser/domain/ports.py:90-209` definit 8 repositories distincts (Document/Store/DocumentStoreLink/Chunk/ChunkEdit/ChunkPush/Analysis), un par bounded context. Aucun import croise direct |
| 2.1.4 | Frontend respecte les memes bounded contexts | 2 | OK | `frontend/src/features/` : `analysis`, `chunks`, `chunking`, `document`, `history`, `ingestion`, `reasoning`, `search`, `store` — mirror exact des contextes backend |

### 2.2 Entites et Value Objects

| # | Item | Poids | Statut | Citation |
|---|------|-------|--------|----------|
| 2.2.1 | Entites = identite + cycle de vie | 2 | OK | `Document.id` (`models.py:39`), `AnalysisJob.id` (`models.py:80`), `Store.id` (`models.py:161`), `DocumentStoreLink.id` (`models.py:192`), `Chunk.id` (`models.py:242`), `DocumentVersion.id` (`models.py:325`). Cycle de vie : `Document.transition_to` (`models.py:49-75`), `AnalysisJob.mark_running/completed/failed` (`models.py:98-139`), `DocumentStoreLink.mark_ingested/stale/failed` (`models.py:201-223`) |
| 2.2.2 | Value objects immutables | 2 | OK | `value_objects.py:79,92,100,118,128,140,146,154,180,194` — tous `@dataclass(frozen=True)` : `PageElement`, `PageDetail`, `ConversionOptions`, `ConversionResult`, `ChunkingOptions`, `ChunkBbox`, `ChunkDocItem`, `ChunkResult`, `ReasoningIteration`, `ReasoningResult`. `ChunkEdit` et `ChunkPush` egalement frozen (`models.py:256,284`). `IndexedChunk` et `SearchResult` (`vector_schema.py`) restent frozen. `GraphPayload` (`value_objects.py:212`) est un container DTO en sortie, non un VO d'identite — acceptable non-frozen |
| 2.2.3 | Pas de persistence dans les VO | 3 | OK | `grep -n "def save\|def update\|def delete" document-parser/domain/value_objects.py` → ZERO match. Les VO n'embarquent que `is_default()` (pure). Persistence centralisee dans `document-parser/persistence/` |
| 2.2.4 | Entites portent du comportement metier | 1 | OK | `Document.transition_to` valide la transition lifecycle (`models.py:49-75`), `AnalysisJob.mark_running/mark_completed/update_progress/mark_failed` portent les regles de transition d'etat (`models.py:98-139`), `DocumentStoreLink.mark_ingested/stale/failed` (`models.py:201-223`). Pas de simple sac de donnees |

### 2.3 Ubiquitous Language

| # | Item | Poids | Statut | Citation |
|---|------|-------|--------|----------|
| 2.3.1 | Vocabulaire coherent domain ↔ services ↔ API ↔ frontend | 2 | OK | Push : `ChunkPush` (`models.py:284`) → `services/chunk_service.py:686` `"pushId": push.id` → `api/schemas.py:438` `push_id: str` → `frontend/src/features/chunks/api.ts:55` `pushId: string` → `frontend/src/features/chunks/store.ts:195` `return res.pushId` → `frontend/src/features/chunks/ui/ChunksEditor.vue:211-215` `pushId`. `grep -rn "pushedJob"` ZERO match. Les references restantes `jobId`/`job_id` portent toutes sur `AnalysisJob` (vocabulaire metier legitime) ou sur la forme wire externe `SidecarEnvelope.job_id` (`frontend/src/features/reasoning/types.ts:38`, anti-corruption boundary R&D) |
| 2.3.2 | Noms refletent le domaine, pas le generique | 1 | OK | `grep -rn "Manager\|Handler\|Processor" document-parser/domain/ document-parser/services/` ZERO match. Services nommes `AnalysisService`, `ChunkService`, `DocumentService`, `GraphService`, `IngestionService`, `StoreService`, `VersionService` — tous noms domaine |
| 2.3.3 | Statuts metier explicites (StrEnum) | 1 | OK | `AnalysisStatus(StrEnum)` (`models.py:22-26`), `DocumentLifecycleState(StrEnum)` (`value_objects.py:18-40`), `StoreKind(StrEnum)` (`value_objects.py:43-49`), `DocumentStoreLinkState(StrEnum)` (`value_objects.py:51-62`), `ChunkEditAction(StrEnum)` (`value_objects.py:65-76`), `DocumentVersionKind(StrEnum)` (`models.py:300-308`), `LLMProviderType(StrEnum)` (`value_objects.py:167-177`) |

### 2.4 Agregats et invariants

| # | Item | Poids | Statut | Citation |
|---|------|-------|--------|----------|
| 2.4.1 | Chaque agregat a une racine claire | 2 | OK | Document est la racine de son agregat (lifecycle + page_count), `AnalysisJob` racine de son cycle status/progress/results, `Store` racine de l'agregat ingestion (DocumentStoreLink + connection credentials), `ChunkEdit` audit append-only, `ChunkPush` snapshot append-only, `DocumentVersion` snapshot pair (analysis + chunks). Repositories en correspondance 1:1 (`ports.py:90-209`) |
| 2.4.2 | Invariants metier proteges dans le domaine | 3 | OK (avec MIN sur l'enforcement type-system) | Transitions lifecycle validees par `domain/lifecycle.py:1-83` `assert_transition` + `Document.transition_to` (`models.py:65-75`). `AnalysisJob.mark_running/completed/failed` levent `ValueError` sur transition invalide (`models.py:100, 114, 133`). `ChunkEdit` frozen → append-only naturel. Les entites mutables (`AnalysisJob`, `Chunk`, `Document`, `Store`, `DocumentStoreLink`, `DocumentVersion`) restent modifiables par champ une fois retournees du service — invariant protege par convention/method, pas par le type — degradation MIN, voir Ecart [MIN] ci-dessous |
| 2.4.3 | Modifications passent par la racine | 2 | OK | Pas de manipulation directe `chunk._private` dans `services/`. Chunk editing transactionnel via `domain/chunk_editing.py:1-216` (pure) puis ecriture atomique chunk + audit trail dans `services/chunk_service.py`. `DocumentStoreLink` modifie par `mark_*` (`models.py:201-223`), jamais par mutation directe dans les services |

### 2.5 Repositories et anti-corruption

| # | Item | Poids | Statut | Citation |
|---|------|-------|--------|----------|
| 2.5.1 | Repositories manipulent des entites du domaine | 2 | OK | `document-parser/domain/ports.py:90-209` : signatures typees `Document`, `AnalysisJob`, `Store`, `DocumentStoreLink`, `Chunk`, `ChunkEdit`, `ChunkPush`. Aucun `dict` ou `Row` en retour. Implementations dans `document-parser/persistence/*_repo.py` |
| 2.5.2 | Anti-corruption HTTP via Pydantic | 2 | OK | `document-parser/api/schemas.py` : DTOs `_CamelModel` traduisent camelCase HTTP en snake_case domaine. `PushChunksResponse.push_id` (schemas.py:438) recoit `pushId` du wire et le mappe au champ snake_case |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OK | `grep -rn "from docling\|^import docling" document-parser/services/ --include="*.py"` → ZERO match. `grep -rn "from docling\|^import docling" document-parser/domain/ --include="*.py"` → ZERO match. Renforce par commit `3936166` (#254 carry `self_ref`) : `infra/serve_converter.py` continue de retourner uniquement des `PageElement` du domaine, jamais des objets Docling brut |

---

## Ecarts constates

### [MIN] AnalysisJob, Chunk, Document, Store, DocumentStoreLink, DocumentVersion restent mutables hors du service (carry-over 0.5.0 / 0.6.1 / 0.6.1-reaudit)

- **Localisation** :
  - `document-parser/domain/models.py:37` — `@dataclass class Document` (non-frozen)
  - `document-parser/domain/models.py:78` — `@dataclass class AnalysisJob` (non-frozen)
  - `document-parser/domain/models.py:142` — `@dataclass class Store` (non-frozen)
  - `document-parser/domain/models.py:182` — `@dataclass class DocumentStoreLink` (non-frozen)
  - `document-parser/domain/models.py:226` — `@dataclass class Chunk` (non-frozen)
  - `document-parser/domain/models.py:311` — `@dataclass class DocumentVersion` (non-frozen)
- **Constat** : Identique au rapport 0.6.1-reaudit, aucun changement sur ces fichiers entre `f9e5619` et `051ac4a`. Les methodes `transition_to`, `mark_running`, `mark_completed`, `mark_failed`, `update_progress`, `mark_ingested`, `mark_stale` verifient les transitions, mais le systeme de types ne les rend pas obligatoires : une fois une entite retournee hors du service, un appelant externe peut toujours faire `job.status = AnalysisStatus.COMPLETED` directement. L'invariant "transitions ordonnees" est applique par la logique metier, pas par le type. `ChunkEdit` (`models.py:256`) et `ChunkPush` (`models.py:284`) sont deja frozen — bon precedent.
- **Regle violee** : 2.4.2 (item poids 3) — l'invariant *est* protege par les methodes de transition, donc l'item reste conforme. La capacite a contourner les transitions par mutation directe constitue une violation de surface, classee MIN (degradation poids 1).
- **Remediation** : Pour 0.7.x, considerer `@dataclass(frozen=True)` sur les entites et passer par des methodes qui retournent une nouvelle instance, ou explorer un pattern equivalent (ex. private fields + accessors). Acceptable en l'etat — le service controle les mutations et les seuls appelants des entites sont les services et les repositories.

---

## Points positifs

- **Aucune regression DDD en 0.6.2** : la branche n'a pas touche `domain/`, `services/`, `api/`, `persistence/`, `frontend/src/`. Le poste DDD est strictement identique a 0.6.1-reaudit, hors un commit `3936166` (#254 carry de `self_ref` dans `infra/serve_converter.py`) qui **renforce** la conformite a 2.5.3 (les value objects domaine restent la frontiere de sortie de `ServeConverter`).
- **Migration uv (#254) sans dette DDD** : la migration `pip → uv` (pyproject.toml + lockfile) reste sur le perimetre build/packaging. Aucun changement de couplage ou de vocabulaire metier introduit.
- **Bounded contexts toujours nets** (2.1.1 ✓) : six contextes alignes backend ↔ frontend (`document`, `analysis`, `chunks`, `stores`, `versions`, `ingestion`).
- **Ports & adapters renforces** (2.1.3 ✓) : `domain/ports.py` continue de definir 12+ protocols runtime-checkable, y compris `DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector` (introduits en 0.6.1 par #audit-01). Aucun import infra dans `domain/` ni dans `services/`.
- **Anti-corruption layer efficace** (2.5.2, 2.5.3 ✓) : zero import Docling dans `services/` ni `domain/`. La traduction Docling → domain reste exclusivement dans `infra/` (`local_converter.py`, `serve_converter.py`, `docling_tree.py`, `docling_graph.py`).
- **Vocabulaire `push` aligne** (2.3.1 ✓) : remediation du MAJ 0.6.1 conservee (push_id / pushId de bout en bout). Aucun retour de `jobId` pour designer un `ChunkPush`.
- **State machine domaine explicite** (2.4.2 ✓ partiel) : `domain/lifecycle.py` + `Document.transition_to` + `DocumentLifecycleChanged` event. Aggregation lifecycle multi-stores via `domain/lifecycle_aggregation.py` (fonction pure).
- **Audit log immuable** (2.4.2 ✓) : `ChunkEdit` (`models.py:256`) frozen ; `SqliteChunkEditRepository` append-only (pas d'`update`/`delete`).
- **Statuts metier explicites avec enums type-safe** (2.3.3 ✓) : sept `StrEnum` couvrant tous les statuts metier.
- **Pas de termes generiques** (2.3.2 ✓) : `Manager`/`Handler`/`Processor` absents de `domain/` et `services/`.
- **Frontend respecte les bounded contexts** (2.1.4 ✓) : `frontend/src/features/` mirroite exactement le backend.

---

## Verdict partiel : GO

**Justification** :

- Score 97/100 (>= 80) ✓ — identique a 0.6.1-reaudit.
- 0 ecart CRITICAL ✓
- 0 ecart MAJOR ✓
- 1 ecart MINOR carry-over (immutabilite type-system des entites) — meme observation depuis 0.5.0, recommande pour 0.7.x.

**Delta vs 0.6.1-reaudit** : **+0 (97 → 97)**.

La branche `release/0.6.2` n'a pas touche le perimetre DDD audite. Le seul changement avec impact indirect sur la couche infra (`infra/serve_converter.py` carry `self_ref`) **renforce** la conformite a 2.5.3 plutot que de la degrader. Le MIN immutabilite reste sans evolution.

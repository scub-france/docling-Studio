# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 17 / 17 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 3 |

Score = (36 / 36) * 100 = **100**. Tous les items de la checklist sont
conformes ; les trois observations ci-dessous sont des notes de purete DDD
sans risque de release (aucun item marque non conforme).

---

## Ecarts constates

### [INFO] `GraphPayload` est le seul value object non-immutable du module

- **Localisation** : `document-parser/domain/value_objects.py:284`
- **Constat** : tous les value objects du module sont declares
  `@dataclass(frozen=True)` (13 occurrences : `PageElement`, `PageDetail`,
  `ConversionOptions`, `ConversionResult`, `ChunkingOptions`, `ChunkBbox`,
  `ChunkDocItem`, `ChunkResult`, `ReasoningIteration`, `ReasoningResult`,
  `ReasoningStepPayload`, `ReasoningStep`, `ReasoningTrace`). Seul
  `GraphPayload` (l.284) est un `@dataclass` mutable. C'est un read-model /
  projection cytoscape produit par `Neo4jGraphReader`, pas un VO porteur
  d'invariants, mais il rompt la convention `frozen=True` du module.
- **Regle violee** : 2.2.2 (value objects immutables) — les VO nommes par la
  checklist (`ConversionResult`, `ChunkingOptions`, `ChunkBbox`) et tous les VO
  reasoning sont bien geles ; l'item reste conforme, cette rupture de
  convention est une observation.
- **Remediation** : ajouter `frozen=True` a `GraphPayload` (les champs `nodes`
  / `edges` sont deja des listes construites une fois), ou documenter
  explicitement dans la docstring qu'il s'agit d'un DTO de lecture volontairement
  mutable.

### [INFO] Dualite "AnalysisJob"/`job` vs le terme ubiquitaire "analysis"

- **Localisation** : `document-parser/domain/models.py:79` (`class AnalysisJob`) ;
  `document-parser/api/analyses.py:23` et `document-parser/services/analysis_service.py:139`
  (variables `job`)
- **Constat** : le langage ubiquitaire public est coherent — feature frontend
  `analysis`, route `/api/.../analyses`, `AnalysisService`, `AnalysisResponse`,
  `AnalysisRepository`, `AnalysisStatus`. Le domaine conserve toutefois le
  suffixe "Job" sur l'entite (`AnalysisJob`) et la variable locale `job` est
  employee de facon quasi systematique en API et services. La checklist met
  precisement en garde contre un vocabulaire "job d'un cote et analysis de
  l'autre" (2.3.1). La dualite est ici contenue et documentee (un `AnalysisJob`
  = une tentative de conversion), le terme "Analysis" reste present dans le nom,
  donc l'item demeure conforme.
- **Regle violee** : 2.3.1 (vocabulaire coherent domain/services/API/frontend) —
  observation, non un ecart bloquant.
- **Remediation** : envisager de renommer l'entite `AnalysisJob` -> `AnalysisRun`
  (ou `Analysis`) et les variables `job` -> `analysis` / `run` pour effacer le
  dernier vestige de la dualite, dans un cycle de refactor dedie.

### [INFO] `models.py` regroupe les entites de cinq bounded contexts dans un seul module

- **Localisation** : `document-parser/domain/models.py:37-332` ;
  entite jointe denormalisee `document_filename` a `models.py:96`
- **Constat** : `models.py` (331 lignes) heberge les entites de plusieurs
  contextes — document (`Document`), analysis (`AnalysisJob`), store
  (`Store`, `DocumentStoreLink`), chunk (`Chunk`, `ChunkEdit`, `ChunkPush`) et
  versioning (`DocumentVersion`). Ce ne sont pas des god objects (chaque contexte
  a bien sa propre dataclass distincte, item 2.1.2 conforme), mais le decoupage
  physique par fichier ne suit pas les frontieres de contextes. Par ailleurs
  `AnalysisJob` porte un champ de presentation joint (`document_filename`,
  "Joined from document — not persisted separately") et plusieurs blobs
  serialises (`*_json`, dont `chunks_json` legacy remplace par l'entite `Chunk`),
  ce qui rend l'entite plutot faconnee pour la persistence/transport.
- **Regle violee** : 2.1.2 (chaque contexte a ses propres modeles) — observation
  d'organisation, l'item reste conforme car aucun modele omniscient partage
  n'existe.
- **Remediation** : si `models.py` grossit, envisager un decoupage par contexte
  (`domain/models/document.py`, `.../chunk.py`, ...). Isoler `document_filename`
  dans un DTO de lecture plutot que sur l'entite.

---

## Points positifs

- **Bounded contexts nets, front et back alignes** (2.1.1, 2.1.4) : les
  contextes parse / analysis / chunk / reasoning / store / config sont
  identifiables cote back (`services/*`, `domain/*`) et refletes 1:1 cote front
  (`frontend/src/features/` : `analysis`, `chunking`, `chunks`, `document`,
  `ingestion`, `reasoning`, `search`, `store`, `history`, `admin-config`).
- **Domaine strictement pur** (2.2.3) : `grep` confirme zero import de framework
  ou d'infra dans `document-parser/domain/` (ni pydantic, fastapi, aiosqlite,
  docling, neo4j, opensearch, httpx, mellea). La seule occurrence "Docling" est
  un commentaire dans `services.py:9`.
- **Aucune logique de persistence sur les entites/VO** (2.2.3) : les methodes
  `insert`/`update`/`delete` n'existent que sur les **ports** repository
  (`domain/ports.py`) ; les fonctions `insert`/`update`/`delete` de
  `chunk_editing.py` sont des fonctions pures qui retournent un nouveau chunkset,
  sans I/O.
- **Invariants metier proteges dans le domaine** (2.4.2) : machine a etats du
  cycle de vie du `Document` via `lifecycle._TRANSITIONS` + `assert_transition`
  (`Document.transition_to`, `models.py:49`) ; garde-fous de statut
  `AnalysisJob.mark_running/mark_completed/mark_failed` ; validation d'entree
  dans `chunk_editing` (offsets, merge cross-document, chunk supprime) et dans
  `app_config.validate_reasoning_config`.
- **Value objects reasoning bien modelises** (2.2.2) : `ReasoningIteration`,
  `ReasoningResult`, `ReasoningStep`, `ReasoningStepPayload`, `ReasoningTrace`
  sont des `frozen` VO purs ; `ReasoningStepKind` (StrEnum) est un miroir 1:1 du
  type TS `frontend/src/features/reasoning/types.ts` (coherence de langage
  ubiquitaire, 2.3.1).
- **Projection reasoning pure et bien placee** (2.5.3) : `domain/trace_builder.py`
  est une fonction pure sur des VO du domaine (aucun HTTP/DB/docling-agent) ;
  elle est deliberement dans `domain/` et documentee comme telle.
- **Couche anti-corruption solide** (2.5.2) : les DTOs Pydantic exposent des
  constructeurs `from_trace` / `from_step` / `from_payload` / `from_view` /
  `from_result` (`api/schemas.py`) qui projettent les objets du domaine vers le
  fil camelCase ; le routeur `api/reasoning.py` ne fait que mapper des DTOs et
  traduire les erreurs typees en codes HTTP.
- **Adaptateurs infra sans fuite de types** (2.5.3) : `grep` confirme zero import
  docling dans `services/` ; `infra/docling_agent_reasoning.py` traduit
  `RAGResult`/`RAGIteration` (via `model_dump()`) en `ReasoningResult`/
  `ReasoningIteration` du domaine, et convertit l'`IndexError` upstream en
  `ReasoningParseError` (port-level).
- **Repositories manipulent des entites** (2.5.1) : `persistence/analysis_repo.py`
  mappe chaque `Row` en `AnalysisJob` via `_row_to_job` (l.18) ; tous les finders
  retournent des entites du domaine, jamais des dicts/Row bruts.
- **Statuts metier explicites** (2.3.3) : `AnalysisStatus = PENDING/RUNNING/
  COMPLETED/FAILED` ; `DocumentLifecycleState`, `DocumentStoreLinkState`,
  `ChunkEditAction` sont des StrEnum au vocabulaire metier clair. Aucun nom de
  classe generique (`Manager`/`Handler`/`Processor`) dans `domain/` ou
  `services/` (2.3.2).
- **Erreurs de service reasoning typees avec hint HTTP** (2.5.2/2.1.3) :
  `ReasoningUnavailableError` (503), `ReasoningEmptyQueryError` (400),
  `ReasoningNoAnalysisError` (404) — le contrat 400 pour la requete vide est
  garde cote service et non delegue a un `min_length` Pydantic (qui renverrait
  422), decision documentee.

---

## Verdict partiel : GO

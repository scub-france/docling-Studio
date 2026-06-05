# Rapport d'audit : SOLID

**Release** : 0.6.2
**Date** : 2026-06-05
**Auditeur** : claude-code
**Commit HEAD** : `051ac4a`
**Baseline** : `docs/audit/reports/release-0.6.1-reaudit/06-solid.md` (100/100, 0/0/0/1, GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 ponderes) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

**Delta vs 0.6.1 (re-audit)** : 0 points (100 → 100). 1 INFO maintenu.

---

## Contexte

Le diff `fix/0.6.1-audit-blockers..release/0.6.2` sur `document-parser/services/`,
`document-parser/domain/ports.py` et `document-parser/infra/` est **vide** :
aucune ligne touchee sur la surface SOLID entre la baseline 100/100 et 0.6.2. Les seuls
deltas backend de 0.6.2 portent sur `pyproject.toml` + `uv.lock` (migration uv),
`Dockerfile` + `.dockerignore` (slim image), et `tests/test_architecture.py`
(exclusion des fichiers generes). La conformite SOLID est donc transposable.

L'audit re-verifie quand meme les 5 principes sur le working tree HEAD pour
confirmer qu'aucune regression silencieuse ne s'est glissee par un autre chemin.

---

## Verification des principes

### SRP (6.1)

- **6.1.1 & 6.1.4 conforme** : 8 services bien delimites, aucun god service.

  | Service | LOC | Responsabilite unique |
  |---------|-----|-----------------------|
  | `AnalysisService` | 553 | Pipeline d'analyse Docling |
  | `ChunkService` | 1014 | CRUD chunks first-class + audit trail |
  | `DocumentService` | 178 | CRUD documents |
  | `GraphService` | 132 | Orchestre `/graph` + `/reasoning-graph` |
  | `IngestionService` | 297 | Embed + push vector + graph |
  | `StoreBackendResolver` | 152 | `Store` -> `IngestionTargets` |
  | `StoreService` | 391 | CRUD stores + test_connection |
  | `VersionService` | 227 | Snapshots paires (analyse, chunks) |

- **6.1.2 conforme** : 10 stores Pinia (`frontend/src/features/*/store.ts`),
  31-234 LOC chacun, un feature = un store.
- **6.1.3 conforme** : 8 routers REST groupes par ressource
  (`analyses.py`, `document_chunks.py`, `document_versions.py`, `documents.py`,
  `graph.py`, `ingestion.py`, `reasoning.py`, `stores.py`).

### OCP (6.2)

- **6.2.1 conforme** : `document-parser/domain/ports.py` declare 17 Protocols
  (`DocumentConverter`, `DocumentChunker`, `DocumentRepository`, `StoreRepository`,
  `DocumentStoreLinkRepository`, `ChunkRepository`, `ChunkEditRepository`,
  `ChunkPushRepository`, `AnalysisRepository`, `EmbeddingService`, `VectorStore`,
  `LLMProvider`, `DocumentTreeReader`, `GraphReader`, `GraphWriter`,
  `DocumentGraphProjector`, `ReasoningRunner`). Ajouter un `PostgresVectorStore`
  ou un `JanusGraphWriter` n'implique aucune modification dans `services/`.
- **6.2.2 conforme** : `main.py:49-64` `_build_converter()` choisit
  `LocalConverter` ou `ServeConverter` via `settings.conversion_engine` sans
  toucher un service. Le `StoreBackendResolver` etend ce pattern aux stores
  per-instance (`store_backend_resolver.py:75-152`).
- **6.2.3 conforme** : Les endpoints serializent un `ConversionResult`
  domain — l'ajout d'un format passe par `domain/value_objects.py` puis
  les adaptateurs, sans toucher `api/`.

### LSP (6.3)

- **6.3.1 conforme** : `LocalConverter` (`infra/local_converter.py`) et
  `ServeConverter` (`infra/serve_converter.py`) implementent `DocumentConverter`
  (`domain/ports.py:52-74`) et renvoient un `ConversionResult` identique.
  Le commit `3936166` corrige la divergence de 0.6.0 sur le champ `self_ref` :
  `serve_converter.py:250,270` le carry maintenant comme `local_converter.py:202`
  le fait deja — meme contrat de retour confirme cote `PageElement`
  (`domain/value_objects.py:150`).
- **6.3.2 conforme** : Les ports declarent leurs exceptions typees au domaine :
  `ReasoningParseError` (`ports.py:37-49`), `GraphServiceError` et sa hierarchie
  (`graph_service.py:33-65`), `StoreBackendNotConfiguredError`
  (`store_backend_resolver.py:65-72`). `Neo4jGraphWriter.ping()`
  (`infra/neo4j/graph_adapter.py:66-75`) swallow toute exception et retourne
  `False`, contrat aligne sur `VectorStore.ping()` (`ports.py:273-276`).
- **6.3.3 conforme** : `grep -rn "isinstance\|type(" document-parser/services/`
  retourne 3 occurrences (`store_service.py:135,139` ; `chunk_service.py:218`),
  toutes sur des types primitifs (`str`, `list`). Zero discrimination
  d'adaptateur.

### ISP (6.4)

- **6.4.1 conforme** : `DocumentConverter` et `DocumentChunker` sont des
  Protocols separes (`ports.py:52-87`), declares avec une methode chacun
  (plus une `@property` pour le converter). Aucune god interface.
- **6.4.2 conforme** : Sur les 17 ports, 63 methodes declarees au total
  (~3.7 methodes/port en moyenne). Les ports les plus gros restent
  `VectorStore` (6 methodes : `embed`/`ensure_index`/`index_chunks`/
  `search_similar`/`get_chunks`/`delete_document`/`ping`) et `ChunkRepository`
  (7 methodes), toutes consommees par les services. `GraphWriter`
  (`ports.py:356-390`) documente explicitement la regle anti-no-op :
  "Adapters that don't support both paths still must implement them
  (raise NotImplementedError rather than silently no-op)" — ISP preserve
  par contrat ecrit.

### DIP (6.5)

- **6.5.1 conforme** : Verification commands :

  ```
  $ grep -rn "from infra\.\|import infra\." document-parser/services/ --include="*.py"
  document-parser/services/store_backend_resolver.py:40:    from infra.neo4j.driver_pool import Neo4jDriverPool
  document-parser/services/store_backend_resolver.py:41:    from infra.opensearch_pool import OpenSearchClientPool
  document-parser/services/store_backend_resolver.py:42:    from infra.opensearch_store import OpenSearchStore
  document-parser/services/chunk_service.py:170:        # `from infra.docling_tree import ...` smell hiding inside two
  ```

  Les 4 occurrences sont **non-runtime** :
  - `store_backend_resolver.py:40-42` sous `if TYPE_CHECKING:` (lignes 37-43)
    — pure annotation pour mypy.
  - `chunk_service.py:170` est un commentaire de docstring expliquant la
    remediation #audit-01.

  `$ grep -rn "^from infra\|^import infra" document-parser/services/`
  retourne **zero match** au top-level. DIP conserve.

- **6.5.2 conforme** : `document-parser/main.py:255-348` est l'unique composition
  root. Il instancie tous les adaptateurs concrets et injecte les ports :
  `LocalConverter`/`ServeConverter` via `_build_converter()` (lignes 49-64),
  `LocalChunker` via `_build_chunker()` (74), `Neo4jGraphReader` +
  `Neo4jGraphWriter` (lignes 264-265), `DoclingTreeReader` (321),
  `DoclingGraphProjector` (346), `OpenSearchStore` via `OpenSearchClientPool`
  (resolver path), `FernetBox` via `get_fernet_box()` (persistence path).

- **6.5.3 conforme** : Verification :

  ```
  $ grep -rn "LocalConverter\|ServeConverter\|LocalChunker\|OpenSearchStore" \
      document-parser/services/ --include="*.py"
  document-parser/services/store_backend_resolver.py:11:  # docstring
  document-parser/services/store_backend_resolver.py:42: # TYPE_CHECKING import
  document-parser/services/store_backend_resolver.py:61: # type annotation only
  ```

  Aucune instanciation directe. Le `graph_writer_factory: Callable[[Any], GraphWriter]`
  injecte par `main.py:298` permet au resolver d'instancier un `Neo4jGraphWriter`
  par store sans connaitre la classe (`store_backend_resolver.py:84,150`).

---

## Verification specifique des nouveautes 0.6.2 mentionnees dans le brief

Le brief liste : `graph_service`, `fernet_box`, store credentials, `opensearch_pool`,
`neo4j_pool`. Ces 5 composants ont ete introduits **avant** le merge de
`fix/0.6.1-audit-blockers` (commits `1432ca4`, `1a0e162`, `841a294`, `b7dbbec`,
`d42885c`) — la baseline 100/100 les couvrait deja. Re-verification :

| Composant | Localisation | Conformite SOLID |
|-----------|--------------|------------------|
| `GraphService` | `services/graph_service.py:74-132` | SRP (132 LOC mono-responsabilite), DIP (consomme `GraphReader` + `DocumentGraphProjector` + `AnalysisRepository`, jamais d'infra), OCP (4 exceptions typees portant `http_status` — l'API mappe sans connaitre les causes). |
| `FernetBox` | `infra/secrets/fernet_box.py:57-105` | Confinement infra : seul `persistence/store_repo.py:25,76,202,213` l'importe (couche persistence — frontiere autorisee par la pile hexagonale). Zero import en `services/` ou `api/`. |
| Store credentials (sealing) | `persistence/store_repo.py:76,213` | Encapsulation totale : sealing/opening invisible au-dessus du repo. `StoreService` reste port-only. |
| `OpenSearchClientPool` | `infra/opensearch_pool.py:31-128` | Inject dans le resolver (`store_backend_resolver.py:83,92,129`) en `TYPE_CHECKING` ; `main.py:289,295` fournit l'instance concrete. OCP : ajouter un autre pool ne touche pas le service. |
| `Neo4jDriverPool` | `infra/neo4j/driver_pool.py:46-158` | Symetrique avec OpenSearch. Le resolver expose seulement un `IngestionTargets.graph_writer: GraphWriter` (port) — la chaine pool -> driver -> writer reste interne au boundary infra. |

Aucun de ces composants n'introduit de couplage descendant ou de violation
de substitution. Le pattern factory pour `graph_writer_factory` reste un
exemple-type de DIP propre.

---

## Ecarts constates

### [INFO] LSP — declaration `@property` vs attribut de classe pour `supports_page_batching`

- **Localisation** :
  - `document-parser/domain/ports.py:67-74` — declare `@property def supports_page_batching(self) -> bool`
  - `document-parser/infra/local_converter.py:286` — `supports_page_batching: bool = True` (attribut de classe)
  - `document-parser/infra/serve_converter.py:64` — `supports_page_batching: bool = False` (attribut de classe)
- **Constat** : Inchange depuis la baseline 0.6.1 reaudit. Le `Protocol` declare
  un `@property`, les deux adaptateurs declarent un attribut simple. Le contrat
  fonctionne au runtime (acces `converter.supports_page_batching` retourne un
  `bool` dans les deux cas) et `analysis_service.py:415` consomme proprement
  la valeur. La forme diverge — `mypy --strict` pourrait raler.
- **Regle violee** : Aucune (forme stricte de 6.3.1 — meme contrat de retour respecte).
- **Remediation** : Harmoniser sur l'attribut simple (supprimer `@property` dans
  le port) OU rendre les deux adaptateurs `@property`. Un test de typage en CI
  eviterait la regression. **Non-bloquant** pour le release 0.6.2.

---

## Points positifs

1. **Surface SOLID byte-identique a la baseline 0.6.1 reaudit** : `git diff
   fix/0.6.1-audit-blockers..release/0.6.2 -- document-parser/services/
   document-parser/domain/ports.py document-parser/infra/` retourne zero ligne.
   La conformite 100/100 est preservee sans intervention supplementaire.
2. **DIP totale — services purement ports** : Aucun `from infra.*` runtime
   dans `document-parser/services/`. La couche service ne connait que des
   ports (`domain/ports.py`).
3. **SRP — `GraphService` extrait proprement** : `services/graph_service.py`
   (132 LOC) orchestre les deux endpoints `/graph` et `/reasoning-graph`.
   4 exceptions typees (`GraphStoreNotConfiguredError`, `GraphNotFoundError`,
   `GraphTooLargeError`, `GraphServiceError`) avec `http_status` integre —
   l'API se contente de mapper.
4. **OCP — Composition root scellee** : `main.py` instancie les 8 adaptateurs
   concrets (`LocalConverter:64`, `ServeConverter:55`, `LocalChunker:76`,
   `OpenSearchStore` via pool, `Neo4jGraphReader:265`, `Neo4jGraphWriter:264`,
   `DoclingTreeReader:321`, `DoclingGraphProjector:346`) et injecte les
   ports. Ajouter un `PostgresVectorStore` ou un `JanusGraphWriter` ne touche
   aucun service.
5. **DIP — Factory pattern pour adaptateurs runtime-dependants** :
   `StoreBackendResolver` recoit un `graph_writer_factory: Callable[[Any],
   GraphWriter]` (ligne 84) injecte avec `Neo4jGraphWriter` (`main.py:298`).
   Le resolver instancie l'adaptateur a la volee (`store_backend_resolver.py:152`)
   sans connaitre la classe concrete.
6. **LSP — Substitution transparente confirmee** : `LocalConverter` et
   `ServeConverter` interchangeables, avec parite renforcee sur `self_ref`
   par #3936166 (`serve_converter.py:250,270` aligne sur `local_converter.py:202`).
   `Neo4jGraphWriter.ping()` (`infra/neo4j/graph_adapter.py:66-75`) swallows
   les exceptions et retourne `False` — meme contrat que `VectorStore.ping()`
   declare dans `domain/ports.py:273-276`.
7. **LSP — Adaptateurs port-only sans logique** : `DoclingTreeReader`,
   `DoclingGraphProjector`, `Neo4jGraphReader`, `Neo4jGraphWriter` sont
   tous des shims stateless de 15-40 LOC qui deleguent aux fonctions libres
   existantes. Aucun risque de divergence comportementale.
8. **ISP — Ports finement segreges** : 17 ports, ~3.7 methodes/port. `GraphReader`
   ne porte que `fetch()`, `GraphWriter` porte `write_document_tree` +
   `write_chunks` + `ping()` (3 methodes, toutes utilisees). Documentation
   anti-no-op explicite dans le docstring du port.
9. **DIP — Aucune fuite infra dans `api/`** : `grep -rn "from infra"
   document-parser/api/` retourne **0 match**. L'API depend exclusivement de
   services et schemas.
10. **DIP — Encapsulation infra des secrets** : `FernetBox` (`infra/secrets/`)
    n'est importe que par `persistence/store_repo.py`. Le sealing reste
    invisible au-dessus de la couche persistence. Les services et l'API
    voient des plaintext ou des handles opaques.
11. **DIP — Pools infra confines** : `Neo4jDriverPool` et `OpenSearchClientPool`
    ne sont importes en TYPE_CHECKING que dans `StoreBackendResolver`. Aucune
    fuite runtime ; les pools sont injectes par `main.py`.
12. **Validation automatisee** : `tests/test_architecture.py:7-13` declare les
    regles de couches (`services -> no import from api, infra, persistence`).
    Toute regression DIP serait detectee au prochain pytest.
13. **S — Routes API et stores Pinia** : 8 routers REST et 10 stores Pinia, un
    router = une ressource DDD, un store = une feature.

---

## Verdict partiel : GO

**Score** : 100 / 100 (delta 0 vs 0.6.1 reaudit).
**Ecarts CRITICAL** : 0 — release autorisee.
**Ecarts MAJOR** : 0.
**Ecarts MINOR** : 0.
**Ecarts INFO** : 1 (LSP `@property` vs attribut — reporte au prochain cycle, non-bloquant).

Le SOLID reste exemplaire sur le perimetre `services/` / `domain/` / `infra/`.
Aucune regression depuis la baseline 0.6.1 reaudit : la surface SOLID est
byte-identique, et les nouveautes 0.6.2 (uv, Dockerfile slim, exclusions de
tests) sont structurellement neutres. Le seul ecart restant est cosmetique
(typage Protocol vs attribut de classe pour `supports_page_batching`) et
n'impacte ni le contrat fonctionnel ni les tests.

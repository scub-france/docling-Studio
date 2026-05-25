# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 75 / 100 |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 2 |
| Écarts MINOR | 1 |
| Écarts INFO | 0 |

Détail du calcul (somme des poids) :

- Total poids = 32
- Poids conformes = 24 (1.1.1=3, 1.1.2=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.2.3=2, 1.3.1=3, 1.4.1=3, 1.4.2=2)
- Poids non conformes = 8 (1.1.3=3, 1.2.4=2, 1.3.3=2, 1.3.2=1)
- Score = 24 / 32 × 100 = **75 / 100**

---

## Écarts constatés

### [CRIT] Les services et la couche API contournent `domain/ports.py` en important directement des modules `infra/`

- **Localisation** :
  - `document-parser/services/chunk_service.py:891` — `from infra.docling_tree import build_collapse_index, iter_items`
  - `document-parser/services/chunk_service.py:974` — `from infra.docling_tree import is_inline_group`
  - `document-parser/services/analysis_service.py:505` — `from infra.neo4j import write_document`
  - `document-parser/services/ingestion_service.py:221` — `from infra.neo4j import write_chunks`
  - `document-parser/api/graph.py:18` — `from infra.docling_graph import build_graph_payload`
  - `document-parser/api/graph.py:19` — `from infra.neo4j import fetch_graph`
- **Constat** : Quatre dépendances infra concrètes (`infra.docling_tree`, `infra.neo4j.write_document`, `infra.neo4j.write_chunks`, `infra.neo4j.fetch_graph`, `infra.docling_graph.build_graph_payload`) sont appelées depuis `services/` et `api/` sans passer par un protocole défini dans `domain/ports.py`. `domain/ports.py` n'expose ni `TreeWriter`, ni `ChunkWriter`, ni `GraphReader`, ni `DocumentTreeWalker`. Les imports lazy à l'intérieur des méthodes ne suppriment pas le couplage : le service reste lié à l'implémentation Neo4j / Docling-tree à la compilation logique. Cette violation s'étend depuis la 0.5.0 (où aucune de ces fonctions n'existait encore) ; elle est née avec l'arrivée de Neo4j et du graph rendering en 0.6.x.
- **Règle violée** : 1.1.3 — *Toute interaction avec l'exterieur passe par un protocole dans `domain/ports.py`* (poids 3).
- **Remédiation** :
  1. Introduire dans `domain/ports.py` les ports manquants : `DocumentTreeWriter` (`write_document`), `ChunkGraphWriter` (`write_chunks`), `DocumentGraphReader` (`fetch_graph`) et `DocumentTreeProjector` (les helpers `build_collapse_index` / `iter_items` / `is_inline_group` / `build_graph_payload`).
  2. Injecter ces ports via le constructeur des services concernés (`AnalysisService`, `IngestionService`, `ChunkService`) à la place des imports `from infra.neo4j ...` enfouis dans les méthodes.
  3. Dans `api/graph.py`, déléguer à un nouveau `GraphService` (résolu depuis `request.app.state`) au lieu d'appeler `infra.neo4j.fetch_graph` directement.

### [MAJ] Services injectés mais aussi importateurs directs de concretions infra

- **Localisation** :
  - `document-parser/services/analysis_service.py:505`
  - `document-parser/services/ingestion_service.py:221`
  - `document-parser/services/chunk_service.py:891,974`
- **Constat** : Les services concernés reçoivent bien leurs ports principaux (`DocumentConverter`, `VectorStore`, `EmbeddingService`, repos) via constructeur — c'est conforme pour les chemins critiques. Mais ils résolvent eux-mêmes le writer Neo4j et les helpers de l'arbre Docling par un `import` interne à la fonction, plutôt que via un port injecté. Cela rend le service non-testable sans monkey-patch et empêche le swap d'implémentation (impossible de passer un fake `TreeWriter` au constructeur).
- **Règle violée** : 1.2.4 — *Les services reçoivent leurs dépendances par injection, pas par import direct de concretions* (poids 2).
- **Remédiation** : Une fois les ports ajoutés (cf. CRIT 1.1.3), supprimer ces imports lazy et passer les writers/walkers au constructeur (`AnalysisService(..., tree_writer=...)`, `IngestionService(..., chunk_graph_writer=...)`, `ChunkService(..., tree_projector=...)`). Le câblage se fait dans `main.py` à côté de `_build_converter()`.

### [MAJ] `api/graph.py` n'a pas de service : les endpoints orchestrent la logique métier eux-mêmes

- **Localisation** : `document-parser/api/graph.py:53-123`
- **Constat** : Les deux routes (`/api/documents/{doc_id}/graph` et `/api/documents/{doc_id}/reasoning-graph`) appellent directement `infra.neo4j.fetch_graph` et `infra.docling_graph.build_graph_payload`, gèrent la traduction des `None` / `truncated` en `HTTPException`, et lisent `request.app.state.analysis_repo` à la main pour aller chercher le `document_json`. Il n'existe pas de `GraphService` dans `services/`. À comparer avec `api/documents.py` (`DocumentService`), `api/analyses.py` (`AnalysisService`), `api/stores.py` (`StoreService`), etc. qui suivent tous le pattern « endpoint → service ». Module orphelin de l'architecture.
- **Règle violée** : 1.3.3 — *Les endpoints délèguent toute la logique aux services* (poids 2).
- **Remédiation** : Créer `services/graph_service.py` qui prend en constructeur un `DocumentGraphReader` (port pour Neo4j fetch), un `DocumentTreeProjector` (port pour `build_graph_payload`) et l'`AnalysisRepository`. Déplacer la logique de récupération + projection + cap `MAX_PAGES` dans le service. Réduire `api/graph.py` à un simple appel délégué + mapping `Pydantic`.

### [MIN] Transformations camelCase contournées dans les schemas inline de `api/graph.py` et `api/reasoning.py`

- **Localisation** :
  - `document-parser/api/graph.py:27-50` — `GraphNode`, `GraphEdge`, `GraphResponse`
  - `document-parser/api/reasoning.py:30-48` — `ReasoningRunRequest`, `ReasoningIterationResponse`, `ReasoningResultResponse`
- **Constat** : `api/schemas.py:19-30` définit le helper `_to_camel` + `alias_generator=_to_camel` que toutes les classes héritant de `CamelModel` partagent. Les schemas Pydantic locaux des routes graph et reasoning ne réutilisent pas ce générateur : `model_id`, `section_ref`, `section_text_length`, `can_answer`, `doc_id`, `node_count`, `edge_count`, `page_count` sont sérialisés en snake_case, alors que le reste du contrat API est en camelCase (cf. règle « contrat API en camelCase » documentée dans `document-parser/CLAUDE.md`). Le frontend doit donc connaître deux conventions pour les mêmes types de payload.
- **Règle violée** : 1.3.2 — *Les transformations camelCase/snake_case restent dans `api/schemas.py`* (poids 1).
- **Remédiation** : Déplacer ces six classes dans `api/schemas.py` en les faisant hériter de la base `CamelModel` (ou ajouter `model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, serialize_by_alias=True)` à chacune). Vérifier ensuite que le front consomme bien les nouveaux noms (changement de contrat — à coordonner avec les stores Pinia `features/graph` et `features/reasoning`).

---

## Points positifs

- **Domain purity préservée** : `grep` sur `document-parser/domain/` ne retourne aucun import de `fastapi`, `aiosqlite` ou `pydantic`. La couche utilise toujours des dataclasses (`domain/models.py`, `domain/value_objects.py`, `domain/lifecycle.py`).
- **Services sans FastAPI** : zéro import `fastapi` / `Request` / `Response` / `Depends` dans `document-parser/services/`. La frontière HTTP n'a pas fuité dans la logique métier.
- **API sans persistence directe** : aucune route n'importe `persistence/*` ; tout passe par les services (sauf `api/graph.py` qui lit `analysis_repo` depuis `request.app.state` pour le fallback reasoning-graph — voir MAJ 1.3.3).
- **Ports élargis** depuis la 0.5.0 : `StoreRepository`, `DocumentStoreLinkRepository`, `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `LLMProvider`, `ReasoningRunner` ont été ajoutés à `domain/ports.py:109-339` — bonne discipline pour les domaines nouveaux (#203, #205, reasoning).
- **Configuration toujours centralisée** : `infra/settings.py:130-193` reste le seul point d'entrée pour les variables d'environnement ; pas de regression depuis la 0.5.0 (les seules constantes ≥ 4 chiffres trouvées dans `infra/` hors `settings.py` sont des `default_limit: int = 1000` dans `opensearch_pool.py:50` et `opensearch_store.py:81` — ce sont des paramètres de méthode, pas des constantes de module).
- **Adapters bien identifiés** : `LocalConverter`, `ServeConverter`, `LocalChunker`, `EmbeddingClient`, `OpenSearchStore`, `OllamaProvider`, `DoclingAgentReasoningRunner`, `FernetBox`, plus les sept `Sqlite*Repository` ; chacun satisfait son protocole par duck-typing structurel (pattern Python Protocol).
- **`main.py` reste un composition root propre** : `_build_converter()`, `_build_chunker()`, `_build_repos()`, `_build_reasoning_runner()` construisent les adaptateurs concrets et les injectent dans les services. Aucun import infra n'est fait au top-level pour le wiring optionnel (Docling Serve, reasoning, Neo4j).
- **Pas de SQL direct dans `services/`** : les seules occurrences de `INSERT/UPDATE/DELETE` sont des valeurs d'enum `ChunkEditAction` (`chunk_service.py:230,268,300,503` ; `version_service.py:188`), pas du SQL exécuté.

---

## Delta vs 0.5.0

| Item | 0.5.0 | 0.6.1 | Cause |
|------|-------|-------|-------|
| 1.1.3 (Ports) | ✅ | ❌ | Nouveaux adaptateurs Neo4j et helpers `docling_tree` / `docling_graph` introduits sans port. |
| 1.2.4 (DI) | ✅ | ❌ | Imports `from infra.neo4j ...` à l'intérieur des services. |
| 1.3.2 (camelCase) | ✅ | ❌ | Schemas locaux dans `api/graph.py` et `api/reasoning.py` en snake_case. |
| 1.3.3 (Endpoints délèguent) | ✅ | ❌ | `api/graph.py` mélange Neo4j fetch + projection + HTTP mapping. |
| Score | 100 | 75 | -25 points. |
| CRIT / MAJ / MIN / INFO | 0 / 0 / 0 / 0 | 1 / 2 / 1 / 0 | Régression structurelle liée au scope Neo4j + reasoning de 0.6. |

---

## Verdict partiel : NO-GO

Le score 75/100 reste en zone « GO CONDITIONNEL » mais la règle absolue de `master.md §3` s'applique : **tout écart `[CRIT]` non résolu = NO-GO**. La régression 1.1.3 doit être corrigée (ajout des ports `DocumentTreeWriter`, `ChunkGraphWriter`, `DocumentGraphReader`, `DocumentTreeProjector` et bascule des imports lazy vers l'injection constructeur) avant que la release 0.6.1 puisse partir. Les écarts MAJ 1.2.4 et 1.3.3 disparaissent mécaniquement avec la même remédiation.

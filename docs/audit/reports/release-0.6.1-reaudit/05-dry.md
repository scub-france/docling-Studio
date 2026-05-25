# Rapport d'audit : DRY (Don't Repeat Yourself) — Re-audit

**Release** : 0.6.1 (re-audit)
**Branche** : `fix/0.6.1-audit-blockers` @ `f9e5619`
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 (poids 9 / 12) |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 3 |

---

## Suivi des ecarts du rapport 0.6.1

| Ecart 0.6.1 | Statut re-audit |
|-------------|-----------------|
| [MIN] Litteraux `table_mode` / `chunker_type` non centralises | **PERSISTE** — aucun `domain/constants.py`, les 6+ occurrences restent inchangees (`api/schemas.py:124,154,172,185`, `domain/value_objects.py:104,130`, `infra/settings.py:20,113,149`, `infra/local_converter.py:91`, `infra/local_chunker.py:88`, `services/analysis_service.py:74`). Le batch de remediation `#audit-*` n'a pas cible cet ecart. |
| [MIN] Logique de polling dupliquee dans 3 stores/pages | **PERSISTE** — toujours 3 occurrences (`features/analysis/store.ts:72`, `features/ingestion/store.ts:31`, `pages/ReasoningPage.vue:117`). Pas de `frontend/src/shared/composables/usePoller.ts`. |
| [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE` | **PERSISTE** — `api/documents.py:19` et `services/document_service.py:26`, memes valeurs `64 * 1024`. |
| [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue` | **PERSISTE** — `frontend/src/features/store/ui/StoreForm.vue:298` (`'bolt://localhost:7687'` / `'http://localhost:9200'`). |

Aucun ecart resorbe, mais aucun nouveau ecart MAJ/CRIT introduit par le batch de remediation.

---

## Verification du nouveau code introduit par `#audit-01`

L'audit ciblait specifiquement les nouveaux fichiers `services/graph_service.py`, `infra/neo4j/graph_adapter.py`, ainsi que le helper `_to_response` ajoute dans `api/graph.py`.

### `Neo4jGraphReader` / `Neo4jGraphWriter` vs free functions

- **Localisation** : `infra/neo4j/graph_adapter.py:27-75` (adapter), `infra/neo4j/queries.py:137` (`fetch_graph`), `infra/neo4j/tree_writer.py:69` (`write_document`), `infra/neo4j/chunk_writer.py:55` (`write_chunks`).
- **Constat** : Les classes adapter sont des shims de 1-2 lignes qui se contentent de lier la fonction libre a un driver et d'exposer la signature du port domaine. Aucune logique metier n'est dupliquee. Les fonctions libres restent l'unique source de verite ; elles ne sont plus appelees ni depuis `services/` ni depuis `api/` (verifie par grep), uniquement depuis l'adapter et l'`__init__.py` (re-export).
- **Verdict** : Conforme — pas de duplication introduite.

### Helper `_to_response` dans `api/graph.py`

- **Localisation** : `api/graph.py:64-73`.
- **Constat** : Le helper suit exactement la convention "1 mapper par routeur" deja en place : `api/documents.py:29` (`_to_response`), `api/document_versions.py:38`, `api/document_chunks.py:53`, `api/analyses.py:31`, `api/stores.py:46/64/78`. Cette convention avait deja ete saluee comme "Point positif" dans le rapport 0.6.1 — chaque routeur possede son mapping, pas de cross-coupling. La generalisation par `api/graph.py` confirme l'uniformite du pattern.
- **Verdict** : Conforme — homogeneite renforcee, pas de divergence.

---

## Ecarts constates (reconduits du rapport 0.6.1)

### [MIN] Litteraux `table_mode` / `chunker_type` non centralises

- **Localisation** :
  - `document-parser/api/schemas.py:124` (`default="accurate"`), `schemas.py:154` (`("accurate", "fast")`)
  - `document-parser/api/schemas.py:172` (`default="hybrid"`), `schemas.py:185` (`("hybrid", "hierarchical")`)
  - `document-parser/domain/value_objects.py:104` (`table_mode: str = "accurate"`), `value_objects.py:130` (`chunker_type: str = "hybrid"`)
  - `document-parser/infra/settings.py:20`, `settings.py:113`, `settings.py:149`
  - `document-parser/infra/local_converter.py:91` (`options.table_mode == "accurate"`)
  - `document-parser/infra/local_chunker.py:88` (`options.chunker_type == "hierarchical"`)
  - `document-parser/services/analysis_service.py:74` (`default_table_mode: str = "accurate"`)
- **Constat** : Inchange depuis 0.6.1. Un typo silencieux dans `local_converter.py:91` ferait basculer `TableFormerMode.ACCURATE` -> `TableFormerMode.FAST` sans alerter Pydantic.
- **Regle violee** : Item 5.3 (poids 2) — magic strings non centralisees.
- **Remediation** : Creer `document-parser/domain/constants.py` avec `TABLE_MODES`, `CHUNKER_TYPES`, `TABLE_MODE_DEFAULT`, `CHUNKER_TYPE_DEFAULT` et importer dans les 6 sites.

### [MIN] Logique de polling dupliquee dans 3 stores/pages

- **Localisation** :
  - `frontend/src/features/analysis/store.ts:72` (`setInterval` 2s + retry 3x + timeout 15min)
  - `frontend/src/features/ingestion/store.ts:31` (`setInterval` recurrent, intervalle parametrable)
  - `frontend/src/pages/ReasoningPage.vue:117` (`window.setInterval` 500ms wait-until-idle)
- **Constat** : Inchange depuis 0.6.1 ; aucun `usePoller` n'a ete ajoute dans `frontend/src/shared/composables/`.
- **Regle violee** : Item 5.4 (poids 1) — logique reactive partagee devrait etre dans `shared/composables/`.
- **Remediation** : Extraire `usePoller(fn, { intervalMs, timeoutMs, maxRetries, until })`.

---

## Ecarts INFO

### [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE`

- **Localisation** : `document-parser/api/documents.py:19`, `document-parser/services/document_service.py:26`.
- **Constat** : Memes `64 * 1024`, nommes differemment. Inchange.
- **Remediation** : Promouvoir `FILE_STREAM_CHUNK_SIZE` dans `services/constants.py` (ou `domain/constants.py`).

### [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue`

- **Localisation** : `frontend/src/features/store/ui/StoreForm.vue:298`.
- **Constat** : `'bolt://localhost:7687'` / `'http://localhost:9200'` toujours en dur. Inchange.
- **Remediation** : Exporter `NEO4J_URI_PLACEHOLDER` et `OPENSEARCH_URI_PLACEHOLDER` depuis `connectionForm.logic.ts`.

### [INFO] Helpers `_element_node` / `_page_node` dupliques entre `infra/docling_graph.py` et `infra/neo4j/queries.py`

- **Localisation** :
  - `document-parser/infra/docling_graph.py:32-63` (`_element_node`, `_page_node`, `_edge`)
  - `document-parser/infra/neo4j/queries.py:88-133` (`_element_node`, `_page_node`, `_chunk_node`, `_edge_id`)
- **Constat** : Deux modules construisent des dicts Cytoscape avec les memes cles (`id`, `group`, `docling_label`, `self_ref`, `text`, `prov_page`, `provs`, `level`, `doc_id` pour les elements ; `id`, `group`, `page_no`, `width`, `height`, `doc_id` pour les pages). Le commentaire `docling_graph.py:4` documente explicitement le mirroring : "Mirrors `infra.neo4j.queries.fetch_graph`". Les contrats d'entree different (dict Docling vs row Neo4j) ce qui justifie l'existence de deux constructeurs ; en revanche les **cles de sortie** sont dupliquees a la main et un drift silencieux casserait la parite des deux endpoints `/graph` et `/reasoning-graph` cote frontend.
- **Constat additionnel** : Cet ecart **existait deja dans 0.6.1** (les deux fichiers sont anterieurs au commit `8103460`) mais n'avait pas ete remonte par le rapport precedent. Il n'est PAS introduit par le batch `#audit-*`. Je le surface ici pour traçabilite, sans modifier le score (le rapport 0.6.1 servait de baseline).
- **Regle violee** : Item 5.3 (poids 2) — magic strings (les cles de schema Cytoscape) non centralisees.
- **Severite** : INFO car les deux modules sont infra-only et un test e2e du frontend `GraphView` rattrape un drift de schema.
- **Remediation** : Extraire un constructeur partage `_cytoscape_element_node({...})` dans `infra/docling_tree.py` (ou un nouveau `infra/cytoscape_schema.py`) prenant un dict normalise et retournant le dict final. Les deux callsites ne fournissent plus que la conversion source->normalise.

---

## Points positifs

- Tous les "Points positifs" du rapport 0.6.1 sont preserves (centralisation HTTP `shared/api/http.ts`, `STORAGE_KEYS`, enums backend, validation URI centralisee, `_SELECT_WITH_DOC` partage, helpers `_to_response` par-router).
- Le batch `#audit-*` n'a introduit **aucune nouvelle duplication** :
  - `services/graph_service.py` est l'unique orchestrateur des deux projections graph (avant `#audit-01`, l'orchestration etait inline dans `api/graph.py` + appels directs a `infra/`).
  - `infra/neo4j/graph_adapter.py` ne reimplemente rien : delegations 1-2 lignes vers les fonctions libres existantes.
  - Le nouveau `_to_response` dans `api/graph.py:64-73` aligne le routeur graph sur la convention deja en place (1 mapper par routeur, scopes par DDD).
- L'ajout du port `GraphReader` / `GraphWriter` dans `domain/ports.py` clarifie au contraire le contrat unique et reduit le risque de divergence entre callsites.

---

## Verdict partiel : GO CONDITIONNEL

**Justification** :
- Score 75 / 100 — identique a 0.6.1 (seuil GO: 80).
- Zero CRITICAL, zero MAJOR.
- Les 2 MIN persistent (non traites par le batch `#audit-*` — hors scope explicite).
- 1 nouvel INFO surface (helpers Cytoscape dupliques entre `docling_graph.py` et `neo4j/queries.py`), mais cet ecart est **anterieur a 0.6.1** et n'est pas une regression.
- Le code introduit par `#audit-01` (ports graph/tree) est exemplaire cote DRY : adaptateurs ultra-fins, helper de mapping aligne sur la convention.

**Delta vs 0.6.1** : score inchange (75), CRIT/MAJ/MIN inchanges (0/0/2), +1 INFO (2 -> 3) attribuable a une observation plus fine, pas a une regression du batch.

**Conditions pour GO inconditionnel (prochain cycle)** : inchangees vs 0.6.1.
1. Creer `document-parser/domain/constants.py` (`TABLE_MODES`, `CHUNKER_TYPES`).
2. Extraire `frontend/src/shared/composables/usePoller.ts`.

Optionnel (INFO) :
3. Centraliser `FILE_STREAM_CHUNK_SIZE`.
4. Centraliser les placeholders URI `StoreForm.vue`.
5. Extraire le schema Cytoscape partage entre `docling_graph.py` et `neo4j/queries.py`.

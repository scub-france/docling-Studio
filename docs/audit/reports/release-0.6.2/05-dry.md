# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.6.2
**Branche** : `release/0.6.2` @ `051ac4a`
**Date** : 2026-06-05
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

## Methode

L'audit re-evalue chaque item de la fiche `docs/audit/audits/05-dry.md` sur le working tree de `release/0.6.2`, en croisant avec la baseline `reports/release-0.6.1-reaudit/05-dry.md` pour detecter regressions ou resorptions.

Le delta `release/0.6.1..release/0.6.2` touche essentiellement le tooling (`#254` : Dockerfile slim, migration `uv`, isolation des deps reasoning) et trois fichiers metier (`api/schemas.py`, `domain/ports.py`, `domain/value_objects.py`, `services/analysis_service.py`). Aucun de ces commits ne touche les sites de duplication identifies — la duplication n'a donc ni regresse ni progresse.

---

## Suivi des ecarts du rapport 0.6.1 re-audit

| Ecart 0.6.1 re-audit | Statut 0.6.2 |
|-----------------------|--------------|
| [MIN] Litteraux `table_mode` / `chunker_type` non centralises | **PERSISTE** — `domain/constants.py` n'existe toujours pas (`ls document-parser/domain/`). Les 9 occurrences sont identiques : `api/schemas.py:124,154,172,185`, `domain/value_objects.py:104,130`, `infra/settings.py:20,113,149`, `infra/local_converter.py:91`, `infra/local_chunker.py:88`, `services/analysis_service.py:74`. |
| [MIN] Polling duplique dans 3 stores/pages | **PERSISTE** — `frontend/src/shared/composables/` ne contient que `usePagination.ts` ; pas de `usePoller.ts`. Sites toujours en place : `features/analysis/store.ts:72,94`, `features/ingestion/store.ts:31`, `pages/ReasoningPage.vue:117`. |
| [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE` | **PERSISTE** — `api/documents.py:19` et `services/document_service.py:26`, memes `64 * 1024`. |
| [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue` | **PERSISTE** — `frontend/src/features/store/ui/StoreForm.vue:298` (`'bolt://localhost:7687'` / `'http://localhost:9200'`). |
| [INFO] Helpers Cytoscape dupliques (`docling_graph.py` ↔ `neo4j/queries.py`) | **PERSISTE** — `infra/docling_graph.py:32-73` (`_element_node`/`_page_node`/`_edge`) et `infra/neo4j/queries.py:88-134` (`_element_node`/`_page_node`/`_chunk_node`/`_edge_id`) restent inchanges. |

Aucun ecart resorbe, aucun nouveau ecart introduit. Le diff `0.6.1..0.6.2` ne touche aucun des sites concernes (verifie via `git diff --stat`).

---

## Items conformes

### 5.1 — Aucun bloc 3+ fois sans factorisation (poids 2)
- Conforme. Le batch `#audit-01` (refactor hex-arch graph + tree access through ports) avait deja consolide les adapters. Les nouveaux helpers `_to_response` continuent de suivre la regle "1 mapper par router" (`api/graph.py:64-73`, `api/documents.py:29`, etc.).
- Pas de copie-colle nouvelle introduite dans `0.6.2`.

### 5.2 — Types partages centralises (poids 2)
- Conforme. `frontend/src/shared/types.ts` (211 lignes) reste le seul lieu des contrats partages cross-feature. `document-parser/domain/models.py` reste la source unique cote backend.

### 5.4 — Composables partages (poids 1)
- **Non conforme** (item porte le MIN — voir Ecarts).

### 5.5 — Centralisation HTTP (poids 2)
- Conforme. `grep -rn "fetch(" frontend/src --include="*.ts" --include="*.vue" | grep -v "http.ts\|node_modules"` retourne 0 ligne. Tous les appels passent par `shared/api/http.ts`.

### 5.6 — Schemas Pydantic ne re-definissent pas le domain (poids 2)
- Conforme. `api/schemas.py` ajoute les `validation_alias` camelCase et les `field_validator`s qui sont des transformations de DTO, pas des re-definitions du domain. Les dataclasses domain (`ConversionOptions`, `ChunkingOptions`) restent en aval, decouplees.

### 5.7 — Regles de validation a un seul endroit (poids 1)
- Conforme. Les seuils numeriques (`max_tokens 64..8192`, `images_scale 0..10`) ne vivent que dans `api/schemas.py:158-194`. Cote frontend, `StrategyPopover.vue:148` / `ChunkPanel.vue:253` exposent les memes valeurs **par defaut** (constantes `512`, `'hybrid'`) mais ne re-implementent pas la validation — l'erreur backend reste autoritative.

---

## Ecarts constates

### [MIN] Litteraux `table_mode` / `chunker_type` non centralises

- **Localisation** :
  - `document-parser/api/schemas.py:124` (`default="accurate"`), `:154-155` (`("accurate", "fast")`)
  - `document-parser/api/schemas.py:172` (`default="hybrid"`), `:185-186` (`("hybrid", "hierarchical")`)
  - `document-parser/domain/value_objects.py:104` (`table_mode: str = "accurate"`), `:130` (`chunker_type: str = "hybrid"`)
  - `document-parser/infra/settings.py:20,113,149`
  - `document-parser/infra/local_converter.py:91` (`options.table_mode == "accurate"`)
  - `document-parser/infra/local_chunker.py:88` (`options.chunker_type == "hierarchical"`)
  - `document-parser/services/analysis_service.py:74` (`default_table_mode: str = "accurate"`)
- **Constat** : Aucune evolution depuis 0.6.1. Un typo silencieux dans `local_converter.py:91` (`"accurte"`) basculerait `TableFormerMode.ACCURATE` -> `FAST` sans declencher la moindre alerte Pydantic. Item 5.3.
- **Regle violee** : Item 5.3 (poids 2) — magic strings dispersees.
- **Remediation** : Creer `document-parser/domain/constants.py` exposant `TABLE_MODES = ("accurate", "fast")`, `CHUNKER_TYPES = ("hybrid", "hierarchical")`, `TABLE_MODE_DEFAULT`, `CHUNKER_TYPE_DEFAULT`. Importer dans les 9 sites. Idealement remplacer par des `Literal[...]` ou des `StrEnum` pour benficier du type-check.

### [MIN] Logique de polling dupliquee dans 3 stores/pages

- **Localisation** :
  - `frontend/src/features/analysis/store.ts:72` (`setInterval` 2s + retry 3x + timeout via `pollingTimeout.value = setTimeout(...)` ligne 94)
  - `frontend/src/features/ingestion/store.ts:31` (`setInterval(checkAvailability, intervalMs)`)
  - `frontend/src/pages/ReasoningPage.vue:117` (`window.setInterval` 500ms + `Date.now() - started > timeoutMs` ligne 121)
- **Constat** : Inchange depuis 0.6.1. La fiche cite l'occurrence dans le repertoire `features/reasoning/...` mais le file reel est `pages/ReasoningPage.vue:117` — fichier confirme par `grep -rn setInterval`. Aucun `usePoller` n'a ete ajoute (`frontend/src/shared/composables/` ne contient que `usePagination.ts` / `usePagination.test.ts`).
- **Regle violee** : Item 5.4 (poids 1) — logique reactive partagee non extraite.
- **Remediation** : Extraire `useAsyncPoller(fn, { intervalMs, timeoutMs, maxRetries, until })` dans `shared/composables/usePoller.ts`. Les 3 sites se reduisent a un seul appel parametre. Couvrir par un test Vitest avec timers fakes.

---

## Ecarts INFO

### [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE`

- **Localisation** : `document-parser/api/documents.py:19` (`_READ_CHUNK_SIZE = 64 * 1024`), `document-parser/services/document_service.py:26` (`_UPLOAD_CHUNK_SIZE = 64 * 1024`).
- **Constat** : Memes 64 KB, deux noms differents pour deux usages contigus (read upload puis flush disk). Aucun changement depuis 0.6.1.
- **Remediation** : Promouvoir en `services/constants.py::FILE_STREAM_CHUNK_SIZE`.

### [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue`

- **Localisation** : `frontend/src/features/store/ui/StoreForm.vue:297-299` :
  ```ts
  const connectionUriPlaceholder = computed(() =>
    form.kind === 'neo4j' ? 'bolt://localhost:7687' : 'http://localhost:9200',
  )
  ```
- **Constat** : Inchange. Aucun export `NEO4J_URI_PLACEHOLDER` / `OPENSEARCH_URI_PLACEHOLDER` cree dans `connectionForm.logic.ts` (`grep PLACEHOLDER` -> 0 hit).
- **Remediation** : Exporter ces constantes depuis `features/store/connectionForm.logic.ts` et les consommer dans le `.vue`.

### [INFO] Helpers `_element_node` / `_page_node` dupliques entre `infra/docling_graph.py` et `infra/neo4j/queries.py`

- **Localisation** :
  - `document-parser/infra/docling_graph.py:32-73` (`_element_node`, `_page_node`, `_edge`)
  - `document-parser/infra/neo4j/queries.py:88-134` (`_element_node`, `_page_node`, `_chunk_node`, `_edge_id`)
- **Constat** : Cet ecart, surface lors du re-audit 0.6.1, persiste. Les deux constructeurs Cytoscape gardent les memes cles (`id`, `group`, `docling_label`, `self_ref`, `text`, `prov_page`, `provs`, `level`, `doc_id` pour les elements ; `id`, `group`, `page_no`, `width`, `height`, `doc_id` pour les pages). Le commentaire de tete `docling_graph.py:4` documente le mirroring : "Mirrors `infra.neo4j.queries.fetch_graph`". Les entrees different (dict Docling vs row Neo4j) — c'est leur raison d'etre — mais les cles de sortie sont dupliquees a la main, un drift silencieux casserait la parite des deux endpoints `/graph` et `/reasoning-graph` cote frontend.
- **Severite** : INFO car infra-only et detectable a l'execution par les e2e du `GraphView`.
- **Remediation** : Extraire un constructeur partage `_cytoscape_element_node({...})` dans `infra/cytoscape_schema.py` (ou `infra/docling_tree.py`) prenant un dict normalise et retournant le dict final. Les deux callsites ne fournissent plus que la conversion source -> normalise.

---

## Points positifs

- Aucune nouvelle duplication introduite par `0.6.2`. Le diff `0.6.1..0.6.2` touche essentiellement le tooling (Dockerfile slim post-uv, migration `uv`, isolation reasoning deps) — aucun de ces commits ne touche les sites de duplication identifies.
- La centralisation HTTP via `shared/api/http.ts` est intacte (0 appel `fetch()` hors du client centralise).
- Les `_to_response` par router (1 mapper par scope DDD) restent l'unique convention — `api/graph.py:64-73` continue de respecter la regle.
- Les adapters fins introduits par `#audit-01` (`infra/neo4j/graph_adapter.py`, `tree_reader.py`) ne re-implementent rien : delegations 1-2 lignes vers les fonctions libres existantes (`infra/neo4j/queries.py:fetch_graph`, `infra/docling_tree.py`).
- Les types frontend partages (`frontend/src/shared/types.ts`, 211 lignes) restent l'unique source de verite cross-feature.

---

## Verdict partiel : GO CONDITIONNEL

**Justification** :
- Score 75 / 100 — identique a 0.6.1 (re-audit) et 0.6.1 initial. Sous le seuil GO (80).
- 0 CRITICAL, 0 MAJOR — les 2 MIN persistent sans nouveau MAJ/CRIT.
- Aucune regression introduite par `0.6.2` (le delta `0.6.1..0.6.2` ne touche aucun des sites concernes).
- Les 3 INFO sont des observations restees telles quelles depuis la baseline.

**Delta vs 0.6.1 (re-audit)** : score inchange (75), CRIT/MAJ/MIN/INFO inchanges (0/0/2/3). Pas de regression, pas de resorption.

**Conditions pour GO inconditionnel (prochain cycle)** : inchangees vs 0.6.1.
1. Creer `document-parser/domain/constants.py` (`TABLE_MODES`, `CHUNKER_TYPES`) et migrer les 9 sites.
2. Extraire `frontend/src/shared/composables/usePoller.ts` et migrer les 3 stores/pages.

Optionnel (INFO) :
3. Centraliser `FILE_STREAM_CHUNK_SIZE`.
4. Centraliser les placeholders URI dans `connectionForm.logic.ts`.
5. Extraire le schema Cytoscape partage entre `docling_graph.py` et `neo4j/queries.py`.

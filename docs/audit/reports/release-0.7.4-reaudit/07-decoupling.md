# Rapport de re-audit : Découplage

> **Re-audit 0.7.4 — score 94 → 94 (100 en lecture « déclarations Python »)**

**Release** : 0.7.4 (re-audit après remédiation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (code audité ; HEAD `4c59df0` n'ajoute que deux rapports de re-audit)
**Baseline** : `release-0.7.4/07-decoupling.md` (code `1de1929`, rapport commité en `e6047c2` ;
94/100, GO, 0 CRIT, 1 MAJ, 0 MIN, 15 INFO)
**Remédiation examinée** : `git log e6047c2..a4d9679` (100 commits). Commits pertinents :
- `7a1f4d5` refactor(api): type the store config and graph node responses (#audit-07) ;
- `cb1e3b9` (handler d'erreurs unique) ;
- `39dcda5` (ports déclarant toutes les méthodes appelées) ;
- `23fb05e` (arête `document → chunks` retirée) ;
- `f0a2a60` (comptage des analyses par les résumés).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 18 |

Somme des poids = 35. Seul **7.4.2** (poids 2) reste non conforme : 33 / 35 = 94,29, soit **94**.

**Lecture des items** : même lecture qu'en 0.7.4. L'item 7.4.2 se lit sur ce que les schémas
Pydantic **publient** comme contrat HTTP : « documentent le contrat HTTP — pas de `dict` ou `Any`
dans les responses ». Le constat 0.7.4 parlait d'un contrat « opaque des deux côtés ». Le
correctif a typé les champs Python et TS, mais l'OpenAPI publié reste un objet libre (cf. MAJ).
Une lecture limitée aux déclarations de champs de `api/schemas.py` / `api/graph.py` rendrait
l'item conforme : **16 / 16 = 100**.

### Méthode

- Chaque écart et chaque INFO 0.7.4 a été re-vérifié dans le code, pas dans les messages de commit.
- Scans exhaustifs rejoués sur l'arbre `a4d9679` et sur `e6047c2` (extrait par `git archive`
  dans le scratchpad, même script pour les deux) :
  - imports `@/` et relatifs de `frontend/src/` (hors tests) ;
  - imports Python par couche (AST, `TYPE_CHECKING` distingué) ;
  - retours publics de `persistence/` ;
  - appels HTTP hors `api.ts`.
- OpenAPI : `main.app.openapi()` (pydantic 2.13.4) inspecté pour les schémas modifiés. Le
  schéma 0.7.4 de `GraphNode` et de `config: dict` a été reconstruit à l'identique dans un script
  hors dépôt.
- Tests ciblés :
  - `test_architecture.py`, `test_graph_api.py`, `test_api_stores.py`, `test_api_errors.py`
    (dans 151 passés, avec les tests DRY) ;
  - `test_architecture.py -k Persistence` relancé seul : 8 passés.
- Suites complètes non relancées. Résultats du coordinateur sur HEAD : pytest 1673 passed /
  19 skipped, eslint OK, vue-tsc OK, vitest 522 passed.

### Mesures

| Mesure | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) |
|--------|-------------------|----------------------|
| Imports feature → feature (hors tests) | 13, tous via barrel | **12, tous via barrel** (arête `document → chunks` retirée, `23fb05e`) |
| Imports profonds feature → internes d'une autre feature | 0 | 0 |
| `import type` feature → feature | 0 | 0 |
| `eslint src` / `vue-tsc --noEmit` | exit 0 / exit 0 | OK / OK (coordinateur) |
| `shared/` → internes de features | 2 (`AppSidebar.vue`) | 2 (=) |
| Imports profonds `pages/` + `app/` → internes de features | 52 (49 + 3) | **44** (41 + 3 ; 3 fichiers `pages/` supprimés) |
| Stores Pinia qui consomment un autre store | 2 (actions seules) | 2 (=) |
| `docling*` hors `infra/` | 0 | 0 |
| `fastapi` / `starlette` hors `api/`, `main.py`, `bootstrap/mcp_mount.py`, `infra/rate_limiter.py` | 0 | 0 |
| Imports `services/` → `infra/` ou `persistence/` | 0 à l'exécution ; 3 + 7 sous `TYPE_CHECKING` | **0 / 0** (garde AST `tests/test_architecture.py:169-188`) |
| Champs `dict` / `extra="allow"` déclarés dans un schéma de réponse | 2 | **0** |
| Schémas de réponse publiés sans propriétés dans l'OpenAPI (`{"type":"object","additionalProperties":true}`) | 1 (`config`), + `GraphNode` ouvert (3 propriétés + extras) | **3** (`StoreConfigResponse`, `GraphNode`, `GraphProvenance`) |
| SQL / `get_connection` hors `persistence/` | 2 sites | 2 sites (=) |
| Appels HTTP hors `api.ts` / `graphApi.ts` / `shared/api/http.ts` | 2 | 2 (=) |
| `tests/test_architecture.py` | 39 passed | 45 tests collectés ; suite verte (coordinateur) |

---

## Statut par item

| Item | Poids | 0.7.4 | Re-audit | Preuve (`a4d9679`) |
|------|-------|-------|----------|--------------------|
| 7.1.1 REST-only front/back | 3 | Conforme | Conforme (=) | Client unique `frontend/src/shared/api/http.ts:5`. Aucun import croisé ni fichier ou DB partagé. Seules mentions croisées : deux commentaires (`mcp_adapter/apps.py:81`, `pages/DocsLibraryPage.logic.ts:14`, cf. INFO 16). |
| 7.1.2 Types TS = schémas Pydantic | 3 | Conforme | Conforme (=) | `StoreConfigResponse` (`api/schemas.py:361-374`) ↔ `StoreConfig` (`features/store/api.ts:22-26`) ; `GraphNode` (`api/graph.py:42-74`) ↔ `GraphNode` (`features/analysis/graphApi.ts:24-50`), signature d'index retirée ; `AnalysisSummary` / `ConfigSource` inchangés (`shared/types.ts:84`, `:5`). Nuances de nullabilité : INFO 19. |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | Conforme | Conforme (=) | 11 `features/*/api.ts` + `graphApi.ts`. Deux appels hors `api.ts`, inchangés (INFO 14). |
| 7.1.4 Back testable sans front | 2 | Conforme | Conforme (=) | 18 fichiers de test utilisent `TestClient` / `AsyncClient`. Le handler d'erreurs est enregistré par les apps de test autonomes (`tests/test_graph_api.py`, `test_reasoning_api.py`, `test_mcp_config_api.py`). |
| 7.1.5 Pas de logique métier dupliquée | 2 | Conforme | Conforme (=) | Gardes UX inchangées (INFO 4, 10). Nouvelle constante front recopiant un défaut de persistence : INFO 16, sans règle métier. |
| 7.2.1 Feature = store + api + ui | 2 | Conforme | Conforme (=) | 13 features, compositions inchangées (`feature-flags` sans `api.ts`, `settings` sans `api.ts`, `store` sans `store.ts`, `search` sans `ui/`, `reasoning` sans barrel). |
| 7.2.2 Frontière barrel + ESLint | 3 | Conforme | Conforme (=) | Règle `frontend/eslint.config.js:28-55` inchangée. 12 imports feature → feature, tous vers `@/features/<nom>`. 0 import profond. |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | Conforme | Conforme (=) | 0 type inter-features. `StoreConfig`, `GraphNode`, `GraphProvenance` restent internes à leur feature. |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | Conforme | Conforme (=) | `features/reasoning/store.ts:22` → action `focusElement` (`:51`, `:55`) ; `features/admin-config/store.ts:80`, `:95` → action `reload`. |
| 7.3.1 Repos → objets du domaine | 2 | Conforme | Conforme (=) | Scan AST des retours publics de `persistence/` : seuls 4 index typés (`analysis_repo.py:129`, `app_settings_repo.py:16`, `document_repo.py:96`, `document_store_link_repo.py:72`). Nouveaux retours domaine : `DocumentVersionEntry` (`domain/ports.py`), `ChunkPush`. |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme | Conforme (=) | `docling` / `docling_core` importés par 8 modules `infra/` uniquement. Liste noire `_SERVICES_FORBIDDEN_EXTERNALS` (`tests/test_architecture.py:345-359`) étendue à `pdf2image` / `pypdfium2`. |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | Conforme | Conforme (=) | Aucun SQL dans `services/`, `api/`, `domain/`, `infra/`, `mcp_adapter/`. Les deux requêtes du composition root restent (INFO 13). |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | Conforme | Conforme (=) | Hors `api/` et `main.py` : `bootstrap/mcp_mount.py:41-42`, `infra/rate_limiter.py:18-19` (INFO 7). Le handler d'erreurs vit dans `api/errors.py` ; les services n'importent pas FastAPI (`services/errors.py`). |
| 7.4.1 Ports = signatures claires, types domaine | 2 | Conforme | Conforme (=) | Nouveaux ports typés : `PdfInspector` (`domain/ports.py`, `page_count` / `page_sizes`), `FileStorage` (`save` / `exists` / `resolve` / `delete`), `ChunkRepository.replace_chunkset`. Exception : `GraphDriverPool.get -> Any` (INFO 18). |
| 7.4.2 Pas de `dict` / `Any` dans les responses | 2 | **Non conforme [MAJ]** | **Non conforme [MAJ]**, partiellement corrigé | Champs typés, mais `ProvidedKeysModel._provided_keys_only -> dict[str, Any]` (`api/schemas.py:76-79`) fait publier les trois modèles comme objets libres (cf. MAJ). |
| 7.4.3 Format de réponse cohérent | 1 | Conforme | Conforme (renforcé) | Un seul handler pour toutes les `ServiceError` : `{"detail": …}` avec le statut porté (`api/errors.py:24-30`, `main.py:90`), testé (`tests/test_api_errors.py`). Le code ne dépend plus du libellé (INFO 5 corrigé). Reliquat 400 / 404 : INFO 20. |

---

## Écarts constatés

### [MAJ] 7.4.2 — `StoreResponse.config` et `GraphNode` typés en Python et en TS, mais toujours publiés comme objets libres dans l'OpenAPI — statut : **partiellement corrigé**

- **Localisation** :
  - `document-parser/api/schemas.py:64-79` : `ProvidedKeysModel`, avec `@model_serializer(mode="wrap")`
    annoté `-> dict[str, Any]` en `:76-77` ;
  - modèles qui en héritent : `StoreConfigResponse` (`api/schemas.py:361-374`, utilisé par
    `StoreResponse.config` `:392`), `GraphProvenance` (`api/graph.py:28-39`), `GraphNode`
    (`api/graph.py:42-74`).
- **Constat** :
  - **Ce qui est corrigé.** Les deux surfaces déclarent leurs champs : `index_name` / `indexName` /
    `database`, et les champs émis par groupe par `infra/neo4j/queries.py`. Les miroirs TS
    n'ont plus de `Record<string, unknown>` ni de signature d'index : `features/store/api.ts:22-26`,
    `:35` et `features/analysis/graphApi.ts:8-18`, `:24-50`. Le JSON servi est inchangé, à
    l'exception des clés de config non lues.
  - **Ce qui ne l'est pas : le contrat publié.**
    - Pydantic dérive le schéma JSON de **sérialisation** d'un modèle doté d'un
      `model_serializer` à partir de l'annotation de retour du sérialiseur, ici
      `dict[str, Any]`. FastAPI publie les schémas de réponse dans ce mode.
    - Sur l'application réelle (`main.app.openapi()["components"]["schemas"]`), on obtient :
      `StoreConfigResponse` = `GraphNode` = `GraphProvenance` =
      `{"additionalProperties": true, "type": "object"}`.
    - Les champs n'apparaissent que dans le schéma de *validation*
      (`model_json_schema(mode="validation")`), que FastAPI n'utilise pas pour une réponse.
  - **`StoreResponse.config`** : le contrat publié est **identique** à 0.7.4. `config: dict`
    produisait déjà `{"additionalProperties": true, "type": "object"}`, reconstruit à l'identique.
  - **`GraphNode`** : le contrat publié **régresse**. En 0.7.4, `extra="allow"` publiait `id` et
    `group` (requis) et `label`, plus les extras. Il ne publie plus aucune propriété.
  - Aucun test n'asserte l'OpenAPI (`git grep "openapi()" document-parser/tests` : 0). Le
    CHANGELOG `[Unreleased]` › Changed (« … are now typed in the OpenAPI schema instead of free
    objects ») est donc inexact ; ce point est signalé pour l'audit 11.
  - Surface dépréciée (ingestion), retrait annoncé en 0.8.0.
- **Règle violée** : 7.4.2 (poids 2) — « Les schémas Pydantic documentent le contrat HTTP — pas de
  `dict` ou `Any` dans les responses ». Le type de sérialisation de ces trois réponses **est**
  `dict[str, Any]`.
- **Remédiation** :
  - retirer l'annotation de retour de `_provided_keys_only` (`api/schemas.py:77`). Vérifié hors
    dépôt avec pydantic 2.13.4 : le schéma de sérialisation liste alors les propriétés
    déclarées, et le dump reste `{'index_name': 'x'}` pour un modèle construit avec la seule
    `index_name`. La règle ruff `ANN` n'est pas activée (`pyproject.toml:82-92`) ;
  - variante : `model_config = ConfigDict(json_schema_mode_override="validation")` sur
    `ProvidedKeysModel` ;
  - ajouter un test qui asserte `properties` de `StoreConfigResponse` et
    `required == ["id", "group"]` de `GraphNode` dans `app.openapi()`.
- **Effort** : XS. **Risque** : nul sur le JSON servi ; seul l'OpenAPI change, et aucun client
  généré ne le consomme. **Gain** : +6 (94 → 100).

### [INFO] Constats 0.7.4 — statut re-vérifié sur `a4d9679`

| # | Constat | Localisation vérifiée | Statut |
|---|---------|-----------------------|--------|
| 1 | `shared/ui` n'est pas une feuille : `AppSidebar.vue` importe deux stores de features | `frontend/src/shared/ui/AppSidebar.vue:55-56` ; barrel `shared/ui/index.ts:1` ; consommateurs du barrel `features/mcp-config/ui/McpConfigSection.vue:376`, `features/settings/ui/SettingsPanel.vue:115`, `features/chunking/ui/ChunkPanel.vue:231` | Inchangé |
| 2 | Cycles de barrels `document` ↔ `analysis` et `document` ↔ `chunks` | `document` → `analysis` : `features/document/store.ts:5`, `ui/DocumentUpload.vue:49`, `ui/DocumentActionsMenu.vue:48` ; `analysis` → `document` : `features/analysis/ui/AnalysisPanel.vue:61`, `ui/StructureViewer.vue:64` | **Partiellement corrigé** : `document` ↔ `chunks` rompu (`document/store.ts` n'importe plus `@/features/chunks`, `23fb05e`) ; `document` ↔ `analysis` demeure |
| 3 | Pages et shell importent en profondeur les internes de features ; `reasoning` sans barrel | 41 imports `pages/` + 3 `app/` (`app/App.vue:52`, `:54`, `app/router/index.ts:3`) ; mélange barrel / profond dans un même fichier : `pages/DocsLibraryPage.vue:211` vs `:212-214` (le `:212` reçoit en plus `fetchAnalysisSummaries`, ajouté par `f0a2a60`) | Inchangé sur le fond ; décompte 52 → 44 par suppression de pages |
| 4 | Bornes MCP et règle d'hôte recopiées côté front, non publiées dans l'OpenAPI de la requête | `features/mcp-config/types.ts:59-62` vs `domain/mcp_config.py:29-35` ; `McpConfigUpdateRequest` sans `Field(ge, le)` (`api/schemas.py:854-855`) ; `features/mcp-config/client.ts:41` | Inchangé |
| 5 | Code HTTP dérivé du texte d'une exception (import d'analyse) | `api/analyses.py:139-145` : seul `ValueError` → 400 ; document inconnu → `DocumentNotFoundError` (`services/analysis_service.py:137`, `:165`) → 404 par le handler | **Corrigé** |
| 6 | Contrat d'URL backend → SPA (deep links MCP), testé en miroir sans fixture commune | `services/citation_service.py:223` ; `frontend/src/app/router/routes.ts:39-49` ; `frontend/src/app/router/router.test.ts:72-74` | Inchangé |
| 7 | Couplage framework HTTP étendu à `bootstrap/mcp_mount.py` ; façade MCP typée `Any` | `bootstrap/mcp_mount.py:41-42`, `:114` ; `mcp_adapter/__init__.py:22` ; `infra/rate_limiter.py:18-19` | Inchangé |
| 8 | Deux casses pour la notion de page ; DTO wire anonyme | `features/document/api.ts:38-42` | Inchangé |
| 9 | Champ de contrat orphelin `Document.stores?` | `frontend/src/shared/types.ts:45` | Inchangé |
| 10 | Pré-validation de taille de fichier côté front (garde UX) | `features/document/store.ts:75` | Inchangé (aucune action requise) |
| 11 | Règle ESLint plus étroite que « barrel uniquement » | `frontend/eslint.config.js:28-55` (non modifié) | Inchangé |
| 12 | Services annotés avec des repos SQLite concrets (sous `TYPE_CHECKING`) | 0 import de `persistence` / `infra` dans `services/`, gardé ou non ; ports `domain/ports.py` (`StoreRepository`, `DocumentStoreLinkRepository`, `VectorStorePool`, `GraphDriverPool`) ; garde AST `tests/test_architecture.py:169-188` | **Corrigé** |
| 13 | SQL brut et `get_connection` dans le composition root | `bootstrap/factories.py:22`, `:122-127` (`check_store_secret_key`) ; `main.py:41`, `:135-137` (`/api/health`) | Inchangé |
| 14 | Deux appels HTTP hors des modules `api.ts` | `features/feature-flags/store.ts:3`, `:159` ; `features/document/ui/DownloadDropdown.vue:133` | Inchangé |
| 15 | Commandes de vérification 7.2.4 et 7.4.2 de la fiche incomplètes | `docs/audit/audits/07-decoupling.md` (non modifié) ; la commande 7.4.2 ne verrait pas non plus le MAJ actuel | Inchangé |

### [INFO] 16 — Constante front miroir d'un défaut de persistence non publié (nouveau, introduit par la remédiation)

- **Localisation** :
  - `frontend/src/pages/DocsLibraryPage.logic.ts:10-17` (`SUMMARIES_PAGE = 200`, la docstring cite
    `document-parser/persistence/analysis_repo.py`) et `:34-44` (`countDocumentAnalyses`) ;
  - côté backend : `document-parser/persistence/analysis_repo.py:70` (`limit: int = 200`) et
    `domain/ports.py:306` ;
  - route : `api/analyses.py:164-187`, qui n'expose ni `limit`, ni total, ni indicateur de
    troncature.
  - Introduit par `f0a2a60`.
- **Constat** : le front décide si la liste des résumés est complète en comparant sa longueur à
  une copie d'un défaut interne au repository. Si ce défaut baisse côté backend, une liste
  tronquée passe pour complète. L'avertissement de suppression sous-compterait alors : c'est
  précisément ce que le commentaire veut éviter. Le contrat REST ne porte pas cette
  information ; elle est dupliquée à la main.
- **Remédiation** : publier la troncature (champ `truncated` / `total` ou en-tête), ou compter
  directement par `GET /api/analyses?documentId=` (déjà utilisé en repli, `ofDocument`).

### [INFO] 17 — Garde-fous d'architecture : seules les règles AST mordent ; `persistence` importe `infra` (rectification)

- **Localisation** :
  - `document-parser/tests/test_architecture.py:229-238` : le test documente que les règles
    pytestarch « never see an edge » ;
  - règles pytestarch : `:114-127` (domain), `:190-203` (api), `:206-219` (infra), `:322-334`
    (persistence) ;
  - gardes AST effectives : `:169-188` (services), `:222-247` (mcp_adapter), `:377-397`
    (externes des services) ;
  - violation : `document-parser/persistence/store_repo.py:24` (`from infra.secrets import
    get_fernet_box`), identique à `e6047c2`.
- **Constat** :
  - La docstring du test annonce « persistence -> no import from … infra » (`:12`), et
    `TestPersistenceLayerIsolation` passe (8/8 relancés) malgré cet import.
  - Le point positif 0.7.4 « `tests/test_architecture.py` verrouille ces invariants » est donc
    exact pour `services/` et `mcp_adapter/` seulement.
  - Les invariants `domain/` et `api/` tiennent aujourd'hui (scan AST de ce re-audit : 0
    import interdit), mais sans garde effective.
  - Sans effet sur 7.3.3 : l'import porte sur le scellement des secrets, pas sur la base.
    Recoupe l'audit 01.
- **Remédiation** : remplacer les règles pytestarch par `_imports_of_layer` (déjà présent) pour
  `domain`, `api`, `infra`, `persistence`. Injecter la boîte de scellement dans
  `SqliteStoreRepository` depuis `bootstrap/`.

### [INFO] 18 — Port typé `Any` (nouveau, introduit par la remédiation)

- **Localisation** : `document-parser/domain/ports.py:436-450` (`GraphDriverPool.get -> Any`), ajouté par `39dcda5`.
- **Constat** : le port remplace l'annotation sous `TYPE_CHECKING` du pool concret d'`infra` (INFO 12 corrigé).
  Le driver est volontairement opaque ; il ne fait que transiter vers la fabrique de `GraphWriter`. La surface
  appartient à l'ingestion, dépréciée. 7.4.1 reste conforme.
- **Remédiation** : un alias opaque (`GraphDriver = NewType(...)` ou `Protocol` vide) si la surface survit à 0.8.0.

### [INFO] 19 — Nuances de nullabilité et double orthographe dans les contrats retypés (nouveau)

- **Localisation** :
  - `GraphNode.label` toujours émis, `null` hors éléments (`api/graph.py:50`, `:54`), contre
    `label?: string` côté TS (`features/analysis/graphApi.ts:28`) ;
  - `GraphProvenance` entièrement optionnel côté Python (`api/graph.py:31-39`), champs requis et
    non nuls côté TS (`graphApi.ts:9-17`) ;
  - `StoreConfigResponse` publie la même clé sous deux orthographes
    (`api/schemas.py:372-373`, `features/store/api.ts:23-24`).
- **Constat** : aucun effet à l'exécution, car le front tolère `null` (`GraphView.vue:153`, `:161`,
  `:231`). La double orthographe est documentée (`api/schemas.py:364-369`) et reflète des lignes
  existantes.
- **Remédiation** : `label?: string | null` côté TS. Normaliser `indexName` → `index_name` à
  l'écriture lors de la prochaine migration des stores, ou jamais si la surface disparaît en 0.8.0.

### [INFO] 20 — Une même absence, deux statuts (7.4.3 reste conforme)

- **Localisation** :
  - réponse 400 : `services/analysis_service.py:214`, `:238`, `:260`
    (`ValueError("Analysis not found")`) → `api/analyses.py:206-207`, `:230-231`, `:253-254` ;
  - réponse 404 : `api/analyses.py:195` et `services/document_tree_service.py:50`.
- **Constat** : préexistant. Le format `{"detail": …}` est uniforme ; c'est la normalisation des
  codes qui ne l'est pas sur trois routes legacy. Détail et remédiation dans le re-audit 05
  (reliquat du contrat d'erreur).

---

## Régressions et nouveaux couplages introduits par la remédiation

| Constat | Gravité | Localisation |
|---------|---------|--------------|
| Contrat OpenAPI de `GraphNode` appauvri (perd `id` / `group` / `label`) ; `config` toujours objet libre | Inclus dans le MAJ 7.4.2 | `api/schemas.py:76-77` |
| Front dépendant d'un défaut interne de persistence (`SUMMARIES_PAGE = 200`) | INFO 16 | `pages/DocsLibraryPage.logic.ts:17` |
| Port `GraphDriverPool.get -> Any` | INFO 18 | `domain/ports.py:436-450` |
| Nouvel import profond `pages/` → `features/analysis/api` (`fetchAnalysisSummaries`) | Dans INFO 3 | `pages/DocsLibraryPage.vue:212` |

Ce qui ne présente pas de couplage nouveau :
- Les nouveaux modules backend respectent les couches (scan AST) : `services/errors.py`,
  `chunk_errors.py`, `chunk_push_service.py`, `document_tree_service.py`, `domain/doc_tree.py`,
  `chunk_serialization.py`, `citation_match.py`, `read_budget.py`, `persistence/timestamps.py`,
  `infra/file_storage.py`, `pdf_inspector.py`, `ssrf_guard.py`, `mcp_adapter/sources_*.py`.
- Le handler d'erreurs garde FastAPI hors de `services/`.
- La garde SSRF est injectée dans `StoreService` comme un callable
  (`bootstrap/builder.py:163`, `services/store_service.py:328-334`), sans import d'`infra`.
- `DocumentNotFoundError` reste dans `services/navigation_errors.py` pour que le filtre MCP
  (`mcp_adapter/tool_errors.py:46`) continue de la voir. Les services chunk et analyse dépendent
  donc d'un module nommé « navigation » : c'est un nommage, pas un couplage de couche.

---

## Points positifs

- **Services découplés des adaptateurs, y compris en annotation.** 0 import `persistence` /
  `infra` dans `services/`, même sous `TYPE_CHECKING`. Une garde AST effective est posée, et
  les ports déclarent toutes les méthodes appelées.
- **Erreurs normalisées par construction.** Un handler, un format, le statut porté par
  l'erreur : le code HTTP ne dépend plus d'un libellé.
- **Frontière inter-features tenue sur quatre audits.** 12 arêtes, toutes par barrel ; 0 import
  profond ou de type ; un cycle de barrels rompu.
- **Miroirs TS sans signature d'index ni `Record<string, unknown>`** pour les deux surfaces
  retypées. `vue-tsc` confirme que le front ne lit aucune autre clé.
- **Docling, FastAPI et les bibliothèques PDF confinés.** La liste noire des services s'étend à
  `pdf2image` / `pypdfium2` ; les lectures PDF passent par `PdfInspector` / `PageRasterizer`.

---

## Verdict partiel : GO

Score **94 / 100** (≥ 80), **0 CRITICAL**, **1 MAJOR** (sous le seuil > 3), 0 MINOR, 18 INFO.

La remédiation corrige deux INFO (5 : statut selon le libellé ; 12 : services annotés sur des
repos concrets), rompt un cycle de barrels et type les deux surfaces de 7.4.2 côté code.
Mais l'OpenAPI publié, objet même de l'item et de l'entrée CHANGELOG, reste un objet libre, et
il régresse pour `GraphNode`. Le correctif tient en une ligne (annotation de retour de
`ProvidedKeysModel`) et un test ; il porte l'audit à **100 / 100**.

Suivi, non bloquant :
- INFO 16 : publier la troncature des résumés ou compter par document ;
- INFO 17 : remplacer les règles pytestarch aveugles par le scanner AST ;
- reconduits d'avant 0.8.0 : INFO 1, 11, 13, 14 et la fiche (15).

---

## Addendum — vérification post-correctifs (HEAD 3f1d1cb, 2026-11-03)

Vérification dans le code de la passe `a4d9679..3f1d1cb` (commit `13a5011` pour cet audit, avec `94fbfcb` et `3b1941f` en périphérie). Gates du coordinateur sur `3f1d1cb` : ruff et format OK, pytest **1723 passed, 19 skipped** ; eslint, vue-tsc OK, vitest 522 passed. Pas de run CI.

### Écart visé : [MAJ] 7.4.2 — schémas publiés comme objets libres

**Statut : fermé.**

- **Cause levée** : `ProvidedKeysModel._provided_keys_only` n'a plus d'annotation de retour (`document-parser/api/schemas.py:81-84`). La docstring (`:73-76`) dit pourquoi : `dict[str, Any]` publiait chaque sous-classe comme objet libre.
- **Contrat réellement servi**, vérifié sur l'application (`cd document-parser && uv run python -c "import main; main.app.openapi()…"`, pydantic du lock) :
  - `StoreConfigResponse` : `type: object`, `properties` = `index_name`, `indexName`, `database`, sans `additionalProperties` ;
  - `StoreResponse.config` = `{"$ref": "#/components/schemas/StoreConfigResponse"}` ;
  - `GraphNode` : 17 propriétés (`id`, `group`, `label`, `doc_id`, `provs`, `page_no`, `chunk_index`…), `required == ["id", "group"]`, sans `additionalProperties`. La régression relevée au re-audit (perte de `id` / `group` / `label`) est réparée ;
  - `GraphProvenance` : `order`, `page_no`, `bbox_l`, `bbox_t`, `bbox_r`, `bbox_b`, `coord_origin`, `charspan_start`, `charspan_end`.
- **Test** : `document-parser/tests/test_openapi_contract.py`, 5 tests passés en local. Il lit `app.openapi()` et non le schéma de validation. Il asserte les propriétés et le `required` des trois modèles et la `$ref` de `config`. `test_no_response_publishes_a_free_object` (`:77-88`) parcourt **toutes** les réponses de toutes les routes, `$ref` suivies, et échoue sur tout objet libre (`additionalProperties: true` sans `properties`). C'est plus que la remédiation demandée : la règle 7.4.2 est désormais gardée pour toute nouvelle route.
- **Vérification complémentaire** : un scan des réponses 2xx à la recherche d'un schéma `{}` (le cas `Any`, que le test ne vise pas) ne trouve que des réponses sans modèle Pydantic. Ce sont les 204 et les deux réponses binaires `GET /api/documents/{doc_id}/export` et `/preview`, publiées avec le schéma JSON vide par défaut de FastAPI, comme avant la passe. Aucun champ `Any` dans un modèle de réponse. Hors périmètre de 7.4.2 (pas de schéma Pydantic) ; observation, non comptée.
- **JSON servi** : inchangé, puisque le sérialiseur garde les seules clés fournies.
- **CHANGELOG** : la puce `CHANGELOG.md:32` (« now typed in the OpenAPI schema … and a test keeps every response schema typed ») est désormais exacte. Le re-audit l'avait signalée à l'audit 11 comme inexacte.

### Autres changements de la passe

- `94fbfcb` : les erreurs document et export passent par `ServiceError` et le handler unique (7.4.3 renforcé). Le reliquat 400 / 404 des routes legacy d'analyse (INFO 20) est inchangé.
- `3b1941f` : la variable de chemin de la route de restore devient `document_version_id`. L'URL ne change pas, et le front construit l'URL lui-même (`frontend/src/features/document/api.ts:81`) : aucun contrat client touché.

**Régressions** : aucune.

### Score recalculé

| Lecture | Re-audit (`a4d9679`) | Post-correctifs (`3f1d1cb`) |
|---------|----------------------|-----------------------------|
| Même lecture qu'en 0.7.4 (contrat publié) | 94 (33 / 35) | **100** (35 / 35) |
| Lecture « déclarations Python » | 100 | 100 |

| Métrique | Re-audit | Post-correctifs |
|----------|----------|-----------------|
| Items conformes | 15 / 16 | **16 / 16** |
| Score | 94 / 100 | **100 / 100** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 1 | **0** |
| Écarts MINOR | 0 | 0 |
| Écarts INFO | 18 | 18 (inchangées ; la régression `GraphNode` était comptée dans le MAJ) |

### Verdict partiel après correctifs : GO

Score **100 / 100** dans les deux lectures, 0 CRITICAL, 0 MAJOR, 0 MINOR, 18 INFO. Le suivi non bloquant est inchangé : INFO 16 (troncature des résumés), INFO 17 (règles pytestarch), INFO 1, 11, 13, 14 et la fiche (15).

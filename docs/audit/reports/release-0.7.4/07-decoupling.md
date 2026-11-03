# Rapport d'audit : Découplage

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `release/0.7.4` @ `1de1929` (= tag `v0.7.3` + 2 commits README)
**Baseline** : `release-0.7.3-reaudit/07-decoupling.md` (`e01fd95`, 94/100, GO, 0 CRIT, 1 MAJ, 12 INFO) ;
premier audit `release-0.7.3/07-decoupling.md` (`02adc68`, 89/100)

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 15 |

Détail du calcul : somme des poids = 3+3+2+2+2 (7.1) + 2+3+2+2 (7.2) + 2+3+2+2 (7.3) + 2+2+1 (7.4)
= **35**. Seul l'item **7.4.2** (poids 2) est non conforme. Poids conformes = 33.
`33 / 35 * 100 = 94,29` → **94**.

### Périmètre du différentiel

`git diff e01fd95..1de1929` (re-audit 0.7.3 → HEAD) : 14 fichiers, dont **2 seulement** dans le
périmètre de la fiche (`document-parser/` hors tests, `frontend/src/`) :

| Fichier | Nature | Effet sur l'audit 07 |
|---------|--------|----------------------|
| `frontend/src/features/mcp-config/ui/McpConfigSection.vue:410-411` | commentaire JSDoc de `localOnly` (#audit-08) | aucun (pas d'import, pas d'appel) |
| `frontend/src/shared/i18n.ts:415-416`, `:1137-1138` | libellé `settings.mcp.localOnly` FR/EN (#audit-08) | aucun |

Le reste (`release-gate.yml`, `.trivyignore.yaml`, `CHANGELOG.md`, `README.md`, GIF, rapports
d'audit) est hors périmètre. **Aucun** fichier de `api/`, `domain/`, `services/`,
`persistence/`, `infra/`, `bootstrap/`, `mcp_adapter/`, `main.py`, `frontend/src/features/*/`
(hors le commentaire ci-dessus), `pages/`, `app/`, `shared/types.ts`, `shared/ui/` ni
`frontend/eslint.config.js` n'a changé. Malgré cela, **chaque écart et chaque preuve ont été
revérifiés sur l'arbre `1de1929`** (citations ci-dessous), et un balayage complet a été rejoué
pour chercher des écarts antérieurs non relevés — il en sort 3 nouveaux INFO et une
rectification.

### Mesures (analyse statique du working tree `1de1929`)

| Mesure | Re-audit 0.7.3 (`e01fd95`) | 0.7.4 (`1de1929`) |
|--------|----------------------------|-------------------|
| Imports feature → feature (hors tests) | 13, tous via barrel | **13, tous via barrel** (=) |
| Imports profonds feature → internes d'une autre feature | 0 | **0** |
| Imports `import type` feature → feature | 0 | **0** |
| `node_modules/.bin/eslint src` | exit 0 | **exit 0** |
| `node_modules/.bin/vue-tsc --noEmit` | exit 0 | **exit 0** |
| Types définis dans une feature et consommés par une autre feature | 0 | **0** |
| `shared/` → internes de features | 2 (`AppSidebar.vue`) | 2 (=) |
| Imports profonds `pages/` + `app/` → internes de features | 52 | **52** (49 `pages/` + 3 `app/`) |
| Stores Pinia qui consomment un autre store | 2 (actions seules) | 2 (=, actions seules) |
| `from docling` / `import docling` dans `services/`, `domain/`, `api/`, `mcp_adapter/` | 0 | 0 |
| `fastapi` / `starlette` hors `api/`, `main.py`, `bootstrap/mcp_mount.py`, `infra/rate_limiter.py` | 0 | 0 |
| Imports runtime `services/` → `infra/` ou `persistence/` | 0 (TYPE_CHECKING seul) | 0 (3 + 7 sous `TYPE_CHECKING`) |
| Champs `dict` / `extra="allow"` dans un schéma de **réponse** | 2 | 2 (=) |
| SQL / `get_connection` hors `persistence/` | non mesuré | **2 sites** (`main.py:133-134`, `bootstrap/factories.py:130-134`) — nouveau INFO 13 |
| Appels HTTP hors `api.ts` / `graphApi.ts` / `shared/api/http.ts` | non mesuré | **2** (`feature-flags/store.ts:159`, `document/ui/DownloadDropdown.vue:133`) — nouveau INFO 14 |
| `tests/test_architecture.py` (garde-fous de couches) | — | **39 passed** |

Commandes de la fiche rejouées :
- 7.2.2 (`grep "from.*features/" frontend/src/features/`) → 13 lignes hors tests, toutes vers
  `@/features/<nom>` ; complété par un scan exhaustif des imports `@/` et relatifs de
  `frontend/src/` (hors `*.test.*`, `__tests__`) ;
- 7.2.4 (`grep useDocumentStore|useAnalysisStore|...`) → seul `reasoning/store.ts:3,22` ; la
  commande ne liste pas `useFeatureFlagStore`, d'où un scan de tous les `defineStore`
  (cf. INFO 15) ;
- 7.3.2 (`grep "from docling|import docling" services/`) → vide ;
- 7.4.2 (`grep "-> dict|-> Any|Dict[str, Any]" api/`) → vide (l'écart est au niveau *champ*).

---

## Statut par item

| Item | Poids | Statut 0.7.4 | Statut vs 0.7.3 (re-audit) | Preuve (arbre `1de1929`) |
|------|-------|--------------|----------------------------|--------------------------|
| 7.1.1 REST-only front/back | 3 | Conforme | = | Client HTTP unique `frontend/src/shared/api/http.ts:5` (`apiFetch`), appelé par 11 `features/*/api.ts` (ex. `mcp-config/api.ts:1,17`) ; aucun import croisé front ↔ back ni fichier/DB partagé (seule mention de `frontend/` côté back : un commentaire, `mcp_adapter/apps.py:81`). |
| 7.1.2 Types TS = schémas Pydantic | 3 | Conforme | = | Échantillon revérifié champ à champ : `AnalysisResponse` (`api/schemas.py:127-142`) ↔ `Analysis` (`shared/types.ts:65-81`) ; `AnalysisSummaryResponse` (`:145-157`) ↔ `AnalysisSummary` (`shared/types.ts:84-96`, `Pick<Analysis>`) ; `McpConfigResponse` (`:772-783`) ↔ `McpConfigView` (`features/mcp-config/types.ts:6-16`) ; `ConfigSource` `shared/types.ts:5` ↔ `domain/app_config.py:17`. Seul champ orphelin : `stores?` (INFO 9). |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | Conforme | = | 11 `features/*/api.ts` ; toutes les requêtes passent par `apiFetch` ou `fetch` global, donc mockables. Deux appels hors `api.ts` relevés (INFO 14), sans effet sur la mockabilité. |
| 7.1.4 Back testable sans front | 2 | Conforme | = | 16 fichiers de test utilisent `TestClient`/`AsyncClient`, ex. `tests/test_mcp_config_api.py:11,75`. |
| 7.1.5 Pas de logique métier dupliquée | 2 | Conforme | = | Gardes UX seulement : `features/document/store.ts:75-77` (taille, alimentée par `/api/health`), bornes MCP `features/mcp-config/types.ts:58-62` (INFO 4). Le backend reste l'autorité (`domain/mcp_config.py:29-35`, `domain/app_config.py:99`). |
| 7.2.1 Feature = store + api + ui | 2 | Conforme | = | Composition revérifiée pour les 13 features ; les exceptions sont structurelles (`feature-flags` sans UI ni `api.ts`, `settings` sans `api.ts`, `store` sans `store.ts`, `search` sans `ui/`), inchangées. `reasoning` n'a pas de barrel (complément INFO 3). |
| 7.2.2 Frontière barrel + ESLint | 3 | Conforme | = | Règle `frontend/eslint.config.js:28-55` ; 13 imports feature → feature, tous vers un barrel (ex. `settings/ui/SettingsPanel.vue:112-114`, `document/ui/DocumentUpload.vue:49`) ; 0 import profond ; `eslint src` exit 0. |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | Conforme | = (MAJ levé au re-audit, **non régressé**) | `ConfigSource` en `shared/types.ts:5`, importé par `features/admin-config/types.ts:1` et `features/mcp-config/types.ts:1` ; barrels : seuls types réexportés `analysis/index.ts:2` (`AnalysisOutcome`, `BatchLaunch`) et `feature-flags/index.ts:1` (`FeatureFlag`), consommés uniquement par des pages (`pages/DocWorkspacePage.logic.ts:9`, `pages/DocsLibraryPage.vue:214`) ; `StoreInfo` (`features/store/api.ts:4`) consommé seulement par `pages/IngestLaunchDialog.vue:114`, `pages/DocIngestTab.logic.ts:17`. |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | Conforme | = | Scan de tous les `defineStore` : `features/reasoning/store.ts:22` n'appelle que l'action `focusElement` (`:51`, `:55`) ; `features/admin-config/store.ts:80,95` n'appelle que l'action `reload`. |
| 7.3.1 Repos → objets du domaine | 2 | Conforme | = | Scan AST des méthodes publiques de `persistence/` : aucun `Row`/`Any` ; les 4 `dict` retournés sont des index typés (`document_repo.py:106` `dict[str, Document]`, `analysis_repo.py:137` `dict[str, str]`, `app_settings_repo.py:16`, `document_store_link_repo.py:82` `dict[str, int]`) ; `document_repo.py:99-104` (`-> Document \| None`, `_row_to_document`). |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme | = | Commande fiche vide ; `docling*` importé uniquement par 8 modules de `infra/` (dont `infra/docling_importer.py:7`) ; `services/analysis_service.py:180` passe par le port (`asyncio.to_thread(self._docling_importer.deserialize, ...)`) ; `tests/test_architecture.py` (`_SERVICES_FORBIDDEN_EXTERNALS`, `:300-304`) verrouille `docling`/`docling_core`/`fastapi` hors services — 39 tests verts. |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | Conforme | = (constat complété) | Aucun SQL ni `get_connection` dans `services/`, `api/`, `domain/`, `infra/`, `mcp_adapter/` ; imports `persistence` des services sous `TYPE_CHECKING` seulement (INFO 12). **Nouveau** : deux requêtes SQL ANSI dans le composition root (`main.py:133-134`, `bootstrap/factories.py:130-134`), antérieures à 0.7.0 (INFO 13). |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | Conforme | = | `fastapi`/`starlette` hors `api/` et `main.py` : seulement `bootstrap/mcp_mount.py:41-42,118` et `infra/rate_limiter.py:18-19` (INFO 7) ; `mcp_adapter/` n'importe ni `api`, ni `fastapi`, ni `starlette`, ni `infra`, ni `persistence`. |
| 7.4.1 Ports = signatures claires, types domaine | 2 | Conforme | = | `domain/ports.py:86-89` (`DoclingDocumentImporter.deserialize -> ConversionResult`), `:423` (`PageRasterizer`), `:449` (`PageTextReader`). Les `dict[str, Any]` de `DocumentTreeReader` (`:389-417`) portent le JSON Docling sérialisé — compromis déjà tracé par les audits 01 et 02 (0.7.3). |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **Non conforme [MAJ]** | = (inchangé, 3ᵉ release) | `api/schemas.py:349` (`StoreResponse.config: dict`, classe `:334`) ; `api/graph.py:32` (`model_config = {"extra": "allow"}`, classe `:27`). |
| 7.4.3 Format de réponse cohérent | 1 | Conforme | = | `{"detail": ...}` uniforme (ex. `api/analyses.py:84-85`, `infra/rate_limiter.py:82-85`) ; erreurs typées `services/config_overrides.py:25-34` ; le 503 JSON-RPC de `bootstrap/mcp_mount.py:166` relève du protocole MCP, pas de l'API REST. |

---

## Écarts constatés

### [MAJ] `dict` non typé et modèle ouvert dans des schémas de réponse (item 7.4.2) — statut vs 0.7.3 : **inchangé**

- **Localisation** : `document-parser/api/schemas.py:349` (`StoreResponse.config: dict`,
  classe en `:334`) ; `document-parser/api/graph.py:32` (`GraphNode` →
  `model_config = {"extra": "allow"}`, classe en `:27`). Miroirs front :
  `frontend/src/features/store/api.ts:23` (`config: Record<string, unknown>`),
  `frontend/src/features/analysis/graphApi.ts:36` (`[key: string]: unknown`).
- **Constat** : revérifié sur `1de1929`, identique (mêmes lignes qu'au re-audit 0.7.3). Le
  contrat est opaque des deux côtés :
  - `StoreResponse.config` est le config store polymorphe. Le service n'en valide que
    `index_name` (accepte aussi `indexName`, `services/store_service.py:129-140`) et lit
    `database` pour Neo4j (`services/store_backend_resolver.py:148`) ; tout autre clé saisie
    est persistée et renvoyée telle quelle.
  - `GraphNode` accepte des champs arbitraires alors que l'adaptateur n'en émet qu'un
    ensemble fini par `group` (`element`, `page`, `chunk`, `document` —
    `infra/neo4j/queries.py:99-130`, `:190-197`).
  - En marge : `GraphNode`/`GraphEdge`/`GraphResponse` héritent de `BaseModel` et non de
    `_CamelModel` (`api/graph.py:27,35,43` vs `api/schemas.py:45`) ; c'est la seule réponse
    REST en snake_case (`doc_id`, `node_count`), reflétée telle quelle côté front
    (`graphApi.ts:48-52`). Cohérent des deux côtés, donc non compté en 7.4.3.

  Les deux surfaces appartiennent à l'ingestion, dépréciée (`CHANGELOG.md:27-29`,
  `docs/architecture.md:84-85`) et dont la suppression est annoncée pour 0.8.0. Aucun nouveau
  schéma de réponse non typé depuis 0.7.3.
- **Règle violée** : 7.4.2 (poids 2) — « pas de `dict` ou `Any` dans les responses ».
- **Remédiation** :
  - **Option A, recommandée pour 0.7.4 (patch)** : accepter l'écart et le solder par la
    suppression de l'ingestion en 0.8.0. Ajouter au plan 0.8.0 une case explicite :
    « `api/graph.py` et `StoreResponse` supprimés ».
  - **Option B, si l'on veut 100/100 dès 0.7.4** :
    - remplacer `config: dict` par un modèle `StoreConfigResponse(index_name: str, database: str | None = None)`, en normalisant `indexName` → `index_name` à la lecture ;
    - remplacer `extra="allow"` par les champs explicites émis par `infra/neo4j/queries.py` (optionnels, ou union discriminée par `group`) ;
    - aligner `features/store/api.ts:23` et `graphApi.ts:20-37`.
  - **Effort** : S à M (deux schémas, deux types TS, tests `test_api_endpoints`/stores/graph).
  - **Risque de régression** : modéré, sur une surface dépréciée. Des lignes `stores` contenant
    d'autres clés ne seraient plus renvoyées, et un champ cytoscape oublié serait filtré
    silencieusement (Pydantic ignore les extras par défaut).

### [INFO] Constats reconduits — statut vs 0.7.3 revérifié sur `1de1929`

| # | Constat | Localisation vérifiée | Statut vs 0.7.3 |
|---|---------|-----------------------|-----------------|
| 1 | `shared/ui` n'est pas une feuille : `AppSidebar.vue` importe deux stores de features et est réexporté par le barrel consommé par `mcp-config` et `settings` | `frontend/src/shared/ui/AppSidebar.vue:55-56` (`../../features/feature-flags/store`, `../../features/ingestion/store`), `shared/ui/index.ts:1` ; seul consommateur de `AppSidebar` : `app/App.vue:49` ; consommateurs du barrel : `features/mcp-config/ui/McpConfigSection.vue:376`, `features/settings/ui/SettingsPanel.vue:115` | = (toujours ouvert ; à traiter au plus tard avec la suppression de `ingestion/store` en 0.8.0) |
| 2 | Cycle de barrels `document` ↔ `analysis` (et `document` ↔ `chunks`) | `features/document/ui/DocumentUpload.vue:49`, `document/ui/DocumentActionsMenu.vue:41`, `document/store.ts:5-6` ; sens inverse `analysis/ui/AnalysisPanel.vue:61`, `analysis/ui/StructureViewer.vue:64`, `chunks/store.ts:5` ; barrels `document/index.ts:3,5`, `analysis/index.ts:6` | = |
| 3 | Pages et shell importent en profondeur les internes de features (hors 7.2.2) | 49 imports `pages/` + 3 `app/` (`app/App.vue:52,54`, `app/router/index.ts:3`) ; incohérence barrel/profond dans un même fichier : `pages/DocsLibraryPage.vue:211` (barrel) vs `:213-214` (profond). **Complément** : la feature `reasoning` n'a pas de `index.ts` ; ses 3 consommateurs (`pages/DocParseTab.vue:188-190`) ne peuvent donc qu'importer en profondeur | = (décompte identique : 52) |
| 4 | Bornes MCP et règle d'hôte recopiées côté front, non publiées dans l'OpenAPI | `features/mcp-config/types.ts:58-62` vs `domain/mcp_config.py:29-35` ; `features/mcp-config/client.ts:41-46` (`hostAllowed`) ; `api/schemas.py:803-814` sans `Field(ge, le)`, contrairement à `:691-695` (reasoning). Choix documenté pour la réponse (`api/schemas.py:773-774` : « No bounds on the fields: an env value outside the panel's bounds is still the effective one ») — l'argument ne vaut pas pour la requête `McpConfigUpdateRequest` | = |
| 5 | Code HTTP dérivé du texte d'une exception (import d'analyse) | `api/analyses.py:84` (`str(e).startswith("Document not found:")`) ; `services/analysis_service.py:173` (`ValueError`), `:176` (`RuntimeError` non mappé → 500) ; `DocumentNotFoundError` disponible en `services/navigation_errors.py:24` | = |
| 6 | Contrat d'URL backend → SPA (deep links MCP) | `services/citation_service.py:292` ; `frontend/src/app/router/routes.ts:39-48` | **Constat rectifié** : le rapport 0.7.3 le disait « non testé ». C'est inexact : le format est épinglé **des deux côtés** depuis `234d805` (2026-09-24, antérieur à l'audit 0.7.3), avec la même URL. Côté front : `frontend/src/app/router/router.test.ts:69-80` (`/analyses/an-1?ref=%23%2Ftexts%2F4&page=2` → props `{id, focusRef, page}`). Côté back : `document-parser/tests/test_navigation_service.py:160-162`, `tests/test_source_service.py:312`, `tests/test_mcp_sources_app.py:137`. Les deux tests ont été rejoués : 6/6 et 4/4 verts. **Risque résiduel** : les deux suites ont chacune leur fixture, sans source commune ; un renommage côté front ferait échouer le test front, sans signal côté back. Remédiation optionnelle : une fixture JSON partagée (`/analyses/{id}?ref=&page=`) lue par les deux suites. |
| 7 | Couplage framework HTTP étendu à `bootstrap/mcp_mount.py` ; façade MCP typée `Any` | `bootstrap/mcp_mount.py:41-42` (imports `starlette`), `:118` (`app.router.routes.extend`) ; `mcp_adapter/__init__.py:22` (`**kwargs: Any) -> Any`) ; `infra/rate_limiter.py:18-19` | = |
| 8 | Deux casses pour la notion de page ; DTO wire anonyme | `features/document/api.ts:37-47` (type inline `{ pageNumber; width; height }`, remappé en `page_number`) ; `shared/types.ts:145-150` (`Page`) ; `api/schemas.py:119` (`PageSizeResponse`) | = |
| 9 | Champ de contrat orphelin `Document.stores?` | `frontend/src/shared/types.ts:45`, absent de `DocumentResponse` (`api/schemas.py:100-116`) et lu nulle part dans `frontend/src` | = |
| 10 | Pré-validation de taille de fichier côté front (garde UX) | `features/document/store.ts:75-77` | = (aucune action requise) |
| 11 | Règle ESLint plus étroite que « barrel uniquement » (ne couvre ni `shared/`, ni `pages/`, ni les chemins à deux segments, ni les imports de type) | `frontend/eslint.config.js:28-55` | = ; le garde-fou « types inter-features » proposé au re-audit 0.7.3 n'est pas posé (0 import de type inter-features à ce commit, la règle passerait sans erreur) |
| 12 | Services annotés avec des repos SQLite concrets (sous `TYPE_CHECKING`) | `services/store_service.py:23-25,148-150`, `services/chunk_service.py:43-44,159-160`, `services/version_service.py:32,87`, `services/store_backend_resolver.py:43,81` ; Protocols existants `domain/ports.py:128` (`StoreRepository`), `:142` (`DocumentStoreLinkRepository`) | = |

### [INFO] 13 — SQL brut et `get_connection` dans le composition root (7.3.3 considéré conforme) — statut vs 0.7.3 : **nouveau constat, écart antérieur**

- **Localisation** :
  - `document-parser/bootstrap/factories.py:22` (import `persistence.database.get_connection`) et `:130-135` (`check_store_secret_key`) : `SELECT COUNT(*) AS n FROM stores WHERE connection_password_sealed IS NOT NULL`, puis `row["n"]` ;
  - `document-parser/main.py:40` (import) et `:133-134` (`/api/health`) : `SELECT 1`.
- **Constat** : ces deux sites sont les seuls endroits hors `persistence/` à ouvrir une connexion
  et à exécuter du SQL. Ils sont présents à l'identique depuis `v0.7.0` au moins
  (`git show v0.7.0:document-parser/bootstrap/factories.py`, l. 124). Le rapport 0.7.0 affirmait
  que « `aiosqlite` [est] cantonné à `persistence/` — les seules mentions hors couche sont des
  commentaires ». C'est vrai pour l'import `aiosqlite`, mais pas pour l'usage de la connexion.
  Le SQL est ANSI : un changement SQLite → PostgreSQL qui conserverait la façade
  `get_connection` dans `persistence/database.py` ne toucherait pas ces lignes, d'où 7.3.3
  jugé conforme.

  La requête de `factories.py` connaît en revanche le **schéma** (table `stores`, colonne
  `connection_password_sealed`) et contourne le port `StoreRepository`
  (`domain/ports.py:128`) : un changement de schéma devrait modifier `bootstrap/`. Une lecture
  stricte de 7.3.3 (« ne modifier que `persistence/` ») ferait passer l'item en non conforme
  (−6 pts). Ce n'est pas retenu, car le composition root est par nature le lieu du câblage
  de la base.
- **Remédiation** :
  - ajouter `count_sealed_passwords() -> int` à `SqliteStoreRepository` (et au Protocol), puis
    l'appeler depuis `check_store_secret_key` ;
  - exposer `persistence.database.ping() -> bool` pour le health check.

  Effort S, risque faible (couvert par les tests de boot et de health).

### [INFO] 14 — Deux appels HTTP hors des modules `api.ts` (7.1.3 considéré conforme) — statut vs 0.7.3 : **nouveau constat, écart antérieur**

- **Localisation** :
  - `frontend/src/features/feature-flags/store.ts:3,159` : `apiFetch<HealthResponse>('/api/health')` appelé directement dans le store. La feature n'a pas d'`api.ts`.
  - `frontend/src/features/document/ui/DownloadDropdown.vue:132-133` : `fetch(url)` brut dans un composant UI. Il contourne `apiFetch` ; seule l'URL vient de `getExportUrl` (`features/document/api.ts:50`).
- **Constat** : ces deux cas sont antérieurs à 0.7.3 (`git log -L` : `dc87383`, 2026-08-08 ;
  `56df3b4`, 2026-09-22). Le front reste mockable, car les deux passent par `fetch`, global ou
  via `apiFetch`. Mais le point d'injection n'est plus uniquement le module `api.ts` de la
  feature : un `vi.mock('../api')` ne suffit pas à isoler `DownloadDropdown`. Ce composant
  gère aussi lui-même le statut HTTP (404 → message « JSON indisponible », `:135-143`), une
  logique de transport qui devrait vivre dans `api.ts`.
- **Remédiation** :
  - déplacer la requête dans `features/document/api.ts`, par exemple `downloadExport(docId, format, analysisId): Promise<Blob>` qui lève une erreur typée sur 404 ;
  - créer `features/feature-flags/api.ts` avec `fetchHealth()`.

  Effort S, risque faible.

### [INFO] 15 — Commandes de vérification de la fiche 07 incomplètes — statut vs 0.7.3 : **nouveau constat (fiche)**

- **Localisation** : `docs/audit/audits/07-decoupling.md:55-56` (7.2.4) et `:61-62` (7.4.2).
- **Constat** :
  - La commande 7.2.4 ne cherche que 5 stores (`useDocumentStore|useAnalysisStore|useChunkingStore|useHistoryStore|useSettingsStore`). Elle ignore les 8 autres stores existants, dont `useFeatureFlagStore`, pourtant consommé par un autre store (`features/admin-config/store.ts:80,95`) ; ce consommateur n'apparaît qu'avec un scan exhaustif.
  - La commande 7.4.2 ne voit que les annotations de retour (`-> dict`), jamais les champs. L'unique écart 7.4.2 lui est donc invisible depuis trois releases.

  Le résultat de cet audit n'en dépend pas, car les deux scans ont été complétés ici. Mais un
  audit qui s'en tiendrait aux commandes de la fiche conclurait à tort à 0 écart sur 7.4.2.
- **Remédiation** :
  - 7.2.4 : remplacer la liste par un motif générique, par exemple `grep -rn "use[A-Z][A-Za-z]*Store()" frontend/src/features/*/store.ts` ;
  - 7.4.2 : ajouter `grep -nE "^\s+\w+: (dict|Any)\b|extra.*allow" document-parser/api/*.py`.

---

## Delta vs 0.7.3

Score : **94 (re-audit 0.7.3) → 94 (=)** ; 89 (1er audit 0.7.3) → 94 (+5).
Items conformes : 15/16 → 15/16.

| Écart baseline (re-audit 0.7.3) | Statut 0.7.4 |
|---------------------------------|--------------|
| [MAJ] 7.4.2 `StoreResponse.config: dict` / `GraphNode extra=allow` | **Toujours présent** (`api/schemas.py:349`, `api/graph.py:32`) — 3ᵉ release consécutive ; extinction prévue avec l'ingestion en 0.8.0. |
| [MAJ] 7.2.3 `ConfigSource` (levé au re-audit 0.7.3) | **Toujours levé** (`shared/types.ts:5`) ; aucun nouveau type inter-features. |
| [CRIT] 7.2.2 imports croisés (levé en 0.7.0) | **Toujours levé** : 13 imports feature → feature, tous via barrel ; `eslint src` exit 0. |
| INFO 1-5, 7-12 | Reconduits à l'identique, localisations revérifiées (aucune ligne n'a bougé). |
| INFO 6 (deep link « non testé ») | **Rectifié** : testé des deux côtés depuis `234d805` ; reste INFO pour l'absence de fixture commune. |

Nouveaux constats 0.7.4 : 0 CRIT, 0 MAJ, 0 MIN, 3 INFO. Ce sont des écarts antérieurs non
relevés jusqu'ici (13 : SQL dans le composition root ; 14 : HTTP hors `api.ts`), plus une
dérive de la fiche (15). Aucune régression : le différentiel de code 0.7.3 → 0.7.4 se limite à
un commentaire et deux libellés i18n.

---

## Points positifs

- **Frontière inter-features stable sur trois audits.** 13 arêtes feature → feature, toutes
  par barrel ; 0 import profond, 0 import de type inter-features ; ESLint et `vue-tsc` propres.
  Le correctif `ConfigSource` du re-audit 0.7.3 tient (`shared/types.ts:5`).
- **Couches backend propres à l'exécution.** Un scan AST des imports montre que :
  - `services/` ne dépend de `infra/` et `persistence/` que sous `TYPE_CHECKING` ;
  - `api/` n'importe ni `infra/` ni `persistence/` ;
  - `mcp_adapter/` ne voit que `services/` et `domain/` ;
  - `domain/` n'importe aucune autre couche.

  `tests/test_architecture.py` verrouille ces invariants : 39 tests verts.
- **Docling confiné à `infra/`.** 8 modules `infra/` l'importent, aucun ailleurs ; l'import
  d'analyse passe par le port `DoclingDocumentImporter` (`domain/ports.py:86-89`), y compris
  dans le thread de travail (`services/analysis_service.py:180`).
- **Contrats HTTP typés de bout en bout hors ingestion.** Tous les endpoints JSON ont un
  `response_model` ; les seules routes sans en avoir renvoient un binaire (`api/documents.py:133`
  export, `:164` preview) ou un 204 (`api/stores.py:167,188`).
- **Contrat de deep link testé en miroir** des deux côtés (cf. INFO 6 rectifié). C'est une
  meilleure situation que celle décrite en 0.7.3.
- **Erreurs normalisées** : `{"detail": ...}` partout, y compris le rate limiter
  (`infra/rate_limiter.py:82-85`) ; les familles d'erreurs typées portent leur `http_status`
  (`services/config_overrides.py:25-34`, `services/navigation_errors.py:24`).

---

## Verdict partiel : GO

Score de compliance **94/100** (≥ 80), **0 CRITICAL**, **1 MAJOR** (sous le seuil master de
> 3), 0 MINOR, 15 INFO. Le découplage de la 0.7.4 est celui de la 0.7.3 : aucun fichier de code
du périmètre n'a changé hors un commentaire et deux libellés i18n. La revérification complète
ne trouve aucune régression. Elle ajoute trois observations antérieures (SQL dans le
composition root, deux appels HTTP hors `api.ts`, commandes de fiche incomplètes) et corrige
un constat inexact du rapport précédent (deep links testés).

Suivi (non bloquant) :
1. [MAJ] 7.4.2 : soit solder avec la suppression de l'ingestion en 0.8.0, à acter dans le plan
   0.8.0 ; soit typer `StoreResponse.config` et `GraphNode`, ce qui donne +6 pts (100/100).
2. Avant 0.8.0 :
   - sortir `AppSidebar.vue` de `shared/ui` (INFO 1) ;
   - étendre la règle ESLint à `src/shared/**` (INFO 11) ;
   - router les deux appels HTTP par `api.ts` (INFO 14) ;
   - passer la requête de `check_store_secret_key` par `StoreRepository` (INFO 13).
3. Mettre à jour les commandes 7.2.4 et 7.4.2 de la fiche (INFO 15).

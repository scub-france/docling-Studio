# Rapport d'audit : Decouplage

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68
**Baseline** : `release-0.7.0-reaudit/07-decoupling.md` (94/100, GO, 1 MAJ) et `release-0.7.0/07-decoupling.md` (80/100, NO-GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 14 / 16 |
| Score | 89 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 12 |

Detail du calcul : somme des poids = 35 ; non conformes : 7.2.3 (poids 2) et
7.4.2 (poids 2) = 4. Poids conformes = 31. `31 / 35 * 100 = 88,57` -> **89**.

| Item | Poids | Statut 0.7.3 | Evolution vs re-audit 0.7.0 |
|------|-------|--------------|-----------------------------|
| 7.1.1 REST-only front/back | 3 | Conforme | = |
| 7.1.2 Types TS = schemas Pydantic | 3 | Conforme | = |
| 7.1.3 Front mockable (api.ts par feature) | 2 | Conforme | = |
| 7.1.4 Back testable sans front (TestClient) | 2 | Conforme | = |
| 7.1.5 Pas de logique metier dupliquee | 2 | Conforme | = |
| 7.2.1 Feature = store + api + ui | 2 | Conforme | = |
| 7.2.2 Frontiere barrel public + ESLint no-restricted-imports | 3 | Conforme | = |
| 7.2.3 Types partages dans `shared/types.ts` | 2 | **Non conforme [MAJ]** | **regression** (nouveau type `ConfigSource`) |
| 7.2.4 Store n'accede pas au state d'un autre store | 2 | Conforme | = |
| 7.3.1 Repos retournent des objets du domaine | 2 | Conforme | = |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme | = |
| 7.3.3 Changement de DB confine a `persistence/` | 2 | Conforme | = |
| 7.3.4 Changement HTTP confine a `api/` + `main.py` | 2 | Conforme | = |
| 7.4.1 Ports = signatures claires + types domaine | 2 | Conforme | = |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **Non conforme [MAJ]** | inchange (dette reportee) |
| 7.4.3 Format de reponse coherent | 1 | Conforme | = |

### Mesures (analyse statique du working tree)

| Mesure | 0.7.0 re-audit (`94eec28`) | 0.7.3 (`02adc68`) |
|--------|----------------------------|-------------------|
| Imports feature -> feature (hors tests) | 10, tous via barrel | **14, tous via barrel** |
| Imports profonds feature -> internes d'une autre feature | 0 | **0** |
| `eslint src` — erreurs `no-restricted-imports` | 0 | **0** (exit 0) |
| Imports profonds `pages/` + `app/` -> internes de features (hors perimetre 7.2.2) | 55 | 58 |
| `shared/` -> internes de features | 2 (`AppSidebar.vue`) | 2 (inchange, mais desormais importe par 2 features via `@/shared/ui`) |
| Types definis dans une feature et consommes par une autre | 0 | **1** (`ConfigSource`) |
| `from docling` / `import docling` dans `services/`, `domain/`, `api/`, `mcp_adapter/` | 0 | 0 |
| `fastapi`/`starlette` dans `services/` ou `domain/` | 0 | 0 |
| Champs `dict` / `extra="allow"` dans un schema de **reponse** | 2 | 2 (inchange) |
| Nouveaux endpoints HTTP avec `response_model` Pydantic + type TS correspondant | — | 7 / 7 |
| Imports `api.*` / `fastapi` / `infra` / `persistence` depuis `mcp_adapter/` | — | 0 |

Commandes de la fiche executees : 7.3.2 (`grep "from docling|import docling" services/`) -> vide ;
7.4.2 (`grep "-> dict|-> Any|Dict[str, Any]" api/`) -> vide (les ecarts 7.4.2 sont au
niveau *champ*, invisibles pour cette commande, cf. ci-dessous) ; 7.2.2 complete par un
scan exhaustif des imports relatifs et `@/` de `frontend/src/` (hors tests) et par
`node_modules/.bin/eslint src`.

---

## Ecarts constates

### [MAJ] Type partage `ConfigSource` defini dans la feature `admin-config` et consomme par `mcp-config` (item 7.2.3)

- **Localisation** : `frontend/src/features/admin-config/types.ts:2` (definition),
  reexporte par `frontend/src/features/admin-config/index.ts:3`, consomme par
  `frontend/src/features/mcp-config/types.ts:1` et `:12`.
- **Constat** : `export type ConfigSource = 'env' | 'db'` vit dans la feature
  `admin-config`. La nouvelle feature `mcp-config` (#364) en a besoin pour typer
  `McpConfigView.sources` et l'importe depuis le barrel `@/features/admin-config`,
  barrel auquel la ligne `export type { ConfigSource }` a ete ajoutee pour l'occasion
  (commit `5182563`). L'import respecte la frontiere barrel (7.2.2 reste conforme),
  mais l'item 7.2.3 est explicite : un type partage entre features doit vivre dans
  `shared/types.ts`, pas dans une feature. C'est exactement le cas `RechunkOptions`
  leve au re-audit 0.7.0, reproduit sur du code neuf. Effet de bord : `mcp-config`
  depend de `admin-config` uniquement pour un type de deux litteraux. Cote backend,
  le meme concept est correctement mutualise (`domain/app_config.py:17`, importe par
  `domain/mcp_config.py:25`). Risque faible, correction triviale.
- **Regle violee** : 7.2.3 (poids 2) — « Les types partages entre features sont dans
  `shared/types.ts`, pas dans une feature specifique ».
- **Remediation** : deplacer `ConfigSource` dans `frontend/src/shared/types.ts`,
  l'importer depuis `@/shared/types` dans `admin-config/types.ts` et
  `mcp-config/types.ts`, retirer la reexportation de `admin-config/index.ts:3`.

### [MAJ] `dict` non type et modele ouvert dans des schemas de reponse (item 7.4.2) — inchange

- **Localisation** : `document-parser/api/schemas.py:349` (`StoreResponse.config: dict`,
  classe en `:334`) ; `document-parser/api/graph.py:32` (`GraphNode` ->
  `model_config = {"extra": "allow"}`).
- **Constat** : ecart identique au re-audit 0.7.0, seules les lignes ont bouge
  (`schemas.py:310` -> `:349`). Le read model `StoreResponse` expose toujours le
  config store polymorphe (neo4j vs opensearch) comme `dict` ; le front le reflete en
  `config: Record<string, unknown>` (`frontend/src/features/store/api.ts:23`), donc le
  contrat est opaque des deux cotes. `GraphNode` accepte toujours des champs
  arbitraires, mirroir de `[key: string]: unknown` cote TS
  (`frontend/src/features/analysis/graphApi.ts:36`). Les deux surfaces appartiennent
  au perimetre ingestion (stores OpenSearch/Neo4j, graphe Neo4j), **deprecie et
  supprime en 0.8.0** : la dette s'eteindra avec la suppression plutot que par un
  typage. Aucun nouvel ecart de ce type dans les schemas ajoutes depuis 0.7.2 (MCP,
  summaries, pages, import). N.B. `ImportAnalysisRequest.document: dict`
  (`schemas.py:276`) est un schema de *requete*, hors perimetre de 7.4.2 ; le
  DoclingDocument y est opaque par nature et valide par l'adaptateur
  (`infra/docling_importer.py:18`).
- **Regle violee** : 7.4.2 (poids 2) — « pas de `dict` ou `Any` dans les responses ».
- **Remediation** : soit typer `StoreResponse.config` (union discriminee par `kind`) et
  remplacer `extra="allow"` par les attributs cytoscape emis, soit — vu la
  deprecation — acter formellement dans le plan 0.8.0 que ces deux schemas
  disparaissent avec l'ingestion et sortir l'ecart de la dette a ce moment-la.

### [INFO] `shared/ui` n'est pas une feuille : son barrel reexporte un composant qui importe des internes de features

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56`
  (`../../features/feature-flags/store`, `../../features/ingestion/store`),
  reexporte par `frontend/src/shared/ui/index.ts:1` ; nouveaux consommateurs du barrel :
  `frontend/src/features/mcp-config/ui/McpConfigSection.vue:376` et
  `frontend/src/features/settings/ui/SettingsPanel.vue:115`.
- **Constat** : la frontiere ratifiee en 0.7.0 suppose des briques `shared/` sans
  dependance vers une feature. `AppSidebar.vue` (composant de shell, seul consommateur
  `app/App.vue:49`) vit dans `shared/ui` et plonge dans deux stores de features. C'est
  anterieur a 0.7.0 (lignes de 2026-04, deja presentes a `94eec28` — l'affirmation du
  re-audit « `shared/` ... sans dependance vers une feature » etait donc inexacte).
  Ce qui change en 0.7.3 : le barrel `@/shared/ui` recoit les briques accordeon et
  devient importe par deux features ; au niveau du graphe de modules, `mcp-config` et
  `settings` dependent desormais transitivement des internes de `ingestion` (deprecie)
  et `feature-flags`. La regle ESLint ne le voit pas (ses motifs `../../*/store` ne
  couvrent qu'un segment ; `../../features/x/store` en a deux). Pas de violation de
  la lettre de 7.2.2 (aucune feature n'importe une autre feature hors barrel), d'ou le
  classement INFO ; a corriger avant la suppression de l'ingestion en 0.8.0, qui
  obligera de toute facon a toucher ce fichier.
- **Remediation** : deplacer `AppSidebar.vue` dans `app/` (c'est un composant de shell)
  ou, a minima, importer les stores via `@/features/feature-flags` et
  `@/features/ingestion` ; ajouter un motif ESLint interdisant `features/` depuis
  `src/shared/**`.

### [INFO] Cycle de barrels `document` <-> `analysis` densifie

- **Localisation** : `frontend/src/features/document/ui/DocumentUpload.vue:49` et
  `frontend/src/features/document/ui/DocumentActionsMenu.vue:41` (nouveaux, ->
  `@/features/analysis`) ; `frontend/src/features/document/store.ts:5` (existant) ;
  sens inverse `frontend/src/features/analysis/ui/AnalysisPanel.vue:61` et
  `frontend/src/features/analysis/ui/StructureViewer.vue:64` (-> `@/features/document`).
- **Constat** : l'import d'analyses Docling (#359) ajoute deux aretes
  `document -> analysis` (appel de `importAnalysis`). Comme `document/index.ts`
  exporte `DocumentUpload` / `DocumentActionsMenu` et `analysis/index.ts` exporte
  `AnalysisPanel`, les deux barrels forment un cycle de modules (deja present en
  0.7.0 via `document/store.ts:5`, idem `document` <-> `chunks`). La frontiere barrel
  est respectee mais ne protege pas contre le couplage bidirectionnel.
- **Remediation** : faire emettre un evenement par `DocumentUpload` /
  `DocumentActionsMenu` et laisser la page appeler `importAnalysis`, ou deplacer
  `importAnalysis` dans un module neutre ; envisager `import/no-cycle` en CI.

### [INFO] Pages : 58 imports profonds dans les internes de features, melanges aux imports barrel

- **Localisation** : ex. nouveaux `frontend/src/pages/DocWorkspacePage.vue:62-63,70-72`,
  `frontend/src/pages/DocsLibraryPage.vue:212-214`,
  `frontend/src/pages/AnalysisLibraryPage.vue:110-111`.
- **Constat** : les pages (couche de composition, hors perimetre de 7.2.2 qui vise les
  features) importent librement `store`/`api`/`ui` des features : 58 occurrences
  (55 en 0.7.0 et 0.7.2). Incoherence nouvelle : `DocsLibraryPage.vue` importe
  `AnalysisImportButton` par le barrel (`:211`) mais `useAnalysisStore` et le type
  `BatchLaunch` en profondeur (`:213-214`) alors que le barrel `analysis/index.ts`
  les exporte. Non bloquant ; la regle ESLint ne couvre pas ces chemins a deux segments.
- **Remediation** : decider explicitement si les pages doivent passer par les barrels ;
  si oui, etendre les motifs ESLint (`../features/*/store` etc.) a `src/pages/**`.

### [INFO] Bornes et regle d'hote MCP reproduites cote front (7.1.5 considere conforme)

- **Localisation** : `frontend/src/features/mcp-config/types.ts:58-62` (bornes
  « mirrored from the backend contract ») vs `document-parser/domain/mcp_config.py:29-35` ;
  `frontend/src/features/mcp-config/client.ts:41-46` (`hostAllowed`) vs la regle
  `_validate_host` du SDK MCP.
- **Constat** : comme pour `MAX_ITERATIONS_*` en 0.7.0, le front recopie les bornes
  pour ses steppers/inputs ; le backend reste l'autorite (400 sur ecriture). Mais,
  contrairement au reasoning qui publie ses bornes dans l'OpenAPI
  (`api/schemas.py:691-695`, `ge`/`le`), `McpConfigUpdateRequest`
  (`api/schemas.py:803-815`) et `McpConfigResponse` n'en publient aucune : rien dans
  le contrat ne permet au front de les deriver. `hostAllowed` reimplemente fidelement
  la regle du SDK (correspondance exacte ou `nom:*`) pour afficher un avertissement :
  garde UX, mais derive possible si le SDK change. Pas de reinvention de validation
  metier, d'ou 7.1.5 conforme.
- **Remediation** : ajouter `Field(ge=..., le=...)` sur les champs MCP du schema
  (au moins sur la reponse, comme le reasoning), voire exposer les bornes dans
  `McpConfigResponse` ; commenter `hostAllowed` avec la version du SDK miroir.

### [INFO] Code HTTP derive du texte d'une exception (import d'analyse)

- **Localisation** : `document-parser/api/analyses.py:84` ;
  `document-parser/services/analysis_service.py:173` et `:176`.
- **Constat** : `POST /api/analyses/import` choisit 404 vs 400 avec
  `str(e).startswith("Document not found:")` : le routeur depend du libelle d'un
  `ValueError` du service. Le `RuntimeError` « importer is not configured » (`:176`)
  n'est pas mappe (500 brut). Le reste du perimetre neuf utilise des erreurs typees
  porteuses de `http_status` (`services/config_overrides.py:25-40`, routes
  `/api/config/mcp`) et un `DocumentNotFoundError` type existe deja
  (`services/navigation_errors.py:24`). Le format de reponse (`{"detail": ...}`)
  reste coherent : 7.4.3 conforme.
- **Remediation** : lever une erreur typee (ex. `DocumentNotFoundError`) dans
  `import_docling_document` et la mapper par type, pas par prefixe de message.

### [INFO] Contrat d'URL implicite backend -> SPA pour les deep links MCP

- **Localisation** : `document-parser/services/citation_service.py:292`
  (`f"{base}/analyses/{version_id}?ref=&page="`) ;
  `frontend/src/app/router/routes.ts:39-48` (route `/analyses/:id`, props `ref`/`page`).
- **Constat** : le service de citation fabrique des URLs de l'application Vue
  (chemin + query). Le contrat est documente des deux cotes (commentaire
  `routes.ts:39-40`) et la base est configurable (`MCP_STUDIO_BASE_URL`), mais aucun
  test ne lie les deux : un renommage de route ou de query cote front casserait
  silencieusement les liens publies aux agents.
- **Remediation** : un test front qui resout `"/analyses/x?ref=#/texts/1&page=2"` via
  le routeur et verifie les props, ou une constante de chemin partagee documentee.

### [INFO] Perimetre « framework HTTP » : le montage MCP s'ajoute a `api/` + `main.py` (7.3.4 considere conforme)

- **Localisation** : `document-parser/bootstrap/mcp_mount.py:41-42` (imports
  `starlette`), `:118` (`app.router.routes.extend(...)`) ;
  `document-parser/mcp_adapter/__init__.py:22` (`build_mcp_server(..., **kwargs: Any) -> Any`).
- **Constat** : l'adaptateur MCP lui-meme n'importe ni `fastapi`, ni `starlette`, ni
  `api.*` (0 occurrence dans `mcp_adapter/`) : c'est un adaptateur primaire parallele
  a `api/`, qui ne depend que de `services/`, `domain/` et du SDK. Le couplage au
  framework est concentre dans le composition root `bootstrap/mcp_mount.py`, qui
  etend directement la table de routes FastAPI et emet une `JSONResponse` Starlette.
  Un changement de framework toucherait donc `api/`, `main.py`, `bootstrap/mcp_mount.py`
  et (deja en 0.7.0) `infra/rate_limiter.py:18-19`. Couplage localise et assume
  (le transport HTTP du SDK est une app Starlette), d'ou 7.3.4 conforme dans l'esprit.
  Detail : la facade `build_mcp_server` efface le type (`-> Any`, `**kwargs: Any`), un
  kwarg mal nomme ne serait detecte qu'a l'execution.
- **Remediation** : typer la facade (`-> MCPServer` sous `TYPE_CHECKING`, parametres
  nommes) ; documenter dans la fiche que `bootstrap/` fait partie du perimetre HTTP.

### [INFO] Deux casses pour la meme notion de page ; type wire anonyme

- **Localisation** : `frontend/src/features/document/api.ts:37-47`
  (`fetchDocumentPages`) ; `frontend/src/shared/types.ts:139-144` (`Page`) ;
  `document-parser/api/schemas.py:119` (`PageSizeResponse`).
- **Constat** : `GET /api/documents/{id}/pages` (#352) renvoie du camelCase
  (`pageNumber`) conformement a `_CamelModel`, mais le type wire est declare inline
  et le front le remappe aussitot vers `Page.page_number` (snake_case, herite du
  contenu de `pagesJson`). Contrat correct et type, mais le DTO n'a pas de nom dans
  `shared/types.ts`, et la meme entite circule sous deux casses.
- **Remediation** : nommer `PageSize` dans `shared/types.ts` ; a terme, aligner `Page`
  sur le camelCase du contrat.

### [INFO] Champ de contrat orphelin `stores?` cote frontend — reconduit de 0.7.0

- **Localisation** : `frontend/src/shared/types.ts:39`
- **Constat** : `Document.stores?: string[]` toujours declare, toujours non emis par
  `DocumentResponse` (`document-parser/api/schemas.py:100-116`). Inoffensif, residu.
- **Remediation** : supprimer le champ.

### [INFO] Pre-validation de taille de fichier cote front — reconduit de 0.7.0

- **Localisation** : `frontend/src/features/document/store.ts:75-77`
- **Constat** : garde UX alimentee par la config serveur (`appMaxFileSizeMb` via
  `/api/health`) ; le backend reste l'autorite. Inchange.
- **Remediation** : aucune.

### [INFO] Perimetre de la regle ESLint plus etroit que « barrel uniquement » — reconduit du re-audit

- **Localisation** : `frontend/eslint.config.js:31-49` (aucune modification depuis `94eec28`)
- **Constat** : la regle ne bloque que `store`/`api`/`ui` a un segment. Toujours zero
  import croise vers un module racine d'une autre feature
  (`linkedView`, `progress`, `layerVisibility`... ne sont importes que par des pages).
  Les trous concrets en 0.7.3 sont `shared/` et `pages/` (INFO ci-dessus).
- **Remediation** (optionnelle) : n'autoriser que `@/features/<name>` (et `index`) via
  `import/no-internal-modules` ou des motifs englobants, y compris depuis
  `src/shared/**` et `src/pages/**`.

### [INFO] Services types contre des repos SQLite concrets (annotations seulement)

- **Localisation** : `document-parser/services/store_service.py:23-25` et `:148-150` ;
  `document-parser/services/chunk_service.py:43-44` ;
  `document-parser/services/version_service.py:32` ;
  `document-parser/services/store_backend_resolver.py:43`.
- **Constat** : ces services annotent leurs dependances avec `Sqlite*Repository`
  (imports sous `TYPE_CHECKING`) alors que les Protocols existent
  (`domain/ports.py:128`, `:142`). A l'execution l'injection passe par `bootstrap/`
  et rien ne depend de SQLite : 7.3.3 reste conforme. Mais un changement de base
  obligerait a retoucher ces annotations hors `persistence/`. Anterieur a 0.7.0, non
  signale jusqu'ici ; aucun nouveau service (MCP, sources, navigation) ne reproduit
  le motif.
- **Remediation** : annoter avec les Protocols de `domain/ports.py`.

---

## Delta vs 0.7.0

Score : **94 (re-audit 0.7.0) -> 89 (-5)** ; 80 (1er audit 0.7.0) -> 89 (+9).
Items conformes : 15/16 -> 14/16.

| Ecart baseline | Statut 0.7.3 |
|----------------|--------------|
| [CRIT] 7.2.2 imports croises entre features (1er audit ; leve au re-audit) | **Toujours leve.** 14 imports feature -> feature, tous via barrel (4 nouveaux : `mcp-config/types.ts:1`, `settings/ui/SettingsPanel.vue:114`, `document/ui/DocumentUpload.vue:49`, `document/ui/DocumentActionsMenu.vue:41`) ; `eslint src` sans erreur. |
| [MAJ] 7.2.3 `RechunkOptions` dans une feature (1er audit ; leve au re-audit) | **Toujours leve** (`shared/types.ts:105`, 4 consommateurs via `@/shared/types`). Mais l'item **regresse** sur un nouveau type : `ConfigSource` ([MAJ] ci-dessus). |
| [MAJ] 7.4.2 `StoreResponse.config: dict` / `GraphNode extra=allow` | **Toujours present** (`schemas.py:349`, `graph.py:32`). Perimetre ingestion deprecie, supprime en 0.8.0. |
| [INFO] `stores?` orphelin | Toujours present (`shared/types.ts:39`). |
| [INFO] Pre-validation taille fichier | Inchange (`document/store.ts:75-77`). |
| [INFO] Perimetre ESLint etroit (re-audit) | Inchange (`eslint.config.js` non modifie) ; trous concrets identifies dans `shared/` et `pages/`. |

Nouveaux constats 0.7.3 : 1 MAJ (7.2.3 `ConfigSource`) et 8 INFO (`shared/ui` non
feuille, cycle `document`<->`analysis`, imports profonds des pages, bornes/regle d'hote
MCP recopiees, code HTTP derive d'un message, contrat d'URL deep link, perimetre HTTP
etendu a `bootstrap/mcp_mount.py`, casse de `Page`) + 1 INFO anterieur non releve
jusqu'ici (annotations `Sqlite*Repository` dans les services).

---

## Points positifs

- **Adaptateur MCP correctement decouple de l'app HTTP.** `mcp_adapter/` n'importe ni
  `fastapi`, ni `starlette`, ni `api.*`, ni `infra`/`persistence` : il ne voit que
  `services/` (via le bundle `services/document_tools.py:29-35`), `domain/` et le SDK.
  Le seul point de contact avec FastAPI est le composition root
  `bootstrap/mcp_mount.py`. `mcp_stdio.py` est un second composition root autonome,
  sans dependance a `api/`.
- **Le SDK MCP reste hors des services.** `services/mcp_config_service.py` n'importe ni
  infra ni SDK (docstring `:16-18` verifiee par ses imports) ; la description du
  serveur est mappee du `Tool` SDK vers les value objects `McpServerStatus` /
  `McpToolInfo` dans `bootstrap/mcp_mount.py:128-148`, puis vers le DTO
  `McpServerResponse.from_status` (`api/schemas.py:823-849`).
- **Contrat MCP distinct du domaine.** `mcp_adapter/wire.py:1-17` declare un contrat
  publie (snake_case assume pour un lecteur LLM), mappe depuis le domaine dans
  `mcp_adapter/wire_mapping.py` — meme discipline que `api/schemas.py` pour le front.
- **Nouveaux contrats HTTP types de bout en bout.** Les 7 nouveaux endpoints ont un
  `response_model` Pydantic `_CamelModel` et un type TS champ a champ :
  `McpConfigResponse` <-> `McpConfigView`, `McpServerResponse` <-> `McpServerView`,
  `AnalysisSummaryResponse` <-> `AnalysisSummary` (`Pick<Analysis, ...>`,
  `shared/types.ts:77-90`), `PageSizeResponse` <-> type de `fetchDocumentPages`,
  `ImportAnalysisRequest` <-> `importAnalysis`. Les sources sont un modele
  (`McpConfigSourcesResponse`, `schemas.py:754-760`), pas un `dict`.
- **Frontiere barrel tenue sur le code neuf.** `mcp-config` est une feature complete
  (`api.ts`, `store.ts`, `ui/`, `index.ts`) et n'est consommee que via son barrel ;
  les briques accordeon partagees ont ete placees dans `shared/ui/`
  (`AccordionSection.vue`, `AccordionRow.vue`, `accordion.ts`), pas dans `settings`.
- **Nouveaux ports orientes domaine.** `PageRasterizer` (`domain/ports.py:423`) et
  `PageTextReader` (`:449`) exposent des types domaine (`RasterCrop`, `Glyph`) ;
  `DoclingDocumentImporter` (`:86`) confine `docling_core` a
  `infra/docling_importer.py:7` ; le merge des PDF batches (#344) passe par
  `DocumentConverter.merge_batches`, implemente dans `infra/`.
- **Back testable sans front.** Nouveaux endpoints couverts via `TestClient` :
  `tests/test_mcp_config_api.py`, `tests/test_api_endpoints.py:232-264` (pages),
  `:394` (summaries), `:544-564` (import).

---

## Verdict partiel : GO

Score de compliance **89/100** (>= 80), **0 CRITICAL**, **2 MAJOR** (sous le seuil
master de > 3). Le decouplage tient sur l'essentiel du perimetre neuf : la frontiere
barrel ratifiee en 0.7.0 n'est violee par aucun import feature -> feature (ESLint
propre), le serveur MCP est un adaptateur primaire sans couplage a FastAPI ni a
`api/`, et les nouveaux endpoints sont types des deux cotes. Le score baisse de 94 a
89 a cause d'une regression ponctuelle sur 7.2.3 (`ConfigSource`), correction de
quelques lignes.

Plan de remediation (non bloquant) :
1. [MAJ] 7.2.3 — deplacer `ConfigSource` dans `shared/types.ts` (prochain cycle 0.7.x).
2. [MAJ] 7.4.2 — dette reportee depuis 0.7.0 ; a solder par la suppression de
   l'ingestion en 0.8.0 (ou par typage si l'ingestion est conservee).
3. Recommande avant 0.8.0 : sortir `AppSidebar.vue` de `shared/ui` (il importe
   `ingestion/store`, que 0.8.0 supprime) et etendre la regle ESLint a
   `src/shared/**`.

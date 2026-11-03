# Rapport d'audit : Tests (re-audit)

**Release** : 0.7.4 (re-audit apres remediation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (100 commits de remediation depuis `e6047c2`)

Baseline : `reports/release-0.7.4/09-tests.md` (93/100, 1 MAJ + 4 MIN + 11 INFO, code audite `1de1929`, rapport commite en `e6047c2`). Perimetre identique : `document-parser/tests/`, `frontend/src/**/*.test.*`, `e2e/`.

**Meme lecture des items qu'en 0.7.4.** 9.1.1 et 9.1.2 sont juges sur les suites unitaires. 9.1.3 vise la suite Karate UI dans son ensemble, pas seulement `@critical`. Les defauts des specs e2e (assertions vides, dependance a l'etat de la base) sont rattaches au MAJ 9.1.3, pas a 9.3.3 / 9.3.5.

Methode :
- Chaque ecart 0.7.4 est re-verifie dans le code a `a4d9679`, pas dans les messages de commit.
- Inventaire Karate UI refait : chaque selecteur `data-e2e` (`=`, `^=`, `~=`) de chaque feature est cherche dans `frontend/src`. Les hooks dynamiques (`nav-${item.key}`, `settings-group-${id}-toggle`, `preview-page-${n}`, `layer-chip-${type}`) sont verifies a la main. Les specs modifiees sont relues contre les composants montes.
- Couverture des modules ajoutes par la remediation : pour chaque fichier `A` de `git diff --name-status e6047c2..HEAD`, recherche des tests qui l'importent ou l'exercent.
- Tests cibles lances localement (venv du projet, sans `docling`) : `test_document_versions_api.py`, `test_page_raster.py`, `test_docling_importer.py`, `test_document_tree_service.py`, `test_api_stores.py`, `test_chunking.py`, `test_pipeline_options.py`, `test_batch_merge.py`. Resultat : **121 passed, 2 skipped**. Les 2 modules sautes sont `test_pipeline_options.py:14` et `test_batch_merge.py:17` (`docling library not installed`).
- Suites completes non relancees. Resultats du coordinateur sur HEAD : pytest **1673 passed, 19 skipped** (15 Neo4j absent, 4 docling non installe) ; vitest **53 fichiers, 522 passed** ; ruff, eslint, prettier, vue-tsc, vite build OK.
- Aucune suite Karate n'a ete lancee par cet audit (pas de navigateur ni de stack). Les resultats e2e cites viennent du coordinateur ; aucun rapport Karate n'est joint au depot.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 8 |

Detail du calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**. Le seul item non conforme reste 9.1.3 (poids 2).

### Metriques d'execution

| Suite | Commande | Resultat 0.7.4 | Resultat re-audit |
|-------|----------|----------------|-------------------|
| Backend, local (coordinateur) | `uv run pytest tests/ -q` (groupe `dev`) | 1323 passed, 19 skipped | **1673 passed, 19 skipped** (+350) |
| Backend, fonctions `def test_` | `git grep -c "def test_"` | 1320 | **1589** (+269 ; le reste vient de `parametrize`) |
| Frontend, local (coordinateur) | `npx vitest run` | 53 fichiers, 545 passed | **53 fichiers, 522 passed** (-23) |
| E2E API Karate | — | 38/38 (Release Gate, `1de1929`) | **Aucun run sur la branche** (pas de PR) ; aucun fichier `e2e/api` modifie |
| E2E UI `@critical` | `UIRunner#testCritical` | 15/15 (3 x 5, CI) | **Aucun run CI sur la branche**. `delete.feature` vert en local (coordinateur) |
| E2E UI complete | `UIRunner#testLocal` | Jamais executee | **24 / 29** en local, contre un faux Docling Serve non commite (coordinateur, voir MAJ) |
| Couverture de lignes | — | Non mesuree | Non mesuree (ni `pytest-cov` ni `@vitest/coverage-*`) |

- **Frontend 545 -> 522** : la remediation a supprime `pages/DocIngestTab.logic.test.ts` avec `DocIngestTab.logic.ts` et `IngestLaunchDialog.vue` (code mort, INFO 0.7.4), et les 2 tests de `pushToStore` avec la methode (`features/document/store.test.ts`). Elle a ajoute `features/history/api.test.ts` et 10 cas (`analysis/store.test.ts`, `analysis/batch.test.ts`, `DocsLibraryPage.logic.test.ts`). Le nombre de fichiers reste 53. Aucune perte de couverture sur du code atteignable.
- **Backend +350** : 17 fichiers de test ajoutes, dont `test_chunk_push_service.py`, `test_chunk_formats.py`, `test_chunkset_writes.py`, `test_document_tree_service.py`, `test_document_versions_api.py`, `test_file_storage.py`, `test_pdf_inspector.py`, `test_page_raster.py`, `test_timestamps.py`, `test_ssrf_guard.py`, `test_read_budget.py`, `test_citation_match.py`, `test_api_errors.py`, `test_port_conformance.py`. Plusieurs commits posent les tests avant le refactoring qu'ils protegent (`ea04ed5`, `14322f8`, `02fdaf0`, `05768ae`).
- **Skips (19)** : inchanges en nature. 15 Neo4j (`tests/neo4j/conftest.py:35`), 1 `skipif(not _has_docling())`, et 3 modules sautes a la collecte faute de `docling` (`test_pipeline_options.py:14`, `test_batch_merge.py:17`, `test_robustness.py`). Ces modules contiennent desormais aussi les tests d'un correctif de securite (voir MIN #344).

| # | Item | Poids | Conforme | 0.7.4 -> re-audit |
|---|------|-------|----------|-------------------|
| 9.1.1 | Tous les tests backend passent | 3 | Oui — 1673 passed / 19 skipped (coordinateur) | Oui -> Oui. Preuve locale seulement : aucun run CI sur la branche |
| 9.1.2 | Tous les tests frontend passent | 3 | Oui — 522 passed, 53 fichiers (coordinateur) | Oui -> Oui |
| 9.1.3 | Les tests e2e Karate UI passent | 2 | **Non** — les 11 scenarios obsoletes sont purges ou repares, mais la seule execution complete donne 24/29, sur une stack non documentee, et au moins un scenario est casse pour une vraie raison (voir MAJ) | Non -> **Non**, perimetre de l'ecart tres reduit |
| 9.2.1 | Chaque endpoint API a un test happy path | 2 | Oui — 53 routes (51 `APIRouter` + `/api/health` + `/mcp`, nombre inchange), **toutes** couvertes : `document_versions` l'est desormais (`tests/test_document_versions_api.py:76-141`) | Oui -> Oui, MIN leve |
| 9.2.2 | Cas d'erreur endpoints (400, 404, 413, 429) | 2 | Oui — les nouveaux refus sont testes : 413 du corps `/api/analyses` (`test_api_endpoints.py:767`, `:790`), 400 du budget de cellules (`:725`), 422 et 403 des stores (`test_api_stores.py:404-437`) | Oui -> Oui |
| 9.2.3 | Services : tests d'orchestration | 2 | Oui — les deux services crees (`chunk_push_service`, `document_tree_service`) ont leur fichier de test ; MIN `LocalChunker` inchange | Oui -> Oui |
| 9.2.4 | Fonctions domain (bbox, value objects) | 1 | Oui — `chunk_serialization`, `citation_match`, `read_budget` ont un test dedie ; `doc_tree` est exerce par `test_document_tree_service.py:198-303` (niveaux de titre, dont le correctif `2a6cf40`) | Oui -> Oui |
| 9.2.5 | Composants Vue critiques (stores/composables) | 2 | Oui — 12 stores sur 13 testes, comme en 0.7.4 (`settings/store.ts` sans test, INFO) | Oui -> Oui |
| 9.3.1 | Pas de `.only` / `fdescribe` / `fit` | 3 | Oui — 0 occurrence (`xit` / `xdescribe` compris) | = |
| 9.3.2 | Pas de skip sans justification | 1 | Oui — aucun skip ajoute ; les 3 `importorskip` ont un `reason` | = |
| 9.3.3 | Tests deterministes | 2 | Oui — les tests ajoutes n'ont ni horloge reelle ni reseau : dates fixes (`test_timestamps.py`), `getaddrinfo` patche ou litteraux IP (`test_ssrf_guard.py:4`, `:52`), PDF generes en local (`test_page_raster.py`, `test_pdf_inspector.py`) | = |
| 9.3.4 | Integration teste le flux reel, pas un mock complet | 2 | Oui — `test_chunkset_writes.py` et `test_document_versions_api.py` passent par les vrais repositories SQLite ; MIN #344 partiel, aggrave (voir ci-dessous) | = |
| 9.3.5 | Assertions specifiques | 1 | Oui — 78 lignes `is not None` / `toBeTruthy()` contre 66 ; les 12 nouvelles sont des gardes suivies d'assertions precises, ou des `deleted_at is not None` (suppression logique) | = |
| 9.3.6 | Noms de tests explicites | 1 | Oui (`test_a_cell_span_is_clamped_to_the_grid_like_docling_does`, `test_writes_are_403_on_a_read_only_deployment`…) | = |

### Inventaire Karate UI (21 features, 29 scenarios, helpers et `demo/` exclus)

0.7.4 : 26 features / 36 scenarios, dont 9 features / 11 scenarios obsoletes et 3 assertions qui ne pouvaient pas echouer.
Re-audit : 21 features / 29 scenarios. **Tous les selecteurs `data-e2e` existent dans un composant monte.** Le CI ne lance toujours que `@critical` (`ci.yml:229`, `release-gate.yml:751`), une seule fois desormais.

| Spec 0.7.4 obsolete | Statut | Preuve |
|---------------------|--------|--------|
| `documents/doc-ingest-view.feature` (3 scen.), `_open-launch-modal.feature`, `doc-chunk-view.feature`, `doc-strategy-popover.feature`, `doc-history-drawer.feature` | **Supprimees** (`662607d`) | Fichiers absents ; les composants morts qu'elles visaient sont supprimes aussi (`IngestLaunchDialog.vue`, `DocChunkTab.vue`, `HistoryDrawer.vue`, `InspectResultTabs.vue`, `2deb5f4`) |
| `documents/doc-parse-properties.feature` | **Rebasee** sur `/analyses/:id` : `analyses/analysis-parse-properties.feature` | Hooks presents dans `ElementProperties.vue:2`, `:10`, `:68`, `DocTreeNode.vue:6`. Voir la nouvelle assertion vide plus bas |
| `documents/doc-new-analysis-opens-analysis.feature:17` | **Reparee** : ouvre le menu d'actions | Hooks `doc-actions-trigger` / `doc-actions-start` ajoutes (`DocumentActionsMenu.vue:7`, `:29`) ; spec `:18-21` |
| `navigation/sidebar.feature:14` (scen. 1) | **Reecrite** sur les 5 entrees reelles, avec etat `active` | `sidebar.feature:10-30` ; `AppSidebar.vue:10`, `:126-163` |
| `navigation/reasoning-feature-flag.feature:19` (scen. 1) et assertion vide `:34` (scen. 2) | **Reecrites** : absence d'onglet Ask sur la vue Parse, avec precondition `/api/health` ; redirections `/reasoning` et `/reasoning/:id` | `reasoning-feature-flag.feature:14-46` ; `DocParseTab.vue:116` (`v-if="propertiesOpen && reasoningAvailable"`), `app/router/routes.ts:64`, `:68` |
| Assertion vide `analyses/analysis-detail.feature:63` | **Corrigee** : `doc-actions-trigger` absent de `/analyses/:id` (`:64`), puis present sur `/docs/:id` (`:69`), ce qui prouve que le controle peut echouer | `DocWorkspacePage.vue:28` |
| `retry(n, ms).script(...)` / `retry().until(...)`, qui n'attendent pas | **Remplaces** par `waitUntil` / `waitForAny` (`9d80099`, `da76861`) | `grep "\.script(\|retry()\.until"` : 0 occurrence executable ; regle ecrite dans `e2e/CONVENTIONS.md:218-219` |

---

## Ecarts constates

### [MAJ] La suite e2e Karate UI n'est toujours pas prouvee verte : 24/29 en local sur une stack non documentee, un scenario casse, une nouvelle assertion vide

**Statut vs 0.7.4** : **partiellement corrige**. Les 11 scenarios obsoletes et les 3 assertions vides sont traites (tableau ci-dessus), et la suite complete a ete executee pour la premiere fois. L'item reste non conforme : la seule execution complete n'est pas verte, et elle ne tourne pas dans les conditions documentees.

- **Localisation** :
  - `e2e/ui/src/test/resources/analyses/pipeline-options.feature:54-55` ; `frontend/src/pages/StudioPage.vue:43`
  - `e2e/ui/src/test/resources/analyses/analysis-parse-properties.feature:33` ; `frontend/src/features/document/ui/ElementProperties.vue:76`, `:110` ; `document-parser/services/analysis_service.py:496`
  - `e2e/ui/src/test/resources/workflows/full-ui-path.feature:78` ; `e2e/ui/src/test/resources/documents/upload.feature:18`
  - CI : `.github/workflows/ci.yml:164`, `:199`, `:229` ; `.github/workflows/release-gate.yml:714`, `:751`
- **Constat** :
  - **Preuve d'execution.** Selon le coordinateur, les agents ont lance localement les features modifiees (7/8 vertes) puis `UIRunner#testLocal` (**24/29**), contre une stack locale ou Docling Serve etait remplace par un faux serveur non commite. Les 5 echecs rapportes :
    - le tokenizer Hugging Face, bloque par le proxy du bac a sable. Il est charge par le chunker cote backend, donc par les scenarios qui decoupent (`rechunk.feature`, `full-ui-path.feature`, `doc-tab-chunk-mode.feature`). C'est l'echec restant des features modifiees ;
    - une liste de documents « polluee » par des donnees restees d'un run precedent ;
    - `pipeline-options.feature`, scenario 2.

    Ce que cette preuve etablit : les specs reecrites trouvent leurs hooks et passent hors chunking, et `delete.feature` (`@critical`, dont l'attente est devenue reelle) passe. Ce qu'elle n'etablit pas :
    - l'execution n'est pas celle de `e2e/ui/README.md:20-27` (vrai Docling Serve, Hugging Face joignable). Les analyses portent donc sur la sortie d'un faux serveur ;
    - aucun `karate-summary.html` n'est joint, et cet audit n'a pu verifier ni le detail des 5 echecs ni leur attribution ;
    - au moins un echec n'est pas environnemental (point suivant) ;
    - aucun run CI n'existe sur la branche, meme pour `@critical`. Or le helper `common/helpers/ui-wait-analysis.feature:10`, utilise par les scenarios `@critical` `analysis`, `batch-progress` et `rechunk`, attend desormais vraiment (jusqu'a 120 s).

    **Jugement** : cette preuve ne suffit pas pour 9.1.3. Elle aurait suffi si le run avait ete fait sur la stack documentee, avec 29/29 (ou des echecs prouves environnementaux) et le rapport joint, comme le proposait le quick win 0.7.4.
  - **Scenario casse, hors liste 0.7.4.** `pipeline-options.feature:54-55` clique sur `verify-btn` puis attend `verify-btn.active`. Or ce bouton est `:disabled="!analysisStore.currentAnalysis"` (`StudioPage.vue:43`), et le scenario ne lance aucune analyse : le clic est sans effet et le `waitFor` expire. Le `:disabled` date au moins de `dc87383` (2026-08-08, avant v0.7.0). Le scenario est donc casse depuis au moins v0.7.0. L'inventaire 0.7.4 ne l'avait pas vu, parce qu'il ne verifiait que l'existence des selecteurs. **Nouveau constat, pas une regression.**
  - **Nouvelle assertion vide.** `analysis-parse-properties.feature:33` verifie que `properties-edit-btn` est absent, « a saved analysis never offers the inline chunk editor ». Mais ce bouton n'est rendu que dans `<section v-if="linkedChunk">` (`ElementProperties.vue:76`, bouton `:110`). Or l'analyse de la spec est creee sans `chunkingOptions` (`common/helpers/analyze.feature`), donc sans chunks (`analysis_service.py:496`). `linkedChunk` est alors toujours nul, et l'assertion passerait meme si `:editable="!analysis"` (`DocParseTab.vue:156`) regressait. C'est le defaut que le MAJ 0.7.4 relevait, **reintroduit par la remediation** dans la spec rebasee. L'ancienne spec creait l'analyse avec un chunker `hybrid`. Le reste de la spec (selection d'un noeud, panneau rempli) est valide.
  - **Specs dependantes de l'etat de la base.** `full-ui-path.feature:78` verifie la suppression sur le **premier** `doc-name` de la liste, et `upload.feature:18` verifie que le premier `doc-name` contient `small.pdf`. Un `medium.pdf` ou `small.pdf` reste d'un run precedent suffit a faire echouer, ou a faire passer a tort. L'echec « liste polluee » releve probablement de ce cas. Le passage de `retry().script` a `waitUntil` (`9d80099`) a rendu `:78` capable d'echouer, ce qui est un progres, et a rendu cette fragilite visible.
  - **Perimetre CI inchange.** Seul `@critical` tourne : 5 scenarios, dont 4 sur `/studio`, avec `STUDIO_MODE_ENABLED: "true"` (`ci.yml:199`, `release-gate.yml:714`). Le job `e2e-ui` de `ci.yml` ne tourne que sur `main` (`:164`). `docs/maintainers.md:73` declare maintenant cette lacune (« The UI end-to-end tests outside `@critical` run in no workflow »), ce qui est exact.
- **Regle violee** : 9.1.3 — Les tests e2e Karate UI passent.
- **Remediation** (effort ; risque) :
  1. `pipeline-options.feature` scenario 2 : lancer une analyse (helper `analyze.feature`, puis selection du document) avant de basculer en Verify, ou supprimer le scenario si la conservation des options n'est plus un comportement voulu. (S ; nul)
  2. `analysis-parse-properties.feature` : creer l'analyse avec `chunkingOptions` (comme l'ancienne spec), selectionner un noeud qui a un chunk lie, puis asserter `properties-linked-chunk` present **et** `properties-edit-btn` absent. Sinon, retirer la ligne `:33`. (S ; nul ; demande le tokenizer, donc le reseau en CI)
  3. `full-ui-path.feature:78`, `upload.feature:18` : cibler le document par son id ou son nom (`docId` connu), pas la premiere ligne. (S ; nul)
  4. Executer `UIRunner#testLocal` sur la stack de `e2e/ui/README.md:20-27` (vrai Docling Serve, base vide) et joindre `karate-summary.html`. Ou, mieux, brancher `-Dtest='UIRunner#testAll' -Dkarate.options="--tags @critical,@regression"` au Release Gate. (S run manuel / M job ; gate plus long)
  5. Ouvrir la PR vers `release/0.7.4` pour obtenir le run `@critical` du gate sur `a4d9679`. (S ; nul)
  6. Dette 0.7.0 inchangee : rebaser les 4 `@critical` `/studio` sur `/docs` et `/analyses`, puis retirer `STUDIO_MODE_ENABLED=true`. (L ; faible)

### [MIN] Les modules qui exigent `docling` ne tournent dans aucun gate, dont desormais un correctif de securite (#344, PDF seulement)

**Statut vs 0.7.4** : **inchange, aggrave**.

- **Localisation** : `document-parser/tests/test_pipeline_options.py:14`, `:141`, `:146` ; `document-parser/tests/test_batch_merge.py:17` ; `document-parser/infra/local_converter.py:76` ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:89`, `:132` ; `.github/workflows/docling-compat.yml:8-10`
- **Constat** :
  - Le constat 0.7.4 tient : les gates n'installent que `--group dev` (`ci.yml:41`, `release-gate.yml:89`). `test_batch_merge.py` (#344), `test_pipeline_options.py` et `test_robustness.py` ne sont pas collectes. Le seul job qui installe `--group local` pour les tests est *Docling compatibility*. Il est planifie sur `main`, donc apres le merge, et utilise le docling non epingle. Le nouveau `uv sync --group local --group reasoning` du gate (`release-gate.yml:132`) ne sert qu'a `pip-audit`.
  - **Fait nouveau** : le correctif de securite `8aaace0`, qui reduit le convertisseur local au PDF (`local_converter.py:76`, `allowed_formats=[InputFormat.PDF]`), n'est verifie que par `test_only_pdf_is_allowed` et `test_a_docling_json_input_is_refused` (`test_pipeline_options.py:141`, `:146`). Ce module est saute a la collecte en CI comme en local (verifie : `SKIPPED [1] tests/test_pipeline_options.py:14`). Une regression de ce correctif ne serait vue par aucun gate du release.
- **Regle violee** : 9.3.4 (partiel).
- **Remediation** : un job de gate `uv sync --frozen --group dev --group local`, limite a `pytest tests/test_batch_merge.py tests/test_pipeline_options.py tests/test_robustness.py`, sans `--upgrade`. Ou, pour le seul correctif, un test sans docling qui verifie l'argument passe a `DocumentConverter` (mock du constructeur). (S-M ; nul)

### [MIN] Le mapping des pages Docling (`extract_pages_detail`) n'a toujours aucune assertion en CI

**Statut vs 0.7.4** : **inchange sur le fond**.

- **Localisation** : `document-parser/infra/docling_pages.py:48-120` ; `document-parser/tests/test_docling_importer.py:43-58`, `:66`, `:103-127`
- **Constat** : `grep extract_pages_detail tests/` ne trouve qu'un `patch` (`test_docling_importer.py:66`). Les nouveaux tests du budget de cellules (`:103-127`) font bien passer des documents avec tableaux par l'import, donc par `extract_pages_detail`. Mais leurs tableaux n'ont ni `prov` ni bbox (`_document`, `:43-58`), et les assertions portent sur le Markdown et le HTML. La conversion des bbox en origine haut-gauche, le type par classe, le repli US Letter et le compteur `skipped` restent sans assertion dans un test execute en CI.
- **Regle violee** : 9.2.3 / 9.2.4 (partiel).
- **Remediation** : inchangee. Un `DoclingDocument` en memoire avec une page dimensionnee, un texte `prov`/`bbox`, un tableau et un element sur une page absente, avec des assertions sur les bbox converties, les types et `skipped`. (S ; nul)

### [MIN] La logique de `LocalChunker` n'est pas testee ; le commentaire renvoie toujours a un fichier inexistant

**Statut vs 0.7.4** : **inchange**.

- **Localisation** : `document-parser/tests/test_chunking.py:486` ; `document-parser/infra/local_chunker.py`
- **Constat** : `test_chunking.py:486` cite toujours « ``test_local_chunker.py`` », absent du depot. `LocalChunker` n'est importe que par `test_serve_converter.py` (cablage) et par `test_chunking.py`, qui le mocke.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel).
- **Remediation** : corriger le commentaire (1 ligne), ou ajouter le test promis avec un tokenizer local. (S ; nul)

### [INFO] Glue de composition non testee : switch live MCP, et desormais la politique des stores

**Statut vs 0.7.4** : **inchange, etendu**.

- **Localisation** : `document-parser/bootstrap/builder.py:162-165`, `:266-271` ; `document-parser/tests/test_api_stores.py:391-398` ; `document-parser/services/store_service.py:323-342`
- **Constat** :
  - La closure `apply_config` -> `mcp_serving` (`builder.py:266-271`) n'est toujours couverte que par `mcp-config.feature`, hors CI.
  - **Nouveau** : le garde SSRF et le mode lecture seule des stores ne sont actifs que si le builder appelle `set_connection_policy` (`builder.py:162-165`). Sans cet appel, le service garde ses valeurs par defaut de classe : controle du schema seulement, ecriture permise (`store_service.py:323-329`). Tous les tests construisent eux-memes leur `StoreService` avec la politique (`test_api_stores.py:391-398`, `test_store_service.py:711-715`). Aucun ne verifie que l'application reelle la recoit. Le correctif #audit-08 est donc teste, mais pas son activation.
- **Remediation** : un test qui construit l'`AppState` par `AppStateBuilder` avec des settings `DEPLOYMENT_MODE=huggingface`, puis verifie un `POST /api/stores` -> 403 et une URI `169.254.169.254` -> 422. Le meme test peut couvrir le switch MCP.

### [INFO] Aucun scenario e2e API pour les routes 0.7.3 ; le proxy nginx `/mcp` n'est pas verifie

**Statut vs 0.7.4** : **inchange** (aucun fichier de `e2e/api/` modifie). Le `/mcp` de nginx a pourtant change (`gzip off`, `X-Forwarded-For`, `frontend/nginx.conf.template:66-77`), sans aucun test.

### [INFO] Import Docling (#359) : le flux client n'a toujours aucun test

**Statut vs 0.7.4** : **partiellement corrige**. Le 400 « document invalide » est desormais exerce en HTTP (`test_api_endpoints.py:793-803`), et les nouveaux 413 et 400 de l'import sont testes (`:725-803`). Le flux client (`JSON.parse`, `importAnalysis`, affichage d'erreur), copie dans `DocumentUpload.vue`, `DocumentActionsMenu.vue` et `AnalysisImportButton.vue`, reste sans test.

### [INFO] Branches 413 secondaires

**Statut vs 0.7.4** : **partiellement corrige**. Le mapping `GraphTooLargeError` -> 413 est teste par le gestionnaire commun (`test_api_errors.py:63`), mais pas le declenchement du service au-dela de `max_pages` (`services/graph_service.py:48`, `:94`). La garde de flux de l'upload (`api/documents.py:77`) n'est toujours pas atteinte : le seul test 413 de l'upload passe par la pre-verification `Content-Length` (`test_api_endpoints.py:248-262`).

### [INFO] RuntimeWarning « coroutine never awaited » dans `test_pipeline_options.py`

**Statut vs 0.7.4** : **inchange** (`test_pipeline_options.py:382`, `:392`). Invisible dans les gates, ou le module n'est pas collecte.

### [INFO] Les 15 tests Neo4j ne tournent dans aucune CI ; la docstring affirme le contraire

**Statut vs 0.7.4** : **inchange** (`tests/neo4j/conftest.py:4`, « CI spins up `neo4j:5.15-community` » ; `grep neo4j .github/workflows/` : 0).

### [INFO] Reasoning : le gate prouve la presence des paquets, pas un appel

**Statut vs 0.7.4** : **partiellement corrige**. Le gate construit l'image `local` avec `WITH_REASONING=true` (`release-gate.yml:272`) et un smoke test sans reseau exige `reasoningAvailable: true` (`:378-419`). Aucun test n'appelle pourtant `POST /api/documents/{id}/reasoning`, et l'adaptateur `docling-agent` n'est teste qu'avec des modules factices (`test_docling_agent_reasoning.py`).

### [INFO] Frontend : un store sans test, 14 tests sur du code inatteignable

**Statut vs 0.7.4** : **partiellement corrige**.
- `DocIngestTab.logic.test.ts` (23 tests) est supprime avec son code.
- `features/store/ui/connectionForm.logic.test.ts` (14 tests) teste toujours la logique de `StoreForm.vue`, qu'aucun composant n'importe. Le fichier a meme ete retouche par `ee17245` (couleurs du theme).
- `features/settings/store.ts` n'a toujours pas de test.

---

## Suivi des ecarts 0.7.4

| Ecart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] Karate UI : 9 features / 11 scenarios obsoletes, 3 assertions vides, 31 scenarios hors CI | **Partiellement corrige** : 0 spec obsolete, assertions corrigees, suite executee une fois (24/29, stack non documentee) ; 1 scenario casse (`pipeline-options:54`), 1 nouvelle assertion vide (`analysis-parse-properties:33`), toujours hors CI | MAJ ci-dessus |
| [MIN] #344 non gate | **Inchange, aggrave** (correctif PDF-only teste dans un module non collecte) | `test_pipeline_options.py:14`, `:141` |
| [MIN] `extract_pages_detail` sans test CI | **Inchange** sur le fond (execute sans assertion) | `test_docling_importer.py:66`, `:103-127` |
| [MIN] `document_versions` sans test API | **Corrige** | `tests/test_document_versions_api.py:76-141` (GET, restore, 404) |
| [MIN] `LocalChunker` + commentaire | **Inchange** | `test_chunking.py:486` |
| [INFO] Glue switch MCP | **Inchange**, etendu a la politique des stores | `builder.py:162-165`, `:266-271` |
| [INFO] Pas d'e2e API routes 0.7.3 | **Inchange** | — |
| [INFO] Import #359 : 400 HTTP et flux client | **Partiellement corrige** (400 teste) | `test_api_endpoints.py:793-803` |
| [INFO] Branches 413 secondaires | **Partiellement corrige** (mapping graphe) | `test_api_errors.py:63` |
| [INFO] RuntimeWarning `test_pipeline_options.py` | **Inchange** | `:382`, `:392` |
| [INFO] Docstring Neo4j | **Inchange** | `tests/neo4j/conftest.py:4` |
| [INFO] Reasoning hors gate | **Partiellement corrige** | `release-gate.yml:272`, `:378-419` |
| [INFO] `tee` sans `pipefail` | **Corrige** | `release-gate.yml:87`, `:94` |
| [INFO] Triple execution `@critical` | **Corrige** | `ci.yml:226`, `release-gate.yml:748` |
| [INFO] `PdfPageRasterizer.crop` non teste | **Corrige** | `tests/test_page_raster.py:87-98` (boite, clamp, WEBP) et `:43-79` (rendu, fichier lu en place, non-PDF refuse) |
| [INFO] Store `settings` sans test, 37 tests de code mort | **Partiellement corrige** (23 supprimes, 14 restent) | `connectionForm.logic.test.ts` |

### Couverture des modules ajoutes par la remediation

| Module ajoute | Teste par |
|---------------|-----------|
| `api/errors.py`, `services/errors.py` | `test_api_errors.py` (chaque famille -> son statut, corps `{"detail"}`) |
| `services/chunk_errors.py` | `test_api_errors.py`, `test_chunk_push_service.py`, `test_document_tree_service.py` |
| `services/chunk_push_service.py` | `test_chunk_push_service.py` (627 lignes), `test_chunk_formats.py` |
| `services/document_tree_service.py` | `test_document_tree_service.py` |
| `domain/chunk_serialization.py` | `test_chunk_serialization.py`, `test_chunk_editing.py` |
| `domain/citation_match.py` | `test_citation_match.py` |
| `domain/read_budget.py` | `test_read_budget.py` |
| `domain/doc_tree.py` | Indirect : `test_document_tree_service.py:198-303` (niveaux de titre) |
| `persistence/timestamps.py` | `test_timestamps.py` |
| `infra/file_storage.py` | `test_file_storage.py`, `test_port_conformance.py` |
| `infra/pdf_inspector.py`, `infra/pdfium_lock.py` | `test_pdf_inspector.py`, `test_page_text.py` |
| `infra/ssrf_guard.py` | `test_ssrf_guard.py`, `test_api_stores.py`, `test_store_service.py` |
| `mcp_adapter/sources_mapping.py`, `sources_text.py`, `sources_wire.py` | Indirect, par `sources_view.py:25-27` : `test_mcp_sources_app.py` (38 tests), `test_mcp_apps.py` |

Chaque module ajoute est exerce par au moins un test execute en CI. Seule l'activation de la politique des stores dans le builder ne l'est pas (INFO).

---

## Regressions et nouveaux ecarts introduits par la remediation

| Constat | Gravite | Localisation |
|---------|---------|--------------|
| Assertion vide dans la spec rebasee (`properties-edit-btn` absent quel que soit `editable`) | Rattache au MAJ | `analysis-parse-properties.feature:33` |
| Correctif de securite PDF-only teste uniquement dans un module non collecte | Rattache au MIN #344 | `test_pipeline_options.py:141`, `:146` |
| Activation du garde SSRF / lecture seule des stores non testee au niveau du builder | INFO | `builder.py:162-165` |

Nouveaux constats sur du code anterieur, pas des regressions : `pipeline-options.feature` scenario 2 (casse depuis au moins v0.7.0) et la dependance de `full-ui-path.feature:78` / `upload.feature:18` a l'etat de la liste.

---

## Ce qui reste a faire pour 100

Seul 9.1.3 (poids 2) fait bouger le score : **93 -> 100**.
1. Corriger `pipeline-options.feature` scenario 2 et `analysis-parse-properties.feature:33` (remediations 1-2 du MAJ). (S)
2. Rendre `full-ui-path.feature:78` et `upload.feature:18` independants de l'etat de la liste (remediation 3). (S)
3. Prouver la suite : `UIRunner#testLocal` 29/29 sur la stack documentee, rapport joint, ou job `@critical,@regression` au gate (remediation 4). (S / M)

Les MIN (#344 avec le test PDF-only, `extract_pages_detail`, commentaire `LocalChunker`) et les INFO ne changent pas le score.

---

## Points positifs

- **+350 tests backend, souvent ecrits avant le refactoring qu'ils protegent** : la remediation pose les filets d'abord (`ea04ed5` « pin the chunkset write paths before batching them », `14322f8`, `02fdaf0`, `05768ae`), puis deplace le code. Les nouveaux tests passent par les vrais repositories SQLite (`test_chunkset_writes.py`, `test_document_versions_api.py`) plutot que par des mocks.
- **Chaque correctif de securite ou de robustesse arrive avec son test** : budget de cellules et plafond 413 (`test_docling_importer.py`, `test_api_endpoints.py:725-803`), garde SSRF des stores (`test_ssrf_guard.py`, `test_api_stores.py:404-437`), bornes de `MCP_MAX_READ_TOKENS` et `MAX_IMPORT_TABLE_CELLS` (`test_settings.py`), dates (`test_timestamps.py`), niveau de titre invalide (`test_document_tree_service.py`). La seule exception est le test PDF-only (MIN #344).
- **Suite Karate assainie** : plus aucune spec ne pilote une UI inexistante. Les attentes `retry().script()`, qui ne pouvaient pas echouer, sont remplacees, et la regle est ecrite dans `e2e/CONVENTIONS.md:218-219`. `@critical` ne tourne plus qu'une fois par run. La documentation des runners (`e2e/ui/README.md`) et la lacune « hors `@critical` » (`docs/maintainers.md:73`) sont exactes.
- **Code mort retire avec ses tests**, au lieu d'entretenir 23 tests sur une UI d'ingestion inatteignable.
- **Discipline intacte** : 0 `.only` / `fdescribe` / `fit` / `xit`, 0 skip ajoute, tests deterministes (pas d'horloge reelle, DNS patche).

---

## Verdict partiel : GO

Score **93/100** (inchange), **0 CRITICAL**, **1 MAJOR** (sous le seuil de 3), 3 MINOR, 8 INFO. Les suites unitaires sont vertes et plus fournies : 1673 tests backend, 522 frontend. Tous les modules ajoutes par la remediation sont testes, et le MIN `document_versions` est leve.

Le MAJ 9.1.3 est fortement reduit : plus aucune spec obsolete, et une premiere execution complete. L'item reste non conforme : cette execution donne 24/29, contre un faux Docling Serve, sans rapport joint, avec au moins un scenario reellement casse (`pipeline-options.feature:54`). La purge a aussi reintroduit une assertion vide (`analysis-parse-properties.feature:33`). Deux corrections de spec et un run sur la stack documentee suffiraient a atteindre 100/100. Aucun run CI n'existe encore sur la branche : ouvrir la PR vers `release/0.7.4` est un prealable pour prouver aussi `@critical` sur `a4d9679`.

---

## Addendum — vérification post-correctifs (HEAD 3f1d1cb, 2026-11-03)

Verification dans le code de la passe `a4d9679..3f1d1cb` (commits `021d4dd`, `1ebc0e0`, `2bf799d` et `a5257e3` pour les specs, plus les tests ajoutes avec chaque correctif). Gates du coordinateur sur `3f1d1cb` : pytest **1723 passed, 19 skipped** (+50 depuis le re-audit) ; vitest **53 fichiers, 522 passed** ; ruff, eslint, prettier, vue-tsc, build OK. **Aucun run CI sur la branche.** Le rapport Karate de l'agent, hors depot, a ete lu dans le scratchpad (`karate-reports-final/`, avec les journaux `karate-*.log` et `fake_serve.log`).

### Ecarts vises (defauts de specs du MAJ 9.1.3)

| Ecart | Statut | Preuve (`3f1d1cb`) |
|-------|--------|--------------------|
| `pipeline-options.feature`, scenario 2 casse (`verify-btn` desactive sans analyse) | **Ferme** | Analyse creee par le helper `analyze.feature` (`:43`), Studio ouvert sur `/studio?analysisId=` (`:47`), ce qui selectionne le document et passe en Verify (`frontend/src/pages/StudioPage.vue:665-674`). Le scenario verifie en plus le defaut `accurate` (`:53`) et l'absence du panneau en Verify (`:59`), puis que `fast` est conserve (`:64`). Avant / apres : `karate-pipeline-before.log` echoue a `:55` (ancienne spec), `karate-pipeline-after.log` donne 2 / 2 |
| `analysis-parse-properties.feature:33` : assertion vide | **Ferme** | L'analyse est creee avec des chunks (`chunkingOptions: { chunkerType: 'hierarchical' }`, `:22` ; aucun tokenizer HF). L'element couvert par le premier chunk (`:37`) est ouvert par lien profond `?ref=` (`:54`, `focusRef` `app/router/routes.ts:46`). La spec attend la section Linked chunk (`:55`, `ElementProperties.vue:76-78`), **puis** l'absence de `properties-edit-btn` (`:56`, `ElementProperties.vue:110-113`, `v-else-if="editable"` ; `DocParseTab.vue:156`, `:editable="!analysis"`). **Preuve que l'assertion peut echouer** : frontend mute (`dist-mutant`), `karate-props-mutant.log` echoue a `:56` (1 bouton trouve au lieu de 0). La sonde sur l'ancienne spec (`zz-local.old-parse-properties-probe`) montre que la section Linked chunk n'y etait jamais rendue : le defaut est confirme |
| `upload.feature:18`, `full-ui-path.feature:78` dependants de la premiere ligne | **Ferme** | Nouveau helper `common/helpers/document-ids.feature` (ids par nom de fichier, avant / apres l'upload). Les specs verifient la **ligne selectionnee** (`upload.feature:23`, `:47` ; `full-ui-path.feature:22`), qu'**un seul** document a ete cree (`upload.feature:28`, `:53` ; `full-ui-path.feature:27`) et nettoient par cet id. `full-ui-path` supprime la ligne selectionnee (`:81`) puis exige un 404 de l'API sur cet id (`:85-87`). Avant / apres : l'ancienne spec echoue sur une base qui contient deja `medium.pdf` (`zz-local.old-full-ui-path-hier`), la nouvelle passe |
| `driver.inputFile` : chemin resolu contre le dossier de la feature (« Failed to fetch ») | **Ferme** | Chemin `classpath:` passe tel quel : `common/helpers/ui-upload.feature:9`, `documents/error-states.feature:9`, `documents/upload.feature:19`, `:43`, `workflows/full-ui-path.feature:18`. Plus aucun `karate.toAbsolutePath` dans `e2e/`. Regle ecrite : `e2e/CONVENTIONS.md:225`. Avant : `karate-upload-before.log` echoue a `upload.feature:17` et `:39` |

Inventaire : 21 features et 29 scenarios, inchange. Tous les selecteurs `data-e2e` des specs modifiees existent dans un composant monte.

### Ce que prouve le run « 8/8 »

Contenu du rapport : `karate-summary-json.txt` (Karate 1.5.0, 1 thread, 2026-11-03 15:09, 42 s) donne **5 features, 8 scenarios, 0 echec** :
- `analyses/analysis-parse-properties` (1) ;
- `analyses/pipeline-options` (2) ;
- `documents/error-states` (2) ;
- `documents/upload` (2) ;
- `zz-local/new-full-ui-path-hier` (1).

**Il prouve** :
- que les 4 features **commitees** modifiees (7 scenarios) passent sur une stack locale ;
- que chaque assertion reecrite peut echouer (avant / apres et mutant ci-dessus) ;
- que le correctif `inputFile` debloque les uploads UI.

**Il ne prouve pas** :
- **les autres scenarios de la suite** : le run couvre 8 des 29 scenarios a HEAD, mais seulement 7 des specs commitees (voir le point suivant). Les 5 `@critical` ne sont pas dans le run ;
- **la spec commitee `workflows/full-ui-path.feature`** : le 8e scenario est une variante locale, qui ajoute `select('[data-e2e=config-select]', 'hierarchical')` (« LOCAL ONLY: no Hugging Face tokenizer »). La spec commitee decoupe avec le chunker par defaut, donc avec le tokenizer HF, et n'a pas ete executee telle quelle ;
- **la stack documentee** (`e2e/ui/README.md:20-27` : `docker compose --profile remote`, vrai Docling Serve) : Docling Serve est remplace par un faux serveur local (`fake_serve.log` : 12 `POST /v1/convert/file` servis par un uvicorn sur 127.0.0.1:5765). Les analyses portent donc sur une sortie fabriquee ;
- **la tracabilite** : aucun rapport n'est joint au depot, et aucun job ne lance `@regression` au gate (`release-gate.yml:751` : toujours `--tags @critical`) ;
- **le CI** : aucun run de la branche, meme `@critical`.

**Decision : 9.1.3 reste non conforme.** Le re-audit exigeait 29 / 29 sur la stack documentee (ou des echecs prouves environnementaux), avec le rapport joint, ou un job `@critical,@regression` au gate. Aucune des deux conditions n'est remplie. Le MAJ est encore reduit : tous les defauts de specs qu'il nommait sont corriges, preuve a l'appui. Il ne reste que la **preuve d'execution** de la suite et son perimetre CI.

### Tests ajoutes par la passe (+50)

Chaque correctif arrive avec son test :
- OpenAPI : `tests/test_openapi_contract.py`, 5 tests sur le schema reellement publie ;
- refus de chunk par MRO : `tests/test_chunk_errors.py` ;
- identifiants Neo4j : `tests/test_store_backend_resolver.py:201-418` ;
- budget de grilles : `tests/test_docling_importer.py:60-218` ;
- plafond de 50 Mo : `tests/test_api_endpoints.py:781-848` ;
- lecture seule HF de `remove_document` : `tests/test_store_service.py:734` ;
- 500 generique de `/reasoning` : `tests/test_reasoning_api.py:251` ;
- une seule question « parse courante » par appel : `tests/test_source_service.py` (`TestOneParsePerCall`, `latest_lookups`).

Exception, rattachee a l'INFO « glue de composition non testee » sans changer le compte : l'activation de la garde SSRF dans le resolveur de production (`bootstrap/factories.py:194`) n'est couverte par aucun test (`grep build_backend_resolver tests/` : 0). La sonde `push_ssrf_probe.py` confirme qu'elle est cablee.

**Regressions** : aucune.

### Score recalcule

Meme lecture que le re-audit (une seule) : seul 9.1.3 (poids 2) reste non conforme, 25 / 27 → **93 / 100**, inchange.

| Metrique | Re-audit (`a4d9679`) | Post-correctifs (`3f1d1cb`) |
|----------|----------------------|-----------------------------|
| Items conformes | 13 / 14 | 13 / 14 |
| Score | 93 / 100 | **93 / 100** |
| Ecarts CRITICAL | 0 | 0 |
| Ecarts MAJOR | 1 | 1 (perimetre reduit a la preuve d'execution) |
| Ecarts MINOR | 3 | 3 (#344 hors gate, `extract_pages_detail`, `LocalChunker`, inchanges) |
| Ecarts INFO | 8 | 8 |

Pour 100 :
- lancer `UIRunner#testLocal` sur la stack de `e2e/ui/README.md:20-27` (vrai Docling Serve, Hugging Face joignable, base vide) et joindre `karate-summary.html`, 29 / 29 ou echecs prouves environnementaux ;
- ou ajouter au Release Gate un job `@critical,@regression` ;
- et ouvrir la PR vers `release/0.7.4` pour obtenir le run `@critical` du gate.

### Verdict partiel apres correctifs : GO

Score **93 / 100**, 0 CRITICAL, 1 MAJOR, 3 MINOR, 8 INFO.

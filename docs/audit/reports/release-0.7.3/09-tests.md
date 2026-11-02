# Rapport d'audit : Tests

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68
**Baseline** : re-audit 0.7.0 (`release/0.7.0` @ `94eec28`, 100/100)

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

Detail du calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**.

### Metriques d'execution

| Suite | Commande | Resultat | Duree |
|-------|----------|----------|-------|
| Backend, local | `.venv/bin/python -m pytest -q -rs` (depuis `document-parser/`) | **1386 passed, 15 skipped, 0 failed**, 5 warnings | 49,20 s |
| Backend, CI (run `41452006012`, job *Backend tests*, commit 02adc68) | `uv run pytest tests/ -v` | **1322 passed, 19 skipped** (`collected 1338 items / 3 skipped`) | 29,22 s |
| Frontend | `npx vitest run` (depuis `frontend/`) | **53 fichiers, 545 passed, 0 failed** | 3,89 s |
| Couverture de lignes | — | Non mesuree : `pytest-cov` absent du venv, aucun provider `@vitest/coverage-*` installe | — |
| E2E API Karate, CI (run `41421174625`, commit `3f1bcb4`, arbre identique a 02adc68 — `git diff 3f1bcb4 02adc68` vide) | `--tags @smoke,@regression,@e2e` | 12 features / 36 scenarios + 2 smoke, **0 echec** | 135,5 s |
| E2E API Karate, CI (run `41452006012`, 02adc68) | `--tags @smoke` | 2 scenarios (health seul), 0 echec | 3,6 s |
| E2E UI Karate | — | **Non execute** dans cet audit (stack live requise) ; aucune execution CI terminee pour cet arbre — le Release Gate `41452005966` etait en cours a l'heure de l'audit | — |

- **Skips locaux (15)** : tous dans `tests/neo4j/` — « Neo4j not reachable at bolt://localhost:7687 » (fixture `tests/neo4j/conftest.py:35`).
- **Skips CI (19)** : les 15 memes, plus 3 modules entiers sautes a la collecte faute de `docling` (`tests/test_robustness.py:154`, `tests/test_pipeline_options.py:14`, `tests/test_batch_merge.py:17`, tous `pytest.importorskip("docling", reason=...)`) et `tests/test_serve_converter.py:792` (`skipif(not _has_docling())`). Au total **64 tests passent en local mais ne tournent jamais en CI** (63 non collectes + 1 skip).
- **Warnings (5)** : `RuntimeWarning: coroutine ... was never awaited`, tous issus de `tests/test_pipeline_options.py` (INFO de la baseline).
- **Volume** : backend 849 -> 1386 tests (+537), frontend 432 -> 545 (+113) depuis 0.7.0. La pile MCP (`test_mcp_*`, `test_navigation_*`, `test_source_*`, `test_page_*`, `test_quote_marks`) compte a elle seule 458 tests. Aucun fichier de test supprime depuis 0.7.2 (`git diff --diff-filter=D caddf30..HEAD`).

| # | Item | Poids | Conforme | Evolution vs re-audit 0.7.0 |
|---|------|-------|----------|-----------------------------|
| 9.1.1 | Tous les tests backend passent | 3 | Oui — 1386 passed / 15 skipped (local), 1322 / 19 (CI) | = |
| 9.1.2 | Tous les tests frontend passent | 3 | Oui — 545 passed (53 fichiers) | = |
| 9.1.3 | Les tests e2e Karate UI passent | 2 | **Non** — voir MAJ | **Oui -> Non** |
| 9.2.1 | Chaque endpoint API a un test happy path | 2 | Oui — les 6 nouvelles routes sont couvertes (voir MIN — versions HTTP) | = |
| 9.2.2 | Cas d'erreur endpoints (400, 404, 413, 429) | 2 | Oui — plus 403/421/422/503 sur les nouvelles routes | = |
| 9.2.3 | Services : tests d'orchestration | 2 | Oui — `ExportService` desormais teste (MIN 0.7.0 leve) | = (1 MIN leve) |
| 9.2.4 | Fonctions domain (bbox, value objects) | 1 | Oui | = |
| 9.2.5 | Composants Vue critiques (stores/composables) | 2 | Oui — store/client mcp-config, accordion, flags `askMode`, batch | = |
| 9.3.1 | Pas de `.only` / `fdescribe` / `fit` | 3 | Oui — aucun | = |
| 9.3.2 | Pas de skip sans justification | 1 | Oui — tous les skips portent un `reason` | = |
| 9.3.3 | Tests deterministes | 2 | Oui | = |
| 9.3.4 | Integration teste le flux reel, pas un mock complet | 2 | Oui (voir MIN — #344, LocalChunker) | = |
| 9.3.5 | Assertions specifiques | 1 | Oui | = |
| 9.3.6 | Noms de tests explicites | 1 | Oui | = |

### Couverture des nouveautes 0.7.3 (chemin critique)

| Nouveaute | Tests rapides (executes en CI) | E2E | Statut |
|-----------|-------------------------------|-----|--------|
| Outils MCP (`find_documents`, `get_outline`, `read_element`, `verify_citation`, `show_sources`, apps) | `test_mcp_adapter.py` (surface, lecture bornee, citation, contenu non fiable, contrat publie), `test_mcp_surface.py` (budget 3 400 car., chaque regle enoncee une fois), `test_mcp_apps.py`, `test_mcp_sources_app.py`, `test_mcp_prompts.py`, `test_mcp_tool_errors.py` — vrai `mcp.Client` en memoire | aucun | Couvert |
| Transport `/mcp` : gate 503 et switch live | `test_mcp_mount.py:75-101` (503 JSON-RPC, retour a 200 sans remount, passage avant boot), `:104-140` (421 hors allow-list, allow-list livree) | `mcp-config.feature:64` — jamais execute en CI | Couvert par moitie (INFO) |
| `/api/config/mcp` (validation) | `test_mcp_config_api.py:113-205` (400 bornes, 422 champ ou switch omis, 403 read-only, 400 sans `MCP_ENABLED`, reset), `test_mcp_config_service.py` (bornes, precedence env/db, rows illisibles) | `mcp-config.feature` — jamais execute en CI | Couvert |
| `/api/mcp/server` | `test_mcp_config_api.py:208-225` (200, 503 non cable), `test_mcp_mount.py` `TestDescribe` | — | Couvert |
| `mcp_stdio.py` | `test_mcp_stdio.py` (chemin DB relatif, DB absente -> exit 1, stdout vierge) | — | Couvert |
| Import Docling (#359) | `test_api_endpoints.py:537-566` (200, 400 `documentId` vide, 404 document absent), `test_analysis_service.py:164`, `:206` (document invalide -> aucun insert), `test_docling_importer.py` ; frontend `analysis/api.test.ts:49` | aucun | Couvert (INFO : 400 « document invalide » non teste en HTTP) |
| `GET /api/analyses/summaries` | `test_api_endpoints.py:380-405` (contenu absent du payload), `test_repos.py:217`, `test_analysis_service.py:732` ; frontend `batch.test.ts`, `store.test.ts` `followActive` (fake timers) | `docs-batch-analysis.feature` — jamais execute en CI | Couvert |
| `GET /api/documents/{id}/pages` | `test_api_endpoints.py:223-264` (200, 404 document, 404 fichier, 422 PDF illisible) ; frontend `document/api.test.ts:45` | `doc-viewer.feature` — jamais execute en CI | Couvert |
| Merge des batches (#344) | orchestration `test_analysis_service.py:383-425` (CI) ; merge reel `test_batch_merge.py` (5 tests) **skippe en CI** | `e2e/api/.../batch-progress.feature:38` (CI) — ne batch pas en mode remote | Voir MIN |
| `ASK_MODE` | `test_settings.py:210-230`, `test_api_endpoints.py:99-106` ; frontend `feature-flags/store.test.ts:149-189` | `reasoning-feature-flag.feature` `@ask-hidden` — jamais execute en CI | Couvert |
| Settings en sections | frontend `shared/ui/accordion.test.ts` (8 tests) | `settings-accordion.feature` — jamais execute en CI | Couvert (logique) |
| Panneau MCP (frontend) | `mcp-config/store.test.ts` (16 tests), `mcp-config/client.test.ts` (8 tests) | `mcp-config.feature` — jamais execute en CI | Couvert (logique) |

---

## Ecarts constates

### [MAJ] La suite e2e Karate UI n'est pas verte dans son ensemble, et ses specs 0.7.3 ne tournent dans aucun workflow

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-ingest-view.feature:38`, `e2e/ui/src/test/resources/documents/doc-chunk-view.feature:30-31`, `e2e/ui/src/test/resources/documents/doc-strategy-popover.feature:30-31` et `:39` ; `frontend/src/shared/routing/modes.ts:36-37` ; `e2e/ui/src/test/java/UIRunner.java:6` et `:19-21` ; `.github/workflows/release-gate.yml:645` ; `.github/workflows/ci.yml:220` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:1` ; `e2e/ui/README.md:56`
- **Constat** :
  - **Trois specs pilotent une UI supprimee. C'etait deja le cas en 0.7.0, et c'est toujours vrai.** `doc-ingest-view.feature:38` attend `[data-e2e=view-switcher]` puis `ingest-tab` et `ingest-launch-cta` : 0 occurrence dans `frontend/src`. `doc-chunk-view.feature:30-31` et `doc-strategy-popover.feature:30-31` ouvrent `?mode=chunk` et attendent `[data-e2e=chunk-tab]`. Or `modes.ts:36-37` resout `chunk` et `ingest` en `parse`, et `pages/DocChunkTab.vue`, seul porteur de `chunk-tab`, n'est importe nulle part. `strategy-btn` (`doc-strategy-popover.feature:39`) a lui aussi 0 occurrence. Ces specs echouent forcement au premier `waitFor` sous `UIRunner.testAll` (`:6`) ou `testLocal` (`:19-21`). Le suivi annonce dans `doc-tab-chunk-mode.feature:14` (« need the same treatment ») n'a pas ete fait.
  - **Les 8 features UI ecrites pour 0.7.3 (10 scenarios) ne sont executees par aucun workflow** : `mcp-config.feature` (3 scenarios), `settings-accordion.feature`, `docs-batch-analysis.feature`, `doc-viewer.feature`, `analysis-detail.feature`, `analysis-parse-hide-boxes.feature`, `analysis-parse-show-all.feature`, `doc-new-analysis-opens-analysis.feature`. Elles sont taguees `@ui @regression` ou `@ui`, alors que la CI ne lance que `--tags @critical` (`release-gate.yml:645`, `ci.yml:220`). `e2e/ui/README.md:56` le reconnait : « No CI job selects these tags, so tests outside `@critical` may be out of date ». `mcp-config.feature` a ete ecrite, mais elle n'a jamais ete branchee en CI.
  - **Le perimetre bloquant (`@critical`, 5 features) ne couvre aucune nouveaute 0.7.3.** 4 de ces 5 features (`analysis`, `batch-progress`, `rechunk`, `delete`) pilotent encore la surface legacy `/studio`. Il faut `STUDIO_MODE_ENABLED=true` (`release-gate.yml:608-611`, commentaire « until those tests are rewritten [...] in 0.7.0 », toujours pas fait en 0.7.3). La cinquieme, `doc-tab-chunk-mode`, est un test API deguise.
  - **Aucune preuve d'execution pour cet arbre.** `e2e-ui` de `ci.yml` ne tourne que sur un push sur `main` (skipped sur le run `41452006012`). L'e2e UI du Release Gate `41452005966` etait en cours a l'heure de l'audit. Le dernier rapport local (`e2e/ui/target/karate-reports/karate-summary-json.txt`, 2026-07-16) ne contient que `demo.ask-demo`.
  - L'item 9.1.3 (« Les tests e2e Karate UI passent ») n'est donc pas demontre, et il est faux pour la suite complete. La baseline le notait conforme sans l'avoir execute, alors que les trois specs obsoletes existaient deja. Une partie du delta vient donc de cette lecture plus stricte, pas d'une regression.
- **Regle violee** : 9.1.3 — Les tests e2e Karate UI passent.
- **Remediation** :
  1. Supprimer, ou reecrire contre `/docs/:id`, `doc-ingest-view`, `doc-chunk-view` et `doc-strategy-popover`. L'ingestion est depreciee, la suppression suffit pour `doc-ingest-view`.
  2. Passer `@critical` au moins sur `mcp-config.feature` (scenario « Turn the server off and back on ») et `docs-batch-analysis.feature`. Ou ajouter au Release Gate un job `--tags @regression` sur `classpath:navigation`.
  3. Rebaser les `@critical` `/studio` sur `/docs` et retirer `STUDIO_MODE_ENABLED=true` du gate.
  4. Joindre au gate le rapport Karate UI du run `41452005966` une fois termine.

### [MIN] Le merge des batches (#344) n'est verifie par aucun gate du release

- **Localisation** : `document-parser/tests/test_batch_merge.py:17` ; `document-parser/pyproject.toml:28` (groupe `dev`) et `:34-35` (`docling` seulement dans `local`) ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:85` ; `document-parser/infra/serve_converter.py:77` ; `document-parser/services/analysis_service.py:448` ; `e2e/api/src/test/resources/analyses/batch-progress.feature:38-50` ; `.github/workflows/docling-compat.yml:8-10`
- **Constat** :
  - Les 5 tests du merge reel (`_merge_batches_sync` : concatenation `DoclingDocument.concatenate`, page details reconstruits contre les refs renumerotes, deux replis) passent en local. En CI, `test_batch_merge.py:17` saute le module entier : la CI n'installe que `--group dev` (`ci.yml:41`, `release-gate.yml:85`), et `docling` n'est que dans le groupe `local` (`pyproject.toml:34-35`). Le log du run `41452006012` montre `collected 1338 items / 3 skipped`.
  - Le scenario e2e « Batched conversion keeps the document structure (#344) » (`batch-progress.feature:38`) tourne en CI contre `CONVERSION_MODE: remote`. Or `ServeConverter.supports_page_batching = False` (`serve_converter.py:77`), donc `analysis_service.py:448` ne batch jamais. Le scenario passe sans exercer le merge qu'il nomme.
  - `docling-compat.yml` installe bien `--group local`, mais il ne tourne que sur `schedule`/`workflow_dispatch` (`:8-10`), donc sur `main`, et contre la *derniere* version de docling, pas celle epinglee.
  - Resultat : la correction #344, livree dans l'image `local`, pourrait regresser sur la branche release sans qu'aucun job ne le voie. Le meme angle mort couvre `test_robustness.py` (25 tests) et `test_pipeline_options.py` (33 tests).
- **Regle violee** : 9.3.4 (partiel) — les tests d'integration testent le flux reel.
- **Remediation** : ajouter un job CI `uv sync --group dev --group local` limite a `pytest tests/test_batch_merge.py tests/test_pipeline_options.py tests/test_robustness.py`. A defaut, extraire la projection `_to_conversion_result` / `concatenate` (qui ne depend que de `docling-core`, deja installe) hors de `infra/local_converter.py`, pour que ces tests ne dependent plus de `docling`. Documenter dans `batch-progress.feature` que le scenario n'exerce le merge qu'en mode `local`.

### [MIN] Les endpoints HTTP `document_versions` n'ont aucun test au niveau API (baseline, inchange)

- **Localisation** : `document-parser/api/document_versions.py:51` (GET `/{doc_id}/versions`), `:63` (POST `.../restore`) ; `document-parser/tests/test_version_service.py`
- **Constat** : inchange. `grep -rln "/versions" tests/` ne renvoie rien. `_to_response` et le mapping `_raise_for` ne sont exerces que par `doc-history-drawer.feature`, `@ui @regression`, donc jamais en CI (voir MAJ). Le happy path reste couvert au niveau service.
- **Regle violee** : 9.2.1 (partiel).
- **Remediation** : `test_document_versions_api.py` sur le modele de `test_mcp_config_api.py` (service reel + repo fake).

### [MIN] La logique de `LocalChunker` n'est pas testee ; un commentaire renvoie a un fichier inexistant (baseline, inchange)

- **Localisation** : `document-parser/tests/test_chunking.py:486` ; `document-parser/infra/local_chunker.py`
- **Constat** : inchange. Le commentaire affirme toujours « Real chunker integration is covered by ``test_local_chunker.py`` », or `tests/test_local_chunker.py` n'existe pas.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel).
- **Remediation** : ajouter le test promis sur un `document_json` fixe, sans reseau, ou corriger le commentaire.

### [INFO] Le switch live du MCP n'est couvert de bout en bout par aucun test execute en CI

- **Localisation** : `document-parser/bootstrap/builder.py:239-246` ; `document-parser/tests/test_mcp_config_api.py:54-73` ; `document-parser/tests/test_mcp_mount.py:75-101` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:64`
- **Constat** : chaque moitie est bien testee. Cote API, `PUT enabled=false` stocke et appelle `apply_config` (`test_mcp_config_api.py`, avec un `applied.append` factice). Cote transport, `mcp_serving=False` donne un 503 et le retour a `True` redonne un 200 sans remount (`test_mcp_mount.py`, via `wire_state`). La glue de la composition root, `apply_config` -> `self._update(document_tools=..., mcp_serving=config.enabled)` (`builder.py:239-246`), n'est en revanche exercee que par `mcp-config.feature:64`, jamais lancee en CI. Si cette closure ou ce nom de slot etait renomme, aucun test rapide ne le verrait.
- **Remediation** : un test `AppStateBuilder._wire_mcp` avec repo en memoire (PUT `enabled=false` puis POST `/mcp` -> 503), ou passer ce scenario Karate en `@critical`.

### [INFO] Aucun scenario e2e API pour les nouvelles routes ; le proxy nginx `/mcp` n'est pas verifie

- **Localisation** : `e2e/api/src/test/resources/` ; `frontend/nginx.conf.template:29`
- **Constat** : `grep -rln "summaries|analyses/import|/pages|config/mcp|/mcp" e2e/api` ne renvoie rien. Les six nouvelles routes (`/api/analyses/summaries`, `/api/analyses/import`, `/api/documents/{id}/pages`, `/api/config/mcp`, `/api/mcp/server`, `/mcp`) sont bien couvertes par TestClient, mais jamais a travers la stack conteneurisee. Le `location = /mcp` de nginx (`nginx.conf.template:29`, `Host $http_host` confronte a `MCP_ALLOWED_HOSTS`) n'est touche que par `mcp-config.feature`, hors CI.
- **Remediation** : ajouter `e2e/api/.../mcp/handshake.feature` (`@regression`) : `initialize` sur `/mcp` via `baseUrl` -> 200, puis GET `/api/mcp/server`. Ajouter aussi un scenario `summaries`/`pages` dans `analyses/` et `documents/`.

### [INFO] Import Docling (#359) : le 400 « document invalide » n'est pas teste en HTTP, et le flux client n'a aucun test

- **Localisation** : `document-parser/api/analyses.py:82-83` ; `document-parser/tests/test_api_endpoints.py:553-566` ; `frontend/src/features/document/ui/DocumentUpload.vue:117-119`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:76-77`, `frontend/src/features/analysis/ui/AnalysisImportButton.vue:49-50`
- **Constat** : la mauvaise entree est testee cote adaptateur (`test_docling_importer.py`, `{}` -> `ValueError`) et cote service (`test_analysis_service.py:206`, aucun insert). En revanche, la branche HTTP `else 400` de `analyses.py:83` n'est jamais atteinte : les tests API couvrent seulement le 400 `documentId` vide et le 404. Cote frontend, le meme flux (`JSON.parse`, appel `importAnalysis`, affichage d'erreur) est copie dans trois composants et n'a aucun test. `DocumentUpload.vue:117-119` televerse le PDF *avant* l'import : un import refuse laisse un document sans analyse, et aucun test ne fixe ce comportement. Aucune feature e2e ne couvre l'import.
- **Remediation** : un test API ou le service leve `ValueError("Invalid Docling document: ...")` -> 400. Extraire le flux client dans un composable teste.

### [INFO] Deux branches 413 secondaires restent non couvertes (baseline, inchange)

- **Localisation** : `document-parser/api/documents.py:86` (garde de flux sur `total`) ; `document-parser/services/graph_service.py:93-94` (`GraphTooLargeError`)
- **Constat** : inchange. Le 413 principal reste teste (`test_api_endpoints.py:193`, `test_upload_rejects_oversized_content_length`). Les deux branches secondaires ne le sont pas (`grep "truncated=True|GraphTooLarge" tests/` ne renvoie rien).
- **Remediation** : test flux (`file.size` absent, corps > limite) et `test_graph_api` avec `truncated=True`.

### [INFO] Preuve d'execution e2e : l'API est verte en CI, l'UI n'est pas prouvee (baseline « non re-execute », change)

- **Localisation** : `.github/workflows/ci.yml:135-137` ; runs `41421174625`, `41452006012`, `41452005966`
- **Constat** : changement depuis la baseline, on dispose maintenant de preuves CI. La suite e2e API complete (`@smoke,@regression,@e2e`) passe sur l'arbre audite : 36 + 2 scenarios, 0 echec, run `41421174625` sur `3f1bcb4`, arbre identique a 02adc68. Le run CI propre a 02adc68 (PR #366 vers `main`) n'a lance que `@smoke` : `ci.yml:135-137` ne passe en scope complet que si `base_ref` est `release/*`. Le Release Gate `41452005966` etait en cours, ses jobs e2e non conclus. Hors perimetre 09 : son job « Security scan — remote » etait deja en `failure` (voir audit 10).
- **Remediation** : relever les rapports `karate-api-reports` / `karate-ui-reports` du run `41452005966` avant le GO final.

### [INFO] RuntimeWarning « coroutine never awaited » dans `test_pipeline_options.py` (baseline, inchange)

- **Localisation** : `document-parser/tests/test_pipeline_options.py:365`, `:375`, `:539`
- **Constat** : inchange : 5 warnings dans le run local. Ces tests dependent de `docling`, donc les warnings n'apparaissent pas en CI, ou le module n'est pas collecte.
- **Remediation** : fermer la coroutine passee au mock de `create_task`.

### [INFO] Les 15 tests Neo4j ne tournent dans aucune CI ; la docstring affirme le contraire (baseline, precise)

- **Localisation** : `document-parser/tests/neo4j/conftest.py:4` ; `.github/workflows/*.yml`
- **Constat** : la baseline renvoyait a l'audit 10 pour verifier que « la CI demarre Neo4j ». Verification faite : aucun workflow ne declare de service Neo4j, et `git log -S neo4j -- .github/workflows` ne renvoie rien, il n'y en a donc jamais eu. Les 15 tests sont skippes aussi en CI (log du run `41452006012`). La docstring `conftest.py:4` (« CI spins up `neo4j:5.15-community` alongside the job ») est fausse. Les skips restent justifies (9.3.2 conforme), et le writer graphe sert surtout l'ingestion, depreciee.
- **Remediation** : corriger la docstring. Ajouter un service Neo4j en CI seulement si le graphe survit a la suppression de l'ingestion (0.8.0).

### [INFO] Reasoning : toujours aucune couverture dans le gate

- **Localisation** : `.github/workflows/release-gate.yml:250` ; `.github/workflows/release.yml:73` ; `document-parser/tests/test_docling_agent_reasoning.py:108-126`
- **Constat** : toujours vrai depuis la gate 0.7.0. Le gate construit `remote` et `local` avec `build-args: APP_VERSION` seulement (`release-gate.yml:250`). L'image publiee, elle, est construite avec `WITH_REASONING=true` (`release.yml:73`). L'adaptateur `docling-agent` n'est teste qu'avec des modules factices (`test_docling_agent_reasoning.py:108-126`). Aucun job e2e reasoning. Avec `ASK_MODE=hidden` par defaut, Ask n'est plus visible sans opt-in, ce qui reduit l'exposition sans combler le trou.
- **Remediation** : voir audit 10 (job gate `WITH_REASONING=true` + smoke `POST /api/documents/{id}/reasoning` != 503).

---

## Delta vs 0.7.0

Score : **100 (re-audit 0.7.0) -> 93** (**-7**). Items conformes 14/14 -> 13/14.

| Ecart baseline (re-audit 0.7.0) | Statut en 0.7.3 |
|---------------------------------|-----------------|
| [MAJ leve en re-audit] 413 non teste | **Toujours corrige** — `test_api_endpoints.py:193` present et vert |
| [MIN] Endpoints `document_versions` sans test API | **Toujours present** |
| [MIN] Orchestration `ExportService` non testee | **Corrige** — `tests/test_export_service.py` construit le vrai `ExportService` (repos fakes) : MD/JSON/PDF, analyse demandee vs derniere, refus inconnue / autre document / non terminee |
| [MIN] `LocalChunker` + commentaire vers `test_local_chunker.py` | **Toujours present** (`test_chunking.py:486`) |
| [INFO] Branches 413 secondaires | **Toujours present** |
| [INFO] Suite e2e non re-executee | **Change** — e2e API complete verte en CI sur l'arbre audite ; e2e UI non prouvee (devient un element du MAJ) |
| [INFO] RuntimeWarning `test_pipeline_options.py` | **Toujours present** (5 warnings) |
| [INFO] 15 skips Neo4j | **Precise** — aucune CI ne lance Neo4j ; la docstring est fausse |
| (gate 0.7.0, hors rapport 09) Specs UI pilotant l'UI chunk supprimee | **Toujours present** — integre au MAJ |
| (gate 0.7.0, hors rapport 09) Zero couverture reasoning dans le gate | **Toujours present** |

Nouveaux ecarts : 1 MAJ (9.1.3 — e2e UI, incluant les 8 features 0.7.3 jamais branchees), 1 MIN (#344 non gate), 3 INFO (glue du switch MCP, pas d'e2e API sur les nouvelles routes, import #359).
Origine des -7 : l'item 9.1.3 (poids 2) passe a Non. Les specs obsoletes existaient deja en 0.7.0, donc ce delta tient autant a une lecture plus stricte de l'item qu'a une regression. Le fait nouveau de 0.7.3 : aucune des features UI qui couvrent ses nouveautes ne tourne en CI.

---

## Points positifs

- **Suites vertes et rapides** : 1386 tests backend (49 s en local, 29 s en CI) et 545 tests frontend (3,9 s), 0 echec. +537 / +113 tests depuis 0.7.0, aucun test supprime.
- **Le serveur MCP est la fonctionnalite la mieux testee de la release** : 458 tests, sur un vrai `mcp.Client` en memoire et non un mock. Ils fixent le contrat publie (champs de sortie, enums), le budget de la surface modele (3 400 caracteres, chaque regle enoncee une seule fois), la neutralisation du contenu non fiable (un document ne peut pas fermer son delimiteur) et les bornes non relevables par le client. S'y ajoutent les codes du transport : 503 JSON-RPC, 421 hors allow-list, allow-list *livree* testee telle quelle.
- **Le switch on/off est teste comme un comportement**, pas comme un flag : 503 sans atteindre le serveur, retour a 200 sans remount, passage avant boot, refus d'allumer un serveur que `MCP_ENABLED` n'a pas monte.
- **Tests API sur le service reel** : `test_mcp_config_api.py` cable le vrai `McpConfigService` sur un repo en memoire et fixe le contrat camelCase champ par champ, sources (`env`/`db`) comprises.
- **Nouvelles routes couvertes sur leurs chemins d'erreur** : `/pages` (404 document, 404 fichier, 422 PDF illisible), `/summaries` (contenu volumineux absent du payload), import (400/404), `/api/config/mcp` (400/403/422).
- **Determinisme tenu** : aucun `sleep` dans les nouveaux tests, polling frontend sous `vi.useFakeTimers()`, aucune horloge ni aucun reseau dans les fichiers modifies. Les deux `asyncio.sleep` reels du backend sont anterieurs et non porteurs d'assertion temporelle fragile.
- **Discipline** : zero `.only` / `fdescribe` / `fit` / `xit`, zero skip non justifie. Les `@ignore` Karate sont des fragments reutilisables. Les noms de test decrivent le comportement (« turning it back on drops the override », « a document cannot close its own delimiter »).
- **Un MIN de la baseline est leve** : `ExportService` a enfin un test d'orchestration reel.

---

## Verdict partiel : GO

Score **93/100**, **0 CRITICAL**, **1 MAJOR** (sous le seuil de blocage de 3). Les suites unitaires sont vertes : 1386/1386 backend executes, 545/545 frontend. Chaque nouveaute 0.7.3 est couverte sur son chemin critique par des tests rapides, et le MCP l'est de facon exemplaire. Le MAJOR porte sur le filet e2e UI. Trois specs pilotent toujours une UI supprimee, et les huit features ecrites pour 0.7.3 (dont `mcp-config.feature`, seule preuve bout en bout du switch live) ne tournent dans aucun workflow. Il entre au plan de remediation du cycle : passer en `@critical` ou en job de regression au moins `mcp-config` et `docs-batch-analysis`, purger les specs obsoletes, puis relever le rapport Karate UI du Release Gate `41452005966` avant le GO final. Le MIN #344 merite un traitement rapide : la correction n'est gardee par aucun job.

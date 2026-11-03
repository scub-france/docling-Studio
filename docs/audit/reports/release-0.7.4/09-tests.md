# Rapport d'audit : Tests

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag v0.7.3 `2b4ef25` + 2 commits README `0465e70`, `1de1929`)
**Baseline** : audit 0.7.3 (`release/0.7.3` @ `02adc68`, 93/100). Le re-audit 0.7.3 n'a pas re-note 09 (« 93 inchange », un test ajoute).

**Perimetre du delta** : `git diff --stat 2b4ef25 HEAD` ne touche que `README.md` et deux GIF. Depuis `02adc68`, l'arbre de l'audit 0.7.3, la remediation 0.7.3 (#367, #368) a modifie un seul fichier de test (`tests/test_analysis_service.py:225`, +24 lignes) et aucun fichier de `e2e/`. Cote frontend, elle a modifie 6 fichiers, sans toucher aux pages ni aux composants que pilotent les specs e2e (`git diff --stat 02adc68..HEAD -- frontend/src e2e`). Le code teste est donc celui de v0.7.3. Ce rapport re-verifie chaque ecart de la baseline et fait l'inventaire exhaustif de la suite Karate UI, que la baseline n'avait que survolee.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 11 |

Detail du calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**. Le seul item non conforme est 9.1.3 (poids 2).

### Metriques d'execution

| Suite | Commande | Resultat | Duree |
|-------|----------|----------|-------|
| Backend, local (coordinateur) | `uv run pytest tests/ -q` (depuis `document-parser/`, groupe `dev` seul) | **1323 passed, 19 skipped** : 15 Neo4j absent, 4 `docling library not installed` | 39,8 s |
| Frontend, local (coordinateur) | `npx vitest run` (depuis `frontend/`) | **53 fichiers, 545 passed** | 6,2 s |
| Backend, collecte locale (cet audit) | `.venv/bin/python -m pytest --collect-only -q` | **1339 tests collectes**. Le venv local n'a pas `docling` (`ModuleNotFoundError`), comme la CI : 3 modules sont sautes a la collecte | 3,3 s |
| Backend, Release Gate (run `41468347487`, job *Unit tests* `125355048341`, commit `59674be`) | `uv run pytest tests/ -v --tb=short` | **1323 passed, 19 skipped** (`collected 1339 items / 3 skipped`) | 32,25 s |
| Backend, CI push `main` (run `41477971314`, job `125388469006`, commit `2b4ef25`) | `uv run pytest tests/ -v` | **1323 passed, 19 skipped** | 32,03 s |
| Backend avec docling (*Docling compatibility*, run `41481215664`, `schedule`, `2b4ef25`) | `uv sync --group dev --group local`, puis montee vers docling 2.145.0 / docling-core 2.105.0 | 1402 collectes, **1387 passed, 15 skipped** (Neo4j), 4 warnings | 47,05 s |
| Frontend, Release Gate (meme job) | `npm run test:run` | **53 fichiers, 545 passed** | 6,58 s |
| Frontend, CI push `main` (job `125388469595`) | `npm run test:run` | **53 fichiers, 545 passed** | 5,54 s |
| E2E API Karate, Release Gate (job `125358209008`) | `--tags @smoke,@regression,@e2e` | 12 features / 36 scenarios + 2 smoke = **38, 0 echec** | 143,6 s |
| E2E UI Karate, Release Gate (job `125358209244`) | `--tags @critical` | 5 features x 3 methodes `UIRunner` = **15, 0 echec** | 114,8 s |
| E2E UI Karate, CI push `main` (job `125389223024`) | `--tags @critical` | **15, 0 echec** | 107,4 s |
| E2E UI Karate, suite complete (`testAll` / `testLocal`) | — | **Jamais executee** : aucun workflow ne la lance et aucun rapport n'existe | — |
| Couverture de lignes | — | Non mesuree : ni `pytest-cov` ni provider `@vitest/coverage-*` ne sont declares (`pyproject.toml`, `frontend/package.json`) | — |

- **Validite des preuves CI** : `git diff 59674be 2b4ef25` est vide, et `HEAD` ne differe de `2b4ef25` que par le README et les GIF. Les runs ci-dessus portent donc sur le code audite. Aucun run n'existe encore pour `release/0.7.4` : aucune PR n'est ouverte (`gh api .../pulls`, la derniere est #369).
- **Skips CI (19)** : les 15 tests Neo4j (`tests/neo4j/conftest.py:35`) et `tests/test_serve_converter.py:792` (`skipif(not _has_docling())`). S'y ajoutent les 3 modules sautes a la collecte faute de `docling` : `tests/test_robustness.py:154`, `tests/test_pipeline_options.py:14` et `tests/test_batch_merge.py:17`, tous via `importorskip` avec `reason`. **64 tests ne tournent dans aucun gate** (63 non collectes + 1 skip). Ils passent dans le job planifie *Docling compatibility* sur `main`, avec la derniere version de docling et non la version epinglee.
- **Volume** : backend 1338 -> 1339 tests collectes en CI (+1 : `test_import_deserializes_off_the_event_loop`, `tests/test_analysis_service.py:225`). Frontend 545, inchange. Aucun fichier de test supprime.

| # | Item | Poids | Conforme | Evolution vs 0.7.3 |
|---|------|-------|----------|--------------------|
| 9.1.1 | Tous les tests backend passent | 3 | Oui — 1323 passed / 19 skipped en CI sur l'arbre audite ; run local : voir placeholder | = |
| 9.1.2 | Tous les tests frontend passent | 3 | Oui — 545 passed (53 fichiers) en CI sur l'arbre audite ; run local : voir placeholder | = |
| 9.1.3 | Les tests e2e Karate UI passent | 2 | **Non** — `@critical` vert (15/15), mais 9 features / 11 scenarios pilotent une UI inexistante et 31 scenarios sur 36 ne tournent nulle part (voir MAJ) | = (Non), constat elargi |
| 9.2.1 | Chaque endpoint API a un test happy path | 2 | Oui — 53 routes (51 `APIRouter` + `/api/health` + `/mcp`), toutes couvertes par TestClient sauf les 2 de `document_versions` (MIN) | = |
| 9.2.2 | Cas d'erreur endpoints (400, 404, 413, 429) | 2 | Oui — 413 principal teste (`test_api_endpoints.py:193`) ; 2 branches 413 secondaires en INFO | = |
| 9.2.3 | Services : tests d'orchestration | 2 | Oui — les 21 modules de `services/` sont exerces avec le vrai service (MIN : `LocalChunker`, `docling_pages`) | = (1 MIN nouveau) |
| 9.2.4 | Fonctions domain (bbox, value objects) | 1 | Oui (`test_bbox.py`, `test_models.py`, `test_navigation_domain.py`) | = |
| 9.2.5 | Composants Vue critiques (stores/composables) | 2 | Oui — 12 stores sur 13 et les 2 composables ont un test ; seul `settings/store.ts` n'en a pas (INFO) | = |
| 9.3.1 | Pas de `.only` / `fdescribe` / `fit` | 3 | Oui — aucun (`grep` vide, `xit`/`xdescribe` compris) | = |
| 9.3.2 | Pas de skip sans justification | 1 | Oui — 7 sites de skip, tous justifies par un `reason`, un message ou un commentaire (`tests/neo4j/conftest.py:15-16`) | = |
| 9.3.3 | Tests deterministes | 2 | Oui — le seul test ajoute verifie l'absence de boucle dans le thread de l'import, sans horloge ni `sleep` | = |
| 9.3.4 | Integration teste le flux reel, pas un mock complet | 2 | Oui (MIN #344 partiel, inchange) | = |
| 9.3.5 | Assertions specifiques | 1 | Oui pour les suites unitaires : 66 lignes `is not None` / `toBeTruthy()` (meme volume qu'en 0.7.3) ; l'echantillon verifie (`test_chunk_service.py`, `test_repos.py`) montre des gardes suivies d'assertions precises. Les 3 assertions e2e vides de sens sont rattachees au MAJ | = |
| 9.3.6 | Noms de tests explicites | 1 | Oui | = |

### Inventaire Karate UI (26 features, 36 scenarios, helpers et `demo/` exclus)

Methode : chaque selecteur `data-e2e` des features est cherche dans `frontend/src`. Un hook qui n'existe que dans un composant que rien n'importe, en partant de `app/main.ts`, est compte comme inexistant. Le perimetre CI est verifie dans `.github/workflows/*.yml` : les seules invocations `mvn test -f e2e/ui/pom.xml` sont `ci.yml:217-220` et `release-gate.yml:647-650`, toutes deux avec `--tags @critical`.

| Feature | Tags | Scen. | En CI | Statut |
|---------|------|-------|-------|--------|
| `analyses/analysis.feature` | `@critical @ui` | 1 | Oui (x3) | Vert. Surface legacy `/studio` |
| `analyses/batch-progress.feature` | `@critical @ui` | 1 | Oui (x3) | Vert. `/studio` |
| `analyses/rechunk.feature` | `@critical @ui` | 1 | Oui (x3) | Vert. `/studio` |
| `documents/delete.feature` | `@critical @ui` | 1 | Oui (x3) | Vert. `/studio` |
| `documents/doc-tab-chunk-mode.feature` | `@ui @critical` | 1 | Oui (x3) | Vert. Test API sans navigateur |
| `analyses/analysis-detail.feature` | `@ui @regression` | 1 | **Non** | Selecteurs presents ; assertion vide `:63` |
| `analyses/analysis-parse-hide-boxes.feature` | `@ui @regression` | 1 | **Non** | Selecteurs presents |
| `analyses/analysis-parse-show-all.feature` | `@ui @regression` | 1 | **Non** | Selecteurs presents |
| `analyses/pipeline-options.feature` | `@ui` | 2 | **Non** | Selecteurs presents (`/studio`, flag requis) |
| `documents/doc-viewer.feature` | `@ui @regression` | 1 | **Non** | Selecteurs presents |
| `documents/docs-batch-analysis.feature` | `@ui @regression` | 1 | **Non** | Selecteurs presents |
| `documents/upload.feature` | `@ui` | 2 | **Non** | Selecteurs presents (`/studio`) |
| `documents/error-states.feature` | `@ui` | 2 | **Non** | Selecteurs presents (`/studio`) |
| `documents/doc-ingest-view.feature` | `@ui @regression` | 3 | **Non** | **Obsolete** (`:38`) |
| `documents/_open-launch-modal.feature` | `@ui` | 1 | **Non** | **Obsolete** (`:10`), et helper non `@ignore` |
| `documents/doc-chunk-view.feature` | `@ui @regression` | 1 | **Non** | **Obsolete** (`:31`) |
| `documents/doc-strategy-popover.feature` | `@ui @regression` | 1 | **Non** | **Obsolete** (`:31`) |
| `documents/doc-history-drawer.feature` | `@ui @regression` | 1 | **Non** | **Obsolete** (`:47`) |
| `documents/doc-parse-properties.feature` | `@ui @regression` | 1 | **Non** | **Obsolete** (`:31`) |
| `documents/doc-new-analysis-opens-analysis.feature` | `@ui @regression` | 1 | **Non** | **Obsolete** (`:17`) |
| `navigation/mcp-config.feature` | `@ui @regression` | 3 | **Non** | Selecteurs presents, contrat API conforme (`api/schemas.py:754-781`) |
| `navigation/settings-accordion.feature` | `@ui` | 1 | **Non** | Selecteurs presents |
| `navigation/i18n.feature` | `@ui` | 1 | **Non** | Selecteurs presents |
| `navigation/sidebar.feature` | `@ui` | 2 | **Non** | Scenario 1 **obsolete** (`:14`) ; scenario 2 OK |
| `navigation/reasoning-feature-flag.feature` | `@ui` | 3 | **Non** | Scenario 1 **obsolete** (`:19`) ; scenario 2 vide (`:34`) ; scenario 3 OK |
| `workflows/full-ui-path.feature` | `@ui` | 1 | **Non** | Selecteurs presents (`/studio`) |

Totaux : 5 features / 5 scenarios en CI, **21 features / 31 scenarios hors CI**, dont **9 features / 11 scenarios obsoletes**. Sur les 8 features ecrites pour 0.7.3, 7 ont des selecteurs presents et une est cassee (`doc-new-analysis-opens-analysis`). Cote API, `e2e/api/.../ingestion/ingest-and-verify.feature` (`@e2e @ingestion`) n'est parcourue par aucun runner : `E2ERunner.java:7` ne scanne pas `classpath:ingestion`. C'est documente dans `e2e/CONVENTIONS.md:168` et concerne l'ingestion, depreciee.

---

## Ecarts constates

### [MAJ] La suite e2e Karate UI n'est pas verte dans son ensemble : 9 features pilotent une UI inexistante, et 21 features sur 26 ne tournent dans aucun workflow

**Statut vs 0.7.3** : toujours present, constat elargi. Aucune regression de code depuis 0.7.3, mais la baseline sous-comptait les specs obsoletes : 3 annoncees, 9 reelles.

- **Localisation** :
  - Runners et workflows : `e2e/ui/src/test/java/UIRunner.java:5-23`, `.github/workflows/ci.yml:158`, `:193`, `:220`, `.github/workflows/release-gate.yml:616`, `:650`.
  - Doc : `e2e/ui/README.md:56`.
  - Specs obsoletes : voir le tableau ci-dessous.
- **Constat** :
  - **Perimetre execute.** La CI ne lance que `--tags @critical` (`ci.yml:220`, `release-gate.yml:650`), et le job `e2e-ui` de `ci.yml` ne tourne qu'apres un push sur `main` (`ci.yml:158`). Les 5 scenarios `@critical` sont verts sur l'arbre audite. 4 d'entre eux pilotent encore `/studio`, d'ou `STUDIO_MODE_ENABLED: "true"` (`ci.yml:193`, `release-gate.yml:616`, commentaire « until those tests are rewritten against /docs/:id in 0.7.0 »). Le cinquieme, `doc-tab-chunk-mode`, n'ouvre pas de navigateur. Les 31 autres scenarios ne tournent nulle part, et `e2e/ui/README.md:56` le reconnait : « tests outside `@critical` may be out of date ».
  - **Specs obsoletes, liste exhaustive.** Chacune echoue au premier `waitFor`/`click` cite, sous `UIRunner#testAll` (`UIRunner.java:6-9`) comme sous `#testLocal` (`:19-23`).

    | Spec : premier point de rupture | Element d'UI attendu | Verification dans `frontend/src` | Statut vs 0.7.3 |
    |---------------------------------|----------------------|----------------------------------|-----------------|
    | `documents/doc-ingest-view.feature:38` (scenario 1), `:56` (scenario 2), `:70` (scenario 3) | `[data-e2e=view-switcher]`, `ingest-tab`, `ingest-launch-cta`, `ingest-history`, `ingest-no-stores`, `ingest-no-history` (`:38-46`) | 0 occurrence. `?mode=ingest` et `?mode=compare` sont resolus en `parse` (`shared/routing/modes.ts:35`, `:37`). La premisse du scenario 3, « compare aliases to ingest », est donc fausse | Deja releve (0.7.0, 0.7.3), inchange |
    | `documents/_open-launch-modal.feature:10` | `ingest-launch-cta` ; `ingest-launch-modal` / `-empty` / `-cancel` (`:11`, `:14`, `:20`) | `ingest-launch-cta` : 0 occurrence. Les autres hooks n'existent que dans `pages/IngestLaunchDialog.vue:2`, `:24`, `:81`, que rien n'importe. De plus, ce helper est tague `@ui` (`:1`) et non `@ignore`, et il vit hors de `common/helpers/`, contrairement a `e2e/CONVENTIONS.md:148`. `testAll`/`testLocal` le lancent donc seul, sans `driver` | **Nouveau** (non releve en 0.7.3) |
    | `documents/doc-chunk-view.feature:31` | `chunk-tab` (apres `?mode=chunk`, `:30`) ; `show-labels-toggle` (`:42`) ; `chunks-panel-list` (`:48`) | `chunk-tab` n'existe que dans `pages/DocChunkTab.vue:2`, importe nulle part. `?mode=chunk` est resolu en `parse` (`modes.ts:36`). `show-labels-toggle` : 0 occurrence. `chunks-panel-list` : uniquement dans `features/chunks/ui/ChunksPanel.vue:41`, inatteignable | Deja releve, inchange |
    | `documents/doc-strategy-popover.feature:31` | `chunk-tab`, `chunks-panel` (`:32`), `strategy-btn` (`:39`), `strategy-popover` / `-form` / `-max-tokens` / `-apply` (`:40-47`) | Memes composants morts. `strategy-btn` n'existe qu'en classe CSS (`features/chunks/ui/StrategyPopover.vue:79`), jamais en `data-e2e`, et `StrategyPopover.vue` est lui-meme inatteignable | Deja releve, inchange |
    | `documents/doc-history-drawer.feature:47` | `parse-tab` sur `/docs/:id` (`:46`), puis `history-btn` (`:48`), `history-drawer` (`:49`) | `/docs/:id` monte `DocWorkspacePage.vue`, qui n'affiche qu'un en-tete, la barre de progression et `PagePreviewWithOverlay` (template `:1-54`, imports `:70-72`). `parse-tab` (`pages/DocParseTab.vue:2`) n'existe que sur `/analyses/:id` (`AnalysisDetailPage.vue:43`). `history-btn` : 0 occurrence. `history-drawer` : uniquement dans `features/document/ui/HistoryDrawer.vue:13`, importe nulle part | **Nouveau** (deja obsolete a `02adc68`) |
    | `documents/doc-parse-properties.feature:31` | `parse-tab` sur `/docs/:id` (`:30`) | Meme cause : la vue Parse n'est plus sur `/docs/:id`. Les hooks suivants (`element-properties`, `tree-rail`, `properties-edit-btn`) existent, mais seulement sur `/analyses/:id` | **Nouveau** (deja obsolete a `02adc68`) |
    | `documents/doc-new-analysis-opens-analysis.feature:17` | `[data-e2e=workspace-new-analysis]` sur `/docs/:id` (`:16-18`) | 0 occurrence. Le hook a ete ajoute par #342 (`bd779d7`, « The button gets a data-e2e hook for the Karate UI scenario »). #359 (`ec3eb00`, 2026-10-15) l'a supprime en remplacant le bouton par `DocumentActionsMenu.vue`, dont le declencheur et les items (`:4-33`) n'ont aucun `data-e2e`. La logique #342 reste couverte en unitaire (`pages/DocWorkspacePage.logic.test.ts`) | **Nouveau** : cassee pendant le cycle 0.7.3. La baseline la comptait parmi les 8 features 0.7.3 valides |
    | `navigation/sidebar.feature:14` (scenario 1) | `nav-studio`, `nav-documents` (`:18`), `nav-history` (`:22`) | La sidebar n'a que `home`, `docs`, `analyses`, `runs`, `settings` (`shared/ui/AppSidebar.vue:126-163`). Le scenario 2 (`:33`) reste valide | **Nouveau** |
    | `navigation/reasoning-feature-flag.feature:19` (scenario 1) | `nav-studio`, `nav-documents` (`:19-20`) | Meme cause | **Nouveau** |

  - **Trois assertions ne peuvent pas echouer.**
    - `analyses/analysis-detail.feature:63` : `assert !exists('[data-e2e=parse-new-analysis]')`. Ce hook n'existe nulle part dans `frontend/src`, et `git log -S` ne le trouve que dans `e2e/`. L'assertion ne detecterait donc pas le retour d'un bouton « New analysis » sur la page de detail.
    - `navigation/reasoning-feature-flag.feature:24` et `:34` : `nav-reasoning` compte 0. La sidebar n'a plus d'entree reasoning, quel que soit le flag (`AppSidebar.vue:126-163`), et `/reasoning` redirige vers `/docs` (`app/router/routes.ts:63-66`). Le scenario 2 passe donc sans rien verifier du flag qu'il nomme.
  - **Correction de la baseline.** Le rapport 0.7.3 comptait 3 specs obsoletes et 8 features 0.7.3 « jamais executees ». L'inventaire exhaustif trouve 9 features obsoletes (11 scenarios), toutes deja obsoletes a `02adc68`, puisque le frontend concerne n'a pas change depuis. Parmi elles, la feature #342 a ete cassee par #359 avant le gel 0.7.3. C'est exactement le risque que le MAJ 0.7.3 decrivait : une spec que personne n'execute derive sans signal.
  - Ce qui est prouve : le perimetre bloquant (`@critical`) est vert sur l'arbre audite (Release Gate `41468347487`, CI `main` `41477971314`). L'item 9.1.3 vise toutefois la suite Karate UI dans son ensemble, et elle ne peut pas passer en l'etat.
- **Regle violee** : 9.1.3 — Les tests e2e Karate UI passent.
- **Remediation** (effort ; risque de regression produit) :
  1. **Supprimer** `doc-ingest-view.feature`, `_open-launch-modal.feature`, `doc-chunk-view.feature`, `doc-strategy-popover.feature` et `doc-history-drawer.feature`. Les vues Ingest, Chunk et History n'existent plus. (S ; nul, aucun code produit touche.)
  2. **Rebaser sur `/analyses/:id`** `doc-parse-properties.feature` : `analyze.feature` renvoie `jobId`, comme dans `analysis-parse-show-all.feature:15-19`. (S ; nul.)
  3. **Reparer `doc-new-analysis-opens-analysis.feature`** : ajouter `data-e2e="doc-actions-trigger"` et `data-e2e="doc-actions-start"` dans `DocumentActionsMenu.vue:4` et `:25`, puis ouvrir le menu avant de cliquer. (S ; quasi nul, attributs seulement.)
  4. **Mettre a jour la navigation** : `sidebar.feature` vers `nav-docs` / `nav-analyses` / `nav-runs` ; `reasoning-feature-flag.feature`, retirer les scenarios 1-2 ou les reecrire sur la vue Parse (`DocParseTab.vue:211`) ; `analysis-detail.feature:63`, asserter sur un hook reel, ou retirer la ligne. (S ; nul.)
  5. **Brancher le reste en CI** : ajouter au Release Gate `-Dtest='UIRunner#testAll' -Dkarate.options="--tags @critical,@regression"`. Une seule methode, donc plus de triple execution (voir INFO). (M ; pas de risque produit, mais un gate plus long de plusieurs minutes, car `docs-batch-analysis` et `doc-new-analysis` attendent jusqu'a 300 s, et un risque de flakiness.)
  6. **Dette 0.7.0** : rebaser les 4 `@critical` `/studio` sur `/docs` et `/analyses`, puis retirer `STUDIO_MODE_ENABLED=true` (`ci.yml:193`, `release-gate.yml:616`). (L ; faible.)

### [MIN] Le merge des batches (#344) n'est verifie par aucun gate du release

**Statut vs 0.7.3** : toujours present dans les gates, mais une preuve d'execution hors gate existe desormais.

- **Localisation** : `document-parser/tests/test_batch_merge.py:17` ; `document-parser/pyproject.toml:29` (groupe `dev`) et `:35-36` (`docling` seulement dans `local`) ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:85` ; `document-parser/infra/serve_converter.py:77` ; `document-parser/services/analysis_service.py:451` ; `e2e/api/src/test/resources/analyses/batch-progress.feature:38` ; `.github/workflows/docling-compat.yml:8-10`, `:44`
- **Constat** :
  - Le constat de la baseline tient. Les gates n'installent que `--group dev`, donc `test_batch_merge.py` (5 tests), `test_pipeline_options.py` et `test_robustness.py` ne sont pas collectes (`collected 1339 items / 3 skipped`, job `125355048341`).
  - Le scenario e2e #344 tourne en `CONVERSION_MODE: remote`, ou `supports_page_batching = False` (`serve_converter.py:77`) : `analysis_service.py:451` ne batch jamais.
  - **Fait nouveau** : le job planifie *Docling compatibility* (run `41481215664`, sur `2b4ef25`, meme code) a execute ces 5 tests et les a passes (1387 passed). Ce run tourne apres le merge sur `main`, et contre docling 2.145.0 et non la version epinglee 2.121.0 (`docling-compat.yml:44`, `--upgrade`). Il ne garde donc pas la branche release.
- **Regle violee** : 9.3.4 (partiel).
- **Remediation** : ajouter un job de gate `uv sync --frozen --group dev --group local`, limite a `pytest tests/test_batch_merge.py tests/test_pipeline_options.py tests/test_robustness.py`, sans `--upgrade`. (S-M ; nul, la CI seule change.)

### [MIN] Le mapping des pages Docling (`extract_pages_detail`, chemin de l'import #359) n'a aucun test execute en CI

**Statut vs 0.7.3** : nouveau constat. Le code est inchange depuis 0.7.3.

- **Localisation** : `document-parser/infra/docling_pages.py:48-120` ; consommateurs `infra/docling_importer.py:10` (#359) et `infra/local_converter.py:33` ; `document-parser/tests/test_docling_importer.py:9-14`
- **Constat** : `extract_pages_detail` porte la logique qui transforme un `DoclingDocument` en pages et elements positionnes :
  - bbox converties en origine haut-gauche ;
  - type d'element par classe ;
  - Markdown des tableaux ;
  - repli US Letter quand une page manque dans `document.pages` ;
  - compteur d'elements ignores.

  `grep -rn "extract_pages_detail|_process_content_item" tests/` ne renvoie rien. En CI, la fonction n'est appelee que par `test_deserialize_returns_conversion_result`, sur un document vide, sans page ni element. Le seul test qui l'exerce sur du contenu est `test_batch_merge.py` (`test_rebuilds_the_page_details_against_the_merged_refs`), saute en CI (MIN precedent). Une regression sur les bbox d'une analyse importee ne serait vue par aucun gate.
- **Regle violee** : 9.2.3 / 9.2.4 (partiel).
- **Remediation** : un test sur un `DoclingDocument` construit en memoire avec `docling-core`, deja installe en CI, puisque `test_docling_importer.py:4` l'importe. Il couvrirait une page dimensionnee, un texte avec `prov`/`bbox`, un tableau, et un element sur une page absente (repli), avec des assertions sur la bbox convertie, les types et `skipped`. (S ; nul.)

### [MIN] Les endpoints HTTP `document_versions` n'ont aucun test au niveau API

**Statut vs 0.7.3** : inchange (baseline 0.7.0).

- **Localisation** : `document-parser/api/document_versions.py:51` (GET `/{doc_id}/versions`), `:63` (POST `.../restore`) ; `document-parser/tests/test_version_service.py`
- **Constat** : `grep -rln "/versions|/restore" tests/` ne renvoie rien. Le happy path et les erreurs sont couverts au niveau service (`test_version_service.py:98-143`), mais `_to_response` et `_raise_for` ne sont exerces par aucun test. La seule spec e2e qui les touchait, `doc-history-drawer.feature`, est obsolete (MAJ). Cote frontend, `HistoryDrawer.vue`, seul consommateur visuel de `document/api.ts:76-81`, est importe nulle part.
- **Regle violee** : 9.2.1 (partiel).
- **Remediation** : `test_document_versions_api.py` sur le modele de `test_mcp_config_api.py` (service reel, repo fake). (S ; nul.)

### [MIN] La logique de `LocalChunker` n'est pas testee ; un commentaire renvoie a un fichier inexistant

**Statut vs 0.7.3** : inchange (baseline 0.7.0).

- **Localisation** : `document-parser/tests/test_chunking.py:486` ; `document-parser/infra/local_chunker.py`
- **Constat** : le commentaire affirme toujours « Real chunker integration is covered by ``test_local_chunker.py`` », or ce fichier n'existe pas. `infra/local_chunker.py` n'est importe que par `test_serve_converter.py:838-848`, qui verifie seulement le cablage (`isinstance`).
- **Regle violee** : 9.2.3 / 9.3.4 (partiel).
- **Remediation** : ajouter le test promis sur un `document_json` fixe, sans reseau, ou corriger le commentaire. (S ; nul.)

### [INFO] La glue du switch live MCP n'est couverte par aucun test execute en CI

**Statut vs 0.7.3** : inchange.

- **Localisation** : `document-parser/bootstrap/builder.py:240-246` ; `document-parser/tests/test_mcp_config_api.py:58-75` ; `document-parser/tests/test_mcp_mount.py:75-101` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:64`
- **Constat** : l'API (`applied.append` factice) et le transport (503 et retour a 200 via `wire_state`) sont testes chacun de leur cote. La closure `apply_config` -> `self._update(document_tools=..., mcp_serving=config.enabled)` ne l'est que par `mcp-config.feature:64`, qui ne tourne pas en CI. Ses selecteurs sont pourtant valides.
- **Remediation** : un test `AppStateBuilder` avec repo en memoire (PUT `enabled=false` puis POST `/mcp` -> 503), ou inclure `mcp-config.feature` dans le job propose au MAJ.

### [INFO] Aucun scenario e2e API pour les routes 0.7.3 ; le proxy nginx `/mcp` n'est pas verifie

**Statut vs 0.7.3** : inchange.

- **Localisation** : `e2e/api/src/test/resources/` ; `frontend/nginx.conf.template:29` ; `e2e/api/src/test/java/E2ERunner.java:7`
- **Constat** : `grep -rlE "summaries|analyses/import|/pages|config/mcp|/mcp" e2e/api/src/test/resources` ne renvoie rien. Le `location = /mcp` de nginx n'est touche que par `mcp-config.feature`, hors CI. Par ailleurs, `ingestion/ingest-and-verify.feature` n'est scanne par aucun runner (`E2ERunner.java:7`). C'est assume et documente (`e2e/CONVENTIONS.md:168`).
- **Remediation** : `e2e/api/.../mcp/handshake.feature` (`@regression`) avec `initialize` sur `/mcp` via `baseUrl`, plus un scenario `summaries` / `pages`.

### [INFO] Import Docling (#359) : le 400 « document invalide » n'est pas teste en HTTP, et le flux client n'a aucun test

**Statut vs 0.7.3** : inchange. Point positif : le passage en `asyncio.to_thread` (`services/analysis_service.py:180`) est desormais fixe par `tests/test_analysis_service.py:225`.

- **Localisation** : `document-parser/api/analyses.py:84` ; `document-parser/tests/test_api_endpoints.py:553-566` ; `frontend/src/features/document/ui/DocumentUpload.vue:117-119`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:76-77`, `frontend/src/features/analysis/ui/AnalysisImportButton.vue:49-50`
- **Constat** :
  - La branche `else 400` de `analyses.py:84` n'est jamais atteinte : seuls le 400 `documentId` vide et le 404 sont testes.
  - Le flux client (`JSON.parse`, `importAnalysis`, affichage d'erreur) est copie dans trois composants, sans aucun test.
  - `DocumentUpload.vue:118` televerse le PDF avant l'import (`:119`) : un import refuse laisse un document sans analyse, et aucun test ne fixe ce comportement.
- **Remediation** : un test API ou le service leve `ValueError("Invalid Docling document: ...")` -> 400. Extraire le flux client dans un composable teste.

### [INFO] Deux branches 413 secondaires restent non couvertes

**Statut vs 0.7.3** : inchange.

- **Localisation** : `document-parser/api/documents.py:86-87` (garde de flux sur `total`) ; `document-parser/services/graph_service.py:94` (`GraphTooLargeError`, `http_status = 413` en `:51`)
- **Constat** : `grep -rn "GraphTooLarge|truncated=True" tests/` ne renvoie rien. Le 413 principal reste teste (`test_api_endpoints.py:193-205`).
- **Remediation** : un test de flux (`file.size` absent, corps > limite) et `test_graph_api` avec un payload au-dela de `max_pages`.

### [INFO] RuntimeWarning « coroutine never awaited » dans `test_pipeline_options.py`

**Statut vs 0.7.3** : inchange.

- **Localisation** : `document-parser/tests/test_pipeline_options.py:365`, `:375`
- **Constat** : `asyncio.create_task` est patche par un `MagicMock`, qui recoit la coroutine `_run_analysis` sans jamais l'attendre. Le run *Docling compatibility* `41481215664` affiche 4 warnings, dont `coroutine 'AnalysisService._run_analysis' was never awaited`. Ils sont invisibles dans les gates, ou le module n'est pas collecte.
- **Remediation** : `mock_task.side_effect = lambda coro: coro.close()`.

### [INFO] Les 15 tests Neo4j ne tournent dans aucune CI ; la docstring affirme le contraire

**Statut vs 0.7.3** : inchange.

- **Localisation** : `document-parser/tests/neo4j/conftest.py:4` ; `.github/workflows/*.yml`
- **Constat** : la docstring dit « CI spins up `neo4j:5.15-community` alongside the job ». `grep -rn neo4j .github/workflows/` ne renvoie rien, et les 15 tests sont skippes dans tous les runs releves ci-dessus.
- **Remediation** : corriger la docstring (1 ligne).

### [INFO] Reasoning : toujours aucune couverture dans le gate

**Statut vs 0.7.3** : inchange.

- **Localisation** : `.github/workflows/release-gate.yml:252` ; `.github/workflows/release.yml:73` ; `document-parser/tests/test_docling_agent_reasoning.py:104-128`
- **Constat** :
  - Le gate construit les images avec `build-args: APP_VERSION` seulement, alors que l'image `local` publiee active `WITH_REASONING=true`.
  - L'adaptateur `docling-agent` n'est teste qu'avec des modules factices injectes dans `sys.modules`.
- **Remediation** : voir l'audit 10 (job gate `WITH_REASONING=true` + smoke `POST /api/documents/{id}/reasoning` != 503).

### [INFO] Le check « Unit tests » du Release Gate ne peut pas echouer sur un test rouge

**Statut vs 0.7.3** : nouveau constat. Le meme defaut avait ete releve en 0.7.3 par l'audit 10, mais sur le job `audit-checks`.

- **Localisation** : `.github/workflows/release-gate.yml:86` (`uv run pytest ... 2>&1 | tee /tmp/backend-tests.txt`), `:92` (`npm run test:run 2>&1 | tee ...`) ; log du job `125355048341` : `shell: /usr/bin/bash -e {0}`
- **Constat** : sans `pipefail`, le statut du pipeline est celui de `tee`, toujours 0. Un pytest ou un vitest rouge laisse donc le job `success`, et le commentaire du gate affiche « Unit tests ✅ — Blocking: Yes ». Le vrai filet est `ci.yml:47` et `:75`, qui lancent les memes suites sans pipe sur les PR vers `main` et `release/**`. Les resultats 9.1.1 / 9.1.2 de ce rapport viennent de la lecture des logs, pas du statut du job.
- **Remediation** : `set -o pipefail` en tete des deux steps, ou `defaults: run: shell: bash`. A traiter dans l'audit 10. (S ; nul.)

### [INFO] Le perimetre `@critical` est execute trois fois a chaque run

**Statut vs 0.7.3** : nouveau constat. Le comportement est documente dans `e2e/ui/README.md:54`.

- **Localisation** : `e2e/ui/src/test/java/UIRunner.java:5-23` ; `.github/workflows/ci.yml:217-220`, `.github/workflows/release-gate.yml:647-650`
- **Constat** : sans `-Dtest`, Maven lance les 3 methodes de `UIRunner`, et `--tags @critical` remplace leurs tags. Chaque scenario tourne donc 3 fois : 15 executions pour 5 scenarios (logs `125358209244`, `125389223024`). Le job dure 107-115 s, contre environ 40 s utiles. Brancher `@regression` sans corriger cela triplerait aussi son cout.
- **Remediation** : `-Dtest='UIRunner#testCritical'` dans les deux workflows. (S ; nul.)

### [INFO] Adaptateur `PdfPageRasterizer` : le clamp de `crop` n'est pas teste

**Statut vs 0.7.3** : nouveau constat. Le code est inchange.

- **Localisation** : `document-parser/infra/page_raster.py:35-64` (clamp `:49-54`) ; `document-parser/tests/navigation_fixtures.py:330-350` ; `document-parser/bootstrap/factories.py:305-307`
- **Constat** : aucun test n'importe `infra.page_raster`. Les tests MCP passent par un `FakeRasterizer` dont le commentaire dit qu'il est « clamped [...] exactly as `PdfPageRasterizer.crop` » : il recopie la logique au lieu de la verifier. Les images de citation MCP en production passent par l'adaptateur reel.
- **Remediation** : un test de `crop` sur un PNG genere par PIL, avec une boite hors limites, une boite de largeur nulle, et le format WEBP. (S ; nul.)

### [INFO] Frontend : un store sans test, et 37 tests unitaires sur du code inatteignable

**Statut vs 0.7.3** : nouveau constat.

- **Localisation** : `frontend/src/features/settings/store.ts` (49 lignes) ; `frontend/src/pages/DocIngestTab.logic.test.ts` (23 tests) ; `frontend/src/features/store/ui/connectionForm.logic.test.ts` (14 tests)
- **Constat** :
  - Sur les 13 stores, seul `settings/store.ts` (theme, locale, persistance `localStorage`) n'a pas de test. Il n'est pas critique.
  - Les clients API `admin-config/api.ts`, `history/api.ts` et `mcp-config/api.ts` n'ont pas de test propre. Ce sont des wrappers `apiFetch` sans logique, mockes par les tests de leurs stores.
  - `DocIngestTab.logic.ts` et `connectionForm.logic.ts` ne sont consommes que par `pages/IngestLaunchDialog.vue` et `features/store/ui/StoreForm.vue`, qu'aucun chemin d'import ne relie a `app/main.ts`. 37 tests maintiennent donc du code mort, de la meme UI d'ingestion que les specs e2e obsoletes.
- **Remediation** : supprimer ces composants et leurs tests avec les specs e2e (audit 03/04), ou documenter leur reactivation prevue. Un test de `settings/store.ts` est optionnel.

---

## Delta vs 0.7.3

Score : **93 -> 93** (=). Items conformes 13/14 -> 13/14.

| Ecart baseline (0.7.3) | Statut en 0.7.4 |
|------------------------|-----------------|
| [MAJ] Karate UI pas vert ; features 0.7.3 hors CI | **Toujours present, elargi** : 9 features / 11 scenarios obsoletes au lieu de 3, dont `doc-new-analysis-opens-analysis` (cassee par #359) ; 3 assertions vides. Le perimetre `@critical` est desormais prouve vert |
| [MIN] #344 non gate | **Toujours present** ; preuve hors gate (*Docling compatibility* `41481215664`, docling non epingle) |
| [MIN] `document_versions` sans test API | **Toujours present** |
| [MIN] `LocalChunker` + commentaire vers `test_local_chunker.py` | **Toujours present** (`test_chunking.py:486`) |
| [INFO] Glue du switch MCP | **Toujours present** (`builder.py:240-246`) |
| [INFO] Pas d'e2e API pour les routes 0.7.3 | **Toujours present** |
| [INFO] Import #359 : 400 HTTP et flux client | **Toujours present** ; `to_thread` desormais teste |
| [INFO] Branches 413 secondaires | **Toujours present** |
| [INFO] Preuve d'execution e2e (UI non prouvee) | **Leve** : e2e API complete (38/38) et UI `@critical` (15/15) vertes sur un arbre identique (runs `41468347487`, `41477971314`). La suite UI complete, elle, n'a toujours aucune preuve (integre au MAJ) |
| [INFO] RuntimeWarning `test_pipeline_options.py` | **Toujours present** (4 warnings dans *Docling compatibility*) |
| [INFO] Neo4j : docstring fausse | **Toujours present** |
| [INFO] Reasoning hors gate | **Toujours present** (`release-gate.yml:252`) |

Nouveaux ecarts :
- 1 MIN : `extract_pages_detail` non teste en CI.
- 4 INFO : `tee` sans `pipefail` dans le gate, triple execution `@critical`, `PdfPageRasterizer.crop`, store `settings` / tests de code mort.

Tous sont des constats sur du code deja present en 0.7.3, pas des regressions 0.7.4.

---

## Quick wins

| Action | Item | Gain estime | Effort | Risque |
|--------|------|-------------|--------|--------|
| Purger et reparer les 9 specs obsoletes et les 3 assertions vides (remediations 1 a 4 du MAJ) | 9.1.3 | Prerequis : 0 point seul, car l'item exige aussi une preuve d'execution | S | Nul (e2e seulement ; 2 attributs `data-e2e` dans `DocumentActionsMenu.vue`) |
| Puis executer une fois `UIRunner#testLocal` sur l'arbre de release (stack de `e2e/ui/README.md:21-23`) et joindre `karate-summary.html`, ou brancher `--tags @critical,@regression` au gate (remediation 5) | 9.1.3 | **+7 points (93 -> 100)**, MAJ leve | S (run manuel) / M (job gate) | Nul / gate plus long |
| `-Dtest='UIRunner#testCritical'` dans `ci.yml:217` et `release-gate.yml:647` | — | 0 point, environ -70 s par run e2e-ui | S | Nul |
| `set -o pipefail` dans `release-gate.yml:86` et `:92` | — (audit 10) | 0 point ici, le gate redevient bloquant | S | Nul |
| Test `extract_pages_detail` sur un `DoclingDocument` en memoire | 9.2.3 | 0 point (MIN partiel), leve 1 MIN | S | Nul |
| `test_document_versions_api.py` | 9.2.1 | 0 point (MIN partiel), leve 1 MIN | S | Nul |
| Corriger le commentaire `test_chunking.py:486` et la docstring `tests/neo4j/conftest.py:4` | 9.2.3 / — | 0 point, leve 1 MIN et 1 INFO | S | Nul |

Seul l'item 9.1.3 peut faire bouger le score. Les autres actions reduisent le nombre d'ecarts sans changer la note.

---

## Points positifs

- **Suites unitaires vertes sur l'arbre audite** : 1323 tests backend (32 s) et 545 tests frontend (6 s) en CI, 0 echec. Avec `docling`, 1387 tests backend passent (job *Docling compatibility*).
- **Filet e2e bloquant vert et prouve** : e2e API complete (12 features, 38 executions) et UI `@critical` (15 executions), 0 echec, sur le Release Gate et sur `main`. La baseline n'avait pas pu le montrer.
- **La remediation 0.7.3 est arrivee avec son test** : le passage de l'import #359 hors de l'event loop est fixe par un test qui verifie l'absence de boucle dans le thread de l'importeur (`test_analysis_service.py:225`). Ce test n'a pas de `sleep` et ne depend pas de l'horloge.
- **Couverture API et services complete au sens de la checklist** : 51 des 53 routes ont un test TestClient (les 2 manquantes sont `document_versions`), et les 21 modules de `services/` sont exerces avec le vrai service, souvent sur des repos en memoire.
- **Les 7 features UI 0.7.3 encore valides sont bien ecrites** : hooks `data-e2e` dedies, donnees creees et nettoyees par l'API, `waitUntil` sur l'etat reel (`aria-pressed`, `data-status`), contrat API verifie dans la meme scenario (`mcp-config.feature:32-37`). Elles ne demandent qu'a etre branchees.
- **Discipline** : zero `.only` / `fdescribe` / `fit` / `xit`, zero skip sans raison. Les helpers `common/helpers/` sont tous `@ignore`. Le seul ecart, `_open-launch-modal.feature`, est releve au MAJ.

---

## Verdict partiel : GO

Score **93/100**, **0 CRITICAL**, **1 MAJOR** (sous le seuil de blocage de 3). Le code teste est celui de v0.7.3, avec des preuves CI sur un arbre identique : 1323/1323 tests backend executes, 545/545 tests frontend, e2e API 38/38, e2e UI `@critical` 15/15. Les chiffres locaux du coordinateur sont identiques (1323 passed / 19 skipped ; 545 passed).

Le MAJOR (9.1.3) est reconduit et precise. La suite Karate UI compte 9 features (11 scenarios) qui pilotent une UI inexistante, au lieu des 3 annoncees en 0.7.3, et 31 scenarios sur 36 ne tournent dans aucun workflow. La feature #342 a ainsi ete cassee par #359 sans que rien ne le signale. Lever ce MAJ ne demande que des changements e2e (purge, rebasage, deux attributs `data-e2e`) et une execution de `testLocal`, ou un job `@regression` au gate. Il ramenerait l'audit a 100/100.

# Rapport d'audit : Tests

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a6fb539` = `release/0.7.4` @ `f7fc791` (PR #401 rendu PDF.js + cache de preview + resumes d'analyses, PR #402 correctifs editeur) + 13 commits locaux (#391 a #400) + commit de merge. Branche non poussee : aucun run CI sur cet arbre.
**Execution** : suites executees localement sur `a6fb539`, deux fois chacune, resultats identiques.
- Backend `.venv/bin/pytest tests/ -q -p no:cacheprovider` : **1501 passed, 15 skipped, 4 warnings**, 15,7 a 16,3 s.
- Frontend `npx vitest run` : **62 fichiers, 586 tests, 586 passed**, 1,2 s.
- Karate API et UI : non executes (ils demandent la stack). Couverture jugee par lecture de `e2e/` et `.github/workflows/`.
- Couverture de lignes : non mesuree. `pytest-cov` absent, aucun `@vitest/coverage-*` dans `frontend/node_modules/@vitest/`. Couverture backend etablie route par route (voir plus bas).

**Baseline** : `docs/audit/reports/release-0.7.4/09-tests.md` (2026-11-13, `eade7fa`, 85/100, provisoire, aucune suite executee).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 11 |

Calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**. Seul item non conforme : 9.1.3 (poids 2). Meme grille et meme lecture que la baseline (les ecarts partiels sur un item juge conforme sont notes MIN, comme en 0.7.3 et 0.7.4).

### Detail par item

| # | Poids | Conforme | Justification |
|---|-------|----------|---------------|
| 9.1.1 | 3 | Oui | 1501 passed / 15 skipped / 0 failed, execute deux fois sur `a6fb539`. Les 15 skips sont les tests Neo4j (pas de serveur local). |
| 9.1.2 | 3 | Oui | 586/586 en 62 fichiers, execute deux fois. Bruit jsdom `HTMLCanvasElement.prototype.getContext` (axe-core) sans echec. |
| 9.1.3 | 2 | **Non** | Pas de run Karate UI sur l'arbre, 3 specs UI obsoletes toujours presentes, `analysis-editor.feature` hors de tout workflow. Voir MAJ. |
| 9.2.1 | 2 | Oui | Les 6 routes de l'editeur ont un happy path (`test_analysis_edits_api.py:86-170`). Restent `GET /versions` et `POST /versions/{id}/restore` sans test HTTP (MIN, precedent 0.7.3). |
| 9.2.2 | 2 | Oui | 404 document et analyse, 409 sequence perimee, 400 element inconnu, 422 commande inconnue testes en HTTP (`test_analysis_edits_api.py:173-215`) ; preview 400/404 (`test_api_endpoints.py:227-258`) ; 413 upload. |
| 9.2.3 | 2 | Oui | `AnalysisEditService` sur SQLite reel ; `PreviewService` (cache, invalidation) ; `find_all_summaries` service et repo (`test_analysis_service.py:763`, `test_repos.py:217`). |
| 9.2.4 | 1 | Oui | Domain editeur et navigation testes ; `clampPageInput` / `pageInRenderWindow` testes (`PagePreviewWithOverlay.logic.test.ts:10-81`). |
| 9.2.5 | 2 | Oui | Stores et composables critiques testes ; `usePdfDocument` couvert par ses deux chemins principaux. `PdfPageCanvas.vue` n'a aucun test direct (INFO, a la limite de l'item). |
| 9.3.1 | 3 | Oui | 0 `.only` / `fdescribe` / `fit` / `xit` dans `frontend/src` et `e2e/`. |
| 9.3.2 | 1 | Oui | Tous les skips pytest ont une `reason` ; les `@ignore` Karate sont des helpers appeles par `call` ou des scenarios appeles par tag. |
| 9.3.3 | 2 | Oui | Aucune instabilite sur deux executions completes ; horloge simulee (`vi.useFakeTimers`) cote front. Un `asyncio.sleep(0.05)` ancien (`test_analysis_service.py:277`) reste tolerable. |
| 9.3.4 | 2 | Oui | API editeur sur service et SQLite reels ; poppler reel exerce par `e2e/api/.../documents/preview.feature` (`@regression`, lance sur PR vers `release/**`). Ecarts partiels en MIN. |
| 9.3.5 | 1 | Oui | Les `is not None` ajoutes sont des gardes suivies d'assertions precises. |
| 9.3.6 | 1 | Oui | Noms descriptifs (`test_save_against_a_stale_sequence_is_a_conflict`, etc.). |

### Couverture route par route (backend)

57 routes dans `document-parser/api/*.py`. 55 ont au moins un test HTTP happy path. Nouvelles ou modifiees depuis la baseline :

| Route | Test HTTP | Remarque |
|-------|-----------|----------|
| `GET /api/documents/{id}/analysis-editor` | `test_analysis_edits_api.py:86`, `:173`, `:180` | service, editeur Docling et SQLite reels |
| `POST .../analysis-edits/preview` | `:97`, `:199`, `:209` | |
| `GET .../analysis-edits/history` | `:126` | |
| `PATCH .../analysis-edits/history/{sequence}` | `:140` | |
| `POST .../analysis-edits` | `:111`, `:187` | |
| `POST .../analysis-edits/rebuild` | `:157` | |
| `GET /api/analyses/summaries` (#401) | `test_api_endpoints.py:496` | service mocke ; repo teste a part (`test_repos.py:217`) |
| `GET /api/documents/{id}/preview` (#401) | `test_api_endpoints.py:227-311` | `generate_preview` patche partout ; poppler reel seulement en e2e API |
| `GET /api/documents/{id}/export` (source PDF.js) | `test_api_endpoints.py:370-468` | aucune requete `Range` testee |
| `GET /api/documents/{id}/versions` | **aucun** | service teste (`test_version_service.py:199-209`) |
| `POST /api/documents/{id}/versions/{vid}/restore` | **aucun** | service teste (`test_version_service.py:121-190`) |

Chemins critiques sans test automatise execute en CI : rendu PDF.js reel (worker, chargement par plages, annulation de rendu), boot de 0.7.4 sur une vraie base 0.7.3 (#391), parcours UI de l'editeur.

### Skips

- Local (15) : tous Neo4j, `tests/neo4j/conftest.py:35`, « Neo4j not reachable at bolt://localhost:7687 ». Justifies.
- CI (deduit, non execute) : `docling` est installe dans le `.venv` local mais pas en CI (`ci.yml:41`, `--group dev` seul ; `docling` est dans le groupe `local`, `pyproject.toml:38-39`). En CI s'ajoutent donc 3 modules sautes a la collecte (`test_pipeline_options.py:14`, 33 tests ; `test_robustness.py:155`, 25 tests ; `test_batch_merge.py:17`, 5 tests) et `test_serve_converter.py:792` (1 test) : **64 tests qui ne tournent qu'en local**. Voir MIN 9.3.4 et INFO process.

---

## Ecarts constates

### [MAJ] La suite Karate UI n'est toujours pas verte ni executee, et l'editeur comme le rendu PDF.js n'ont aucune preuve bout en bout en CI (baseline, inchange)

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-ingest-view.feature:38`, `e2e/ui/src/test/resources/documents/doc-chunk-view.feature:31`, `e2e/ui/src/test/resources/documents/doc-strategy-popover.feature:31` et `:39` ; `frontend/src/shared/routing/modes.ts:36-37` ; `e2e/ui/src/test/java/UIRunner.java:6`, `:19` ; `e2e/ui/src/test/resources/analyses/analysis-editor.feature:1` ; `e2e/ui/src/test/java/AnalysisEditorRunner.java:6` ; `.github/workflows/ci.yml:162`, `:228` ; `.github/workflows/release-gate.yml:4-6`, `:658`
- **Constat** :
  - Les 3 specs obsoletes sont inchangees : `[data-e2e=view-switcher]` et `[data-e2e=strategy-btn]` n'existent nulle part dans `frontend/src` ; `[data-e2e=chunk-tab]` n'est porte que par `pages/DocChunkTab.vue:2`, que rien n'importe ; `modes.ts:36-37` resout `chunk` et `ingest` en `parse`. Elles echouent sous `UIRunner.testAll` et `testLocal`.
  - `analysis-editor.feature` (3 scenarios, `:7`, `:78`, `:105`) reste tague `@ui` seul. La CI ne lance que `@critical` (`ci.yml:228`, `release-gate.yml:658`), et `e2e-ui` de `ci.yml` ne tourne que sur `main` (`:162`). Le Release Gate ne tourne que sur une PR vers `main` (`release-gate.yml:4-6`). `AnalysisEditorRunner` n'est appele par aucun workflow.
  - Nouveau perimetre non couvert : le rendu PDF.js de #401. Aucune feature UI n'attend un `canvas` de page ni `[data-e2e=pdf-page-preview]` ; `doc-viewer.feature:23-24` n'attend que les conteneurs `preview-with-overlay` et `preview-page-1`, qui s'affichent aussi quand PDF.js echoue et que l'image serveur prend le relais. Un worker mal empaquete ou un `Range` mal servi par nginx passerait donc inapercu.
  - Aucun rapport Karate UI recent : `e2e/ui/target/karate-reports/` date du 2026-07-16.
- **Regle violee** : 9.1.3.
- **Remediation** : supprimer ou reecrire les 3 specs obsoletes contre `/docs/:id` ; passer le premier scenario de `analysis-editor.feature` en `@critical` ; ajouter dans `doc-viewer.feature` une attente sur un `canvas` rendu (`[data-e2e=pdf-page-preview] canvas` ou equivalent dans l'overlay) et l'absence de `img.preview-image` ; joindre le rapport Karate UI au gate (#374, #382). Effort M.

### [MIN] Les 2 routes `document_versions` n'ont toujours aucun test HTTP

- **Localisation** : `document-parser/api/document_versions.py:54`, `:66`
- **Constat** : `grep -rn "/versions" document-parser/tests` ne trouve que des tests de service et de schema (`test_version_service.py`, `test_database_upgrade.py`). Le mapping d'erreur `_raise_for` (`document_versions.py:50-51`) n'est jamais exerce en HTTP. C'etait le MIN de 0.7.3, absorbe dans le MAJ 9.2.1 de la baseline ; ce MAJ etant leve, l'ecart redevient MIN.
- **Regle violee** : 9.2.1 (partiel).
- **Remediation** : 2 happy paths + 404 version inconnue dans un `test_document_versions_api.py` sur le modele de `test_analysis_edits_api.py`. Effort S.

### [MIN] 64 tests ne tournent qu'en local faute de `docling` en CI, et ils pourrissent deja (baseline #344, elargi)

- **Localisation** : `document-parser/tests/test_pipeline_options.py:14`, `document-parser/tests/test_robustness.py:155`, `document-parser/tests/test_batch_merge.py:17`, `document-parser/tests/test_serve_converter.py:792` ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:85` ; `document-parser/pyproject.toml:29-47`
- **Constat** : la CI installe `--group dev` seulement ; les 3 modules sont sautes a la collecte (33 + 25 + 5 tests) et un test de `test_serve_converter.py` aussi. Le merge des batches (#344) n'est toujours valide par aucun gate. Preuve qu'ils derivent : le commit `256c494` (#397, `update_status(select_analysis=True)` -> `complete_and_select`) a du ajouter a la main `complete_and_select = AsyncMock()` dans `test_pipeline_options.py:336` et `test_robustness.py:91`. Sans execution locale avec `docling`, ces tests auraient casse en silence. Les 4 RuntimeWarning « coroutine never awaited » viennent aussi de ce module (`test_pipeline_options.py:380` et suivants, 3 tests) : ils passent, mais un `AsyncMock` est appele sans `await` quelque part, origine non isolee.
- **Regle violee** : 9.3.4 (partiel).
- **Remediation** : job CI dedie `uv sync --group dev --group local` limite a ces 4 fichiers, ou deplacer les tests de service de `test_pipeline_options.py` (qui n'ont pas besoin de `docling`) hors du module garde par `importorskip`. Effort M.

### [MIN] `LocalChunker` sans test ; le commentaire renvoie toujours a un fichier inexistant (baseline, inchange)

- **Localisation** : `document-parser/tests/test_chunking.py:486`
- **Constat** : « Real chunker integration is covered by ``test_local_chunker.py`` » ; `tests/test_local_chunker.py` n'existe pas.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel).
- **Remediation** : ecrire le test ou corriger le commentaire. Effort S.

### [INFO] `PdfPageCanvas.vue` n'est monte par aucun test

- **Localisation** : `frontend/src/features/document/ui/PdfPageCanvas.vue:30-89` ; `frontend/src/features/document/ui/PdfPagePreview.test.ts:27`, `:51` ; `frontend/src/features/document/ui/PagePreviewWithOverlay.test.ts:31`
- **Constat** : les deux tests PDF.js utilisent `shallowMount`, donc `PdfPageCanvas` est un stub ; ils emettent `ready` a la main. Aucun test n'exerce `render()` : annulation puis attente de la tache precedente (`:39-48`), garde `generation` (`:49`, `:52`, `:60`), `RenderingCancelledException` ignoree (`:64`), seuil de 2 px du `ResizeObserver` (`:35`), emission de `error`. Ce code n'a pas besoin d'un vrai canvas : un faux `PDFDocumentProxy` (`getPage` -> `render` -> `{ promise, cancel }`) suffit sous jsdom. Ce que les tests verifient reellement : un seul `getDocument` pour plusieurs pages, l'image serveur en repli si le chargement echoue, l'ordonnancement des pages montees. `onPdfError` de l'overlay (`PagePreviewWithOverlay.vue:314-318`) et le `destroy` de la tache au changement de document (`usePdfDocument.ts:20`) ne sont pas testes. L'item 9.2.5 reste conforme parce que le repli image est teste ; c'est la limite basse.
- **Remediation** : `PdfPageCanvas.test.ts` avec un faux document : rendu nominal, rendu annule par un changement de page, erreur -> `emit('error')`. Effort S.

### [INFO] Aucun test ne fait de vraie requete `Range` sur l'export PDF lu par PDF.js

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts:25-30` ; `document-parser/api/documents.py:134-170`
- **Constat** : PDF.js charge le PDF par plages de 256 Ko (`disableStream`, `disableAutoFetch`, `rangeChunkSize: 262144`) via `FileResponse`. Ni pytest, ni vitest, ni Karate n'envoie d'en-tete `Range` (aucune occurrence de `Range`/`bytes=` dans les tests). Si le backend ou nginx renvoie le fichier entier, le rendu marche toujours mais le gain de #401 disparait, sans signal.
- **Remediation** : un test pytest `Range: bytes=0-99` -> 206 et `Content-Range`, et un scenario e2e API equivalent a travers nginx. Effort S.

### [INFO] Le chemin poppler reel n'est teste qu'en e2e API ; PNG seulement

- **Localisation** : `document-parser/services/document_service.py:160-179` ; `document-parser/tests/test_document_service.py:164-205` ; `document-parser/tests/test_api_endpoints.py:271`, `:305` ; `e2e/api/src/test/resources/documents/preview.feature:7-45`
- **Constat** : tous les tests pytest patchent `convert_from_path` ou `DocumentService.generate_preview`. `pdftoppm` est present en local et en CI (`ci.yml:38`) mais aucun test unitaire ne l'appelle. Le rendu reel est couvert par `preview.feature` (`@regression`, lance sur les PR vers `release/**`, `ci.yml:137-143`), qui ne teste ni `format=webp` ni le cache. Couverture suffisante pour 9.3.4.
- **Remediation** : un test pytest non mocke sur un PDF d'une page genere en fixture, PNG et WebP. Effort S.

### [INFO] L'API editeur n'est testee qu'avec `replaceText` ; 5 des 6 branches de `_to_edit_commands` ne passent jamais par HTTP

- **Localisation** : `document-parser/api/analysis_edits.py:84-105` ; `document-parser/tests/test_analysis_edits_api.py:81-82`
- **Constat** : `mergeText`, `setHeadingLevel`, `deleteElement`, `deleteElements` et `moveElement` (branche `else`) ne sont traduits du JSON camelCase vers le payload domaine que dans les e2e UI, hors CI. Une erreur d'alias (`elementIds`, `beforeElementId`...) ne serait detectee par aucun gate.
- **Remediation** : parametrer `test_preview_projects_pending_commands_without_saving` sur les 6 types. Effort S.

### [INFO] Les tests mis a jour a la main pendant le merge revelent un trou de process

- **Localisation** : commit de merge `a6fb539` ; `document-parser/tests/test_api_endpoints.py:429`, `:444` ; `document-parser/tests/test_export_service.py:44`
- **Constat** : 8 tests backend et 1 test frontend ont du etre realignes au merge. Ce ne sont pas des tests faux : PR #401/#402 ont ete ecrites et validees en CI contre l'API de `release/0.7.4`, pendant que les renommages de #397 (`export(edited=True)` -> `export_edited`, `active_result` -> `load_active_result`) dormaient 5 jours sur une branche locale non poussee. Le conflit ne pouvait apparaitre qu'au merge, et seule l'execution locale complete l'a detecte. Deux causes : (1) refactorings d'API interne garde hors de `release/*` sans CI ; (2) les tests de modules gardes par `importorskip("docling")` ne sont pas executes en CI (MIN ci-dessus), donc une derive de ce type y passerait meme apres push.
- **Remediation** : pousser les correctifs tot et en petites PR vers `release/0.7.4` ; fusionner `release/0.7.4` dans les branches longues a chaque merge ; job CI avec `docling`. Effort S.

### [INFO] L'upgrade 0.7.3 -> 0.7.4 n'est teste que sur une copie de schema (baseline, inchange)

- **Localisation** : `document-parser/tests/test_database_upgrade.py:17-58`, `:101-170` ; `.github/workflows/ci.yml:107-108`
- **Constat** : les 5 tests passent. Ils recopient 3 tables 0.7.3 a la main. Aucun job, aucun e2e ne demarre 0.7.4 sur une base reellement creee par l'image 0.7.3 : toute la CI part d'un volume neuf.
- **Remediation** : versionner une base 0.7.3 minimale generee par l'image `0.7.3` et l'utiliser en fixture. Effort S.

### [INFO] Les PDF de test `editor-provenance.pdf` et `editor-readonly.pdf` ne servent toujours a aucun scenario (baseline, inchange)

- **Localisation** : `e2e/generate-test-data.py:185-186` ; `e2e/ui/README.md:61-62`

### [INFO] Aucun scenario e2e API pour les routes de l'editeur, les resumes d'analyses ni l'export par plages (baseline, elargi)

- **Localisation** : `e2e/api/src/test/resources/` (16 features ; aucune ne contient `analysis-edit`, `summaries` ou `Range`)
- **Constat** : les seuls appels HTTP reels de l'editeur sont dans `analysis-editor.feature:145`, `:153`, hors CI.

### [INFO] Import Docling : 400 « document invalide » non teste en HTTP ; deux branches 413 secondaires non couvertes (baseline, inchange)

- **Localisation** : `document-parser/api/analyses.py:83-85` ; `document-parser/api/documents.py:86-87` ; `document-parser/services/graph_service.py:48`

### [INFO] Les tests Neo4j ne tournent dans aucune CI ; la docstring affirme le contraire (baseline, inchange)

- **Localisation** : `document-parser/tests/neo4j/conftest.py:4` (« CI spins up `neo4j:5.15-community` ») ; aucune occurrence de `neo4j` dans `.github/workflows/`.

### [INFO] Un test dont le nom promet plus que son assertion

- **Localisation** : `document-parser/tests/test_pipeline_options.py:359-368`
- **Constat** : `test_create_passes_pipeline_options_to_run` ne verifie que `create_task.assert_called_once()` ; les options transmises ne sont pas controlees. Le test ne peut echouer que si `create` ne lance aucune tache. Ancien, non bloquant.

### [INFO] Reasoning : toujours aucune couverture dans le gate (baseline, inchange)

- **Localisation** : `.github/workflows/release-gate.yml:252`

---

## Delta vs audit du 2026-11-13

Score : **85 -> 93 (+8)**. Items conformes 12/14 -> 13/14. CRIT 0 -> 0, MAJ 2 -> 1, MIN 2 -> 3, INFO 11 -> 11. Le score n'est plus provisoire : les deux suites ont tourne.

| Ecart baseline | Statut |
|----------------|--------|
| [MAJ] 9.2.1 routes de l'editeur sans happy path | **Corrige** par `d59f9f4` (#399) : 11 tests HTTP sur service et SQLite reels |
| [MAJ] 9.1.3 e2e UI | **Toujours ouvert**, elargi au rendu PDF.js (#401) |
| [MIN] #344 merge des batches non gate | **Toujours ouvert**, elargi : 64 tests hors CI, derive deja constatee |
| [MIN] `LocalChunker` + commentaire faux | Toujours ouvert |
| [MIN] `document_versions` sans test API (absorbe en 0.7.4) | Redevient MIN |
| [INFO] 13 tests des correctifs non executes | **Clos** : executes, tous verts |
| [INFO] Document absent -> 409 | **Clos** : 404, fige par `test_analysis_edits_api.py:173` |
| [INFO] Upgrade teste sur copie de schema | Toujours present |
| [INFO] PDF de test inutilises | Toujours present |
| [INFO] RuntimeWarning `test_pipeline_options.py` | **Verifie** : present (3 tests, 4 warnings), integre au MIN #344 |
| [INFO] e2e API, import 400, 413, Neo4j, reasoning, switch MCP | Toujours presents (switch MCP non re-verifie) |

Nouveaux : 5 INFO (`PdfPageCanvas` non teste, aucune requete `Range`, poppler reel seulement en e2e, 5 commandes editeur non testees en HTTP, trou de process revele par le merge) et 1 INFO de qualite (`test_pipeline_options.py:359`).
Origine des +8 : 9.2.1 (poids 2) repasse a Oui.

---

## Points positifs

- **Suites vertes et rapides, executees deux fois sans difference** : 1501 backend en 16 s, 586 frontend en 1,2 s. Aucun test instable observe.
- **Le MAJ principal de la baseline est traite sur les bonnes dependances** : `test_analysis_edits_api.py` monte le vrai routeur, le vrai `AnalysisEditService`, l'editeur Docling et SQLite `tmp_path`, sans mock du domaine, et fige le contrat d'erreur (404, 409, 400, 422).
- **#401 arrive avec ses tests** : cache de preview borne en octets avec LRU (`test_preview_cache.py`), invalidation quand le PDF change, en-tete `Cache-Control`, WebP, cache injectable par port ; ordonnancement des pages PDF.js (`PagePreviewWithOverlay.test.ts`, `.logic.test.ts`) ; repli image si PDF.js echoue.
- **Chaque correctif #391 a #398 a son test de non-regression nomme**, y compris l'ouverture des PDF par chemin (#398, `test_api_endpoints.py:288-291`) et le rejeu d'un cache corrompu (#402).
- **Discipline intacte** : 0 `.only`, 0 skip sans raison, aucun fichier de test supprime.

---

## Verdict partiel : GO

Score **93/100**, **0 CRITICAL**, **1 MAJOR** (9.1.3, e2e UI). Les suites ont tourne et sont vertes. A faire avant le tag : pousser la branche pour obtenir la CI et l'e2e API `@regression` sur l'arbre merge, et passer au moins un scenario de `analysis-editor.feature` et une verification de canvas PDF.js en `@critical`.

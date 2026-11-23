# Rapport d'audit : Tests

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a12b744` (arbre de travail ; seuls `docs/audit/reports/release-0.7.4-reaudit/remediation-plan.md` et `experiments/mcp-bench/` y different du commit, hors perimetre). Branche sans amont configure : aucun run CI sur cet arbre.
**Nature** : Audit de controle apres remediation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/09-tests.md`, 93/100).
**Execution** (une fois chacune, sur `a12b744`) :
- Backend `.venv/bin/pytest tests/ -q -p no:cacheprovider -rs` : **1559 passed, 15 skipped, 0 warning**, 16,8 s. Les 15 skips sont tous Neo4j (`tests/neo4j/conftest.py:36`, « Neo4j not reachable at bolt://localhost:7687 »).
- `.venv/bin/pytest tests/test_pipeline_options.py -W error::RuntimeWarning` : **33 passed**. Les 4 RuntimeWarning « coroutine never awaited » de la base ont disparu.
- Frontend `npx vitest run` : **65 fichiers, 605 tests, 605 passed**, 1,1 s. Seul bruit : `HTMLCanvasElement.prototype.getContext` (axe-core sous jsdom), sans echec.
- Karate API et UI : non executes (ils demandent la stack). Juges par lecture de `e2e/` et `.github/workflows/`.
- Couverture de lignes : non mesuree (ni `pytest-cov` ni `@vitest/coverage-*`), comme dans la base.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 12 |

Calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**. Seul item non conforme : 9.1.3 (poids 2). Meme grille et meme lecture que la base : un ecart partiel sur un item juge conforme est note MIN.

### Detail par item

| # | Poids | Conforme | Justification |
|---|-------|----------|---------------|
| 9.1.1 | 3 | Oui | 1559 passed / 15 skipped (Neo4j) / 0 failed / 0 warning. Chiffres identiques a ceux annonces par le mainteneur. |
| 9.1.2 | 3 | Oui | 605/605 en 65 fichiers. Chiffres identiques a ceux annonces. |
| 9.1.3 | 2 | **Non** | Aucun changement dans `e2e/` depuis `a6fb539` (`git diff --stat a6fb539 a12b744 -- e2e` vide). Voir MAJ. |
| 9.2.1 | 2 | Oui | Les 2 routes `document_versions` ont maintenant leur test HTTP (`test_document_versions_api.py:111`, `:145`). 57 routes sur 57 ont un happy path HTTP. |
| 9.2.2 | 2 | Oui | Erreurs des versions en HTTP : 404 document (`:135`, `:158`), 404 version inconnue et version d'un autre document (`:165`, `:173`), 409 (`:180`), 503 (`:188`). Import : 404, 400 document invalide, 400 autre rejet (`test_api_endpoints.py:779-815`). Export : 416 (`test_document_export_range.py:115`). |
| 9.2.3 | 2 | Oui | `PreviewService` sur ses ports (`test_preview_service.py:45-112`), `DocumentService.find_with_store_links` (`test_document_service.py:189-228`), comptage de pages par le port (`test_analysis_page_count.py`), `VersionService` sur SQLite reel via HTTP. |
| 9.2.4 | 1 | Oui | Domaine inchange, tests renommes sans changement de valeurs attendues (`test_navigation_domain.py`, `test_page_regions.py`, `test_hashing.py`). |
| 9.2.5 | 2 | Oui | `PdfPageCanvas.vue` est maintenant monte (`PdfPageCanvas.test.ts`, 6 tests), `usePdfDocument` teste directement (3 tests), annulation de preview du store editeur (`store.test.ts:209`, `:230`). Trous residuels en INFO. |
| 9.3.1 | 3 | Oui | 0 `.only` / `fdescribe` / `fit` / `xit` / `.skip` dans `frontend/src` et `e2e/`. |
| 9.3.2 | 1 | Oui | 9 marqueurs de skip, tous avec `reason` (dont 3 nouveaux sur poppler : `test_page_raster_real.py:19`, `test_document_service.py:132`, `test_api_endpoints.py:252`). |
| 9.3.3 | 2 | Oui | Nouveaux tests a fils et verrou deterministes (voir « Qualite des nouveaux tests ») ; horloge simulee restauree dans un `finally` (`store.test.ts:209-227`). |
| 9.3.4 | 2 | Oui | Nouveaux tests sur collaborateurs reels : routeur + `VersionService` + SQLite, export + `ExportService` + SQLite + vrai PDF, poppler reel, `PdfiumInspector` reel a l'upload. Ecart partiel (tests `docling` hors CI) en MIN. |
| 9.3.5 | 1 | Oui | Assertions precises (corps JSON complets, en-tetes `Content-Range` exacts, octets compares). Plusieurs tests existants renforces (detail des 404). |
| 9.3.6 | 1 | Oui | Noms descriptifs (`test_a_range_starting_past_the_end_is_not_satisfiable`, `test_restore_of_another_documents_version_is_not_found`...). |

### Couverture route par route (routes dont le handler a change)

Les handlers de 12 fichiers `api/*.py` ont change. Pour 8 d'entre eux le changement se limite au renommage `http_error` -> `to_http_error` (`analysis_edits.py`, `config.py`, `document_chunks.py`, `graph.py`, `mcp.py`, `reasoning.py`, `stores.py`, `errors.py`), couvert par `test_api_errors.py` et les tests existants de ces routes. Changements de comportement :

| Route | Changement | Test HTTP |
|-------|------------|-----------|
| `GET /api/documents/{id}` | liens de stores calcules par `DocumentService.find_with_store_links` | `test_api_endpoints.py:167`, `:190` (mapping des liens), `:214` (404 + detail) ; service : `test_document_service.py:189-228` |
| `POST /api/documents/upload` | comptage par le port `PdfInspector` | `test_api_endpoints.py:256` (service et inspecteur reels : 200, 400 trop de pages, 400 non-PDF, fichier temporaire nettoye) |
| `GET /api/documents/{id}/preview` | rendu par le port `PageRasterizer`, erreurs par `ServiceError` | `test_api_endpoints.py:307-410` ; nouveau 404 « page non rendue » sans chemin dans le message (`:341`) |
| `GET /api/documents/{id}/pages` | lecture par `PreviewService` + inspecteur | `test_api_endpoints.py:415-460` (200, 404 + detail, fichier absent, PDF illisible 422) |
| `GET /api/documents/{id}/export` | garde editeur dans le corps, erreurs par `ServiceError` | `test_api_endpoints.py:473-580` ; `Range` : `test_document_export_range.py` (200, 206 debut/milieu/fin bornee/suffixe, 416) |
| `POST /api/analyses/import` | 404 par type d'erreur et non plus par prefixe de message | `test_api_endpoints.py:779` (404), `:791` (400 document invalide), `:805` (400 autre) |
| `GET /api/documents/{id}/versions` | renommage | `test_document_versions_api.py:111`, `:128`, `:135`, `:188` |
| `POST /api/documents/{id}/versions/{vid}/restore` | renommage | `test_document_versions_api.py:145-185` |

---

## Ecarts constates

### [MAJ] La suite Karate UI n'est toujours ni verte ni executee ; l'editeur et le rendu PDF.js n'ont aucune preuve bout en bout en CI (base, inchange)

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-ingest-view.feature:38`, `e2e/ui/src/test/resources/documents/doc-chunk-view.feature:31`, `e2e/ui/src/test/resources/documents/doc-strategy-popover.feature:31`, `:39` ; `frontend/src/shared/routing/modes.ts:36-37` ; `e2e/ui/src/test/java/UIRunner.java:14`, `:21` ; `e2e/ui/src/test/resources/analyses/analysis-editor.feature:1` ; `e2e/ui/src/test/resources/documents/doc-viewer.feature:23-24` ; `.github/workflows/ci.yml:162`, `:228` ; `.github/workflows/release-gate.yml:4-5`, `:660`
- **Constat** : rien n'a bouge dans `e2e/`.
  - Les 3 specs obsoletes attendent `[data-e2e=view-switcher]`, `[data-e2e=chunk-tab]`, `[data-e2e=strategy-btn]`. Aucun n'est rendu par une route active : `modes.ts:36-37` resout `chunk` et `ingest` en `parse`, et `strategy-btn` n'existe que comme classe CSS (`StrategyPopover.vue:79`), pas comme `data-e2e`.
  - `analysis-editor.feature` (scenarios `:7`, `:78`, `:105`) reste tague `@ui` seul. La CI ne lance que `@critical` (`ci.yml:228`, `release-gate.yml:660`) ; le job `e2e-ui` ne tourne que sur `main` (`ci.yml:162`) ; le Release Gate ne tourne que sur une PR vers `main` (`release-gate.yml:4-5`).
  - Rendu PDF.js : `doc-viewer.feature:23-24` n'attend que les conteneurs, qui s'affichent aussi quand PDF.js echoue et que l'image serveur prend le relais. Les nouveaux tests unitaires (`PdfPageCanvas.test.ts`, `usePdfDocument.test.ts`) mockent PDF.js : ni le worker empaquete ni le chargement par plages a travers nginx ne sont verifies.
- **Regle violee** : 9.1.3.
- **Remediation** : supprimer ou reecrire les 3 specs contre `/docs/:id` ; passer le premier scenario de `analysis-editor.feature` en `@critical` ; attendre un `canvas` rendu dans `doc-viewer.feature` et l'absence de `img.preview-image` ; joindre un rapport Karate UI au gate. Effort M.

### [MIN] 64 tests ne tournent qu'en local faute de `docling` en CI (base, inchange ; warnings corriges)

- **Localisation** : `document-parser/tests/test_pipeline_options.py:14`, `document-parser/tests/test_robustness.py:155`, `document-parser/tests/test_batch_merge.py:17`, `document-parser/tests/test_serve_converter.py:792` ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:86`
- **Constat** : la CI installe toujours `--group dev` seul. Sont donc sautes en CI : 33 + 25 + 5 tests a la collecte, plus 1 test de `test_serve_converter.py`. Comptes verifies sur les ids collectes. Progres : les 4 RuntimeWarning sont corriges par `_close_and_stub_task` (`test_pipeline_options.py:326-329`) et `find_by_id` qui rend `None` (`:347`), et le module passe avec `-W error::RuntimeWarning`. Ce correctif ne touche pas aux assertions des tests concernes.
- **Regle violee** : 9.3.4 (partiel).
- **Remediation** : job CI avec `uv sync --group dev --group local` limite a ces 4 fichiers, ou sortir les tests de service de `test_pipeline_options.py` du module garde par `importorskip`. Effort M.

### [INFO] `LocalChunker` n'a pas de test pytest ; le commentaire est maintenant juste (base MIN, retrograde)

- **Localisation** : `document-parser/tests/test_chunking.py:486-488` ; `document-parser/bootstrap/factories.py:61-70` ; `e2e/api/src/test/resources/analyses/rechunk.feature:1`
- **Constat** : la reference a `test_local_chunker.py`, qui n'existe pas, est remplacee par un renvoi exact vers `rechunk.feature`. Ce scenario est `@regression`, lance par `ci.yml:140-142` sur les PR vers `release/**` et maintenant aussi sur un push sur `release/**`. Comme `build_chunker` rend `LocalChunker` dans tous les modes (`factories.py:64-70`), ce scenario exerce bien le vrai chunker. Le trou reste pour pytest seul.

### [INFO] Deux comportements annonces par le code ne sont fixes par aucun test

- **Localisation** : `document-parser/services/analysis_service.py:94`, `:448-449` ; `document-parser/bootstrap/factories.py:216` ; `document-parser/tests/test_analysis_page_count.py:44-46` ; `document-parser/api/documents.py:121-124`
- **Constat** :
  1. `AnalysisService` accepte `pdf_inspector=None` et coupe alors le decoupage en lots sans rien signaler. `test_without_an_inspector_batching_is_disabled` fige ce mode degrade, et c'est voulu : le sens du test a change de « garde le comptage local » a « lots desactives ». Mais aucun test ne verifie que `build_analysis_service` passe bien l'inspecteur (`factories.py:216`). Si cette ligne saute, la suite reste verte et le decoupage en lots disparait en production.
  2. Le commentaire `documents.py:121-122` justifie la garde dans le corps par l'ordre 422 avant 404. Aucun test n'envoie `format=docx&edited=true` avec l'editeur desactive.
- **Remediation** : un test sur `build_analysis_service()` (`service._pdf_inspector is not None`), ou rendre le parametre obligatoire ; un test de l'ordre 422 avant 404. Effort S.

### [INFO] Trous residuels dans les nouveaux tests PDF.js

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.test.ts:60-81` ; `frontend/src/features/document/ui/usePdfDocument.ts:36` ; `frontend/src/features/document/ui/PdfPageCanvas.vue:35`, `:64` ; `frontend/src/features/document/ui/usePdfDocument.test.ts:47-53`
- **Constat** :
  - « ignores its late result » ne discrimine pas : le premier document est resolu avant le second (`:75-76`). Sans la garde `usePdfDocument.ts:36`, l'etat final serait quand meme `doc-2`, et le test passerait. Il faudrait resoudre `second` puis `first`. La partie `destroy` du test (`:72`) est, elle, discriminante.
  - `PdfPageCanvas` : le seuil de 2 px du `ResizeObserver` (`:35`) n'est jamais exerce, car `FakeResizeObserver` n'appelle jamais son callback. Le filtre `RenderingCancelledException` (`:64`) n'est jamais teste seul : dans les deux tests d'annulation, la garde `generation` suffit deja a taire l'erreur.
  - `disableStream: true` n'est pas verifie par `objectContaining` (`:47-53`).
- **Remediation** : inverser l'ordre de resolution ; un test de resize qui declenche le callback ; un rejet `RenderingCancelledException` sans changement de page. Effort S.

### [INFO] Huit tests poppler se sautent sans bruit sur une machine sans poppler

- **Localisation** : `document-parser/tests/test_page_raster_real.py:19-22` (4 tests), `document-parser/tests/test_document_service.py:132` (3 tests), `document-parser/tests/test_api_endpoints.py:252-255` (1 test) ; `.github/workflows/ci.yml:38` ; `.github/workflows/release-gate.yml:80`
- **Constat** : `poppler-utils` est installe dans le job backend de `ci.yml` et dans `release-gate.yml`, donc ces tests tournent en CI. Ils ont aussi tourne localement (`pdftoppm` et `pdfinfo` presents). Si l'etape apt disparait un jour, les 8 tests passeront en `skipped` sans faire rougir la CI.
- **Remediation** : option, faire echouer ces skips quand `CI=true`. Effort S.

### [INFO] Aucun run CI sur l'arbre controle (process, base, reduit)

- **Localisation** : branche `fix/0.7.4-editor-followups` (aucun amont) ; `.github/workflows/ci.yml:4-5`
- **Constat** : `c4c0474` fait tourner la CI sur un push vers `release/**` et ajoute `pipefail` au Release Gate (`release-gate.yml:84`, `:91`). Mais la branche n'est pas poussee : aucune CI ni aucun e2e API `@regression` n'a tourne sur les 15 commits de remediation. Les chiffres de ce rapport viennent tous d'executions locales.

### [INFO] L'upgrade 0.7.3 -> 0.7.4 n'est teste que sur une copie de schema (base, inchange)

- **Localisation** : `document-parser/tests/test_database_upgrade.py:17-58`

### [INFO] Les PDF `editor-provenance.pdf` et `editor-readonly.pdf` ne servent a aucun scenario (base, inchange)

- **Localisation** : `e2e/generate-test-data.py:185-186`

### [INFO] Aucun scenario e2e API pour les routes de l'editeur, les resumes d'analyses ni l'export par plages a travers nginx (base, reduit)

- **Localisation** : `e2e/api/src/test/resources/` (aucune feature ne contient `analysis-edit`, `summaries` ou `Range`)
- **Constat** : cote pytest, le contrat `Range` est maintenant fige sur la vraie route (`test_document_export_range.py`). Le passage par nginx reste non verifie.

### [INFO] Deux branches 413 secondaires non couvertes (base, reduit)

- **Localisation** : `document-parser/api/documents.py:66` (limite atteinte pendant la lecture du flux) ; `document-parser/services/graph_service.py:48`
- **Constat** : le 400 « document Docling invalide » de l'import est maintenant teste (`test_api_endpoints.py:791`). Seul le 413 sur `Content-Length` est teste (`:291`).

### [INFO] Les tests Neo4j ne tournent dans aucune CI (base, reduit)

- **Localisation** : `document-parser/tests/neo4j/conftest.py:1-7`
- **Constat** : la docstring ne pretend plus que la CI demarre Neo4j. Le fait reste : 15 tests jamais executes en CI.

### [INFO] Un test dont le nom promet plus que son assertion (base, inchange)

- **Localisation** : `document-parser/tests/test_pipeline_options.py:368-380`
- **Constat** : `test_create_passes_pipeline_options_to_run` ne verifie que `create_task.assert_called_once()`. La coroutine est maintenant fermee sans etre inspectee, donc les options transmises a `_run_analysis` ne sont toujours pas controlees.

### [INFO] Reasoning : aucune couverture dans le gate (base, inchange)

- **Localisation** : `.github/workflows/release-gate.yml` (aucune occurrence de « reasoning »)

---

## Delta vs re-audit a6fb539

Score : **93 -> 93 (=)**. Items conformes 13/14 -> 13/14. CRIT 0 -> 0, MAJ 1 -> 1, MIN 3 -> 1, INFO 11 -> 12. Suites : backend 1501 -> 1559 passed (+58), 15 -> 15 skipped, 4 -> 0 warning ; frontend 586 -> 605 (+19), 62 -> 65 fichiers.

Le score ne bouge pas parce que le seul item non conforme, 9.1.3, ne depend que de `e2e/` et de la CI UI, que la remediation n'a pas touches. Le gain reel se lit dans les MIN et les INFO.

| Ecart de la base | Statut |
|------------------|--------|
| [MAJ] 9.1.3 Karate UI | **Inchange** |
| [MIN] `document_versions` sans test HTTP | **Corrige** (`fea6e57`) : 9 tests sur service et SQLite reels, dont 404, 409, 503 et l'etat des chunks apres restauration |
| [MIN] 64 tests hors CI faute de `docling` | **Reduit** : warnings corriges ; les 64 tests restent hors CI |
| [MIN] `LocalChunker` + commentaire faux | **Reduit -> INFO** : commentaire corrige, renvoi verifie vers un e2e `@regression` |
| [INFO] `PdfPageCanvas` jamais monte | **Corrige** (`450dad6`), trous residuels en INFO |
| [INFO] Aucune requete `Range` testee | **Corrige cote pytest** (`fea6e57`, 6 tests) ; nginx reste en INFO e2e |
| [INFO] Poppler reel seulement en e2e | **Corrige** (`test_page_raster_real.py`, PNG + WebP + DPI) |
| [INFO] 5 commandes editeur jamais passees par HTTP | **Corrige** : `setHeadingLevel`, `mergeText`, `deleteElement`, `deleteElements`, `moveElement` (3 placements) + 400 sur fusion interdite + historique d'un revert (`test_analysis_edits_api.py:176-312`) |
| [INFO] Import 400 non teste | **Corrige** ; deux 413 restent |
| [INFO] Docstring Neo4j fausse | **Corrigee** ; Neo4j toujours hors CI |
| [INFO] Trou de process du merge | **Reduit** (CI sur push `release/**`, `pipefail`) ; branche toujours non poussee |
| [INFO] Upgrade sur copie de schema, PDF inutilises, e2e API, nom de test trompeur, reasoning | Inchanges |

Nouveaux : 4 INFO (inspecteur non verifie au cablage et ordre 422/404, trous residuels PDF.js, skips poppler silencieux, `LocalChunker` retrograde de MIN).

---

## Tests modifies ou deplaces par la remediation

### Methode

1. **Ids collectes** : `git archive a6fb539 document-parser` extrait dans le scratchpad, puis `pytest --collect-only -q` dans les deux arbres avec le meme `.venv`. Resultat : 1516 ids -> 1574 (= 1559 + 15 skips), 70 ajoutes, 12 disparus.
2. **Assertions** : nombre de lignes d'assertion par fichier de test modifie, a `a6fb539` puis a `a12b744`. Une seule baisse : `test_document_service.py` (34 -> 31), expliquee par les deplacements ci-dessous. Puis `git diff --word-diff` des fichiers renommes : les valeurs attendues sont identiques, seuls les noms de fonctions changent.
3. **Cibles de `patch()`** : les 16 cibles en chaine de `tests/` (hors appels `client.patch` sur des URL) resolvent toutes dans l'arbre actuel. Aucun `create=True`. Aucun `monkeypatch.setattr(..., raising=False)`, seulement des `delenv`. Les `patch.object` sans `create` echoueraient bruyamment.
4. **Fakes contre `domain/ports.py`** : methodes de port renommees `latest_parsed_ids` -> `find_latest_parsed_ids`, `parsed_document_id` -> `find_parsed_document_id`, `dfs_order` -> `list_dfs_order`, `glyphs` -> `read_glyphs`. Aucune occurrence de l'ancien nom dans `tests/` hors variables locales. Les fakes de `navigation_fixtures.py` et `test_page_text.py` portent le nouveau nom. Plus largement, des 139 fonctions de production supprimees ou renommees, aucune n'est encore appelee ou patchee par un test.
5. **Frontend** : titres `describe`/`it` compares fichier par fichier entre les deux commits (`npx vitest list` non utilise : il demanderait un `node_modules` dans l'arbre extrait). Resultat : 697 -> 719 titres, aucun fichier supprime, et les 29 titres disparus sont tous renommes avec la fonction qu'ils testent : 27 `describe` (`analysisProgress` -> `computeAnalysisProgress`, etc.) et 2 `it` de `feature-flags/store.test.ts` (`modeFlags()` -> `getModeFlags()`), avec le meme nombre d'assertions par fichier.

### Les 12 ids disparus, un par un

| Id disparu (`test_document_service.py::`) | Devenu | Assertion conservee |
|-------------------------------------------|--------|---------------------|
| `TestCountPages::test_returns_page_count` | `test_pdf_inspector.py:106` | oui, cible `infra.pdf_inspector.pdfinfo_from_bytes` |
| `TestCountPages::test_returns_none_on_error` | `test_pdf_inspector.py:110` | oui ; s'y ajoute le cas `RuntimeError` (`:117`) |
| `TestPageSizes::test_reads_the_size_of_every_page` | `test_pdf_inspector.py:17` | identique |
| `TestPageSizes::test_opens_the_pdf_by_path_not_by_bytes` | `test_pdf_inspector.py:29` | identique (#398) |
| `TestPageSizes::test_raises_on_a_file_that_is_not_a_pdf` | `test_pdf_inspector.py:40` | identique |
| `TestPageSizes::test_raises_file_not_found_on_a_missing_file` | `test_pdf_inspector.py:47` | identique |
| `TestPageSizes::test_resolves_docker_upload_path_from_local_worktree` | `test_document_service.py:232` (`TestResolveStoragePath`) | identique |
| `TestGeneratePreview::test_returns_webp_bytes_at_the_same_page_size` | `test_preview_service.py:131` | identique (taille et pixels) |
| `TestGeneratePreview::test_returns_png_bytes` | `test_preview_service.py:124` (signature PNG reelle) et `test_page_raster.py:21` | oui, et plus fort (vrai PNG au lieu d'un `MagicMock.save`) |
| `TestGeneratePreview::test_renders_only_the_requested_page_from_the_path` | `test_page_raster.py:21-29` (deja present a `a6fb539`) | oui : `convert_from_path(str(pdf), first_page=2, last_page=2, dpi=110)` |
| `TestGeneratePreview::test_raises_on_invalid_page` | `test_page_raster.py:31` (deja present) ; contrat HTTP `test_api_endpoints.py:341`, service `test_preview_service.py:58` | oui |
| `TestGeneratePreview::test_raises_file_not_found_on_a_missing_file` | `test_page_raster.py:41` (deja present, verifie aussi que poppler n'est pas appele) ; `test_page_raster_real.py:71` | oui |

**Aucun test supprime sans equivalent, aucune assertion perdue.**

### Tests reecrits pour un refactoring

- `test_document_service.py:64-110` (`TestUploadValidation`) : `patch("services.document_service._count_pages", ...)` remplace par un inspecteur injecte (`_counting(n)`). Les assertions sont identiques. Le vrai chemin est couvert a cote, sur `PdfiumInspector` reel : `test_document_service.py:133-166` et `test_api_endpoints.py:256`.
- `test_analysis_service.py:317-350` (`TestCountPdfPages`) : `_count_pdf_pages(path)` remplace par `_count_pages` sur `PdfiumInspector()` reel. Memes 4 cas, memes valeurs. `TestBatchedConversion` (`:598`) injecte un inspecteur au lieu de patcher.
- `test_analysis_service.py:226`, `:266` : `pytest.raises(ValueError)` resserre en `InvalidDoclingDocumentError`. C'est plus strict, pas plus lache.
- `test_api_endpoints.py:364-388` : le patch de `DocumentService.generate_preview` devient un `PageRasterizer` injecte. Memes 4 rendus attendus ; `args[0]` est maintenant `str(pdf)` et le kwarg s'appelle `fmt`, ce qui suit la signature du port (`domain/ports.py:636`).
- `test_analysis_page_count.py:44-46` : changement de sens voulu (« sans inspecteur, lots desactives »). Il suit le retrait de pdfium de `services/`, verifie par `test_architecture.py` (nouveaux cas `pypdfium2` et `pdf2image`). Le test est juste ; le risque qu'il laisse ouvert est en INFO.
- `test_pipeline_options.py:326-329`, `:347` : correction des warnings, assertions inchangees.
- `test_analysis_edits_api.py:26-32` : la fixture gagne un titre et un troisieme paragraphe. Les tests existants (`:105-195`) gardent des assertions valables : ils ciblent `First` par texte, pas par position.
- Renforcements : details des 404 de `/pages` (`test_api_endpoints.py:435-438`), de l'export editeur desactive (`:552`) et de l'import (`:789`) ; `storeLinks` verifie sur `GET /documents/{id}` (`:188`) ; `vi.clearAllMocks()` ajoute dans `AnalysisDetailPage.test.ts:23`, ce qui rend utiles les `not.toHaveBeenCalled()` des nouveaux cas.

**Aucun test affaibli trouve.**

### Qualite des nouveaux tests

- **Peuvent-ils echouer ?** (mutation par la pensee)
  - Versions : inverser le tri, perdre un alias camelCase, ne plus filtrer la version d'un autre document, restaurer malgre une analyse non terminee : chacun casse au moins un test. `_live_state` relit SQLite et verifie que rien n'a change apres un 404 ou un 409.
  - Export par plages : passer de `FileResponse` a une reponse en memoire casse 5 tests (206 et `Content-Range` exacts).
  - Commandes editeur : une erreur d'alias dans `_to_edit_commands` (`api/analysis_edits.py:84-102`) casse le test de la commande concernee. Les 3 placements de `moveElement` sont couverts.
  - `PdfPageCanvas` : supprimer l'`await previous.promise` (`:44`) casse `:97` ; supprimer la garde `:52` casse `:149` ; ne plus annuler au demontage casse `:117`.
  - Store editeur : ne plus vider le minuteur casse `:209` ; ne plus annuler casse `:230`.
  - Seul test non discriminant : « late result » de `usePdfDocument` (INFO).
- **Collaborateurs** : reels pour versions, export, poppler, upload (`PdfiumInspector`), editeur (Docling + SQLite). Mocks seulement aux frontieres : `PdfPageCanvas` et `usePdfDocument` mockent PDF.js, ce qui est raisonnable sous jsdom ; `test_preview_service.py` mocke les ports pour tester l'orchestration.
- **Determinisme** :
  - `test_pdf_inspector.py:86-100` tient le verrou dans le fil principal, puis verifie que le lecteur attend (`done.wait(0.1)` faux), puis qu'il finit (`join(5)`). Ce test ne peut pas echouer a tort. Au pire, sur une machine tres lente, il raterait une regression : le seul cas est une lecture d'un PDF d'une page qui prendrait plus de 100 ms.
  - `:70-84` lit `pdfium_lock.locked()` au moment de l'ouverture. C'est valable que le verrou soit celui de Docling ou le `threading.Lock` local (`infra/pdfium_lock.py:12-15`), donc en local comme en CI.
  - `test_analysis_page_count.py:20-34` compare les identifiants de fil, ce qui est deterministe avec `asyncio.to_thread`.
  - Les horloges simulees sont restaurees dans un `finally`. Les tests canvas forcent `clientWidth` sur le prototype et le retirent en `afterEach`.
  - Une seule execution de chaque suite (consigne). Aucun echec.

---

## Points positifs

- **La remediation a ajoute 58 tests backend et 19 frontend sans en perdre un seul** : les 12 ids disparus sont tous retrouves avec leurs assertions, souvent renforcees.
- **Les refactorings n'ont pas ete payes par les tests** : quand un `patch` sur un detail interne a ete remplace par un port injecte, le vrai adaptateur a recu un test non mocke a cote (upload sur `PdfiumInspector`, rendu poppler reel, comptage pour les lots).
- **Les 4 trous de couverture signales par la base sont fermes sur de vrais collaborateurs** : routes de versions, `Range`, poppler, commandes editeur.
- **Le module `test_pipeline_options.py` est propre** (`-W error::RuntimeWarning` vert), et les tests d'architecture interdisent maintenant `pypdfium2` et `pdf2image` dans `services/`.
- **Discipline intacte** : 0 `.only`, 0 skip sans raison, 0 `create=True`.

---

## Verdict partiel : GO

Score **93/100**, **0 CRITICAL**, **1 MAJOR** (9.1.3, Karate UI, inchange). Les deux suites sont vertes et la remediation n'a affaibli aucun test. Il reste a pousser la branche pour obtenir une CI (backend avec poppler, e2e API `@regression`) sur `a12b744`, et a traiter le MAJ e2e UI avant le tag.

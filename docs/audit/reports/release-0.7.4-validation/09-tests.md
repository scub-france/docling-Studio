# Rapport d'audit : Tests

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `efc0bc5` (arbre de travail ; seuls `docs/audit/reports/release-0.7.4-validation/` et `experiments/mcp-bench/` different du commit, hors perimetre). Branche sans amont : aucun run CI sur cet arbre.
**Nature** : Audit de validation apres la seconde remediation ; base : controle du 2026-11-18 sur `a12b744` (`docs/audit/reports/release-0.7.4-control/09-tests.md`, 93/100).
**Execution des suites** : **oui**. L'auditeur n'a rien lance (consigne machine). Le mainteneur a lance les suites sur l'arbre audite le 2026-11-19 entre 22:58 et 23:05 ; le journal `suites.log` (scratchpad de la session) sert de reference :
- `ruff check` : **10 erreurs** RUF043, toutes dans des fichiers de test (exit 1).
- `ruff format --check` : 4 fichiers a reformater, dont 2 de test (exit 1).
- Backend `pytest` : **1 failed, 1748 passed, 15 skipped** en 22,2 s. Echec : `tests/test_api_host_guard.py::TestMiddleware::test_loopback_is_always_allowed`.
- Frontend `eslint`, `prettier --check`, `vue-tsc` : verts.
- Frontend `vitest run` : **72 fichiers, 633 tests, 633 passed**. Seul bruit : `HTMLCanvasElement.prototype.getContext` (axe-core sous jsdom), deja present dans la base.
- Karate API et UI : non executes (ils demandent la stack). Juges par lecture.

Methode complementaire (lecture seule) : `git diff f8eab8a efc0bc5` sur `document-parser/tests`, `frontend/src`, `e2e`, `.github` ; ids de tests backend extraits par AST dans les deux arbres (`git archive f8eab8a`), sans importer le code ; chaque selecteur `data-e2e` des specs nouvelles ou modifiees cherche dans `frontend/src`.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 14 |
| Score | 81 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 7 |

Calcul : poids conformes 22 / poids total 27 = 81,5 -> **81**. Non conformes : 9.1.1 (poids 3) et 9.1.3 (poids 2).

**Lecture appliquee a 9.1.3** : la meme que la base. L'item demande des tests e2e UI qui *passent*. Les specs sont corrigees sur le papier, mais aucune n'a tourne (ni en local ni en CI), et le scenario PDF.js ne tournera dans aucune CI telle qu'elle est configuree. Item non conforme.
**Autre lecture** (specs corrigees = conforme) : 24/27 = **89**. Le verdict ne change pas : le CRIT de 9.1.1 suffit a faire un NO-GO.
**Apres correction du seul test rouge** (une ligne, voir plus bas) : 25/27 = **93** avec la lecture de la base, 100 avec l'autre.

### Detail par item

| # | Poids | Conforme | Justification |
|---|-------|----------|---------------|
| 9.1.1 | 3 | **Non** | 1 failed / 1748 passed / 15 skipped (Neo4j). Voir CRIT. |
| 9.1.2 | 3 | Oui | 633/633 en 72 fichiers (605 -> 633, 65 -> 72 fichiers). `eslint`, `prettier`, `vue-tsc` verts. |
| 9.1.3 | 2 | **Non** | Specs reecrites mais jamais executees ; le scenario PDF.js n'est pas `@critical` et aucun job ne lance les UI `@regression`. Voir MAJ. |
| 9.2.1 | 2 | Oui | Pas de nouvelle route. `GET /api/analyses/summaries?documentId=` (parametre ajoute) a son test HTTP (`test_api_endpoints.py:693`). |
| 9.2.2 | 2 | Oui | 413 du corps : en-tete declare et corps chunked (`test_body_limit.py:42`, `:50`) ; 421 du controle de `Host` (`test_api_host_guard.py:52`, `:65`) ; 422 avant 404 sur l'export edite (`test_api_endpoints.py:609`) ; formes typees de l'editeur dans `test_analysis_edits_api.py`. |
| 9.2.3 | 2 | Oui | `CurrentAnalysis` sur SQLite reel (`test_current_analysis.py`, 12 tests), `DocumentFileStore` reel (`test_document_file_store.py`), regles d'edition et de chunks au domaine. Ecart partiel (deux gardes sans test apres deplacement) en MIN. |
| 9.2.4 | 1 | Oui | Nouveau : `test_analysis_edit_rules.py`, `test_heading_tree.py`, `test_chunk_editing.py` reecrit sur la nouvelle API du domaine. |
| 9.2.5 | 2 | Oui | Nouveaux tests : `pendingDraft`, `commandStacks`, `mergeSelection`, `previewScheduler`, `PageRaster`, `cssTokens`, `BboxCanvas.logic` ; store document sur `currentAnalysisId` (`store.test.ts:262-300`, `:420`). |
| 9.3.1 | 3 | Oui | 0 `.only` / `fdescribe` / `fit` / `xit` / `.skip(` dans `frontend/src` et `e2e/`. |
| 9.3.2 | 1 | Oui | Aucun nouveau marqueur de skip ; les 8 existants ont une `reason`. |
| 9.3.3 | 2 | Oui | Horloges simulees restaurees en `afterEach` (`previewScheduler.test.ts:5-6`) ; globals restaurees (`pendingDraft.test.ts:19`). L'echec de 9.1.1 est stable, pas aleatoire. |
| 9.3.4 | 2 | Oui | `CurrentAnalysis`, export, restauration et repos sur SQLite reel ; `LocalDocumentFileStore` reel. Le MIN « 64 tests sans Docling en CI » est corrige sur le papier par le job `backend-docling` (`ci.yml:62-97`), qui n'a pas encore tourne (INFO). |
| 9.3.5 | 1 | Oui | Messages d'erreur exacts (`test_chunk_editing.py`, `test_analysis_edit_rules.py`), forme JSON complete des reponses typees. |
| 9.3.6 | 1 | Oui | Noms descriptifs (`test_a_cleared_selection_does_not_fall_back`, `test_split_halves_inherit_the_source_metadata`...). |

---

## Ecarts constates

### [CRIT] Un test backend echoue : le client de test ne sait pas lire une adresse IPv6 dans `base_url`

- **Localisation** : `document-parser/tests/test_api_host_guard.py:57-59` (boucle), `:42-44` (`_get`) ; trace dans `starlette/testclient.py:228`
- **Constat** : `test_loopback_is_always_allowed` passe `base_url="http://[::1]:8000"` au `TestClient`. Le transport de Starlette coupe le `netloc` au premier `:` (`netloc.split(":", 1)`) et tente `int(":1]:8000")` : `ValueError` avant meme d'atteindre le middleware. Le defaut est dans le test, pas dans `infra/host_guard.py` : `[::1]` est dans `LOOPBACK_HOSTS` (`host_guard.py:33`) et le cas est deja couvert au niveau unitaire (`test_api_host_guard.py:92`, `:104`). Ce test n'a jamais tourne avant la mesure du mainteneur.
- **Regle violee** : 9.1.1 (poids 3).
- **Remediation** : garder `base_url` par defaut et forcer l'en-tete, par exemple `client.get(path, headers={"host": "[::1]:8000"})` pour l'entree IPv6 ; ou retirer `"http://[::1]:8000"` de la boucle, puisque `is_allowed_host("[::1]:3000", ...)` est deja teste. Effort XS.

### [MAJ] Karate UI : les specs sont corrigees, mais rien n'a tourne et le scenario PDF.js ne tournera dans aucune CI (base, reduit)

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-viewer.feature:1`, `:32-51` ; `e2e/ui/src/test/resources/analyses/analysis-editor.feature:13-56` ; `e2e/ui/src/test/resources/documents/doc-legacy-mode-links.feature` ; `e2e/CONVENTIONS.md:167` ; `.github/workflows/ci.yml:215`, `:276-284` ; `.github/workflows/release-gate.yml:3-5`, `:705-713`
- **Constat** :
  - Fait (`3a794e1`) : les 3 specs obsoletes et le helper `_open-launch-modal.feature` sont supprimes, plus aucune reference ; `doc-legacy-mode-links.feature` verifie que les 6 anciens `?mode=` ouvrent la vue Parse, ce que confirment `modes.ts:30-38` et la garde `app/router/index.ts:52-67`. Le premier scenario de `analysis-editor.feature` est `@critical`. Le job `e2e-ui` tourne aussi sur un push vers `release/**` et ne lance que `UIRunner#testCritical` (`23e4c81`). Tous les selecteurs `data-e2e` des trois specs existent dans `frontend/src` (statiques ou par prefixe dynamique : `analysis-editor-tree-item-*`, `analysis-editor-item-*`, `analysis-editor-history-toggle-*`, `preview-page-*`). Le flag editeur est actif par defaut dans la stack (`docker-compose.yml:200`).
  - Reste : (1) aucune de ces specs n'a tourne ; la branche n'est pas poussee, donc meme le `@critical` editeur n'a pas de run. (2) `doc-viewer.feature` est `@ui @regression` : le scenario « PDF.js draws page 1 » n'est selectionne par aucun job (`@critical` seul en CI et dans le gate ; `CONVENTIONS.md:167` dit « UI: no CI job » pour `@regression`). La preuve que PDF.js dessine reste donc hors CI. (3) Le commentaire `doc-viewer.feature:40-43` dit qu'aucun `data-e2e` ne distingue le canvas PDF.js de l'image de repli ; c'est faux depuis `4c54fe3` (`PdfPageCanvas.vue:5` `pdf-page-canvas`, `PageRaster.vue:14` `preview-fallback-image`), et le scenario utilise encore des selecteurs par type d'element. Ils restent justes : `[data-e2e=bbox-canvas]` est un `div` (`BboxCanvas.vue:2`), donc `canvas:not([data-e2e=bbox-canvas] canvas)` vise bien le canvas PDF.js.
- **Regle violee** : 9.1.3.
- **Remediation** : passer le scenario PDF.js en `@critical` (ou ajouter un job UI `@regression` sur `release/**`) ; utiliser `[data-e2e=pdf-page-canvas]` et `[data-e2e=preview-fallback-image]` et retirer le commentaire ; pousser la branche (ou une PR vers `main`) pour obtenir un rapport Karate UI. Effort S.

### [MIN] Deux gardes ont perdu leur test en changeant de place

- **Localisation** : `document-parser/bootstrap/factories.py:103-110` ; `document-parser/services/chunk_service.py:267-272` ; anciennement `tests/test_docling_agent_reasoning.py` (`TestProviderRejection`) et `tests/test_chunk_editing.py` (`test_merge_across_documents_raises`)
- **Constat** :
  1. Le refus d'un fournisseur autre qu'Ollama est passe du constructeur du runner (`NotImplementedError`) a `build_reasoning_runner`, qui rend `None` avec un warning. Le test du constructeur est supprime avec la garde, et aucun test n'exerce `LLM_PROVIDER_TYPE != "ollama"` dans la fabrique (`rg llm_provider_type tests` : 0).
  2. `merge` du domaine ne verifie plus le document des chunks : c'est `ChunkService.merge_chunks` qui ne garde que les chunks du document (`find_for_document`) et leve `ChunkNotFoundError` pour un id inconnu ou etranger. Aucun test de `test_chunk_service.py` (`:271-311`) ni de `test_document_chunks_api.py` ne fusionne un id d'un autre document.
- **Regle violee** : 9.2.3 (partiel).
- **Remediation** : un test de `build_reasoning_runner` avec `llm_provider_type="openai"` (attendu `None`) ; un test `merge_chunks(doc, ["c-0", "x-0"])` avec `x-0` d'un autre document (attendu `ChunkNotFoundError`, 404 en HTTP). Effort XS.

### [INFO] Le lint casse le job backend de la CI avant les tests

- **Localisation** : `tests/test_analysis_edit_rules.py:121`, `:130`, `:135`, `:143`, `:155`, `:160`, `:172` ; `tests/test_chunk_editing.py:198`, `:200` ; `tests/test_export_service.py:134` ; `.github/workflows/ci.yml:49-53` ; `.github/workflows/release-gate.yml:50`
- **Constat** : 10 `match="^..."` sans prefixe `r` (RUF043). Le job `backend` lance `ruff check .` avant `pytest` : en CI, la suite ne tournerait pas du tout. Les assertions sont justes (aucun echec a l'execution). `ruff format --check` signale aussi `tests/test_analysis_editing.py` et `tests/test_api_endpoints.py`, mais aucune CI ne lance `ruff format --check`. Releve ici parce qu'il empeche la CI d'executer les tests ; le fond releve de l'audit 10.
- **Remediation** : `match=r"^..."` sur les 10 lignes ; `ruff format` sur les 4 fichiers. Effort XS.

### [INFO] Les tests Docling ont un job CI, qui n'a jamais tourne (base MIN, retrograde)

- **Localisation** : `.github/workflows/ci.yml:62-97`
- **Constat** : `backend-docling` installe le groupe `local`, verifie que `docling` s'importe (sinon les tests se sauteraient et le job passerait vide) et lance les 4 fichiers concernes. Il tourne sur push (`main`, `release/**`) et sur PR vers `main`, pas sur une PR vers `release/**`. Localement, ces tests ont tourne (15 skips, tous Neo4j). Aucune preuve CI tant que la branche n'est pas poussee.

### [INFO] Le test de rendu PDF.js mesure des pixels sombres

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-viewer.feature:50`
- **Constat** : le `waitUntil` lit `getImageData` et cherche un pixel opaque de composantes < 128. C'est une bonne preuve que PDF.js dessine, a condition que `medium.pdf` contienne du texte noir (genere par `e2e/generate-test-data.py`). Non execute, donc non verifie.

### [INFO] Trous residuels dans les nouveaux tests PDF.js (base, inchange)

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.test.ts:60-81` ; `frontend/src/features/document/ui/PdfPageCanvas.vue:35`, `:64`
- **Constat** : « late result » non discriminant, seuil `ResizeObserver` et filtre `RenderingCancelledException` non exerces. Aucun de ces fichiers n'a change.

### [INFO] Huit tests poppler se sautent sans bruit sans poppler (base, inchange)

- **Localisation** : `document-parser/tests/test_page_raster_real.py:19-22`, `document-parser/tests/test_document_service.py:135`, `document-parser/tests/test_api_endpoints.py:275`

### [INFO] Aucun run CI sur l'arbre valide (process, base, inchange)

- **Constat** : 14 commits depuis `a12b744`, branche non poussee. Tous les chiffres de ce rapport viennent d'executions locales du mainteneur.

### [INFO] Inchanges depuis la base

- `LocalChunker` sans test pytest (`tests/test_chunking.py:486-488`, renvoi vers `rechunk.feature`).
- Upgrade 0.7.3 -> 0.7.4 teste sur une copie de schema (`tests/test_database_upgrade.py`).
- `editor-provenance.pdf` et `editor-readonly.pdf` sans scenario (`e2e/generate-test-data.py`).
- Pas d'e2e API pour l'editeur, les resumes ni `Range` a travers nginx ; Neo4j hors CI ; `test_create_passes_pipeline_options_to_run` promet plus qu'il ne verifie ; reasoning absent du gate.

Corriges depuis la base (INFO fermees) : le cablage de l'inspecteur dans `build_analysis_service` est teste (`tests/test_bootstrap_pdf_wiring.py:28`) ; l'ordre 422 avant 404 de l'export edite est teste (`tests/test_api_endpoints.py:609-617`).

---

## Delta vs controle

Score : **93 -> 81 (-12)**. Items conformes 13/14 -> 12/14. CRIT 0 -> 1, MAJ 1 -> 1, MIN 1 -> 1, INFO 12 -> 7 (la derniere INFO regroupe les observations inchangees de la base). Verdict GO -> **NO-GO**.

Suites : backend 1559 passed / 0 failed (base) et 1563 (dernier commit execute `f8eab8a`) -> **1748 passed / 1 failed**, 15 skipped inchanges ; frontend 605 -> **633** passed, 65 -> 72 fichiers. Ids de tests backend (AST, fonctions avant parametrisation) : 1471 -> 1623, 167 ajoutes, 15 disparus.

La baisse vient d'un seul test, ecrit sans etre execute. Sur le fond, la remediation tient : 186 tests backend collectes de plus depuis `f8eab8a` (1578 -> 1764) et 28 frontend, les specs e2e obsoletes traitees, les tests Docling cables en CI.

| Ecart du controle | Statut |
|-------------------|--------|
| [MAJ] 9.1.3 Karate UI | **Reduit** : specs obsoletes remplacees, editeur `@critical`, `e2e-ui` sur `release/**`, scenario PDF.js ecrit. Reste : rien execute, scenario PDF.js hors de toute CI. |
| [MIN] 64 tests hors CI faute de Docling | **Corrige sur le papier -> INFO** (job `backend-docling`, jamais lance) |
| [INFO] Inspecteur non verifie au cablage, ordre 422/404 | **Corriges** |
| [INFO] Trous PDF.js, skips poppler, LocalChunker, upgrade, PDF inutilises, e2e API, Neo4j, nom trompeur, reasoning | Inchanges |
| [INFO] Aucun run CI | Inchange |

Nouveaux : 1 CRIT (test IPv6), 1 MIN (deux gardes sans test apres deplacement), 2 INFO (lint qui bloquerait la CI, mesure des pixels PDF.js).

---

## Tests ecrits sans execution : echecs previsibles

Les suites ont tourne pendant l'audit : le tableau donne les echecs **observes**, puis les risques que seule une execution en CI ou de la stack peut lever. Honnetete de methode : le journal backend etait deja disponible au debut de l'audit, donc la ligne 1 n'est pas une prediction a l'aveugle. La lecture du frontend (10 fichiers de test nouveaux ou modifies, plus les tests inchanges des composants refactores : `BboxCanvas.test.ts`, `AnalysisEditor.a11y.test.ts`, `analysis-editor/store.test.ts`, `PagePreviewWithOverlay.test.ts`) a ete faite avant de lire la partie frontend du journal ; elle ne prevoyait aucun echec, et vitest a confirme 633/633.

| # | Test / cible | Certitude | Cause | Correctif |
|---|--------------|-----------|-------|-----------|
| 1 | `tests/test_api_host_guard.py::TestMiddleware::test_loopback_is_always_allowed` (`:58`) | **Observe** | `TestClient(base_url="http://[::1]:8000")` : Starlette fait `int(":1]:8000")` (`testclient.py:228`) | `headers={"host": "[::1]:8000"}` sur le `base_url` par defaut, ou retirer l'entree IPv6 (deja couverte `:92`, `:104`) |
| 2 | `ruff check` sur 10 lignes de `tests/` (job `backend`, `ci.yml:50` ; gate `release-gate.yml:50`) | **Observe** | RUF043 : `match="^..."` sans `r` | prefixe `r` sur `test_analysis_edit_rules.py:121,130,135,143,155,160,172`, `test_chunk_editing.py:198,200`, `test_export_service.py:134` |
| 3 | `ruff format --check` | **Observe** (hors CI) | `tests/test_analysis_editing.py`, `tests/test_api_endpoints.py`, `infra/docling_editor.py`, `services/current_analysis.py` | `ruff format` |
| 4 | `analysis-editor.feature` scenario `@critical` (`:13-56`) | Possible | Jamais execute ; depend de Docling Serve (analyse reelle de `editor-text.pdf`) et du slug du texte (`editor-alpha-critical-marker`) | Lancer `UIRunner#testCritical` sur la stack avant le tag |
| 5 | `doc-viewer.feature` « PDF.js draws page 1 » (`:32-51`) | Possible | Jamais execute ; depend du worker PDF.js empaquete et des requetes par plages a travers nginx, invisibles sous jsdom | Le lancer a la main (`UIRunner#testLocal`) ou le passer `@critical` |
| 6 | `doc-legacy-mode-links.feature` (6 exemples) | Possible (faible) | Jamais execute ; la logique lue (`modes.ts:30-38`, garde `index.ts:52-67`) donne bien `mode=parse` | idem |
| 7 | Job `backend-docling` (`ci.yml:62-97`) | Possible (faible) | Jamais lance en CI ; roues torch CPU, temps d'installation. Les memes tests passent en local | Pousser sur `release/0.7.4` |

Aucun echec prevu par lecture sur les points de la consigne : imports (`services/chunk_errors.py`, `domain/document_tree.py`) resolus, fixtures definies, fakes de `navigation_fixtures.py` a jour, aucune cible de `patch()` disparue, aucun `asyncio.run` dans une boucle active (les 3 `asyncio.run` ajoutes sont dans des tests synchrones, `asyncio_mode = auto` dans `pytest.ini:2`), horloges simulees restaurees. Tout cela est confirme par l'execution.

---

## Tests supprimes ou affaiblis

Methode : ids extraits par AST des deux arbres (`f8eab8a` via `git archive`, arbre de travail), puis `git diff` de chaque fichier concerne. 15 ids backend disparus, 1 test frontend renomme, 4 fichiers e2e supprimes.

| Id disparu | Devenu | Assertions |
|------------|--------|-----------|
| `test_chunk_editing.py::test_merge_removes_sources_and_returns_new_chunk` | `test_merge_orders_the_sources_by_sequence`, `test_merge_keeps_the_first_source_headings_and_page`, `test_merge_gives_a_fresh_chunk_of_the_document` ; retrait des sources au service (`test_chunk_service.py:271`, `:282`) | Conservees, sauf une **changee volontairement** : la page du chunk fusionne etait le minimum des sources, c'est maintenant celle de la premiere source (aligne sur ce que faisait le service) |
| `test_chunk_editing.py::test_merge_across_documents_raises` | **Aucun equivalent** : le domaine ne voit plus qu'un document, le service filtre par document sans test | **Affaibli** (MIN) |
| `test_chunk_editing.py::test_split_creates_two_new_chunks` | `test_split_cuts_the_text_at_the_offset` ; service `test_chunk_service.py:219` | Conservees |
| `test_chunk_editing.py::test_split_preserves_headings_on_both_halves` | `test_split_halves_inherit_the_source_metadata` | Renforcees (bboxes, doc_items, copies, `token_count`) |
| `test_chunk_editing.py::test_split_shifts_subsequent_sequences` | `test_chunk_service.py:234`, `:243` ; domaine `test_split_halves_follow_the_source_sequence` | Conservees au service |
| `test_chunk_editing.py::test_split_at_zero_offset_raises`, `::test_split_beyond_text_length_raises` | `test_split_offset_out_of_range_raises` (0, -1, 6, 99) | Renforcees (message exact) |
| `test_docling_agent_reasoning.py::TestProviderRejection::test_rejects_non_ollama_provider` | **Aucun** : la garde est passee dans `bootstrap/factories.py:103`, sans test | **Affaibli** (MIN) |
| `test_document_service.py::TestResolveStoragePath::test_resolves_docker_upload_path_from_local_worktree` | `test_document_file_store.py:200` (+ fichier absent `:205`) | Conservees |
| `test_export_service.py::TestExportAnalysisSelection::test_defaults_to_the_latest_completed_analysis` | `test_defaults_to_the_current_analysis` (+ `test_no_current_analysis_is_not_found`) | Conservees, selon la nouvelle regle (analyse courante) |
| `test_ollama_provider.py::test_provider_exposes_type_host_default_model_id` | `test_provider_exposes_host_and_default_model_id` | L'assertion sur `type` part avec l'attribut |
| `test_repos.py::TestAnalysisRepo::test_find_latest_completed_by_document`, `::..._none`, `::test_find_latest_completed_prefers_newest_completed_even_without_json` | La methode n'existe plus (0 occurrence dans le code). La lecture passe par `CurrentAnalysis` : `test_current_analysis.py` (analyse plus recente encore en cours `:111`, aucune analyse `:119`, selection effacee `:124`, document sans etat `:130`, analyse sans parse `:141`) | Remplacees, regle plus precise |
| `test_version_service.py::TestRestore::test_restore_soft_deletes_live_chunks_in_one_statement` | `test_restore_replaces_live_chunks_in_one_transaction` | Conservees (un appel `replace_for_document`) |
| Frontend `analysis/api.test.ts` « fetchDocumentAnalyses calls GET /api/analyses?documentId=:id » | « fetchDocumentAnalysisSummaries filters the summaries by document » | Renforcee (encodage de l'id verifie) |
| E2E `doc-chunk-view.feature`, `doc-ingest-view.feature`, `doc-strategy-popover.feature`, `_open-launch-modal.feature` | `doc-legacy-mode-links.feature` ; chunks par `doc-tab-chunk-mode.feature` et `analyses/rechunk.feature` | Les vues testees n'existent plus ; plus aucune reference au helper |

Autres modifications : `test_analysis_editing.py`, `test_document_analysis_repo.py`, `test_navigation_service.py`, `test_preview_service.py`, `test_api_endpoints.py` ont ete rebranches sur les nouveaux ports (`DocumentFileStore`, `CurrentAnalysis`, `DocumentAnalysisState`) sans perte d'assertion trouvee. Un seul fichier frontend inchange voit son montage modifie : `PagePreviewWithOverlay.test.ts:40` desactive le stub de `PageRaster` pour continuer a compter les `PdfPageCanvas`, ce qui garde le test discriminant.

**Bilan : 2 tests supprimes sans relais (MIN), 1 assertion changee volontairement (page du chunk fusionne), aucun autre test affaibli.**

---

## Points positifs

- **Le frontend ecrit sans execution est passe du premier coup** : 28 tests de plus, `eslint`, `prettier` et `vue-tsc` verts.
- **Cote backend, un seul echec pour 186 tests collectes de plus**, et il tient au client de test, pas au code.
- **Les specs e2e obsoletes sont traitees proprement** : supprimees, remplacees par une spec qui verifie le comportement actuel, sans reference morte.
- **Les regles metier sont testees au domaine avec leurs messages exacts** (`test_analysis_edit_rules.py`, `test_chunk_editing.py`, `test_heading_tree.py`), et l'analyse courante sur SQLite reel (`test_current_analysis.py`).
- **Deux INFO de la base sont fermees** : cablage de l'inspecteur, ordre 422/404.

---

## Verdict partiel : NO-GO

Score **81/100**, **1 CRITICAL** (9.1.1 : un test rouge), 1 MAJOR (9.1.3, reduit), 1 MINOR. Le score depasse 80 mais la regle absolue s'applique. Pour revenir au GO : corriger `test_api_host_guard.py:58` (une ligne) et les 10 `match=` (sinon la CI ne lance meme pas pytest), relancer `pytest`. Le score remonte alors a 93. Avant le tag : pousser pour obtenir la CI (`backend-docling`, e2e API `@regression`, `e2e-ui` `@critical`) et faire tourner au moins une fois le scenario PDF.js.

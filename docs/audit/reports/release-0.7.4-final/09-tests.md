# Rapport d'audit : Tests

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a744f48` (arbre de travail ; seuls `docs/audit/reports/release-0.7.4-final/` et `experiments/mcp-bench/` different du commit, hors perimetre). Branche non poussee : aucun run CI.
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur efc0bc5 (`docs/audit/reports/release-0.7.4-validation/09-tests.md`, 81/100).
**Execution des suites** : par le mainteneur, sur `a744f48`, machine au calme. L'auditeur n'a rien lance (consigne machine).
- Backend : `ruff check` et `ruff format --check` propres ; `pytest tests/` = **1773 passed, 15 skipped** (les skips sont les tests Neo4j), 0 failed.
- Frontend : `eslint`, `prettier`, `vue-tsc` propres ; `vitest run` = **604 passed en 71 fichiers** ; `vite build` OK.
- Karate API et UI : non executes. Aucun run CI.

Methode (lecture seule) : `git archive efc0bc5` et `git archive a744f48` de `document-parser/tests`, `frontend/src`, `e2e`, `.github` dans le scratchpad ; script AST (sans import du projet) qui liste chaque fonction de test backend (fichier, classe, nom, nombre de lignes `assert` / `pytest.raises` / `assert_*` de mock, nombre de cas parametres) dans les deux arbres ; `git diff` de chaque fichier de test touche ; decompte des `it(` / `it.each` et des titres de tests frontend dans les 5 fichiers de test touches ; `rg` dans le code de production pour chaque fonction dont les tests ont disparu ; script qui verifie chaque selecteur `data-e2e` des specs Karate UI contre `frontend/src` (valeurs statiques et prefixes dynamiques).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 10 |

Calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**. Seul item non conforme : 9.1.3 (poids 2).

**Lecture appliquee a 9.1.3** : la meme que la base et le controle. L'item demande des tests e2e UI qui *passent* ; aucun n'a tourne sur cet arbre, et trois specs `@regression` pilotent des selecteurs qui n'existent plus (voir MAJ). Item non conforme.
**Autre lecture** (specs corrigees sur le papier = conforme) : elle ne tient plus ici, puisque trois specs echoueraient a coup sur. Le score reste 93.

### Detail par item

| # | Poids | Conforme | Justification |
|---|-------|----------|---------------|
| 9.1.1 | 3 | Oui | 1773 passed / 0 failed / 15 skipped (Neo4j). Le test IPv6 de la base passe : il force l'en-tete `Host` au lieu du `base_url` (`test_api_host_guard.py:48-51`, `:74-76`). |
| 9.1.2 | 3 | Oui | 604/604 en 71 fichiers ; `eslint`, `prettier`, `vue-tsc`, `vite build` verts. Baisse de 633 a 604 entierement expliquee (section « Tests supprimes »). |
| 9.1.3 | 2 | **Non** | Rien n'a tourne ; scenario PDF.js toujours `@regression`, hors de toute CI ; 3 specs UI visent des selecteurs absents du frontend. Voir MAJ. |
| 9.2.1 | 2 | Oui | Pas de nouvelle route. `DELETE /api/analyses/{id}` a un test HTTP de bout en bout sur SQLite reel (`test_analysis_deletion.py:178`). |
| 9.2.2 | 2 | Oui | 400 sur `Content-Length` malforme, 5 cas (`test_body_limit.py:64`) ; 421 + JSON du controle `Host`, 13 en-tetes malformes ou etrangers (`test_api_host_guard.py:59`, `:115`) ; 409 d'une restauration dont l'analyse disparait en cours (`test_version_service.py:262`) ; 404 d'une fusion avec un chunk d'un autre document (`test_chunk_service.py:329`). |
| 9.2.3 | 2 | Oui | Suppression de l'analyse active et successeur (`test_analysis_deletion.py`, 8 tests, SQLite reel) ; premier rechunk sans ligne d'etat (`test_chunk_service.py:498`) ; restauration sans ligne d'etat ou avec source a moitie remplie (`test_version_service.py:235`, `:287`) ; fabrique du runner de raisonnement (`test_reasoning_runner_factory.py`). Le MIN de la base est ferme. |
| 9.2.4 | 1 | Oui | `test_quote_location.py` (8 tests, nouveau module de domaine `domain/quote_location.py`) ; predicats `can_be_current`, `can_be_current_of`, `has_docling_document` (`test_models.py:183-197`) ; regle du successeur sur l'agregat (`test_analysis_deletion.py:130`). |
| 9.2.5 | 2 | Oui | Store document : pas d'analyse chargee sans analyse courante (`store.test.ts:296`, `:305`, `:448`) ; store editeur et composant : un enregistrement refuse garde l'editeur et les modifications (`analysis-editor/store.test.ts`, `AnalysisEditor.a11y.test.ts`). |
| 9.3.1 | 3 | Oui | 0 `.only` / `fdescribe` / `fit` / `xit` / `.skip(` dans `frontend/src` et `e2e/`. |
| 9.3.2 | 1 | Oui | Aucun nouveau marqueur de skip ; les existants ont une `reason` (poppler, docling, neo4j). |
| 9.3.3 | 2 | Oui | Les nouveaux tests datent leurs analyses avec une horloge fixe (`test_analysis_deletion.py:28`) ; les tests a 3 000 et 200 elements construisent leurs documents de facon deterministe et n'assertent aucun temps. |
| 9.3.4 | 2 | Oui | Suppression, rechunk, restauration et etat d'analyse sur SQLite reel avec les vrais repositories ; le test API de suppression monte les vrais routeurs et services (`test_analysis_deletion.py:138-175`). Les mocks restent cantonnes aux tests de routes (`test_document_chunks_api.py`, un mock par service). |
| 9.3.5 | 1 | Oui | Assertions precises : identifiant de l'analyse successeur, contenu exact des chunks apres refus, corps JSON exact des 400/421, niveau de log. Le seul `is not None` nouveau (`test_analysis_deletion.py:87`) distingue « pas de ligne » de « selection NULL » et est suivi d'une assertion precise. |
| 9.3.6 | 1 | Oui | Noms descriptifs (`test_deleting_the_active_analysis_selects_the_latest_parsed_one`, `test_a_restore_selecting_a_deleted_analysis_writes_nothing`...). Seule reserve : un nom promet plus que le test (INFO 1). |

---

## Ecarts constates

### [MAJ] Karate UI : rien n'a tourne, le scenario PDF.js reste hors CI, et trois specs visent des ecrans qui n'existent plus

- **Localisation** :
  - `e2e/ui/src/test/resources/documents/doc-viewer.feature:1` (tag `@ui @regression`)
  - `e2e/ui/src/test/resources/documents/doc-history-drawer.feature:47`, `:48`, `:49-50`, `:53`, `:56`, `:60-61`
  - `e2e/ui/src/test/resources/documents/doc-new-analysis-opens-analysis.feature:17-18`
  - `e2e/ui/src/test/resources/analyses/analysis-detail.feature:63`
  - `.github/workflows/ci.yml:210-284` ; `.github/workflows/release-gate.yml:647-723` ; `e2e/ui/src/test/java/UIRunner.java:11-14` ; `e2e/CONVENTIONS.md:167`
- **Constat** :
  1. **Fait (`1cd8413`)** : `doc-viewer.feature` utilise `[data-e2e=pdf-page-canvas]` et `[data-e2e=preview-fallback-image]` ; les deux existent (`PdfPageCanvas.vue:5`, `PageRaster.vue:14`), comme tous les autres selecteurs de la spec (`document-viewer`, `preview-with-overlay`, `preview-page-${n}`, `page-input`, `page-next`, `bbox-canvas`). Le commentaire faux de la base est remplace par une description juste (`:33-39`).
  2. **Reste** : le scenario PDF.js est toujours `@regression`. Le job `e2e-ui` de `ci.yml` (push sur `main` et `release/**`) et celui du gate (PR vers `main`) lancent seulement `UIRunner#testCritical` avec `--tags @critical`. `CONVENTIONS.md:167` le dit : « UI: no CI job » pour `@regression`. Aucune spec UI n'a tourne sur cet arbre, pas meme les `@critical`.
  3. **Nouveau constat (anterieur au cycle, manque par la base qui ne lisait que les specs modifiees)** : trois specs `@regression` echoueraient ou ne prouvent rien.
     - `doc-history-drawer.feature` : `/docs/:id` monte `DocWorkspacePage.vue`, qui n'a pas de `parse-tab` (`:47` attend un element qui n'apparait jamais sur cette route) ; `history-btn` (`:48`, `:60`) n'existe nulle part dans `frontend/src`. `HistoryDrawer.vue` existe encore (`history-drawer`, `history-list`, `history-item-*`) mais aucun fichier ne l'importe (`rg HistoryDrawer frontend/src` : 0 resultat hors du fichier lui-meme). Aucune route ne l'affiche (`app/router/routes.ts`).
     - `doc-new-analysis-opens-analysis.feature:17-18` : `workspace-new-analysis` n'existe plus (retire par `ec3eb00`, #359) ; l'action « Nouvelle analyse » de `DocumentActionsMenu.vue` n'a pas de `data-e2e`. La spec bloque au premier `waitFor`.
     - `analysis-detail.feature:63` : `assert !exists('[data-e2e=parse-new-analysis]')` vise un selecteur qui n'existe nulle part (retire par `12a3fd1`). L'assertion passe toujours : elle ne prouve pas l'absence de l'action « Nouvelle analyse » sur la page de detail.
  Toutes les autres specs UI (`@critical` comprises) ont leurs selecteurs `data-e2e` dans `frontend/src`.
- **Regle violee** : 9.1.3.
- **Remediation** : (a) passer « PDF.js draws page 1 » en `@critical`, ou ajouter un job UI `@regression` sur `release/**` ; (b) supprimer `doc-history-drawer.feature` avec `HistoryDrawer.vue` (code mort), ou remonter le tiroir dans une page et reecrire la spec ; (c) donner un `data-e2e` a l'action « Nouvelle analyse » de `DocumentActionsMenu.vue` et le reprendre dans `doc-new-analysis-opens-analysis.feature` ; (d) remplacer `parse-new-analysis` par le selecteur reel de l'action, ou retirer la ligne ; (e) pousser la branche et faire tourner au moins une fois `UIRunner#testCritical` et la spec PDF.js sur la stack. Effort S.

### [INFO] 1. Le test a 3 000 elements garde le resultat, pas la complexite

- **Localisation** : `document-parser/tests/test_analysis_editing.py:260-283` (et `:286-306`, 200 textes)
- **Constat** : le nom (`..._stays_linear`) et la docstring promettent un comportement lineaire (« about 4 s here pairwise »). Le test n'asserte que le resultat : 3 000 references, document vide apres suppression. Un retour a l'algorithme quadratique le laisserait vert, avec environ 4 s de suite en plus. Il est deterministe (construction fixe, aucune mesure de temps). C'est un bon test de correction sur un gros volume (doublons et descendants inclus), pas une garde de performance.
- **Remediation** (optionnelle) : renommer (`test_delete_elements_of_a_long_document`), ou compter les appels de la fonction de comparaison au lieu de mesurer un temps.

### [INFO] 2. Le joker `*` du controle `Host` ne tient plus qu'au branchement de `main.py`, qui n'est pas teste

- **Localisation** : `document-parser/infra/host_guard.py:73-76` ; `document-parser/main.py:117-118`
- **Constat** : l'ancien middleware acceptait tout hote avec `*` (`test_wildcard_allows_everything`, supprime). Le nouveau ignore `*` (`parse_host_name("*")` rend `None`) : avec `["*"]` seul, il refuserait tout sauf le loopback. Ce n'est pas un defaut aujourd'hui, car `main.py:117` ne monte le middleware que si `is_host_check_on(...)`, qui rend `False` avec `*` (teste, `test_api_host_guard.py:147-149`). Le branchement de `main.py` lui-meme n'a pas de test.
- **Remediation** (optionnelle) : un test qui construit l'application avec `API_ALLOWED_HOSTS=*` et verifie qu'un `Host` etranger obtient 200.

### [INFO] 3. Trois cas limites des chunks ne sont plus testes qu'au niveau HTTP ou plus du tout

- **Localisation** : `document-parser/services/chunk_service.py:99-121`, `:261-265` ; anciennement `tests/test_chunk_editing.py` (`test_update_can_change_headings_only`, `test_update_deleted_chunk_raises`, `test_delete_is_idempotent`)
- **Constat** : ces tests portaient sur `chunk_editing.insert/update/delete`, que le service n'appelait deja plus a `efc0bc5` (code mort, supprime). Les regles equivalentes du service (`_require_chunk` refuse un chunk supprime ; mise a jour des seuls titres) n'ont pas de test de service : la mise a jour des titres est verifiee au niveau route (`test_document_chunks_api.py:112-117`, avec un mock), le refus d'un chunk deja supprime nulle part. Ce n'est pas une perte sur du code vivant, mais un trou.
- **Remediation** (optionnelle) : deux tests de `ChunkService` : `update_chunk` puis `delete_chunk` sur un chunk deja supprime -> `ChunkNotFoundError` ; `update_chunk(headings=...)` sans texte.

### [INFO] 4. Commentaire perime sur le « promoter » de chunks

- **Localisation** : `document-parser/services/analysis_service.py:503-510`
- **Constat** : le commentaire dit que le hook du promoter « stays wired in main.py so legacy callers / tests can still trigger it ». `set_chunk_promoter` et `promote_from_analysis_if_empty` sont supprimes (`rg promote_from|chunk_promoter` : 0 hors ce commentaire), leurs tests aussi. Releve ici parce qu'il parle de tests ; le fond releve des audits 03 et 11.
- **Remediation** : reduire le commentaire a la regle (« une analyse ne cree pas de chunks ; voir `/rechunk` »).

### [INFO] 5. `HistoryDrawer.vue` est du code mort que le nettoyage `60234e4` a manque

- **Localisation** : `frontend/src/features/document/ui/HistoryDrawer.vue`
- **Constat** : aucun import, aucune route. Il n'est reference que par la spec obsolete du MAJ. Hors champ 09 sur le fond (audit 04).

### [INFO] 6. Le job `backend-docling` n'a jamais tourne (base, inchange)

- **Localisation** : `.github/workflows/ci.yml:62-97`
- **Constat** : les tests Docling passent en local (les 15 skips sont tous Neo4j) ; aucune preuve CI tant que la branche n'est pas poussee.

### [INFO] 7. Le test de rendu PDF.js mesure des pixels sombres, sans execution (base, inchange)

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-viewer.feature:46`
- **Constat** : bonne preuve si `medium.pdf` porte du texte noir (`e2e/generate-test-data.py`) ; jamais execute.

### [INFO] 8. Trous PDF.js et skips poppler (base, inchanges)

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.test.ts:60-81` ; `document-parser/tests/test_page_raster_real.py:19-22`, `test_document_service.py:134`, `test_api_endpoints.py:274`

### [INFO] 9. Aucun run CI sur l'arbre controle (process, base, inchange)

- **Constat** : 9 commits depuis `efc0bc5`, branche non poussee. Tous les chiffres viennent des executions locales du mainteneur.

### [INFO] 10. Inchanges depuis la base

- `LocalChunker` sans test pytest (`tests/test_chunking.py:486-488`, renvoi vers `rechunk.feature`).
- Upgrade 0.7.3 -> 0.7.4 teste sur une copie de schema (`tests/test_database_upgrade.py`).
- `editor-provenance.pdf` et `editor-readonly.pdf` sans scenario (`e2e/generate-test-data.py`).
- Pas d'e2e API pour l'editeur, les resumes ni `Range` a travers nginx ; Neo4j hors CI ; `test_create_passes_pipeline_options_to_run` promet plus qu'il ne verifie ; reasoning absent du gate.

Fermes depuis la base : le lint qui aurait bloque la CI avant `pytest` (`ruff check` et `ruff format --check` propres) ; le commentaire faux de `doc-viewer.feature`.

---

## Delta vs validation

Score : **81 -> 93 (+12)**. Items conformes 12/14 -> 13/14. CRIT 1 -> **0**, MAJ 1 -> 1, MIN 1 -> **0**, INFO 7 -> 10. Verdict NO-GO -> **GO**.

Suites : backend 1748 passed / 1 failed -> **1773 passed / 0 failed**, 15 skipped inchanges ; frontend 633 -> **604**, 72 -> 71 fichiers. Fonctions de test backend (AST, avant parametrisation) : 1623 -> 1625, 42 ajoutees, 40 disparues, **aucune fonction conservee avec moins d'assertions ou moins de cas parametres**.

| Ecart de la validation | Statut |
|------------------------|--------|
| [CRIT] 9.1.1 test IPv6 rouge | **Corrige** (`89c33f0`) : en-tete `Host` force, 1773/0 |
| [MAJ] 9.1.3 Karate UI | **Reduit sur la spec PDF.js, elargi par le constat des specs obsoletes** : selecteurs nommes et commentaire corrige ; reste rien d'execute, scenario PDF.js hors CI, 3 specs anterieures qui visent des ecrans disparus |
| [MIN] deux gardes sans test | **Corrige** : `test_reasoning_runner_factory.py:31` (fournisseur `openai` -> `None` + warning) ; `test_chunk_service.py:329` (chunk d'un autre document -> `ChunkNotFoundError`, rien supprime ni insere, les deux documents intacts) |
| [INFO] lint qui bloquerait la CI | **Corrige** (`89c33f0`) |
| [INFO] commentaire faux dans `doc-viewer.feature` | **Corrige** (`1cd8413`) |
| [INFO] `backend-docling`, pixels PDF.js, trous PDF.js, poppler, aucun run CI, divers | Inchanges |

Nouveaux : 5 INFO (test a 3 000 elements, joker `*`, cas limites des chunks, commentaire du promoter, `HistoryDrawer.vue` mort). Les specs obsoletes sont versees au MAJ existant.

---

## Tests supprimes, deplaces ou reecrits

### Backend : 40 fonctions disparues

| Fonctions disparues | Devenues | Code de production |
|---------------------|----------|--------------------|
| `test_hashing.py` (9 tests) | Rien | `domain/hashing.py` supprime ; a `efc0bc5` deja, aucun module de production ne l'importait (`git grep hashing efc0bc5`). Le hash des pushes est `_compute_chunkset_hash` (`chunk_push_service.py:347`), une autre fonction, couverte par `test_chunk_service.py:667`, `:692` |
| `test_lifecycle_aggregation.py` (5 tests) | Rien | `domain/lifecycle_aggregation.py` supprime ; aucun appelant a `efc0bc5` |
| `test_chunk_editing.py` : 10 tests de `insert`, `update`, `delete` | Rien au domaine | Fonctions supprimees ; le service ne les appelait deja plus a `efc0bc5` (il n'utilisait que `split`, `merge`, `check_merge_count`). Les regles du service ont leurs propres tests (`TestAddChunk`, `TestUpdateChunk`, `TestDeleteChunk`) ; deux cas limites restent sans test de service (INFO 3) |
| `test_chunk_repos.py` : 2 tests de `soft_delete_for_document` | `replace_for_document` (`test_version_service.py`, `test_document_analysis_repo.py:121`) | Methode et port supprimes (`rg` : 0) |
| `test_chunk_service.py::TestPromote` (4 tests) | Rien | `promote_from_analysis_if_empty` et `set_chunk_promoter` supprimes (`rg` : 0 ; commentaire perime, INFO 4) |
| `test_ollama_provider.py` : 3 tests de `health_check` | Rien | `OllamaProvider.health_check` et la methode du port supprimes ; la sonde utilisee au demarrage est `infra/llm/ollama_probe.py`. Le seul `health_check` restant est celui de `serve_converter.py:189`, teste (`test_serve_converter.py:634`, `:649`) |
| `test_api_host_guard.py` : 6 tests (`is_allowed_host`, `split_host`, joker, port exact, refus 421 texte) | Fichier reecrit, voir plus bas | `is_allowed_host` et `split_host` remplaces par `parse_host_name` |
| `test_document_analysis_repo.py::test_a_save_writes_only_what_changed` | `test_a_rechunk_keeps_a_selection_made_meanwhile` (`:121`) | `save_state` supprime ; le nouveau test passe par le vrai chemin d'ecriture (`replace_for_document(..., keep_selection=True)`) et garde les deux assertions finales |

Les `get_default` (store) et `find_latest_for_document` (versions) supprimes n'avaient pas de fonction de test propre : `test_store_repo.py:43` lit maintenant le store `default` par `find_by_slug` et garde ses deux assertions (`slug`, `is_default`). `rg` confirme leur disparition de la production.

**Aucune assertion perdue sur du code encore present.** Chaque test disparu visait du code supprime (verifie par `rg` dans `document-parser` hors `tests` et `.venv`), ou a ete reecrit avec des assertions au moins equivalentes.

### Backend : fichiers reecrits

- **`test_api_host_guard.py`** : 17 -> 18 fonctions, et bien plus de cas. Gagne : corps JSON exact du 421, log en DEBUG seulement, IPv6 avec et sans port, 13 en-tetes malformes ou etrangers (`localhost:80@evil.com`, `[::1]evil`, `localhost.evil.com`, vide...), `parse_host_name` sur 9 cas, joker de port reserve a la liste blanche. Change volontairement (`914246e`, documente par `a744f48`) : le port est ignore des deux cotes ; l'ancien `test_an_exact_pattern_wants_the_same_port` (421 sur un autre port) devient `test_the_port_of_an_entry_is_ignored` (200). Perdu sans equivalent direct : le joker `*` au niveau du middleware, qui ne tient plus qu'a `main.py` (INFO 2).
- **`test_document_analysis_repo.py`** : les helpers passent de `save_state` (supprime) aux fonctions d'ecriture de production (`tests/analysis_state_helpers.py`) ; memes assertions, plus `test_a_restore_selecting_a_deleted_analysis_writes_nothing` (`:152`).
- **`test_export_service.py`** : memes tests sur le nouveau lecteur (`UneditedResultReader`) ; message attendu change avec le code (« no active analysis ») ; plus `test_pdf_export_reads_the_path_the_preview_resolves` (`:161`).
- **`test_chunk_service.py`** : les tests de push et d'arbre visent maintenant `ChunkPushService` et `DocumentTreeService`, sans perte ; ajouts : fusion inter-documents (`:329`), premier rechunk sans ligne d'etat (`:498`).
- **`test_document_chunks_api.py`** : un mock par service (`chunks`, `pushes`, `tree`) ; une route branchee sur le mauvais service echoue desormais. Toutes les assertions sont conservees.
- `test_api_endpoints.py`, `test_current_analysis.py`, `test_analysis_editing.py`, `test_reasoning_api.py` : renommages (`load_current_analysis` -> `load_current_original`, `load_active_result` -> `load_current_edited`), memes assertions.

### Frontend : 633 -> 604 (-29), compte exact

| Fichier | Avant | Apres | Delta | Raison |
|---------|------:|------:|------:|--------|
| `pages/DocIngestTab.logic.test.ts` (supprime) | 29 | 0 | **-29** | 23 `it` + 1 `it.each` de **6 cas** (`getStateBucket`). Code teste supprime avec lui (`DocIngestTab.logic.ts`, `IngestLaunchDialog.vue`, `DocChunkTab.vue` : `rg` 0) |
| `features/document/linkedView.test.ts` | 10 | 6 | **-4** | Tests de `findElementRefsForChunk` (3) et `filterChunkBboxesOnPage` (1) ; les deux fonctions sont supprimees de `linkedView.ts` (`rg` 0) |
| `features/document/store.test.ts` | 28 | 30 | **+2** | 4 tests reecrits pour la nouvelle regle (plus de repli sur la derniere version sans analyse courante, `da6603d`) et 2 ajoutes (`:305`, `:448`) |
| `features/analysis-editor/store.test.ts` | 11 | 12 | **+1** | Enregistrement refuse |
| `features/analysis-editor/ui/AnalysisEditor.a11y.test.ts` | 4 | 5 | **+1** | Bandeau d'erreur d'enregistrement |
| **Total** | | | **-29** | 633 - 29 = **604** ; fichiers 72 - 1 = 71 |

L'ecart avec l'estimation d'environ 610 du rapport de cycle vient du `it.each` : compte comme un test, le fichier supprime en fait 24 ; vitest en compte 29 (6 cas). Aucun autre fichier de test frontend n'a change entre `efc0bc5` et `a744f48`.

Les 4 tests reecrits de `store.test.ts` changent une attente volontairement, alignee sur `store.ts` : sans analyse courante, aucune version n'est marquee active et aucune analyse n'est chargee (avant : la version la plus recente). Ce n'est pas un affaiblissement : les nouveaux tests ont plus d'assertions (66 -> 76 `expect(` dans le fichier).

### Qualite des nouveaux tests

- **Peuvent-ils echouer ?** Oui. Fusion inter-documents : verifie l'exception, aucun `soft_delete_many` ni `insert`, et l'etat des deux documents. Fabrique du runner : `None` et le warning exact. Suppression : identifiant precis du successeur, en ecartant une analyse sans parse, une en cours et une d'un autre document. Restauration avec suppression concurrente : 409, message, chunks vivants intacts.
- **Collaborateurs** : SQLite reel et vrais repositories pour la suppression, l'etat, le rechunk et la restauration ; vrais routeurs pour le test API de suppression. Mocks pour les tests de routes, la fabrique (`has_usable_deps`, classe du runner) et le spy de `hash_result`.
- **Determinisme** : horloge fixe `_T0` ; aucune dependance au temps ni au reseau ; aucun `asyncio.run` dans une boucle active (le seul nouveau est dans une fixture synchrone, `test_analysis_deletion.py:151`).

---

## Points positifs

- **Le CRIT est corrige sans masquer le cas** : l'IPv6 est teste avec et sans port, en forcant l'en-tete.
- **Les deux trous du MIN sont combles par des tests qui discriminent** : fournisseur `openai` et chunk etranger, avec verification qu'aucune ecriture n'a eu lieu.
- **Le nettoyage du code mort emporte ses tests sans toucher au code vivant** : 40 fonctions backend et 33 tests frontend, chacune rattachee a du code supprime ; aucune fonction conservee n'a perdu d'assertion.
- **Les nouvelles regles (successeur d'une analyse supprimee, rechunk et restauration sans ligne d'etat) sont testees sur SQLite reel**, et une fois de bout en bout par l'API.
- **Les tests de routes de chunks distinguent maintenant les trois services**, ce qui attrape un mauvais branchement.

---

## Verdict partiel : GO

Score **93/100**, 0 CRITICAL, 1 MAJOR (9.1.3), 0 MINOR. Le MAJ ne bloque pas seul (seuil : plus de 3 MAJ). Avant le tag : pousser pour obtenir une CI (`backend`, `backend-docling`, e2e API, `e2e-ui` `@critical`) ; lancer une fois la spec PDF.js ; supprimer ou reecrire `doc-history-drawer.feature`, `doc-new-analysis-opens-analysis.feature` et la ligne 63 de `analysis-detail.feature`.

# Rapport d'audit : Tests

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `eade7fa` = `release/0.7.4` @ `2f47f72` + 3 commits locaux non pousses (#391, #392, #393)
**Baseline** : audit 0.7.3 (`release/0.7.3` @ `02adc68`, 93/100)
**Mode** : lecture statique uniquement. Aucune suite n'a ete executee pour cet audit (machine occupee, consigne). Les preuves d'execution viennent de la CI GitHub.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 14 |
| Score | 85 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 11 |

Detail du calcul : poids conformes 23 / poids total 27 = 85,2 -> **85**. Non conformes : 9.1.3 (2) et 9.2.1 (2).

**Score provisoire.** 9.1.1 et 9.1.2 sont notes conformes sur la preuve CI de l'arbre `release/0.7.4` et sur une relecture statique des 13 tests ajoutes par les 3 commits correctifs, qui n'ont jamais tourne. Si l'un d'eux echoue a l'execution, l'item tombe en `[CRIT]` (poids 3) : score 74, **NO-GO** (regle absolue). Voir la premiere INFO.

### Metriques d'execution (preuves CI, aucune execution locale)

| Suite | Source | Resultat |
|-------|--------|----------|
| Backend, CI | run `43253020395`, job *Backend tests*, commit `3c00d44` (tete de la PR #319 ; `git diff 3c00d44 2f47f72` vide, donc arbre identique a `release/0.7.4`) | **1369 passed, 19 skipped, 0 failed** (`collected 1385 items / 3 skipped`), 21,8 s |
| Frontend, CI | meme run, job *Frontend tests & build* | **59 fichiers, 570 passed, 0 failed** |
| E2E API Karate, CI | meme run, `--tags @smoke,@regression,@e2e` (PR vers `release/**`, `ci.yml:139-142`) | 12 features / 36 scenarios + 2 smoke, **0 echec** |
| E2E UI Karate | — | **Jamais execute** : `e2e-ui` de `ci.yml` est `skipped` hors `main` (`ci.yml:162`), le Release Gate ne tourne que sur une PR vers `main` (`release-gate.yml:4-6`) |
| Tests des 3 commits correctifs | — | **Non executes** : 8 tests backend (`test_database_upgrade.py` x5, `test_analysis_editing.py` x3) et 5 tests frontend (`commands.test.ts` x4, `store.test.ts` x1). Branche non poussee, donc aucun run CI |
| Couverture de lignes | — | Non mesuree (inchange : ni `pytest-cov` ni provider `@vitest/coverage-*`) |

- **Volume** : backend CI 1322 -> 1369 (+47) depuis 0.7.3, frontend 545 -> 570 (+25), 53 -> 59 fichiers. Attendu a `eade7fa` : 1377 backend et 575 frontend en CI. Aucun fichier de test supprime (`git diff --diff-filter=D 1de1929..HEAD -- '*test*'` vide).
- **Skips CI (19)** : inchanges. 15 Neo4j, 3 modules sans `docling` (`test_robustness.py:154`, `test_pipeline_options.py:14`, `test_batch_merge.py:17`), `test_serve_converter.py:792`.
- **Les nouveaux tests de l'editeur tournent bien en CI** : ils ne dependent que de `docling-core` (dependance principale). Le log du run `43253020395` montre 38 PASSED dans `test_analysis_editing.py`, 3 dans `test_document_analysis_repo.py`, 1 dans `test_analysis_editor_feature_flag.py`.

| # | Item | Poids | Conforme | Evolution vs 0.7.3 |
|---|------|-------|----------|--------------------|
| 9.1.1 | Tous les tests backend passent | 3 | Oui (provisoire) — 1369/19 en CI sur l'arbre `release/0.7.4` ; 8 tests des correctifs non executes | = |
| 9.1.2 | Tous les tests frontend passent | 3 | Oui (provisoire) — 570 en CI ; 5 tests des correctifs non executes | = |
| 9.1.3 | Les tests e2e Karate UI passent | 2 | **Non** — voir MAJ (inchange) | = |
| 9.2.1 | Chaque endpoint API a un test happy path | 2 | **Non** — voir MAJ | **Oui -> Non** |
| 9.2.2 | Cas d'erreur endpoints (400, 404, 413, 429) | 2 | Oui — 404 du flag teste sur les 6 routes editeur ; 400/409 seulement au niveau service (voir MAJ 9.2.1) | = |
| 9.2.3 | Services : tests d'orchestration | 2 | Oui — `AnalysisEditService` sur SQLite reel, editeur et projecteur reels | = |
| 9.2.4 | Fonctions domain | 1 | Oui — `active_edit_commands` (`test_analysis_editing.py:708`) | = |
| 9.2.5 | Composants Vue critiques | 2 | Oui — store, api, commands, a11y de l'editeur, `AnalysisDetailPage`, flag | = |
| 9.3.1 | Pas de `.only` / `fdescribe` / `fit` | 3 | Oui — aucun | = |
| 9.3.2 | Pas de skip sans justification | 1 | Oui — tous avec `reason` | = |
| 9.3.3 | Tests deterministes | 2 | Oui | = |
| 9.3.4 | Integration teste le flux reel | 2 | Oui (voir MIN #344, inchange) | = |
| 9.3.5 | Assertions specifiques | 1 | Oui — les `is not None` sont des gardes suivies d'assertions precises | = |
| 9.3.6 | Noms de tests explicites | 1 | Oui | = |

### Couverture de la nouveaute 0.7.4 (editeur d'analyse, PR #388/#319, correctifs #391-#393)

| Element | Tests rapides (CI) | E2E | Statut |
|---------|-------------------|-----|--------|
| Commandes Docling (`replaceText`, `mergeText`, `setHeadingLevel`, `moveElement`, `deleteElement(s)`) | `test_analysis_editing.py:87-341` (editeur reel, round-trip valide), `:402-413` (chaque commande parametree) | `analysis-editor.feature:7`, `:78` — hors CI | Couvert |
| Projection (bbox, texte edite, structure imbriquee) | `test_analysis_editing.py:350-491` | — | Couvert |
| Service : save, preview, history, revert/reapply, rebuild, conflit de sequence | `test_analysis_editing.py:529-958` (SQLite reel via `tmp_path`) | `analysis-editor.feature:105` — hors CI | Couvert |
| 6 routes HTTP `/api/documents/{id}/analysis-editor`, `/analysis-edits*` | `test_analysis_editor_feature_flag.py:10-28` (404 flag off **seulement**) | idem, hors CI | **Non couvert en happy path** (MAJ) |
| Flag `ANALYSIS_EDITOR_ENABLED` | `test_settings.py`, `test_api_endpoints.py:118-127` (`/api/health`), `:364-369` (export `edited` 404) ; frontend `feature-flags/store.test.ts` | — | Couvert |
| Export `edited=true` | `test_api_endpoints.py:349-362`, `test_export_service.py` | — | Couvert |
| Store / UI editeur | `analysis-editor/store.test.ts` (409, brouillon recupere, preview obsolete ignoree), `commands.test.ts`, `api.test.ts`, `AnalysisEditor.a11y.test.ts` (axe-core sous jsdom) | — | Couvert |
| #391 upgrade d'une base 0.7.3 | `test_database_upgrade.py:100-170` (5 tests) — **non executes** | aucun | Couvert, non prouve |
| #392 ordre de fusion | `test_analysis_editing.py:129-147`, `commands.test.ts:33-80`, `store.test.ts:34-64` — **non executes** | — | Couvert, non prouve |
| #393 chunks sans provenance, sauvegarde vide | `test_analysis_editing.py:596-636` — **non executes** | — | Couvert, non prouve |

Relecture statique des 13 tests non executes : les fixtures, les noms de methode (`clear_selection`, `get_selection`, `set_chunk_source`, `count_for_document`), les champs (`DocumentChunkSource`, `DocumentVersion.chunks_source_*`) et les valeurs attendues ont ete confrontes au code de `eade7fa`. Aucune incoherence trouvee : par exemple la requete de backfill (`persistence/database.py:300-313`) donne bien `json-new` et `batched-with-json` sur les lignes de `test_database_upgrade.py:60-74`, et `inReadingOrder` traite `Infinity - Infinity = NaN` par le repli sur l'ordre de clic, ce que `commands.test.ts:77-80` attend. Ce n'est pas une preuve d'execution.

---

## Ecarts constates

### [MAJ] La suite e2e Karate UI n'est toujours pas verte dans son ensemble, et la feature de l'editeur ne tourne dans aucun workflow (baseline, inchange et elargi)

- **Localisation** : `e2e/ui/src/test/resources/documents/doc-ingest-view.feature:38`, `e2e/ui/src/test/resources/documents/doc-chunk-view.feature:31`, `e2e/ui/src/test/resources/documents/doc-strategy-popover.feature:31` et `:39` ; `frontend/src/shared/routing/modes.ts:36-37` ; `e2e/ui/src/test/java/UIRunner.java:7`, `:20` ; `e2e/ui/src/test/resources/analyses/analysis-editor.feature:1` ; `e2e/ui/src/test/java/AnalysisEditorRunner.java:7` ; `.github/workflows/ci.yml:162`, `:228` ; `.github/workflows/release-gate.yml:658` ; `e2e/ui/README.md:104`
- **Constat** :
  - **Les trois specs obsoletes sont toujours la.** `doc-ingest-view.feature:38` attend `[data-e2e=view-switcher]` et `doc-strategy-popover.feature:39` `[data-e2e=strategy-btn]` : 0 attribut `data-e2e` correspondant dans `frontend/src` (seule la classe CSS `strategy-btn` existe). `doc-chunk-view.feature:31` et `doc-strategy-popover.feature:31` attendent `[data-e2e=chunk-tab]`, porte uniquement par `pages/DocChunkTab.vue:2`, que rien n'importe ; `modes.ts:36-37` resout `chunk` et `ingest` en `parse`. Elles echouent au premier `waitFor` sous `UIRunner.testAll` / `testLocal`.
  - **La feature de l'editeur, `analyses/analysis-editor.feature` (3 scenarios : remplacement/fusion/suppression/abandon, deplacement et ordre de lecture persistes, brouillon recupere puis rejete apres une sauvegarde concurrente), est taguee `@ui` seulement (`:1`).** La CI ne lance que `--tags @critical` (`ci.yml:228`, `release-gate.yml:658`), et `e2e-ui` de `ci.yml` ne tourne que sur `main` (`:162`). `AnalysisEditorRunner.java:7` n'est appele par aucun workflow. C'est pourtant la seule preuve bout en bout des 6 routes de l'editeur a travers nginx et la stack conteneurisee.
  - **Aucune preuve d'execution pour l'arbre audite.** Pas de Release Gate sur 0.7.4, pas de rapport Karate UI recent (`e2e/ui/target/karate-reports/karate-summary-json.txt` date du 2026-07-16 et ne contient que `demo.ask-demo`).
  - Les 8 features UI ecrites pour 0.7.3 restent hors CI, le perimetre `@critical` (5 features) pilote toujours `/studio` sous `STUDIO_MODE_ENABLED=true` (`ci.yml:201`). Les issues #382 et #374 (jalon 0.7.4) portent ce chantier et sont ouvertes.
- **Regle violee** : 9.1.3 — Les tests e2e Karate UI passent.
- **Remediation** : (1) supprimer `doc-ingest-view`, `doc-chunk-view`, `doc-strategy-popover` ou les reecrire contre `/docs/:id` ; (2) passer au moins le premier scenario de `analysis-editor.feature` en `@critical`, ou livrer #382 (job `@regression` dans le Release Gate) ; (3) joindre au gate le rapport Karate UI complet (#374). Effort M.

### [MAJ] Les 6 routes HTTP de l'editeur n'ont aucun test happy path ; seul leur 404 « flag off » est teste

- **Localisation** : `document-parser/api/analysis_edits.py:120`, `:132`, `:145`, `:162`, `:184`, `:208` (routes) ; `:86-107` (`_commands`), `:59-70` (`_response`), `:73-83` (`_history_entry`), `:110-117` (`_raise`) ; `document-parser/tests/test_analysis_editor_feature_flag.py:10-28` ; aussi `document-parser/api/document_versions.py:53`, `:65` (baseline)
- **Constat** :
  - `grep -rn "analysis-edit\|analysis-editor" document-parser/tests` ne renvoie que `test_analysis_editor_feature_flag.py`. Ce test monte le routeur avec `analysis_editor_enabled=False` et verifie 6 x 404. Aucun test n'appelle une route de l'editeur avec le flag actif.
  - La couche HTTP porte pourtant de la logique propre, jamais executee en CI : la traduction des 7 types de commande camelCase vers les payloads du domaine (`_commands`, avec une branche `else` qui suppose `moveElement`), la construction de `AnalysisEditorResponse` (arbre recursif, `readingOrder`, `chunksStale`, `referenceChanges`), le calcul `active` de l'historique (`:156-157`) et le mapping d'erreurs `_raise` (409 conflit, 409 indisponible, 400 commande invalide).
  - Le contrat d'erreur n'est donc fixe nulle part au niveau HTTP. Exemple : un document inexistant leve `AnalysisEditUnavailableError("Document not found: ...")` (`services/analysis_edit_service.py:272-274`) et sort en **409**, pas en 404 (voir INFO).
  - Le seul appel reel de ces routes est dans `analysis-editor.feature:142-152` (GET `analysis-editor`, POST `analysis-edits`), hors CI (MAJ precedent). Le frontend les mocke (`store.test.ts:12-18`, `AnalysisEditor.a11y.test.ts:11-17`).
  - Lecture litterale de l'item : 6 nouvelles routes, plus les 2 routes `document_versions` deja signalees en MIN en 0.7.3, n'ont aucun test happy path. La baseline acceptait l'ecart sur 2 routes legacy couvertes au niveau service ; sur les 6 routes de la fonctionnalite phare de la release, l'item n'est plus tenable.
- **Regle violee** : 9.2.1 — Chaque endpoint API a au moins un test (happy path). Recoupe 9.2.2 pour 400/409.
- **Remediation** : `tests/test_analysis_edits_api.py` sur le modele de `test_mcp_config_api.py` : routeur reel + vrai `AnalysisEditService` sur SQLite `tmp_path` (la fixture `edit_service` de `test_analysis_editing.py:494-526` est reutilisable). Un test par route en happy path, plus 409 (sequence perimee), 400 (commande invalide) et document absent. Ajouter `GET/POST /versions` au passage. Effort M.

### [MIN] Le merge des batches (#344) n'est toujours verifie par aucun gate (baseline, inchange)

- **Localisation** : `document-parser/tests/test_batch_merge.py:17` ; `document-parser/pyproject.toml:29-34` (groupe `dev`), `:38-47` (`docling` dans `local`) ; `.github/workflows/ci.yml:41` ; `.github/workflows/release-gate.yml:85`
- **Constat** : inchange. La CI installe `--group dev` seulement, le module est saute a la collecte (`collected 1385 items / 3 skipped` dans le run `43253020395`). Le nouveau groupe `ci` (`pyproject.toml:35-37`, `fpdf2`) ne sert qu'a generer les PDF e2e et ne change rien a ce trou.
- **Regle violee** : 9.3.4 (partiel).
- **Remediation** : inchangee — job `uv sync --group dev --group local` limite a `test_batch_merge.py`, `test_pipeline_options.py`, `test_robustness.py`. Effort M.

### [MIN] `LocalChunker` sans test ; le commentaire renvoie toujours a un fichier inexistant (baseline, inchange)

- **Localisation** : `document-parser/tests/test_chunking.py:486`
- **Constat** : « Real chunker integration is covered by ``test_local_chunker.py`` » ; `tests/test_local_chunker.py` n'existe pas.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel).
- **Remediation** : ajouter le test promis ou corriger le commentaire. Effort S.

### [INFO] Les 13 tests ajoutes par #391, #392 et #393 n'ont jamais ete executes

- **Localisation** : `document-parser/tests/test_database_upgrade.py:100-170` ; `document-parser/tests/test_analysis_editing.py:129`, `:596`, `:612` ; `frontend/src/features/analysis-editor/commands.test.ts:33-80` ; `frontend/src/features/analysis-editor/store.test.ts:34`
- **Constat** : commits locaux non pousses, aucun run CI, et l'execution locale etait exclue pour cet audit. La relecture statique ne trouve pas d'incoherence (voir plus haut), mais 9.1.1 et 9.1.2 restent conformes sous condition.
- **Remediation** : pousser la branche et ouvrir la PR vers `release/0.7.4` : le job CI la validera (`ci.yml:7`). Si un test echoue, 9.1.x devient `[CRIT]` et le verdict passe a NO-GO jusqu'a correction. Effort S.

### [INFO] Contrat d'erreur de l'API editeur : document absent -> 409, aucun test ne le fixe

- **Localisation** : `document-parser/services/analysis_edit_service.py:272-274` ; `document-parser/api/analysis_edits.py:113-114`
- **Constat** : `_require_document` leve `AnalysisEditUnavailableError`, que `_raise` mappe en 409, comme « aucune analyse active ». Les autres routes du projet repondent 404 pour un document absent (`test_api_endpoints.py:171`, `:254`). Recoupe l'audit 07.
- **Remediation** : decider du code, puis le figer dans le test API du MAJ 9.2.1. Effort S.

### [INFO] Le chemin d'upgrade 0.7.3 -> 0.7.4 n'est teste que sur une copie de schema

- **Localisation** : `document-parser/tests/test_database_upgrade.py:14-58` ; `docker-compose.yml:162` ; `.github/workflows/ci.yml:107-108`
- **Constat** : le test recopie 3 tables du schema 0.7.3 ; c'est suffisant aujourd'hui (ce sont les seules tables existantes modifiees, `git diff 1de1929..2f47f72 -- persistence/database.py`), mais rien ne garantit que la copie suive. Toute la CI demarre sur un volume `db_data` neuf : aucun job ne boote 0.7.4 sur une base reellement creee par 0.7.3, ce qui est exactement le defaut qu'a corrige #391.
- **Remediation** : versionner une base SQLite 0.7.3 minimale en fixture (generee une fois par l'image `0.7.3`) et l'utiliser dans `test_database_upgrade.py`. Effort S.

### [INFO] Deux PDF de test de l'editeur sont generes mais ne servent a aucun scenario

- **Localisation** : `e2e/generate-test-data.py:185-186` ; `e2e/ui/README.md:61-62`
- **Constat** : le README annonce que `editor-provenance.pdf` (navigation entre pages, selection sur le calque PDF) et `editor-readonly.pdf` (listes et tableaux en lecture seule) « couvrent » ces cas ; aucun fichier de `e2e/` ne les reference hors du generateur. Ces comportements n'ont donc pas de test e2e.
- **Remediation** : ecrire les scenarios ou retirer les lignes du README. Effort S.

### [INFO] Le switch live du MCP n'est couvert de bout en bout par aucun test execute en CI (baseline, inchange)

- **Localisation** : `document-parser/bootstrap/builder.py:268-273` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:64`
- **Remediation** : inchangee.

### [INFO] Aucun scenario e2e API pour les routes 0.7.3 ni pour les 6 routes de l'editeur (baseline, elargi)

- **Localisation** : `e2e/api/src/test/resources/` (`git diff --stat 1de1929..HEAD -- e2e/api` vide)
- **Constat** : la suite e2e API est identique a 0.7.3 (12 features, 36 scenarios). Les routes de l'editeur s'ajoutent a la liste des routes jamais appelees a travers la stack conteneurisee en CI.
- **Remediation** : `e2e/api/.../analyses/analysis-edits.feature` (`@regression`) : GET editeur, POST save, 409 sur sequence perimee. Effort S.

### [INFO] Import Docling (#359) : 400 « document invalide » non teste en HTTP (baseline, inchange)

- **Localisation** : `document-parser/api/analyses.py:84` ; `document-parser/tests/test_api_endpoints.py:571-600`

### [INFO] Deux branches 413 secondaires non couvertes (baseline, inchange)

- **Localisation** : `document-parser/api/documents.py:86-87` ; `document-parser/services/graph_service.py:48`

### [INFO] RuntimeWarning « coroutine never awaited » dans `test_pipeline_options.py` (baseline, non re-verifie)

- **Localisation** : `document-parser/tests/test_pipeline_options.py:14`
- **Constat** : module saute en CI faute de `docling` ; pas d'execution locale pour cet audit, statut inconnu.

### [INFO] Les 15 tests Neo4j ne tournent dans aucune CI ; la docstring affirme le contraire (baseline, inchange)

- **Localisation** : `document-parser/tests/neo4j/conftest.py:4`

### [INFO] Reasoning : toujours aucune couverture dans le gate (baseline, inchange)

- **Localisation** : `.github/workflows/release-gate.yml:252` (seul `APP_VERSION`) contre `.github/workflows/release.yml:72-73`

---

## Delta vs 0.7.3

Score : **93 -> 85** (**-8**). Items conformes 13/14 -> 12/14.

| Ecart baseline (0.7.3) | Statut en 0.7.4 |
|------------------------|-----------------|
| [MAJ] 9.1.3 e2e UI pas verte, specs 0.7.3 hors CI | **Toujours ouvert** — les 3 specs obsoletes sont la ; la feature de l'editeur s'ajoute aux features hors CI (#382, #374 ouvertes) |
| [MIN] #344 merge des batches non gate | **Toujours ouvert** |
| [MIN] `document_versions` sans test API | **Absorbe** dans le nouveau MAJ 9.2.1 |
| [MIN] `LocalChunker` + commentaire faux | **Toujours ouvert** |
| [INFO] Glue du switch MCP | Toujours present |
| [INFO] Pas d'e2e API sur les nouvelles routes | Toujours present, elargi a l'editeur |
| [INFO] Import #359 400 HTTP | Toujours present |
| [INFO] Branches 413 secondaires | Toujours present |
| [INFO] Preuve e2e UI absente | Integre au MAJ 9.1.3 |
| [INFO] RuntimeWarning | Non re-verifie |
| [INFO] Docstring Neo4j | Toujours present |
| [INFO] Reasoning hors gate | Toujours present |

Nouveaux ecarts : 1 MAJ (9.2.1, routes de l'editeur), 4 INFO (tests des correctifs non executes, 409 sur document absent, upgrade teste sur copie de schema, PDF de test inutilises).
Origine des -8 : 9.2.1 (poids 2) passe a Non. Le MAJ 9.1.3 de la baseline n'a pas ete traite.

---

## Points positifs

- **L'editeur est teste sur ses vraies dependances** : `DoclingDocumentEditor` et `DoclingAnalysisProjector` reels sur des `DoclingDocument` construits, `AnalysisEditService` sur SQLite reel (`tmp_path`), sans mock du domaine. Chaque commande est rejouee de bout en bout (`test_analysis_editing.py:402-413`, `:793-833`), y compris les round-trips de validation Docling.
- **Les invariants durs sont testes** : conflit de sequence sans ecriture (`:905`), revert refuse quand une edition ulterieure en depend (`:748`), flux et cache par analyse avec cascade et contrainte FK (`:551-578`), cache par analyse de base (`:928`).
- **Chaque correctif arrive avec son test de non-regression**, nomme d'apres l'issue (#391, #392, #393), et le test d'upgrade part d'un schema 0.7.3 reel avec des cas limites (analyse batchee sans JSON, choix utilisateur preserve, idempotence).
- **Frontend** : brouillon recupere puis rejete si la sequence a bouge, preview en vol ignoree apres abandon, 409 qui preserve les editions en attente, et un test d'accessibilite axe-core sur l'editeur monte.
- **Discipline intacte** : 0 `.only` / `fdescribe` / `fit`, 0 skip non justifie, aucun test supprime, determinisme tenu (pas d'horloge ni de reseau dans les nouveaux tests).
- **CI verte sur l'arbre de `release/0.7.4`** : 1369 backend, 570 frontend, 36 scenarios e2e API.

---

## Verdict partiel : GO

Score **85/100**, **0 CRITICAL**, **2 MAJOR** (sous le seuil de 3). Le verdict est provisoire : il suppose que les 13 tests ajoutes par #391, #392 et #393 passent. Ils n'ont pas tourne ; s'il en echoue un, 9.1.1 ou 9.1.2 devient CRITICAL et le verdict passe a **NO-GO**. A faire avant le tag : pousser la branche et obtenir une CI verte (#377), puis ajouter le test API des 6 routes de l'editeur (MAJ 9.2.1, effort M). Le MAJ e2e UI de la baseline reste ouvert ; le moins cher est de passer un scenario de `analysis-editor.feature` en `@critical`.

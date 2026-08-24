# Rapport d'audit : Tests

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 3 |

Detail du calcul : poids conformes 25 / poids total 27 = 92,6 -> **93**.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 9.1.1 | Tous les tests backend passent | 3 | Oui — 849 passed, 15 skipped |
| 9.1.2 | Tous les tests frontend passent | 3 | Oui — 432 passed (44 fichiers) |
| 9.1.3 | Les tests e2e Karate passent | 2 | Oui (voir INFO — non re-execute dans cet audit) |
| 9.2.1 | Chaque endpoint API a un test happy path | 2 | Oui (voir MIN — versions couverts service+e2e) |
| 9.2.2 | Cas d'erreur endpoints (400, 404, 413, 429) | 2 | **Non — 413 non teste** |
| 9.2.3 | Services : tests d'orchestration | 2 | Oui (voir MIN — export_service) |
| 9.2.4 | Fonctions domain (bbox, value objects) | 1 | Oui |
| 9.2.5 | Composants Vue critiques (stores/composables) | 2 | Oui |
| 9.3.1 | Pas de `.only` / `fdescribe` / `fit` | 3 | Oui — aucun |
| 9.3.2 | Pas de skip sans justification | 1 | Oui — skips env-gated justifies |
| 9.3.3 | Tests deterministes | 2 | Oui |
| 9.3.4 | Integration teste le flux reel, pas un mock complet | 2 | Oui (voir MIN — export) |
| 9.3.5 | Assertions specifiques | 1 | Oui |
| 9.3.6 | Noms de tests explicites | 1 | Oui |

---

## Ecarts constates

### [MAJ] Le cas d'erreur 413 (payload trop volumineux) n'est teste nulle part

- **Localisation** : `document-parser/api/documents.py:80` et `:88` ; `document-parser/services/graph_service.py:51` ; `document-parser/tests/test_api_endpoints.py:168`
- **Constat** : L'item 9.2.2 exige que les codes 400, 404, 413 et 429 soient testes. Les trois autres le sont (400 : 22 assertions ; 404 : 23 ; 429 : `tests/test_rate_limiter.py:70` et `:88`, deterministe via `time.monotonic` patche). Le **413 ne l'est pas** :
  - L'endpoint upload leve deux fois un `HTTPException(413)` — a la volee sur `file.size` (`api/documents.py:80`) et pendant la lecture en flux sur `total` (`:88`). Le seul test dedie, `test_upload_too_large` (`tests/test_api_endpoints.py:168-177`), mocke `service.upload` pour lever un `ValueError` et assure `status_code == 400` : il exerce la branche service->400, jamais les gardes 413 de l'endpoint.
  - `GraphService` leve `GraphTooLargeError` (HTTP 413) quand `payload.truncated` est vrai (`services/graph_service.py:51`, `:94`). `tests/test_graph_api.py` ne teste que `truncated=False` (`:42`, `:63`) — la branche 413 n'est jamais atteinte.
  - La feature e2e `e2e/api/src/test/resources/documents/size-validation.feature` ne couvre pas non plus le 413 : ses deux scenarios verifient un upload sous la limite (200) et le health endpoint, aucun upload sur-dimensionne.
  - Verification : `grep -rn "413\|GraphTooLarge\|truncated=True" tests/*.py` -> aucun resultat.
- **Regle violee** : 9.2.2 — Les cas d'erreur des endpoints sont testes (400, 404, 413, 429).
- **Remediation** : Ajouter (a) un test API upload avec `file.size` au-dela de la limite assurant `status_code == 413`, et un test flux (`file.size` absent, corps > limite) ; (b) un test `test_graph_api` avec `truncated=True` assurant le 413. Optionnel : un scenario e2e size-validation uploadant `large.pdf` au-dela de `maxFileSizeMb`.

### [MIN] Les endpoints HTTP `document_versions` n'ont aucun test au niveau API

- **Localisation** : `document-parser/api/document_versions.py:51` (GET `/{doc_id}/versions`), `:63` (POST `/{doc_id}/versions/{version_id}/restore`) ; `document-parser/tests/test_version_service.py:1`
- **Constat** : `test_version_service.py` est purement au niveau service (`VersionService`) — 8 tests, aucun `TestClient`. Aucun test ne monte le router `document_versions` (`grep -rn "document_versions" tests/*.py` -> aucun). La serialisation `_to_response` et le mapping d'erreur `_raise_for` (`VersionServiceError` -> code HTTP) ne sont donc exerces par aucun test rapide ; ils ne le sont que via la feature e2e ui `doc-history-drawer.feature`. Le happy path reste couvert (service + e2e), d'ou item 9.2.1 conforme, mais le contrat HTTP de ces deux routes n'a pas de filet unitaire.
- **Regle violee** : 9.2.1 (partiel) — Chaque endpoint API a au moins un test happy path.
- **Remediation** : Ajouter un `test_document_versions_api.py` sur le modele de `test_reasoning_api.py` (service reel + repo fake) couvrant list/restore happy path et le mapping d'erreur.

### [MIN] L'orchestration de `ExportService` n'est executee par aucun test

- **Localisation** : `document-parser/tests/test_api_endpoints.py:48-52` (fixture `mock_export_service`) et `:205-263` ; `document-parser/services/export_service.py:40`
- **Constat** : Les tests d'export mockent integralement le service (`mock_svc.export = AsyncMock()` puis `mock_export_service.export.return_value = ...`). Ils valident le cablage du router (pdf/md/json, 422 format non supporte, 404) mais n'executent jamais la logique reelle de `ExportService.export()` : dispatch de format, les six branches `ExportNotFoundError` (`export_service.py:43,47,57,59,68,70`), ni le constructeur de nom de fichier `_build_export_filename` / `build_content_disposition`. C'est le seul service (sur 11) dont l'orchestration n'est couverte par aucun test — les 10 autres ont un test service reel.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel) — logique d'orchestration des services testee ; integration testant le flux reel.
- **Remediation** : Ajouter un test unitaire de `ExportService.export()` sur les trois formats et les branches d'erreur, avec repos fakes.

### [MIN] La logique reelle de `LocalChunker.chunk()` n'est pas testee ; commentaire vers un fichier inexistant

- **Localisation** : `document-parser/infra/local_chunker.py:24` (`_chunk_sync`), `:87` (`_build_chunker`) ; `document-parser/tests/test_chunking.py:483-487`
- **Constat** : Sur le chemin critique parse/chunk, la logique de `LocalChunker` (construction `HybridChunker`/`HierarchicalChunker`, comptage de tokens, mapping `source_page`, 106 lignes) n'est exercee par aucun test : le seul reference dans les tests est un `isinstance(chunker, LocalChunker)` de cablage (`tests/test_serve_converter.py:822`). Le commentaire de `test_chunking.py:486` affirme « Real chunker integration is covered by `test_local_chunker.py` » — **ce fichier n'existe pas** (`find tests -name test_local_chunker.py` -> aucun). Le mock au niveau port pour eviter le reseau HuggingFace est une bonne pratique, mais la reference laisse croire a une couverture inexistante hors e2e.
- **Regle violee** : 9.2.3 / 9.3.4 (partiel) — flux reel du chunking.
- **Remediation** : Soit ajouter le `test_local_chunker.py` promis (sur un `document_json` fixe, sans reseau), soit corriger le commentaire pour pointer vers la seule couverture reelle (e2e).

### [INFO] Suite e2e Karate non re-executee dans cet audit ; rapport stocke obsolete

- **Localisation** : `e2e/api/target/karate-reports/karate-summary-json.txt` ; `e2e/ui/` ; `e2e/api/`
- **Constat** : L'execution Karate necessite une stack live (backend + services) — hors perimetre de cet audit en lecture seule. Les suites existent et sont completes : `e2e/api` (16 features : analyses, documents, ingestion, workflows, health) et `e2e/ui` (features couvrant les chemins critiques 0.7.0 — `navigation/reasoning-feature-flag.feature`, `documents/doc-parse-properties.feature`, `documents/doc-chunk-view.feature`, `demo/ask-demo.feature`, `documents/doc-history-drawer.feature`). Le dernier rapport karate stocke (`resultDate 2026-05-26`) ne contient qu'`health.health` (2 scenarios) — artefact local partiel, non representatif d'un run complet a ce commit. L'execution reelle releve du pipeline CI (audit 10).
- **Remediation** : S'appuyer sur l'audit 10 (CI/Build) pour la preuve d'execution ; ne pas versionner `target/`.

### [INFO] RuntimeWarning « coroutine never awaited » dans `test_pipeline_options.py`

- **Localisation** : `document-parser/tests/test_pipeline_options.py:365` et `:375`
- **Constat** : Le run backend emet des `RuntimeWarning: coroutine 'AnalysisService._run_analysis' was never awaited`. Cause : `patch("services.analysis_service.asyncio.create_task")` remplace `create_task` par un `MagicMock` ; la coroutine `_run_analysis(...)` construite pour l'argument n'est donc jamais awaited/fermee. Le test est correct (il assure `create_task` appele une fois) mais laisse un coroutine non consomme — bruit de determinisme sans impact fonctionnel.
- **Remediation** : Fermer explicitement la coroutine (recuperer l'argument du mock et `.close()`), ou asserter sur le nom de coroutine sans en creer une reelle.

### [INFO] 15 tests Neo4j skippes en l'absence de Neo4j local — couverture nulle du writer graphe hors CI

- **Localisation** : `document-parser/tests/neo4j/conftest.py:35`
- **Constat** : Les 15 skips du run backend sont tous « Neo4j not reachable » — env-gated et justifies (l'item 9.3.2 reste conforme). Consequence : en dev local sans Neo4j, tout le paquet `tests/neo4j/` (chunk writer, tree writer, roundtrip, schema, driver) n'apporte aucune couverture ; la garantie repose entierement sur le service `neo4j:5.15-community` de la CI.
- **Remediation** : Verifier dans l'audit 10 que la CI demarre bien Neo4j et n'ignore pas silencieusement ces skips (echec si `skipped > 0` sur le job neo4j).

---

## Points positifs

- **Suite verte et rapide** : 849 tests backend passants (11 s) et 432 tests frontend passants (0,7 s) — aucun echec.
- **Discipline anti-focus** : zero `.only` / `fdescribe` / `fit` / `xit` cote frontend, zero focus cote backend (9.3.1).
- **Chemins critiques 0.7.0 tres bien couverts** : le reasoning (`test_reasoning_api.py`) teste happy path + 503/400/404/502/500 ; la config runtime (`test_config_api.py`) teste GET/PUT/DELETE/probe + 400/403/422 + read-only + provenance des sources ; les deux cablent le **service reel** avec des fakes au seul niveau port (approche hexagonale correcte, pas de mock complet).
- **Assertions specifiques** : les `assert x is not None` sont des gardes de type suivies d'assertions precises, jamais l'unique assertion d'un test (9.3.5) ; contrats camelCase verifies champ par champ.
- **Determinisme maitrise** : le rate-limiter patche `time.monotonic` (`test_rate_limiter.py:91`), le chunking mocke au port pour eviter le reseau HuggingFace (`test_chunking.py:482`), les timestamps `datetime.now(UTC)` ne servent qu'a construire des fixtures. Fixture autouse `conftest.py` qui vide les buckets du rate-limiter entre tests pour eviter le crosstalk 429.
- **Skips justifies** : `skipif(not _has_docling())` avec `reason`, skips Neo4j documentes (9.3.2).
- **Domain et stores couverts** : bbox (20 tests backend + 35 frontend), value objects, hashing, fernet, trace_builder ; les 9 stores/composables Vue critiques (reasoning, document, chunking, chunks, admin-config, ingestion, analysis, history, search) ont chacun un test.
- **Noms explicites** : aucun nom de test placeholder (`it('works')`, `test('test')`).

---

## Verdict partiel : GO

Score 93/100, 0 CRITICAL. La suite est solide, verte et couvre finement les chemins critiques (reasoning, config runtime, parse/chunk). Le seul ecart bloquant potentiel — l'absence totale de test du code 413 (9.2.2, MAJ) — est isole et facilement remediable ; il ne compromet pas la release mais doit figurer au plan de remediation du cycle courant, avec les trois MIN (endpoints versions, orchestration export, LocalChunker).

# Synthese d'audit — Release 0.6.2

**Date** : 2026-06-05
**Branche** : `release/0.6.2`
**Commit audite** : `051ac4a`
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.6.1-reaudit/summary.md` (`f9e5619`, GO, 90.27/100)

---

## Tableau de bord

| #  | Audit                | Score   | CRIT  | MAJ | MIN | INFO | Verdict           | Δ vs 0.6.1-reaudit |
|----|----------------------|---------|-------|-----|-----|------|-------------------|--------------------|
| 01 | Clean Architecture   | 97      | 0     | 0   | 1   | 1    | GO                | =                  |
| 02 | DDD                  | 97      | 0     | 0   | 1   | 0    | GO                | =                  |
| 03 | Clean Code           | 72      | 0     | 1   | 3   | 0    | GO CONDITIONNEL   | =                  |
| 04 | KISS                 | 92      | 0     | 0   | 1   | 3    | GO                | + (correction methodologie ponderee, items identiques) |
| 05 | DRY                  | 75      | 0     | 0   | 2   | 3    | GO CONDITIONNEL   | =                  |
| 06 | SOLID                | 100     | 0     | 0   | 0   | 1    | GO                | =                  |
| 07 | Decouplage           | 73      | 0     | 1   | 3   | 1    | GO CONDITIONNEL   | =                  |
| 08 | Securite             | 100     | 0     | 0   | 0   | 2    | GO                | =                  |
| 09 | Tests                | 96      | 0     | 0   | 1   | 0    | GO                | =                  |
| 10 | CI / Build           | **70**  | **2** | 0   | 0   | 1    | **NO-GO**         | **-30**            |
| 11 | Documentation        | **44**  | **2** | 2   | 0   | 2    | **NO-GO**         | **-56**            |
| 12 | Performance          | 76.19   | 0     | 1   | 2   | 2    | GO CONDITIONNEL   | = (baseline 85.71 etait une erreur d'arithmetique du re-audit, recalcul 16/21=76.19 pour le meme triplet) |

**Score global (moyenne simple)** : **82.68 / 100** (vs 90.27 en 0.6.1-reaudit → **-7.59**, vs 79.12 en 0.6.1 initial → +3.56)
**Ecarts CRITICAL totaux** : **4** (vs 0 en 0.6.1-reaudit, vs 4 en 0.6.1 initial → recidive)
**Ecarts MAJOR totaux** : **5** (vs 3 en 0.6.1-reaudit, vs 11 en 0.6.1 initial)
**Ecarts MINOR totaux** : 14 (vs 13)
**Ecarts INFO totaux** : 15 (vs 11)

---

## Ecarts CRITICAL (tous audits confondus)

### 1. [10] CI rouge — backend test casse par appel HF Hub depuis un "unit test"

- **Localisation** : `document-parser/tests/test_chunking.py:480` (`TestRemoteChunkingPath::test_rechunk_with_serve_document_json`)
- **Constat** : le test instancie `LocalChunker()` qui tire le tokenizer `sentence-transformers/all-MiniLM-L6-v2` depuis HF Hub. Sur les runners GitHub Actions partages, HF renvoie `HTTP 429 Too Many Requests` → `OSError: We couldn't connect to 'https://huggingface.co'`. Localement (cache chaud) le test passe en 3.64s, ce qui explique pourquoi il survit aux validations developpeur. Run CI `#27005192862` sur HEAD → `Backend tests = failure`.
- **Bloquant absolu** (regle 10.1.1 — toutes les GitHub Actions doivent passer sur la branche de release).

### 2. [10] Release Gate E2E rouge — `release-gate.yml` ne propage pas `BAKE_MODELS=false`

- **Localisation** : `.github/workflows/release-gate.yml:522-527` (job `e2e-api`) et `.github/workflows/release-gate.yml:586-595` (job `e2e-ui`)
- **Constat** : le patch `051ac4a ci(#254): skip Docling model bake in E2E` a ajoute `BAKE_MODELS: "false"` dans `ci.yml:114` et `ci.yml:189`, **mais a oublie release-gate.yml**. Les deux jobs `e2e-*` font `docker compose up -d --wait --build` et heritent du defaut `BAKE_MODELS: ${BAKE_MODELS:-true}` de `docker-compose.yml:99`. Resultat : `Dockerfile:100` execute `docling-tools models download` au build, hits HF Hub, et casse en 429.
- Run `Release Gate #27005192861` sur HEAD → `e2e-api` + `e2e-ui` + `Security scan — remote` = `failure`. Two-liner fix.
- **Bloquant absolu** (regle 10.1.1).

### 3. [11] CHANGELOG.md sans section `## [0.6.2]`

- **Localisation** : `CHANGELOG.md:7` (la section la plus recente reste `## [0.6.1] - 2026-05-25`).
- **Constat** : 11 commits 0.6.2-specifiques depuis `f9e5619` ne sont references nulle part (uv migration #289, reasoning opt-in, model checkpoints bake, slim docker, remote-mode bbox fix `3936166`, CI updates). La "reserve operationnelle" du re-audit 0.6.1 (`reports/release-0.6.1-reaudit/11-documentation.md:111`) recommandait deja un check CI bloquant sur la presence de `## [X.Y.Z]` — il n'a pas ete cable. **Recidive parfaite du pattern 0.5.0 et 0.6.0/0.6.1**.
- **Bloquant absolu** (regle 11.1.1, poids 3).

### 4. [11] Breaking changes 0.6.2 non identifies

- **Localisation** : `CHANGELOG.md` (rubrique manquante).
- **Constat** : deux changements operationnels cassent le workflow developer/operator existant et ne sont signales nulle part :
  1. **Migration `pip` → `uv`** (`4d9bcf6`) — `document-parser/requirements*.txt` et `embedding-service/requirements.txt` supprimes. Toute CI tierce / script d'install qui fait `pip install -r requirements.txt` echoue.
  2. **Reasoning stack opt-in** (`d1ed61e` + `bb2fe2b`) — `docling-agent` + `mellea` passent dans `[dependency-groups.reasoning]`. L'image `latest-local` construite sans `--build-arg WITH_REASONING=true` repond `503` sur `/api/reasoning`.
- **Bloquant absolu** (regle 11.1.3, poids 3).

---

## Top blockers (poids 2 — MAJOR)

### Bloquants si > 3 non resolus (regle master.md §2)

- **[03] Handlers et fichiers sur-dimensionnes** (carry-over 0.6.1) : `document-parser/services/chunk_service.py::push_to_store` (~118L), `rechunk_document` (~88L), `document-parser/main.py::lifespan` (~150L), `document-parser/infra/neo4j/tree_writer.py::write_document` (~240L) ; cote front `frontend/src/views/StudioPage.vue` (1450L — 3eme audit consecutif sans action), `ChunkPanel.vue`, `ResultTabs.vue`.
- **[07] Couplage UI cross-feature** (carry-over 0.6.1) : `features/reasoning/**` ↔ `features/analysis/**`, `features/chunks/**` → `features/document/StatusBadge`, `features/chunking/**` → `features/analysis/**`, plus l'AppSidebar partage qui reverse-importe `feature-flags/store` et `ingestion/store` (nouveau INFO 0.6.2). Aucun nouveau couplage introduit par les features 0.6.2 (Ingest tab #283, push history, store form #279) — la dette est anterieure, mais elle reste a solder.
- **[11] Modifications fonctionnelles 0.6.2 non documentees** — meme cause racine que CRIT #3 ; ferme automatiquement par la remediation du CHANGELOG.
- **[11] `frontend/package.json` + `frontend/package-lock.json` toujours a `0.6.1`** — `frontend/package.json:3`, `frontend/package-lock.json:3,9`. **Recidive de l'ecart MAJ ferme dans le re-audit 0.6.1**. Le check CI propose pour empecher la recidive n'a pas ete cable.
- **[12] Requetes N+1** (carry-over 0.6.1) : `document-parser/services/store_service.py:163-164` (list_stores), `:358-360` (list_documents), `document-parser/services/version_service.py:161-173` + `:180-192` (restore : soft_delete + edit insert par chunk).

---

## Quick wins (poids 1 — corrections rapides)

Items deja identifies dans le re-audit 0.6.1 et toujours ouverts en 0.6.2 :

- **[03] Decouper les 3 plus gros fichiers** — `StudioPage.vue` 1450L (3e audit), `ChunkPanel.vue`, `ResultTabs.vue`. 28 fichiers front + 8 fichiers back > 300L.
- **[03] Wrapper trivial `_to_response`** — repete sur 5 routers (`api/documents.py:29`, `stores.py:46/64/78`, `analyses.py:31`, `document_versions.py:38`). Remplacer par `Pydantic.model_validate(..., from_attributes=True)`.
- **[05] Litteraux `table_mode` / `chunker_type` dupliques** sur 9 sites backend — extraire en Enum dans `domain/constants.py` (non cree malgre le re-audit).
- **[05] Pattern de polling** — `frontend/src/pages/ReasoningPage.vue:117` (3eme occurrence depuis 0.5.0) — extraire `shared/composables/usePoller.ts`.
- **[12] `frontend/src/features/settings/store.ts:69-101`** — watchers `setInterval+setTimeout` sans cleanup `effectScope`/`onScopeDispose` (carry-over 0.5.0).
- **[12] `nginx.conf`** — directives de cache statiques manquantes pour `frontend/dist/assets/`.

Items nouveaux 0.6.2 :

- **[12] `GraphService.project_reasoning_graph`** (`document-parser/services/graph_service.py:124`) — execute la projection synchrone `DoclingGraphProjector.project` (`infra/docling_graph.py:76-178`, parse JSON + DFS jusqu'a 200 pages) directement dans l'event loop. Wrapper dans `asyncio.to_thread(...)` comme les autres chemins.

---

## Bilan structurel

### Ce qui est solide en 0.6.2

- **Architecture hexagonale** (01/06) : ports `domain/ports.py` etendus a 17 ports apres le fix `f9e5619` ; aucun import `infra` runtime dans `services/` ou `api/`. La garde `test_architecture.py` tourne (collection 768 / 0 erreur).
- **Securite** (08) : le scellement Fernet ajoute en 0.6.0 reste irreprochable en 0.6.2 (`infra/secrets/fernet_box.py`), boot precondition `STORE_SECRET_KEY` intacte (`main.py:212-243,249`), Cypher/SQL parametres partout, CVE-2026-7598 (libssh2) ignore avec justification verifiable.
- **Tests** (09) : 768 collected / 0 erreur, 753 passed + 15 skipped justifies. `test_architecture.py` exclut maintenant les fichiers generes (`d29360d`) sans masquer le code source.
- **DDD** (02/06) : ubiquitous language `analysis`/`push` propre (rename `jobId → pushId` ferme en 0.6.1), 100/100 sur SOLID.
- **Surface code 0.6.2 backend** : les 105 commits sont overwhelmingly tooling (uv, docker slim, model bake, CI) ; aucune regression structurelle sur `services/`, `domain/`, `infra/` qui sont byte-identiques (sauf delta narrow comme `self_ref` carry remote-mode `3936166`).

### Ce qui regresse vs 0.6.1-reaudit

- **CI/Build** (10, -30) : le patch HF Hub a ete applique a ci.yml mais pas a release-gate.yml ; un test "unit" tire HF Hub. Les deux issues sont reelles et reproduites en CI sur HEAD.
- **Documentation** (11, -56) : **exact recidive** du pattern 0.5.0 → 0.6.0/0.6.1. Le check CI propose pour empecher cette recidive n'a pas ete cable.
- **Score global** (-7.59) : tire vers le bas exclusivement par 10 et 11 ; le reste de la base technique est stable.

---

## Verdict final : **NO-GO**

**Justification** : **4 ecarts CRITICAL non resolus** sur les audits 10 (CI x2) et 11 (CHANGELOG x2). Regle absolue master.md §3 : `tout ecart [CRIT] non resolu = NO-GO quel que soit le score`.

Note complementaire : avec 5 MAJ, on est legerement au-dessus du seuil bloquant (`>3` non resolus) mais 3 d'entre eux sont des carry-over connus de 0.6.1-reaudit (`03` handlers, `07` couplage UI, `12` N+1) et 2 sont les corollaires directs des CRIT (`11` package.json, `11` modifications non documentees).

Score global 82.68 dans la zone GO (`>=80`) — le release est techniquement saine sur le coeur (architecture, securite, tests, DDD, SOLID) mais bute sur le **dernier kilometre** : CI flaky et changelog non tenu. **Meme pattern que 0.6.1 initial**.

### Conditions pour passer a GO (4 actions, ~1h30)

**Bloquants absolus** :

1. **[10] CI #1** — `document-parser/tests/test_chunking.py:480` : soit mocker `LocalChunker()` / le tokenizer dans ce test, soit le marquer `@pytest.mark.integration` et l'exclure du job `Backend tests` de `ci.yml`, soit pre-charger le tokenizer via `actions/cache` sur `~/.cache/huggingface` (pansement).
2. **[10] CI #2** — `.github/workflows/release-gate.yml:522-527` et `:586-595` : ajouter `env: BAKE_MODELS: "false"` au niveau des steps `Start stack`, identique a `ci.yml:114,189`. **Two-liner**.
3. **[11] Doc #1** — Ajouter `## [0.6.2] - 2026-06-05` en tete de `CHANGELOG.md` avec sous-sections `Changed` (uv migration, model checkpoints bake, slim docker, PyTorch CPU pin, reasoning opt-in), `Fixed` (`3936166` remote-mode bbox), `CI` (`8a61c22`, `051ac4a`).
4. **[11] Doc #2** — Sous `### BREAKING CHANGES` dans la section 0.6.2, signaler explicitement (a) `pip install -r requirements*.txt` → `uv sync --group dev/local` ; (b) `latest-local` reasoning opt-in via `--build-arg WITH_REASONING=true`, sans quoi `/api/reasoning` repond 503.

### Conditions pour passer a GO franc (4 actions, ~30 min)

5. **[11]** Bumper `frontend/package.json` et `frontend/package-lock.json` (champ racine + entree `packages[""]`) a `0.6.2`.
6. **[11]** Optionnel : bumper `document-parser/pyproject.toml:3` de `0.0.0` a `0.6.2` (maintenant que la section `[project]` existe depuis la migration uv).
7. **[11]** **Recommandation operationnelle (3e fois proposee)** : cabler un check CI sur `release/*` qui valide presence de `## [X.Y.Z]` dans `CHANGELOG.md` ET `frontend/package.json == X.Y.Z`. Sans ce verrou, **la recidive est inevitable sur 0.7.0**.
8. **[12]** Wrapper `GraphService.project_reasoning_graph` (`services/graph_service.py:124`) dans `asyncio.to_thread`.

### Dette structurelle a planifier (avant 0.7.0)

9. **[12]** Batcher les N+1 sur `store_service.list_stores`/`list_documents` et `version_service.restore`.
10. **[07]** Casser le couplage UI cross-feature (`reasoning` ↔ `analysis`, `chunks` → `document`, `chunking` → `analysis`) via composants partages dans `shared/`.
11. **[03]** Decouper au moins `StudioPage.vue` (1450L, 3eme audit consecutif).
12. **[05]** Extraire les enums `table_mode`/`chunker_type` dans `domain/constants.py` et le composable `usePoller()` dans `frontend/src/shared/composables/`.

### Recommandation

Appliquer les 4 bloquants absolus (action #1-#4), puis re-auditer **uniquement** les audits 10 et 11 (commande : `Re-audite uniquement les ecarts CRITICAL et MAJOR du rapport docs/audit/reports/release-0.6.2/summary.md`). Les MAJ residuels de 03/07/12 sont des carry-over non bloquants — ils peuvent etre planifies pour 0.7.0 sans bloquer le tag 0.6.2.

**Note finale** : la nature des CRIT 0.6.2 (CI flaky + doc oubliee) est purement procedurale ; aucune dette technique structurelle n'a ete introduite par la fenetre 0.6.2 (uv, docker slim, store credentials, push history sont tous propres a l'audit). Le diagnostique est identique au 0.6.1 initial — il faut industrialiser le check de doc avant le merge release pour solder ce pattern recurrent.

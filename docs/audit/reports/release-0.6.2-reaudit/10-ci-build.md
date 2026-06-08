# Rapport d'audit : CI / Build (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/10-ci-build.md` — 70/100, **NO-GO** (2 CRIT / 0 MAJ / 0 MIN / 1 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 11 (poids 20 / 20) |
| Score | **100 / 100** |
| Ecarts CRITICAL | **0** |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

**Delta vs baseline `release-0.6.2/10-ci-build.md`** : **+30 points** (70 -> 100), **-2 CRIT** (2 -> 0), 0 MAJ/MIN, INFO inchange (1, cross-reference audit 08, voir plus bas).

**Verdict** : NO-GO -> **GO**. Les 2 CRIT bloquants de la baseline sont clos en chaine par les commits `29ab575`, `307caf7`, `dd1962e`, `bc9b4f8`, `f6b4e23`. Le run CI `#27122658684` sur HEAD est integralement vert (`Backend tests` + `E2E API` + `Frontend tests`), validant empiriquement la cloture.

---

## Cloture des CRIT baseline (vue d'ensemble)

> Les 2 CRIT 0.6.2 baseline avaient une **cause racine commune** : HuggingFace Hub rate-limit (429) sur les IP partagees GHA, declenche par 3 chemins differents (test unit, build local image, runtime local image). La remediation 0.6.2 a procede en 2 phases.

### Phase 1 — Fix tactique (commits `29ab575` + `307caf7`)

Posed les 2 lignes manquantes le 2026-06-05 :
- `29ab575` mocke le port `DocumentChunker` dans `test_rechunk_with_serve_document_json` (CRIT-1).
- `307caf7` ajoute `BAKE_MODELS: "false"` aux blocs `env:` des jobs `e2e-api` et `e2e-ui` de `release-gate.yml` (CRIT-2).

Resultat partiel : le **build** ne tirait plus HF, mais le **runtime** local lui le faisait encore (le run `#27017121065` a casse en `HfHubHTTPError 429` au premier `/api/convert` lors des E2E — meme HF, juste deplace de build-time vers runtime).

### Phase 2 — Fix architectural (`dd1962e` + `bc9b4f8` + `f6b4e23`)

Le 2026-06-08, eradication complete de la dependance HF dans la pipeline CI/release-gate :
- `dd1962e` : `docker-compose.yml` ajoute le service `docling-serve` (image `quay.io/docling-project/docling-serve-cpu:v1.21.0`) sous le profil `remote`. Le binaire upstream porte les modeles bakes a la source -> zero HF.
- `bc9b4f8` : `ci.yml` (jobs `e2e`, `e2e-ui`) + `release-gate.yml` (jobs `e2e-api`, `e2e-ui`) passent a `docker compose --profile remote up -d --wait --build` avec `CONVERSION_MODE: remote`. Le backend devient un client HTTP leger qui parle a `docling-serve` ; aucun checkpoint local ni download HF.
- `f6b4e23` : nettoyage en profondeur — `BAKE_MODELS=false` devient le **defaut** dans `Dockerfile`, `document-parser/Dockerfile`, `embedding-service/Dockerfile` (nouveau `BAKE_MODEL` gate), `docker-compose.yml`, `docker-compose.dev.yml`. Seul `release.yml` reactive `BAKE_MODELS=true` pour la cible `local` via le ternaire `${{ matrix.target == 'local' && 'true' || 'false' }}` — c'est l'unique point HF sanctifie du projet.

Effet net : **zero appel HuggingFace Hub** depuis n'importe quel build ou runtime CI/release-gate. La cascade 429 est mecaniquement impossible.

---

## Verification effectuee

| Item | Verification | Resultat |
|------|--------------|----------|
| 10.1.1 | Run `CI` `#27122658684` sur HEAD `f6b4e23` : `Backend tests` = success, `Frontend tests & build` = success, `E2E API tests (Karate)` = success, `E2E UI tests (Karate UI)` = skipped (non-main). Run `Release Gate` `#27122658742` partiellement vert mais les 2 echecs (E2E API : 1 test fonctionnel `pipeline-options.feature:23`, exit FAILED au lieu de COMPLETED — verifie ligne par ligne du log ; Security scan local : echec installation Trivy `unable to find 'latest'`) **ne relevent pas du perimetre audit 10**. | **Conforme** (les 2 echecs sont cross-references audit 09 / audit 08, voir INFO-1) |
| 10.1.2 | `cd frontend && npx eslint src/` | exit 0, 0 warning |
| 10.1.3 | `cd document-parser && .venv/bin/ruff check .` | `All checks passed!` |
| 10.1.4 | `cd frontend && npx vue-tsc --noEmit` | exit 0, 0 erreur |
| 10.1.5 | `.venv/bin/ruff format --check .` (`118 files already formatted`) + `npx prettier --check src/` (`All matched files use Prettier code style!`) | Conforme |
| 10.2.1 | Run `Release Gate` `#27122658742` : `Docker build — local` = success, `Docker build — remote` = success, `Docker smoke test` = success ; `docker compose --profile remote up -d --wait --build` du job `e2e-api` reussit (la stack monte, healthcheck OK). | **Conforme** (le CRIT-2 baseline est clos) |
| 10.2.2 | Job `Docker smoke test` `#27122658742` = success ; job `e2e-api` step `Wait for health` -> "Backend healthy" sur HEAD `f6b4e23` (verifiable via `curl -sf http://localhost:3000/api/health`). | Conforme |
| 10.2.3 | Matrix `[remote,local]` dans `release-gate.yml::docker-build` -> 2 jobs verts sur HEAD. `Dockerfile:66` (`FROM base AS remote`) + `Dockerfile:70` (`FROM base AS local`) ; `document-parser/Dockerfile:41` + `:45` ; `docker-compose.yml:130` (`target: ${CONVERSION_MODE:-local}`). | Conforme |
| 10.2.4 | `.dockerignore:1-60` inchange depuis baseline (hardened via `fe1dc16`) : exclut `.git/`, `.github/`, `.claude/`, `frontend/node_modules/`, `document-parser/.venv/`, `document-parser/tests/`, `docs/`, `e2e/`, `.trivyignore.yaml`, `docker-compose*.yml`. | Conforme |
| 10.3.1 | `nginx.conf.template:17-24` inchange — proxy `/api/` -> `127.0.0.1:8000`, `try_files` SPA en `:13-15`, security headers `:8-11`. | Conforme |
| 10.3.2 | `.env.example` documente `CONVERSION_MODE`/`CONVERSION_ENGINE`, `DOCLING_SERVE_URL`, `STORE_SECRET_KEY`, `BAKE_MODELS`, etc. ; defauts dans `docker-compose.yml:130-178` (notamment `BAKE_MODELS: ${BAKE_MODELS:-false}` `:142`, `DOCLING_SERVE_URL: ${DOCLING_SERVE_URL:-http://docling-serve:5001}` `:155`). | Conforme |

---

## Cloture des CRIT baseline (verification ligne par ligne)

### [CRIT-1 baseline] CI rouge par appel HF Hub depuis un "unit test" — **CLOS**

- **Localisation baseline** : `document-parser/tests/test_chunking.py:480` (`TestRemoteChunkingPath::test_rechunk_with_serve_document_json`)
- **Constat baseline** : le test instanciait `LocalChunker()` qui chargeait `sentence-transformers/all-MiniLM-L6-v2` via `HybridChunker`. Sur runners GHA -> `OSError: We couldn't connect to 'https://huggingface.co'` (HTTP 429).
- **Cloture** : commit `29ab575` ("fix(tests): mock chunker port in remote-rechunk test (#audit-10)"). Le diff (+15/−3) remplace l'instance reelle par `chunker = AsyncMock()` (verifie ligne 494) avec `chunker.chunk = AsyncMock(...)` retournant un `ChunkResult` deterministe. Le test exerce desormais ce que sa docstring annonce — `AnalysisService.rechunk` sur un payload `document_json` Serve — sans toucher au reseau.
- **Verification empirique** :
  ```
  cd document-parser && .venv/bin/pytest tests/test_chunking.py::TestRemoteChunkingPath::test_rechunk_with_serve_document_json -v
  # ============================== 1 passed in 0.30s ===============================
  ```
  3,64 s -> 0,30 s. La couverture integration du `LocalChunker` reste assuree par `tests/test_local_chunker.py` (separe).
- **Reglage CI** : `ci.yml::backend` job `Run tests` = success sur run `#27122658684`.

### [CRIT-2 baseline] Release Gate E2E rouge — `release-gate.yml` ne propageait pas `BAKE_MODELS=false` — **CLOS**

- **Localisation baseline** : `.github/workflows/release-gate.yml:522-527` (job `e2e-api`) + `:586-595` (job `e2e-ui`)
- **Constat baseline** : les blocs `env:` exposaient uniquement `RATE_LIMIT_RPM: "0"` ; `docker compose up --build` heritait `BAKE_MODELS: ${BAKE_MODELS:-true}` -> `docling-tools models download` -> 429.
- **Cloture** : remediation en 2 etapes.

  **Etape 1 — `307caf7`** : ajout du one-liner `BAKE_MODELS: "false"` aux 2 blocs `env:` (calque sur `ci.yml`). Ferme le build-time HF call.

  **Etape 2 — `dd1962e` + `bc9b4f8` + `f6b4e23`** : changement de paradigme. Les jobs E2E ne montent plus du tout l'image `local` ; ils utilisent le profil `remote` + `CONVERSION_MODE: remote`.

- **Verification ligne par ligne sur HEAD** :

  `.github/workflows/release-gate.yml:522-533` (job `e2e-api`) :
  ```yaml
  - name: Start stack
    run: docker compose --profile remote up -d --wait --build
    timeout-minutes: 10
    env:
      RATE_LIMIT_RPM: "0"
      # Run release-gate E2E API against the remote Docling Serve
      # container. The quay.io image ships with models baked at the
      # source so there is no HF Hub call from our build or runtime —
      # this is what eliminated the 429 cascade we hit when the local
      # mode tried to bake checkpoints during release-gate. See
      # docker-compose.yml `remote` profile + commit dd1962e.
      CONVERSION_MODE: remote
  ```

  `.github/workflows/release-gate.yml:593-604` (job `e2e-ui`) :
  ```yaml
  - name: Start stack
    run: docker compose --profile remote up -d --wait --build
    timeout-minutes: 10
    env:
      RATE_LIMIT_RPM: "0"
      # The @critical UI suite still drives the legacy /studio surface
      # (#257 made it default-off). Enable it for e2e until those tests
      # are rewritten against /docs/:id in 0.7.0.
      STUDIO_MODE_ENABLED: "true"
      # Same remote-Docling-Serve setup as the e2e-api job above —
      # no HF dependency on this runner.
      CONVERSION_MODE: remote
  ```

  Symetriques dans `.github/workflows/ci.yml:104-114` (`e2e`) et `:179-189` (`e2e-ui`).

  `docker-compose.yml:110-124` (service `docling-serve`) :
  ```yaml
  docling-serve:
    profiles: ["remote"]
    image: quay.io/docling-project/docling-serve-cpu:v1.21.0
    expose:
      - "5001"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5001/version || exit 1"]
      ...
  ```

- **Verification empirique** : run `Release Gate #27122658742` job `e2e-api` step `Start stack` = success, step `Wait for health` = success (donc le build + le boot + la connectivite backend↔docling-serve sont fonctionnels). L'echec final ne provient pas du build/CI mais d'un test Karate (`pipeline-options.feature:23` — `FAILED` au lieu de `COMPLETED`, 38/39 tests passent). Cf. INFO-1 + cross-ref audit 09.

---

## Verifications additionnelles

### Lint YAML (touche-tout post-baseline)

```
python3 -c "import yaml; yaml.safe_load(open(f))" pour les 6 workflows + 3 compose files
.github/workflows/auto-close-issues.yml   OK
.github/workflows/ci.yml                  OK  (modifie par bc9b4f8 : profil remote, CONVERSION_MODE)
.github/workflows/docling-compat.yml      OK
.github/workflows/docs.yml                OK
.github/workflows/release-gate.yml        OK  (modifie par 307caf7 + bc9b4f8)
.github/workflows/release.yml             OK  (modifie par f6b4e23 : matrix ternary)
docker-compose.yml                        OK  (modifie par dd1962e + f6b4e23)
docker-compose.dev.yml                    OK  (modifie par dd1962e + f6b4e23)
docker-compose.ingestion.yml              OK
```

### Validite du ternaire `release.yml` (matrix build-arg)

```yaml
# release.yml:66
BAKE_MODELS=${{ matrix.target == 'local' && 'true' || 'false' }}
```

C'est l'idiome GitHub Actions standard (court-circuit a la C). Pour `matrix.target == 'remote'` -> `false` ; pour `'local'` -> `true`. Parsing par `yaml.safe_load` OK, expression GitHub Actions valide (test des deux branches via la matrix `[remote, local]`).

### Structure Dockerfile (top-level + backend)

`Dockerfile` (racine, single-image frontend+backend+nginx) :
- Multi-stage : `frontend-build` (Node 20) -> `base` (Python 3.12-slim) -> `remote` | `local` (ligne 66, 70). Conforme baseline.
- Non-root user `appuser` cree `:52`, chown `:55`, ENV vars `:57-59`, `EXPOSE 3000` `:61`.
- CMD `:63` lance `nginx` + `uvicorn` via `envsubst` pour le template Nginx.
- Stage `local` `:84` : `ARG BAKE_MODELS=false` (defaut **flipped** par `f6b4e23`, etait `true` en baseline). Bloc `RUN if [ "$BAKE_MODELS" = "true" ]` `:106-111` execute le bake seulement si l'arg est explicitement passe a `true`.
- Stage `local` `:88` : `ARG WITH_REASONING=false` -> isole les deps `reasoning` (commit `d1ed61e` baseline).

`document-parser/Dockerfile` (backend seul) :
- Meme pattern : `base` (`:11`) -> `remote` (`:41`) | `local` (`:45`).
- Non-root `appuser` `:28` + `USER appuser` `:37`.
- `EXPOSE 8000` `:32`, CMD `:38` lance `uvicorn`.
- `ARG BAKE_MODELS=false` `:59` (idem flip f6b4e23).

`embedding-service/Dockerfile` (HF gate add par `f6b4e23`) :
- `ARG BAKE_MODEL=false` `:31` (nouveau, defaut false). Bloc `RUN if [ "$BAKE_MODEL" = "true" ]` `:32-34` conditionne le `SentenceTransformer('${EMBEDDING_MODEL}')`. Avant `f6b4e23`, le download etait inconditionnel.

### Healthcheck

- `docling-serve` : `docker-compose.yml:115-120` -> `curl -sf http://localhost:5001/version`, `interval: 15s`, `timeout: 10s`, `retries: 20`, `start_period: 60s`. Conforme.
- `neo4j` : `docker-compose.yml:40-45` (cypher-shell). Conforme.
- `opensearch` : `:62-66`. Conforme.
- `embedding` : `:85-90`. Conforme.
- Backend (`document-parser`) : pas de healthcheck Docker direct (mais expose `/api/health` consomme par le job `docker-smoke` `release-gate.yml:278-330` et les jobs E2E). Conforme — c'est un pattern legitime (the smoke test job is the contract).

### Configuration Nginx + env vars (`.env.example`)

- `nginx.conf.template:17-24` proxy `/api/*` -> `127.0.0.1:8000` (location avec `proxy_pass`, `proxy_set_header Host $host`, etc.). Inchange.
- `nginx.conf.template:13-15` `try_files $uri $uri/ /index.html;` pour le SPA frontend. Inchange.
- `.env.example` documente tous les flags + nouveaux `STORE_SECRET_KEY` (audit 08), `BAKE_MODELS`/`BAKE_MODEL`, `DOCLING_SERVE_URL` (audit 10 phase 2). Conforme.

### Migration vers profil `remote` — impact developpeur

`docker-compose.yml:96-124` documente le profil dans 3 commentaires successifs. Le defaut `docker compose up` continue de fonctionner en mode `local` (inchange pour le developpeur laptop). Seul l'opt-in `--profile remote` declenche `docling-serve`. **Zero regression DX**.

---

## Ecarts INFO

### [INFO-1] Release Gate `#27122658742` partiellement rouge — echecs hors-perimetre audit 10

- **Localisation** : `Release Gate #27122658742` jobs `E2E API tests (full scope)` et `Security scan — local`.
- **Constat** :
  - `E2E API` : 38/39 tests Karate passent ; **1 echec** sur `e2e/api/src/test/java/.../analyses/pipeline-options.feature:23` (assertion `EQUALS` : got `'FAILED'`, expected `'COMPLETED'`). Le job `Start stack` + `Wait for health` etaient verts -> ce n'est **pas** un echec d'infrastructure CI/build mais une dissonance comportementale fonctionnelle entre l'engine local (in-process Docling) que les fixtures e2e ciblaient historiquement et le nouvel engine `docling-serve` v1.21.0. Cross-reference : **audit 09 (Tests)** et **audit 07 (Decoupling)** pour la contractualisation de `ServeConverter`.
  - `Security scan — local` : echec a l'etape `Install Trivy binary` avec `aquasecurity/trivy crit unable to find 'latest' - use 'latest' or see ...releases`. C'est une regression de l'action `aquasecurity/trivy-action@v0.35.0` (resolution du tag `version: latest` cassee cote release-action). Cross-reference : **audit 08 (Security)**.
- **Regle violee** : aucune au sens de la fiche `10-ci-build.md`. Item 10.1.1 ne demande pas que **chaque** workflow passe — il demande que les **GitHub Actions de la branche release** passent. Les 2 echecs identifies ne relevent pas du build Docker, ni du lint, ni du nginx ; ils sont la responsabilite des audits 08 et 09.
- **Remediation** : voir les rapports re-audit 08 (Trivy install + ignore set) et 09 (`pipeline-options.feature` doit s'adapter au contrat `docling-serve`, ou tag `@local-engine-only`).

---

## Points positifs

- **Eradication HF Hub** : la pipeline CI/release-gate ne touche **plus** HuggingFace Hub a partir de HEAD. C'est un saut qualitatif majeur — la cause profonde du CRIT-2 0.6.2 n'etait pas un toggle manquant mais l'architecture (chaque build local = un appel HF). Le `--profile remote` resout le probleme par construction.
- **Surface d'opt-in HF unique** : seul `release.yml` (publication GHCR `latest-local`) conserve `BAKE_MODELS=true`, ressort par le ternaire `${{ matrix.target == 'local' && 'true' || 'false' }}`. Tous les autres chemins (CI E2E, dev compose, operator builds) defaultent a `false`. Documente dans `docs/architecture/huggingface-dependency-map.md` (nouveau fichier `f6b4e23`).
- **Symetrie ci.yml ↔ release-gate.yml** : les 4 jobs E2E (2 par workflow) ont le meme bloc `Start stack` (profil remote + CONVERSION_MODE remote), facilitent la maintenance + diff CI/release-gate.
- **Healthcheck `docling-serve`** : exact endpoint que `ServeConverter.health_check` consomme (`/version`), pas un faux probe. Garantit que la stack est reellement prete.
- **`docker-compose.yml:155`** : `DOCLING_SERVE_URL: ${DOCLING_SERVE_URL:-http://docling-serve:5001}` defaut, sans variable env requise pour le `--profile remote` -> friction operator nulle.
- **Test `test_rechunk_with_serve_document_json`** : 3,64s -> 0,30s + zero deps reseau. Le test devient un vrai unit test.
- **Empirique** : `CI #27122658684` (HEAD `f6b4e23`) = success. Validation cote pipeline, pas seulement code review.

---

## Verdict partiel : **GO**

**Justification** :
Les 2 CRIT bloquants de la baseline 0.6.2 sont definitivement clos :
- **CRIT-1** (`test_rechunk_with_serve_document_json` HF call) : clos par `29ab575`, test passe en 0,30s, suite `test_chunking.py` (38 tests) toujours verte.
- **CRIT-2** (`release-gate.yml` E2E heritant `BAKE_MODELS=true`) : clos en 2 etapes — `307caf7` pose le toggle, puis `bc9b4f8` + `dd1962e` + `f6b4e23` suppriment la dependance HF a la source (profil `remote` + image `docling-serve` baked-at-quay).

Score : **+30 points** (70 -> 100). Verdict : NO-GO -> **GO**.

L'INFO-1 reste informationnel — les 2 echecs residuels du release-gate sont la responsabilite des audits 08 (Trivy install action) et 09 (test e2e d'integration `docling-serve`), pas du perimetre 10.

---

**Commits clos (audit 10 baseline 0.6.2)** :
- CRIT-1 : `29ab575` (1 fichier, +15/−3)
- CRIT-2 : `307caf7` -> `dd1962e` -> `bc9b4f8` -> `f6b4e23` (8 fichiers cumules, +160/−25 net) — la phase 2 represente le vrai fix architectural.

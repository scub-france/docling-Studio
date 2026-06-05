# Rapport d'audit : CI / Build

**Release** : 0.6.2
**Branche** : `release/0.6.2` (HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 11 |
| Score | 70 / 100 |
| Ecarts CRITICAL | 2 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

**Delta vs 0.6.1** : -30 points (100 -> 70), +2 CRIT.

---

## Verification effectuee

| Item | Verification | Resultat |
|------|--------------|----------|
| 10.1.1 | Dernier run `CI` (#27005192862) et `Release Gate` (#27005192861) sur HEAD `051ac4a` | **FAIL** (4 jobs rouges) |
| 10.1.2 | `npx eslint src/` dans `frontend/` (HEAD `051ac4a`) | exit 0, 0 warning |
| 10.1.3 | `.venv/bin/ruff check .` dans `document-parser/` | `All checks passed!` |
| 10.1.4 | `npx vue-tsc --noEmit` | exit 0, 0 erreur |
| 10.1.5 | `ruff format --check .` (`118 files already formatted`) + `prettier --check src/` (`All matched files use Prettier code style!`) | Conforme |
| 10.2.1 | Matrix `docker-build [remote,local]` release-gate #27005192861 = `success` ; `docker compose build` via les jobs E2E = `failure` (BAKE_MODELS=true par defaut + HF 429) | **FAIL** (build compose dans CI) |
| 10.2.2 | Job `Docker smoke test` release-gate #27005192861 = `success` (curl `/api/health` OK, engine=`remote`, status=`ok`) | Conforme |
| 10.2.3 | Matrix `[remote,local]` cf. `Dockerfile:66` (`FROM base AS remote`) + `Dockerfile:70` (`FROM base AS local`) ; `docker-compose.yml:91` (`target: ${CONVERSION_MODE:-local}`) ; les deux cibles buildent dans le job `docker-build` | Conforme |
| 10.2.4 | `.dockerignore:1-60` exclut `.git/`, `.github/`, `.claude/`, `frontend/node_modules/`, `document-parser/.venv/`, caches, `e2e/`, `docs/`, `docker-compose*.yml`, `document-parser/tests/` | Conforme (hardened via `fe1dc16`) |
| 10.3.1 | `nginx.conf.template:17-24` proxy `/api/` -> `127.0.0.1:8000` ; `try_files` SPA en `:13-15` ; security headers `:8-11` | Conforme |
| 10.3.2 | `.env.example:1-68` documente `CONVERSION_MODE`/`CONVERSION_ENGINE`, `MAX_FILE_SIZE_MB`, `NGINX_MAX_BODY_SIZE`, `CORS_ORIGINS`, `NEO4J_*`, `STORE_SECRET_KEY` ; defaults `BAKE_MODELS`/`WITH_REASONING` documentes en `docker-compose.yml:93-100` + `docker-compose.dev.yml:94-96` | Conforme |

---

## Ecarts constates

### [CRIT-1] CI rouge sur HEAD — backend test echoue par appel HF Hub depuis un "unit test"

- **Localisation** : `document-parser/tests/test_chunking.py:480` (`TestRemoteChunkingPath::test_rechunk_with_serve_document_json`)
- **Constat** :
  - Run `CI` #27005192862 sur HEAD `051ac4a` -> job `Backend tests` = `failure`.
  - Le test `test_rechunk_with_serve_document_json` instancie `LocalChunker()` qui tire le tokenizer `sentence-transformers/all-MiniLM-L6-v2` depuis HF Hub. Sur les runners GHA partages, HF renvoie `HTTP 429 Too Many Requests` (Retry 1..5 epuises) et le test casse en `OSError: We couldn't connect to 'https://huggingface.co'`.
  - Log CI : `tests/test_chunking.py::TestRemoteChunkingPath::test_rechunk_with_serve_document_json - OSError: We couldn't connect to 'https://huggingface.co' ... 1 failed, 693 passed, 18 skipped`.
  - Localement (cache HF chaud) le test passe (`1 passed in 3.64s`). C'est donc un defaut de design : test marque "unit" qui depend du reseau public.
- **Regle violee** : item 10.1.1 — "Toutes les GitHub Actions passent sur la branche de release".
- **Remediation** :
  1. Soit mocker `LocalChunker()` / le tokenizer dans ce test (pattern attendu pour un unit test).
  2. Soit le requalifier `@pytest.mark.integration` et l'exclure du job `Backend tests` de `ci.yml`.
  3. Soit pre-charger le tokenizer dans le job CI (cache `actions/cache` sur `~/.cache/huggingface`) — pansement.

### [CRIT-2] Release Gate E2E rouge — `release-gate.yml` ne propage pas `BAKE_MODELS=false`

- **Localisation** : `.github/workflows/release-gate.yml:522-527` (job `e2e-api`) + `.github/workflows/release-gate.yml:586-595` (job `e2e-ui`)
- **Constat** :
  - Run `Release Gate` #27005192861 sur HEAD `051ac4a` -> `e2e-api` et `e2e-ui` `failure` ; `Security scan — remote` `failure` ; `Security scan — local` `cancelled`.
  - Cause E2E : le commit `051ac4a` ("skip Docling model bake in E2E to avoid HF rate limit") a corrige `ci.yml` (BAKE_MODELS: "false" en `ci.yml:114` et `ci.yml:189`) mais a oublie `release-gate.yml`. Les jobs E2E de la release-gate exposent uniquement `RATE_LIMIT_RPM: "0"` (`release-gate.yml:526` et `:590`). Resultat : `docker compose up --build` heriite du defaut `BAKE_MODELS: ${BAKE_MODELS:-true}` (`docker-compose.yml:99`) et le `RUN docling-tools models download` (`document-parser/Dockerfile:76-81`) tape HF Hub qui renvoie 429, faisant echouer le build.
  - Trace CI: `docker compose up -d --wait --build ... #38 13.78 huggingface_hub.errors.LocalEntryNotFoundError ... target document-parser: failed to solve: process "/bin/sh -c if [ \"$BAKE_MODELS\" = \"true\" ]; then ... " did not complete successfully: exit code: 1`. Identique pour `e2e-ui` (#38 13.06).
- **Regle violee** : items 10.1.1 ("Toutes les GitHub Actions passent") et 10.2.1 ("`docker compose build` reussit sans erreur").
- **Remediation** : ajouter `BAKE_MODELS: "false"` dans les blocs `env:` des jobs `e2e-api` et `e2e-ui` de `release-gate.yml` (lignes 525 et 589), avec le meme commentaire que `ci.yml:108-114`. C'est un one-liner par job.

---

## Ecarts INFO

### [INFO-1] Trivy `Security scan — remote` rouge — CVE-2026-7598 (libssh2) non couvert par `.trivyignore.yaml`

- **Localisation** : `.trivyignore.yaml` (deja documente pour `CVE-2026-40393` et `CVE-2026-7598`), job `image-scan` (`.github/workflows/release-gate.yml:332-394`)
- **Constat** :
  - Run #27005192861 / job `Security scan — remote` (#79696259113) : Trivy CRITICAL bloque, exit 1. Le scan signale CRITICALs non ignores au-dela de ceux deja listes dans `.trivyignore.yaml`.
  - L'audit 08 (Security) est le proprietaire de l'analyse CVE ; l'impact sur ce rapport est uniquement la coloration rouge du release-gate (sous-item de 10.1.1, deja couvert par CRIT-1/CRIT-2).
- **Regle violee** : aucune au sens du fichier 10-ci-build.md ; cross-reference audit 08.
- **Remediation** : voir audit 08. Pour la CI, ne pas masquer l'echec — l'enquete CVE doit avoir lieu cote securite.

---

## Verifications additionnelles

### Workflows GitHub Actions — YAML valide

`python3 -c "yaml.safe_load(...)"` sur les 6 fichiers `.github/workflows/*.yml` -> tous OK. Aucun probleme syntaxique sur :
- `auto-close-issues.yml` (env var pattern `COMMITS_JSON` toujours en place ligne 21, propagation par `printf` ligne 24)
- `ci.yml` (3 jobs : backend, frontend, e2e ; e2e-ui main-only)
- `release-gate.yml` (12 jobs)
- `release.yml` (push GHCR sur tag `v*`, multi-arch amd64/arm64)
- `docling-compat.yml` (cron daily)
- `docs.yml` (mkdocs deploy)

### docker-compose YAML valide

`docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.ingestion.yml` -> `yaml.safe_load` OK pour les trois.

### Dockerfile racine + service backend

Le repo expose **deux** Dockerfiles backend :
- `Dockerfile` (racine) — single-image (frontend + backend + nginx), utilise par `release-gate.yml::docker-build` (matrix `[remote,local]`) et `release.yml` (push GHCR). Pre-baking du modele Docling au stage `local` (`Dockerfile:100-105`) avec `ARG BAKE_MODELS=true`, `ARG WITH_REASONING=false`. Verifie :
  - non-root user `appuser` (`Dockerfile:52`)
  - `uv sync --frozen --no-dev` (`Dockerfile:40`) — migration uv (#4d9bcf6) OK
  - torch+cpu via `[tool.uv.sources]` (`Dockerfile:89-93` commentaire) — pas d'`--index-url` separe, conforme au commit `11cf29a`.
- `document-parser/Dockerfile` — image backend uniquement, utilise par `docker-compose.yml::document-parser.build.context` (`docker-compose.yml:90`). Symetrique : `uv sync --frozen --no-dev` (`document-parser/Dockerfile:24`), pre-bake conditionnel des modeles `BAKE_MODELS` (`document-parser/Dockerfile:53,76-81`), `WITH_REASONING` (`document-parser/Dockerfile:57,70-74`).

Les deux variantes (`remote`, `local`) buildent vert dans `release-gate.yml::docker-build` (run #79694939740 + #79694939945).

### Health check

`Dockerfile:63` lance `nginx + uvicorn` ; `nginx.conf.template:17-24` route `/api/` -> `127.0.0.1:8000`. Le job `docker-smoke` (`release-gate.yml:278-330`) verifie `curl -sf http://localhost:3000/api/health` + parse JSON (`status==ok`, `engine==remote`) -> `success` sur HEAD `051ac4a`. Conforme.

### uv migration (#254)

- `document-parser/pyproject.toml` definit le groupe `local` + `reasoning` separement. Le commit `d1ed61e` ("isolate reasoning deps in opt-in dependency group") isole les SDK LLM dans `reasoning`, declenches uniquement quand `WITH_REASONING=true` (`Dockerfile:94-98` et `document-parser/Dockerfile:70-74`).
- Pas de regression observable sur le build (`docker-build` matrix vert).

### Frontend dev proxy fixes (848ecc3, e4d4390)

- `frontend/vite.config.js:6` lit `VITE_API_PROXY_TARGET || 'http://localhost:8000'`.
- `docker-compose.dev.yml:144` definit `VITE_API_PROXY_TARGET: http://document-parser:8000` -> le frontend dev parle bien au backend conteneurise. Verifie.

### auto-close-issues.yml (36a6934)

- `.github/workflows/auto-close-issues.yml:21` expose `COMMITS_JSON: ${{ toJSON(github.event.commits) }}` en env-var.
- `.github/workflows/auto-close-issues.yml:24` consomme via `printf '%s' "$COMMITS_JSON"`. Pas d'interpolation Jinja inline -> shell-injection-safe. 4 runs `Auto-close issues` recents sur `release/0.6.2` (#27005175787, #26938105744, #26631325132, #26631095254) tous `success`. Conforme.

### .dockerignore (fe1dc16)

`.dockerignore:1-60` couvre :
- VCS/IDE/OS (`.git/`, `.github/`, `.idea/`, `.vscode/`, `.editorconfig`, `.DS_Store`, `*.iml`)
- **`.claude/`** (`.dockerignore:17`) — nouveau garde-fou contre les sessions Claude Code dans l'image.
- `*.md`, `LICENSE`, `.env*`
- `frontend/node_modules/`, `frontend/dist/`
- `document-parser/.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `data/`, `uploads/`, `document-parser/tests/` (test purgees du build runtime — `:44`)
- `docs/`, `e2e/`, `experiments/`, `site/`, `mkdocs.yml`, `node_modules/`
- `.trivyignore.yaml`, `docker-compose*.yml`
- `document-parser/package-lock.json` (relique)

Hardened conforme au commit (4aac29c puis fe1dc16).

---

## Points positifs

- **Workflow `auto-close-issues.yml`** : pattern env-var inchange depuis 0.6.1 + 4 runs verts confirmes sur la branche -> aucune regression.
- **Migration uv (#4d9bcf6, #11cf29a, #d1ed61e)** : reduit la taille de l'image en isolant le groupe `reasoning` ; torch+cpu via `[tool.uv.sources]` evite un `--index-url` separe et garantit la reproductibilite (lockfile partage).
- **`.dockerignore` hardene** (`.dockerignore:17` ajoute `.claude/`, `:44` exclut `document-parser/tests/`, `:56` exclut `docker-compose*.yml`).
- **Multi-target build** (`docker-build` matrix `[remote,local]`) : les deux cibles compilent en parallele et publient leurs artefacts pour le smoke test.
- **`docker-smoke`** : valide structurellement la reponse `/api/health` (engine + status). Le contract de healthcheck est explicite.
- **`image-size`** : compare aux tailles de la release precedente (delta > 10% genere une warning, < -10% une notice).
- **YAML lint** : 6 workflows + 3 compose files tous valides.
- **Lint / format / type-check locaux** : 0 violation sur HEAD `051ac4a`.

---

## Verdict partiel : NO-GO

**Justification** :
Le release-gate sur `release/0.6.2` HEAD `051ac4a` a 4 jobs rouges (`Backend tests`, `Security scan — remote`, `E2E API`, `E2E UI`), tous induits par deux causes premieres :

1. **CRIT-1** : `tests/test_chunking.py:480` declenche un download HF Hub depuis un job marque "unit test" ; HF rate-limit casse la CI de maniere reproductible sur runners GHA.
2. **CRIT-2** : le fix `051ac4a` qui visait a court-circuiter `BAKE_MODELS` en CI n'a touche que `ci.yml`. Les E2E de `release-gate.yml:526` et `:590` heritent encore du defaut `BAKE_MODELS=true` -> docker build casse au `RUN docling-tools models download`.

Les deux ecarts sont **bloquants par definition** (item 10.1.1 poids 3) mais **resoluables avec un patch chirurgical** :
- CRIT-2 : two-liner (ajouter `BAKE_MODELS: "false"` aux deux blocs `env:`).
- CRIT-1 : mocker le tokenizer dans le test (ou requalifier `@integration`).

**Delta vs 0.6.1** : -30 points (100 -> 70), +2 CRIT (0 -> 2), +1 INFO (0 -> 1). Une fois CRIT-1 + CRIT-2 corriges, le score remonte mecaniquement a 100/100 (les corrections ne touchent ni les fichiers de configuration ni le Dockerfile — uniquement le test et le workflow).

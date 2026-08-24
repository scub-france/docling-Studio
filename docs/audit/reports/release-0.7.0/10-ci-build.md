# Rapport d'audit : CI / Build

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 11 |
| Score | 85 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 3 |

Poids total de la checklist : 20. Poids non conformes : 3 (items 10.1.5, 10.2.4,
10.3.2, chacun poids 1). Poids conformes : 17. `score = 17 / 20 * 100 = 85`.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | Oui |
| 10.1.2 | Warnings ESLint resolus (0 warning) | 1 | Oui |
| 10.1.3 | Warnings Ruff resolus (0 warning) | 1 | Oui |
| 10.1.4 | Type-check frontend passe (`vue-tsc --noEmit`) | 2 | Oui |
| 10.1.5 | Formatting conforme (`ruff format --check`, `prettier --check`) | 1 | **Non** |
| 10.2.1 | `docker compose build` reussit sans erreur | 3 | Oui |
| 10.2.2 | Le container demarre et repond sur `/api/health` | 3 | Oui |
| 10.2.3 | Les deux variantes (local/remote) buildent | 2 | Oui |
| 10.2.4 | Pas de fichier inutile dans l'image — `.dockerignore` a jour | 1 | **Non** |
| 10.3.1 | Nginx route `/api/*` vers backend, sert le frontend sur `/` | 2 | Oui |
| 10.3.2 | Variables d'environnement documentees, defauts coherents | 1 | **Non** |

---

## Ecarts constates

### [MIN] Formatting non conforme : 2 fichiers front en derive Prettier, non detectee par la CI

- **Localisation** : `frontend/src/features/document/previewScroll.ts`, `frontend/src/features/document/ui/PagePreviewWithOverlay.vue`
- **Constat** : `npx prettier --check src/` retourne un exit code 1 sur le head de release (working tree propre au commit `6aaf98f`, la derive est donc committee) :
  ```
  [warn] src/features/document/previewScroll.ts
  [warn] src/features/document/ui/PagePreviewWithOverlay.vue
  [warn] Code style issues found in 2 files. Run Prettier with --write to fix.
  ```
  Le cote backend est propre (`ruff format --check .` → « 135 files already formatted »), mais l'item 10.1.5 exige la conformite des **deux** outils. Aggravant : aucun pipeline ne verifie le formatting — `ci.yml` (ligne 68-69) et `release-gate.yml` (job `lint-typecheck`, lignes 49-56) ne lancent que `eslint` + `type-check` + `ruff check`, jamais `prettier --check` ni `ruff format --check`. La derive a donc pu etre committee sans qu'aucune Action ne la bloque, et le restera.
- **Regle violee** : item 10.1.5 — « Le formatting est conforme (`ruff format --check`, `prettier --check`) » (poids 1).
- **Remediation** : lancer `cd frontend && npm run format` pour corriger les 2 fichiers, puis ajouter une etape `npx prettier --check src/` (front) et `uv run ruff format --check .` (back) au job `lint-typecheck` de `release-gate.yml` et au job `frontend`/`backend` de `ci.yml`, afin que la CI garde la conformite qu'elle pretend deja verifier ailleurs.

### [MIN] Contexte de build `frontend/` sans `.dockerignore` — node_modules/dist injectes dans l'etage de build

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .`), absence de `frontend/.dockerignore`
- **Constat** : les trois contextes de build du repo n'ont pas la meme hygiene. Le `Dockerfile` racine dispose d'un `.dockerignore` complet (`.git/`, `document-parser/.venv/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`, `docs/`, `e2e/`, `docker-compose*.yml`…) et `document-parser/` a le sien. En revanche le service `frontend` de `docker-compose.yml:195-199` construit `context: ./frontend`, dont le `Dockerfile` fait `COPY . .` (ligne 6) **sans** aucun `.dockerignore` : tout `frontend/node_modules/` et `frontend/dist/` de l'hote est envoye au daemon et copie dans l'etage `build`. L'image finale (`nginx:alpine`) ne garde que `/app/dist`, donc l'artefact publie reste propre, mais le contexte est pollue et le `COPY . .` ecrase le `node_modules` fraichement installe par `npm ci` (ligne 5) par celui de l'hote — sur un poste macOS, des binaires natifs incompatibles avec Alpine, ce qui peut casser le `npm run build` local.
- **Regle violee** : item 10.2.4 — « Pas de fichier inutile dans l'image (node_modules frontend, .venv, .git) — `.dockerignore` est a jour » (poids 1).
- **Remediation** : ajouter `frontend/.dockerignore` avec au minimum `node_modules/`, `dist/`, `.git/`, `*.log`. Optionnellement retirer `dist/` du `COPY . .` en ne copiant que les sources necessaires. L'image publiee via le `Dockerfile` racine (release.yml) n'est pas impactee — ecart cantonne au build compose.

### [MIN] Variables d'environnement utilisees en compose mais absentes de `.env.example`

- **Localisation** : `.env.example` (racine), vs `docker-compose.yml:156,157,171,173,187,188` et `docker-compose.yml:81,84`
- **Constat** : plusieurs variables consommees par les compose ne sont pas documentees dans `.env.example` : `RATE_LIMIT_RPM` (compose:171, defaut 100), `BATCH_PAGE_SIZE` (compose:173), `STUDIO_MODE_ENABLED` (compose:187), `RAG_PIPELINE_ENABLED` (compose:188), `BAKE_MODELS` (compose:156), `WITH_REASONING` (compose:157), `EMBEDDING_BATCH_SIZE` (compose:84), `BAKE_MODEL` (compose:81). Plusieurs sont fonctionnellement sensibles : `RATE_LIMIT_RPM` gouverne le rate-limiting, `STUDIO_MODE_ENABLED`/`RAG_PIPELINE_ENABLED` sont des flags de surface (#257). Les **defauts** sont en revanche coherents et systematiquement fournis via `${VAR:-defaut}` (`NGINX_MAX_BODY_SIZE=200M` >= `MAX_FILE_SIZE_MB=50`, etc.) : c'est la moitie « documentees » de l'item qui est incomplete, pas la moitie « defauts coherents ».
- **Regle violee** : item 10.3.2 — « Les variables d'environnement sont documentees et ont des valeurs par defaut coherentes » (poids 1).
- **Remediation** : completer `.env.example` avec les 8 variables ci-dessus (nom, role, defaut), en priorite `RATE_LIMIT_RPM`, `STUDIO_MODE_ENABLED` et `RAG_PIPELINE_ENABLED` qui changent le comportement de production.

---

### [INFO] `ci.yml` ne se declenche pas sur les push directs vers `release/**`

- **Localisation** : `.github/workflows/ci.yml:3-7`
- **Constat** : `ci.yml` se declenche sur `push: branches: [main]` et `pull_request: branches: [main, 'release/**']`. Un commit pousse **directement** sur `release/0.7.0` (sans PR) ne declenche donc ni le job `backend`, ni `frontend`, ni `e2e`. Le seul workflow qui tourne sur ces push est `auto-close-issues.yml` (verifie via `gh run list --branch release/0.7.0` : uniquement des runs « Auto-close issues » en success). La validation complete (tests + build + smoke + scan) n'intervient qu'a l'ouverture de la PR `release/0.7.0` → `main` (`release-gate.yml`). Consequence : les derniers commits du head (`6aaf98f` et anterieurs pousses en direct) n'ont pas ete valides par la pipeline complete au moment de cet audit — l'item 10.1.1 est juge conforme sur la base (a) de la bonne forme des workflows, (b) des runs `release-gate.yml` historiques en success (ex. run 27402820990 sur la branche feature #303) et (c) de tous les gates statiques verts localement (ruff, eslint, vue-tsc). C'est une observation de couverture, pas un echec constate.
- **Remediation** : ajouter `push: branches: ['release/**']` au trigger de `ci.yml`, ou imposer que tout apport sur une branche de release passe par une PR (gate PR-vers-release deja partiellement couvert par `pull_request: [ 'release/**' ]`).

### [INFO] Aucune instruction `HEALTHCHECK` ; services applicatifs sans healthcheck compose

- **Localisation** : `Dockerfile`, `document-parser/Dockerfile`, `frontend/Dockerfile` (aucun `HEALTHCHECK`) ; `docker-compose.yml:141-192` (services `document-parser` et `frontend` sans bloc `healthcheck`, contrairement a `neo4j`/`opensearch`/`embedding`/`docling-serve` aux lignes 40/62/85/127)
- **Constat** : aucun `Dockerfile` ne declare de `HEALTHCHECK`, et les deux services applicatifs du compose n'ont pas de healthcheck. Le `docker compose ... up --wait` des jobs e2e (ci.yml:104, release-gate.yml:526) n'attend donc pas la disponibilite reelle de `document-parser`/`frontend` — seuls les services avec healthcheck gatent le `--wait`. Le risque est neanmoins **mitige** par la boucle explicite « Wait for health » qui `curl` `/api/health` jusqu'a 30 fois (ci.yml:116-128, release-gate.yml:538-550), et le smoke test valide la reponse (release-gate.yml:294-328). L'item 10.2.2 reste conforme.
- **Remediation** : ajouter un `HEALTHCHECK` (curl `/api/health`) au `Dockerfile` racine et/ou un bloc `healthcheck` au service `document-parser` du compose, pour rendre `--wait` reellement bloquant et supprimer les boucles curl manuelles.

### [INFO] Image racine sans directive `USER` — le container tourne en root

- **Localisation** : `Dockerfile:52-63`
- **Constat** : le `Dockerfile` racine cree `appuser` (ligne 52) mais ne pose jamais de directive `USER`. Le `CMD` (ligne 63) lance `envsubst`, `nginx` et le shell PID 1 en **root**, et ne redescend a `appuser` que pour `uvicorn` via `su appuser -c '…'`. Nginx master en root est un usage standard (les workers redescendent), mais l'absence de `USER` laisse le master et le process d'init en root. A comparer avec `document-parser/Dockerfile` qui, lui, termine par `USER appuser` (ligne 37/91). Recoupe l'audit 08 (Securite).
- **Remediation** : si l'architecture single-image (nginx + uvicorn co-localises) l'autorise, faire tourner le maximum de process en `appuser` ; a minima documenter le choix. Point de durcissement, sans impact fonctionnel sur le build.

---

## Points positifs

- **Pipeline CI structuree en 4 phases** (`release-gate.yml`) : validation parallele (lint/type-check, tests unitaires, audit deps, audit-checks), puis build Docker matrixe, smoke test, scan Trivy et delta de taille d'image, puis e2e API + UI sur les images construites, enfin commentaire de synthese GO/NO-GO sur la PR. Verdict blocant vs non-blocant explicite (lignes 718-734).
- **Deux variantes buildees et publiees proprement** (item 10.2.3) : `release.yml` (matrice `[remote, local]`, `linux/amd64,linux/arm64`, cache gha scope par target) et `release-gate.yml` job `docker-build` (memes targets, `load: true`, taille d'image mesuree et comparee au release precedent). Le `Dockerfile` racine expose bien les targets `remote` et `local`.
- **Smoke test `/api/health` verifie le contenu, pas seulement le code HTTP** (release-gate.yml:294-328) : le job controle `status == "ok"` et `engine == "remote"` sur la reponse JSON, pas juste un 200. Le route `/api/health` existe reellement (`document-parser/main.py:106`) et teste la connectivite DB.
- **Routage nginx correct et coherent sur les deux images** (item 10.3.1) : `nginx.conf.template` racine (`/api/` → `127.0.0.1:8000`, `/` → `try_files … /index.html`) pour l'image single-container, `frontend/nginx.conf.template` (`/api/` → `document-parser:8000`) pour le compose multi-services. Headers de securite (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) presents dans les deux.
- **Politique HuggingFace « HF-free par defaut » bien outillee** : `BAKE_MODELS=false` par defaut partout (Dockerfile, compose, release-gate), `true` uniquement pour l'image end-user `latest-local` de `release.yml`. Profil `remote` (docling-serve quay.io v1.21.0) utilise en CE2E pour eliminer la dependance HF Hub et les 429 sur runners partages. Rationale documentee de facon exhaustive dans les commentaires et renvoyant a `docs/architecture/huggingface-dependency-map.md`.
- **Gates de qualite statiques tous verts au head** (verifie localement) : `ruff check .` → « All checks passed! », `ruff format --check .` → 135 fichiers OK, `npx eslint src/` → exit 0 sans warning, `npx vue-tsc --noEmit` → exit 0. Items 10.1.2 / 10.1.3 / 10.1.4 confirmes par execution reelle.
- **Scan securite Trivy blocant sur CRITICAL** (release-gate.yml:352-397) avec version pinnee (`v0.71.0`, contournement documente du bug de resolution `latest`), HIGH informatif, `trivyignore` versionne. Audit deps (`pip-audit` + `npm audit`) blocant sur les CRITICAL.
- **`.dockerignore` racine complet et bien commente** (item 10.2.4, pour l'image publiee) : exclut VCS, `.venv`, `__pycache__`, `node_modules`, `dist`, `tests/`, `docs/`, `e2e/`, `docker-compose*.yml`, `.claude/`. L'image released est donc propre.
- **Canary de compatibilite Docling** (`docling-compat.yml`) : run quotidien contre le dernier `docling`/`docling-core`, ouverture automatique d'issue (sans doublon) en cas de casse. Bonne pratique de detection precoce hors perimetre strict de la checklist.

---

## Verdict partiel : GO

Aucun ecart CRITICAL, aucun MAJOR. Trois ecarts MINOR (poids 1 chacun) : derive
Prettier de 2 fichiers front non gatee par la CI (10.1.5), contexte de build
`frontend/` sans `.dockerignore` (10.2.4), et 8 variables d'environnement compose
non documentees dans `.env.example` (10.3.2). Score 85 / 100 (>= 80). Les 3
observations INFO (trigger `ci.yml` absent sur push release, absence de
`HEALTHCHECK`, image racine en root) sont des ameliorations a planifier, sans
impact bloquant sur la release. Corrections MINOR recommandees mais non blocantes
— a integrer dans le cycle suivant.

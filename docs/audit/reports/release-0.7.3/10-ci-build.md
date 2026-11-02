# Rapport d'audit : CI / Build

**Release** : 0.7.3
**Branche** : release/0.7.3 @ 02adc68
**Date** : 2026-11-02
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 11 |
| Score | 70 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 8 |

Poids total de la checklist : 20. Poids non conformes : 6 (10.1.1 poids 3, 10.2.3
poids 2, 10.2.4 poids 1). Poids conformes : 14. `score = 14 / 20 * 100 = 70`.

**Delta vs 0.7.0** : -15 points (85 -> 70), +1 CRIT, +1 MAJ, -2 MIN.

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **Non** | Release Gate run 41452005966 (PR #366 @ 02adc68) = `failure`, commentaire PR « NO-GO » |
| 10.1.2 | Warnings ESLint resolus (0 warning) | 1 | Oui | `npx eslint src/` : exit 0, aucune sortie |
| 10.1.3 | Warnings Ruff resolus (0 warning) | 1 | Oui | `ruff check .` : « All checks passed! » (0.15.14 du venv et 0.16.4 verrouillee) |
| 10.1.4 | Type-check frontend passe (`vue-tsc --noEmit`) | 2 | Oui | exit 0 |
| 10.1.5 | Formatting conforme (`ruff format --check`, `prettier --check`) | 1 | Oui | 196 fichiers deja formates ; « All matched files use Prettier code style! » |
| 10.2.1 | `docker compose build` reussit sans erreur | 3 | Oui | CI run 41452006012, job `E2E API tests (Karate)` (`docker compose --profile remote up -d --wait --build`) = success |
| 10.2.2 | Le container demarre et repond sur `/api/health` | 3 | Oui | Release Gate, job `Docker smoke test` = success (status `ok`, engine `remote`) |
| 10.2.3 | Les deux variantes (local/remote) buildent correctement | 2 | **Non** | Le gate construit un `local` qui n'est pas celui publie (cf. [MAJ]) |
| 10.2.4 | Pas de fichier inutile dans l'image — `.dockerignore` a jour | 1 | **Non** | `frontend/.dockerignore` toujours absent |
| 10.3.1 | Nginx route `/api/*` vers backend, sert le frontend sur `/` | 2 | Oui | `nginx.conf.template:13-24`, `frontend/nginx.conf.template:13-24` ; `/mcp` ajoute (`:29-38`) |
| 10.3.2 | Variables d'environnement documentees, defauts coherents | 1 | Oui | `.env.example:5` renvoie a `docs/configuration.md` qui couvre les 6 variables manquantes en 0.7.0 ; MCP en `.env.example:102-125` + `docs/mcp-server.md:40-46` |

### Gates statiques executes localement (head 02adc68, lecture seule)

| Gate | Commande | Resultat |
|------|----------|----------|
| Lint backend | `.venv/bin/ruff check .` (ruff 0.15.14) | « All checks passed! », exit 0 |
| Lint backend (version CI) | `uvx ruff@0.16.4 check .` (version de `uv.lock:3200-3201`) | « All checks passed! », exit 0 |
| Format backend | `ruff format --check .` (0.15.14 et 0.16.4) | « 196 files already formatted », exit 0 |
| Lockfile | `uv lock --check` (uv 0.8.4) | « Resolved 180 packages », exit 0 |
| Lint frontend | `npx eslint src/` (eslint 9.39.4) | exit 0, 0 warning |
| Format frontend | `npx prettier --check src/` (prettier 3.8.1) | « All matched files use Prettier code style! » |
| Type-check | `npx vue-tsc --noEmit` | exit 0 |
| Build frontend | `npx vite build --outDir <scratchpad>` (sortie hors `frontend/dist/`) | « built in 2.09s », exit 0 |
| Docs | `mkdocs build --strict -d <scratchpad>/site` (mkdocs 1.6.1, material 9.8.0, comme `docs.yml`) | exit 0 |

### Etat GitHub Actions au moment de l'audit

| Run | Cible | Resultat |
|-----|-------|----------|
| Release Gate 41452005966 | PR #366 `release/0.7.3` -> `main` @ 02adc68 | **failure** : `Security scan — remote` failure, `Security scan — local` cancelled ; les 10 autres jobs success |
| CI 41452006012 | PR #366 @ 02adc68 | success (Backend, Frontend, E2E API ; E2E UI skipped car reserve a `main`) |
| CI (checks PR #328) | head 3f1bcb4 | success (E2E UI skipped) |
| Push sur `release/0.7.3` | 02adc68 et anterieurs | seul `Auto-close issues` tourne (success) |

---

## Ecarts constates

### [CRIT] Release Gate rouge sur 02adc68 : scan Trivy CRITICAL en echec, suppressions `.trivyignore.yaml` expirees

> **Vérification de l'orchestrateur (2026-11-02, artefacts `trivy-remote` / `trivy-local` du run `41452005966`)** :
> la cause de l'échec n'est pas celle supposée ci-dessous. Le scan CRITICAL remonte des paquets **corrigeables** :
> PyJWT 2.13.0 (CVE-2026-102268, fix 2.14.0), certifi 2026.7.22 (GHSA-6q48-6c7w-9gw2), Pillow 10.4.0
> (CVE-2026-112393, -112398, -112403, -112900, fix 13.0.0), le paquet `uv` 0.11.6 (GHSA-hq85-5cpj-mr62) et le
> crate `zip` 8.1.0 embarqué dans `/usr/local/bin/uv` et `uvx` (CVE-2026-115905). Côté OS, seule
> CVE-2026-6653 (libxml2, image `local`) réapparaît. Les autres suppressions expirées ne sont plus
> détectées, car Debian a publié les correctifs. Le constat CRIT et le score restent inchangés.

- **Localisation** : `.github/workflows/release-gate.yml:352-366` (step `Run Trivy — CRITICAL (blocking)`), `.trivyignore.yaml:25`, `:40`, `:52`, `:67`, `:81` (dates `expired_at` depassees)
- **Constat** :
  - Run 41452005966 (PR #366, head 02adc68) : le job `Security scan — remote` sort en `exit code 1` sur le step CRITICAL (Trivy v0.71.0, Debian 13.7, 167 paquets OS + paquets Python). `Security scan — local` est `cancelled` par le fail-fast de la matrice, son resultat est donc inconnu. Le job `Release summary` publie « Release Gate — NO-GO » sur la PR, avec `Image security scan` comme seul check rouge.
  - A la date de l'audit (2026-11-02), 5 des 7 suppressions de `.trivyignore.yaml` sont expirees, et Trivy les ignore donc plus :

    | CVE | Paquet | `expired_at` | Ligne |
    |-----|--------|--------------|-------|
    | CVE-2026-7598 | libssh2 (base slim) | 2026-08-31 | `.trivyignore.yaml:25` |
    | CVE-2026-42496 | perl-base | 2026-09-30 | `.trivyignore.yaml:40` |
    | CVE-2026-8376 | perl-base | 2026-09-30 | `.trivyignore.yaml:52` |
    | CVE-2026-58016 | libglib2.0 (`local`) | 2026-10-31 | `.trivyignore.yaml:67` |
    | CVE-2026-6653 | libxml2 (`local`) | 2026-10-31 | `.trivyignore.yaml:81` |
    | CVE-2026-40393 | mesa (`local`) | 2026-11-30 (expire dans 28 jours) | `.trivyignore.yaml:13` |
    | CVE-2026-13221 | perl-base | 2026-11-30 (expire dans 28 jours) | `.trivyignore.yaml:93` |

    Pour l'image `remote` (sans libgl1 ni libglib), 3 des 4 suppressions qui la concernent (libssh2 et deux perl) sont expirees. C'est la cause la plus probable de l'echec, mais pas la seule possible : Trivy scanne aussi les paquets Python, et `pip-audit` remonte des vulnerabilites connues sur les dependances principales (cf. [INFO] dep-audit). La table exacte n'apparait pas dans les logs. Elle est dans l'artefact `trivy-remote` du run, que cet audit n'a pas telecharge.
  - Le mecanisme d'expiration a fonctionne comme prevu (forcer la reevaluation). Mais aucune reevaluation n'a eu lieu depuis le 2026-08-24, et le fix racine #189 (opencv-headless) n'est toujours pas livre.
- **Regle violee** : item 10.1.1 — « Toutes les GitHub Actions passent sur la branche de release » (poids 3).
- **Remediation** :
  1. Recuperer les artefacts `trivy-remote` / `trivy-local` du run 41452005966. Pour chaque CVE CRITICAL, verifier si Debian 13 a publie un backport : `python:3.12-slim` est une etiquette flottante, donc un rebuild peut suffire.
  2. Pour celles qui restent sans correctif et ne sont pas atteignables : renouveler la suppression avec une justification datee et une expiration courte. Livrer #189 pour supprimer libgl1/libglib.
  3. Ajouter `fail-fast: false` a la matrice `image-scan` (cf. [INFO] fail-fast) pour obtenir le verdict `local` dans le meme run.
  4. Relancer le Release Gate sur PR #366 et obtenir un vert complet avant le tag.

### [MAJ] La variante `local` publiee (reasoning + modeles, multi-arch) n'est ni construite ni scannee par le gate

- **Localisation** : `.github/workflows/release-gate.yml:243-252` (build du gate, `build-args: APP_VERSION=...` seulement, ligne 250), contre `.github/workflows/release.yml:55` et `:70-73` (build publie)
- **Constat** :
  - Le gate construit `--target local` avec les valeurs par defaut du `Dockerfile` (`BAKE_MODELS=false` `Dockerfile:84`, `WITH_REASONING=false` `Dockerfile:88`), en `linux/amd64` seulement. `release.yml` publie `latest-local` / `X.Y.Z-local` avec `WITH_REASONING=true`, `BAKE_MODELS=true`, sur `linux/amd64,linux/arm64`. L'image que les utilisateurs tirent n'est donc construite pour la premiere fois qu'apres le push du tag. Un echec de `uv sync --group local --group reasoning` (`Dockerfile:100-101`), du telechargement des modeles ou du build arm64 n'apparait qu'au moment de publier.
  - Ecart de contenu mesure via `uv export --frozen` : le groupe `reasoning` ajoute 20 paquets absents de l'image du gate : `docling-agent`, `mellea`, `openai`, `ollama`, `boto3`, `botocore`, `s3transfer`, `jmespath`, `nltk`, `joblib`, `pyarrow`, `fastparquet`, `cramjam`, `absl-py`, `rouge-score`, `math-verify`, `latex2sympy2-extended`, `mistletoe`, `jiter`, `sniffio`. Ils ne passent ni par Trivy (seule l'image du gate est scannee, `release-gate.yml:352-380`), ni par `pip-audit` : le job `dep-audit` ne synchronise que les dependances principales et `dev` (`release-gate.yml:124`, `uv sync --frozen` sans `--group local --group reasoning`). Le groupe `local` (docling, torch...) n'est pas non plus audite par `pip-audit`.
  - Consequence sur la mesure de taille : le gate rapporte `local: 1856MB` (taille non compressee de son image sans reasoning ni modeles, run 41452005966). L'image `0.7.2-local` publiee pese deja 1 870 Mo **compresses** pour la seule plateforme amd64 (somme des couches du manifest GHCR). Le chiffre affiche sur la PR ne decrit donc pas l'artefact livre.
  - Cet ecart date du hotfix 0.7.1 (`e95680a`, `WITH_REASONING` ajoute a `release.yml`). Le gate n'a pas suivi. La couverture reasoning du gate est nulle.
- **Regle violee** : item 10.2.3 — « Les deux variantes (local/remote) buildent correctement » (poids 2). La variante `local` telle qu'elle est publiee n'est pas verifiee.
- **Remediation** : aligner le job `docker-build` du gate sur `release.yml` pour la cible `local`, au minimum `WITH_REASONING=true`. Ce flag ne touche que PyPI, pas HuggingFace, donc il respecte la politique HF-free. `BAKE_MODELS` peut rester `false` en le documentant. Scanner cette image dans `image-scan`. Ajouter `--group local --group reasoning` a l'installation du job `dep-audit`. Optionnel : un build `linux/arm64` sans `load` (buildx + QEMU) pour valider la plateforme publiee.

### [MIN] Contexte de build `frontend/` toujours sans `.dockerignore` ; `__pycache__` imbriques non exclus

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .`), absence de `frontend/.dockerignore` ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7`
- **Constat** :
  - Ecart 0.7.0 inchange. Le service `frontend` du compose (`docker-compose.yml:202-204`, `context: ./frontend`) envoie `frontend/node_modules/` (121 Mo sur le poste de l'auditeur) et `frontend/dist/` (2 Mo) au daemon. Le `COPY . .` ecrase le `node_modules` installe par `npm ci` (`frontend/Dockerfile:5`) avec celui de l'hote (binaires macOS dans un stage Alpine). L'image finale `nginx:alpine` reste propre.
  - Nouveau detail : dans `.dockerignore`, les motifs sont ancres a la racine du contexte. `document-parser/__pycache__/` et `document-parser/*.pyc` (`.dockerignore:33-34`), comme `__pycache__/` et `*.pyc` (`document-parser/.dockerignore:6-7`), n'excluent que le niveau superieur. Il faudrait `**/__pycache__`. Le poste de l'auditeur compte 15 repertoires `__pycache__` sous `document-parser/` (dont `mcp_adapter/__pycache__`, `infra/__pycache__`). Sur un `docker build` local, 14 d'entre eux partent dans l'image via `COPY document-parser/ .` (`Dockerfile:43`). La CI n'est pas touchee (checkout propre).
- **Regle violee** : item 10.2.4 — « Pas de fichier inutile dans l'image (node_modules frontend, .venv, .git) — `.dockerignore` est a jour » (poids 1).
- **Remediation** : creer `frontend/.dockerignore` (`node_modules/`, `dist/`, `*.log`, `.DS_Store`). Remplacer les motifs Python par `**/__pycache__/` et `**/*.pyc` dans les deux `.dockerignore`.

---

### [INFO] Le job `Dependency audit` ne peut jamais bloquer sur Python : 129 vulnerabilites connues, job vert

- **Localisation** : `.github/workflows/release-gate.yml:135-141`, `:718-734`, `:769`
- **Constat** : la detection « critical » teste `'CRITICAL' in v.get('fix_versions', [''])` (ligne 139). `fix_versions` est une liste de numeros de version, et la sortie JSON de `pip-audit` ne porte pas de severite : la condition est toujours fausse. Dans le run 41452005966, `pip-audit` rapporte « Found 129 known vulnerabilities in 12 packages », et le job est `success`. Parmi elles, la nouvelle dependance MCP : `mcp 2.1.1` porte CVE-2026-59951, CVE-2026-116684, CVE-2026-116685 et CVE-2026-116686, toutes corrigees en 2.2.0 (`pyproject.toml:24` autorise `<3.0.0`). Suivent `pillow 10.4.0` (66 vulnerabilites, borne `<11.0.0` en `pyproject.toml:14`), `cryptography 45.0.7` (borne `<46.0.0`, `pyproject.toml:20`), `pyjwt`, `aiohttp`, `urllib3`... Par ailleurs, le tableau du commentaire PR affiche `Dependency audit | Yes (CRITICAL)` et `Audit checks | Yes` (lignes 769-770), alors que la logique de verdict les traite en non bloquants (« GO CONDITIONAL », lignes 728-730). Le bilan positif 0.7.0 « Audit deps (`pip-audit` + `npm audit`) blocant sur les CRITICAL » etait donc faux pour la moitie Python. Recoupe l'audit 08.
- **Remediation** : passer par un outil qui expose la severite (`pip-audit` + OSV, ou `trivy fs` sur `uv.lock`), ou bloquer sur tout correctif disponible. Monter `mcp` a `>=2.2.0`. Aligner le libelle du commentaire sur la logique reelle.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert : le script n'existe pas dans le depot

- **Localisation** : `.github/workflows/release-gate.yml:187-191`, `:755-757` ; `.gitignore:50-51`
- **Constat** : `profiles/` est gitignore depuis `5f8b355` (2026-04-13, « gitignore profiles/ (internal audit tooling) »). Le runner n'a donc jamais le script. Log du run 41452005966 : `bash: profiles/fastapi-vue/commands.sh: No such file or directory`. Le step tourne avec `shell: /usr/bin/bash -e {0}`, sans `pipefail` : le `| tee` masque l'exit 127 et le job sort `success`. Le meme log apparait dans le gate 0.7.1 (job 97488023182). Le commentaire PR affiche en plus un tableau casse (`0` puis `?` dans chaque cellule), parce que `grep -c ... || echo "?"` imprime les deux valeurs.
- **Remediation** : versionner le script, ou supprimer le job et sa ligne du resume. A minima, `set -o pipefail` et un test `[ -f ... ] || exit 1`.

### [INFO] `Image size check` ne compare jamais rien (nom d'image en majuscules)

- **Localisation** : `.github/workflows/release-gate.yml:15` (`IMAGE_NAME: ${{ github.repository }}`), `:436`
- **Constat** : `github.repository` vaut `scub-france/docling-Studio`. La reference construite ligne 436 contient une majuscule, que Docker refuse. Log du run 41452005966 : `Could not pull ghcr.io/scub-france/docling-Studio:0.7.2-remote — skipping remote delta` (idem `-local`), puis « no previous baseline ». Le meme echec apparait des le gate 0.7.1 (avec v0.6.2). `release.yml` n'est pas concerne : `docker/metadata-action` met le nom en minuscules. S'y ajoute le probleme de perimetre decrit dans [MAJ] : l'image `local` mesuree n'est pas l'image publiee.
- **Remediation** : `IMAGE="${REGISTRY}/${IMAGE_NAME,,}:..."` (minuscules bash). Comparer `remote` a `remote`, et `local` a l'image `local` construite avec les memes build-args que la release.

### [INFO] Matrices en fail-fast : le scan `local` est annule des que `remote` echoue

- **Localisation** : `.github/workflows/release-gate.yml:226-228` (`docker-build`), `:336-338` (`image-scan`), `.github/workflows/release.yml:21-23`
- **Constat** : aucune matrice ne pose `fail-fast: false`. Dans le run 41452005966, `Security scan — local` est `cancelled` apres l'echec de `remote` : on ignore si l'image `local`, qui porte deux suppressions expirees de plus (glib, libxml2), passerait. Dans `release.yml`, l'echec d'une cible annule l'autre, ce qui peut publier une release partielle (une seule variante poussee).
- **Remediation** : ajouter `strategy.fail-fast: false` aux trois matrices.

### [INFO] Les nouveautes 0.7.3 ne sont pas exercees de bout en bout par le gate ; la route nginx `/mcp` n'est jamais appelee en CI

- **Localisation** : `.github/workflows/release-gate.yml:640-645` (`--tags @critical`), `.github/workflows/ci.yml:156-158` (E2E UI reserve a `main`) ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:1` (`@ui @regression`)
- **Constat** : 10 features UI ont ete ajoutees ou modifiees depuis 0.7.2 (`git diff caddf30..HEAD -- e2e/`), et aucune n'est `@critical`. 7 portent `@regression` : `mcp-config`, `docs-batch-analysis`, `analysis-detail`, `analysis-parse-show-all`, `analysis-parse-hide-boxes`, `doc-viewer`, `doc-new-analysis-opens-analysis`. 2 portent `@ui` seul : `settings-accordion`, `reasoning-feature-flag`. 1 porte `@demo`. Le gate ne lance que les 6 features `@critical`. Aucune feature API ne cible `POST /mcp` ni la configuration MCP, et l'import Docling (#359) n'a pas de feature e2e. Ce qui est couvert : le demarrage avec MCP active par defaut (le smoke test boote `remote` avec `MCP_ENABLED` implicite a `true`), les tests unitaires MCP (`tests/test_mcp_mount.py`, `tests/test_mcp_stdio.py`...), et le batch cote API (`e2e/api/.../batch-progress.feature`, `@regression`, lance par `e2e-api`). Recoupe l'audit 09.
- **Remediation** : taguer `@critical` au moins `mcp-config.feature` et `docs-batch-analysis.feature`. Ajouter une feature API Karate qui envoie un `initialize` JSON-RPC sur `/mcp` via nginx (port 3000), pour valider le routage et l'allow-list `Host`.

### [INFO] Declencheurs : la CI ne garde ni les push sur `release/**`, ni le formatting, ni la doc ; le gate est contournable

- **Localisation** : `.github/workflows/ci.yml:3-7`, `:68-72` ; `.github/workflows/release-gate.yml:3-6`, `:49-56` ; `.github/workflows/docs.yml:3-9`
- **Constat** :
  - `ci.yml` ne se declenche pas sur les push directs vers `release/**` (ecart 0.7.0 inchange). `gh run list --branch release/0.7.3` ne montre que `Auto-close issues` pour les push.
  - Le formatting n'est verifie nulle part en CI : ni `ruff format --check` ni `prettier --check` dans `ci.yml:68-72` ou `release-gate.yml:49-56`. Le code est conforme aujourd'hui (10.1.5), mais rien ne garde cette conformite.
  - `docs.yml` ne tourne que sur push `main`. `mkdocs build --strict` n'est jamais execute sur une PR, alors que 0.7.3 reecrit la nav (`mkdocs.yml`, 80 lignes modifiees). Le build passe localement.
  - Le Release Gate n'est declenche que par une PR vers `main` (`release-gate.yml:3-6`). v0.7.2 a ete poussee directement sur `main` (`caddf30`, aucune PR de release) et publiee par `release.yml` (run 35725811239), sans aucun run du gate entre le 2026-08-24 et le 2026-11-02.
- **Remediation** : ajouter `push: branches: ['release/**']` a `ci.yml`. Ajouter les deux checks de format aux jobs lint. Ajouter `pull_request` (chemins `docs/**`, `mkdocs.yml`) a `docs.yml` en build seul. Proteger `main` (PR obligatoire, check `Release summary` requis).

### [INFO] Durcissement Docker inchange : pas de `HEALTHCHECK`, image racine sans `USER`

- **Localisation** : `Dockerfile:52-63`, `document-parser/Dockerfile`, `frontend/Dockerfile` ; `docker-compose.yml:141-199` (`document-parser`), `:202-210` (`frontend`)
- **Constat** : ecarts 0.7.0 inchanges. Aucun `HEALTHCHECK` dans les trois Dockerfiles. Les deux services applicatifs du compose n'ont pas de bloc `healthcheck`, donc `--wait` ne les attend pas reellement ; les boucles `curl` (`ci.yml:116-128`, `release-gate.yml:538-550`) compensent. L'image racine cree `appuser` (`Dockerfile:52`) sans jamais poser `USER` : nginx et le PID 1 tournent en root, `uvicorn` redescend via `su` (`Dockerfile:63`).
- **Remediation** : `HEALTHCHECK` curl `/api/health` dans le `Dockerfile` racine et bloc `healthcheck` sur `document-parser`. Documenter ou reduire l'execution en root.

### [INFO] Images de base : Node 20 en fin de vie dans les etages de build, etiquettes flottantes

- **Localisation** : `Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:173` (`node:20-alpine`) ; `Dockerfile:22`, `document-parser/Dockerfile:11` (`python:3.12-slim`) ; `frontend/Dockerfile:9` (`nginx:alpine`)
- **Constat** : le bundle publie est construit avec Node 20, en fin de vie depuis le 2026-04-30. La CI teste et build avec Node 22 (`ci.yml:61`, `release-gate.yml:39`), donc l'artefact livre ne sort pas de la toolchain testee. Les runners signalent aussi « Node.js 20 is deprecated » pour `actions/checkout@v4.3.1`, `upload-artifact@v4.6.2`... Aucune image de base n'est epinglee par digest : le passage silencieux a Debian 13.7 sous `python:3.12-slim` change la surface Trivy d'un run a l'autre. A l'inverse, Docling Serve est bien epingle (`docker-compose.yml:112`, `docker-compose.dev.yml:104`, `v1.37.0`).
- **Remediation** : passer les etages de build a `node:22-alpine`, aligne sur la CI. Epingler `python:3.12-slim` / `nginx:alpine` par digest (Renovate/Dependabot pour les bumps).

---

## Delta vs 0.7.0

Score : 85 -> 70 (-15). Items conformes : 8/11 -> 8/11, mais pas les memes.

| Ecart baseline 0.7.0 | Statut 0.7.3 | Detail |
|----------------------|--------------|--------|
| [MIN] Derive Prettier (2 fichiers), formatting non gate par la CI | **Corrige en partie** | Code conforme (`prettier --check src/` et `ruff format --check .` verts) : 10.1.5 repasse **Oui**. La CI ne verifie toujours pas le format (rattache a [INFO] Declencheurs). |
| [MIN] `frontend/` sans `.dockerignore` | **Toujours present** | Inchange, aggrave par les motifs `__pycache__` non recursifs ([MIN]). |
| [MIN] 8 variables compose absentes de `.env.example` | **Corrige** | `.env.example:1-5` assume renvoyer a `docs/configuration.md`, qui documente `RATE_LIMIT_RPM` (l.31), `RAG_PIPELINE_ENABLED` (l.52), `STUDIO_MODE_ENABLED` (l.53), `WITH_REASONING` (l.130), `BAKE_MODELS` (l.131), `BATCH_PAGE_SIZE`. Les variables MCP sont documentees (`.env.example:102-125`, `docs/mcp-server.md:40-46`). Restent `EMBEDDING_BATCH_SIZE` / `BAKE_MODEL`, propres a l'ingestion, depreciee (hors perimetre). 10.3.2 repasse **Oui**. |
| [INFO] `ci.yml` sans push `release/**` | **Toujours present** | `ci.yml:3-7` inchange. |
| [INFO] Aucun `HEALTHCHECK` / services compose sans healthcheck | **Toujours present** | Inchange. |
| [INFO] Image racine sans `USER` | **Toujours present** | `Dockerfile` racine inchange depuis juin. |
| Item 10.1.1 (Oui en 0.7.0) | **Regresse -> [CRIT]** | Release Gate rouge : suppressions Trivy expirees. |
| Item 10.2.3 (Oui en 0.7.0) | **Regresse -> [MAJ]** | `release.yml` publie `local` avec `WITH_REASONING=true` depuis 0.7.1, et le gate n'a pas suivi. |

Points de l'enonce verifies :
- Couverture reasoning nulle dans le gate : **confirme** ([MAJ]).
- `Security scan — local` masque par `remote` : **confirme**. Le mecanisme exact est le fail-fast : `local` est annule quand `remote` echoue ([INFO]).
- Suppressions Trivy expirees : **pire que prevu**. 5 entrees expirees sur 7 (pas une seule), et les 2 restantes expirent le 2026-11-30.
- Taille d'image trompeuse : **confirme**. Le « 1850 MB » est la taille non compressee de l'image `local` du gate (1856 Mo en 0.7.3), sans reasoning ni modeles. L'image publiee `0.7.2-local` fait deja 1 870 Mo compresses en amd64. En plus, le delta ne fonctionne pas (majuscules).
- `ci.yml` limite aux PR : **confirme**.

Deux points positifs du rapport 0.7.0 sont revises : le blocage `pip-audit` sur CRITICAL ne fonctionne pas, et la comparaison de taille n'a jamais tourne.

---

## Points positifs

- **Gates statiques verts au head** et a la version verrouillee : ruff 0.16.4 (lint + format, 196 fichiers), eslint sans warning, prettier conforme, vue-tsc exit 0, build Vite OK, `uv lock --check` OK, `mkdocs build --strict` OK. La derive Prettier de 0.7.0 est resorbee.
- **CI verte sur la PR de release** (run 41452006012) : tests backend et frontend, build compose `remote`, E2E API. Le Release Gate est vert sur 10 jobs sur 12 : lint, tests unitaires, build des deux cibles, smoke `/api/health`, E2E API full scope, E2E UI `@critical`.
- **Serveur MCP correctement empaquete** : `mcp>=2.1.1,<3.0.0` en dependance principale (`pyproject.toml:24`), verrouille a 2.1.1 (`uv.lock:1683-1684`), installe dans l'etage commun des deux Dockerfiles (`Dockerfile:40`, `document-parser/Dockerfile:24`). `mcp_adapter/` (cartes HTML comprises) et `mcp_stdio.py` sont copies par `COPY document-parser/ .` (`Dockerfile:43`) sans etre exclus par `.dockerignore`. Le smoke test boote avec MCP actif par defaut, donc le chemin de montage est valide au demarrage.
- **Route `/mcp` coherente sur les trois points d'entree** : nginx single-image (`nginx.conf.template:29-38`), nginx compose (`frontend/nginx.conf.template:29-38`), proxy Vite dev (`frontend/vite.config.js:37-40`). La correspondance exacte `location = /mcp` suit le choix backend d'une route ajoutee au routeur plutot qu'un `mount` qui redirigerait en 307 (`document-parser/bootstrap/mcp_mount.py:25-27`). `proxy_buffering off` sert le streaming, et `Host $http_host` preserve le port pour l'allow-list.
- **Defaut MCP du Space HF bien traite** : `MCP_ENABLED` vaut `false` quand `DEPLOYMENT_MODE=huggingface` (`document-parser/infra/settings.py:255-258`), avec des tests (`tests/test_settings.py:199-207`) et une case dans la checklist de deploiement (`docs/release/deployment-checklist.md:55`). Defense en profondeur si la variable est oubliee : l'allow-list par defaut `127.0.0.1:*,localhost:*,[::1]:*` rejette un `Host` `*.hf.space`.
- **Docling Serve epingle** a `v1.37.0` dans les deux compose (`docker-compose.yml:112`, `docker-compose.dev.yml:104`) : E2E reproductibles, sans dependance HuggingFace sur les runners.
- **Le scan Trivy bloque reellement** sur CRITICAL, et l'expiration datee des suppressions a joue son role d'alarme : la release ne peut pas partir avec des suppressions perimees.
- **Documentation des variables d'environnement** desormais complete et honnete (`.env.example:1-5` dit explicitement quelles variables le compose transmet).

---

## Verdict partiel : NO-GO

Un ecart CRITICAL : le Release Gate est rouge sur 02adc68 (scan Trivy CRITICAL de l'image `remote` en echec, avec 5 suppressions `.trivyignore.yaml` sur 7 expirees ; scan `local` annule). Selon la regle absolue, le verdict est NO-GO quel que soit le score (70/100). S'y ajoutent un MAJOR (la variante `local` publiee, avec reasoning, modeles et arm64, n'est ni construite ni scannee avant le tag), un MINOR (`.dockerignore` frontend et `__pycache__` imbriques) et 8 INFO. Parmi ces INFO, trois sont des faux verts du gate a corriger rapidement : `pip-audit` qui ne bloque jamais (dont 4 CVE sur `mcp 2.1.1`), `Audit checks` sans script, comparaison de taille inoperante.

Conditions de levee : reevaluer et traiter les CVE CRITICAL (backport Debian, renouvellement justifie ou #189), passer les matrices en `fail-fast: false`, relancer le Release Gate sur PR #366 jusqu'au vert complet. Le MAJ releve d'un plan de remediation : aligner le build `local` du gate sur `release.yml` et etendre `pip-audit` aux groupes `local` et `reasoning`.

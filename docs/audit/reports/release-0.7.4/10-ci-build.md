# Rapport d'audit : CI / Build

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Branche** : `fix/0.7.4-editor-followups` @ `eade7fa` = `release/0.7.4` @ `2f47f72` + 3 commits locaux non poussés (#391, #392, #393)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Baseline** : re-audit 0.7.3 (`release/0.7.3` @ `e01fd95`, 85/100, Release Gate `41464248455` vert)
**Mode** : lecture statique des workflows, Dockerfiles et fichiers compose ; `gh run list` / `gh run view` en lecture seule. Aucun build, lint, type-check ni conteneur lancé localement (consigne).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 9 / 11 |
| Score | **85 / 100** |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 1 |
| Écarts INFO | 12 |

Poids total de la checklist : 20. Poids non conformes : 10.2.3 (2) + 10.2.4 (1) = 3. `score = 17 / 20 * 100 = 85`.

**Score provisoire.** Deux items conformes reposent sur une preuve indirecte :
- **10.1.1** : tous les workflows lancés pour le contenu de `release/0.7.4` sont verts, mais le Release Gate n'a jamais tourné sur 0.7.4 (il ne se déclenche que sur une PR vers `main`) et la branche auditée n'est pas poussée. Si le gate de la PR de release finit rouge : 10.1.1 en `[CRIT]`, score **70**, **NO-GO**.
- **10.1.5** : aucun job CI ne vérifie le formatage, et l'exécution locale était exclue. Conformité présumée sur la base des hooks pre-commit (`.pre-commit-config.yaml:27-33`, `:59-64`) et du commit `36c9ffc` (« style: apply editor formatters »). Si `ruff format --check` ou `prettier --check` échoue : `[MIN]`, score **80**.

**Delta vs re-audit 0.7.3** : 0 (85 → 85). Le MAJ et le MIN de la baseline sont toujours ouverts. 2 INFO de la baseline sont corrigés (dep-audit) ou corrigés en partie (fail-fast).

### État GitHub Actions (relevé le 2026-11-13)

| Run | Cible | Résultat |
|-----|-------|----------|
| `gh run list --branch release/0.7.4` | 3 runs, tous `Auto-close issues on release branch merge` (push des merges #388, #319, et d'un commit docs) | **success** ×3. C'est le seul workflow qu'un push sur `release/**` déclenche (`ci.yml:3-7`) |
| CI `43253020395` | PR #319 → `release/0.7.4`, tête `3c00d44` (`git diff 3c00d44 2f47f72` vide : arbre identique à `release/0.7.4`) | **success** : `Backend tests` (ruff « All checks passed! », 1369 passed / 19 skipped), `Frontend tests & build` (eslint sans sortie, `vue-tsc --noEmit` OK, 570 tests, `vite build` OK), `E2E API tests (Karate)` (build compose `remote`, santé, 36 + 2 scénarios). `E2E UI tests (Karate UI)` **skipped** (réservé à `main`, `ci.yml:162`) |
| CI `43217842632` | PR #319, tête antérieure `2089b07` | success, même profil |
| Release Gate | — | **Jamais lancé sur le contenu 0.7.4** : déclencheur `pull_request` vers `main` seulement (`release-gate.yml:3-6`). Les runs Release Gate récents (`43107856576`, `43104940301`) concernent la PR #390 (`klcd/feat-colab-auth` → `main`), hors périmètre |
| `fix/0.7.4-editor-followups` | — | **Aucun run** : branche non poussée |

---

## Vérification de la checklist

| # | Item | Poids | Conforme | Preuve | Évolution vs 0.7.3 |
|---|------|-------|----------|--------|--------------------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | Oui (provisoire) | CI `43253020395` verte sur l'arbre `release/0.7.4` ; Auto-close vert ×3. Release Gate non lancé (INFO) | = |
| 10.1.2 | Warnings ESLint résolus | 1 | Oui | Step `npx eslint src/` du run `43253020395` : aucune sortie, exit 0 | = |
| 10.1.3 | Warnings Ruff résolus | 1 | Oui | Step `uv run ruff check .` : « All checks passed! ». Les deux lignes > 100 colonnes (`services/analysis_edit_service.py:245`, `infra/docling_editor.py:327`) relèvent de E501, ignoré par `pyproject.toml:96` | = |
| 10.1.4 | Type-check frontend | 2 | Oui | Step `npm run type-check` (`vue-tsc --noEmit`) vert ; `vite build` vert | = |
| 10.1.5 | Formatting conforme | 1 | Oui (présumé) | Non vérifiable (voir plus haut et INFO format) | = |
| 10.2.1 | `docker compose build` réussit | 3 | Oui | Job `E2E API tests (Karate)` du run `43253020395` : `docker compose --profile remote up -d --wait --build` (`ci.yml:107-108`), donc `document-parser/Dockerfile` (cible `remote`, `docker-compose.yml:142-144`) et `frontend/Dockerfile` (`npm ci` avec les nouvelles devDeps `jsdom`, `@vue/test-utils`, `axe-core`, `playwright-core`) | = |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | Oui | Même job : boucle de santé `ci.yml:120-132` verte. Le smoke de l'image unique (`release-gate.yml:296-330`) n'a pas tourné (INFO) | = |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Non** | Voir MAJ (inchangé) | = |
| 10.2.4 | `.dockerignore` à jour | 1 | **Non** | Voir MIN (inchangé, élargi) | = |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | `nginx.conf.template:13-15` (`/`, fallback SPA), `:17-24` (`/api/`) ; `frontend/nginx.conf.template:13-24`. Fichiers inchangés depuis 0.7.3. Les 6 routes de l'éditeur sont sous `/api/documents/` et `PATCH` passe par `proxy_pass` | = |
| 10.3.2 | Variables d'environnement documentées, défauts cohérents | 1 | Oui | `ANALYSIS_EDITOR_ENABLED` : défaut `true` partout — `infra/settings.py:126`, `:279-280` ; `docker-compose.yml:197` ; `docker-compose.dev.yml:140` ; `.env.example:7-8` ; `docs/configuration.md:22-26`. `DB_PATH` désormais explicite dans compose (`docker-compose.yml:164`), même défaut que `docs/configuration.md:126` | = |

### Changements CI / build depuis 0.7.3 (`git diff 1de1929..HEAD`)

- `ci.yml:92-95`, `:103-105`, `:173-176`, `:189-191` et les deux jobs e2e de `release-gate.yml` (`:519-532`, `:596-614`) : la génération des PDF e2e passe de `pip install fpdf2 pypdfium2` à `uv run --directory document-parser --group ci`, avec un nouveau groupe `ci` épinglé (`document-parser/pyproject.toml:35-37`) et verrouillé (`uv.lock` : `fpdf2`, `fonttools`). Le groupe n'est pas installé dans les images (`--no-dev` sans `--group ci`, `Dockerfile:42`).
- `.pre-commit-config.yaml:11-13` : `check-yaml` exclut `mkdocs.yml` (tag Python Pymdownx). Le build MkDocs reste le garde-fou.
- `orca.yaml` (nouveau, outillage de worktree) appelle `.development_scripts/worktree_setup.sh`, présent et versionné. Hors images (non copié par les Dockerfiles).
- Nouvelles devDeps frontend : présentes uniquement dans l'étage de build Node, jamais dans l'image nginx ni dans l'image unique (`Dockerfile:48` ne copie que `dist`).

---

## Écarts constatés

### [MAJ] La variante `local` publiée (reasoning + modèles, multi-arch) n'est ni construite ni scannée par le gate — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:245-252` (`build-args: APP_VERSION=...` seulement, ligne 252), contre `.github/workflows/release.yml:55` (`linux/amd64,linux/arm64`) et `:70-73` (`BAKE_MODELS`, `WITH_REASONING` à `true` pour `local`) ; `Dockerfile:86`, `:90`, `:103-105` ; `release-gate.yml:124` (`uv sync --frozen` sans `--group local --group reasoning`)
- **Constat** : aucun de ces fichiers n'a changé depuis le re-audit 0.7.3 (hors décalage de lignes). Le gate construit toujours `local` sans reasoning ni modèles, en amd64 seul ; `release.yml` publie l'inverse. Les paquets du groupe `reasoning` ne passent ni par Trivy ni par `pip-audit` avant le tag.
- **Règle violée** : item 10.2.3 (poids 2).
- **Remédiation** : inchangée. `WITH_REASONING=true` au build `local` du gate et scan de cette image ; `--group local --group reasoning` au `uv sync` du job `dep-audit` ; en option un build `linux/arm64` sans `load`. Effort M.

### [MIN] Contexte de build `frontend/` sans `.dockerignore` ; `__pycache__` imbriqués non exclus ; `out/` absent — inchangé, élargi

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .`), absence de `frontend/.dockerignore`, `docker-compose.yml:205-206` ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7`
- **Constat** :
  - Inchangé : `node_modules/` et `dist/` de l'hôte partent dans le contexte et dans l'étage de build du frontend compose (`COPY . .` après `npm ci`, ce qui peut écraser les modules installés). Les motifs `__pycache__/` et `*.pyc` ne couvrent que le premier niveau.
  - Nouveau : les scripts d'enregistrement de démo (`frontend/scripts/record-analysis-editor*.mjs`) écrivent dans `out/demo/` à la racine (13 Mo aujourd'hui). `out/` est ignoré par git (`.gitignore:65`) mais pas par `.dockerignore` : il part dans le contexte de l'image unique. Il n'est pas copié dans l'image (`COPY` ciblés), l'effet se limite au temps de build.
- **Règle violée** : item 10.2.4 (poids 1).
- **Remédiation** : créer `frontend/.dockerignore` (`node_modules/`, `dist/`, `*.log`, `.DS_Store`), passer à `**/__pycache__/` et `**/*.pyc`, ajouter `out/` à `.dockerignore`. Effort S.

---

### [INFO] Le Release Gate n'a jamais tourné sur 0.7.4, et la branche auditée n'est pas poussée

- **Localisation** : `.github/workflows/release-gate.yml:3-6` ; `.github/workflows/ci.yml:3-7`
- **Constat** : le gate (Trivy CRITICAL bloquant, image unique `remote` et `local`, smoke `/api/health`, e2e API complète, e2e UI `@critical`) ne part qu'avec la PR `release/0.7.4` → `main`. Aucune preuve n'existe donc encore pour : l'image unique (`Dockerfile`, étage Node 20 avec les nouvelles devDeps), le scan Trivy de la nouvelle `uv.lock`, le smoke de l'image. Les 3 commits correctifs n'ont aucun run. L'issue #377 (« Run CI and the Release Gate on 0.7.4 before the tag ») est ouverte.
- **Remédiation** : pousser `fix/0.7.4-editor-followups`, PR vers `release/0.7.4` (CI), puis ouvrir la PR de release vers `main` et attendre un gate vert avant le tag. Effort S.

### [INFO] Le formatage n'est vérifié par aucun job CI — inchangé

- **Localisation** : `.github/workflows/ci.yml:43-47`, `:68-78` ; `.github/workflows/release-gate.yml:49-56` ; `.pre-commit-config.yaml:27-33`, `:59-64`
- **Constat** : ni `ruff format --check` ni `prettier --check` dans la CI ou le gate. Seuls les hooks pre-commit (`ruff format .`, `npm run format`) le font, côté poste du contributeur. L'item 10.1.5 n'a donc aucune preuve automatique ; le re-audit 0.7.3 l'avait vérifié localement, ce qui était exclu ici.
- **Remédiation** : ajouter `uv run ruff format --check .` et `npx prettier --check src/` au job `lint-typecheck` du gate et à `ci.yml`. Effort S.

### [INFO] [NOUVEAU] Le job `Unit tests` du Release Gate ne peut pas échouer sur un test rouge

- **Localisation** : `.github/workflows/release-gate.yml:82-86`, `:88-92`
- **Constat** : `uv run pytest ... 2>&1 | tee /tmp/backend-tests.txt` et `npm run test:run 2>&1 | tee ...` tournent sous le shell par défaut de GitHub Actions, `bash -e {0}` sans `pipefail` (visible dans les logs : « shell: /usr/bin/bash -e {0} »). Le code de sortie du step est celui de `tee`, toujours 0. C'est le même mécanisme que le faux vert `Audit checks` (INFO suivante). Préexistant en 0.7.3, non relevé jusqu'ici. Atténuation : les jobs `Backend tests` / `Frontend tests & build` de `ci.yml:46-47`, `:74-75` tournent sur la même PR sans `tee` et, eux, échouent.
- **Remédiation** : `set -o pipefail` en tête des deux blocs, ou `defaults.run.shell: bash` au niveau du workflow (GitHub ajoute alors `-o pipefail`). Effort S.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:189-193` ; `.gitignore:50-51`
- **Constat** : `profiles/` est ignoré par git et absent du dépôt ; `bash profiles/... | tee` masque l'exit 127.
- **Remédiation** : inchangée. Versionner le script ou supprimer le job et sa ligne du résumé.

### [INFO] `Image size check` ne compare jamais rien (nom d'image en majuscules) — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:441`
- **Remédiation** : inchangée. `${IMAGE_NAME,,}`.

### [INFO] Matrices en fail-fast — corrigé en partie

- **Localisation** : `.github/workflows/release-gate.yml:339-341` (corrigé), `:228-230` ; `.github/workflows/release.yml:21-23`
- **Constat** : `image-scan` a maintenant `fail-fast: false`, avec la raison en commentaire. `docker-build` du gate et la matrice de `release.yml` restent en fail-fast par défaut : un échec du build `remote` annule `local`.
- **Remédiation** : `fail-fast: false` sur les deux matrices restantes. Effort S.

### [INFO] Les nouveautés ne sont pas exercées de bout en bout en CI ; l'éditeur s'ajoute à la liste — inchangé, élargi

- **Localisation** : `.github/workflows/ci.yml:162`, `:228` ; `.github/workflows/release-gate.yml:658` ; `e2e/ui/src/test/resources/analyses/analysis-editor.feature:1`
- **Constat** : la feature UI de l'éditeur (3 scénarios) est taguée `@ui` seulement, la CI ne lance que `@critical`. Aucun scénario e2e API ne touche les routes de l'éditeur. Recoupe l'audit 09 (MAJ 9.1.3 et 9.2.1).
- **Remédiation** : voir audit 09 (#382).

### [INFO] Déclencheurs : pas de CI sur push `release/**` — inchangé

- **Localisation** : `.github/workflows/ci.yml:3-7`
- **Constat** : les deux merges sur `release/0.7.4` n'ont lancé que `Auto-close issues`. La CI ne tourne que via les PR. Un commit poussé directement sur la branche de release (comme le seraient les 3 correctifs s'ils n'étaient pas passés par une PR) n'aurait aucune vérification.
- **Remédiation** : inchangée — ajouter `release/**` à `on.push.branches`.

### [INFO] `uv` reste installé dans les images d'exécution — inchangé

- **Localisation** : `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9`
- **Remédiation** : inchangée (montage du binaire uv au build ou désinstallation dans le même `RUN`).

### [INFO] Suppressions Trivy : échéance commune au 2026-12-31 — inchangé

- **Localisation** : `.trivyignore.yaml:20`, `:38`, `:44`, `:50`, `:56`
- **Constat** : sans conséquence pour 0.7.4 si son gate tourne avant le 31 décembre. Tout run après cette date échouera sur Pillow et libxml2 (#378, ouvert, jalon 0.7.4).
- **Remédiation** : suivre #378.

### [INFO] Durcissement Docker : pas de `HEALTHCHECK`, image unique sans `USER` — inchangé

- **Localisation** : `Dockerfile` (aucune instruction `HEALTHCHECK` ni `USER`), `frontend/Dockerfile`
- **Remédiation** : inchangée.

### [INFO] Images de base et actions sur Node 20 — inchangé

- **Localisation** : `Dockerfile:11`, `frontend/Dockerfile:1` (`node:20-alpine`) ; `.github/workflows/ci.yml:26`, `:59` (`actions/checkout@v4`, `actions/setup-node@v4`)
- **Constat** : le run `43253020395` porte de nouveau l'annotation « Node.js 20 is deprecated ». Les nouvelles devDeps (`jsdom` 26, `playwright-core` 1.56) acceptent encore Node 20, la CI les teste sous Node 22 (`ci.yml:61`) : l'étage de build Docker et la CI n'utilisent pas la même version de Node.
- **Remédiation** : inchangée — `node:22-alpine` dans les deux Dockerfiles, actions à jour.

---

## Delta vs re-audit 0.7.3

| Écart baseline (@ e01fd95) | Statut @ eade7fa | Détail |
|----------------------------|------------------|--------|
| [MAJ] 10.2.3 `local` publiée ni construite ni scannée | **Toujours ouvert** | `release-gate.yml:252`, `:124` inchangés |
| [MIN] 10.2.4 `.dockerignore` | **Toujours ouvert**, élargi | + `out/` des vidéos de démo |
| [INFO] Dependency audit : échec silencieux et libellé | **Corrigé** | `release-gate.yml:143-144` avertit quand `pip-audit` ne produit aucun rapport ; `:782` affiche « npm CRITICAL only » |
| [INFO] fail-fast | **Corrigé en partie** | `image-scan` corrigé (`:339-341`) ; `docker-build` et `release.yml` restent |
| [INFO] `Audit checks` faux vert | Toujours présent | — |
| [INFO] `Image size check` (majuscules) | Toujours présent | — |
| [INFO] Nouveautés hors e2e | Toujours présent, élargi | + éditeur |
| [INFO] Déclencheurs | Toujours présent | Pas de format check, pas de CI sur push `release/**` (format traité en INFO séparée) |
| [INFO] `uv` dans les images | Toujours présent | — |
| [INFO] Pillow : échéance commune | Toujours présent | #378 |
| [INFO] Durcissement Docker | Toujours présent | — |
| [INFO] Node 20 | Toujours présent | — |
| — | **[INFO] nouveau** | Release Gate jamais lancé sur 0.7.4, branche non poussée |
| — | **[INFO] nouveau** | `Unit tests` du gate masqué par `tee` sans `pipefail` (préexistant) |

Score : 85 → 85 (0). Aucune régression introduite par 0.7.4 dans la CI ou les images : les seuls changements de workflow (génération des PDF e2e via `uv --group ci`) sont verts dans le run `43253020395` et suppriment une installation pip non épinglée.

---

## Points positifs

- **CI verte sur l'arbre de `release/0.7.4`** (run `43253020395`) : ruff, eslint sans warning, `vue-tsc`, `vite build`, 1369 tests backend, 570 tests frontend, build compose `remote`, santé, 38 scénarios e2e API.
- **Dépendances de test épinglées et verrouillées** : `fpdf2` passe d'un `pip install` flottant dans quatre jobs à un groupe `ci` dans `pyproject.toml` et `uv.lock`, hors images.
- **Nouvelle variable bien câblée** : `ANALYSIS_EDITOR_ENABLED` a le même défaut (`true`) dans les settings, les deux compose, `.env.example` et la doc ; `/api/health` l'expose et le frontend s'y fie.
- **Les nouvelles devDeps lourdes (`playwright-core`, `jsdom`) n'atteignent aucune image** : elles restent dans l'étage de build Node.
- **Deux INFO de la baseline sont traitées** : `pip-audit` sans rapport est signalé, le libellé du résumé est juste, et le scan Trivy de `local` n'est plus annulé par un échec de `remote`.
- **Routage nginx inchangé et suffisant** pour les nouvelles routes (`/api/` couvre `/api/documents/{id}/analysis-edits*`).

---

## Verdict partiel : GO

85/100, 0 CRITICAL, 1 MAJOR, 1 MINOR → **GO** (≥ 80), sous condition. Le verdict suppose deux preuves encore absentes. (1) Le Release Gate de la PR de release doit finir vert, Trivy compris : 0.7.4 change `uv.lock` et l'étage Node de l'image unique, et le gate n'a jamais tourné sur ce contenu. Sinon 10.1.1 tombe en CRITICAL (70, NO-GO). (2) La branche des correctifs doit passer la CI avant merge. Le MAJ (variante `local` publiée non vérifiée avant le tag) reste au plan de remédiation, comme en 0.7.3. Corrections rapides et sans risque, à faire avant de lancer le gate : `set -o pipefail` sur le job `Unit tests`, `fail-fast: false` sur `docker-build`, `out/` dans `.dockerignore`.

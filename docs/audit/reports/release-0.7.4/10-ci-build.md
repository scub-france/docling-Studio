# Rapport d'audit : CI / Build

**Release** : 0.7.4
**Branche** : `release/0.7.4` @ `1de1929` (= tag `v0.7.3` `2b4ef25` + 2 commits README)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Baseline** : re-audit 0.7.3 `release-0.7.3-reaudit/10-ci-build.md` (`e01fd95`, 85/100, GO, 0 CRIT, 1 MAJ, 1 MIN, 10 INFO) ;
premier audit `release-0.7.3/10-ci-build.md` (`02adc68`, 70/100, NO-GO)

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 9 / 11 |
| Score | **85 / 100** (provisoire, voir 10.1.1) |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 1 |
| Écarts INFO | 13 |

Poids total de la checklist : 3+1+1+2+1 (10.1) + 3+3+2+1 (10.2) + 2+1 (10.3) = **20**.
Poids non conformes : 10.2.3 (2) + 10.2.4 (1) = 3. Poids conformes : 17. `score = 17 / 20 * 100 = 85`.

**Réserve sur 10.1.1** : aucun run de `CI` ni de `Release Gate` n'existe sur `1de1929` (commits en `[skip ci]`, pas encore de PR `release/0.7.4` → `main`). L'item est jugé conforme par équivalence : l'arbre de code est identique à celui validé par le gate 0.7.3 (voir plus bas). Si le Release Gate de la future PR 0.7.4 finit rouge, 10.1.1 tombe : `14 / 20 * 100 = 70`, 1 CRIT, **NO-GO**. Le scan Trivy dépend de la base de vulnérabilités du jour : un rouge reste possible sans changement de code.

**Delta vs re-audit 0.7.3** : 85 → 85 (=). Les mêmes items sont non conformes. Le MAJ et le MIN sont inchangés (3e audit consécutif pour le MAJ). Sur les 10 INFO, 3 sont corrigés en partie par la branche de suivi #368 (fail-fast du scan, rapport pip-audit absent, libellé du résumé, justification Pillow). 3 INFO sont nouveaux.

### Périmètre du différentiel

- `git diff e01fd95..1de1929` (re-audit → HEAD) : 2 fichiers dans le périmètre de la fiche, issus de #368 :
  - `.github/workflows/release-gate.yml` (+7/−2) : `fail-fast: false` sur `image-scan` (`:338-341`), avertissement si `pip-audit` ne produit pas de rapport (`:143-144`), libellé `npm CRITICAL only` (`:774`) ;
  - `.trivyignore.yaml` (+3/−2) : la note Pillow cite le plafond `pillow<11` de Studio (`:22`).
- `git diff 2b4ef25..1de1929` (tag `v0.7.3` → HEAD) : `README.md` et `docs/screenshots/*.gif` seulement. Les deux sont exclus des contextes Docker (`.dockerignore:20` `*.md`, `:47` `docs/`) et ne touchent ni le code ni les tests.
- Le commit `59674be`, validé par le dernier Release Gate, a **le même arbre** que `2b4ef25` (`5ebe87e9…`).

### État GitHub Actions (vérifié via l'API GitHub le 2026-11-03)

| Run | Cible | Résultat |
|-----|-------|----------|
| — | `release/0.7.4` (toutes workflows) | **0 run**. Aucune PR `release/0.7.4` → `main` ouverte, donc pas de Release Gate 0.7.4 |
| Code Quality (CodeQL) 41627217412 | push `main` @ `1de1929` | success |
| CI / Release Gate | push `main` @ `0465e70` et `1de1929` | **non lancés** : les deux messages se terminent par `[skip ci]` |
| CI 41625312396 / Release Gate 41625312292 | PR #369 `hotfix/readme-mcp-gif` @ `c08aff5` | **cancelled**. La PR a été fermée sans merge 3 min après son ouverture. Les commits ont été poussés directement sur `main` |
| **Release Gate 41468347487** | PR #366 @ `59674be` (même arbre que `v0.7.3`) | **success, 13/13 jobs**, 11 min 40 s. `Docker build — local` 5 min (build 2 min 53 s, `docker save` 1 min 29 s), `Security scan — local` 2 min 30 s, E2E 5 min 30 s |
| CI 41477971314 | push `main` @ `2b4ef25` | success, 4/4 (Backend, Frontend, E2E API, E2E UI) |
| Release Docker Images 41478041280 | tag `v0.7.3` | success. Build-push multi-arch : `remote` 14 min 01 s, `local` 18 min 06 s |
| Deploy docs 41477971397 / Docling compat 41481215664 | `main` @ `2b4ef25` | success / success |

**Protection de `main`** (API `repos/…/branches/main`) : 14 checks requis. Ce sont les 11 jobs du gate, sauf `Image size check` et `Release summary`, plus `Backend tests`, `Frontend tests & build` et `E2E API tests (Karate)` de `ci.yml`. `enforcement_level: non_admins` : les administrateurs passent outre, ce que montrent les deux push directs ci-dessus.

### Gates statiques exécutés localement (head `1de1929`, lecture seule)

| Gate | Commande | Résultat |
|------|----------|----------|
| Lint backend | `ruff check .` (ruff 0.16.4 = `uv.lock:3281-3282`) | « All checks passed! » |
| Format backend | `ruff format --check .` | « 196 files already formatted » |
| Lockfile | `uv lock --check` | « Resolved 180 packages » |
| Lint frontend | `npx eslint src/` (9.39.4) | exit 0, aucune sortie |
| Format frontend | `npx prettier --check src/` (3.8.1) | « All matched files use Prettier code style! » |
| Type-check | `npx vue-tsc --noEmit` | exit 0 |
| Workflows | `actionlint` 1.7.12, puis avec `shellcheck` 0.11.0 | 0 erreur ; 2 warnings SC2193 sur `ci.yml:134` (voir INFO Déclencheurs) et 5 remarques de style |
| Compose | `docker compose config -q` sur `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.yml + docker-compose.ingestion.yml --profile ingestion` | exit 0 pour les trois |
| Docs | `mkdocs build --strict` (1.6.1, dans le scratchpad) | exit 0. Le GIF retiré n'est référencé nulle part |
| Audit deps hors gate | `pip-audit --no-deps` sur `uv export` des groupes `local` et `reasoning` (scratchpad) | voir INFO Dependency audit |

Non exécutés, conformément à la consigne : suites de tests complètes et builds Docker.

---

## Vérification des trous connus (`docs/maintainers.md:68`)

| Affirmation de `maintainers.md` | Verdict au 2026-11-03 | Preuve |
|---------------------------------|-----------------------|--------|
| « the unit-test steps pipe into `tee` without `pipefail`, so they cannot fail » | **Toujours vrai** | `release-gate.yml:86` (`uv run pytest … \| tee`) et `:92` (`npm run test:run \| tee`). Aucun `shell:` ni `defaults.run.shell` dans les 6 workflows (grep). Le shell par défaut est donc `bash -e {0}` sans `pipefail`, visible dans les logs du run 41468347487 (`shell: /usr/bin/bash -e {0}`). Seul `tee` donne le code retour |
| « the audit script is not in the repository » | **Toujours vrai** | `release-gate.yml:192` appelle `profiles/fastapi-vue/commands.sh`, ignoré par `.gitignore:50-51`. Log du job 125355048336 : `bash: profiles/fastapi-vue/commands.sh: No such file or directory`, job `success` |
| « the Python audit never reports anything as critical » | **Toujours vrai**, et voulu depuis `eb84d77` | `release-gate.yml:129` (`continue-on-error`), `:143-147` (avertissements seulement), `:177-181` (seul `npm` peut faire échouer le job) |
| « Lint and tests are still enforced by the CI checks required on `main` » | **Vrai, avec une nuance** | `Backend tests` (`ci.yml:44`, `:47`, sans `tee`) et `Frontend tests & build` (`ci.yml:68-78`) sont requis. Mais `enforcement_level: non_admins` : un administrateur pousse sans checks (`0465e70`, `1de1929`) |

## Vérification de la checklist

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **Oui (provisoire)** | Pas de run CI ou gate sur `1de1929` (`[skip ci]`, pas de PR). Gate 41468347487 13/13 et CI 41477971314 4/4 verts sur un arbre identique, CodeQL vert sur `1de1929`. À confirmer par le gate de la PR 0.7.4 |
| 10.1.2 | Warnings ESLint résolus | 1 | Oui | `npx eslint src/` exit 0, sortie vide |
| 10.1.3 | Warnings Ruff résolus | 1 | Oui | ruff 0.16.4 « All checks passed! » |
| 10.1.4 | Type-check frontend | 2 | Oui | `vue-tsc --noEmit` exit 0 ; job `Lint & type-check` vert (41468347487) |
| 10.1.5 | Formatting conforme | 1 | Oui | 196 fichiers formatés ; Prettier conforme. Ce n'est pas vérifié en CI (INFO Déclencheurs) |
| 10.2.1 | `docker compose build` réussit | 3 | Oui | CI 41477971314, `E2E API tests (Karate)` et `E2E UI` : `docker compose --profile remote up -d --wait --build` (`ci.yml:104`) vert. La cible par défaut `local` du compose n'est pas construite en CI (INFO nouveau) |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | Oui | `Docker smoke test` du gate 41468347487 (`release-gate.yml:296-330`, `status=ok`, `engine=remote`) ; boucle de santé `ci.yml:116-128` |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Non** | [MAJ] : `release-gate.yml:252` ≠ `release.yml:55`, `:70-73` |
| 10.2.4 | `.dockerignore` à jour | 1 | **Non** | [MIN] : `frontend/.dockerignore` absent ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7` |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | `nginx.conf.template:13-24`, `:29-38` ; `frontend/nginx.conf.template` identique, au `listen 80` et au backend près |
| 10.3.2 | Variables d'environnement documentées | 1 | Oui | Sur les 25 `${VAR}` de `docker-compose.yml`, 23 sont dans `.env.example` ou `docs/configuration.md` (MCP : `.env.example` et `docs/mcp-server.md`). Seules exceptions : `EMBEDDING_BATCH_SIZE` et `BAKE_MODEL`, propres à l'ingestion dépréciée, comme en 0.7.3 |

---

## Écarts constatés

### [MAJ] La variante `local` publiée (reasoning + modèles, multi-arch) n'est ni construite, ni scannée, ni démarrée avant le tag — inchangé vs 0.7.3

- **Localisation** :
  - `.github/workflows/release-gate.yml:245-254` : build du gate, `build-args: APP_VERSION=…` seul, ligne 252, sans `platforms` ;
  - `.github/workflows/release.yml:55` (`linux/amd64,linux/arm64`) et `:70-73` (`BAKE_MODELS=true`, `WITH_REASONING=true` pour `local`) ;
  - `Dockerfile:86`, `:90` (défauts `false`), `:102-106`, `:108-113` ;
  - `release-gate.yml:124` (`uv sync --frozen` sans `--group local --group reasoning`) ;
  - `release-gate.yml:287-332` (smoke sur `remote` seulement).
- **Constat** :
  - Fichiers inchangés depuis 0.7.3. Le gate construit `--target local` sans reasoning ni modèles, en amd64 seul. `release.yml` publie `X.Y.Z-local` et `latest-local` avec reasoning et modèles, en amd64 et arm64. La première construction de l'image que tirent les utilisateurs a lieu au push du tag.
  - Écart de contenu, re-mesuré (`uv export --frozen`) : le groupe `reasoning` ajoute 20 paquets. Ce sont `docling-agent`, `mellea`, `openai`, `ollama`, `boto3`, `botocore`, `s3transfer`, `jmespath`, `nltk`, `joblib`, `pyarrow`, `fastparquet`, `cramjam`, `absl-py`, `rouge-score`, `math-verify`, `latex2sympy2-extended`, `mistletoe`, `jiter` et `sniffio`. Ils pèsent **67,9 Mo de wheels amd64** et 75,3 Mo arm64 (tailles de `uv.lock`). Ni Trivy ni `pip-audit` ne les voient. `pip-audit` lancé par l'auditeur y trouve CVE-2026-81726 (`nltk` 3.10.3, sans correctif).
  - Le conteneur `local` n'est jamais démarré, ni dans le gate ni après publication. Rien ne vérifie que `docling-agent` et `mellea` s'importent dans l'image publiée. C'est la classe de bug du hotfix 0.7.1 (`/api/reasoning` en 503 faute de paquets).
  - Taille rapportée par le gate : `local: 1835MB` (run 41468347487). C'est la taille non compressée d'une image sans reasoning ni modèles, donc pas celle de l'artefact livré.
  - Effet de bord probable : le gate et `release.yml` écrivent le même scope de cache GHA `local` (`release-gate.yml:253-254`, `release.yml:76-77`), avec des build-args différents. Chacun invalide la couche reasoning de l'autre.
- **Règle violée** : item 10.2.3 (poids 2).
- **Remédiation** : étapes 1 et 2 pour rendre l'item conforme, 3 recommandée, 4 et 5 optionnelles.
  1. **Build `local` aligné (S, 3 lignes)**. Remplacer `release-gate.yml:252` par :
     ```yaml
               build-args: |
                 APP_VERSION=${{ steps.version.outputs.value }}
                 WITH_REASONING=${{ matrix.target == 'local' && 'true' || 'false' }}
     ```
     - Garder `BAKE_MODELS` à `false` (politique sans HuggingFace, `release.yml:56-63`) et le documenter en commentaire. `image-scan` couvre alors les 20 paquets, et le CRITICAL bloque.
     - **Coût estimé** : environ 68 Mo de plus à télécharger et installer. Comme le code est copié avant les dépendances `local` (INFO cache), rien de ce surcoût n'est mis en cache. Compter +45 s à 1 min 30 s sur `Docker build — local` (5 min aujourd'hui) et environ +20 s sur `Security scan — local`. Ce job est sur le chemin critique (`docker-smoke` attend les deux builds) : gate d'environ 11 min 40 s à environ 12 min 30 s – 13 min.
     - Le `APP_VERSION` du gate (tiré de `release/0.7.4`) et celui du tag valent tous deux `0.7.4`. Une fois les build-args alignés, `release.yml` pourrait réutiliser les couches amd64 du gate.
  2. **Smoke `local` (S, environ 25 lignes)**. Ajouter un job `docker-smoke-local` (`needs: [docker-build]`, hors du chemin des E2E), ajouté à `release-summary.needs` et à la boucle bloquante (`:724`). Il fait `docker load` de l'artefact `docker-image-local`, puis :
     ```bash
     docker run -d --name smoke-local -p 3000:3000 -e RATE_LIMIT_RPM=0 -e REASONING_ENABLED=true docling-studio:local
     ```
     Ensuite, la même boucle `/api/health` que `:303-315`, et vérifier `status == "ok"`, `engine == "local"` et `reasoning_available == true`.
     - `reasoning_available` vaut `runner.is_available`, c'est-à-dire `deps_present()` (`document-parser/main.py:159`, `infra/docling_agent_reasoning.py:143-147`). Ollama n'est sondé qu'à l'appel (`bootstrap/factories.py:93-114`).
     - **Coût estimé** : téléchargement d'environ 25 s, `docker load` d'environ 35 s (mesuré dans `Security scan — local`), démarrage, soit environ 1 min 30 s en parallèle. Peu ou pas d'impact sur la durée totale.
     - **Risque** : vérifier au premier run que le démarrage `local` sans modèles n'appelle pas HuggingFace. `/api/health` ne touche pas les modèles.
  3. **`dep-audit` sur tous les groupes livrés (S, 1 ligne)**. Remplacer `release-gate.yml:124` par `uv sync --frozen --group local --group reasoning && …`.
     - **Coût** : torch CPU et docling à installer, +1 à 2 min sur un job de phase 1, parallèle et hors chemin critique.
     - **Gain** : de la visibilité seulement, puisque le job reste non bloquant pour Python. Voir l'INFO Dependency audit pour les 17 vulnérabilités du groupe `local` qu'il ne voit pas aujourd'hui.
  4. **arm64 (M, optionnel)**. Ajouter un job `docker-build-local-arm64` :
     - `runs-on: ubuntu-24.04-arm` (le dépôt est public) ;
     - `platforms: linux/arm64`, `push: false`, `WITH_REASONING=true` ;
     - en dehors des checks requis au début.

     Sur un runner arm64 natif, le temps devrait rester proche du build amd64 (quelques minutes), en parallèle. Avec QEMU sur `ubuntu-latest`, à éviter, le build-push multi-arch de `local` a pris 18 min 06 s contre 2 min 53 s pour le build amd64 du gate.
  5. **Vérification après publication (S-M, optionnel)**. Dans `release.yml`, après le push, un job lance `ghcr.io/…:X.Y.Z-local` (amd64), appelle `/api/health` et lance Trivy sur l'image publiée. C'est le seul endroit où l'étape `BAKE_MODELS` (`Dockerfile:108-113`) peut être couverte.
  - **Contrainte** : garder les noms `Docker build — local` et `Security scan — local`, c'est-à-dire les valeurs `remote` et `local` de la matrice. Ce sont des contextes requis par la protection de `main` : les renommer bloquerait toute PR vers `main` (« Expected — waiting for status »).
  - **Effort global** : S pour les étapes 1 à 3 (une quinzaine de lignes YAML) ; M avec 4 et 5.
  - **Risque** : faible techniquement. Le risque principal est voulu : le premier run peut passer au rouge si Trivy trouve un CRITICAL dans les 20 paquets reasoning. À faire avant le commit de gel 0.7.4, pas le jour du tag.

### [MIN] Contexte `frontend/` sans `.dockerignore` ; motifs `__pycache__` non récursifs — inchangé vs 0.7.3

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .`), `frontend/.dockerignore` absent, `docker-compose.yml:202-204` ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7` ; `Dockerfile:45`, `document-parser/Dockerfile:26`
- **Constat** :
  - Fichiers inchangés. Sur ce poste, `frontend/node_modules` (122 Mo) et `frontend/dist` (2,1 Mo) partent dans le contexte du service `frontend`. Le `COPY . .` écrase le `node_modules` installé par `npm ci`.
  - On compte 13 répertoires `__pycache__` sous `document-parser/` (hors `.venv`), dont 12 imbriqués que les motifs ancrés à la racine du contexte ne filtrent pas. La CI n'est pas touchée (checkout propre).
- **Règle violée** : item 10.2.4 (poids 1).
- **Remédiation (S, sans risque)** :
  - créer `frontend/.dockerignore` avec `node_modules/`, `dist/`, `*.log`, `.DS_Store`, `.env*` ;
  - remplacer par `**/__pycache__/` et `**/*.pyc` dans `.dockerignore:33-34` (préfixés `document-parser/`) et dans `document-parser/.dockerignore:6-7`.

---

### [INFO] [NOUVEAU dans ce rapport] Les tests unitaires du gate ne peuvent pas échouer — vs 0.7.3 : non relevé, mais déjà présent

- **Localisation** : `.github/workflows/release-gate.yml:82-86`, `:88-92`, `:724`, `:773`
- **Constat** :
  - Voir le tableau `maintainers.md` plus haut : un `pytest` ou un `vitest` rouge sort quand même en `success`, parce que `tee` donne le code retour.
  - Le job `Unit tests` est pourtant un check requis, compté comme bloquant par le résumé (`:724`, libellé `Yes` en `:773`).
  - Le risque reste couvert par `Backend tests` et `Frontend tests & build` de `ci.yml`, eux aussi requis, sauf contournement administrateur.
- **Remédiation (S)** : ajouter `set -o pipefail` en première ligne des deux blocs `run` (`:84`, `:90`). **Ne pas** poser `defaults.run.shell: bash` au niveau du workflow, ce qui activerait `pipefail` partout :
  - le step `Node audit` s'arrêterait en `:155` (`npm audit | tee` sort en 1 dès qu'il y a une vulnérabilité). Il n'écrirait jamais `critical=` et le blocage npm CRITICAL serait désactivé en silence ;
  - `audit-checks` deviendrait rouge (script absent), ce qui bloque `main`, puisque c'est un check requis.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert, et c'est un check requis — inchangé vs 0.7.3

- **Localisation** : `.github/workflows/release-gate.yml:183-219`, `:192-193`, `:760-762`, `:775`, `:787` ; `.gitignore:50-51`
- **Constat** :
  - Le job est inchangé (log du run 41468347487 cité plus haut).
  - Nouveau fait : `Audit checks (commands.sh)` fait partie des 14 contextes requis sur `main`. Un check qui ne vérifie rien conditionne donc le merge.
  - Le tableau `PASS | WARN | FAIL` du commentaire PR reste cassé : `grep -c … || echo "?"` imprime `0` puis `?`.
- **Remédiation (S, plus une action administrateur)** : versionner le script, ou supprimer le job. Dans ce second cas, il faut aussi :
  - le retirer de `release-summary.needs` (`:678`) ;
  - retirer les lignes `:714`, `:733`, `:760-762`, `:775` et `:783-787` ;
  - **retirer le contexte des checks requis de `main`, faute de quoi toutes les PR vers `main` restent bloquées**.

### [INFO] Dependency audit : honnête, mais aveugle sur les groupes livrés `local` et `reasoning` ; npm ne bloque que sur CRITICAL — corrigé en partie vs 0.7.3

- **Localisation** : `.github/workflows/release-gate.yml:124`, `:127-147`, `:157-168`, `:177-181`, `:774` ; `frontend/package.json:22`
- **Constat** :
  - **Corrigé (#368)** : `pip-audit` sans rapport → `::warning::pip-audit produced no report` (`:143-144`). Libellé du résumé → `npm CRITICAL only` (`:774`).
  - **Inchangé, Python** : `uv sync --frozen` (`:124`) n'installe que le groupe principal et `dev`. Le job a vu 95 vulnérabilités au run 41468347487 ; l'auditeur en retrouve 93 sur le groupe principal (pillow 66, cryptography 13, filelock 12, transformers 2). `pip-audit --no-deps`, lancé par l'auditeur sur `uv export` :
    - **groupe `local`** : 17 vulnérabilités. `docling` 2.121.0 en a 8, corrigées en 2.131.0 ou 2.132.0, avec les mêmes 8 CVE sur `docling-slim`. S'y ajoutent `accelerate` 1.14.0 (CVE-2026-69112, sans correctif) et `setuptools` 84.0.0 (corrigé en 84.1.0, Windows seulement). L'une des failles docling (GHSA-p944-4xh2-x776) porte sur l'entrée `DoclingDocument` JSON, voisine de l'import #359. **Recoupe l'audit 08**, qui juge l'exploitabilité ;
    - **groupe `reasoning`** : 1 vulnérabilité (`nltk`, ci-dessus).

    Trivy scanne `docling` dans l'image `local` du gate, mais ne bloque que les CRITICAL, et le scan HIGH est informatif (`:373-385`).
  - **Inchangé, npm** : `npm audit` du run 41468347487 compte 29 vulnérabilités (19 moderate, 10 high, 0 critical), toutes corrigibles par `npm audit fix` sauf `minimatch`. `dompurify` 3.3.3 (dépendance runtime, `frontend/package.json:22`) en porte 17 de sévérité high. Studio l'appelle en mode par défaut (`DOMPurify.sanitize(html)`, `frontend/src/shared/ui/MarkdownViewer.vue:24`), alors que la plupart des advisories visent `IN_PLACE`, `RETURN_DOM` ou les hooks. Rien ne bloque sous CRITICAL. Recoupe l'audit 08.
- **Remédiation** : étape 3 du [MAJ] (`--group local --group reasoning`). Planifier `docling ≥ 2.132` avec la montée Pillow (#361). `npm audit fix` sur `dompurify` (patch dans `^3.3.3`). En option, bloquer npm sur `high` pour les seules dépendances `--omit=dev`.

### [INFO] `.trivyignore.yaml` : les 5 suppressions expirent le 2026-12-31, soit dans 58 jours, sans issue de suivi Pillow — corrigé en partie vs 0.7.3

- **Localisation** : `.trivyignore.yaml:7-20` (libxml2, `expired_at` `:20`), `:21-56` (Pillow, `expired_at` `:38`, `:44`, `:50`, `:56`), `:22` ; `document-parser/pyproject.toml:14`
- **Constat** :
  - **Corrigé (#368)** : la note cite désormais le plafond `pillow<11` du projet (`:22`).
  - **Échéance** : les 5 entrées tombent le même jour, le 2026-12-31 (58 jours après la date d'audit). Aucun jalon n'a de date (`0.8.0 — Production ready`, 22 issues ouvertes, `due_on: null`). Aucun jalon 0.7.4 n'existe. Tout run du gate après le 31 décembre, qu'il s'agisse d'un hotfix 0.7.x ou de la 0.8.0 si Pillow n'a pas bougé, échouera sur les 4 CVE Pillow.
  - **Suivi** : l'issue « montée docling → Pillow 13 », demandée par la synthèse du re-audit 0.7.3, n'existe pas (recherche REST `is:issue pillow` : 0 résultat). #361 (« Upgrade Docling … docling 2.140.0 ») est ouverte, sans jalon. #189 (Mesa CVE-2026-40393) reste ouverte alors que sa suppression a été retirée comme corrigée par Debian (`.trivyignore.yaml:2-6`).
  - **Mécanisme vérifié** : l'expiration et le format YAML sont bien honorés par `trivy-action` (`release-gate.yml:365`). Le gate 0.7.3 est passé au vert grâce aux entrées Pillow et a rebasculé libxml2 à son expiration.
- **Remédiation (S)** : créer l'issue Pillow 13 / docling ≥ 2.132 avec le jalon 0.8.0 et l'échéance 2026-12-31 en titre. Lever `pyproject.toml:14` dans la même PR. Fermer ou recadrer #189. Si 0.8.0 glisse au-delà de mi-décembre, réévaluer les suppressions avant leur expiration, pas après un gate rouge.

### [INFO] `uv` reste installé dans les images d'exécution — inchangé vs 0.7.3

- **Localisation** : `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9`
- **Remédiation** : inchangée. `RUN --mount=from=ghcr.io/astral-sh/uv:0.13.6,source=/uv,target=/bin/uv uv sync …`, ou `pip uninstall -y uv` dans le dernier `RUN` qui l'utilise.

### [INFO] `Image size check` ne compare jamais rien (nom d'image en majuscules) — inchangé vs 0.7.3

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:441` ; `:390`
- **Constat** :
  - Log du run 41468347487 : `Could not pull ghcr.io/scub-france/docling-Studio:0.7.2-remote` (idem `-local`), puis « no previous baseline ».
  - Détail connexe : l'annotation HIGH (`:390`, `grep -c "HIGH"`) compte des **lignes** du rapport Trivy, pas des vulnérabilités (« local image has 4 HIGH », run 41468347487).
- **Remédiation (S)** : à la ligne `:441`, `IMAGE="${REGISTRY}/${IMAGE_NAME,,}:${PREV_TAG#v}-${target}"` (variables d'environnement bash, déjà exportées par `env:` en `:12-15`). Tant que le [MAJ] n'est pas traité, ne comparer que `remote` : la `local` publiée contient environ 1,3 Go de modèles que l'image du gate n'a pas.

### [INFO] Matrices en fail-fast — corrigé en partie vs 0.7.3

- **Localisation** : `.github/workflows/release-gate.yml:338-341` (corrigé), `:228-230` (`docker-build`), `.github/workflows/release.yml:21-23`
- **Constat** :
  - `image-scan` passe désormais en `fail-fast: false` : les deux scans ont abouti au run 41468347487.
  - `docker-build` et `release.yml` restent en fail-fast. Un échec du build `local` à la publication annule `remote`, d'où une release partielle possible.
- **Remédiation (S)** : `fail-fast: false` sur les deux matrices restantes.

### [INFO] Déclencheurs et contournement : `main` reçoit des push directs en `[skip ci]`, et le head de `release/0.7.4` n'a jamais été vérifié par la CI — aggravé vs 0.7.3

- **Localisation** : `.github/workflows/ci.yml:3-7`, `:68-72`, `:134-139` ; `.github/workflows/release-gate.yml:3-6`, `:49-56` ; `.github/workflows/docs.yml:3-9` ; `.github/workflows/auto-close-issues.yml:3-6` ; commits `0465e70` et `1de1929`
- **Constat** :
  - **Inchangé** :
    - pas de CI sur push `release/**` ;
    - pas de `ruff format --check` ni de `prettier --check` en CI, alors que le script `format:check` existe (`frontend/package.json`) ;
    - `mkdocs build --strict` ne tourne qu'au push sur `main`.
  - **Nouveau** :
    - Les deux commits README sont passés en push direct sur `main` avec `[skip ci]`, après fermeture de la PR #369 sans merge. Un administrateur le peut grâce à `enforcement_level: non_admins`. `release/0.7.4` a été créée sur ce commit, et aucun workflow n'y a tourné, pas même `Auto-close issues`, qui se déclenche sur tout push `release/**`. C'est cohérent avec un commit de tête en `[skip ci]`.
    - Les règles de skip de GitHub s'appliquent à l'événement `push`, dont relève un push de tag. Un tag `v0.7.4` posé directement sur `1de1929` (par exemple via la procédure hotfix, `docs/maintainers.md:74`) ne lancerait donc probablement pas `release.yml`. Ce n'est pas vérifié par un run. La procédure standard (commit de gel puis merge) n'est pas concernée.
  - **Détail** : `ci.yml:136` teste `github.ref == refs/heads/release/*`. C'est impossible, puisque `ci.yml` ne se déclenche pas sur push `release/**` : condition morte (shellcheck SC2193).
- **Remédiation (S)** :
  - ne pas taguer un commit en `[skip ci]` ;
  - passer la protection de `main` à « Do not allow bypassing » (ou réserver le contournement aux urgences documentées) ;
  - ajouter `push: branches: ['release/**']` à `ci.yml` ;
  - ajouter `uv run ruff format --check .` après `ci.yml:44` et `npm run format:check` après `ci.yml:69` ;
  - ajouter `pull_request` (chemins `docs/**`, `mkdocs.yml`) à `docs.yml` en build seul.

### [INFO] Les nouveautés 0.7.3 ne sont pas exercées de bout en bout ; `/mcp` n'est jamais appelé en CI — inchangé vs 0.7.3

- **Localisation** : `.github/workflows/release-gate.yml:650` (`--tags @critical`), `.github/workflows/ci.yml:156-158` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:1` (`@ui @regression`)
- **Constat** : 6 features `@critical`, aucune feature API qui mentionne `mcp`, `mcp-config.feature` toujours `@regression`. Recoupe l'audit 09.
- **Remédiation** : inchangée. Une feature Karate qui envoie un `initialize` JSON-RPC sur `POST /mcp` via nginx (port 3000), taguée `@regression`.

### [INFO] Durcissement Docker : pas de `HEALTHCHECK`, image racine sans `USER` — inchangé vs 0.7.3

- **Localisation** : `Dockerfile:54-65`, `document-parser/Dockerfile`, `frontend/Dockerfile`, `embedding-service/Dockerfile` (aucun `USER`) ; `docker-compose.yml:141-199`, `:209-210` (`depends_on` sans `condition: service_healthy`)
- **Remédiation** : inchangée. Ni `curl` ni `wget` n'est installé dans `python:3.12-slim`. Utiliser `HEALTHCHECK CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"`, ou le port 3000 dans l'image racine.

### [INFO] Images de base et chaîne d'approvisionnement des actions — inchangé vs 0.7.3, élargi

- **Localisation** : `Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:173` (`node:20-alpine`) ; `Dockerfile:22`, `document-parser/Dockerfile:11`, `embedding-service/Dockerfile:1`, `frontend/Dockerfile:9` (étiquettes flottantes) ; `.github/workflows/*.yml` (`uses:`)
- **Constat** :
  - **Inchangé** :
    - Node 20, en fin de vie depuis le 2026-04-30, dans les étages de build, alors que la CI teste avec Node 22 ;
    - aucune image de base épinglée par digest ;
    - annotations « Node.js 20 is deprecated » sur `checkout@v4.3.1`, `setup-node@v4`, `setup-python@v5`, `upload-artifact@v4.6.2` et `setup-uv@v5` (run 41468347487).
  - **Élargi** :
    - les 18 références `uses:` distinctes sont épinglées par étiquette mutable, aucune par SHA. C'est le cas de `aquasecurity/trivy-action@v0.35.0` et de `docker/build-push-action@v6`, qui tourne avec `packages: write` dans `release.yml:17-19` ;
    - `ci.yml`, `docling-compat.yml` et la plupart des jobs de `release-gate.yml` n'ont pas de bloc `permissions:` et héritent des droits par défaut du dépôt, que l'auditeur ne peut pas lire (API refusée) ;
    - aucun `.github/dependabot.yml` ni Renovate. Seul le graphe de dépendances Dependabot tourne (run « Graph Update » 41477977361).
- **Remédiation** :
  - passer à `node:22-alpine` (3 lignes) ;
  - épingler les actions tierces par SHA, avec le tag en commentaire ;
  - ajouter `permissions: contents: read` au niveau des workflows ;
  - ajouter un `dependabot.yml` (`github-actions`, `docker`, `npm`, `uv`).

### [INFO] [NOUVEAU] Le cache Docker est invalidé à chaque changement de code et à chaque version

- **Localisation** : `Dockerfile:24-25` (`ARG`/`ENV APP_VERSION` en tête de l'étage `base`), `:45` (`COPY document-parser/ .` dans `base`), puis `:92-106` (apt et `uv sync --group local`, dans l'étage `local` qui hérite de `base`) ; `document-parser/Dockerfile:26` puis `:66-80`
- **Constat** :
  - Le code backend est copié avant l'installation des dépendances `local` (torch CPU, docling…). Tout changement de code relance donc l'apt et le `uv sync --group local` complet dans le gate et dans `release.yml`.
  - `ENV APP_VERSION` en ligne 25 invalide toutes les couches suivantes (apt, `pip install uv`, `uv sync`) à chaque changement de version.
  - Cela explique en partie les 2 min 53 s du build `local` du gate et les 18 min 06 s de `release.yml`, et cela fixe le coût de l'étape 1 du [MAJ] (pas de cache pour le groupe reasoning).
- **Remédiation (M)** :
  - déplacer `ARG`/`ENV APP_VERSION` juste avant le `CMD` ;
  - installer les groupes `local` et `reasoning` dans un étage de dépendances avant `COPY document-parser/ .`, ou copier le code dans les étages finaux `remote` et `local` ;
  - ou ajouter `RUN --mount=type=cache,target=/root/.cache/uv`.

### [INFO] [NOUVEAU] Le chemin compose par défaut (`CONVERSION_MODE` absent → `local`) n'est jamais construit en CI

- **Localisation** : `docker-compose.yml:144` (`target: ${CONVERSION_MODE:-local}`), `document-parser/Dockerfile:45-92` ; `ci.yml:114`, `release-gate.yml:541`, `:619` (`CONVERSION_MODE: remote` partout)
- **Constat** :
  - La commande de la fiche (`docker compose build`, sans variable) construit `document-parser/Dockerfile --target local`. Aucun workflow ne la lance.
  - Le gate construit la cible `local` du `Dockerfile` racine, une autre image.
  - Les deux étages `local` sont aujourd'hui équivalents : le diff se limite à `USER root` / `USER appuser` et aux commentaires. Mais ce sont deux Dockerfiles à maintenir en parallèle, sans garde-fou.
- **Remédiation (S)** : dans le job `docker-build` du gate, une étape `docker compose build document-parser` avec `CONVERSION_MODE=local` (sans `BAKE_MODELS`), ou factoriser l'étage backend commun. Coût d'environ +3 min en parallèle.

---

## Delta vs 0.7.3 (re-audit)

| Écart re-audit 0.7.3 (@ `e01fd95`) | Statut 0.7.4 (@ `1de1929`) | Détail |
|------------------------------------|----------------------------|--------|
| [CRIT, conditionnel] 10.1.1 gate pas encore vert | **Levé, provisoire** | Gate 41468347487 13/13 sur `59674be` (même arbre que `v0.7.3`). Pas encore de gate 0.7.4 |
| [MAJ] 10.2.3 `local` publiée non vérifiée | **Toujours ouvert** (3e audit) | `release-gate.yml:252` et `:124` inchangés. Constat élargi : `local` jamais démarré |
| [MIN] 10.2.4 `.dockerignore` | **Toujours ouvert** | Fichiers non touchés |
| [INFO] Dependency audit | **Corrigé en partie** | Rapport absent signalé, libellé corrigé (#368). Périmètre `local`/`reasoning` et npm HIGH restent |
| [INFO] `uv` dans les images | Inchangé | — |
| [INFO] Justification Pillow | **Corrigé en partie** | Plafond Studio cité. Échéance commune, issue de suivi absente |
| [INFO] Audit checks faux vert | Inchangé | Nouveau fait : check requis sur `main` |
| [INFO] Image size (majuscules) | Inchangé | Vérifié au log du run 41468347487 |
| [INFO] fail-fast | **Corrigé en partie** | `image-scan` corrigé ; `docker-build` et `release.yml` restent |
| [INFO] Nouveautés hors e2e / `/mcp` | Inchangé | — |
| [INFO] Déclencheurs | **Aggravé** | Push directs `[skip ci]` sur `main`, head de release jamais vérifié en CI |
| [INFO] Durcissement Docker | Inchangé | — |
| [INFO] Images de base | Inchangé, élargi | Pins par SHA, `permissions`, Dependabot |
| — | **[INFO] nouveau** | Tests unitaires du gate infaillibles (trou n°1 de `maintainers.md`, confirmé) |
| — | **[INFO] nouveau** | Cache Docker invalidé par le code et la version |
| — | **[INFO] nouveau** | Cible compose par défaut `local` jamais construite |

---

## Quick wins (gain estimé)

| # | Action | Item | Gain | Effort / risque |
|---|--------|------|------|-----------------|
| 1 | Créer `frontend/.dockerignore` ; motifs `**/__pycache__/`, `**/*.pyc` dans les deux `.dockerignore` | 10.2.4 (poids 1) | **+5 pts** (85 → 90) | S, environ 10 lignes, aucun risque |
| 2 | `WITH_REASONING` dans le build `local` du gate (étape 1) et smoke `local` (étape 2) | 10.2.3 (poids 2) | **+10 pts** (→ 95, → 100 avec #1) | S, environ 30 lignes ; gate +1 min environ ; risque de rouge voulu au premier run |
| 3 | `--group local --group reasoning` en `release-gate.yml:124` | renforce 10.2.3 | 0 pt | S, 1 ligne, job parallèle +1 à 2 min |
| 4 | `set -o pipefail` dans les deux steps de tests (`:84`, `:90`), **pas** au niveau du workflow | fiabilise 10.1.1 | 0 pt | S, 2 lignes |
| 5 | `${IMAGE_NAME,,}` en `:441` | — | 0 pt | S, 1 ligne |
| 6 | `fail-fast: false` en `release-gate.yml:228` et `release.yml:21` | — | 0 pt | S, 2 lignes |
| 7 | `ruff format --check` et `npm run format:check` dans `ci.yml` | protège 10.1.3 et 10.1.5 | 0 pt | S, 4 lignes |
| 8 | Issue Pillow 13 / docling ≥ 2.132 avec l'échéance 2026-12-31 | protège 10.1.1 | 0 pt | S |
| 9 | Supprimer `audit-checks` **et** retirer son contexte requis de `main` | — | 0 pt | S, plus une action administrateur |

Les quick wins 1 et 2 portent le score à **100**, si le gate 0.7.4 est vert.

---

## Points positifs

- **Gates statiques verts** à `1de1929` : ruff 0.16.4 (lint et format, 196 fichiers), eslint sans warning, Prettier conforme, vue-tsc, `uv lock --check`, `mkdocs build --strict`, les 3 fichiers compose valides. actionlint ne trouve aucune erreur sur les 6 workflows.
- **Dernier Release Gate complet : 13/13** (run 41468347487). Les **deux** scans Trivy aboutissent, grâce au `fail-fast: false` posé par #368 : c'est la première fois en 0.7.x que `Security scan — local` va au bout sans dépendre de `remote`. Smoke, E2E API (full scope) et E2E UI (`@critical`) sont verts.
- **Publication 0.7.3 réussie** (run 41478041280) : `remote` et `local` (reasoning, modèles, amd64 et arm64) poussés. CI verte sur `main`, E2E UI compris.
- **`main` protégé par 14 checks requis**, qui couvrent lint, tests, build des deux cibles, smoke, scans et E2E. L'affirmation de `maintainers.md` sur les tests est donc vraie.
- **Suivis du re-audit 0.7.3 appliqués** (#368) : fail-fast du scan, rapport pip-audit absent signalé, libellé honnête du résumé, justification Pillow complétée.
- **Suppressions Trivy saines** : 5 entrées datées, chacune avec ce qui a été vérifié et ce qui ne l'a pas été. Le mécanisme d'expiration fonctionne (prouvé en 0.7.3).
- **Configuration inchangée et conforme** : routage nginx `/api/` et `/mcp` identique sur les deux points d'entrée, variables d'environnement documentées, Docling Serve épinglé en `v1.37.0`.

---

## Verdict partiel : GO (provisoire)

85/100, 0 CRITICAL, 1 MAJOR, 1 MINOR, 13 INFO → **GO** (≥ 80, MAJ ≤ 3).

- **Condition** : le Release Gate de la PR `release/0.7.4` → `main` doit finir vert. Elle n'existe pas encore et aucun run CI ne couvre `1de1929`. S'il est rouge (par exemple une nouvelle CVE CRITICAL dans la base Trivy), on passe à 70/100 avec 1 CRITICAL, donc **NO-GO**.
- **Ne pas taguer `1de1929`, ni aucun commit en `[skip ci]`** : `release.yml` ne partirait probablement pas.
- **Le MAJ a 3 audits d'ancienneté.** L'image réellement livrée (`X.Y.Z-local` : reasoning, modèles, arm64) ne sera toujours construite, scannée et démarrée qu'au push du tag. Les étapes 1 à 3 de la remédiation tiennent en une quinzaine de lignes et coûtent environ 1 min de gate. Elles sont recommandées avant le gel 0.7.4, pour qu'un éventuel CRITICAL du groupe `reasoning` apparaisse avant le tag et pas après.
- **Échéance externe** : les suppressions Trivy expirent le 2026-12-31 (58 jours). Il faut une issue de suivi datée avant la 0.8.0.

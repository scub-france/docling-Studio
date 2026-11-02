# Rapport d'audit : CI / Build

> **Re-audit de release/0.7.3 @ e01fd95 — score 70 → 85 (Release Gate `41464248455` vert)**

> **Résultat du gate, relevé par l'orchestrateur après la fin du run (2026-11-02)** : le Release Gate
> `41464248455` (PR #366, `e01fd95`) a fini en **`success`, avec les 13 jobs verts**. Les deux scans,
> `Security scan — remote` et `Security scan — local`, sont verts. `Docker smoke test`, `Image size check`,
> `E2E API tests (full scope)`, `E2E UI tests (@critical)` et `Release summary` sont verts aussi.
> Les scores et les verdicts provisoires ci-dessous sont donc confirmés dans leur branche « gate vert ».


**Release** : 0.7.3
**Branche** : release/0.7.3 @ e01fd95 (merge de la PR #367, remédiation)
**Date** : 2026-11-02
**Auditeur** : claude-code
**Type** : re-audit après remédiation (audit initial : 70/100, NO-GO, @ 02adc68)

---

## Score de compliance

Le Release Gate de la PR #366 sur `e01fd95` (run `41464248455`) tournait encore au moment de la vérification (un seul relevé, environ 6 minutes après son démarrage à 14:40 UTC). Les scans Trivy, qui portaient le CRIT initial, n'avaient pas démarré. L'item 10.1.1 est donc noté dans les deux cas.

| Métrique | Si le gate finit vert | Si le gate finit rouge |
|----------|-----------------------|------------------------|
| Items conformes | 9 / 11 | 8 / 11 |
| Score | **85 / 100** | **70 / 100** |
| Écarts CRITICAL | 0 | 1 |
| Écarts MAJOR | 1 | 1 |
| Écarts MINOR | 1 | 1 |
| Écarts INFO | 10 | 10 |

Poids total de la checklist : 20.
- Gate vert : poids non conformes = 10.2.3 (2) + 10.2.4 (1) = 3. `score = 17 / 20 * 100 = 85`.
- Gate rouge : on ajoute 10.1.1 (3), soit 6. `score = 14 / 20 * 100 = 70`, comme à l'audit initial.

**Delta vs audit initial** : +15 si le gate est vert (le CRIT est levé). Le MAJ et le MIN ne sont pas traités par la remédiation. Sur les 8 INFO initiaux, 1 est corrigé en partie (pip-audit) et 7 sont inchangés. 2 INFO sont nouveaux.

### État GitHub Actions au moment de la vérification

| Run | Cible | Résultat |
|-----|-------|----------|
| Release Gate 41464248455 | PR #366 `release/0.7.3` → `main` @ e01fd95 | **in_progress**. Terminés en `success` : `Lint & type-check`, `Unit tests`, `Dependency audit`, `Audit checks (commands.sh)`, `Docker build — remote`. En cours : `Docker build — local`. Pas encore lancés : `Security scan — remote`, `Security scan — local`, `Docker smoke test`, `Image size check`, `E2E API tests (full scope)`, `E2E UI tests (@critical)`, `Release summary` |
| CI 41464248680 | PR #366 @ e01fd95 | **success** : `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` ; `E2E UI tests (Karate UI)` skipped (réservé à `main`, `ci.yml:158`) |
| CI 41460137670 | PR #367 (`fix/release-0.7.3-audit-blockers`) | **success** |
| Auto-close issues 41464241695 | push du merge e01fd95 sur `release/0.7.3` | success (seul workflow lancé par un push sur `release/**`) |

Le job `Dependency audit` du gate est terminé : son log (API `actions/jobs/125340839053/logs`) montre le nouveau comportement, voir « Validation du step `Python audit` » plus bas.

### Gates statiques ré-exécutés localement (head e01fd95, lecture seule)

| Gate | Commande | Résultat |
|------|----------|----------|
| Lint backend | `ruff check .` (ruff 0.16.4, version de `uv.lock:3281-3282`) | « All checks passed! », exit 0 |
| Format backend | `ruff format --check .` (0.16.4) | « 196 files already formatted », exit 0 |
| Lockfile | `uv lock --check` (uv 0.13.6, version des Dockerfiles) | « Resolved 180 packages », exit 0. uv 0.8.4 lit aussi le lock (révision 5) sans erreur |
| Lint frontend | `npx eslint src/` | exit 0, aucune sortie |
| Format frontend | `npx prettier --check src/` | « All matched files use Prettier code style! », exit 0 |
| Type-check | `npx vue-tsc --noEmit` | exit 0 |
| Workflow | extraction des 4 blocs `run:` du job `dep-audit` (`yaml.safe_load`) puis `bash -n` | syntaxe valide pour les 4 |

Non ré-exécutés : `vite build` et `mkdocs build --strict` (couverts par le job `Frontend tests & build` de la CI pour le premier ; le second n'est pas un item de la checklist).

---

## Vérification de la remédiation

| # | Item | Poids | Audit initial | Re-audit | Preuve |
|---|------|-------|---------------|----------|--------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **[CRIT]** | ⏳ **En attente du gate (run 41464248455)** | Causes du rouge traitées : `uv.lock:2748-2749` (pyjwt 2.15.1), `uv.lock:300-301` (certifi 2026.10.23), `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9` (uv 0.13.6), `.trivyignore.yaml:21-55` (Pillow accepté jusqu'au 2026-12-31). 5 jobs du gate verts, scans non lancés. CI 41464248680 verte |
| 10.1.2 | Warnings ESLint résolus | 1 | ✅ | ✅ Conforme | `npx eslint src/` exit 0, sortie vide |
| 10.1.3 | Warnings Ruff résolus | 1 | ✅ | ✅ Conforme | ruff 0.16.4 « All checks passed! » ; job gate `Lint & type-check` success |
| 10.1.4 | Type-check frontend | 2 | ✅ | ✅ Conforme | `vue-tsc --noEmit` exit 0 ; job gate `Lint & type-check` success |
| 10.1.5 | Formatting conforme | 1 | ✅ | ✅ Conforme | 196 fichiers formatés ; prettier conforme |
| 10.2.1 | `docker compose build` réussit | 3 | ✅ | ✅ Conforme | CI 41464248680, job `E2E API tests (Karate)` success : `docker compose --profile remote up -d --wait --build` (`ci.yml:104`), donc build de `document-parser/Dockerfile` avec uv 0.13.6 (`:17`) et de `frontend/Dockerfile` |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | ✅ | ✅ Conforme (smoke du gate en attente) | Même run CI : la boucle de santé `ci.yml:116-128` passe sur la stack compose. Le smoke de l'image unique (`release-gate.yml:294-330`) n'avait pas démarré ; `Docker build — remote` du gate (même `Dockerfile`, uv 0.13.6) est vert |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **[MAJ]** | ❌ **Inchangé** | `release-gate.yml:250` (seul `APP_VERSION`) vs `release.yml:55`, `:70-73` ; `release-gate.yml:124` |
| 10.2.4 | `.dockerignore` à jour | 1 | **[MIN]** | ❌ **Inchangé** | `frontend/.dockerignore` absent ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7` |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | ✅ | ✅ Conforme (fichiers inchangés) | `nginx.conf.template:13-24`, `:29-38` ; `frontend/nginx.conf.template:13-24`, `:29-38` |
| 10.3.2 | Variables d'environnement documentées | 1 | ✅ | ✅ Conforme | `.env.example:1-5` inchangé ; `.env.example:10-13` (`BATCH_PAGE_SIZE` remis à jour, #344) ; `.env.example:102-127` (MCP : le texte ne promet plus une restriction à localhost) |

### Détail 10.1.1 — causes du rouge traitées, preuve finale en attente

Causes relevées par l'orchestrateur dans les artefacts `trivy-remote` / `trivy-local` du run initial `41452005966`, face à la remédiation :

| Cause (run 41452005966) | Remédiation | Preuve à e01fd95 | Statut |
|-------------------------|-------------|------------------|--------|
| PyJWT 2.13.0, CVE-2026-102268 (fix 2.14.0) | montée à 2.15.1 (`7246efe`) | `uv.lock:2748-2749` | Corrigé dans le lock |
| certifi 2026.7.22, GHSA-6q48-6c7w-9gw2 | montée à 2026.10.23 | `uv.lock:300-301` | Corrigé dans le lock |
| Paquet `uv` 0.11.6, GHSA-hq85-5cpj-mr62 | `pip install uv==0.13.6` dans les 3 Dockerfiles | `Dockerfile:34-36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9` | Corrigé si le scan le confirme |
| Crate `zip` 8.1.0 dans `/usr/local/bin/uv` et `uvx`, CVE-2026-115905 | même montée | Indice statique : le binaire uv 0.13.6 (build darwin du scratchpad) ne contient aucune chaîne `zip-<version>`, seulement `astral_async_zip-0.0.22` ; uv 0.8.4 contient `zip-2.4.2`. Le retrait de la racine emSign n'est pas vérifiable sans le scan | Probable, à confirmer par le scan |
| Pillow 10.4.0, CVE-2026-112393, -112398, -112403, -112900 (fix 13.0.0) | **risque accepté** jusqu'au 2026-12-31 (décision (b) du mainteneur, `79b9ae9`) | `.trivyignore.yaml:21-55` ; `uv.lock:2377-2378` reste à 10.4.0 | Supprimé, non corrigé (voir INFO Pillow) |
| libxml2, CVE-2026-6653 (image `local`) | suppression renouvelée jusqu'au 2026-12-31, justification datée | `.trivyignore.yaml:7-20` | Risque accepté |

Autres effets de `7246efe` : `mcp` 2.1.1 → 2.2.0 (`document-parser/pyproject.toml:24-25`, `uv.lock:1725-1726`), qui ferme les 4 CVE signalées par l'INFO pip-audit initial. Montent aussi `aiohttp` 3.14.5 (`uv.lock:49-50`), `urllib3` 2.8.0 (`uv.lock:3877-3878`), `multidict`, `yarl` et `opentelemetry-api`. Le lock passe de la révision 3 à 5 et reste cohérent (`uv lock --check` vert en 0.13.6).

Suppressions retirées de `.trivyignore.yaml` (commentaire `:2-6`) : les 5 expirées, plus 2 qui couraient encore jusqu'au 2026-11-30, CVE-2026-40393 (mesa, `local`) et CVE-2026-13221 (perl). La justification cite les correctifs Debian (perl 5.40.1-6+deb13u1, mesa 25.0.7-2+deb13u1). C'est cohérent avec le constat de l'orchestrateur pour les expirées. Pour mesa et perl 13221, seul le scan le prouvera, et en particulier le scan `local`, qui n'a encore jamais tourné jusqu'au bout en 0.7.3 (annulé par le fail-fast au run initial).

Ce qui n'a pas été appliqué : l'étape 3 de la remédiation initiale (`fail-fast: false` sur la matrice `image-scan`, `release-gate.yml:336-338`). Si `Security scan — remote` échoue encore, `local` sera de nouveau annulé (voir INFO fail-fast).

**Statut** : le CRIT reste ouvert tant que le run 41464248455 n'est pas vert. Toutes les causes identifiées sont traitées, par correctif ou par acceptation datée.

### Validation du step `Python audit` modifié (`eb84d77`)

Lu à `release-gate.yml:127-145` et `:175-179` :

- **Syntaxe** : les 4 blocs `run:` du job passent `bash -n`. Une fois l'indentation du bloc YAML retirée, le script Python inline (`:139-141`) commence en colonne 0, il est donc valide.
- **Comportement simulé** (scratchpad, `uv` remplacé par un stub qui écrit un JSON `pip-audit`) :
  - 3 vulnérabilités → `::warning::pip-audit: 3 known vulnerabilities…`, exit 0 ;
  - aucune vulnérabilité → pas d'avertissement, exit 0 ;
  - `pip-audit` en erreur, sans JSON → `COUNT` retombe à 0 via `|| echo 0` (`:142`) : pas d'avertissement, exit 0. Voir l'INFO dep-audit.
- **Comportement réel** (job `Dependency audit` du run 41464248455, success) : « Found 95 known vulnerabilities in 5 packages », plus l'annotation `warning` « pip-audit: 95 known vulnerabilities in Python dependencies, see the dep-audit-results artifact ». C'était 129 vulnérabilités dans 12 paquets au run initial. Restent `pillow` 10.4.0 (66), `cryptography` 45.0.7 (13), `filelock` (12), `transformers` (2) et `pytest` (2, groupe `dev`, absent des images). `mcp`, `pyjwt`, `aiohttp` et `urllib3` ne figurent plus dans la liste.
- **Cohérence des sorties et conditions** : aucune référence restante à `steps.pip_audit.outputs.*`. L'`id: pip_audit` (`:128`) ne sert plus à rien, sans conséquence. `Fail on critical vulnerabilities` ne teste plus que `steps.npm_audit.outputs.critical` (`:176`), que le step npm écrit dans les deux branches (`:162-166`). Le nom d'artefact cité dans l'avertissement (`dep-audit-results`) est bien celui de `:172`.
- **Exactitude du commentaire** (`:134-137`) : « CRITICAL Python packages are blocked by the Trivy image scan (python-pkg) ». C'est vrai pour les paquets présents dans les deux images du gate : le run initial a bien bloqué sur PyJWT, certifi et Pillow. C'est faux pour le groupe `reasoning`, absent de l'image `local` du gate (rattaché au [MAJ]).

Verdict : le step est sain et honnête. Deux défauts mineurs restent, regroupés dans l'INFO dep-audit : l'échec silencieux et le libellé du résumé.

---

## Écarts constatés (restants)

### [CRIT, conditionnel] 10.1.1 — Release Gate pas encore vert sur e01fd95

- **Localisation** : `.github/workflows/release-gate.yml:352-366` (step `Run Trivy — CRITICAL (blocking)`), `.trivyignore.yaml:7-55`
- **Constat** : au relevé, le run 41464248455 n'avait pas atteint les scans Trivy. Les causes du rouge initial sont traitées (tableau ci-dessus), mais aucune preuve d'exécution ne montre encore un gate vert. Si le run finit vert, ce constat est levé et le score passe à 85.
- **Règle violée (si rouge)** : item 10.1.1 (poids 3).
- **Remédiation (si rouge)** : lire l'artefact `trivy-remote` / `trivy-local` du run, traiter les CVE CRITICAL restantes de la même façon (correctif, ou suppression datée et justifiée), poser `fail-fast: false` sur `image-scan`, relancer.

### [MAJ] La variante `local` publiée (reasoning + modèles, multi-arch) n'est ni construite ni scannée par le gate — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:243-252` (build du gate, `build-args: APP_VERSION=...` seulement, ligne 250), contre `.github/workflows/release.yml:55` et `:70-73` ; `Dockerfile:86` (`BAKE_MODELS=false`), `:90` (`WITH_REASONING=false`), `:102-106` ; `release-gate.yml:124` (`uv sync --frozen` sans `--group local --group reasoning`)
- **Constat** : fichiers inchangés par la remédiation (les lignes du `Dockerfile` ont glissé de 2 à cause du commentaire uv). Le gate construit toujours `local` sans reasoning ni modèles, en amd64 seul, alors que `release.yml` publie `WITH_REASONING=true`, `BAKE_MODELS=true` en amd64 + arm64. Les 20 paquets du groupe `reasoning` ne passent ni par Trivy ni par `pip-audit`. Le nouveau commentaire de `release-gate.yml:134-137` confie le blocage des CRITICAL Python à Trivy, ce qui rend ce trou plus important : pour le groupe `reasoning`, plus aucun contrôle ne s'applique avant le tag.
- **Règle violée** : item 10.2.3 (poids 2).
- **Remédiation** : inchangée. Passer `WITH_REASONING=true` au build `local` du gate (PyPI seulement, compatible avec la politique HF-free) et scanner cette image. Ajouter `--group local --group reasoning` au `uv sync` du job `dep-audit`. En option, un build `linux/arm64` sans `load`.

### [MIN] Contexte de build `frontend/` toujours sans `.dockerignore` ; `__pycache__` imbriqués non exclus — inchangé

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .`), absence de `frontend/.dockerignore`, `docker-compose.yml:202-204` ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7` ; `Dockerfile:45` (`COPY document-parser/ .`)
- **Constat** : aucun de ces fichiers n'est touché par la remédiation. Le constat initial s'applique tel quel : `node_modules/` et `dist/` de l'hôte partent dans le contexte du frontend, et les motifs `__pycache__/` / `*.pyc` ne couvrent que le premier niveau.
- **Règle violée** : item 10.2.4 (poids 1).
- **Remédiation** : créer `frontend/.dockerignore` (`node_modules/`, `dist/`, `*.log`, `.DS_Store`) et passer aux motifs `**/__pycache__/` et `**/*.pyc`.

---

### [INFO] Dependency audit : honnête désormais, mais échec silencieux et libellé du résumé périmé — corrigé en partie

- **Localisation** : `.github/workflows/release-gate.yml:127-145`, `:142`, `:728-730`, `:769`
- **Constat** :
  - **Corrigé** : le faux contrôle « CRITICAL » est supprimé. Le step publie un avertissement chiffré, vérifié dans le run 41464248455. `mcp` est à 2.2.0. Le message d'erreur final précise « npm » (`:178`).
  - **Nouveau, introduit par `eb84d77`** : si `pip-audit` échoue sans écrire `/tmp/pip-audit.json` (résolution, réseau, index), `python3` lève une exception, `|| echo 0` donne `COUNT=0`, et le step reste vert sans rien signaler. L'ancien code faisait échouer le job dans ce cas, même si c'était par accident (`json.load` sur une entrée vide → `critical=true`).
  - **Inchangé** : le tableau du commentaire PR affiche toujours `Dependency audit | Yes (CRITICAL)` (`:769`). Or la logique de verdict traite un échec de `dep-audit` en « GO CONDITIONAL » (`:728-730`), et seul `npm audit` peut maintenant le faire échouer.
- **Remédiation** : `[ -s /tmp/pip-audit.json ] || echo "::warning::pip-audit produced no report"` avant le calcul. Libellé `:769` → `No (npm CRITICAL → GO CONDITIONAL)`.

### [INFO] [NOUVEAU] `uv` reste installé dans les images d'exécution

- **Localisation** : `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9`
- **Constat** : `pip install uv` se fait dans l'étage `base`, dont héritent `remote` et `local`. Le binaire `uv`/`uvx` et son paquet Python restent donc dans l'image livrée, alors qu'ils ne servent qu'au build. Deux des cinq causes du CRIT initial (GHSA-hq85-5cpj-mr62 et CVE-2026-115905) venaient de cet outil de build. La montée à 0.13.6 traite le symptôme, et chaque future CVE de uv fera de nouveau échouer le gate. Ce point existait avant 0.7.3, mais la remédiation l'a fait ressortir.
- **Remédiation** : ne pas laisser uv dans un calque. Par exemple `RUN --mount=from=ghcr.io/astral-sh/uv:0.13.6,source=/uv,target=/bin/uv uv sync --frozen --no-dev`, ou un `pip uninstall -y uv` dans le même `RUN` que le dernier `uv sync`.

### [INFO] [NOUVEAU] Suppressions Pillow : justification incomplète, échéance commune au 2026-12-31

- **Localisation** : `.trivyignore.yaml:21-25`, `:20`, `:37`, `:43`, `:49`, `:55` ; `document-parser/pyproject.toml:14`
- **Constat** :
  - Le commentaire attribue le plafond de Pillow aux paquets docling verrouillés. Mais le projet borne lui-même `pillow>=10.0.0,<11.0.0` (`pyproject.toml:14`) : la montée docling prévue pour 0.8.0 ne suffira pas sans lever aussi cette borne.
  - Les 5 suppressions expirent le même jour, le 2026-12-31. Le mécanisme d'alarme est voulu, mais tout run du gate après cette date échouera d'un coup si la 0.8.0 n'est pas sortie (ou si un hotfix 0.7.x part après le 31 décembre).
  - La décision (b) et l'honnêteté de la justification (« ACCEPTED, not ruled out », avec ce qui a été vérifié et ce qui ne l'a pas été) sont conformes à la décision du mainteneur.
  - Recoupe l'audit 08.
- **Remédiation** : ajouter au commentaire, ou au ticket 0.8.0, la levée de la borne `pyproject.toml:14`.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:187-191`, `:755-757` ; `.gitignore:50-51`
- **Constat** : `profiles/` est toujours ignoré par git et absent du dépôt. Le job est de nouveau `success` dans le run 41464248455, pour la même raison qu'au run initial (pas de `pipefail`, le `| tee` masque l'exit 127).
- **Remédiation** : inchangée. Versionner le script, ou supprimer le job et sa ligne du résumé.

### [INFO] `Image size check` ne compare jamais rien (nom d'image en majuscules) — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:436`
- **Remédiation** : inchangée. `${IMAGE_NAME,,}`.

### [INFO] Matrices en fail-fast — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:226-228` (`docker-build`), `:336-338` (`image-scan`), `.github/workflows/release.yml:21-23`
- **Constat** : la remédiation n'a pas posé `fail-fast: false`, alors que c'était l'étape 3 du plan initial. Si `remote` échoue encore sur le run en cours, `local` sera de nouveau annulé et l'image `local` restera non scannée en 0.7.3.
- **Remédiation** : inchangée. `strategy.fail-fast: false` sur les trois matrices.

### [INFO] Les nouveautés 0.7.3 ne sont pas exercées de bout en bout ; la route nginx `/mcp` n'est jamais appelée en CI — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:640-645` (`--tags @critical`), `.github/workflows/ci.yml:156-158` ; `e2e/ui/src/test/resources/navigation/mcp-config.feature:1` (`@ui @regression`)
- **Remédiation** : inchangée. Recoupe l'audit 09.

### [INFO] Déclencheurs : pas de CI sur push `release/**`, pas de check de format, doc non buildée sur PR, gate contournable — inchangé

- **Localisation** : `.github/workflows/ci.yml:3-7`, `:68-72` ; `.github/workflows/release-gate.yml:3-6`, `:49-56` ; `.github/workflows/docs.yml:3-9`
- **Constat** : inchangé. `ci.yml:7` couvre les PR vers `release/**` (d'où la CI 41460137670 sur la PR #367), mais le push du merge `e01fd95` n'a lancé que `Auto-close issues`.
- **Remédiation** : inchangée.

### [INFO] Durcissement Docker : pas de `HEALTHCHECK`, image racine sans `USER` — inchangé

- **Localisation** : `Dockerfile:54-65` (lignes décalées de 2 par le commentaire uv), `document-parser/Dockerfile`, `frontend/Dockerfile` ; `docker-compose.yml:141-199`, `:202-210`
- **Remédiation** : inchangée.

### [INFO] Images de base : Node 20 en fin de vie dans les étages de build, étiquettes flottantes — inchangé

- **Localisation** : `Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:173` (`node:20-alpine`) ; `Dockerfile:22`, `document-parser/Dockerfile:11` (`python:3.12-slim`) ; `frontend/Dockerfile:9` (`nginx:alpine`)
- **Constat** : inchangé. Le job `Dependency audit` du run 41464248455 porte de nouveau l'annotation « Node.js 20 is deprecated » pour `actions/checkout@v4.3.1`, `setup-node@v4`, `setup-python@v5`, `upload-artifact@v4.6.2` et `setup-uv@v5`. L'étiquette flottante `python:3.12-slim` a joué dans les deux sens : elle a apporté les correctifs Debian qui ont permis de retirer 6 suppressions, mais elle rend la surface Trivy non reproductible d'un run à l'autre.
- **Remédiation** : inchangée.

---

## Delta vs audit initial

| Écart initial (@ 02adc68) | Statut @ e01fd95 | Détail |
|---------------------------|------------------|--------|
| [CRIT] 10.1.1 Release Gate rouge (Trivy) | **En attente du gate** | Toutes les causes sont traitées : bumps pyjwt, certifi et uv ; Pillow et libxml2 acceptés jusqu'au 2026-12-31 ; 6 suppressions obsolètes retirées. Scans non lancés au relevé |
| [MAJ] 10.2.3 `local` publiée ni construite ni scannée | **Toujours ouvert** | Aucun changement de `release-gate.yml:243-252` ni de `:124` |
| [MIN] 10.2.4 `.dockerignore` | **Toujours ouvert** | Fichiers non touchés |
| [INFO] pip-audit ne bloque jamais | **Corrigé en partie** | Step honnête et vérifié en run, `mcp` 2.2.0. Restent le libellé `:769` et l'échec silencieux (nouveau) |
| [INFO] `Audit checks` faux vert | Toujours présent | Job de nouveau `success` sans script |
| [INFO] `Image size check` (majuscules) | Toujours présent | — |
| [INFO] fail-fast | Toujours présent | Étape 3 de la remédiation initiale non appliquée |
| [INFO] Nouveautés 0.7.3 hors e2e | Toujours présent | — |
| [INFO] Déclencheurs | Toujours présent | — |
| [INFO] Durcissement Docker | Toujours présent | — |
| [INFO] Images de base | Toujours présent | — |
| — | **[INFO] nouveau** | `uv` livré dans les images d'exécution |
| — | **[INFO] nouveau** | Justification Pillow incomplète (`pyproject.toml:14`), échéance commune |

Régression introduite par la remédiation : une seule, mineure. Le step `Python audit` ne signale plus un `pip-audit` en échec (rattachée à l'INFO dep-audit). Aucune autre : lint, format, lock, type-check et la CI complète sont verts à e01fd95, et le build `remote` du gate passe avec uv 0.13.6.

---

## Points positifs

- **Remédiation ciblée et traçable** : chaque cause du rouge initial a un commit dédié (`7246efe`, `eb84d77`, `79b9ae9`), et le diff CI se limite au job `dep-audit` (28 lignes).
- **Suppressions Trivy assainies** : on passe de 7 entrées, dont 5 expirées, à 5 entrées toutes datées au 2026-12-31. Chacune dit ce qui a été vérifié et ce qui ne l'a pas été. Les suppressions devenues inutiles grâce aux correctifs Debian sont retirées au lieu d'être prolongées.
- **Le contrôle pip-audit ne ment plus** : il affiche un chiffre réel, vu dans le run (95 vulnérabilités, 5 paquets, contre 129 dans 12 paquets), et le commentaire du workflow dit où se fait réellement le blocage.
- **Versions uv alignées** : 0.13.6 dans les trois Dockerfiles, le lock relu proprement en 0.13.6.
- **CI verte de bout en bout sur e01fd95** (run 41464248680) : tests backend et frontend, build compose `remote`, E2E API. Gates statiques locaux verts : ruff 0.16.4 (lint et format), eslint, prettier, vue-tsc, `uv lock --check`.
- **Configuration nginx et variables d'environnement** toujours conformes. `.env.example` est plus honnête sur la MCP (`:102-108`) et à jour sur `BATCH_PAGE_SIZE` (`:10-13`).

---

## Verdict partiel : GO (Release Gate `41464248455` vert, 13/13 jobs)

- **Si le run finit vert** : 85/100, 0 CRITICAL, 1 MAJOR, 1 MINOR → **GO** (≥ 80). Le MAJ, la variante `local` publiée non vérifiée avant le tag, relève du plan de remédiation 0.8.0. Le premier build de l'image réellement livrée (reasoning, modèles, arm64) aura toujours lieu au push du tag.
- **Si le run finit rouge** : 70/100, 1 CRITICAL → **NO-GO** (règle absolue). Lire les artefacts `trivy-*` du run et appliquer `fail-fast: false` avant de relancer, pour avoir le verdict de l'image `local`.

Conditions de levée : run 41464248455 entièrement vert, y compris `Security scan — local`, qui n'a jamais abouti en 0.7.3. À faire rapidement, sans blocage : signaler un `pip-audit` sans rapport, corriger le libellé `:769`, `fail-fast: false`.

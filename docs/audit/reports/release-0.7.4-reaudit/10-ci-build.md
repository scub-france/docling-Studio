# Rapport d'audit : CI / Build

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche auditée** : `fix/0.7.4-editor-followups` @ `a6fb539` (working tree) = `release/0.7.4` @ `f7fc791` (PR #401 PDF.js + cache de previews + résumés d'analyse, PR #402 correctifs éditeur) + 13 commits correctifs locaux (#391 à #400) + commit de merge. Branche **non poussée** : GitHub ne connaît que `release/0.7.4` @ `f7fc791`.
**Baseline** : `docs/audit/reports/release-0.7.4/10-ci-build.md` (2026-11-13, `eade7fa`, 85/100, 0 CRIT, 1 MAJ, 1 MIN, score provisoire)
**Mode** : lecture statique des workflows, Dockerfiles, compose et nginx ; `gh run list` / `gh run view` / `gh api` en lecture seule ; `ruff format --check` lancé en local (lecture seule). Exécutions locales fournies par le commanditaire sur `a6fb539`, non relancées : ruff propre, pytest 1501 passed / 15 skipped, `npm ci` OK, eslint, prettier, `vue-tsc` propres, vitest 586 passed, `vite build` OK. Aucun build Docker, aucun conteneur, aucun workflow déclenché.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 8 / 11 |
| Score | **70 / 100** |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 1 |
| Écarts INFO | 14 |

Poids total : 20. Poids non conformes : 10.1.1 (3) + 10.2.3 (2) + 10.2.4 (1) = 6. `score = 14 / 20 * 100 = 70`.

Le CRIT est un **défaut de preuve**, pas un test rouge connu : aucun run CI n'existe sur `f7fc791`, la PR #402 a été fusionnée sans qu'un seul job tourne, et la branche auditée n'est pas poussée. Les exécutions locales sur `a6fb539` sont vertes. Dès qu'un run CI vert existe sur la branche des correctifs (PR vers `release/0.7.4`), 10.1.1 redevient conforme (provisoire) et le score remonte à **85**.

### Tableau de recalcul

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **Non** | Aucun run CI sur `f7fc791` ; run CI de la PR #402 en `failure` avec 0 job ; branche auditée sans run ; Release Gate jamais lancé (voir CRIT) |
| 10.1.2 | Warnings ESLint résolus | 1 | Oui | eslint propre en local sur `a6fb539` ; job `Frontend tests & build` vert sur `de5fe66` (run `43752042089`) |
| 10.1.3 | Warnings Ruff résolus | 1 | Oui | `ruff check` propre en local sur `a6fb539` ; E501 ignoré par configuration |
| 10.1.4 | Type-check frontend | 2 | Oui | `vue-tsc --noEmit` propre en local ; `npm run build` (`frontend/package.json:8`) l'enchaîne avant `vite build` |
| 10.1.5 | Formatting conforme | 1 | Oui | `ruff format --check .` : « 220 files already formatted » (lancé pour cet audit) ; `prettier --check` propre en local (commanditaire). N'est plus « présumé » |
| 10.2.1 | `docker compose build` réussit | 3 | Oui (provisoire) | Job `E2E API tests (Karate)` du run `43752042089` (`de5fe66`, PR #401) : build compose `remote` vert avec `pdfjs-dist`. #402 et les correctifs locaux ne touchent aucune entrée de build (pas de diff sur `uv.lock`, Dockerfiles, compose) |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | Oui (provisoire) | Même job : boucle de santé `ci.yml:120-132` verte. Smoke de l'image unique (`release-gate.yml:296-330`) jamais lancé sur 0.7.4 |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Non** | Inchangé : la variante `local` publiée (reasoning, modèles, arm64) n'est ni construite ni scannée (voir MAJ) |
| 10.2.4 | `.dockerignore` à jour | 1 | **Non** | Pas de `frontend/.dockerignore`, `out/` absent de `.dockerignore`, `__pycache__` imbriqués non couverts (voir MIN) |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | `nginx.conf.template:19-21`, `:23-30` ; le worker PDF.js sort en `.js` et passe par `location /` ; l'en-tête `Range` est relayé tel quel vers `/api/` (voir détail ci-dessous) |
| 10.3.2 | Variables d'environnement documentées | 1 | Oui | Aucune nouvelle variable depuis la baseline (`PreviewCache` a une borne en dur de 64 Mo, `infra/preview_cache.py:16`) ; `ANALYSIS_EDITOR_ENABLED` cohérent : `.env.example:8`, `docker-compose.yml:197`, `docker-compose.dev.yml:140`, `infra/settings.py:279`, `docs/configuration.md:26` |

### État GitHub Actions (relevé le 2026-11-18)

| Run | Cible | Résultat |
|-----|-------|----------|
| `44399691994` | push `release/0.7.4` @ `f7fc791` (merge #401) | success. Seul workflow déclenché : `Auto-close issues` (`auto-close-issues.yml:3-6`). **Aucun run CI sur `f7fc791`** |
| `44171965618` | push `release/0.7.4` @ `b507aad` (merge #402) | success, `Auto-close issues` seulement |
| `44149188645` | CI, PR #402 (fork `jhaveri-bhavya`), tête `f45b2a1` | **failure, 0 job** (« workflow file issue »). Créé 2026-11-17 18:33:47, clos 20:41:32, une seconde après le merge de la PR (20:41:31) : le run attendait une approbation et n'a jamais tourné. `gh pr view 402` : aucun check |
| `43899578187` | CI, PR #402, tête `5a80f8b` | failure, 0 job, même cause |
| `43752042089` | CI, PR #401, tête `de5fe66` | success : `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` ; `E2E UI tests (Karate UI)` **skipped** (`ci.yml:162`, `main` seulement) |
| `44382595574` | CI, PR #403 (ouverte, fork, vers `release/0.7.4`), tête `61ba2cd` | success, même profil (E2E UI skipped) |
| Release Gate | — | **Jamais lancé sur un contenu 0.7.4** (déclencheur `pull_request` vers `main`, `release-gate.yml:3-6`) |
| `fix/0.7.4-editor-followups` | — | **Aucun run**, branche non poussée |

L'arbre `f7fc791` (#401 + #402 combinés) n'a donc jamais été testé en CI. Le contenu de #402 non plus, ni seul ni combiné.

### PR #401 : vérifications build / nginx

- **Worker PDF.js** : `frontend/src/features/document/ui/usePdfDocument.ts:3` importe `pdfjs-dist/build/pdf.worker.min.mjs?worker&url` (commit `fbf2763`). Vite le rebundle et l'émet en `dist/assets/pdf.worker.min-DmhzNYGx.js` (1 228 596 octets, IIFE qui s'initialise sur `self`), référencé depuis un chunk. Aucune configuration spécifique dans `frontend/vite.config.js` (inchangé). Même nom haché dans le log du run `43752042089` : build reproductible.
- **Type MIME** : l'image unique installe le nginx Debian (`Dockerfile:28-32`) et écrit le gabarit dans `sites-enabled` (`Dockerfile:65`), donc `mime.types` s'applique : `.js` → `application/javascript`. L'extension `.js` compte : avec `X-Content-Type-Options: nosniff` (`nginx.conf.template:15`), un worker `.mjs` servi en `application/octet-stream` par une table MIME ancienne serait refusé. Même chose pour `frontend/nginx.conf.template:8` (nginx:alpine).
- **Range** : `getDocument({ url: getExportUrl(id, 'pdf'), disableStream, disableAutoFetch, rangeChunkSize: 262144 })` (`usePdfDocument.ts:25-30`). La route d'export renvoie un `FileResponse` (`document-parser/api/documents.py:159-164`) ; Starlette 1.6.0 (`uv.lock:3597-3598`) gère `Range` et pose `accept-ranges: bytes`. `location /api/` (`nginx.conf.template:23-30`, `frontend/nginx.conf.template:17-24`) ne réécrit aucun en-tête de requête : `Range` passe. Le `gzip` ajouté (`nginx.conf.template:4-8`) ne vise que `application/json`, donc ni le PDF ni les réponses 206. Non vérifié en exécution (aucun job sur une PR vers `release/*` ne charge une page avec PDF.js).
- **Lockfile** : `package.json` et l'entrée racine de `package-lock.json` concordent pour toutes les dépendances (contrôle script) ; `pdfjs-dist` 6.5.438 verrouillé, avec `@napi-rs/canvas` et ses binaires par plateforme en optionnel (+278 lignes). `npm ci` vert en local et en CI.
- **Chunk de 501 kB** : `pdf-AVAxhmeW.js` (501,34 kB, 150 kB gzip) déclenche l'avertissement Vite « Some chunks are larger than 500 kB », visible dans le run `43752042089`. Chargé à la demande (`await import('pdfjs-dist')`, `usePdfDocument.ts:22`), donc hors du bundle initial. Avertissement seulement, pas d'échec de build.
- **Taille d'image** : `dist/` passe à 3,7 Mo, dont 1,73 Mo pour PDF.js (chunk + worker). Négligeable devant les images (centaines de Mo). Le gate n'applique **aucun budget** : il avertit au-delà de +10 % (`release-gate.yml:474-475`), et la comparaison ne s'exécute jamais (INFO image-size).
- **Versions** : `frontend/package.json:3` et `package-lock.json:3` = `0.7.3` ; `document-parser/pyproject.toml:3` = `0.0.0` (jamais utilisé : la version runtime vient de `APP_VERSION`, `infra/settings.py:207`, passé en build-arg depuis le nom de branche ou le tag, `release-gate.yml:237-252`, `release.yml:46-48`). Pas de `__version__` côté Python. Attendu avant le gel : en 0.7.3, c'est le commit de gel `99e1230` qui a porté `package.json` à `0.7.3`. Le `CHANGELOG.md:7` est encore sous `[Unreleased]`.

---

## Écarts constatés

### [CRIT] Aucune CI n'a tourné sur la tête de `release/0.7.4` ; la PR #402 a été fusionnée sans un seul job

- **Localisation** : `.github/workflows/ci.yml:3-7` ; `.github/workflows/release-gate.yml:3-6` ; run `44149188645` (PR #402) ; protection de branche `release/0.7.4`
- **Constat** :
  - `f7fc791` n'a qu'un run `Auto-close issues`. La CI ne part pas sur un push `release/**` (`ci.yml:4-5` : `main` seulement).
  - Les deux runs CI de la PR #402 (fork) sont en `failure` sans aucun job : ils attendaient une approbation, le second a été clos au moment du merge. Le code de #402 (`b507aad`) n'a jamais tourné en CI, ni l'arbre combiné #401 + #402.
  - `gh api .../branches/release%2F0.7.4` : `protected: false`, aucun check requis. Rien n'empêche un merge sans CI verte sur une branche de release.
  - La branche auditée (`a6fb539`) n'est pas poussée ; le Release Gate n'a jamais tourné sur 0.7.4 (déjà relevé le 2026-11-13).
  - Atténuation : sur `a6fb539` (qui contient tout `f7fc791`), lint, format, type-check, 1501 tests backend, 586 tests frontend et `vite build` sont verts en local. Restent sans preuve : e2e API sur l'arbre combiné, build de l'image unique, Trivy, smoke, e2e UI.
- **Règle violée** : item 10.1.1 (poids 3).
- **Remédiation** : pousser `fix/0.7.4-editor-followups`, ouvrir la PR vers `release/0.7.4` et attendre la CI verte (couvre #401 + #402 + correctifs). Puis PR `release/0.7.4` → `main` et Release Gate vert avant le tag. Protéger `release/**` avec les checks `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` requis. Effort S.

### [MAJ] La variante `local` publiée (reasoning + modèles, multi-arch) n'est ni construite ni scannée par le gate — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:252` (`build-args: APP_VERSION=...` seul), `:124` (`uv sync --frozen` sans `--group local --group reasoning`) ; `.github/workflows/release.yml:55` (`linux/amd64,linux/arm64`), `:70-73` (`BAKE_MODELS`, `WITH_REASONING` à `true` pour `local`) ; `Dockerfile:86`, `:90`, `:102-106`
- **Constat** : aucun de ces fichiers n'a changé depuis la baseline. Le gate construit `local` sans reasoning ni modèles, en amd64 ; `release.yml` publie l'inverse. Les paquets du groupe `reasoning` ne passent ni par Trivy ni par `pip-audit` avant le tag.
- **Règle violée** : item 10.2.3 (poids 2).
- **Remédiation** : `WITH_REASONING=true` au build `local` du gate et scan de cette image ; `--group local --group reasoning` au `uv sync` du job `dep-audit` ; en option un build `linux/arm64` sans `load`. Effort M.

### [MIN] `.dockerignore` : pas de `frontend/.dockerignore`, `out/` absent, `__pycache__` imbriqués non exclus — inchangé, aggravé

- **Localisation** : `frontend/Dockerfile:6` (`COPY . .` après `npm ci`, `:5`), absence de `frontend/.dockerignore`, `docker-compose.yml:205-206` ; `.dockerignore:33-34` ; `document-parser/.dockerignore:6-7`
- **Constat** :
  - Inchangé : `out/` (13 Mo de vidéos de démo, ignoré par git `.gitignore:65`) part dans le contexte de l'image unique ; les motifs `__pycache__/` et `*.pyc` ne couvrent que le premier niveau.
  - Aggravé par #401 : sur un poste de dev, `frontend/node_modules` (225 Mo) contient maintenant `@napi-rs/canvas-darwin-arm64`, binaire natif tiré par `pdfjs-dist`. Le `COPY . .` du build compose le recopie par-dessus le `node_modules` Linux installé par `npm ci`. Le build Vite ne charge pas ce binaire, le build passe ; mais l'étage mélange des modules de deux plateformes. Sans effet en CI (checkout propre).
- **Règle violée** : item 10.2.4 (poids 1).
- **Remédiation** : créer `frontend/.dockerignore` (`node_modules/`, `dist/`, `*.log`, `.DS_Store`) ; `**/__pycache__/` et `**/*.pyc` ; `out/` dans `.dockerignore`. Effort S.

---

### [INFO] `pdfjs-dist` exige Node ≥ 22.13, les images frontend se construisent en Node 20 — aggravé

- **Localisation** : `Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:174` (`node:20-alpine`) ; `frontend/package-lock.json` (`pdfjs-dist` 6.5.438, `engines.node: ">=22.13.0 || >=24"`) ; `.github/workflows/ci.yml:61` (Node 22)
- **Constat** : le log du run `43752042089` affiche `npm warn EBADENGINE package: 'pdfjs-dist@6.5.438'` sous `node v20.20.2`. Le build passe (npm n'est pas en `engine-strict`, pas de `.npmrc`) et le bundle est identique au build local. Node 20 n'est plus maintenu depuis avril 2026. La CI teste le frontend en Node 22 alors que les images le construisent en Node 20 : l'écart signalé en baseline porte maintenant sur une dépendance d'exécution, plus seulement sur des devDeps.
- **Remédiation** : `node:22-alpine` dans les deux Dockerfiles et dans `docker-compose.dev.yml`. Effort S. À faire avant le gel.

### [INFO] Le chemin d'exécution PDF.js n'est vérifié par aucun job qui tourne sur une PR vers `release/*`

- **Localisation** : `.github/workflows/ci.yml:162` (e2e UI sur `main` seulement) ; `.github/workflows/release-gate.yml:585-658` ; `nginx.conf.template:4-8`
- **Constat** : chargement du worker sous `nosniff`, requêtes `Range` à travers nginx, rendu canvas : rien de tout ça n'est exercé avant le gate. De plus, le gabarit nginx de l'image unique (modifié par #401 pour le gzip) n'est utilisé que par l'image unique ; la CI des PR construit la stack compose avec `frontend/nginx.conf.template`. Une erreur de syntaxe dans `nginx.conf.template` ne serait vue qu'au smoke du gate.
- **Remédiation** : lancer le Release Gate tôt (PR brouillon `release/0.7.4` → `main`) ; un scénario e2e UI `@critical` qui ouvre un document et attend le canvas PDF.js.

### [INFO] `gzip` ne couvre que le JSON, et seulement dans l'image unique

- **Localisation** : `nginx.conf.template:4-8` ; `frontend/nginx.conf.template` (pas de `gzip`)
- **Constat** : `gzip_types application/json` laisse le JS et le CSS non compressés : `pdf-*.js` part en 501 kB au lieu de 150 kB, le worker en 1,2 Mo. La stack compose n'a aucun gzip : les deux déploiements se comportent différemment.
- **Remédiation** : ajouter `application/javascript text/css image/svg+xml` à `gzip_types` et aligner `frontend/nginx.conf.template`. Effort S.

### [INFO] Le job `Unit tests` du Release Gate ne peut pas échouer sur un test rouge — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:82-86`, `:88-92`
- **Constat** : `pytest ... | tee` et `npm run test:run | tee` sous `bash -e` sans `pipefail` : le code de sortie est celui de `tee`. Atténuation : les jobs de `ci.yml:46-47`, `:74-75` n'utilisent pas `tee`.
- **Remédiation** : `set -o pipefail` en tête des deux blocs, ou `defaults.run.shell: bash` au niveau du workflow. Effort S.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:189-193` ; `.gitignore:50-51` (`profiles/` absent du dépôt)
- **Remédiation** : versionner le script ou supprimer le job et sa ligne du résumé.

### [INFO] `Image size check` ne compare jamais rien et n'impose aucun budget — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:441`, `:474-475`
- **Constat** : `IMAGE_NAME` = `github.repository` contient des majuscules, `docker pull` échoue, la comparaison tombe sur « no previous baseline ». Même si elle tournait, ce ne serait qu'un `::warning` au-delà de +10 %.
- **Remédiation** : `${IMAGE_NAME,,}` ; si un budget est voulu, un seuil bloquant explicite.

### [INFO] Le formatage n'est vérifié par aucun job CI — inchangé

- **Localisation** : `.github/workflows/ci.yml:43-47`, `:68-78` ; `.github/workflows/release-gate.yml:49-56`
- **Constat** : 10.1.5 est conforme grâce aux vérifications locales, pas à la CI.
- **Remédiation** : `uv run ruff format --check .` et `npx prettier --check src/` dans `ci.yml` et le job `lint-typecheck`. Effort S.

### [INFO] Matrices en fail-fast — inchangé (corrigé en partie)

- **Localisation** : `.github/workflows/release-gate.yml:228-230` ; `.github/workflows/release.yml:21-23`
- **Remédiation** : `fail-fast: false`. Effort S.

### [INFO] Pas de CI sur push `release/**` ; une PR vers `release/*` n'a ni image unique, ni Trivy, ni smoke, ni e2e UI — inchangé, précisé

- **Localisation** : `.github/workflows/ci.yml:3-7`, `:137-143`, `:162`
- **Constat** : une PR `fix/*` → `release/0.7.4` reçoit ruff, eslint, `vue-tsc`, tests unitaires, `vite build`, build compose `remote` (images `document-parser/Dockerfile` + `frontend/Dockerfile`), santé et e2e API en `@smoke,@regression,@e2e` (`ci.yml:140-141`). Elle ne reçoit pas : le `Dockerfile` racine (image publiée), la variante `local`, Trivy, `pip-audit`/`npm audit`, le smoke de l'image unique, l'e2e UI. Couverture suffisante pour le code applicatif, pas pour l'image livrée.
- **Remédiation** : `release/**` dans `on.push.branches` ; un job léger `docker build --target remote .` + smoke dans `ci.yml` pour les PR vers `release/**`.

### [INFO] Permissions du `GITHUB_TOKEN` non restreintes dans `ci.yml` et `release-gate.yml`

- **Localisation** : `.github/workflows/ci.yml` et `.github/workflows/release-gate.yml` (pas de bloc `permissions:` de niveau workflow ; seuls `release-gate.yml:408-409` et `:694-696` en ont par job)
- **Constat** : `gh api .../actions/permissions/workflow` → `default_workflow_permissions: write`. Pour une PR interne, les jobs de build et de test reçoivent un jeton en écriture. Les PR de fork restent en lecture. Préexistant, non relevé jusqu'ici. Secrets : seul `GITHUB_TOKEN` est utilisé, passé par `env:` (`release-gate.yml:423`, `:716`, `:819`) ; seul `github.event.pull_request.number` (entier) est interpolé dans un script (`:821`).
- **Remédiation** : `permissions: contents: read` en tête des deux workflows. Effort S.

### [INFO] Actions épinglées par tag, pas par SHA — inchangé

- **Localisation** : `.github/workflows/ci.yml:26-32` (`@v4`, `@v5`), `release-gate.yml:26` (`@v4.3.1`), `:358` (`aquasecurity/trivy-action@v0.35.0`), `release.yml:26-50`
- **Constat** : tags majeurs flottants dans `ci.yml` et `release.yml`, tags précis dans le gate. `sha_pinning_required: false` au niveau du dépôt. Les runs portent l'annotation « Node.js 20 is deprecated » et « setup-java v4 is deprecated ».
- **Remédiation** : SHA pour les actions tierces (Trivy, setup-uv, setup-chrome, docker/*), montée de version des actions officielles.

### [INFO] `uv` dans les images d'exécution ; pas de `HEALTHCHECK` ; image unique lancée en root — inchangé

- **Localisation** : `Dockerfile:36`, `document-parser/Dockerfile:17` ; `Dockerfile:65` (nginx en root, uvicorn via `su appuser`, pas de `USER`) ; aucun `HEALTHCHECK` dans `Dockerfile`, `document-parser/Dockerfile`, `frontend/Dockerfile`, ni healthcheck sur `document-parser` dans `docker-compose.yml:141-201`
- **Constat** : multi-stage correct (`Dockerfile:11`, `:22` ; seul `dist` est copié, `:48`) ; `uv sync --frozen --no-dev` partout (`Dockerfile:42`, `:103-105`, `document-parser/Dockerfile:24`).
- **Remédiation** : inchangée.

### [INFO] Suppressions Trivy : échéance commune au 2026-12-31 — inchangé

- **Localisation** : `.trivyignore.yaml:20`, `:38`, `:44`, `:50`, `:56`
- **Constat** : 43 jours restants. Tout gate lancé après le 31 décembre échouera (#378).

### [INFO] PR #403 ouverte vers `release/0.7.4` recoupe un correctif local

- **Localisation** : PR #403 (`fix/393-editor-chunks-stale-unknown-source`, CI `44382595574` verte) ; correctif local #393 sur `a6fb539`
- **Constat** : deux branches traitent #393. Risque de conflit au moment de fusionner la branche locale. Hors périmètre CI, signalé pour l'ordre des merges.

---

## Delta vs audit du 2026-11-13

| Écart baseline (@ `eade7fa`) | Statut @ `a6fb539` | Détail |
|------------------------------|---------------------|--------|
| 10.1.1 conforme (provisoire) | **Régression → [CRIT]** | Nouveau fait : #402 fusionnée sans CI (runs à 0 job), aucun run sur `f7fc791`, branche de release non protégée |
| 10.1.5 conforme (présumé) | **Conforme, vérifié** | `ruff format --check` et `prettier --check` propres en local |
| [MAJ] 10.2.3 variante `local` | Toujours ouvert | Fichiers inchangés |
| [MIN] 10.2.4 `.dockerignore` | Toujours ouvert, aggravé | + binaires natifs `@napi-rs/canvas` de l'hôte copiés dans l'étage compose |
| [INFO] Release Gate jamais lancé | Absorbé dans le CRIT | — |
| [INFO] `Unit tests` sans `pipefail` | Toujours présent | `release-gate.yml:82-92` inchangé |
| [INFO] `Audit checks` faux vert | Toujours présent | — |
| [INFO] `Image size check` | Toujours présent | Précisé : aucun budget bloquant |
| [INFO] Format hors CI | Toujours présent | — |
| [INFO] fail-fast | Toujours présent (partiel) | — |
| [INFO] Déclencheurs | Toujours présent | Précisé : ce qu'une PR vers `release/*` couvre et ne couvre pas |
| [INFO] `uv` dans les images, durcissement Docker | Toujours présent | Fusionnés en une INFO |
| [INFO] Trivy 2026-12-31 | Toujours présent | — |
| [INFO] Node 20 | **Aggravé** | `pdfjs-dist` (dépendance d'exécution) exige Node ≥ 22.13, `EBADENGINE` en CI |
| [INFO] Nouveautés hors e2e | Toujours présent | Recentré sur PDF.js |
| — | [INFO] nouveau | `gzip` limité au JSON, absent de la stack compose |
| — | [INFO] nouveau | Permissions `GITHUB_TOKEN` en écriture par défaut |
| — | [INFO] nouveau | Actions épinglées par tag |
| — | [INFO] nouveau | PR #403 en doublon de #393 |

Score : 85 → **70** (−15). La baisse vient entièrement de 10.1.1 (poids 3). Aucune régression de build : les workflows, Dockerfiles et compose n'ont pas changé depuis la baseline ; #401 ajoute `pdfjs-dist`, le gzip nginx et un worker émis en `.js`, et le build compose avec ces changements est vert en CI.

---

## Points positifs

- **Worker PDF.js correctement livré** : `?worker&url` produit un `.js` haché, servi avec un MIME JavaScript malgré `nosniff` ; PDF.js est chargé à la demande, hors bundle initial.
- **Range de bout en bout sans configuration fragile** : `FileResponse` gère `Range`, nginx relaie l'en-tête, le gzip ne touche pas le PDF.
- **Lockfile cohérent et build reproductible** : `package.json` et `package-lock.json` concordent, mêmes noms hachés en local et en CI.
- **Pas de nouvelle variable d'environnement** : le cache de previews est borné en dur (64 Mo), sans réglage à documenter.
- **Formatage maintenant vérifié** (ruff et prettier), et non plus présumé.
- **Code applicatif vert en local sur `a6fb539`** : 1501 tests backend, 586 tests frontend, lint, type-check, build.

---

## Verdict partiel : NO-GO

70/100, 1 CRITICAL, 1 MAJOR, 1 MINOR → **NO-GO** (règle absolue : tout CRIT non résolu). Le CRIT est un manque de preuve CI, pas un échec connu, et se lève vite : pousser `fix/0.7.4-editor-followups`, obtenir la CI verte sur la PR vers `release/0.7.4` (score 85, GO conditionnel au gate), puis Release Gate vert sur la PR vers `main` avant le tag. À faire en même temps, effort S : `node:22-alpine` dans les deux Dockerfiles et `docker-compose.dev.yml`, `set -o pipefail` sur `Unit tests`, `out/` dans `.dockerignore`, protection de `release/**` avec checks requis. Le MAJ (variante `local` publiée non vérifiée) reste au plan de remédiation.

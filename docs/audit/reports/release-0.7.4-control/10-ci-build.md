# Rapport d'audit : CI / Build

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche auditée** : `fix/0.7.4-editor-followups` @ `a12b744` (working tree). Branche **non poussée** : GitHub ne connaît que `release/0.7.4` @ `f7fc791`.
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/10-ci-build.md`, 70/100).
**Mode** : lecture statique des workflows, Dockerfiles, `.dockerignore`, compose et gabarits nginx du working tree ; `gh run list --branch release/0.7.4` et `gh pr list --state open` en lecture seule. Exécutions locales fournies par le commanditaire sur `a12b744`, non relancées : `ruff check` et `ruff format --check` propres, pytest 1559 passed / 15 skipped ; `npm ci` (Node 26), eslint, prettier, `vue-tsc` propres, vitest 605 passed (65 fichiers), `vite build` OK. Aucun build Docker, aucun nginx lancé, aucun workflow déclenché : tous les changements CI/build de la remédiation sont revus **par lecture**, aucun n'a été exécuté.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 9 / 11 |
| Score | **75 / 100** |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 14 |

Poids total : 20. Poids non conformes : 10.1.1 (3) + 10.2.3 (2) = 5. `score = 15 / 20 * 100 = 75`.

### Tableau de recalcul

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **Non** | Inchangé côté GitHub : seul `Auto-close issues` a tourné sur `f7fc791` (run `44399691994`) ; aucun run CI ni Release Gate sur 0.7.4 ; `a12b744` non poussé. Le correctif `.github/workflows/ci.yml:5` ne prendra effet qu'au premier push sur `release/**` qui le contient (voir CRIT) |
| 10.1.2 | Warnings ESLint résolus | 1 | Oui | eslint propre en local sur `a12b744` |
| 10.1.3 | Warnings Ruff résolus | 1 | Oui | `ruff check` propre en local sur `a12b744` |
| 10.1.4 | Type-check frontend | 2 | Oui | `vue-tsc` propre ; `frontend/package.json:8` l'enchaîne avant `vite build` |
| 10.1.5 | Formatting conforme | 1 | Oui | `ruff format --check` et `prettier --check` propres en local |
| 10.2.1 | `docker compose build` réussit | 3 | Oui (provisoire, revue statique) | Dernière preuve d'exécution : run `43752042089` (`de5fe66`), sur des entrées de build **antérieures** : Node 20, sans `frontend/.dockerignore`, ancien gabarit nginx. Les nouvelles entrées n'ont jamais été construites ; la revue ci-dessous ne trouve aucun défaut bloquant (`COPY` toujours satisfaits, binaires musl présents dans le lockfile) |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | Oui (provisoire, revue statique) | Gabarits nginx relus ligne à ligne, syntaxe valide. Une erreur nginx serait visible : le conteneur frontend sortirait et `docker compose up --wait` (`ci.yml:108`) échouerait ; dans l'image unique, `nginx && exec su ...` (`Dockerfile:65`) s'arrête et le smoke (`release-gate.yml:298-317`) échoue |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Non** | Inchangé : `release-gate.yml:254` (`APP_VERSION` seul), `:126` (`uv sync --frozen` sans groupes) ; `release.yml:70` publie `local` avec reasoning et modèles (voir MAJ) |
| 10.2.4 | `.dockerignore` à jour | 1 | **Oui** | `frontend/.dockerignore:4-9` créé ; `out/` (`.dockerignore:52`) et `__pycache__`/`*.pyc` imbriqués (`.dockerignore:34`, `:36`) couverts. Résidus sans effet sur l'image publiée (INFO) |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | `nginx.conf.template:19-21`, `:36-43` ; `frontend/nginx.conf.template:19-21`, `:36-43`. Le nouveau `location /assets/` (`:26-34`) ne capte ni `/`, ni `/api/`, ni `/mcp`, ni aucune route SPA (aucune route `/assets` dans `frontend/src`) |
| 10.3.2 | Variables d'environnement documentées | 1 | Oui | Aucune nouvelle variable ; le nouveau bloc nginx ne référence aucune variable d'environnement |

### État GitHub Actions (relevé le 2026-11-18, après remédiation)

| Run | Cible | Résultat |
|-----|-------|----------|
| `44399691994` | push `release/0.7.4` @ `f7fc791` | success, `Auto-close issues` seulement. **Toujours aucun run CI sur la tête de `release/0.7.4`** |
| `44171965618` | push `release/0.7.4` @ `b507aad` (merge #402) | success, `Auto-close issues` seulement |
| Release Gate | — | Jamais lancé sur 0.7.4 |
| `fix/0.7.4-editor-followups` | — | Aucun run, branche non poussée |

PR ouvertes vers `release/0.7.4` : #403 (fork, recoupe le correctif local #393). Rien n'a bougé sur GitHub depuis le re-audit.

---

## Revue des changements CI/build de la remédiation

### `c4c0474` — `ci.yml` : CI sur push `release/**`

- **Changement** : `.github/workflows/ci.yml:5` `branches: [main, 'release/**']`.
- **Jobs lancés sur un push `release/*`** : `backend` et `frontend` (pas de `if:`), `e2e` (`:80-158`, pas de `if:`, `needs: [backend, frontend]`) avec la portée complète `@smoke,@regression,@e2e` : la condition `:140` teste déjà `github.ref == refs/heads/release/*`, donc elle s'applique maintenant aux pushs. `e2e-ui` reste `skipped` (`:162`, `main` seulement).
- **Concurrence** : `group: ci-${{ github.ref }}` (`:10-12`). Push : `refs/heads/release/0.7.4` ; PR : `refs/pull/N/merge`. Les groupes sont distincts, un push n'annule pas la PR ni l'inverse. En revanche, deux merges rapprochés sur `release/0.7.4` annulent le run du premier (`cancel-in-progress: true`) : le commit intermédiaire reste sans preuve, seule la tête est vérifiée. C'est le même comportement que sur `main` et c'est la tête qui compte pour 10.1.1. **Risque faible** (INFO).
- **Double exécution** : une PR fusionnée produit un run `pull_request` (sur le merge ref, SHA différent) puis un run `push` sur le commit de merge. Ce n'est pas un doublon : c'est précisément la preuve qui manquait sur la tête. Pas de push-trigger sur les branches `fix/*`, donc pas de double run pour une PR interne en cours.
- **Coût** : chaque merge sur une branche de release reconstruit la stack compose (`ci.yml:108`), démarre docling-serve et passe la portée Karate complète. Acceptable pour une branche de release (quelques merges par cycle).
- **Secrets** : aucun secret dans `ci.yml` (pas de `secrets.` ; seul le `GITHUB_TOKEN` implicite de `actions/checkout`). Un push n'a donc besoin de rien qu'un fork n'aurait pas. Surtout, le run `push` d'un merge de fork tourne dans le contexte du dépôt **sans approbation** : c'est ce qui comble le trou de #402 (runs de PR bloqués en attente d'approbation). Le jeton est en écriture par défaut (INFO permissions, inchangée), sur du code déjà fusionné par un mainteneur.
- **Prise d'effet** : GitHub lit le workflow dans le commit poussé. Le déclencheur ne vaudra qu'à partir du premier push sur `release/0.7.4` qui contient `c4c0474` (le merge de la PR des correctifs). Rien ne tourne rétroactivement sur `f7fc791`.
- **Verdict : OK.**

### `c4c0474` — `release-gate.yml` : `set -o pipefail`

- **Changement** : `.github/workflows/release-gate.yml:84` et `:91`.
- **Effet** : sans `shell:` explicite, GitHub lance `bash -e {0}` ; avec `pipefail`, un pytest ou un vitest rouge rend le pipeline `| tee` non nul et `bash -e` fait échouer l'étape. Correct.
- **Suite du job** : `Upload test results` (`:96-101`) a `if: always()` : il est atteint et téléverse ce qui existe. Le job `unit-tests` finit en `failure`, `needs.unit-tests.result` = `failure` (`:722`), la boucle `:734-738` passe le verdict à `NO-GO`. Aucun job ne dépend de `unit-tests` (`docker-build` n'a pas de `needs`), rien n'est sauté par ricochet.
- **Effet de bord** : `Frontend tests` (`:89-94`) n'a pas de `if:`. Si les tests backend échouent, l'étape frontend est maintenant **sautée** : un run rouge ne dit plus si le frontend est vert, et `/tmp/frontend-tests.txt` manque à l'artefact. Avant, l'étape tournait toujours (puisque rien n'échouait). **Risque faible** (INFO). Correctif : `if: ${{ !cancelled() }}` sur `Frontend tests` (`:89`).
- **Autres `| tee` du gate** :
  - `:135` `pip-audit | tee ... || true` : masquage voulu, l'étape est informative (`continue-on-error`, `:131`) et le bloquant est Trivy.
  - `:156` `npm audit 2>&1 | tee /tmp/npm-audit.txt` : masque le code de `npm audit`, mais c'est voulu : `continue-on-error` (`:152`) et le bloquant est le décompte `critical` (`:158-169`) puis `Fail on critical vulnerabilities` (`:178-182`).
  - `:194` `bash profiles/fastapi-vue/commands.sh | tee` : masque l'échec. Le script n'existe pas dans le dépôt (`profiles/` ignoré), donc `steps.audit.outcome` vaut toujours `success` et `:217` ne se déclenche jamais : c'est le faux vert déjà relevé (INFO). Y ajouter `pipefail` sans versionner le script rendrait le gate rouge : ne pas toucher sans décider du sort du job.
- **Verdict : OK**, avec un risque faible (étape frontend sautée).

### `10ecb05` — Node 22 dans les images

- **Changement** : `Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:174` → `node:22-alpine` ; `CONTRIBUTING.md` « Node 22 ».
- **Cohérence** : `actions/setup-node` en `node-version: 22` dans `ci.yml:61` et `release-gate.yml:39`, `:75`, `:120`. Même majeure en CI et dans les images. `pdfjs-dist` : `engines.node` `>=22.13.0 || >=24` (`frontend/package-lock.json`) ; `node:22-alpine` suit la dernière 22.x, au-delà de 22.13 : l'avertissement `EBADENGINE` doit disparaître.
- **Dépendances natives** : seuls `esbuild` (binaire Go), `fsevents` (macOS, optionnel) et `vue-demi` ont un script d'installation ; `@napi-rs/canvas` est N-API (indépendant de l'ABI Node) et le lockfile contient `@napi-rs/canvas-linux-x64-musl`, `-linux-arm64-musl`, `@rollup/rollup-linux-x64-musl`, `-arm64-musl` : `npm ci` sur Alpine trouve ses binaires en amd64 comme en arm64. `lockfileVersion: 3` (`package-lock.json:4`) est lu par npm 10 (livré avec Node 22) comme par npm 11.
- **Rien d'autre sur Node 20** dans le dépôt hors rapports d'audit (recherche `node:20`, `Node 20`, `node-version: 20`).
- **Dev compose** : le volume nommé `frontend_node_modules` (`docker-compose.dev.yml:180`) a été rempli sous Node 20. La commande `npm install && npm run dev` (`:187`) le remet à jour à chaque démarrage, et aucun module natif ne dépend de l'ABI Node : pas de casse attendue. En cas de doute, `docker volume rm` sur ce volume.
- **Verdict : OK.** Non vérifié en exécution : `npm ci` sous `node:22-alpine` (le `npm ci` local a tourné sous Node 26).

### `10ecb05` — `.dockerignore`

- **Image unique** (contexte racine, `.dockerignore`) : `COPY frontend/package*.json` (`Dockerfile:16`), `COPY frontend/` (`:18`), `COPY document-parser/pyproject.toml document-parser/uv.lock` (`:41`), `COPY document-parser/` (`:45`), `COPY nginx.conf.template` (`:51`). Ajouts : `document-parser/**/__pycache__/` (`.dockerignore:34`), `document-parser/**/*.pyc` (`:36`), `out/` (`:52`). Aucun ne retire une source de `COPY` : `out/` est ancré à la racine (pas de `frontend/out` ni `document-parser/out` concernés), les motifs `**` ne visent que des caches. `frontend/.dockerignore` n'est **pas** lu pour ce build (seul le `.dockerignore` du contexte compte) ; `frontend/node_modules/` et `frontend/dist/` y restent exclus par `.dockerignore:28-29`.
- **Image frontend** (contexte `frontend/`, `docker-compose.yml:205-206`) : `COPY package*.json ./` (`frontend/Dockerfile:4`), `COPY . .` (`:6`), `COPY nginx.conf.template` (`:12`). `frontend/.dockerignore:4-9` exclut `node_modules/`, `dist/`, `.vite/`, `coverage/`, `*.log`, `.DS_Store` : aucun n'est requis par `npm ci` ni `npm run build` (`vue-tsc --noEmit && vite build`, `frontend/package.json:8`), ni par le second étage. Le binaire hôte `@napi-rs/canvas-darwin-arm64` n'entre plus dans l'étage de build.
- **Dev compose** : le service frontend n'a pas de `build:` (`docker-compose.dev.yml:172-187`), il monte `./frontend` en bind mount : aucun `.dockerignore` ne s'applique. `document-parser` y garde son propre contexte (`document-parser/.dockerignore`, non modifié).
- **Résidus** (INFO) : `document-parser/.dockerignore:6-7` reste non récursif (`__pycache__/`, `*.pyc`) pour les builds compose ; 15 dossiers `__pycache__` imbriqués existent en local. `frontend/.dockerignore` ne liste pas `.claude/`, `.ruff_cache/`, `CLAUDE.md`, `frontend.iml`, présents dans `frontend/` : ils entrent dans l'étage de build (pas dans l'image finale, qui ne reçoit que `dist`).
- **Verdict : OK**, résidus mineurs.

### `397ff32` — gabarits nginx

Contenu identique dans les deux gabarits pour le bloc ajouté (`nginx.conf.template:5`, `:23-34` ; `frontend/nginx.conf.template:4-8`, `:23-34`).

- **Syntaxe** : `gzip_types` (contexte `http/server/location`), `expires 1y` (`http/server/location/if in location`), `add_header` (idem), `try_files $uri =404` (`server/location`) : tous valides là où ils sont. Points-virgules et accolades équilibrés (relu ligne à ligne). `location /assets/` est un préfixe plus long que `location /`, il gagne pour `/assets/*` ; pas de location regex qui pourrait passer devant ; `location = /mcp` est exact.
- **`gzip_types`** : pas de `text/html` (toujours inclus, sa mention produirait l'avertissement « duplicate MIME type ») et aucun doublon dans la liste. `application/javascript` et `text/javascript` sont listés tous les deux : la table `mime.types` de nginx Debian (`Dockerfile:28-32`, base `python:3.12-slim`) mappe `.js` sur `application/javascript`, et `nginx:alpine` suit la table amont ; lister les deux couvre l'une ou l'autre table. `gzip on` est déjà posé au niveau `http` dans le `nginx.conf` Debian : redéfinir au niveau `server` est permis. Le gabarit frontend reçoit enfin le gzip : les deux déploiements se comportent pareil.
- **Range / PDF** : `application/pdf` n'est pas dans `gzip_types`, et le PDF passe par `/api/` (proxy). Les réponses 206 de l'export PDF ne sont pas touchées.
- **SPA** : `index.html`, `logo.png`, `favicon.svg` sont à la racine de `dist/` (vérifié dans `frontend/dist`), donc servis par `location /` sans `expires` : pas de cache d'un an sur ce qui n'est pas haché. Les 52 fichiers de `frontend/dist/assets/` portent tous un suffixe de hachage (contrôle par motif, aucun fichier non haché, worker `pdf.worker.min-DmhzNYGx.js` compris). `frontend/public/` ne contient pas de dossier `assets/`. Un asset absent (hachage d'une version précédente) renvoie 404 au lieu de `index.html` servi en `text/html` puis refusé sous `nosniff` : c'est une amélioration.
- **En-têtes** : `add_header` dans un `location` annule l'héritage du niveau `server` ; les quatre en-têtes de sécurité sont répétés avec `always` (`:29-32`) : correct. `expires 1y` émet `Cache-Control: max-age=31536000` et `add_header Cache-Control "public, immutable"` en émet un second : deux lignes `Cache-Control`, que les navigateurs fusionnent (RFC 9110). Correct, un peu redondant ; `add_header Cache-Control "public, max-age=31536000, immutable";` sans `expires` donnerait une seule ligne. `expires` ne s'applique qu'aux 2xx/3xx et le `Cache-Control` sans `always` non plus : un 404 sous `/assets/` n'est pas mis en cache pour un an.
- **`envsubst`** : l'image unique substitue seulement `${NGINX_MAX_BODY_SIZE}` (`Dockerfile:65`). L'image frontend passe par `/etc/nginx/templates` (`frontend/Dockerfile:12`) : le script d'entrée de l'image nginx substitue **toutes les variables d'environnement définies**. Le nouveau bloc ne contient que `$uri` (comme `location /`) : il n'existe pas de variable d'environnement `uri`, il survit comme `$uri`, `$host`, `$remote_addr`, `$http_host` existants. Aucune autre occurrence de `$` dans les lignes ajoutées.
- **Verdict : OK.** Non vérifié en exécution : `nginx -t`, en-têtes réels, compression effective.

### `397ff32` — `logo.png`

- `frontend/public/logo.png` : PNG 256 x 256, 61 510 octets. Consommateurs : `frontend/index.html:7` (favicon), `frontend/src/app/App.vue:19` (affiché à 28 px, `:264-266`), `frontend/src/pages/HomePage.vue:5` (72 px, `:137-139`), `frontend/src/pages/StudioPage.vue:5` (64 px, `:699-701`). 256 px couvre 72 px en écran 3x (216 px).
- Aucun autre consommateur : la doc MkDocs utilise `docs/images/logo.png` (`mkdocs.yml:9-10`, fichier distinct, toujours 1024 px) ; aucune référence à `public/logo.png` dans le README, `document-parser/mcp_adapter`, le plugin Claude ou des balises Open Graph.
- **Verdict : OK.**

---

## Écarts constatés

### [CRIT] Aucune CI n'a tourné sur la tête de `release/0.7.4` — inchangé, correctif de déclencheur en attente

- **Localisation** : `.github/workflows/ci.yml:3-7` (corrigé dans le working tree, pas sur GitHub) ; `.github/workflows/release-gate.yml:3-6` ; run `44399691994` ; branche `release/0.7.4` non protégée (relevé du re-audit, non re-vérifié)
- **Constat** :
  - Rien n'a bougé sur GitHub : `f7fc791` n'a que `Auto-close issues` ; le contenu de #402 et l'arbre combiné #401 + #402 n'ont jamais tourné en CI ; le Release Gate n'a jamais tourné sur 0.7.4 ; `a12b744` n'est pas poussé.
  - `ci.yml:5` ajoute `release/**` au déclencheur `push`. Le défaut de méthode (un merge sur une branche de release sans run) est donc corrigé **pour l'avenir**, mais un changement local ne produit aucune preuve. 10.1.1 se lit sur les runs, comme dans le re-audit.
  - Atténuation : sur `a12b744`, lint, format, type-check, 1559 tests backend, 605 tests frontend et `vite build` sont verts en local. Restent sans preuve : build compose avec Node 22 et le nouveau gabarit nginx frontend, e2e API sur l'arbre combiné, image unique, Trivy, smoke, e2e UI.
- **Règle violée** : item 10.1.1 (poids 3).
- **Ce qui le fermera** :
  1. Pousser `fix/0.7.4-editor-followups`, ouvrir la PR vers `release/0.7.4` : le run `pull_request` (`Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` en portée complète) doit être vert. Ce run construit la stack compose avec `frontend/Dockerfile` en Node 22, `frontend/.dockerignore` et le nouveau gabarit nginx frontend : il valide aussi 10.2.1 et 10.2.2 en exécution.
  2. Fusionner : le commit de merge contient `ci.yml:5`, donc le **premier run `push` CI** sur `release/0.7.4` part. Vert, il établit la preuve sur la tête de la branche de release. À ce point 10.1.1 redevient conforme (provisoire), score **90**.
  3. Avant le tag : PR `release/0.7.4` → `main`, Release Gate vert (image unique `remote` et `local` avec le nouveau `Dockerfile` et `nginx.conf.template`, smoke, Trivy, e2e UI).
  4. Toute PR fusionnée ensuite (#403 par exemple) doit avoir son run `push` vert sur le nouveau commit de tête.
  5. Protéger `release/**` avec les trois checks requis, sinon une PR de fork peut encore être fusionnée sans run `pull_request` (seul le run `push` d'après coup rattraperait).

### [MAJ] La variante `local` publiée (reasoning + modèles, multi-arch) n'est ni construite ni scannée par le gate — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:254` (`build-args: APP_VERSION=...` seul), `:126` (`uv sync --frozen` sans `--group local --group reasoning`) ; `.github/workflows/release.yml:70` (`build-args` avec `BAKE_MODELS`, `WITH_REASONING`) ; `Dockerfile:86`, `:90`, `:102-106`
- **Constat** : non traité par la remédiation. Le gate construit `local` sans reasoning ni modèles en amd64 ; `release.yml` publie l'inverse. Le groupe `reasoning` ne passe ni par Trivy ni par `pip-audit` avant le tag.
- **Règle violée** : item 10.2.3 (poids 2).
- **Remédiation** : `WITH_REASONING=true` au build `local` du gate et scan de cette image ; `--group local --group reasoning` au `uv sync` de `dep-audit` ; en option un build `linux/arm64` sans `load`. Effort M.

---

### [INFO] Le chemin `push release/**` et les nouveaux réglages nginx ne sont vérifiés par aucun run

- **Localisation** : `.github/workflows/ci.yml:5` ; `nginx.conf.template:26-34` ; `frontend/nginx.conf.template:4-8`, `:26-34`
- **Constat** : toutes les modifications CI/build sont revues par lecture seulement. Un run CI prouvera que nginx démarre et que les images se construisent ; **aucun job** ne vérifie les en-têtes (`Cache-Control`, `Content-Encoding: gzip`, en-têtes de sécurité sur `/assets/`). Le gabarit de l'image unique n'est exercé qu'au smoke du gate.
- **Remédiation** : dans le smoke du gate (`release-gate.yml:298-334`), `curl -sI -H 'Accept-Encoding: gzip'` sur un fichier de `/assets/` (repéré dans `index.html`) avec contrôle de `immutable`, `gzip` et `nosniff`, et `curl -sI /` sans `immutable`. Effort S.

### [INFO] `pipefail` : l'étape `Frontend tests` du gate est sautée si les tests backend échouent

- **Localisation** : `.github/workflows/release-gate.yml:89` (pas de `if:`), `:84`
- **Constat** : effet de bord du correctif. Le verdict reste juste (`unit-tests` = `failure`, `NO-GO`), mais on perd le résultat frontend dans ce cas.
- **Remédiation** : `if: ${{ !cancelled() }}` sur `Frontend tests`. Effort XS.

### [INFO] `cancel-in-progress` annule le run d'un merge intermédiaire sur `release/**`

- **Localisation** : `.github/workflows/ci.yml:10-12`
- **Constat** : deux merges rapprochés : le premier commit de merge reste « cancelled ». La tête est toujours vérifiée.
- **Remédiation** (optionnelle) : `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.

### [INFO] Résidus `.dockerignore`

- **Localisation** : `document-parser/.dockerignore:6-7` ; `frontend/.dockerignore`
- **Constat** : `__pycache__/` et `*.pyc` non récursifs pour le contexte `document-parser` (builds compose, pas l'image publiée) ; `frontend/.dockerignore` ne liste pas `.claude/`, `.ruff_cache/`, `CLAUDE.md`, `*.iml` (étage de build seulement).
- **Remédiation** : `**/__pycache__/` et `**/*.pyc` dans `document-parser/.dockerignore` ; `.claude/`, `.ruff_cache/`, `*.iml`, `CLAUDE.md` dans `frontend/.dockerignore`. Effort XS.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:194` (`| tee` sans `pipefail`, `continue-on-error`), `:217` ; `profiles/` absent du dépôt
- **Remédiation** : versionner le script ou supprimer le job et sa ligne du résumé. Ne pas y ajouter `pipefail` avant.

### [INFO] `Image size check` ne compare jamais rien et n'impose aucun budget — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:443`
- **Remédiation** : `${IMAGE_NAME,,}` ; seuil bloquant explicite si un budget est voulu.

### [INFO] Le formatage n'est vérifié par aucun job CI — inchangé

- **Localisation** : `.github/workflows/ci.yml:43-47`, `:68-78` ; `.github/workflows/release-gate.yml:49-56`
- **Remédiation** : `uv run ruff format --check .` et `npx prettier --check src/` dans `ci.yml` et `lint-typecheck`.

### [INFO] Matrice de build du gate et de `release.yml` en fail-fast — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:231` ; `.github/workflows/release.yml:22` (le scan, `release-gate.yml:343`, est déjà en `fail-fast: false`)
- **Remédiation** : `fail-fast: false`.

### [INFO] Une PR vers `release/*` n'a ni image unique, ni Trivy, ni smoke, ni e2e UI — précisé

- **Localisation** : `.github/workflows/ci.yml:80-158`, `:162`
- **Constat** : le volet « pas de CI sur push `release/**` » est corrigé (`ci.yml:5`). Reste : le `Dockerfile` racine (image publiée) et le gabarit `nginx.conf.template` ne sont construits et démarrés qu'au gate.
- **Remédiation** : un job léger `docker build --target remote .` + smoke dans `ci.yml` pour `release/**`.

### [INFO] Permissions du `GITHUB_TOKEN` non restreintes dans `ci.yml` et `release-gate.yml` — inchangé

- **Localisation** : pas de bloc `permissions:` de niveau workflow dans `ci.yml` ; `release-gate.yml` n'en a que par job (`:410`, `:696`)
- **Constat** : les runs `push` sur `release/**` ajoutés par `c4c0474` reçoivent eux aussi un jeton en écriture.
- **Remédiation** : `permissions: contents: read` en tête des deux workflows.

### [INFO] Actions épinglées par tag, pas par SHA — inchangé

- **Localisation** : `.github/workflows/ci.yml:26-32`, `:185` ; `release-gate.yml` (tags précis) ; `release.yml`

### [INFO] `uv` dans les images d'exécution ; pas de `HEALTHCHECK` ; image unique lancée en root — inchangé

- **Localisation** : `Dockerfile:36`, `:65` ; `document-parser/Dockerfile` ; `docker-compose.yml:141-201`

### [INFO] Suppressions Trivy : échéance commune au 2026-12-31 — inchangé

- **Localisation** : `.trivyignore.yaml:20`, `:38`, `:44`, `:50`, `:56`
- **Constat** : 43 jours restants ; tout gate lancé après le 31 décembre échouera (#378).

### [INFO] PR #403 ouverte vers `release/0.7.4` recoupe le correctif local #393 — inchangé

- **Constat** : ordre des merges à décider ; si #403 passe après la branche des correctifs, son merge déclenchera lui aussi un run `push` (bon), mais le conflit avec #393 est à régler.

---

## Delta vs re-audit a6fb539

| Écart re-audit (@ `a6fb539`) | Statut @ `a12b744` | Détail |
|------------------------------|---------------------|--------|
| [CRIT] 10.1.1 aucune CI sur la tête de `release/0.7.4` | **Toujours ouvert** | Déclencheur corrigé localement (`ci.yml:5`), aucune preuve nouvelle sur GitHub |
| [MAJ] 10.2.3 variante `local` | Toujours ouvert | Fichiers inchangés |
| [MIN] 10.2.4 `.dockerignore` | **Fermé** | `frontend/.dockerignore`, `out/`, `**/__pycache__` ; résidus en INFO |
| [INFO] Node 20 vs `pdfjs-dist` ≥ 22.13 | **Fermé** | `node:22-alpine` partout, aligné sur la CI |
| [INFO] `gzip` limité au JSON, absent de la stack compose | **Fermé** | Les deux gabarits compressent JS, CSS, SVG, JSON |
| [INFO] `Unit tests` sans `pipefail` | **Fermé** | `release-gate.yml:84`, `:91` ; effet de bord en INFO |
| [INFO] Pas de CI sur push `release/**` | **Fermé en partie** | Le push déclenche la CI ; image unique, Trivy, smoke, e2e UI toujours absents avant le gate |
| [INFO] Chemin PDF.js non vérifié avant le gate | Remplacé | Recentré sur l'absence de vérification des nouveaux réglages nginx |
| [INFO] `Audit checks` faux vert | Toujours présent | — |
| [INFO] `Image size check` | Toujours présent | — |
| [INFO] Format hors CI | Toujours présent | — |
| [INFO] fail-fast | Toujours présent | — |
| [INFO] Permissions `GITHUB_TOKEN` | Toujours présent | S'étend aux nouveaux runs `push` |
| [INFO] Actions par tag | Toujours présent | — |
| [INFO] Durcissement Docker | Toujours présent | — |
| [INFO] Trivy 2026-12-31 | Toujours présent | — |
| [INFO] PR #403 | Toujours présent | — |
| — | [INFO] nouveau | `Frontend tests` sauté si backend rouge (`release-gate.yml:89`) |
| — | [INFO] nouveau | `cancel-in-progress` sur les pushs `release/**` |
| — | [INFO] nouveau | Résidus `.dockerignore` |

Score : 70 → **75** (+5). Le gain vient de 10.2.4 (poids 1). Le CRIT 10.1.1 pèse toujours 3. Après une CI verte sur la PR des correctifs puis sur le merge dans `release/0.7.4` : **90** (provisoire jusqu'au Release Gate). Aucune régression introduite par la remédiation n'a été trouvée à la lecture.

---

## Points positifs

- **Le trou qui a laissé passer #402 est fermé pour la suite** : tout merge sur `release/**` produira un run CI sur la tête, sans approbation de fork et sans secret requis.
- **Le gate peut enfin échouer sur un test rouge**, et le verdict `NO-GO` suit (`needs.unit-tests.result`).
- **Node 22 partout**, aligné sur la CI et sur `pdfjs-dist` ; binaires musl présents pour amd64 et arm64.
- **Contextes Docker propres** : plus de `node_modules` de l'hôte (binaires darwin) dans l'étage de build, plus de 13 Mo de vidéos dans le contexte de l'image unique.
- **Cache et compression nginx bien bornés** : cache d'un an limité aux fichiers hachés, `index.html` et `logo.png` exclus, en-têtes de sécurité répétés là où `add_header` les aurait perdus, PDF et réponses 206 non compressés, aucun `$` exposé à l'`envsubst` du gabarit frontend. Les deux déploiements se comportent maintenant pareil.
- **Logo réduit de 878 kB à 61 kB** sans perte visible (affiché à 72 px au plus), sans autre consommateur du fichier 1024 px.

---

## Verdict partiel : NO-GO

75/100, 1 CRITICAL, 1 MAJOR, 0 MINOR → **NO-GO** (règle absolue : tout CRIT non résolu). Le CRIT est un manque de preuve, pas un défaut connu, et ne peut se lever que sur GitHub : PR des correctifs verte vers `release/0.7.4`, puis run `push` vert sur le commit de merge (score 90, provisoire), puis Release Gate vert sur `release/0.7.4` → `main` avant le tag. Les changements CI/build de la remédiation sont jugés corrects à la lecture ; deux retouches XS recommandées (`if: ${{ !cancelled() }}` sur `Frontend tests`, résidus `.dockerignore`) et une vérification d'en-têtes à ajouter au smoke. Le MAJ (variante `local` publiée non vérifiée) reste au plan de remédiation.

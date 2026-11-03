# Rapport d'audit : CI / Build (re-audit)

**Release** : 0.7.4 (re-audit après remédiation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (100 commits de remédiation depuis `e6047c2` ;
les commits suivants, `a2a10ac` et `4c59df0`, n'ajoutent que des rapports d'audit)
**Baseline** : `reports/release-0.7.4/10-ci-build.md` (**85/100 provisoire**, GO, 0 CRIT, 1 MAJ,
1 MIN, 13 INFO, code audité `1de1929`)

---

## Score de compliance

| Métrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 9 / 11 | **11 / 11** |
| Score | 85 / 100 (provisoire) | **100 / 100 (provisoire, voir 10.1.1)** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 1 | **0** |
| Écarts MINOR | 1 | **0** |
| Écarts INFO | 13 | 13 |

Poids total : 3+1+1+2+1 (10.1) + 3+3+2+1 (10.2) + 2+1 (10.3) = **20**. Les deux items non conformes
en 0.7.4 (10.2.3, poids 2 ; 10.2.4, poids 1) sont corrigés. `score = 20 / 20 * 100 = 100`.

### Réserve sur 10.1.1, 10.2.1 et 10.2.2 : aucun run CI sur cette branche

**Aucun workflow n'a tourné** sur `claude/nifty-turing-fmn3wo` (API REST : 0 run ; pas de PR,
et `ci.yml` ne se déclenche que sur push `main` ou PR vers `main` / `release/**`). Le dernier
Release Gate complet reste le run `41468347487` (2026-11-02, 13/13), sur l'arbre de `v0.7.3`.

- **Lecture 0.7.4** : 10.1.1 était jugé conforme « par équivalence », l'arbre étant identique à
  celui validé par le gate. **Cette équivalence n'existe plus** (100 commits, code et workflows
  modifiés). Je garde la lecture provisoire, comme demandé, mais sur une base plus faible : tous
  les contrôles reproductibles hors Docker sont verts (voir « Gates exécutés localement »), et
  les fichiers Docker n'ont changé que par des commentaires.
- **Lecture stricte** (aucun run = non vérifié) : 10.1.1 non conforme → `17 / 20 = 85`, 1 CRIT,
  **NO-GO**. C'est aussi le résultat si le premier Release Gate de la PR finit rouge.
- 10.2.1 et 10.2.2 étaient prouvés en 0.7.4 par des runs CI sur un arbre identique ; ils sont ici
  provisoires au même titre (pas de démon Docker dans le bac à sable).

### Périmètre du différentiel (`git diff e6047c2..a4d9679`)

- `.github/workflows/release-gate.yml` (+111/−7) : `set -o pipefail` dans les tests unitaires,
  `--group local --group reasoning` pour pip-audit, `fail-fast: false` sur `docker-build`,
  `WITH_REASONING` pour le build `local`, nouveau job `docker-smoke-local`, `${IMAGE_NAME,,}` et
  comparaison de taille limitée à `remote`, `-Dtest='UIRunner#testCritical'`.
- `.github/workflows/ci.yml` (+9) : `ruff format --check`, `npm run format:check`, `-Dtest`.
- `.github/workflows/release.yml` (+11/−5) : `fail-fast: false`, commentaire `BAKE_MODELS` corrigé.
- `.dockerignore` (+14), `document-parser/.dockerignore` (+9), **`frontend/.dockerignore` créé**.
- `Dockerfile`, `document-parser/Dockerfile` : **commentaires seulement**. `docker-compose*.yml` :
  `MAX_IMPORT_TABLE_CELLS` ajouté et commentaire. Templates nginx : cache, gzip, `X-Forwarded-For`.
- `document-parser/pyproject.toml` / `uv.lock` : bornes de `torch` / `torchvision` (métadonnées du
  lock seulement, versions inchangées).
- `docs/maintainers.md` : section du gate réécrite.

### État GitHub (API REST, 2026-11-03)

| Élément | État |
|---------|------|
| Runs sur `claude/nifty-turing-fmn3wo` | **0** |
| Dernier Release Gate terminé | `41468347487` (PR #366, 2026-11-02) **13/13** ; le suivant (`41625312292`) annulé |
| Checks requis sur `main` | **14 contextes, inchangés**, dont `Docker smoke test`. **`Docker smoke test — local` n'en fait pas partie.** `enforcement_level: non_admins` |
| Release précédente | `v0.7.3` (2026-11-02) ; jeton GHCR anonyme pour `scub-france/docling-studio` : HTTP 200 (image publique, donc `docker pull` du check de taille possible sans login) |

### Gates exécutés localement (lecture seule)

| Gate | Résultat | Source |
|------|----------|--------|
| `ruff check` / `ruff format --check` (230 fichiers) / `uv lock --check` | OK | coordinateur |
| pytest | 1673 passed, 19 skipped (15 Neo4j absent, 4 docling non installé) | coordinateur |
| eslint / prettier / vue-tsc / vitest (53 fichiers, 522 passed) / vite build | OK | coordinateur |
| `npm audit --omit=dev` | 0 vulnérabilité | coordinateur et auditeur |
| `mkdocs build --strict` | OK | coordinateur |
| actionlint 1.7.12 (`uvx --from actionlint-py`) | **0 erreur** ; avec shellcheck (`shellcheck-py`) : 2 warnings SC2193 (`ci.yml:140`, condition morte, inchangé) et 5 remarques de style, comme en 0.7.4 | auditeur |
| `docker compose config -q` (`docker-compose.yml` ; `docker-compose.dev.yml` ; `+ docker-compose.ingestion.yml --profile ingestion`) | exit 0 ×3 | auditeur |
| Filtre surefire `-Dtest='UIRunner#testCritical'` (copie de `e2e/ui` dans le scratchpad, `mvn -o`, tag sans scénario) | **1 suite** Karate lancée, contre 4 sans `-Dtest` (`DemoRunner` + 3 méthodes `UIRunner`) ; `BUILD SUCCESS` | auditeur |
| Couverture des variables du compose | 26 / 26 documentées (`docs/configuration.md`, `.env.example`, `docs/mcp-server.md`) | auditeur |

Non exécutés : builds Docker, smoke tests, Trivy, E2E (pas de démon Docker : `docker info` →
socket absent).

---

## Vérification de la checklist

| # | Item | Poids | Conforme | Preuve (@ `a4d9679`) |
|---|------|-------|----------|----------------------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche | 3 | **Oui (provisoire)** | Aucun run (voir réserve). Contrôles reproductibles verts ; actionlint 0 erreur |
| 10.1.2 | 0 warning ESLint | 1 | Oui | coordinateur |
| 10.1.3 | 0 warning Ruff | 1 | Oui | coordinateur |
| 10.1.4 | Type-check frontend | 2 | Oui | `vue-tsc` OK (coordinateur) ; job `Lint & type-check` (`release-gate.yml:56`) |
| 10.1.5 | Formatting conforme | 1 | Oui | ruff format (230 fichiers) et Prettier OK ; **désormais vérifié en CI** : `ci.yml:46-47`, `:74-75` (jobs `Backend tests` et `Frontend tests & build`, requis sur `main`) |
| 10.2.1 | `docker compose build` réussit | 3 | **Oui (provisoire)** | Dockerfiles : commentaires seulement ; compose valide ; `frontend/.dockerignore` n'exclut rien de ce que `npm run build` lit (sources, `public/`, configs, `nginx.conf.template` restent) ; vite build OK. À confirmer par `E2E API tests (Karate)` (`ci.yml`) et le gate |
| 10.2.2 | Le container répond sur `/api/health` | 3 | **Oui (provisoire)** | `docker-smoke` inchangé (`release-gate.yml:300-352`) ; nouveau `docker-smoke-local` (`:354-425`). Aucun n'a tourné sur cette branche |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Oui (provisoire, corrigé)** | voir [MAJ] corrigé ci-dessous : `release-gate.yml:270-272`, `:354-425`, `:132` |
| 10.2.4 | `.dockerignore` à jour | 1 | **Oui (corrigé)** | `frontend/.dockerignore:12-28` ; `.dockerignore:17,25-26,37-38` ; `document-parser/.dockerignore:7-9,29-30` |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | `nginx.conf.template:23-25` (`/`), `:52-60` (`/api/`), `:66-77` (`/mcp`) ; `frontend/nginx.conf.template` identique au port et au backend près (diff relu). `/assets/` manquant → 404 au lieu du shell |
| 10.3.2 | Variables documentées, défauts cohérents | 1 | Oui | 26/26 variables du compose documentées (en 0.7.4, `EMBEDDING_BATCH_SIZE` et `BAKE_MODEL` manquaient) ; `MAX_IMPORT_TABLE_CELLS` identique dans le code, les deux compose, `.env.example` et `docs/configuration.md:31` |

---

## Écarts constatés

Aucun écart CRITICAL, MAJOR ou MINOR. Les deux écarts 0.7.4 sont corrigés :

### ~~[MAJ] La variante `local` publiée n'est ni construite, ni scannée, ni démarrée avant le tag~~ — corrigé (provisoire)

- **Étape 1 (build aligné)** : `release-gate.yml:270-272` passe
  `WITH_REASONING=${{ matrix.target == 'local' && 'true' || 'false' }}`, comme `release.yml:79`.
  `BAKE_MODELS` reste à `false`, avec la raison en commentaire (`:262-269`). Trivy (`image-scan`)
  voit donc les 20 paquets du groupe `reasoning`.
- **Étape 2 (smoke `local`)** : job `docker-smoke-local` (`:354-425`) : `docker load` de l'artefact,
  `docker run --network none -e REASONING_ENABLED=true` (`:378-381`), `/api/health` interrogé depuis
  le conteneur (`:384-387`, 60 × 2 s), puis `status == ok`, `engine == local`,
  `reasoningAvailable == true` (`:405-423`). Le champ existe bien (`api/schemas.py:96`, alias
  camelCase) et vaut `runner.is_available`, donc l'import de docling-agent et mellea
  (`infra/docling_agent_reasoning.py:40-87`) ; `engine` vient du défaut `local` des réglages (l'étage
  `local` ne fixe pas `CONVERSION_ENGINE`). Ajouté à `release-summary.needs` (`:782`) et à la boucle
  bloquante du verdict (`:827`).
- **Étape 3 (audit)** : `release-gate.yml:132` (`uv sync --frozen --group local --group reasoning`).
  `uv run pip-audit` fait une synchronisation non exacte par défaut (vérifié avec `uv run --help`) :
  les groupes restent installés au moment de l'audit.
- **Effet de bord 0.7.4 levé** : le gate et `release.yml` écrivent toujours le même scope de cache
  `local` (`release-gate.yml:273-274`, `release.yml:82-83`), mais leurs build-args ne diffèrent plus
  que par `BAKE_MODELS`, dont l'étape vient après `uv sync` : la couche `reasoning` devient
  partageable.
- **Non fait (étapes optionnelles 4 et 5 de 0.7.4)** : arm64 et modèles ne sont construits qu'au tag,
  pas de vérification après publication. Documenté (`docs/maintainers.md:72`). Voir [INFO] résidu.
- **Provisoire** : aucun de ces jobs n'a tourné.

### ~~[MIN] Contexte `frontend/` sans `.dockerignore` ; motifs `__pycache__` non récursifs~~ — corrigé

- `frontend/.dockerignore` créé (`node_modules/`, `dist/`, `coverage/`, `.env*`, logs, éditeurs,
  `Dockerfile`), commentaire qui précise que l'image racine ne le lit pas.
- `.dockerignore:37-38` et `document-parser/.dockerignore:7-9` : `**/__pycache__/`, `**/*.pyc`
  (`**/*.pyo` côté backend). `.env` exclus à toute profondeur (`.dockerignore:25-26`). `.claude/`
  exclu (`:17`) : utile ici, le poste de l'auditeur porte 2 Go de worktrees sous `.claude/`, ignorés
  par git (`.gitignore:16`) mais présents dans le contexte d'un build local.

---

### [INFO] [NOUVEAU] Premier run : ce que la remédiation fait tourner pour la première fois

Rien de ce qui suit n'a été exécuté en CI. Les risques à surveiller au premier gate :

- **Trivy sur le groupe `reasoning`** (20 paquets, ≈ 68 Mo, jamais scannés par le gate) : pip-audit y
  trouve `nltk` 3.10.3 (CVE-2026-81726, correctif 3.10.4 désormais publié) ; `accelerate` 1.14.0
  (groupe `local`, CVE-2026-69112, sans correctif) était déjà dans l'image du gate. Sévérités non
  lisibles. Une CRITICAL bloquerait `Security scan — local`. C'est le rouge « voulu » annoncé en 0.7.4.
- **`docker-smoke-local` en `--network none`** : le démarrage importe docling-agent et mellea
  (`deps_present()`). Si un import ou le démarrage tente un accès réseau avec de longs délais, la
  boucle de 120 s peut expirer. Non vérifié (pas de Docker).
- **`dep-audit`** installe désormais torch CPU et docling : job plus long (estimé +1 à 2 min en
  0.7.4), parallèle, hors chemin critique.
- **`Image size check`** compare pour la première fois réellement `remote` à `0.7.3-remote` (le nom
  minuscule rend le `docker pull` possible ; image publique). Avertissement seulement.
- **E2E UI `@critical`** : chaque scénario ne tourne plus qu'une fois (filtre vérifié hors ligne,
  voir plus haut). `analyses/rechunk.feature` (`@critical`) fait un rechunk `hybrid` : le
  `HybridChunker` de docling-core (`infra/local_chunker.py:91-95`, sans tokenizer explicite) charge
  son tokenizer par défaut depuis HuggingFace Hub dans le conteneur backend. Ce téléchargement
  existait déjà (gate 0.7.3 vert) ; il a désormais lieu une fois au lieu de trois. Un 429 de
  HuggingFace sur l'IP du runner ferait rougir `E2E UI tests (@critical)`, indépendamment du code.
- **Remédiation** : ouvrir la PR assez tôt pour corriger au premier rouge, et pas le jour du tag.

### [INFO] [NOUVEAU] `Docker smoke test — local` n'est pas un check requis sur `main`

- **Localisation** : protection de `main` (14 contextes, lus par l'API) ; `release-gate.yml:355`
  (nom du job) ; `docs/maintainers.md:52-73`.
- **Constat** : le nouveau job peut finir rouge sans bloquer le merge. `Release summary`, qui le
  compte comme bloquant (`:827`), n'est pas requis non plus et n'échoue pas : il n'écrit qu'un
  commentaire NO-GO. Les noms des jobs requis existants sont conservés (`Docker smoke test`,
  `Docker build — local`, `Security scan — local`) : rien ne reste en « Expected — waiting ».
  `docs/maintainers.md` ne mentionne pas l'action administrateur.
- **Remédiation** : après le premier run vert (le contexte doit avoir existé), ajouter
  `Docker smoke test — local` aux checks requis de `main` ; une ligne dans `docs/maintainers.md`.

### [INFO] [NOUVEAU] Résidu de 10.2.3 : modèles et arm64 construits pour la première fois au tag

- **Localisation** : `release.yml:59` (`linux/amd64,linux/arm64`), `:78` (`BAKE_MODELS=true`) ;
  `docs/maintainers.md:72` (écart documenté).
- **Constat** : le gate prouve le contenu Python de l'image `local` publiée, pas l'étape
  `docling-tools models download` (`Dockerfile:112-117`) ni l'arm64. Le CHANGELOG et les Dockerfiles
  précisent désormais que les modèles embarqués ne sont pas lus par le backend (pas
  d'`artifacts_path`) : l'étape coûte environ 1,3 Go sans effet à l'exécution.
- **Remédiation** : étapes 4 et 5 de 0.7.4 (runner `ubuntu-24.04-arm`, vérification après
  publication), ou retirer `BAKE_MODELS` tant que les modèles ne sont pas lus.

### [INFO] Le job `Audit checks (commands.sh)` est un faux vert, et c'est un check requis — inchangé

- **Localisation** : `release-gate.yml:191-232` ; `.gitignore:50-51`.
- **Constat** : inchangé. Désormais documenté comme tel (`docs/maintainers.md:70`).
- **Remédiation** : inchangée (versionner le script, ou supprimer le job **et** son contexte requis).

### [INFO] Dependency audit : Python ne bloque jamais, npm seulement sur CRITICAL — corrigé en partie

- **Corrigé** : périmètre étendu aux groupes livrés (`release-gate.yml:132`), documenté
  (`docs/maintainers.md:60`). npm production à 0 vulnérabilité.
- **Inchangé** : `continue-on-error` (`:137`), avertissement seulement (`:151-155`), seul npm
  CRITICAL fait échouer le job (`:185-188`). vite 6.4.1 (HIGH, dev) non mis à jour.

### [INFO] `.trivyignore.yaml` : les 5 suppressions expirent le 2026-12-31 (J+58), sans issue de suivi Pillow — inchangé

- **Localisation** : `.trivyignore.yaml:20,38,44,50,56` (inchangé depuis `e6047c2`).
- **Constat** : recherche REST `is:issue pillow` : 0 résultat. Recoupe l'audit 08.

### [INFO] `uv` reste installé dans les images d'exécution — inchangé

- **Localisation** : `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9`.

### [INFO] Déclencheurs et contournement — corrigé en partie

- **Corrigé** : `ruff format --check` et `npm run format:check` en CI (`ci.yml:46-47,74-75`), dans
  des checks requis.
- **Inchangé** :
  - pas de CI sur push `release/**` (`ci.yml:3-7`) ; les PR vers `release/**` sont couvertes ;
  - `ci.yml:141` : `github.ref == refs/heads/release/*` reste une condition morte (SC2193) ;
  - `mkdocs build --strict` ne tourne qu'au push sur `main` ;
  - `enforcement_level: non_admins` : un administrateur peut toujours pousser sans checks ;
  - ne pas taguer un commit en `[skip ci]` (règle à rappeler au moment du gel).

### [INFO] `/mcp` n'est jamais appelé en CI — inchangé

- **Localisation** : aucune feature `e2e/api` ne mentionne `mcp` ;
  `e2e/ui/src/test/resources/navigation/mcp-config.feature:1` (`@ui @regression`), et les tests UI
  hors `@critical` ne tournent dans aucun workflow (documenté, `docs/maintainers.md:73`).

### [INFO] Durcissement Docker : pas de `HEALTHCHECK`, image racine sans `USER` — inchangé

- **Localisation** : aucun `HEALTHCHECK` (grep) ; `Dockerfile:65` (nginx en root, uvicorn via
  `su appuser`) ; `frontend/Dockerfile:9` ; `document-parser/Dockerfile:37,95` (`USER appuser`, sain).

### [INFO] Images de base et chaîne d'approvisionnement des actions — inchangé

- **Localisation** : `node:20-alpine` (`Dockerfile:11`, `frontend/Dockerfile:1`,
  `docker-compose.dev.yml:175`) ; 18 références `uses:` distinctes par étiquette, aucune par SHA ;
  pas de bloc `permissions:` dans `ci.yml` ; pas de `.github/dependabot.yml`.

### [INFO] Le cache Docker est invalidé à chaque changement de code et de version — inchangé

- **Localisation** : `Dockerfile:24-25` (`ARG`/`ENV APP_VERSION` dans `base`), `:45`
  (`COPY document-parser/ .`) avant `:106-110` (`uv sync --group local [--group reasoning]`).
- **Constat** : inchangé ; le build `local` du gate installe désormais aussi le groupe `reasoning`
  sans cache utile après un changement de code.

### [INFO] La cible compose par défaut (`CONVERSION_MODE` absent → `local`) n'est jamais construite en CI — inchangé

- **Localisation** : `docker-compose.yml:144` ; `CONVERSION_MODE: remote` partout
  (`ci.yml:120,202`, `release-gate.yml:639,717`).

---

## Delta vs 0.7.4

Score : **85 → 100 (provisoire)**. Comptes : CRIT 0 → 0 ; MAJ 1 → 0 ; MIN 1 → 0 ; INFO 13 → 13
(3 corrigés, 3 nouveaux).

| Écart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] 10.2.3 `local` publiée non vérifiée | **Corrigé (provisoire)** ; résidu arm64 / modèles en INFO | `release-gate.yml:132,270-272,354-425,782,827` |
| [MIN] 10.2.4 `.dockerignore` | **Corrigé** | `frontend/.dockerignore` ; `.dockerignore:37-38` ; `document-parser/.dockerignore:7-9` |
| [INFO] Tests unitaires infaillibles (`tee` sans `pipefail`) | **Corrigé** | `release-gate.yml:87,94` ; `pipefail` local aux deux steps (le step npm, qui dépend de `npm audit \| tee`, n'est pas touché) |
| [INFO] Audit checks faux vert | Inchangé (désormais documenté) | `docs/maintainers.md:70` |
| [INFO] Dependency audit | **Corrigé en partie** (groupes) | `release-gate.yml:132` |
| [INFO] `.trivyignore.yaml` 2026-12-31 | Inchangé | `.trivyignore.yaml:20-56` |
| [INFO] `uv` dans les images | Inchangé | `Dockerfile:36` |
| [INFO] Image size (majuscules) | **Corrigé** | `release-gate.yml:539` (`${IMAGE_NAME,,}`), `:532-534` (`remote` seul) |
| [INFO] fail-fast | **Corrigé** | `release-gate.yml:239` ; `release.yml:25` |
| [INFO] Déclencheurs | **Corrigé en partie** (format en CI) | `ci.yml:46-47,74-75` |
| [INFO] `/mcp` hors CI | Inchangé | — |
| [INFO] Durcissement Docker | Inchangé | — |
| [INFO] Images de base / actions | Inchangé | — |
| [INFO] Cache Docker | Inchangé | `Dockerfile:24-25,45` |
| [INFO] Cible compose `local` | Inchangé | `docker-compose.yml:144` |
| — | **[INFO] nouveau** | Premier run : risques |
| — | **[INFO] nouveau** | `Docker smoke test — local` non requis |
| — | **[INFO] nouveau** | Résidu 10.2.3 (arm64, modèles) |

**Régressions : aucune trouvée.** Vérifié : noms des jobs requis conservés ; `pipefail` limité aux
deux steps de tests ; `docker-smoke-local` hors du chemin des E2E (`e2e-api` dépend toujours de
`docker-smoke` seul) ; le filtre surefire ne retire aucun scénario `@critical` (les seuls fichiers
`@critical` sont sous `documents/` et `analyses/`, couverts par `testCritical` ;
`demo/ask-demo.feature` est `@demo` et ne cite `@critical` qu'en commentaire) ; contextes Docker sans fichier requis exclu.

---

## Ce qui reste à faire

Pour que le 100 cesse d'être provisoire :
1. Ouvrir la PR (`release/0.7.4` → `main`) et obtenir un Release Gate **et** une CI verts, y compris
   `Docker smoke test — local` et `Security scan — local` (premier scan du groupe `reasoning`).
2. Ajouter `Docker smoke test — local` aux checks requis de `main` (action administrateur).

Pour réduire les INFO (sans effet sur le score) : issue Pillow 13 datée ; `audit-checks` versionné
ou supprimé avec son contexte requis ; `node:22-alpine` ; `permissions: contents: read` et pins par
SHA ; `HEALTHCHECK` ; dépendances installées avant le code dans le Dockerfile.

---

## Points positifs

- **MAJ ouvert depuis trois audits corrigé** : l'image `local` du gate a enfin le contenu Python de
  l'image publiée, elle est scannée, et elle est démarrée sans réseau avec une vérification qui
  attrape exactement le bug du hotfix 0.7.1 (`reasoningAvailable`).
- **Trois trous connus de `docs/maintainers.md` fermés** (tests infaillibles, comparaison de taille
  morte, fail-fast) et la liste des trous restants réécrite honnêtement.
- **Format vérifié en CI**, dans des checks déjà requis : 10.1.5 n'est plus tenu que par la
  discipline locale.
- **Correctifs ciblés et commentés** : `pipefail` posé step par step avec la raison (ne pas casser
  `npm audit | tee`) ; `BAKE_MODELS` laissé à `false` avec la politique HuggingFace citée ; noms de
  jobs requis préservés.
- **Contextes Docker propres** : trois `.dockerignore` à jour, secrets `.env` exclus à toute
  profondeur.
- **Statique vert** : actionlint 0 erreur, compose valides, toutes les variables documentées.

---

## Verdict partiel : GO (provisoire)

100/100, 0 CRITICAL, 0 MAJOR, 0 MINOR, 13 INFO → **GO**, **sous condition du premier Release
Gate**.

- Aucun run CI n'a encore couvert ces 100 commits. Lecture stricte : 85/100, 1 CRIT, **NO-GO** tant
  que le gate n'est pas vert.
- Les risques du premier run sont identifiés (Trivy sur `reasoning`, smoke `local` sans réseau,
  téléchargement HuggingFace du tokenizer dans l'E2E UI) : ouvrir la PR tôt.
- Après ce premier run vert, rendre `Docker smoke test — local` requis sur `main`.
- Échéance externe inchangée : suppressions Trivy expirées le 2026-12-31.

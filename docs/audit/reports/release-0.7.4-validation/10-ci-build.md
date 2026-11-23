# Rapport d'audit : CI / Build

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche auditée** : `fix/0.7.4-editor-followups` @ `efc0bc5` (working tree). Branche **non poussée** : GitHub ne connaît que `release/0.7.4` @ `f7fc791`.
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/10-ci-build.md`, `a12b744`, 75/100).
**Workflows non exécutés : rien n'a été poussé.**
**Mode** : lecture statique de `.github/workflows/`, `Dockerfile`, compose, `e2e/ui`, `document-parser/pyproject.toml` et `uv.lock` ; en lecture seule sur GitHub : `gh run list`, `gh run view 41478041280`, `gh pr list`, `gh api` (branche `release/0.7.4`, permissions par défaut des workflows, `action.yml` de `astral-sh/setup-uv@v5`). Aucun outil du projet lancé (ni ruff, ni eslint, ni vue-tsc, ni prettier, ni pytest, ni vitest, ni Docker, ni Maven). Aucune suite n'a tourné sur `efc0bc5` : le message de `efc0bc5` le dit (« Not run: no test, lint, format or type-check was executed »), celui de `23e4c81` aussi (« Not run: no workflow was triggered »).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 10 / 11 |
| Score | **85 / 100** |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 0 |
| Écarts INFO | 15 |

Poids total : 20. Poids non conformes : 10.1.1 (3). `score = 17 / 20 * 100 = 85`.

Lecture alternative de 10.2.3 (non conforme tant que la variante n'est pas construite **telle que publiée**, modèles et arm64 compris, ou tant qu'aucun run ne l'a construite) : 9 / 11, **75 / 100**, 1 CRIT, 1 MAJ. Le verdict ne change pas (NO-GO par le CRIT).

### Tableau de recalcul

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 10.1.1 | Toutes les GitHub Actions passent sur la branche de release | 3 | **Non** | Inchangé sur GitHub : `release/0.7.4` @ `f7fc791`, non protégée ; seul `Auto-close issues` a tourné (run `44399691994`) ; ni CI ni Release Gate sur 0.7.4 ; `efc0bc5` non poussé |
| 10.1.2 | Warnings ESLint résolus | 1 | Oui (provisoire) | Dernière preuve : eslint propre sur `a12b744`. 22 commits depuis, non lintés. La lecture des autres audits de validation ne relève pas d'import inutilisé |
| 10.1.3 | Warnings Ruff résolus | 1 | Oui (provisoire) | Idem : `ruff check` propre sur `a12b744`, non relancé sur `efc0bc5` |
| 10.1.4 | Type-check frontend | 2 | Oui (provisoire) | `vue-tsc` propre sur `a12b744` ; `frontend/package.json:8` l'enchaîne avant `vite build`, et `ci.yml:121-122` le lance. Non relancé sur `efc0bc5` |
| 10.1.5 | Formatting conforme | 1 | Oui (provisoire) | Propre sur `a12b744`, non relancé ; toujours vérifié par aucun job CI (INFO) |
| 10.2.1 | `docker compose build` réussit | 3 | Oui (provisoire, revue statique) | Aucune entrée de build de l'image compose modifiée depuis le contrôle (`git diff b5f8c7f efc0bc5` : seuls les blocs `environment:` des deux compose changent). Même réserve que le contrôle : le dernier build exécuté (`43752042089`, `de5fe66`) précède Node 22 et le nouveau gabarit nginx |
| 10.2.2 | Le container démarre et répond sur `/api/health` | 3 | Oui (provisoire, revue statique) | `API_ALLOWED_HOSTS` vide → liste vide (`document-parser/infra/settings.py:284-286`) → middleware non monté (`document-parser/main.py:117-118`) : le health check et l'e2e ne sont pas touchés. `MAX_IMPORT_SIZE_MB=200` = défaut du code (`settings.py:31`, `:230`) |
| 10.2.3 | Les deux variantes buildent correctement | 2 | **Oui (provisoire, revue statique)** | Le gate construit maintenant `local` avec `WITH_REASONING=true` (`release-gate.yml:244-247`) et le scanne avec Trivy (`:378-425`, `fail-fast: false`) ; `dep-audit` installe `local` et `reasoning` (`:131`). Écarts restants avec `release.yml:55`, `:72` : modèles non intégrés, amd64 seul. Lecture détaillée plus bas |
| 10.2.4 | `.dockerignore` à jour | 1 | Oui | `document-parser/.dockerignore:6-8` récursifs ; `frontend/.dockerignore:10-14` ajoute `.env*`, `.claude/`, `CLAUDE.md`, `*.iml`. Seul `.ruff_cache/` manque côté frontend (étage de build, sans effet sur l'image finale) |
| 10.3.1 | Nginx route `/api/*` et sert `/` | 2 | Oui | Gabarits inchangés depuis le contrôle ; le smoke du gate vérifie désormais les en-têtes de `/` et de `/assets/` (`release-gate.yml:327-376`) |
| 10.3.2 | Variables d'environnement documentées | 1 | Oui | `MAX_IMPORT_SIZE_MB` et `API_ALLOWED_HOSTS` : `docs/configuration.md:31`, `:127-144`, `.env.example:37`, `:49` ; défauts compose identiques au code |

### Lecture de 10.2.3

L'item demande que les deux variantes buildent correctement. Le MAJ du contrôle portait sur l'écart entre ce que le gate construit et ce que `release.yml` publie. Après `23e4c81` :

- **Ce qui est couvert** : le jeu de paquets publié. `Dockerfile:102-106` installe `--group local --group reasoning` quand `WITH_REASONING=true` ; le gate passe cette valeur à `local` (`release-gate.yml:247`). Les deux groupes existent dans `document-parser/pyproject.toml:38-61` et dans le lockfile (`uv.lock`, `[package.dev-dependencies]` et `[package.metadata.requires-dev]` alignés sur le `pyproject`), `torch`/`torchvision` résolus en `2.13.0+cpu`/`0.28.0+cpu` depuis l'index CPU pour Linux. `--frozen` ne relit pas le `pyproject` : il installe le lock tel quel, sans conflit possible.
- **Ce qui ne l'est pas** :
  - `BAKE_MODELS=false` (`:246`) : l'étape `Dockerfile:108-113` ne tourne pas au gate. Elle ne fait que télécharger des points de contrôle (`docling-tools models download`) dans `/home/appuser/.cache/docling/models` : aucun paquet OS ni Python, rien que Trivy en mode image rattacherait à une base de vulnérabilités. Le scan de l'image sans modèles vaut celui de l'image publiée. En revanche, la **réussite** de cette étape (Hub Hugging Face joignable, CLI `docling-tools` inchangée) n'est vérifiée qu'au moment du tag.
  - `linux/arm64` (`release.yml:55`) : jamais construit avant le tag.
- **Preuve historique** : le run `41478041280` (`release.yml`, `v0.7.3`, 2026-11-02) a construit et poussé `local` avec `BAKE_MODELS=true` et `WITH_REASONING=true`, amd64 + arm64, en 19 min. Depuis `v0.7.3`, le `Dockerfile` ne change que d'une ligne (`node:20-alpine` → `node:22-alpine`) et le lockfile n'ajoute que `fpdf2` et `fonttools` (groupe `ci`, hors image). Les deux étapes non couvertes par le gate ont donc réussi sur des entrées quasi identiques.

Ma lecture : **conforme, à titre provisoire**, comme 10.2.1 et 10.2.2 l'étaient au contrôle (revue statique, aucun run). Ce qui reste (modèles, arm64) est un risque de build au moment du tag, pas un trou de scan : il passe en INFO. Si l'on exige que la variante soit construite exactement comme publiée, ou qu'un run l'ait construite, l'item reste non conforme : **75**, 1 MAJ.

### État GitHub Actions (relevé le 2026-11-19)

| Élément | État |
|---------|------|
| `release/0.7.4` | `f7fc791`, `protected=false` |
| Runs sur `release/0.7.4` | 5 derniers : `Auto-close issues` seulement (`44399691994` sur `f7fc791`). Aucun run CI ni Release Gate |
| `fix/0.7.4-editor-followups` | Non poussée, aucun run |
| PR ouvertes vers `release/0.7.4` | #403, #390, #371 |
| Permissions par défaut des workflows du dépôt | `default_workflow_permissions: write` |
| Dernier `release.yml` | `41478041280`, `v0.7.3`, success |

---

## Écarts constatés

### [CRIT] Aucune CI n'a tourné sur la tête de `release/0.7.4` — inchangé

- **Localisation** : `.github/workflows/ci.yml:3-7` (correct dans le working tree, absent de GitHub) ; `.github/workflows/release-gate.yml:3-6` ; run `44399691994` ; branche `release/0.7.4` non protégée
- **Constat** : rien n'a bougé sur GitHub depuis le contrôle. Les changements CI de la seconde remédiation (`53e3633`, `23e4c81`) n'ont jamais tourné. Aucune suite (lint, format, type-check, pytest, vitest) n'a tourné sur `efc0bc5`, qui porte 22 commits de plus que `a12b744`.
- **Règle violée** : item 10.1.1 (poids 3).
- **Ce qui le fermera** :
  1. Lancer en local sur `efc0bc5` : `ruff check`, `ruff format --check`, `pytest`, `eslint`, `prettier --check`, `vue-tsc`, `vitest`, `vite build` (la dernière preuve date de `a12b744`).
  2. Pousser la branche, ouvrir la PR vers `release/0.7.4` : `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` (portée complète) doivent être verts. `Backend tests (docling)` et `E2E UI tests (Karate UI)` sont `skipped` sur une PR vers une branche de release, c'est voulu.
  3. Fusionner : le commit de merge contient `ci.yml:5`, le premier run `push` sur `release/0.7.4` part et lance cette fois aussi `Backend tests (docling)` et `E2E UI tests (Karate UI)`. Tout vert : 10.1.1 conforme (provisoire), score **100** dans ma lecture de 10.2.3.
  4. Avant le tag : PR `release/0.7.4` → `main`, Release Gate vert, image `local` avec reasoning et Trivy compris.
  5. Protéger `release/**` avec les checks requis listés plus bas.

---

### [INFO] Les changements CI de la seconde remédiation n'ont jamais tourné

- **Localisation** : `.github/workflows/ci.yml:62-97`, `:215`, `:279-284` ; `.github/workflows/release-gate.yml:131`, `:204-260`, `:327-376`, `:392-400`, `:710-715`
- **Constat** : tout est relu, rien n'est prouvé. La revue ci-dessous ne trouve aucun défaut qui ferait échouer un job ou le ferait passer à tort ; elle liste ce que seul un run tranchera. Le contrôle des en-têtes ne couvre que le gabarit de l'image unique (`nginx.conf.template`) : `frontend/nginx.conf.template`, servi par la stack compose, n'est vérifié par aucun job.
- **Remédiation** : premier run sur la PR, puis sur le merge, puis au gate. En option, le même contrôle d'en-têtes dans le job `e2e` de `ci.yml` après `Wait for health`.

### [INFO] Lint, format, type-check et tests non relancés sur `efc0bc5`

- **Localisation** : `git log a12b744..efc0bc5` (22 commits) ; messages de `efc0bc5` et `23e4c81`
- **Constat** : 10.1.2 à 10.1.5 reposent sur des résultats de `a12b744`. Ils sont gardés conformes à titre provisoire.
- **Remédiation** : relancer les huit commandes avant de pousser.

### [INFO] `release-gate.yml` : huit jobs reçoivent un jeton en écriture — inchangé

- **Localisation** : pas de bloc `permissions:` de niveau workflow ; blocs par job seulement : `image-size` (`:462-463`, `packages: read`), `release-summary` (`:750-752`)
- **Constat** : le dépôt donne `write` par défaut. Sur une PR interne vers `main`, `lint-typecheck`, `unit-tests`, `dep-audit`, `docker-build`, `docker-smoke`, `image-scan`, `e2e-api`, `e2e-ui` reçoivent un jeton en écriture tout en lançant `npm ci`, `uv sync`, `docker build` et Maven. Les deux jobs qui ont un bloc n'ont pas `contents: read` : `actions/checkout` et `gh release list` (`:480`) passent parce que le dépôt est public. `ci.yml` est corrigé (`:11-12`).
- **Remédiation** : en tête de `release-gate.yml`, `permissions: { contents: read }` ; ajouter `contents: read` aux blocs de `image-size` et `release-summary`.

### [INFO] Le résumé du gate peut annoncer « GO » sur un run annulé — préexistant

- **Localisation** : `.github/workflows/release-gate.yml:738`, `:784-799`, `:8-10`
- **Constat** : la suppression d'`audit-checks` est propre (plus de `needs`, d'artefact, de variable ni de ligne de tableau ; la boucle `:784` ne l'avait jamais contenu). Mais la logique ne compte que `failure` comme bloquant. `always()` fait tourner `release-summary` même quand le run est annulé (`cancel-in-progress: true` à chaque nouveau push sur la PR, ou annulation manuelle) : les jobs sont alors `cancelled` ou `skipped`, aucun n'est `failure`, et le commentaire posté dit **GO**. Le run suivant le remplace, mais le commentaire est faux entre-temps. Sur une PR de fork vers `main`, le jeton est en lecture seule et `Post or update PR comment` échoue (403).
- **Remédiation** : `if: ${{ !cancelled() && github.event_name == 'pull_request' }}` (`:738`) et, dans la boucle `:784-788`, `if [ "$result" != "success" ]` pour les jobs bloquants.

### [INFO] Image `local` du gate : modèles non intégrés, amd64 seul

- **Localisation** : `.github/workflows/release-gate.yml:238-247` ; `.github/workflows/release.yml:55`, `:72` ; `Dockerfile:108-113`
- **Constat** : écart voulu et commenté. Le scan est équivalent ; la réussite du téléchargement des modèles et du build arm64 n'est vérifiée qu'au tag (dernier succès : `41478041280`, `v0.7.3`).
- **Remédiation** (optionnelle) : un build `linux/arm64` sans `load` dans le gate ; garder `BAKE_MODELS=false`.

### [INFO] Coût du build `local` au gate : cache GHA et double compression

- **Localisation** : `.github/workflows/release-gate.yml:248-249`, `:251-260`
- **Constat** : image `local` sans modèles avec reasoning ≈ 1,92 Go (`docs/design/254-docker-slim-post-uv.md:250`). Disque : l'image, le cache BuildKit et l'archive tiennent sans le nettoyage ; le nettoyage (`:211-219`) est inoffensif et laisse de la marge. Durée attendue : 10 à 20 min à froid (la publication amd64 + arm64 avec modèles a pris 19 min sur `v0.7.3`). Deux pertes : `cache-to: type=gha,mode=max` exporte toutes les couches de `local` (torch compris) dans un cache GHA limité à 10 Go par dépôt, au risque d'évincer les caches uv, npm et Maven ; `upload-artifact` recompresse une archive déjà gzippée.
- **Remédiation** : `compression-level: 0` sur `Upload image artifact` (`:255-260`) ; `mode=min` pour `local` si l'éviction se voit.

### [INFO] `Image size check` ne compare jamais rien et n'impose aucun budget — inchangé

- **Localisation** : `.github/workflows/release-gate.yml:15`, `:495`
- **Constat** : `IMAGE_NAME` = `scub-france/docling-Studio` ; `docker pull` refuse une référence avec une majuscule, la branche « Could not pull » est toujours prise.
- **Remédiation** : `${IMAGE_NAME,,}` ; seuil bloquant si un budget est voulu.

### [INFO] Le formatage n'est vérifié par aucun job CI — inchangé

- **Localisation** : `.github/workflows/ci.yml:49-50`, `:118-122` ; `.github/workflows/release-gate.yml:49-56`
- **Remédiation** : `uv run ruff format --check .` et `npx prettier --check src/` dans `ci.yml` et `lint-typecheck`.

### [INFO] `release.yml` reste en fail-fast — fermé en partie

- **Localisation** : `.github/workflows/release.yml:21-23` (le gate est corrigé : `release-gate.yml:204`, `:385`)
- **Remédiation** : `fail-fast: false`.

### [INFO] Une PR vers `release/*` n'a ni image unique, ni Trivy, ni smoke, ni e2e UI — fermé en partie

- **Localisation** : `.github/workflows/ci.yml:64`, `:215`
- **Constat** : l'e2e UI `@critical` et les tests Docling tournent maintenant à chaque push sur `release/**`, donc après chaque merge. Le `Dockerfile` racine (image publiée) et `nginx.conf.template` ne sont toujours construits et démarrés qu'au gate.
- **Remédiation** : un job léger `docker build --target remote .` + smoke dans `ci.yml` pour `release/**`.

### [INFO] Points de détail des nouveaux jobs

- **Localisation** : `.github/workflows/ci.yml:62-97`, `:215` ; `.github/workflows/release-gate.yml:139-140`
- **Constat** :
  - `backend-docling` n'installe pas `poppler-utils`, contrairement à `backend` (`ci.yml:43-44`). Aucun des quatre fichiers ciblés n'importe `pdf2image` ni `infra/page_raster.py` : sans effet à la lecture.
  - `setup-uv@v5` élague par défaut les roues téléchargées avant de sauver son cache : `cache-suffix: docling` (entrée bien déclarée dans l'`action.yml` de `v5`) sépare les caches mais n'évite pas de retélécharger torch à chaque run.
  - `pip-audit` interroge PyPI : `torch 2.13.0+cpu` et `torchvision 0.28.0+cpu` n'y existent pas et sont ignorés. Trivy les couvre dans l'image.
  - `github.event_name == 'push'` est redondant dans `ci.yml:215` (le déclencheur `push` ne vise que `main` et `release/**`). Sans effet.
- **Remédiation** : aucune requise.

### [INFO] Actions épinglées par tag, pas par SHA — inchangé

- **Localisation** : `.github/workflows/ci.yml`, `release-gate.yml`, `release.yml`

### [INFO] `uv` dans les images d'exécution ; pas de `HEALTHCHECK` ; image unique lancée en root — inchangé

- **Localisation** : `Dockerfile:36`, `:65` ; `document-parser/Dockerfile` ; `docker-compose.yml:141-201`

### [INFO] Suppressions Trivy : échéance commune au 2026-12-31 — inchangé

- **Localisation** : `.trivyignore.yaml:20`, `:38`, `:44`, `:50`, `:56`
- **Constat** : 42 jours restants ; tout gate lancé après le 31 décembre échouera (#378). Le scan de `local` avec reasoning peut aussi faire apparaître des CRITICAL nouveaux (paquets `docling-agent`, `mellea` et leurs dépendances) : c'est le but, mais le premier gate peut être rouge pour cette raison.

### [INFO] PR #403 ouverte vers `release/0.7.4` recoupe le correctif local #393 — inchangé

- **Constat** : ordre des merges à décider ; si #403 passe après la branche des correctifs, son merge déclenche lui aussi un run `push`.

---

## Delta vs contrôle

| Écart du contrôle (@ `a12b744`) | Statut @ `efc0bc5` | Détail |
|---------------------------------|---------------------|--------|
| [CRIT] 10.1.1 aucune CI sur la tête de `release/0.7.4` | **Toujours ouvert** | Rien de poussé, aucun run |
| [MAJ] 10.2.3 variante `local` non construite ni scannée | **Fermé (provisoire)** | `release-gate.yml:244-247`, `:131` ; modèles et arm64 en INFO. Lecture stricte : reste ouvert (75) |
| [INFO] Chemin `push release/**` et nginx vérifiés par aucun run | Fermé en partie | Contrôle d'en-têtes au smoke (`release-gate.yml:327-376`) ; rien n'a tourné, gabarit frontend non vérifié |
| [INFO] `Frontend tests` sauté si backend rouge | **Fermé** | `release-gate.yml:91` `if: ${{ !cancelled() }}` |
| [INFO] `cancel-in-progress` sur les pushs `release/**` | **Fermé** | `ci.yml:18` `cancel-in-progress: ${{ github.event_name == 'pull_request' }}` |
| [INFO] Résidus `.dockerignore` | **Fermé** | `document-parser/.dockerignore:6-8`, `frontend/.dockerignore:10-14` ; reste `.ruff_cache/` côté frontend, négligeable |
| [INFO] `Audit checks` faux vert | **Fermé** | Job supprimé, aucune référence pendante (`needs`, artefact, variable, ligne de tableau, `docs/maintainers.md`) |
| [INFO] `Image size check` | Toujours présent | — |
| [INFO] Format hors CI | Toujours présent | — |
| [INFO] fail-fast | Fermé en partie | Gate corrigé, `release.yml` non |
| [INFO] PR vers `release/*` sans image unique, Trivy, smoke, e2e UI | Fermé en partie | e2e UI et tests Docling sur push `release/**` |
| [INFO] Permissions `GITHUB_TOKEN` | Fermé en partie | `ci.yml:11-12` en lecture ; `release-gate.yml` toujours sans bloc |
| [INFO] Actions par tag | Toujours présent | — |
| [INFO] Durcissement Docker | Toujours présent | — |
| [INFO] Trivy 2026-12-31 | Toujours présent | 42 jours |
| [INFO] PR #403 | Toujours présent | — |
| — | [INFO] nouveau | Workflows modifiés jamais exécutés |
| — | [INFO] nouveau | Suites non relancées sur `efc0bc5` |
| — | [INFO] nouveau | Résumé du gate : « GO » possible sur un run annulé (préexistant, relevé maintenant) |
| — | [INFO] nouveau | Image `local` du gate sans modèles, amd64 seul |
| — | [INFO] nouveau | Coût du build `local` : cache GHA, double compression |
| — | [INFO] nouveau | Points de détail des nouveaux jobs |

Score : 75 → **85** (+10), par 10.2.3 (poids 2). Lecture stricte de 10.2.3 : 75 (±0). Après une CI verte sur la PR puis sur le merge dans `release/0.7.4` : **100** (provisoire jusqu'au Release Gate).

---

## Revue des workflows avant première exécution

Chaque changement est lu comme le runner l'exécuterait. Événements : push `main`, push `release/x`, PR vers `main`, PR vers `release/x`, PR de fork.

### `ci.yml` — `permissions` et concurrence (`53e3633`)

- `:11-12` `contents: read` pour tous les jobs. Suffisant : checkout d'un dépôt public, `upload-artifact` et le cache de `setup-uv`/`setup-node`/`setup-java` passent par le jeton d'exécution, pas par `GITHUB_TOKEN`. Aucun job n'écrit.
- `:16-18` `cancel-in-progress: ${{ github.event_name == 'pull_request' }}` : expression booléenne acceptée. Push : jamais annulé. PR : groupe `ci-refs/pull/N/merge`, les runs dépassés sont annulés.
- **Verdict : OK.**

### `ci.yml` — job `backend-docling` (`23e4c81`, `:62-97`)

- **`if:` (`:64`)** `github.event_name == 'push' || github.base_ref == 'main'`, contexte `github` valide au niveau job. Push `main` : vrai. Push `release/x` : vrai. PR vers `main` : vrai. PR vers `release/x` : faux, `skipped`. PR de fork vers `main` : vrai, aucun secret requis. Sur un push, `base_ref` est vide, la seconde clause est fausse, sans effet.
- **`needs:`** aucun, et aucun job n'en dépend : un échec ne saute rien par ricochet.
- **`setup-uv@v5`** : `cache-suffix` est une entrée réelle de `v5` (`action.yml` : « Suffix for the cache key »). OK.
- **`uv sync --frozen --group dev --group local` (`:85`)** : les deux groupes existent dans `pyproject.toml:29-47` et dans le lock. L'index CPU s'applique par `[tool.uv.sources]` (`pyproject.toml:69-76`) et le lock fige `torch 2.13.0+cpu` pour `sys_platform != 'darwin'`. `--frozen` installe le lock sans le revalider. Python 3.12 de `setup-python` satisfait `requires-python >=3.12`.
- **Contrôle d'import (`:87-89`)** : échoue si `docling` manque, ce qui empêche le faux vert d'une suite entièrement sautée (`importorskip` dans `test_pipeline_options.py:14`, `test_batch_merge.py:17`, `test_robustness.py:155`). OK.
- **Cibles pytest (`:92-97`)** : bloc `>` replié en une ligne. Les trois fichiers existent ; le nœud `tests/test_serve_converter.py::TestConverterWiring::test_local_engine_builds_local_converter` existe (`:791`, `:796`, `skipif(not _has_docling())`). `uv run` ne retire pas les paquets du groupe `local` (synchronisation non exacte par défaut).
- **Seul un run dira** : que les 64 tests ne déclenchent aucun téléchargement de modèle (construction de convertisseurs Docling, conversions simulées), la durée d'installation (torch CPU, docling).
- **Verdict : OK.** Détails (poppler, élagage du cache) en INFO.

### `ci.yml` — `e2e-ui` sur push `main` et `release/**` (`23e4c81`, `:210-299`)

- **`if:` (`:215`)** vrai pour push `main` et push `release/x`, faux pour toute PR (fork compris) : `skipped`. Contexte valide au niveau job.
- **`needs: [backend, frontend]`** : jobs existants.
- **Commande (`:279-284`)** : bloc `>` replié ; `-Dtest='UIRunner#testCritical'` : quotes simples correctes, `#` à l'intérieur d'un mot n'est pas un commentaire bash. `UIRunner#testCritical` existe (`e2e/ui/src/test/java/UIRunner.java:11-16`) ; `-Dtest` remplace l'`include` `**/*Runner.java` de surefire (`e2e/ui/pom.xml:44-52`), donc `AnalysisEditorRunner` et `DemoRunner` ne tournent pas. Si le filtre ne trouvait rien, surefire échoue (`failIfNoSpecifiedTests` vrai par défaut) : pas de faux vert. Six features portent `@critical` sous `documents/` et `analyses/` ; aucune référence aux features supprimées par `3a794e1`.
- **Seul un run dira** : que surefire 3.2.5 filtre bien une méthode `@TestFactory` de Karate par `#méthode`, et que les journeys `@critical` réécrits passent.
- **Verdict : OK.**

### `release-gate.yml` — `Frontend tests` (`53e3633`, `:89-96`)

- `if: ${{ !cancelled() }}` : tourne même si `Backend tests` échoue ; le job reste `failure`. **Verdict : OK.**

### `release-gate.yml` — `dep-audit` (`23e4c81`, `:126-132`)

- `uv sync --frozen --group local --group reasoning` : groupes présents dans le lock (`docling-agent==0.6.0`, `mellea==0.4.2`) ; `dev` reste inclus par défaut. Même installation que `Dockerfile:103` hors `--no-dev`, réussie à la publication de `v0.7.3`. `uv pip install ... pip-audit` dans le même `.venv`, puis `uv run pip-audit` (`:139-140`) : `uv run` ne retire rien, l'audit voit les groupes `local` et `reasoning`.
- `torch`/`torchvision` en version locale `+cpu` ne sont pas sur PyPI : ignorés par `pip-audit`, couverts par Trivy (INFO).
- **Verdict : OK.**

### `release-gate.yml` — suppression d'`audit-checks` (`23e4c81`)

- Plus de job, de `needs` (`:739-748` : neuf jobs, tous existants), de téléchargement d'artefact `audit-checks-results`, de variables `AUDIT*`, de ligne « Audit checks » ni de section « Audit Checks Summary ». `docs/maintainers.md` est aligné. Le seul reste est le commentaire `:190-193`.
- **Verdict : OK.** Faiblesse préexistante de la logique de verdict (« GO » sur un run annulé) en INFO.

### `release-gate.yml` — `docker-build` (`23e4c81`, `:199-273`)

- **`fail-fast: false` (`:204`)** : les deux jambes vont au bout. `needs.docker-build.result` vaut `failure` si une seule échoue : le commentaire `:772-774` est exact.
- **`Free disk space` (`:211-219`)** : `if: matrix.target == 'local'`, contexte `matrix` valide au niveau step. Placé avant `setup-buildx-action` : `docker system prune -af` ne supprime pas le builder. `sudo rm -rf` sur des chemins absents ne fait pas échouer l'étape.
- **`build-args` (`:244-247`)** : `APP_VERSION` (`Dockerfile:13`, `:24`), `BAKE_MODELS` (`:86`), `WITH_REASONING` (`:90`) existent. `WITH_REASONING=${{ matrix.target == 'local' && 'true' || 'false' }}` donne `true` pour `local`. Pour `remote`, `BAKE_MODELS` et `WITH_REASONING` ne sont déclarés dans aucun étage parcouru : BuildKit affiche un avertissement « build-arg not consumed », sans échec (même situation que `release.yml`).
- **Disque et durée** : image ≈ 1,92 Go, archive gzip d'environ 1 Go ; aucun `timeout-minutes` (360 min par défaut). Tient sur un runner standard, détails en INFO.
- **Verdict : OK.**

### `release-gate.yml` — `docker-smoke`, contrôle des en-têtes (`23e4c81`, `:327-376`)

- Shell : `bash -e` sans `pipefail`, voulu ici. `expect_header` et le test d'`index.html` sont dans des `if`, donc un `grep` sans correspondance n'arrête pas le script. Toutes les variables sont citées.
- Motifs `grep -iE` : `nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin` correspondent à `nginx.conf.template:14-17`, `:29-32` ; `expires 1y` et `add_header Cache-Control "public, immutable"` (`:27-28`) produisent deux lignes `Cache-Control`, chacune trouvée par son motif. Le `\r` de fin de ligne ne gêne pas : aucun motif n'est ancré en fin. `^HTTP/[0-9.]+ 200` correspond à `HTTP/1.1 200 OK`.
- Repérage de l'asset (`:348`) : `grep -oE '/assets/[^"]+\.js'` trouve `/assets/index-<hash>.js` dans l'`index.html` de Vite (vérifié sur `frontend/dist/index.html`) ; le pipeline se termine par `head -1`, pas d'arrêt sur `grep` vide, et le cas vide est compté comme échec.
- Gzip (`:364`) : GET avec `-o /dev/null -D -`, pas HEAD ; le JS dépasse `gzip_min_length 1024`, `application/javascript` est dans `gzip_types`.
- Nettoyage : `docker stop`/`docker rm` (`:370`) passent **avant** le `exit 1` des en-têtes (`:372-375`). Un `curl` en échec dans une substitution arrêterait le script avant le nettoyage, mais le runner est jetable et l'étape échoue quand même : pas de faux vert.
- **Verdict : OK.**

### `release-gate.yml` — `image-scan` (`23e4c81`, `:378-456`)

- `Free disk space` (`:392-400`) avant `Download image` : correct. Trivy lit l'image dans le démon et en fait une copie temporaire : place suffisante après nettoyage.
- Le scan CRITICAL bloque aussi pour `local` avec reasoning. **Seul un run dira** si `docling-agent`, `mellea` et leurs dépendances apportent un CRITICAL non supprimé.
- **Verdict : OK.**

### `release-gate.yml` — `e2e-ui` (`23e4c81`, `:707-715`)

- Même commande que `ci.yml`, mêmes conclusions. **Verdict : OK.**

### `release-gate.yml` — permissions par job

- Jeton par défaut (`write`) : `lint-typecheck`, `unit-tests`, `dep-audit`, `docker-build`, `docker-smoke`, `image-scan`, `e2e-api`, `e2e-ui`. Bloc explicite : `image-size` (`packages: read`), `release-summary` (`pull-requests: write`, `actions: read`). Aucun job n'a besoin de plus que `contents: read`, sauf `release-summary` (commentaire de PR) et `image-size` (`packages: read`). Voir INFO.

### `docker-compose.yml` et `docker-compose.dev.yml` (`efc0bc5`)

- `MAX_IMPORT_SIZE_MB: ${MAX_IMPORT_SIZE_MB:-200}` et `API_ALLOWED_HOSTS: ${API_ALLOWED_HOSTS:-}` (`docker-compose.yml:174-176`, `docker-compose.dev.yml:146-148`) : même forme `${VAR:-défaut}` que leurs voisins (`MAX_FILE_SIZE_MB`, `MCP_ALLOWED_HOSTS` à `:198`).
- Uniquement dans le service `document-parser`, seul à servir `/api` ; ni `frontend`, ni `docling-serve`, ni `opensearch`, ni `embedding`. `docker-compose.ingestion.yml` surcharge le même service et en hérite.
- Valeurs vides sans effet de bord : `API_ALLOWED_HOSTS=""` donne une liste vide et pas de middleware ; `NGINX_MAX_BODY_SIZE` (`200M`, `:213`) reste au niveau de `MAX_IMPORT_SIZE_MB`.
- **Verdict : OK.**

### `docs/maintainers.md`

- Le tableau du gate correspond au workflow (plus de ligne « Audit script », image `local` avec reasoning sans modèles, en-têtes au smoke, Trivy sur les deux images). **Verdict : OK.**

### Checks requis à poser

- **`release/**`** (protection de branche, sur les PR) : `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)`. Ne pas exiger `Backend tests (docling)` ni `E2E UI tests (Karate UI)` : ils sont `skipped` sur une PR vers une branche de release, et un job sauté compte comme réussi ; ils ne protègent que par leur run `push` après le merge.
- **`main`** : les trois mêmes + `Backend tests (docling)` ; pour le gate : `Lint & type-check`, `Unit tests`, `Docker build — remote`, `Docker build — local`, `Docker smoke test`, `Security scan — remote`, `Security scan — local`, `E2E API tests (full scope)`, `E2E UI tests (@critical)`.

### Ce que seul un run peut dire

- Que l'image `local` avec reasoning se construit sur le lock actuel en amd64, dans le temps et le disque estimés.
- Que Trivy ne trouve aucun CRITICAL non supprimé dans les paquets du reasoning.
- Que les 64 tests Docling passent sans réseau vers le Hub et sans `poppler`.
- Que surefire filtre `UIRunner#testCritical` et que les journeys `@critical` réécrits passent.
- Que nginx renvoie réellement les en-têtes attendus (`nginx -t`, gzip, cache).
- Que l'e2e API passe sur `efc0bc5` avec les schémas de réponse de l'éditeur, qui refusent désormais les clés inconnues.
- Que lint, format, type-check et tests sont toujours propres après 22 commits.

---

## Points positifs

- **L'image `local` que les utilisateurs tirent est enfin construite et scannée avant le tag**, reasoning compris, et `pip-audit` voit les mêmes groupes que l'image.
- **Le gate peut échouer sur les en-têtes nginx**, et le contrôle est écrit pour ne pas tomber sur un faux négatif (GET pour le gzip, cas « aucun asset » compté, nettoyage avant l'échec).
- **Les tests qui se sautaient sans Docling tournent maintenant** à chaque push sur `main` et `release/**`, avec une garde contre la suite vide.
- **Fini le faux vert d'`audit-checks`**, supprimé proprement, sans reste dans le verdict, les artefacts ou la doc.
- **CI en lecture seule**, pushs de release jamais annulés, les deux suites rapportées même quand l'une échoue.
- **Compose cohérent** : deux variables, même forme que les voisines, au seul service concerné, défauts identiques au code.

---

## Verdict partiel : NO-GO

85/100, 1 CRITICAL, 0 MAJOR, 0 MINOR → **NO-GO** (règle absolue : tout CRIT non résolu). Lecture stricte de 10.2.3 : 75, 1 MAJ, même verdict. Le CRIT est un manque de preuve : il se lève sur GitHub seulement (suites relancées en local sur `efc0bc5`, PR verte vers `release/0.7.4`, run `push` vert sur le merge, puis Release Gate vert avant le tag). La revue ne trouve aucun défaut qui ferait échouer un job ou le ferait passer à tort ; trois retouches recommandées avant le gate : `permissions: contents: read` en tête de `release-gate.yml`, verdict du résumé sur `!= success` avec `!cancelled()`, `compression-level: 0` sur l'artefact image.

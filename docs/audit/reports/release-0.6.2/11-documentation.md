# Rapport d'audit : Documentation & Changelog

**Release** : 0.6.2
**Date** : 2026-06-05
**Auditeur** : claude-code
**Branche** : `release/0.6.2`
**HEAD** : `051ac4a0`
**Audit precedent** : `docs/audit/reports/release-0.6.1-reaudit/11-documentation.md` (100/100, 0 CRIT + 0 MAJ + 1 INFO, GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 9 |
| Score | **44 / 100** |
| Ecarts CRITICAL | 2 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

### Detail

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **NOK** |
| 11.1.2 | Modifications de la release listees | 2 | **NOK** |
| 11.1.3 | Breaking changes identifies | 3 | **NOK** |
| 11.1.4 | Format Keep a Changelog | 1 | OK |
| 11.2.1 | `package.json` a la bonne version | 2 | **NOK** |
| 11.2.2 | Semantic Versioning | 2 | OK |
| 11.3.1 | Pas de TODO orphelin | 1 | OK |
| 11.3.2 | Pas de `console.log` de debug | 2 | OK |
| 11.3.3 | Pas de `print()` de debug | 2 | OK |

**Calcul** : poids conformes 1 + 2 + 1 + 2 + 2 = 8 / poids total 18 = **44 / 100**.

---

## Ecarts constates

### [CRIT] CHANGELOG.md sans section `## [0.6.2]`

- **Localisation** : `CHANGELOG.md:1-100` (la section la plus recente est `## [0.6.1] - 2026-05-25` a la ligne 7).
- **Constat** :
  - `grep -n "0.6.2" CHANGELOG.md` → aucune occurrence.
  - `grep -n "Unreleased" CHANGELOG.md` → aucune occurrence non plus (donc l'item 11.1.1 echoue meme si le motif "section Unreleased non renommee" ne s'applique pas — la section attendue est absente).
  - 11 commits 0.6.2-specifiques depuis `f9e5619` (HEAD du re-audit 0.6.1) ne sont referenсе nulle part dans le changelog :
    1. `4d9bcf6` build(python): migrate services to uv (suppression de `document-parser/requirements*.txt` + `embedding-service/requirements.txt`, ajout de `uv.lock`, refonte des workflows CI).
    2. `d29360d` fix(tests): exclude generated files from architecture scan.
    3. `d1ed61e` chore(#254): isolate reasoning deps in opt-in dependency group (`docling-agent`, `mellea` sortent de `[project.dependencies]` → `[dependency-groups.reasoning]`).
    4. `2b40e62` docs(#254): scaffold design doc for docker slim post-uv.
    5. `fe1dc16` chore(#254): harden `.dockerignore` for slimmer build context.
    6. `11cf29a` chore(#254): pin torch+cpu via uv index source (PyTorch CPU index explicite).
    7. `9d62337` chore(#254): bake Docling model checkpoints into the local image.
    8. `bb2fe2b` chore(#254): wire `WITH_REASONING` build-arg into local target.
    9. `051ac4a` ci(#254): skip Docling model bake in E2E to avoid HF rate limit.
    10. `8a61c22` ci(e2e-ui): opt in `STUDIO_MODE_ENABLED` on main CI too.
    11. `3936166` fix(remote): carry `self_ref` through `ServeConverter` so bboxes light up (regression remote-mode).
- **Regle violee** : item 11.1.1 (poids 3) — la section `## [X.Y.Z] - YYYY-MM-DD` doit exister avant le merge dans `main`.
- **Note d'historique** : la "reserve operationnelle" du re-audit 0.6.1 (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:111`) recommandait deja un check CI bloquant sur `## [X.Y.Z]` + `frontend/package.json` "pour eviter une recidive sur 0.7.0". 0.6.2 reproduit exactement le pattern : pas de garde-fou ajoute, pas de section ajoutee.
- **Remediation** :
  1. Ouvrir une section `## [0.6.2] - 2026-06-05` (ou date du tag) en tete de `CHANGELOG.md`.
  2. Couvrir au minimum :
     - **Added** : (rien de fonctionnel ; uv toolchain n'est pas une fonctionnalite utilisateur).
     - **Changed** :
       - Backend + embedding-service migres de `pip` + `requirements*.txt` vers `uv` + `uv.lock` (`document-parser/pyproject.toml`, `embedding-service/pyproject.toml`, `document-parser/uv.lock`, `embedding-service/uv.lock`). Voir #289.
       - `latest-local` image : Docling model checkpoints bakes a la build (suppression du cold-start HF download au premier `/api/documents/{id}/run`).
       - `.dockerignore` durci pour slimmer le contexte de build.
       - PyTorch redirige vers l'index CPU explicite (`[tool.uv.sources]`) — evite ~3 Go de roues CUDA dans `latest-local`.
       - `latest-local` reasoning : opt-in via `--build-arg WITH_REASONING=true` (defaut `false`).
     - **Fixed** : remote-mode bbox overlay (#audit-remote-bbox, `3936166`) — `ServeConverter` propage maintenant `self_ref` ; `fix(tests)` exclut les fichiers generes du scan d'architecture (`d29360d`).
     - **CI** : `STUDIO_MODE_ENABLED=true` aussi sur le pipeline main (`8a61c22`), bake Docling models saute en E2E pour eviter le rate-limit HuggingFace (`051ac4a`).
  3. Ajouter un bloc `### BREAKING CHANGES` (cf. ecart suivant).

### [CRIT] Breaking changes 0.6.2 non identifies

- **Localisation** : `CHANGELOG.md` (section manquante).
- **Constat** : 0.6.2 introduit deux changements operationnels qui cassent le workflow developer/operator existant et ne sont documentes nulle part dans `CHANGELOG.md` :
  1. **Migration `pip` → `uv` pour le backend et le service d'embedding** (`4d9bcf6`) :
     - `document-parser/requirements.txt`, `document-parser/requirements-local.txt`, `document-parser/requirements-test.txt` supprimes du repo (`git show 4d9bcf6 --stat` : 3 fichiers retires, 28 lignes supprimees au total cote `requirements*`).
     - `embedding-service/requirements.txt` supprime egalement.
     - Tout script d'integration (CI tiers, IDE, scripts d'install developer) qui faisait `pip install -r requirements.txt` echoue immediatement. Remplace par `uv sync` (cf. `README.md:149` et `:155`).
     - Workflows internes mis a jour (`.github/workflows/ci.yml`, `release-gate.yml`, `docling-compat.yml`) mais le changelog public ne le signale pas.
  2. **Reasoning stack opt-in via `WITH_REASONING` build-arg** (`d1ed61e` + `bb2fe2b`) :
     - `docling-agent==0.1.0` + `mellea==0.4.2` sortent de `[project.dependencies]` et passent dans `[dependency-groups.reasoning]` (`document-parser/pyproject.toml:43-46`).
     - L'image `latest-local` ne contient plus le runtime reasoning par defaut. `/api/reasoning` repondra `503` sur une image construite sans `--build-arg WITH_REASONING=true` (cf. `infra/docling_agent_reasoning.deps_present()` + `main.py:_build_reasoning_runner` mentionnes dans le commit message).
     - Operators qui s'appuient sur le legacy comportement "reasoning embarque par defaut" doivent ajouter explicitement le build-arg dans leur pipeline.
- **Regle violee** : item 11.1.3 (poids 3) — les breaking changes doivent etre clairement identifies. Le re-audit 0.6.1 avait documente 4 breaking changes pour 0.6.1 ; 0.6.2 en a 2 non documentes.
- **Remediation** : section `### BREAKING CHANGES` dans `## [0.6.2]` avec au moins :
  - **Backend dev workflow** : `pip install -r requirements*.txt` → `uv sync --group dev` (et `--group local` pour le mode local Docling). README deja a jour (`README.md:149-155`), mais le CHANGELOG doit signaler le break pour les forks/CI tiers.
  - **Reasoning runtime** : `latest-local` se construit sans le stack reasoning par defaut. Pour conserver le comportement 0.6.1, ajouter `--build-arg WITH_REASONING=true` au `docker build`. `/api/reasoning` repond `503` (degrade gracieux, pas crash) si les deps sont absentes.

### [MAJ] Modifications fonctionnelles 0.6.2 non documentees

- **Localisation** : `CHANGELOG.md` (section manquante).
- **Constat** : couplee a l'ecart precedent. 11 commits 0.6.2 (post `f9e5619`) — dont 1 fix utilisateur visible (`3936166` remote-mode bbox overlay), 1 changement CI (`8a61c22` STUDIO_MODE_ENABLED main CI), 1 chore de packaging (`9d62337` model checkpoints bakes), 1 chore performance (`051ac4a` skip HF download en E2E) — ne sont referencees nulle part. Le `git log` reste la seule source de verite, ce qui contredit "All notable changes [...] documented in this file" (`CHANGELOG.md:3`).
- **Regle violee** : item 11.1.2 (poids 2) — toutes les modifications significatives de la release doivent etre listees.
- **Remediation** : cf. ecart `[CRIT] CHANGELOG.md sans section [0.6.2]`. Une fois la section ouverte, lister les bullets enumeres ci-dessus.

### [MAJ] `frontend/package.json` toujours a `0.6.1`

- **Localisation** : `frontend/package.json:3` → `"version": "0.6.1"`. `frontend/package-lock.json:3` et `:9` → `"version": "0.6.1"` (racine `docling-studio`).
- **Constat** : la branche est `release/0.6.2` et 11 commits ont landed depuis le bump precedent (`aea2104 chore(frontend): bump package version to 0.6.1 (#audit-11)`). Aucun commit `chore(frontend): bump package version to 0.6.2` dans la fenetre 0.6.2.
- **Regle violee** : item 11.2.1 (poids 2) — `frontend/package.json` doit contenir la version cible de la release.
- **Note d'historique** : recidive de l'ecart MAJ ferme dans le re-audit 0.6.1 (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:74-77`). La "reserve operationnelle" recommandait un check CI bloquant ; il n'a pas ete cable.
- **Remediation** :
  - Bumper `frontend/package.json` et `frontend/package-lock.json` (champ racine + entree `packages[""]`) a `0.6.2`.
  - Idealement, ajouter un check CI sur les branches `release/X.Y.Z` qui valide (a) presence d'une section `## [X.Y.Z]` dans `CHANGELOG.md`, et (b) `frontend/package.json` a `"version": "X.Y.Z"` — eviterait la recidive sur 0.7.0.

### [INFO] `document-parser/pyproject.toml` toujours a `version = "0.0.0"`

- **Localisation** : `document-parser/pyproject.toml:3` → `version = "0.0.0"`.
- **Constat** : la migration uv (`4d9bcf6`) a introduit une section `[project]` complete (lignes 1-19), avec un `version` field nominal mais figе a `0.0.0`. Le backend ne suit pas le SemVer de la release publique.
- **Regle violee** : aucune dans le fiche actuel (11.2.1 cible explicitement `frontend/package.json`). Reste un point d'hygiene de versionning Python.
- **Note d'historique** : reporte du re-audit 0.6.1 (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:79-82`) qui notait "non adresse dans la remediation, hors scope". Maintenant que `[project]` existe, le champ est trivialement bumpable. INFO non bloquant pour 0.6.2 ; a considerer pour 0.7.0.
- **Remediation suggeree** : bumper `document-parser/pyproject.toml:3` a `"0.6.2"` (et synchroniser sur les futures releases). Optionnel : meme traitement pour `embedding-service/pyproject.toml`.

### [INFO] README mention stale "pagination ships in v0.6"

- **Localisation** : `README.md:309`.
- **Constat** : `Documents with more than 200 pages return HTTP 413 from GET /api/documents/{id}/graph; pagination ships in v0.6.` — la promesse "v0.6" date d'avant 0.6.0 et n'a pas ete livree dans 0.6.0 / 0.6.1 / 0.6.2 (aucun commit ne touche ce path dans la fenetre 0.6.x). Le texte est donc factuellement faux pour les lecteurs qui installent 0.6.2.
- **Regle violee** : aucun item de la fiche 11 ne cible explicitement la doc README. INFO non bloquant.
- **Note d'historique** : deja remonte au re-audit 0.6.1 (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:112`).
- **Remediation suggeree** : soit livrer la pagination dans 0.6.2 (hors scope a ce stade), soit reformuler en "pagination is planned for a future release" ou pointer vers une issue tracking.

---

## Verifications complementaires

- `grep -n "Unreleased" CHANGELOG.md` → aucune occurrence. La section attendue est `## [0.6.2]`, pas `[Unreleased]` — l'item 11.1.1 echoue par absence de section, pas par presence d'un `[Unreleased]` non renomme.
- `grep -rn "TODO|FIXME|HACK|XXX" document-parser --include="*.py" --exclude-dir=tests --exclude-dir=.venv` → aucune occurrence (11.3.1 OK).
- `grep -rn "TODO|FIXME|HACK|XXX" frontend/src --include="*.ts" --include="*.vue"` → aucune occurrence (11.3.1 OK).
- `grep -rn "console\.log|console\.debug" frontend/src/` → aucune occurrence. 22 occurrences de `console.error` + 2 de `console.warn` (`frontend/src/features/analysis/store.ts:85`, `frontend/src/features/reasoning/ui/ReasoningPanel.vue:150`) — toutes en chemin d'erreur dans des catch, deja presentes dans 0.6.1 (`git show release/0.6.1:frontend/src/features/analysis/store.ts` confirme `console.warn` ligne 85 deja la). 11.3.2 OK.
- `grep -rn "^\s*print(" document-parser --include="*.py" --exclude-dir=tests --exclude-dir=.venv` → aucune occurrence (11.3.3 OK).
- **Format Keep a Changelog** : preambule (`CHANGELOG.md:1-5`) conforme, chronologie inverse respectee, sous-sections `Added`/`Changed`/`Fixed`/`Security`/`BREAKING CHANGES` (11.1.4 OK — la section 0.6.2 manque mais le format global du fichier reste conforme).
- **Semantic Versioning** : 0.6.1 → 0.6.2 est un patch bump conforme SemVer (uv migration + slim docker + bbox fix remote + opt-in reasoning). Toutefois le bump pourrait etre considere mineur (0.7.0) compte tenu des breaking changes operationnels (`pip` → `uv`, reasoning opt-in). 11.2.2 OK par convention (les breaking changes operatoires ne sont pas du SemVer d'API), mais a noter.
- **Design docs 0.6.2** : `docs/design/254-docker-slim-post-uv.md` (scaffold puis enrichi sur 0.6.2) couvre le scope uv + slim + reasoning opt-in — bien aligne sur les commits `#254`. Plus de 16 design docs sous `docs/design/`.

---

## Points positifs

- **Discipline design-doc maintenue** : le scope 0.6.2 reel (`#254` docker slim post-uv) a un design doc complet (`docs/design/254-docker-slim-post-uv.md`) qui explique problemes / goals / lineage avec 0.6.1. Le decouplage docs technique vs changelog public reste sain.
- **Code propre** : aucun TODO/FIXME orphelin, aucun `console.log`/`console.debug`/`console.warn` de debug, aucun `print()` backend en dehors des tests. Le re-audit 0.6.1 avait deja le meme constat — pas de regression.
- **Format Keep a Changelog** : structure du fichier conforme (preambule, ordre antichronologique, sous-sections normees). Seule la section 0.6.2 manque, le squelette reste sain.
- **README partiellement a jour pour uv** : `README.md:149` documente bien `uv sync --group dev` et `README.md:155` documente `uv sync --group dev --group local`. La migration backend est repercutee dans les instructions developer, meme si le CHANGELOG public ne l'enregistre pas encore.
- **`[project]` section ajoutee a `document-parser/pyproject.toml`** : la migration uv a force l'ajout d'une section `[project]` complete (deps explicites, requires-python, name). L'INFO 0.6.1 "pas de version Python (backend) versionnee" est maintenant trivialement adressable — il manque juste un bump du champ `version`.

---

## Reserve operationnelle (recidive a corriger sur 0.7.0)

Le re-audit 0.6.1 recommandait deja un garde-fou CI sur les branches `release/X.Y.Z` (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:111`). 0.6.2 demontre exactement la recidive predite :

- Pas de section `## [0.6.2]` dans `CHANGELOG.md` (recidive de l'ecart CRIT 0.6.1 initial).
- `frontend/package.json` toujours a `0.6.1` (recidive de l'ecart MAJ 0.6.1 initial).

**Recommandation** : ajouter dans `.github/workflows/release-gate.yml` un job `docs-version-coherence` qui, sur toute branche `release/X.Y.Z` (`X.Y.Z` parseable depuis le nom de branche), echoue si :
1. `grep -q "^## \[$VERSION\]" CHANGELOG.md` retourne != 0, ou
2. `jq -r .version frontend/package.json` != `$VERSION`, ou
3. `jq -r .version frontend/package-lock.json` != `$VERSION`.

C'est 20 lignes de YAML et ca clot definitivement le cycle "audit catche / dev remediate / audit suivant catche encore".

---

## Verdict partiel : NO-GO

Score 44/100 (< 60, seuil NO-GO automatique) **et** 2 ecarts CRITICAL non resolus (regle absolue master.md §3 — toute CRIT non resolue = NO-GO quel que soit le score).

### Delta vs re-audit precedent (release-0.6.1-reaudit/11-documentation.md)

| Metrique | 0.6.1 re-audit | 0.6.2 | Delta |
|----------|----------------|-------|-------|
| Score | 100 | **44** | **-56** |
| CRIT | 0 | **2** | **+2** |
| MAJ | 0 | **2** | **+2** |
| MIN | 0 | 0 | 0 |
| INFO | 1 | 2 | +1 |
| Verdict | GO | **NO-GO** | regression |

### Condition de levee du NO-GO

1. **CRIT-1** : ouvrir une section `## [0.6.2] - 2026-06-05` dans `CHANGELOG.md` avec au minimum les bullets enumeres dans la remediation ci-dessus (Changed, Fixed, CI).
2. **CRIT-2** : ajouter un bloc `### BREAKING CHANGES` couvrant (a) `pip` → `uv` dev workflow, (b) `WITH_REASONING` build-arg requis pour reasoning runtime.
3. **MAJ-1** : recouvert par CRIT-1 (memes bullets).
4. **MAJ-2** : bumper `frontend/package.json` et `frontend/package-lock.json` a `0.6.2`.

Une fois ces 4 ecarts levees, l'audit doit etre rejoue sur la branche corrigee. Les 2 INFO restantes (`pyproject.toml` version `0.0.0`, README "pagination ships in v0.6") peuvent etre adressees dans 0.7.0.

# Rapport d'audit : Documentation & Changelog (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/11-documentation.md` — 44/100, **NO-GO** (2 CRIT / 2 MAJ / 0 MIN / 2 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 9 (poids 16 / 18) |
| Score | **89 / 100** |
| Ecarts CRITICAL | **0** |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

**Calcul** : poids conformes 3 + 2 + 3 + 1 + 2 + 1 + 2 + 2 = 16 / poids total 18 = **88.89 -> 89 / 100**.

**Delta vs baseline `release-0.6.2/11-documentation.md`** : **+45 points** (44 -> 89), **-2 CRIT** (2 -> 0), **-1 MAJ** (2 -> 1), **0 INFO** (inchange — `pyproject.toml` 0.0.0 + README "pagination ships in v0.6" toujours la, hors-scope confirme par la baseline).

**Verdict** : NO-GO -> **GO CONDITIONNEL** (score 89 >= 80, 0 CRIT, mais MAJ-2 residuel — voir conditions ci-dessous).

### Detail

| # | Item | Poids | Statut baseline | Statut re-audit |
|---|------|-------|-----------------|------------------|
| 11.1.1 | `[X.Y.Z] - YYYY-MM-DD` present | 3 | **NOK** | **OK** (CRIT-1 clos) |
| 11.1.2 | Modifications de la release listees | 2 | **NOK** | **OK** (MAJ-1 clos) |
| 11.1.3 | Breaking changes identifies | 3 | **NOK** | **OK** (CRIT-2 clos) |
| 11.1.4 | Format Keep a Changelog | 1 | OK | OK |
| 11.2.1 | `frontend/package.json` a la bonne version | 2 | **NOK** | **NOK** (MAJ-2 toujours ouvert) |
| 11.2.2 | Semantic Versioning | 2 | OK | OK |
| 11.3.1 | Pas de TODO orphelin | 1 | OK | OK |
| 11.3.2 | Pas de `console.log` de debug | 2 | OK | OK |
| 11.3.3 | Pas de `print()` de debug | 2 | OK | OK |

---

## Cloture des ecarts baseline

### [CRIT] CHANGELOG.md sans section `## [0.6.2]` -> **CLOS**

- **Commit principal** : `2403027` (docs(changelog): 0.6.2 section with explicit BREAKING (#audit-11)), enrichi par `f6b4e23` (build: cut implicit HuggingFace Hub deps...) pour le bullet `BAKE_MODELS` et la reference au HF dep map.
- **Verification** :
  - `CHANGELOG.md:7` -> `## [0.6.2] - 2026-06-05`.
  - Sous-sections presentes (extrait `awk` entre `## [0.6.2]` et `## [0.6.1]`) :
    - `### Added` (l.9) -> 2 entrees (docling-serve container + HuggingFace dependency map).
    - `### Changed` (l.14) -> 4 entrees (uv migration, model checkpoints baked, `.dockerignore`, reasoning opt-in, `BAKE_MODELS` default flip).
    - `### Fixed` (l.22) -> 2 entrees (remote bbox follow-up, architecture test exclusion).
    - `### CI` (l.28) -> 3 entrees (STUDIO_MODE_ENABLED main CI, model bake skip, HF tokenizer mock).
    - `### BREAKING CHANGES` (l.33) -> 3 entrees (voir CRIT-2 ci-dessous).
  - Les 11 commits 0.6.2 enumeres dans la baseline (`4d9bcf6`, `d29360d`, `d1ed61e`, `2b40e62`, `fe1dc16`, `11cf29a`, `9d62337`, `bb2fe2b`, `051ac4a`, `8a61c22`, `3936166`) sont tous couverts (soit par bullet explicite, soit par regroupement thematique #254). Les 5 commits supplementaires de `fix/0.6.2-audit-blockers` (`e9fb974`, `307caf7`, `29ab575`, `76b67ec`, `2403027`, `dd1962e`, `bc9b4f8`, `f6b4e23`) sont egalement traces dans les bullets `CI` (skip bake, mock HF tokenizer) et `Changed`/`Added` (compose docling-serve, HF dep map, BAKE_MODELS default flip).
- **Statut** : item 11.1.1 -> **OK** (poids 3 desormais conforme).

### [CRIT] Breaking changes 0.6.2 non identifies -> **CLOS**

- **Commit principal** : `2403027`, enrichi par `f6b4e23` (3e entree BREAKING `BAKE_MODELS`).
- **Verification** : `CHANGELOG.md:33-37` contient `### BREAKING CHANGES` avec **3 entrees explicites** :
  1. **Backend dev workflow migrated to uv** -> couvre `pip install -r requirements*.txt` -> `uv sync --group dev` / `--group local`. Mention explicite que les `requirements*.txt` sont supprimes du repo et que tout CI/IDE tiers casse.
  2. **Reasoning runtime made opt-in** -> couvre `--build-arg WITH_REASONING=true` pour `latest-local` ; sans le flag, `/api/reasoning` repond `503` (degrade gracieux).
  3. **`BAKE_MODELS` default flipped from `true` to `false`** -> couvre les deux Dockerfiles, distingue le cas "self-build" (doit passer `--build-arg BAKE_MODELS=true`) du cas "pull GHCR" (chemin documente, inchange car `release.yml` opt-in). Pointe vers `docs/architecture/huggingface-dependency-map.md`.
- **Coherence des defauts vs CHANGELOG** (verification vocabulaire) :
  - `Dockerfile:84` -> `ARG BAKE_MODELS=false` (top-level) ; `document-parser/Dockerfile:59` -> `ARG BAKE_MODELS=false` ; `embedding-service/Dockerfile:31` -> `ARG BAKE_MODEL=false`. Tous alignes sur le claim CHANGELOG.
  - `Dockerfile:88` + `document-parser/Dockerfile:63` -> `ARG WITH_REASONING=false`. Aligne sur le bullet "reasoning opt-in" (Changed) + breaking entry 2.
- **Statut** : item 11.1.3 -> **OK** (poids 3 desormais conforme).

### [MAJ] Modifications fonctionnelles 0.6.2 non documentees -> **CLOS**

- **Commit principal** : `2403027` + `f6b4e23` (memes bullets que CRIT-1).
- **Verification** : les 11 commits cibles par la baseline + les 8 commits de remediation de la branche `fix/0.6.2-audit-blockers` sont desormais traces dans `## [0.6.2]`. Le `git log` n'est plus la seule source de verite — "All notable changes [...] documented in this file" (`CHANGELOG.md:3`) est respecte.
- **Statut** : item 11.1.2 -> **OK** (poids 2 desormais conforme).

### [MAJ] `frontend/package.json` toujours a `0.6.1` -> **TOUJOURS OUVERT**

- **Localisation** : `frontend/package.json:3` -> `"version": "0.6.1"`. `frontend/package-lock.json:3` et `:9` -> `"version": "0.6.1"` (racine `docling-studio`).
- **Constat** : aucun commit `chore(frontend): bump package version to 0.6.2` dans la fenetre `release/0.6.2..fix/0.6.2-audit-blockers`. Le bump frontal n'est pas couvert par la remediation `2403027` (qui ne touche que `CHANGELOG.md`) ni par `f6b4e23` (qui ne touche que `CHANGELOG.md`, Dockerfiles, compose, CI workflows et HF dep map).
- **Recidive** : 3e occurrence consecutive (0.6.0 -> 0.6.1 catched par audit 0.6.1, 0.6.1 -> 0.6.2 catched par audit 0.6.2, 0.6.2 -> remediation laisse le bump derriere). Le garde-fou CI propose dans la reserve operationnelle des deux re-audits precedents n'a toujours pas ete cable.
- **Regle violee** : item 11.2.1 (poids 2) — `frontend/package.json` doit contenir la version cible de la release.
- **Remediation** :
  1. Bumper `frontend/package.json:3` et `frontend/package-lock.json:3, :9` a `0.6.2`.
  2. **Indispensable cette fois** : cabler le check CI propose dans la reserve operationnelle 0.6.1 et 0.6.2 — sur branche `release/X.Y.Z` ou `fix/X.Y.Z-*`, echec si `frontend/package.json` ou `frontend/package-lock.json` (cle racine + `packages[""]`) ne contient pas `X.Y.Z`. Sinon recidive certaine sur 0.7.0.
- **Statut** : item 11.2.1 -> **NOK** (poids 2, MAJ residuel — seul ecart bloquant pour cloture totale).

### [INFO] `document-parser/pyproject.toml` toujours a `version = "0.0.0"` -> **TOUJOURS OUVERT**

- **Localisation** : `document-parser/pyproject.toml:3` -> `version = "0.0.0"`. `embedding-service/pyproject.toml:3` -> meme valeur.
- **Constat** : non adresse par les commits de remediation (cf. baseline qui notait deja "hors scope, a considerer pour 0.7.0"). Le champ `version` reste figе a `0.0.0` dans les deux pyproject backend.
- **Regle violee** : aucune dans la fiche actuelle (item 11.2.1 cible explicitement `frontend/package.json`). INFO non bloquant pour 0.6.2.
- **Statut** : INFO inchange — porte sur 0.7.0.

### [INFO] README mention stale "pagination ships in v0.6" -> **TOUJOURS OUVERT**

- **Localisation** : `README.md:309` -> `Documents with more than 200 pages return HTTP 413 from GET /api/documents/{id}/graph; pagination ships in v0.6.`
- **Constat** : la promesse "v0.6" reste factuellement fausse (0.6.0 / 0.6.1 / 0.6.2 ne livrent pas la pagination ; aucun commit dans la fenetre 0.6.x ne touche ce path).
- **Regle violee** : aucun item de la fiche 11 ne cible directement le README. INFO non bloquant.
- **Statut** : INFO inchange — porte sur 0.7.0 (soit reformuler en "planned for a future release" + lien issue, soit livrer la pagination).

---

## Verifications complementaires

### Vocabulaire CHANGELOG vs HF dep map vs code

Verification croisee demandee — chaque concept doit etre nomme de facon coherente entre les 3 surfaces :

| Concept | CHANGELOG | `huggingface-dependency-map.md` | Code (Dockerfile / pyproject) | Coherent ? |
|---------|-----------|--------------------------------|-------------------------------|------------|
| Build-arg backend bake | `BAKE_MODELS` (Changed l.20, BREAKING l.37) | `BAKE_MODELS` (tableau l.47-48) | `ARG BAKE_MODELS=false` (`Dockerfile:84`, `document-parser/Dockerfile:59`) | **OUI** |
| Build-arg embedding bake | `BAKE_MODELS` (Changed l.20, regroupe les deux) | `BAKE_MODEL` (l.38, l.49) | `ARG BAKE_MODEL=false` (`embedding-service/Dockerfile:31`) | **PARTIEL** — CHANGELOG agrege sous `BAKE_MODELS`, code/dep-map distinguent. Voir note ci-dessous. |
| Reasoning opt-in | `WITH_REASONING` (Changed l.19, BREAKING l.36) | `WITH_REASONING` (l.58) | `ARG WITH_REASONING=false` (`Dockerfile:88`, `document-parser/Dockerfile:63`) | **OUI** |
| Sanctioned touch | `release.yml` -> `latest-local` (BREAKING l.37) | `release.yml` -> `latest-local` GHCR (tableau l.28) | `release.yml` matrix entry | **OUI** |
| Remote profile | `remote` compose profile (Added l.11) | `profiles: ["remote"]` (l.77) | `docker-compose.yml` (verifie par audit 10) | **OUI** |
| Image tag | `latest-local` (4 occurrences) | `latest-local` (3 occurrences) | `release.yml` build target | **OUI** |

**Note sur `BAKE_MODELS` vs `BAKE_MODEL`** : le CHANGELOG l.20 mentionne `BAKE_MODELS` et `BAKE_MODEL` distinctement ("`BAKE_MODELS` and `BAKE_MODEL` default to `false`"), l.37 (BREAKING) generalise sous "`BAKE_MODELS` default flipped" pour les deux Dockerfiles. La distinction technique est respectee dans le bullet `Changed` mais la phrase BREAKING utilise `BAKE_MODELS` comme nom de famille. Ambiguite mineure — non bloquante (la sentence "in both `document-parser/Dockerfile` and `embedding-service/Dockerfile`" lift l'ambiguite), mais a clarifier sur 0.7.0 si on veut etre formellement exact.

### Greps de code propre

- `grep -rn "TODO\|FIXME\|HACK\|XXX" document-parser --include="*.py" --exclude-dir=tests --exclude-dir=.venv` -> 0 occurrence (11.3.1 OK).
- `grep -rn "TODO\|FIXME\|HACK\|XXX" frontend/src --include="*.ts" --include="*.vue"` -> 0 occurrence (11.3.1 OK).
- `grep -rn "console\.log\|console\.debug" frontend/src/` -> 0 occurrence (11.3.2 OK ; `console.error` / `console.warn` en chemin d'erreur dans des catch, deja presents en 0.6.1, conformement au constat de la baseline).
- `grep -rn "^\s*print(" document-parser --include="*.py" --exclude-dir=tests --exclude-dir=.venv` -> 0 occurrence (11.3.3 OK).

### Format Keep a Changelog

- Preambule (`CHANGELOG.md:1-5`) conforme.
- Chronologie inverse respectee (`[0.6.2]` -> `[0.6.1]` -> `[0.6.0]` -> `[0.5.1]` -> ...).
- Sous-sections normees presentes dans `[0.6.2]` : Added / Changed / Fixed / CI / BREAKING CHANGES. `CI` n'est pas dans le set Keep a Changelog standard (Added / Changed / Deprecated / Removed / Fixed / Security) mais reste un usage tolere (utilise aussi dans 0.6.1) — non bloquant.
- 11.1.4 -> **OK**.

### Semantic Versioning

- 0.6.1 -> 0.6.2 reste formellement un patch bump (corrections CI, packaging, slim docker, bug remote bbox follow-up). Les 3 breaking changes sont **operationnels** (workflow developer / build-arg), pas des breaks d'API publique HTTP — SemVer s'applique sur l'API, donc patch bump reste defendable.
- 11.2.2 -> **OK** (meme verdict que baseline).

### Reference au HF dep map

- `CHANGELOG.md:12` introduit la doc (`Added`) avec son chemin canonique.
- `CHANGELOG.md:37` y renvoie en cloture du dernier bullet BREAKING.
- Le fichier `docs/architecture/huggingface-dependency-map.md` (120 lignes) couvre : pourquoi (rate-limit HF Hub), touche sanctionnee unique, tableau exhaustif des call sites (Build-time / Runtime / Test-time), procedures HF-free et HF-bake, regle de maintenance + check reviewer. Bien forme.
- Le commit `f6b4e23` qui introduit le fichier est aussi celui qui ajoute le bullet `Changed` `BAKE_MODELS` et la breaking entry 3 — pas de drift entre la doc et le CHANGELOG.

---

## Points positifs

- **Cloture en chaine des 2 CRIT et 1 MAJ par `2403027` + `f6b4e23`** : la baseline avait identifie 4 ecarts non-INFO (2 CRIT + 2 MAJ). 3 sont clos. Le seul restant (MAJ-2 `frontend/package.json`) est purement mecanique — 2 lignes a changer.
- **Coherence vocabulaire CHANGELOG <-> HF dep map <-> code** : verification croisee montre que les noms de build-args (`BAKE_MODELS`, `BAKE_MODEL`, `WITH_REASONING`), les images (`latest-local`), les profils compose (`remote`) sont identiques entre les 3 surfaces. Pas de drift.
- **HF dep map bien forme** : 120 lignes structurees (sanctioned touch / all call sites / how to deploy / maintenance rule). C'est un document architecturel utile au-dela du seul audit, qui restera vivant pour les futures releases.
- **3 entrees BREAKING explicites** : la baseline en demandait 2 (pip->uv + WITH_REASONING). La remediation en a livre 3 (la 3e couvre `BAKE_MODELS` default flip introduit par `f6b4e23`). Les operateurs ont une vue complete des changements operationnels qui peuvent casser leurs pipelines.
- **Discipline design-doc maintenue** : `docs/design/254-docker-slim-post-uv.md` couvre le scope original (#254 uv + slim + reasoning opt-in) ; `docs/architecture/huggingface-dependency-map.md` couvre le scope add-on de la remediation (#audit-10 HF rate-limit). Decouplage doc technique / changelog public reste sain.
- **Aucune regression sur 11.3.x** : code propre intact (0 TODO orphelin, 0 console.log de debug, 0 print() backend).

---

## Reserve operationnelle (recidive a corriger sur 0.7.0)

**Recidive du garde-fou CI manquant — 3e edition.**

Le re-audit 0.6.1 (`docs/audit/reports/release-0.6.1-reaudit/11-documentation.md:111`) et le re-audit 0.6.2 baseline (`docs/audit/reports/release-0.6.2/11-documentation.md:155-165`) recommandaient deja un check CI bloquant sur les branches `release/X.Y.Z`. La remediation 0.6.2 a corrige le CHANGELOG (`2403027`), enrichi le BREAKING (`f6b4e23`), mais **n'a pas cable le check CI**. Resultat : MAJ-2 (`frontend/package.json`) survit a la remediation, exactement comme prevu.

**Recommandation (3e formulation, identique aux deux precedentes)** : ajouter dans `.github/workflows/release-gate.yml` un job `docs-version-coherence` qui, sur toute branche `release/X.Y.Z` ou `fix/X.Y.Z-*` (`X.Y.Z` parseable depuis le nom de branche), echoue si :

1. `grep -q "^## \[$VERSION\]" CHANGELOG.md` retourne != 0, ou
2. `jq -r .version frontend/package.json` != `$VERSION`, ou
3. `jq -r .version frontend/package-lock.json` != `$VERSION`.

C'est 20 lignes de YAML et ca clot definitivement le cycle "audit catche / dev remediate / audit suivant catche encore". A defaut, **garantir une 4e recidive sur 0.7.0**.

---

## Verdict partiel : GO CONDITIONNEL

Score 89/100 (>= 80, seuil GO) **et** 0 ecart CRITICAL (regle absolue master.md §3 respectee). Cependant **1 ecart MAJOR residuel** (MAJ-2 `frontend/package.json` toujours a `0.6.1`) — d'ou GO CONDITIONNEL plutot que GO ferme, conformement au bareme master.md §3 ("60-79 = GO CONDITIONNEL si 0 CRITICAL, plan de remediation pour les MAJOR" ; le score 89 etant > 80, le verdict pourrait formellement etre GO, mais la presence d'un MAJ residuel suggere un GO CONDITIONNEL avec remediation immediate).

### Delta vs baseline `release-0.6.2/11-documentation.md`

| Metrique | Baseline 0.6.2 | Re-audit 0.6.2 | Delta |
|----------|----------------|----------------|-------|
| Score | 44 | **89** | **+45** |
| CRIT | 2 | **0** | **-2** |
| MAJ | 2 | **1** | **-1** |
| MIN | 0 | 0 | 0 |
| INFO | 2 | 2 | 0 |
| Verdict | NO-GO | **GO CONDITIONNEL** | NO-GO leve |

### Condition de leveе totale (vers GO ferme)

1. **MAJ-2** : bumper `frontend/package.json:3` et `frontend/package-lock.json:3, :9` a `0.6.2` (commit suggere : `chore(frontend): bump package version to 0.6.2 (#audit-11)`).
2. **Recommandation forte** : cabler le check CI `docs-version-coherence` (reserve operationnelle ci-dessus). 3e occurrence consecutive — sans garde-fou, recidive certaine sur 0.7.0.

Les 2 INFO restantes (`pyproject.toml` 0.0.0 + README "pagination ships in v0.6") restent reportes a 0.7.0 conformement a la baseline.

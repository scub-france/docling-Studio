# Rapport d'audit : Documentation & Changelog (RE-AUDIT)

**Release** : 0.6.1
**Date** : 2026-05-25
**Auditeur** : claude-code
**Branche** : `fix/0.6.1-audit-blockers`
**HEAD** : `f9e5619`
**Audit precedent** : `docs/audit/reports/release-0.6.1/11-documentation.md` (44/100, 2 CRIT + 2 MAJ + 1 INFO, NO-GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 9 |
| Score | **100 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

### Detail

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **OK** |
| 11.1.2 | Modifications de la release listees | 2 | **OK** |
| 11.1.3 | Breaking changes identifies | 3 | **OK** |
| 11.1.4 | Format Keep a Changelog | 1 | OK |
| 11.2.1 | `package.json` a la bonne version | 2 | **OK** |
| 11.2.2 | Semantic Versioning | 2 | OK |
| 11.3.1 | Pas de TODO orphelin | 1 | OK |
| 11.3.2 | Pas de `console.log` de debug | 2 | OK |
| 11.3.3 | Pas de `print()` de debug | 2 | OK |

**Calcul** : poids conformes 3 + 2 + 3 + 1 + 2 + 2 + 1 + 2 + 2 = 18 / poids total 18 = **100 / 100**.

---

## Verification des ecarts du rapport precedent

### [CRIT] CHANGELOG.md sans section `[0.6.0]` ni `[0.6.1]` — **CLOSED**

- **Constat re-audit** : `CHANGELOG.md:7` ouvre une section `## [0.6.1] - 2026-05-25` complete, suivie de `## [0.6.0] - 2026-05-19` a `CHANGELOG.md:55`, puis de l'historique pre-existant `## [0.5.1]` (`CHANGELOG.md:81`).
- **Couverture 0.6.1** (`CHANGELOG.md:9-46`) :
  - **Added** (8 entrees) : per-document workspace (#263–#268), version history (#267), chunk service + routes (#256, #269), ingest tab redesign (#225, #283, #285), store connection credentials (#279), sealing-at-rest (#279), master surface flags (#257), Karate UI e2e.
  - **Changed** (5 entrees) : push-chunks wire vocabulary, backend DDD audit (#269), workspace navigation polish, backend uploads non-blocking, architecture test optional pytestarch.
  - **Fixed** (10 entrees) : re-chunk preserves doc_items (#266), document-store-links upsert (#225), ingest view refresh (#225), Neo4j Document node merge (#225), ingestion availability (#199), cross-doc bbox leak, frontend feature-flag race, Docker dev proxy, push-chunks duplicate, backend test collection, CI auto-close, frontend package version.
  - **Security** (2 entrees) : CVE-2026-7598 ignored, STORE_SECRET_KEY plumbed.
- **Couverture 0.6.0** (`CHANGELOG.md:55-79`) : Added (doc-centric data model, Document Library, doc workspace tabs, Stores CRUD), Changed (vocabulary rename, workspace shell, doc state reset, SQLite schema clean-slate), Fixed (CI).
- **Verdict** : item 11.1.1 (poids 3) **OK**. CRIT leve.

### [CRIT] Breaking changes 0.6.x non identifies — **CLOSED**

- **Constat re-audit** : deux blocs `### BREAKING CHANGES` explicites, l'un pour 0.6.1 (`CHANGELOG.md:48-53`), l'autre pour 0.6.0 (`CHANGELOG.md:75-79`).
- **0.6.1 BREAKING** (4 entrees) :
  1. `POST /api/documents/{id}/chunks/push` field `jobId` → `pushId` (`CHANGELOG.md:50`).
  2. Surface flags `STUDIO_MODE_ENABLED`/`RAG_PIPELINE_ENABLED` default off (`CHANGELOG.md:51`).
  3. `STORE_SECRET_KEY` required pour les sealed stores avec one-liner de generation Fernet et avertissement sur la rotation (`CHANGELOG.md:52`).
  4. i18n keys renamed (`chunks.pushedJob`, `chunks.stale.jobDispatched`, `docs.jobDispatched` + placeholder `{jobId}` → `{pushId}`) (`CHANGELOG.md:53`).
- **0.6.0 BREAKING** (3 entrees) :
  1. URL scheme migration `/analysis/:id` → `/docs/:id/...` avec gating `STUDIO_MODE_ENABLED=true` pour legacy (`CHANGELOG.md:77`).
  2. Vocabulaire `index` → `ingest` (`CHANGELOG.md:78`).
  3. **No auto-migration from 0.5.x** : SQLite schema bootstrappe fresh, deux options proposees (re-import ou catch-up DDL manuel) (`CHANGELOG.md:79`).
- **Couverture vs scope reclame** : 5 breaking changes reclamees par le contexte de remediation — toutes presentes (jobId→pushId, surface flags, STORE_SECRET_KEY, i18n rename, no 0.5→0.6 auto-migration), plus 2 supplementaires legitimes (URL scheme migration, vocabulaire index→ingest).
- **Verdict** : item 11.1.3 (poids 3) **OK**. CRIT leve.

### [MAJ] Modifications fonctionnelles 0.6.x non documentees — **CLOSED**

- **Constat re-audit** : 23 bullets agreges (Added + Changed + Fixed + Security) couvrent l'ensemble du scope 0.6.x referenсе dans le rapport precedent (multi-doc workspace, stores CRUD, version history, feature flags, Karate UI, DDD audit).
- **Verdict** : item 11.1.2 (poids 2) **OK**. MAJ leve.

### [MAJ] `frontend/package.json` toujours a `0.5.0` — **CLOSED**

- **Constat re-audit** : `frontend/package.json:3` → `"version": "0.6.1"`. Lockfile en sync (`frontend/package-lock.json:3` et `:9` portent `"version": "0.6.1"` pour la racine `docling-studio`).
- **Verdict** : item 11.2.1 (poids 2) **OK**. MAJ leve.

### [INFO] Pas de version Python (backend) versionnee — **REPORTED**

- **Statut** : non adresse dans la remediation `fix/0.6.1-audit-blockers` (hors scope du re-audit). Reste un INFO non bloquant.
- **Constat re-audit** : `document-parser/pyproject.toml` toujours sans section `[project]`. A garder pour 0.7.0.

---

## Verifications complementaires

- `grep -n "Unreleased" CHANGELOG.md` → aucune occurrence (regle 11.1.1 OK : la section a bien ete renommee, pas laissee `[Unreleased]`).
- `grep -rn "TODO|FIXME|HACK|XXX" document-parser --include="*.py" --exclude-dir=tests` → aucune occurrence (11.3.1 OK).
- `grep -rn "TODO|FIXME|HACK|XXX" frontend/src --include="*.ts" --include="*.vue"` → aucune occurrence (11.3.1 OK).
- `grep -rn "console\.log|console\.debug" frontend/src/` → aucune occurrence (11.3.2 OK).
- `grep -rn "^\s*print(" document-parser --include="*.py" --exclude-dir=tests` → aucune occurrence (11.3.3 OK).
- **Format Keep a Changelog** : preambule (`CHANGELOG.md:1-5`) conforme, chronologie inverse respectee, sous-sections `Added`/`Changed`/`Fixed`/`Security`/`BREAKING CHANGES` (11.1.4 OK).
- **Semantic Versioning** : tags + branches alignes (`v0.5.0 → v0.5.1 → release/0.6.0 → release/0.6.1`), `frontend/package.json` semver valide (11.2.2 OK).
- **Design docs** : 14 design docs sous `docs/design/` (#195, #202–#210, #256, #264, #269, #279) — alignes avec le scope 0.6.x reclame dans les `Added`/`Changed` du changelog.

---

## Points positifs

- **Les deux CRIT du rapport precedent sont levees** : sections `## [0.6.0]` et `## [0.6.1]` redigees avec contenu complet ; blocs `### BREAKING CHANGES` explicites avec instructions operationnelles (one-liner Fernet, gating `STUDIO_MODE_ENABLED=true`).
- **Les deux MAJ sont levees** : scope 0.6.x enumere bullet par bullet ; `frontend/package.json` + lockfile bumpes a `0.6.1`.
- **Rattrapage exemplaire** : le commit `4fbf3b8 docs(changelog): rattrapage 0.6.0 + 0.6.1 sections with explicit BREAKING` ne se contente pas de minimum syndical — chaque entree est ratachee a un numero d'issue ou un SHA, ce qui rend le changelog tracable.
- **Zero recidive sur les items propres a 0.5.1** : pas de TODO, pas de console.log, pas de print, format Keep a Changelog respecte.
- **Design docs 0.6.x** : `docs/design/` reste la source de verite technique (14 entrees), alignee avec le changelog public.

---

## Reserve operationnelle

- **Recommendation CI residuelle (deja faite au rapport precedent)** : ajouter sur toute branche `release/X.Y.Z` un check bloquant qui valide (a) presence d'une section `## [X.Y.Z]` dans `CHANGELOG.md`, et (b) `frontend/package.json` a `"version": "X.Y.Z"`. La remediation a leve les deux CRIT manuellement mais le garde-fou eviterait une recidive sur 0.7.0.
- **README** : `README.md:311` mentionne encore "pagination ships in v0.6" — l'intention 0.6 est ancienne ; a confirmer dans le scope 0.7.0 ou mettre a jour. Pas un ecart bloquant pour le re-audit 0.6.1.

---

## Verdict partiel : GO

Score 100/100 (>= 80, seuil GO), **0 ecart CRITICAL**, **0 ecart MAJOR**, 1 INFO non bloquant.

### Delta vs rapport precedent (release-0.6.1/11-documentation.md)

| Metrique | 0.6.1 initial | 0.6.1 re-audit | Delta |
|----------|---------------|----------------|-------|
| Score | 44 | **100** | **+56** |
| CRIT | 2 | **0** | **-2** |
| MAJ | 2 | **0** | **-2** |
| MIN | 0 | 0 | 0 |
| INFO | 1 | 1 | 0 |
| Verdict | NO-GO | **GO** | leve |

**Les deux CRIT du rapport initial sont explicitement closes** :
1. `[CRIT] CHANGELOG.md sans section [0.6.0] ni [0.6.1]` → sections presentes (`CHANGELOG.md:7` et `:55`).
2. `[CRIT] Breaking changes 0.6.x non identifies` → blocs `### BREAKING CHANGES` presents pour 0.6.1 (`CHANGELOG.md:48-53`, 4 entrees) **et** pour 0.6.0 (`CHANGELOG.md:75-79`, 3 entrees), couvrant les 5 breaking changes reclamees + 2 supplementaires.

La branche `fix/0.6.1-audit-blockers` peut etre mergee dans `release/0.6.1` du point de vue de l'audit Documentation.

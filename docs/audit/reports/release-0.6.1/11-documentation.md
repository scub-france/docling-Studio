# Rapport d'audit : Documentation & Changelog

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code
**Branche** : `release/0.6.1`
**HEAD** : `825e7d7`

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 9 |
| Score | **44 / 100** |
| Ecarts CRITICAL | 2 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

### Detail

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **KO** |
| 11.1.2 | Modifications de la release listees | 2 | **KO** |
| 11.1.3 | Breaking changes identifies | 3 | **KO** |
| 11.1.4 | Format Keep a Changelog | 1 | OK |
| 11.2.1 | `package.json` a la bonne version | 2 | **KO** |
| 11.2.2 | Semantic Versioning | 2 | OK |
| 11.3.1 | Pas de TODO orphelin | 1 | OK |
| 11.3.2 | Pas de `console.log` de debug | 2 | OK |
| 11.3.3 | Pas de `print()` de debug | 2 | OK |

**Calcul** : poids conformes 1 + 2 + 2 + 1 + 2 = 8 / poids total 18 = 44.4 → **44 / 100**.

---

## Ecarts constates

### [CRIT] CHANGELOG.md sans section `[0.6.0]` ni `[0.6.1]`

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : la derniere section est `## [0.5.1] - 2026-04-30`. Aucune entree `## [0.6.0]`, `## [0.6.1]`, ni `[Unreleased]` n'existe. La branche est `release/0.6.1` et la sequence de tags Git va deja jusqu'a `v0.5.1`. Tout le scope 0.6.x — environ 75 commits depuis `v0.5.1` — n'est documente nulle part dans le changelog.
- **Regle violee** : 11.1.1 (poids 3).
- **Impact** : un tag `v0.6.1` cree depuis ce HEAD produirait une release publique mensongere : les utilisateurs (et les outils de release notes scrapant le changelog) ne verraient aucune trace des fonctionnalites livrees entre 0.5.1 et 0.6.1. **Meme defaut bloquant que pour 0.5.0 (CRIT 11.1.1 — NON CORRIGE)** : la regression de process est integrale, l'enseignement de l'audit precedent n'a pas ete capitalise.
- **Remediation** : ajouter deux sections `## [0.6.0] - YYYY-MM-DD` puis `## [0.6.1] - YYYY-MM-DD` (ou une seule section consolidee si 0.6.0 n'a jamais ete tagguee publiquement) listant au minimum :
  - **Added** : routing document-centric (`/docs/:id/...`), workspace shell avec onglets Parse/Chunk/Ingest/Ask, library `/docs` avec filtres + bulk actions, sidebar nav (Home/Docs/Stores/Runs/Settings), breadcrumb workspace, multi-store backend (Neo4j + OpenSearch dispatch per-store), `POST /api/stores` CRUD complet, formulaire de connexion store avec test-connection + chiffrement Fernet des credentials at rest, history des pushes (`GET /api/documents/{id}/chunks/pushes`), snapshots versionnes paired (analysis + chunks) avec timeline, popover de strategie de chunking inline, edition de chunks dans Parse view, dedicated "Generate chunks" button, `STUDIO_MODE_ENABLED` + `RAG_PIPELINE_ENABLED` master flags, ingest workspace view avec stale-count, doc tree rail, headers d'analyse versionnes, Karate UI e2e (`@critical` suite), 14 design docs sous `docs/design/` (cf. issues #195, #202–#210, #225, #240–#245, #251, #256, #257, #263–#269, #279, #283, #285).
  - **Changed** : vocabulaire `index` → `ingest`, navigation refactor, ChunkService extrait, DocumentRouter restructure backend (#269 DDD audit — chaque route reclassifiee).
  - **Fixed** : bbox↔chunk linking apres rechunk (#266), close de la race new-analysis + backfill versions (#267), filter cross-doc bbox leak, store slug→id resolution, chunk_writer MERGE doc node, ingestion availability decouplee d'OpenSearch (#199), nginx upload cap (deja dans 0.5.1 mais a verifier), Vite proxy target en dev/docker, feature-flag load idempotent + async router guard (#257).
- **Tracabilite** : `git log --oneline v0.5.1..HEAD` (75 commits) fournit le materiau brut.

### [CRIT] Breaking changes 0.6.x non identifies

- **Localisation** : `CHANGELOG.md` (section manquante).
- **Constat** : plusieurs changements de la branche `release/0.6.1` ont un impact breaking sur les deploiements existants, **aucun n'est documente** :
  1. **Fernet sealing des credentials store** (`9852d47 feat(#279): seal store connection password at rest, split secret access` + `ef3e520 feat(#279): Fernet box for sealing store credentials at rest`) — les rangees `stores` existantes contenant un mot de passe en clair deviennent inutilisables apres deploiement ; le secret Fernet (`STORE_SECRET_KEY` ou equivalent) devient une variable d'environnement obligatoire.
  2. **Drop de la machinerie de migrations + reecriture clean du `_SCHEMA`** (`db145ca chore(#279): drop migration machinery + rewrite _SCHEMA clean`) — toute base SQLite preexistante n'est plus migree automatiquement ; le contrat « upgrade transparent » des releases 0.5.x est rompu.
  3. **Routes API restructurees** (`#256` chunks under `/api/documents/{id}/chunks/*`, `#251` `/api/stores`, `#283` `/api/documents/{id}/chunks/pushes`, `aa.` schema changes pour `document_store_links`) — les clients externes (s'il y en a) qui consommaient l'ancienne surface se cassent.
  4. **Vocabulaire `index` → `ingest`** (`e40b5ba feat(#225,#224): vocabulary rename index→ingest`) — endpoints, labels, vars d'env potentiellement renommes ; aucun script de migration documente.
  5. **Master feature flags** (`27e3323 feat(#257): surface gating via STUDIO_MODE + RAG_PIPELINE master flags`) — `STUDIO_MODE_ENABLED` n'est pas dans `.env.example` documenté en CHANGELOG ; un deploiement existant sans cette var pourrait perdre des onglets UI (cf. `d4c7034 ci(e2e-ui): opt in STUDIO_MODE_ENABLED for @critical tests`).
- **Regle violee** : 11.1.3 (poids 3) — les breaking changes doivent etre clairement identifies dans le changelog.
- **Impact** : un upgrade 0.5.1 → 0.6.1 sans documentation des breakings peut corrompre des donnees (creds Fernet), casser des integrations API, et silencer des UIs (feature flags). **Critique pour les utilisateurs en self-hosting.**
- **Remediation** : ajouter une sous-section explicite **`### Breaking changes`** ou prefixer chaque entree concernee avec `**Breaking — ...`** comme fait pour 0.5.0 (RAG → REASONING). Inclure les scripts/operations migratoires necessaires (ex. : "set `STORE_SECRET_KEY` before upgrade, then re-create existing store credentials via the UI / Store API").

### [MAJ] Modifications fonctionnelles 0.6.x non documentees

- **Localisation** : `CHANGELOG.md`.
- **Constat** : corollaire direct du CRIT 11.1.1 — aucun bullet n'enumere les nouveautes de 0.6.x (regle 11.1.2, poids 2). Le scope perdu est important (multi-doc workspace, stores CRUD, version history, feature flags, reasoning trace deja existant mais reorganise, Karate UI e2e).
- **Regle violee** : 11.1.2.
- **Remediation** : voir CRIT 11.1.1 (les deux ecarts seront leves par la meme intervention).

### [MAJ] `frontend/package.json` toujours a `0.5.0`

- **Localisation** : `frontend/package.json:3`
- **Constat** : `"version": "0.5.0"`. Pour une release 0.6.1, il faut bumper a `"version": "0.6.1"` (regle 11.2.1, poids 2). **Meme defaut que sur 0.5.0 (MAJ — NON CORRIGE)** : le process de release n'a toujours pas integre le bump.
- **Impact** : version du frontend affichee `0.5.0`, confusion utilisateur (le sidebar affiche la version per `version display in sidebar` de 0.3.0), bundle non traceable a la release 0.6.1, possibles erreurs de support.
- **Remediation** : bumper `frontend/package.json` a `"version": "0.6.1"` avant le tag final. Pour eviter une troisieme recidive, automatiser via script ou hook de release (cf. INFO).

### [INFO] Pas de version Python (backend) versionnee

- **Localisation** : `document-parser/pyproject.toml`
- **Constat** : le `pyproject.toml` backend ne contient qu'une config Ruff (`[tool.ruff]`) — pas de section `[project]` avec `name` / `version`. Le backend n'a donc pas de version applicative versionnee en parallele du frontend.
- **Regle violee** : aucune regle explicite de la fiche 11, donc INFO et non MAJ. Mais la coherence semver entre front + back serait souhaitable, et c'est ce que faisait deja `0.3.0` (cf. `version display in sidebar, settings page, and health endpoint`).
- **Remediation** : envisager d'ajouter `[project]\nname = "docling-studio-backend"\nversion = "0.6.1"\nrequires-python = ">=3.12"` dans `document-parser/pyproject.toml` et de derouler le bump dans le script de release. Le `/api/health` peut alors exposer la version backend par introspection.

---

## Points positifs

- **Zero TODO/FIXME/HACK/XXX** dans `document-parser/` (hors tests). Constat etabli sur 0.5.0, **maintenu sur 0.6.1**.
- **Zero `console.log`/`console.debug`** dans `frontend/src/`. Les 31 occurrences de `console.error`/`console.warn` sont toutes des reports d'erreur legitimes dans les stores Pinia (`features/*/store.ts:53`, `features/analysis/ui/GraphView.vue:205`, etc.), pas du debug oublie.
- **Zero `print()` de debug** dans le backend (hors tests).
- **Format Keep a Changelog correctement respecte** sur les sections existantes (`CHANGELOG.md:1-5` — preambule conforme, chronologie inverse, sous-sections `Added`/`Changed`/`Fixed`).
- **Semantic Versioning suivi** dans le naming des tags et branches : `v0.5.0 → v0.5.1 → release/0.6.0 → release/0.6.1` (`git tag --sort=-v:refname`).
- **Section `[0.5.0]` ajoutee correctement** apres le NO-GO de l'audit precedent (`CHANGELOG.md:13-52`). La leçon a ete capitalisee pour 0.5.0/0.5.1 mais **pas reproduite pour 0.6.x** (recidive).
- **Design docs `docs/design/`** : 14 design docs presents pour les issues 0.6.x principales (`195`, `202`–`210`, `256`, `264`, `269`, `279`) — la doc de conception est saine, c'est uniquement le changelog public et le bump de version qui manquent.
- **README** : a jour pour les fonctionnalites Neo4j / reasoning, et mentionne explicitement le palier "pagination ships in v0.6" (`README.md:311`) — il y a une intention 0.6 documentee, juste pas finalisee cote CHANGELOG.

---

## Verdict partiel : NO-GO

Score 44/100 < 60 (seuil minimum) et **2 ecarts CRITICAL non resolus** (regle absolue du master : tout `[CRIT]` non resolu = NO-GO).

**Comparaison vs 0.5.0** :

| Metrique | 0.5.0 | 0.6.1 | Delta |
|----------|-------|-------|-------|
| Score | 44 | 44 | 0 |
| CRIT | 1 | 2 | +1 |
| MAJ | 2 | 2 | 0 |
| MIN | 0 | 0 | 0 |
| INFO | 0 | 1 | +1 |
| Verdict | NO-GO | **NO-GO** | identique |

**La situation s'aggrave** : non seulement les deux defauts critiques de 0.5.0 ne sont pas corriges en mode preventif sur 0.6.1 (CHANGELOG manquant + frontend `package.json` non bumpe), mais un nouveau CRIT s'ajoute (breaking changes 0.6.x non identifies) parce que le scope 0.6.x est beaucoup plus large que 0.5.0 et contient au moins 5 changes a impact breaking. C'est une **regression de process** : l'enseignement de l'audit precedent n'a pas ete institutionnalise.

Le release 0.6.1 ne peut pas partir (ne peut pas etre taguee) tant que :

1. **CHANGELOG.md** n'enumere pas les changements sous `## [0.6.0] - YYYY-MM-DD` et `## [0.6.1] - YYYY-MM-DD` (ou une section unique consolidee).
2. **CHANGELOG.md** ne documente pas les **breaking changes** 0.6.x (Fernet sealing, drop migrations, routes API restructurees, vocabulaire `index → ingest`, master feature flags) avec instructions de migration.
3. **frontend/package.json** n'est pas bumpe a `"version": "0.6.1"`.

**Recommendation operationnelle** : ajouter un check CI bloquant qui verifie, sur toute branche `release/X.Y.Z`, que (a) `CHANGELOG.md` contient une section `## [X.Y.Z]`, et (b) `frontend/package.json` a `"version": "X.Y.Z"`. Ce check transformerait la regression en garde-fou et eviterait une troisieme recidive sur 0.7.0.

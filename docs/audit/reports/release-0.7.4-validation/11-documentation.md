# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `efc0bc5`. Arbre de travail lu tel quel.
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/11-documentation.md`, `a12b744`, 72/100, 1 CRIT, 1 MAJ, 12 INFO).
**Contexte** : le commit de freeze n'est toujours pas fait (`docs/maintainers.md:22-24`). `[Unreleased]` et la version `0.7.3` du frontend restent attendus ; deux scores, comme la baseline.

Commits relus : `git log b5f8c7f..efc0bc5` (15 commits). Pages touchées : `CHANGELOG.md`, `SECURITY.md`, `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml`, `docs/analysis-editor.md`, `docs/configuration.md`, `docs/maintainers.md`, `docs/mcp-server.md`, `docs/user-guide.md`, `e2e/CONVENTIONS.md`, `e2e/ui/README.md`. Chaque affirmation de ces sections, et chaque affirmation ailleurs que ces commits ont pu rendre fausse, a été vérifiée contre le code à `efc0bc5`. Rien n'a été exécuté hors deux scripts de lecture (liens, identifiants).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 9 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 18 |

Pondération : poids total 18. Non conformes : 11.1.1 (3), 11.2.1 (2), 11.1.4 (1) = 6. `12 / 18 * 100 = 66,7` -> **67**.

### Score au freeze

| Scénario | Écarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Aujourd'hui (pré-freeze) | 11.1.1 CRIT, 11.2.1 MAJ, 11.1.4 MIN | 67 | NO-GO (CRIT) |
| Après le commit de freeze seul | 11.1.4 MIN | 94 | GO |
| Après le freeze, `### Deprecated` remonté avant `### Fixed` | aucun | 100 | GO |

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 11.1.1 | `[Unreleased]` renommée en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pré-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listées | 2 | Oui | Les changements de cette passe sont annoncés : Ask/MCP sur l'analyse active `:22`, `currentAnalysisId` `:23`, atomicité `:24`, schémas et bornes `:27`, résumés par document `:28`, `MAX_IMPORT_SIZE_MB` `:29`, `LLM_PROVIDER_TYPE` `:48`, `API_ALLOWED_HOSTS` `:52`, couleurs `:26`. Manques mineurs (INFO V8) |
| 11.1.3 | Breaking changes identifiés | 3 | Oui | Aucune suppression de route ni de champ. Les changements de comportement (Ask/MCP, `stale_version`, 422 des bornes) sont décrits sous `Changed` |
| 11.1.4 | Format Keep a Changelog | 1 | **Non** | `CHANGELOG.md:9` Added, `:15` Changed, `:33` Fixed, `:46` Deprecated, `:50` Security : `Deprecated` arrive après `Fixed`. Ordre Keep a Changelog : Added, Changed, Deprecated, Removed, Fixed, Security. Une section de chaque, c'est bon |
| 11.2.1 | `frontend/package.json` en X.Y.Z | 2 | **Non** (pré-freeze) | `frontend/package.json:3`, `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version SemVer | 2 | Oui | `0.7.3 -> 0.7.4` (INFO 6) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | Oui | 0 `TODO|FIXME|HACK|XXX` dans `document-parser` (hors `.venv`) et `frontend/src` |
| 11.3.2 | Pas de `console.log` de debug | 2 | Oui | 0 `console.log`/`console.debug` ; 2 `console.warn` en `catch` : `frontend/src/features/analysis/store.ts:118`, `:177` |
| 11.3.3 | Pas de `print()` de debug | 2 | Oui | 0 `print(` en début de ligne hors `tests/` |

---

## Ecarts constates

### [CRIT] `[Unreleased]` non figée (attendu pré-freeze)

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : inchangé. Normal tant que le freeze n'est pas fait.
- **Regle violee** : 11.1.1 (poids 3).
- **Remediation** : commit `chore(release): freeze [0.7.4]`, après les retouches de texte ci-dessous.

### [MAJ] `frontend/package.json` encore en 0.7.3 (attendu pré-freeze)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Constat** : inchangé.
- **Regle violee** : 11.2.1 (poids 2).
- **Remediation** : `0.7.4` dans les deux fichiers, dans le commit de freeze.

### [MIN] Sections du changelog hors de l'ordre Keep a Changelog

- **Localisation** : `CHANGELOG.md:33` (`### Fixed`), `:46` (`### Deprecated`), `:50` (`### Security`)
- **Constat** : `efc0bc5` a ajouté `### Deprecated` et `### Security` à la fin, après `### Fixed`. Keep a Changelog range `Deprecated` avant `Fixed`. Nouveau depuis le contrôle.
- **Regle violee** : 11.1.4 (poids 1).
- **Remediation** : déplacer le bloc `### Deprecated` (`:46-48`) entre `### Changed` et `### Fixed`. Supprimer au passage la ligne vide en double avant `## [0.7.3]` (`:53-54`).

### [INFO] V1. `docs/user-guide.md:104` : « l'analyse active » mal située et incomplète

- **Localisation** : `docs/user-guide.md:104`, `:116-121`
- **Constat** : la phrase est vraie sur le fond (Ask lit l'analyse active, sans les éditions : `services/reasoning_service.py:103-105`, `services/current_analysis.py:70-78`), mais :
  - « **History** » : la page ne décrit que l'History de l'éditeur (`:84`, Revert/Reapply), qui ne change pas l'analyse active. Le **Restore** qui la change est dans l'History du document (`frontend/src/features/document/ui/HistoryDrawer.vue:64`), absent du guide. D'où la lecture inverse relevée par l'autre audit.
  - « the newest one » : c'est la dernière analyse *terminée*, import compris (`services/analysis_service.py:514`, `persistence/analysis_repo.py:177-191`), pas la plus récente lancée.
  - Cas sans analyse courante absent : analyse active supprimée (`persistence/database.py:90`, `ON DELETE SET NULL`, `services/analysis_service.py:220-226` ne resélectionne rien), version restaurée sans analyse (`domain/models.py:158-161`), analyse active sans document Docling (`services/reasoning_service.py:104`). Ask répond alors 404. La section **Delete** (`:116-121`) ne le dit pas non plus.
  - Ask s'ouvre dans la page d'une analyse (`:94`) mais n'envoie pas son id (`document-parser/api/reasoning.py:29-34`) : sur une analyse ouverte qui n'est pas l'active, la réponse vient d'une autre analyse que celle affichée.
- **Remediation** : voir « Vérification des affirmations », texte prêt à coller.

### [INFO] V2. `docs/mcp-server.md:154` : `null` ne veut plus dire « pas encore analysé », et la page ne dit pas ce que MCP lit

- **Localisation** : `docs/mcp-server.md:154`, `:150-160`
- **Constat** : `find_documents` renvoie `version_id = find_current_parse_ids` (`services/navigation_service.py:88-95`, `services/current_analysis.py:58-68`) : `null` aussi quand l'analyse active a été supprimée, quand une version restaurée n'a pas d'analyse, ou quand l'analyse active n'a pas de document Docling. Le message de `services/parse_loader.py:101-104` (« no parsed content to navigate yet. Run an analysis ») a le même biais. Nulle part la page ne dit que les outils sans `version_id` lisent l'analyse active, ni qu'ils lisent le texte d'origine, sans les éditions (`services/parse_loader.py:3-6`).
- **Remediation** : voir plus bas.

### [INFO] V3. `docs/mcp-server.md:216` : `stale_version`, cas sans analyse courante

- **Localisation** : `docs/mcp-server.md:216` ; `services/citation_service.py:138-150`, `:196-199`
- **Constat** : vrai dans le cas courant, et vrai aussi pour une ancre plus récente que l'analyse restaurée. Mais si le document n'a plus d'analyse courante, `_find_superseding_parse` renvoie `None` et la citation est `verified`, alors que la parse épinglée n'est plus la courante.
- **Remediation** : voir plus bas.

### [INFO] V4. `API_ALLOWED_HOSTS` : `name:port` ne passe jamais derrière le nginx fourni

- **Localisation** : `docs/configuration.md:142`, `:144` ; `CHANGELOG.md:52` ; `SECURITY.md:58` ; `.env.example:44-49`
- **Constat** : `nginx.conf.template:38` et `frontend/nginx.conf.template:38` transmettent `Host $host`, sans port. `is_allowed_host` (`document-parser/infra/host_guard.py:54-68`) compare alors `studio.lan` à `studio.lan:3000` : refus 421. Seuls `name:*` et `name` nu passent. La page le laisse déduire (« which is what the bundled nginx forwards ») mais présente `name:port` comme une option valable. Le reste est exact : opt-in (`main.py:117-119`), `*` coupe la vérification (`host_guard.py:71-74`), loopback toujours accepté (`:33`, `:60-61`), 421 `Invalid Host header` en texte brut (`:34-35`, `:112`), seul `/api/` est vérifié (`:104`), ligne de log au démarrage (`:77-87`, `main.py:119`). Aucune entrée 421 dans `docs/troubleshooting.md`.
- **Remediation** : voir plus bas ; ajouter une entrée « 421 Invalid Host header » au dépannage.

### [INFO] V5. `NGINX_MAX_BODY_SIZE` « au-dessus » de `MAX_IMPORT_SIZE_MB`, alors que les deux valent 200

- **Localisation** : `docs/configuration.md:32` ; `.env.example:39-42`
- **Constat** : `200M` côté nginx (`Dockerfile:61`, `frontend/Dockerfile:14`, `docker-compose.yml:213`) = 200 Mio ; `MAX_IMPORT_SIZE_MB=200` = 200 Mio (`main.py:95-101`). Même seuil : au-delà, nginx répond 413 (sa page HTML) avant le backend, et le message `Docling JSON too large (max 200 MB)` n'est jamais vu derrière nginx avec les défauts. `.env.example` dit « >= », la page dit « above » : la page contredit les défauts.
- **Remediation** : voir plus bas.

### [INFO] V6. `docs/analysis-editor.md:78-84` : le `422` des bornes manque

- **Localisation** : `docs/analysis-editor.md:78-84` ; `document-parser/api/schemas.py:153-219`
- **Constat** : `efc0bc5` borne les requêtes de l'éditeur (id et séparateur 1 000 caractères, texte 1 000 000, 100 000 ids, 10 000 commandes) ; au-delà, FastAPI répond 422. Le CHANGELOG le dit (`:27`), la page API de l'éditeur non.
- **Remediation** : ajouter la ligne `422` (texte plus bas).

### [INFO] V7. CHANGELOG : entrées contradictoires

- **Localisation** : `CHANGELOG.md:19`, `:21`, `:22`
- **Constat** : `:19` « document reads always apply its saved edits » contredit `:22` « Both still read the original result » (Ask et MCP sont des lectures du document). `:21` « instead of the latest completed conversion » laisse croire que l'export change toujours d'analyse, alors que l'active est par défaut la dernière terminée ; la différence n'existe qu'après un Restore ou avec des éditions.
- **Remediation** : textes de remplacement dans la section CHANGELOG.

### [INFO] V8. CHANGELOG : changements visibles absents

- **Localisation** : `CHANGELOG.md:15-31`
- **Constat** : cinq changements de cette passe, visibles d'un client ou d'un opérateur, n'ont pas de puce : erreurs 500 de `/preview` et `/pages` ; `currentAnalysisId: null` sur la liste et l'upload ; nouveau `detail` de `stale_version` ; repli sur la dernière analyse analysée pour un document sans ligne d'état ; `find_documents` renvoie la version de l'analyse active. Tous sont des cas limites ou des détails de contrat ; 11.1.2 reste conforme.
- **Remediation** : textes dans la section CHANGELOG.

### [INFO] V9. `docs/mcp-server.md:329` : « The same guard exists for `/api` »

- **Localisation** : `docs/mcp-server.md:329-330`
- **Constat** : pas le même. Le garde MCP vérifie `Host` et `Origin` (`:325-326`) ; celui de `/api` ne vérifie que `Host`, accepte toujours le loopback, et son `name:*` accepte le nom sans port (`infra/host_guard.py:7-12`, `:54-68`).
- **Remediation** : « A similar `Host` check exists for `/api` (no `Origin` check, loopback always accepted), off unless `API_ALLOWED_HOSTS` is set (see [Configuration](configuration.md#host-check-on-the-api)). »

### [INFO] V10. Portée de la CI : trois phrases en retard (hors site publié)

- **Localisation** : `CONTRIBUTING.md:97` ; `e2e/api/README.md:54` ; `e2e/CONVENTIONS.md:167`
- **Constat** :
  - `CONTRIBUTING.md:97` « tests on every pull request » : vrai pour les tests sans Docling. Les tests qui ont besoin de Docling (`backend-docling`, ajouté par `23e4c81`) ne tournent que sur les pushs et les PR vers `main` (`.github/workflows/ci.yml:62-64`).
  - `e2e/api/README.md:54` et `e2e/CONVENTIONS.md:167` : un push sur `release/*` lance aussi `@smoke,@regression,@e2e` (`ci.yml:4-5`, `:189-192`). Antérieur à cette passe (le `on:` n'a pas bougé), mais `23e4c81` a corrigé la ligne `@critical` voisine sans celle-ci.
  - Exact : `docs/maintainers.md:53-67` (job `audit-checks` retiré `release-gate.yml:192-195`, groupes `local` et `reasoning` audités `:126-130`, image `local` avec raisonnement sans modèles `:199-240`, en-têtes nginx du smoke test, Trivy sur les deux images, verdict `GO CONDITIONAL` sur le seul audit de dépendances, `pipefail` présent `:84`, `:93`) ; `e2e/ui/README.md:102` et `e2e/CONVENTIONS.md:170` (`ci.yml:215`, `:281`, `release-gate.yml:712`, `UIRunner.java:12-15`, premier scénario `@critical` de `analysis-editor.feature:13-14`).
- **Remediation** : `CONTRIBUTING.md:97` : « The CI runs the lint, type-check and tests on every pull request. The tests that need Docling itself run on pull requests to `main` and on every push to `main` or a `release/*` branch. The format checks are yours to run. » ; `e2e/api/README.md:54` : « `ci.yml` runs `@smoke` on every pull request to `main` and on every push to `main`. Pull requests to a `release/*` branch, and pushes to one, run `@smoke,@regression,@e2e` instead. » ; `e2e/CONVENTIONS.md:167`, colonne CI : « API: `ci.yml` on pull requests to and pushes on `release/*`, and `release-gate.yml`. UI: no CI job. »

### [INFO] N4. Règles de couches : interdiction du système de fichiers absente (réduite)

- **Localisation** : `docs/architecture.md:73` ; `document-parser/tests/test_architecture.py:15`, `:237-282`
- **Constat** : la ligne `services` cite maintenant les bibliothèques interdites (`_SERVICES_FORBIDDEN_EXTERNALS`, `:186-197`), et la docstring périmée du test est corrigée. Depuis `ac7ac17`, le test interdit aussi `os`, `shutil`, `glob`, `tempfile`, `pathlib.Path` et `open()` dans `services/` ; la page ne le dit pas. Incomplet, pas faux. Aucun module déplacé par `d3059c6`/`8a60cee` (`ChunkPushService`, `DocumentTreeService`, `domain/heading_tree.py`) n'est cité dans la doc publiée ; `services/reasoning_service.py`, `infra/docling_agent_reasoning.py`, `domain/trace_builder.py` (`:124`) existent.
- **Remediation** : `:73` : « `api`, `infra`, `persistence`, FastAPI, the Docling, PDF, HTTP, graph, search and cryptography libraries, and the filesystem (`os`, `shutil`, `pathlib.Path`, `open()`): services reach them through ports ».

### [INFO] 1. `### Fixed` ne corrige aucun défaut publié (inchangée, laissée au freeze)

- **Localisation** : `CHANGELOG.md:33-44`
- **Remediation** : comme la baseline : fondre #392-#396 dans `:11`, passer #391 et #398 sous `### Changed`, supprimer `### Fixed`.

### [INFO] 2. #398 encore à part de #401 (inchangée)

- **Localisation** : `CHANGELOG.md:17`, `:40`
- **Remediation** : fondre `:40` dans `:17` (« (#398, #401) »).

### [INFO] 3. Puces redondantes autour de l'éditeur, `analysisEditorEnabled` non cité (inchangée)

- **Localisation** : `CHANGELOG.md:12-13`, `:19-20`, `:41-44` ; `document-parser/main.py` (`analysisEditorEnabled` de `/api/health`)

### [INFO] 4. Design doc du rendu PDF sans `Status` (inchangée)

- **Localisation** : `docs/design/pdf-loading-performance.md:1-5`

### [INFO] 5. Fichiers de travail suivis à la racine (inchangée)

- **Localisation** : `analysis_editor_path_to_alpha.md`, `orca.yaml` ; `docs/design/analysis-editor.md:1-3` sans `Status`

### [INFO] 6. SemVer : un patch qui livre une fonctionnalité, une API et une migration (inchangée)

- **Localisation** : `CHANGELOG.md:7-52` ; règle absente de `docs/maintainers.md`

### [INFO] 7. Versions secondaires (inchangée)

- **Localisation** : `document-parser/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10` (`0.3.1`)

---

## Vérification des affirmations

V = vrai, F = faux, I = imprécis, N = invérifiable ici.

### Ce que lisent Ask, MCP, l'éditeur et l'export

Règle du code : `domain/models.py:193-209` (ligne d'état présente : son `active_analysis_id`, éventuellement NULL ; pas de ligne : dernière analyse terminée avec document Docling), alimentée par `services/current_analysis.py:35-56`. Une analyse qui se termine devient active (`persistence/analysis_repo.py:177-191`, appelé par `services/analysis_service.py:514`, import compris `:193`). Ask : analyse courante telle que stockée (`services/reasoning_service.py:103-105`). MCP : parse courante ou épinglée, texte d'origine (`services/parse_loader.py:79-107`). Éditeur et export par défaut : analyse courante avec éditions (`services/analysis_edit_service.py:100-106`, `:265-282` ; `services/export_service.py:125-153`).

| Fichier:ligne | Affirmation | Verdict | Code | Texte corrigé |
|---------------|-------------|---------|------|---------------|
| `docs/user-guide.md:104` | Ask lit l'analyse active, « the newest one, until you restore another from **History** » ; sans les éditions | I | voir ci-dessus ; `HistoryDrawer.vue:64` ; `database.py:90` | « Ask reads the document's active analysis, which is not always the one on screen: the analysis that completed last, or the one you restored from the document's **History** (open the document from **Docs**). Opening an older analysis from **Analyses** does not change it, and Ask still answers from the active one. If the active analysis was deleted, or has no Docling document, Ask has nothing to read until a new analysis completes or you restore a version. Ask reads that analysis as Docling produced it, without the changes saved in **Edit analysis**. » |
| `docs/user-guide.md:119` | Supprimer une analyse | I (incomplet) | `database.py:90` ; `analysis_service.py:220-226` | ajouter après `:119` : « Deleting the document's active analysis leaves the document without one: Ask, the MCP tools, the default download and the document tree have nothing to read until a new analysis completes or you restore a version from the document's **History**. » |
| `docs/analysis-editor.md:41` | Ask et MCP lisent l'analyse active (ou celle qu'une ancre épingle), résultat d'origine | V | `reasoning_service.py:103`, `parse_loader.py:94-104` | — (optionnel : « …the active one, when it has a Docling document… ») |
| `docs/analysis-editor.md:65` | Sans `analysisId`, l'analyse active | V | `analysis_edit_service.py:270-273` | — |
| `docs/analysis-editor.md:82` | `404` : éditeur coupé, document absent, analyse d'un autre document, pas d'analyse active ; export `edited=true` sans `analysisId` ou sans document Docling | V | `api/errors.py:18`, `analysis_edit_service.py:258-282` ; `export_service.py:147-153`, `:159-160` | — (N2 de la baseline résolue) |
| `docs/analysis-editor.md:83` | `409` : sauvegarde concurrente, ou sur une route d'éditeur analyse non terminée / sans document Docling | V | `api/errors.py:19-20` ; `analysis_edit_service.py:276-280` | — |
| `docs/analysis-editor.md:78-84` | Tableau des erreurs | I (incomplet) | `api/schemas.py:153-219` | ajouter : « `422` \| A request over the editor's bounds: an id or a separator over 1,000 characters, a text over 1,000,000 characters, more than 100,000 ids or more than 10,000 commands; or a malformed body. » |
| `docs/mcp-server.md:154` | `find_documents` : « `null` means not parsed yet » | F | `navigation_service.py:88-95` ; `current_analysis.py:58-68` | « `document_id` and the `version_id` the tools read by default: the document's active analysis. `null` when there is none with a Docling document: never analysed, active analysis deleted, or restored to a version without one. » |
| `docs/mcp-server.md` (après `:160`) | Ce que lisent les outils | I (absent) | `parse_loader.py:3-6`, `:79-107` | ajouter : « Without `version_id`, a tool reads the document's active analysis, the one Studio's workspace opens, until another analysis completes or one is restored from History. Every tool reads the parse as Docling produced it: changes saved in the [analysis editor](analysis-editor.md) are not visible to MCP. » |
| `docs/mcp-server.md:216` | `stale_version` : l'ancre épingle une parse qui n'est plus la courante | I (cas limite) | `citation_service.py:138-150`, `:196-199` | « The quote is there, but the anchor pins a parse other than the document's current one (an older one, or a newer one after a restore from History). A document with no current parse answers `verified`. » |
| `docs/mcp-server.md:329` | « The same guard exists for `/api` » | I | `infra/host_guard.py:7-12`, `:54-68` | voir INFO V9 |
| `CHANGELOG.md:22` | Ask/MCP lisent l'active ; après Restore, `stale_version` pour l'ancre plus récente ; pas d'analyse courante si l'active est supprimée ou sans document Docling ; texte d'origine | V | voir ci-dessus | — (compléments en section CHANGELOG) |
| `CHANGELOG.md:23` | `GET /api/documents/{id}` renvoie `currentAnalysisId`, le workspace ouvre cette analyse | V | `api/documents.py:93-105` ; `frontend/src/features/document/store.ts:170-172`, `:203-206` | compléter (V8) |
| `CHANGELOG.md:24` | Restore et rechunk atomiques | V | `persistence/chunk_repo.py:147` ; `services/version_service.py:150-154` | — |
| `docs/getting-started.md:135` | Migration : active = dernière terminée, en préférant celle qui a un document Docling | V | `persistence/database.py:296-310` (inchangé depuis `b5f8c7f`) | — |

### Réglages de cette passe

| Fichier:ligne | Affirmation | Verdict | Code | Texte corrigé |
|---------------|-------------|---------|------|---------------|
| `docs/configuration.md:31` | `MAX_IMPORT_SIZE_MB` `200`, `POST /api/analyses/import`, `413`, `0` = pas de limite | V | `infra/settings.py:31`, `:230`, `:154-155` ; `main.py:95-101` ; `infra/body_limit.py:35-67` | — |
| `docs/configuration.md:32` | `NGINX_MAX_BODY_SIZE` « Keep it above `MAX_FILE_SIZE_MB` and `MAX_IMPORT_SIZE_MB` » | I | `Dockerfile:61` ; `nginx.conf.template:42` ; `main.py:99` | « Body limit in nginx for every `/api` request, in nginx format. Over it, nginx answers `413` itself, before the backend. Keep it at least as large as `MAX_FILE_SIZE_MB` and `MAX_IMPORT_SIZE_MB`. With the defaults it equals `MAX_IMPORT_SIZE_MB`, so an import over 200 MB gets nginx's `413` page rather than the backend's message; raise both together. » |
| `.env.example:39-40` | « Must be >= … » | V | idem | — |
| `docs/configuration.md:49` ; `.env.example:101-103` | `LLM_PROVIDER_TYPE` déprécié, autre valeur = Ask coupé + avertissement, lecture seule dans le panneau | V | `infra/settings.py:54-58`, `:245` ; `bootstrap/factories.py:90-108` ; `bootstrap/builder.py:274` | — |
| `docs/configuration.md:127`, `:134-136` | `API_ALLOWED_HOSTS` vide par défaut = pas de vérification ; 421 `Invalid Host header` | V | `infra/settings.py:111`, `:283-286` ; `main.py:117-119` ; `host_guard.py:34-35`, `:112` | — |
| `docs/configuration.md:142` | `name:port`, `name:*`, `*` ; `name:*` accepte le nom sans port | I | `host_guard.py:54-74` ; `nginx.conf.template:38` | « The values are written like `MCP_ALLOWED_HOSTS`: `name:port` for one port, `name:*` for any port, `*` for no check. Behind the bundled nginx, write `name:*` (or the bare `name`): nginx forwards `Host` without the port (`Host $host`), so a `name:port` entry never matches there. » |
| `docs/configuration.md:143` | Loopback toujours accepté, `curl http://localhost:8000/api/health` passe | V | `host_guard.py:33`, `:60-61` | — |
| `docs/configuration.md:144` | Nom LAN : `localhost:*,studio.lan:*` ; derrière un proxy, le nom qu'il transmet | V | idem | — |
| `docs/configuration.md:145-146` | Seul `/api/*` ; log au démarrage | V | `host_guard.py:104` ; `:77-87` ; `main.py:119` | — |
| `SECURITY.md:52-59` | DNS rebinding ; `/mcp` vérifié par défaut ; `/api` seulement si réglé ; pas un contrôle d'accès | V | `infra/settings.py:104-111`, `:179-180` ; `host_guard.py` | optionnel, `:58` : ajouter « Behind the bundled nginx, list names as `name:*`. » |
| `CHANGELOG.md:52` | 421, loopback, opt-in, valeur conseillée | V | idem | ajouter « Behind the bundled nginx, list other names as `name:*`: nginx drops the port. » |
| compose | `MAX_IMPORT_SIZE_MB` `200`, `API_ALLOWED_HOSTS` vide, mêmes noms que le code | V | `docker-compose.yml:174-176`, `docker-compose.dev.yml:146-148` | — |
| `docs/configuration.md` (variables) | Toutes les variables lues par le backend sont documentées | V | script : chaque variable de `infra/settings.py`, `persistence/database.py:22`, `:342`, `infra/secrets/fernet_box.py:126` est citée dans `docs/configuration.md` ou `docs/mcp-server.md` | — |

### Bornes, schémas, routes, statuts

| Fichier:ligne | Affirmation | Verdict | Code |
|---------------|-------------|---------|------|
| `CHANGELOG.md:27` | Bornes 1 000 / 1 000 000 / 100 000 / 10 000, 422 | V | `api/schemas.py:153-219` |
| `CHANGELOG.md:27` | « The JSON returned is unchanged » | N | `api/schemas.py:222` et suivantes, `extra="forbid"` ; exige d'exécuter l'API |
| `CHANGELOG.md:28` | `GET /api/analyses/summaries?documentId=` renvoie toutes les analyses du document ; la suppression compte sur ces lignes | V | `api/analyses.py:107-138` ; `frontend/src/pages/DocsLibraryPage.vue:345` |
| `CHANGELOG.md:29` | `MAX_IMPORT_SIZE_MB`, 413 | V | voir plus haut |
| `docs/architecture.md:88-95` | Préfixes et routes | V | `api/documents.py:52-180`, `api/analyses.py:47-220`, `api/analysis_edits.py:111-200`, `api/document_chunks.py`, `api/reasoning.py:29` |
| `docs/architecture.md:66-77` | Test des couches, une exception, tableau | V (ligne `services` incomplète, N4) | `tests/test_architecture.py:55-68`, `:186-197`, `:237-282` |
| `docs/configuration.md:158` | `page` au-delà de la fin : `400`, `404` si nombre de pages inconnu | V | `services/preview_service.py:83-86`, `:109-118` (N3 de la baseline résolue) |
| (aucune page) | Erreurs de `/preview` et `/pages` : `404` fichier absent, `422` PDF illisible, `500` pour tout le reste depuis `ac7ac17` | — | `services/preview_service.py:121-138` ; avant : `422` pour toute exception (`b5f8c7f:api/documents.py`) | non documenté ; voir CHANGELOG |
| `docs/maintainers.md:53-67` | Contenu de la gate | V | voir INFO V10 |
| `e2e/ui/README.md:102`, `e2e/CONVENTIONS.md:170`, `:176` | `@critical` sur push `main`/`release/*` et PR vers `main`, via `UIRunner#testCritical` | V | `ci.yml:215`, `:281-284` ; `release-gate.yml:712-715` |

### Liens, nav, identifiants

- **Liens** (script, `docs/**/*.md` hors `audit/reports`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, `e2e/CONVENTIONS.md`, `e2e/ui/README.md`, `e2e/api/README.md`) : 119 liens relatifs, 0 cassé dans les pages publiées ou modifiées. Ancres nouvelles résolues : `configuration.md#host-check-on-the-api` (depuis `SECURITY.md:58`, `docs/mcp-server.md:330`, `docs/configuration.md:127`). Seule ancre cassée, antérieure et non publiée : `docs/design/329-mcp-investigation-journal-navigation-tree.md:592` -> `../mcp-server.md#investigations`.
- **Nav `mkdocs.yml:34-46`** : inchangée, toutes les pages existent. `mkdocs build --strict` non exécuté (consigne machine).
- **Identifiants** (script, 128 identifiants entre backticks dans les pages de la nav, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`) : aucun nom périmé après les déplacements de `d3059c6`/`8a60cee`/`ac7ac17`. Absents du code, normalement : `chunk_edits` (la page dit qu'elle n'est plus utilisée), `docker-compose.override.yml`, `extra_hosts`, et les exemples de branche. `profiles/fastapi-vue/commands.sh` n'est plus cité (N5 résolue).
- **TODO/FIXME** : 0 dans le code (11.3.1).

---

## CHANGELOG

### Entrées fausses à `efc0bc5`

Aucune entrée n'est fausse au sens strict. `:19` contredit `:22` (ci-dessous).

### Entrées contradictoires, texte proposé

- **`:19`** (remplace la puce) : « **Analysis editor active result**: each document has one active analysis: the last one that completed, or the one restored from History. The document workspace, the tree, the default export and rechunking read it with its saved edits; Ask and the MCP tools read its original result. A shared document-analysis state row records which analysis and result hash produced the current chunks, so stale chunks are identified accurately without false warnings after equivalent edits. »
- **`:21`** (remplace la puce) : « **Default Markdown and JSON export**: without `analysisId`, the export returns the document's active analysis with its saved edits. It used to return the latest completed analysis without edits; the two differ after a restore from History or once edits are saved. An active analysis without a Docling document answers 404. »
- **`:22`** (compléter la fin) : « … Both still read the original result, without editor changes. `find_documents` returns that analysis as `version_id`, `null` when the document has none. The `stale_version` detail now reads "the anchor pins a parse that is no longer current: <id> is" instead of "the anchor pins an earlier parse". »
- **Éditeur `:11-13`, `:19-20`, `:41-44`** : plus de contradiction de fond depuis `732d4c6` (le 404 de `:44` est vrai : `api/errors.py:18`). Reste la redondance (INFO 3), à traiter au freeze.

### Entrées manquantes, texte proposé (sous `### Changed`)

- **Erreurs de rendu de page** : « **Page preview errors**: `GET /api/documents/{id}/preview` and `/pages` answer `500` for a failure that is not reading the PDF (database, cache), instead of `422`. A PDF that cannot be read or rendered still answers `422`, a missing file `404`. »
- **`currentAnalysisId` sur la liste et l'upload** (compléter `:23`) : « The list (`GET /api/documents`) and upload responses carry the field too, always `null`: read it from `GET /api/documents/{id}`. »
- **Repli sans ligne d'état** (compléter `:19` ou `:22`) : « A document with no state row, such as one in a database the 0.7.3 upgrade did not reach, falls back to its latest completed analysis with a Docling document, for the editor, the active result, exports, Ask and MCP alike; saving edits on that analysis also refreshes the graph. »
- **`stale_version`** : voir le complément de `:22`.

### Ordre des sections

Déplacer `### Deprecated` (`:46-48`) entre `### Changed` et `### Fixed` (MIN 11.1.4).

---

## Delta vs contrôle

| Item | Contrôle (`a12b744`) | Validation (`efc0bc5`) | Évolution |
|------|----------------------|------------------------|-----------|
| 11.1.1 | CRIT | CRIT | = (pré-freeze) |
| 11.1.2 | OK | OK | = ; N1 résolue (`:26`), cinq manques mineurs (V8) |
| 11.1.3 | OK | OK | = |
| 11.1.4 | OK | **MIN** | **pire** : `Deprecated` ajouté après `Fixed` |
| 11.2.1 | MAJ | MAJ | = (pré-freeze) |
| 11.2.2 | OK | OK | = |
| 11.3.1 | OK | OK | = |
| 11.3.2 | OK | OK | = |
| 11.3.3 | OK | OK | = |
| **Score** | **72** (100 au freeze) | **67** (94 au freeze, 100 si l'ordre est corrigé) | **-5** |

INFO du contrôle (12) :

| # | Sujet | Statut |
|---|-------|--------|
| 1 | `Fixed` sans défaut publié | inchangée |
| 2 | #398 à part de #401 | inchangée |
| 3 | Puces redondantes, `analysisEditorEnabled` | inchangée |
| 4 | Design doc PDF sans `Status` | inchangée |
| 5 | Fichiers de travail à la racine | inchangée |
| 6 | SemVer | inchangée |
| 7 | Versions secondaires | inchangée |
| N1 | Couleurs absentes du changelog | **résolue** (`CHANGELOG.md:26`) |
| N2 | Trois imprécisions de l'API de l'éditeur | **résolue** (`docs/analysis-editor.md:41`, `:82`, `:83`) |
| N3 | `400` conditionnel | **résolue** (`docs/configuration.md:158`) |
| N4 | Ligne `services`, docstring de test | réduite : bibliothèques citées, docstring corrigée ; interdiction du système de fichiers non citée |
| N5 | Script de gate absent | **résolue** (job retiré `release-gate.yml:192-195`, ligne retirée de `docs/maintainers.md`) |

Aucune INFO aggravée. Nouvelles INFO : V1 à V10. Total : 8 restantes + 10 nouvelles = 18.

---

## Points positifs

- **Les réglages nouveaux sont documentés au bon endroit et avec les bons défauts** : `MAX_IMPORT_SIZE_MB`, `API_ALLOWED_HOSTS`, `LLM_PROVIDER_TYPE` ont le même nom et le même défaut dans `infra/settings.py`, `.env.example`, les deux compose et `docs/configuration.md`.
- **La section « Host check on the API » décrit exactement le middleware** : opt-in, `*`, loopback, 421, `/api/*` seulement, ligne de log. Le seul défaut est un conseil (`name:port`) qui ne marche pas derrière nginx.
- **`SECURITY.md` dit ce que la vérification ne protège pas** (un client non navigateur), sans la survendre.
- **La doc CI a suivi `23e4c81`** : job retiré, groupes audités, image `local`, `@critical` sur `release/*`, `UIRunner#testCritical`.
- **Quatre INFO du contrôle résolues**, aucun nom périmé malgré trois commits de déplacements, 0 lien cassé publié, 0 TODO.

---

## Verdict partiel : NO-GO (pré-freeze)

67/100, 1 CRITICAL, 1 MAJOR, 1 MINOR. Le commit de freeze lève le CRIT et le MAJ (94, GO) ; remonter `### Deprecated` avant `### Fixed` dans ce même commit donne 100. Avant le freeze, corriger les textes faux ou imprécis : `docs/mcp-server.md:154` (faux), `docs/user-guide.md:104`, `docs/configuration.md:32`, `:142`, `docs/analysis-editor.md` (ligne `422`), `CHANGELOG.md:19`, `:21`, et ajouter les puces manquantes.

### Non vérifiable ici

- Le rendu des pages et des diagrammes (`mkdocs` non lancé, consigne machine).
- « The JSON returned is unchanged » (`CHANGELOG.md:27`) : il faudrait comparer des réponses réelles avant et après `efc0bc5`.
- Le comportement réel derrière nginx : 413 de nginx contre celui du backend à 200 Mo, 421 avec un `name:port` (déduit de `nginx.conf.template:38` et `host_guard.py`, non exécuté).
- Ce que montre l'écran quand Ask répond depuis une autre analyse que celle affichée (étapes du raisonnement sur la page) : l'app n'a pas été lancée.
- L'aspect des écrans après `1516a0c` et le retour en 0.7.3 (comme la baseline).

# Rapport d'audit : Documentation & Changelog

> **Re-audit de release/0.7.3 @ e01fd95 — score 44 → 100**

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Type** : re-audit apres remediation (audit initial : 44/100, NO-GO, sur `02adc68`). Remediation : PR #367, commits `99e1230` (freeze du changelog, BREAKING, #359, #323, Security, version front), `79b9ae9` (ligne Security Pillow), `619f6fd` (`.env.example` `BATCH_PAGE_SIZE`, statuts des design docs), `3cc0160` (exposition MCP dans le changelog, `docs/mcp-server.md`, `.env.example`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 9 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 10 |

Ponderation : items conformes = 18 pts / 18 pts totaux → 100/100.
Les quatre ecarts ponderes de l'audit initial (11.1.1 poids 3, 11.1.3 poids 3, 11.1.2 poids 2, 11.2.1 poids 2) sont resolus.

---

## Verification de la remediation

| # | Item | Poids | Audit initial | Re-audit | Preuve |
|---|------|-------|---------------|----------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **[CRIT]** | ✅ Conforme | `CHANGELOG.md:7` `## [0.7.3] - 2026-11-02` |
| 11.1.2 | Modifications significatives listees | 2 | **[MAJ]** | ✅ Conforme | #359 `CHANGELOG.md:14`, #323 `CHANGELOG.md:19`, dependances `CHANGELOG.md:31-34` ; 12/12 merges couverts |
| 11.1.3 | Breaking changes identifies | 3 | **[CRIT]** | ✅ Conforme | `CHANGELOG.md:36-38` (`### BREAKING CHANGES`, `ASK_MODE`) |
| 11.1.4 | Format Keep a Changelog | 1 | ✅ | ✅ Conforme | `CHANGELOG.md:5` ; groupes `:9`, `:17`, `:27`, `:31`, `:36` (voir INFO `[Unreleased]`) |
| 11.2.1 | `frontend/package.json` a la version X.Y.Z | 2 | **[MAJ]** | ✅ Conforme | `frontend/package.json:3` = `0.7.3` ; lockfile `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version conforme au SemVer | 2 | ✅ | ✅ Conforme | `0.7.2 → 0.7.3` (voir INFO SemVer, inchangee) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | ✅ | ✅ Conforme | grep : 0 occurrence (back hors `.venv`, tests compris ; `frontend/src`) |
| 11.3.2 | Pas de `console.log` de debug | 2 | ✅ | ✅ Conforme | 2 `console.warn`, en `catch` : `frontend/src/features/analysis/store.ts:117`, `:176` |
| 11.3.3 | Pas de `print()` de debug | 2 | ✅ | ✅ Conforme | 0 `print(` executable ; 4 en commentaire/docstring (`document-parser/mcp_stdio.py:25`, `infra/settings.py:45`, `infra/secrets/fernet_box.py:46`, `:133`) |

### Detail des corrections

**11.1.1 — CRIT resolu.** `CHANGELOG.md:7` porte `## [0.7.3] - 2026-11-02`. La section contient Added (`:9`), Changed (`:17`), Deprecated (`:27`), Security (`:31`) et BREAKING CHANGES (`:36`). L'extraction des notes de GitHub Release (`awk '/^## \[0.7.3\]/…'`, `docs/maintainers.md:40`) renvoie desormais `CHANGELOG.md:8-39`. La date est celle d'aujourd'hui : si le tag glisse, il faut la mettre a jour. La section `[Unreleased]` vide n'a pas ete recreee (voir INFO).

**11.1.3 — CRIT resolu.** `### BREAKING CHANGES` (`CHANGELOG.md:36`) contient la puce **Ask hidden by default** (`:38`), retiree de `### Changed`. Verification dans le code :

| Affirmation (`CHANGELOG.md:38`) | Code | Resultat |
|---------------------------------|------|----------|
| `ASK_MODE` vaut `hidden` sauf `visible` | `document-parser/infra/settings.py:67`, `:236` | exact |
| Plus d'onglet Ask dans la vue Parse | `frontend/src/features/feature-flags/store.ts:80-84`, `:166` | exact |
| Plus de reglages de raisonnement dans Settings | `frontend/src/features/settings/ui/SettingsPanel.vue:94` (`v-if="askShown"`), `:122` | exact sur le fond, voir INFO sur le nom de la section |
| Ne fait que cacher : l'API suit `REASONING_ENABLED` | `ask_mode` n'est lu que pour `/api/health` (`document-parser/main.py:160`) | exact |
| `/api/health` expose `askMode` | `document-parser/main.py:160`, `document-parser/api/schemas.py:72` | exact |
| `ASK_MODE=visible` retablit Ask | `docker-compose.yml:190` transmet deja `ASK_MODE` | exact |

Les deux autres candidats sont acceptables. L'export Docling Serve `placeholder` reste sous `### Changed` (`CHANGELOG.md:25`), avec l'explication complete : c'est l'arbitrage que l'audit initial laissait au mainteneur. Le serveur MCP actif par defaut est un ajout, sans rupture d'un comportement existant. Son exposition sans authentification est maintenant ecrite sans ambiguite (`CHANGELOG.md:15` : « anyone who can reach `/mcp` can read every document »), ce que confirment `document-parser/infra/settings.py:92-96` et `document-parser/bootstrap/mcp_mount.py:218-230` (protection DNS rebinding sur `Host`/`Origin`, pas un controle d'acces).

**11.1.2 — MAJ resolu.** Les deux merges manquants ont leur entree, verifiee dans le code :

| Affirmation | Code | Resultat |
|-------------|------|----------|
| #359 : route `POST /api/analyses/import` (`CHANGELOG.md:14`) | `document-parser/api/analyses.py:22`, `:73-87` ; corps `documentId` + `document` `document-parser/api/schemas.py:272-276` | exact |
| #359 : **Import analysis** dans le menu d'actions d'un document, fichier `.json` | `frontend/src/features/document/ui/DocumentActionsMenu.vue:3`, `:28-30`, monte dans `frontend/src/pages/DocWorkspacePage.vue:28` ; libelle `frontend/src/shared/i18n.ts:981` | exact |
| #359 : PDF + JSON Docling ensemble a l'upload | `frontend/src/features/document/ui/DocumentUpload.vue:11-18`, `:38-40`, `:105-124` ; libelle `frontend/src/shared/i18n.ts:984` | exact, voir INFO sur l'endroit |
| #359 : validation contre `DoclingDocument` | `document-parser/infra/docling_importer.py:18` (`DoclingDocument.model_validate`), erreur → 400 `document-parser/api/analyses.py:83-85` | exact |
| #359 : analyse terminee avec Markdown, HTML, pages, entree History | `document-parser/infra/docling_importer.py:19-26` ; `document-parser/services/analysis_service.py:165-192`, `:481-498` (`record_on_analysis`) | exact |
| #323 : plus de *New analysis* sur la page d'une analyse | `frontend/src/pages/AnalysisDetailPage.vue:15-24` (aucun `newAnalysis` dans la page ni dans `DocParseTab.vue`) | exact |
| #323 : lien **Open document** vers l'espace du document | `frontend/src/pages/AnalysisDetailPage.vue:16-22`, libelle `frontend/src/shared/i18n.ts:1003` | exact |
| #323 : l'export prend `analysisId` en option | `document-parser/api/documents.py:133-146`, `document-parser/services/export_service.py:43-54`, `:97` ; envoye par `AnalysisDetailPage.vue:23` | exact |
| #323 : « the Analyses page is now the **Analysis library** » (`CHANGELOG.md:19`) | le menu et le titre affichent toujours « Analyses » (`frontend/src/shared/i18n.ts:752`, `:989`) | **inexact**, voir INFO |

Couverture : les 12 merges first-parent de `caddf30..02adc68` ont maintenant une entree. Le merge de remediation #367 est couvert par `### Security` (`CHANGELOG.md:33-34`). Ses autres commits sont internes (CI, refactor, import #359 sorti de la boucle d'evenements). Aucune puce pour les sujets reportes (#348, #349, #358, #350, #351, #319).

**11.2.1 — MAJ resolu.** `frontend/package.json:3` = `"version": "0.7.3"`. Le lockfile, reste a `0.6.2` depuis quatre releases, est aligne (`frontend/package-lock.json:3`, `:9`).

### Section `### Security` (ajoutee)

| Affirmation (`CHANGELOG.md:33-34`) | Source | Resultat |
|------------------------------------|--------|----------|
| PyJWT 2.15.1, mcp 2.2.0, certifi 2026.10.23 | `document-parser/uv.lock` (etaient 2.13.0, 2.1.1, 2026.7.22 a `02adc68`) | exact |
| aiohttp 3.14.5, multidict 6.9.1, opentelemetry-api 1.45.2, urllib3 2.8.0 | `document-parser/uv.lock` (etaient 3.14.3, 6.7.1, 1.44.0, 2.7.0) | exact |
| uv 0.13.6 dans les images | `Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9` (etait 0.11.6) | exact |
| Six suppressions Trivy retirees | `git diff 02adc68..e01fd95 -- .trivyignore.yaml` : 6 `- id` retires (mesa, libssh2, perl ×3, glib), commentaire `.trivyignore.yaml:2-6` | exact |
| Pillow 10.4.0, 4 CRITICAL acceptes jusqu'a 0.8.0, expiration 2026-12-31 | `document-parser/uv.lock` (pillow 10.4.0) ; `.trivyignore.yaml:32-55` (4 IDs identiques, `expired_at: 2026-12-31`) | exact |

---

## Metriques collectees

| Metrique | Valeur |
|----------|--------|
| Merges first-parent depuis `caddf30` (freeze 0.7.2) | 13 (les 12 de l'audit initial + #367 remediation) |
| Merges couverts par une entree du changelog | 13 / 13 (#357 via l'entree #340 ; #367 via `### Security`) |
| Affirmations nouvelles verifiees dans le code | 25 : 24 exactes, 1 inexacte (renommage « Analysis library ») |
| Puces pour des sujets reportes (#348, #349, #358, #350, #351, #319) | 0 (correct) |
| Versions | `frontend/package.json` 0.7.3, lockfile 0.7.3, `pyproject.toml` 0.0.0 (×2, placeholder), `e2e/*/pom.xml` 0.3.1 |
| TODO / FIXME / HACK / XXX | 0 |
| `console.log` / `console.debug` | 0 (`console.warn` : 2, en `catch`) |
| `print(` executable | 0 |
| `mkdocs build --strict` | OK (code 0 ; seul le bandeau « MkDocs 2.0 » de Material s'affiche) |

---

## Ecarts constates

### [INFO] `CHANGELOG.md:19` annonce un renommage que l'utilisateur ne voit pas

- **Localisation** : `CHANGELOG.md:19` ; aussi `:13` et `:21` (« opens the Analysis library », « found in the Analysis library »)
- **Constat** : la nouvelle puce #323 dit « the Analyses page is now the **Analysis library** ». Le renommage de #323 ne touche que le code : le fichier `AnalysesPage.vue` devient `AnalysisLibraryPage.vue` et la route s'appelle `analysis-library` (`a763420`, `frontend/src/shared/routing/names.ts:17`). Le menu affiche toujours « Analyses » (`frontend/src/shared/ui/AppSidebar.vue:145`, `frontend/src/shared/i18n.ts:752`), comme le titre de la page (`frontend/src/pages/AnalysisLibraryPage.vue:6`, `frontend/src/shared/i18n.ts:989`) et le lien retour de la page de detail (`frontend/src/pages/AnalysisDetailPage.vue:8`). Le nom `analysis-library` n'apparait que dans le badge de route en mode dev (`frontend/src/shared/routing/routeLabel.ts`). Le guide utilisateur dit bien **Analyses** (`docs/user-guide.md:30`, `:56`, `:62`). Le mot en gras renvoie donc a un ecran qui n'existe pas sous ce nom.
- **Regle violee** : hors checklist ponderee (exactitude du changelog).
- **Remediation** : avant le tag, reecrire le debut de `CHANGELOG.md:19`, par exemple « **Saved analyses** (#323): a saved analysis's page no longer offers *New analysis*… », sans annoncer de renommage. Ou bien renommer vraiment le libelle (`nav.analyses`, `analyses.title`), ce qui depasse le freeze. A `:13` et `:21`, « the **Analyses** page » suffit.

### [INFO] Import combine PDF + JSON : seulement sur la zone de depot de Home

- **Localisation** : `CHANGELOG.md:14` (« the upload dialog takes a PDF and its Docling JSON together ») ; `docs/user-guide.md:34-42`
- **Constat** : le bouton « Upload PDF and Docling analysis » appartient a `DocumentUpload.vue:38-40`, monte sur Home (`frontend/src/pages/HomePage.vue:12`) et sur `/studio`. Le parcours documente pour importer, **Docs** puis **Import** (`docs/user-guide.md:36`, page `DocsNewPage.vue`), ne l'offre pas. Le guide utilisateur ne parle toujours pas de l'import d'analyse (l'audit initial le proposait en option).
- **Regle violee** : hors checklist ponderee.
- **Remediation** : remplacer « the upload dialog » par « the Home drop zone ». Ajouter au cycle suivant une ligne dans `docs/user-guide.md` (menu ⋯ d'un document → **Import analysis** ; Home → **Upload PDF and Docling analysis**).

### [INFO] Puce BREAKING : la section Settings s'appelle « Ask », et elle dit comment revenir

- **Localisation** : `CHANGELOG.md:38`
- **Constat** : la puce dit que « **Settings** has no **Reasoning** section ». En 0.7.3, aucune section ne porte ce titre : `settings.reasoning.title` n'est plus utilise. Les reglages de raisonnement sont dans la section **Ask** (`frontend/src/features/settings/ui/SettingsPanel.vue:86-94`). Quand Ask est cache, cette section reste visible, avec la pastille *Hidden* et le texte « Start the backend with ASK_MODE=visible to show Ask here and in the Parse view » (`SettingsPanel.vue:95-100`, `frontend/src/shared/i18n.ts:1100-1101`). Le fond de la puce est exact (les reglages disparaissent), et le classement en rupture reste justifie : il faut redemarrer avec une variable d'environnement. Correction de l'audit initial : il ecrivait « L'interface ne donne aucun indice ». C'est faux, l'indice existait deja a `02adc68` (fichiers non modifies depuis).
- **Regle violee** : hors checklist ponderee (11.1.3 conforme).
- **Remediation** : optionnelle. Ecrire « **Settings › Ask** shows *Hidden* instead of the reasoning settings, and says how to bring them back ».

### [INFO] Pas de section `[Unreleased]` vide recreee au freeze

- **Localisation** : `CHANGELOG.md:5-7`
- **Constat** : le changelog passe de l'en-tete directement a `## [0.7.3]`. Les freezes 0.7.1 et 0.7.2 avaient garde un `## [Unreleased]` vide (`git show caddf30:CHANGELOG.md`, `git show e95680a:CHANGELOG.md`), comme le recommande Keep a Changelog. Le modele de PR demande toujours de mettre a jour le changelog « under `[Unreleased]` » (`.github/PULL_REQUEST_TEMPLATE.md:26`). `docs/maintainers.md:22-24` ne l'exige pas. Le commit de freeze s'appelle aussi `docs(changelog): freeze [Unreleased] as [0.7.3]`, et non `chore(release): freeze [0.7.3]` comme le prevoit `docs/maintainers.md:22`. Sans effet sur le tag.
- **Regle violee** : hors checklist ponderee (11.1.4 reste conforme : `[Unreleased]` est une recommandation).
- **Remediation** : ajouter `## [Unreleased]` au-dessus de `CHANGELOG.md:7`, maintenant ou a l'ouverture de `release/0.8.0`. Ecrire l'etape dans `docs/maintainers.md:22-24`.

### [INFO] Le changelog ne nomme que 4 des 7 variables `MCP_*` nouvelles (inchangee)

- **Localisation** : `CHANGELOG.md:15` (« new variable `MCP_MAX_ROUNDS` »)
- **Constat** : la puce a ete reecrite par `3cc0160` pour l'exposition, mais la fin n'a pas change. Elle parle d'une seule nouvelle variable alors que les sept `MCP_*` sont nouvelles. `MCP_APPS_ENABLED`, `MCP_MAX_READ_TOKENS` et `MCP_STUDIO_BASE_URL` ne sont evoquees qu'en prose. Le renvoi vers `docs/mcp-server.md` est la.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : « new variables `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, `MCP_STUDIO_BASE_URL`, `MCP_MAX_READ_TOKENS`, `MCP_MAX_ROUNDS`, `MCP_APPS_ENABLED`, `MCP_CITATION_CARD` ».

### [INFO] Section Security : tracabilite des avis certifi et uv

- **Localisation** : `CHANGELOG.md:33`
- **Constat** : les versions et les CVE citees correspondent au lockfile, aux Dockerfiles et aux rapports `docs/audit/reports/release-0.7.3/08-security.md:75-76` et `10-ci-build.md:71-72`. En revanche, la puce attribue les intermediaires emSign compromis a certifi. Le commit `7246efe` les attribue a uv (« drops the compromised emSign root (GHSA-hq85-5cpj-mr62) ») et donne certifi pour GHSA-6q48-6c7w-9gw2 sans description. Les deux GHSA ne figurent pas dans le changelog. Point non verifiable hors ligne.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : verifier les deux avis et citer leurs GHSA dans la puce, comme pour les CVE.

### [INFO] Jalons GitHub incoherents avec le contenu livre (inchangee, action mainteneur)

- **Localisation** : GitHub (`gh issue list --milestone 0.7.3`, `gh issue view`)
- **Constat** : le jalon `0.7.3` liste toujours #348, #349 et #358 comme ouverts (reportes). #327 et #363 sont OPEN sous `0.8.0`, #364 est CLOSED sous `0.8.0`. #329 est OPEN alors que son design doc dit maintenant « Superseded by #363 ». #361 est OPEN sans jalon. Les PR #359 et #323 n'ont pas de jalon.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : celle de l'audit initial (deplacer #348, #349, #358 vers 0.8.0 ; rattacher #327, #363, #364 a 0.7.3 et les fermer ; fermer #329 ; garder #361 ouvert pour docling 2.140.0).

### [INFO] Versions secondaires (partiellement resolue)

- **Localisation** : `document-parser/pyproject.toml:3`, `embedding-service/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10`, `e2e/ui/pom.xml:10` (`0.3.1`)
- **Constat** : le lockfile frontend est aligne (`frontend/package-lock.json:3`, `:9`). Les `pyproject.toml` gardent leur placeholder `0.0.0` : la version servie vient de `APP_VERSION`. `docs/maintainers.md` ne le dit toujours pas. Les POM e2e restent a `0.3.1`.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : une ligne dans `docs/maintainers.md` sur le placeholder volontaire.

### [INFO] SemVer : un patch qui ajoute de l'API publique et une depreciation (inchangee)

- **Localisation** : `CHANGELOG.md:7-34`
- **Constat** : 0.7.3 ajoute des routes publiques (`/mcp`, `/api/config/mcp`, `/api/mcp/server`, `/api/analyses/summaries`, `/api/analyses/import`, `/api/documents/{id}/pages`), une depreciation et maintenant une rupture declaree. 11.2.2 reste conforme : SemVer §4 en 0.y.z, precedent 0.6.1/0.6.2, decision du mainteneur.
- **Regle violee** : item 11.2.2 conforme ; simple note.
- **Remediation** : aucune pour 0.7.3. Pour 0.8.0, une regle ecrite dans `docs/maintainers.md`.

### [INFO] Pages Architecture et Configuration muettes sur le serveur MCP (inchangee)

- **Localisation** : `docs/architecture.md:80-87`, `docs/configuration.md`
- **Constat** : le tableau des prefixes ne contient ni `/mcp` ni `/api/mcp`. Il decrit `/api/config` comme « The reasoning settings edited in **Settings** » (`docs/architecture.md:86`) et `/api/analyses` comme « start, read, delete » (`:83`), sans l'import ni les summaries. `docs/configuration.md` ne contient aucune occurrence de « MCP ». Les variables sont documentees dans `docs/mcp-server.md`, que la remediation a precise sur l'exposition (`docs/mcp-server.md:14-20`, `:324-331`).
- **Regle violee** : hors checklist ponderee.
- **Remediation** : celle de l'audit initial, au cycle suivant.

### INFO de l'audit initial resolues

- **`.env.example` et `BATCH_PAGE_SIZE`** : resolue. `.env.example:11-12` dit maintenant que les batchs sont fusionnes (#344) et que l'arbre, les chunks, Ask et l'export JSON fonctionnent, ce qui est coherent avec `docs/configuration.md:20`.
- **Statut des design docs** : resolue. `docs/design/363-mcp-chunkless-rag-simplification.md:7` et `docs/design/364-mcp-admin-panel-section.md:7` sont `Implemented (shipped in 0.7.3)`, et `docs/design/329-mcp-investigation-journal-navigation-tree.md:33` est `Superseded by #363`. Detail restant : la ligne `Target milestone` dit toujours `0.8.0` (`:8` dans 363 et 364).

---

## Delta vs audit initial

| Item | 0.7.3 initial (`02adc68`) | 0.7.3 re-audit (`e01fd95`) | Evolution |
|------|---------------------------|----------------------------|-----------|
| 11.1.1 Changelog fige | **CRIT** | OK | freeze `[0.7.3] - 2026-11-02` |
| 11.1.2 Changements listes | **MAJ** | OK | #359, #323 et Security ajoutes |
| 11.1.3 Breaking identifies | **CRIT** | OK | `### BREAKING CHANGES` avec `ASK_MODE` |
| 11.1.4 Keep a Changelog | OK | OK | = (INFO `[Unreleased]`) |
| 11.2.1 Version front | **MAJ** | OK | `0.7.3`, lockfile aussi |
| 11.2.2 SemVer | OK | OK | = |
| 11.3.1 TODO/FIXME | OK | OK | = |
| 11.3.2 console.log | OK | OK | = |
| 11.3.3 print() | OK | OK | = |
| **Score** | **44** | **100** | **+56** |

INFO : 7 a l'audit initial. 2 sont resolues (`BATCH_PAGE_SIZE`, design docs), 5 restent (jalons, versions secondaires en partie, SemVer, Architecture/Configuration, variables MCP). 5 sont nouvelles et portent sur le texte ajoute par la remediation : renommage « Analysis library », lieu de l'import combine, nom de la section Settings, `[Unreleased]` absent, avis certifi/uv. Total : 10.

---

## Points positifs

- **Freeze complet en un commit** (`99e1230`) : changelog fige, rupture classee, deux merges ajoutes, Security, `package.json` et lockfile. Le lockfile, en retard depuis 0.6.2, est enfin aligne.
- **Texte ajoute exact dans l'ensemble** : 24 des 25 affirmations nouvelles correspondent au code, aux lockfiles, aux Dockerfiles et a `.trivyignore.yaml`. C'est le cas de la route et de la validation de #359, de l'`analysisId` de #323, des 8 versions de dependances, d'uv dans les 3 images, des 6 suppressions retirees et des 4 CVE Pillow avec leur date d'expiration.
- **Puce BREAKING utile a l'operateur** : elle dit ce qui disparait, ce qui ne change pas (l'API suit `REASONING_ENABLED`) et comment revenir (`ASK_MODE=visible`, deja transmis par `docker-compose.yml:190`).
- **Risque accepte ecrit en clair** : la puce Pillow dit ce qui a ete verifie et ce qui ne l'a pas ete (« the paths inside docling are not verified »). Elle donne aussi l'echeance.
- **Exposition MCP decrite honnetement** : le changelog (`CHANGELOG.md:15`), `.env.example:102-106`, `docs/mcp-server.md:14-20` et `:324-331` disent maintenant que `MCP_ALLOWED_HOSTS` n'est pas un controle d'acces, ce que confirme `document-parser/bootstrap/mcp_mount.py:218-230`.
- **Code propre** : 0 TODO/FIXME, 0 `console.log`, 0 `print()` executable. `mkdocs build --strict` passe.

---

## Verdict partiel : GO

Les deux `[CRIT]` (11.1.1 changelog non fige, 11.1.3 rupture `ASK_MODE` non classee) et les deux `[MAJ]` (11.1.2 #359/#323 absents, 11.2.1 version front) sont resolus et verifies sur `e01fd95`. Score : **100/100** (18/18), 0 CRITICAL, 0 MAJOR. 10 INFO non bloquantes. Avant le tag, il est recommande de corriger la phrase inexacte de `CHANGELOG.md:19` (« the Analyses page is now the **Analysis library** » : l'interface dit toujours « Analyses »), car elle partira telle quelle dans les notes de la GitHub Release. Il faut aussi ajuster la date de `CHANGELOG.md:7` si le tag n'est pas pose le 2026-11-02.

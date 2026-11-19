# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `a744f48`. Arbre de travail lu tel quel.
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (`release-0.7.4-validation/11-documentation.md` : 67/100, 94 puis 100 au freeze, 1 CRIT, 1 MAJ, 1 MIN, 18 INFO).
**Contexte** : le commit de freeze n'est toujours pas fait (`docs/maintainers.md:22-24`). `[Unreleased]` et la version `0.7.3` du frontend restent attendus ; deux scores, comme la base.

Commits relus : `git log efc0bc5..a744f48` (9 commits ; code : `60234e4`, `da6603d`, `73ceaf3`, `914246e`, `1cd8413` ; docs : `894bba4`, `a744f48`). Pages touchées : `CHANGELOG.md`, `.env.example`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/analysis-editor.md`, `docs/architecture.md`, `docs/configuration.md`, `docs/mcp-server.md`, `docs/user-guide.md`, `e2e/CONVENTIONS.md`, `e2e/api/README.md`. `docs/user-guide.md` relu en entier contre `frontend/src/app/router/routes.ts`, les pages montées et `frontend/src/shared/i18n.ts`. Rien n'a été exécuté hors un script de lecture (liens, ancres, identifiants).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 15 |

Pondération : poids total 18. Non conformes : 11.1.1 (3), 11.2.1 (2) = 5. `13 / 18 * 100 = 72,2` -> **72**.

### Score au freeze

| Scénario | Écarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Aujourd'hui (pré-freeze) | 11.1.1 CRIT, 11.2.1 MAJ | 72 | NO-GO (CRIT) |
| Après le commit de freeze | aucun | 100 | GO |

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 11.1.1 | `[Unreleased]` renommée en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pré-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listées | 2 | Oui | Les changements de ce cycle sont annoncés : analyse active après suppression `:24`, chemin du PDF exporté `:51`, Host par nom et 421 JSON `:55`, 400 sur `Content-Length` invalide `:31`. Les quatre manques de la base sont comblés (`:19`, `:22`, `:23`, `:26`). Deux manques mineurs (INFO F7) |
| 11.1.3 | Breaking changes identifiés | 3 | Oui | Aucune route ni champ retiré. Changement de sémantique de `API_ALLOWED_HOSTS` (port ignoré) : la variable n'a jamais été publiée, rien ne casse. Composants frontend supprimés par `60234e4` : aucun n'était monté, rien de visible |
| 11.1.4 | Format Keep a Changelog | 1 | Oui | `:9` Added, `:15` Changed, `:35` Deprecated, `:39` Fixed, `:53` Security : ordre correct, une section de chaque. Ligne vide en double supprimée |
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

### [INFO] F1. `docs/user-guide.md:119` : suppression de l'analyse active, deux imprécisions

- **Localisation** : `docs/user-guide.md:119`
- **Constat** :
  - « the last remaining completed analysis becomes the active one » : c'est la dernière analyse terminée *qui a un document Docling* (`persistence/analysis_repo.py:229-235`, `_find_latest_parsed_ids` `:249-268`, `status = 'COMPLETED' AND document_json IS NOT NULL`).
  - « the default download and the document tree have nothing to read » : faux pour l'écran. La page de résultat passe toujours l'id de l'analyse ouverte au téléchargement (`frontend/src/pages/AnalysisDetailPage.vue:42-46`) et à l'arbre (`frontend/src/pages/DocParseTab.vue:331`). Seuls Ask, MCP et les appels API sans `analysisId` dépendent de l'analyse active.
- **Remediation** : texte prêt à coller dans « Vérification des affirmations ».

### [INFO] F2. `docs/user-guide.md:48-49` : **New analysis** est dans un menu

- **Localisation** : `docs/user-guide.md:49`
- **Constat** : dans la page du document, **New analysis** est un élément du menu **Document actions** (bouton `⋯`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:4-26`, monté par `pages/DocWorkspacePage.vue:28`). Le guide dit « Click **New analysis** » comme s'il s'agissait d'un bouton visible. Antérieur à ce cycle, non relevé par la base.
- **Remediation** : « 2. Open the **Document actions** menu (`⋯`) and click **New analysis**. (In **Docs**, the row's magnifier icon does the same.) While Docling works, … »

### [INFO] F3. `docs/bbox-pipeline.md:86` : « the Parse and Chunk tabs », l'onglet Chunk n'existe plus

- **Localisation** : `docs/bbox-pipeline.md:86` (page publiée, nav `mkdocs.yml` « Bounding boxes »)
- **Constat** : `frontend/src/pages/DocChunkTab.vue` a été supprimé par `60234e4` (déjà non monté avant). `BboxCanvas.vue` sert via `PagePreviewWithOverlay.vue`, monté par `DocParseTab.vue`, `DocWorkspacePage.vue` et `AnalysisEditor.vue`.
- **Remediation** : « The result page, the document page and the analysis editor draw with `frontend/src/features/document/ui/BboxCanvas.vue`. »

### [INFO] F4. `docs/maintainers.md:54` : un run annulé ne publie plus de verdict

- **Localisation** : `docs/maintainers.md:54`
- **Constat** : depuis `1cd8413`, `release-summary` ne tourne pas sur un run annulé (`.github/workflows/release-gate.yml:746-747`) et tout résultat autre que `success` d'un job bloquant donne NO-GO (`:793-803`). La page dit qu'un verdict est toujours posté. Le reste est exact (GO CONDITIONAL si seul `dep-audit` échoue `:805-806`, taille d'image non bloquante, jeton en lecture seule `:14-15`).
- **Remediation** : « It runs on every pull request to `main` and posts a verdict: GO, GO CONDITIONAL (only the dependency audit failed), or NO-GO (any other check that did not succeed, a skipped one included). A cancelled run, for example one replaced by a newer push, posts none. »

### [INFO] F5. `CHANGELOG.md:51` : le libellé **Download PDF** n'existe pas

- **Localisation** : `CHANGELOG.md:51`
- **Constat** : le menu **Download** propose **PDF Document** (`frontend/src/shared/i18n.ts:906`, `docs.downloadPdf`) ; la liste **Docs** n'a qu'une icône. Le fond est vrai : `services/export_service.py:95-96` résout maintenant le chemin par `infra/document_file_store.py:56-65`, comme `services/preview_service.py:89`, `:106`.
- **Remediation** : remplacer « answered 404 on **Download PDF** » par « answered 404 when downloading the PDF ».

### [INFO] F6. `CHANGELOG.md:20` : « document History » désigne un écran qu'aucune route n'affiche

- **Localisation** : `CHANGELOG.md:20`
- **Constat** : `HistoryDrawer.vue` n'est monté nulle part (`rg HistoryDrawer frontend/src` : aucun import ; `setWorkspaceVersion`, seul appelant de la restauration, n'a aucun appelant monté, `features/document/store.ts:221`). La phrase parle du stockage, mais le mot « History » en majuscule se lit comme un écran.
- **Remediation** : « … document versions still store chunk snapshots. »

### [INFO] F7. CHANGELOG : deux changements absents

- **Localisation** : `CHANGELOG.md:11`, `:25`
- **Constat** : (a) restauration d'une version dont l'analyse est supprimée au même moment : 409 au lieu de 500 (`services/version_service.py:76`, `:162-164`, `73ceaf3`) ; (b) une sauvegarde refusée par le serveur pour une autre raison qu'un conflit s'affiche dans un bandeau, édits en attente conservés (`features/analysis-editor/ui/EditorBanners.vue:6`, `:56`, `da6603d`). (b) touche une fonctionnalité nouvelle de 0.7.4 : une phrase dans la puce Added suffit.
- **Remediation** : textes dans la section CHANGELOG.

### [INFO] F8. Pas d'entrée « 421 Invalid Host header » au dépannage (reprise de V4)

- **Localisation** : `docs/troubleshooting.md`
- **Remediation** : « **The API answers 421 `Invalid Host header`.** `API_ALLOWED_HOSTS` is set and the name in the address bar is not in it. Add that name (without the port), or the name your proxy forwards in `Host`. See [Host check on the API](configuration.md#host-check-on-the-api). »

### [INFO] 1 à 7. Reprises de la base (inchangées)

1. `### Fixed` : #391-#398 corrigent du code non publié ; seul `:51` (chemin du PDF) corrige un défaut publié. Réduite.
2. #398 (`:46`) encore à part de #401 (`:17`).
3. Puces redondantes autour de l'éditeur (`:11-13`, `:19-20`, `:47-50`), `analysisEditorEnabled` de `/api/health` non cité.
4. `docs/design/pdf-loading-performance.md:1-5` sans `Status`.
5. Fichiers de travail suivis à la racine : `analysis_editor_path_to_alpha.md`, `orca.yaml`.
6. SemVer : un patch qui livre une fonctionnalité, une API et une migration.
7. Versions secondaires : `document-parser/pyproject.toml:3` (`0.0.0`), `e2e/api/pom.xml:10` (`0.3.1`).

---

## Vérification des affirmations

V = vrai, F = faux, I = imprécis, N = invérifiable ici.

### Les onze affirmations et les sept points CHANGELOG de la base

| Base | Texte actuel (`fichier:ligne`) | Statut | Code |
|------|--------------------------------|--------|------|
| `user-guide.md:104` (V1) | `:104` « the analysis that completed last… Opening an older analysis from **Analyses** does not change it… without the changes saved » ; plus de « restore from **History** » | **corrigé** | `persistence/analysis_repo.py:171-185` ; `services/reasoning_service.py:103-105` ; `api/reasoning.py:29-34` (pas d'id d'analyse) |
| `user-guide.md:119` (V1) | `:119` phrase ajoutée | **partiel** (F1) | voir F1 |
| `mcp-server.md:154` (V2, F) | `:154` « the `version_id` the tools read by default… `null` when it has none with a Docling document » | **corrigé** | `services/current_analysis.py:57-67`, `services/navigation_service.py:92` |
| `mcp-server.md` après `:160` (V2) | `:161-164` paragraphe ajouté | **corrigé** | `services/parse_loader.py:1-6`, `:78-104` |
| `mcp-server.md:216` (V3) | `:221` « other than the document's current one… A document with no current parse answers `verified` » | **corrigé** | `services/citation_service.py:148-162`, `:209-215` |
| `mcp-server.md:329` (V9) | `:334-336` « A similar `Host` check… (no `Origin` check, loopback always accepted) » | **corrigé** | `infra/host_guard.py:31`, `:78-89` |
| `configuration.md:32` (V5) | `:32` « at least as large… With the defaults it equals `MAX_IMPORT_SIZE_MB`… raise both together » | **corrigé** | `main.py:95-101` ; `Dockerfile` / compose `200M` |
| `configuration.md:142` (V4) | `:142` « Only the host name is compared… the port is ignored here. `*` means no check » | **corrigé** (sémantique changée par `914246e`) | `infra/host_guard.py:34-42`, `:75-76`, `:45-48` ; `main.py:117-119` |
| `analysis-editor.md` 422 (V6) | `:85` ligne `422` | **corrigé** | `api/schemas.py:166-229` |
| `CONTRIBUTING.md:97`, `e2e/api/README.md:54`, `e2e/CONVENTIONS.md:167` (V10) | textes de la base repris mot pour mot | **corrigé** | `.github/workflows/ci.yml:3-7`, `:64`, `:189-192` |
| `architecture.md:73` (N4) | `:73` « and the filesystem (`os`, `shutil`, `pathlib.Path`, `open()`) » | **corrigé** | `tests/test_architecture.py:237-265` |
| CHANGELOG `:19` contradiction | `:19` active = dernière terminée ; workspace/arbre/export/rechunk avec éditions, Ask/MCP sans | **corrigé** | voir plus haut |
| CHANGELOG `:21` contradiction | `:21` « the two differ once edits are saved, or after an older analysis was made active again » | **corrigé** | `services/export_service.py:125-151` |
| CHANGELOG `:22` complément | `:22` `find_documents`, nouveau `detail` de `stale_version`, restauration par l'API seulement | **corrigé** | `services/citation_service.py:156-158` |
| Manque : erreurs de `/preview` | `:26` | **ajouté** | `services/preview_service.py:122-138` |
| Manque : `currentAnalysisId` liste/upload | `:23` | **ajouté** | `api/documents.py:36`, `:106` |
| Manque : repli sans ligne d'état | `:19` (fin) | **ajouté** | `domain/models.py:144-161` |
| Manque : `detail` de `stale_version` | `:22` | **ajouté** | idem |

### Phrases ajoutées ou modifiées depuis `efc0bc5`

| Fichier:ligne | Affirmation | Verdict | Code | Texte corrigé |
|---------------|-------------|---------|------|---------------|
| `.env.example:46-49` | Nom seul comparé, port ignoré, loopback toujours, 421, valeur conseillée | V | `infra/host_guard.py:31-42`, `:75-89` | — |
| `SECURITY.md:58` | `/api` vérifié si réglé ; valeur conseillée | V | `main.py:117-119` | — |
| `configuration.md:136` | Non listé ou malformé : 421 `{"detail": "Invalid Host header"}` | V | `host_guard.py:39-42`, `:88` | — |
| `configuration.md:142-146` | Nom seul ; port accepté et ignoré ; `*` = pas de vérification ; loopback ; `/api/*` seul ; ligne au démarrage | V | `host_guard.py:45-61`, `:79` ; `main.py:119` | — (non dit : une entrée malformée est ignorée en silence, `:75-76`) |
| `configuration.md:32` | `NGINX_MAX_BODY_SIZE` | V | voir plus haut | — |
| `analysis-editor.md:85` | 422 : bornes ou corps malformé | V | `api/schemas.py:166-229` | — |
| `architecture.md:73` | Système de fichiers interdit dans `services` | V | `tests/test_architecture.py:237-265` (`PurePath` permis) | — |
| `mcp-server.md:154`, `:161-164`, `:221`, `:334-336` | voir tableau précédent | V | | — |
| `user-guide.md:104` | Ask lit l'analyse active, la dernière terminée, sans les éditions | V | voir plus haut | — |
| `user-guide.md:119` | Suppression de l'active | I | `analysis_repo.py:229-235`, `:249-268` ; `AnalysisDetailPage.vue:42-46` ; `DocParseTab.vue:331` | « An analysis: in **Analyses**, click **Delete analysis** on its row. If it was the document's active analysis, the latest remaining completed analysis that has a Docling document becomes the active one. If none remains, the document has no active analysis: Ask and the MCP tools have nothing to read until a new analysis completes. » |
| `CHANGELOG.md:19` | Active = dernière terminée, sauf restauration par l'API ; repli sans ligne d'état | V | `analysis_repo.py:171-185` ; `domain/models.py:144-161` | — |
| `CHANGELOG.md:21` | Export par défaut ; 404 sans document Docling | V | `export_service.py:105-151` | — |
| `CHANGELOG.md:22` | « no screen offers it in this release » | V | `HistoryDrawer.vue` non monté ; `store.ts:221` sans appelant | — |
| `CHANGELOG.md:23` | `currentAnalysisId` ; `null` sur liste et upload | V | `api/documents.py:36`, `:48`, `:106` | — |
| `CHANGELOG.md:24` | Suppression de l'active : dernière terminée avec document Docling, même transaction ; aucune = pas d'active | V | `analysis_repo.py:206-237` (`BEGIN IMMEDIATE`) ; `domain/models.py:129-141` | — |
| `CHANGELOG.md:25` | Restauration et rechunk atomiques (API) | V | `persistence/chunk_repo.py:147-163` | — |
| `CHANGELOG.md:26` | `/preview`, `/pages` : 500 / 422 / 404 | V | `preview_service.py:122-138` | — |
| `CHANGELOG.md:31` | `Content-Length` malformé : 400 | V | `infra/body_limit.py:39-45` | — |
| `CHANGELOG.md:44` | Réponses hors boucle, plus de coût quadratique | N | exige une mesure | — |
| `CHANGELOG.md:51` | Chemin du PDF exporté résolu comme la prévisualisation | V (libellé I) | `export_service.py:95-96` ; `document_file_store.py:56-65` | F5 |
| `CHANGELOG.md:55` | Host check : 421 JSON, nom seul, loopback, opt-in | V | `host_guard.py` ; `main.py:117-119` | — |
| `CONTRIBUTING.md:97` | Tests Docling sur PR vers `main` et push `main`/`release/*` | V | `ci.yml:62-64` | — |
| `e2e/api/README.md:54`, `e2e/CONVENTIONS.md:167` | `@smoke,@regression,@e2e` sur PR et push `release/*` | V | `ci.yml:189-192` | — |

### Écrans retirés et guide utilisateur

- Aucune page publiée ni entrée de `[Unreleased]` ne présente comme faisable dans l'interface : la restauration depuis History, l'onglet Chunk, la boîte de lancement d'ingestion, le popover de stratégie, les onglets Inspect, le StructureViewer. Les mentions restantes sont dans des sections publiées de versions passées (`CHANGELOG.md:166-169`, `:247`), ce qui est normal. Seule trace d'un écran retiré dans une page publiée : `docs/bbox-pipeline.md:86` (F3). Studio (`/studio`, `STUDIO_MODE_ENABLED`) offre toujours le chunking et l'ingestion (`pages/StudioPage.vue:478-494`) : `user-guide.md:131` et `configuration.md:56` restent vrais.
- `docs/user-guide.md` relu en entier : chaque libellé cité existe dans `i18n.ts` (anglais) et est utilisé par un composant monté sur une route : **Home** (`HomePage.vue:16-37`, `:92` 5 derniers), **Docs**/**Import**/**Open visualization**/**Analyze**/**Delete** (`DocsLibraryPage.vue`), **Imported**/**File too large** (`DocsNewPage.vue:114`, `upload.tooLarge`), **Runs** « Coming soon » (`RunsPage.vue`), **Settings**/**Langue** (`SettingsPanel.vue`), **Structure**/**Filter elements…**/**Properties**/**Show all**/**Ask** (`DocParseTab.vue`), **LAYERS**/**Hide boxes**/**Show boxes** (`LayersBar.vue`), **Open large** (`ElementProperties.vue`), **Page**/**Scroll** (`PagePreviewWithOverlay.vue`), **Edit analysis**/**Inspect analysis**/**Download** (`AnalysisDetailPage.vue`), **Save**/**Discard changes**/**Show reading order**/**Undo**/**Redo**/**History (n)** (`AnalysisEditor.vue`), **Revert**/**Reapply** (`AnalysisEditHistoryPanel.vue`), **Run**/**model override** (`Composer.vue`), **Reasoning** (`TraceTimeline.vue`), **Delete analysis** (`AnalysisLibraryPage.vue`), **PDF Document**/**Markdown**/**Docling JSON** (`DownloadDropdown.vue`, PDF seul dans **Docs** `:89`). Seul écart : **New analysis** dans un menu (F2). Défauts cités vrais : 50 Mo (`settings.py:28`), 3 analyses simultanées (`:24`).

### Liens, nav, identifiants, réglages

- **Liens** (script, `docs/*.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, trois fichiers `e2e/`) : 85 liens relatifs, 0 cassé, 0 ancre cassée. Nouvelle ancre `configuration.md#host-check-on-the-api` depuis `CHANGELOG.md:55` : résolue.
- **Nav `mkdocs.yml:34-46`** : inchangée, toutes les pages existent. `mkdocs build --strict` non exécuté.
- **Identifiants** : aucun des noms retirés ou renommés (`load_active_result`, `find_latest_completed`, `hash_chunkset`, `health_check`, `get_default`, `domain/hashing.py`, `StructureViewer`, `DocChunkTab`, `IngestLaunchDialog`, `InspectResultTabs`, `AnalysisPanel`) n'apparaît dans une page publiée ni dans `[Unreleased]`. Seules mentions : sections de versions passées (`CHANGELOG.md:247`, `:249`). Les identifiants absents du code relevés par le script sont des exemples (`release/x.y.z`, `fix/142-…`), des fichiers générés (`out/demo/…`, `target/karate-reports/…`), `docker-compose.override.yml`, `chunk_edits` (dit retiré) et des noms historiques du CHANGELOG.
- **Réglages** : chaque variable lue par `document-parser` (hors `tests/`) est documentée dans `docs/configuration.md`, `docs/mcp-server.md` ou `docs/getting-started.md` ; seules `NEO4J_TEST_*` ne le sont pas, lues par `tests/neo4j/conftest.py`. Chaque variable du tableau de configuration est lue par le code ou la config Docker. `OPENSEARCH_DEFAULT_LIMIT` toujours lu (`infra/settings.py:252`).

---

## CHANGELOG

### Ordre et cohérence

Ordre Keep a Changelog respecté, une section de chaque. Aucune entrée fausse sur le fond ; aucune contradiction entre `:19`, `:21`, `:22`, `:24`. Retouches de libellé : `:51` (F5), `:20` (F6).

### Entrées manquantes, texte proposé

- Sous `### Changed`, après `:25` : « **Restoring a version while its analysis is deleted**: the versions API answers 409 instead of a server error. »
- Dans `:11`, après la phrase sur le 409 : « A save the server refuses for another reason, for example a request over the editor's bounds, shows in a banner and keeps the pending edits. »
- Écrans supprimés par `60234e4` : aucune entrée à ajouter, aucun n'était atteignable.

---

## Delta vs validation

| Item | Validation (`efc0bc5`) | Final (`a744f48`) | Évolution |
|------|------------------------|-------------------|-----------|
| 11.1.1 | CRIT | CRIT | = (pré-freeze) |
| 11.1.2 | OK | OK | = ; V8 résolue, deux manques mineurs (F7) |
| 11.1.3 | OK | OK | = |
| 11.1.4 | MIN | **OK** | **mieux** : `Deprecated` avant `Fixed` |
| 11.2.1 | MAJ | MAJ | = (pré-freeze) |
| 11.2.2 | OK | OK | = |
| 11.3.1 | OK | OK | = |
| 11.3.2 | OK | OK | = |
| 11.3.3 | OK | OK | = |
| **Score** | **67** (94 au freeze, 100 avec l'ordre) | **72** (100 au freeze) | **+5** |

INFO de la validation (18) :

| # | Sujet | Statut |
|---|-------|--------|
| V1 | `user-guide.md:104`, `:119` | `:104` résolue ; `:119` réduite (F1) |
| V2 | `find_documents` et ce que lit MCP | résolue |
| V3 | `stale_version` | résolue |
| V4 | `name:port` derrière nginx | résolue (port ignoré par le code) ; entrée de dépannage reprise en F8 |
| V5 | `NGINX_MAX_BODY_SIZE` | résolue |
| V6 | 422 de l'éditeur | résolue |
| V7 | Entrées contradictoires | résolue |
| V8 | Entrées manquantes | résolue |
| V9 | « The same guard » | résolue |
| V10 | Portée de la CI | résolue |
| N4 | Système de fichiers | résolue |
| 1-7 | Reprises | inchangées (1 réduite) |

Nouvelles INFO : F2 à F7 (F1 et F8 sont des reprises réduites). Total : 7 reprises + 8 = 15.

---

## Points positifs

- Les onze imprécisions et les sept points CHANGELOG de la validation sont tous traités, la plupart avec le texte proposé.
- La doc a suivi le code le jour même : port ignoré, 421 JSON, analyse active après suppression, 400 du `Content-Length`, verdict de la gate dans le code.
- Le retrait de la restauration dans l'interface est dit honnêtement (`CHANGELOG.md:22`) au lieu d'être caché ; plus aucune page ne promet un écran disparu, sauf une ligne technique (F3).
- 0 lien cassé, 0 nom périmé publié, 0 TODO, ordre Keep a Changelog rétabli.

---

## Verdict partiel : NO-GO (pré-freeze)

72/100, 1 CRITICAL, 1 MAJOR, 0 MINOR. Le commit de freeze lève les deux : 100, GO. Avant le freeze, à coller : `docs/user-guide.md:119` (F1), `:49` (F2), `docs/bbox-pipeline.md:86` (F3), `docs/maintainers.md:54` (F4), `CHANGELOG.md:51`, `:20` et deux phrases (F5-F7). Aucun n'est bloquant.

### Non vérifiable ici

- Le rendu des pages et des diagrammes (`mkdocs` non lancé).
- `CHANGELOG.md:29` « The JSON returned is unchanged » et `:44` (temps quadratique) : il faudrait exécuter l'API et mesurer.
- Le comportement réel derrière nginx (413, 421) : déduit du code, non exécuté.
- L'aspect du bandeau de sauvegarde refusée et des écrans : l'app n'a pas été lancée.

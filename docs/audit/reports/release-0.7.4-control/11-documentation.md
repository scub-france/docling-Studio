# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `a12b744`. Arbre de travail lu tel quel.
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/11-documentation.md`, 72/100, 1 CRIT, 1 MAJ, 11 INFO).
**Contexte** : le commit de freeze n'est pas fait (étape du mainteneur, `docs/maintainers.md:22-24`). `[Unreleased]` et la version `0.7.3` du frontend sont donc attendus. Même lecture de la fiche que la baseline ; deux scores.

Commits relus pour cet audit : `9491d26` (docs), `a12b744` (CHANGELOG), `10ecb05` (`CONTRIBUTING.md`), `4bd6e0c` (`docs/bbox-pipeline.md`). Chaque affirmation des pages modifiées a été vérifiée contre le code à `a12b744`, après les commits de code de la soirée (`437058d`, `25f5d8b`, renommages `0c97a1a`, `0c4d701`, `4bd6e0c`, couleurs `1516a0c`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 12 |

Pondération : poids total 18. Non conformes : 11.1.1 (3), 11.2.1 (2) = 5. `13 / 18 * 100 = 72,2` -> **72**.

### Score au freeze

| Scénario | Écarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Aujourd'hui (pré-freeze) | 11.1.1 CRIT, 11.2.1 MAJ | 72 | NO-GO (CRIT) |
| Après le commit de freeze (`## [0.7.4] - YYYY-MM-DD`, `frontend/package.json` + lockfile en `0.7.4`) | aucun | 100 | GO |

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 11.1.1 | `[Unreleased]` renommée en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pré-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listées | 2 | Oui | Éditeur `:11`, rendu PDF `:17`, résumés `:18`, export par défaut `:21`, fichiers statiques `:23`, Node 22 `:24`, #391-#398 `:28-37`. Manque le changement d'aspect de `1516a0c` (INFO N1), non significatif au sens de la fiche |
| 11.1.3 | Breaking changes identifiés | 3 | Oui | Aucune rupture. Node 22 pour construire depuis les sources est annoncé `:24`. Codes HTTP inchangés par `437058d`/`25f5d8b` (`api/errors.py:17-31`, `api/documents.py:148-175`) |
| 11.1.4 | Format Keep a Changelog | 1 | Oui | `CHANGELOG.md:5` ; une seule section `### Added` `:9`, `### Changed` `:15`, `### Fixed` `:26`, dans l'ordre. Contenu de `Fixed` laissé au freeze (INFO 1) |
| 11.2.1 | `frontend/package.json` en X.Y.Z | 2 | **Non** (pré-freeze) | `frontend/package.json:3`, `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version SemVer | 2 | Oui | `0.7.3 -> 0.7.4` (INFO 10) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | Oui | 0 `TODO|FIXME|HACK|XXX` dans `document-parser` (hors `.venv`) et `frontend/src` |
| 11.3.2 | Pas de `console.log` de debug | 2 | Oui | 0 `console.log`/`console.debug` ; 2 `console.warn` en `catch` : `frontend/src/features/analysis/store.ts:118`, `:177` |
| 11.3.3 | Pas de `print()` de debug | 2 | Oui | 0 `print(` en début de ligne hors `tests/` |

---

## Ecarts constates

### [CRIT] `[Unreleased]` non figée (attendu pré-freeze)

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : inchangé. Normal tant que le freeze n'est pas fait.
- **Regle violee** : 11.1.1 (poids 3).
- **Remediation** : commit `chore(release): freeze [0.7.4]`, après les retouches de texte des INFO 1 à 3 et N1.

### [MAJ] `frontend/package.json` encore en 0.7.3 (attendu pré-freeze)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Constat** : inchangé.
- **Regle violee** : 11.2.1 (poids 2).
- **Remediation** : `0.7.4` dans les deux fichiers, dans le commit de freeze.

### [INFO] 1. `### Fixed` ne corrige aucun défaut publié (laissé au freeze)

- **Localisation** : `CHANGELOG.md:26-37`
- **Constat** : toujours 10 puces, toutes sur l'éditeur ou le schéma introduits par 0.7.4 (#391-#396), plus #398 (une optimisation). Le report au freeze est un choix délibéré ; l'item 11.1.4 reste conforme comme dans la baseline.
- **Remediation** : au freeze, fondre #392-#396 dans `:11`, passer #391 et #398 sous `### Changed`, supprimer `### Fixed`.

### [INFO] 2. Entrées #401 (réduite)

- **Localisation** : `CHANGELOG.md:17-18`, `:33`
- **Constat** : `:17` et `:18` portent `(#401)`. `:17` annonce le cache mémoire (64 Mo par processus, vrai : `document-parser/infra/preview_cache.py:16`, `bootstrap/builder.py:180`), `format=webp` (vrai : `api/documents.py:154`, `infra/page_raster.py:35-38`) et la contrainte `Range` sur un proxy. Reste : #398 (`:33`, « page previews open the PDF by path ») est toujours une puce séparée sous `Fixed` pour le même sujet.
- **Remediation** : au freeze, fondre `:33` dans `:17` (« (#398, #401) »).

### [INFO] 3. Puces redondantes ou sans numéro autour de l'éditeur (inchangée)

- **Localisation** : `CHANGELOG.md:12-13`, `:19-20`, `:34-37`
- **Constat** : inchangé. Le champ `analysisEditorEnabled` de `/api/health` (`document-parser/main.py:169`) n'est toujours pas cité.
- **Remediation** : comme la baseline.

### [INFO] 4. Rendu PDF dans la doc publiée (réduite)

- **Localisation** : `docs/configuration.md:130-144`, `docs/troubleshooting.md:34-36` ; `docs/design/pdf-loading-performance.md:1-5`
- **Constat** : la doc publiée explique maintenant les plages HTTP, le comportement d'un proxy, le repli, les paramètres de `/preview`, le cache 64 Mo et l'en-tête `Cache-Control` (vérifiés plus bas). Reste : le design doc n'a toujours pas de ligne `Status`.
- **Remediation** : `Status: phase 1 + scrolling follow-up shipped in 0.7.4 (#401); phases 2-3 not started` en tête du design doc.

### [INFO] 5. Fichiers de travail suivis à la racine (inchangée, ex-INFO 9)

- **Localisation** : `analysis_editor_path_to_alpha.md`, `orca.yaml` (tous deux suivis) ; `docs/design/analysis-editor.md:1-3` sans `Status`
- **Remediation** : comme la baseline.

### [INFO] 6. SemVer : un patch qui livre une fonctionnalité, une API et une migration (inchangée, ex-INFO 10)

- **Localisation** : `CHANGELOG.md:7-37`
- **Remediation** : écrire la règle de numérotation dans `docs/maintainers.md`.

### [INFO] 7. Versions secondaires (inchangée, ex-INFO 11)

- **Localisation** : `document-parser/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10` (`0.3.1`)
- **Remediation** : une ligne dans `docs/maintainers.md` sur le placeholder volontaire.

### [INFO] N1. Changement d'aspect de `1516a0c` absent du changelog

- **Localisation** : `CHANGELOG.md:15-24` ; commit `1516a0c` (`frontend/src/shared/breadcrumb/AppBreadcrumb.vue:43-45`, `frontend/src/features/document/ui/BboxCanvas.vue:155-199`, `frontend/src/features/store/ui/StoreForm.vue`, `frontend/src/shared/ui/ComingSoonShell.vue`, `frontend/src/features/chunking/ui/ChunkPanel.vue`)
- **Constat** : le message du commit dit lui-même que l'aspect change : le fil d'Ariane suit maintenant le thème clair, le bouton principal du formulaire de store et le badge « coming soon » passent du bleu à la couleur d'accent, les champs et badges du panneau de chunks ont un fond visible, les numéros d'ordre de lecture du canevas suivent le thème. Le fil d'Ariane et le canevas sont sur les écrans par défaut. Aucune puce. Le commit précise aussi que l'app n'a pas été lancée.
- **Remediation** : sous `### Changed` : « **Theme colours**: every screen takes its colours from the theme. The breadcrumb now follows the light theme, the reading-order badges on the page follow the theme, the store form's main button and the "coming soon" badge use the accent colour, and the chunk panel's fields and badges have a visible background. » Vérifier ces écrans dans un navigateur avant le freeze.

### [INFO] N2. `docs/analysis-editor.md` : trois imprécisions dans la section API

- **Localisation** : `docs/analysis-editor.md:82`, `:83`, `:41`
- **Constat** :
  - `:83` dit `409` quand l'analyse n'est pas terminée ou n'a pas de document Docling. Vrai pour les routes de l'éditeur (`services/analysis_edit_service.py:292-296`, `api/errors.py:20`). Faux pour l'export `edited=true`, qui répond `404` dans ces deux cas (`services/export_service.py:128-133`, `:146-149`).
  - `:82` dit qu'un export `edited=true` sans `analysisId` répond `404`. Vrai pour `md` et `json` (`export_service.py:143-144`). Avec `format=pdf`, le PDF est renvoyé (`export_service.py:85-92` passe avant).
  - `:41` dit que le serveur MCP lit la dernière analyse terminée. Vrai sans ancre ; une ancre `dstudio://` qui épingle une version lit cette version (`services/parse_loader.py:82-87`). Sans effet sur le propos (pas d'édition dans les deux cas).
- **Remediation** : `:83` : « `409` | Another save came first (`expectedAppliedThroughSequence` is stale), or, on an editor route, the analysis is not completed or has no Docling document (an `edited=true` export answers `404` instead). » ; `:82` : « Also an `edited=true` Markdown or JSON export without `analysisId`. » ; `:41` : « …they read the original result of the latest completed analysis that has a Docling document (or the one an MCP anchor pins), even when another analysis is active. »

### [INFO] N3. `docs/configuration.md:140` : « Past the last page: `400` » seulement si le nombre de pages est connu

- **Localisation** : `docs/configuration.md:140` ; `document-parser/services/preview_service.py:56-59`, `:85-88`, `:29`, `:35`
- **Constat** : le `400` n'est levé que si `document.page_count` est renseigné. Sinon poppler ne rend rien et la route répond `404`. Le comptage est fait à l'upload (`services/document_service.py:108-114`), donc le cas courant est bien `400`.
- **Remediation** : « 1 to the page count. Past the last page: `400` (`404` if the page count is unknown). »

### [INFO] N4. Règles de couches : ligne `services` incomplète, docstring de test périmée

- **Localisation** : `docs/architecture.md:73` ; `document-parser/tests/test_architecture.py:186-197`, `:115-116`
- **Constat** : depuis `25f5d8b`, le test interdit aussi aux services `docling`, `docling_core`, `pdf2image`, `pypdfium2`, `httpx`, `neo4j`, `opensearchpy`, `cryptography`, `starlette`. La page ne cite que FastAPI (incomplet, pas faux). Hors doc publiée : la docstring `test_architecture.py:115-116` dit encore que `document_service.py` compte les pages avec pdf2image, ce qui n'est plus vrai (`services/document_service.py:108-114` passe par `self._pdf_inspector.count_pages_in_bytes`).
- **Remediation** : `:73` : « `api`, `infra`, `persistence`, FastAPI, and the Docling, PDF, HTTP and store client libraries » ; corriger la docstring du test.

### [INFO] N5. `docs/maintainers.md:61` cite un script absent du dépôt

- **Localisation** : `docs/maintainers.md:61` ; `.github/workflows/release-gate.yml:194` ; `git ls-files profiles/` vide
- **Constat** : antérieur à ce soir (`ea47a3e`). Le job de la gate lance `bash profiles/fastapi-vue/commands.sh`, qui n'existe pas ; `continue-on-error: true` le rend silencieux. La doc décrit fidèlement le workflow, mais le contrôle annoncé ne tourne pas. Relève aussi de l'audit 10.
- **Remediation** : ajouter le script ou retirer le job et la ligne du tableau.

---

## Vérification des pages écrites pendant la remédiation

V = vrai, F = faux, N = invérifiable ici, V* = vrai avec réserve (INFO N2/N3).

### `docs/configuration.md`

| Ligne | Affirmation | Verdict | Code |
|-------|-------------|---------|------|
| `:30` | `MAX_FILE_SIZE`, défaut `0`, moteur local seulement, en octets | V | `infra/settings.py:218`, `infra/local_converter.py:116-117` |
| `:33` | `MAX_PASTE_IMAGE_SIZE_MB` `10`, `PASTE_ALLOWED_IMAGE_TYPES` ; renvoyés par `/api/health`, lus par aucun écran | V | `infra/settings.py:203-205`, `:244` ; `main.py:153-156` ; aucun usage dans `frontend/src` |
| `:56` | `ANALYSIS_EDITOR_ENABLED=false` : routes éditeur et exports `edited=true` en `404`, éditions sauvées toujours appliquées | V | `api/deps.py:53-61`, `api/documents.py:123-124` ; service construit quel que soit le drapeau `bootstrap/builder.py:127`, `:147`, `:187` |
| `:57` | `INSPECT_MODE_ENABLED=false` renvoie `/docs/{id}` vers la liste ; seulement avec `RAG_PIPELINE_ENABLED` | V | `frontend/src/features/feature-flags/store.ts:103-106`, `:228-232` ; `frontend/src/app/router/index.ts:50-61` |
| `:58` | `LINKED_MODE_ENABLED` renvoyé, lu par aucun écran | V | `main.py:168` ; seul usage frontend : le registre `store.ts:107-110`, jamais consulté |
| `:60` | Au moins un de `RAG_PIPELINE_ENABLED`, `STUDIO_MODE_ENABLED` | V | `infra/settings.py:171` |
| `:101` | `OPENSEARCH_DEFAULT_LIMIT` `1000` | V | `infra/settings.py:240`, `bootstrap/factories.py:349`, `infra/opensearch_store.py:177` |
| `:102` | `DEFAULT_EMBEDDER` `bge-m3`, au premier démarrage, ignoré ensuite | V | `persistence/database.py:342` (`INSERT OR IGNORE`) |
| `:116` | `EMBEDDING_BATCH_SIZE` `64` | V | `embedding-service/main.py:20` |
| `:126-127` | `UPLOAD_DIR`, `DB_PATH` : images et sources | V | `Dockerfile:59-60`, `document-parser/Dockerfile:34-35` ; `infra/settings.py:242-243` |
| `:132` | PDF.js demande des plages sur `GET /api/documents/{id}/export?format=pdf` | V | `frontend/src/features/document/ui/usePdfDocument.ts:28-33` (`rangeChunkSize` 256 Kio, `getExportUrl(id, 'pdf')`) |
| `:132` | Le nginx fourni transmet les plages tel quel | V | `nginx.conf.template:36-43` (aucune règle sur `Range`) ; `FileResponse` `api/documents.py:133-138` |
| `:134` | Un proxy qui retire `Range` : le navigateur télécharge tout | N | comportement de PDF.js, non testé ici |
| `:136` | Repli sur `/preview?page=N&dpi=150&format=webp` si PDF.js échoue | V | `PdfPagePreview.vue:4-16` ; `frontend/src/features/document/api.ts:47-50` |
| `:140` | `page` défaut 1, au-delà : `400` | V* | `api/documents.py:152` ; `services/preview_service.py:56-59` (INFO N3) |
| `:141-142` | `dpi` 72 à 300, défaut 150 ; `format` `png`/`webp`, défaut `png` | V | `api/documents.py:153-154` |
| `:144` | Cache 64 Mo par processus, LRU, non configurable ; `Cache-Control: private, max-age=86400, immutable` | V | `infra/preview_cache.py:16`, `:26`, `:38-40` ; `bootstrap/builder.py:180` (sans argument) ; `api/documents.py:162` |

Toutes les variables lues par `infra/settings.py` sont maintenant citées dans `docs/*.md` (script : 0 manquante).

### `docs/getting-started.md` (« Upgrade », « From 0.7.3 to 0.7.4 »)

| Ligne | Affirmation | Verdict | Code |
|-------|-------------|---------|------|
| `:121` | Données dans `DB_PATH` (`/app/data/docling_studio.db`) et le dossier d'upload | V | `Dockerfile:59-60` |
| `:126` | Commande de sauvegarde, volume `docling-data` | V | même nom que `:28` |
| `:131` | Mise à niveau en place au premier démarrage, rien à réanalyser | V | `persistence/database.py:273-284`, `:314-330` |
| `:133` | Crée les tables nouvelles, dont celles de l'éditeur | V | `CREATE TABLE IF NOT EXISTS` `database.py:88`, `:235`, `:242`, `:258` |
| `:134` | Ajoute deux colonnes à `document_versions` | V | `database.py:292-295` |
| `:135` | Analyse active = dernière terminée, en préférant celle qui a un document Docling | V | `database.py:300-312` |
| `:137` | Étapes idempotentes ; lignes `Upgraded database:` ; `chunk_edits` reste, inutilisée | V | `database.py:320-330` ; aucun `DROP`, la table n'est plus dans le schéma (retirée par `848a64a`) ni dans le code |
| `:139` | Retour en 0.7.3 non supporté | N | aucune preuve à chercher dans le code |
| `:141` | Base antérieure à 0.6.1 non mise à niveau | V | `database.py:8` |

### `docs/analysis-editor.md`

| Ligne | Affirmation | Verdict | Code |
|-------|-------------|---------|------|
| `:18` | Fusion en ordre de lecture, même type, tiret de fin + minuscule supprimé | V | `infra/docling_editor.py:214-221`, `:243-249` ; `frontend/src/features/analysis-editor/commands.ts:57-64`, `:84-91` |
| `:41` | Ask et MCP lisent le résultat d'origine de la dernière analyse terminée avec document Docling | V* | `services/reasoning_service.py:97`, `persistence/analysis_repo.py:114-129` ; `services/parse_loader.py:82-97`, `analysis_repo.py:131-148` (INFO N2) |
| `:65` | Les 6 routes sous `/api/documents/{id}`, `analysisId` optionnel, sinon analyse active | V | `api/analysis_edits.py:105-203` ; `services/analysis_edit_service.py:280-288` |
| `:69-74` | Rôle de chaque route ; `commands`, `expectedAppliedThroughSequence`, `"active"` | V | `api/schemas.py:194-196`, `:217-219` ; `analysis_edit_service.py:157-165`, `:215-249`, `:250-268` |
| `:76` | Export `edited=true` ; sans `edited` : analyse nommée d'origine, ou résultat actif avec éditions | V | `services/export_service.py:114-123`, `:136-149` |
| `:82` | `404` : éditeur coupé, document absent, analyse d'un autre document, pas d'analyse active ; `edited=true` sans `analysisId` | V* | `api/deps.py:53-56` ; `analysis_edit_service.py:274-291` ; `api/errors.py:18` ; `export_service.py:143-144` (INFO N2) |
| `:83` | `409` : sauvegarde concurrente, analyse non terminée ou sans document Docling | V* | `analysis_edit_service.py:170-172`, `:292-296` ; `api/errors.py:19-20` ; export : 404 (INFO N2) |
| `:84` | `400` : édition inapplicable, fusion texte + paragraphe, revert dont dépend une édition | V | `infra/docling_editor.py:221` ; `analysis_edit_service.py:244-249` ; `api/errors.py:21` |

### `docs/architecture.md`

| Ligne | Affirmation | Verdict | Code |
|-------|-------------|---------|------|
| `:8`, `:13` | Navigateur et client MCP passent par nginx sur `/api` et `/mcp` | V | `nginx.conf.template:36`, `:48` |
| `:47-50` (diagramme) | `bootstrap` construit `api` et `mcp_adapter`, qui appellent `services` | V | `main.py:104-127`, `bootstrap/mcp_mount.py:89-91` |
| `:66-68` | Le test liste les exceptions par source et cible | V | `tests/test_architecture.py:66-68` (1 entrée) |
| `:70-77` | Tableau des couches | V (ligne `services` incomplète, INFO N4) | `tests/test_architecture.py:55-62`, `:186-197` |
| `:79` | `/mcp` monté sauf `MCP_ENABLED=false` | V | `bootstrap/mcp_mount.py:89-91` |
| `:88-95` | Préfixes : `/export`, `/preview`, `/pages`, éditeur, `/summaries`, `/import`, `rechunk`, `/api/config/reasoning|mcp`, `GET /api/mcp/server`, `/mcp` | V | `api/documents.py:107`, `:148`, `:178` ; `api/analyses.py:75`, `:107`, `:142-189` ; `api/config.py:32-98` ; `api/mcp.py:16-19` |
| `:124` | `ReasoningRunner`, `infra/docling_agent_reasoning.py`, `domain/trace_builder.py`, `services/reasoning_service.py` | V | fichiers présents ; `domain/ports.py` |
| `:137` | `ANALYSIS_EDITOR_ENABLED` décide de **Edit analysis** | V | `feature-flags/store.ts:111-114`, `:186` |

### Autres pages

| Fichier:ligne | Affirmation | Verdict | Code |
|---------------|-------------|---------|------|
| `docs/troubleshooting.md:34-36` | Plages HTTP, `206`, lien vers la section proxy | V | voir `configuration.md:132` ; ancre vérifiée par script |
| `docs/user-guide.md:104` | Ask lit le résultat d'origine, sans les éditions | V | `services/reasoning_service.py:97` |
| `docs/user-guide.md:125` | « no default screen reaches them » (plus de « 0.7.3 ») | V | inchangé sur le fond |
| `README.md:30`, `:40` | Puce et ligne de tableau pour l'éditeur | V | `docs/analysis-editor.md` existe, dans la nav `mkdocs.yml:38` |
| `CONTRIBUTING.md:66` | Node 22 | V | `frontend/Dockerfile:1`, `Dockerfile:11`, `.github/workflows/ci.yml:61` ; `pdfjs-dist` exige `>=22.13.0` (`frontend/package-lock.json`, entrée `node_modules/pdfjs-dist`) |
| `docs/bbox-pipeline.md:92` | `isPointInRect()` | V | `frontend/src/shared/bboxScaling.ts:52`, `BboxCanvas.vue:220`, `:224` |

### `CHANGELOG.md` `[Unreleased]`, entrées de ce soir

| Ligne | Affirmation | Verdict | Code |
|-------|-------------|---------|------|
| `:17` | Cache 64 Mo par processus, cache navigateur, `format=webp` sans perte, `png` par défaut, proxy et `Range` | V | voir ci-dessus |
| `:23` | `/assets/` en cache un an ; gzip JS, CSS, SVG en plus de JSON | V | `nginx.conf.template:5`, `:26-28` ; avant : `gzip_types application/json` seul (`a6fb539`) |
| `:23` | 1,7 Mo de scripts du viewer | V | `pdf.min.mjs` 474 284 o + `pdf.worker.min.mjs` 1 271 915 o |
| `:23` | Logo, aussi favicon, de 878 ko à 61 ko | V | `frontend/index.html:7` ; `git cat-file -s` : 878 643 -> 61 510 o |
| `:24` | Images construites sur Node 22, `pdfjs-dist` exige 22.13+ | V | voir `CONTRIBUTING.md:66` |

### Identifiants cités dans la doc publiée

Script sur les pages de la nav, `README.md` et `CONTRIBUTING.md` : chaque chemin, fonction `foo()` et identifiant camelCase/snake_case entre backticks est cherché dans le code. Après les renommages de la soirée, **aucun nom périmé**. Restent trois chemins absents du dépôt : `claude_desktop_config.json` et `docker-compose.override.yml` (fichiers de l'utilisateur, normal) et `profiles/fastapi-vue/commands.sh` (INFO N5). `chunk_edits` n'existe plus dans le code, ce que la page dit.

---

## Verifications sans ecart

- **Liens** : script sur `docs/**/*.md` (hors `audit/reports`), `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md` : 110 liens relatifs, 0 cassé dans les pages publiées. Ancres `#behind-your-own-proxy`, `#keep-your-data`, `analysis-editor.md#api` résolues. Seule ancre cassée : `docs/design/329-mcp-investigation-journal-navigation-tree.md` -> `../mcp-server.md#investigations`, page non publiée, antérieure.
- **Nav `mkdocs.yml:34-46`** : les 10 entrées `.md` existent. `mkdocs build --strict` non exécuté (thème `material` absent).
- **Mermaid** : blocs fermés dans toutes les pages (nombre de clôtures pair) ; les deux diagrammes modifiés (`architecture.md:5-28`, `:46-62`) ont des nœuds, arêtes et `class` cohérents. Rendu non vérifié.
- **Versions** : plus aucun « 0.7.3 » dans le texte courant ; les mentions restantes sont la section d'upgrade et un exemple de tag. `SECURITY.md:9` couvre `0.7.x`.
- **Codes HTTP après l'unification** (`437058d`, `25f5d8b`) : `api/errors.py` et les routes donnent les mêmes codes que ceux documentés (au détail près des INFO N2/N3).

---

## Delta vs re-audit a6fb539

| Item | Re-audit (`a6fb539`) | Contrôle (`a12b744`) | Évolution |
|------|----------------------|----------------------|-----------|
| 11.1.1 | CRIT | CRIT | = (pré-freeze) |
| 11.1.2 | OK | OK | = ; deux entrées ajoutées (`:23`, `:24`), une manque (N1) |
| 11.1.3 | OK | OK | = |
| 11.1.4 | OK | OK | = |
| 11.2.1 | MAJ | MAJ | = (pré-freeze) |
| 11.2.2 | OK | OK | = |
| 11.3.1 | OK | OK | = |
| 11.3.2 | OK | OK | = |
| 11.3.3 | OK | OK | = |
| **Score** | **72** (100 au freeze) | **72** (100 au freeze) | **0** |

INFO de la baseline (11) :

| # | Sujet | Statut |
|---|-------|--------|
| 1 | `Fixed` sans défaut publié | inchangée (reportée au freeze, choix délibéré) |
| 2 | #401 sans numéro ni détails | réduite : numéros, cache, WebP, proxy ajoutés ; #398 encore à part |
| 3 | Puces redondantes, `analysisEditorEnabled` non cité | inchangée |
| 4 | Rien de publié sur le rendu PDF | réduite : `configuration.md:130-144`, `troubleshooting.md:34-36` ; design doc sans `Status` |
| 5 | Note d'upgrade seulement dans le changelog | **résolue** : `getting-started.md:119-141` |
| 6 | Deux sections d'interrupteurs, « 0.7.3 » dans le texte, variables non documentées | **résolue** : section unique `configuration.md:50-60`, plus de « 0.7.3 », 7 variables ajoutées |
| 7 | Architecture : `mcp_adapter`, préfixes | **résolue** : `architecture.md:47-50`, `:75`, `:88-95` |
| 8 | README muet sur l'éditeur | **résolue** : `README.md:30`, `:40` |
| 9 | Fichiers de travail à la racine | inchangée |
| 10 | SemVer | inchangée |
| 11 | Versions secondaires | inchangée |

Aucune aggravée. Nouvelles INFO : N1 (aspect de `1516a0c` absent du changelog), N2 (trois imprécisions dans l'API de l'éditeur), N3 (`400` conditionnel), N4 (ligne `services` incomplète, docstring de test périmée), N5 (script de gate absent, antérieur). Total : 7 restantes + 5 nouvelles = 12.

---

## Points positifs

- **Les pages écrites ce soir tiennent après les refactorings qui les ont suivies** : sur plus de 50 affirmations vérifiées, aucune n'est fausse dans le cas courant ; trois demandent une précision.
- **Aucun nom périmé** dans la doc publiée malgré des centaines de renommages ; `bbox-pipeline.md` a suivi `isPointInRect`.
- **La note d'upgrade décrit exactement le code** : colonnes, ordre de choix de l'analyse active, messages de log, `chunk_edits`.
- **Toutes les variables lues par le backend sont documentées.**
- **Le changelog chiffre ses affirmations, et les chiffres sont justes** (64 Mo, 1,7 Mo, 878 -> 61 ko, Node 22.13).
- **0 TODO, 0 `console.log`, 0 `print()`, 0 lien cassé publié.**

---

## Verdict partiel : NO-GO (pré-freeze)

72/100, 1 CRITICAL, 1 MAJOR, tous deux levés par le commit de freeze, qui porte le score à 100 (GO). Avant ce commit : vider `### Fixed` (INFO 1-3), ajouter la puce sur les couleurs (N1), corriger `docs/analysis-editor.md:82-83` et `docs/configuration.md:140` (N2, N3).

### Non vérifiable ici

- Le rendu des pages (`mkdocs` non installé) et des diagrammes Mermaid.
- Le comportement réel de PDF.js derrière un proxy qui retire `Range` (`configuration.md:134`).
- L'aspect des écrans après `1516a0c` (l'app n'a pas été lancée, ni par le commit ni par cet audit).
- Le retour en 0.7.3 sur une base migrée (`getting-started.md:139`).

# Rapport d'audit : Performance & Ressources

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`,
plus `nginx.conf.template` / `frontend/nginx.conf.template` / `frontend/public/`. Examen
approfondi du delta depuis 0.7.2 (`caddf30..02adc68`) : serveur MCP (`mcp_adapter/`,
`mcp_stdio.py`, `bootstrap/mcp_mount.py`, `services/parse_loader.py`, `source_service.py`,
`citation_image_service.py`, `infra/page_raster.py`, `infra/page_text.py`), panneau d'admin MCP,
analyse par lot et polling `GET /api/analyses/summaries` (#354), import d'analyses Docling
(#359), viewer du doc workspace et `GET /api/documents/{id}/pages` (#352), fusion des lots
(#344). Baseline : `reports/release-0.7.0-reaudit/12-performance.md` (86/100).
Methode : analyse statique uniquement (application non lancee, suites de tests non executees).
Les ordres de grandeur non mesures sont marques PLAUSIBLE.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 13 |
| Score | 52 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 6 |
| Ecarts INFO | 6 |

### Detail par item

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 12.1.1 | Pas de requete N+1 (pas de boucle avec requete unitaire) | 2 | Non |
| 12.1.2 | Fichiers uploades temporaires supprimes apres traitement | 2 | Oui |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` configuree et respectee (semaphore) | 2 | Oui |
| 12.1.4 | Operations longues asynchrones, n'occupent pas l'event loop | 3 | Non |
| 12.1.5 | Pas de chargement de fichier entier en memoire sans necessite | 2 | Non |
| 12.2.1 | Watchers Vue avec cleanup | 2 | Oui |
| 12.2.2 | Event listeners supprimes dans `onUnmounted` | 2 | Oui |
| 12.2.3 | Annulation ou debounce des requetes quand pertinent | 1 | Oui |
| 12.2.4 | Pas de re-render excessif (computed plutot que fonctions) | 1 | Oui |
| 12.2.5 | Assets lourds optimises | 1 | Non |
| 12.3.1 | Cache nginx pour les fichiers statiques | 1 | Non |
| 12.3.2 | Reponses API de taille raisonnable | 1 | Non |
| 12.3.3 | Health check leger | 1 | Oui |

Poids total = 21 (12.1 : 2+2+2+3+2 = 11 ; 12.2 : 2+2+1+1+1 = 7 ; 12.3 : 1+1+1 = 3).
Non conformes : 12.1.1 (2) + 12.1.4 (3) + 12.1.5 (2) + 12.2.5 (1) + 12.3.1 (1) + 12.3.2 (1) = 10.
Poids conformes = 11. `score = 11 / 21 * 100 = 52,4` => **52 / 100**.

Delta vs re-audit 0.7.0 : 86 -> 52 (**-34**), 10/13 -> 7/13 items conformes. Detail en
section "Delta vs 0.7.0".

---

## Ecarts constates

### [MAJ] Import d'analyse Docling execute sur l'event loop (#359) — contextualise CRIT -> MAJ

- **Localisation** : `document-parser/services/analysis_service.py:177`
  (`result = self._docling_importer.deserialize(document)`, appel synchrone dans la coroutine
  `import_docling_document`, l.165-189), appele depuis le handler `async`
  `document-parser/api/analyses.py:82` ; travail effectue dans
  `document-parser/infra/docling_importer.py:18-26`.
- **Constat** : `deserialize` enchaine `DoclingDocument.model_validate` (l.18),
  `extract_pages_detail` (l.19), `export_to_markdown()` (l.22), `export_to_html()` (l.23),
  `export_to_dict()` + `json.dumps` (l.26), puis `_finalize_analysis` fait encore
  `json.dumps([asdict(p) ...])` sur l'event loop (`analysis_service.py:464`). C'est exactement
  le post-traitement que le convertisseur local considere comme lourd et execute dans un
  thread (`infra/local_converter.py:127-154` `_to_conversion_result`, appele sous
  `asyncio.to_thread` l.201 et l.204). Ici, rien n'est deporte : pendant toute la duree de
  l'import, l'event loop est occupe et **toutes** les requetes sont figees (polling des
  statuts, previews, `/mcp`, health check, progression des analyses en cours). La duree
  croit avec la taille du document importe, et le corps accepte par nginx monte a 200 Mo
  (`NGINX_MAX_BODY_SIZE=200M`, `Dockerfile:59`, `docker-compose.yml:208`). PLAUSIBLE :
  quelques centaines de ms pour un document de quelques pages, plusieurs secondes pour un
  document de plusieurs centaines de pages.
- **Regle violee** : 12.1.4 (poids 3) — "Les operations longues (conversion Docling) sont
  asynchrones et ne bloquent pas l'event loop". Classe MAJ et non CRIT, comme en 0.5.0 et
  0.6.1 pour le meme item : chemin unique, declenche manuellement, sans corruption de
  donnees ; l'item reste compte non conforme dans le score.
- **Remediation** : `result = await asyncio.to_thread(self._docling_importer.deserialize,
  document)` (une ligne), et deporter de meme la serialisation `pages_json` de
  `_finalize_analysis` (l.464), qui sert aussi aux analyses normales.

### [MAJ] Fichier PDF entier relu en memoire (et recopie sur disque) pour chaque page rendue

- **Localisation** :
  - `document-parser/infra/page_raster.py:27-28` (nouveau, rasters MCP `get_source_page` /
    `get_citation_image`) : `Path(storage_path).read_bytes()` puis `convert_from_bytes(...)`.
  - `document-parser/api/documents.py:185-190` + `services/document_service.py:162`
    (`/preview`, viewer du doc workspace #352) : `read_bytes` puis `convert_from_bytes`.
  - `document-parser/api/documents.py:213-216` + `services/document_service.py:176`
    (nouveau `/pages`, #352) : `read_bytes` puis `pdfium.PdfDocument(file_content)`.
- **Constat** : pour rendre **une** page d'un PDF deja stocke sur disque, le backend charge
  tout le fichier en RAM, puis `convert_from_bytes` le **reecrit integralement** dans un
  fichier temporaire avant d'appeler poppler (`pdf2image/pdf2image.py` de la venv :
  `tempfile.mkstemp()` + `f.write(pdf_file)` + `convert_from_path(f.name, ...)` +
  `os.remove`). Le cout est donc 1 lecture + 1 ecriture + 1 suppression de la taille du PDF
  par page, borne seulement par `MAX_FILE_SIZE_MB` (50 Mo par defaut,
  `infra/settings.py:28`). 0.7.3 multiplie ce chemin : le viewer du doc workspace demarre en
  mode defilement (`PagePreviewWithOverlay.vue:182`) et monte les pages de la fenetre de
  rendu (+/-100 % du viewport, l.372), chacune un `/preview` ; la carte des sources MCP
  feuillette page par page ; et l'echelle de dpi de `CitationImageService._shrink_to_budget`
  re-rend la page depuis zero a chaque palier (`services/citation_image_service.py:89-91`,
  `126-130`), donc relit le fichier a chaque palier. Aucune borne de concurrence sur ces
  rendus.
- **Pourquoi l'item bascule** : le re-audit 0.7.0 jugeait ce chargement "avec necessite"
  car "ces bibliotheques exigent les octets complets". C'est inexact : `convert_from_bytes`
  n'est qu'un wrapper de `convert_from_path`, et pdfium ouvre un chemin — le code de la
  release le fait deja (`infra/page_text.py:32`, `services/analysis_service.py:62`).
- **Regle violee** : 12.1.5 (poids 2) — "Pas de chargement de fichier entier en memoire sans
  necessite (streaming si possible)".
- **Remediation** : `convert_from_path(storage_path, first_page=page, last_page=page,
  dpi=dpi)` dans `page_raster.py` et `generate_preview` ; `pdfium.PdfDocument(path)` dans
  `page_sizes` (sous le verrou pdfium, cf. [MIN] plus bas). Accessoirement, renvoyer l'image
  PIL plutot qu'un PNG que `crop` redecode aussitot (`page_raster.py:31-33` puis l.44).

### [MAJ] Boucles d'ecriture une-requete-par-chunk (carry-over 0.6.2, absent du rapport 0.7.0)

- **Localisation** :
  - `document-parser/services/chunk_service.py:474-486` (`rechunk_document` : par chunk
    existant, `soft_delete` + `_edits.insert`) et `:503-513` (par nouveau chunk, un
    `_edits.insert`).
  - `document-parser/services/chunk_service.py:230-241` (`promote_from_analysis_if_empty`).
  - `document-parser/services/chunk_service.py:836-842` (`_shift_sequences` : un `update`
    par chunk decale lors d'un ajout/split).
  - `document-parser/services/version_service.py:161-173` et `:180-192` (`restore`).
- **Constat** : chaque appel ouvre une connexion aiosqlite neuve (un thread + `PRAGMA
  foreign_keys`) et fait son propre `commit` (`persistence/chunk_repo.py:104-111`,
  `persistence/chunk_edit_repo.py:58-79`, `persistence/database.py:265-280`). Un rechunk ou
  une restauration de version sur un document de N chunks coute donc ~3N connexions et
  ~3N transactions (journal rollback, pas de WAL). PLAUSIBLE : plusieurs secondes pour
  quelques centaines de chunks, et un verrou d'ecriture SQLite repris en boucle pendant que
  les analyses ecrivent leur progression. Ces sites etaient deja signales `[MAJ]` en 0.6.1
  et 0.6.2 ; le re-audit 0.7.0 a declare 12.1.1 conforme apres avoir verifie le seul
  `store_service.py`, mais ces boucles n'ont jamais ete corrigees.
- **Regle violee** : 12.1.1 (poids 2) — "pas de boucle avec requete unitaire".
- **Remediation** : `chunk_repo.soft_delete_many(ids, at)` et `chunk_edit_repo.insert_many(edits)`
  en `executemany` dans **une** transaction (le pattern existe : `chunk_repo.insert_many`) ;
  `_shift_sequences` en un `UPDATE chunks SET sequence = sequence + 1 WHERE document_id = ?
  AND sequence >= ?`.

### [MIN] `show_sources` recharge la meme parse pour chaque citation (nouveau, MCP) — contextualise MAJ -> MIN

- **Localisation** : `document-parser/services/source_service.py:102`
  (`checked = [await self._check(uri, quote) for uri, quote in cited]`) ->
  `services/citation_service.py:99` (`self._parses.load(...)`) ->
  `services/parse_loader.py:78` (`documents.find_by_id`) et `:83`
  (`analyses.parsed_document_id`) ; puis `source_service.py:107` et
  `navigation_service.py:110` rechargent encore deux fois.
- **Constat** : toutes les ancres d'un `show_sources` epinglent la meme `(document, version)`
  (verifie par `_single_pin`, l.266-279), mais chaque citation refait 2 requetes SQL (2
  connexions) pour relire exactement les memes lignes : 2N + 4 connexions par appel. L'index
  lui-meme vient du cache, seules les requetes de resolution sont repetees.
- **Regle violee** : 12.1.1 (poids 2, deja non conforme par l'ecart precedent). Contextualise
  MIN : N est plafonne par `max_source_anchors = 50` (`services/navigation_config.py:60`),
  requetes sur cle primaire, un appel par reponse d'agent.
- **Remediation** : resoudre l'epinglage une fois, charger la parse une fois, et verifier les
  citations contre cette `LoadedParse` (une variante `verify_citation(parse, uri, quote)`),
  puis la passer a `get_outline`.

### [MIN] La bibliotheque d'analyses charge toujours la liste complete (correctif #354 partiel)

- **Localisation** : `frontend/src/features/analysis/store.ts:54` (`load()` ->
  `api.fetchAnalyses()`), appele par `frontend/src/pages/AnalysisLibraryPage.vue:135-138`
  (montage, l.168, et bouton rafraichir, l.8) ; `document-parser/api/analyses.py:90-100` +
  `_to_response` l.25-42 ; `persistence/analysis_repo.py:39-43` (`SELECT aj.*`) et
  `:68-76`. Aussi `frontend/src/pages/DocsLibraryPage.vue:345`
  (`fetchDocumentAnalyses(id)` complet pour n'en garder que `.length`).
- **Constat** : `GET /api/analyses/summaries` existe et le polling l'utilise (bon point),
  mais la page n'affiche que des champs de resume (date, nom, id, statut, progression —
  `AnalysisLibraryPage.vue:45-99`, `features/analysis/progress.ts:15-18`) et charge
  pourtant, a chaque visite et a chaque rafraichissement, la liste lourde : markdown, HTML,
  `pages_json`, `chunks_json` de jusqu'a 200 analyses, `document_json` lu cote DB puis jete.
  La suppression d'un document telecharge de meme tout le contenu de ses analyses pour un
  compte.
- **Regle violee** : 12.3.2 (poids 1).
- **Remediation** : `load()` sur `fetchAnalysisSummaries()` (le type `AnalysisSummary` couvre
  deja tout ce que la page lit) ; pour le compte avant suppression, filtrer les resumes ou
  exposer un compte. `GET /api/analyses` peut alors cesser de renvoyer le contenu.

### [MIN] Logo PNG 1024x1024 (~858 Kio) non optimise, servi en topbar et en favicon

- **Localisation** : `frontend/public/logo.png` (1024x1024, 8-bit RGB, 878 643 octets),
  `frontend/index.html:7`, `frontend/src/app/App.vue:19`, `frontend/src/pages/HomePage.vue:5`,
  `frontend/src/pages/StudioPage.vue:5`.
- **Constat** : inchange depuis 0.7.0. `favicon.svg` (270 octets) toujours present et non
  branche.
- **Regle violee** : 12.2.5 (poids 1).
- **Remediation** : `rel="icon"` sur `favicon.svg`, logo redimensionne/compresse (< ~100 Kio).

### [MIN] Nginx ne configure aucun cache pour les fichiers statiques

- **Localisation** : `nginx.conf.template:13-15` et `frontend/nginx.conf.template:13-15`.
- **Constat** : inchange. Le seul ajout de 0.7.3 aux deux templates est le bloc `location =
  /mcp` (l.26-38). Aucun `expires` / `Cache-Control` pour les assets Vite content-hashes.
- **Regle violee** : 12.3.1 (poids 1).
- **Remediation** : `location ~* \.(js|css|woff2?|png|svg|jpg)$ { expires 1y; add_header
  Cache-Control "public, immutable"; }` et `no-cache` sur `index.html`, dans les deux
  templates.

### [MIN] pdfium appele hors du verrou partage avec Docling (hors checklist, PLAUSIBLE)

- **Localisation** : `document-parser/services/document_service.py:176` (`page_sizes`, nouveau
  #352, execute dans un thread via `api/documents.py:216`) ;
  `document-parser/services/analysis_service.py:59-68` (`_count_pdf_pages`, appele **sur
  l'event loop** a la l.446).
- **Constat** : pypdfium2 n'est pas thread-safe ; le code de la release le dit lui-meme et
  prend le verrou process-wide de Docling dans `infra/page_text.py:7-9, 21-31`. Ces deux
  sites ne le prennent pas. En moteur local, un `/pages` (ouverture d'un doc) ou le
  demarrage d'une analyse du lot (#354) pendant qu'une conversion Docling utilise pdfium
  dans son thread peut faire deux appels pdfium concurrents. Effet PLAUSIBLE : crash natif
  du process backend (toutes les analyses en cours perdues). Non demontre ici.
- **Regle concernee** : concurrence (hors checklist, n'affecte pas le score).
- **Remediation** : envelopper les deux usages dans le meme `_pdfium_lock` que
  `page_text.py` (a factoriser dans `infra/`), et deporter `_count_pdf_pages` sous
  `asyncio.to_thread`.

### [MIN] Le suivi a 3 s n'a pas de borne de duree ; les analyses orphelines le font tourner indefiniment (hors checklist)

- **Localisation** : `frontend/src/features/analysis/store.ts:170-181` (`followActive`) ;
  `frontend/src/features/analysis/batch.ts:11-17` (`hasActive`) ; aucune reconciliation des
  lignes `PENDING`/`RUNNING` au demarrage (`grep` sans resultat dans `bootstrap/`,
  `persistence/`, `main.py`, `services/analysis_service.py`).
- **Constat** : le suivi s'arrete quand plus rien n'est actif et au demontage (bon), mais pas
  sur une duree maximale, contrairement au polling unitaire (`MAX_POLLING_DURATION`, l.31,
  l.125-130). Or les taches d'analyse vivent en memoire (`analysis_service.py:151-161`) : un
  redemarrage du backend pendant un lot laisse des lignes `PENDING`/`RUNNING` pour
  toujours, et la bibliotheque ouverte interroge alors `/summaries` toutes les 3 s sans fin,
  soit 20 req/min sur un budget par IP de 100 req/min (`infra/settings.py:29`), partage avec
  les previews du viewer et `/mcp`.
- **Regle concernee** : hors checklist (ressources), n'affecte pas le score.
- **Remediation** : marquer `FAILED` ("interrompue par un redemarrage") les lignes
  `PENDING`/`RUNNING` au boot ; ajouter un plafond de duree a `followActive`.

### [INFO] Polling des resumes : continue onglet masque, sans garde de requete en vol, re-rend toute la table

- **Localisation** : `frontend/src/features/analysis/store.ts:172-180` ;
  `frontend/src/features/analysis/batch.ts:28-32` ;
  `frontend/src/pages/AnalysisLibraryPage.vue:52, 158-162`.
- **Constat** : pas d'ecoute de `visibilitychange` (le navigateur bride seulement les timers
  d'un onglet masque) ; `setInterval` + callback `async` sans garde, donc des ticks se
  chevauchent si le backend repond en plus de 3 s (cas de l'import ci-dessus) ;
  `mergeSummaries` recree **chaque** ligne (`{ ...analysis, ...summary }`) a chaque tick,
  ce qui re-rend les <= 200 lignes et appelle `formatDate`, qui construit un
  `Intl.DateTimeFormat` par ligne. Borne, d'ou INFO ; 12.2.4 reste conforme.
- **Suggestion** : `setTimeout` chaine apres la reponse, pause sur `document.hidden`, ne
  remplacer que les lignes changees, un formateur `Intl` partage.

### [INFO] `/summaries` : les colonnes legeres sont stockees apres les colonnes lourdes (PLAUSIBLE)

- **Localisation** : `document-parser/persistence/analysis_repo.py:47-52` (`_SELECT_SUMMARY`)
  vs `document-parser/persistence/database.py:67-81` (ordre des colonnes de `analysis_jobs`).
- **Constat** : cote Python, la projection est correcte : colonnes explicites, ni
  `document_json` ni contenus materialises (bon point, reponse a la question "evite-t-on de
  charger `document_json` ?"). Cote SQLite en revanche, `progress_current`, `progress_total`,
  `error_message`, `started_at`, `completed_at`, `created_at` sont stockes **apres**
  `content_markdown`, `content_html`, `pages_json`, `document_json`, `chunks_json`. Pour lire
  une colonne situee apres un contenu en pages de debordement, SQLite parcourt la chaine de
  ces pages : chaque tick a 3 s relit donc probablement depuis le disque (ou le cache OS)
  l'essentiel du contenu des <= 200 analyses, sur une connexion neuve au cache froid. Non
  mesure.
- **Suggestion** : index couvrant `analysis_jobs(created_at, id, document_id, status,
  error_message, progress_current, progress_total, started_at, completed_at)` : la requete
  ne toucherait plus la table. A mesurer avec `EXPLAIN QUERY PLAN` sur une base reelle.

### [INFO] Budgets memoire/CPU du serveur MCP : bornes, mais larges

- **Localisation** : `document-parser/services/navigation_config.py:36-54` ;
  `document-parser/services/parse_loader.py:99-111` ;
  `document-parser/infra/page_raster.py:31-33, 61` ;
  `document-parser/services/citation_image_service.py:72-79`.
- **Constat** : le cache d'index LRU est borne (4 entrees, 24 M caracteres de JSON source),
  mais le code documente qu'un index retient 4 a 15 fois son JSON (l.39-43), soit PLAUSIBLE
  ~100-360 Mo retenus par process au pire. Deux requetes concurrentes sur la meme version non
  cachee construisent chacune l'index (pas de deduplication des chargements en vol). Les
  rasters ne sont pas caches cote serveur (la carte a son propre cache cote client) et leur
  concurrence n'est pas bornee ; chaque rendu encode un PNG, le redecode, puis encode en
  WEBP avec `method=6` (le reglage le plus lent). Tout cela tourne hors event loop.
- **Suggestion** : une `asyncio.Lock`/future par `version_id` en cours de construction ; un
  semaphore sur les rendus ; `method=4`.

### [INFO] Fusion des lots (#344) : pic memoire en fin d'analyse longue

- **Localisation** : `document-parser/services/analysis_service.py:304-340` ;
  `document-parser/infra/local_converter.py:157-180`.
- **Constat** : la fusion est bien deportee (`local_converter.py:204`). Mais tous les
  `ConversionResult` de lot (markdown, HTML, pages, JSON) restent en memoire toute la duree
  de l'analyse (`results.append`, l.329), alors que la fusion n'utilise que leur
  `document_json` ; puis tous les JSON sont parses en `DoclingDocument` simultanement
  (l.173), concatenes, et re-exportes en markdown, HTML et JSON. Pic PLAUSIBLE de quelques
  fois la taille du `document_json` final, en plus du pipeline. Inherent au besoin de
  reconstruire un document unique ; reductible.
- **Suggestion** : ne garder que `document_json` (et la progression) par lot ; liberer
  `documents` apres `concatenate`.

### [INFO] CPU pre-existant sur l'event loop (non releve en 0.7.0)

- **Localisation** : `document-parser/infra/serve_converter.py:136-139` et `:236-258`
  (moteur distant : `response.json()`, `_parse_response`, `json.dumps(json_content)`) ;
  `document-parser/services/analysis_service.py:464` (`pages_json`) ;
  `document-parser/domain/outline_builder.py:51` et `:127-133` (`get_outline` en mode pages :
  pour chaque page, parcours complet de `index.order`).
- **Constat** : travaux proportionnels a la taille du document executes sur l'event loop. Le
  mode pages de l'outline est en O(pages x elements) par appel (plafonne a 200 pages par
  `max_outline_nodes`), et le total de tokens est recalcule a chaque appel alors que l'index
  est cache. Moins lourds que l'import ; PLAUSIBLE de quelques dizaines a quelques centaines
  de ms sur un gros document.
- **Suggestion** : `asyncio.to_thread` pour `_parse_response` et `pages_json` ;
  memoiser dans l'index les couts par element et l'appartenance aux pages.

### [INFO] Observations reportees de 0.7.0, toujours presentes

- **Connexion neuve par appel, pas de WAL** : `persistence/database.py:265-280` (chaque
  `aiosqlite.connect` demarre un thread). Aggrave les deux N+1 ci-dessus.
- **Pas d'`AbortController`** (`grep` sans resultat dans `frontend/src/`) : 12.2.3 reste
  conforme grace aux debounces et aux gardes de requete perimee
  (`DocWorkspacePage.vue:144-174`, `requestedId !== props.id`).
- **Timers a un coup non annules au demontage** : `features/chunks/ui/ChunksEditor.vue:239-249`
  (`saveTimer`, inchange) et `pages/DocsLibraryPage.vue:239-245` (`searchTimer`, qui peut
  appeler `router.replace` apres avoir quitte la page).
- **Upload en memoire** : `api/documents.py:84-90` — les octets arrivent de toute facon par
  le reseau, borne par `MAX_FILE_SIZE_MB` ; reste INFO (seuls les relectures d'un fichier
  deja sur disque passent en MAJ ci-dessus).

---

## Delta vs 0.7.0

| Ecart baseline (0.7.0 initial / re-audit) | Statut a 02adc68 |
|---|---|
| [MAJ] N+1 `StoreService.list_stores` / `list_documents` (leve au re-audit) | **Toujours corrige** : `store_service.py:163` (`count_by_store`), `:361` (`find_by_ids`) |
| [MIN] Logo PNG 858 Kio / favicon (12.2.5) | **Toujours present**, inchange |
| [MIN] Pas de cache nginx (12.3.1) | **Toujours present** ; seul ajout : `location = /mcp` |
| [MIN] Liste des analyses lourde (12.3.2) | **Partiellement corrige** : projection `/summaries` (`analysis_repo.py:47-52`) utilisee par le polling ; la bibliotheque charge encore la liste complete |
| [INFO] Upload / preview en memoire (12.1.5 conforme) | **Requalifie [MAJ]** pour les relectures de fichiers sur disque : pattern etendu par #352 (`/pages`, viewer en defilement) et le MCP (`page_raster.py`), et motif "avec necessite" refute par le code de pdf2image |
| [INFO] Pas de WAL, connexion par appel | **Toujours present** |
| [INFO] Pas d'`AbortController` | **Toujours present** (item conforme) |
| [INFO] `saveTimer` de `ChunksEditor` | **Toujours present** |
| (0.6.2) [MAJ] N+1 `version_service.restore` — non reporte en 0.7.0 | **Jamais corrige** ; reintroduit ici avec les boucles de `chunk_service` (12.1.1) |

Nouveaux ecarts 0.7.3 : import sur l'event loop (#359, 12.1.4), N+1 de `show_sources` (MCP),
pdfium hors verrou (`/pages`), suivi a 3 s sans borne de duree.

Variation de score : -3 (12.1.4, regression #359), -2 (12.1.5, requalification + extension du
pattern), -2 (12.1.1, boucles non corrigees depuis 0.6.2 hors du perimetre verifie au re-audit
0.7.0, plus le nouveau N+1 MCP). 18 -> 11 points conformes : **86 -> 52**.

---

## Points positifs

- **Polling batch bien concu sur l'essentiel (#354)** : une seule requete `/summaries` par
  tick quel que soit le nombre d'analyses (`store.ts:164-181`), projection SQL a colonnes
  explicites (`analysis_repo.py:45-52`), arret quand plus rien n'est actif (`store.ts:179`)
  et au demontage (`AnalysisLibraryPage.vue:169`).
- **Serveur MCP sans etat par session** : `stateless_http=True` (`bootstrap/mcp_mount.py:103-116`),
  donc aucune croissance memoire par session ; `mcp_stdio.py` ne construit que les
  repositories et services utiles (pas de Docling).
- **Parse chargee une fois et cachee** : LRU a double borne (`parse_loader.py:57-58, 123-135`),
  seule la colonne `document_json` est lue (`analysis_repo.py:166-173`, commit `873f4e8`), le
  `json.loads` et la construction d'index sont deportes (`parse_loader.py:105-108`) ; la
  parse survit aux changements de config (`bootstrap/factories.py:255-267`).
- **Pas de N+1 dans la navigation** : `find_documents` = 2 requetes quel que soit le nombre
  (`navigation_service.py:76-99`), `latest_parsed_ids` en une requete fenetree
  (`analysis_repo.py:137-154`).
- **Rasters et couche texte hors event loop** : `citation_image_service.py:72-79`,
  `source_service.py:153-167` (avec memo par page), budget d'octets et echelle de dpi
  (`navigation_config.py:52-54`), WEBP ; `page_text.py` prend le verrou pdfium de Docling.
- **Entrees MCP bornees avant tout travail** : `source_service.py:188-207`,
  `citation_service.py:73-91`, `navigation_config.py:30-62`.
- **Fusion des lots (#344) deportee** : `local_converter.py:203-204`.
- **Viewer du doc workspace (#352)** : fenetre de rendu par `IntersectionObserver`
  (`PagePreviewWithOverlay.vue:365-395`), `loading="lazy"`, observers deconnectes au
  demontage (l.522-525) ; `/pages` ne renvoie que des tailles.
- **Nettoyage frontend des nouveaux composants** : `DocumentActionsMenu.vue:91-92`,
  `AnalysisProgressBar.vue:36-40` ; `AnalysisDetailPage` passe l'analyse a `DocParseTab` au
  lieu de la recharger.
- **Aucune nouvelle dependance frontend** ; les deux apps HTML MCP (~50 Ko) sont lues une fois
  a l'import (`mcp_adapter/apps.py:67`, `sources_view.py:39`).
- **Semaphore et health check inchanges et corrects** : `analysis_service.py:100, 421` ;
  `main.py:129-137` (`SELECT 1` + settings).

---

## Verdict partiel : NO-GO

Score **52/100** (< 60), **0 ecart CRITICAL**, 3 ecarts MAJOR (<= 3, non bloquant en
nombre). Le NO-GO tient au score seul, que la granularite binaire des items amplifie : les
trois MAJ se corrigent en quelques lignes chacun.

1. Deporter `deserialize` sous `asyncio.to_thread` [MAJ 12.1.4] -> +3 => 67 (GO CONDITIONNEL).
2. Passer `page_raster.py`, `generate_preview` et `page_sizes` sur le chemin du fichier
   [MAJ 12.1.5] -> +2 => 76.
3. Ecritures de chunks en `executemany` dans une transaction [MAJ 12.1.1], et parse chargee
   une fois dans `show_sources` [MIN] -> +2 => 86 (GO).

Recommandes au passage, a faible risque : le verrou pdfium sur `page_sizes` et
`_count_pdf_pages` [MIN], la reconciliation au boot des analyses orphelines [MIN], et le
passage de la bibliotheque sur `/summaries` [MIN 12.3.2].

# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` = `release/0.7.4` @ `1de1929` (tag `v0.7.3` + 2 commits README)

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`, plus
`nginx.conf.template` / `frontend/nginx.conf.template` / `frontend/public/`. Baseline :
`reports/release-0.7.3-reaudit/12-performance.md` (67/100, `e01fd95`) ; rapport initial
`reports/release-0.7.3/12-performance.md` (52/100, `02adc68`).

Delta de code depuis la baseline :
- `git diff --stat v0.7.3..HEAD` : `README.md` et deux GIF de `docs/screenshots/` seulement.
- `git diff --stat e01fd95..HEAD` sur `document-parser/`, `frontend/`, templates nginx, `Dockerfile`,
  `docker-compose.yml` : `frontend/src/features/mcp-config/ui/McpConfigSection.vue` (+2/-1, un
  commentaire) et `frontend/src/shared/i18n.ts` (+4/-2, deux libelles). Aucun effet sur cet audit.

**Chaque ecart de la baseline a ete re-verifie ligne a ligne sur `1de1929`** (les numeros de ligne
sont inchanges). L'audit a ensuite ete elargi aux points demandes pour 0.7.4 : appels bloquants dans
les handlers async, N+1, listes non paginees, limites de taille, polling frontend, fuites
(watchers / intervals / listeners / observers). Cela fait apparaitre 1 MIN et 2 INFO nouveaux (code
pre-existant, jamais releve) et une correction de perimetre sur un site du MAJ 12.1.1.

Methode : lecture du code ; tests cibles executes (`tests/test_chunk_service.py`,
`test_version_service.py`, `test_document_service.py`, `test_chunk_repos.py`,
`test_source_service.py` : 111 passed ; `tests/test_api_endpoints.py -k "preview or page_sizes"` :
5 passed) ; mesures indicatives par scripts hors depot (scratchpad, venv du projet, PDF et
DoclingDocument synthetiques), application non lancee. Les ordres de grandeur non mesures sont
marques PLAUSIBLE.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 13 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 7 |
| Ecarts INFO | 9 |

### Detail par item

| # | Item | Poids | 0.7.3 re-audit (e01fd95) | 0.7.4 (1de1929) | Ecarts rattaches |
|---|------|-------|--------------------------|-----------------|------------------|
| 12.1.1 | Pas de requete N+1 / acces DB optimises | 2 | Non | **Non** | [MAJ] ecritures par chunk ; [MIN] `show_sources` ; [MIN] liste des versions (nouveau) |
| 12.1.2 | Fichiers uploades temporaires supprimes | 2 | Oui | **Oui** | — |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` configuree et respectee | 2 | Oui | **Oui** | [INFO] imports hors semaphore |
| 12.1.4 | Operations longues hors event loop | 3 | Oui | **Oui** | [INFO] reliquat CPU (complete : `get_tree`) |
| 12.1.5 | Pas de fichier entier en memoire sans necessite | 2 | Non | **Non** | [MAJ] PDF relu et recopie par page rendue |
| 12.2.1 | Watchers Vue avec cleanup | 2 | Oui | **Oui** | — |
| 12.2.2 | Event listeners supprimes au demontage | 2 | Oui | **Oui** | — |
| 12.2.3 | Annulation ou debounce des requetes | 1 | Oui | **Oui** | [INFO] reports 0.7.0 |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | **Oui** | [INFO] polling des resumes |
| 12.2.5 | Assets lourds optimises | 1 | Non | **Non** | [MIN] logo / favicon |
| 12.3.1 | Cache nginx pour les fichiers statiques | 1 | Non | **Non** | [MIN] pas de cache ; [INFO] pas de compression |
| 12.3.2 | Reponses API de taille raisonnable | 1 | Non | **Non** | [MIN] bibliotheque sur la liste complete |
| 12.3.3 | Health check leger | 1 | Oui | **Oui** | — |

Justification par item (conforme / non conforme) :

- **12.1.1 — Non conforme.** Boucles une-requete-par-chunk dans `rechunk_document`, `restore`,
  `_shift_sequences`, `merge_chunks` (detail en [MAJ]) ; `show_sources` recharge la meme parse par
  citation ; `GET /versions` charge toutes les snapshots pour un `len()`. Le grep de la fiche
  (`for ... in` + `execute` dans `persistence/`) ne renvoie rien : les N+1 sont dans `services/`.
- **12.1.2 — Conforme.** `services/document_service.py:96` supprime le fichier rejete
  (`os.unlink` sous `asyncio.to_thread`) ; `pdf2image` supprime ses temporaires dans un `finally`
  (`.venv/.../pdf2image/pdf2image.py:383-385`, `:662-664`) ; aucun `tempfile` dans le code applicatif
  (`grep tempfile|mkstemp` vide sur `api/ services/ infra/ mcp_adapter/ bootstrap/`).
- **12.1.3 — Conforme.** `infra/settings.py:24`, `:212` (`MAX_CONCURRENT_ANALYSES`, defaut 3, valide
  `:133-135`) ; `bootstrap/factories.py:209` ; `services/analysis_service.py:100`
  (`asyncio.Semaphore`), `:424` (`async with self._semaphore`).
- **12.1.4 — Conforme.** Conversions (`infra/local_converter.py:201`, `:204`), chunker
  (`infra/local_chunker.py:106`), import (`services/analysis_service.py:180`), construction d'index MCP
  (`services/parse_loader.py:108`), rasters (`services/citation_image_service.py:72-79`), previews et
  tailles de page (`api/documents.py:185-190`, `:213-216`), upload (`services/document_service.py:87-89`)
  sont hors loop. Le reliquat (lineaire, d'un ordre de grandeur sous ce que faisait l'import avant
  correction) reste INFO, selon le meme critere qu'au re-audit 0.7.3.
- **12.1.5 — Non conforme.** Voir [MAJ] : chaque page rendue lit tout le PDF puis le recopie.
- **12.2.1 — Conforme.** Watchers de composants arretes avec le composant ; ceux des stores
  singletons (`features/settings/store.ts:27-39`, `shared/breadcrumb/store.ts:41`) vivent le temps de
  l'application, ce qui est voulu ; `useCrumbs` nettoie au demontage (`shared/breadcrumb/store.ts:50-52`).
- **12.2.2 — Conforme.** Tous les `addEventListener` ont leur `removeEventListener` :
  `DocumentActionsMenu.vue:91-92`, `DownloadDropdown.vue:197-203`, `TableModal.vue:46-47`,
  `StudioPage.vue:554-555` / `:680-684` ; observers deconnectes : `PagePreviewWithOverlay.vue:522-525`,
  `BboxCanvas.vue:198`, `BboxOverlay.vue:196` ; intervals arretes : `AnalysisLibraryPage.vue:169`,
  `StudioPage.vue:681`, `AppSidebar.vue:176-178`, `AnalysisProgressBar.vue:36-40`.
- **12.2.3 — Conforme.** Debounce de recherche (`DocsLibraryPage.vue:239-245`), de sauvegarde
  (`ChunksEditor.vue:239-249`), gardes de requete perimee (`DocWorkspacePage.vue:148-173`,
  `requestedId !== props.id`). Pas d'`AbortController` (INFO reporte).
- **12.2.4 — Conforme.** Inchange ; cout du polling des resumes en INFO.
- **12.2.5 — Non conforme.** `frontend/public/logo.png` 1024x1024, 878 643 octets.
- **12.3.1 — Non conforme.** Aucun `expires` / `Cache-Control` dans les deux templates.
- **12.3.2 — Non conforme.** La bibliotheque d'analyses charge encore la liste complete.
- **12.3.3 — Conforme.** `document-parser/main.py:128-137` : `SELECT 1` + lecture des settings,
  exclu du rate limiter (`infra/rate_limiter.py:59`).

Calcul :
- Poids total = 21 (12.1 : 2+2+2+3+2 = 11 ; 12.2 : 2+2+1+1+1 = 7 ; 12.3 : 1+1+1 = 3).
- Non conformes : 12.1.1 (2) + 12.1.5 (2) + 12.2.5 (1) + 12.3.1 (1) + 12.3.2 (1) = 7.
- Poids conformes = 21 - 7 = 14. `score = 14 / 21 * 100 = 66,7` => **67 / 100**.

Delta vs 0.7.3 (re-audit) : **67 -> 67 (=)**, 8/13 -> 8/13 items. Aucun ecart leve, aucun item
bascule. Les deux MAJ sont reconduits sans changement de code ; ils etaient deja signales en 0.6.1 /
0.6.2 (N+1) et en 0.7.3 (relecture du PDF).

---

## Verification des ecarts de la baseline (0.7.3 re-audit)

| Ecart baseline | Statut a 1de1929 | Preuves |
|---|---|---|
| [MAJ] PDF entier relu (et recopie) par page rendue (12.1.5) | **Toujours ouvert** — inchange | `infra/page_raster.py:27-28` ; `api/documents.py:185-190` + `services/document_service.py:162` ; `api/documents.py:213-216` + `services/document_service.py:176` ; echelle de dpi `services/citation_image_service.py:89-91`, `:125-130` |
| [MAJ] Boucles d'ecriture une-requete-par-chunk (12.1.1) | **Toujours ouvert** — inchange ; perimetre corrige (voir [MAJ]) | `services/chunk_service.py:474-486`, `:503-514`, `:427-428`, `:836-842` ; `services/version_service.py:162-173`, `:182-192` ; `persistence/database.py:265-280` |
| [MIN] `show_sources` recharge la parse par citation | Toujours present | `services/source_service.py:102` -> `:182` -> `services/citation_service.py:99` -> `services/parse_loader.py:78`, `:83` ; puis `source_service.py:107`, `navigation_service.py:110` |
| [MIN] Bibliotheque sur la liste complete (12.3.2) | Toujours present | `frontend/src/features/analysis/store.ts:54` ; `pages/AnalysisLibraryPage.vue:135-138`, `:168` ; `pages/DocsLibraryPage.vue:345` ; `document-parser/api/analyses.py:90-100` |
| [MIN] Logo PNG 858 Kio / favicon (12.2.5) | Toujours present | `frontend/public/logo.png` (878 643 o) ; `frontend/index.html:7` |
| [MIN] Pas de cache nginx (12.3.1) | Toujours present | `nginx.conf.template:13-15`, `frontend/nginx.conf.template:13-15` |
| [MIN] pdfium hors verrou (hors checklist) | Toujours present | `services/document_service.py:176` ; `services/analysis_service.py:59-68`, appel sur la loop `:449` |
| [MIN] Suivi a 3 s sans borne de duree (hors checklist) | Toujours present | `frontend/src/features/analysis/store.ts:170-181` vs `MAX_POLLING_DURATION` `:31` ; aucune reconciliation `PENDING`/`RUNNING` au boot (`grep` vide dans `bootstrap/`, `persistence/`, `main.py`, `services/analysis_service.py`) |
| [INFO] Reliquat CPU sur l'event loop | Toujours present ; **complete** (`get_tree`, mesure) | voir INFO |
| [INFO] Imports paralleles hors semaphore | Toujours present | `services/analysis_service.py:165-192` vs `:424` |
| [INFO] Polling des resumes | Toujours present | `store.ts:172-180` ; `batch.ts:24-33` ; `AnalysisLibraryPage.vue:52`, `:158-162` |
| [INFO] `/summaries` colonnes legeres apres les lourdes | Toujours present | `persistence/analysis_repo.py:47-52` vs `persistence/database.py:67-81` |
| [INFO] Budgets memoire/CPU MCP | Toujours present | `services/navigation_config.py:44-54` ; `infra/page_raster.py:31-33`, `:61` |
| [INFO] Fusion des lots | Toujours present | `services/analysis_service.py:332` ; `infra/local_converter.py:173-174` |
| [INFO] Observations reportees de 0.7.0 | Toujours presentes ; complete (petits appels bloquants) | voir INFO |

---

## Ecarts constates

### [MAJ] Fichier PDF entier relu en memoire, puis recopie sur disque, pour chaque page rendue — statut vs 0.7.3 : inchange (ouvert depuis 0.7.3)

- **Localisation** (call sites exacts) :
  1. Rasters MCP — `document-parser/infra/page_raster.py:26-28` :
     `content = Path(storage_path).read_bytes()` puis `convert_from_bytes(content, first_page=page,
     last_page=page, dpi=dpi)`. Appele par `services/citation_image_service.py:90` (closure `render`,
     l.89-91), elle-meme rejouee a chaque palier de l'echelle de dpi (`_shrink_to_budget`, l.125-130).
     Points d'entree : outils MCP `get_citation_image` (`mcp_adapter/apps.py:206`) et
     `get_source_page` (`mcp_adapter/sources_view.py:204-206`).
  2. `GET /api/documents/{id}/preview` — `document-parser/api/documents.py:185-190` (lecture des
     octets sous `to_thread`, puis `DocumentService.generate_preview`) ->
     `services/document_service.py:162` (`convert_from_bytes`). Appele par le viewer du doc
     workspace (`frontend/src/features/document/ui/PagePreviewWithOverlay.vue:96-104`, mode defilement
     par defaut l.182, fenetre de rendu +/-100 % du viewport l.372), `PagePreview.vue:32-33`,
     `StructureViewer.vue:125`, `StudioPage.vue:617`.
  3. `GET /api/documents/{id}/pages` — `api/documents.py:213-216` ->
     `services/document_service.py:176` (`pdfium.PdfDocument(file_content)`, en memoire). Appele a
     chaque ouverture du doc workspace (`frontend/src/pages/DocWorkspacePage.vue:167`).
  4. Meme motif a l'upload (une fois par document, nouveau dans ce rapport) —
     `services/document_service.py:202` -> `:208` (`pdfinfo_from_bytes(file_content)`) : le fichier
     tout juste ecrit en `file_path` (l.199-201) est reecrit integralement dans un temporaire par
     pdf2image (`pdf2image.py:647-664`) pour compter les pages.
- **Constat** : `convert_from_bytes` n'est qu'un wrapper : `tempfile.mkstemp()` + `f.write(pdf_file)`
  + `convert_from_path(f.name, ...)` + `os.remove` (`.venv/.../pdf2image/pdf2image.py:354-385`), et
  `convert_from_path` lance en plus un sous-processus `pdfinfo` avant `pdftoppm` (`:127`). Pour une
  page, le backend fait donc : 1 lecture complete + 1 ecriture complete + 1 suppression du PDF +
  2 sous-processus. Borne seulement par `MAX_FILE_SIZE_MB` = 50 (`infra/settings.py:28`). Aucune
  borne de concurrence sur ces rendus (`grep Semaphore` : seul `analysis_service.py:100`), aucun
  cache serveur, et `/preview` ne pose aucun en-tete de cache HTTP (`api/documents.py:191`).
- **Mesure indicative** (PDF synthetique de 17 pages, 48,2 Mo, page 9 a 150 dpi, mediane de 5) :

  | Variante | Temps | RSS max du process |
  |----------|-------|--------------------|
  | actuelle (`read_bytes` + `convert_from_bytes`) | 468 ms | 114 Mio |
  | `convert_from_path(path)` | 407 ms | 68 Mio |
  | pypdfium2 par chemin (`PdfDocument(path)` + `render`) | 352 ms | 74 Mio |
  | `page_sizes` actuel (octets) | 38 ms | 312 Mio |
  | `page_sizes` par chemin | 13 ms | 88 Mio |

  Le surcout pur lecture + copie temporaire est de 69 ms et 48 Mo ecrits sur disque **par page**
  (`pdfinfo` : 9 ms). Le viewer monte plusieurs pages a la fois (fenetre de rendu) et l'echelle
  de dpi MCP re-rend 1 a 3 fois : PLAUSIBLE 150-500 Mo d'ecritures temporaires pour afficher un
  ecran de pages d'un gros PDF, et autant de copies resident simultanement en RAM.
- **Regle violee** : 12.1.5 (poids 2) — "Pas de chargement de fichier entier en memoire sans
  necessite". Le fichier est deja sur disque ; le chemin suffit, et le code le fait deja ailleurs
  (`infra/page_text.py:31-32`, `services/analysis_service.py:62`).
- **Remediation proposee** (par etapes, chacune autonome) :
  1. **Ouvrir par chemin, sans copie (S, risque faible).**
     - `infra/page_raster.py:27-28` -> `images = convert_from_path(storage_path, first_page=page,
       last_page=page, dpi=dpi)` (import `convert_from_path`, retirer `Path.read_bytes`).
     - `DocumentService.generate_preview(path: str | Path, page, dpi)` avec `convert_from_path` ;
       call site `api/documents.py:185-190` : un seul `to_thread` qui recoit
       `service.resolve_storage_path(doc.storage_path)` (supprimer le `read_bytes`).
     - `DocumentService.page_sizes(path)` -> `pdfium.PdfDocument(str(path))` **sous le verrou pdfium**
       partage avec Docling ; factoriser `_pdfium_lock` de `infra/page_text.py:21-24` dans un module
       `infra/pdfium_lock.py` reutilise par `page_text.py`, `page_sizes` et `_count_pdf_pages` (ce qui
       ferme aussi le [MIN] "pdfium hors verrou"). Call site `api/documents.py:213-216`.
     - Upload : `_count_pages(file_path)` avec `pdfinfo_from_path` (`services/document_service.py:202`,
       `:208`).
  2. **Cache HTTP sur `/preview` et `/pages` (S, risque faible).** Le PDF d'un `doc_id` n'est jamais
     reecrit : `Response(..., headers={"Cache-Control": "private, max-age=86400"})` sur
     `api/documents.py:191` et `:222-224` (plus un `ETag` = `doc_id:page:dpi` si l'on veut la
     revalidation). Evite les re-rendus serveur au re-montage d'une page (voir [INFO] dedie).
  3. **Cache serveur borne + rendu unique par vignette (M, risque moyen).**
     - Dans `CitationImageService._page_thumbnail` : rendre une fois au dpi demande, puis reduire
       l'image PIL (`Image.reduce` / `resize`) pour les paliers suivants au lieu de re-rasteriser
       (`services/citation_image_service.py:89-91`, `:125-130`) ; faire renvoyer l'image PIL par le
       port plutot qu'un PNG aussitot redecode par `crop` (`page_raster.py:31-33` puis `:44`).
     - LRU borne en octets (meme patron que `ParseLoader._evict`, `services/parse_loader.py:123-135`),
       cle `(storage_path, mtime, page, dpi)`, ~32-64 Mio, cote adaptateur `PdfPageRasterizer` et
       `generate_preview`.
     - `asyncio.Semaphore` (2-4) autour des rendus pour borner les sous-processus poppler
       simultanes.
  - Variante a l'etape 1 : rendu pypdfium2 par chemin (`PdfDocument(path)[page - 1].render(scale=dpi
    / 72).to_pil()`), -2 sous-processus par page (352 ms vs 407 ms mesures). Risque moyen : prise du
    verrou pdfium partage avec les conversions Docling (latence des previews pendant une analyse
    locale), rendu legerement different de poppler (anticrenelage, polices) a valider sur les
    overlays.
- **Tests existants qui couvrent ces chemins** :
  - `tests/test_document_service.py:112-132` (`TestPageSizes`, appelle `page_sizes` avec des
    **octets** issus de `pdf_with_pages`, l.101-109) et `:134-152` (`TestGeneratePreview`, patche
    `services.document_service.convert_from_bytes`) : **a adapter** (chemin `tmp_path`, patch de
    `convert_from_path`) ; `:154-167` (`TestCountPages`, patche `pdfinfo_from_bytes`) idem.
  - `tests/test_api_endpoints.py:209-221` (preview hors bornes) et `:223-263` (`/pages` sur de vrais
    fichiers `tmp_path`, document absent, fichier manquant, PDF illisible) : restent valides.
  - E2E : `e2e/api/src/test/resources/documents/preview.feature` (4 scenarios : PNG page 1, dpi 72,
    hors bornes, document inconnu) ; `e2e/ui/src/test/resources/documents/doc-viewer.feature:17-24`
    (`/pages` puis `preview-page-1`) ; `e2e/ui/.../documents/upload.feature`.
  - Rasters MCP : `tests/test_navigation_service.py:537-597` et `tests/test_mcp_apps.py:112-139`
    passent par le faux `BlankRasterizer` (`tests/navigation_fixtures.py:330-360`) et couvrent
    l'echelle de dpi, pas l'adaptateur. **`PdfPageRasterizer` n'a aucun test unitaire direct**
    (`grep PdfPageRasterizer|page_raster tests/` : seulement une docstring de
    `test_architecture.py:211`) : en ajouter un sur un PDF reel (`pdf_with_pages`) avant de le
    modifier.
- **Effort** : S (etapes 1-2, ~30 lignes + adaptation de 4 tests) ; M (etape 3).
  **Risque de regression** : faible pour 1-2 (meme moteur poppler, meme sortie ; seul le contrat
  d'entree des deux methodes statiques change) ; moyen pour 3 (cache a invalider si un fichier est
  remplace, qualite des paliers reduits) et pour la variante pdfium.

### [MAJ] Ecritures de chunks une-requete-par-chunk, une connexion et un commit chacune — statut vs 0.7.3 : inchange (carry-over 0.6.2) ; perimetre corrige

- **Localisation** (call sites exacts, chemins de production) :
  - `document-parser/services/chunk_service.py:472-486` (`rechunk_document`) : pour chaque chunk vivant,
    `soft_delete` (l.475) + `_edits.insert` (l.476) ; puis `:502-514` : `insert_many` (une
    transaction, bon) suivi d'un `_edits.insert` **par** nouveau chunk (l.503-514). Route
    `POST /api/documents/{id}/rechunk` (`api/document_chunks.py:165`), appelee par le bouton
    "Generate chunks" (`frontend/src/features/document/api.ts:61-67`).
  - `document-parser/services/version_service.py:160-173` (`restore`) : `soft_delete` + `_edits.insert`
    par chunk vivant ; `:180-192` : un `_edits.insert` par chunk restaure. Route
    `POST /api/documents/{id}/versions/{vid}/restore` (`api/document_versions.py:75`).
  - `document-parser/services/chunk_service.py:836-842` (`_shift_sequences`) : un `update` complet
    (texte, JSON des bboxes / doc_items re-serialises) par chunk decale ; appele par `add_chunk`
    (l.259, route `api/document_chunks.py:88`) et `split_chunk` (l.368, route `:132`).
  - `document-parser/services/chunk_service.py:427-428` (`merge_chunks`) : un `soft_delete` par chunk
    fusionne (N = taille de la selection ; route `:145`).
  - Primitives : `persistence/chunk_repo.py:81-102` (`update`), `:104-111` (`soft_delete`),
    `persistence/chunk_edit_repo.py:58-79` (`insert`) ; chacune ouvre une connexion aiosqlite neuve
    (un thread + `PRAGMA foreign_keys`) et `commit` : `persistence/database.py:265-280`. Aucun
    `journal_mode=WAL` ni `synchronous` (seul PRAGMA : `database.py:269`).
  - **Correction de perimetre** : `promote_from_analysis_if_empty`
    (`services/chunk_service.py:229-241`), liste comme site actif en 0.7.3, **n'est plus appele en
    production** : le hook est cable (`bootstrap/builder.py:137`, `services/analysis_service.py:113`,
    `:126`) mais jamais invoque (`analysis_service.py:513-520` ; `grep _chunk_promoter` sans appel).
    Seuls les tests l'executent. A traiter avec le meme `insert_many` des editions, ou a supprimer.
- **Constat** : un rechunk ou une restauration d'un document de N chunks coute 3N connexions et 3N
  commits (journal rollback, fsync par commit) ; un ajout en tete d'un document de N chunks, N+2.
  **Mesure indicative** (base SQLite temporaire, vrais repositories du projet, schema `init_db`) :
  N soft-deletes + N editions DELETE = **626 ms pour N=100, 3 043 ms pour N=500** ; les memes
  ecritures en deux `executemany` dans une transaction = **6 ms et 14 ms** (x100 a x200). Un rechunk
  de 500 chunks passe donc PLAUSIBLE ~4,5 s dans ces boucles (DELETE + INSERT d'audit), pendant
  lesquelles le verrou d'ecriture SQLite est repris 1 500 fois et entrelace avec les ecritures de
  progression des analyses. L'event loop n'est pas bloque (SQL dans le thread aiosqlite) : c'est
  la latence de la requete et la contention d'ecriture qui sont en cause.
- **Effet de bord d'integrite** : la docstring du repo affirme "audit + chunk write happen in the same
  SQL transaction" (`persistence/chunk_edit_repo.py:52-56`) ; c'est faux aujourd'hui (connexions
  separees). Une erreur au milieu de la boucle laisse un chunkset a moitie supprime sans retour
  arriere. La remediation ci-dessous rend la promesse vraie.
- **Regle violee** : 12.1.1 (poids 2) — "pas de boucle avec requete unitaire".
- **Remediation proposee** :
  1. Repository batch, **une connexion, une transaction** (patron existant :
     `persistence/chunk_repo.py:74-79` `insert_many`) :
     - `SqliteChunkRepository.replace_chunkset(document_id, *, retire_ids: list[str], at,
       add: list[Chunk], edits: list[ChunkEdit])` : `executemany("UPDATE chunks SET deleted_at = ?,
       updated_at = ? WHERE id = ?")` + `executemany(_INSERT_SQL)` + `executemany(INSERT INTO
       chunk_edits ...)` puis **un** `commit` (rollback sur exception).
     - `SqliteChunkRepository.shift_sequences(document_id, from_sequence, at)` :
       `UPDATE chunks SET sequence = sequence + 1, updated_at = ? WHERE document_id = ? AND
       deleted_at IS NULL AND sequence >= ?` (l'index `idx_chunks_doc_seq` n'est pas UNIQUE,
       `persistence/database.py:154` : pas de conflit transitoire).
     - `SqliteChunkEditRepository.insert_many(edits)` pour `promote_from_analysis_if_empty`.
     - Ajouter ces methodes aux ports `domain/ports.py:158-179` (`ChunkRepository`) et `:181-195`
       (`ChunkEditRepository`).
  2. Call sites : `rechunk_document` (`chunk_service.py:472-514`) et `restore`
     (`version_service.py:160-192`) construisent les listes en memoire puis appellent
     `replace_chunkset` une fois ; `_shift_sequences` (`chunk_service.py:836-842`) devient un appel
     a `shift_sequences` ; `merge_chunks` (`:427-429`) et `split_chunk` (`:368-370`) passent par
     `replace_chunkset` (retire + ajoute + edition dans la meme transaction).
  3. Optionnel, gain transversal : `PRAGMA journal_mode=WAL` une fois dans `init_db`
     (`persistence/database.py:233-236`) — lectures concurrentes des ecritures, commit moins couteux.
- **Tests existants qui couvrent ces chemins** :
  - `tests/test_chunk_service.py:126-139` (ajout apres ancre : decalage des sequences), `:214-227`
    (split : decalage), `:229-257` (merge, contiguite, minimum 2), `:265-334` (rechunk : remplace le
    chunkset, preserve `doc_items`, 409/503), `:341-380` (promotion, dont le compte d'editions INSERT
    l.354-355), `:151-192` (audit d'update / delete).
  - `tests/test_version_service.py:97-129` (`TestRestore`).
  - `tests/test_chunk_repos.py:51-112` (`TestChunkRepo`, dont `insert_many` l.71, soft delete l.82,
    update l.93) et `:114-182` (`TestChunkEditRepo`).
  - `tests/test_document_chunks_api.py:156-170` (rechunk via un service mocke).
  - **Manques** : ni le rechunk ni la restauration n'asserent les lignes d'audit produites (nombre
    d'editions DELETE / INSERT, acteur `system:rechunk` / `system:restore:<id>`) ; aucun test
    d'atomicite. A ajouter avant le refactoring : compte d'editions par action apres rechunk et
    restore, et un test ou l'echec d'une insertion laisse le chunkset intact.
- **Effort** : M (3 methodes de repo + ports + 5 call sites + tests). **Risque de regression** :
  moyen — le journal d'audit doit rester identique (memes actions, acteurs, horodatages, `before` /
  `after`), et l'ordre des sequences apres `shift_sequences` doit egaler l'actuel ; couverts en
  partie par les tests ci-dessus, a completer comme indique.

### [MIN] `show_sources` recharge la meme parse pour chaque citation — statut vs 0.7.3 : inchange

- **Localisation** : `document-parser/services/source_service.py:102`
  (`checked = [await self._check(uri, quote) for uri, quote in cited]`) -> `:182`
  (`self._citations.verify_citation`) -> `services/citation_service.py:99` (`self._parses.load`) ->
  `services/parse_loader.py:78` (`documents.find_by_id`) et `:83` (`analyses.parsed_document_id`) ;
  puis `source_service.py:107` et `services/navigation_service.py:110` rechargent encore.
- **Constat** : 2N + 4 connexions par appel pour relire les memes lignes (l'index vient du cache) ;
  N plafonne a 50 (`services/navigation_config.py:60`).
- **Regle violee** : 12.1.1 (poids 2, deja non conforme), contextualise MIN.
- **Remediation** : resoudre l'epinglage et charger la parse une fois dans `SourceService.show`, puis
  une variante `verify_citation_in(parse, uri, quote)` ; passer la `LoadedParse` a `get_outline`.
  Tests : `tests/test_source_service.py`, `tests/test_mcp_sources_app.py`. Effort S-M, risque faible.

### [MIN] `GET /api/documents/{id}/versions` charge toutes les snapshots pour les compter — nouveau (pre-existant, #267)

- **Localisation** : `document-parser/persistence/document_version_repo.py:65-73` (`SELECT * FROM
  document_versions WHERE document_id = ? ORDER BY created_at DESC`, sans `LIMIT`) ;
  `document-parser/api/document_versions.py:29-34` (`len(json.loads(version.chunks_snapshot))` par
  version, sur l'event loop) et `:59`. Appele a chaque ouverture du doc workspace et apres chaque
  analyse / rechunk (`frontend/src/features/document/store.ts:140-143`, `:166`).
- **Constat** : chaque analyse et chaque rechunk ajoutent une version contenant **tout** le chunkset
  serialise (`services/version_service.py:114-124`, `:135-145`), sans retention. La liste lit toutes
  ces snapshots depuis SQLite, les materialise en Python et les parse une a une sur la loop, pour
  n'en renvoyer que le nombre d'elements. Mesure indicative : 20 versions de 500 chunks = 14,2 Mo
  parses en **55 ms sur la loop**, a chaque ouverture du workspace ; croissance non bornee.
- **Regle violee** : 12.1.1 (poids 2, deja non conforme) — acces DB non optimise ; contextualise MIN
  (lineaire, quelques dizaines de ms au volume mesure).
- **Remediation** : projection sans la colonne lourde, compte calcule par SQLite :
  `SELECT id, document_id, kind, analysis_id, summary, created_at,
  json_array_length(chunks_snapshot) AS chunks_snapshot_size ...` (ou une colonne `chunk_count`
  ecrite a l'insertion), plus un `LIMIT` (le tiroir n'affiche que l'historique recent).
  Tests : `tests/test_version_service.py:132-145` (`TestListForDocument`). Effort S, risque faible.

### [MIN] La bibliotheque d'analyses charge toujours la liste complete — statut vs 0.7.3 : inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:54` (`api.fetchAnalyses()`), appele par
  `frontend/src/pages/AnalysisLibraryPage.vue:135-138` (montage l.168, bouton l.8) ;
  `document-parser/api/analyses.py:90-100` + `_to_response` l.25-42 (markdown, HTML, `pages_json`,
  `chunks_json`) ; `persistence/analysis_repo.py:39-43` (`SELECT aj.*`, `document_json` lu puis
  jete) ; `frontend/src/pages/DocsLibraryPage.vue:345` (liste complete d'un document pour un
  `.length`).
- **Regle violee** : 12.3.2 (poids 1).
- **Remediation** : `load()` sur `fetchAnalysisSummaries()` (`features/analysis/api.ts:51-53`, le type
  `AnalysisSummary` couvre ce que la page lit) ; un compte (ou le filtrage des resumes) avant
  suppression. Effort S, risque faible (tests `features/analysis/*.test.ts` a ajuster).

### [MIN] Logo PNG 1024x1024 (~858 Kio) non optimise, servi en topbar et en favicon — statut vs 0.7.3 : inchange

- **Localisation** : `frontend/public/logo.png` (1024x1024, RGB, 878 643 octets) ;
  `frontend/index.html:7` (`rel="icon"` sur `/logo.png`) ; `favicon.svg` (270 octets) toujours non
  branche.
- **Regle violee** : 12.2.5 (poids 1).
- **Remediation** : `rel="icon" type="image/svg+xml" href="/favicon.svg"` ; logo redimensionne
  (256 px suffisent en topbar) et compresse (< ~100 Kio). Effort S, risque nul.

### [MIN] Nginx ne configure aucun cache pour les fichiers statiques — statut vs 0.7.3 : inchange

- **Localisation** : `nginx.conf.template:13-15` et `frontend/nginx.conf.template:13-15`.
- **Constat** : aucun `expires` / `Cache-Control` pour les assets Vite a empreinte de contenu.
- **Regle violee** : 12.3.1 (poids 1).
- **Remediation** : dans les deux templates, `location /assets/ { expires 1y; add_header
  Cache-Control "public, immutable"; }` et `add_header Cache-Control "no-cache"` sur `index.html`
  (attention : un `add_header` dans un `location` masque ceux du niveau `server`, l.8-11 — les
  repeter). Effort S, risque faible (verifier le smoke test du gate).

### [MIN] pdfium appele hors du verrou partage avec Docling (hors checklist, PLAUSIBLE) — statut vs 0.7.3 : inchange

- **Localisation** : `document-parser/services/document_service.py:176` (`page_sizes`) ;
  `document-parser/services/analysis_service.py:59-68` (`_count_pdf_pages`, appele **sur l'event
  loop** a la l.449).
- **Constat** : le verrou process-wide de `infra/page_text.py:21-24`, `:31` n'est pas pris ; crash
  natif PLAUSIBLE en moteur local. N'affecte pas le score.
- **Remediation** : verrou factorise (`infra/pdfium_lock.py`, cf. [MAJ] 12.1.5 etape 1) ;
  `_count_pdf_pages` sous `asyncio.to_thread`. Effort S.

### [MIN] Le suivi a 3 s n'a pas de borne de duree (hors checklist) — statut vs 0.7.3 : inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:170-181` (`followActive`) vs
  `MAX_POLLING_DURATION` l.31 ; aucune reconciliation au boot des lignes `PENDING` / `RUNNING`
  (taches d'analyse en memoire, `services/analysis_service.py:101`, `:151-161`).
- **Constat** : un redemarrage pendant un lot laisse des lignes actives pour toujours ; la
  bibliotheque ouverte interroge alors `/summaries` toutes les 3 s sans fin (20 req/min sur un budget
  de 100 req/min, `infra/settings.py:29`).
- **Remediation** : marquer `FAILED` les analyses `PENDING` / `RUNNING` au demarrage (lifespan) ;
  plafond de duree sur `followActive`. N'affecte pas le score.

### [INFO] Reliquat CPU sur l'event loop — statut vs 0.7.3 : inchange, complete (`get_tree`)

- **Localisation** :
  - `services/analysis_service.py:467` (`pages_json`, toutes les analyses et l'import).
  - `infra/neo4j/tree_writer.py:84-91` (pretraitement de l'arbre, seulement si Neo4j est branche).
  - `infra/serve_converter.py:137` et `:236-258` (moteur distant : `response.json()`,
    `_parse_response`, `json.dumps`).
  - `domain/outline_builder.py:51` et `:125-133` (`get_outline` en mode pages, O(pages x elements)).
  - **Nouveau** : `services/chunk_service.py:789-810` (`GET /api/documents/{id}/tree`,
    `api/document_chunks.py:171-182`, appele par `frontend/src/pages/DocParseTab.vue:329`) :
    `json.loads(job.document_json)` (l.806) puis `_build_tree_nodes` (l.810) sur la loop ; de plus
    `find_by_id` / `find_latest_completed_by_document` (l.798, l.802) chargent markdown, HTML,
    `pages_json` et `chunks_json` pour n'utiliser que `document_json`.
- **Constat** : travaux lineaires en taille de document. Mesure indicative de `get_tree` sur un
  DoclingDocument synthetique : **4 ms** pour 20 pages (0,8 Mo) ; **212 ms** pour 500 pages x 40
  elements (20 Mo). Meme ordre que `pages_json` ; 12.1.4 reste conforme (critere du re-audit 0.7.3).
- **Suggestion** : `asyncio.to_thread` pour `get_tree` (parse + projection) et `pages_json` ;
  lire seulement `document_json` via `analysis_repo.parse_json` (`persistence/analysis_repo.py:166-173`)
  apres un controle d'appartenance leger ; memoiser couts et appartenance aux pages dans l'index MCP.

### [INFO] `/preview` et `/pages` sans en-tete de cache HTTP, sous un rate limit de fait global (nouveau)

- **Localisation** : `document-parser/api/documents.py:191` et `:222-224` (aucun `Cache-Control`,
  `ETag` ni `Last-Modified`) ; `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:97`
  (`v-if="shouldRenderPage(...)"`), `:268-274`, `:385-396` (une page sortie de la fenetre de rendu
  perd son `<img>`) ; `document-parser/main.py:96-101`, `infra/rate_limiter.py:59`, `:71`.
- **Constat** : le contenu d'une page est immuable pour un `(doc_id, page, dpi)`, mais rien ne le dit
  au navigateur. Au re-montage d'une page ou au rechargement, un nouveau rendu serveur est PLAUSIBLE
  (le cache d'images du document peut l'eviter dans la meme session, non verifie). Toutes les
  previews comptent dans le rate limit de 100 req/min (`infra/settings.py:29`), qui est de fait global
  derriere nginx (ecart [MIN] de l'audit 08 : `request.client.host`) : PLAUSIBLE qu'un defilement
  rapide d'un document de plus de ~100 pages renvoie des 429, pour tous les utilisateurs.
- **Suggestion** : en-tetes de cache (cf. [MAJ] 12.1.5 etape 2) ; correction de la cle du rate
  limiter (audit 08).

### [INFO] Aucune compression HTTP configuree (nouveau, PLAUSIBLE sur l'effet)

- **Localisation** : `nginx.conf.template`, `frontend/nginx.conf.template` (`grep gzip` vide) ;
  `document-parser/main.py` (pas de `GZipMiddleware`).
- **Constat** : la compression depend donc de la configuration par defaut de l'image nginx (Debian
  pour l'image unique, `Dockerfile:30` ; `nginx:alpine` pour `frontend/Dockerfile:9`), ou elle est
  au mieux limitee a `text/html` (PLAUSIBLE, non verifie dans les images). Les bundles JS/CSS et les
  JSON d'analyse (markdown, HTML, `pages_json`) partent alors non compresses.
- **Suggestion** : `gzip on; gzip_types application/json application/javascript text/css
  image/svg+xml; gzip_proxied any;` dans les deux templates (a joindre a la correction 12.3.1).

### [INFO] Imports paralleles, hors du semaphore d'analyse — statut vs 0.7.3 : inchange

- **Localisation** : `services/analysis_service.py:165-192` ; le semaphore n'entoure que
  `_run_analysis` (l.424). Corps accepte jusqu'a 200 Mo (`Dockerfile:61`, `docker-compose.yml:208`),
  `document: dict` sans plafond applicatif (`api/schemas.py:272-276`).
- **Suggestion** : `deserialize` sous `self._semaphore` (ou un semaphore d'import a 1).

### [INFO] Polling des resumes : continue onglet masque, sans garde de requete en vol, re-rend toute la table — statut vs 0.7.3 : inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:172-180` ;
  `frontend/src/features/analysis/batch.ts:24-33` ; `frontend/src/pages/AnalysisLibraryPage.vue:52`,
  `:158-162` (un `Intl.DateTimeFormat` construit par ligne).
- **Suggestion** : `setTimeout` chaine apres la reponse, pause sur `document.hidden`, formateur partage.

### [INFO] `/summaries` : les colonnes legeres sont stockees apres les colonnes lourdes (PLAUSIBLE) — statut vs 0.7.3 : inchange

- **Localisation** : `persistence/analysis_repo.py:47-52` vs `persistence/database.py:67-81`.
- **Suggestion** : index couvrant, a valider par `EXPLAIN QUERY PLAN`.

### [INFO] Budgets memoire/CPU du serveur MCP : bornes, mais larges — statut vs 0.7.3 : inchange

- **Localisation** : `services/navigation_config.py:44-54` (cache d'index 4 entrees / 24 M caracteres,
  `image_dpi` 150, `image_page_max_bytes` 400 000) ; `services/parse_loader.py:99-111` (pas de
  deduplication des chargements en vol) ; `infra/page_raster.py:31-33`, `:61` (PNG encode puis
  redecode, WEBP `method=6`) ; `services/citation_image_service.py:72-79`.

### [INFO] Fusion des lots (#344) : pic memoire en fin d'analyse longue — statut vs 0.7.3 : inchange

- **Localisation** : `services/analysis_service.py:332` (`results.append`, tous les `ConversionResult`
  gardes) ; `infra/local_converter.py:173-174` (tous les JSON parses puis concatenes).

### [INFO] Observations reportees de 0.7.0, toujours presentes — statut vs 0.7.3 : inchange, complete

- Connexion neuve par appel, pas de WAL : `persistence/database.py:265-280`.
- Pas d'`AbortController` (`grep` vide dans `frontend/src/`) ; 12.2.3 reste conforme.
- Timers a un coup non annules au demontage : `features/chunks/ui/ChunksEditor.vue:239-249`
  (`saveTimer`), `pages/DocsLibraryPage.vue:239-245` (`searchTimer`, peut appeler `router.replace`
  apres avoir quitte la page) ; minuteurs de retour "copie" (`McpConfigSection.vue:515`,
  `ResultTabs.vue:306`, `:318`), sans effet hors d'une ref.
- Upload en memoire, borne par `MAX_FILE_SIZE_MB` : `api/documents.py:81-89`.
- Complement 0.7.4 — petits appels bloquants sur la loop, negligeables : `DocumentService.delete`
  (`services/document_service.py:144-147`, `realpath` / `exists` / `unlink`) ;
  `resolve_storage_path` evalue avant le `to_thread` (`api/documents.py:186`, `:214` ->
  `services/document_service.py:128-131`, un ou deux `stat`).

---

## Delta vs 0.7.3

| Ecart 0.7.3 (re-audit, e01fd95) | Statut a 1de1929 |
|---|---|
| [MAJ] PDF entier relu par page rendue (12.1.5) | **Toujours ouvert**, fichiers inchanges ; 4e site releve (upload, `pdfinfo_from_bytes`) ; mesure ajoutee |
| [MAJ] Boucles une-requete-par-chunk (12.1.1) | **Toujours ouvert**, fichiers inchanges ; `promote_from_analysis_if_empty` retire des sites actifs (non appele) ; `merge_chunks` ajoute ; mesure ajoutee |
| [MIN] N+1 `show_sources` | Toujours present |
| [MIN] Bibliotheque sur la liste complete (12.3.2) | Toujours present |
| [MIN] Logo / favicon (12.2.5) | Toujours present |
| [MIN] Pas de cache nginx (12.3.1) | Toujours present |
| [MIN] pdfium hors verrou | Toujours present |
| [MIN] Suivi a 3 s sans borne | Toujours present |
| [INFO] Reliquat CPU sur la loop | Toujours present ; complete par `get_tree` (mesure) |
| [INFO] Imports hors semaphore, polling, `/summaries`, budgets MCP, fusion des lots, reports 0.7.0 | Inchanges (reports 0.7.0 completes par deux petits appels bloquants) |
| — | **Nouveau [MIN]** : `GET /versions` charge et parse toutes les snapshots (12.1.1) |
| — | **Nouveau [INFO]** : `/preview` et `/pages` sans cache HTTP, rate limit de fait global |
| — | **Nouveau [INFO]** : aucune compression HTTP configuree |

Les trois nouveautes sont du code pre-existant (#267, #352, templates) jamais releve, et non des
regressions : la release 0.7.4 ne modifie aucun fichier de code audite. Score inchange : **67**.

---

## Points positifs

- **Aucune regression** : le seul code modifie depuis la baseline est un commentaire et deux libelles.
- **Correctif 12.1.4 de 0.7.3 en place** : `services/analysis_service.py:180` avec son test
  `tests/test_analysis_service.py:224-246`.
- **Les lectures de liste sont bornees** : documents et analyses a `LIMIT 200`
  (`persistence/document_repo.py:93`, `persistence/analysis_repo.py:68-96`), editions et pushes
  pagines (`persistence/chunk_edit_repo.py:81-97`, `:162-166`), `list_pushes` en enveloppe paginee
  avec cache de store (`services/chunk_service.py:693-741`).
- **Pas de N+1 dans `store_service` ni dans la navigation MCP** : `store_service.py:163`
  (`count_by_store`), `:361` (`find_by_ids`) ; `latest_parsed_ids` en une requete fenetree
  (`persistence/analysis_repo.py:137-154`).
- **Polling bien nettoye** : chaque `setInterval` a son `clearInterval` sur le chemin de demontage
  (`AnalysisLibraryPage.vue:169`, `StudioPage.vue:681`, `AppSidebar.vue:176-178`,
  `AnalysisProgressBar.vue:36-40`) ; polling unitaire borne a 15 min (`store.ts:31`, `:125-130`) ;
  disponibilite de l'ingestion a 30 s seulement si active (`AppSidebar.vue:170-173`).
- **Viewer du doc workspace econome cote client** : fenetre de rendu par `IntersectionObserver`
  (`PagePreviewWithOverlay.vue:365-373`), `loading="lazy"` et `decoding="async"` (l.101-102),
  observers deconnectes (l.522-525) ; les cartes MCP ont leur cache client par page
  (`mcp_adapter/sources_app.html:909`, `:939-941`).
- **Entrees bornees avant tout travail lourd** : dpi `/preview` 72-300 (`api/documents.py:169`), largeur
  des rasters MCP 120-1600 (`mcp_adapter/apps.py:206`, `sources_view.py:204-206`), upload a
  `MAX_FILE_SIZE_MB` controle avant et pendant la lecture (`api/documents.py:78`, `:86`), budgets MCP
  (`services/navigation_config.py:30-62`).
- **Parse MCP chargee une fois et cachee**, LRU a double borne et `json.loads` / index hors loop
  (`services/parse_loader.py:99-135`).
- **Semaphore et health check corrects** : `services/analysis_service.py:100`, `:424` ;
  `main.py:128-137`.

---

## Plan de remediation et gains

Chaque item de poids 2 rapporte 2/21 = **+9,5 points**, chaque item de poids 1 **+4,8 points**.

| Ordre | Action | Item | Ecarts a lever pour que l'item bascule | Effort | Risque | Score apres |
|-------|--------|------|----------------------------------------|--------|--------|-------------|
| 1 | Rendus et comptage par chemin (`convert_from_path`, `PdfDocument(path)` sous verrou, `pdfinfo_from_path`) | 12.1.5 | [MAJ] PDF relu | S | Faible | **76** |
| 2 | `replace_chunkset` / `shift_sequences` / `insert_many` en une transaction ; parse chargee une fois dans `show_sources` ; projection `json_array_length` + `LIMIT` sur les versions | 12.1.1 | [MAJ] ecritures par chunk + [MIN] `show_sources` + [MIN] versions | M + S + S | Moyen / faible / faible | **86 (GO)** |
| 3 | `expires 1y` + `immutable` sur `/assets/`, `no-cache` sur `index.html` (+ gzip) | 12.3.1 | [MIN] cache nginx | S | Faible | 90 |
| 4 | `favicon.svg` en icone, logo < 100 Kio | 12.2.5 | [MIN] logo | S | Nul | 95 |
| 5 | Bibliotheque sur `/summaries`, compte avant suppression | 12.3.2 | [MIN] liste complete | S | Faible | 100 |

Quick wins (S, risque faible) : etapes 1, 3, 4 et 5, soit **+23,8 points** (12.1.5 +9,5 ; 12.3.1,
12.2.5, 12.3.2 +4,8 chacun) : 19 / 21 = 90,5 => **90 / 100** meme si la MAJ "ecritures par chunk"
restait ouverte. Les deux MIN de 12.1.1 (S) ne rapportent des points qu'avec cette MAJ (M), l'item
etant binaire. Recommandes au passage, hors score :
en-tetes de cache sur `/preview` et `/pages`, verrou pdfium factorise (ferme le [MIN] hors
checklist), `get_tree` et `pages_json` sous `asyncio.to_thread`, reconciliation au boot des analyses
orphelines.

---

## Verdict partiel : GO CONDITIONNEL

Score **67/100** (bande 60-79), **0 ecart CRITICAL**, **2 ecarts MAJOR** (<= 3, non bloquant en
nombre). Etat identique a la baseline 0.7.3 : aucun ecart leve, aucune regression, trois
observations nouvelles sur du code pre-existant (1 MIN, 2 INFO). Les deux MAJ sont reconduits
depuis 0.7.3 (relecture du PDF) et 0.6.2 (ecritures par chunk) et ont ete chiffres ici : 69 ms et
48 Mo d'ecriture par page rendue sur un PDF de 48 Mo ; ~3 s pour retirer 500 chunks contre 14 ms
en lot. Plan de remediation ci-dessus : l'etape 1 (S) suffit a passer 76, les etapes 1-2 a
atteindre le GO (86).

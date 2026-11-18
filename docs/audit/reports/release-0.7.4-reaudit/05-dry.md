# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` @ `f7fc791`, PR #401 et #402 incluses, + 13 commits locaux #391-#400 + merge), lu dans l'arbre de travail.

> **Score 67 / 100, identique au 2026-11-13, mais 2 MAJ au lieu de 4.** Trois des quatre MAJ
> sont resolus : un seul parseur ISO (`persistence/iso_datetime.py`), une seule base
> `ServiceError` traduite par `api/errors.py::http_error`, une seule extraction
> `DoclingDocument → pages` (le projecteur appelle `extract_pages_detail`). Le score ne bouge
> pas parce que les items 5.1 et 5.3 restent non conformes : l'algorithme de pile de titres
> existe toujours en 4 copies divergentes (5.1) et les couleurs en dur n'ont pas bouge (5.3).
> PR #401 factorise bien le rendu PDF.js (un composable, un canvas, deux consommateurs) mais
> ajoute de petites copies : `history/api.ts` recopie `analysis/api.ts`, la rasterisation
> d'une page existe en 2 versions, une 4e lecture de `pagesJson`, une famille d'erreurs de
> preview hors `ServiceError`. Pas d'ecart bloquant : GO CONDITIONNEL.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 18 |
| Ecarts INFO | 9 |

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | **Non** | `_parse_iso` x8, erreurs x7 et pages x3 resolus ; restent la pile de titres x4 (divergente), `pagesJson` x4, `stored[-1].sequence if stored else 0` x7, `?analysisId=` x9 |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui | `AnalysisSummary` dans `shared/types.ts:85`, `PreviewImageKey` dans `domain/ports.py` ; aucun type redeclare |
| 5.3 | Pas de magic numbers/strings eparpilles | 2 | **Non** | 33 `var(--color-*)` non definis, 7 replis `var(--warning, #…)`, 6 replis hex dans `BboxCanvas.vue`, `--on-accent` toujours absent |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui | `usePdfDocument` est propre a la feature `document` et utilise par ses 2 composants ; garde de sortie en 2 copies (sous le seuil) |
| 5.5 | Config HTTP centralisee dans `shared/api/http.ts` | 2 | Oui | Aucun nouveau `fetch()` ; PDF.js charge une URL produite par `getExportUrl` |
| 5.6 | Schemas Pydantic transforment le domaine | 2 | Oui | `schemas.py` inchange depuis le 2026-11-13 ; pas de redefinition |
| 5.7 | Validation a un seul endroit / pas de desaccord front-back | 1 | Oui | Regle de fusion (meme type, `text`/`paragraph`) identique front (`commands.ts:78-93`) et back (`docling_editor.py:218-221`) |

Poids total : 12. Poids conformes : 2 + 1 + 2 + 2 + 1 = 8. `score = 8 / 12 × 100 = 66,7 → 67`.

### Compteurs

Methode : grep et lecture de l'arbre de travail, aucun outil de detection de clones.

| Compteur | 2026-11-13 (`eade7fa`) | 2026-11-18 (`a6fb539`) |
|----------|------------------------|------------------------|
| Definitions locales de parse ISO dans `persistence/` | 8 (+1 inline) | **0** (un seul `fromisoformat`, `persistence/iso_datetime.py:18`) |
| Bases d'erreur service avec `http_status` | 6 + `AnalysisEditError` sans statut | **1** (`services/errors.py:11`) ; 9 familles en heritent |
| Familles d'erreurs de service hors `ServiceError` | 0 | **1** (`PreviewDocumentNotFoundError`, `PreviewPageOutOfRangeError`) |
| Implementations `DoclingDocument → PageDetail` | 3 | **2** (`docling_pages.py`, `serve_converter.py` sur dict brut) |
| Pile de titres cote backend | 4 | 4 |
| Lecture `JSON.parse(...pagesJson)` dans le front | 3 | **4** |
| Construction de `?analysisId=` dans le front | 9 | 9 |
| `Query(default=None, alias="analysisId")` dans `api/` | 8 | 8 |
| Parse booleen `("1","true","yes","on")` dans `infra/settings.py` | 9 | 9 |
| `var(--color-*)` / `#d1d5db` / `#6b7280` / `#dc2626` (insensible a la casse) | 33 / 7 / 12 / 15 | 33 / 7 / 12 / 15 |
| Replis `var(--warning, #…)` | 7 | 7 |
| SFC avec `@keyframes spin` | 17 | 17 |
| Rasterisation d'une page PDF (`convert_from_path` + save) | 2 (bytes) | 2 (chemin) |

---

## Ecarts constates

### [MAJ] Algorithme « pile de titres » recopie quatre fois, avec trois definitions du titre (5.1)

- **Localisation** : `document-parser/domain/outline_builder.py:94` ; `document-parser/domain/parse_index.py:102` ; `document-parser/services/chunk_service.py:829-834` ; `document-parser/infra/docling_projector.py:189-197`
- **Constat** : quatre vues (plan MCP, `heading_path`, arbre de chunks, arbre de l'editeur) refont la meme boucle « depiler tant que le niveau du sommet est >= au niveau courant, rattacher au sommet ». Les copies divergent sur la racine sentinelle (`len(stack) > 1` dans `outline_builder.py:94` et `chunk_service.py:831`, `stack` vide ailleurs), sur le niveau d'un `title` (`0` en dur dans `chunk_service.py:830`, `heading_level()` dans le domaine, `getattr(child, "level", 0)` dans le projecteur `:191`) et sur ce qui est un titre (`HEADING_LABELS` `domain/navigation.py:315`, litteral `{"title", "section_header"}` `chunk_service.py:829`, `isinstance(SectionHeaderItem) or label == "title"` `docling_projector.py:189`). C'est la plus grosse logique encore copiee 3+ fois depuis la resolution des trois MAJ du 2026-11-13 ; elle porte la non-conformite de l'item 5.1, avec les MIN « `pagesJson` x4 », « repetitions du service de l'editeur » et « `?analysisId=` x9 ».
- **Regle violee** : item 5.1 (poids 2).
- **Remediation** : un generateur pur `nest_by_heading(items, level_of, is_heading)` dans `domain/`, appele par les quatre ; `HEADING_LABELS` et `heading_level` comme seules definitions. Effort S a M (tests existants sur chaque vue).

### [MAJ] Couleurs UI en dur et tokens non definis ou contournes (5.3, reconduit, inchange)

- **Localisation** : `var(--color-*)` (token jamais defini dans `app/App.vue`) : `frontend/src/features/store/ui/StoreForm.vue` (10), `frontend/src/shared/ui/ComingSoonShell.vue` (10), `frontend/src/shared/breadcrumb/AppBreadcrumb.vue` (7), `frontend/src/features/store/ui/Neo4jConfigForm.vue:94`, `:103`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:77` (+1), `frontend/src/pages/IngestLaunchDialog.vue` (2) ; `#dc2626` en dur : `StoreForm.vue:394`, `:405`, `:503`, `Neo4jConfigForm.vue:99`, `:107`, `OpenSearchConfigForm.vue:82`, `:90`, `IngestLaunchDialog.vue:327`, `:345`, `features/analysis/ui/GraphView.vue:576` ; replis `var(--warning, #…)` : `features/analysis-editor/ui/AnalysisEditor.vue:585`, `:616`, `:636`, `:637` (`#d97706`), `features/chunks/ui/StaleStoresStrip.vue:119`, `:120` (`#ca8a04`), `pages/DocumentsPage.vue:428` (`#f59e0b`) ; `features/document/ui/BboxCanvas.vue:156`, `:172-175` (replis = valeurs du theme sombre), `:194` (`'#18181b'` en dur)
- **Constat** : aucun compteur n'a bouge depuis le 2026-11-13. Trois replis differents pour le meme `--warning` (`#d97706`, `#ca8a04`, `#f59e0b`), dont aucun n'est la valeur sombre (`#eab308`, `App.vue:98`). `BboxCanvas.vue` recopie les valeurs sombres de `App.vue:85-96` ; `--on-accent` n'existe toujours pas.
- **Regle violee** : item 5.3 (poids 2).
- **Remediation** : inchangee : `var(--border)`, `var(--text-muted)`, `var(--error)` a la place de `--color-*` et des hex ; `var(--warning)` sans repli ; ajouter `--on-accent` (clair + sombre) ; dans `BboxCanvas.vue`, lire les tokens sans repli en dur. Effort S pour l'editeur et le canvas, M pour l'ensemble.

### [MIN] Repetitions internes du service et du routeur de l'editeur (reconduit, inchange)

- **Localisation** : chargement document → base → flux → commandes : `document-parser/services/analysis_edit_service.py:77-80`, `:115-118`, `:126-129`, `:249-252` ; `stored[-1].sequence if stored else 0` x7 : `analysis_edit_service.py:81`, `:132`, `:166`, `:218`, `:254`, `:395`, `document-parser/domain/analysis_editing.py:133` ; controle de sequence x3 avec deux libelles : `analysis_edit_service.py:166-170`, `:218-222`, `document-parser/persistence/analysis_edit_repo.py:155-158` ; construction du cache a 10 champs x2 : `analysis_edit_service.py:176-187`, `:256-267` ; `Query(default=None, alias="analysisId")` x6 : `document-parser/api/analysis_edits.py:112`, `:125`, `:142`, `:158`, `:179`, `:202` (+ `api/documents.py:140-142`, `api/document_chunks.py:176`)
- **Regle violee** : item 5.1.
- **Remediation** : `_load_stream()`, `_last_sequence()`, `_check_sequence()`, `_cache_from()` ; alias `AnalysisIdQuery = Annotated[str | None, Query(alias="analysisId")]` dans `api/deps.py`. Effort S.

### [MIN] Formule de hash des commandes ecrite dans deux couches (reconduit, inchange)

- **Localisation** : `document-parser/services/analysis_edit_service.py:393` et `:401-405` (`_command_hash`) ; `document-parser/persistence/analysis_edit_repo.py:164` et `:211-215` (`_hash_command`)
- **Constat** : meme serialisation canonique et meme chaine `previous|sequence|type|version|payload`. Le repository fait foi, le service la recalcule pour predire `command_stream_hash`. Une divergence invaliderait silencieusement tous les caches.
- **Regle violee** : item 5.1.
- **Remediation** : une fonction pure `command_hash()` dans `domain/analysis_editing.py`, importee par les deux. Effort S.

### [MIN] Mappings de reponse et appels d'API recopies (reconduit, inchange)

- **Localisation** : `document-parser/api/analysis_edits.py:28-45` (`_to_analysis_response`) copie de `document-parser/api/analyses.py:25-42` (`_to_response`) ; `ChunkResponse(...)` x3 : `api/analyses.py:149`, `:173`, `:196` ; `frontend/src/features/document/api.ts:19-28` (`fetchDocumentEditedAnalysisResult`) contre `frontend/src/features/analysis-editor/api.ts:10-19` (`fetchAnalysisEditor`, meme endpoint) ; `?analysisId=` x9 : `features/document/api.ts:24`, `:74`, `:90`, `features/analysis-editor/api.ts:15`, `:27`, `:39`, `:50`, `:61`, `:75`
- **Regle violee** : item 5.1.
- **Remediation** : `AnalysisResponse.from_job()` dans `api/schemas.py` ; reutiliser `fetchAnalysisEditor` via le barrel ; helper `withAnalysisId(path, id)` dans `shared/api/`.

### [MIN] `history/api.ts` recopie `analysis/api.ts` (nouveau, PR #401)

- **Localisation** : `frontend/src/features/history/api.ts:4-6` (`fetchHistory` → `/api/analyses/summaries`) = `frontend/src/features/analysis/api.ts:51-53` (`fetchAnalysisSummaries`) ; `history/api.ts:8-10` (`deleteHistoryEntry`) = `analysis/api.ts:59-61` (`deleteAnalysis`)
- **Constat** : PR #401 a bascule les deux listes sur les resumes en ecrivant le meme appel dans les deux features. `fetchAnalysisSummaries` est deja exporte par le barrel `features/analysis/index.ts:3`.
- **Regle violee** : item 5.1 (2 copies).
- **Remediation** : `history` importe `fetchAnalysisSummaries` et `deleteAnalysis` depuis `@/features/analysis`, ou les deux stores fusionnent. Effort S.

### [MIN] Rasterisation d'une page PDF ecrite deux fois (nouveau, #398 / PR #401)

- **Localisation** : `document-parser/services/document_service.py:160-179` (`generate_preview`, PNG/WebP) ; `document-parser/infra/page_raster.py:26-36` (`PdfPageRasterizer.render_page`, PNG)
- **Constat** : meme sequence `is_file()` → `FileNotFoundError` → `convert_from_path(first_page=page, last_page=page, dpi=dpi)` → `ValueError` si vide → `save` dans un `BytesIO`. #398 a modifie les deux copies a l'identique. Un adaptateur `PageRasterizer` existe deja, mais le service de preview passe par la methode statique du service de documents.
- **Regle violee** : item 5.1 (2 copies).
- **Remediation** : ajouter `image_format` a `PdfPageRasterizer.render_page` et injecter le port dans `PreviewService` ; supprimer `DocumentService.generate_preview`. Effort S.

### [MIN] Residus du contrat d'erreur service → HTTP (nouveau pour la preview)

- **Localisation** : `document-parser/services/preview_service.py:14-19` (`PreviewDocumentNotFoundError(Exception)`, `PreviewPageOutOfRangeError(ValueError)`, hors `ServiceError`) mappees a la main dans `document-parser/api/documents.py:189-192` ; `ExportNotFoundError` (`services/export_service.py:152-155`, `http_status = 404`) mappee a la main en 404 dans `api/documents.py:156-157` au lieu de `http_error` ; statut devine sur le texte du message : `api/analyses.py:83-85` ; meme `AnalysisEditUnavailableError` traduite en 409 (`services/chunk_service.py:372-373`) et en 404 (`services/export_service.py:139-140`, `:148-149`) ; « Document not found » 404 ecrit 4 fois dans `api/documents.py:121`, `:131`, `:190`, `:211` ; recherche document + `resolve_storage_path` dans le service pour la preview (`preview_service.py:28-36`) mais dans le routeur pour `page_sizes` (`api/documents.py:209-214`)
- **Constat** : le gros de la duplication est resolu (une base, une traduction), mais PR #401 reintroduit une famille d'erreurs hors du contrat, et ~33 blocs `try/except … raise http_error(exc)` restent ecrits route par route (cf. INFO).
- **Regle violee** : item 5.1.
- **Remediation** : `PreviewDocumentNotFoundError(ServiceError, http_status=404)`, `PreviewPageOutOfRangeError(ServiceError, http_status=400)` ; `http_error` pour `ExportNotFoundError` ; `DocumentNotFoundError` type dans `analysis_service` ; `page_sizes` dans `PreviewService`.

### [MIN] Seconde extraction `DoclingDocument → pages` dans le convertisseur distant (residu du MAJ resolu)

- **Localisation** : `document-parser/infra/serve_converter.py:52-68` (`_LABEL_MAP`, par label) et `:269-298` (`_extract_pages_from_docling_document`) + `:339-380` (`_add_element`, `level=0` en dur) ; reference : `document-parser/infra/docling_pages.py:28-38` (`_ELEMENT_TYPE_MAP`, par classe) et `:48-65`
- **Constat** : la 3e copie (projecteur) est supprimee (`docling_projector.py:51` appelle `extract_pages_detail`). Reste la copie du mode Docling Serve, sur dict brut, avec sa propre table de types et sans niveau. Deux copies seulement, mais deux vocabulaires a maintenir.
- **Regle violee** : item 5.1 (2 copies).
- **Remediation** : `DoclingDocument.model_validate(json_content)` puis `extract_pages_detail`, comme `docling_importer.py:19`.

### [MIN] Lecture de `pagesJson` recopiee quatre fois dans le front (promu de INFO, +1 copie)

- **Localisation** : `frontend/src/features/analysis-editor/types.ts:89-96` (`parseAnalysisPages`, exporte par le barrel) ; `frontend/src/features/analysis/store.ts:46` ; `frontend/src/features/analysis/ui/InspectResultTabs.vue:65` ; **nouveau** `frontend/src/pages/AnalysisDetailPage.vue:88-94`
- **Constat** : la page importe deja `@/features/analysis-editor` mais reecrit le meme `try { JSON.parse } catch { [] }`.
- **Regle violee** : item 5.1 (4 copies).
- **Remediation** : deplacer `parseAnalysisPages` dans `shared/` et l'utiliser partout.

### [MIN] Magic numbers et strings de l'editeur et du rendu PDF

- **Localisation** : ensemble `{"text","paragraph"}` x4 : `document-parser/infra/docling_editor.py:220`, `document-parser/infra/docling_projector.py:136`, `frontend/src/features/analysis-editor/commands.ts:84`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:364-367` ; bornes `-1`/`6` : `docling_editor.py:176` ; **nouveau** : `frontend/src/features/document/ui/usePdfDocument.ts:29` (`rangeChunkSize: 262144`), `frontend/src/features/document/ui/PdfPageCanvas.vue:54` (plafond de ratio `2`), `document-parser/infra/preview_cache.py:16` (`64 * 1024 * 1024`), `document-parser/api/documents.py:187` (`max-age=86400`) ; DPI `150` ecrit dans `api/documents.py:178`, `services/document_service.py:161`, `services/navigation_config.py:52`, `domain/navigation.py:63` (et `PREVIEW_DPI`, `frontend/src/features/document/api.ts:47`)
- **Constat** : les `612.0`/`792.0` du projecteur ont disparu (resolu). Le reste demeure ; PR #401 ajoute des constantes non nommees.
- **Regle violee** : item 5.3 (deja non conforme).
- **Remediation** : `MERGEABLE_LABELS` cote backend et `supportedOperations.includes('mergeText')` cote front ; constantes nommees (`PDF_RANGE_CHUNK_BYTES`, `MAX_PIXEL_RATIO`, `PREVIEW_CACHE_BYTES`, `DEFAULT_PREVIEW_DPI`).

### [MIN] Pont JSON-RPC MCP Apps recopie dans les deux cartes HTML (reconduit, etendu)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:769-845` (`post`, `request`, `handshake`) et `:497` (detection de langue) ; `document-parser/mcp_adapter/sources_app.html:1155-1230` et `:532`
- **Constat** : #397 a ajoute la meme detection `LOCALE` et la meme structure `MESSAGES` dans les deux cartes.
- **Remediation** : `mcp_adapter/app_bridge.js` injecte au chargement.

### [MIN] Import d'une analyse Docling recopie dans trois composants (reconduit, inchange)

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:50`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:77`, `frontend/src/features/document/ui/DocumentUpload.vue:119` (blocs lecture fichier → parse → `importAnalysis`)
- **Remediation** : `useAnalysisImport()`.

### [MIN] Parse booleen d'environnement recopie (reconduit, inchange)

- **Localisation** : `document-parser/infra/settings.py:233`, `:249`, `:251`, `:254`, `:256`, `:263`, `:273`, `:275`, `:280`
- **Remediation** : `_env_bool(name, default)`.

### [MIN] Vocabulaire des labels Docling recopie (reconduit)

- **Localisation** : `{"page_header","page_footer"}` : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` ; normalisation d'un label : `document-parser/domain/parse_index.py:189` (`label_of`), `document-parser/infra/docling_projector.py:94-96` (`_label_of`), `document-parser/services/chunk_service.py:827` ; test de titre front : `frontend/src/features/analysis-editor/ui/EditableStructureNode.vue:177`
- **Remediation** : `FURNITURE_LABELS`, `HEADING_LABELS`, `label_of` publics et importes.

### [MIN] Bloc de style `.field-*` des formulaires de store (reconduit, inchange)

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue`, `StoreForm.vue` (classes `field-label` / `field-input` et leurs styles)
- **Remediation** : aucune (perimetre retire en 0.8.0).

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO et value objects (reconduit, inchange)

- **Localisation** : `document-parser/api/schemas.py` (`PipelineOptionsRequest`, `ChunkingOptionsRequest`), `document-parser/domain/value_objects.py`, `frontend/src/features/chunks/ui/StrategyPopover.vue`
- **Remediation** : inchangee.

### [MIN] Primitives CSS recopiees (reconduit, inchange)

- **Localisation** : `@keyframes spin` dans 17 SFC (p. ex. `frontend/src/features/ingestion/ui/IngestPanel.vue`, `features/analysis/ui/AnalysisProgressBar.vue`, `features/analysis/ui/ResultTabs.vue`)
- **Remediation** : `shared/ui/AppSpinner.vue`.

### [MIN] Palette de la vue graphe Neo4j recopiee trois fois (reconduit, perimetre deprecie)

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue:146`, `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:131`, `frontend/src/features/analysis/legendFilters.ts:74`
- **Remediation** : suppression en 0.8.0.

### [MIN] Helpers `_utcnow` / `_new_id` recopies (reconduit, 4 → 3 copies)

- **Localisation** : `document-parser/domain/models.py:28-34`, `document-parser/domain/chunk_editing.py:29-34`, `document-parser/services/chunk_service.py:91-96` ; en ligne : `document-parser/persistence/analysis_edit_repo.py:172-173`
- **Constat** : la copie de `version_service.py` a disparu.
- **Remediation** : `new_id()` / `utcnow()` publics dans `domain/models.py`.

---

### [INFO] Regle de fusion ecrite deux fois dans le front, en accord avec le backend (5.7 conforme)

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:78-93` (`validateMerge`, avec la regle « meme type » de #395) et `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:364-367` (`isMergeable`) ; backend `document-parser/infra/docling_editor.py:218-221`
- **Constat** : apres le merge de PR #402 et de `9d3510d`/`29c5b76`, une seule implementation de `validateMerge` subsiste (pas de doublon issu du merge). `isMergeable` du SFC repete la moitie de la regle au lieu de lire `supportedOperations`, comme le fait `isMovable` (`:368-369`).

### [INFO] Contrat du modele d'editeur ecrit a la main, hors Pydantic (inchange)

- **Localisation** : `document-parser/infra/docling_projector.py:215-229` (`_element_dict`), `document-parser/api/analysis_edits.py:48-54` (`_serialize_tree`), `frontend/src/features/analysis-editor/types.ts`

### [INFO] Boilerplate `try/except … raise http_error(exc)` route par route

- **Localisation** : `document-parser/api/config.py` (5), `api/analysis_edits.py:116-207` (6), `api/stores.py:105-198` (7), `api/document_chunks.py:76-235` (11), `api/document_versions.py` (2), `api/graph.py:70`, `api/reasoning.py:35`
- **Constat** : la decision (statut) est en un seul endroit ; seule la plomberie est repetee. Un `@app.exception_handler(ServiceError)` la supprimerait.

### [INFO] Formatage de dates : helper partage ignore (inchange)

- **Localisation** : `frontend/src/shared/format.ts:26` (`formatAbsolute`) ; `frontend/src/pages/AnalysisDetailPage.vue:102`, `frontend/src/pages/AnalysisLibraryPage.vue:159` (copies exactes) ; `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:414` (variante `short`)

### [INFO] Garde « modifications non enregistrees » en deux copies (inchange)

- **Localisation** : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:494-495`, `frontend/src/pages/AnalysisDetailPage.vue:96-97`

### [INFO] Chargements hors `apiFetch` justifies (5.5 conforme)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:135` (`fetch` brut pour `blob()`) ; `frontend/src/features/document/ui/usePdfDocument.ts:25-30` (PDF.js charge `getExportUrl(id, 'pdf')` par requetes de plage)
- **Constat** : `apiFetch` n'ajoute que `Content-Type` ; aucune configuration (base URL, auth) n'est perdue.

### [INFO] Deux tests couvrent le meme cas de cache corrompu

- **Localisation** : `document-parser/tests/test_analysis_editing.py:668` (`test_corrupt_edited_cache_is_replayed_instead_of_failing`, commit `9d3510d`) et `:984` (`test_load_replays_saved_stream_when_edited_cache_is_corrupt`, parametre `("document_json", "not json")`, commit `c824002` de PR #402)
- **Constat** : le code n'a qu'une implementation (`services/analysis_edit_service.py:297-320`, `_project_cache`), mais le test de `9d3510d` est inclus dans le test parametre de PR #402. Hors perimetre strict (tests), a nettoyer.

### [INFO] Deux composants de dessin des bbox

- **Localisation** : `frontend/src/features/analysis/ui/BboxOverlay.vue` (323 l.), `frontend/src/features/document/ui/BboxCanvas.vue` (294 l.)
- **Constat** : meme role (rectangles par element sur un canvas superpose, `ResizeObserver`), adaptes en parallele par PR #401 (`imageEl: HTMLElement`). Seul `BboxCanvas` utilise `colorFor`.

### [INFO] Resolution de l'analyse active faite deux fois

- **Localisation** : `document-parser/services/analysis_edit_service.py:105-111` (`load_active_result`, message `:110`) puis `:282-286` (`_base_analysis`), meme message « This document has no active analysis »
- **Constat** : `load_active_result` lit la selection puis appelle `load_editor` avec son id ; la branche « sans id » de `_base_analysis` refait la meme lecture pour les autres appelants.

---

## Delta vs audit du 2026-11-13

Base : `fix/0.7.4-editor-followups` @ `eade7fa`, score 67, 0 CRIT / 4 MAJ / 15 MIN / 6 INFO.

| Ecart du 2026-11-13 | Niveau | Statut au 2026-11-18 | Verification |
|---------------------|--------|----------------------|--------------|
| `_parse_iso` x8 | MAJ | **Resolu** | `persistence/iso_datetime.py:14-27` ; 8 repositories l'importent ; un seul `fromisoformat` hors `.venv` |
| Couleurs UI en dur / tokens | MAJ | Toujours present, inchange | compteurs identiques |
| Contrat d'erreur service → HTTP (7 familles) | MAJ | **Resolu** (residus en MIN) | `services/errors.py:11` ; `api/errors.py:25-31` ; plus aucun `HTTPException(status_code=<err>.http_status)` ; `_raise` supprime ; 404 pour document/analyse absents (`analysis_edit_service.py:274`, `:281`, `:289`) |
| Conversion `DoclingDocument → pages` x3 | MAJ | **Resolu** (copie `serve_converter` en MIN) | `docling_projector.py:51` appelle `extract_pages_detail` ; `_pages`, `_page_dict`, `612.0`/`792.0` supprimes |
| Repetitions internes de l'editeur | MIN | Toujours present | |
| Hash des commandes x2 | MIN | Toujours present | |
| Pile de titres x4 | MIN | **Promu MAJ** | seule logique 3+ fois restante d'ampleur, porte l'item 5.1 |
| Mapping `AnalysisResponse` / appel d'API inter-features | MIN | Toujours present | |
| Magic numbers/strings de l'editeur | MIN | Toujours present, partiellement resolu | `612.0`/`792.0` supprimes ; codes 409/400 en dur supprimes ; + constantes PDF |
| Pont MCP Apps | MIN | Toujours present, etendu | + detection de langue x2 (#397) |
| Import d'analyse x3 | MIN | Toujours present | |
| Defauts MCP/Ask, parse booleen | MIN | Toujours present | 9 sites |
| Labels Docling | MIN | Toujours present | |
| `.field-*`, bornes de chunking, primitives CSS, palette Neo4j | MIN | Toujours present | |
| `_utcnow` / `_new_id` | MIN | Toujours present, 4 → 3 copies | |
| Validation editeur en accord | INFO | Inchange | regle « meme type » ajoutee des deux cotes, une seule `validateMerge` |
| Modele d'editeur hors Pydantic | INFO | Inchange | |
| Formatage de dates | INFO | Inchange | |
| Parse de `pagesJson` | INFO | **Promu MIN** | 3 → 4 copies (`AnalysisDetailPage.vue:88-94`) |
| Garde de sortie x2 | INFO | Inchange | |
| `fetch()` brut DownloadDropdown | INFO | Inchange | |

**Nouveaux ecarts** : 4 MIN (`history/api.ts` = `analysis/api.ts` ; rasterisation x2 ; erreurs de preview hors `ServiceError` et mappings manuels residuels ; seconde extraction de pages separee du MAJ resolu), 4 INFO (boilerplate `http_error`, tests de cache corrompu en double, deux composants bbox, double resolution de l'analyse active).

**Score : 67 → 67 (delta 0).** Les items non conformes sont les memes (5.1, 5.3). Le nombre de MAJ passe de 4 a 2.

---

## Points positifs

- **Trois factorisations reelles** : un parseur ISO teste (`tests/test_iso_datetime.py`), une base d'erreur et une traduction HTTP testee (`tests/test_api_errors.py`), une extraction de pages partagee par conversion locale, import et editeur.
- **Rendu PDF.js factorise des le depart (PR #401)** : `usePdfDocument.ts` (chargement), `PdfPageCanvas.vue` (rendu), consommes par `PdfPagePreview.vue` et `PagePreviewWithOverlay.vue` ; `StudioPage.vue` et `StructureViewer.vue` reutilisent `PdfPagePreview` au lieu de leur propre `<img>`. Une seule construction d'URL de preview (`getPreviewUrl`).
- **Cache de preview derriere un port** (`domain/ports.py`, `infra/preview_cache.py`) au lieu d'un cache ad hoc dans le routeur.
- **Pas de doublon issu du merge PR #402 / commits locaux** : une seule `validateMerge`, un seul `_project_cache`, un seul id de travail (`analysis_edit_service.py:354`), une seule table de statuts de l'editeur (`api/errors.py:17-22`).
- **Client HTTP toujours centralise** : aucun nouveau `fetch()` brut.

---

## Verdict partiel : GO CONDITIONNEL

0 CRITICAL, 2 MAJOR (sous le seuil bloquant de 3), score 67 / 100 (tranche 60-79).
Conditions : plan de remediation pour les deux MAJ (pile de titres factorisee dans `domain/`,
tokens CSS + `--on-accent`), et correction rapide des residus introduits par PR #401
(`history/api.ts`, erreurs de preview sur `ServiceError`, rasterisation unique).

# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `efc0bc5`, lu dans l'arbre de travail (aucune modification hors cible : seul `experiments/mcp-bench/` est non suivi).
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`b5f8c7f`, score 83).

> Code non exécuté : aucune suite n'a tourné sur ce commit.

> **Score 100 / 100 (+17). 7 / 7 items conformes. 0 CRIT, 0 MAJ, 14 MIN, 20 INFO. GO.**
> Le seul MAJ du contrôle (la pile de titres écrite quatre fois) est résolu : `domain/heading_tree.py::nest_by_heading`
> porte la seule boucle « dépiler tant que le sommet est au même niveau ou plus profond », et les quatre
> vues ne font plus que lire le résultat. Aucune pile ni aucun `pop()` de titre ne reste ailleurs dans le
> backend ou le frontend. Les deux formules de hash, le contrôle de séquence, les règles de découpe et de
> fusion des chunks, l'horloge et les générateurs d'id, l'échelle `except` des routes preview/pages et la
> lecture des tokens CSS par les canvas n'existent plus qu'une fois. À la lecture, chaque règle unifiée
> produit le même résultat que ses anciennes copies sur les cas demandés ; les seules différences de
> comportement relevées sont voulues et annoncées dans les messages de commit (voir « Équivalence »).
> 5.3 reste conforme : 0 littéral égal à un token, et les nouveaux composants n'apportent aucune couleur.
> Aucune nouvelle copie de taille MIN : 8 INFO nouveaux, tous à deux copies ou voulus.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 7 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 14 |
| Ecarts INFO | 20 |

| # | Item | Poids | Conforme (contrôle → validation) | Mesures contrôle `b5f8c7f` → validation `efc0bc5` |
|---|------|-------|----------------------------------|----------------------------------------------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois | 2 | Non → **Oui** | boucle de pile de titres 4 → **1** (`domain/heading_tree.py:72-73`) ; `_hash_command` 2 → **0** (`hash_command`, `domain/analysis_editing.py:152`) ; `json.dumps(..., sort_keys=True, separators=…)` 2 → **1** (`:149`) ; `stored[-1].sequence if stored else 0` 7 → **1** (`get_last_sequence`, `:163-165`) ; message de conflit de séquence écrit 3 → **2 constantes** (`:209-212`) ; définitions `_get_utc_now`/`_generate_id` 4 → **1 horloge + 2 générateurs** (`domain/models.py:28-45`) ; règles split/merge 2 versions divergentes → **1** (`domain/chunk_editing.py:118-192`) ; échelle `except` preview/pages 2 → **1** (`services/preview_service.py:121-138`) ; SQL d'état d'analyse 3 écrivains → **1** (`persistence/document_analysis_repo.py:50`) ; `?analysisId=` 9 → 8 ; `Query(alias="analysisId")` 8 → 8 ; parse booléen 9 → 9 (+1 hors `settings.py`, déjà là) ; `@keyframes spin` 17 → 17 |
| 5.2 | Types partagés centralisés | 2 | Oui → Oui | aucun `Protocol` défini deux fois ; aucun `export interface/type` en double dans `frontend/src` ; `currentAnalysisId` ajouté une fois (`shared/types.ts:49-51`) |
| 5.3 | Pas de magic numbers/strings éparpillés | 2 | Oui → **Oui** | tokens définis 29 → 29 ; noms non définis 0 → 0 ; replis `var(--x, …)` 0 → 0 ; littéraux hors palettes et hors commentaires 58 → **58** (32 teintes, 5 anneaux, 14 voiles, 7 hex) ; littéraux égaux à un token 0 → **0** ; bornes de l'éditeur nommées une fois (`api/schemas.py:155-166`) |
| 5.4 | Logique réactive partagée dans `shared/composables/` | 1 | Oui → Oui | `shared/composables/` inchangé ; les modules sortis du store (`commandStacks.ts`, `pendingDraft.ts`, `previewScheduler.ts`, `mergeSelection.ts`) sont des fonctions pures déplacées, sans copie restante |
| 5.5 | Config HTTP centralisée | 2 | Oui → Oui | un seul `fetch()` brut, justifié (`DownloadDropdown.vue:135`) |
| 5.6 | Schémas Pydantic transforment le domaine | 2 | Oui → Oui | les réponses de l'éditeur sont typées (`api/schemas.py:228-299`) et décodent le JSON du projecteur, sans redéfinir de règle métier ; `CommandType` importé du domaine (`:15`) |
| 5.7 | Validation à un seul endroit | 1 | Oui → Oui | règles de l'éditeur sur valeurs simples dans le domaine (`domain/analysis_editing.py:228-276`), appelées par l'adaptateur ; bornes de taille dans les schémas seulement ; règle de fusion front (`commands.ts:84`, `AnalysisEditor.vue:294`) en accord avec `MERGEABLE_TEXT_LABELS` |

Poids total : 12. Poids conformes : 2 + 2 + 2 + 1 + 2 + 2 + 1 = 12. `score = 12 / 12 × 100 = 100`.

**Lecture de 5.1.** Même lecture que le contrôle : les répétitions d'une ligne (`Query(alias=…)`, `?analysisId=`,
parse booléen) et les `@keyframes spin` sont des MIN, et ce n'est pas elles qui rendaient 5.1 non conforme
(le contrôle : « Seul 5.1 reste non conforme », à cause de la pile de titres). Une lecture plus stricte, qui
compterait les 17 `@keyframes spin` (3 lignes chacun) comme un bloc répété, garderait 5.1 non conforme et le
score à 83. Je ne l'ai pas retenue pour rester comparable au contrôle.

### 5.1 : une marche, quatre paramétrages

J'ai lu `domain/heading_tree.py` et chaque site d'appel pour vérifier qu'aucun ne refait la pile.

| Vue | Appel | Ce qui reste local | Pile ou `pop()` local ? |
|-----|-------|--------------------|-------------------------|
| Plan MCP (`domain/outline_builder.py`) | `:96-100` avec `may_open=is_within_depth` (limite de profondeur, le titre ne compte pas) ; `:162` pour `_count_children` | construction des `OutlineNode`, rattachement via `step.parent` (`:122`) | non |
| Index de parse (`domain/parse_index.py`) | `:151`, `level_of=read_heading_level` (`:227-233`) | fil d'Ariane via `step.ancestors`, fins de section via `step.closed` et `still_open` (`:154-160`) | non |
| Arbre des chunks (`domain/document_tree.py`, sorti de `chunk_service.py`) | `:62`, `level_of=_read_tree_heading_level` (`:94-103`) | nœuds et conteneurs (`_build_item_subtree`) | non |
| Arbre de l'éditeur (`infra/docling_projector.py`) | `:199`, `level_of=_read_heading_level` (`:101-106`) | `build_node`, `freeze` | non |

`rg "\.pop\(\)"` sur le code audité ne trouve plus que `heading_tree.py:73` pour des titres
(`element_reader.py:82`, `source_service.py:284` et `treeReveal.ts:32` sont d'autres piles). La boucle
`while stack and stack[-1][0] >= level` n'apparaît qu'à `heading_tree.py:72`. C'est une seule implémentation :
la différence entre vues tient au paramètre `level_of` (et `may_open` pour le plan), ce que demandait la
remédiation du contrôle. Les définitions du titre restent trois, volontairement et documentées
(`heading_tree.py:9-13`, `document_tree.py:97-98`) : voir INFO.

### Méthode de mesure 5.3

Le script du contrôle n'était plus disponible (`/private/tmp/.../control05`, `recontrol05` absents). Je l'ai
reconstruit d'après la méthode documentée : sur `frontend/src` (hors `*.test.ts`), relevé de tous les hex,
`rgb/rgba` et `white`/`black` en contexte de couleur, normalisés en (r, g, b, α) et comparés aux valeurs de
tous les tokens de `app/App.vue` (lignes 80-146, deux thèmes), plus le relevé des `var(--x)` non définis et
des replis. Résultat sur `efc0bc5` :

| Compteur | b5f8c7f (contrôle) | efc0bc5 |
|----------|--------------------|---------|
| Tokens définis | 29 | 29 (`App.vue` inchangé) |
| Noms de token utilisés mais jamais définis | 0 | 0 (le script relève `--token`, qui est dans un commentaire de `shared/cssTokens.ts:4`) |
| Replis `var(--x, …)` | 0 | 0 |
| Table par type (`shared/elementColors.ts`) | 10 | 10 |
| Palette Neo4j | 70 | 70 |
| Hors palettes, hors commentaires | 58 | **58** |
| → teintes `rgba` de statut/accent | 32 | 32 |
| → anneaux de spinner `rgba(255,255,255,α)` | 5 | 5 |
| → voiles et ombres noirs | 14 | 14 |
| → hex sans token | 7 | 7 |
| Littéraux égaux à la valeur d'un token (hors commentaires et palettes) | 0 | **0** (les 4 égalités relevées sont dans les commentaires de fin de ligne de `features/reasoning/kindColors.ts:15-21`, comme au contrôle) |

Nouveaux fichiers vérifiés à la main : `features/document/ui/PageRaster.vue`,
`features/analysis-editor/ui/AnalysisEditHistoryPanel.vue`, `EditorBanners.vue`, `editorButton.css` ne
contiennent aucune couleur littérale. Les bandeaux passent par
`color-mix(in srgb, var(--warning|--success|--error) 10%, transparent)` (`EditorBanners.vue:85`, `:89`,
`:103`), la forme que le contrôle recommandait. Les trois canvas lisent les tokens par un seul lecteur,
`createCssTokenReader` (`shared/cssTokens.ts:12-15`), appelé dans `BboxCanvas.vue:103`,
`BboxOverlay.vue:143`, `StructureViewer.vue:171` ; plus aucun `getComputedStyle` ailleurs.

---

## Ecarts constates

Aucun CRIT, aucun MAJ.

### [MIN] Teintes, voiles et hex sans token (5.3 conforme ; reconduit, inchangé)

- **Localisation** : 32 teintes (`shared/ui/StatusBadge.vue:57-77`, `features/history/ui/HistoryList.vue:155-196`, `features/analysis/ui/AnalysisPanel.vue:170-182`, `features/ingestion/ui/IngestPanel.vue:274-288`, `features/chunking/ui/ChunkPanel.vue:530`, `:574`, `:623`, `:649`, `:774-775`, `features/document/ui/DocumentList.vue:128`, `features/document/ui/HistoryDrawer.vue:206`, `:211`, `features/analysis/ui/ResultTabs.vue:606`, `:648`, `:661`, `features/chunks/ui/StrategyPopover.vue:265`, `pages/StudioPage.vue:920`) ; 5 anneaux de spinner (`IngestPanel.vue:335`, `AnalysisPanel.vue:144`, `ChunkPanel.vue:792`, `pages/DocChunkTab.vue:213`, `pages/StudioPage.vue:877`) ; 14 voiles et ombres (dont `0 4px 12px rgba(0,0,0,0.3)` à `BboxOverlay.vue:308` et `StructureViewer.vue:446`) ; 7 hex (`StrategyPopover.vue:361-362`, `pages/DocsLibraryPage.vue:407-409`, `StatusBadge.vue:58`, `HistoryDrawer.vue:212`)
- **Constat** : mêmes familles et mêmes comptes qu'au contrôle ; seuls des numéros de ligne ont bougé. Aucun n'a la valeur d'un token.
- **Regle violee** : item 5.3, sans le rendre non conforme.
- **Remediation** : `color-mix(… var(--x) …)` comme `EditorBanners.vue` ; `--overlay`, `--shadow-tooltip` ; `var(--error)` pour le bouton danger de `StrategyPopover`.

### [MIN] Répétitions internes du routeur de l'éditeur (reconduit, réduit)

- **Localisation** : `Query(default=None, alias="analysisId")` x8 : `document-parser/api/analysis_edits.py:115`, `:128`, `:145`, `:160`, `:181`, `:204`, `api/document_chunks.py:176`, `api/documents.py:124`
- **Constat** : la moitié « service » est résolue : `get_last_sequence` (`domain/analysis_editing.py:163`) et `check_expected_sequence` (`:215`) remplacent les 7 `stored[-1].sequence if stored else 0` et les 3 contrôles écrits à la main. Le paramètre de requête reste écrit 8 fois.
- **Regle violee** : item 5.1.
- **Remediation** : `AnalysisIdQuery = Annotated[str | None, Query(alias="analysisId")]` dans `api/deps.py`.

### [MIN] Mappings de réponse et appels d'API recopiés (reconduit, inchangé)

- **Localisation** : `document-parser/api/analysis_edits.py:29` (`_to_analysis_response`) = `document-parser/api/analyses.py:27` (`_to_response`) ; `ChunkResponse(` x3 : `api/analyses.py:160`, `:184`, `:207` ; même endpoint `/analysis-editor` appelé par `frontend/src/features/document/api.ts:20-27` et `frontend/src/features/analysis-editor/api.ts:10-16` ; `?analysisId=` x8 : `features/analysis-editor/api.ts:15`, `:27`, `:39`, `:50`, `:61`, `:75`, `features/document/api.ts:24`, `:90`
- **Regle violee** : item 5.1.
- **Remediation** : `AnalysisResponse.from_job()` ; `withAnalysisId(path, id)` dans `shared/api/`.

### [MIN] Résidus du contrat d'erreur service → HTTP (reconduit, réduit)

- **Localisation** : `AnalysisEditUnavailableError` traduite en 409 (`document-parser/services/chunk_service.py:312-313`), en 404 (`services/export_service.py:149-150`, `:158-159`) et en liste vide (`services/document_tree_service.py:67-68`) ; « Document not found » écrit dans la route : `api/documents.py:99`, `:113`
- **Constat** : l'échelle `except FileNotFoundError / OSError / Exception` des routes preview et pages est résolue par `ac7ac17` : une seule traduction, `_translate_pdf_read_errors` (`services/preview_service.py:121-138`), et les routes ne font plus que `except ServiceError` (`api/documents.py:170-171`, `:185-186`). Restent les trois issues de `AnalysisEditUnavailableError` (le cas de l'arbre est nouveau, mais c'est un choix de vue, pas une traduction HTTP) et les deux 404 en dur.
- **Regle violee** : item 5.1.
- **Remediation** : un statut unique pour `AnalysisEditUnavailableError` ; `DocumentNotFoundError` levée par le service document.

### [MIN] Seconde extraction `DoclingDocument → pages` dans le convertisseur distant (reconduit, inchangé)

- **Localisation** : `document-parser/infra/serve_converter.py:52` (`_LABEL_MAP`), `:254` (`_extract_pages_from_docling_document`) ; référence : `document-parser/infra/docling_pages.py`
- **Regle violee** : item 5.1 (2 copies).

### [MIN] Magic numbers et strings de l'éditeur et du rendu PDF (reconduit, réduit)

- **Localisation** : `text`/`paragraph` x3 : `document-parser/domain/analysis_editing.py:228` (`MERGEABLE_TEXT_LABELS`, nommé, utilisé par `infra/docling_projector.py:146` et `domain/analysis_editing.py:258`), `frontend/src/features/analysis-editor/commands.ts:84`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:294` ; plafond de ratio `2` : `frontend/src/features/document/ui/PdfPageCanvas.vue:55` ; `64 * 1024 * 1024` : `document-parser/infra/preview_cache.py:16` ; `max-age=86400` : `document-parser/api/documents.py:176` ; DPI `150` : `api/documents.py:165`, `domain/navigation.py:63`, `services/navigation_config.py:52` (+ `PREVIEW_DPI`, `frontend/src/features/document/api.ts:47`)
- **Constat** : côté backend, la paire de labels n'est plus écrite qu'une fois, nommée. Le reste est inchangé.
- **Regle violee** : item 5.3.

### [MIN] Pont JSON-RPC MCP Apps recopié dans les deux cartes HTML (reconduit, inchangé)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html`, `document-parser/mcp_adapter/sources_app.html` (fichiers non modifiés depuis `b5f8c7f`)

### [MIN] Import d'une analyse Docling recopié dans trois composants (reconduit, inchangé)

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue`, `frontend/src/features/document/ui/DocumentActionsMenu.vue`, `frontend/src/features/document/ui/DocumentUpload.vue` (non modifiés)

### [MIN] Parse booléen d'environnement recopié (reconduit, inchangé)

- **Localisation** : `document-parser/infra/settings.py` : 9 occurrences de `("1", "true", "yes", "on")` (+1 dans `services/config_overrides.py`, déjà présente sur `b5f8c7f`)

### [MIN] Vocabulaire des labels Docling recopié (reconduit, déplacé)

- **Localisation** : `{"page_header","page_footer"}` : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` ; normalisation d'un label : `domain/parse_index.py:236-237` (`get_label`), `domain/document_tree.py:90-91` (`_get_label_type`, déplacé de `chunk_service.py`), `infra/docling_projector.py:96-98` (`_get_label`)
- **Constat** : `_get_label_type` et `get_label` donnent le même résultat (label en minuscules, `"text"` par défaut) et vivent maintenant tous deux dans `domain/` : le déplacement aurait pu réutiliser `get_label`.

### [MIN] Bloc de style `.field-*` des formulaires de store (reconduit, inchangé)

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue`, `StoreForm.vue`

### [MIN] Bornes de chunking dupliquées entre DTO, value objects et popover (reconduit, inchangé)

- **Localisation** : `document-parser/api/schemas.py:461`, `:476-480`, `document-parser/domain/value_objects.py:117`, `frontend/src/features/chunks/ui/StrategyPopover.vue`

### [MIN] `@keyframes spin` dans 17 SFC (reconduit, inchangé)

- **Remediation** : `shared/ui/AppSpinner.vue`.

### [MIN] Palette de la vue graphe Neo4j recopiée (reconduit, périmètre déprécié)

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue`, `NodeDetailsPanel.vue`, `features/analysis/legendFilters.ts` : 70 littéraux, non touchés.

---

### [INFO] Deux lectures du niveau de titre qui ne diffèrent que par l'erreur (nouveau, voulu)

- **Localisation** : `document-parser/domain/parse_index.py:217-233` (`get_heading_level` / `read_heading_level`) ; `document-parser/domain/document_tree.py:94-103` (`_read_tree_heading_level`) ; `document-parser/infra/docling_projector.py:101-106`
- **Constat** : même règle (`title` = 0, `section_header` = niveau déclaré, au moins 1) sauf sur un niveau non numérique : l'index renvoie 1, l'arbre lève. C'est voulu pour garder le comportement de chaque vue, et c'est écrit (`document_tree.py:97-98`). Le projecteur lit des objets Docling, sa forme diffère par nature.

### [INFO] L'horloge partagée n'est pas utilisée par l'éditeur (nouveau)

- **Localisation** : `datetime.now(UTC)` direct : `document-parser/services/analysis_edit_service.py:233`, `:349`, `:382` ; `document-parser/persistence/analysis_edit_repo.py:167-168` (avec `uuid.uuid4().hex`)
- **Constat** : les quatre définitions de `_get_utc_now`/`_generate_id` sont devenues `get_utc_now`, `generate_id`, `generate_compact_id` (`domain/models.py:28-45`), mais le service et le dépôt de l'éditeur appellent toujours l'horloge et `uuid4` en direct. Pas de copie de fonction, juste le helper contourné.

### [INFO] Comptage de la taille d'un corps écrit deux fois (nouveau, `efc0bc5`)

- **Localisation** : `document-parser/api/documents.py:58-70` (upload : `Content-Length` puis lecture par blocs) ; `document-parser/infra/body_limit.py:39-54` (import : même schéma, sur le corps brut)
- **Constat** : deux copies, cibles différentes (fichier multipart / corps JSON), même message 413. Sous le seuil de 5.1.

### [INFO] Contrôle `Host` : la correspondance n'est pas écrite deux fois, la lecture de la liste oui (nouveau, `efc0bc5`)

- **Localisation** : `document-parser/infra/host_guard.py:38-74` ; `document-parser/bootstrap/mcp_mount.py:220-232` ; `document-parser/infra/settings.py:276-286`
- **Constat** : le montage MCP délègue la correspondance au SDK (`TransportSecuritySettings`) ; `host_guard.py` l'écrit pour `/api`, avec une différence voulue et documentée (`name:*` accepte aussi `name` sans port, `:9-12`). Il n'y a donc qu'une implémentation dans notre code. Se répètent seulement le test `"*" in hosts` (`mcp_mount.py:223`, `host_guard.py:74`, `:80`) et la lecture `[h.strip() for h in … .split(",") if h.strip()]` des deux variables d'environnement (`settings.py:276-282`, `:284-286`).

### [INFO] Modèles de commande déclarés deux fois dans les schémas (nouveau, voulu)

- **Localisation** : requêtes bornées `document-parser/api/schemas.py:169-205` ; charges stockées `:306-372`
- **Constat** : chaque type de commande a un modèle de requête (avec bornes) et un modèle de relecture (sans bornes, `extra="forbid"`). C'est justifié en commentaire (`:306-310` : une ligne stockée doit toujours se relire). Pas de règle métier redéfinie.

### [INFO] Deux composants « canvas PDF.js ou PNG de repli » (reconduit sous une autre forme)

- **Localisation** : `frontend/src/features/document/ui/PageRaster.vue:1-19` (nouveau) ; `frontend/src/features/document/ui/PdfPagePreview.vue:1-18`
- **Constat** : `18cdf1b` fait passer `PagePreviewWithOverlay` par `PageRaster`, qui remplace la copie qui y était en ligne. `PdfPagePreview` garde sa propre version (gestion d'erreur et événements différents). Toujours deux écritures, pas trois.

### [INFO] Chemin de la route d'import écrit deux fois (nouveau, `efc0bc5`)

- **Localisation** : `document-parser/main.py:98` (`"/api/analyses/import"`) ; `document-parser/api/analyses.py:75` (`"/import"` sous le préfixe du routeur)
- **Constat** : le commentaire de `main.py:98` signale le lien. Un renommage de la route désactiverait la limite sans erreur.

### [INFO] Mise en place de la base de test recopiée dans `test_document_analysis_repo.py` (nouveau)

- **Localisation** : `document-parser/tests/test_document_analysis_repo.py:33-34`, `:58-59`, `:83-84`, `:101-102`, `:125-126`, `:151-152`, `:165-166`
- **Constat** : `monkeypatch.setattr(database, "DB_PATH", …)` + `init_db()` sept fois (trois sur `b5f8c7f`), là où `tests/test_current_analysis.py:55-71` a une fixture. Hors cible stricte de la fiche.

### [INFO] Les deux nouveaux tokens partagent la valeur d'un token existant (reconduit)

- **Localisation** : `frontend/src/app/App.vue:106` / `:111` (`#f59e0b`) ; `:112` / `:132` (`#ea580c`)

### [INFO] `--warning-muted` non redéfini en thème clair (reconduit)

- **Localisation** : `frontend/src/app/App.vue:99`

### [INFO] En-têtes de sécurité nginx répétés dans le bloc `/assets/` (reconduit, inchangé)

- **Localisation** : `nginx.conf.template:14-17` et `:29-32` ; `frontend/nginx.conf.template:14-17` et `:29-32`

### [INFO] Fabriques de PDF de test recopiées (reconduit, inchangé)

- **Localisation** : `document-parser/tests/test_document_export_range.py:33-40`, `document-parser/tests/test_page_raster_real.py:29-37`, `document-parser/tests/test_analysis_service.py:328-331` ; helper existant `pdf_with_pages`, `tests/test_document_service.py:121`

### [INFO] Adaptateurs PDF construits à deux endroits (reconduit)

- **Localisation** : `document-parser/bootstrap/builder.py:194-195` contre `document-parser/bootstrap/factories.py:321`, `:327`

### [INFO] Règle de fusion écrite deux fois dans le front, en accord avec le backend (5.7 conforme)

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:84`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:294` ; `document-parser/domain/analysis_editing.py:228`

### [INFO] Boilerplate `try/except ServiceError → to_http_error` route par route (inchangé)

### [INFO] Formatage de dates : helper partagé ignoré (reconduit, déplacé)

- **Localisation** : `frontend/src/shared/format.ts:29` ; copies `frontend/src/pages/AnalysisDetailPage.vue:100`, `frontend/src/pages/AnalysisLibraryPage.vue:159` ; variante déplacée de l'éditeur vers `frontend/src/features/analysis-editor/ui/AnalysisEditHistoryPanel.vue:71`

### [INFO] Garde « modifications non enregistrées » en deux copies (inchangé)

- **Localisation** : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:406`, `frontend/src/pages/AnalysisDetailPage.vue:95`

### [INFO] `fetch()` brut justifié (5.5 conforme, inchangé)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:135`

### [INFO] Deux tests couvrent le même cas de cache corrompu (inchangé)

- **Localisation** : `document-parser/tests/test_analysis_editing.py:707` et `:1027`

### [INFO] Deux composants de dessin des bbox (reconduit, lecture des tokens unifiée)

- **Localisation** : `frontend/src/features/analysis/ui/BboxOverlay.vue`, `frontend/src/features/document/ui/BboxCanvas.vue`
- **Constat** : les trois façons de lire un token sont devenues une (`shared/cssTokens.ts`). Les deux composants de dessin restent.

---

## Équivalence des règles unifiées

Lu, pas exécuté. Ancien code lu par `git show b5f8c7f:<chemin>`.

| Règle | Anciennes copies (`b5f8c7f`) | Règle unifiée (`efc0bc5`) | Verdict |
|-------|------------------------------|---------------------------|---------|
| Hash d'une commande (persisté) | `services/analysis_edit_service.py:399-403` et `persistence/analysis_edit_repo.py:211-215` : `sha256(f"{previous}\|{sequence}\|{type}\|{version}\|{payload}")`, payload `json.dumps(sort_keys=True, separators=(",", ":"))` | `domain/analysis_editing.py:143-160` ; appelé par `persistence/analysis_edit_repo.py:165-166` | **Équivalent.** Même chaîne, même ordre, même JSON (`ensure_ascii` par défaut dans les deux), même encodage UTF-8. Le chaînage reste `previous_hash = command_hash` (`analysis_edit_repo.py:161`, `:191`), `""` au départ. Les hash stockés restent valides. |
| Hash du flux (cache) | `_hash_stream`, `analysis_edit_service.py:385-396` | `hash_command_stream`, `domain/analysis_editing.py:168-184` | **Équivalent.** Même amorce (`stored[-1].command_hash` ou `""`), mêmes hash stockés digérés dans l'ordre, puis chaque commande en attente chaînée à la séquence `dernière + offset` (offset depuis 1). |
| Contrôle de séquence | 3 écritures : service `save` et `set_command_active` (« The editor stream changed: expected {e}, actual {a} »), dépôt (« Edit stream changed: expected sequence {e}, actual sequence {a} ») | `check_expected_sequence` + `EDITOR_SEQUENCE_CONFLICT` / `STORED_SEQUENCE_CONFLICT` (`domain/analysis_editing.py:209-220`) ; appels `analysis_edit_service.py:155`, `:183`, `analysis_edit_repo.py:158-160` | **Équivalent.** Mêmes textes au caractère près, même classe `AnalysisEditConflictError`, même condition `actual != expected`. |
| Découpe de chunk | service `chunk_service.py:274-310` (la règle appliquée) ; domaine `chunk_editing.split` (tests seulement, ids hex, sans bbox) | `domain/chunk_editing.py:161-192`, appelé par `services/chunk_service.py:239-260` | **Équivalent au chemin de production.** Même borne `0 < offset < len` avec le même message (« cursorOffset … out of range for chunk of length … ») traduit en `ChunkValidationError` ; tête à la séquence source, queue à `+1` ; titres, page source, bbox et doc items copiés ; `token_count` à None ; ids et dates par défaut de `Chunk` (UUID avec tirets, comme avant) ; décalage, suppression douce et insertion inchangés dans le service. L'ancienne version du domaine, divergente, n'était appelée que par les tests. |
| Fusion de chunks | service `chunk_service.py:312-357` | `domain/chunk_editing.py:118-158`, appelé par `services/chunk_service.py:262-290` | **Équivalent.** Même contrôle « au moins 2 ids » avant toute lecture, avec le même message ; même `ChunkNotFoundError` pour les absents (resté dans le service) ; tri par séquence, contiguïté stricte → `ChunkMergeGapError` traduite en `ChunkConflictError` avec le même message ; texte joint par `\n`, titres et page du premier, bbox et doc items concaténés dans l'ordre, somme des tokens ou None ; séquence du premier ; même suppression douce. |
| Ids et horloge | 4 paires : `models.py` (UUID tirets), `chunk_service.py` (tirets), `chunk_editing.py` (hex), `version_service.py` (hex) | `get_utc_now`, `generate_id` (tirets), `generate_compact_id` (hex), `domain/models.py:28-45` | **Équivalent.** Chaque appelant garde son format : versions et chunks d'une restauration en hex (`version_service.py:113`, `:137`, `:209`), insertion de chunk en hex (`chunk_editing.py:66`), push en tirets (`chunk_push_service.py:233`), entités par défaut en tirets. |
| Règles d'édition sur valeurs simples | `infra/docling_editor.py` (`b5f8c7f`) : version, niveau de titre, fusion, suppression multiple, cible de déplacement | `domain/analysis_editing.py:232-276`, appelées par `infra/docling_editor.py:122`, `:157`, `:184-185`, `:218`, `:224`, `:283` | **Équivalent.** Mêmes conditions et mêmes messages. Le test de titre existant ne tourne que pour le niveau 0, comme avant. La fusion garde l'ordre : regroupement (`_gather_merge_run`) puis jointure (`_join_merged_text`) ; le trait d'union conditionnel est maintenant écrit comme caractère U+00AD littéral au lieu de `"­"` (mêmes octets, vérifié). |
| Marche des titres : index de parse | `parse_index.py:94-111` | `parse_index.py:151-161` | **Équivalent.** Texte avant le premier titre : fil d'Ariane vide. H1 → H3 : H3 sous H1. Titre après des sections : niveau 0, ferme tout, puis contient la suite. Titre sans niveau ou non numérique : niveau 1. Document vide : rien. Fins de section identiques (`closed` = ce que l'ancien `pop()` fermait ; fin de document pour le reste). |
| Marche des titres : plan MCP | `outline_builder.py:75-124` (sentinelle -1) et `:154-168` | `outline_builder.py:76-127`, `:157-167` | **Équivalent.** La sentinelle -1 et la pile vide donnent les mêmes rattachements, aucun niveau n'étant négatif (`get_heading_level` ≥ 0). Profondeur : même compte des niveaux ouverts > 0 après fermeture ; un titre refusé ferme sans s'ouvrir, comme l'ancien `continue` placé après les `pop()`. Arrêt sur `max_nodes` au même point. Moins de 2 titres (dont document vide) : mode pages, inchangé. |
| Marche des titres : arbre des chunks | `chunk_service.py:789-843` | `domain/document_tree.py:34-103` | **Équivalent.** Mêmes labels de titre (`HEADING_LABELS` = `{"title","section_header"}`), niveau 0 pour `title`, `max(int(level or 1), 1)` sinon ; un niveau non numérique lève toujours `ValueError`. Seule nuance : les niveaux de tous les éléments sont lus avant de construire les nœuds, donc l'erreur part avant toute construction au lieu d'en cours de route ; le résultat (exception) est le même. |
| Marche des titres : arbre de l'éditeur | `docling_projector.py:163-213` | `docling_projector.py:101-106`, `:192-203` | **Équivalent.** Même définition (`SectionHeaderItem` ou label `title`), même niveau `int(level or 0)`, mêmes rattachements (pile vide = racine). `placed[step.parent]` est indexé par position, chaque pas ajoutant une entrée : correct. |
| Erreurs preview / pages | routes `api/documents.py:150-196` (`b5f8c7f`) | `services/preview_service.py:79-138`, routes `api/documents.py:161-190` | **Diffère, voulu et annoncé** (message de `ac7ac17`). Une erreur hors lecture du PDF (base, cache) répondait 422, elle répond maintenant 500 (`preview_service.py:80`, `:92`, `:96`, `:102`). Effet de bord non annoncé, marginal : un `ValueError` levé hors du rasteriseur (par exemple un chemin avec un octet nul) répondait 404 avec son message (`api/documents.py:166` sur `b5f8c7f`), il répond 422 « Failed to generate preview » (`preview_service.py:136-138`). FNF → 404 « PDF file not found on disk », `OSError` → 422 « Failed to read PDF file », et le reste → 422 avec le même texte qu'avant : inchangés. Clé de cache identique (chemin résolu en `str`, taille, mtime_ns). |
| Analyse courante | sélection seule (`analysis_edit_service.py:102-105`, `:285-288` sur `b5f8c7f`) | `CurrentAnalysisResolver` (`services/current_analysis.py:35-56`) et `resolve_current_analysis_id` (`domain/models.py:193-209`) | **Diffère, voulu** (message de `4939413`). Pour un document **sans ligne d'état** (base que l'upgrade 0.7.3 n'a pas atteinte), l'éditeur et `load_active_result` prennent maintenant la dernière analyse parsée au lieu de répondre « no active analysis » (`analysis_edit_service.py:103`, `:270-273`). Conséquence non écrite dans le CHANGELOG : sur un tel document, un enregistrement rafraîchit désormais le graphe (`analysis_edit_service.py:162`), ce que l'ancien `selection.analysis_id == base.id` excluait. Un document avec une ligne d'état se comporte comme avant. |

Aucun écart de comportement non voulu sur les hash, les messages de séquence, la découpe, la fusion ou la
marche des titres.

---

## Delta vs contrôle

Base : `fix/0.7.4-editor-followups` @ `b5f8c7f`, score 83, 0 CRIT / 1 MAJ / 16 MIN / 14 INFO.

| Ecart du contrôle | Niveau | Statut sur efc0bc5 | Vérification |
|-------------------|--------|--------------------|--------------|
| Pile de titres x4 | MAJ | **Résolu** (`d3059c6`) | 1 boucle (`heading_tree.py:72`), 4 appels, aucun `pop()` de titre ailleurs |
| Teintes, voiles et hex sans token | MIN | Inchangé | 32 / 5 / 14 / 7 |
| Répétitions internes éditeur | MIN | Réduit | séquence : 7 → 1 ; `Query(alias=…)` : 8 → 8 |
| Hash des commandes x2 | MIN | **Résolu** (`d3059c6`) | `hash_command` seul, octets identiques |
| Mappings de réponse / appels d'API | MIN | Inchangé | `?analysisId=` 9 → 8 |
| Résidus contrat d'erreur | MIN | Réduit (`ac7ac17`) | échelle `except` 2 → 0 ; 409/404/[] et 2 « Document not found » en route restent |
| Seconde extraction de pages | MIN | Inchangé | |
| Magic numbers éditeur/PDF | MIN | Réduit | `text`/`paragraph` 4 → 3, nommé côté backend |
| Pont MCP Apps | MIN | Inchangé | fichiers non modifiés |
| Import d'analyse x3 | MIN | Inchangé | fichiers non modifiés |
| Parse booléen | MIN | Inchangé | 9 |
| Labels Docling | MIN | Inchangé, déplacé | `_get_label_type` passé dans `domain/document_tree.py` |
| `.field-*` | MIN | Inchangé | |
| Bornes de chunking | MIN | Inchangé | |
| `@keyframes spin` | MIN | Inchangé | 17 |
| Palette Neo4j | MIN | Inchangé | 70 |
| `_get_utc_now`/`_generate_id` x4 | MIN | **Résolu** (`d3059c6`) | 1 horloge, 2 générateurs, formats gardés (INFO : contournés par l'éditeur) |
| INFO « résolution de l'analyse active faite deux fois » | INFO | **Résolu** (`4939413`) | un seul résolveur |
| INFO « contrat du modèle d'éditeur écrit à la main, hors Pydantic » | INFO | **Résolu** (`efc0bc5`) | réponses typées, `extra="forbid"` |
| INFO « trois lectures d'un token en JS » (dans « deux composants bbox ») | INFO | **Résolu** (`453a1b9`) | `createCssTokenReader` ; les deux composants restent (INFO) |
| Autres INFO (11) | INFO | Inchangés | |

**Résolus** : 1 MAJ, 2 MIN (hash, horloge/ids), 2 INFO. **Réduits** : 3 MIN (répétitions éditeur, contrat d'erreur, magic strings).
**Nouveaux** : 0 MAJ, 0 MIN, 8 INFO (deux lectures du niveau de titre, horloge contournée, comptage de corps x2, liste d'hôtes lue deux fois, modèles de commande x2, `PageRaster`/`PdfPagePreview`, chemin d'import x2, base de test recopiée).
**Copie laissée à côté de la version partagée** : aucune. Les anciennes fonctions (`_hash_command` x2, `_hash_stream`, `_build_tree_nodes`, les quatre `_get_utc_now`/`_generate_id`, l'échelle `except` des routes, les `readToken`/`getComputedStyle` des canvas) ont disparu. Les méthodes restées dans `ChunkService` (`diff_against_store`, `push_to_store`, `list_pushes`, `get_tree`, `chunk_service.py:378-398`) délèguent à `ChunkPushService` et `DocumentTreeService`, sans corps recopié. `_build_cache` sert à `save` et `rebuild` (`analysis_edit_service.py:159-161`, `:216`). `require_document` (`services/chunk_errors.py:42`) sert à `ChunkService`, `ChunkPushService` et `DocumentTreeService`.

**Score : 83 → 100 (+17).** MAJ : 1 → 0. MIN : 16 → 14. INFO : 14 → 20.

---

## Points positifs

- **La pile de titres n'existe plus qu'une fois**, et chaque vue garde sa définition du titre par un paramètre, sans changer de comportement sur les cas limites.
- **Les hash persistés restent valides** : même chaîne, même JSON, et le dépôt comme le service passent par la même fonction.
- **Les règles de chunk du domaine sont celles qui tournaient** : l'ancienne version, qui avait divergé (ordre, contiguïté, page source, bbox), est réécrite sur le service au lieu de l'inverse.
- **Les formats d'id sont gardés appelant par appelant** (`generate_id` / `generate_compact_id`), là où une fusion naïve aurait changé la forme des ids de versions.
- **Les bornes de l'éditeur sont nommées et commentées une fois** (`api/schemas.py:152-166`).
- **5.3 n'a pas régressé** malgré quatre nouveaux composants : aucune couleur littérale, et les bandeaux utilisent `color-mix` sur les tokens.

---

## Ce qui n'a pas pu être vérifié

- Rien n'a été exécuté : ni pytest, ni ruff, ni vitest, ni navigateur. L'équivalence est établie par lecture.
- Le script de mesure 5.3 du contrôle n'existe plus ; il a été reconstruit d'après la méthode du rapport et retrouve les mêmes comptes (58, ventilés 32 / 5 / 14 / 7).
- Le comportement du SDK MCP sur `MCP_ALLOWED_HOSTS` n'a pas été relu dans `.venv` : l'affirmation « une seule correspondance dans notre code » porte sur le code du dépôt.

---

## Verdict partiel : GO

0 CRITICAL, 0 MAJOR, score 100 / 100 (>= 80). Les 14 MIN sont des répétitions d'une ligne, des styles et
des chaînes, à traiter au prochain cycle. Rien n'a tourné sur ce commit.

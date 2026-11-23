# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `b5f8c7f`, lu dans l'arbre de travail.
**Nature** : Audit de contrôle après remédiation (seconde passe) ; base : re-audit du 2026-11-18 sur a6fb539.

> **Score 83 / 100 (+16). 5.3 est conforme.**
> La seconde passe (`2d5a80e`) a fait ce que le premier contrôle demandait : les 25 encres
> blanches passent par `var(--on-accent)`, les 9 hex recopiant un token et les 3 copies de
> `--shadow-lg` ont disparu, et les deux canvas lisent leurs couleurs dans les tokens. Ce contrôle
> a trouvé un dernier site, que le premier avait manqué : `StrategyPopover.vue:264` recopiait la
> valeur de `--warning-muted`. `b5f8c7f` l'a remplacé par `var(--warning-muted)`. Re-mesuré sur
> b5f8c7f : aucun littéral de couleur, d'ombre ou d'encre n'a la valeur d'un token, hors
> commentaires et palettes admises. 0 token non défini, 0 repli. Les teintes, voiles et hex sans
> token restent un MIN. 5.1 n'était pas ciblé : la pile de titres existe toujours en 4 copies, et
> c'est le seul MAJ. Les renommages et les derniers commits n'ajoutent aucune copie. GO.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 7 |
| Score | 83 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 16 |
| Ecarts INFO | 14 |

| # | Item | Poids | Conforme | Mesure a6fb539 → a12b744 → b5f8c7f |
|---|------|-------|----------|------------------------------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois | 2 | **Non** | pile de titres 4 → 4 → 4 ; `stored[-1].sequence if stored else 0` 7 → 7 → 7 ; `?analysisId=` 9 → 9 → 9 ; `Query(alias="analysisId")` 8 → 8 → 8 ; parse booléen 9 → 9 → 9 ; `_get_utc_now`/`_generate_id` 4 → 4 → 4 ; `pagesJson` 4 → 1 → 1 |
| 5.2 | Types partagés centralisés | 2 | Oui | aucun `Protocol` défini deux fois ; `05c0ae5` renomme des méthodes de port (`read_page_sizes`, `count_pages`) sans en dupliquer |
| 5.3 | Pas de magic numbers/strings éparpillés | 2 | **Oui** | tokens non définis 17 → 0 → 0 ; replis 71 → 0 → 0 ; littéraux hors palettes 217 → 97 → **58** ; sites contournant un token existant : 33 + canvas (compte du re-audit) → 37 + 2 canvas → **0** (le dernier, `StrategyPopover.vue:264`, corrigé par `b5f8c7f`) ; restes sans token en MIN |
| 5.4 | Logique réactive partagée dans `shared/composables/` | 1 | Oui | pas de nouveau composable dupliqué |
| 5.5 | Config HTTP centralisée | 2 | Oui | un seul `fetch()` brut, justifié (`DownloadDropdown.vue:135`) |
| 5.6 | Schémas Pydantic transforment le domaine | 2 | Oui | `api/schemas.py` inchangé depuis a12b744 |
| 5.7 | Validation à un seul endroit | 1 | Oui | règle de fusion identique front (`commands.ts:84`) et back (`docling_editor.py:220`) |

Poids total : 12. Poids conformes : 2 + 2 + 1 + 2 + 2 + 1 = 10. `score = 10 / 12 × 100 = 83,3 → 83`.

### Méthode de mesure 5.3

Même script que le premier contrôle, sur `frontend/src` (hors `*.test.ts`), relancé sur l'arbre
de travail. Seul changement : la plage des lignes du thème clair dans `App.vue` (125-146 au lieu
de 119-140, deux tokens ajoutés au-dessus). Le script ne compare aux tokens que les hex et les
couleurs nommées. J'ai donc ajouté une seconde passe qui normalise **tous** les littéraux (hex,
`rgb/rgba`, ombres, `white`/`black`) et les compare aux valeurs de tous les tokens, dans les
deux thèmes. Sur 2d5a80e, elle a trouvé `StrategyPopover.vue:264`. Sur b5f8c7f, elle ne trouve
plus que des commentaires (`App.vue:229`, `features/reasoning/kindColors.ts:16-20`) et les
palettes admises (`shared/elementColors.ts`, palette Neo4j). Le script ne compte que les
`var(--x)` : les tokens lus en JS ont été vérifiés à la main (voir plus bas). Seul changement
entre 2d5a80e et b5f8c7f : une ligne de `StrategyPopover.vue`.

| Compteur | a6fb539 | a12b744 | b5f8c7f |
|----------|---------|---------|---------|
| Tokens définis (`:root`) | 22 | 27 | 29 (+ `--chunk-highlight`, `--reasoning`, `App.vue:111-112`) |
| Noms de token utilisés mais jamais définis | 17 (49 usages) | 0 | **0** |
| Tokens définis jamais utilisés | 0 | 0 | 1 pour le script (`--reasoning`), **0 en réalité** : lu en JS, `StructureViewer.vue:171` |
| Replis `var(--x, …)` | 71 | 0 | **0** |
| Littéraux de couleur, total | 297 | 177 | 138 |
| dont table par type partagée (`shared/elementColors.ts`, admise) | 10 | 10 | 10 |
| dont palette du graphe Neo4j (périmètre déprécié, MIN dédié) | 70 | 70 | 70 |
| **dont hors palettes** | **217** | **97** | **58** |
| → encre blanche (`white`, `#fff`, `#ffffff`), rôle de `--on-accent` | 35 | 25 | **0** |
| → hex égal à la valeur d'un token | 33 | 9 | **0** |
| → teintes `rgba(r,g,b,α)` des couleurs de statut/accent | 50 | 33 | 32 (aucune égale à un token ; 33 dont 1 = `--warning-muted` sur 2d5a80e) |
| → ombres et voiles `rgba(0,0,0,α)` | 19 | 17 (dont 3 = `--shadow-lg`) | 14 (dont 0 = `--shadow-lg`) |
| → anneaux de spinner `rgba(255,255,255,α)` | 6 | 5 | 5 |
| → autres hex | 74 | 8 | 7 (`#ea580c` du canvas est devenu `--reasoning`) |
| Couleurs de dessin canvas en dur (`StructureViewer`, `BboxOverlay`) | 3 | 3 | **0** |
| `var(--on-accent)` / `var(--shadow-lg)` / `var(--banner-bg)` | 0 / 1 / 0 | 6 / 1 / 1 | 30 / 4 / 1 (+ `--on-accent` lu en JS, `StructureViewer.vue:172`) |
| `var(--warning-muted)` | 0 | 2 | 3 (`StrategyPopover.vue:264` ajouté) |
| Littéraux égaux à la valeur d'un token (hors commentaires et palettes) | — | 38 (37 listés + 1 manqué) | **0** |

Vérification des tokens lus en JS :

- `--reasoning` : lu une fois par dessin (`StructureViewer.vue:170-172`), utilisé pour le trait,
  le remplissage (`globalAlpha = 0x33 / 255`, `:191`), la pastille et l'anneau de focus (`:187`,
  `:190`, `:217`, `drawVisitBadge` `:237`). Aucun `#ea580c` ne reste hors `App.vue`.
- `--chunk-highlight` : `var()` dans `ChunkPanel.vue:525`, `:529`, `:573`, et lu en JS dans
  `BboxOverlay.vue:142` (`globalAlpha = 0x30 / 255`, `:149`). Aucun `#f59e0b` ne reste hors
  `App.vue`.
- Les couleurs par type des deux canvas viennent de `ELEMENT_COLORS` (`shared/elementColors.ts`),
  avec un suffixe d'alpha hex (`BboxOverlay.vue:131`, `:135` ; `StructureViewer.vue:198`, `:201`).
  C'est la table admise, comme dans `BboxCanvas.vue:112-114`.

Les deux nouveaux tokens ne sont pas des doublons de rôle. `--chunk-highlight` a la valeur de
`--banner-bg` (`#f59e0b`), mais l'un marque un chunk surligné, l'autre colore le fond du bandeau
d'avertissement. `--reasoning` a la valeur de `--accent-hover` en thème clair (`#ea580c`,
`App.vue:132`), mais pas en sombre, et son rôle est autre. Les deux sont constants d'un thème à
l'autre, et c'est voulu (commentaire `App.vue:108-110`). Voir INFO.

---

## Ecarts constates

### [MAJ] Algorithme « pile de titres » recopié quatre fois, avec trois définitions du titre (5.1, reconduit, inchangé)

- **Localisation** : `document-parser/domain/outline_builder.py:94` ; `document-parser/domain/parse_index.py:102` ; `document-parser/services/chunk_service.py:831-834` ; `document-parser/infra/docling_projector.py:189-194`
- **Constat** : non ciblé. Les quatre boucles « dépiler tant que le sommet est >= au niveau courant » sont toujours là, aux mêmes lignes. Leurs divergences n'ont pas changé : racine sentinelle (`len(stack) > 1` dans `outline_builder.py:94` et `chunk_service.py:833`, pile vide ailleurs) ; définition d'un titre (`HEADING_LABELS`, `domain/navigation.py:315` ; littéral `{"title", "section_header"}`, `chunk_service.py:831` ; `isinstance(SectionHeaderItem) or … == "title"`, `docling_projector.py:189`). `05c0ae5` a renommé des fonctions dans `outline_builder.py` et `parse_index.py` sans toucher aux boucles.
- **Regle violee** : item 5.1 (poids 2).
- **Remediation** : un générateur pur `nest_by_heading(items, level_of, is_heading)` dans `domain/`, appelé par les quatre vues ; `HEADING_LABELS` et `heading_level` comme seules définitions. Effort S à M.

### [MIN] Teintes, voiles et hex sans token (5.3 conforme ; reste de l'ancien MAJ)

- **Localisation** :
  - 32 teintes de statut `rgba(r,g,b,α)` figées sur les RGB du thème sombre, aucune égale à un token : `shared/ui/StatusBadge.vue:57-77`, `features/history/ui/HistoryList.vue:155-196`, `features/analysis/ui/AnalysisPanel.vue:170-182`, `features/ingestion/ui/IngestPanel.vue:274-288`, `features/chunking/ui/ChunkPanel.vue:530`, `:574` (teintes de `--chunk-highlight`), `:623`, `:649`, `:774`, `features/document/ui/DocumentList.vue:128`, `features/document/ui/HistoryDrawer.vue:206`, `:211`, `features/analysis/ui/ResultTabs.vue:606`, `:648`, `:661`, `features/chunks/ui/StrategyPopover.vue:265`, `pages/StudioPage.vue:920`
  - 5 anneaux de spinner `rgba(255, 255, 255, 0.3/0.4)`, teinte de `--on-accent` laissée en dur : `features/ingestion/ui/IngestPanel.vue:335`, `features/analysis/ui/AnalysisPanel.vue:144`, `features/chunking/ui/ChunkPanel.vue:792`, `pages/DocChunkTab.vue:213`, `pages/StudioPage.vue:877`. Le sixième spinner passe par `color-mix(… var(--on-accent) …)` (`pages/IngestLaunchDialog.vue`) : deux écritures du même anneau.
  - 14 voiles et ombres noirs, aucun égal à `--shadow-lg` ; l'ombre d'infobulle `0 4px 12px rgba(0, 0, 0, 0.3)` est écrite deux fois (`features/analysis/ui/BboxOverlay.vue:307`, `features/analysis/ui/StructureViewer.vue:439`), le voile `rgba(0, 0, 0, 0.4)` quatre fois (`HistoryDrawer.vue:107`, `ChunkPanel.vue:689`, `StrategyPopover.vue:199`, `ChunksEditor.vue:513`)
  - 7 hex sans token : `features/chunks/ui/StrategyPopover.vue:361-362` (`#b91c1c`, bouton danger, alors que `ChunkPanel.vue:730` utilise `var(--error)` pour le même rôle) ; `pages/DocsLibraryPage.vue:407-409` (bandeau ambre clair) ; `shared/ui/StatusBadge.vue:58` (`#818cf8`) ; `features/document/ui/HistoryDrawer.vue:212` (`#8b5cf6`)
- **Constat** : ce sont les familles que le premier contrôle déclarait non bloquantes. Elles n'ont pas bougé, à part la teinte de `StrategyPopover.vue:264` passée en `var(--warning-muted)` par `b5f8c7f` (32 teintes, 5 anneaux, 14 voiles, 7 hex). Aucun de ces littéraux n'a la valeur d'un token. Ils restent des couleurs sans nom, et les teintes ne suivent pas le thème clair.
- **Regle violee** : item 5.3, sans le rendre non conforme : aucun token existant n'est contourné.
- **Remediation** : `color-mix(in srgb, var(--error) 10%, transparent)` comme dans `IngestLaunchDialog.vue:262-270` ; `--overlay` et `--shadow-tooltip` ; `var(--error)` pour le bouton danger de `StrategyPopover`.

### [MIN] Répétitions internes du service et du routeur de l'éditeur (reconduit, inchangé)

- **Localisation** : `stored[-1].sequence if stored else 0` x7 : `document-parser/services/analysis_edit_service.py:75`, `:134`, `:168`, `:220`, `:256`, `:393`, `document-parser/domain/analysis_editing.py:164` ; `Query(default=None, alias="analysisId")` x8 : `document-parser/api/analysis_edits.py:109`, `:122`, `:139`, `:154`, `:175`, `:198`, `api/document_chunks.py:176`, `api/documents.py:113-116`
- **Regle violee** : item 5.1.
- **Remediation** : `_last_sequence()`, `_check_sequence()` ; `AnalysisIdQuery = Annotated[…]` dans `api/deps.py`.

### [MIN] Formule de hash des commandes écrite dans deux couches (reconduit, inchangé)

- **Localisation** : `document-parser/services/analysis_edit_service.py:399` (`_hash_command`) ; `document-parser/persistence/analysis_edit_repo.py:211` (`_hash_command`)
- **Constat** : même chaîne `previous|sequence|type|version|payload`. `05c0ae5` a renommé `_cache_values` en `_to_cache_params` dans le même dépôt, sans toucher au hash.
- **Regle violee** : item 5.1.
- **Remediation** : `command_hash()` dans `domain/analysis_editing.py`, à côté de `hash_result`.

### [MIN] Mappings de réponse et appels d'API recopiés (reconduit, inchangé)

- **Localisation** : `document-parser/api/analysis_edits.py:24` (`_to_analysis_response`) = `document-parser/api/analyses.py:27` (`_to_response`) ; `ChunkResponse(` x3 : `api/analyses.py:152`, `:176`, `:199` ; `frontend/src/features/document/api.ts:20` et `frontend/src/features/analysis-editor/api.ts:10` (même endpoint) ; `?analysisId=` x9 : `features/document/api.ts:24`, `:74`, `:90`, `features/analysis-editor/api.ts:15`, `:27`, `:39`, `:50`, `:61`, `:75`
- **Regle violee** : item 5.1.
- **Remediation** : `AnalysisResponse.from_job()` ; `withAnalysisId(path, id)` dans `shared/api/`.

### [MIN] Résidus du contrat d'erreur service → HTTP (reconduit, inchangé)

- **Localisation** : même échelle `except FileNotFoundError → 404 "PDF file not found on disk"` / `→ 422 "Failed to read PDF file"` : `document-parser/api/documents.py:169-172` et `:187-190` ; `AnalysisEditUnavailableError` traduite en 409 (`services/chunk_service.py:372-373`) et en 404 (`services/export_service.py:139-140`, `:148-149`) ; « Document not found » écrit dans la route : `api/documents.py:94`, `:104`
- **Regle violee** : item 5.1.
- **Remediation** : erreur de lecture typée levée par le service, un seul statut pour `AnalysisEditUnavailableError`.

### [MIN] Seconde extraction `DoclingDocument → pages` dans le convertisseur distant (reconduit, inchangé)

- **Localisation** : `document-parser/infra/serve_converter.py:52` (`_LABEL_MAP`), `:269`, `:339` ; référence : `document-parser/infra/docling_pages.py`
- **Regle violee** : item 5.1 (2 copies).
- **Remediation** : `DoclingDocument.model_validate(json)` puis `extract_pages_detail`.

### [MIN] Magic numbers et strings de l'éditeur et du rendu PDF (reconduit, inchangé)

- **Localisation** : `{"text","paragraph"}` x4 : `document-parser/infra/docling_editor.py:220`, `document-parser/infra/docling_projector.py:136`, `frontend/src/features/analysis-editor/commands.ts:84`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:366` ; plafond de ratio `2` : `frontend/src/features/document/ui/PdfPageCanvas.vue:54` ; `64 * 1024 * 1024` : `document-parser/infra/preview_cache.py:16` ; `max-age=86400` : `document-parser/api/documents.py:162` ; DPI `150` : `api/documents.py:153`, `domain/navigation.py:63`, `services/navigation_config.py:52` (+ `PREVIEW_DPI`, `frontend/src/features/document/api.ts:47`)
- **Regle violee** : item 5.3.

### [MIN] Pont JSON-RPC MCP Apps recopié dans les deux cartes HTML (reconduit, inchangé)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:497-499`, `:769`, `:816` ; `document-parser/mcp_adapter/sources_app.html:532-534`, `:1155`

### [MIN] Import d'une analyse Docling recopié dans trois composants (reconduit, inchangé)

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:50`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:77`, `frontend/src/features/document/ui/DocumentUpload.vue:119`

### [MIN] Parse booléen d'environnement recopié (reconduit, inchangé)

- **Localisation** : `document-parser/infra/settings.py` : 9 occurrences de `("1", "true", "yes", "on")`

### [MIN] Vocabulaire des labels Docling recopié (reconduit, inchangé)

- **Localisation** : `{"page_header","page_footer"}` : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` ; normalisation d'un label : `document-parser/infra/docling_projector.py:94` (`_get_label`), `document-parser/services/chunk_service.py:829`

### [MIN] Bloc de style `.field-*` des formulaires de store (reconduit, inchangé)

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue`, `StoreForm.vue`

### [MIN] Bornes de chunking dupliquées entre DTO, value objects et popover (reconduit, inchangé)

- **Localisation** : `document-parser/api/schemas.py`, `document-parser/domain/value_objects.py`, `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`

### [MIN] `@keyframes spin` dans 17 SFC (reconduit, inchangé)

- **Remediation** : `shared/ui/AppSpinner.vue`, qui réglerait aussi les deux écritures de l'anneau de spinner.

### [MIN] Palette de la vue graphe Neo4j recopiée (reconduit, périmètre déprécié)

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue:135-146` et `:557-576` ; `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:115-132` ; `frontend/src/features/analysis/legendFilters.ts:38-74`
- **Constat** : 70 littéraux, non touchés. Plusieurs ont la valeur d'un token (`#F97316` = `--accent`, `#3B82F6` = `--info` sombre, `#DC2626` = `--error` clair) : palette de données d'un périmètre déprécié, traitée à part comme dans les contrôles précédents.

### [MIN] Helpers `_get_utc_now` / `_generate_id` recopiés (reconduit, 4 copies)

- **Localisation** : `document-parser/domain/models.py:28-33`, `document-parser/domain/chunk_editing.py:29-34`, `document-parser/services/chunk_service.py:91-96`, `document-parser/services/version_service.py:44-49`
- **Constat** : inchangé. `05c0ae5` a modifié `chunk_editing.py` (`_index_of` → `_find_index`) sans factoriser.
- **Remediation** : `new_id()` / `utc_now()` publics dans `domain/models.py`.

---

### [INFO] Les deux nouveaux tokens partagent la valeur d'un token existant (introduit par `2d5a80e`)

- **Localisation** : `frontend/src/app/App.vue:106` (`--banner-bg: #f59e0b`) et `:111` (`--chunk-highlight: #f59e0b`) ; `:112` (`--reasoning: #ea580c`) et `:132` (`--accent-hover: #ea580c`, thème clair)
- **Constat** : même valeur, rôle différent (fond de bandeau / chunk surligné ; marque de raisonnement / survol de l'accent). Ce ne sont pas des doublons de rôle, et nommer chaque rôle est le but des tokens. Les deux sont identiques dans les deux thèmes, c'est voulu et documenté (`:108-110`). Si l'équipe veut lier les valeurs, `--chunk-highlight: var(--banner-bg)` le ferait.

### [INFO] `--warning-muted` non redéfini en thème clair (reconduit)

- **Localisation** : `frontend/src/app/App.vue:99` (défini dans `:root` seulement) ; utilisé par `features/document/ui/DocTreeNode.vue:133`, `features/chunks/ui/StaleStoresStrip.vue:118`
- **Constat** : en clair, `--warning` vaut `#ca8a04` (`App.vue:144`) mais la teinte reste celle du jaune sombre.

### [INFO] En-têtes de sécurité nginx répétés dans le bloc `/assets/` (reconduit, inchangé)

- **Localisation** : `nginx.conf.template:14-17` et `:29-32` ; `frontend/nginx.conf.template:14-17` et `:29-32`
- **Constat** : répétition nécessaire (un `add_header` de `location` remplace ceux du `server`, commentaire `:24-25`). Pas d'`include` ajouté. Hors cible stricte de la fiche.

### [INFO] Fabriques de PDF de test recopiées (reconduit, inchangé)

- **Localisation** : `document-parser/tests/test_document_export_range.py:30-37`, `document-parser/tests/test_page_raster_real.py:29-37`, `document-parser/tests/test_analysis_service.py:328-329` ; helper existant `pdf_with_pages`, `tests/test_document_service.py:118`
- **Constat** : toujours trois. Le test ajouté par `8436e27` (`tests/test_pdf_inspector.py`, `TestPageSizesStayLight`) réutilise `pdf_with_pages`. `tests/test_bootstrap_pdf_wiring.py` ne crée pas de PDF.

### [INFO] Adaptateurs PDF construits à deux endroits, pages comptées par deux bibliothèques (reconduit)

- **Localisation** : `document-parser/bootstrap/builder.py:178-179` contre `document-parser/bootstrap/factories.py:307-316` ; `document-parser/infra/pdf_inspector.py:44-50` (`count_pages`, pdfium) et `:52-63` (`count_pages_in_bytes`, poppler)
- **Constat** : `8436e27` lit les tailles dans la table des pages (`:38`, `get_page_size`), sans nouveau chemin. Le nouveau test de câblage vérifie `factories.py`, pas `builder.py`.

### [INFO] Règle de fusion écrite deux fois dans le front, en accord avec le backend (5.7 conforme, inchangé)

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:84`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:364-366` ; `document-parser/infra/docling_editor.py:220`

### [INFO] Contrat du modèle d'éditeur écrit à la main, hors Pydantic (inchangé)

- **Localisation** : `document-parser/infra/docling_projector.py`, `document-parser/api/analysis_edits.py`, `frontend/src/features/analysis-editor/types.ts`

### [INFO] Boilerplate `try/except ServiceError → to_http_error` route par route (inchangé)

- **Constat** : la traduction est unique (`api/errors.py:25-31`). Seule la plomberie se répète.

### [INFO] Formatage de dates : helper partagé ignoré (inchangé)

- **Localisation** : `frontend/src/shared/format.ts:26` ; copies `frontend/src/pages/AnalysisDetailPage.vue:99-102`, `frontend/src/pages/AnalysisLibraryPage.vue:159` ; variante `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:414`

### [INFO] Garde « modifications non enregistrées » en deux copies (inchangé)

- **Localisation** : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:506-515`, `frontend/src/pages/AnalysisDetailPage.vue:95`

### [INFO] `fetch()` brut justifié (5.5 conforme, inchangé)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:135`

### [INFO] Deux tests couvrent le même cas de cache corrompu (inchangé)

- **Localisation** : `document-parser/tests/test_analysis_editing.py:668` et `:984`

### [INFO] Deux composants de dessin des bbox (reconduit, divergence de couleurs résolue)

- **Localisation** : `frontend/src/features/analysis/ui/BboxOverlay.vue`, `frontend/src/features/document/ui/BboxCanvas.vue`
- **Constat** : les deux lisent maintenant leurs couleurs dans les tokens (`BboxOverlay.vue:142`, `BboxCanvas.vue:157-158`), mais de deux façons : `getComputedStyle(...).getPropertyValue` en ligne d'un côté, `readToken` local de l'autre, et une troisième fois dans `StructureViewer.vue:170-172`. Un `readCssToken(el, name)` partagé éviterait la troisième écriture.

### [INFO] Résolution de l'analyse active faite deux fois (inchangé)

- **Localisation** : `document-parser/services/analysis_edit_service.py:99-104` (`load_active_result`) et `:287`

---

## Premier contrôle (a12b744)

Score 67 (5/7 items, 8/12 de poids), 0 CRIT, 2 MAJ, 15 MIN, 13 INFO, GO CONDITIONNEL. Le MAJ de
5.3 citait 37 sites contournant un token existant et deux canvas :

| Constat du premier contrôle | Sites | Sur b5f8c7f |
|-----------------------------|-------|-------------|
| Encre blanche au lieu de `var(--on-accent)` (boutons, spinners, pastilles d'interrupteur, canvas) | 25 | **0** : 24 en `var(--on-accent)` (ex. `ChunkPanel.vue:483`, `Composer.vue:122`, `McpConfigSection.vue:663`, spinners `IngestPanel.vue:336`), 1 lu en JS (`StructureViewer.vue:172`) |
| Hex égal à la valeur d'un token | 9 | **0** : `#ef4444` → `var(--error)` (`ChunkPanel.vue:622`, `:729`) ; `#f59e0b` → `var(--chunk-highlight)` (`ChunkPanel.vue:525`, `:529`, `:573`) et lu en JS (`BboxOverlay.vue:142`) ; `#0a0a0b` → `var(--on-bright)` (`McpConfigSection.vue:1041`, `:1047`) ; `#3b82f6` → `var(--info)` (`HistoryDrawer.vue:207`) |
| `--shadow-lg` recopié | 3 | **0** : `DownloadDropdown.vue:264`, `ChunkPanel.vue:703`, `StudioPage.vue:1264` en `var(--shadow-lg)` |
| Canvas en dur dans `StructureViewer.vue` et `BboxOverlay.vue` | 2 fichiers | **Résolu** : `getComputedStyle` une fois par dessin, `globalAlpha` au lieu d'un suffixe d'alpha (`StructureViewer.vue:170-193`, `BboxOverlay.vue:142-151`) |

Le premier contrôle annonçait 83 si ces sites étaient corrigés. `2d5a80e` les a tous corrigés.
Un dernier site, que le premier contrôle avait rangé parmi les teintes, a été trouvé par ce
contrôle (`StrategyPopover.vue:264`, valeur exacte de `--warning-muted`) et corrigé par `b5f8c7f`.

---

## Delta vs re-audit a6fb539

Base : `fix/0.7.4-editor-followups` @ `a6fb539`, score 67, 0 CRIT / 2 MAJ / 18 MIN / 9 INFO.

| Ecart du re-audit | Niveau | Statut sur b5f8c7f | Vérification |
|-------------------|--------|--------------------|--------------|
| Pile de titres x4 | MAJ | Toujours présent, inchangé | 4 boucles, non ciblé |
| Couleurs en dur / tokens non définis | MAJ | **Résolu, 5.3 conforme** ; restes sans token en MIN | 0 nom non défini, 0 repli, 0 littéral égal à un token (encres, hex, rgba, ombres), canvas convertis |
| Répétitions internes de l'éditeur | MIN | Toujours présent | 7 + 8 sites |
| Hash des commandes x2 | MIN | Toujours présent | `_hash_command` x2 |
| Mappings de réponse / appels d'API | MIN | Toujours présent | |
| `history/api.ts` recopie `analysis/api.ts` | MIN | Résolu (a12b744) | réexport |
| Rasterisation x2 | MIN | Résolu (a12b744) | un seul `convert_from_path` |
| Résidus contrat d'erreur | MIN | Toujours présent, réduit | 2 échelles `except`, 409/404 |
| Seconde extraction de pages | MIN | Toujours présent | |
| `pagesJson` x4 | MIN | Résolu (a12b744) | `shared/analysisPages.ts:9` |
| Magic numbers éditeur/PDF | MIN | Toujours présent, réduit | DPI 150 : 3 sites backend |
| Pont MCP Apps | MIN | Toujours présent | |
| Import d'analyse x3 | MIN | Toujours présent | |
| Parse booléen | MIN | Toujours présent | 9 |
| Labels Docling | MIN | Toujours présent | |
| `.field-*` | MIN | Toujours présent | |
| Bornes de chunking | MIN | Toujours présent | |
| `@keyframes spin` | MIN | Toujours présent | 17 |
| Palette Neo4j | MIN | Toujours présent | 70 littéraux |
| `_utcnow`/`_new_id` | MIN | Toujours présent, 4 copies | |
| 9 INFO | INFO | Inchangés | |

**Résolus** : 1 MAJ (5.3), 3 MIN (depuis a12b744). **Nouveaux** : 1 MIN (teintes, voiles et hex sans token, sortis du MAJ 5.3 qui les englobait), 5 INFO (en-têtes nginx, fabriques de PDF de test, double câblage des adaptateurs PDF, `--warning-muted` en clair, valeurs partagées des nouveaux tokens).
**Duplication introduite par la seconde passe et les derniers commits** : aucune dans le code audité. `05c0ae5` ne fait que renommer : aucun nom renommé ne double une fonction existante (`_build_chunk_id`, `build_page_ref`, `_find_index`, `hash_quote`, `_gate_route` sont uniques). `8436e27` remplace une boucle par `get_page_size` et réutilise `pdf_with_pages` dans son test. `2d5a80e` ajoute deux tokens à rôle propre et une troisième écriture de la lecture d'un token en JS (INFO). `b5f8c7f` change une ligne. Les commits CI et docs sont hors cible.

**Score : 67 → 83 (+16).** Seul 5.1 reste non conforme. MAJ : 2 → 1. MIN : 18 → 16. INFO : 9 → 14.

---

## Points positifs

- **Les tokens ne sont plus contournés** : 297 → 138 littéraux de couleur, 217 → 58 hors palettes, et plus aucun littéral n'a la valeur d'un token existant.
- **Les trois canvas lisent les tokens** : `BboxCanvas.vue`, `BboxOverlay.vue`, `StructureViewer.vue`. Le passage à `globalAlpha` évite de coller un suffixe hex à une valeur qui peut ne pas être un hex.
- **Les nouveaux tokens sont documentés** (`App.vue:102-112`) et chacun a un rôle propre.
- **Le thème clair est corrigé au passage** : le rouge et le bleu figés sur le thème sombre (`ChunkPanel.vue:622`, `:729`, `HistoryDrawer.vue:207`) suivent maintenant le thème.
- **Aucune copie introduite** par les renommages ni par le passage aux tailles lues dans la table des pages.

---

## Verdict partiel : GO

0 CRITICAL, 1 MAJOR (5.1, sous le seuil bloquant de 3), score 83 / 100 (>= 80).
Reste à planifier : factoriser la pile de titres dans `domain/` (5.1), puis les MIN au prochain
cycle. Rien n'a été vérifié dans un navigateur.

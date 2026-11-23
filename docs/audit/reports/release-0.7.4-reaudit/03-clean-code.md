# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` au commit `a6fb539` (= `release/0.7.4` @ `f7fc791`, avec #401 et #402, + 13 commits locaux #391-#400 + merge), arbre de travail

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 14 |
| Score | 56 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 9 |

**Calcul** : poids conformes = 10 (3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur un total de 18 → `10 / 18 × 100 = 55,6` → **56**.

Périmètre identique à l'audit du 2026-11-13 : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`), `frontend/src/` (hors `*.test.*`, `*.d.ts`), plus les deux pages HTML du serveur MCP (`mcp_adapter/citation_app.html`, `sources_app.html`). Hors périmètre : `e2e/`, `frontend/scripts/`, `experiments/mcp-bench/` (non suivi).

Méthode : analyse statique, aucun test relancé (résultats fournis : ruff check/format propres, pytest 1501 passés, eslint/prettier/vue-tsc propres, vitest 586 passés). Mesures par scripts sur tout le périmètre, pas par échantillon :

- Python : AST (`document-parser/.venv/bin/python`), longueur = lignes de corps hors signature et docstring, paramètres hors `self`/`cls` (`*args`/`**kwargs` comptés).
- TS/Vue : parseur `frontend/node_modules/typescript` sur les `.ts` et les blocs `<script>` des `.vue`, étendue signature comprise, callbacks `defineStore(...)` exclus.
- Les mêmes scripts lancés sur `git archive eade7fa` redonnent exactement les chiffres de l'audit du 2026-11-13 (127 fichiers / 21 615 l., 53 fonctions > 30 l., 36 signatures > 4 paramètres ; front 158 fichiers / 28 631 l., 30 fichiers > 300 l., 18 fonctions > 30 l., 1 signature > 4). Les deux scores sont donc comparables, avec les mêmes seuils.

---

## Metriques

| Mesure | 2026-11-13 (`eade7fa`) | 2026-11-18 (`a6fb539`) | Offenders à corriger pour passer l'item |
|--------|------------------------|------------------------|------------------------------------------|
| Fichiers `.py` source | 127 (21 615 l.) | 133 (21 880 l.) | — |
| Fichiers `.vue`/`.ts` source | 158 (28 631 l.) | 161 (29 049 l.) | — |
| `.py` > 300 lignes | 17 | 17 | 17 |
| `.vue`/`.ts` > 300 lignes (i18n compris) | 30 | 30 | 30 (29 hors `i18n.ts`) |
| Fonctions Python > 30 lignes | 53 | **52** | 52 |
| Fonctions TS/Vue > 30 lignes | 18 | **21** | 21 |
| Fonctions Python > 4 paramètres | 36 | **37** | 37 |
| Fonctions TS > 4 paramètres | 1 | 1 | 1 |
| Paramètres booléens Python (tous types `bool`) | 21 | 18 | 0 flag réel restant (voir 3.2.4) |
| Code commenté laissé en place | 0 | 0 | — |
| Libellés français hors table de messages (cartes MCP) | ~64 | **0** | — |
| Libellés anglais de l'éditeur hors i18n | ~12 | **1** | — |

Détail des variations :

- **Fichiers > 300** : même liste qu'au 13. Grossissent : `domain/ports.py` 576 → 633, `services/analysis_edit_service.py` 378 → 405, `AnalysisEditor.vue` 759 → 804, `PagePreviewWithOverlay.vue` 726 → 761, `EditableStructureNode.vue` 311 → 324, `BboxOverlay.vue` 312 → 323, `StructureViewer.vue` 438 → 445, `shared/i18n.ts` 1600 → 1642. Maigrissent : `chunk_service.py` 935 → 921, `StudioPage.vue` 1450 → 1444, `analysis-editor/store.ts` 441 → 437, `store_service.py` 395 → 391. Les nouveaux fichiers de #401 restent courts (`PdfPageCanvas.vue` 101, `PdfPagePreview.vue` 48, `usePdfDocument.ts` 47, `preview_service.py` 50, `preview_cache.py` 40).
- **Fonctions Python > 30** : sortent `export_service.export` (49, découpée) et `analysis_repo.update_status` (34, remplacée par `complete_and_select`) ; entre `services/export_service.py:75` (`_export`, 32). Pire offenders inchangés : `infra/neo4j/tree_writer.py:69` (227), `infra/neo4j/queries.py:137` (115), `infra/neo4j/chunk_writer.py:55` (107), `services/chunk_service.py:474` (103), `bootstrap/builder.py:104` (93).
- **Fonctions TS > 30** : nouvelles `features/document/ui/usePdfDocument.ts:7` (41), `features/document/ui/PdfPageCanvas.vue:30` (`render`, 38), `pages/AnalysisDetailPage.vue:107` (callback `onMounted`, 36) ; aggravées `features/analysis/ui/StructureViewer.vue:147` (`drawOverlay`, 66 → 72), `features/analysis/ui/BboxOverlay.vue:85` (`draw`, 61 → 67) ; améliorée `PagePreviewWithOverlay.vue:392` (`setupObserver`, 53 → 37). Pires : `GraphView.vue:193` (216), `BboxCanvas.vue:80` (120).
- **Paramètres** : entre `api/documents.py:174` (`preview`, 5) ; `analysis_edit_service.py:54` (`__init__`) passe de 9 à 8. Front : sort `setAnalysisEditActive` (objet de changement), entre `features/document/ui/PagePreviewWithOverlay.logic.ts:14` (`pageInRenderWindow`, 6).

---

## Checklist

| # | Item | Poids | Conforme | Justification (mesures) |
|---|------|-------|----------|-------------------------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | non | Éditeur renommé (#397), mais ~50 fonctions restent nommées par leur résultat, surtout `mcp_adapter/` (inchangé) et 6 nouvelles (`export_service.py:114-142`, `analysis_edit_service.py:401`) |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | Pas de régression ; `L` global des cartes MCP et `document` qui masque `window.document` notés en INFO |
| 3.1.3 | Code en anglais, traductions dans i18n | 2 | oui | Cartes MCP : 0 libellé français hors `MESSAGES` (anglais par défaut, table en/fr) ; éditeur : 1 phrase serveur résiduelle (INFO), même tolérance que les ~4 libellés anglais préexistants acceptés au 13 |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | Nouveau code : `dpi`, `pdfjs`, `bbox`, conventions établies |
| 3.2.1 | Une fonction = une chose | 2 | non | 9 fonctions d'orchestration reconduites sur 10 (seul `export` corrigé) + 1 nouvelle (`AnalysisDetailPage.vue:107`) |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | non | 52 Python + 21 TS = 73 offenders (71 au 13) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | non | 37 Python + 1 TS = 38 offenders (37 au 13) |
| 3.2.4 | Pas de flag arguments | 1 | oui | `select_analysis`, `edited` (service), `additive` retirés ; restent des booléens de données ou de configuration, plus le paramètre HTTP `edited` (INFO) |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | Nouveaux `get_preview` (cache LRU idempotent, INFO) et `get_preview_service` (lecture pure) |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | non | 17 `.py` + 30 `.vue`/`.ts` = 47 offenders (inchangé) |
| 3.3.2 | Un concept par fichier | 2 | non | `chunk_service.py`, `analysis-editor/store.ts`, `AnalysisEditor.vue` inchangés dans leur structure ; `PagePreviewWithOverlay.vue` porte désormais deux moteurs de rendu |
| 3.3.3 | Imports ordonnés | 1 | oui | `ruff` règle `I` active (`pyproject.toml:87`) et propre ; nouveaux fichiers front lus : vue, deps, puis local |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | Nouveaux commentaires explicatifs (`PdfPageCanvas.vue:41-42`, `preview_service.py:41`, `AnalysisDetailPage.vue:125-126`, `:134-135`) ; 3 commentaires périmés en INFO |
| 3.4.2 | Pas de code commenté | 1 | oui | Grep sur tout le périmètre : 2 hits, tous deux de la prose (`mcp_stdio.py:50`, `serve_converter.py:40`) |

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration multi-responsabilités (reconduit, 1 nouveau cas)

- **Localisation** :
  - reconduits, inchangés : `document-parser/services/chunk_service.py:474` (`push_to_store`, 103 l.), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l.), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.), `document-parser/domain/parse_index.py:80` (`build_index`, 79 l.), `document-parser/services/analysis_service.py:460` (`_finalize_analysis`, 67 l.), `document-parser/services/analysis_edit_service.py:135` (`save`, 66 l.), `document-parser/infra/docling_editor.py:204` (`_merge_text`, 50 l.), `document-parser/infra/docling_editor.py:261` (`_move_element`, 47 l.), `frontend/src/features/document/ui/BboxCanvas.vue:80` (`draw`, 120 l.) ;
  - nouveau : `frontend/src/pages/AnalysisDetailPage.vue:107` (callback `onMounted`, 36 l.).
- **Constat** :
  - `save` crée toujours le flux et relit en cas de course (`:149-161`), contrôle la séquence (`:165-170`), construit le cache (`:176-187`), lit la sélection (`:188`), persiste, puis rafraîchit le graphe en avalant l'erreur (`:196-206`).
  - `_move_element` porte toujours deux protocoles : `placement` (`:269`) et l'ancien `beforeElementId` (`:295`).
  - Le nouveau `onMounted` d'`AnalysisDetailPage.vue` charge la liste complète des résumés pour en trouver un (`:109`), fabrique une analyse provisoire à partir du manifeste de pages (`:111-119`), recharge l'analyse complète (`:123`), puis gère deux chemins de reprise avec un `try` imbriqué dans le `catch` (`:124-138`).
  - Résolu : `export_service.export` (cascade dupliquée remplacée par `_export` + `_original_analysis` / `_edited_analysis`, `services/export_service.py:49-149`).
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** : inchangée pour les 9 cas reconduits (`save` → `_ensure_stream`, `_check_sequence`, `_cache_from`, `_refresh_graph` ; `_move_element` → `_move_relative` + `_move_before` ; `draw` → `drawBoxes` / `drawNextMarker` / `drawOrderBadges`, etc.). `AnalysisDetailPage` : sortir `loadPreviewFromSummary(id)` et `loadFullAnalysis(id)` dans le store `analysis`, le hook ne fait plus que les enchaîner. Pour passer l'item au seuil de l'audit du 13, les 10 fonctions listées sont à découper ; le périmètre Neo4j (3 fonctions) peut être sorti si la retraite 0.8.0 est actée et tracée.

### [MAJ] Fichiers fourre-tout (reconduit, 1 cas aggravé)

- **Localisation** : `document-parser/services/chunk_service.py:133` (classe `ChunkService`, push/diff `:440`, `:474`, `:593`, `:643`, `:665`, projection d'arbre `:689`, `:787`, `:844`, `:877`, `:892`) ; `document-parser/mcp_adapter/sources_view.py` (inchangé) ; `frontend/src/features/analysis-editor/store.ts` (setup unique : aperçu avec `AbortController` `:32`/`:207`, undo/redo `:117`/`:131`, sélection de fusion `:171`, brouillon `sessionStorage` `:349-381`) ; `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:1-305` (barre d'outils, bannière de conflit `:126`, récupération `:140`, panneau d'historique `:166`, arbre, aperçu, édition) ; **aggravé** : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:96-114` et `:238-318`.
- **Constat** :
  - `chunk_service.py` (921 l.) porte toujours trois concepts : édition du chunkset, push/diff vers un store, projection d'arbre.
  - L'éditeur n'a pas été découpé ; `AnalysisEditor.vue` grossit (759 → 804 l., template 305 l.).
  - `PagePreviewWithOverlay.vue` (761 l., script 430 l.) ajoute à la navigation, au scroll et à l'overlay un second moteur de rendu : canvas PDF.js et `<img>` de repli dans le même template (`:96-114`), avec deux jeux de handlers quasi identiques (`registerImage` `:238` / `registerPdf` `:248`, `onImageLoad` `:289` / `onPdfReady` `:307`, `onImageError` `:302` / `onPdfError` `:314`) et trois ensembles d'état de page (`loaded`, `settled`, `pending`). Le composant `PdfPagePreview.vue` créé par #401 encapsule exactement ce choix canvas / repli, mais n'est pas réutilisé ici.
- **Regle violee** : item 3.3.2 (poids 2).
- **Remediation** : `chunk_service.py` → sortir `services/tree_projection.py` (5 fonctions, effort S) et le push vers `services/chunk_push_service.py`. Éditeur → `usePendingDraft(key)`, `useMergeSelection()`, `AnalysisEditHistoryPanel.vue`, `EditorBanners.vue`. Aperçu → un composant `PdfPageFrame` (canvas ou repli + suivi `pending/settled`) utilisé par `PagePreviewWithOverlay` comme `PdfPagePreview` l'est par `PagePreview`. Pour passer l'item : ces 4 fichiers (et `sources_view.py`, cité au 13).

### [MIN] Nommage : fonctions nommées par leur résultat (reconduit, réduit dans l'éditeur, étendu ailleurs)

- **Localisation** : résolu dans l'éditeur (`api/analysis_edits.py:28` `_to_analysis_response`, `:48` `_serialize_tree`, `:57` `_to_editor_response`, `persistence/analysis_edit_repo.py:20` `_to_stream`, `services/analysis_edit_service.py` `list_history` / `load_active_result`, front `findFoldTarget`, `parseAnalysisPages`). Restent ou apparaissent : `document-parser/services/export_service.py:114` (`_original_analysis`), `:125` (`_requested_analysis`), `:136` (`_active_analysis`), `:142` (`_edited_analysis`), `document-parser/services/analysis_edit_service.py:277` (`_base_analysis`), `:350` (`_snapshot`), `:401` (`_command_hash`), `document-parser/infra/docling_projector.py:216` (`_element_dict`), `frontend/src/features/document/ui/BboxCanvas.vue:65` (`badgeRect`), et le package MCP inchangé : `document-parser/mcp_adapter/sources_view.py:223` (`sources_card`), `:278` (`_hop`), `:297` (`_passage`), `:323` (`_node`), `document-parser/mcp_adapter/wire_mapping.py:46` (`document_row`), `:120` (`citation_out`), `:165` (`excerpt_result`), `document-parser/services/source_service.py:224` (`_marks`), `:234` (`_title`), `:243` (`text`).
- **Constat** : un scan heuristique (premier mot du nom absent d'une liste de ~250 verbes) relève 202 noms Python (208 au 13) ; une fois retirés les faux positifs (`ping`, `health_check`, `_row_to_*`, `soft_delete*`, `lifespan`), il reste environ 50 fonctions nommées par la valeur qu'elles renvoient. #397 a corrigé l'éditeur mais #397 lui-même a introduit les quatre `_*_analysis` de `export_service.py`.
- **Regle violee** : item 3.1.1 (poids 1).
- **Remediation** : soit renommer (~50 fonctions, renommages mécaniques : `_resolve_original_analysis`, `_load_requested_analysis`, `_build_snapshot`, `_hash_command`, `build_sources_card`…), soit acter dans la fiche 3.1.1 que les helpers privés purs peuvent porter le nom de leur résultat (proposé depuis 0.7.3). La seconde option fait passer l'item sans toucher au code si les fonctions publiques restantes (`sources_card`, `document_row`, `citation_out`, `excerpt_result`, `text`) sont renommées. C'est le levier le moins cher du rapport (+1 poids, 56 → 61).

### [MIN] Fonctions au-delà de 30 lignes (52 Python, 21 TS)

- **Localisation** : nouvelles : `frontend/src/features/document/ui/usePdfDocument.ts:7` (41), `frontend/src/features/document/ui/PdfPageCanvas.vue:30` (38), `frontend/src/pages/AnalysisDetailPage.vue:107` (36), `document-parser/services/export_service.py:75` (32) ; aggravées : `frontend/src/features/analysis/ui/StructureViewer.vue:147` (66 → 72), `frontend/src/features/analysis/ui/BboxOverlay.vue:85` (61 → 67), `document-parser/bootstrap/builder.py:104` (92 → 93) ; pires : `document-parser/infra/neo4j/tree_writer.py:69` (227), `frontend/src/features/analysis/ui/GraphView.vue:193` (216).
- **Constat** : 73 offenders au total (71 au 13). Sortis : `export_service.export`, `analysis_repo.update_status`. `usePdfDocument` et `render` restent cohérents (une seule tâche, avec annulation par génération) ; leur longueur vient de la gestion de course, pas d'un mélange de responsabilités.
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : item hors d'atteinte pour 0.7.4 (73 fonctions). Priorité aux 10 fonctions du MAJ 3.2.1, qui comptent aussi ici.

### [MIN] Fonctions à plus de 4 paramètres (37 Python, 1 TS)

- **Localisation** : nouvelles : `document-parser/api/documents.py:174` (`preview`, 5), `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14` (`pageInRenderWindow`, 6 dont 2 booléens positionnels) ; reconduites : `document-parser/services/chunk_service.py:136` (12), `document-parser/services/store_service.py:233` (10), `document-parser/services/analysis_service.py:83` (9), `document-parser/services/analysis_edit_service.py:54` (8), `:209` (`set_command_active`, 5), `document-parser/persistence/analysis_edit_repo.py:211` (`_hash_command`, 5).
- **Constat** : 38 offenders (37 au 13). `setAnalysisEditActive` est corrigé (objet de changement). `pageInRenderWindow(pageNumber, currentPage, viewMode, focusedPage, currentPageSettled, alreadyRequested)` reprend le motif signalé au 13 : deux booléens consécutifs, appelés positionnellement (`PagePreviewWithOverlay.vue:327-334`), qu'une inversion ne ferait pas détecter par le typage. `preview` est une route FastAPI dont 3 paramètres sont des `Query` ; atténuant.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : `pageInRenderWindow(pageNumber, { currentPage, viewMode, focusedPage, currentPageSettled, alreadyRequested })`. Item hors d'atteinte pour 0.7.4 (38 signatures, dont 12 constructeurs keyword-only).

### [MIN] Fichiers sources au-delà de 300 lignes (17 Python, 30 front)

- **Localisation** : voir « Métriques ». Plus gros : `document-parser/api/schemas.py` (939), `document-parser/services/chunk_service.py` (921), `document-parser/domain/ports.py` (633, +57 avec le port `PreviewImageCache` `:143-151` et ceux de #394), `frontend/src/shared/i18n.ts` (1642, données), `frontend/src/pages/StudioPage.vue` (1444), `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue` (804).
- **Constat** : liste inchangée en nombre (47) ; 8 fichiers grossissent, 4 maigrissent.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4 (47 fichiers). Les découpages du MAJ 3.3.2 en retirent 3 à 4.

### [INFO] Résidus de 3.1.3 (item jugé conforme)

- **Localisation** : `document-parser/infra/docling_projector.py:147` (« … elements are not editable yet. », affiché tel quel par `frontend/src/features/analysis-editor/ui/ElementEditPanel.vue:34`) ; préexistants tolérés au 13 : `frontend/src/app/App.vue:31` (`aria-label="Close"`), `frontend/src/features/document/ui/DocumentList.vue:31` et `frontend/src/features/history/ui/HistoryList.vue:34` (`title="Delete"`), `frontend/src/shared/ui/AppSidebar.vue:41` ; `Page N` en dur dans `PdfPageCanvas.vue:6`, `PdfPagePreview.vue:15`, `PagePreviewWithOverlay.vue:107` (identique en français).
- **Analyse** : l'item était non conforme le 13 à cause des ~64 libellés français des cartes MCP ; ils sont tous passés dans une table `MESSAGES` en/fr, anglais par défaut, locale tirée de `navigator.language` (`citation_app.html:409`, `:497` ; `sources_app.html:367`, `:532`), y compris le texte d'attente (`citation_app.html:500`). Côté éditeur, 11 des 12 libellés sont passés en i18n. Le seul résidu nouveau depuis 0.7.3 est la phrase serveur de `docling_projector.py:147`, que la remédiation du 13 demandait déjà de remplacer par un code. Une lecture stricte de « tout » ferait tomber l'item (−11 points, 56 → 44) ; le seuil appliqué ici est celui du 13, qui tolérait 4 libellés anglais préexistants.
- **Remediation** : `nonEditableReason: "not_editable"` + `label`, traduit côté front (`analysisEditor.notEditable`) ; clés `common.close`, `common.delete`.

### [INFO] Flag HTTP `edited` conservé à la frontière (3.2.4 jugé conforme)

- **Localisation** : `document-parser/api/documents.py:145` (`edited: bool = Query(False)`, branches `:148`, `:151-155`) ; `frontend/src/features/document/api.ts:72` (`getExportUrl(..., edited = false)`).
- **Analyse** : les trois flags relevés au 13 sont retirés (`complete_and_select`, `export` / `export_edited`, `select` / `extendSelection` à `AnalysisEditor.vue:389` / `:395`). Le booléen subsiste dans le contrat HTTP et le constructeur d'URL, comme `include_deleted` déjà accepté ; la route ne fait que choisir entre deux opérations nommées. Un `source=analysis|edited` (enum) ou une route `/export/edited` le supprimerait. Les autres booléens restants (`set_command_active(active)`, `setSavedCommandActive(active)`, `verify_certs`, `read_only`, `is_default`, `apps`) sont des valeurs ou de la configuration.

### [INFO] Code mort (partiellement résorbé)

- **Localisation** : résolu : `_TEXT_LABELS` (`docling_projector.py`). Restent : `document-parser/domain/chunk_editing.py` (213 l., importé seulement par `tests/test_chunk_editing.py`), `document-parser/services/analysis_service.py:113` (`_chunk_promoter`, écrit `:126`, jamais lu ; câblé par `bootstrap/builder.py:160` dont le commentaire `:157-159` dit lui-même que le flux ne l'invoque plus), `document-parser/mcp_adapter/wire.py:72` et `wire_mapping.py:42` (`_neutralise_all`), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `frontend/src/features/analysis-editor/api.ts:71` (`rebuildAnalysisEdits`, aucun appelant), `frontend/src/features/chunks/api.ts:82` (`fetchChunkPushes`), `frontend/src/shared/format.ts:26` (`formatAbsolute`).

### [INFO] Commentaires périmés (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:108-112` (« Wired in main.py », le câblage est dans `bootstrap/builder.py:160` et n'a plus d'effet) ; `document-parser/services/chunk_service.py:115` (« Used by `_promote_from_analysis` », fonction inexistante) ; `frontend/src/pages/StudioPage.vue:16` (modes nommés « Configurer / Vérifier »). `StudioPage.vue:479` du 13 a disparu.

### [INFO] Duplication introduite par #401 et #397 (renvoi audit 05)

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:238-255` (`registerImage` / `registerPdf`, mêmes 6 lignes) et `:289-318` ; `PdfPagePreview.vue:3-18` réimplémenté en ligne dans `PagePreviewWithOverlay.vue:96-114` ; `document-parser/services/analysis_edit_service.py:401` (`_command_hash`) recopie `document-parser/persistence/analysis_edit_repo.py:211` (`_hash_command`, avec `import hashlib` local `:212`, déjà relevé au 13).

### [INFO] Mémoïsation dans les lectures (3.2.5 jugé conforme)

- **Localisation** : `document-parser/services/preview_service.py:27` (`get_preview` écrit dans le cache `:49`), `document-parser/infra/preview_cache.py:22` (`get` réordonne la LRU `:26`) ; préexistants `analysis_edit_service.py` (`_unedited_projection`), `navigation_service.py`, `parse_loader.py`.
- **Analyse** : cache idempotent indexé par `(chemin, taille, mtime, page, dpi, format)` ; aucun état métier modifié. Même jugement qu'au 13.

### [INFO] Constantes magiques dans le nouveau code (renvoi audit 05)

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts:29` (`rangeChunkSize: 262144`), `frontend/src/features/document/ui/PdfPageCanvas.vue:35` (`< 2` px) et `:54` (ratio max `2`), `document-parser/infra/preview_cache.py:16` (`64 * 1024 * 1024`, défaut d'argument), `document-parser/api/documents.py:178` (`150`, `72`, `300` dpi) et `:187` (`max-age=86400`). Préexistants du 13 inchangés (`docling_projector.py`, délais de l'éditeur).

### [INFO] Nommage des variables dans le nouveau code (3.1.2 jugé conforme)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:498` et `sources_app.html:533` (`const L = MESSAGES[LOCALE]`, lu partout sous la forme `L.xxx`) ; `frontend/src/features/document/ui/usePdfDocument.ts:8` et `PdfPageCanvas.vue:32` (`document` masque `window.document`).
- **Analyse** : portée claire et usage cohérent, sans ambiguïté réelle ; `messages` / `pdfDocument` seraient plus lisibles.

### [INFO] Imbrication (inchangé)

- **Localisation** : `document-parser/infra/local_chunker.py:24` (`_chunk_sync`, 7 niveaux) ; nouveau code plat, au plus 3 niveaux (`AnalysisDetailPage.vue:124-138`, `try` dans `catch` dans `if`).

---

## Delta vs audit du 2026-11-13

**Score : 39 → 56 (+17).** Items conformes : 6/14 → 8/14. Gagnés : 3.1.3 (+2 poids) et 3.2.4 (+1). Aucun item perdu.

| Écart du 2026-11-13 | Statut au 2026-11-18 | Détail |
|---------------------|----------------------|--------|
| [MAJ] 3.1.3 Cartes MCP en français | **Résolu** | table `MESSAGES` en/fr, anglais par défaut, `lang="en"` |
| [MAJ] 3.2.1 Orchestration multi-responsabilités | **Toujours ouvert** | 1 cas résolu (`export`), 9 reconduits, 1 nouveau (`AnalysisDetailPage.vue:107`) |
| [MAJ] 3.3.2 Fichiers fourre-tout | **Toujours ouvert, aggravé** | rien de découpé ; `PagePreviewWithOverlay.vue` ajoute un second moteur de rendu |
| [MIN] 3.1.1 Nommage | Toujours ouvert | éditeur corrigé, 6 nouveaux helpers nommés par leur résultat, MCP inchangé |
| [MIN] 3.2.2 Fonctions > 30 lignes | Toujours ouvert | 71 → 73 (Python 53 → 52, TS 18 → 21) |
| [MIN] 3.2.3 Fonctions > 4 paramètres | Toujours ouvert | 37 → 38 (Python 36 → 37, TS 1 → 1, offender remplacé) |
| [MIN] 3.2.4 Flag arguments | **Résolu** | `complete_and_select`, `export_edited`, `extendSelection` |
| [MIN] 3.3.1 Fichiers > 300 lignes | Toujours ouvert | 47 → 47 |
| [MIN] Libellés anglais de l'éditeur hors i18n | **Résolu à 11/12** | reste `docling_projector.py:147` (INFO) |
| [INFO] Code mort | Partiellement résolu | `_TEXT_LABELS` retiré ; le reste inchangé |
| [INFO] Commentaires périmés | Toujours présent | `StudioPage.vue:479` disparu |
| [INFO] Imports locaux redondants | Toujours présent | `analysis_edit_repo.py:212`, `chunk_service.py:774` |
| [INFO] Constantes magiques | Toujours présent | + constantes PDF.js / cache d'aperçu |
| [INFO] Mémoïsation dans `get_*` | Inchangé | + `get_preview` |
| [INFO] Imbrication | Inchangé | |

Nouveaux écarts : [MAJ] 3.2.1 `AnalysisDetailPage.vue:107` (intégré au MAJ reconduit), aggravation 3.3.2 par `PagePreviewWithOverlay.vue`, [INFO] flag HTTP `edited`, [INFO] duplication #401 / #397, [INFO] nommage `L` / `document`.

---

## Points positifs

- **Corrections ciblées et réelles** : #397 a traité tous les points dont la remédiation était qualifiée d'« effort S » au 13 (cartes MCP, libellés de l'éditeur, trois flags, signature front à 5 paramètres, renommages de l'éditeur).
- **`export` exemplaire** : une seule implémentation `_export` paramétrée par une fonction de résolution (`services/export_service.py:75`), deux entrées nommées, plus de cascade dupliquée.
- **Cartes MCP propres** : textes du document jamais traduits, uniquement les libellés de la carte, avec un commentaire qui l'explique (`citation_app.html:406-408`, `sources_app.html:362-366`).
- **Nouveau code backend petit et à sa place** : `preview_service.py` (50 l.) et `preview_cache.py` (40 l.) derrière un port `PreviewImageCache` (`domain/ports.py:146`), une méthode publique chacun.
- **Composants PDF.js courts** : `PdfPageCanvas.vue` (101 l.), `PdfPagePreview.vue` (48 l.), `usePdfDocument.ts` (47 l.), gestion de course par compteur de génération, commentaires qui expliquent les contraintes de PDF.js (`PdfPageCanvas.vue:41-42`).
- **Logique pure extraite et testable** : `pageInRenderWindow` dans `PagePreviewWithOverlay.logic.ts` plutôt que dans le SFC.
- **Aucun code commenté** sur tout le périmètre ; `ruff` (dont isort) propre.

---

## Verdict partiel : NO-GO

Score **56/100** (< 60), **0 CRITICAL**, **2 MAJOR** (3.2.1, 3.3.2).

Chemin le moins cher :

1. **≥ 60** : faire passer **3.1.1** (+1 poids → 61, GO CONDITIONNEL). Soit acter dans la fiche que les helpers privés purs peuvent porter le nom de leur résultat et renommer les 5 fonctions publiques restantes (`sources_card`, `document_row`, `citation_out`, `excerpt_result`, `source_service.text`), soit renommer les ~50 fonctions. Effort S.
2. **≥ 80** : il faut 15 poids sur 18 (14 donnent 77,8). En plus de 3.1.1, les deux MAJ sont nécessaires (61 + 11 + 11 = **83**) : les items de poids 1 restants (3.2.2 : 73 fonctions, 3.2.3 : 38 signatures, 3.3.1 : 47 fichiers) sont hors d'atteinte pour cette release.
   - 3.3.2 : sortir la projection d'arbre et le push de `chunk_service.py`, découper le store et le SFC de l'éditeur, extraire `PdfPageFrame` de `PagePreviewWithOverlay.vue`. Effort M.
   - 3.2.1 : découper les 10 fonctions listées. Effort M à L, dont 3 dans le périmètre Neo4j appelé à disparaître en 0.8.0.

Aucun écart ne présente de risque fonctionnel ou de sécurité ; le NO-GO vient du barème.

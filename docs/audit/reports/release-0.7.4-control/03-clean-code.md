# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `2d5a80e`, arbre de travail (seul `docs/audit/reports/release-0.7.4-reaudit/remediation-plan.md` modifié, hors périmètre ; `experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Audit de contrôle après remédiation (seconde passe) ; base : re-audit du 2026-11-18 sur a6fb539

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 14 |
| Score | 61 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 6 |

**Calcul** : poids conformes = 11 (3.1.1=1, 3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18 → `11 / 18 × 100 = 61,1` → **61**. Premier contrôle : 56.

Méthode : analyse statique de l'arbre de travail, aucune suite relancée (résultats fournis sur `2d5a80e` : ruff check/format propres, pytest 1563 passés / 15 ignorés, eslint/prettier/vue-tsc propres, vitest 605 passés dans 65 fichiers, build OK). Les scripts du re-audit et du premier contrôle (`pyfuncs.py`, `tsfuncs.cjs`, `pynames.py`, `pyflags.py`) ont été relancés **sans modification et avec les mêmes seuils** (`document-parser/.venv/bin/python`, `frontend/node_modules/typescript`). Le message du commit de renommage (`05c0ae5`) n'a pas servi de preuve : chaque nom a été cherché dans le code. Pour 3.1.1, un second scan indépendant a été écrit, avec une liste de verbes sans noms (voir 3.1.1), et chaque hit a été lu.

---

## Métriques (re-audit → premier contrôle → ce contrôle)

| Mesure | Re-audit `a6fb539` | 1er contrôle `a12b744` | Ce contrôle `2d5a80e` |
|--------|--------------------|------------------------|-----------------------|
| Fichiers `.py` source | 133 (21 880 l.) | 135 (22 170 l.) | 135 (22 171 l.) |
| Fichiers `.vue`/`.ts` source | 161 (29 049 l.) | 162 (29 075 l.) | 162 (29 097 l.) |
| `.py` > 300 lignes | 17 | 18 | 18 |
| `.vue`/`.ts` > 300 lignes | 30 | 30 | 30 |
| Fonctions Python > 30 lignes | 52 | 52 | 52 |
| Fonctions TS/Vue > 30 lignes | 21 | 20 | 20 |
| Fonctions Python > 4 paramètres | 37 | 39 | 39 |
| Fonctions TS > 4 paramètres | 1 | 1 | **2** |
| Paramètres booléens Python | 18 | 18 | 18 |
| Noms Python hors liste (`pynames.py` d'origine) | 202 | 57 | 58 |
| Noms TS hors liste (`tsnames.cjs`, liste d'origine) | 96 | 81 | 81 |
| Fonctions nommées par leur résultat (lecture humaine) | ~50 | 26 | **0** |
| Code commenté | 0 | 0 | 0 |

Détail des variations depuis `a12b744` :

- **Fichiers > 300** : même ensemble. Grossissent `frontend/src/features/analysis/ui/StructureViewer.vue` 445 → 458, `BboxOverlay.vue` 323 → 326, `app/App.vue` 310 → 316 (commit couleurs `2d5a80e`) ; `infra/pdf_inspector.py` +1 ligne (`8436e27`).
- **Fonctions > 30 lignes** : même ensemble (52 + 20). S'allongent `frontend/src/features/analysis/ui/StructureViewer.vue:145` (`drawOverlay`, 72 → 80) et `frontend/src/features/analysis/ui/BboxOverlay.vue:85` (`draw`, 67 → 70), par la lecture des jetons de couleur.
- **Paramètres** : entre `frontend/src/features/analysis/ui/StructureViewer.vue:226` (`drawVisitBadge`, 4 → 6 : `fill`, `ink` ajoutés par `2d5a80e`). Côté Python, seul changement : `services/citation_image_service.py:81` renommé `_render_page_thumbnail` (toujours 5).
- **`pynames.py` d'origine** : +1, `bootstrap/mcp_mount.py:174` `_gate_route` (`gate` n'est pas dans la liste ; c'est un verbe). Les 81 noms TS sont les mêmes (seul `scrollToFocused` change de ligne).
- **Script corrigé de la passe de renommage** (`rename3/pynames.py`, liste sans `page`, `chunk`, `index`, `preview`, `cache`, `display`, `copy`…) : 103 noms Python, 95 TS, identiques à ses sorties « après » (`py_after.txt`, `ts_after.txt`) au déplacement de `scrollToFocused` près. Tous relus via le second scan ci-dessous.

---

## Checklist

| # | Item | Poids | Conforme | Re-audit `a6fb539` → 1er contrôle `a12b744` → ce contrôle |
|---|------|-------|----------|-----------------------------------------------------------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | **oui** | ~50 → 26 → **0** fonctions nommées par leur résultat |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | pas de régression → idem → idem (`fill`, `ink`, `reasoning`, `onAccent` dans `StructureViewer.vue`) |
| 3.1.3 | Code en anglais, i18n | 2 | oui | résidu `docling_projector.py:147` → idem → idem ; aucun libellé en dur dans `2d5a80e` (couleurs seulement) |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | conforme → `fmt*` supprimés → aucun nouveau nom abrégé (`Ch` de `computePageInputWidthCh` = unité CSS `ch`) |
| 3.2.1 | Une fonction = une chose | 2 | **non** | 10 → 9 → 9 |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | non | 73 → 72 → 72 (52 Py + 20 TS) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | non | 38 → 40 → **41** (39 Py + 2 TS) |
| 3.2.4 | Pas de flag arguments | 1 | oui | 18 → 18 → 18 booléens, aucun flag réel ajouté |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | conforme → conforme → 3 nouveaux `get*` relus, purs (`getChunkTitle`, `getChunkBadgeType`, `getCopyLabel`) |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | non | 47 → 48 → 48 (18 Py + 30 front) |
| 3.3.2 | Un concept par fichier | 2 | **non** | 4 fichiers + `sources_view.py` → idem → idem |
| 3.3.3 | Imports ordonnés | 1 | oui | ruff `I` propre (résultat fourni) |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | aucun commentaire devenu faux ; le nouveau commentaire de `StructureViewer.vue:168` est exact (`--reasoning` `App.vue:112`, `--on-accent` `:104`) |
| 3.4.2 | Pas de code commenté | 1 | oui | 0 → 0 → 0 |

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration multi-responsabilités (reconduit, 9 fonctions)

- **Localisation** : `document-parser/services/chunk_service.py:474` (`push_to_store`, 103 l.), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l.), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.), `document-parser/domain/parse_index.py:80` (`build_index`, 79 l.), `document-parser/services/analysis_service.py:480` (`_finalize_analysis`, 67 l.), `document-parser/services/analysis_edit_service.py:137` (`save`, 66 l.), `document-parser/infra/docling_editor.py:204` (`_merge_text`, 50 l.), `document-parser/infra/docling_editor.py:261` (`_move_element`, 47 l.), `frontend/src/features/document/ui/BboxCanvas.vue:80` (`draw`, 124 l.).
- **Constat** : aucune des 9 n'a bougé depuis `a12b744` (mêmes lignes, mêmes longueurs). `StructureViewer.vue:145` (`drawOverlay`) passe de 72 à 80 lignes mais reste un dessin en deux passes : compté en 3.2.2, pas ici.
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** : inchangée (`save` → `_ensure_stream` / `_check_sequence` / `_cache_from` / `_refresh_graph` ; `_move_element` → deux protocoles ; `draw` → `drawBoxes` / `drawNextMarker` / `drawOrderBadges` ; `push_to_store` en étapes nommées). Les 3 fonctions Neo4j peuvent sortir du périmètre si la retraite 0.8.0 est actée.

### [MAJ] Fichiers fourre-tout (reconduit, inchangé)

- **Localisation** : `document-parser/services/chunk_service.py:133` (classe `ChunkService`, fichier de 923 l. : push `:474`, projection d'arbre `:689` `get_tree`, `:789` `_build_tree_nodes`) ; `document-parser/mcp_adapter/sources_view.py` (369 l. : modèle de carte `:223` `build_sources_card` et rendu texte `:338` `render_sources_text`) ; `frontend/src/features/analysis-editor/store.ts` (444 l. : aperçu, undo/redo, sélection de fusion, brouillon `sessionStorage`) ; `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue` (805 l. : bannières, panneau d'historique) ; `frontend/src/features/document/ui/PagePreviewWithOverlay.vue` (761 l. : `registerImage` `:238` / `registerPdf` `:248`, `onImageLoad` `:289` / `onPdfReady` `:307`, `onImageError` `:302` / `onPdfError` `:314`).
- **Constat** : aucun découpage. `05c0ae5` n'a changé que des noms dans `chunk_service.py` et `PagePreviewWithOverlay.vue` (tailles identiques) ; `store.ts`, `AnalysisEditor.vue` et `sources_view.py` n'ont pas été touchés depuis `a12b744`.
- **Regle violee** : item 3.3.2 (poids 2).
- **Remediation** : inchangée (`services/tree_projection.py` et `services/chunk_push_service.py` ; `usePendingDraft`, `useMergeSelection`, `AnalysisEditHistoryPanel.vue`, `EditorBanners.vue` ; composant `PdfPageFrame` réutilisé comme `PdfPagePreview`).

### [MIN] Fonctions au-delà de 30 lignes (52 Python, 20 TS)

- **Localisation** : rallongées depuis `a12b744` : `frontend/src/features/analysis/ui/StructureViewer.vue:145` (`drawOverlay`, 72 → 80), `frontend/src/features/analysis/ui/BboxOverlay.vue:85` (`draw`, 67 → 70). Pires inchangées : `document-parser/infra/neo4j/tree_writer.py:69` (227), `frontend/src/features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216), `frontend/src/features/document/ui/BboxCanvas.vue:80` (124).
- **Constat** : 72 → 72 offenders, même ensemble ; deux s'allongent par la lecture des jetons de couleur (`2d5a80e`).
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4 ; priorité aux 9 fonctions du MAJ 3.2.1.

### [MIN] Fonctions à plus de 4 paramètres (39 Python, 2 TS)

- **Localisation** : nouvelle : `frontend/src/features/analysis/ui/StructureViewer.vue:226` (`drawVisitBadge`, 4 → 6, `fill` et `ink` ajoutés par `2d5a80e`). Reconduites : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14` (`isPageInRenderWindow`, 6, deux booléens positionnels), `document-parser/services/chunk_service.py:136` (`__init__`, 12), `document-parser/services/analysis_service.py:83` (`__init__`, 10), `document-parser/services/store_service.py:231` (`update_store`, 10), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 7), `document-parser/services/document_service.py:58` (`__init__`, 6), `document-parser/domain/ports.py:484` (`get`, 5).
- **Constat** : 40 → 41. Le nouveau cas passe deux couleurs lues une fois par dessin plutôt que de relire le style à chaque badge : choix défendable, mais il franchit le seuil.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : `drawVisitBadge(ctx, at: {x, y}, order, colors: {fill, ink})` ; objet de paramètres pour `isPageInRenderWindow`. Hors d'atteinte pour 0.7.4 sur les constructeurs Python.

### [MIN] Fichiers sources au-delà de 300 lignes (18 Python, 30 front)

- **Localisation** : grossissent depuis `a12b744` : `frontend/src/features/analysis/ui/StructureViewer.vue` (445 → 458), `frontend/src/features/analysis/ui/BboxOverlay.vue` (323 → 326), `frontend/src/app/App.vue` (310 → 316). Plus gros inchangés : `document-parser/api/schemas.py` (939), `document-parser/services/chunk_service.py` (923), `document-parser/domain/ports.py` (766), `frontend/src/shared/i18n.ts` (1642), `frontend/src/pages/StudioPage.vue` (1444).
- **Constat** : 48 → 48, même ensemble.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4 ; scinder `domain/ports.py` en package reste l'effort le plus simple.

### [INFO] 3.1.1 : vérification indépendante des renommages (item désormais conforme)

- **Les 26 noms du premier contrôle** : aucun n'est encore défini dans le code source, et aucun n'est référencé nulle part (source et tests, `grep -w`), à deux exceptions près qui ne sont pas les fonctions visées : `document-parser/api/documents.py:179` `page_sizes` est un handler de route (operationId OpenAPI, exclu par la règle de lecture) et `document-parser/domain/parse_index.py:76` `page_count` est une `@property` de `DocumentIndex`. Nouveaux noms vérifiés à leur définition : `domain/ports.py:657` / `:662` / `:666` et `infra/pdf_inspector.py:27` / `:44` / `:52` (`read_page_sizes`, `count_pages`, `count_pages_in_bytes`), `services/preview_service.py:70` (`read_page_sizes`), `domain/parse_index.py:32` (`build_page_ref`), `domain/navigation.py:93` (`to_page_fraction`), `infra/neo4j/queries.py:112` / `:123` (`_build_page_node`, `_build_chunk_node`), `infra/neo4j/chunk_writer.py:51` (`_build_chunk_id`), `domain/outline_builder.py:127` (`_build_page_nodes`), `services/citation_image_service.py:81` (`_render_page_thumbnail`), `domain/chunk_editing.py:37` (`_find_index`), `services/parse_loader.py:101` (`_load_index`), `services/chunk_service.py:894` (`_pick_display_label`), `persistence/analysis_edit_repo.py:76` (`_to_cache_params`) ; front : `features/document/previewScroll.ts:72` / `:88` (`computePageFrameGeometry`, `computePageTopScrollPosition`), `features/document/linkedView.ts:29` / `:72` (`findChunkForElement`, `filterChunkBboxesOnPage`), `features/chunks/ui/ChunksPanel.vue:145` / `:154` (`getChunkTitle`, `getChunkBadgeType`), `features/analysis/ui/NodeDetailsPanel.vue:195` (`formatPreviewText`), `features/mcp-config/ui/McpConfigSection.vue:523` (`getCopyLabel`), `features/document/ui/PagePreviewWithOverlay.logic.ts:9` / `:14` (`computePageInputWidthCh`, `isPageInRenderWindow`). Les 3 renommages en plus : `domain/anchors.py:89` (`hash_quote`), `domain/quote_marks.py:59` (`find_quote_marks`), `bootstrap/mcp_mount.py:174` (`_gate_route`).
- **Second scan** : liste de verbes sans noms (retirés : `page`, `chunk`, `index`, `preview`, `cache`, `display`, `outline`, `record`, `order`, `rank`, `score`, `group`, `batch`, `stream`, `query`, `lookup`, `diff`, `quote`, `sign`, `process`, `project`, `export`, `import`, `mount`, `wire`, `edit`, `store`, `log`, `trace`, `map`, `copy`, `hash`, `count`, `sort`, `filter`, `search`) ; les 10 derniers mis en relecture séparée. Python : 869 fonctions, 133 hits ; TS/Vue : 575 fonctions, 92 hits. Tous lus. Exclus par la règle de lecture du premier contrôle : 14 handlers de route, propriétés (16), convertisseurs `x_to_y` (22) et fabriques `from_*` (9 : `api/schemas.py`, `infra/settings.py:200`, `services/navigation_config.py:65`), options d'objet (`component`, `props`, `match`, `default`, `state`), composants `*Icon`, `t`. Restent des verbes absents de la liste : `wire`, `mount`, `project`, `chunk`, `put`, `export`, `import`, `process`, `diff_against_store`, `record_on_*`, `index_chunks`, `shift_sequences`, `joins` (prédicat verbal, `domain/page_regions.py:55`), `queue*`, `reingest`, `coalesceCommands`, `dismissDisclaimer`, `previewNow`… et, en relecture séparée, `count_*`, `search_*`, `hash_*`, `sort*`, `filter*`, `copy*` sont tous employés comme verbes. Les noms menés par un verbe de la liste ont aussi été relus (`list_*`, `mark_*`, `format*`, `select*`, `focus*`…) : aucun nom-groupe déguisé.
- **Résultat** : **0 fonction nommée par son résultat.** Seul cas limite, toléré comme au premier contrôle : `health_check` (`domain/ports.py:572`, `infra/llm/ollama_provider.py:41`, `infra/serve_converter.py:189`), nom de méthode de port usuel qui dit l'action.
- **Qualité des nouveaux noms** : aucun faux, aucun trompeur. `PdfInspector` porte désormais une seule convention (`read_page_sizes`, `count_pages`, `count_pages_in_bytes`) : l'incohérence relevée au premier contrôle est levée. `_gate_route` dit ce que fait la fonction. Deux réserves mineures : `_find_index` (`domain/chunk_editing.py:37`) lève une exception si l'id manque, alors que les `find_*` des dépôts renvoient `None` ; `computePageInputWidthCh` garde le suffixe d'unité (`ch`), exact mais différent du nom proposé.

### [INFO] Paires incohérentes reconduites et une nouvelle

- **Localisation** :
  - Reconduites : `frontend/src/features/analysis/ui/GraphView.vue:149` (`getNodeColor`) et `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:184` (`getKindColor`), même calcul ; `getKindColor` aussi dans `frontend/src/features/reasoning/kindColors.ts:37` (autre concept) ; `formatDuration` dans `frontend/src/features/history/ui/HistoryList.vue:76` (une analyse) et `frontend/src/features/reasoning/timeline.logic.ts:9` (des ms) ; `_hash_command` dans `document-parser/services/analysis_edit_service.py:399` et `document-parser/persistence/analysis_edit_repo.py:211`, deux implémentations de signatures différentes ; `document-parser/bootstrap/builder.py:247` `deps_present=has_usable_deps()`.
  - Relevée à ce contrôle : deux empreintes de chunkset sous deux conventions, `document-parser/domain/hashing.py:43` (`hash_chunkset`, texte / page / titres) et `document-parser/services/chunk_service.py:769` (`_compute_chunkset_hash`, autres champs). Deux calculs distincts, noms trop proches pour qu'on devine lequel sert à quoi.
  - Levées : `count_pages` / `count_pages_in_bytes` (même convention), `_wrap_route` → `_gate_route`.
- **Analyse** : renvoi audit 05 pour les doublons ; aucun impact sur la conformité de 3.1.1.

### [INFO] Références aux anciens noms dans la documentation de conception

- **Localisation** : `docs/design/364-mcp-admin-panel-section.md:50`, `:90` (`mcp_mount._tools_from`), `:78` (`server_status`) ; `docs/design/254-docker-slim-post-uv.md:71`, `:84`, `:90`, `:156` (`deps_present()`) ; `docs/design/317-admin-panel-runtime-reasoning-config.md:110`, `:327` ; `docs/design/210-feature-flag-mode-gating.md:120` ; `docs/design/264-linked-view-preview-chunks-layers.md:119`, `:530`.
- **Analyse** : documents de conception historiques, inchangés. Aucun des 29 anciens noms de `05c0ae5` n'apparaît dans la doc vivante (`docs/*.md` hors `design/` et `audit/`) ni dans un commentaire du code ; `quote_hash` restant dans `mcp_adapter/apps.py:77`, `:101`, `:180` est un champ de modèle, pas la fonction.

### [INFO] Helpers dupliqués renommés en série (renvoi audit 05)

- **Localisation** : `_get_utc_now` et `_generate_id` définis 4 fois : `document-parser/domain/models.py:28`, `:32`, `document-parser/domain/chunk_editing.py:29`, `:33`, `document-parser/services/chunk_service.py:91`, `:95`, `document-parser/services/version_service.py:44`, `:48`.
- **Analyse** : inchangé.

### [INFO] Résidus reconduits sans changement

- 3.1.3 : `document-parser/infra/docling_projector.py:147` (phrase anglaise affichée telle quelle).
- 3.2.4 : flag HTTP `edited` (`document-parser/api/documents.py:108`, `export_document`).
- Code mort : `document-parser/services/analysis_service.py:115` / `:128` (`_chunk_promoter`), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `_neutralise_all` en double (`document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`), `frontend/src/features/analysis-editor/api.ts:71`, `frontend/src/features/chunks/api.ts:82`, `frontend/src/shared/format.ts:26` (fichiers inchangés depuis `a12b744`), module `document-parser/domain/chunk_editing.py` (utilisé par les seuls tests).
- Commentaires périmés : `document-parser/services/analysis_service.py:110` (« Wired in main.py »), `document-parser/services/chunk_service.py:115` (`_promote_from_analysis`, inexistante).

### [INFO] Le script de nommage reste une heuristique

- **Analyse** : la passe de renommage a corrigé la liste de verbes (`rename3/pynames.py`, sans `page`, `chunk`, `index`, `preview`, `cache`, `display`, `copy`), ce qui ferme la cause relevée au premier contrôle. Mais la liste d'origine (`audit03/pynames.py`) est toujours celle des scripts du re-audit et de ce contrôle, et elle garde des noms (`outline`, `record`, `order`, `query`, `store`…). Pour qu'un futur « le script ne sort plus rien » vaille quelque chose, versionner la liste corrigée avec la fiche ou dans `docs/audit/`, et garder une relecture des hits.

### [INFO] Mémoïsation dans les lectures (3.2.5 conforme, inchangé)

- `document-parser/mcp_adapter/results.py:25` (`_get_type_adapter`, `@cache`), avec `preview_service.get_preview` et `preview_cache.get` : cache idempotent, aucun état métier. `services/parse_loader.py:101` (`_load_index`) déplace l'entrée dans son LRU : il s'appelle `load`, pas `get`, donc hors du champ de 3.2.5.

---

## Premier contrôle (a12b744)

- **Score 56** (8/14, 10/18), 0 CRIT, 2 MAJ (3.2.1, 3.3.2), 4 MIN (3.1.1, 3.2.2, 3.2.3, 3.3.1), 6 INFO. Verdict NO-GO.
- **26 fonctions** encore nommées par leur résultat, invisibles pour le script parce que sa liste de verbes contenait des noms : Python `ports.py` `page_sizes` / `page_count`, `pdf_inspector.py` `page_sizes` / `page_count`, `preview_service.py` `page_sizes`, `page_ref`, `page_fraction`, `_page_node`, `_chunk_node`, `_chunk_id`, `_page_nodes`, `_page_thumbnail`, `_index_of`, `_index_for`, `_display_label`, `_cache_values` ; TS `pageFrameGeometry`, `pageTopScrollPosition`, `chunkForElement`, `chunkBboxesOnPage`, `chunkTitle`, `chunkBadgeType`, `previewText`, `copyLabel`, `pageInputWidthCh`, `pageInRenderWindow`.
- **Ce qu'elles sont devenues** : les 26 renommées par `05c0ae5` sous les noms proposés (à `computePageInputWidthCh` près, qui garde son suffixe d'unité), plus 3 autres (`quote_hash` → `hash_quote`, `quote_marks` → `find_quote_marks`, `_wrap_route` → `_gate_route`). Vérifié dans le code : aucune ancienne définition, aucune référence restante, aucun handler de route renommé.

---

## Delta vs re-audit a6fb539

**Score : 56 → 61 (+5)** (re-audit 56, premier contrôle 56). Items conformes : 8/14 → 9/14. Item gagné : 3.1.1. Aucun item perdu. Verdict : NO-GO → **GO CONDITIONNEL**.

| Écart du re-audit | Statut au 1er contrôle (`a12b744`) | Statut à ce contrôle (`2d5a80e`) | Mesures re-audit → 1er contrôle → ce contrôle |
|-------------------|------------------------------------|----------------------------------|-----------------------------------------------|
| [MAJ] 3.2.1 Orchestration multi-responsabilités | Réduit | **Inchangé** (ouvert) | 10 → 9 → 9 fonctions |
| [MAJ] 3.3.2 Fichiers fourre-tout | Inchangé | **Inchangé** (ouvert) | 4 fichiers + `sources_view.py`, tailles identiques |
| [MIN] 3.1.1 Nommage | Réduit, non conforme | **Résolu** | ~50 → 26 → 0 |
| [MIN] 3.2.2 Fonctions > 30 lignes | Réduit | Inchangé | 73 → 72 → 72 |
| [MIN] 3.2.3 Fonctions > 4 paramètres | Aggravé | **Aggravé** | 38 → 40 → 41 (+ `drawVisitBadge`, 6) |
| [MIN] 3.3.1 Fichiers > 300 lignes | Aggravé | Inchangé | 47 → 48 → 48 |
| [INFO] Résidus 3.1.3, flag `edited`, code mort, commentaires périmés, mémoïsation | Inchangés | Inchangés | |
| [INFO] Paires incohérentes | Relevées | 2 levées, 1 ajoutée (`hash_chunkset` / `_compute_chunkset_hash`) | |

Nouveaux écarts depuis `a12b744` : `drawVisitBadge` à 6 paramètres (3.2.3), aucun autre. Ce que la seconde passe a obtenu : la conformité de 3.1.1 (+1 poids, +5 points), avec des noms justes et le port `PdfInspector` sur une seule convention.

---

## Points positifs

- **Renommage complet et vérifiable** : les 26 offenders et 3 de plus, sans ancienne définition ni référence orpheline, sans handler de route ni nom MCP touché ; suites vertes sur `2d5a80e`.
- **Un port, une convention** : `PdfInspector` (`domain/ports.py:654-669`) lit et compte avec des verbes, chaque méthode avec son contrat d'erreur.
- **La cause est traitée, pas seulement les symptômes** : la liste de verbes du script de la passe de renommage ne contient plus les noms qui l'aveuglaient.
- **Couleurs du canvas lues depuis les jetons** (`StructureViewer.vue:168-172`), une fois par dessin, avec un commentaire qui dit pourquoi.

---

## Verdict partiel : GO CONDITIONNEL

Score **61/100** (60-79), **0 CRITICAL**, **2 MAJOR** (3.2.1 : 9 fonctions ; 3.3.2 : 5 fichiers, ≤ 3 donc non bloquants), 3 MINOR, 6 INFO.

Condition : plan de remédiation pour les deux MAJ (déjà décrit ci-dessus). Au-delà de 80, les deux MAJ sont nécessaires (61 + 11 + 11 = 83). Aucun gain rapide : corriger `drawVisitBadge` et `isPageInRenderWindow` ne rend pas 3.2.3 conforme, 39 cas Python restent.

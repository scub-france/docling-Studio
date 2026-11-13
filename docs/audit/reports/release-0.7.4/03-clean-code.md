# Rapport d'audit : Clean Code

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 14 |
| Score | 39 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 6 |
| Ecarts INFO | 6 |

**Detail du calcul** : somme des poids conformes = 7 (3.1.2=1, 3.1.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur un total de 18 → `7 / 18 * 100 = 38,9` → **39**.

Périmètre audité : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/` (hors `*.test.*`), arbre de travail de `fix/0.7.4-editor-followups` au commit `eade7fa` (= `release/0.7.4` @ `2f47f72` + #391, #392, #393). Comme en 0.7.3, les deux pages HTML du serveur MCP (`mcp_adapter/citation_app.html`, `sources_app.html`) sont auditées comme du code source. Hors périmètre : `frontend/scripts/record-analysis-editor*.mjs` (641 l., scripts de capture vidéo), `e2e/`, `experiments/mcp-bench/` (non suivi). Attention particulière au delta depuis 0.7.3 (`1de1929..eade7fa`) : éditeur d'analyse durable (#319 / #388).

Méthode : analyse statique uniquement (aucune suite de tests, aucun lint, aucun build lancé). Tailles mesurées par `wc -l`. Fonctions Python mesurées par AST (lignes de corps hors signature et docstring, même méthode qu'en 0.7.3) ; fonctions TS/Vue mesurées avec le parseur TypeScript du projet (`frontend/node_modules/typescript`, étendue signature comprise). La base 0.7.3 a été remesurée avec les mêmes scripts sur `git archive 1de1929`. `ruff` n'a pas été lancé : l'item 3.3.3 est jugé par lecture des imports des fichiers nouveaux ou modifiés.

---

## Metriques

| Mesure | 0.7.3 | 0.7.4 | Commentaire |
|--------|-------|-------|-------------|
| Fichiers `.py` source (hors tests) | 119 (19 773 l.) | 127 (21 615 l.) | dont 1 709 l. d'éditeur dans 8 fichiers nouveaux |
| Fichiers `.vue`/`.ts` source (hors tests) | 150 (26 386 l.) | 158 (28 631 l.) | feature `analysis-editor` : 1 912 l. |
| `.py` > 300 lignes | 14 | **17** | + `analysis_edit_service.py` 378, `database.py` 373, `docling_editor.py` 338 |
| `.vue`/`.ts` > 300 lignes (i18n compris) | 26 | **30** | + `AnalysisEditor.vue` 759, `analysis-editor/store.ts` 441, `EditableStructureNode.vue` 311, `DownloadDropdown.vue` 299 → 301 |
| Fonctions Python > 30 lignes de corps | 45 | **53** | + 9 nouvelles, − 1 disparue (`promote_from_analysis_if_empty` passe sous le seuil) |
| Fonctions TS/Vue > 30 lignes (hors stores Pinia setup) | 15 (remesuré) | 18 | nouvelles : `analysis-editor/store.ts:232` (39), `:272` (33), callback de `feature-flags/store.ts:168` (31) ; `BboxCanvas.vue` `draw` 75 → 120 |
| Fonctions Python > 4 paramètres | 29 | **36** | + 7, toutes liées à l'éditeur |
| Fonctions TS > 4 paramètres | 0 | **1** | `features/analysis-editor/api.ts:55` |
| Code commenté laissé en place | 0 | 0 | |
| Libellés UI français hors `i18n.ts` | ~64 | ~64 | cartes MCP inchangées (seul `lang="fr"` corrigé au re-audit 0.7.3) |
| Libellés UI anglais hors `i18n.ts` (nouveau code) | — | ~12 | éditeur d'analyse (voir 3.1.3) |

### Fichiers > 300 lignes

**Python** (0.7.3 → 0.7.4) : `api/schemas.py` 939 (849), `services/chunk_service.py` 935 (1019, retrait de l'audit trail `ChunkEdit`), `services/analysis_service.py` 589, `domain/ports.py` 576 (542), `infra/serve_converter.py` 402, `services/store_service.py` 395, `domain/navigation.py` 385, `services/analysis_edit_service.py` 378 (**nouveau**), `persistence/database.py` 373 (**passe le seuil**, upgrade #391 + 3 tables éditeur), `mcp_adapter/sources_view.py` 369, `domain/source_map.py` 354, `bootstrap/factories.py` 353, `infra/docling_editor.py` 338 (**nouveau**), `domain/models.py` 314 (331), `infra/neo4j/tree_writer.py` 310, `services/citation_service.py` 307, `infra/docling_tree.py` 307. Hors `.py` : `mcp_adapter/sources_app.html` 1 188, `citation_app.html` 1 177 (inchangés).

**Front** : `shared/i18n.ts` 1600 (données, +128), `pages/StudioPage.vue` 1450, `features/mcp-config/ui/McpConfigSection.vue` 1110, `features/chunking/ui/ChunkPanel.vue` 801, `pages/DocParseTab.vue` 794, `features/analysis-editor/ui/AnalysisEditor.vue` **759** (template 293 / script 210 / style 254, **nouveau**), `features/document/ui/PagePreviewWithOverlay.vue` 726, `pages/DocsLibraryPage.vue` 701, `features/analysis/ui/ResultTabs.vue` 679, `features/analysis/ui/GraphView.vue` 657, `features/chunks/ui/ChunksEditor.vue` 622, `features/store/ui/StoreForm.vue` 520, puis 18 fichiers entre 301 et 456 lignes, dont `features/analysis-editor/store.ts` 441 (**nouveau**), `features/analysis-editor/ui/EditableStructureNode.vue` 311 (**nouveau**) et `features/document/ui/DownloadDropdown.vue` 301.

---

## Checklist

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 3.1.1 | Fonctions nommées avec des verbes d'action | 1 | ❌ |
| 3.1.2 | Variables qui expriment l'intention | 1 | ✅ |
| 3.1.3 | Tout le code en anglais — traductions dans `shared/i18n.ts` | 2 | ❌ |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | ✅ |
| 3.2.1 | Chaque fonction fait une seule chose | 2 | ❌ |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | ❌ |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | ❌ |
| 3.2.4 | Pas de flag arguments | 1 | ❌ (nouveau) |
| 3.2.5 | Un `get_*` ne modifie pas d'état | 2 | ✅ |
| 3.3.1 | Aucun fichier source > 300 lignes | 1 | ❌ |
| 3.3.2 | Un seul concept par fichier | 2 | ❌ |
| 3.3.3 | Imports ordonnés | 1 | ✅ (lecture manuelle, cf. INFO) |
| 3.4.1 | Commentaires = « pourquoi » | 1 | ✅ |
| 3.4.2 | Pas de code commenté laissé en place | 1 | ✅ |

---

## Ecarts constates

### [MAJ] Cartes MCP : libellés UI en français codés en dur, hors i18n (reconduit de 0.7.3, inchangé)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:395` (« En attente d'une citation… »), `:611` et `:644` (« Lire la suite », « Réduire ») ; `document-parser/mcp_adapter/sources_app.html:391` (« mot pour mot · vérifiée par le serveur »), `:743`, `:998` (`TIMEOUT_MESSAGE = "l’hôte n’a pas répondu"`).
- **Constat** : aucun fichier de `mcp_adapter/` n'a changé depuis 0.7.3 (`git diff --stat 1de1929..HEAD -- document-parser/mcp_adapter` vide). Le re-audit 0.7.3 a seulement aligné l'attribut `lang="fr"` (`citation_app.html:2`, `sources_app.html:2`) sur le contenu. Les ~64 libellés restent uniquement en français : un utilisateur anglophone de l'application bilingue reçoit des cartes françaises.
- **Regle violee** : item 3.1.3 — « Tout le code est en anglais — les traductions i18n sont dans `shared/i18n.ts` » (poids 2).
- **Remediation** : inchangée. Libellés anglais par défaut et table `MESSAGES = { en, fr }` en tête de chaque page, locale prise du contexte hôte. Effort faible (≈ 64 chaînes). Ce seul item rapporte 11 points (39 → 50).

### [MAJ] Fonctions d'orchestration multi-responsabilités (reconduit, nouveaux cas dans l'éditeur)

- **Localisation** :
  - reconduits : `document-parser/services/chunk_service.py:484` (`push_to_store`, 103 l.), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l.), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.), `document-parser/domain/parse_index.py:80` (`build_index`, 79 l.), `document-parser/services/analysis_service.py:460` (`_finalize_analysis`, 67 l.) ;
  - nouveaux en 0.7.4 : `document-parser/services/analysis_edit_service.py:135` (`save`, 66 l.), `document-parser/infra/docling_editor.py:204` (`_merge_text`, 50 l.), `document-parser/infra/docling_editor.py:261` (`_move_element`, 47 l.), `frontend/src/features/document/ui/BboxCanvas.vue:80` (`draw`, 75 → 120 l.), `document-parser/services/export_service.py:46` (`export`, 41 → 49 l.).
- **Constat** : aucune extraction demandée en 0.7.0 / 0.7.3 n'a été faite. Le nouveau code reproduit le motif :
  - `save` crée le flux si absent et relit en cas de course (`:149-161`), vérifie le hash de base (`:162`), contrôle la séquence (`:165-170`), rejoue et projette (`:171-172`), construit le cache à 10 champs (`:176-187`), lit la sélection, persiste (`:190-195`), rafraîchit le graphe Neo4j avec avalement d'erreur (`:196-206`) puis construit le snapshot ;
  - `_merge_text` valide (`:210-221`), regroupe les éléments sous le parent cible par déplacements de sous-arbres (`:222-238`), fusionne le texte avec la règle de césure (`:239-255`), fusionne les provenances, arbitre l'hyperlien et supprime les sources (`:256-259`) ;
  - `_move_element` porte **deux protocoles** de déplacement dans un même corps : cible + `placement` (`:268-294`, seul utilisé par l'UI, `store.ts:202`) puis l'ancien `beforeElementId` (`:295-313`, produit par aucun appelant front) ;
  - `BboxCanvas.draw` dessine les boîtes, puis le marqueur « suivant » (`:155-167`), puis les pastilles d'ordre de lecture (`:169-198`) ;
  - `export` choisit sa source d'analyse par la même cascade à quatre branches écrite deux fois (`:74-81` pour MD, `:92-99` pour JSON).
- **Regle violee** : item 3.2.1 — « Chaque fonction fait une seule chose » (poids 2).
- **Remediation** : `save` → `_ensure_stream(base)`, `_check_sequence(stored, expected)` (déjà dupliqué dans `set_command_active:218-222`), `_cache_from(projection, …)` (déjà dupliqué dans `rebuild:256-267`), `_refresh_graph(...)`. `_merge_text` → `_gather_under_target(...)` + `_join_text(items, separator)` (fonction pure testable). `_move_element` → `_move_relative(item, target, placement)` et, si le format v1 doit rester rejouable, `_move_before(...)` séparé. `draw` → `drawBoxes`, `drawNextMarker`, `drawOrderBadges`. `export` → `_resolve_analysis(doc_id, analysis_id, edited, fallback)` appelé une fois. Le périmètre Neo4j/OpenSearch reste à tracer en dette (retrait 0.8.0).

### [MAJ] Fichiers fourre-tout : `chunk_service.py` (reconduit) et l'éditeur front (nouveau)

- **Localisation** : `document-parser/services/chunk_service.py:137` (classe `ChunkService`) avec push/diff `:450`, `:484`, `:603`, `:653`, `:675` et projection d'arbre `:699`, `:801`, `:858`, `:891`, `:906` ; `document-parser/mcp_adapter/sources_view.py` (inchangé) ; **nouveau** : `frontend/src/features/analysis-editor/store.ts:14-441` et `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:1-293`.
- **Constat** :
  - `chunk_service.py` maigrit (1019 → 935 l.) grâce au retrait de l'audit trail `ChunkEdit`, mais porte toujours trois concepts : édition du chunkset, push/diff vers un store, projection de l'arbre d'affichage.
  - `analysis-editor/store.ts` est une seule fonction setup de 428 lignes qui réunit quatre préoccupations : synchronisation serveur (chargement, aperçu avec `AbortController`, sauvegarde, historique sauvegardé, `:75-98`, `:206-304`), file locale undo/redo (`:100-145`), état d'interface de sélection et de fusion (`:167-204`) et persistance du brouillon en `sessionStorage` (`:343-390`).
  - `AnalysisEditor.vue` rend dans un seul template de 293 lignes la barre d'outils (`:3`), la bannière de conflit (`:115`), la bannière de récupération (`:129`), le panneau d'historique (`:155-200`), l'arbre, l'aperçu page/Markdown (`:233-290`) et le panneau d'édition.
- **Regle violee** : item 3.3.2 — « Un seul concept par fichier — pas de fichier fourre-tout » (poids 2).
- **Remediation** : `chunk_service.py` : inchangée (sortir `services/tree_projection.py` ; supprimer le push avec l'ingestion en 0.8.0). Éditeur : extraire `usePendingDraft(key)` (persistance `sessionStorage`) et `useMergeSelection()` du store ; extraire `AnalysisEditHistoryPanel.vue` et `EditorBanners.vue` (conflit + récupération) du SFC. Effort M.

### [MIN] Nommage : la convention « nom = valeur renvoyée » s'étend à l'éditeur (reconduit)

- **Localisation** : `document-parser/api/analysis_edits.py:30` (`_analysis`), `:50` (`_tree`), `:59` (`_response`), `:86` (`_commands`) ; `document-parser/persistence/analysis_edit_repo.py:19` (`_dt`), `:24` (`_stream`), `:33` (`_command`), `:48` (`_cache`) ; `document-parser/services/analysis_edit_service.py:105` (`active_result`), `:113` (`history`), `:356` (`_sha256`), `:360` (`_stream_hash`) ; `document-parser/infra/docling_projector.py:101` (`_label`), `:170` (`_pages`), `:205` (`_tree`) ; front `frontend/src/features/analysis-editor/commands.ts:10` (`structuralElementIds`), `:41` (`foldTargetIndex`), `frontend/src/features/analysis-editor/types.ts:82` (`pagesFromAnalysis`), `frontend/src/features/document/ui/BboxCanvas.vue:65` (`badgeRect`).
- **Constat** : la dérive relevée en 0.7.3 sur le package MCP gagne le nouveau code. Le cas le plus gênant : `history(...)` (`:113`) est une méthode publique de service dont le nom ne dit ni « lire » ni « lister », à côté de `load_editor`, `preview`, `save` et `rebuild`, qui sont des verbes. Deux fonctions homonymes `_tree` coexistent (API et projecteur) avec des rôles différents (sérialisation contre construction).
- **Regle violee** : item 3.1.1 — « Les fonctions sont nommées avec des verbes d'action » (poids 1).
- **Remediation** : `history` → `list_history`, `active_result` → `load_active_result`, `_analysis`/`_response`/`_tree` → `_to_analysis_response`/`_to_editor_response`/`_serialize_tree`, `_dt` → `_parse_iso`. Ou acter la convention dans la fiche 3.1.1, comme proposé en 0.7.3. Effort S.

### [MIN] Fonctions au-delà de 30 lignes (aggravé : 45 → 53)

- **Localisation** :
  - Python, nouvelles en 0.7.4 : `services/analysis_edit_service.py:135` (`save`, 66), `persistence/analysis_edit_repo.py:138` (`save_commands_and_cache`, 61), `infra/docling_projector.py:105` (`_editor_element`, 57), `infra/docling_editor.py:204` (`_merge_text`, 50), `infra/docling_editor.py:261` (`_move_element`, 47), `infra/docling_projector.py:205` (`_tree`, 45), `infra/docling_projector.py:34` (`project`, 39), `persistence/analysis_repo.py:175` (`update_status`, 34), `infra/docling_editor.py:36` (`apply`, 32).
  - Python, aggravées : `bootstrap/builder.py:103` (`build`, 69 → 92), `services/version_service.py:164` (`restore`, 48 → 56), `services/export_service.py:46` (`export`, 41 → 49).
  - Python, préexistantes (inchangées) : `infra/neo4j/tree_writer.py:69` (227), `infra/neo4j/queries.py:137` (115), `infra/neo4j/chunk_writer.py:55` (107), `services/chunk_service.py:484` (103), `infra/docling_agent_reasoning.py:149` (86), `mcp_adapter/server.py:95` (87), `mcp_adapter/apps.py:146` (80), `domain/parse_index.py:80` (79), etc.
  - Front, nouvelles : `features/analysis-editor/store.ts:232` (`save`, 39), `:272` (`setSavedCommandActive`, 33) ; aggravée : `features/document/ui/BboxCanvas.vue:80` (`draw`, 75 → 120).
- **Constat** : 53 fonctions Python dépassent le seuil (45 en 0.7.3) : +9 nouvelles, −1 sortie (`promote_from_analysis_if_empty`). `_editor_element` (57 l.) calcule dans un seul corps le parent, les enfants, la provenance avec conversion de repère, puis la liste des opérations autorisées par trois `if` successifs qui s'écrasent (`:139-150`). `save_commands_and_cache` mêle la transaction, le calcul de la chaîne de hash et l'INSERT ligne à ligne.
- **Regle violee** : item 3.2.2 — « Aucune fonction ne dépasse 30 lignes (hors boilerplate inévitable) » (poids 1).
- **Remediation** : traiter d'abord les 9 nouvelles. `_editor_element` → `_provenance(item, document)` + `_supported_operations(item, label)` ; `save_commands_and_cache` → `_append_command(db, …)`. Pour les anciennes, voir 3.2.1.

### [MIN] Fonctions à plus de 4 paramètres (aggravé : 29 → 36, et première occurrence front)

- **Localisation** : nouvelles : `document-parser/services/analysis_edit_service.py:51` (`__init__`, 9), `document-parser/services/version_service.py:91` (`__init__`, 6, était ≤ 4), `document-parser/api/documents.py:134` (`export_document`, 6), `document-parser/services/analysis_edit_service.py:209` (`set_command_active`, 5), `document-parser/api/analysis_edits.py:163` (`set_edit_active`, 5), `document-parser/infra/docling_projector.py:34` (`project`, 5), `document-parser/persistence/analysis_edit_repo.py:215` (`_hash_command`, 5) ; front `frontend/src/features/analysis-editor/api.ts:55` (`setAnalysisEditActive`, 5). Préexistantes : `services/chunk_service.py:140` (12), `services/store_service.py:237` (10), `services/analysis_service.py:83` (9), etc.
- **Constat** : 36 signatures Python et, pour la première fois, une signature TS dépassent le seuil. Les constructeurs sont en keyword-only, ce qui atténue. `set_command_active(document_id, target_sequence, active, expected_sequence, analysis_id)` enchaîne trois entiers/booléens positionnels relayés tels quels par la route et par l'API front : un ordre inversé entre `target_sequence` et `expected_sequence` ne serait pas détecté par le typage.
- **Regle violee** : item 3.2.3 — « Aucune fonction n'a plus de 4 paramètres » (poids 1).
- **Remediation** : un value object `EditTarget(document_id, analysis_id)` réduirait `preview`, `save`, `set_command_active`, `rebuild`, `history` d'un paramètre ; rendre `target_sequence`/`active`/`expected_sequence` keyword-only. Côté front, passer un objet `{ sequence, active, expectedAppliedThroughSequence }`. `_hash_command` disparaît si le hash est factorisé (voir audit 05). Effort S.

### [MIN] Flag arguments introduits par l'éditeur (nouveau)

- **Localisation** : `document-parser/persistence/analysis_repo.py:175` (`update_status(job, *, select_analysis=False)`, branches `:177-178` et `:202-209`), port `document-parser/domain/ports.py:245`, appelant unique `document-parser/services/analysis_service.py:508` ; `document-parser/services/export_service.py:46-52` (`export(..., *, edited=False)`, branches `:74` et `:92`), relayé par `document-parser/api/documents.py:144` ; front `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:376` (`select(id, additive = false)`), émis par `frontend/src/features/analysis-editor/ui/EditableStructureNode.vue:32-34` (`select: [id, additive]`).
- **Constat** : contrairement aux booléens de configuration jugés acceptables en 0.7.3 (`include_deleted`, `apps`), ces trois drapeaux changent ce que fait la fonction. `select_analysis=True` ajoute une précondition et une **seconde écriture dans une autre table** (`document_analysis_state`), dont le SQL recopie celui de `SqliteDocumentAnalysisRepository.select` (`persistence/document_analysis_repo.py:26-29`). `edited=True` change la source des données et rend `analysis_id` obligatoire. `additive` bascule entre « remplacer la sélection » et « l'étendre ».
- **Regle violee** : item 3.2.4 — « Pas de flag arguments (booléen qui change le comportement) » (poids 1).
- **Remediation** : `complete_and_select(job)` sur le repository (la transaction unique reste possible) ; `export_edited(doc_id, format, analysis_id)` à côté de `export(...)`, ou un enum `ExportSource` ; côté front `select(id)` et `extendSelection(id)`. Effort S, l'item repasse conforme (+1 poids).

### [MIN] Fichiers sources au-delà de 300 lignes (aggravé)

- **Localisation** : voir « Fichiers > 300 lignes ». Nouveaux : `document-parser/services/analysis_edit_service.py` (378), `document-parser/persistence/database.py` (373), `document-parser/infra/docling_editor.py` (338), `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue` (759), `frontend/src/features/analysis-editor/store.ts` (441), `frontend/src/features/analysis-editor/ui/EditableStructureNode.vue` (311), `frontend/src/features/document/ui/DownloadDropdown.vue` (301).
- **Constat** : 17 fichiers Python (14 en 0.7.3) et 30 fichiers front (26) dépassent le seuil. `api/schemas.py` grossit encore (849 → 939). Points d'amélioration : `chunk_service.py` (−84 l.) et `domain/models.py` (−17 l.) après le retrait de `ChunkEdit`. `AnalysisEditor.vue` dépasse le seuil par son seul template (293 l.) et son style (254 l.).
- **Regle violee** : item 3.3.1 — « Aucun fichier source ne dépasse 300 lignes » (poids 1).
- **Remediation** : le découpage de `AnalysisEditor.vue` (3.3.2) le ramène sous le seuil. Sortir `_upgrade_from_0_7_3` et ses constantes de `database.py` dans `persistence/upgrades.py`. Sortir les DTO de l'éditeur de `api/schemas.py` (`api/analysis_edit_schemas.py`).

### [MIN] Éditeur : libellés anglais affichés hors i18n (aggravation de 3.1.3)

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:72`, `:77`, `:79` (messages de validation de fusion, affichés par `AnalysisEditor.vue:51` et `:56-57`) ; `document-parser/infra/docling_projector.py:151-155` (`nonEditableReason` « … elements are not editable yet. », affiché par `ElementEditPanel.vue:34`) ; `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:22`, `:31` (`title="Undo (Cmd/Ctrl+Z)"`, `"Redo (…)"`), `:173` (type de commande brut `entry.commandType`), `:397` (`'Structural change'`) ; `frontend/src/features/analysis-editor/ui/EditableStructureNode.vue:45` (`'Collapse section' / 'Expand section'`), `:61` (`title="Reorder"`), `:82` (`aria-label="Select section children"`).
- **Constat** : la feature est bien traduite dans l'ensemble (112 clés `analysisEditor.*` en fr et en en dans `shared/i18n.ts`), mais une douzaine de libellés visibles ou lus par les lecteurs d'écran restent en anglais en dur : un utilisateur francophone les voit au milieu d'une interface française. Les replis d'erreur `'Failed to …'` du store (`store.ts:94`, `:264`, `:298`) suivent une convention préexistante (70 occurrences dans le front) et ne sont pas comptés ici. Classé MIN : l'item 3.1.3 est déjà non conforme à cause des cartes MCP, et l'ampleur est faible.
- **Regle violee** : item 3.1.3 (poids 2, déjà compté non conforme).
- **Remediation** : clés `analysisEditor.undoHint`, `redoHint`, `structuralChange`, `reorder`, `expandSection`/`collapseSection`, `selectChildren`, `commandType.<type>`, `merge.needTwo`/`merge.unavailable`/`merge.textOnly` ; renvoyer côté serveur un code (`nonEditableReason: "not_editable"` + type) plutôt qu'une phrase. Effort S.

### [INFO] Code mort, dont du nouveau

- **Localisation** : nouveau : `document-parser/infra/docling_projector.py:19-28` (`_TEXT_LABELS`, aucun lecteur), `frontend/src/features/analysis-editor/api.ts:72` (`rebuildAnalysisEdits`, aucun appelant) ; reconduit : `document-parser/domain/chunk_editing.py` (213 l., importé seulement par `tests/test_chunk_editing.py:7`, retouché en 0.7.4 alors que l'audit trail qu'il servait a été retiré), `document-parser/services/analysis_service.py:113-126` (`_chunk_promoter` jamais lu) avec `services/chunk_service.py:196`, `document-parser/mcp_adapter/wire.py:72` et `wire_mapping.py:42` (`_neutralise_all` ×2), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `frontend/src/features/chunks/api.ts:82` (`fetchChunkPushes`), `frontend/src/shared/format.ts:26` (`formatAbsolute`, toujours sans appelant alors que `AnalysisEditor.vue:388` en réécrit une variante).
- **Constat** : 3.4.2 reste conforme (l'item vise le code commenté, il n'y en a pas). La 0.7.4 a retiré du code mort (`ChunkEditAction`, `ChunkEdit`, table `chunk_edits`, `SqliteChunkEditRepository`) mais en laisse le module pur `chunk_editing.py`.
- **Remediation** : supprimer `_TEXT_LABELS`, `chunk_editing.py` et son test ; brancher `rebuildAnalysisEdits` (action « reconstruire le cache » dans l'UI) ou le retirer avec la route (voir audit 04).

### [INFO] Commentaires périmés (reconduit, +1)

- **Localisation** : `document-parser/services/analysis_service.py:108-112` (promoteur « Wired in main.py »), `document-parser/services/chunk_service.py:119` (« Used by `_promote_from_analysis` », fonction inexistante), `frontend/src/pages/StudioPage.vue:16` et `:479` (noms de modes français).
- **Remediation** : inchangée ; supprimer avec le code mort du promoteur.

### [INFO] Imports locaux redondants (3.3.3 jugé conforme)

- **Localisation** : `document-parser/persistence/analysis_edit_repo.py:216` (`import hashlib` dans `_hash_command`) ; `document-parser/services/chunk_service.py:788` (`import hashlib` local alors que le module l'importe déjà en tête, `:17`, depuis 0.7.4).
- **Analyse** : ordre des imports correct dans tous les fichiers nouveaux lus (stdlib, `docling_core`/`fastapi`, puis `domain`/`infra`/`persistence`). Les imports locaux ne violent pas l'ordre mais n'ont pas de raison d'être (pas de cycle, pas de dépendance lourde). `ruff` non lancé (consigne).

### [INFO] Constantes magiques dans le nouveau code (renvoi audit 05)

- **Localisation** : `document-parser/infra/docling_projector.py:132` et `:192` (`792.0`, `612.0` alors que `DEFAULT_PAGE_WIDTH/HEIGHT` existent, `domain/value_objects.py:14-15`) ; `document-parser/infra/docling_editor.py:176` (bornes de niveau `-1`/`6`) ; `document-parser/api/analysis_edits.py:112-116` (409/400) ; `frontend/src/features/analysis-editor/store.ts:108` (`400` ms), `ui/AnalysisEditor.vue:428` (`4000` ms), `:490` (`1000` éléments).
- **Remediation** : voir audit 05 (5.3).

### [INFO] Mémoïsation dans les lectures (3.2.5 jugé conforme)

- **Localisation** : `document-parser/services/analysis_edit_service.py:73`, `:83-85`, `:101-102` (`_unedited_projection`, cache à une entrée écrit par `load_editor`) ; préexistants `services/navigation_service.py:101`, `services/parse_loader.py:99-111`.
- **Analyse** : `load_editor` n'est pas un `get_*` et l'effet est un cache idempotent indexé par `(base.id, hash)`. Les nouveaux `get_*` (`get_selection`, `get_chunk_source`, `deps.get_analysis_edit_service`) sont des lectures pures.

### [INFO] Profondeur d'imbrication (inchangé)

- **Localisation** : `document-parser/infra/local_chunker.py:24` (`_chunk_sync`, 7 niveaux, inchangé depuis 0.7.0).
- **Constat** : le code de l'éditeur reste plat. Les chaînes `if/elif` de `infra/docling_editor.py:116-134` et `api/analysis_edits.py:89-105` sont des dispatchs à un niveau, pas une imbrication réelle.

---

## Delta vs 0.7.3

**Score : 44 → 39 (−5).** Items conformes : 7/14 → 6/14. Le seul item perdu est 3.2.4 (poids 1), à cause des flags `select_analysis`, `edited` et `additive` introduits par l'éditeur.

| Écart 0.7.3 | Statut 0.7.4 | Détail |
|-------------|--------------|--------|
| [MAJ] 3.1.3 Cartes MCP en français | **Toujours ouvert, inchangé** | `mcp_adapter/` intact depuis 0.7.3 ; s'y ajoutent ~12 libellés anglais hors i18n dans l'éditeur (MIN) |
| [MAJ] 3.2.1 Orchestration multi-responsabilités | **Toujours ouvert, aggravé** | 5 cas reconduits, 5 nouveaux (`save`, `_merge_text`, `_move_element`, `BboxCanvas.draw`, `export`) |
| [MAJ] 3.3.2 Fourre-tout `chunk_service.py` | **Toujours ouvert** | 1019 → 935 l. mais 3 concepts ; nouveaux cas : store et SFC de l'éditeur |
| [MIN] 3.1.1 Nommage | Toujours ouvert, étendu | ~20 nouvelles fonctions nommées par leur résultat |
| [MIN] 3.2.2 Fonctions > 30 lignes | **Aggravé** | Python 45 → 53 ; `BboxCanvas.draw` 75 → 120 |
| [MIN] 3.2.3 Fonctions > 4 paramètres | **Aggravé** | Python 29 → 36 ; front 0 → 1 |
| [MIN] 3.3.1 Fichiers > 300 lignes | **Aggravé** | Python 14 → 17, front 26 → 30 |
| [INFO] Constantes magiques | Toujours présent | + doublons des défauts de page et des délais de l'éditeur |
| [INFO] Code mort | Partiellement résorbé | `ChunkEdit`, `ChunkEditAction`, `chunk_edits` retirés ; `_TEXT_LABELS` et `rebuildAnalysisEdits` ajoutés |
| [INFO] Commentaires périmés | Toujours présent | + `chunk_service.py:119` |
| [INFO] Booléens de configuration | Inchangé | mais trois vrais flags apparaissent (nouveau MIN 3.2.4) |
| [INFO] Variables d'une lettre | Inchangé | rien de nouveau dans l'éditeur |
| [INFO] `get_*` à mémoïsation | Inchangé | + cache `_unedited_projection` |
| [INFO] JS inline des cartes MCP | Inchangé | renvoi audits 05 / 10 |
| [INFO] Imbrication | Inchangé | `_chunk_sync` 7 |

Nouveaux écarts 0.7.4 : [MIN] 3.2.4 (flags), [MIN] libellés anglais hors i18n dans l'éditeur, 2 INFO (imports locaux, dead code nouveau intégré à l'INFO existant). Aucun écart de 0.7.3 n'est corrigé.

---

## Points positifs

- **Cœur de domaine pur et court** : `domain/analysis_editing.py` (145 l.) ne contient que des dataclasses gelées et une fonction pure, `active_edit_commands` (`:119-145`), qui résout l'historique en commandes actives sans I/O.
- **Dispatch simple et lisible** : `DoclingDocumentEditor._apply_one` (`infra/docling_editor.py:107-134`) est un `if/elif` par type de commande, sans registre ni stratégie ; chaque opération a sa méthode privée.
- **Commentaires « pourquoi » de qualité** : `infra/docling_projector.py:67-69` (pourquoi `orig` est réécrit seulement dans la copie d'export), `services/analysis_edit_service.py:204-205` (SQLite fait foi, le graphe est reconstructible), `infra/docling_editor.py:56-57` (pourquoi l'aller-retour JSON), `persistence/database.py:288-291` (pourquoi la règle « both or neither » n'est pas en base sur un upgrade), `commands.ts:23-30` (#392, pourquoi le repli s'arrête à une commande structurelle).
- **Logique front extraite en fonctions pures** : `features/analysis-editor/commands.ts` (82 l., `coalesceCommands`, `inReadingOrder`, `mergeValidationMessage`) est testé sans Vue (`commands.test.ts`).
- **Upgrade 0.7.3 → 0.7.4 minimal et idempotent** : `_upgrade_from_0_7_3` (`persistence/database.py:314-330`) tient en 17 lignes, documentées.
- **Nettoyage réel** : retrait de l'audit trail `ChunkEdit` jamais lu (`chunk_service.py` −84 l., `models.py`, `value_objects.py`, table `chunk_edits`).
- **i18n de la feature** : 112 clés fr/en ajoutées pour l'éditeur ; aucun texte français hors `i18n.ts` dans le nouveau code.
- **Aucun code commenté** laissé en place.

---

## Verdict partiel : NO-GO

Score **39/100** (< 60), **0 écart CRITICAL**, **3 écarts MAJOR** (au seuil, pas au-delà de 3).

Le NO-GO vient du barème, comme en 0.7.3, et s'aggrave d'un item (3.2.4). Aucun écart ne présente de risque fonctionnel ou de sécurité. Chemin le plus court vers GO CONDITIONNEL (≥ 60), dans l'ordre coût/gain :

1. **3.2.4** : remplacer les trois flags (`complete_and_select`, `export_edited`, `extendSelection`). Effort S. Score : 44.
2. **3.1.3** : passer les cartes MCP en anglais avec table fr/en, et traduire la douzaine de libellés anglais de l'éditeur. Effort S. Score : 56.
3. **3.1.1** : renommer les fonctions publiques/à effet du MCP et de l'éditeur, ou acter la convention dans la fiche. Effort S. Score : 61.

Les trois MAJ de structure (3.2.1, 3.3.2) restent la dette de fond : le découpage de `chunk_service.py` et celui du store / SFC de l'éditeur adressent à eux seuls 3.2.1, 3.2.2, 3.3.1 et 3.3.2.

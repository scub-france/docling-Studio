# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `efc0bc5`, arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`2d5a80e`, score 61)

Code non exécuté : aucune suite n'a tourné sur ce commit

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 10 / 14 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 7 |

**Calcul** : poids conformes = 13 (3.1.1=1, 3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.2=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18 → `13 / 18 × 100 = 72,2` → **72**. Contrôle : 61.

### Méthode

- Analyse statique de l'arbre de travail. Aucun outil du projet lancé (ni pytest, ni ruff, ni eslint, prettier, vue-tsc, vitest, ni build) ; aucun résultat de suite n'existe pour `efc0bc5` (les messages de commit `8a60cee`, `453a1b9`, `18cdf1b`, `e03ac99`, `81e11f3` le disent).
- **Les scripts du contrôle n'existent plus** (le dossier de travail de la session précédente a été vidé). Je les ai **reconstruits** à partir des seuils et de la méthode du rapport de contrôle, puis **étalonnés sur `2d5a80e`** (arbre extrait par `git archive` dans un dossier temporaire) avant de les passer sur `efc0bc5`. Étalonnage obtenu, identique au contrôle sur toutes les mesures : 135 `.py` (22 171 l.), 162 `.vue`/`.ts` (29 097 l.), 18 + 30 fichiers > 300, 52 + 20 fonctions > 30 lignes, 39 + 2 fonctions > 4 paramètres, 18 paramètres booléens.
- Règles de mesure retrouvées par l'étalonnage : Python, longueur = de la première instruction après la docstring à la dernière ligne, paramètres hors `self`/`cls`, tests exclus ; TS/Vue, longueur = de la signature à l'accolade fermante, `<script>` des `.vue` seulement, setup des `defineStore` exclus, tests exclus ; fichiers, `wc -l` sur le fichier entier.
- Nommage (3.1.1) : différence des ensembles de noms de fonctions entre `2d5a80e` et `efc0bc5` (75 nouveaux noms Python, 29 TS), chacun lu. Code mort : références comptées par `rg -w` hors tests. Imports inutilisés : deux scripts AST (Python, TypeScript) sur les fichiers changés, le second vérifié sur un cas construit.

---

## Métriques (contrôle → validation)

| Mesure | Contrôle `2d5a80e` | Validation `efc0bc5` |
|--------|--------------------|----------------------|
| Fichiers `.py` source | 135 (22 171 l.) | 146 (23 415 l.) |
| Fichiers `.vue`/`.ts` source | 162 (29 097 l.) | 171 (29 472 l.) |
| `.py` > 300 lignes | 18 | 18 |
| `.vue`/`.ts` > 300 lignes | 30 | **31** |
| Fonctions Python > 30 lignes | 52 | **44** |
| Fonctions TS/Vue > 30 lignes | 20 | **21** |
| Fonctions Python > 4 paramètres | 39 | **41** |
| Fonctions TS > 4 paramètres | 2 | **1** |
| Paramètres booléens Python | 18 | 20 (aucun flag) |
| Fonctions faisant plusieurs choses (3.2.1) | 9 | **2** |
| Fichiers fourre-tout (3.3.2) | 5 | **0** |
| Fonctions nommées par leur résultat | 0 | 0 |
| Code commenté | 0 | 0 |

Détail des variations :

- **Fichiers > 300** : Python, sort `mcp_adapter/sources_view.py` (369 → 97), entre `services/chunk_push_service.py` (365) ; `services/chunk_service.py` 923 → 426 reste au-dessus. Grossissent `api/schemas.py` 939 → 1092, `domain/models.py` 314 → 436, `domain/ports.py` 766 → 826, `infra/docling_editor.py` 338 → 382, `bootstrap/builder.py` 301 → 319, `bootstrap/factories.py` 363 → 374. Front, entre `features/document/ui/BboxCanvas.vue` (298 → 335, découpage de `draw`) ; restent au-dessus après découpage `AnalysisEditor.vue` (805 → 620), `PagePreviewWithOverlay.vue` (761 → 738), `analysis-editor/store.ts` (444 → 409) ; `StructureViewer.vue` 458 → 465, `BboxOverlay.vue` 326 → 327.
- **Fonctions > 30 lignes, Python (−8)** : sortent `chunk_editing.merge` (33), `chunk_editing.split` (36), `docling_editor._merge_text` (50), `_move_element` (47), `analysis_edit_service.save` (66), `ChunkService.__init__` (33), `_build_tree_nodes` (38), `merge_chunks` (43), `split_chunk` (41). Raccourcies mais encore au-dessus : `parse_index.build_index` 79 → 31, `_finalize_analysis` 67 → 48, `push_to_store` 103 → 40, `version_service.restore` 53 → 36. Entre `mcp_stdio.py:48` `_serve` (36). S'allongent `bootstrap/builder.py:108` `build` 100 → 116, `infra/settings.py:210` `from_env` 80 → 85.
- **Fonctions > 30 lignes, TS (+1)** : `BboxCanvas.vue:84` `draw` 124 → 34 (toujours au-dessus) ; entre `features/analysis-editor/previewScheduler.ts:23` `createPreviewScheduler` (35, fabrique à fermeture, lue comme `usePagination`).
- **Paramètres, Python (+2)** : sortent `_build_item_subtree` (6), `_make_node` (5), `_upsert_link_ingested` (5), `persistence/analysis_edit_repo.py` `_hash_command` (5). Entrent `services/document_tree_service.py` `__init__` (5), `services/export_service.py` `__init__` (5), `services/parse_loader.py` `__init__` (5), `services/preview_service.py` `__init__` (5), `services/chunk_push_service.py:41` `__init__` (7, mots-clés), `bootstrap/factories.py:227` `build_document_service` (6). S'élargissent `services/chunk_service.py:107` `__init__` 12 → 13, `services/document_service.py:51` `__init__` 6 → 8 (injection de la lecture de l'analyse courante, `4939413`).
- **Paramètres, TS (−1)** : `StructureViewer.vue:239` `drawVisitBadge` 6 → 2 (objet `VisitBadge`). Reste `PagePreviewWithOverlay.logic.ts:14` `isPageInRenderWindow` (6).
- **Booléens (+2)** : `domain/models.py:173` `are_chunks_stale(..., *, has_chunks)` et `domain/analysis_editing.py:238` `check_heading_level(level, *, title_exists)` : deux faits passés par mot-clé, pas des flags qui changent le comportement de la fonction.

---

## Checklist

| # | Item | Poids | Conforme | Contrôle `2d5a80e` → validation `efc0bc5` |
|---|------|-------|----------|-------------------------------------------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | oui | 0 → 0 ; 75 nouveaux noms Python et 29 TS lus, tous menés par un verbe (`resolve_*`, `record_*`, `check_*`, `queueCommand`, `undoPending`, `drawReadingOrderBadges`…) ; `selection` et `chunk_source` (`domain/models.py:123`, `:129`) sont des `@property`, exclues comme au contrôle |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | pas de régression (`frame`, `highlighted`, `located`, `stacks`, `resolved_store_id`) |
| 3.1.3 | Code en anglais, i18n | 2 | oui | résidu `docling_projector.py:147` inchangé ; les deux nouveaux composants passent tout par `t()` et les 64 clés `analysisEditor.*` employées existent en FR et EN dans `shared/i18n.ts` |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | aucun nouveau nom abrégé (`cx`/`cy` = centre du badge, convention géométrique) |
| 3.2.1 | Une fonction = une chose | 2 | **non** | 9 → **2** (les deux fonctions Neo4j, laissées exprès) |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | non | 72 → **65** (44 Py + 21 TS) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | non | 41 → **42** (41 Py + 1 TS) |
| 3.2.4 | Pas de flag arguments | 1 | oui | 18 → 20 booléens, aucun flag ajouté |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | nouveaux `get_last_sequence`, `_get_label_type` purs ; `DocumentTreeService.get_tree` lit comme l'ancien `ChunkService.get_tree` (même appel `load_active_result`) |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | non | 48 → **49** (18 Py + 31 front) |
| 3.3.2 | Un concept par fichier | 2 | **oui** | 5 → **0** (voir Delta, case par case) |
| 3.3.3 | Imports ordonnés | 1 | oui | **non vérifié par ruff** (non lancé) ; imports des 11 nouveaux modules Python lus : stdlib, tiers, internes, `TYPE_CHECKING` pour les annotations seules ; aucun import inutilisé trouvé par script |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | aucun commentaire faux ajouté ; deux commentaires périmés déplacés tels quels (INFO) |
| 3.4.2 | Pas de code commenté | 1 | oui | 0 → 0 (lignes ajoutées de commentaire relues : de la prose) |

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration multi-responsabilités (réduit, 2 fonctions)

- **Localisation** : `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l., 7 paramètres), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.).
- **Constat** : 9 → 2. Les 7 autres sont découpées en étapes nommées, au même niveau d'abstraction (détail dans le Delta). Les deux restantes n'ont pas bougé : `8a60cee` les laisse exprès (« their tests need a server that neither CI nor this machine runs, and the module goes in 0.8.0 »). La dépréciation de l'ingestion Neo4j figure au CHANGELOG (`CHANGELOG.md:77`), mais elle y figurait déjà au contrôle, qui comptait ces fonctions : même lecture ici, elles comptent.
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** : deux voies. (a) Les sortir du périmètre de l'audit par une décision écrite (le module part en 0.8.0) : l'item devient conforme, score 83. (b) Découper : `write_document` en `_write_document_node` / `_write_pages` / `_write_items` / `_write_relations` ; `fetch_graph` en une requête par type de nœud plus un assemblage. Sans serveur Neo4j pour les tests, (a) est la voie sûre.

### [MIN] Fonctions au-delà de 30 lignes (44 Python, 21 TS)

- **Localisation** : pires : `document-parser/infra/neo4j/tree_writer.py:69` (227), `frontend/src/features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216), `document-parser/bootstrap/builder.py:108` (`build`, 116), `document-parser/infra/neo4j/queries.py:137` (115). Nouveaux : `document-parser/mcp_stdio.py:48` (`_serve`, 36), `frontend/src/features/analysis-editor/previewScheduler.ts:23` (`createPreviewScheduler`, 35). Juste au-dessus après découpage : `document-parser/domain/parse_index.py:91` (`build_index`, 31), `frontend/src/features/document/ui/BboxCanvas.vue:84` (`draw`, 34).
- **Constat** : 72 → 65.
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4 ; `build_index` et `draw` passent sous le seuil en sortant respectivement la construction du `DocumentIndex` et la lecture des jetons dans une fonction.

### [MIN] Fonctions à plus de 4 paramètres (41 Python, 1 TS)

- **Localisation** : constructeurs en tête : `document-parser/services/chunk_service.py:107` (13), `document-parser/services/analysis_service.py:83` (10), `document-parser/services/store_service.py:231` (`update_store`, 10), `document-parser/services/document_service.py:51` (8). Nouveaux : voir Métriques (4 constructeurs à 5 par l'injection de `current_analysis`, `chunk_push_service.py:41`, `factories.py:227`). TS : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14` (`isPageInRenderWindow`, 6).
- **Constat** : 41 → 42. `drawVisitBadge` est réglé ; le reste vient surtout de l'injection de dépendances, qui ajoute un port par constructeur.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : objet de paramètres pour `isPageInRenderWindow` ; côté Python, regrouper les dépôts d'un service dans un objet de dépendances (`ChunkService` construit déjà deux sous-services avec les mêmes dépôts). Hors d'atteinte pour 0.7.4.

### [MIN] Fichiers sources au-delà de 300 lignes (18 Python, 31 front)

- **Localisation** : nouveaux : `document-parser/services/chunk_push_service.py` (365), `frontend/src/features/document/ui/BboxCanvas.vue` (335). Plus gros : `frontend/src/shared/i18n.ts` (1642), `frontend/src/pages/StudioPage.vue` (1444), `document-parser/api/schemas.py` (1092, +153), `document-parser/domain/ports.py` (826, +60).
- **Constat** : 48 → 49. Les découpages ont fait baisser trois gros fichiers sans les passer sous 300 ; `BboxCanvas.vue` franchit le seuil par le découpage même (en-têtes et docstrings des quatre étapes). `frontend/src/pages/IngestLaunchDialog.vue` (399) est compté alors qu'il n'est importé nulle part (INFO code mort).
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : supprimer les pages mortes (−1 fichier > 300) ; sortir les quatre fonctions de dessin de `BboxCanvas.vue` dans `BboxCanvas.draw.ts` (−1). Le reste est hors d'atteinte pour 0.7.4.

### [INFO] Code mort : trois fichiers de page jamais importés (relevé à cette validation, préexistant)

- **Localisation** : `frontend/src/pages/DocChunkTab.vue` (241 l.), `frontend/src/pages/IngestLaunchDialog.vue` (399 l.), `frontend/src/pages/DocIngestTab.logic.ts` (192 l.).
- **Constat** : `rg` sur `frontend/` (hors `node_modules`) : aucun import de `DocChunkTab` ni d'`IngestLaunchDialog`, ni par le routeur ni par un composant ; `DocIngestTab.logic.ts` n'est importé que par `IngestLaunchDialog.vue:126` (mort) et par son test. `DocIngestTab.vue` n'existe plus. Même situation à `2d5a80e` : le contrôle ne l'avait pas relevé.
- **Analyse** : ce n'est pas du code commenté, donc pas l'item 3.4.2 ; même classement que les autres restes de code mort du contrôle (INFO, renvoi audit 05/11). Effet mesurable : un fichier > 300 compté en 3.3.1.
- **Remediation** : supprimer les trois fichiers et `DocIngestTab.logic.test.ts`, ou les rebrancher si une route est prévue.

### [INFO] Restes de code mort et commentaires périmés reconduits

- Code mort inchangé : `document-parser/services/analysis_service.py:116` / `:122` (`_chunk_promoter`, `set_chunk_promoter`, câblé par `bootstrap/builder.py:170` mais jamais appelé), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `_neutralise_all` en double (`document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`), `document-parser/domain/hashing.py:43` (`hash_chunkset`, tests seulement), `frontend/src/features/document/ui/BboxCanvas.vue:29` / `:319` (`UNKNOWN_ELEMENT_COLOR` importé pour être `void`-é), `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:598` (règle `.merge-button` sans élément).
- Levé : `document-parser/domain/chunk_editing.py` est désormais utilisé par `ChunkService.split_chunk` / `merge_chunks` (`services/chunk_service.py:242`, `:264`, `:275`) ; `_get_utc_now` / `_generate_id` ne sont plus définis qu'une fois, publics, dans `document-parser/domain/models.py:28` / `:33`.
- Aucun code mort laissé par les déplacements : toutes les fonctions nouvelles ont au moins un appelant hors définition ; aucun test n'importe un symbole déplacé (`build_sources_card`, `render_sources_text`, `_compute_chunkset_hash`, `_build_tree_nodes` ne sont cherchés par aucun test) ; `PdfPagePreview.vue` reste utilisé (`frontend/src/pages/StudioPage.vue:258`, `frontend/src/features/analysis/ui/StructureViewer.vue:33`, `frontend/src/features/document/ui/PagePreview.vue:31`).
- Commentaires périmés, déplacés tels quels : `document-parser/services/chunk_service.py:129-131` (« Wired in main.py » ; c'est `bootstrap/builder.py:174`), `document-parser/services/analysis_service.py:111` (idem) ; `document-parser/services/chunk_push_service.py:108` et `:119-123` (« per-store dispatch is a follow-up ») alors que `_resolve_targets` (`:205`) fait ce dispatch depuis #279.

### [INFO] Paires incohérentes reconduites

- `getNodeColor` / `getKindColor` (`frontend/src/features/analysis/ui/GraphView.vue:149`, `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:184`, `frontend/src/features/reasoning/kindColors.ts:37`), `formatDuration` en double sens, `_hash_command` (désormais `domain/analysis_editing.py:152` `hash_command`, une seule implémentation : levé), `hash_chunkset` (`domain/hashing.py:43`) / `_compute_chunkset_hash` (déplacé en `services/chunk_push_service.py:350`) : inchangé. Renvoi audit 05.

### [INFO] Résidus 3.1.3 et 3.2.4 reconduits

- 3.1.3 : `document-parser/infra/docling_projector.py:147`. Le libellé « Page N » déplacé dans `frontend/src/features/document/ui/PageRaster.vue:12` (`alt`) et `PagePreviewWithOverlay.vue:86` est le même mot en français et en anglais : pas d'écart. Les nouveaux messages d'erreur backend (`domain/analysis_editing.py:244-247`, `infra/body_limit.py`, `services/chunk_push_service.py:168-201`) sont en anglais comme tous les messages d'API, relayés tels quels par l'éditeur : même lecture qu'au contrôle.
- 3.2.4 : flag HTTP `edited` (`document-parser/api/documents.py:117`, `export_document`).

### [INFO] Mesures reconstruites, pas reprises

- Les scripts du contrôle ont disparu avec le dossier temporaire de la session. Les scripts reconstruits reproduisent exactement les chiffres du contrôle sur `2d5a80e` (étalonnage ci-dessus), ce qui donne une base de comparaison fiable. Pour ne plus dépendre d'un dossier volatil, versionner les scripts de mesure de l'audit 03 (et la liste de verbes corrigée du contrôle) sous `docs/audit/`.

### [INFO] Constructeurs qui s'élargissent avec chaque port

- `ChunkService.__init__` (13) construit lui-même `ChunkPushService` et `DocumentTreeService` (`services/chunk_service.py:133-148`) pour que routes et tests restent inchangés. C'est une façade honnête, mais le composition root ne voit pas ces deux services : le jour où une route veut `ChunkPushService` seul, il faudra les construire dans `bootstrap/factories.py` et faire de `ChunkService` un simple service d'édition.

---

## Delta vs contrôle 2d5a80e

**Score : 61 → 72 (+11).** Items conformes : 9/14 → 10/14. Item gagné : 3.3.2. Aucun item perdu. Verdict : GO CONDITIONNEL → **GO CONDITIONNEL**.

| Écart du contrôle | Statut à cette validation | Mesures contrôle → validation |
|-------------------|---------------------------|-------------------------------|
| [MAJ] 3.2.1 Orchestration multi-responsabilités | **Réduit** (ouvert) | 9 → 2 |
| [MAJ] 3.3.2 Fichiers fourre-tout | **Résolu** | 5 → 0 |
| [MIN] 3.2.2 Fonctions > 30 lignes | Réduit | 72 → 65 |
| [MIN] 3.2.3 Fonctions > 4 paramètres | Aggravé | 41 → 42 |
| [MIN] 3.3.1 Fichiers > 300 lignes | Aggravé | 48 → 49 |
| [INFO] Code mort, commentaires périmés, résidus | Partiellement levés (`chunk_editing`, helpers dupliqués, `_hash_command`) ; un nouveau relevé (pages mortes, préexistant) | |

### 3.2.1, cas par cas

| Fonction (contrôle) | Maintenant | Statut |
|---------------------|------------|--------|
| `chunk_service.py:474` `push_to_store` (103) | `document-parser/services/chunk_push_service.py:110` (40) : `require_document` → `_require_ingestion` → `_resolve_store` → `_load_chunks_to_push` → `_resolve_targets` → `ingest` → `_record_push` ; la façade `chunk_service.py:382` délègue | Résolu |
| `parse_index.py:80` `build_index` (79) | `document-parser/domain/parse_index.py:91` (31) : `_map_sections`, `_read_page_sizes`, `_locate_items`, puis construction | Résolu (reste en 3.2.2) |
| `analysis_service.py:480` `_finalize_analysis` (67) | `document-parser/services/analysis_service.py:485` (48, dont 17 de commentaires) : `_chunk_result`, `_record_analysis_version`, `complete_and_select`, `_transition_document`, `_write_tree_to_graph` | Résolu (reste en 3.2.2) |
| `analysis_edit_service.py:137` `save` (66) | `document-parser/services/analysis_edit_service.py:138` (≤ 30) : `_ensure_stream`, `check_expected_sequence`, `_build_cache`, `_refresh_graph` | Résolu |
| `docling_editor.py:204` `_merge_text` (50) | `document-parser/infra/docling_editor.py:210` : contrôles du domaine (`check_merge_request`, `check_mergeable_labels`), `_gather_merge_run` (`:233`), `_join_merged_text` (`:360`) | Résolu |
| `docling_editor.py:261` `_move_element` (47) | `document-parser/infra/docling_editor.py:255` : simple aiguillage vers `_move_relative_to_target` (`:273`) et `_move_before_sibling` (`:306`), un par protocole | Résolu |
| `BboxCanvas.vue:80` `draw` (124) | `frontend/src/features/document/ui/BboxCanvas.vue:84` (34) : `prepareCanvas`, `drawElementBoxes`, `drawHighlightedBoxes`, `drawNextElementMarker`, `drawReadingOrderBadges` ; `computeBadgeRect` sorti en `BboxCanvas.logic.ts` | Résolu (reste en 3.2.2) |
| `tree_writer.py:69` `write_document` (227) | inchangé | Ouvert |
| `queries.py:137` `fetch_graph` (115) | inchangé | Ouvert |

Les étapes sont fidèles : `draw` relu ligne à ligne contre `2d5a80e` (mêmes jetons `--success`, `--accent`, `--bg-elevated`, `--text`, `--border-light`, `--on-bright`, même ordre de dessin, même lecture paresseuse du style).

### 3.3.2, cas par cas (vraie séparation ou même fourre-tout réparti ?)

| Fichier (contrôle) | Maintenant | Statut |
|--------------------|------------|--------|
| `services/chunk_service.py` (923 : édition, push, arbre) | 426 l. : cycle de vie des chunks seulement. Push → `services/chunk_push_service.py` (365), arbre → `services/document_tree_service.py` (78) + projection pure `domain/document_tree.py` (166), erreurs → `services/chunk_errors.py` (46). Graphe d'imports : les deux nouveaux services n'importent que `chunk_errors` et le domaine, jamais `chunk_service` ni l'un l'autre ; seul `ChunkService` les importe, pour déléguer (`:378-398`). | Résolu : séparation réelle |
| `mcp_adapter/sources_view.py` (369 : modèle de carte + rendu texte + outils) | 97 l. : enregistrement des deux outils. Modèle et construction → `sources_card.py` (248), rendu texte → `sources_text.py` (47, n'importe que les types de la carte sous `TYPE_CHECKING`). | Résolu |
| `analysis-editor/store.ts` (444 : aperçu, undo/redo, sélection, brouillon) | 409 l. : l'état de la session d'édition. Brouillon → `pendingDraft.ts`, piles undo/redo → `commandStacks.ts`, sélection de fusion → `mergeSelection.ts`, minuterie et abandon de l'aperçu → `previewScheduler.ts` ; quatre modules purs, aucun n'importe le store, chacun avec son test. | Résolu (reste en 3.3.1) |
| `analysis-editor/ui/AnalysisEditor.vue` (805 : bannières, historique) | 620 l. (dont ~170 de CSS) : barre d'outils et trois colonnes. Bannières → `EditorBanners.vue` (108), historique → `AnalysisEditHistoryPanel.vue` (140), style commun des boutons → `editorButton.css`. Les enfants ne reçoivent que des props et émettent des événements ; aucun n'accède au store. | Résolu (reste en 3.3.1) |
| `document/ui/PagePreviewWithOverlay.vue` (761 : deux chemins parallèles image / PDF) | 738 l. : les trois paires `registerImage`/`registerPdf`, `onImageLoad`/`onPdfReady`, `onImageError`/`onPdfError` deviennent `registerRaster` (`:233`), `onRasterReady` (`:274`), `onRasterError` (`:293`), avec un `source` ; le choix canvas/PNG vit dans `PageRaster.vue` (61). | Résolu (reste en 3.3.1) |

Nouveaux écarts depuis `2d5a80e` : `BboxCanvas.vue` et `chunk_push_service.py` au-delà de 300 lignes (3.3.1), six signatures à 5+ paramètres par l'injection de dépendances (3.2.3), `_serve` et `createPreviewScheduler` au-delà de 30 lignes (3.2.2). Aucun écart nouveau sur les items de poids 2.

---

## Relecture avant première exécution

Périmètre lu en entier : `frontend/src/features/analysis-editor/` (`store.ts`, `pendingDraft.ts`, `commandStacks.ts`, `mergeSelection.ts`, `previewScheduler.ts`, `ui/AnalysisEditor.vue`, `ui/AnalysisEditHistoryPanel.vue`, `ui/EditorBanners.vue`, `ui/editorButton.css` et leurs tests), `frontend/src/features/document/ui/` (`PageRaster.vue`, `PagePreviewWithOverlay.vue`, `BboxCanvas.vue`, `BboxCanvas.logic.ts`, `PdfPageCanvas.vue` et leurs tests), `frontend/src/features/analysis/ui/StructureViewer.vue`, `BboxOverlay.vue`, `frontend/src/shared/cssTokens.ts` et son test. Côté backend, lecture des modules de `8a60cee` et de leurs appelants.

**Aucun défaut probable de type, de lint ou d'exécution trouvé.** Ce qui a été vérifié, point par point :

- **Props et émissions** : `EditorBanners` déclare 6 props et 5 émissions ; `AnalysisEditor.vue:120-132` passe exactement ces 6 props, avec les mêmes types (`string | null`, `number`, `boolean` via `Boolean(...)`), et écoute les 5 émissions en kebab-case. `AnalysisEditHistoryPanel` (`history`, `canChange`, `setActive: [number, boolean]`) ↔ `AnalysisEditor.vue:133-138`. `PageRaster` (`documentId`, `document`, `failed`, `pageNumber`, `priority: 'high' | 'low'` ; `ready: [HTMLElement, source]`, `error: [source]`) ↔ `PagePreviewWithOverlay.vue:98-110` et `onRasterReady` / `onRasterError` (`source: 'pdf' | 'image'`, compatible avec le type local `PageRasterSource`). `PdfPageCanvas` émet `ready: [HTMLCanvasElement]` et `error: []`, relayés par `PageRaster.vue:6-7`.
- **Imports** : tous les chemins résolvent (`./commandStacks`, `./mergeSelection`, `./pendingDraft`, `./previewScheduler`, `./PageRaster.vue`, `@/shared/cssTokens`, `./BboxCanvas.logic`, `Rect` et `Scale` exportés par `shared/types.ts:168`, `:173`). `getPreviewUrl`, retiré des imports de `PagePreviewWithOverlay.vue`, n'y est plus référencé. Aucun import ni variable inutilisé (script AST sur les 32 fichiers TS/Vue changés ; contrôle visuel des déstructurations `{ ctx, scale }: DrawFrame`, que `@typescript-eslint/no-unused-vars` ne signale pas). Aucun import croisé interdit par `no-restricted-imports` (`'../api'` ne correspond pas à `'../*/api'`).
- **Template** : chaque identifiant des templates est défini dans le `<script setup>` correspondant ; les 64 clés i18n `analysisEditor.*` existent dans les deux langues.
- **`<style scoped src="./editorButton.css">`** : forme admise par `@vitejs/plugin-vue` (style importé par `src`, avec `scoped`, à côté d'un second bloc `<style scoped>`). `EditorBanners` est un fragment (plusieurs racines) : il ne reçoit aucun attribut non déclaré, donc pas d'avertissement « extraneous attrs ».
- **Tests** : aucun test n'importe un symbole déplacé. `PageRaster.test.ts` attend `/api/documents/doc-1/preview?page=3` dans l'URL, qui est bien un préfixe de `getPreviewUrl` (`features/document/api.ts:50`) ; `PagePreviewWithOverlay.test.ts:40` rend `PageRaster` réellement (`stubs: { PageRaster: false }`) pour compter les `pdf-page-canvas-stub`. `BboxCanvas.logic.test.ts` : 1 chiffre → 17 → plancher 18, 2 chiffres → 24, conformes à la formule. `AnalysisEditor.a11y.test.ts` monte avec `mount` (pas `shallowMount`), donc le panneau d'historique rendu par l'enfant reste trouvable par `data-e2e`. `cssTokens.test.ts` caste son faux `CSSStyleDeclaration` (`as unknown as`), et les tests sont exclus de `vue-tsc` (`tsconfig.json`).
- **Comportement** : le store reproduit à l'identique l'ancienne gestion de l'aperçu (`previewScheduler.begin/isCurrent/abort/cancel` ↔ ancien `abortController`/`previewTimer`), et `PagePreviewWithOverlay` l'ancienne séquence d'enregistrement / chargement / erreur, y compris le second passage de focus réservé aux images.
- **Prettier** : aucune ligne nouvelle > 100 caractères hors chaînes insécables préexistantes.

Remarques sans effet sur une exécution, à traiter avec le reste :

| Où | Quoi | Correctif |
|----|------|-----------|
| `frontend/src/features/document/ui/BboxCanvas.vue:29`, `:318-319` | `UNKNOWN_ELEMENT_COLOR` importé pour être aussitôt `void`-é (préexistant) | Retirer l'import et les deux lignes : `getElementColor` porte déjà le repli |
| `frontend/src/features/analysis-editor/previewScheduler.ts:37-40` | `timer` n'est pas remis à `null` après l'exécution de la tâche ; `clearTimeout` sur un id échu ne fait rien | Optionnel : `timer = setTimeout(() => { timer = null; task() }, delayMs)` |
| `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:598` | règle `.merge-button` sans élément (préexistant) | La supprimer |
| `document-parser/services/chunk_push_service.py:108`, `:119-123` | commentaire « per-store dispatch is a follow-up » contredit par `_resolve_targets` | Réécrire le commentaire |

Ce que la lecture ne peut pas garantir : le typage des expressions de template par `vue-tsc` (casts `as` dans `PageRaster.vue:17`, déjà utilisés ailleurs dans le projet), la propagation de l'attribut de portée CSS à travers `PageRaster` → `PdfPageCanvas` (racine de racine), l'ordre exact attendu par ruff `I` / `TC` sur les nouveaux modules Python, et le résultat réel des suites. Lancer `vue-tsc --noEmit`, `eslint src/`, `prettier --check src/`, `vitest run`, puis `ruff check`, `ruff format --check`, `pytest` avant toute conclusion de release.

---

## Points positifs

- **Les découpages séparent vraiment** : aucun des nouveaux modules n'importe le fichier dont il sort ; les modules du store sont purs et testés un par un ; les enfants de l'éditeur ne voient pas le store.
- **7 des 9 fonctions multi-responsabilités découpées**, en étapes nommées et fidèles à l'ancien comportement (vérifié sur `draw` ligne à ligne), sans toucher aux routes ni aux signatures publiques.
- **Doublons supprimés en passant** : `get_utc_now` / `generate_id` une seule fois, `hash_command` une seule implémentation, `chunk_editing` enfin utilisé par le service.
- **`drawVisitBadge`** ramené à un objet de paramètres, comme proposé au contrôle.
- **Commits honnêtes** : chacun dit qu'il n'a rien exécuté et signale l'écart de comportement introduit (`push_to_store` sans dépôt de stores).

---

## Verdict partiel : GO CONDITIONNEL

Score **72/100** (60-79), **0 CRITICAL**, **1 MAJOR** (3.2.1 : 2 fonctions Neo4j, ≤ 3 donc non bloquant), 3 MINOR, 7 INFO.

Conditions : (1) faire tourner les suites (aucune n'a tourné sur `efc0bc5`) ; la relecture ne trouve rien qui doive casser, mais elle ne remplace pas `vue-tsc` et `vitest`. (2) Pour le MAJ restant, acter par écrit que `infra/neo4j/` sort du périmètre de l'audit (module retiré en 0.8.0) : l'item 3.2.1 devient conforme et le score passe à **83** (GO). Supprimer les trois pages mortes est le seul gain rapide sur les MIN, et il ne suffit pas à rendre 3.3.1 conforme.

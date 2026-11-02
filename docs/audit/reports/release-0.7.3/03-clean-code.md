# Rapport d'audit : Clean Code

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 14 |
| Score | 44 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 8 |

**Detail du calcul** : somme des poids conformes = 8 (3.1.2=1, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur un total de 18 → `8 / 18 * 100 = 44,4` → **44**.

Périmètre audité : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/` (hors `*.test.*`), arbre de travail de `release/0.7.3` au commit `02adc68`. Les deux pages HTML servies par le serveur MCP (`document-parser/mcp_adapter/citation_app.html`, `sources_app.html`) sont dans `document-parser/` : elles sont auditées comme du code source (≈ 1 650 lignes de JavaScript inline à elles deux). Répertoires non suivis `docs/demo/video/` et `experiments/laya-nav-test/` ignorés.

Méthode : analyse statique uniquement. Tailles mesurées par `wc -l` ; fonctions Python mesurées par AST (lignes de corps, hors signature et docstring) ; fonctions TS/Vue/JS mesurées avec le parseur TypeScript du projet (`frontend/node_modules/typescript`, étendue signature comprise) ; `ruff check` (config du projet) pour l'ordre des imports. Les suites de tests n'ont pas été lancées.

---

## Metriques

| Mesure | 0.7.0 | 0.7.3 | Commentaire |
|--------|-------|-------|-------------|
| Fichiers `.py` source (hors tests) | — | 119 (19 769 l.) | +41 fichiers depuis 0.7.2 (MCP, navigation, citations) |
| Fichiers `.vue`/`.ts` source (hors tests) | — | 150 (26 379 l.) | dont `shared/i18n.ts` (1 472 l., données) |
| `.py` > 300 lignes | 8 | **14** | + 2 pages HTML MCP de ~1 180 l. |
| `.vue`/`.ts` > 300 lignes | 24 | **26** | `McpConfigSection.vue` (1 109) nouveau, `App.vue` passe à 301 |
| Fonctions Python > 30 lignes de corps | ~48 | 45 | 13 dans des fichiers nouveaux ; 83 si l'on compte signature + docstring |
| Fonctions TS/Vue > 30 lignes (hors stores Pinia setup) | — | 12 | + 8 dans le JS inline des pages MCP |
| Fonctions Python > 4 paramètres | 20 | **29** | 9 dans des fichiers nouveaux ; 0 côté front |
| Imbrication max (Python / TS / JS MCP) | — | 7 / 4 / 4 | le 7 est préexistant (`local_chunker.py:24`) ; nouveau code ≤ 4 |
| Code commenté laissé en place | 0 | 0 | |
| Lignes de libellés UI en français hors `i18n.ts` | 0 | **~64** | toutes dans les 2 pages HTML MCP (19 + 45) |

### Fichiers > 300 lignes

**Python** (0.7.0 → 0.7.3) : `services/chunk_service.py` 1019 (inchangé), `api/schemas.py` 849 (707), `services/analysis_service.py` 586 (553), `domain/ports.py` 542 (454), `infra/serve_converter.py` 402 (396), `services/store_service.py` 395 (inchangé), `domain/navigation.py` 385 (**nouveau**), `mcp_adapter/sources_view.py` 369 (**nouveau**), `domain/source_map.py` 354 (**nouveau**), `bootstrap/factories.py` 354 (270, **passe le seuil**), `domain/models.py` 331, `infra/neo4j/tree_writer.py` 310, `services/citation_service.py` 307 (**nouveau**), `infra/docling_tree.py` 307 (298, **passe le seuil**). Hors `.py` : `mcp_adapter/sources_app.html` 1 188 et `mcp_adapter/citation_app.html` 1 177 (**nouveaux**). `services/source_service.py` reste juste sous le seuil (293).

**Front** (script / template / style) : `pages/StudioPage.vue` 1450 (175/505/762), `features/mcp-config/ui/McpConfigSection.vue` 1109 (169/355/577, **nouveau**), `features/chunking/ui/ChunkPanel.vue` 801, `pages/DocParseTab.vue` 794 (318/160/308), `features/document/ui/PagePreviewWithOverlay.vue` 720 (**400**/121/191, était 621), `pages/DocsLibraryPage.vue` 701 (157/201/335, était 525), `features/analysis/ui/ResultTabs.vue` 679, `features/analysis/ui/GraphView.vue` 657 (**437**/59/153), `features/chunks/ui/ChunksEditor.vue` 622, `features/store/ui/StoreForm.vue` 520, puis 16 fichiers entre 301 et 456 lignes (dont `pages/AnalysisLibraryPage.vue` 365, ex-`AnalysesPage.vue`, et `app/App.vue` 301).

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
| 3.2.4 | Pas de flag arguments | 1 | ✅ |
| 3.2.5 | Un `get_*` ne modifie pas d'état | 2 | ✅ |
| 3.3.1 | Aucun fichier source > 300 lignes | 1 | ❌ |
| 3.3.2 | Un seul concept par fichier | 2 | ❌ |
| 3.3.3 | Imports ordonnés | 1 | ✅ |
| 3.4.1 | Commentaires = « pourquoi » | 1 | ✅ |
| 3.4.2 | Pas de code commenté laissé en place | 1 | ✅ |

---

## Ecarts constates

### [MAJ] Cartes MCP : libellés UI en français codés en dur, hors i18n (nouveau)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:395` (« En attente d'une citation… »), `:611-615` (« Lire la suite », « Copier la citation », « Ouvrir dans Docling Studio »), `:814`, `:832`, `:836`, `:1165` ; `document-parser/mcp_adapter/sources_app.html:317`, `:391-392` (« mot pour mot · vérifiée par le serveur »), `:490`, `:509`, `:735`, `:751`, `:998` (`TIMEOUT_MESSAGE = "l’hôte n’a pas répondu"`), `:343` (formateur `fr()` figé sur `fr-FR`).
- **Constat** : les deux cartes servies par le serveur MCP affichent ~64 lignes de libellés en français, en dur, sans aucun mécanisme de traduction. Le choix est délibéré (commit `2374189`, « Both cards are light only and labelled in French », pour la démo sur scène), mais il part dans la release : un utilisateur anglophone de Docling Studio (appli bilingue fr/en via `shared/i18n.ts`) reçoit des cartes en français. Le reste de la fonctionnalité est en anglais, d'où des incohérences : `citation_app.html:2` déclare `<html lang="en">` sur un contenu français (lecteurs d'écran), le même message de timeout est en anglais dans `citation_app.html:706` (« the host did not answer ») et en français dans `sources_app.html:998`, et le repli texte côté serveur (`mcp_adapter/sources_view.py:338`, `sources_text`) est en anglais. Les identifiants et commentaires du JS sont, eux, en anglais.
- **Regle violee** : item 3.1.3 — « Tout le code est en anglais — les traductions i18n sont dans `shared/i18n.ts` » (poids 2).
- **Remediation** : passer les libellés des deux cartes en anglais par défaut, et regrouper les chaînes dans une table de messages en tête de chaque page (`MESSAGES = { en: {…}, fr: {…} }`) dont la locale vient du contexte hôte ou d'un réglage serveur. La page ne peut pas importer `frontend/src/shared/i18n.ts` (iframe isolée), mais la règle « une seule source par langue » peut s'appliquer localement. Corriger `lang` en conséquence. Effort faible (≈ 64 chaînes).

### [MAJ] Fonctions d'orchestration multi-responsabilités (dette 0.7.0, toujours présente, nouveaux cas)

- **Localisation** : `document-parser/services/chunk_service.py:574` (`push_to_store`, 103 l. de corps), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l.), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.) — **les trois fichiers sont identiques à v0.7.0** (`git diff v0.7.0..HEAD` vide). Nouveaux cas : `document-parser/domain/parse_index.py:80` (`build_index`, 79 l.), `document-parser/services/analysis_service.py:457` (`_finalize_analysis`, 67 l.).
- **Constat** : aucune des extractions demandées en 0.7.0 n'a été faite. Le nouveau code reproduit le motif : `build_index` enchaîne quatre calculs indépendants dans un seul corps (indexation des items, pile des titres → `heading_path`/`section_end`, tailles de pages, provenance/bbox). `_finalize_analysis` sérialise, chunke, marque terminé, enregistre la version, met à jour le statut et le nombre de pages, fait la transition de cycle de vie et écrit le graphe. Depuis #359 c'est aussi la fin du chemin d'import (`analysis_service.py:184`), donc son rôle s'est élargi. Neo4j/OpenSearch (`tree_writer.py`, `queries.py`, `push_to_store`) sont dépréciés et retirés en 0.8.0, ce qui relativise ces trois cas mais ne les efface pas pour 0.7.3.
- **Regle violee** : item 3.2.1 — « Chaque fonction fait une seule chose (Single Responsibility) » (poids 2).
- **Remediation** : pour `build_index`, extraire `_items_by_ref`, `_heading_paths`, `_page_sizes`, `_provenance` (fonctions pures, testables une à une). Pour `_finalize_analysis`, séparer « persister le résultat » de « effets de bord post-analyse » (version, lifecycle, graphe). Pour le périmètre ingestion, ne rien faire si le retrait en 0.8.0 est confirmé, et le tracer explicitement dans la dette.

### [MAJ] Fichier fourre-tout `chunk_service.py` (dette 0.7.0, inchangée)

- **Localisation** : `document-parser/services/chunk_service.py:146` (classe `ChunkService`), push vers store `:540` (`diff_against_store`), `:574` (`push_to_store`), `:693` (`list_pushes`), `:743` (`_upsert_link_ingested`), `:765` (`_mark_link_failed`) ; projection d'arbre `:885` (`_build_tree_nodes`), `:942`, `:975`, `:990`, `:1015`.
- **Constat** : fichier identique octet pour octet à 0.7.0 (1 019 lignes). Il porte toujours trois concepts : édition du chunkset, push/diff vers un store, projection d'affichage de l'arbre. Nouveau cas, moins grave : `mcp_adapter/sources_view.py` (369 l.) réunit les DTO du contrat (`:43-150`), l'enregistrement des outils (`:163`), le mapping domaine → wire (`:223-335`) et le rendu texte (`:338`). C'est précisément le mélange que le package s'interdit ailleurs : la docstring de `mcp_adapter/wire_mapping.py:3-6` explique que `wire.py` et `wire_mapping.py` ont été séparés parce qu'un module de 370 lignes mêlant contrat et traduction rendait les diffs illisibles.
- **Regle violee** : item 3.3.2 — « Un seul concept par fichier — pas de fichier fourre-tout » (poids 2).
- **Remediation** : inchangée depuis 0.7.0. Sortir la projection d'arbre (`services/tree_projection.py`) et le push (`ChunkStorePushService`, ou suppression avec l'ingestion en 0.8.0). Pour `sources_view.py`, aligner sur la convention du package : DTO dans `wire.py` (ou un `sources_wire.py`), mapping dans `wire_mapping.py`, enregistrement seul dans `sources_view.py`.

### [MIN] Glissement de convention : la moitié des nouvelles fonctions portent un nom de nom, pas de verbe (nouveau)

- **Localisation** : `document-parser/domain/source_map.py:236` (`_totals`), `:292` (`_hops`), `:347` (`_cost`), `:351` (`_stronger`) ; `document-parser/services/source_service.py:224` (`_marks`), `:234` (`_title`), `:258` (`_anchor`), `:282` (`_resolvable`) ; `document-parser/mcp_adapter/sources_view.py:278` (`_hop`), `:323` (`_node`), `:365` (`_said`) ; `document-parser/mcp_adapter/wire_mapping.py:57` (`search_result`), `:84` (`outline_result`), `:188` (`verification_result`) ; `document-parser/domain/quote_marks.py:79-132` (`_key`, `_haystack`, `_inside`, `_lines`) ; `document-parser/services/citation_image_service.py:133` (`_image`) ; JS `sources_app.html:483` (`head`), `:506` (`sources`), `:639` (`foot`), `:710` (`details`), `:758` (`coverage`), `:803` (`roundsTable`).
- **Constat** : dans les 26 modules ajoutés pour MCP/navigation, ~47 % des fonctions (≈ 93 sur ≈ 197, propriétés exclues) sont nommées d'après ce qu'elles renvoient. Le même comptage heuristique donne ~19 % dans le code antérieur, où l'audit 0.7.0 relevait des noms « systématiquement verbaux ». Le style est cohérent à l'intérieur du package, mais il s'écarte de la règle et a un coût concret : `_anchor(uri, unknown)` (`source_service.py:258-263`) et `_resolvable(...)` (`:282-293`) ont l'air de simples lectures alors qu'elles **ajoutent dans la liste `unknown` reçue en argument**. Rien dans le nom ne signale cette mutation.
- **Regle violee** : item 3.1.1 — « Les fonctions sont nommées avec des verbes d'action » (poids 1).
- **Remediation** : renommer au moins les fonctions à effet de bord (`_anchor` → `_parse_or_report`, `_resolvable` → `_partition_known`) et les mappers publics (`to_search_result`, `build_outline_result`…). Si l'équipe assume la convention « nom = valeur renvoyée » pour les fonctions pures, l'écrire dans la fiche 3.1.1 plutôt que de la laisser diverger silencieusement.

### [MIN] Fonctions au-delà de 30 lignes

- **Localisation** :
  - Python, préexistantes : `infra/neo4j/tree_writer.py:69` (227 l.), `infra/neo4j/queries.py:137` (115), `infra/neo4j/chunk_writer.py:55` (107), `services/chunk_service.py:574` (103), `infra/docling_agent_reasoning.py:149` (86), `services/chunk_service.py:451` (79), `infra/settings.py:196` (78, mapping d'env).
  - Python, nouvelles en 0.7.3 : `mcp_adapter/server.py:95` (`build_mcp_server`, 87), `mcp_adapter/apps.py:146` (`_register_citation_card`, 80), `domain/parse_index.py:80` (`build_index`, 79), `services/citation_service.py:94` (`verify_citation`, 62), `mcp_adapter/sources_view.py:223` (`sources_card`, 52), `infra/docling_pages.py:68` (48, code déplacé de `local_converter.py`), `domain/outline_builder.py:75` (43), `services/source_service.py:91` (`show`, 40), `mcp_adapter/sources_view.py:163` (38), `bootstrap/mcp_mount.py:84` (37), `services/navigation_service.py:124` (34), `domain/source_map.py:178` (33), `domain/source_map.py:292` (32). Total : 45 fonctions.
  - Front : `features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216 l. — vue graphe Neo4j, dépréciée), `features/document/ui/BboxCanvas.vue:62` (75), `features/analysis/ui/StructureViewer.vue:146` (66), `features/analysis/ui/BboxOverlay.vue:85` (61), `features/analysis/sectionParenting.ts:31` (58), `features/document/ui/PagePreviewWithOverlay.vue:331` (53) et `:425` (46), `features/document/ui/DownloadDropdown.vue:130` (49), `shared/ui/accordion.ts:58` (40, nouveau).
  - JS des cartes MCP : `citation_app.html:460` (`renderMarkdown`, 77), `:808` (`hydrateLocator`, 68), `:565` (`render`, 66) ; `sources_app.html:710` (`details`, 45), `:516` (`strip`, 38), `:803` (`roundsTable`, 37).
- **Constat** : le volume est stable par rapport à 0.7.0 (~48 → 45). Les nouveaux longs corps sont en partie de l'enregistrement d'outils FastMCP par fermetures décorées : `build_mcp_server`, `_register_citation_card` et `register_sources_view` contiennent des outils de 4 à 10 lignes, avec des descriptions et commentaires, ce qui se rapproche du « boilerplate inévitable ». `build_index`, `verify_citation`, `sources_card` et le JS de rendu (`renderMarkdown`, `hydrateLocator`) sont, eux, de vrais corps longs.
- **Regle violee** : item 3.2.2 — « Aucune fonction ne dépasse 30 lignes (hors boilerplate inévitable) » (poids 1).
- **Remediation** : traiter d'abord `build_index` (voir 3.2.1) et `renderMarkdown` (un rendu par type de bloc). Dans `build_mcp_server`, une fonction `_register_<tool>(server, tools)` par outil rendrait le builder déclaratif.

### [MIN] Fonctions à plus de 4 paramètres (aggravé : 20 → 29)

- **Localisation** : préexistantes `services/chunk_service.py:149` (12), `services/store_service.py:237` (10), `services/store_service.py:186` (9), `services/analysis_service.py:83` (**9**, était 8 : ajout de `docling_importer` pour #359), `services/store_backend_resolver.py:78` (8), `infra/neo4j/tree_writer.py:69` (7), `services/app_config_service.py:68` (7). Nouvelles : `mcp_adapter/server.py:95` (6), `mcp_adapter/server.py:168` (`read_element`, 6), `services/navigation_service.py:124` (6), `services/mcp_config_service.py:112` (6), `services/citation_image_service.py:133` (6) et `:81` (5), `services/source_service.py:76` (5), `services/config_overrides.py:79` (5), `domain/source_map.py:236` (5).
- **Constat** : 29 signatures dépassent 4 paramètres (hors `self`/`cls`), dont 9 dans des fichiers nouveaux. Atténuation réelle : la plupart sont en keyword-only. `read_element` côté outil MCP reflète le schéma publié à l'agent, ce qui est difficile à réduire. Côté front : aucune fonction au-delà de 4 paramètres.
- **Regle violee** : item 3.2.3 — « Aucune fonction n'a plus de 4 paramètres » (poids 1).
- **Remediation** : regrouper les options de lecture (`version_id`, `include`, `max_tokens`, `cursor`) dans un value object `ReadRequest` côté `NavigationService`. `_totals(outline, sections_total, hops, covered, index)` peut prendre un objet intermédiaire déjà construit par `_hops`. Pour les constructeurs, voir la remédiation 0.7.0 (objet de dépendances / builder).

### [MIN] Fichiers sources au-delà de 300 lignes (aggravé)

- **Localisation** : voir « Fichiers > 300 lignes » ci-dessus. Les plus marquants pour 0.7.3 : `document-parser/mcp_adapter/sources_app.html` (1 188) et `citation_app.html` (1 177), `frontend/src/features/mcp-config/ui/McpConfigSection.vue` (1 109), `document-parser/api/schemas.py` (849, +142), `frontend/src/pages/DocsLibraryPage.vue` (701, +176), `frontend/src/features/document/ui/PagePreviewWithOverlay.vue` (720, script seul 400 l.).
- **Constat** : 14 fichiers Python (8 en 0.7.0), 2 pages HTML de ~1 180 lignes et 26 fichiers front (24) dépassent le seuil. Comme en 0.7.0, plusieurs gros `.vue` le sont surtout par leur CSS (`StudioPage.vue` : 762 l. de style). En revanche, `McpConfigSection.vue` rend **trois** sections d'accordéon dans un même SFC (sa docstring le dit : serveur, budgets, environnement) avec 355 lignes de template. `GraphView.vue` (437), `PagePreviewWithOverlay.vue` (400) et `DocParseTab.vue` (318) dépassent 300 lignes **de script seul**.
- **Regle violee** : item 3.3.1 — « Aucun fichier source ne dépasse 300 lignes » (poids 1).
- **Remediation** : découper `McpConfigSection.vue` en `McpServerSection`, `McpBudgetsSection` et `McpEnvironmentSection` (le store est déjà commun). Dans les pages MCP, sortir le pont hôte (JSON-RPC/postMessage) partagé et le CSS commun. Garder `chunk_service.py` en tête (voir 3.3.2).

### [INFO] Constantes magiques dans le nouveau code, dont des doublons de constantes nommées

- **Localisation** : `document-parser/services/navigation_service.py:281` (`[:96]` alors que `_MAX_TITLE_LEN = 96` existe dans `domain/parse_index.py:29`) ; `document-parser/mcp_adapter/apps.py:206` et `document-parser/mcp_adapter/sources_view.py:205` (même borne `max(120, min(max_width, 1600))` répétée) ; `document-parser/services/navigation_service.py:109` (`min(depth, 6)`, à côté de `_MAP_DEPTH = 6` dans `services/source_service.py:48` et du « (1-6) » de `mcp_adapter/server.py:146`) ; `document-parser/domain/outline_builder.py:44` (`max_nodes=200`, doublon de `services/navigation_config.py:33`) ; `document-parser/services/citation_image_service.py:71` (`24`, `72.0`, aussi dans `domain/navigation.py:75`) ; `frontend/src/features/mcp-config/ui/McpConfigSection.vue:516` (`1500`) ; `timeoutMs = 8000` dans `citation_app.html:701` et `sources_app.html:1000`.
- **Constat** : la plupart des budgets sont bien nommés et documentés (`NavigationConfig`), mais quelques littéraux en double peuvent diverger d'une constante qui existe déjà.
- **Remediation** : réutiliser `_MAX_TITLE_LEN`, `NavigationConfig.max_outline_nodes`, et une constante `MAX_OUTLINE_DEPTH` / `IMAGE_WIDTH_BOUNDS` partagée par les deux outils d'image. Nommer `POINTS_PER_INCH = 72`.

### [INFO] Code mort préexistant (3.4.2 jugé conforme : l'item vise le code commenté)

- **Localisation** : `document-parser/domain/chunk_editing.py` (216 l., importé seulement par `tests/test_chunk_editing.py:7`, déjà relevé par l'audit 01 en 0.7.0) ; `document-parser/domain/lifecycle_aggregation.py:35` (`aggregate_lifecycle`, appelé seulement par les tests) ; `document-parser/services/analysis_service.py:113` / `:119` (`_chunk_promoter`, injecté par `bootstrap/builder.py:137` mais jamais lu), avec `services/chunk_service.py:205` (`promote_from_analysis_if_empty`, appelé seulement par les tests) ; front : `frontend/src/features/store/api.ts:84-129` (8 fonctions CRUD store appelées seulement par `api.test.ts`, périmètre ingestion déprécié), `frontend/src/features/chunks/api.ts:82` (`fetchChunkPushes`, 0 appelant), `frontend/src/shared/format.ts:26` (`formatAbsolute`, 0 appelant).
- **Constat** : tout ce code était déjà mort en 0.7.0 ; 0.7.3 n'en ajoute pas (le commit `dc54211` a même retiré des chemins morts du MCP). Aucun code commenté laissé en place, ni en Python, ni en TS/Vue, ni dans le JS des cartes.
- **Remediation** : supprimer avec le retrait de l'ingestion en 0.8.0 (`store/api.ts`, `fetchChunkPushes`, promoteur) ; supprimer `chunk_editing.py` ou le brancher (voir audit 01).

### [INFO] Commentaires périmés

- **Localisation** : `document-parser/services/analysis_service.py:108-112` (le promoteur « Wired in main.py » remplirait le chunkset « on the first successful analysis »), contredit par `:510-517` (« no longer invoked as part of the analysis flow ») ; le câblage est en réalité dans `bootstrap/builder.py:137`, pas `main.py`. `frontend/src/pages/StudioPage.vue:16`, `:287`, `:470`, `:479` (noms de modes en français « Configurer / Vérifier / PREPARER », commentaires datant de mars 2026).
- **Constat** : les commentaires restent majoritairement du « pourquoi » (3.4.1 conforme), mais ces blocs décrivent un état disparu.
- **Remediation** : supprimer le commentaire d'en-tête du promoteur et le « tombstone » `:510-517` en même temps que le code mort ci-dessus ; renommer les commentaires de modes en anglais.

### [INFO] Booléens de configuration en paramètre (3.2.4 jugé conforme)

- **Localisation** : `document-parser/mcp_adapter/server.py:81` (`instructions(apps=…)`), `:95` (`build_mcp_server(apps=…, citation_card=…)`), `document-parser/mcp_adapter/prompts.py:56` (`register_prompts(apps=…)`), `document-parser/mcp_adapter/apps.py:123` (`build_apps_extension(citation_card=…)`) ; préexistant `domain/ports.py:173` / `persistence/chunk_repo.py:117` (`include_deleted`).
- **Analyse** : ces booléens portent la configuration de déploiement (`MCP_APPS_ENABLED`, `MCP_CITATION_CARD`) jusqu'aux builders. La fonction construit la même chose, avec ou sans un composant optionnel ; elle ne fait pas deux choses distinctes selon le booléen. Même jugement que pour `include_deleted` en 0.7.0. À surveiller : le même drapeau `apps` est désormais testé dans trois fonctions.

### [INFO] Variables d'une lettre et abréviations (3.1.2 / 3.1.4 jugés conformes)

- **Localisation** : `document-parser/services/source_service.py:101` (`(a, w, f)` pour anchor/why/found), `:103` (`(a, q, st)`), `document-parser/mcp_adapter/sources_view.py:177` (`e`) ; JS `sources_app.html:343` (`fr`), `pct`, `px`, `num`, `esc` ; helpers 0.7.0 de `chunk_service.py:98/112/116/851` inchangés.
- **Analyse** : portées minuscules (compréhensions, helpers d'une ligne). `(a, w, f)` est néanmoins opaque sans relire la signature : `(anchor, why, found)` ne coûte rien.

### [INFO] `get_*` à mémoïsation (3.2.5 jugé conforme)

- **Localisation** : `document-parser/services/navigation_service.py:101` (`get_outline` → `ParseLoader.load` → cache LRU `services/parse_loader.py:99-111`) ; préexistants `infra/opensearch_pool.py:131`, `infra/neo4j/driver_pool.py:161`, `infra/secrets/fernet_box.py:114`.
- **Analyse** : effet de cache idempotent et borné (éviction LRU documentée, `parse_loader.py:123`), pas un effet de bord métier. Tous les autres `get_*` (routes, `get_citation`, `get_config`, `get_mcp_server`, `getMcpConfig`…) sont des lectures pures.

### [INFO] JS inline des cartes MCP : hors lint, pont hôte dupliqué

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:396-1175`, `document-parser/mcp_adapter/sources_app.html:319-1186` ; périmètre ESLint `frontend/eslint.config.js:10` (`src/**/*.{ts,js,vue}`) ; pont JSON-RPC/postMessage en double : `citation_app.html:690-800` contre `sources_app.html:984-1090`.
- **Constat** : ~1 650 lignes de JavaScript échappent à ESLint, Prettier et au typage. Les tests Python (`tests/test_mcp_apps.py`, `tests/test_mcp_sources_app.py`) les chargent, mais n'en vérifient pas la qualité. Les fonctions `post`, `call`, `settle`, `handshake`, `applyHostContext`, `applyContainerDimensions`, `reportSize`, `extract` et `showState` existent dans les deux pages avec de légères divergences. Imbrication maximale : 4 (`extract`, `citation_app.html:1105` et `sources_app.html:1125`).
- **Remediation** : renvoi aux audits 05 (DRY) et 10 (CI). Un module JS commun injecté à la construction de la ressource, plus un lint ESLint dédié, couvriraient les deux points.

### [INFO] Profondeur d'imbrication

- **Localisation** : `document-parser/infra/local_chunker.py:24` (`_chunk_sync`, 7 niveaux : `for chunk` › `if meta` › `for doc_item` › `for prov` › `if bbox` › `if page_obj` › `if bbox != EMPTY`, inchangé depuis 0.7.0) ; `frontend/src/features/document/ui/DownloadDropdown.vue:130` (4).
- **Constat** : le nouveau code est remarquablement plat (maximum 4, dans `infra/docling_pages.py:68`). Seul `_chunk_sync`, préexistant, mérite une extraction (`_collect_bboxes(doc_item, doc)`).

---

## Delta vs 0.7.0

**Score : 61 → 44 (−17).** Items conformes : 9/14 → 7/14. Les deux items perdus sont 3.1.3 (poids 2, cartes MCP en français) et 3.1.1 (poids 1, convention de nommage du nouveau code).

| Écart 0.7.0 | Statut 0.7.3 | Détail |
|-------------|--------------|--------|
| [MAJ] Orchestration multi-responsabilités (`chunk_service.py:574`, `tree_writer.py:69`, `queries.py:137`) | **Toujours présent** | Fichiers identiques à v0.7.0. Nouveaux cas : `parse_index.py:80`, `analysis_service.py:457` |
| [MAJ] Fichier fourre-tout `chunk_service.py` | **Toujours présent** | 1 019 l., inchangé. Nouveau cas mineur : `mcp_adapter/sources_view.py` |
| [MIN] Fonctions > 30 lignes | Toujours présent, stable | ~48 → 45 (13 nouvelles) |
| [MIN] Fonctions > 4 paramètres | **Aggravé** | 20 → 29 (9 nouvelles, `AnalysisService.__init__` 8 → 9) |
| [MIN] Fichiers > 300 lignes | **Aggravé** | Python 8 → 14 (+2 HTML ~1 180 l.), front 24 → 26 |
| [INFO] Getters à mémoïsation | Inchangé | + `get_outline` (cache LRU de parses) |
| [INFO] Flag `include_deleted` | Inchangé (ligne `ports.py:157` → `:173`) | + booléens de configuration MCP (`apps`, `citation_card`) |
| [INFO] Paramètres d'une lettre | Inchangé | + compréhensions `(a, w, f)` de `source_service.py:101` |
| [INFO] `conversion_timeout = 600` | Inchangé (`analysis_service.py:89`) | Intégré à l'INFO « constantes magiques » |

Nouveaux écarts 0.7.3 : [MAJ] 3.1.3 (cartes MCP en français), [MIN] 3.1.1 (nommage). Aucun écart de 0.7.0 n'est corrigé : la remédiation planifiée pour 0.7.x (découpage de `chunk_service.py`) n'a pas été faite.

---

## Points positifs

- **Adaptateur MCP mince et bien découpé** : chaque outil de `mcp_adapter/server.py` (`:134`, `:149`, `:168`, `:194`) fait 4 à 10 lignes, mapping plus traduction d'erreur, comme l'annonce la docstring (`server.py:5-7`). Le contrat publié (`wire.py`) est séparé de la traduction (`wire_mapping.py`).
- **Nouveau code plat et lisible** : imbrication maximale de 4 dans tout le code ajouté ; `services/source_service.py` (293 l.) reste sous le seuil avec des helpers courts ; `domain/` reste fait de fonctions pures et testables (`source_map`, `quote_marks`, `page_regions`, `spans`).
- **Langue côté application** : aucun texte français en Python ni dans les `.vue`/`.ts` hors `i18n.ts`. Tous les nouveaux composants (`McpConfigSection.vue`, `AnalysisImportButton.vue`, `DocumentActionsMenu.vue`, `AccordionSection.vue`) passent par `t()` (aucun texte de template en dur trouvé).
- **Imports** (3.3.3) : `ruff check` avec la configuration du projet (règle `I` active) : « All checks passed ». `mcp_adapter` a été ajouté à `known-first-party` (`pyproject.toml:99`).
- **Commentaires « pourquoi » exemplaires** : par exemple `bootstrap/mcp_mount.py:104-114` (coût du mode `stateless_http`), `mcp_adapter/apps.py:200-204` (pourquoi l'outil image est réservé à l'app), `services/parse_loader.py:123-128` (pourquoi la dernière entrée n'est jamais évincée).
- **Factorisation utile** : `infra/docling_pages.py` extrait de `local_converter.py` (−165 l.) le parcours des pages, partagé par le convertisseur local et l'import Docling (#359).
- **Budgets nommés** : `services/navigation_config.py` centralise les plafonds MCP (`max_read_tokens`, `index_cache_max_chars`, `image_page_max_bytes`…) avec leur justification.
- **Aucun code commenté** laissé en place, et des chemins morts du MCP retirés avant release (`dc54211`).

---

## Verdict partiel : NO-GO

Score **44/100** (< 60), **0 ecart CRITICAL**, **3 ecarts MAJOR** (au seuil, pas au-delà de 3).

Le NO-GO vient du barème. Une base déjà basse (61, deux MAJ non remédiés depuis 0.7.0) perd un item de poids 2 (3.1.3) et un item de poids 1 (3.1.1). Aucun écart ne présente de risque fonctionnel ou de sécurité. Pour revenir en GO CONDITIONNEL (≥ 60) :

1. **3.1.3** : passer les libellés des deux cartes MCP en anglais, avec une table de messages fr/en locale à chaque page et un `lang` correct. Effort faible, ~64 chaînes. Score atteint : 56.
2. **3.1.1** : renommer les fonctions à effet de bord et les mappers publics du package MCP, ou faire acter la convention « nom = valeur renvoyée » dans la fiche. Score atteint : 61.
3. Porter (de nouveau) en dette tracée les deux MAJ de 0.7.0. Le découpage de `chunk_service.py` adresse à lui seul 3.2.1, 3.2.2, 3.2.3, 3.3.1 et 3.3.2, et la partie push/ingestion disparaît naturellement avec le retrait d'OpenSearch/Neo4j en 0.8.0.

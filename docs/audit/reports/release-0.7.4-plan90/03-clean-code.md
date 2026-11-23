# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `513e8f9` (HEAD), seul `experiments/mcp-bench/` non suivi (hors périmètre)
**Nature** : contrôle après le « plan 90 », puis recontrôle après corrections. Premier passage sur `8dc0623` (78/100, voir « Premier passage sur 8dc0623 » et « Recontrôle sur 513e8f9 »). Base de comparaison : contrôle final sur `707a486` (`docs/audit/reports/release-0.7.4-final/03-clean-code.md`, 72/100). Diffs étudiés : `039778c..8dc0623` (12 commits, dont 7 `#audit-03`), puis `8dc0623..513e8f9` (3 commits : `c4fca8a`, `8e1560b`, `513e8f9`).

Suites lancées par le mainteneur sur `513e8f9` (non relancées ici) : ruff propre, pytest 1776 passés / 15 ignorés ; eslint, prettier, vue-tsc propres, vitest 580 passés, build OK ; document OpenAPI identique. Sur `8dc0623` : 1773 / 15 et 589 tests.

---

## Score de compliance (513e8f9)

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 94 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 8 |

**Calcul** : poids conformes = 17 (tous sauf 3.3.1) sur 18 → `17 / 18 × 100 = 94,4` → **94**. Premier passage sur `8dc0623` : 78 (14/18). Contrôle final `707a486` : 72.

**Verdict : GO.** Les sections « Checklist » à « Points non vérifiés » ci-dessous décrivent le premier passage sur `8dc0623` ; la section « Recontrôle sur 513e8f9 », en fin de rapport, donne l'état actuel item par item et prime sur elles.

---

## Premier passage sur 8dc0623

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 14 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 8 |

**Calcul** : poids conformes = 14 (3.1.1=1, 3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.2=1, 3.2.4=1, 3.2.5=2, 3.3.2=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18 → `14 / 18 × 100 = 77,8` → **78**. Précédent : 72.

### Méthode

- Analyse statique, aucun outil du projet lancé. Machine vérifiée calme (`calm.sh`, code 0), scripts lancés avec `nice -n 15`.
- Scripts de mesure de la consigne (`pyfuncs.py`, `tsfuncs.cjs`, `pyunused.py`, `unused_imports.py`, `ts_unused.cjs`, `pynames_all.py`, `tsnames_all.cjs`) lus puis lancés sans modification sur l'arbre à HEAD et sur un extrait `git archive 039778c` (point de départ du diff). Étalonnage : sur `039778c`, ils redonnent les chiffres du rapport précédent (145 `.py`, 164 `.vue`/`.ts`, 18 + 29 fichiers > 300, 45 + 20 fonctions > 30 lignes, 44 + 1 fonctions > 4 paramètres, 20 booléens).
- Nommage : différence des couples (fichier, fonction) `039778c` → HEAD : 125 noms Python et 41 noms TS nouveaux, 22 + 20 disparus. Tous lus. Les 19 dataclasses Python et 4 interfaces TS ajoutées lues une par une.
- Diff de production lu en entier (`git diff 039778c..HEAD`, 86 fichiers hors tests, +3 027 / −3 223).
- Code mort : `pyunused.py` sur tout le backend, `unused_imports.py` et `ts_unused.cjs` sur les fichiers changés, exports TS cherchés par `grep -w` hors tests, et recherche des symboles supprimés par `16144f4`, `0ac6ee2`, `92390c6`, `1ad4846`.

---

## Métriques (707a486 → 8dc0623)

`039778c` a les mêmes mesures que `707a486` (commits documentaires entre les deux).

| Mesure | Précédent `707a486` | HEAD `8dc0623` |
|--------|---------------------|----------------|
| Fichiers `.py` source | 145 (23 320 l.) | 144 (23 647 l.) |
| Fichiers `.vue`/`.ts` source | 164 (27 698 l.) | 162 (27 175 l.) |
| Fonctions Python / TS (comptées par script) | 979 / 1 042 | 1 082 / 1 057 |
| `.py` > 300 lignes | 18 | **19** |
| `.vue`/`.ts` > 300 lignes | 29 | 29 |
| Fonctions Python > 30 lignes | 45 | **0** |
| Fonctions TS/Vue > 30 lignes | 20 | **0** |
| Fonctions Python > 4 paramètres (mesure brute) | 44 | **15** |
| Fonctions TS > 4 paramètres | 1 | **0** |
| Fonctions > 4 paramètres, précision 3.2.3 appliquée | 31 | **2** |
| Paramètres booléens Python | 20 | 15 (5 déplacés dans des objets valeur, aucun ajouté) |
| Fonctions faisant plusieurs choses (3.2.1) | 2 (Neo4j) | 2 nouvelles, petites (Neo4j réglé) |
| Fichiers fourre-tout (3.3.2) | 0 | 0 |
| Fonctions nommées par leur résultat | 0 | 0 |
| Code commenté | 0 | 0 |

---

## Checklist

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | oui | Les 166 noms ajoutés commencent tous par un verbe (`_build_*`, `_read_*`, `_check_*`, `_apply_*`, `_link_*`, `_create_*`, `draw*`, `resolve*`, `apply*`…) ou par le préfixe de conversion `to_` déjà en usage (`to_command`, `_to_citation_view`, `_to_segment_out`, `_to_totals_out`). Les types ajoutés sont des noms. Quelques noms imprécis, voir INFO |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | `ns` supprimé (`config_overrides`), `stored`, `replacement`, `batching`, `scope`, `surface`, `source` sont explicites. Un tuple anonyme `upload` (INFO) |
| 3.1.3 | Code en anglais, i18n | 2 | oui | Aucun texte français ajouté. Résidu inchangé, déplacé : `infra/docling_projector.py:135` |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | Aucun nom abrégé ajouté |
| 3.2.1 | Une fonction = une chose | 2 | **non** | Neo4j réglé (`write_document` 29 l., `fetch_graph` 37 l. avec signature et docstring, une étape par fonction). Le découpage a créé deux fonctions qui cachent une écriture sous un nom qui en annonce une autre : `services/analysis_service.py:341` `_plan_batches`, `infra/neo4j/chunk_writer.py:85` `_clear_document_chunks` |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | oui | 0 Python, 0 TS (mesure de la fiche : corps hors docstring). La plus longue en lignes totales, signature et docstring comprises : `infra/docling_tree.py:152` (50, dont 22 de docstring) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | **non** | 15 signatures brutes ; 13 exemptées par la précision ; restent `services/analysis_service.py:102` `AnalysisService.__init__` (10) et `services/document_service.py:50` `DocumentService.__init__` (7), dont le corps calcule |
| 3.2.4 | Pas de flag arguments | 1 | oui | 20 → 15 booléens. Les 5 disparus sont rangés dans des objets valeur, avec la même nature qu'avant (valeurs ou configuration) ; aucun drapeau ajouté. Détail plus bas |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | Aucun `get_*` ajouté hors `_register_get_*` (enregistrement d'outils MCP) |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | **non** | 47 → 48 (19 Py + 29 front) |
| 3.3.2 | Un concept par fichier | 2 | oui | Objets valeur à côté de leur consommateur ; aucun fichier devenu fourre-tout (cas par cas plus bas) |
| 3.3.3 | Imports ordonnés | 1 | oui | ruff propre (règle I) d'après le mainteneur ; aucun import inutilisé par script dans les 59 fichiers Python et 25 fichiers TS changés |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | Aucun commentaire ne raconte le refactoring. Un commentaire rendu faux par le découpage (`bootstrap/builder.py:289`) et six commentaires périmés antérieurs, classés INFO comme dans les rapports précédents |
| 3.4.2 | Pas de code commenté | 1 | oui | 0 ; les 36 lignes que remonte la commande de la fiche sont de la prose |

---

## Ecarts constates

### [MAJ] 3.2.1 — Deux fonctions extraites qui cachent une écriture

Les deux fonctions Neo4j du rapport précédent sont réglées (voir Delta). L'écart ne porte plus sur elles, mais sur deux fonctions créées par le découpage.

- **Localisation 1** : `document-parser/services/analysis_service.py:341` `_plan_batches`.
- **Constat 1** : sa docstring dit elle-même deux choses : « Split the document into 1-based page ranges and reset the job's progress ». Elle calcule les plages de pages (calcul pur) et écrit la progression du job (`update_progress(job_id, 0, total_pages)`) puis journalise. Un nom en « plan » annonce un calcul, pas une écriture en base.
- **Localisation 2** : `document-parser/infra/neo4j/chunk_writer.py:85` `_clear_document_chunks`.
- **Constat 2** : la fonction crée le nœud `:Document` s'il manque (`MERGE`, `:90`) puis supprime les chunks (`:93-100`). Le nom annonce une suppression ; la création est l'effet inverse. Le `MERGE` est la précondition de toute l'écriture (`_create_chunk_nodes` et `_flag_chunks_stage` font `MATCH` sur ce nœud), pas une partie du nettoyage.
- **Cas voisin, non compté** : `services/analysis_service.py:529` `_update_document_after_analysis` reprend la fin de `_finalize_analysis` : nombre de pages, état du cycle de vie et écriture de l'arbre dans le graphe. La docstring l'annonce, mais l'écriture du graphe n'est pas une mise à jour du document. C'est la seule fonction du lot qui ressemble à un « reste » découpé pour passer sous 30 lignes.
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** (environ 20 min, sans risque) : remettre `update_progress(…, 0, …)` et le journal dans `_run_batched_conversion` et faire de `_plan_batches` un calcul pur (il peut alors devenir une fonction de module) ; sortir le `MERGE` dans `_ensure_document_node(tx, doc_id)` appelé par `write_chunks`. Score avec 3.2.1 conforme : **89**.

### [MIN] 3.2.3 — Deux constructeurs à plus de 4 paramètres qui font autre chose que recevoir

- **Localisation** : `document-parser/services/analysis_service.py:102` `AnalysisService.__init__` (10 paramètres), `document-parser/services/document_service.py:50` `DocumentService.__init__` (7).
- **Constat** : la précision du 3.2.3 n'exempte que les constructeurs qui ne font que recevoir leurs collaborateurs. `AnalysisService.__init__` reçoit deux valeurs scalaires de configuration (`conversion_timeout`, `max_concurrent`), construit un `asyncio.Semaphore` à partir de l'une et un `AnalysisConfig()` par défaut (`:121`, `:124`). `DocumentService.__init__` calcule une taille en octets à partir de la configuration (`:68-70`). Critère appliqué : un corps qui ne fait qu'affecter ce qu'il reçoit, plus un état privé vide (cache, dictionnaire de tâches), est exempté ; un corps qui calcule ne l'est pas.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** (environ 30 min) : déplacer `conversion_timeout` et `max_concurrent` dans `AnalysisConfig`, qui existe déjà pour cela (« Configuration values needed by AnalysisService, extracted from settings ») ; le constructeur passe à 8 collaborateurs et ne garde que l'initialisation du sémaphore depuis sa configuration. Ajouter `DocumentConfig.max_file_size_bytes` et supprimer le calcul de `DocumentService.__init__`. Score avec 3.2.3 conforme (et 3.2.1 toujours non conforme) : **83**.

### [MIN] 3.3.1 — Fichiers sources au-delà de 300 lignes (19 Python, 29 front)

- **Localisation** : entre `document-parser/domain/analysis_editing.py` (311, +`CommandActivation`). Grossissent : `bootstrap/builder.py` 324 → 421, `infra/neo4j/tree_writer.py` 310 → 380, `infra/settings.py` 301 → 340, `services/analysis_service.py` 615 → 640, `services/store_service.py` 389 → 413, `bootstrap/factories.py` 363 → 384, `domain/source_map.py` 355 → 368, `services/source_service.py` 320 → 327. Maigrissent : `domain/ports.py` 869 → 837, `infra/docling_editor.py` 393 → 339. Front : même liste de 29 fichiers ; plus gros `frontend/src/shared/i18n.ts` (1571), `frontend/src/pages/StudioPage.vue` (1444), `frontend/src/features/mcp-config/ui/McpConfigSection.vue` (1110).
- **Constat** : 47 → 48. Découper les fonctions ajoute des signatures, des docstrings et des lignes vides : +327 lignes Python au total.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4 (48 fichiers, dont `i18n.ts` qui ne se découpe pas sans changer l'organisation des traductions). Plus proches du seuil : `domain/analysis_editing.py` (311, sortir les erreurs et les `check_*` dans `domain/analysis_edit_rules.py`), `infra/docling_tree.py` (309), `frontend/src/features/chunks/ui/ChunksPanel.vue` (301), `frontend/src/shared/ui/AppSidebar.vue` (304).

### [INFO] Commentaires faux ou périmés (3.4.1)

- **Rendu faux par ce lot** : `document-parser/bootstrap/builder.py:289` « Doc-centric chunks (#256), their pushes to stores, and the tree. » est resté dans `_build_analysis_services`, alors que les pushes sont construits dans `_build_store_services` (`:378`) et l'arbre dans `_build_structure_services` (`:408`).
- **Faux, antérieur, déplacé dans une fonction de ce lot** : `document-parser/services/analysis_service.py:537-544` dit que « the promoter hook stays wired in main.py so legacy callers / tests can still trigger it ». Le hook (`_chunk_promoter` / `set_chunk_promoter`) a été supprimé au cycle précédent ; le commentaire raconte aussi l'historique (« was previously called here »).
- **Antérieurs, non relevés par les rapports précédents** : « main.py » désigne le câblage, qui est dans `bootstrap/` : `services/analysis_service.py:130-132`, `services/store_backend_resolver.py:95`, `services/app_config_service.py:9`, `services/reasoning_service.py:12`. `infra/neo4j/tree_writer.py:49` renvoie à `_iter_provs`, qui n'existe pas (la fonction est `iter_provs` dans `infra/docling_tree.py`). `frontend/src/features/analysis/ui/GraphView.vue:97` dit `parentMap` mis à jour « at the end of `renderGraph` » ; il l'est au début (`:361`, fonction à `:350`).
- **Analyse** : même classement que les rapports précédents (INFO). Aucun commentaire ne raconte le refactoring de ce lot ; aucun commentaire n'a été perdu en route (les commentaires « pourquoi » ont suivi le code déplacé).
- **Remediation** : 15 min. Supprimer la phrase de `builder.py:289` (ou la réduire à « Doc-centric chunks (#256). »), supprimer le paragraphe `analysis_service.py:537-544`, remplacer « main.py » par « bootstrap » dans les quatre services, corriger `_iter_provs` et `GraphView.vue:97`.

### [INFO] Noms imprécis parmi les fonctions ajoutées (3.1.1 / 3.1.2)

Tous ont un verbe ; ils ne décrivent pas exactement ce que fait la fonction.
- `document-parser/infra/body_limit.py:85` `_refuse` construit la réponse sans l'envoyer (`_build_refusal`).
- `document-parser/infra/serve_converter.py:178` `_wait_for_serve_startup` attend un délai de reprise, il ne surveille pas le démarrage (`_sleep_before_retry`).
- `document-parser/infra/settings.py:193` `_check_modes` vérifie aussi `reasoning_max_iterations` ; les groupes de `__post_init__` (`_check_timeouts_and_concurrency`, `_check_size_and_rate_limits`, `_check_embedding_and_mcp`) suivent la taille plus que le sens.
- `document-parser/infra/neo4j/queries.py:163` `_check_document_exists` renvoie un booléen ; ailleurs dans le lot, `_check_*` lève une erreur (`_document_exists`).
- `frontend/src/features/analysis/sectionParenting.ts` `ReadingOrder` porte aussi `kindById` et `explicitParentOf`.

### [INFO] Paramètres regroupés sans nom (3.1.2)

- `document-parser/infra/serve_converter.py:143` `upload: tuple[str, bytes, str]` remplace trois paramètres nommés par un tuple positionnel ; la docstring doit en donner l'ordre. Le nombre de paramètres baisse, la lisibilité aussi. Un `NamedTuple` ou trois paramètres (4 au total) suffiraient.
- `document-parser/services/chunk_service.py:225` construit `ChunkReplacement` avec cinq arguments positionnels, dont deux qui répètent `chunk_source` (`document_id`, `analysis_id`).

### [INFO] Constructeurs à plus de 7 collaborateurs (précision 3.2.3, renvoi audit 06)

`AnalysisService.__init__` (10), `StoreBackendResolver.__init__` (8, dont 4 valeurs `env_*` qui formeraient un objet valeur), `AnalysisEditService.__init__` (8).

### [INFO] Code mort front antérieur, nouveau relevé

- `frontend/src/features/chunks/api.ts:82` `fetchChunkPushes` et `frontend/src/shared/format.ts` `formatAbsolute` : aucun appelant, pas même un test.
- `frontend/src/features/analysis/api.ts:46` `fetchAnalyses` et `frontend/src/features/analysis/legendFilters.ts` `partitionByHiddenChips` : tests seulement.
- Présents à `039778c`, non touchés par le lot, non relevés par le rapport précédent. Renvoi audit 04.

### [INFO] Fonctions qui mêlent un refus et un nettoyage

`document-parser/services/document_service.py:121` `_check_page_count` supprime le fichier déjà écrit avant de lever l'erreur ; `document-parser/services/store_service.py:267` `_insert_store` insère et retire le défaut aux autres stores. Une transaction ou un invariant chacune, docstring ou nom explicite : pas compté en 3.2.1, comme `analysis_repo.delete` au rapport précédent.

### [INFO] Résidus reconduits

- 3.1.3 : `document-parser/infra/docling_projector.py:135` (message utilisateur hors i18n).
- 3.2.4 : flag HTTP `edited` (`document-parser/api/documents.py:119`), jugé à la frontière comme avant ; booléens de configuration `apps` / `citation_card` (`mcp_adapter/server.py:82`, `mcp_adapter/apps.py:123`, `mcp_adapter/prompts.py:56`).
- Docstrings longues (E501 ignoré) : `services/parse_loader.py:6`, `infra/docling_editor.py`, `infra/body_limit.py`.

---

## Delta vs contrôle final 707a486

**Score : 72 → 78 (+6).** Items conformes : 10/14 → 11/14. Gagné : 3.2.2. Changé de cause : 3.2.1 (Neo4j réglé, deux nouvelles fonctions). Restent non conformes : 3.2.3 (31 → 2 avec la précision), 3.3.1 (47 → 48). Verdict : GO CONDITIONNEL → **GO CONDITIONNEL**.

| Item | 707a486 | 8dc0623 | Ce qui a changé et pourquoi |
|------|---------|---------|-----------------------------|
| 3.1.1 | oui | oui | 166 noms ajoutés, tous avec un verbe |
| 3.1.2 | oui | oui | `workspaceLatestAnalysis` supprimé avec le chemin workspace (`1ad4846`) |
| 3.2.1 | non (Neo4j) | non (2 nouvelles) | `79463bb` découpe les trois fonctions Neo4j ; `ccfa928` et `b1d6495` créent `_plan_batches` et `_clear_document_chunks` |
| 3.2.2 | non (65) | **oui (0)** | `79463bb`, `b1d6495`, `ccfa928`, `bf1f3de`, `78ab470` |
| 3.2.3 | non (45 brut) | non (15 brut, 2 après précision) | `52610cf`, `8dc0623` (objets valeur), `e4a73b3` (précision), suppressions `16144f4` / `92390c6` / `0ac6ee2` |
| 3.2.4 | oui (20) | oui (15) | 5 booléens rangés dans des objets valeur, même nature |
| 3.3.1 | non (47) | non (48) | `domain/analysis_editing.py` passe à 311 |
| 3.3.2 | oui | oui | Aucun fourre-tout |
| 3.4.1 | oui | oui | 1 commentaire rendu faux (INFO) ; 6 périmés antérieurs relevés |

### 3.2.1 — Les fonctions Neo4j sont-elles réglées ?

Oui. Lecture complète des trois fichiers à HEAD :

| Fonction | Avant | Après |
|----------|-------|-------|
| `infra/neo4j/tree_writer.py` `write_document` | 227 l., 7 paramètres | `:352`, 29 l. : charge le JSON, horodate, projette (`_build_tree_projection`), écrit dans une transaction (`_write_tree`), journalise, renvoie le résultat. `_write_tree` (`:334`) enchaîne neuf étapes Cypher nommées, une requête chacune (`_wipe_document_graph`, `_create_document_node`, `_create_page_nodes`, `_create_element_nodes`, `_link_parents`, `_link_roots`, `_create_provenance_nodes`, `_link_provenances_to_pages`, `_link_reading_order`) |
| `infra/neo4j/queries.py` `fetch_graph` | 115 l. | `:252`, 37 l. : trois lectures (`_read_page_count`, `_check_document_exists`, la requête du graphe) puis l'assemblage (`_build_graph_nodes`, `_build_graph_edges`). La table `_EDGE_KINDS` remplace six boucles copiées |
| `infra/neo4j/chunk_writer.py` `write_chunks` | > 30 l. | 33 l. avec docstring : une étape par fonction, sauf `_clear_document_chunks` (écart ci-dessus) |

`_write_tree` et `write_document` enchaînent sans rien calculer ; c'est leur rôle (une transaction, un ordre d'écriture). Ce ne sont pas des fourre-tout : chaque appel est une étape du même cas d'usage. Les tests du module tournent sur des faux pilotes (`_FakeNeo`, `_FakeTx`…, ajoutés par `79463bb`) ; aucun serveur Neo4j n'a été utilisé.

### 3.2.1 — Le découpage a-t-il créé des fonctions multi-responsabilités ?

Sur les 125 fonctions Python et 41 fonctions TS ajoutées, lues une à une : deux cachent une écriture (écart MAJ), une regroupe une fin de séquence (`_update_document_after_analysis`, cité dans l'écart). Les autres extraient une étape nommée : construction d'objets (`_build_*`, `_to_*`), lecture (`_read_*`, `_load_*`), garde (`_check_*`, `_require_*`, `_validate_*`), écriture unique (`_create_*`, `_link_*`, `_insert_store`). Côté front, les extractions sont des étapes de dessin (`prepareCanvas`, `drawElementBoxes`, `drawChunkBoxes`), des liaisons d'événements (`bindSelectionHandlers`, `bindTooltipHandlers`) et des actions de store (`applyPolledAnalysis`, `abandonPolling`, `recordEditFailure`, `resetPendingEdits`), chacune avec une seule responsabilité.

### 3.1.x — Types ajoutés

| Type | Fichier | Lecture |
|------|---------|---------|
| `StoreDraft`, `StoreChanges` | `services/store_service.py:78`, `:93` | Noms justes (création / modification partielle) |
| `ChunkReplacement`, `AnalysisOutput` | `domain/models.py:374`, `:185` | Justes ; `ChunkReplacement` répète deux champs de `chunk_source` (INFO) |
| `AnalysisRun`, `PageBatching` | `services/analysis_service.py:72`, `:83` | Justes |
| `IngestionSource` | `services/ingestion_service.py:42` | Juste |
| `McpSurface` | `mcp_adapter/server.py:96` | Juste (ce que le serveur expose) |
| `ReadScope` | `services/navigation_service.py:52` | Juste |
| `GraphDocument`, `_DocumentNode`, `_TreeProjection` | `infra/neo4j/tree_writer.py:72`, `:84`, `:92` | Justes |
| `Repositories` | `bootstrap/factories.py:237` | Juste |
| `NamespaceOverrides` | `services/config_overrides.py:83` | Juste ; la fonction libre `pick` devient la méthode `pick`, ce qui supprime le paramètre `namespace` |
| `CommandActivation` | `domain/analysis_editing.py:39` | Juste ; `to_command` construit la commande |
| `_AnalysisServices`, `_FileServices`, `_StoreServices`, `_StructureServices` | `bootstrap/builder.py:271`, `:339`, `:371`, `:401` | Justes, privés au module |
| `PreviewViewState`, `SchedulerState`, `ReadingOrder`, `PdfLoaderState` (TS) | `PagePreviewWithOverlay.logic.ts`, `previewScheduler.ts`, `sectionParenting.ts`, `usePdfDocument.ts` | Justes, sauf `ReadingOrder` qui contient plus que l'ordre (INFO) |

### 3.2.3 — Ce que change la précision de `e4a73b3`

À HEAD, 15 signatures dépassent 4 paramètres (mesure brute, comparable aux 45 du rapport précédent). La précision en exempte **13** :

- **4 signatures imposées par un framework**, toutes vérifiées : routes FastAPI `api/documents.py:119` `export_document` (6), `api/documents.py:163` `preview` (5), `api/analysis_edits.py:148` `set_edit_active` (5) ; outil MCP `mcp_adapter/server.py:191` `read_element` (6, chaque paramètre est un argument de l'outil).
- **9 constructeurs qui ne font qu'affecter leurs collaborateurs** : `StoreBackendResolver` (8), `AnalysisEditService` (8), `ChunkPushService` (7), `AppConfigService` (7), `VersionService` (6), `McpConfigService` (6), `SourceService` (5), `PreviewService` (5), `ParseLoader` (5). `AnalysisEditService` et `ParseLoader` initialisent en plus un cache privé vide : accepté comme état interne.
- **2 non exemptés** : `AnalysisService.__init__` et `DocumentService.__init__` (écart MIN).

Appliquée à `039778c`, la précision aurait exempté 14 des 45 signatures (les mêmes 4 de framework et 10 constructeurs ; `AnalysisService`, `DocumentService` et `OpenSearchStore.__init__`, qui construisait un client, ne l'étaient pas) : 31 signatures comptées. Le lot en a donc retiré 29 par le code, et la précision n'a pas suffi seule à rendre l'item conforme.

Les 29 retirées : `update_store` → `StoreChanges` ; `create_store` → `StoreDraft` ; `write_document` → `GraphDocument` ; `NavigationService.read_element` → `ReadScope` ; `_replace`, `replace_and_select` et `replace_keeping_selection` (dépôt et port, 5 signatures) → `ChunkReplacement` ; `build_mcp_server` → `McpSurface` ; `ingest`, `_build_indexed_chunks` → `IngestionSource` ; `pick` → `NamespaceOverrides` ; `_run_analysis`, `_run_analysis_inner` → `AnalysisRun` ; `_run_batched_conversion` → `PageBatching` ; `set_command_active` → `CommandActivation` ; `mark_completed` → `AnalysisOutput` ; `build_document_service` → `Repositories` ; `isPageInRenderWindow` → `PreviewViewState` ; `_post_convert_with_startup_retry` → tuple `upload` (INFO) ; `_build_image` intégré ; `_render_page_thumbnail` (le nombre de pages est posé après coup par `replace`) ; `_compute_totals` (le total est recalculé dedans) ; `body_limit._answer` → `_refuse` ; `OpenSearchStore.__init__`, `OpenSearchClientPool.get` et `VectorStorePool.get` (suppression de `default_limit`, `92390c6`) ; `DoclingAnalysisProjector.project` (suppression de `reference_changes` / `warnings`, `0ac6ee2`). `ChunkService.__init__` passe aussi de 5 à 4 (suppression de `analysis_state_repo`, `16144f4`).

### 3.2.4 — Booléens déplacés dans des objets valeur

| Booléen | Avant | Après | Nature |
|---------|-------|-------|--------|
| `apps`, `citation_card` | paramètres de `build_mcp_server` | champs de `McpSurface` (`mcp_adapter/server.py:101-102`) | configuration (`MCP_APPS_ENABLED`, `MCP_CITATION_CARD`), déjà acceptée ainsi ; ils restent des paramètres de `build_instructions`, `register_prompts`, `build_apps_extension` |
| `active` | paramètre de `set_command_active` | champ de `CommandActivation` (`domain/analysis_editing.py:43`) | valeur écrite dans la commande (`setCommandActive`), pas un aiguillage |
| `is_default` (×2) | paramètres de `create_store` / `update_store` | champs de `StoreDraft` / `StoreChanges` | valeur du store |

Aucun booléen ajouté ni caché : les cinq ont la même nature qu'avant, que le rapport précédent avait jugée conforme. `PreviewViewState.currentPageSettled` (TS) est un fait passé à un calcul, pas un drapeau.

### 3.3.2 — Objets valeur et fichiers

| Fichier | Lignes 707a486 → HEAD | Lecture | Statut |
|---------|------------------------|---------|--------|
| `bootstrap/builder.py` | 324 → 421 | La racine de composition : `AppStateBuilder`, puis les étapes de construction et quatre dataclasses privées qui groupent leurs résultats. Un concept | Pas d'écart |
| `bootstrap/factories.py` | 363 → 384 | Fabriques ; reçoit `Repositories`, consommé surtout par `builder.py`. À sa place dans `bootstrap/` | Pas d'écart |
| `infra/settings.py` | 301 → 340 | `Settings`, ses contrôles, sa lecture de l'environnement par groupe. Un concept | Pas d'écart |
| `domain/models.py` | 452 → 445 | Reçoit `AnalysisOutput` (sortie d'une conversion) et `ChunkReplacement` (argument du port `ChunkRepository`) ; perd `resolve_selection_after_rechunk` et `mark_stale` | Pas d'écart |
| `services/analysis_service.py` | 615 → 640 | `AnalysisRun`, `PageBatching` à côté de `AnalysisConfig`, au service de la même classe | Pas d'écart |
| `services/store_service.py` | 389 → 413 | `StoreDraft` / `StoreChanges` à côté des vues `StoreInfoView` ; l'API les importe du service comme elle importait déjà les vues | Pas d'écart |
| `infra/neo4j/tree_writer.py` | 310 → 380 | Écriture de l'arbre, et ses objets | Pas d'écart |

### Code mort lié aux suppressions

- `pyunused.py` à HEAD : **aucun** symbole Python sans second usage (à `039778c` : `mark_stale`, `DocumentMerger`, `DoclingDocumentMerger`, `health_check`). Les autres restes du rapport précédent sont partis : `get_chunks` (port, OpenSearch), `INSTRUCTIONS`, les deux `_neutralise_all`.
- Aucune trace des symboles supprimés par `16144f4`, `0ac6ee2`, `92390c6`, `1ad4846` dans le code de production (recherche de `parse_allowed_host_name`, `is_host_check_on`, `_match_host`, `resolve_selection_after_rechunk`, `reference_changes`, `beforeElementId`, `default_limit`, `rebuildAnalysisEdits`, `loadWorkspace`, `HistoryDrawer`, `StaleStoresStrip`, `workspaceLatestAnalysis`…).
- Les 166 fonctions ajoutées ont toutes au moins un appelant.
- Aucun import inutilisé dans les fichiers changés (scripts Python et TS).
- Front : les quatre restes du rapport précédent sont supprimés. Quatre exports morts antérieurs relevés (INFO).

---

## Points positifs

- **Plus aucune fonction au-delà de 30 lignes**, back et front (65 → 0), sans comprimer le code : les étapes extraites ont des noms d'action et souvent une docstring d'une ligne.
- **Les deux fonctions Neo4j** sont devenues des séquences d'étapes Cypher nommées, et le module a des tests sur faux pilotes.
- **Objets valeur bien nommés et bien placés** : 19 types, chacun à côté de son consommateur ; `NamespaceOverrides.pick` et `CommandActivation.to_command` portent leur comportement.
- **Suppressions propres** : aucun reste des symboles retirés, plus de code mort Python.
- **Commentaires « pourquoi » conservés** pendant les déplacements ; aucun commentaire ne raconte le refactoring.

---

## Points non vérifiés

- Équivalence de comportement des refactorings : non vérifiée ici (aucun test lancé) ; je m'appuie sur les suites du mainteneur et l'OpenAPI inchangé. En particulier, `rechunk_document` ne lit plus l'état de sélection et passe toujours l'analyse découpée à `replace_keeping_selection` (`services/chunk_service.py:225`) ; d'après le contrat du port (`domain/ports.py`), seule une ligne d'état créée par l'écriture l'adopte, donc le résultat est le même, mais je ne l'ai pas exécuté.
- Écriture Neo4j réelle : non testée contre un serveur.
- Variables locales : relues dans le diff, pas dans tout le périmètre.
- Exports TS morts : recherche par nom (`grep -w`), qui ne voit pas les usages par chaîne dynamique.
- Templates Vue : non mesurés (la fiche ne compte que les fonctions et les fichiers).

---

### Verdict du premier passage (8dc0623) : GO CONDITIONNEL

Score **78/100**, 0 CRITICAL, 1 MAJOR (3.2.1), 2 MINOR, 8 INFO. Conditions posées : rendre `_plan_batches` pur et sortir le `MERGE` de `_clear_document_chunks` (→ 89) ; déplacer `conversion_timeout` / `max_concurrent` dans `AnalysisConfig` et le calcul de taille dans `DocumentConfig` (→ 94 avec la première) ; corriger les sept commentaires faux ou périmés.

---

## Recontrôle sur 513e8f9

Diff lu : `git diff 8dc0623..513e8f9`, hors `docs/audit/reports/` (58 fichiers, +298 / −655 ; production : 26 fichiers backend, 9 fichiers frontend). Scripts relancés sans modification (machine calme, `nice -n 15`).

### Métriques (8dc0623 → 513e8f9)

| Mesure | `8dc0623` | `513e8f9` |
|--------|-----------|-----------|
| Fichiers `.py` source | 144 (23 647 l.) | 144 (23 612 l.) |
| Fichiers `.vue`/`.ts` source | 162 (27 175 l.) | 162 (26 896 l.) |
| `.py` > 300 lignes | 19 | 19 |
| `.vue`/`.ts` > 300 lignes | 29 | **28** |
| Fonctions Python / TS > 30 lignes | 0 / 0 | 0 / 0 |
| Fonctions > 4 paramètres, brut | 15 + 0 | 15 + 0 |
| Fonctions > 4 paramètres, précision 3.2.3 appliquée | 2 | **0** |
| Paramètres booléens Python | 15 | 15 (mêmes) |
| Symboles Python sans second usage (`pyunused.py`) | 0 | 0 |
| Imports inutilisés dans les fichiers changés | 0 | 0 |

### Items, de 8dc0623 à 513e8f9

| # | Item | Poids | 8dc0623 | 513e8f9 | Ce qui a changé et pourquoi |
|---|------|-------|---------|---------|-----------------------------|
| 3.1.1 | Verbes | 1 | oui | oui | Noms ajoutés : `_ensure_document_node`, `_plan_batches` (fonction de module), `DocumentConfig.max_file_size_bytes` (propriété, nom de valeur), méthodes de `PreviewScheduler` (`debounce`, `clearDebounce`, `begin`, `isCurrent`, `abort`, `cancel`, reprises de l'interface). Tous justes |
| 3.1.2 | Intention | 1 | oui | oui | `batch_label` sert désormais aux deux journaux ; `_DocumentNode.title` dit ce qu'il porte. Les noms imprécis relevés en INFO sont inchangés |
| 3.1.3 | Anglais / i18n | 2 | oui | oui | 8 clés i18n retirées avec le mode édition ; résidu `infra/docling_projector.py:135` inchangé |
| 3.1.4 | Abréviations | 1 | oui | oui | Rien d'ajouté |
| 3.2.1 | Une fonction = une chose | 2 | **non** | **oui** | Les deux écarts sont levés, vérifiés dans le code (détail ci-dessous). Aucune fonction multi-responsabilités ajoutée |
| 3.2.2 | ≤ 30 lignes | 1 | oui | oui | 0 / 0. `_run_batched_conversion` (`services/analysis_service.py:308`), qui reprend la remise à zéro et le journal, reste sous le seuil |
| 3.2.3 | ≤ 4 paramètres | 1 | **non** | **oui** | Les 15 signatures restantes sont toutes exemptées (détail ci-dessous) |
| 3.2.4 | Pas de flag | 1 | oui | oui | Même liste de 15 booléens. Champs ajoutés à `AnalysisConfig` : deux entiers. Aucun drapeau ajouté ni déplacé |
| 3.2.5 | `get_*` sans effet | 2 | oui | oui | Aucun `get_*` ajouté |
| 3.3.1 | ≤ 300 lignes | 1 | non (48) | **non (47)** | Sort `frontend/src/features/document/ui/ElementProperties.vue` (456 → 299, mode édition supprimé). `domain/analysis_editing.py` passe de 311 à 312 (commentaire ajouté sur `EditStream.engine_version`). `services/analysis_service.py` 640 → 622, `domain/ports.py` 837 → 841, `infra/neo4j/tree_writer.py` 380 → 377 |
| 3.3.2 | Un concept par fichier | 2 | oui | oui | `IngestionSource` passe dans `domain/value_objects.py` (bon endroit : objet valeur du domaine, consommé par trois couches), mais sous le mauvais intertitre (INFO). `GraphDocument` supprimé, `_DocumentNode` absorbe ses champs utiles |
| 3.3.3 | Imports ordonnés | 1 | oui | oui | ruff propre ; aucun import inutilisé (scripts) |
| 3.4.1 | Commentaires « pourquoi » | 1 | oui | oui | Les sept commentaires faux ou périmés relevés sont corrigés (vérifiés un par un) ; deux nouveaux commentaires « pourquoi » justes ; un intertitre devenu trompeur (INFO) |
| 3.4.2 | Pas de code commenté | 1 | oui | oui | Rien d'ajouté |

### 3.2.1 — Vérification des deux écarts

- **`_plan_batches`** (`document-parser/services/analysis_service.py:101`) : fonction de module, sans `self`, sans `await`, sans journal ; elle ne fait que calculer les plages (`math.ceil`, compréhensions). La remise à zéro de la progression et le journal sont revenus dans `_run_batched_conversion` (`:322-329`), qui orchestre le traitement par lots. Levé.
- **`_clear_document_chunks`** (`document-parser/infra/neo4j/chunk_writer.py`) : ne contient plus que les deux suppressions ; le `MERGE` est dans `_ensure_document_node`, appelé par `write_chunks` juste avant. Le commentaire « pourquoi » du `MERGE` a suivi. Levé.
- **Changements KISS relus sous l'angle 3.2.1** :
  - `SqliteAnalysisEditRepository.save_commands_and_cache` (`document-parser/persistence/analysis_edit_repo.py`) écrit aussi `engine_version` sur le flux, dans la même transaction. La docstring du port (`domain/ports.py`, `AnalysisEditRepository.save_commands_and_cache`) le dit, et c'est l'invariant du cache (une copie de travail n'est valable que pour le moteur qui l'a projetée). Même classement que `_insert_store` : INFO, pas un écart.
  - `write_document` (`infra/neo4j/tree_writer.py`) reprend trois paramètres nommés en mot-clé (4 au total, sous le seuil) à la place de `GraphDocument` ; `_create_document_node` écrit des valeurs neutres pour `source_uri`, `docling_version`, `tenant_id`, avec un commentaire qui dit pourquoi.
  - `PreviewScheduler` devient une classe de six méthodes courtes, chacune avec une seule action.
  - `_update_document_after_analysis` (`services/analysis_service.py:517`) est inchangée ; elle reste en INFO.

### 3.2.3 — Chaque signature encore comptée

15 signatures brutes, toutes exemptées :

- **4 signatures imposées par un framework**, inchangées : `api/documents.py:119` `export_document`, `api/documents.py:163` `preview`, `api/analysis_edits.py:148` `set_edit_active` (routes FastAPI), `mcp_adapter/server.py:191` `read_element` (outil MCP).
- **11 constructeurs**, corps relus un par un :
  - `DocumentService.__init__` (`services/document_service.py:55`, 7) : n'affecte plus que ses sept paramètres ; le calcul en octets est la propriété `DocumentConfig.max_file_size_bytes`. Exempté.
  - `AnalysisService.__init__` (`services/analysis_service.py:111`, 8, était 10) : `conversion_timeout` et `max_concurrent` sont dans `AnalysisConfig`, le défaut `config or AnalysisConfig()` est devenu une valeur par défaut de paramètre (la classe est désormais `frozen`). Le corps affecte ses paramètres, initialise un état privé vide (`_running_tasks`, `_background_tasks`, `_version_recorder`) et construit `asyncio.Semaphore(config.max_concurrent)`. Jugement : le sémaphore est l'état privé de la limite de concurrence, construit tel quel depuis la configuration reçue, sans calcul ; il est traité comme le cache vide de `ParseLoader`. C'est la remédiation proposée au premier passage. Exempté. Reste une copie redondante, `self._conversion_timeout = config.conversion_timeout` (`:127`), alors que `self._config` est aussi gardé (INFO).
  - Inchangés et toujours exemptés : `StoreBackendResolver` (8), `AnalysisEditService` (8), `ChunkPushService` (7), `AppConfigService` (7), `VersionService` (6), `McpConfigService` (6), `SourceService` (5), `PreviewService` (5), `ParseLoader` (5). Seuls des commentaires ont changé dans `StoreBackendResolver`.
- `[INFO]` constructeurs à plus de 7 collaborateurs (renvoi audit 06) : `AnalysisService` (8), `StoreBackendResolver` (8), `AnalysisEditService` (8).

### 3.4.1 — Commentaires

Les sept commentaires relevés au premier passage sont corrigés :
- `bootstrap/builder.py:289` (« Doc-centric chunks (#256). ») ;
- `services/analysis_service.py:525-526` : paragraphe du « promoter hook » réduit à la règle actuelle ;
- `services/analysis_service.py:137-138`, `services/store_backend_resolver.py:95`, `services/app_config_service.py:9`, `services/reasoning_service.py:12` : « main.py » remplacé par « the bootstrap » ou « at boot » ;
- `infra/neo4j/tree_writer.py:49` (`iter_provs`) ;
- `frontend/src/features/analysis/ui/GraphView.vue:97`, qui dit maintenant que `renderGraph` remplit la carte avant de dessiner, ce qui est vrai (`:361`).

Ajouts justes : `domain/analysis_editing.py:74` (moteur estampillé à chaque sauvegarde), `infra/neo4j/tree_writer.py:155-156` (pourquoi les valeurs neutres), `services/analysis_edit_service.py:89-91`.

Nouveau `[INFO]` : `IngestionSource` a été inséré dans `document-parser/domain/value_objects.py:154`, sous l'intertitre « # --- Reasoning (live docling-agent runner) --- » (`:150`), entre `ChunkResult` et `ReasoningIteration`. L'intertitre classe désormais à tort cet objet parmi ceux du raisonnement. Remédiation : 1 min, déplacer la classe au-dessus de l'intertitre, après `ChunkResult`.

Reste antérieur, non relevé jusqu'ici : `services/analysis_service.py:132-133` raconte l'historique (« was a raw `Neo4jDriver` until the hex-arch fix ») (INFO).

### Code mort après ces commits

- Les quatre exports morts relevés sont supprimés avec leurs tests : `fetchAnalyses`, `partitionByHiddenChips`, `fetchChunkPushes`, `formatAbsolute`. Leurs mocks ont été retirés de `store.test.ts`, `pipelineOptions.test.ts` et `history-navigation.test.ts`.
- Suppressions KISS propres dans le périmètre :
  - `replace_cache` (port et dépôt), la façade `mcp_adapter.build_mcp_server` et `GraphDocument` n'ont plus aucune référence dans `document-parser/` ;
  - le mode édition d'`ElementProperties.vue` part avec son CSS (aucune classe orpheline dans le fichier) et ses 8 clés i18n ;
  - la fonction retirée de `features/document/store.ts` n'a plus d'appelant (vue-tsc propre d'après le mainteneur).
- `pyunused.py` : 0 ; `unused_imports.py` et `ts_unused.cjs` sur les fichiers changés : 0.
- `[INFO]` hors périmètre (ni `document-parser/` ni `frontend/src/`) : `docs/demo/video/mcp-card/record.py:31` importe encore `from mcp_adapter import build_mcp_server`, façade supprimée par `8e1560b`. Le script était déjà cassé avant ce commit : il appelle `build_document_tools` avec deux dépôts et `build_mcp_server(…, version=, apps=)`, deux signatures qui n'existent plus depuis le lot précédent. À supprimer ou réécrire (audit 11).

### Écart restant

**[MIN] 3.3.1 — 47 fichiers au-delà de 300 lignes (19 Python, 28 front).**
- Le plus proche du seuil est `document-parser/domain/analysis_editing.py` (312) : sortir les erreurs et les `check_*` dans un module de règles.
- Viennent ensuite `infra/docling_tree.py` (309), `frontend/src/features/chunks/ui/ChunksPanel.vue` (301) et `frontend/src/shared/ui/AppSidebar.vue` (304).
- Hors d'atteinte pour 0.7.4 dans son ensemble (`i18n.ts` 1 571 l., `StudioPage.vue` 1 444 l.).

### INFO conservés depuis le premier passage

- Noms imprécis : `_refuse`, `_wait_for_serve_startup`, `_check_modes`, `_check_document_exists`, `ReadingOrder`.
- Tuple `upload` (`infra/serve_converter.py:143`) et `ChunkReplacement` construit par position (`services/chunk_service.py:225`).
- `_update_document_after_analysis`.
- Refus avec nettoyage (`_check_page_count`, `_insert_store`).
- Résidus 3.1.3 et 3.2.4.

### Points non vérifiés (recontrôle)

- Comportement : aucun test lancé ; je m'appuie sur les suites du mainteneur.
  - Changement de comportement voulu : la sauvegarde estampille désormais `engine_version` sur le flux. Lu, non exécuté.
  - Le défaut `AnalysisConfig()` est désormais une instance partagée entre appels ; elle est `frozen`, donc sans risque d'état partagé. Lu, non exécuté.
- Écriture Neo4j réelle : non testée contre un serveur.
- Clés i18n retirées : je n'ai pas cherché d'usage dynamique par chaîne construite.

### Verdict : GO

Score **94/100** (≥ 80), 0 CRITICAL, 0 MAJOR, 1 MINOR (3.3.1, hors d'atteinte pour 0.7.4), 8 INFO. Non bloquant : remettre `IngestionSource` sous le bon intertitre (1 min), supprimer ou réécrire `docs/demo/video/mcp-card/record.py`.

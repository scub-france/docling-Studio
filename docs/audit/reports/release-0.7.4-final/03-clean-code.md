# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `707a486`, arbre de travail propre (seuls `docs/audit/reports/release-0.7.4-final/` et `experiments/mcp-bench/` non suivis, hors périmètre)
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (72). Un premier passage de ce contrôle sur `a744f48` donnait 61 (voir « Contrôle à a744f48 »).

Suites lancées par le mainteneur sur `707a486` (non relancées ici) : ruff propre, pytest 1789 passés / 15 ignorés ; frontend inchangé depuis le dernier passage vert (eslint, prettier, vue-tsc propres, vitest 604 tests dans 71 fichiers, build OK).

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

**Calcul** : poids conformes = 13 (3.1.1=1, 3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.2=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18 → `13 / 18 × 100 = 72,2` → **72**. Validation : 72. Passage à `a744f48` : 61.

### Méthode

- Analyse statique. Aucun outil du projet lancé.
- Scripts de la validation (`validation03/scripts/` : `pyfuncs.py`, `tsfuncs.cjs`, `pynames_all.py`, `tsnames_all.cjs`, `unused_imports.py`, `ts_unused.cjs`) relancés **sans modification et avec les mêmes seuils**, sur l'arbre de travail à `707a486`. Étalonnage : sur `efc0bc5` (extrait par `git archive`), ils redonnent exactement les chiffres de la validation (146 `.py` / 23 415 l., 171 `.vue`/`.ts` / 29 472 l., 18 + 31 fichiers > 300, 44 + 21 fonctions > 30 lignes, 41 + 1 fonctions > 4 paramètres, 20 booléens).
- Nommage (3.1.1) : différence des couples (fichier, fonction) `efc0bc5` → `a744f48` (28 nouveaux noms Python, 0 TS), puis `a744f48` → `707a486` (16 nouveaux, 9 disparus), tous lus.
- Code mort : `final03/scripts/pyunused.py` (définitions Python qui n'apparaissent qu'une fois hors tests), exports TS cherchés par `rg -w` fichier par fichier, composants `.vue` sans importeur ; chaque cas relu.

---

## Métriques (validation → a744f48 → 707a486)

| Mesure | Validation `efc0bc5` | `a744f48` | Final `707a486` |
|--------|----------------------|-----------|-----------------|
| Fichiers `.py` source | 146 (23 415 l.) | 145 (23 137 l.) | 145 (23 319 l.) |
| Fichiers `.vue`/`.ts` source | 171 (29 472 l.) | 164 (27 691 l.) | 164 (27 698 l.) |
| `.py` > 300 lignes | 18 | 18 | 18 |
| `.vue`/`.ts` > 300 lignes | 31 | 29 | 29 |
| Fonctions Python > 30 lignes | 44 | 45 | 45 |
| Fonctions TS/Vue > 30 lignes | 21 | 20 | 20 |
| Fonctions Python > 4 paramètres | 41 | 40 | **44** |
| Fonctions TS > 4 paramètres | 1 | 1 | 1 |
| Paramètres booléens Python | 20 | 23 (2 vrais flags) | **20** (aucun flag ajouté) |
| Fonctions faisant plusieurs choses (3.2.1) | 2 | 2 | 2 |
| Fichiers fourre-tout (3.3.2) | 0 | 0 | 0 |
| Fonctions nommées par leur résultat | 0 | 2 | **0** |
| Code commenté | 0 | 0 | 0 |

### Ce qui entre et sort de chaque liste (validation → 707a486)

- **Fichiers > 300, Python (18 → 18)** : sortent `services/chunk_service.py` (426 → 292) et `services/citation_service.py` (307 → 246) ; entrent `services/source_service.py` (300 → 320) et `infra/settings.py` (300 → 301). Variations : `domain/models.py` 436 → 415 → 452 (trois règles de sélection ajoutées par `062bf70`), `domain/ports.py` 826 → 846 → 869, `api/schemas.py` 1092 → 1079 → 1090 (classes de payload réécrites à la main), `domain/navigation.py` 385 → 429 → 385 (`pick_within_budget` reparti dans `domain/element_reader.py`, 286 l.).
- **Fichiers > 300, front (31 → 29)** : sortent `features/analysis/ui/StructureViewer.vue` (465) et `pages/IngestLaunchDialog.vue` (399), supprimés par `60234e4`.
- **Fonctions > 30 lignes, Python (44 → 45)** : entre `infra/body_limit.py:35` `__call__` (34). S'allongent `services/chunk_service.py:181` `rechunk_document` 71 → 66 → **75** (lecture de l'état et traduction de l'erreur de sélection), `services/version_service.py:157` `restore` 36 → 40 → **43**, `bootstrap/builder.py` `build` 116 → 117, `persistence/analysis_edit_repo.py:137` `save_commands_and_cache` 53 → 56, `services/citation_service.py:94` `verify_citation` 62 → 64, `services/export_service.py:83` `_export` 32 → 35, `services/source_service.py:91` `show` 40 → 41.
- **Fonctions > 30 lignes, TS (21 → 20)** : sort `StructureViewer.vue` `drawOverlay` (80, fichier supprimé) ; `previewScheduler.ts:23` `createPreviewScheduler` 35 → 38.
- **Paramètres, Python (41 → 40 → 44)** : sortent `ChunkService.__init__` (13 → 5), `domain/chunk_editing.py` `insert` (6, supprimé), `DocumentTreeService.__init__` et `ExportService.__init__` (5 → 4). Entrent, à `a744f48`, `infra/body_limit.py:72` `_answer` (5) et `replace_for_document` (6, port et dépôt) ; à `707a486`, `replace_for_document` est remplacé par `replace_and_select` et `replace_keeping_selection` (5 chacun, dans `domain/ports.py` et `persistence/chunk_repo.py`) plus `persistence/chunk_repo.py` `_replace` (6), et `services/chunk_service.py` `__init__` repasse à 5 (`analysis_state_repo`). Le retrait du flag coûte donc +4 signatures à 3.2.3.
- **Booléens (20 → 23 → 20)** : `keep_selection` (port et dépôt) et `port_wildcard` ont disparu ; la liste est revenue aux 20 booléens de la validation, tous des valeurs, de la configuration ou des faits passés par mot-clé, plus le flag HTTP `edited` déjà accepté.

---

## Checklist

| # | Item | Poids | Conforme | Validation → `a744f48` → `707a486` |
|---|------|-------|----------|-------------------------------------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | oui | 0 → 2 → **0**. `_ancestors` → `_iter_ancestors` (`infra/docling_editor.py:364`), `_version_analysis_gone` → `_build_version_analysis_gone_error` (`services/version_service.py:76`). Les 16 noms ajoutés par `062bf70` / `707a486` commencent tous par un verbe : `resolve_selection_after_deleting` / `_restore` / `_rechunk`, `replace_and_select`, `replace_keeping_selection`, `_replace`, `parse_allowed_host_name`, `_match_host`, `split_allowed_hosts`, `log_host_check`, `_load_exported_analysis`, `pick_within_budget` |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | `_resolve_default_analysis`, `select_after_deleting` et les messages de `api/deps.py` corrigés ; reste `workspaceLatestAnalysis` (code mort, INFO) |
| 3.1.3 | Code en anglais, i18n | 2 | oui | résidu `infra/docling_projector.py:147` inchangé |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | aucun nouveau nom abrégé |
| 3.2.1 | Une fonction = une chose | 2 | **non** | 2 → 2 → 2 (les deux fonctions Neo4j, non touchées). Aucune nouvelle fonction multi-responsabilités |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | non | 65 → 65 → **65** (45 Py + 20 TS) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | non | 42 → 41 → **45** (44 Py + 1 TS) |
| 3.2.4 | Pas de flag arguments | 1 | oui | 20 → 23 → **20** booléens ; les deux flags remplacés par des méthodes nommées. `_replace(..., write_state_selection=…)` reçoit une fonction d'écriture, pas un booléen : c'est une stratégie, pas un flag |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | nouveaux `get_*` de `api/deps.py` : simples lectures de l'état |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | non | 49 → 47 → **47** (18 Py + 29 front) |
| 3.3.2 | Un concept par fichier | 2 | oui | 0 → 0 → 0 (cas par cas dans le Delta) |
| 3.3.3 | Imports ordonnés | 1 | oui | ruff propre d'après le mainteneur ; aucun import inutilisé trouvé par script dans les fichiers changés |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | trois commentaires périmés de la validation levés ; les deux rendus faux par `da6603d` corrigés par `ef37b6f` |
| 3.4.2 | Pas de code commenté | 1 | oui | 0 → 0 → 0 |

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration multi-responsabilités (2 fonctions Neo4j, inchangé)

- **Localisation** : `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l., 7 paramètres), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.).
- **Constat** : non touchées. Même lecture qu'à la validation : la dépréciation du module (CHANGELOG) ne les sort pas du périmètre tant qu'aucune décision écrite ne le dit.
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** : deux voies. (a) Une décision écrite qui sort `infra/neo4j/` du périmètre de l'audit, puisque le module part en 0.8.0 : l'item devient conforme, score **83** (GO). (b) Découper : `write_document` en `_write_document_node` / `_write_pages` / `_write_items` / `_write_relations`, `fetch_graph` en une requête par type de nœud plus un assemblage. Sans serveur Neo4j pour les tests, (a) est la voie sûre.

### [MIN] Fonctions au-delà de 30 lignes (45 Python, 20 TS)

- **Localisation** : pires, inchangés : `document-parser/infra/neo4j/tree_writer.py:69` (227), `frontend/src/features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216), `document-parser/bootstrap/builder.py` (`build`, 117), `document-parser/infra/neo4j/queries.py:137` (115). Nouveau depuis la validation : `document-parser/infra/body_limit.py:35` (`__call__`, 34). S'allongent : `document-parser/services/chunk_service.py:181` (`rechunk_document`, 75), `document-parser/services/version_service.py:157` (`restore`, 43).
- **Constat** : 65 → 65 → 65.
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4. Sous le seuil sans effort : `body_limit.__call__` (sortir `_check_declared_length`), `restore` (sortir la conversion du snapshot, la boucle `:177-180`), `rechunk_document` (sortir la construction des `Chunk` et l'écriture de la version d'historique).

### [MIN] Fonctions à plus de 4 paramètres (44 Python, 1 TS)

- **Localisation** : en tête, `document-parser/services/store_service.py:231` (`update_store`, 10), `document-parser/services/analysis_service.py:83` (`__init__`, 10), `document-parser/services/store_service.py:180` (`create_store`, 9). Nouveaux : `document-parser/persistence/chunk_repo.py` `_replace` (6), `replace_and_select` et `replace_keeping_selection` (5, dans `document-parser/domain/ports.py` et `document-parser/persistence/chunk_repo.py`), `document-parser/services/chunk_service.py` `__init__` (5), `document-parser/infra/body_limit.py:72` `_answer` (5). TS : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14` (6).
- **Constat** : 42 → 41 → 45. Le retrait de `keep_selection` a dédoublé une signature à 6 paramètres en deux méthodes publiques à 5 plus une privée à 6, dans le port et dans le dépôt : +4. Bon échange pour la lisibilité (3.2.4 regagné), mais il se voit ici.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : un objet valeur `ChunkReplacement(document_id, chunks, at, chunk_source, active_analysis_id)` ramènerait les cinq signatures à 1 ou 2 paramètres ; objet de paramètres pour `isPageInRenderWindow`. Le reste vient de l'injection de dépendances, hors d'atteinte pour 0.7.4.

### [MIN] Fichiers sources au-delà de 300 lignes (18 Python, 29 front)

- **Localisation** : nouveaux depuis la validation : `document-parser/services/source_service.py` (320), `document-parser/infra/settings.py` (301). Plus gros : `frontend/src/shared/i18n.ts` (1599), `frontend/src/pages/StudioPage.vue` (1444), `frontend/src/features/mcp-config/ui/McpConfigSection.vue` (1110), `document-parser/api/schemas.py` (1090), `document-parser/domain/ports.py` (869).
- **Constat** : 49 → 47 → 47.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : `infra/settings.py` passe sous le seuil en retirant une ligne. Le reste est hors d'atteinte pour 0.7.4.

### [INFO] Code mort front (inchangé depuis a744f48)

- **Localisation** :
  - `frontend/src/features/document/ui/HistoryDrawer.vue` (263 l.) : aucun importeur.
  - Chemin « workspace » de `frontend/src/features/document/store.ts` : `loadWorkspace` (`:155`) n'est appelé que par les branches `else` inatteignables de `frontend/src/pages/DocParseTab.vue:374-379` et `:417` (le seul montage, `frontend/src/pages/AnalysisDetailPage.vue:55-60`, passe toujours `:analysis`) ; `refreshWorkspace` (`:185`), `reloadWorkspaceVersions` (`:196`), `setWorkspaceVersion` (`:221`) sans appelant ; `workspaceCurrentVersion` (`:67`) et `workspaceLatestAnalysis` (`:73`, alias de `workspaceActiveAnalysis` au nom trompeur) sans lecteur.
  - `frontend/src/features/analysis-editor/api.ts:71` `rebuildAnalysisEdits` : aucun appelant, pas même un test.
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue` (143 l.) : aucun importeur. Préexistant, non relevé à la validation.
- **Analyse** : pas du code commenté, donc pas 3.4.2 ; même classement qu'à la validation (INFO, renvoi audits 04 et 05). Aucun effet sur les mesures de cet audit.
- **Remediation** : trancher « code mort ou fonctionnalité perdue » (question de l'audit 04). Si c'est du code mort : supprimer ces deux composants, le chemin workspace, les deux branches de `DocParseTab.vue`, `rebuildAnalysisEdits` et leurs tests.

### [INFO] Code mort back restant

- `document-parser/infra/serve_converter.py:189` (`health_check`, tests seulement), `document-parser/domain/models.py:351` (`mark_stale`, aucun appelant), `document-parser/domain/ports.py:102` (`DocumentMerger`) et `document-parser/infra/docling_merger.py:12` (tests seulement), `get_chunks` (`domain/ports.py`, `infra/opensearch_store.py`, tests seulement), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `_neutralise_all` en double (`document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`).
- Levés pendant ce cycle : `_chunk_promoter` / `set_chunk_promoter`, `domain/hashing.py` (et la paire `hash_chunkset` / `_compute_chunkset_hash`), `domain/lifecycle_aggregation.py`, l'import `void`-é de `UNKNOWN_ELEMENT_COLOR` dans `BboxCanvas.vue`, la règle `.merge-button` d'`AnalysisEditor.vue`.

### [INFO] Lignes de docstring trop longues

- `document-parser/services/parse_loader.py:6` (125 caractères), `document-parser/infra/docling_editor.py:355` (107), `document-parser/infra/body_limit.py:24` (107). E501 est ignoré et le formateur ne coupe pas les docstrings.

### [INFO] Fonctions plus lourdes sans être multi-responsabilités

- `document-parser/services/chunk_service.py:181` `rechunk_document` (75 l.) : garde, lecture de l'analyse courante, chunking, construction des `Chunk`, lecture de l'état, écriture, traduction de l'erreur, journal, version d'historique. Un cas d'usage, mais la plus longue fonction de service hors Neo4j et `builder.build`.
- `document-parser/services/version_service.py` `restore` (43 l.) : la règle est désormais dans le domaine (`resolve_selection_after_restore`, `document-parser/domain/models.py:164`), ce qui est mieux ; la fonction a pris 3 lignes pour lire l'état et le repli.
- `document-parser/persistence/analysis_repo.py:206` `delete` : SQL brut et appels de plus haut niveau dans la même fonction ; une transaction pour un seul invariant, donc pas 3.2.1.

### [INFO] Résidus reconduits

- 3.1.3 : `document-parser/infra/docling_projector.py:147`.
- 3.2.4 : flag HTTP `edited` (`document-parser/api/documents.py:119`), jugé à la frontière comme avant.
- Paire incohérente `getNodeColor` / `getKindColor` (`frontend/src/features/analysis/ui/GraphView.vue`, `NodeDetailsPanel.vue`, `frontend/src/features/reasoning/kindColors.ts`) : renvoi audit 05.

### [INFO] Constructeurs qui s'élargissent

- `ChunkService.__init__` est passé de 13 à 4 avec le retrait de la façade, puis à 5 avec `analysis_state_repo` (`062bf70`). Pas une régression de fond ; à suivre avec les autres constructeurs (3.2.3).

---

## Contrôle à a744f48

Un premier passage de ce contrôle, sur `a744f48` (2026-11-19), donnait **61/100** (9/14), 0 CRIT, 1 MAJ, 5 MIN, 8 INFO, GO CONDITIONNEL. Mêmes mesures de taille qu'aujourd'hui à 4 signatures près (3.2.3 : 41). Deux items étaient perdus, tous deux par des écarts introduits pendant le cycle :

- **3.1.1** : deux fonctions nommées par leur résultat, `infra/docling_editor.py:364` `_ancestors` et `services/version_service.py:75` `_version_analysis_gone`.
- **3.2.4** : deux vrais flags, `keep_selection` (`domain/ports.py:303`, `persistence/chunk_repo.py:140`, qui choisissait entre `adopt_selection` et `write_selection`) et `port_wildcard` (`infra/host_guard.py:37`).

Ce passage relevait aussi : deux commentaires rendus faux dans le chemin workspace (`store.ts:148-149`, `DocParseTab.vue:446`), des noms trompeurs (`_resolve_default_analysis`, `select_after_deleting`, messages 503 de `api/deps.py:43`, `:92`, `:99` qui nommaient un autre service), et des modèles de payload générés par introspection de types dans `api/schemas.py` (`_strip_bounds`, `_stored_payload_model`), illisibles en une minute. Pendant ce premier passage, l'arbre de travail a bougé ; les mesures avaient été faites sur un extrait `git archive` de `a744f48`.

Ce qui s'est passé depuis :

| Commit | Effet sur cet audit |
|--------|---------------------|
| `ef37b6f` | Les deux commentaires faux du front corrigés (`store.ts:148-149`, `DocParseTab.vue:446-447`) |
| `062bf70` | Sept classes de payload écrites à la main (`api/schemas.py:320-370`) et un test qui compare leurs champs à ceux des requêtes ; règles de sélection après restauration et rechunk dans le domaine (`domain/models.py:164`, `:184`) ; `pick_within_budget` déplacé dans `domain/element_reader.py:59` |
| `707a486` | `_iter_ancestors`, `_build_version_analysis_gone_error` (3.1.1 regagné) ; `replace_and_select` / `replace_keeping_selection` sur un `_replace` qui reçoit la fonction d'écriture, `parse_host_name` / `parse_allowed_host_name` (3.2.4 regagné) ; `resolve_selection_after_*`, `_load_exported_analysis` ; messages de `api/deps.py:43`, `:92`, `:99` qui nomment leur service |

Les deux items sont regagnés, les noms trompeurs signalés sont corrigés (sauf `workspaceLatestAnalysis`, dans le code mort), et les modèles de payload redeviennent lisibles d'un coup d'œil, avec un test qui garde l'unicité des champs. Le prix : +4 signatures à plus de 4 paramètres (3.2.3, déjà non conforme).

---

## Delta vs validation efc0bc5

**Score : 72 → 61 (a744f48) → 72 (707a486), soit ±0 sur le cycle.** Items conformes : 10/14 → 9/14 → 10/14. Aucun item gagné ni perdu au bilan. Verdict : GO CONDITIONNEL → **GO CONDITIONNEL**.

| Écart de la validation | Statut final | Mesures validation → a744f48 → 707a486 |
|------------------------|--------------|----------------------------------------|
| [MAJ] 3.2.1 Orchestration multi-responsabilités | Inchangé (Neo4j, ouvert) | 2 → 2 → 2 |
| [MIN] 3.2.2 Fonctions > 30 lignes | Stable | 65 → 65 → 65 |
| [MIN] 3.2.3 Fonctions > 4 paramètres | Aggravé | 42 → 41 → 45 |
| [MIN] 3.3.1 Fichiers > 300 lignes | Réduit | 49 → 47 → 47 |
| [INFO] Code mort (pages mortes, restes back) | Largement levé (8 fichiers front, restes back) ; reste le chemin workspace, `HistoryDrawer.vue`, `rebuildAnalysisEdits`, `StaleStoresStrip.vue` (nouveau relevé, préexistant) | |
| [INFO] Commentaires périmés | Levés (les trois de la validation, puis les deux du cycle) | |
| [INFO] Constructeurs qui s'élargissent | `ChunkService` 13 → 5 | |
| 3.1.1 (perdu à a744f48) | Regagné | 0 → 2 → 0 |
| 3.2.4 (perdu à a744f48) | Regagné | 0 → 2 → 0 flags |

### 3.2.1, cas par cas (le cycle crée-t-il une fonction multi-responsabilités ?)

| Fonction | Lecture | Statut |
|----------|---------|--------|
| `persistence/analysis_repo.py:206` `delete` (supprimer et resélectionner) | Une transaction, un invariant ; la règle vient du domaine (`DocumentAnalysisState.resolve_selection_after_deleting`, `domain/models.py:129`). Niveaux mêlés (INFO) | Pas d'écart |
| `services/version_service.py` `restore` (43 l.) | Le cas d'usage « restaurer une version » ; la règle est désormais dans le domaine | Pas d'écart (3.2.2) |
| `services/chunk_service.py:181` `rechunk_document` (75 l.) | Un cas d'usage, long (INFO) | Pas d'écart (3.2.2) |
| `persistence/chunk_repo.py` `_replace` | Une écriture transactionnelle ; la sélection est une fonction passée par l'appelant, pas un aiguillage interne | Pas d'écart |
| Routes de `api/document_chunks.py` sur trois services | Chaque route dépend d'un seul service | Pas d'écart |
| `tree_writer.py:69` `write_document`, `queries.py:137` `fetch_graph` | Non touchées | Ouvert (MAJ) |

### 3.3.2, cas par cas (nouveau fichier fourre-tout ?)

| Fichier | Lignes validation → a744f48 → 707a486 | Lecture | Statut |
|---------|----------------------------------------|---------|--------|
| `domain/models.py` | 436 → 415 → 452 | Entités et règles du domaine ; les trois `resolve_selection_after_*` sont des règles de l'agrégat d'état, à leur place à côté de `resolve_current_analysis_id` | Pas d'écart |
| `domain/ports.py` | 826 → 846 → 869 | Uniquement des protocoles | Pas d'écart |
| `api/schemas.py` | 1092 → 1079 → 1090 | Les DTO HTTP ; la mécanique d'introspection de `a744f48` a disparu | Pas d'écart |
| `services/chunk_push_service.py` | 365 → 362 → 362 | Diff, push et historique des push : un concept | Pas d'écart |
| `domain/quote_location.py` (nouveau) | — → 97 → 97 | Localiser une citation ; fonctions pures | Pas d'écart |
| `domain/element_reader.py` | → 286 | Lecture d'éléments d'un index ; reçoit `pick_within_budget`, ce qui supprime l'import local qui contournait un cycle | Pas d'écart |
| `infra/host_guard.py` | 113 → 89 → 130 | Contrôle du `Host` et son journal de démarrage | Pas d'écart |

---

## Points positifs

- **Les deux items perdus à `a744f48` sont regagnés en un commit**, par des noms justes et deux méthodes nommées, sans nouveau booléen : `_replace` reçoit l'écriture à faire, ce qui garde une seule transaction sans aiguillage.
- **Les noms trompeurs signalés sont corrigés** (`_load_exported_analysis`, `resolve_selection_after_*`, messages 503 de `api/deps.py`), et les règles de sélection après suppression, restauration et rechunk sont toutes dans le domaine, côte à côte.
- **Payloads lisibles à nouveau** : sept classes explicites, et un test qui garde l'unicité des champs que la génération voulait garantir.
- **Beaucoup de code en moins sur le cycle** : −96 lignes Python et −1 774 lignes front depuis la validation, 8 composants morts supprimés, la façade `ChunkService` retirée, deux fichiers backend passés sous 300 lignes, tous les commentaires périmés relevés corrigés.
- **Aucun import inutilisé, aucun code commenté** dans les fichiers changés.

---

## Verdict partiel : GO CONDITIONNEL

Score **72/100** (60-79), **0 CRITICAL**, **1 MAJOR** (3.2.1 : 2 fonctions Neo4j, ≤ 3 donc non bloquant), 3 MINOR, 7 INFO.

Conditions :

1. Pour le MAJ, acter par écrit que `infra/neo4j/` sort du périmètre de l'audit (module retiré en 0.8.0) : 3.2.1 conforme, score **83** (GO).
2. Non bloquant : supprimer le code mort front (chemin workspace, `HistoryDrawer.vue`, `StaleStoresStrip.vue`, `rebuildAnalysisEdits`) une fois tranchée la question « code mort ou fonctionnalité perdue ». Les trois MIN restants (3.2.2, 3.2.3, 3.3.1) sont hors d'atteinte pour 0.7.4.

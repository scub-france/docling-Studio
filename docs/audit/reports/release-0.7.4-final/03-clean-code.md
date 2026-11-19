# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `a744f48`
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (score 72)

Suites lancées par le mainteneur sur `a744f48` (non relancées ici) : ruff propre, pytest 1773 passés / 15 ignorés ; eslint, prettier, vue-tsc propres, vitest 604 tests dans 71 fichiers, build OK.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 14 |
| Score | 61 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 5 |
| Ecarts INFO | 8 |

**Calcul** : poids conformes = 11 (3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.5=2, 3.3.2=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18 → `11 / 18 × 100 = 61,1` → **61**. Validation : 72.

Les deux items perdus (3.1.1 et 3.2.4) le sont pour des écarts introduits par ce cycle, de petite taille, et qui se corrigent en moins d'une heure (voir Remédiation). Les mesures de taille, elles, ne bougent presque pas.

### Méthode

- Analyse statique. Aucun outil du projet lancé.
- **L'arbre de travail a bougé pendant l'audit** : le commit `ef37b6f` est arrivé sur la branche et une vingtaine de fichiers ont été modifiés sans commit (dont `api/schemas.py`, `domain/models.py`, `services/chunk_service.py`, `services/version_service.py`). Pour mesurer ce qui est demandé, j'ai extrait `a744f48` par `git archive` dans un dossier temporaire et j'ai tout mesuré et relu sur cet extrait. Les premières mesures, prises sur l'arbre de travail avant qu'il bouge, donnent exactement les mêmes chiffres. Ce qui est arrivé après `a744f48` n'est pas audité (une ligne en INFO).
- Scripts de la validation (`validation03/scripts/` : `pyfuncs.py`, `tsfuncs.cjs`, `pynames_all.py`, `tsnames_all.cjs`, `unused_imports.py`, `ts_unused.cjs`) relancés **sans modification et avec les mêmes seuils**. Étalonnage : sur `efc0bc5` (extrait par `git archive`), ils redonnent les chiffres exacts de la validation (146 `.py` / 23 415 l., 171 `.vue`/`.ts` / 29 472 l., 18 + 31 fichiers > 300, 44 + 21 fonctions > 30 lignes, 41 + 1 fonctions > 4 paramètres, 20 booléens).
- Nommage (3.1.1) : différence des couples (fichier, fonction) entre `efc0bc5` et `a744f48` : 28 nouveaux noms Python, 0 en TS, tous lus.
- Code mort : un petit script de plus (`final03/scripts/pyunused.py`, les définitions Python qui n'apparaissent qu'une fois dans le code hors tests), les exports TS cherchés par `rg -w` fichier par fichier, les composants `.vue` sans importeur. Chaque cas relu à la main.

---

## Métriques (validation → final)

| Mesure | Validation `efc0bc5` | Final `a744f48` |
|--------|----------------------|-----------------|
| Fichiers `.py` source | 146 (23 415 l.) | 145 (23 137 l.) |
| Fichiers `.vue`/`.ts` source | 171 (29 472 l.) | 164 (27 691 l.) |
| `.py` > 300 lignes | 18 | 18 |
| `.vue`/`.ts` > 300 lignes | 31 | **29** |
| Fonctions Python > 30 lignes | 44 | 45 |
| Fonctions TS/Vue > 30 lignes | 21 | **20** |
| Fonctions Python > 4 paramètres | 41 | **40** |
| Fonctions TS > 4 paramètres | 1 | 1 |
| Paramètres booléens Python | 20 | 23 (**2 vrais flags ajoutés**) |
| Fonctions faisant plusieurs choses (3.2.1) | 2 | 2 |
| Fichiers fourre-tout (3.3.2) | 0 | 0 |
| Fonctions nommées par leur résultat | 0 | **2** |
| Code commenté | 0 | 0 |

### Ce qui entre et sort de chaque liste

- **Fichiers > 300, Python (18 → 18)** : sortent `services/chunk_service.py` (426 → 282, façade retirée) et `services/citation_service.py` (307 → 246) ; entrent `services/source_service.py` (300 → 320, `_find_current_parses`) et `infra/settings.py` (300 → 301). Variations des autres : `domain/navigation.py` 385 → 429 (`pick_within_budget` sorti du service), `domain/ports.py` 826 → 846, `infra/docling_editor.py` 382 → 393, `api/schemas.py` 1092 → 1079, `domain/models.py` 436 → 415, `bootstrap/factories.py` 374 → 363.
- **Fichiers > 300, front (31 → 29)** : sortent `features/analysis/ui/StructureViewer.vue` (465) et `pages/IngestLaunchDialog.vue` (399), supprimés par `60234e4`. `shared/i18n.ts` 1642 → 1599.
- **Fonctions > 30 lignes, Python (44 → 45)** : entre `infra/body_limit.py:35` `__call__` (34, contrôle du `Content-Length` ajouté). S'allongent `services/version_service.py:156` `restore` 36 → 40, `persistence/analysis_edit_repo.py:137` `save_commands_and_cache` 53 → 56, `services/citation_service.py:94` `verify_citation` 62 → 64, `services/export_service.py:83` `_export` 32 → 35, `services/source_service.py:91` `show` 40 → 41. Raccourcit `services/chunk_service.py:177` `rechunk_document` 71 → 66.
- **Fonctions > 30 lignes, TS (21 → 20)** : sort `StructureViewer.vue` `drawOverlay` (80, fichier supprimé). `features/analysis-editor/previewScheduler.ts:23` `createPreviewScheduler` 35 → 38 (correctif `timer = null` proposé à la validation).
- **Paramètres, Python (41 → 40)** : sortent `services/chunk_service.py` `__init__` (13 → 4), `domain/chunk_editing.py` `insert` (6, supprimé), `services/document_tree_service.py` `__init__` et `services/export_service.py` `__init__` (5 → 4). Entrent `domain/ports.py:295` et `persistence/chunk_repo.py:132` `replace_for_document` (6, avec `keep_selection`), `infra/body_limit.py:72` `_answer` (5). Varient : `services/document_service.py:50` `__init__` 8 → 7, `bootstrap/factories.py:226` `build_document_service` 6 → 5, `services/version_service.py:82` `__init__` 5 → 6.
- **Paramètres, TS** : inchangé, `features/document/ui/PagePreviewWithOverlay.logic.ts:14` `isPageInRenderWindow` (6).
- **Booléens (20 → 23)** : `infra/host_guard.py:37` `parse_host_name(..., *, port_wildcard)`, `domain/ports.py:303` et `persistence/chunk_repo.py:140` `replace_for_document(..., keep_selection)`. Les deux sont de vrais flags (voir 3.2.4).

---

## Checklist

| # | Item | Poids | Conforme | Validation `efc0bc5` → final `a744f48` |
|---|------|-------|----------|----------------------------------------|
| 3.1.1 | Fonctions nommées avec des verbes | 1 | **non** | 0 → **2** fonctions nommées par leur résultat : `infra/docling_editor.py:364` `_ancestors`, `services/version_service.py:75` `_version_analysis_gone`. Les 26 autres nouveaux noms commencent par un verbe ou sont des prédicats (`can_be_current`, `can_be_current_of`, `has_docling_document`) |
| 3.1.2 | Variables qui expriment l'intention | 1 | oui | pas de régression dans le code ajouté ; `workspaceLatestAnalysis` (alias trompeur, préexistant) en INFO |
| 3.1.3 | Code en anglais, i18n | 2 | oui | résidu `infra/docling_projector.py:147` inchangé ; aucune chaîne d'interface ajoutée hors `t()` |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | oui | aucun nouveau nom abrégé |
| 3.2.1 | Une fonction = une chose | 2 | **non** | 2 → 2 (les deux fonctions Neo4j, non touchées). Aucune nouvelle fonction multi-responsabilités (cas par cas dans le Delta) |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | non | 65 → **65** (45 Py + 20 TS) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | non | 42 → **41** (40 Py + 1 TS) |
| 3.2.4 | Pas de flag arguments | 1 | **non** | 20 → 23 booléens, dont **2 vrais flags ajoutés** : `keep_selection` (`domain/ports.py:303`, `persistence/chunk_repo.py:140`) et `port_wildcard` (`infra/host_guard.py:37`) |
| 3.2.5 | `get_*` sans effet de bord | 2 | oui | nouveaux `get_current_analysis`, `get_chunk_push_service`, `get_document_tree_service` (`api/deps.py:42`, `:91`, `:98`) : simples lectures de l'état |
| 3.3.1 | Aucun fichier > 300 lignes | 1 | non | 49 → **47** (18 Py + 29 front) |
| 3.3.2 | Un concept par fichier | 2 | oui | 0 → 0 (cas par cas dans le Delta) |
| 3.3.3 | Imports ordonnés | 1 | oui | ruff propre d'après le mainteneur ; aucun import inutilisé trouvé par script sur les fichiers changés (Python et TS) |
| 3.4.1 | Commentaires = « pourquoi » | 1 | oui | trois commentaires périmés de la validation corrigés ou supprimés ; deux commentaires rendus faux par ce cycle, dans du code inatteignable (INFO), corrigés par `ef37b6f` après le commit audité |
| 3.4.2 | Pas de code commenté | 1 | oui | 0 → 0 (lignes de commentaire ajoutées relues : de la prose) |

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration multi-responsabilités (2 fonctions Neo4j, inchangé)

- **Localisation** : `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l., 7 paramètres), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.).
- **Constat** : non touchées par ce cycle. Même lecture qu'à la validation : la dépréciation du module (CHANGELOG) ne les sort pas du périmètre tant qu'aucune décision écrite ne le dit.
- **Regle violee** : item 3.2.1 (poids 2).
- **Remediation** : deux voies. (a) Une décision écrite qui sort `infra/neo4j/` du périmètre de l'audit, puisque le module part en 0.8.0 : l'item devient conforme (+11 points). (b) Découper : `write_document` en `_write_document_node` / `_write_pages` / `_write_items` / `_write_relations`, `fetch_graph` en une requête par type de nœud plus un assemblage. Sans serveur Neo4j pour les tests, (a) est la voie sûre.

### [MIN] Deux fonctions nommées par leur résultat (nouveau, item perdu)

- **Localisation** : `document-parser/infra/docling_editor.py:364` (`_ancestors`, générateur des ancêtres d'un élément, ajouté par `914246e`) ; `document-parser/services/version_service.py:75` (`_version_analysis_gone`, fabrique l'erreur 409, ajoutée par `73ceaf3`).
- **Constat** : l'item était devenu conforme au contrôle précisément à « 0 fonction nommée par son résultat » (après 26 renommages). Les 26 autres noms ajoutés par ce cycle sont justes, et parlants : `locate_quote`, `pick_within_budget`, `write_selection`, `adopt_selection`, `write_chunk_source`, `read_document_analysis_state`, `select_after_deleting`, `load_current_original`, `load_current_edited`, `parse_host_name`, `_find_latest_parsed_ids`, `_find_current_parses`, `_build_editor_response`, `_answer`, `_trim_left`, `_locate_across`.
- **Regle violee** : item 3.1.1 (poids 1). Même lecture qu'au contrôle, qui ne tolérait que `health_check`.
- **Remediation** : `_ancestors` → `_iter_ancestors`, `_version_analysis_gone` → `_raise_version_analysis_gone` (ou `_build_version_gone_error`). Deux renommages privés, deux et trois appelants. +1 poids.

### [MIN] Deux vrais flags ajoutés (nouveau, item perdu)

- **Localisation** : `document-parser/domain/ports.py:303` et `document-parser/persistence/chunk_repo.py:140` (`replace_for_document(..., keep_selection: bool = False)`, seul appelant avec `True` : `document-parser/services/chunk_service.py:229`) ; `document-parser/infra/host_guard.py:37` (`parse_host_name(host, *, port_wildcard: bool = False)`, seul appelant avec `True` : `:75`).
- **Constat** : `keep_selection` choisit entre deux écritures différentes (`adopt_selection` ou `write_selection`, `chunk_repo.py:160-163`), et la docstring du port doit expliquer les deux comportements (`ports.py:309-314`). `port_wildcard` change la grammaire acceptée (entrée de liste blanche ou en-tête de requête). C'est le schéma que le premier audit 0.7.4 avait compté comme flag (`select_analysis`, `additive`) et que le re-audit avait fait retirer ; la validation jugeait l'item conforme parce qu'« aucun flag » n'avait été ajouté.
- **Regle violee** : item 3.2.4 (poids 1).
- **Remediation** : passer la règle de sélection plutôt qu'un booléen (deux méthodes `replace_for_document` / `replace_for_rechunk`, ou un paramètre `selection: SelectionWrite` à deux valeurs nommées) ; scinder `parse_host_name` en `parse_request_host` et `parse_allowed_host`. +1 poids. Note : les modifications en cours dans l'arbre de travail (non auditées) introduisent `select_after_rechunk` / `select_after_restore` dans `domain/models.py`, ce qui pourrait servir à retirer `keep_selection`.

### [MIN] Fonctions au-delà de 30 lignes (45 Python, 20 TS)

- **Localisation** : pires, inchangés : `document-parser/infra/neo4j/tree_writer.py:69` (227), `frontend/src/features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216), `document-parser/bootstrap/builder.py:112` (`build`, 116), `document-parser/infra/neo4j/queries.py:137` (115). Nouveau : `document-parser/infra/body_limit.py:35` (`__call__`, 34).
- **Constat** : 65 → 65. Un départ (`drawOverlay`, fichier supprimé), une entrée, six fonctions qui s'allongent de 1 à 4 lignes.
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : hors d'atteinte pour 0.7.4. Sous le seuil sans effort : `body_limit.__call__` (sortir `_check_declared_length`), `version_service.restore` (sortir la conversion du snapshot et le choix de la sélection).

### [MIN] Fonctions à plus de 4 paramètres (40 Python, 1 TS)

- **Localisation** : en tête, `document-parser/services/store_service.py:231` (`update_store`, 10), `document-parser/services/analysis_service.py:83` (`__init__`, 10), `document-parser/services/store_service.py:180` (`create_store`, 9). Nouveaux : `document-parser/domain/ports.py:295` et `document-parser/persistence/chunk_repo.py:132` (`replace_for_document`, 6), `document-parser/infra/body_limit.py:72` (`_answer`, 5). TS : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14` (6).
- **Constat** : 42 → 41. Le plus gros cas de la validation est réglé (`ChunkService.__init__` 13 → 4, façade retirée et services construits par le composition root).
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : objet de paramètres pour `isPageInRenderWindow` ; `replace_for_document` retombe à 5 si le flag part. Le reste vient de l'injection de dépendances, hors d'atteinte pour 0.7.4.

### [MIN] Fichiers sources au-delà de 300 lignes (18 Python, 29 front)

- **Localisation** : nouveaux : `document-parser/services/source_service.py` (320), `document-parser/infra/settings.py` (301). Plus gros : `frontend/src/shared/i18n.ts` (1599), `frontend/src/pages/StudioPage.vue` (1444), `frontend/src/features/mcp-config/ui/McpConfigSection.vue` (1110), `document-parser/api/schemas.py` (1079), `document-parser/domain/ports.py` (846).
- **Constat** : 49 → 47. Les deux pages mortes de plus de 300 lignes sont parties ; `chunk_service.py` et `citation_service.py` passent sous le seuil.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : `infra/settings.py` passe sous le seuil en retirant une ligne ; supprimer le code mort front ci-dessous ne touche pas de fichier > 300. Le reste est hors d'atteinte pour 0.7.4.

### [INFO] Code mort front laissé par les suppressions

- **Localisation** :
  - `frontend/src/features/document/ui/HistoryDrawer.vue` (263 l.) : aucun importeur, absent de `features/document/index.ts`. Préexistant (déjà sans importeur à `efc0bc5`).
  - Chemin « workspace » de `frontend/src/features/document/store.ts` : `loadWorkspace` (`:155`) n'est appelé que par les branches `else` de `frontend/src/pages/DocParseTab.vue:374-379` et `:417`, inatteignables puisque le seul montage de `DocParseTab` passe toujours `:analysis` (`frontend/src/pages/AnalysisDetailPage.vue:55-60`, sous `v-else` d'un `!analysis`) ; `refreshWorkspace` (`:185`), `reloadWorkspaceVersions` (`:196`), `setWorkspaceVersion` (`:221`) n'ont aucun appelant ; `workspaceCurrentVersion` (`:67`) et `workspaceLatestAnalysis` (`:73`) aucun lecteur ; `pickWorkspaceVersion` (`:18`) ne sert qu'à ce chemin. `da6603d` a pourtant modifié ce code et ses tests.
  - `frontend/src/features/analysis-editor/api.ts:71` `rebuildAnalysisEdits` : aucun appelant, pas même un test.
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue` (143 l.) : aucun importeur. Préexistant, non relevé à la validation (seul un commentaire de `DocChunkTab.vue`, supprimé, le nommait).
- **Analyse** : ce n'est pas du code commenté, donc pas 3.4.2 ; même classement qu'à la validation (INFO, renvoi audits 04 et 05). Aucun effet sur un score de cet audit : aucun de ces fichiers ne dépasse 300 lignes, aucune de ces fonctions ne dépasse 30 lignes ni 4 paramètres.
- **Remediation** : trancher « code mort ou fonctionnalité perdue » (question déjà posée par l'audit 04). Si c'est du code mort : supprimer `HistoryDrawer.vue`, `StaleStoresStrip.vue`, le chemin workspace du store, les deux branches de `DocParseTab.vue`, `rebuildAnalysisEdits`, et leurs tests.

### [INFO] Code mort back restant

- `document-parser/infra/serve_converter.py:189` (`health_check`, appelé par les tests seulement ; il paraissait vivant parce que `OllamaProvider.health_check`, supprimé par `914246e`, portait le même nom), `document-parser/domain/models.py:314` (`mark_stale`, aucun appelant), `document-parser/domain/ports.py:102` (`DocumentMerger`) et `document-parser/infra/docling_merger.py:12` (tests seulement), `document-parser/domain/ports.py:553` / `document-parser/infra/opensearch_store.py:168` (`get_chunks`, tests seulement), `document-parser/mcp_adapter/server.py:90` (`INSTRUCTIONS`), `_neutralise_all` en double (`document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`).
- Levés depuis la validation : `_chunk_promoter` / `set_chunk_promoter`, `domain/hashing.py` (`hash_chunkset`, fichier supprimé, ce qui règle aussi la paire `hash_chunkset` / `_compute_chunkset_hash`), `domain/lifecycle_aggregation.py`, l'import `void`-é de `UNKNOWN_ELEMENT_COLOR` dans `BboxCanvas.vue`, la règle `.merge-button` d'`AnalysisEditor.vue`.

### [INFO] Commentaires périmés

- Rendus faux par ce cycle, dans le code inatteignable ci-dessus : `frontend/src/features/document/store.ts:148-149` (« Without a current analysis the newest version is pinned, as before » : depuis `da6603d`, `pickWorkspaceVersion` rend `null` sans analyse courante, `:22`) ; `frontend/src/pages/DocParseTab.vue:446` (« restores a different version from the History drawer » : le tiroir n'est plus monté). Les deux sont corrigés par `ef37b6f`, après le commit audité.
- Levés depuis la validation : « Wired in main.py » (`chunk_service.py`, `analysis_service.py`), « per-store dispatch is a follow-up » (`chunk_push_service.py`).
- Mineur : `document-parser/infra/body_limit.py:24`, ligne de docstring de 107 caractères (E501 est ignoré et le formateur ne coupe pas les docstrings).

### [INFO] Noms trompeurs

- `document-parser/services/export_service.py:125` `_resolve_default_analysis` : rend l'analyse demandée telle quelle **ou** l'analyse courante éditée ; « default » ne décrit que la seconde branche. Introduit par `73ceaf3` (renommage de `_resolve_original_analysis`). Proposition : `_resolve_analysis_to_export`.
- `frontend/src/features/document/store.ts:73` `workspaceLatestAnalysis` : simple alias de `workspaceActiveAnalysis`, qui est l'analyse affichée, pas la dernière. Aucun lecteur : à supprimer avec le chemin workspace.
- `document-parser/domain/models.py:129` `select_after_deleting` : nom d'action, mais la méthode ne sélectionne rien, elle rend l'id à sélectionner (la persistance écrit). Lisible avec sa docstring ; `choose_active_after_deleting` dirait mieux ce qu'elle fait.
- `document-parser/api/deps.py:43` répond « Document service not available » pour le lecteur de l'analyse courante, `:92` et `:99` « Chunk service not available » pour `ChunkPushService` et `DocumentTreeService`. Message 503 seulement, sans effet fonctionnel, mais il oriente mal un diagnostic.
- Ces noms ne relèvent pas de 3.1.1 (ils commencent par un verbe) ; ils relèvent de 3.1.2. Comme à la validation, quelques noms imprécis ne font pas perdre l'item.

### [INFO] Lisibilité des modèles de payload générés

- **Localisation** : `document-parser/api/schemas.py:317-359` (`_strip_bounds` `:323`, `_stored_payload_model` `:339`, `_EDIT_REQUESTS` `:356`, `EditCommandPayloadResponse` `:357`).
- **Constat** : six classes explicites de 4 à 6 lignes (≈ 45 lignes) sont remplacées par ≈ 30 lignes d'introspection de types : retrait récursif des `Annotated`, reconstruction des unions par `reduce(operator.or_, ...)`, re-souscription `get_origin(annotation)[...]`, double `get_args` pour sortir les membres de l'union discriminée annotée, nom de classe fabriqué par `str.replace("EditRequest", "PayloadResponse")`. Le commentaire `:317-320` dit bien le pourquoi (pas de bornes, pour relire les anciennes lignes ; clés inconnues interdites), `_strip_bounds` a une docstring, `_stored_payload_model` n'en a pas.
- **Analyse** : non, ce n'est pas compréhensible en une minute. Un mainteneur comprend vite **l'intention** grâce au commentaire, mais vérifier **le mécanisme** demande de connaître `typing.get_origin` / `get_args`, la forme `Annotated[Union[...], Field(discriminator=...)]` et `pydantic.create_model`. Effets concrets : `rg ReplaceTextPayloadResponse` ne trouve plus rien alors que le nom figure dans l'OpenAPI ; un type-checker ne voit pas les membres (d'où `fields: Any`) ; renommer une classe de requête renomme en silence un schéma de réponse. Le gain DRY est réel (une seule définition des champs) mais ne justifie pas ce coût de lecture pour six modèles stables. Pas d'item perdu : ni nommage, ni taille, ni commentaire faux. Renvoi audit 04 (même constat).
- **Remediation** : revenir à des classes explicites et garder l'unicité par un test qui compare les champs de chaque payload à ceux de sa requête. Les modifications en cours dans l'arbre de travail (non auditées) semblent aller dans ce sens.

### [INFO] Fonctions plus lourdes sans être multi-responsabilités

- `document-parser/services/version_service.py:156` `restore` (40 l.) : vérifications, conversion du snapshot (boucle inline), choix de la sélection avec repli (`:181-185`), écriture, traduction de l'erreur, journal. Toujours un seul cas d'usage, en étapes lisibles ; il a pris 4 lignes et une règle métier inline. Sortir `_restored_chunks` et la règle de sélection (ce que font les modifications en cours, non auditées).
- `document-parser/persistence/analysis_repo.py:206` `delete` : SQL brut (`BEGIN IMMEDIATE`, `SELECT`, `DELETE`) mêlé à des appels de plus haut niveau (`read_document_analysis_state`, `_find_latest_parsed_ids`, `write_selection`, la règle `select_after_deleting` du domaine). C'est une seule transaction pour un seul invariant (garder une analyse courante), donc pas 3.2.1 ; un `_find_document_id(db, job_id)` alignerait les niveaux.

### [INFO] Résidus reconduits

- 3.1.3 : `document-parser/infra/docling_projector.py:147`.
- 3.2.4 : flag HTTP `edited` (`document-parser/api/documents.py:119`, `export_document`), jugé à la frontière comme avant.
- Paire incohérente `getNodeColor` / `getKindColor` (`frontend/src/features/analysis/ui/GraphView.vue`, `frontend/src/features/analysis/ui/NodeDetailsPanel.vue`, `frontend/src/features/reasoning/kindColors.ts`) : inchangée, renvoi audit 05.

### [INFO] Arbre de travail modifié pendant l'audit

- `ef37b6f` (deux commentaires et une phrase de doc) et une vingtaine de fichiers modifiés non commités sont arrivés pendant le contrôle. Tout ce rapport porte sur `a744f48`, extrait par `git archive`. Les modifications en cours touchent trois points de ce rapport (`keep_selection`, les modèles de payload, `restore`) : elles demandent un nouveau passage des scripts une fois commitées.

---

## Delta vs validation efc0bc5

**Score : 72 → 61 (−11).** Items conformes : 10/14 → 9/14. Items perdus : 3.1.1 (2 noms) et 3.2.4 (2 flags), tous deux du fait de ce cycle. Aucun item gagné. Verdict : GO CONDITIONNEL → **GO CONDITIONNEL**.

| Écart de la validation | Statut final | Mesures validation → final |
|------------------------|--------------|----------------------------|
| [MAJ] 3.2.1 Orchestration multi-responsabilités | Inchangé (Neo4j, ouvert) | 2 → 2 |
| [MIN] 3.2.2 Fonctions > 30 lignes | Stable | 65 → 65 (44 + 21 → 45 + 20) |
| [MIN] 3.2.3 Fonctions > 4 paramètres | Réduit | 42 → 41 (41 + 1 → 40 + 1) |
| [MIN] 3.3.1 Fichiers > 300 lignes | Réduit | 49 → 47 (18 + 31 → 18 + 29) |
| [INFO] Code mort (pages mortes, restes back) | Largement levé (8 fichiers front, `_chunk_promoter`, `hash_chunkset`, `lifecycle_aggregation`, `health_check` d'Ollama) ; reste le chemin workspace, `HistoryDrawer.vue`, `rebuildAnalysisEdits`, et un nouveau relevé préexistant (`StaleStoresStrip.vue`) | |
| [INFO] Commentaires périmés | Les trois de la validation levés ; deux rendus faux par ce cycle (corrigés après, par `ef37b6f`) | |
| [INFO] Constructeurs qui s'élargissent | `ChunkService` levé (13 → 4, façade retirée) | |
| — | **Nouveau [MIN] 3.1.1** : `_ancestors`, `_version_analysis_gone` | 0 → 2 |
| — | **Nouveau [MIN] 3.2.4** : `keep_selection`, `port_wildcard` | 0 → 2 flags |

### 3.2.1, cas par cas (ce cycle crée-t-il une fonction multi-responsabilités ?)

| Fonction | Lecture | Statut |
|----------|---------|--------|
| `persistence/analysis_repo.py:206` `delete` (supprimer et resélectionner) | Une transaction, un invariant : verrou, lecture de l'état, suppression, nouvelle sélection calculée par le domaine (`DocumentAnalysisState.select_after_deleting`, `domain/models.py:129`), écriture. Niveaux d'abstraction mêlés (INFO), pas deux responsabilités | Pas d'écart |
| `services/version_service.py:156` `restore` (40 l.) | Le cas d'usage « restaurer une version », étapes dans l'ordre ; la règle de repli est inline (INFO). Compté en 3.2.2 | Pas d'écart |
| Routes de `api/document_chunks.py` sur trois services | Chaque route dépend d'un seul service (`ChunkServiceDep`, `ChunkPushServiceDep` ou `DocumentTreeServiceDep`) ; c'est le module qui en voit trois, ce qui est la séparation voulue. `api/documents.py` `get_document` lit deux dépendances pour une seule réponse | Pas d'écart |
| `api/schemas.py:339` `_stored_payload_model` | Fait une chose (fabriquer un modèle sans `type` ni bornes) ; le problème est la lisibilité (INFO), pas la responsabilité | Pas d'écart |
| `persistence/chunk_repo.py:132` `replace_for_document` | Deux comportements derrière `keep_selection` : compté en 3.2.4, pas en 3.2.1 | Voir 3.2.4 |
| `tree_writer.py:69` `write_document`, `queries.py:137` `fetch_graph` | Non touchées | Ouvert (MAJ) |

### 3.3.2, cas par cas (nouveau fichier fourre-tout ?)

| Fichier | Lignes validation → final | Lecture | Statut |
|---------|---------------------------|---------|--------|
| `domain/models.py` | 436 → 415 | Les entités et objets valeur du domaine. Le cycle retire la mécanique de suivi des changements (`selection_changed`, `mark_saved`) et ajoute des prédicats sur `AnalysisJob` et `DocumentVersion.chunk_source` : du comportement au bon endroit, pas un nouveau concept | Pas d'écart |
| `domain/ports.py` | 826 → 846 | Uniquement des protocoles ; `CurrentAnalysisReader` et `replace_for_document` élargi | Pas d'écart |
| `api/schemas.py` | 1092 → 1079 | Les DTO HTTP ; une petite mécanique générique de types s'y ajoute (`_strip_bounds`), qui serait mieux ailleurs ou absente, mais ne fait pas un deuxième concept | Pas d'écart |
| `services/chunk_push_service.py` | 365 → 362 | Diff, push et historique des push vers les stores : un concept | Pas d'écart |
| `domain/quote_location.py` (nouveau) | — → 97 | Localiser une citation dans un index de parse ; fonctions pures, un seul appelant (vérification de citation) | Pas d'écart, bonne extraction |
| `domain/navigation.py` | 385 → 429 | `pick_within_budget` sort de `NavigationService` : règle de budget de lecture, à sa place dans le domaine de navigation | Pas d'écart |
| `persistence/document_analysis_repo.py` | — | Seul module SQL de `document_analysis_state`, écritures en deux parties nommées | Pas d'écart |

---

## Points positifs

- **Beaucoup de code en moins, sans mesure qui se dégrade sérieusement** : −278 lignes Python, −1 781 lignes front, 8 composants morts supprimés avec preuve, la façade `ChunkService` retirée (constructeur 13 → 4) et deux fichiers backend passés sous 300 lignes.
- **Les restes signalés à la validation sont presque tous traités** : commentaires périmés, `_chunk_promoter`, import `void`-é, règle CSS orpheline, minuterie de l'aperçu, `hash_chunkset` en double.
- **Règles déplacées dans le domaine, avec des noms justes** : `can_be_current_of`, `has_docling_document`, `select_after_deleting`, `locate_quote`, `pick_within_budget` ; `write_selection` / `adopt_selection` / `write_chunk_source` disent exactement ce que chaque écriture touche.
- **`_to_edit_commands`** passe de 20 lignes d'aiguillage par type à un `model_dump` : une seule définition des champs côté écriture.
- **Aucun import inutilisé, aucun code commenté** dans les fichiers changés.

---

## Verdict partiel : GO CONDITIONNEL

Score **61/100** (60-79), **0 CRITICAL**, **1 MAJOR** (3.2.1 : 2 fonctions Neo4j, ≤ 3 donc non bloquant), 5 MINOR, 8 INFO.

Le score baisse de 11 points parce que ce cycle a ajouté deux noms et deux flags qui défont deux items gagnés aux cycles précédents ; les mesures de taille sont stables ou meilleures. Conditions et chemin le plus court :

1. Renommer `_ancestors` et `_version_analysis_gone` (3.1.1, +1 poids) et retirer les flags `keep_selection` et `port_wildcard` (3.2.4, +1 poids) : retour à **72**. Effort : moins d'une heure, tests compris.
2. Acter par écrit que `infra/neo4j/` sort du périmètre (module retiré en 0.8.0) : 3.2.1 conforme, **83** (GO) avec le point 1, 72 sans.
3. Faire repasser les scripts sur le commit qui portera les modifications en cours, qui touchent `keep_selection`, les modèles de payload et `restore`.

# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `513e8f9` (HEAD), arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Contrôle après le « plan 90 », en deux passages. Premier passage sur `8dc0623` (score 75), recontrôle sur `513e8f9` après les corrections `c4fca8a`, `8e1560b`, `513e8f9`. Base de comparaison : contrôle final sur `707a486` (`docs/audit/reports/release-0.7.4-final/04-kiss.md`, score 75).

Code non exécuté par l'auditeur. Le mainteneur indique, sur `513e8f9` : ruff propre, 1 776 tests passés, 15 ignorés ; front : eslint, prettier, vue-tsc propres, 580 tests passés, build réussi ; document OpenAPI identique. Non vérifié ici.

Périmètre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/` pour les constats) et `frontend/src/`.
Delta examiné : `git log 039778c..513e8f9` (15 commits). Quatre visent KISS (`16144f4`, `0ac6ee2`, `92390c6`, `1ad4846`), sept sont le découpage de masse de l'audit 03 (`52610cf` à `8dc0623`), un modifie la fiche 03 (`e4a73b3`), trois corrigent après le premier passage (`c4fca8a`, `8e1560b`, `513e8f9`).
Méthode : lecture de l'arbre à HEAD, `rg`, `git diff` / `git show` en lecture seule, recherche d'appelants de production pour chaque symbole suspect (méthodes de port, exports front, composants `.vue`, clés i18n), script AST de détection de relais (scratchpad, comparé entre `039778c`, `8dc0623` et `513e8f9`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 8 |
| Score | 83 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 12 |

Poids total : 12. Poids conformes : 10 (4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8). Non conforme : 4.2 (2).
`score = 10 / 12 × 100 = 83`. Premier passage (`8dc0623`) : 75. Contrôle précédent (`707a486`) : 75.

Toutes les corrections annoncées sont faites et 4.3 redevient conforme. 4.2 reste non conforme, pour du code mort plus ancien que le plan 90 que ni le contrôle précédent ni mon premier passage n'avaient trouvé : toute la fonctionnalité front des stores (environ 1 030 lignes) et `StatusBadge.vue`, sans importeur depuis le 2026-07-29.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:88`). `PreviewScheduler` redevient une classe simple de 52 lignes, sans fabrique |
| 4.2 | Résout le problème actuel, pas hypothétique | 2 | **Non** | Les restes du premier passage sont levés. Mais `frontend/src/features/store/` (api, `StoreForm.vue`, trois sous-formulaires, logique, barrel : 1 034 lignes) n'a aucun importeur de production depuis `61ccd54` ; `shared/ui/StatusBadge.vue` (91 l.) non plus ; environ 51 clés i18n par langue ne sont lues que par ce code ou par rien |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | **Oui** | Relais `mcp_adapter.build_mcp_server` supprimé, les deux appelants importent `mcp_adapter.server` (`bootstrap/mcp_mount.py:106`, `mcp_stdio.py:58`) ; `PreviewScheduler` sans délégation. Reste un relais, justifié par écrit (`services/parse_loader.py:72-79`) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui | Inchangé : contrôle `Host` maison, raison écrite (`infra/host_guard.py:79-86`) ; cache d'aperçu sur `OrderedDict` |
| 4.5 | Configuration simple | 1 | Oui | Inchangé depuis le premier passage : `API_ALLOWED_HOSTS` en noms seuls (`infra/host_guard.py`, 104 l.), `MAX_IMPORT_SIZE_MB` constante (`main.py:53`). `AnalysisConfig` reçoit `conversion_timeout` et `max_concurrent` (`services/analysis_service.py:90-98`) : un seul objet de réglage au lieu de deux canaux |
| 4.6 | Pas d'indirection inutile | 2 | Oui (limite) | Chemin des requêtes inchangé. Les quatre dataclasses de transport de `bootstrap/builder.py` restent (INFO) |
| 4.7 | Pas de méta-programmation / magie | 2 | Oui | Grep fiche + `create_model`, `importlib`, `__getattr__` : rien en production |
| 4.8 | Structures de données les plus simples | 1 | Oui (limite) | Objets valeur qui déplacent des paramètres : 6 → 4 (`GraphDocument` supprimé ; `_DocumentNode`, `PageBatching`, `AnalysisRun` et les dataclasses de `builder.py` restent). `AnalysisDetailPage` télécharge toujours tous les résumés pour en trouver un (`pages/AnalysisDetailPage.vue:123`) |

### Métriques de périmètre

| Mesure | efc0bc5 | a744f48 | 707a486 | 8dc0623 | 513e8f9 |
|--------|---------|---------|---------|---------|---------|
| Lignes Python de production, net depuis la colonne précédente (hors `tests/`) | — | −278 | +182 | +327 (+2 322 / −1 995) | **−35** (+108 / −143) |
| Lignes Python de production, net depuis `039778c` | | | | +327 | **+292** (+2 351 / −2 059) |
| Lignes front de production, net depuis la colonne précédente (hors tests) | — | −1 781 | +12 | −523 (+705 / −1 228) | **−279** (+41 / −320) |
| Lignes front de production, net depuis `039778c` | | | | −523 | **−802** (+709 / −1 511) |
| Paramètres du constructeur de `ChunkService` | 13 | 4 | 5 | 4 | 4 |
| Paramètres du constructeur d'`AnalysisService` | | | | 10 | 8 |
| `infra/host_guard.py` | 113 l. | 89 l. | 130 l. | 104 l. | 104 l. |
| Relais purs | 6 | 1 | 1 (justifié) | 2 + 6 délégations | **1** (justifié) |
| Création dynamique de classes en production | 0 | 1 | 0 | 0 | 0 |
| Objets valeur qui ne font que déplacer des paramètres | — | — | — | 6 (+ 2 états TS) | 4 (+ 1 état TS) |
| Code front sans importeur de production | — | — | — | ≈ 150 l. relevées | ≈ 1 125 l. (`features/store/`, `StatusBadge.vue`) + ≈ 102 lignes i18n |

---

## Ecarts constatés

### [MAJ] Fonctionnalité front des stores et composant sans importeur — porte l'item 4.2 (nouveau constat, code antérieur)

- **Localisation** :
  - `frontend/src/features/store/api.ts` (133 l. : `fetchStores`, `fetchStore`, `createStore`, `updateStore`, `deleteStore`, `fetchStoreDocuments`, `removeDocumentFromStore`, `queryStore` sans aucun appelant ; `testStoreConnection` appelé seulement par `StoreForm.vue:197`) ; `frontend/src/features/store/index.ts` (barrel que rien n'importe) ; `frontend/src/features/store/ui/StoreForm.vue` (520 l.), `StoreConfigForm.vue` (47 l.), `Neo4jConfigForm.vue` (109 l.), `OpenSearchConfigForm.vue` (92 l.), `connectionForm.logic.ts` (132 l.) ; tests associés `features/store/api.test.ts`, `features/store/ui/connectionForm.logic.test.ts`.
  - `frontend/src/shared/ui/StatusBadge.vue` (91 l.), sans importeur depuis `825332c`.
  - `frontend/src/shared/i18n.ts` : 33 clés lues seulement par `features/store/`, 18 clés `stores.*` lues par rien (`:689` et suivantes), en deux langues.
- **Constat** : `rg` sur `features/store`, `@/features/store`, `StoreForm`, `StoreConfigForm`, `Neo4jConfigForm`, `OpenSearchConfigForm`, `import.meta.glob` et `app.component(` ne trouve aucun importeur hors du dossier lui-même et de ses tests. Les pages qui montaient ces composants (`StoresListPage`, `StoreCreatePage`, `StoreEditPage`, `StoreDetailPage`, `StoreQueryPage`) et leurs routes ont été supprimées par `61ccd54` (« remove store workspace routes », 2026-07-29, avant `v0.7.0`) ; le client, le formulaire et leurs tests sont restés. Ce code compile et ses tests passent, ce qui l'a rendu invisible aux contrôles précédents, y compris à mon premier passage. Les routes backend `/api/stores/*` restent une API légitime (création et liste des stores par API) ; seul le côté front est mort.
- **Règle violée** : item 4.2 (poids 2), au même titre que le code mort compté dans les rapports précédents.
- **Remédiation** : décider « code mort ou écran perdu ». Si aucun écran de gestion des stores n'est prévu en 0.7.x : supprimer `features/store/` en entier (code et tests), `StatusBadge.vue`, et les 51 clés i18n par langue (environ 1 300 lignes). Sinon, rebrancher une route qui monte `StoreForm`. Avec l'une ou l'autre, 4.2 redevient conforme (score 100).

---

### [INFO] Version du moteur estampillée à chaque sauvegarde (nouveau, `8e1560b`)

- **Localisation** : `document-parser/services/analysis_edit_service.py:172` (`replace(stream, engine_version=ENGINE_VERSION)`) ; `persistence/analysis_edit_repo.py:214-217` (`UPDATE analysis_edit_streams SET engine_version = ?`, dans la transaction de sauvegarde) ; `domain/ports.py:438-450`.
- **Constat** : sans cet estampillage, un flux créé par une ancienne version du moteur n'aurait plus jamais eu de copie de travail acceptée au chargement (`:85-95`) : relecture complète à chaque ouverture. L'ajout coûte une requête dans une transaction déjà ouverte et rend la comparaison ajoutée au premier passage cohérente. Pas de sur-ingénierie. Réserve de modèle : la version décrit la copie de travail (`edited_analysis_cache`) mais elle est rangée sur le flux ; la mettre sur la ligne de cache éviterait la mise à jour d'une deuxième table. Neutre pour la note.

### [INFO] `IngestionSource` déplacée dans le domaine (nouveau, `8e1560b`)

- **Localisation** : `document-parser/domain/value_objects.py:153-159` ; importée par `api/ingestion.py:16`, `services/chunk_push_service.py:17`, `services/ingestion_service.py:28`.
- **Constat** : la route et deux services la construisent ; la sortir du service supprime l'import d'un service par l'API. Neutre pour KISS. Détail : elle est rangée sous l'en-tête de section « Reasoning (live docling-agent runner) » (`:150`), qui ne la concerne pas.

### [INFO] Trois propriétés du nœud `:Document` écrites en constantes (nouveau statut, `8e1560b`)

- **Localisation** : `document-parser/infra/neo4j/tree_writer.py:154-180`.
- **Constat** : `GraphDocument` est supprimé ; `write_document` reprend `(neo, *, doc_id, filename, document_json)`. `source_uri=""`, `docling_version=""` et `tenant_id="default"` sont écrits en dur, avec un commentaire qui dit pourquoi (garder la forme du graphe). Plus de paramètre pour un besoin non exprimé ; reste trois propriétés sans lecteur dans le dépôt (`rg` dans `infra/neo4j/queries.py` : aucune lecture). Recevable.

### [INFO] Objets valeur qui déplacent encore des paramètres (réduit)

| Objet | Où | Statut à 513e8f9 |
|-------|----|------------------|
| `GraphDocument` | — | **Supprimé** |
| `_DocumentNode` | `infra/neo4j/tree_writer.py:72` | Gardé, aplati (quatre champs). Sert à passer sous quatre paramètres une fonction privée qui envoie une requête Cypher |
| `PageBatching` | `services/analysis_service.py:83` | Gardé. `_plan_batches` est maintenant une fonction pure de module (`:101-105`), testable seule : mieux. Elle pourrait prendre `(total_pages, batch_size)` |
| `AnalysisRun` | `services/analysis_service.py:72` | Inchangé |
| `_AnalysisServices` … `_StructureServices` | `bootstrap/builder.py:270-421` | Inchangés (voir INFO suivant) |
| `SchedulerState` | — | **Supprimé** (classe `PreviewScheduler`) |
| `PdfLoaderState` | `features/document/ui/usePdfDocument.ts:9` | Inchangé |

Les objets valeur qui simplifient l'appel (`ChunkReplacement`, `CommandActivation`, `AnalysisOutput`, `StoreDraft`, `StoreChanges`, `ReadScope`, `NamespaceOverrides`, `McpSurface`, `PreviewViewState`) sont inchangés. `AnalysisConfig` absorbe deux réglages du constructeur : simplifie.

### [INFO] Quatre dataclasses de transport dans le démarrage (reconduit)

- **Localisation** : `document-parser/bootstrap/builder.py:270-421`, consommées une seule fois `:124-142`.
- **Constat** : inchangé. Chaque `_build_*` retourne un objet que `build()` recopie champ par champ dans `self._update(...)` ; treize noms de services écrits trois fois.
- **Remédiation** : faire retourner aux `_build_*` les arguments de `_update`, ou accepter un `build()` plat.

### [INFO] Composables découpés en fabriques à usage unique (reconduit)

- **Localisation** : `frontend/src/shared/composables/usePagination.ts` (`createPageWindow`, `createPageNavigation`, résultat étalé) ; `frontend/src/shared/ui/accordion.ts` (`createClosedSet`). Inchangé.

### [INFO] Lecture de l'environnement par familles de `dict[str, Any]` (reconduit)

- **Localisation** : `document-parser/infra/settings.py:226-336`. Inchangé : clés non vérifiées par le typage, défauts écrits deux fois.

### [INFO] Deux grammaires pour deux listes d'hôtes (reconduit)

- **Localisation** : `document-parser/infra/settings.py:101-108`, `:328-330`. `API_ALLOWED_HOSTS` en noms seuls, `MCP_ALLOWED_HOSTS` avec la grammaire du SDK MCP.

### [INFO] Cache d'aperçu et carte de citation (reconduits, hors 4.2)

- `infra/preview_cache.py` (42 l.), raison écrite. Carte de citation : option documentée (`docs/mcp-server.md:50`, `:158`), 1 256 lignes d'HTML pour une option éteinte par défaut.

### [INFO] API sans client front (statut précisé)

- **Localisation** : `document-parser/api/document_versions.py:54-77` (versions) ; `GET /api/documents/{id}/chunks/pushes` (client `fetchChunkPushes` supprimé par `513e8f9`) ; `/api/stores/*` (client mort, voir MAJ).
- **Constat** : fonctionnalités d'API, documentées pour les versions ; la docstring du routeur de versions ne parle plus du tiroir (`c4fca8a`). Pas 4.2.

### [INFO] Un relais gardé, raison écrite ; résidus reconduits

- `services/parse_loader.py:72-79`, recevable.
- Port `ActiveAnalysisResultReader` / `active_result_service`, `provider_type` du LLM, alias `features/history/api.ts:2-5`, `PdfInspector` construit par deux chemins, adaptateur `DoclingTreeReader` (relais au titre du port, non compté).

---

## Recontrôle sur 513e8f9

Lu : `git diff 8dc0623..513e8f9` hors `docs/audit/reports/` (58 fichiers, +298 / −655, dont production Python +108 / −143 et front +41 / −320).

### Constats du premier passage

| Constat (8dc0623) | Statut à 513e8f9 | Preuve |
|-------------------|------------------|--------|
| [MAJ 4.2] Mode édition mort d'`ElementProperties.vue` | **Levé** | Template, props `saving` / `editable`, émission `saveChunk`, état, `startEdit` / `cancel` / `save`, observateur, 74 lignes de CSS supprimés ; docstring réécrite (`ElementProperties.vue:97-107`) ; quatre clés `properties.editChunk|cancel|save|saving` retirées des deux langues ; scénario `@editInline` et l'appel conditionnel retirés de `doc-parse-properties.feature` |
| [MAJ 4.2] `documentStore.rechunk` / `pushToStore` | **Levé** | Supprimés avec leurs tests et l'import de `pushChunksToStore` (`features/document/store.ts`) |
| [MAJ 4.2] `GraphDocument` et trois paramètres jamais renseignés | **Levé** | Objet supprimé, `write_document(neo, *, doc_id, filename, document_json)` (`tree_writer.py:343-345`) ; valeurs neutres écrites en dur avec leur raison (`:155-156`) |
| [MIN 4.3] Relais `mcp_adapter.build_mcp_server` | **Levé** | `mcp_adapter/__init__.py` ne contient plus que sa docstring ; appelants sur `mcp_adapter.server.build_mcp_server` |
| [MIN 4.3] Délégations de `previewScheduler.ts` | **Levé** | Classe `PreviewScheduler` (`previewScheduler.ts:8-52`), méthodes directes, état privé ; appel `new PreviewScheduler(...)` (`analysis-editor/store.ts:47`) |
| [INFO] `PageBatching` déballé dans `_plan_batches` | **Partiellement levé** | `_plan_batches` devient pure et module-level ; l'objet reste |
| [INFO] `_DocumentNode` | **Partiellement levé** | Aplati, ne contient plus un autre objet ; reste un regroupement pour une fonction privée |
| [INFO] Docstring du routeur de versions | **Levé** | `api/document_versions.py:5-6` |
| [INFO] Dataclasses de `builder.py`, composables, `**dict` de settings, grammaires d'hôtes, `PdfLoaderState` | **Intacts** | Non touchés par les corrections |

### Corrections annoncées en plus

| Correction | Vérifiée | Effet KISS |
|------------|----------|------------|
| `AnalysisEditRepository.replace_cache` supprimé | Oui (`domain/ports.py:438-450`, `persistence/analysis_edit_repo.py`) | Moins de surface : une méthode de port et son adaptateur sans appelant de production |
| Quatre exports front sans appelant supprimés | Oui : `fetchAnalyses` (`features/analysis/api.ts`), `partitionByHiddenChips` (`legendFilters.ts`), `fetchChunkPushes` + deux interfaces (`features/chunks/api.ts`), `formatAbsolute` (`shared/format.ts`) | −77 lignes de production |
| `_plan_batches` pure | Oui (`services/analysis_service.py:101-105`, appel `:320`) | Plus simple ; la mise à jour de progression et le log passent dans l'appelant |
| `conversion_timeout`, `max_concurrent` dans `AnalysisConfig` | Oui (`:90-98`, `bootstrap/factories.py:217-222`) ; `AnalysisConfig` devient `frozen`, défaut `AnalysisConfig()` au lieu de `None` + repli | Plus simple : un canal de réglage au lieu de deux |
| Estampillage de `engine_version` | Oui | Voir INFO ; justifié |
| `IngestionSource` dans le domaine | Oui | Voir INFO ; neutre |
| `DocumentConfig.max_file_size_bytes` (`services/document_service.py:37-40`) | Oui | Deux attributs recopiés du config supprimés ; plus simple |
| `_ensure_document_node` séparé de `_clear_document_chunks` (`infra/neo4j/chunk_writer.py:85-90`) | Oui | Neutre : le nom dit ce que fait la requête ; l'instantané Cypher est mis à jour (`tests/fixtures/neo4j_statements.json`) |

### Ce que les corrections ont pu introduire

Rien de nouveau au sens de la fiche. Le script de relais ne trouve que trois fonctions de plus à une ligne, toutes des requêtes Cypher nommées ou l'adaptateur du port `GraphWriter`, pas des relais. Aucune méthode de port n'est sans appelant de production (vérifié pour chaque méthode de `domain/ports.py`). Les deux défauts de détail sont en INFO : en-tête de section mal placé au-dessus d'`IngestionSource`, version du moteur rangée sur le flux plutôt que sur le cache.

### Ce que le recontrôle trouve en plus

La recherche d'importeurs étendue à tous les composants `.vue` et à tous les exports du front trouve le MAJ ci-dessus : la fonctionnalité front des stores et `StatusBadge.vue`, morts depuis juillet. C'est un oubli des passages précédents, le mien compris : je n'avais cherché que les symboles touchés par le delta.

---

## Delta vs contrôle précédent (707a486)

Score : **75 → 83 (+8)**. Items conformes : 6/8 → 7/8. 4.5 devient conforme ; 4.3 reste conforme (après un aller-retour au premier passage) ; 4.2 reste non conforme. CRIT 0 → 0, MAJ 1 → 1, MIN 4 → 0.

| Écart du contrôle précédent | Statut à 513e8f9 | Preuve |
|-----------------------------|------------------|--------|
| [MAJ] Plomberie de l'éditeur (4.2) | **Levé** | Route et client `rebuild` absents ; `engine_version` comparé (`analysis_edit_service.py:90`) et estampillé (`:172`) ; `warnings`, `reference_changes`, `beforeElementId`, `replace_cache` absents |
| [MIN] Configuration (4.5) | **Levé** | `host_guard.py` 130 → 104 l. ; `MAX_IMPORT_SIZE_MB` constante ; `OPENSEARCH_DEFAULT_LIMIT` absent |
| [MIN] Code mort front listé (chemin workspace, `HistoryDrawer.vue`, spec e2e) | **Levé** | `1ad4846`, puis mode édition d'`ElementProperties` retiré par `513e8f9` |
| [MIN] Code mort back (`DocumentMerger`, `get_chunks`, `mark_stale`) | **Levé** | `rg` vide |
| [MIN] Cache d'aperçu (4.2) | **Partiellement levé, accepté** | Verrou retiré, borne 16 Mo, raison écrite |
| [MIN] Carte de citation (4.2) | **Requalifié en INFO** | Option documentée avec un usage |
| [INFO] Règle de rechunk calculée deux fois | **Levé** | `chunk_service.py:225-229` |
| Nouveau | — | [MAJ] 4.2 `features/store/` et `StatusBadge.vue` (code antérieur, non relevé avant) ; [INFO] dataclasses de transport, composables découpés, `**dict` de settings |

### Le découpage de masse (audit 03), après corrections

Les trois formes de complexité relevées au premier passage sont réduites : le relais sans raison et `GraphDocument` ont disparu, `PreviewScheduler` est une classe sans délégation. Restent quatre objets qui déplacent des paramètres et deux composables découpés en fabriques à usage unique, sans effet sur la note. Bilan Python depuis `039778c` : +292 lignes nettes pour un comportement identique ; bilan front : −802.

---

## Points positifs

- **Toutes les corrections demandées au premier passage sont faites**, chacune vérifiée dans le code.
- **Plomberie de l'éditeur retirée en entier**, et la version du moteur est maintenant à la fois comparée et estampillée.
- **Configuration réduite** : noms seuls, constante, un seul objet de réglage pour `AnalysisService`.
- **Code mort traité avec preuve** sur les deux couches, y compris les exports front sans appelant.
- **Découpage Neo4j sous instantané** des requêtes, mis à jour avec la correction.

---

## Non vérifié

- Comportement réel : rien n'a été exécuté par l'auditeur ; les résultats de suites cités sont ceux du mainteneur.
- Qu'aucun écran prévu (feuille de route, issue ouverte) n'attende `features/store/` : la décision « code mort ou écran perdu » revient au mainteneur.
- Qu'aucun consommateur hors dépôt n'appelle l'API de versions, `/chunks/pushes` ou `/api/stores/*`, ni ne lise `source_uri`, `docling_version`, `tenant_id` sur les nœuds `:Document`.
- Le décompte des clés i18n mortes : par recherche littérale de `'clé'` ; une clé construite dynamiquement (`t(\`stores.${x}\`)`) échapperait au comptage.
- Le commentaire périmé de `api/schemas.py` sur les payloads (INFO du rapport `707a486`).
- Les composants front découpés non cités (`GraphView.vue`, `BboxOverlay.vue`, `sectionParenting.ts`, `PagePreviewWithOverlay.vue`) : lus en diff seulement.

---

## Verdict partiel : GO

Aucun écart CRITICAL. Un écart MAJOR (4.2), sous le seuil bloquant (plus de trois MAJ). Score 83 / 100, au-dessus du seuil GO (80), en hausse de 8 points sur le contrôle précédent et sur le premier passage.

Pour atteindre 100 : **4.2** — supprimer `frontend/src/features/store/` (code et tests), `shared/ui/StatusBadge.vue` et les 51 clés i18n par langue qu'ils sont seuls à lire ou que rien ne lit ; ou rebrancher un écran de gestion des stores si ce besoin existe.

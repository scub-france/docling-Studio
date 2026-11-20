# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `520aaf6` (HEAD), arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Contrôle après le « plan 90 », en quatre passages. Premier passage sur `8dc0623` (score 75), recontrôle sur `513e8f9` (83), second recontrôle sur `3ba8cf9` (83), troisième recontrôle sur `520aaf6` (**100**). Base de comparaison : contrôle final sur `707a486` (`docs/audit/reports/release-0.7.4-final/04-kiss.md`, score 75).

Code non exécuté par l'auditeur. Le mainteneur indique, sur `520aaf6` : front eslint, prettier, vue-tsc propres, 517 tests passés sur 67 fichiers, build réussi ; backend inchangé depuis `6295dc0` (ruff propre, 1 776 tests passés). Non vérifié ici.

**Troisième recontrôle, en bref** : `features/chunks/` et ses restes sont supprimés, plus aucun fichier du front n'est hors d'atteinte depuis `app/main.ts`, aucune clé ni aucun symbole supprimé n'est encore lu. 4.2 redevient conforme : **score 100, 8/8**. Voir « Troisième recontrôle sur 520aaf6 ». Les sections suivantes gardent l'historique des passages précédents.

**Second recontrôle, en bref** : les suppressions annoncées sont faites et aucune clé de traduction lue n'a été retirée. Mais une recherche d'atteignabilité depuis `app/main.ts` (graphe des imports statiques et dynamiques) trouve un autre bloc mort que la recherche par nom avait manqué : toute la fonctionnalité `frontend/src/features/chunks/` (1 971 lignes) et ses 44 clés i18n. 4.2 reste non conforme ; le score reste 83. Le détail est dans la section « Second recontrôle sur 3ba8cf9 » ; les sections plus bas décrivent l'état à `513e8f9`, sauf mention contraire.

Périmètre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/` pour les constats) et `frontend/src/`.
Delta examiné : `git log 039778c..513e8f9` (15 commits). Quatre visent KISS (`16144f4`, `0ac6ee2`, `92390c6`, `1ad4846`), sept sont le découpage de masse de l'audit 03 (`52610cf` à `8dc0623`), un modifie la fiche 03 (`e4a73b3`), trois corrigent après le premier passage (`c4fca8a`, `8e1560b`, `513e8f9`).
Méthode : lecture de l'arbre à HEAD, `rg`, `git diff` / `git show` en lecture seule, recherche d'appelants de production pour chaque symbole suspect (méthodes de port, exports front, composants `.vue`, clés i18n), script AST de détection de relais (scratchpad, comparé entre `039778c`, `8dc0623` et `513e8f9`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 8 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 13 |

Poids total : 12. Poids conformes : 12.
`score = 12 / 12 × 100 = 100`. Second recontrôle (`3ba8cf9`) : 83. Recontrôle (`513e8f9`) : 83. Premier passage (`8dc0623`) : 75. Contrôle précédent (`707a486`) : 75.

Le tableau des items ci-dessous vaut à `520aaf6`. Pour 4.2, la justification garde l'historique des constats levés ; l'état à `520aaf6` est en tête de cellule.

Toutes les corrections annoncées sont faites et 4.3 redevient conforme. 4.2 reste non conforme, pour du code mort plus ancien que le plan 90 que ni le contrôle précédent ni mon premier passage n'avaient trouvé : toute la fonctionnalité front des stores (environ 1 030 lignes) et `StatusBadge.vue`, sans importeur depuis le 2026-07-29.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:88`). `PreviewScheduler` redevient une classe simple de 52 lignes, sans fabrique |
| 4.2 | Résout le problème actuel, pas hypothétique | 2 | **Oui (limite)** | **À 520aaf6** : `features/chunks/`, `rechunkDocument`, `RechunkOptions`, `ChunkDiff`, `ChunkDiffStatus`, `PushSummary`, barrel `features/search/index.ts` et 44 clés par langue supprimés ; 0 fichier front hors d'atteinte. Restent, en INFO : 4 clés et `ALL_MODES` lus seulement par des tests, 3 alias de type sans lecteur, une API backend de chunks de document sans client propriétaire. **Historique — à 3ba8cf9** : `features/store/`, `StatusBadge.vue` et 162 clés i18n par langue supprimés ; reste `frontend/src/features/chunks/` (api, store, quatre composants : 1 971 l.) hors d'atteinte depuis `app/main.ts`, `rechunkDocument` (`features/document/api.ts:63`) lu seulement par lui, et 44 clés i18n par langue. **À 513e8f9** : les restes du premier passage sont levés. Mais `frontend/src/features/store/` (api, `StoreForm.vue`, trois sous-formulaires, logique, barrel : 1 034 lignes) n'a aucun importeur de production depuis `61ccd54` ; `shared/ui/StatusBadge.vue` (91 l.) non plus ; environ 51 clés i18n par langue ne sont lues que par ce code ou par rien |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | **Oui** | Relais `mcp_adapter.build_mcp_server` supprimé, les deux appelants importent `mcp_adapter.server` (`bootstrap/mcp_mount.py:106`, `mcp_stdio.py:58`) ; `PreviewScheduler` sans délégation. Reste un relais, justifié par écrit (`services/parse_loader.py:72-79`) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui | Inchangé : contrôle `Host` maison, raison écrite (`infra/host_guard.py:79-86`) ; cache d'aperçu sur `OrderedDict` |
| 4.5 | Configuration simple | 1 | Oui | Inchangé depuis le premier passage : `API_ALLOWED_HOSTS` en noms seuls (`infra/host_guard.py`, 104 l.), `MAX_IMPORT_SIZE_MB` constante (`main.py:53`). `AnalysisConfig` reçoit `conversion_timeout` et `max_concurrent` (`services/analysis_service.py:90-98`) : un seul objet de réglage au lieu de deux canaux |
| 4.6 | Pas d'indirection inutile | 2 | Oui (limite) | Chemin des requêtes inchangé. Les quatre dataclasses de transport de `bootstrap/builder.py` restent (INFO) |
| 4.7 | Pas de méta-programmation / magie | 2 | Oui | Grep fiche + `create_model`, `importlib`, `__getattr__` : rien en production |
| 4.8 | Structures de données les plus simples | 1 | Oui (limite) | Objets valeur qui déplacent des paramètres : 6 → 4 (`GraphDocument` supprimé ; `_DocumentNode`, `PageBatching`, `AnalysisRun` et les dataclasses de `builder.py` restent). `AnalysisDetailPage` télécharge toujours tous les résumés pour en trouver un (`pages/AnalysisDetailPage.vue:123`) |

### Métriques de périmètre

| Mesure | efc0bc5 | a744f48 | 707a486 | 8dc0623 | 513e8f9 | 3ba8cf9 | 520aaf6 |
|--------|---------|---------|---------|---------|---------|---------|---------|
| Lignes Python de production, net depuis la colonne précédente (hors `tests/`) | — | −278 | +182 | +327 (+2 322 / −1 995) | −35 (+108 / −143) | 0 (+10 / −10) | **0** |
| Lignes Python de production, net depuis `039778c` | | | | +327 | +292 | +292 | **+292** (+2 356 / −2 064) |
| Lignes front de production, net depuis la colonne précédente (hors tests) | — | −1 781 | +12 | −523 (+705 / −1 228) | −279 (+41 / −320) | −1 511 | **−2 118** (+4 / −2 122) |
| Lignes front de production, net depuis `039778c` | | | | −523 | −802 | −2 313 | **−4 431** (+712 / −5 143) |
| Paramètres du constructeur de `ChunkService` | 13 | 4 | 5 | 4 | 4 | 4 | 4 |
| Paramètres du constructeur d'`AnalysisService` | | | | 10 | 8 | 8 | 8 |
| `infra/host_guard.py` | 113 l. | 89 l. | 130 l. | 104 l. | 104 l. | 104 l. | 104 l. |
| Relais purs | 6 | 1 | 1 (justifié) | 2 + 6 délégations | 1 (justifié) | 1 (justifié) | 1 (justifié) |
| Création dynamique de classes en production | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Objets valeur qui ne font que déplacer des paramètres | — | — | — | 6 (+ 2 états TS) | 4 (+ 1 état TS) | 4 (+ 1 état TS) | 4 (+ 1 état TS) |
| Code front hors d'atteinte depuis `app/main.ts` | — | — | — | non mesuré | non mesuré (≈ 1 125 l. trouvées par nom) | 1 972 l. | **0** |
| Clés i18n par langue sans lecteur de production | | | | | ≈ 51 | 48 | **4** (lues seulement par `i18n.test.ts`) |

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

## Second recontrôle sur 3ba8cf9

Lu : `git diff 513e8f9..3ba8cf9` hors `docs/audit/reports/` (`6295dc0`, `3ba8cf9` ; `b77b07a` ne touche que des rapports). Production : Python +10 / −10, front −1 511.

### Ce qui est annoncé, vérifié

| Annonce | Vérifié | Preuve |
|---------|---------|--------|
| `frontend/src/features/store/` supprimé en entier | Oui | api, barrel, `StoreForm.vue`, trois sous-formulaires, logique et deux fichiers de test supprimés ; plus aucune référence (`rg "features/store\|StoreForm"` vide) |
| `shared/ui/StatusBadge.vue` supprimé | Oui | 91 lignes ; il était le seul lecteur des clés construites `status.${state}` et `status.tooltip.${state}`, retirées avec lui |
| « 108 clés par langue » retirées | **Plus que ça** | Le diff retire **162 clés distinctes, chacune dans les deux langues** (324 lignes) : `storeForm` 40, `stores` 18, `ingest` 17, `docs` 15, `storeDetail` 13, `status` 12, `storeQuery` 12, `comingSoon` 9, et 26 autres. Le nombre annoncé est faux, pas le résultat (voir ligne suivante) |
| Aucune clé lue n'est retirée | **Oui** | Pour chacune des 162 clés : aucune lecture littérale (`'clé'`, `"clé"`, `` `clé` ``) dans le code de production. Seules constructions dynamiques du front : `` t(`docsNew.${status}`) `` (`pages/DocsNewPage.vue:114`) et `` `analysisEditor.commandType.${commandType}` `` (`AnalysisEditHistoryPanel.vue:66`) ; leurs 11 et 6 clés sont toutes présentes. `t(item.labelKey)` (`AppSidebar.vue:13`) lit des clés écrites en clair, toutes présentes. Pas de défaut visible à l'écran attendu |
| Les deux langues restent alignées | Oui | 485 clés, chacune exactement deux fois |
| `IngestionSource` sortie de la section « Reasoning » | Oui | `domain/value_objects.py:150-159` |
| `AnalysisService` lit son délai dans la configuration | Oui | Attribut `_conversion_timeout` supprimé, trois lectures de `self._config.conversion_timeout` (`services/analysis_service.py:354`, `:477`, `:613-617`) ; plus de copie de la même valeur. Plus simple |

### Ce que le second recontrôle trouve

**[MAJ] `frontend/src/features/chunks/` hors d'atteinte — porte l'item 4.2 (nouveau constat, code antérieur au plan 90).**

- **Localisation** : `frontend/src/features/chunks/api.ts` (60 l.), `index.ts` (2), `store.ts` (230), `ui/ChunksPanel.vue` (301), `ui/ChunksEditor.vue` (622), `ui/ChunkItem.vue` (387), `ui/StrategyPopover.vue` (369) : 1 971 lignes ; `frontend/src/features/document/api.ts:63` (`rechunkDocument`, seul lecteur `features/chunks/store.ts:158`) ; 44 clés i18n par langue lues seulement par ce dossier (`chunk.panel.*`, `chunks.*`, `strategy.*`).
- **Constat** : un parcours du graphe d'imports (statiques, dynamiques `import()` du routeur, barrels résolus) depuis `app/main.ts` n'atteint aucun de ces fichiers. Rien hors du dossier n'importe `features/chunks`, `@/features/chunks`, `useChunksStore`, `ChunksPanel` ou `ChunksEditor`. Le dernier importeur de `ChunksPanel` était `pages/DocChunkTab.vue`, supprimé par `60234e4` (2026-11-19, « remove components nothing mounts ») ; `ChunksEditor` n'y apparaissait déjà qu'en commentaire. Le seul lien vivant était l'import de `pushChunksToStore` par `features/document/store.ts`, retiré par `513e8f9` : depuis, le dossier entier est isolé. Le contrôle précédent et mes deux passages l'ont manqué : la recherche par nom trouvait des mentions en commentaire (`shared/elementColors.ts:4`, `features/document/ui/DocTreeRail.vue:60`) et les comptait comme des importeurs. Les routes backend `/api/documents/{id}/chunks/*` (CRUD, fusion, découpe, diff, push) restent une API légitime ; seul le client front est mort. `features/chunking/` (chunks d'une analyse), lui, est vivant.
- **Règle violée** : item 4.2 (poids 2).
- **Remédiation** : décider « code mort ou écran perdu » (l'édition des chunks d'un document et leur envoi vers un store n'ont plus d'écran). Si aucun écran n'est prévu en 0.7.x : supprimer `features/chunks/` avec ses tests, `rechunkDocument` et son export dans `features/document/index.ts`, et les 44 clés par langue. 4.2 redevient conforme (score 100).

**[INFO] Restes mineurs.**
- 4 clés par langue lues seulement par `shared/i18n.test.ts` (`nav.studio`, `nav.history`, `history.tabAnalyses`, `history.tabDocuments`) : le test les prend comme exemples. Changer d'exemples dans le test et retirer les clés.
- `features/search/index.ts` (1 ligne) : barrel que rien n'importe ; le store de recherche est importé directement.
- `ALL_MODES` (`shared/routing/modes.ts:28`) : lu seulement par son test.

**Rien d'introduit par les deux commits.** 4.1, 4.3, 4.5, 4.6, 4.7 et 4.8 inchangés. Backend : aucune méthode de port sans appelant, aucun nouveau relais ; la recherche de symboles Python sans second usage (`pyunused.py`) ne trouve rien.

---

## Troisième recontrôle sur 520aaf6

Lu : `git diff 3ba8cf9..520aaf6` hors `docs/audit/reports/` (17 fichiers, +4 / −2 526 ; production front +4 / −2 122 ; backend inchangé). `6138331` ne touche que des rapports.

| Annonce / question | Vérifié | Preuve |
|--------------------|---------|--------|
| `features/chunks/` supprimé en entier | Oui | api, barrel, store, `ChunkItem`, `ChunksEditor`, `ChunksPanel`, `StrategyPopover` et leurs deux tests |
| `rechunkDocument` et son export supprimés | Oui | `features/document/api.ts`, `features/document/index.ts:2` |
| `RechunkOptions`, `ChunkDiff`, `ChunkDiffStatus`, `PushSummary` supprimés | Oui | `shared/types.ts` ; `DocChunk`, `ChunkBbox`, `ChunkingOptions` restent et ont des lecteurs (`DocParseTab.vue`, `linkedView.ts`, `ChunkPanel.vue`, `features/analysis/api.ts`…) |
| Barrel `features/search/index.ts` supprimé | Oui | `SearchPage.vue:54` importe `features/search/store` directement |
| 44 clés par langue retirées, aucune encore lue | Oui | 485 → 441 clés, chacune deux fois. Aucune des 44 n'a de lecture littérale ; les seules constructions dynamiques restent `docsNew.*` et `analysisEditor.commandType.*`, toutes présentes |
| Aucun symbole supprimé encore lu | Oui | `rg` de `RechunkOptions`, `ChunkDiff`, `PushSummary`, `rechunkDocument`, `useChunksStore`, `features/chunks` dans `frontend/src` et `e2e/` : vide |
| Specs Karate `doc-tab-chunk-mode.feature`, `doc-legacy-mode-links.feature` | Oui, intactes à bon droit | La première n'appelle que l'API (`/api/analyses`, `/rechunk`, `/chunks`) ; la seconde n'attend que `document-viewer`, `preview-with-overlay`, `preview-page-1`. Aucun des 19 `data-e2e` des composants supprimés n'apparaît dans `e2e/ui/src` |
| Graphe des imports depuis `app/main.ts` | 0 fichier hors d'atteinte | Script du scratchpad (imports statiques, `import()` du routeur, barrels) |
| Exports sans lecteur | `ALL_MODES` (lu par son test), alias de type `ElementType` (`shared/types.ts:143`), `StorageKey` (`shared/storage/keys.ts:16`), `RouteName` (`shared/routing/names.ts:32`) | Déjà présents avant le plan 90 ; types sans coût d'exécution |
| Backend | Inchangé | Aucune méthode de port sans appelant, un seul relais (justifié), rien de nouveau |

**4.2 rejugé sur tout le périmètre : conforme (limite).** Il ne reste ni code front hors d'atteinte, ni plomberie sans lecteur. Les restes sont de taille négligeable et en INFO :
- `nav.studio`, `nav.history`, `history.tabAnalyses`, `history.tabDocuments` et `ALL_MODES` ne sont lus que par des tests (laissés volontairement) ; `ElementType`, `StorageKey`, `RouteName` sont des alias de type sans lecteur.
- **[INFO] API de chunks de document sans client propriétaire.** `api/document_chunks.py` (245 l., 11 routes : CRUD, fusion, découpe, diff, push) et ses services (`chunk_service.py` 296 l., `chunk_push_service.py` 365 l.) n'ont plus d'appelant dans le front, ni dans le serveur MCP. Ils restent couverts par l'API et par `doc-tab-chunk-mode.feature`, et le mainteneur les garde explicitement (message de `520aaf6`). Je les classe comme une API légitime, comme l'API de versions et `/api/stores/*`. Si aucun client n'est prévu, c'est la prochaine candidate à une décision « API publique ou reste » ; dans le second cas, elle relèverait de 4.2.

4.1, 4.3, 4.4, 4.5, 4.6, 4.7 et 4.8 inchangés.

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

**À 520aaf6** : aucun écart CRITICAL, MAJOR ni MINOR. Score **100 / 100**, 8/8 items conformes (4.2, 4.6 et 4.8 à la limite), contre 75 au contrôle précédent. Les points de vigilance sont en INFO : l'API de chunks de document sans client, les quatre objets valeur qui déplacent des paramètres, les dataclasses de transport de `builder.py`, la carte de citation éteinte par défaut.

Historique — à `3ba8cf9` : 83 / 100, un écart MAJOR (4.2). Remédiation alors demandée, faite par `520aaf6` : supprimer `frontend/src/features/chunks/` (code et tests), `rechunkDocument` et les 44 clés i18n par langue que seul ce dossier lit ; ou rebrancher un écran d'édition des chunks d'un document si ce besoin existe. (Le constat de `513e8f9`, `features/store/` et `StatusBadge.vue`, est levé par `3ba8cf9`.)

Non vérifié en plus, au second recontrôle : la recherche d'atteignabilité suit les imports écrits en clair ; un composant enregistré globalement par un plugin tiers ou chargé par un chemin calculé lui échapperait (aucun `app.component(` ni `import.meta.glob` dans `frontend/src`). Les clés i18n lues par une construction dynamique autre que les deux trouvées échapperaient aussi au comptage.

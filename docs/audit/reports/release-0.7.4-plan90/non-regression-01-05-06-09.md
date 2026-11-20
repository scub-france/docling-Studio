# Contrôle de non-régression : audits 01, 05, 06, 09 après le « plan 90 »

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `8dc0623`
**Nature** : contrôle de non-régression, pas un audit complet. Quatre audits n'ont pas été refaits après les 12 commits `039778c..8dc0623` (suppression de code sans appelant, découpage des fonctions de plus de 30 lignes, objets valeur pour les signatures de plus de 4 paramètres). Pour chaque item du dernier rapport : inchangé, amélioré ou régressé, à partir du diff réel et du code à HEAD. Un item que le diff ne touche pas garde son verdict précédent.

Rapports de référence :

| Audit | Rapport de référence | Commit | Score |
|-------|----------------------|--------|-------|
| 01 Hexagonal Architecture | `release-0.7.4-final/01-clean-architecture.md` | `707a486` | 97 |
| 05 DRY | `release-0.7.4-validation/05-dry.md` | `efc0bc5` | 100 |
| 06 SOLID | `release-0.7.4-validation/06-solid.md` | `efc0bc5` | 100 |
| 09 Tests | `release-0.7.4-final/09-tests.md` | `a744f48` | 93 |

Les rapports 05 et 06 datent de `efc0bc5`. Les commits entre `efc0bc5` et `039778c` sont hors du périmètre de ce contrôle : je ne re-note que ce que les 12 commits touchent.

Suites lancées par le mainteneur sur `8dc0623` (non relancées ici, consigne machine) : ruff propre, backend 1773 passés / 15 ignorés ; frontend eslint, prettier, vue-tsc propres, 589 passés, build OK ; OpenAPI identique.

**Méthode** (lecture seule, rien exécuté du projet) :
- `git diff 039778c..HEAD` lu fichier par fichier sur `domain/`, `services/`, `api/`, `persistence/chunk_repo.py`, `bootstrap/`, `mcp_adapter/server.py`, `infra/neo4j/`, `infra/docling_editor.py`, les tests et le frontend touchés.
- `git archive` des deux arbres (`039778c`, `HEAD`) dans le scratchpad, puis trois scripts AST sans import du projet :
  1. corps de fonctions normalisés (noms et constantes effacés) apparaissant 2 fois ou plus, et blocs de 3 instructions consécutives répétés 3 fois ou plus, sur `document-parser/` hors tests, avant et après ;
  2. liste des fonctions de test backend avec leur nombre d'assertions (`assert`, `pytest.raises`, `.assert_*`) et de cas paramétrés, avant et après ;
  3. pour chaque méthode de `Protocol` de `domain/ports.py`, recherche d'un appel `.méthode` dans le code de production, avant et après.
- Comptage des `it(` des fichiers de test frontend touchés ; vérification de chaque sélecteur `data-e2e` des specs Karate UI contre `frontend/src` (préfixes dynamiques compris).
- Comparaison statique des requêtes Cypher de l'instantané Neo4j avec les littéraux du code avant découpage.

---

## Synthèse

| Audit | Avant | Après | Items qui basculent | Régressions (sans effet sur la note) |
|-------|-------|-------|---------------------|---------------------------------------|
| 01 | 97 | **97** | aucun | 1.2.3 : la règle du rechunk n'existe plus dans le domaine que comme contrat de port (lecture stricte : 91) |
| 05 | 100 | **100** | aucun | aucune ; plusieurs MIN réduits |
| 06 | 100 | **100** | aucun | `AnalysisEditRepository.replace_cache` sans appelant de production ; import d'un service pair à l'exécution |
| 09 | 93 | **93** | aucun | un cas de la règle du rechunk n'est plus testé ; mappage `Neo4jGraphWriter` sans test ; cache de l'éditeur jamais rafraîchi après un changement de version du moteur, sans test |

Aucun item ne bascule. Les régressions trouvées sont des réductions sous le niveau de l'item (INFO), listées en fin de rapport avec leur remédiation.

---

## 01 — Hexagonal Architecture

| # | Item | Poids | Verdict précédent (`707a486`) | Verdict à HEAD | Preuve |
|---|------|-------|-------------------------------|----------------|--------|
| 1.1.1 | `domain/` sans lib infra | 3 | Oui | **Inchangé (Oui)** | Grep de la fiche vide. Nouveaux objets du domaine (`AnalysisOutput`, `domain/models.py:185` ; `ChunkReplacement`, `:374` ; `CommandActivation`, `domain/analysis_editing.py:39`) : dataclasses gelées, stdlib et `domain.*` seulement. |
| 1.1.2 | Modèles, VO, ports sans I/O | 3 | Oui | **Inchangé (Oui)** | Les trois objets ci-dessus ne font que porter des champs ; `CommandActivation.to_command` construit un `EditCommand` (`domain/analysis_editing.py:46-48`). |
| 1.1.3 | Interaction externe par protocole | 3 | Oui | **Amélioré (Oui)** | `ChunkRepository.replace_and_select` / `replace_keeping_selection` prennent un `ChunkReplacement` (`domain/ports.py:290`, `:306`) ; adaptateur aligné (`persistence/chunk_repo.py:136`, `:140`). Retirés du port et de l'adaptateur sans appelant laissé : `DocumentMerger`, `VectorStore.get_chunks`, `default_limit` du pool (grep vide hors `.venv`). L'INFO « `get_chunks` : limite différente port/adaptateur » disparaît avec la méthode. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | **Inchangé (Oui)** | Aucun import. |
| 1.2.1 | `services/` sans FastAPI | 3 | Oui | **Inchangé (Oui)** | Grep vide. |
| 1.2.2 | Pas de SQL dans les services | 3 | Oui | **Inchangé (Oui)** | Aucun SQL ni `aiosqlite` dans `services/`. |
| 1.2.3 | Règles métier dans `domain/` | 2 | Oui | **Oui, réduit** (voir détail) | `resolve_selection_after_rechunk` supprimée (`16144f4`). La règle « un rechunk ne change pas une sélection existante ; sans ligne d'état, il adopte l'analyse découpée » n'est plus écrite que dans le contrat du port (`domain/ports.py:306-322`) et appliquée par `INSERT … ON CONFLICT DO NOTHING` (`persistence/document_analysis_repo.py:25-27`, `:90-103`). Le service ne décide plus rien (`services/chunk_service.py:223-229`). Suppression et restauration restent des fonctions du domaine (`domain/models.py:129`, `:164`). |
| 1.2.4 | Injection, pas de concrétions | 2 | Oui | **Amélioré (Oui)** | `ChunkService` perd `analysis_state_repo` (`services/chunk_service.py:53-63`) : une dépendance de moins. Aucun service n'importe `infra`/`persistence` (grep vide). Nouvel import à l'exécution d'un service pair pour un objet valeur : `services/chunk_push_service.py:18` (`IngestionSource`), voir R5. |
| 1.3.1 | Routes sans `persistence/` | 3 | Oui | **Inchangé (Oui)** | Grep vide. Les routes construisent maintenant des objets de la couche services (`api/stores.py:97`, `:133` ; `api/ingestion.py:16`, `:42`) ou du domaine (`api/analysis_edits.py:22`, `:159`). C'est le sens `api → services → domain` ; `tests/test_architecture.py:59` n'interdit à `api` que `infra` et `persistence`, et l'API importait déjà `EditCommand` du domaine. Conforme. |
| 1.3.2 | camelCase dans `api/schemas.py` seulement | 1 | **Non** | **Inchangé (Non)** | La clé `targetSequence` du payload `setCommandActive` est passée du service (`services/analysis_edit_service.py:199` à `707a486`) au domaine (`domain/analysis_editing.py:47`). Même format persisté, autre couche ; le domaine la lisait déjà (`:298`). Reste [MIN]. |
| 1.3.3 | Endpoints qui délèguent | 2 | Oui | **Inchangé (Oui)** | Les routes touchées ne font que mapper le DTO vers l'objet valeur et appeler une méthode. Route `/analysis-edits/rebuild` retirée (`0ac6ee2`). |
| 1.4.1 | Chaque adaptateur implémente un port | 3 | Oui | **Amélioré (Oui)** | `infra/docling_merger.py` (adaptateur d'un port jamais câblé) supprimé : l'INFO « `DocumentMerger` jamais câblé » est soldé. `GraphDocument` (`infra/neo4j/tree_writer.py:72`) est un paramètre interne de `write_document`, derrière `Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py:38`). |
| 1.4.2 | Config issue de `settings.py` | 2 | Oui | **Inchangé (Oui)**, INFO étendu | Le plafond d'import redevient une constante nommée (`main.py:53`, `MAX_IMPORT_SIZE_MB = 200`) au lieu d'un réglage, choix annoncé par `16144f4` ; le cache d'aperçu passe à 16 Mo (`infra/preview_cache.py:20`). Même lecture que l'INFO « configuration hors `settings` » du rapport précédent : ce sont des limites fixes du produit, plus des valeurs de configuration. `docs/configuration.md` et `.env.example` n'en parlent plus. |

**Score à HEAD** : poids conformes 31 / 32 = 96,9 → **97** (inchangé). Seul non conforme : 1.3.2 (MIN).
**Lecture stricte de 1.2.3** (une règle métier doit exister dans le domaine sous forme exécutable) : 1.2.3 non conforme [MAJ], 29 / 32 = **91**. C'est la lecture qui avait fait compter un MAJ à `a744f48`.

### 1.2.3 : la règle du rechunk

Ce qu'il y avait à `039778c` : `ChunkService` lisait l'état, appelait `resolve_selection_after_rechunk(state, chunked_id)` et passait le résultat à `replace_keeping_selection`. Quand une ligne d'état existait, la valeur rendue était ignorée par le `DO NOTHING` ; quand il n'y en avait pas, elle valait l'analyse découpée. La seule partie de la fonction qui changeait le résultat était donc « sans ligne, l'analyse découpée », et c'est exactement ce que le service passe maintenant (`services/chunk_service.py:225-227`, `chunk_source.analysis_id`). Le comportement est identique.

Ce qui change pour l'item :
- la règle n'a plus de forme exécutable dans le domaine ; elle est décrite en prose dans le contrat du port (`domain/ports.py:311-316`) et appliquée en SQL ;
- elle n'a plus de test unitaire (voir 09) ;
- le message de `16144f4` range ce retrait sous « Removed, no caller », ce qui est faux : la fonction avait un appelant (`services/chunk_service.py` à `039778c`). Le corps du message, lui, l'annonce (« ChunkService no longer reads the state first »).

Pourquoi je garde « Oui » : le service ne porte aucune règle (l'item vise d'abord « pas dans les services »), la règle est nommée par la méthode du port et écrite dans `domain/ports.py`, et le rapport précédent avait déjà accepté que la garantie réelle soit le SQL atomique (« la règle est dite deux fois, une fois en Python, une fois en SQL »). La différence avec `a744f48`, où j'avais compté un MAJ : il n'y a plus de drapeau `keep_selection=True`, mais une méthode de port dont le contrat énonce la règle. Je le signale comme réduction (R1) et donne la note stricte ci-dessus.

### `tests/test_architecture.py`

Aucune modification dans `039778c..HEAD` (`git diff --stat` vide). Les règles de couches sont par répertoire (`tests/test_architecture.py:56-63`) : les nouveaux modules et objets y tombent sans changement. Rien n'a été retiré de `_LEGACY_LAYER_IMPORTS`. La règle des services pairs (`PEERS`, `:132-149`) ne couvre toujours que les cinq modules de navigation : l'import `services/chunk_push_service.py:18 → services.ingestion_service` n'est pas vu (il l'était déjà sous `TYPE_CHECKING` à `039778c`, il est maintenant à l'exécution). Couverture inchangée, ni resserrée ni élargie.

### Placement des objets valeur

| Objet | Fichier | Utilisé par | Couche juste ? |
|-------|---------|-------------|----------------|
| `IngestionSource` | `services/ingestion_service.py:42` | `api/ingestion.py:42`, `services/chunk_push_service.py:133` | Oui (entrée d'un cas d'usage). Partagé par deux services : sa place naturelle serait `domain/value_objects.py` (R5). |
| `StoreDraft`, `StoreChanges` | `services/store_service.py:78`, `:93` | `api/stores.py:97`, `:133` | Oui : commandes du cas d'usage ; le domaine garde `Store`. |
| `AnalysisRun`, `PageBatching` | `services/analysis_service.py:72`, `:83` | le service seul | Oui. |
| `ReadScope` | `services/navigation_service.py:52` | `mcp_adapter/server.py:47`, `:204` | Oui (`mcp_adapter → services` permis, `tests/test_architecture.py:61`). |
| `NamespaceOverrides` | `services/config_overrides.py:83` | `app_config_service.py:160`, `mcp_config_service.py:80` | Oui ; la règle « la ligne si elle se lit, sinon l'env » était déjà dans ce module. |
| `ChunkReplacement`, `AnalysisOutput`, `CommandActivation` | `domain/` | ports, services, API | Oui : types d'un port ou d'une transition du domaine. |
| `McpSurface` | `mcp_adapter/server.py:96` | `bootstrap/mcp_mount.py:107`, `mcp_stdio.py:59` | Oui. |
| `GraphDocument` | `infra/neo4j/tree_writer.py:72` | `infra/neo4j/graph_adapter.py:59` | Oui (interne à l'adaptateur). |
| `Repositories` | `bootstrap/factories.py:237` | `bootstrap/builder.py:251` | Oui : la racine de composition peut connaître les classes SQLite. |

Aucune règle métier n'a changé de couche pendant les découpages : les fonctions extraites sont des méthodes privées du même module (`_load_restorable_version`, `_resolve_restored_selection` dans `services/version_service.py:199`, `:210`, qui appellent toujours `resolve_selection_after_restore` ; `_check_identity_free`, `_apply_name`, `_apply_slug` dans `store_service.py`). Seule exception : la règle du rechunk ci-dessus, qui n'a pas été déplacée mais retirée du domaine.

---

## 05 — DRY

| # | Item | Poids | Verdict précédent (`efc0bc5`) | Verdict à HEAD | Preuve |
|---|------|-------|-------------------------------|----------------|--------|
| 5.1 | Pas de bloc 3+ fois | 2 | Oui | **Amélioré (Oui)** | Script 1 : aucun nouveau corps de fonction en double ; blocs de 3 instructions répétés 3+ fois : 3 → 2, les deux restants sont l'édition legacy de `services/analysis_service.py:235`, `:259`, `:281` (déjà connue) ; le bloc ×4 de `infra/neo4j/queries.py:242-248` a disparu. MIN reconduits réduits : parse booléen `("1","true","yes","on")` 10 → 2 (`infra/settings.py:242`, `services/config_overrides.py:24`) ; `Query(alias="analysisId")` 8 → 7 ; `?analysisId=` front 8 → 6 ; fichiers avec `@keyframes spin` 15 → 14. |
| 5.2 | Types partagés centralisés | 2 | Oui | **Inchangé (Oui)** | Aucun `Protocol` ni `export interface/type` en double. Les nouveaux objets valeur partagés entre couches vivent dans `services/` (`IngestionSource`, `StoreDraft`, `StoreChanges`) : voir INFO. |
| 5.3 | Pas de magic numbers/strings éparpillés | 2 | Oui | **Amélioré (Oui)** | `HistoryDrawer.vue` supprimé emporte 2 teintes, 2 voiles et 1 hex sans token. La palette Cytoscape de `GraphView.vue` est déplacée telle quelle (mêmes 15 littéraux, `buildGraphElements`/`renderGraph`). Aucune couleur ajoutée ailleurs dans le diff. `MAX_IMPORT_SIZE_MB = 200` est nommé (`main.py:53`). |
| 5.4 | Logique réactive dans `shared/composables/` | 1 | Oui | **Inchangé (Oui)** | `shared/composables/usePagination.ts:19`, `:52` découpé sur place. |
| 5.5 | Config HTTP centralisée | 2 | Oui | **Inchangé (Oui)** | Un seul `fetch()` brut, le même (`frontend/src/features/document/ui/DownloadDropdown.vue:172`). |
| 5.6 | Schémas Pydantic qui transforment | 2 | Oui | **Inchangé (Oui)** | Champs `warnings`/`referenceChanges` retirés du schéma et du projecteur ensemble ; `MoveElementEditRequest` et `MoveElementPayloadResponse` alignés (`api/schemas.py:194`, `:337`). |
| 5.7 | Validation à un seul endroit | 1 | Oui | **Inchangé (Oui)** | Déplacement : cible et placement obligatoires dans le schéma (`api/schemas.py:194-198`), le type front (`frontend/src/features/analysis-editor/types.ts:12-17`) et la règle du domaine pour la relecture (`check_move_target`, `domain/analysis_editing.py:279`) : les trois sont d'accord. |

**Score à HEAD** : 12 / 12 = **100** (inchangé).

### Points regardés de près

- **`StoreDraft` / `StoreChanges` contre `StoreCreateRequest` / `StoreUpdateRequest`** (`services/store_service.py:78`, `:93` ; `api/schemas.py:592`, `:611`) : mêmes 9 champs. Ce n'est pas une duplication nouvelle : à `039778c`, les mêmes 9 noms étaient déjà écrits deux fois comme listes de paramètres nommés de `create_store` et `update_store`. Les objets valeur remplacent ces listes une pour une. Le DTO garde les types HTTP (`kind: str`), l'objet de service les types du domaine (`StoreKind`) ; la route mappe. Duplication tolérée par la fiche (DTO d'API contre objet de service), [INFO].
- **`GraphDocument` / `_DocumentNode`** (`infra/neo4j/tree_writer.py:72`, `:84`) : `_DocumentNode` contient un `GraphDocument` et ajoute `ingested_at`. Composition, pas copie de champs.
- **`AnalysisOutput`** (`domain/models.py:185`) : remplace les 5 paramètres de `mark_completed` ; ne recopie pas `ConversionResult` (`domain/value_objects.py:105`, champs et types différents : `pages` contre `pages_json`, `page_count`).
- **Frontend** : les fonctions extraites (`prepareCanvas`, `drawElementBoxes`, `findElementAt` dans `features/analysis/ui/BboxOverlay.vue:90`, `:107`, `:182`) portent les mêmes noms que celles de `features/document/ui/BboxCanvas.vue:125`, `:142`, `:247`. Les corps diffèrent (gestion du `devicePixelRatio`, signature) : c'est l'INFO existant « deux composants de dessin des bbox », toujours deux copies. `clickDownloadLink`, `createPageWindow`, `trackPageVisibility` n'ont pas d'équivalent ailleurs (grep `createElement('a')`, `IntersectionObserver(`).

---

## 06 — SOLID

| # | Item | Poids | Verdict précédent (`efc0bc5`) | Verdict à HEAD | Preuve |
|---|------|-------|-------------------------------|----------------|--------|
| 6.1.1 | Responsabilité unique des services | 2 | Oui | **Inchangé (Oui)** | Méthodes ajoutées dans les services touchés : toutes privées et extraites du même corps (`_plan_batches`, `_convert_batch`, `_update_document_after_analysis` dans `analysis_service.py` ; `_check_upload`, `_check_page_count` dans `document_service.py` ; `_build_drift_check`, `_build_match_check` dans `citation_service.py` ; `_export_source_pdf` dans `export_service.py`). Aucune nouvelle responsabilité. `AnalysisEditService.rebuild` retiré. |
| 6.1.2 | Un store Pinia par feature | 2 | Oui | **Inchangé (Oui)** | 14 `defineStore` avant et après. Le store document perd le chemin « workspace » qu'aucun écran n'atteignait. |
| 6.1.3 | Routes groupées par ressource | 1 | Oui | **Inchangé (Oui)** | 57 → 56 décorateurs `@router` (route `rebuild` retirée), aucune ajoutée. |
| 6.1.4 | Pas de module hétérogène | 2 | Oui | **Inchangé (Oui)** | Les objets valeur restent dans le module de leur cas d'usage. |
| 6.2.1 | Ports extensibles | 2 | Oui | **Inchangé (Oui)** | Aucun service n'importe `infra`/`persistence`. |
| 6.2.2 | Local/remote via `build_converter()` | 2 | Oui | **Inchangé (Oui)** | `ServeConverter.health_check` retiré (INFO 3 soldé) ; contrat de conversion inchangé. |
| 6.2.3 | Export sans modifier les endpoints | 1 | Oui | **Inchangé (Oui)** | `ExportService` découpé sur place (`_export_source_pdf`). |
| 6.3.1 | Convertisseurs interchangeables | 3 | Oui | **Inchangé (Oui)** | Non touché au-delà du retrait de `health_check`. |
| 6.3.2 | Pas d'exception hors contrat | 2 | Oui | **Inchangé (Oui)** | Contrat de `replace_*` réécrit sur `ChunkReplacement`, mêmes `ValueError` et `AnalysisNotSelectableError` déclarés (`domain/ports.py:299-303`, `:318-321`). |
| 6.3.3 | Pas d'`isinstance` sur les implémentations | 2 | Oui | **Inchangé (Oui)** | Non touché. |
| 6.4.1 | `DocumentConverter` / `DocumentChunker` séparés | 2 | Oui | **Inchangé (Oui)** | Non touché. |
| 6.4.2 | Aucun port n'impose de méthode inutile | 2 | Oui | **Oui, une régression INFO** | Script 3 : `VectorStore.get_chunks` et le port `DocumentMerger` (inutilisés) retirés. Mais `AnalysisEditRepository.replace_cache` (`domain/ports.py:446`, implémenté `persistence/analysis_edit_repo.py:220`) n'a plus d'appelant de production depuis le retrait de `rebuild` (`0ac6ee2`) ; seul un test l'appelle (`tests/test_analysis_editing.py:736`). Même lecture que l'INFO 30 du rapport précédent (`save_state` appelé par les tests seuls) : INFO, l'item tient. Voir R2. |
| 6.5.1 | Services dépendants de ports | 3 | Oui | **Inchangé (Oui)** | Grep `from infra|from persistence` sur `services/` : aucun import (trois mentions dans des commentaires). |
| 6.5.2 | Injection au composition root | 2 | Oui | **Inchangé (Oui)** | `bootstrap/builder.py` découpé en étapes nommées (`_build_repositories`, `_build_analysis_services`, `_build_file_services`, `_build_store_services`, `_build_structure_services`, `:250-412`). `Repositories` (`bootstrap/factories.py:237`) est typé sur les classes SQLite, ce qui est la place de ces concrétions. |
| 6.5.3 | Pas d'adaptateur instancié dans les services | 3 | Oui | **Inchangé (Oui)** | Grep `LocalConverter|ServeConverter|PreviewCache(|Sqlite*(|PdfiumInspector(|PdfPageRasterizer(|LocalDocumentFileStore(` sur `services/` : zéro. |

**Score à HEAD** : 31 / 31 = **100** (inchangé).

### Points regardés de près

- **Ports retirés ou changés** (`domain/ports.py`) : `DocumentMerger` retiré (INFO 15 soldé) ; `VectorStore.get_chunks` et `VectorStorePool.get(default_limit=…)` retirés, adaptateurs alignés (`infra/opensearch_store.py`, `infra/opensearch_pool.py`) ; `ChunkRepository.replace_and_select` / `replace_keeping_selection` : 6 paramètres → 1 objet. L'INFO 28 (le port des chunks écrit aussi l'état d'analyse) reste vrai sur le fond : `ChunkReplacement` regroupe chunks, source et sélection (`domain/models.py:374-381`).
- **Inversion de dépendance dans `bootstrap/`** : les services sont toujours construits à la racine et reçoivent leurs ports ; `ChunkService` est construit sans dépôt d'état (`bootstrap/builder.py:290`).
- **Import d'un service pair à l'exécution** : `services/chunk_push_service.py:18` importe `IngestionSource` de `services/ingestion_service.py`. Le module dépendait déjà de ce service sous `TYPE_CHECKING` ; la dépendance devient effective au chargement. Extension de l'INFO 25 (`PEERS` ne couvre pas ces modules). Voir R5.
- **Découvert en passant, antérieur au diff, non re-noté** : les six méthodes de `DocumentTreeReader` (`domain/ports.py:650`) n'ont pas d'appel `.méthode` dans le code de production, avant comme après. Je ne l'ai pas creusé : hors périmètre de ce contrôle.

---

## 09 — Tests

| # | Item | Poids | Verdict précédent (`a744f48`) | Verdict à HEAD | Preuve |
|---|------|-------|-------------------------------|----------------|--------|
| 9.1.1 | Tests backend passent | 3 | Oui | **Inchangé (Oui)** | Mainteneur : 1773 passés / 15 ignorés (Neo4j) sur `8dc0623`. Non relancé. |
| 9.1.2 | Tests frontend passent | 3 | Oui | **Inchangé (Oui)** | Mainteneur : 589 passés. Écart expliqué : `features/document/store.test.ts` 30 → 16 (-14), `features/document/api.test.ts` 14 → 13 (-1) ; 604 - 15 = 589. |
| 9.1.3 | Tests e2e UI qui passent | 2 | **Non** | **Inchangé (Non), réduit** | `doc-history-drawer.feature` supprimée avec `HistoryDrawer.vue` (remédiation (b) du MAJ précédent). Les deux autres specs obsolètes avaient été corrigées avant `039778c` (`cce3d24`). Les 135 sélecteurs `data-e2e` des specs existent dans `frontend/src` (préfixes dynamiques compris). Reste : aucune spec UI n'a tourné, et « PDF.js draws page 1 » est toujours `@regression`, hors de toute CI (`e2e/ui/src/test/resources/documents/doc-viewer.feature:1`). |
| 9.2.1 | Chaque route a un test | 2 | Oui | **Inchangé (Oui)** | Route `rebuild` retirée avec son test ; aucune route ajoutée. |
| 9.2.2 | Cas d'erreur testés | 2 | Oui | **Inchangé (Oui)** | Les tests d'erreur touchés gardent leurs assertions (`test_rechunk_409_when_the_analysis_disappears_before_the_write`, `test_saved_history_action_rejects_stale_and_invalid_targets`). Hôte : `*`, port et schéma maintenant refusés et testés (`tests/test_api_host_guard.py:97`). |
| 9.2.3 | Cas limites testés | 2 | Oui | **Oui, une perte INFO** | Le cas « ligne d'état avec sélection NULL : un rechunk la laisse NULL » n'est plus testé nulle part (R4). Les deux autres cas de la règle restent couverts sur SQLite réel (`tests/test_document_analysis_repo.py:122`, `tests/test_chunk_service.py:504`). |
| 9.2.4 | Règles du domaine testées | 1 | Oui | **Inchangé (Oui)** | `CommandActivation` passe par les tests du service ; `check_move_target` testé sur les trois placements (`tests/test_analysis_edit_rules.py:163-173`). |
| 9.2.5 | Stores et composants testés | 2 | Oui | **Inchangé (Oui)** | Les 14 tests retirés de `store.test.ts` visaient `loadWorkspace`, `reloadWorkspaceVersions`, `setWorkspaceVersion`, `pickWorkspaceVersion`, supprimés de `store.ts` ; le seul point de montage de `DocParseTab` passe toujours une analyse (`frontend/src/pages/AnalysisDetailPage.vue:55`), donc ce chemin était inatteignable. |
| 9.3.1 | Pas de `.only` / `.skip` | 3 | Oui | **Inchangé (Oui)** | 0 dans `frontend/src` et `e2e/`. |
| 9.3.2 | Skips justifiés | 1 | Oui | **Inchangé (Oui)** | Nombre de `pytest.mark.skip` identique. |
| 9.3.3 | Tests déterministes | 2 | Oui | **Inchangé (Oui)** | Le nouveau test Neo4j fige `datetime` du writer (`tests/test_neo4j_statements.py:448`) ; le seul `datetime()` restant est côté Cypher, donc dans le texte de la requête. |
| 9.3.4 | Vrais collaborateurs | 2 | Oui | **Inchangé (Oui)** | Les tests réécrits gardent SQLite réel ; `_load_replayed` (`tests/test_analysis_editing.py:1010`) passe par le vrai chemin de relecture au lieu de `rebuild`. |
| 9.3.5 | Assertions précises | 1 | Oui | **Inchangé (Oui)** | Script 2 : aucune fonction conservée n'a perdu d'assertion ni de cas paramétré, hormis les assertions des réglages et fonctions supprimés (`is_host_check_on`, `opensearch_default_limit`, `max_import_size_mb`). |
| 9.3.6 | Noms descriptifs | 1 | Oui | **Inchangé (Oui)** | Les tests renommés décrivent le nouveau comportement (`test_the_port_of_a_request_is_ignored`, `test_move_payload_reads_back_with_its_target_and_placement`). |

**Score à HEAD** : 25 / 27 = 92,6 → **93** (inchangé). Seul non conforme : 9.1.3 (MAJ).

### Tests backend supprimés ou réécrits

Fonctions de test : 1636 → 1623 (19 disparues, 6 ajoutées).

| Test disparu | Code de production | Verdict |
|--------------|--------------------|---------|
| `test_current_analysis.py::test_a_rechunk_keeps_an_existing_selection`, `::test_a_rechunk_without_a_row_adopts_the_chunked_analysis` | `resolve_selection_after_rechunk` supprimée, règle passée au SQL | **Perte partielle** : « sélection existante gardée » reste testé sur SQLite (`test_document_analysis_repo.py:122`), « sans ligne, l'analyse découpée » aussi (`test_chunk_service.py:504`) ; « ligne avec sélection NULL reste NULL » n'est plus testé (R4). |
| `test_analysis_editing.py::test_move_element_hands_each_protocol_to_its_own_mover` (5 cas) | second protocole de déplacement supprimé | Code retiré. Les trois placements restent testés de bout en bout (`test_analysis_editing.py:382`, `:390` ; `test_analysis_edits_api.py:379-413`). |
| `test_analysis_edits_api.py::test_rebuild_replays_the_saved_stream`, `::test_move_payload_keeps_its_null_keys_in_the_history` | route `rebuild` et champ `beforeElementId` supprimés | Code retiré ; remplacé par `test_move_payload_reads_back_with_its_target_and_placement` (`:206`). |
| `test_api_host_guard.py` (3 tests) | joker `*`, port dans une entrée, `is_host_check_on` supprimés | Comportement changé volontairement (`16144f4`), nouveaux tests `:90`, `:97`. L'INFO 2 du rapport précédent (joker non testé) tombe : `*` est maintenant une entrée ignorée, testée. |
| `test_body_limit.py::TestSetting` (3), `test_settings.py` (1 test, 2 assertions) | réglages `MAX_IMPORT_SIZE_MB`, `OPENSEARCH_DEFAULT_LIMIT` supprimés | Code retiré ; le middleware garde ses tests avec un plafond explicite. |
| `test_docling_merger.py`, `test_opensearch_store.py::TestGetChunks` (2), `test_vector_store_port.py` (2), `test_serve_converter.py` (2) | `DocumentMerger`, `get_chunks`, `health_check` supprimés | Code retiré. |

Réécritures mécaniques (appel par objet valeur, mêmes assertions) : `test_store_service.py`, `test_navigation_service.py`, `test_ingestion_service.py`, `test_mcp_*.py`, `test_bootstrap_pdf_wiring.py`, `tests/neo4j/*.py`, `test_chunk_service.py` (`args[0] == doc.id` → `args[0].document_id == doc.id`, même force). `test_analysis_editing.py` : `service.rebuild(...)` → `_load_replayed(service)`, qui efface le cache puis relit : la relecture reste comparée à l'état enregistré.

### Le nouveau test `test_neo4j_statements.py`

Ce qu'il prouve : pour 12 scénarios (`write_document` complet et vide, `write_chunks` nominal, écart de comptage, vide, et 7 cas de `fetch_graph`), la suite exacte des appels au pilote (session, transaction, `run`, `single`, `commit`), le texte Cypher (espaces normalisés), les paramètres, la valeur rendue ou l'exception, et les logs, sont égaux à l'instantané `tests/fixtures/neo4j_statements.json`. C'est une bonne garde pour un découpage pur : toute requête réordonnée, paramètre renommé ou lot regroupé autrement fait échouer le test. Comparaison statique : 20 des 27 requêtes distinctes de l'instantané sont des littéraux présents tels quels dans le code d'avant le découpage (`039778c`) ; les 7 autres sont des f-strings par label (`CREATE (n:Element:{label} …)`), introuvables comme littéral dans les deux versions. Cela ne contredit pas le message de `79463bb` (« instantané pris avant le découpage »), sans le prouver.

Ce qu'il ne prouve pas :
- que le Cypher est valide ou produit le bon graphe : aucun serveur, le faux pilote accepte tout ;
- la sémantique réelle du pilote : rollback d'une transaction qui échoue (le faux `__aexit__` n'en fait rien), forme des `Node` (`labels` est une liste ici, un `frozenset` dans `neo4j`) ;
- le mappage de l'adaptateur `Neo4jGraphWriter.write_document_tree` → `GraphDocument` (`infra/neo4j/graph_adapter.py:50-60`), modifié par `8dc0623`, qu'aucun test n'exécute (les tests `tests/neo4j/` appellent `write_document` directement et sont ignorés sans serveur) (R6) ;
- rien si `NEO4J_SNAPSHOT_UPDATE` est défini : le test réécrit l'instantané puis compare (`tests/test_neo4j_statements.py:454-457`), donc passe toujours. La variable n'apparaît pas dans `.github/` (grep).

Les 12 scénarios sont dans une seule fonction : le premier écart arrête le test et masque les suivants. Acceptable pour un instantané.

### La spec Karate supprimée

`e2e/ui/src/test/resources/documents/doc-history-drawer.feature` est supprimée dans le même lot que `HistoryDrawer.vue` (`1ad4846`). Cohérent : le composant n'était importé nulle part et aucune route ne l'affichait ; la spec visait `history-btn`, qui n'existait plus. Aucune autre spec, runner ou `CONVENTIONS.md` ne la référence (grep sur `e2e/` hors `target/`, ignoré par git). Les routes backend des versions (liste, restauration) n'ont plus d'appelant dans le frontend ; elles gardent leurs tests backend (`test_version_service.py`).

---

## Régressions et remédiations

Aucune ne fait basculer un item. Par ordre d'importance :

### R1 — La règle de sélection après un rechunk n'est plus exécutable dans le domaine (01, 1.2.3)

- **Localisation** : `domain/ports.py:306-322` (contrat) ; `persistence/document_analysis_repo.py:25-27`, `:90-103` (`ON CONFLICT DO NOTHING`) ; `services/chunk_service.py:223-229` ; commit `16144f4`.
- **Constat** : `resolve_selection_after_rechunk` supprimée. Comportement identique, mais la règle n'est plus qu'une phrase du contrat et une clause SQL, et son test unitaire a disparu. Suppression et restauration, elles, gardent leur fonction du domaine : les trois écrivains de la sélection ne sont plus traités de la même façon.
- **Remédiation** : au choix, (a) remettre une fonction du domaine que le test de l'adaptateur vérifie contre le SQL (la règle dite en Python et prouvée équivalente en SQL), ou (b) acter dans la fiche 01 qu'une règle appliquée atomiquement en SQL est conforme si le contrat du port l'énonce et qu'un test d'adaptateur couvre chacun de ses cas (voir R4). Effort XS.

### R2 — `AnalysisEditRepository.replace_cache` sans appelant de production (06, 6.4.2)

- **Localisation** : `domain/ports.py:446` ; `persistence/analysis_edit_repo.py:220` ; seul appelant `tests/test_analysis_editing.py:736`.
- **Constat** : son seul appelant était `AnalysisEditService.rebuild`, supprimé par `0ac6ee2`. Le nettoyage du code sans appelant a créé un nouveau symbole sans appelant.
- **Remédiation** : voir R3, qui lui redonne un appelant ; sinon le retirer du port et préparer le test par `save_commands_and_cache` ou en SQL. Effort XS.

### R3 — Le cache de l'éditeur n'est plus jamais rafraîchi après un changement de version du moteur (09, sans test ; fond : audits 12 et 02)

- **Localisation** : `services/analysis_edit_service.py:90` (cache refusé si `stream.engine_version != ENGINE_VERSION`), `:217` (`engine_version` écrit à la création du flux seulement), `:164` (seul `_build_cache` restant, dans `save`) ; commit `0ac6ee2`.
- **Constat** : un flux créé sous une version précédente du moteur garde cette version. Son cache est alors refusé à chaque lecture et le flux est rejoué à chaque `load_editor`, même après un enregistrement qui réécrit le cache. Avant, la route `rebuild` réécrivait le cache (sans changer non plus la version du flux). Le nouveau test (`tests/test_analysis_editing.py:1069`) vérifie la relecture, pas le retour à un cache utilisé. Sans effet tant que `ENGINE_VERSION` ne change pas.
- **Remédiation** : après une relecture dans `load_editor`, écrire le cache (`replace_cache`, ce qui règle R2) et mettre à jour `engine_version` du flux ; un test : après changement de version, une première lecture rejoue, la seconde utilise le cache. Effort S.

### R4 — Un cas de la règle du rechunk n'est plus testé (09, 9.2.3)

- **Localisation** : test supprimé `tests/test_current_analysis.py::test_a_rechunk_keeps_an_existing_selection` (seconde assertion, sélection NULL).
- **Constat** : « une ligne d'état dont la sélection est NULL reste NULL après un rechunk » n'est plus vérifié ni au domaine, ni au dépôt, ni au service.
- **Remédiation** : un test de dépôt à côté de `tests/test_document_analysis_repo.py:122` : ligne avec sélection NULL, `replace_keeping_selection(ChunkReplacement(..., active_analysis_id="analysis-a"))`, sélection toujours NULL et source écrite. Effort XS.

### R5 — Import à l'exécution d'un service pair pour un objet valeur (01 INFO 7, 06 INFO 25)

- **Localisation** : `services/chunk_push_service.py:18` ; `IngestionSource` défini `services/ingestion_service.py:42`, construit aussi par `api/ingestion.py:42`.
- **Constat** : la dépendance `chunk_push_service → ingestion_service` existait sous `TYPE_CHECKING` ; elle devient un import de module. `tests/test_architecture.py` (`PEERS`) ne la voit pas.
- **Remédiation** : déplacer `IngestionSource` dans `domain/value_objects.py` (il décrit un document, pas une étape du service), ou ajouter `chunk_push_service` à `PEERS` avec la raison. Effort XS.

### R6 — Mappage de `Neo4jGraphWriter` sans test (09)

- **Localisation** : `infra/neo4j/graph_adapter.py:50-60`.
- **Constat** : `8dc0623` y construit un `GraphDocument` ; ni l'instantané ni les tests d'intégration (ignorés sans serveur) ne passent par cet adaptateur. Le risque est faible (trois champs nommés), mais c'est la seule ligne modifiée de la couche Neo4j que rien n'exécute.
- **Remédiation** : un scénario de l'instantané qui passe par `Neo4jGraphWriter(driver).write_document_tree(...)` au lieu de `write_document`. Effort XS.

### INFO sans remédiation urgente

- Le message de `16144f4` range `resolve_selection_after_rechunk` sous « Removed, no caller » alors qu'elle avait un appelant (01).
- `StoreDraft`/`StoreChanges` recopient les 9 champs des DTO de store : duplication tolérée, et qui remplace les listes de paramètres d'avant (05).
- Le contrôle de cycle et de racine du déplacement (`infra/docling_editor.py:271`, `:279`) n'a de test ni avant ni après (09, antérieur au diff).
- `main.py:120` (montage conditionnel du contrôle `Host`) et `main.py:53` (plafond d'import) ne sont pas testés au niveau de l'application, comme avant (09).

---

## Points non vérifiés

- Rien n'a été exécuté : ni pytest, ni vitest, ni Karate, ni l'application. Les chiffres de suites sont ceux du mainteneur.
- L'affirmation de `79463bb` « instantané pris sur le code d'avant le découpage » : seule la comparaison statique de 20 requêtes sur 27 la soutient ; je n'ai pas fait tourner le test sur `039778c`.
- La validité du Cypher et le comportement réel du pilote Neo4j (aucun serveur).
- L'équivalence fine de chaque découpage frontend (`GraphView.vue`, `PagePreviewWithOverlay.vue`, `usePdfDocument.ts`, `BboxOverlay.vue`) : lue en diff, sans recherche systématique de doublons comme pour le backend (pas d'outil AST TS équivalent lancé).
- Les éléments des rapports 05 et 06 modifiés entre `efc0bc5` et `039778c` : hors périmètre, verdicts repris tels quels.
- R3 est établi par lecture du code ; je n'ai pas reproduit le cas avec deux versions du moteur.

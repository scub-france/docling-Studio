# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `a12b744`

Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/01-clean-architecture.md`, 78/100, 0 CRIT / 3 MAJ / 1 MIN).

Fiche : `docs/audit/audits/01-clean-architecture.md`, cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Méthode : lecture de l'arbre de travail, greps de la fiche, `git diff a6fb539 a12b744` (backend), comparaison de `tests/test_architecture.py` avec `git show a6fb539:…`, et un script Python en lecture seule qui compare la signature de chaque méthode des ports nouveaux ou élargis à celle de leur implémentation (13 couples, tous identiques sauf `VectorStore.get_chunks`, écart antérieur). Ni l'application ni les suites n'ont été lancées (résultats fournis : `pytest` 1559 passed / 15 skipped, ruff propre). Même lecture que le re-audit : un item n'est conforme que si toutes les occurrences listées par la base ont disparu.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 11 |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` sans FastAPI, aiosqlite ni lib infra | 3 | Oui | Grep de la fiche vide. `domain/analysis_editing.py:9` ajoute `hashlib` (stdlib, calcul pur). |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Aucun `open(`, `os`, client HTTP ou SQL. `pathlib.Path` n'est importé que sous `TYPE_CHECKING` (`domain/ports.py:14`). |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | 33 classes de port ; nouveaux : `DocumentFileLocator` `:148`, `DocumentVersionRepository` `:285`, `ActiveAnalysisResultReader` `:360`, `VectorStorePool` `:481`, `GraphDriverPool` `:495`, `PdfInspector` `:654`. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import `pydantic`. `EditorSnapshot`/`EditHistoryEntry` ajoutés en dataclasses (`domain/analysis_editing.py:47`, `:120`). |
| 1.2.1 | `services/` sans `fastapi`/`starlette` | 3 | Oui | Grep vide. |
| 1.2.2 | Services → dépôts, jamais de SQL | 3 | Oui | Aucun `SELECT`/`INSERT`/`execute(`/`aiosqlite` dans `services/`. |
| 1.2.3 | Règles métier dans `domain/` | 2 | **Non** | Inchangé (hors périmètre de la remédiation). Seul `hash_result` est passé dans le domaine (`domain/analysis_editing.py:129`). Voir [MAJ] n°1. |
| 1.2.4 | Dépendances injectées, pas de concrétions | 2 | **Non** | Fortement réduit : plus aucune lib PDF, `Sqlite*`, pool ni `infra` dans `services/`, tous les paramètres typés sur des ports. Restent les accès disque directs que la base listait (`os.unlink`, `path.stat`) et leurs voisins. Voir [MAJ] n°2. |
| 1.3.1 | Routes sans `persistence/` | 3 | Oui | Grep vide ; `StoreRepoDep`/`DocumentStoreLinkRepoDep` supprimés de `api/deps.py`. |
| 1.3.2 | camelCase confiné à `api/schemas.py` | 1 | **Non** | Inchangé (laissé volontairement). Voir [MIN]. |
| 1.3.3 | Endpoints qui délèguent toute la logique | 2 | **Non** | 4 occurrences sur 6 résolues (store-links, tailles de page, historique, `ValueError` → 404). Restent le `json.loads` du modèle d'éditeur et la garde du drapeau d'export dans le routeur. Voir [MAJ] n°3. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | `PdfiumInspector` (`infra/pdf_inspector.py:24`) ↔ `PdfInspector`, `PdfPageRasterizer` ↔ `PageRasterizer` (nouveau `fmt`), `OpenSearchClientPool` ↔ `VectorStorePool`, `Neo4jDriverPool` ↔ `GraphDriverPool` : signatures identiques. `infra/pdfium_lock.py` est un utilitaire, pas un adaptateur. |
| 1.4.2 | Config issue de `infra/settings.py` | 2 | Oui | Aucune lecture d'environnement nouvelle ; mêmes défauts de constructeur tolérés qu'en base (`infra/preview_cache.py:16`, `infra/opensearch_pool.py:50`). |

Calcul : poids conformes = 3+3+3+2 + 3+3 + 3 + 3+2 = **25 / 32**. Non conformes : 1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2). `25 / 32 × 100 = 78,1`, soit **78**.

---

## Ecarts constates

### [MAJ] Règles métier hors domaine (inchangé)

- **Localisation** :
  - Split/merge dans le service alors que le domaine les porte : `services/chunk_service.py:274` (`split_chunk`) et `:317` (`merge_chunks`, contiguïté `:330`) ; `domain.chunk_editing` n'est toujours importé que par `tests/test_chunk_editing.py:7`.
  - Citation et lecture budgétée : `services/citation_service.py:204` (`_locate_quote`), `services/navigation_service.py:233` (`_pick`).
  - Flux d'édition : chaîne de hachage `services/analysis_edit_service.py:385-403`, recopiée dans `persistence/analysis_edit_repo.py:164` et `:215` ; contrôle de séquence `services/analysis_edit_service.py:169` et `:221`, recopié dans `persistence/analysis_edit_repo.py:155`.
  - Règles d'édition dans l'adaptateur : racine protégée `infra/docling_editor.py:129`, `:157`, `:224`, `:283`.
  - « Seule une analyse terminée devient active » : `persistence/analysis_repo.py:181`, `services/version_service.py:171`, `services/analysis_edit_service.py:292`.
- **Constat** : hors périmètre de la remédiation, comme annoncé. Petit progrès : l'empreinte d'un résultat (`hash_result`) est désormais une fonction du domaine partagée par l'éditeur et les chunks (`domain/analysis_editing.py:129`, importée en `services/chunk_service.py:23`). La chaîne de hachage du flux reste en double service/dépôt.
- **Regle violee** : item 1.2.3 (poids 2).
- **Remediation** : inchangée. `command_hash`/`stream_hash`/`check_sequence` dans `domain/analysis_editing.py`, utilisés par service et dépôt ; brancher `domain.chunk_editing` dans `ChunkService` ; extraire `locate_quote`/`pick_within_budget`. Effort M.

### [MAJ] Services : plus de concrétions importées, mais le disque reste manipulé en direct

- **Localisation** :
  - `services/document_service.py:7` (`import os`), `:104`, `:121` (`os.unlink` au rejet d'un upload, occurrence listée par la base), `:195-199` (`os.path.realpath`/`exists`/`unlink` à la suppression, occurrence listée par la base), `:223-224` (`os.makedirs`, `open(…, "wb")`) ;
  - `services/document_service.py:170-182` (`resolve_storage_path`, `Path.is_file`), exposé comme implémentation du port `DocumentFileLocator` (`domain/ports.py:148-153`, câblé en `bootstrap/builder.py:177`) ;
  - `services/preview_service.py:61-62` (`path.stat` pour la clé de cache, occurrence listée par la base) ;
  - `services/export_service.py:86` (`Path(doc.storage_path).is_file()`, préexistant, non listé par la base).
- **Constat** : la remédiation a traité tout le reste de l'item, et je l'ai vérifié dans le code, pas seulement dans les messages de commit :
  - plus aucun `pypdfium2`/`pdf2image` dans `services/` ; `DocumentService.generate_preview` et `DocumentService.page_sizes` ont disparu, `PreviewService` dépend de `DocumentFileLocator`, `PageRasterizer`, `PdfInspector`, `PreviewImageCache` (`services/preview_service.py:39-46`) ;
  - `VersionService` reçoit un `DocumentVersionRepository` (`services/version_service.py:85`) ; `StoreBackendResolver` reçoit `GraphDriverPool`/`VectorStorePool` et une fabrique de `GraphWriter` (`services/store_backend_resolver.py:79-86`) ; `StoreService`/`ChunkService` sont typés sur `StoreRepository`/`DocumentStoreLinkRepository` (`services/store_service.py:142-145`, `services/chunk_service.py:146-147`) ;
  - `graph_writer: GraphWriter | None` (`services/analysis_edit_service.py:57`), `active_result_service: ActiveAnalysisResultReader | None` (`services/chunk_service.py:149`, `services/export_service.py:43`) ;
  - aucun import runtime de `infra`/`persistence` dans `services/`, et le test d'architecture le garantit (liste legacy réduite à `persistence/store_repo.py → infra.secrets`).
  Ce qui reste n'est pas un import de concrétion de l'application, mais le système de fichiers utilisé sans port. La base a compté `os.unlink` et `path.stat` dans cet item ; à lecture égale, il ne passe pas. Le port `DocumentFileLocator` déplace d'ailleurs le problème au lieu de le résoudre : il renvoie un `Path` et c'est un service qui l'implémente en interrogeant le disque.
- **Regle violee** : item 1.2.4 (poids 2).
- **Remediation** : un port `DocumentFileStore` (`save(bytes) -> str`, `delete(path)`, `fingerprint(path) -> (size, mtime)`, `exists(path)`, `resolve(path) -> str`) implémenté dans `infra/` ; `DocumentService`, `PreviewService` et `ExportService` l'utilisent ; `DocumentFileLocator` ne renvoie plus de `Path`. Effort S.

### [MAJ] Routeurs : deux résidus sur six

- **Localisation** :
  - `api/analysis_edits.py:54` (`json.loads(snapshot.projection.editor_model_json)` dans `_to_editor_response`, occurrence listée par la base) ;
  - `api/documents.py:123-124` (`if edited: deps.ensure_analysis_editor_enabled(state)` dans le corps de la route d'export, occurrence listée par la base).
- **Constat** : quatre occurrences résolues, vérifiées dans le code :
  - store-links : `DocumentService.find_with_store_links` (`services/document_service.py:144-168`), la route ne fait que mapper (`api/documents.py:92-96`) ;
  - tailles de page : `PreviewService.page_sizes` (`services/preview_service.py:70-77`), appelé en `api/documents.py:183` ;
  - historique : `AnalysisEditService.list_history_entries -> list[EditHistoryEntry]` (`services/analysis_edit_service.py:114-120`), la route ne rejoue plus rien (`api/analysis_edits.py:142-143`) ;
  - import : `ImportDocumentNotFoundError`/`InvalidDoclingDocumentError` (`services/analysis_service.py:59`, `:65`), la route ne lit plus le préfixe du message (`api/analyses.py:85-88`).
  Pour le drapeau d'export, la garde est maintenant la même fonction que celle de toutes les routes de l'éditeur (`api/deps.py:53-56`) : c'est une exposition HTTP (404 quand la fonction est coupée) plutôt qu'une règle métier, et je ne la compterais pas seule. Mais elle n'a pas été déplacée dans `ExportService` comme demandé, et le `json.loads` reste un travail de désérialisation que le service devrait rendre déjà typé. À lecture égale avec la base, l'item ne passe pas.
- **Regle violee** : item 1.3.3 (poids 2).
- **Remediation** : `ProjectedAnalysis` expose le modèle en structure typée (ou `AnalysisEditService` le désérialise) et la route le mappe vers un schéma ; acter dans la fiche que la garde de fonctionnalité relève de `deps` (ou la déplacer dans `ExportService.export_edited`). Effort S.

### [MIN] camelCase hors `api/schemas.py` (inchangé)

- **Localisation** : `api/analysis_edits.py:44-50` (`_serialize_tree`, `elementId`) et `:84-100` (payloads de commande) ; `infra/docling_projector.py:54` (`baseAnalysisId`) ; `domain/analysis_editing.py:171` (`targetSequence`) ; `services/analysis_edit_service.py:237` ; `services/analysis_service.py:44-51` ; `services/version_service.py:52-70` ; `services/chunk_service.py:631` ; `api/schemas.py:200-201` (`model: dict`, `tree: list[dict]`).
- **Constat** : laissé volontairement par la remédiation ; code identique, lignes décalées.
- **Regle violee** : item 1.3.2 (poids 1).
- **Remediation** : inchangée (schémas typés pour l'arbre et le modèle d'éditeur, payload de commande v1 documenté comme format durable). Effort S.

### [INFO] Nouveau : `PdfiumInspector` appelle aussi poppler

- **Localisation** : `infra/pdf_inspector.py:15-16` (`pypdfium2` et `pdf2image`), `:53-61` (`count_pages_in_bytes` via `pdfinfo_from_bytes`).
- **Constat** : l'adaptateur nommé d'après pdfium utilise poppler pour une des trois opérations du port. C'est documenté (`:7`, `:54-55`) et justifié (garder le même comptage qu'avant à l'upload), mais le nom trompe, et le rendu (`infra/page_raster.py`, poppler) et l'inspection (`pdfium`) n'ont plus la même source de vérité sur le nombre de pages : `page_count` (pdfium) sert au découpage en lots, `count_pages_in_bytes` (poppler) à la limite d'upload.
- **Remediation** : renommer en `PdfInspectorAdapter` (ou séparer `count_pages_in_bytes`), ou compter avec pdfium partout après vérification sur les PDF de test.

### [INFO] Nouveau : `AppState` garde trois dépôts que l'API ne lit plus

- **Localisation** : `api/state.py:61-64` (commentaire « Repositories reached directly by the API layer », champs `analysis_repo`, `store_repo`, `document_store_link_repo`), toujours remplis en `bootstrap/builder.py:172-174`.
- **Constat** : plus aucun lecteur dans `api/`, `mcp_adapter/` ou `bootstrap/mcp_mount.py`. Le commentaire est faux et les champs laissent la porte ouverte à un retour des dépôts dans les routes (le test interdit `persistence`, pas les ports de dépôt).
- **Remediation** : supprimer les trois champs et leur affectation.

### [INFO] Test d'architecture : resserré, une docstring périmée, le contrôle des peers toujours partiel

- **Localisation** : `tests/test_architecture.py:66-68` (liste legacy), `:186-196` et `:202` (denylist et candidats), `:109-116` (docstring), `:119-125` (`MODULES`).
- **Constat** : comparé à `a6fb539`, rien n'est relâché : dix entrées legacy supprimées (`store_service`, `chunk_service`, `store_backend_resolver`, `version_service`), `pdf2image` et `pypdfium2` passés de candidats à interdits, liste des candidats vide. Mais la docstring dit encore que « `document_service.py` still counts upload pages with pdf2image » (`:115-116`), ce que la denylist interdit désormais, et parle de « four modules » pour une liste de cinq. Le contrôle service → service reste limité à ces cinq modules alors que plus rien ne justifie l'exception.
- **Remediation** : corriger la docstring ; étendre le contrôle des peers à tout `services/` avec une liste blanche explicite.

### [INFO] Nouveau : port à méthode inutilisée et écart de signature hérité

- **Localisation** : `domain/ports.py:294` (`DocumentVersionRepository.find_latest_for_document`, aucun appelant hors `persistence/document_version_repo.py:72`) ; `domain/ports.py:461` `VectorStore.get_chunks` (`limit: int = 1000`) face à `infra/opensearch_store.py:168` (`limit: int | None = None`).
- **Constat** : le port de version a été calqué sur la classe SQLite plutôt que sur les besoins de `VersionService`. L'écart `get_chunks` précède la remédiation.
- **Remediation** : retirer la méthode du port ; aligner la signature de `get_chunks`.

### [INFO] Erreurs de service : la preview rejoint `ServiceError`, la route garde quatre `except` bruts

- **Localisation** : `services/preview_service.py:17-35` (trois erreurs, toutes `ServiceError`) ; `api/documents.py:166-175` et `:186-190` (`ValueError`, `FileNotFoundError`, `OSError`, `Exception`) ; `services/errors.py:14` (`http_status`).
- **Constat** : l'INFO de base sur les exceptions de preview hors hiérarchie est résolu. Les erreurs d'adaptateur (`FileNotFoundError` de `infra/page_raster.py:30` et `infra/pdf_inspector.py:29`) traversent toujours le service sans traduction. `http_status` dans les services est inchangé.
- **Remediation** : traduire ces erreurs dans `PreviewService` ; à terme, catégorie neutre à la place de `http_status`.

### [INFO] Reportés de la base, inchangés

- `DocumentMerger` jamais câblé : `domain/ports.py:104`, `infra/docling_merger.py:12`.
- MCP sur la dernière parse brute : `services/parse_loader.py:89` (`find_latest_parsed_ids`), `:109`.
- `persistence` importe `infra` : `persistence/store_repo.py:24` (seule entrée legacy restante du test).
- Le domaine lit le schéma JSON Docling : `domain/element_reader.py:86`, `:157`.
- Invariants de sélection active en persistance : `persistence/analysis_repo.py:181`.
- Configuration hors `settings` : `persistence/database.py:22` (`DB_PATH`), `infra/preview_cache.py:16`.
- Frontend `shared` → `features` : `frontend/src/shared/ui/AppSidebar.vue:55-56` (hors barème).

---

## Delta vs re-audit a6fb539

**Score : 78 → 78 (Δ 0).** 9/13 items conformes, comme en base. Les deux MAJ visés (1.2.4, 1.3.3) sont nettement réduits mais pas soldés : chacun garde des occurrences que la base listait explicitement.

| Écart du re-audit (a6fb539) | Statut à `a12b744` | Preuve |
|-----------------------------|--------------------|--------|
| [MAJ] 1.2.3 Règles métier hors domaine | **Inchangé** | Hors périmètre. Seul `hash_result` passe dans le domaine (`domain/analysis_editing.py:129`). |
| [MAJ] 1.2.4 Concrétions dans les services | **Réduit** | Libs PDF, `Sqlite*`, pools et paramètres non typés résolus (voir le MAJ n°2). Restent `os.unlink` `services/document_service.py:121`, `:198`, `open` `:224`, `path.stat` `services/preview_service.py:62`, `Path.is_file` `services/export_service.py:86`. |
| [MAJ] 1.3.3 Routeurs qui orchestrent | **Réduit** | 4/6 résolus. Restent `api/analysis_edits.py:54` (`json.loads`) et `api/documents.py:123-124` (garde d'export). |
| [MIN] 1.3.2 camelCase hors schémas | **Inchangé** | Volontairement laissé. |
| [INFO] Angles morts du test d'architecture | Réduit | Allow-lists resserrées ; docstring périmée et peers partiels restent. |
| [INFO] Exceptions de preview hors `ServiceError` | **Résolu** | `services/preview_service.py:17-35`. |
| [INFO] `DocumentMerger`, MCP, `persistence → infra`, schéma Docling, invariants de sélection, config, frontend | Inchangés | Voir INFO « Reportés ». |

**Nouveaux constats** : [INFO] `PdfiumInspector` qui appelle poppler ; [INFO] dépôts orphelins dans `AppState` ; [INFO] méthode de port inutilisée (`find_latest_for_document`). L'accès disque via `DocumentFileLocator` implémenté par un service est intégré au MAJ 1.2.4.

**Régressions introduites par la remédiation** : aucune qui change un item. J'ai vérifié en particulier :
- aucun import runtime de `infra`/`persistence` dans `services/` ou `api/` ; le grep de la fiche et la liste legacy du test concordent ;
- le test d'architecture n'est relâché nulle part (seulement resserré) ;
- les six ports nouveaux sont étroits et chacun a un appelant dans `services/` (sauf une méthode, en INFO) ; les signatures des adaptateurs correspondent ;
- le read model `DocumentStoreLinkView` (`services/document_service.py:46-52`) suit le patron déjà utilisé par `StoreInfoView` (`services/store_service.py:52`) : pas une violation ;
- le composition root reste le seul endroit qui nomme les classes concrètes (`bootstrap/builder.py:44-45`, `:57`, `:176-181`).

---

## Points positifs

- **Plus aucune lib PDF dans les services**, et le test le garantit (`tests/test_architecture.py:194-195`). Le rendu poppler n'existe plus qu'en un exemplaire, derrière `PageRasterizer` (`infra/page_raster.py:26-41`), avec le format WebP sans perte ajouté au port.
- **Plus aucun dépôt SQLite ni pool infra dans les services** : dix entrées legacy retirées du test d'architecture, une seule reste (`persistence → infra.secrets`).
- **`PreviewService` exemplaire sur ses dépendances** : quatre ports, aucune classe concrète (`services/preview_service.py:39-50`).
- **Verrou pdfium unique** partagé avec Docling (`infra/pdfium_lock.py:12-15`), utilisé par l'inspecteur : un vrai sujet de concurrence réglé dans la bonne couche.
- **Routeurs allégés** : store-links, tailles de page, historique et erreurs d'import sortis de `api/`, avec des types de retour (`EditHistoryEntry`, `DocumentStoreLinkView`) au lieu de `list` nus.

---

## Verdict partiel : GO CONDITIONNEL

78/100, 0 CRITICAL, 3 MAJOR (sous le seuil bloquant de « > 3 MAJ »). La remédiation est réelle et propre, mais elle n'a fait passer aucun item. Les deux plus proches de la conformité coûtent peu :

1. 1.2.4 : port `DocumentFileStore` pour l'écriture, la suppression, la stat et la résolution des fichiers (effort S). Seul, il porte le score à 84 (27/32).
2. 1.3.3 : modèle d'éditeur typé hors du routeur, et décision écrite sur la garde de fonctionnalité dans `deps` (effort S). Avec le point 1 : 91 (29/32).
3. 1.2.3 puis 1.3.2 : inchangés, plan de la base.

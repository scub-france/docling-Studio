# Rapport de re-audit : SOLID

> **Re-audit de la 0.7.4 sur `claude/nifty-turing-fmn3wo` @ `a4d9679` : score 87 → 100, 2 MAJ → 0 MAJ.**

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Type** : re-audit après remédiation
**Référence** : rapport initial `docs/audit/reports/release-0.7.4/06-solid.md` (code `1de1929`, rapports commités en `e6047c2` ; `git diff 1de1929 e6047c2 -- document-parser frontend/src` est vide). 87/100, GO, 0 CRIT, 2 MAJ, 0 MIN, 12 INFO.
**Remédiation examinée** : `git log e6047c2..a4d9679` (100 commits). Commits qui touchent cet audit :
- MAJ-1 : `e68ee5a` (PDF derrière `PageRasterizer`/`PdfInspector`, routeur sur l'instance), `e331670` (`FileStorage`), `cba03bf` (store-links dans le service) ;
- MAJ-2 : `39dcda5` (« declare every repository method services call » : ports complétés, `DocumentVersionRepository`, `VectorStorePool`/`GraphDriverPool`, retypage, test AST, `tests/test_port_conformance.py`) ;
- INFO : `23fb05e` (INFO 11), `2ce5cf1`, `fd4c7e1` et `b181c22` (INFO 12), `cde3c7b` (INFO 9), `e95c75d`, `c925943` et `7ae77c2` (découpage de `ChunkService`, INFO 5).

Fiche : `docs/audit/audits/06-solid.md`. Cible : `document-parser/` (hors `.venv/`, `__pycache__/`), `frontend/src/`.

---

## Score de compliance

| Metrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 13 / 15 (27 / 31 pondérés) | **15 / 15 (31 / 31 pondérés)** |
| Score | 87 / 100 | **100 / 100** |
| Ecarts CRITICAL | 0 | 0 |
| Ecarts MAJOR | 2 | **0** |
| Ecarts MINOR | 0 | 0 |
| Ecarts INFO | 12 | 13 (10 reportées, dont 2 partiellement corrigées ; 2 fermées ; 3 nouvelles) |

Détail du calcul :
- Poids total : 6.1 (7) + 6.2 (5) + 6.3 (7) + 6.4 (4) + 6.5 (8) = **31**.
- Les 15 items sont conformes : 6.1.4 (2) et 6.2.1 (2) le redeviennent.
- `31 / 31 × 100` = **100**.

**Lecture des items : la même qu'au rapport 0.7.4.** La « note de lecture 6.5.1 » de 0.7.4 (lecture stricte : CRIT) n'a plus d'objet. Les deux lectures donnent maintenant le même résultat (voir 6.5.1 plus bas).

### Méthode

- Lecture des sources à `a4d9679`, et commandes de la fiche rejouées. Celle de 6.5.1 est étendue à `from persistence` et à `TYPE_CHECKING`.
- Trois scripts AST, gardés dans le scratchpad et non versionnés :
  - **typage** : type déclaré de chaque paramètre de constructeur des 19 classes de `services/` ;
  - **croisement avec les ports** : chaque appel `self._x.m(...)` et ses arguments nommés, comparés au `Protocol` déclaré pour `_x` ;
  - **adaptateurs** : pour chacun des 26 ports, la classe de `infra/` ou de `persistence/` qui en porte tous les membres.
- Tests lancés : uniquement `pytest tests/test_architecture.py tests/test_port_conformance.py` → **69 passed** (39 en 0.7.4 pour `test_architecture.py` seul).
- Résultats du coordinateur sur `a4d9679`, cités sans les avoir rejoués : backend `ruff` OK, pytest **1673 passed, 19 skipped** ; frontend eslint, vue-tsc et vitest (522 passed) OK.

### Périmètre mesuré

| Surface | 0.7.4 | Re-audit |
|---------|-------|----------|
| Ports `Protocol` (`domain/ports.py`) | 21 (10 `@runtime_checkable`) | 26 (12 `@runtime_checkable`) |
| Classes de la couche `services/` | 17 | 19 (+ `ChunkPushService`, `DocumentTreeService`) |
| Routers REST (`api/`) | 10 | 10 |
| Racines de composition | 2 (`bootstrap/` via `main.py`, et `mcp_stdio.py`) | 2 |
| Stores Pinia de feature | 12 + 1 partagé | 12 + 1 partagé (`shared/breadcrumb/store.ts`) |

---

## Checklist

| # | Item | Poids | Conforme | Statut vs 0.7.4 |
|---|------|-------|----------|-----------------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | ✅ (cf. INFO 5, 6, 9) | = (INFO 5 et 9 partiellement corrigées) |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | ✅ | = (INFO 11 fermée) |
| 6.1.3 | Routes API groupées par ressource | 1 | ✅ | = |
| 6.1.4 | Aucune classe ni aucun module ne cumule des responsabilités hétérogènes | 2 | ✅ | **❌ → ✅ (MAJ-1 corrigé)** |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier le code existant | 2 | ✅ (cf. INFO 13, 15) | **❌ → ✅ (MAJ-2 corrigé)** |
| 6.2.2 | Local/remote extensible via `build_converter()` sans modifier les services | 2 | ✅ | = |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | ✅ | = |
| 6.3.1 | `LocalConverter` et `ServeConverter` interchangeables | 3 | ✅ (cf. INFO 1, 2, 10) | = |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | ✅ (cf. INFO 13) | = |
| 6.3.3 | Pas d'`isinstance()` ni de `type()` pour différencier les implémentations | 2 | ✅ (cf. INFO 14) | = |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | ✅ | = |
| 6.4.2 | Aucun port ne force une implémentation à définir des méthodes inutiles | 2 | ✅ (à la limite, cf. INFO 1, 7) | = (INFO 12 fermée) |
| 6.5.1 | Les services dépendent de ports, pas d'implémentations concrètes | 3 | ✅ en lecture opérationnelle **et** en lecture stricte | = (la réserve de lecture tombe) |
| 6.5.2 | Injection au composition root | 2 | ✅ (cf. INFO 4) | = |
| 6.5.3 | Pas d'instanciation directe d'adaptateurs dans les services | 3 | ✅ | = |

---

## Vérification des principes

### SRP (6.1)

- **6.1.1 conforme.**
  - `ChunkService` est découpé :
    - l'édition reste dans `services/chunk_service.py`, qui passe de 1 019 à 311 lignes ;
    - le push vers les stores va dans `services/chunk_push_service.py` (339 lignes) ;
    - l'arbre va dans `services/document_tree_service.py` (60 lignes).
  - Les autres services n'ont pas changé de périmètre. `AnalysisService` passe de 589 à 619 lignes : finalisation découpée en étapes (`:466-583`), comptage de pages par port.
  - Dette restante : INFO 5, 6 et 9.
- **6.1.2 conforme.**
  - Un `defineStore` par fichier `frontend/src/features/*/store.ts`, soit 12, plus `shared/breadcrumb/store.ts`.
  - Le store `document` ne porte plus l'action `pushToStore` de la feature `chunks`, et ne l'importe plus : INFO 11 fermée.
- **6.1.3 conforme.** Les mêmes 10 routers : `analyses`, `config`, `document_chunks`, `document_versions`, `documents`, `graph`, `ingestion`, `mcp`, `reasoning`, `stores` (`main.py:61`, `:106-121`). `api/errors.py` n'est pas un router : c'est le gestionnaire d'erreurs.
- **6.1.4 conforme (était MAJ-1).** `DocumentService` ne lit ni ne rend plus aucun PDF lui-même, et ne touche plus le disque. Détail dans « Statut des écarts ».

### OCP (6.2)

- **6.2.1 conforme (était MAJ-2).** Les 12 méthodes et l'argument nommé manquants sont déclarés, `DocumentVersionRepository` existe, et le croisement AST ne trouve **aucun** appel hors contrat. Détail dans « Statut des écarts ».
- **6.2.2 conforme.**
  - La sélection local/remote est centralisée dans `build_converter()` (`bootstrap/factories.py:45-59`).
  - `AnalysisService` ne lit que la capacité `supports_page_batching` (`services/analysis_service.py:443`) et délègue la fusion à `merge_batches` (`:335`).
- **6.2.3 conforme.** `export_document` (`api/documents.py:118-146`) ne reçoit que l'enum `ExportFormat`. La chaîne `if format is …` est dans le service (`services/export_service.py:63`, `:72`).

### LSP (6.3)

- **6.3.1 conforme (poids 3).**
  - `LocalConverter` (`infra/local_converter.py:192`) et `ServeConverter` (`infra/serve_converter.py:71`) exposent toujours `convert`, `supports_page_batching` et `merge_batches`, et retournent un `ConversionResult`.
  - Nouveau depuis 0.7.4 : le convertisseur local n'accepte plus que le PDF (`allowed_formats=[InputFormat.PDF]`, `infra/local_converter.py:76`, `8aaace0`), alors que Docling Serve n'a pas cette restriction. La divergence n'est pas observable : le seul chemin d'entrée refuse tout fichier qui ne commence pas par `%PDF` (`services/document_service.py:133-134`).
  - INFO 1, 2 et 10 inchangées.
- **6.3.2 conforme.**
  - `PdfiumInspector` respecte le contrat de son port : `FileNotFoundError` si le fichier manque, une autre exception s'il est illisible (`domain/ports.py:674-681`).
  - `LocalFileStorage.delete` refuse et journalise un chemin hors stockage sans lever, et lève `OSError` sur un échec réel (`infra/file_storage.py:51-59`), comme le dit le port (`domain/ports.py:720-725`).
  - `DoclingImportTooLargeError` hérite de `ValueError` (`infra/docling_importer.py:18`) : il reste dans le contrat « document invalide → 400 » (`api/analyses.py:139-145`).
  - `OllamaProbe.probe` ramène toujours tout échec à `reachable=False`, y compris une cible refusée par le garde SSRF (`infra/llm/ollama_probe.py:29-57`).
  - Une réserve : le service s'appuie sur une exception que le port `PageRasterizer` ne déclare pas (INFO 13).
- **6.3.3 conforme.** Le grep de la fiche sur `services/` trouve 4 `isinstance`, tous sur des types primitifs de payload : `chunk_service.py:101`, `store_service.py:136`, `:140`, `mcp_config_service.py:71`. S'y ajoute un `type(exc)` (`services/chunk_errors.py:57`), qui associe une exception du domaine à une erreur de service sans distinguer d'implémentations (INFO 14).

### ISP (6.4)

- **6.4.1 conforme.**
  - `DocumentConverter` (`domain/ports.py:57`), `DocumentChunker` (`:94`) et `DoclingDocumentImporter` (`:88`) restent séparés.
  - La lecture PDF est découpée en trois ports étroits, que `DocumentService` reçoit séparément : rendu `PageRasterizer` (`:551`), texte `PageTextReader` (`:577`) et géométrie `PdfInspector` (`:674`). C'est l'option recommandée en 0.7.4, plutôt qu'un `PageTextReader` élargi.
- **6.4.2 conforme, à la limite.**
  - Les nouveaux ports sont minces : `FileStorage` a 4 méthodes, toutes consommées (`save`/`delete`/`resolve` par `DocumentService`, `exists` par `ExportService`) ; `PdfInspector` en a 2, consommées ; les pools ont une méthode chacun. `DocumentVersionRepository` n'a pas repris `find_latest_for_document`, qu'aucun service ne consomme (`domain/ports.py:286-296`).
  - `LLMProvider` est réduit à ce que le runner consomme (`host`, `default_model_id`, `domain/ports.py:487-502`) : INFO 12 fermée.
  - Restent INFO 1 (`merge_batches` imposé à Serve) et INFO 7 (ports larges pour des clients étroits).

### DIP (6.5)

- **6.5.1 conforme (poids 3), en lecture opérationnelle et en lecture stricte.**
  - `grep -rn "from infra\.\|import infra\.\|from persistence\|import persistence" services/` est vide, `TYPE_CHECKING` compris. En 0.7.4, ce grep trouvait 3 imports `infra` et 7 imports `persistence`, tous sous `TYPE_CHECKING`.
  - Les 19 constructeurs sont annotés sur des ports, des services pairs, des configs ou des `Callable` (script AST).
  - `VersionService` est typé sur `DocumentVersionRepository` (`services/version_service.py:66-71`).
  - `TestServicesReachAdaptersThroughPortsOnly` (`tests/test_architecture.py:169-187`) interdit `api`, `bootstrap`, `infra` et `persistence` dans `services/`, `TYPE_CHECKING` compris. J'ai vérifié que le scanner mord en le rejouant sur une copie de `services/` dans le scratchpad, avec un import ajouté.
  - La lecture stricte de 0.7.4 portait sur les adaptateurs (`Sqlite*`, `infra.*`). Elle est désormais satisfaite : la décision de lecture laissée au mainteneur n'a plus d'enjeu pour cet item.
  - Une lecture encore plus large, qui compterait comme « concrètes » les dépendances entre services applicatifs, n'a jamais été appliquée. Ce sont par exemple `ChunkPushService` → `IngestionService`/`StoreBackendResolver` (`chunk_push_service.py:65`, `:68`) et `NavigationService` → `ParseLoader`/`CitationService`. Ces injections sont recensées par `PEERS` (`tests/test_architecture.py:275-292`). Cette lecture n'est pas retenue.
- **6.5.2 conforme.**
  - Les adaptateurs ne sont instanciés que dans `bootstrap/builder.py`, `bootstrap/factories.py` et `mcp_stdio.py` (grep des constructeurs `Sqlite*Repository(`, `LocalFileStorage(`, `PdfiumInspector(`, `PdfPageRasterizer(`, etc. hors `infra/` et `tests/`).
  - Nouveaux câblages : `build_file_storage` (`bootstrap/factories.py:213-217`), `_build_pdf_inspector` (`:318-321`), injection dans `build_document_service` (`:220-235`) et `build_analysis_service` (`:193-210`), politique SSRF injectée en `Callable` (`bootstrap/builder.py:162-165`).
  - Seconde racine : `mcp_stdio.py:51-70`, qui réutilise les factories.
- **6.5.3 conforme (poids 3).** Le grep `LocalConverter|ServeConverter|LocalChunker` sur `services/` ne renvoie rien. `pdfium.PdfDocument`, compté en 0.7.4 sous MAJ-1, a quitté `services/`.

---

## Statut des écarts du rapport 0.7.4

### [MAJ] MAJ-1 (6.1.4) — `DocumentService` cumulait parsing/rendu PDF et persistence → **corrigé**

| Élément 0.7.4 | Statut | Preuve dans le code actuel |
|---------------|--------|----------------------------|
| `import pypdfium2` et `pdf2image` au niveau du module (`document_service.py:14-15`) | **corrigé** | Imports de `services/document_service.py:12-31` : `asyncio`, `logging`, `dataclasses`, `typing`, `domain.*`. Aucun `os`, `pathlib`, `pdfium` ni `pdf2image`. |
| `generate_preview` qui duplique `PageRasterizer` | **corrigé** | `render_preview` (`:219-241`) appelle `self._rasterizer.render_page` sur le chemin résolu (`:261-263`). Plus de méthode statique. |
| `page_sizes` par pdfium sans verrou | **corrigé** | `self._pdf.page_sizes` (`:265-266`) ; l'adaptateur prend le verrou pdfium (`infra/pdf_inspector.py:33`). |
| `_persist_and_count` (`open(…, "wb")`), `_count_pages` par poppler, `os.realpath`/`os.unlink` | **corrigé** | `_store_and_count` (`:268-276`) appelle `FileStorage.save` puis `PdfInspector.page_count` (`:278-284`) ; la suppression passe par `FileStorage.delete` (`:209`). Garde-fou de chemin dans `infra/file_storage.py:51-59`. |
| Le routeur appelle `DocumentService.generate_preview`/`page_sizes` sur la classe et lit le fichier | **corrigé** | `api/documents.py:158` et `:187` appellent l'instance injectée ; aucune lecture de fichier dans `api/`. |
| Secondaire : `analysis_service.py:17` (`pypdfium2`), `_count_pdf_pages` sur la boucle | **corrigé** | `PdfInspector` injecté (`services/analysis_service.py:82`, `:99`), appel dans un thread (`:452-464`). |
| Garde-fou (remédiation point 4) | **fait en grande partie** | `pdf2image` et `pypdfium2` sont dans `_SERVICES_FORBIDDEN_EXTERNALS` (`tests/test_architecture.py:353-358`), et la liste des candidats est vide (`:365`). Non fait : l'extension de `TestDocumentAgentServicesAreFrameworkFree.MODULES` (`:262-268`) à `document_service`/`analysis_service`. `PIL` n'est donc interdit qu'aux 5 modules document-agent (INFO 15). |

`DocumentService` garde trois rôles d'orchestration du document : politique d'upload (taille, signature `%PDF`, nombre de pages, `:121-158`), CRUD par le dépôt, et lectures du PDF déléguées aux ports. S'y ajoute la jointure des store-links (`:168-195`), une lecture de la zone dépréciée. Aucune de ces responsabilités n'est hétérogène au sens de l'item : il n'y a plus ni parsing ni I/O.

### [MAJ] MAJ-2 (6.2.1) — Contrats de ports incomplets ou absents → **corrigé**

**A. Les 12 méthodes et l'argument nommé sont déclarés.**

| Port | Méthode | Déclaration actuelle (`domain/ports.py`) |
|------|---------|------------------------------------------|
| `AnalysisRepository` | `find_by_document` | `:312` |
| `ChunkPushRepository` | `count_for_document`, `find_for_document` | `:270`, `:260` |
| `VectorStore` | `search_fulltext` | `:388` |
| `StoreRepository` | `insert(…, *, password=)` | `:142` |
| `StoreRepository` | `find_by_name`, `update`, `clear_default_except`, `delete`, `get_connection_password`, `set_connection_password` | `:150`, `:154`, `:158`, `:162`, `:164`, `:168` |
| `DocumentStoreLinkRepository` | `count_by_store` | `:184` |
| `DocumentRepository` | `find_by_ids` | `:118` |

**B. Port créé** : `DocumentVersionRepository` (`domain/ports.py:286-296`), avec `insert`, `find_by_id` et `list_for_document`. Cette dernière remplace `find_for_document` et renvoie des `DocumentVersionEntry` sans le corps du snapshot (`:273-283`).

**C. Retypage** :

| Service | 0.7.4 | Re-audit |
|---------|-------|----------|
| `StoreService` | `Sqlite*` ×3 | `StoreRepository`, `DocumentStoreLinkRepository`, `DocumentRepository` (`services/store_service.py:155`) |
| `ChunkService` | `SqliteStoreRepository`, `SqliteDocumentStoreLinkRepository` | le push est parti dans `ChunkPushService`, typé sur `StoreRepository`/`DocumentStoreLinkRepository` (`services/chunk_push_service.py:60-76`) ; `ChunkService` ne prend plus de dépôt de stores (`services/chunk_service.py:61`) |
| `StoreBackendResolver` | `SqliteStoreRepository`, `Neo4jDriverPool`, `OpenSearchClientPool` | `StoreRepository`, `GraphDriverPool`, `VectorStorePool` (`services/store_backend_resolver.py:80-90` ; ports `domain/ports.py:420`, `:436`). C'est une variante de la remédiation 4 de 0.7.4, qui proposait des fabriques `Callable`. |
| `IngestionTargets.vector_store` | `OpenSearchStore` | `VectorStore` (`services/store_backend_resolver.py:63`) |
| `VersionService` | `SqliteDocumentVersionRepository` | `DocumentVersionRepository` (`services/version_service.py:66-71`) |

**Vérifications** :
- Croisement AST de tous les appels `self._x.m(...)` des 19 classes de service avec le `Protocol` déclaré : **0 méthode et 0 argument nommé hors contrat**. L'inventaire 0.7.4 relevait 13 écarts (12 méthodes, 1 argument nommé) sur 16 sites d'appel.
- Les appels indirects relevés à la main sont tous dans leur port : `targets.vector_store.ping()` et `targets.graph_writer.ping()` (`store_service.py:394`, `:399`), `self._parses.documents.find_all` (`navigation_service.py:82`).
- `tests/test_port_conformance.py:29-83` vérifie, pour 12 couples port/adaptateur, que l'adaptateur porte chaque membre du port avec les mêmes paramètres (nom, nature, présence d'une valeur par défaut). Seules des options nommées avec valeur par défaut peuvent s'y ajouter.
- Script « adaptateurs » : chacun des 26 ports a au moins une classe de `infra/` ou de `persistence/` qui en porte tous les membres. `LocalConverter` n'a pas été importé, car `docling` est absent du `.venv` ; `ServeConverter` couvre `DocumentConverter`.

La partie non dépréciée signalée en 0.7.4 (`VersionService`, `AnalysisRepository.find_by_document`) est corrigée au même titre que la zone stores et ingestion.

### INFO du rapport 0.7.4

| INFO 0.7.4 | Statut | Preuve |
|------------|--------|--------|
| 1 `merge_batches` imposé à `ServeConverter` (code mort) | **inchangé** | `domain/ports.py:81-85` ; `infra/serve_converter.py:95-98` |
| 2 `supports_page_batching` : `@property` au port, attribut de classe dans les adaptateurs | **inchangé** | `domain/ports.py:72-79` ; `infra/local_converter.py:197`, `infra/serve_converter.py:77` |
| 3 `ServeConverter.health_check()` orphelin | **inchangé** | `infra/serve_converter.py:189` ; grep hors `tests/` : seule la définition |
| 4 Libellés de fiche périmés, deux racines | **inchangé** | La fiche cite toujours `_build_converter()` et `main.py`, et sa commande 6.5.1 ne cherche que `from infra`. Le nom réel est `build_converter()` (`bootstrap/factories.py:45`). Le test AST couvre désormais ce que la commande ratait. |
| 5 Dette SRP `AnalysisService`/`ChunkService` | **partiellement corrigé** | `ChunkService` découpé en trois (voir 6.1.1). Reste l'édition legacy du blob dans `AnalysisService` : `rechunk` `:210`, `update_chunk_text` `:234`, `delete_chunk` `:256`. |
| 6 `ParseLoader` expose ses dépôts | **inchangé** | `services/parse_loader.py:60-68` ; consommateurs `navigation_service.py:82`, `:87`, `citation_service.py:207` |
| 7 `AnalysisRepository` : un port large pour la surface MCP | **inchangé, port élargi** | 15 méthodes (`domain/ports.py:299-338`) avec `find_by_document`, comme prévu en 0.7.4 ; `ParseLoader` n'en appelle que 3 (`parse_loader.py:83`, `:89`, `:107`). Même motif, zone dépréciée : `StoreBackendResolver` est typé sur `StoreRepository` (11 méthodes) et n'appelle que `get_connection_password` (`store_backend_resolver.py:130`, `:145`). |
| 8 `PageRasterizer.crop` détourné en transcodeur | **inchangé** | `services/citation_image_service.py:91` |
| 9 Découpage SRP de l'adaptateur MCP | **partiellement corrigé** | `sources_view.py` passe de 369 à 105 lignes (enregistrement seul, `:48-95`) ; contrat dans `mcp_adapter/sources_wire.py`, mapping dans `sources_mapping.py`, texte dans `sources_text.py` (`cde3c7b`). Restent mixtes : `mcp_adapter/apps.py` (contrat `CitationView` `:73-74` + enregistrement `:146`) et `bootstrap/mcp_mount.py` (mapping `:124-146` + passerelle ASGI `:147-183`). |
| 10 `PageElement.level = 0` côté Docling Serve | **inchangé** | `infra/serve_converter.py:377` contre `infra/docling_pages.py:107` |
| 11 `pushToStore` mort et dupliqué dans le store `document` | **corrigé** | `grep pushToStore\|pushChunksToStore frontend/src/features/document/store.ts` est vide (`23fb05e`). Le cycle d'imports entre les barrels `document` et `chunks` disparaît : seul `chunks/store.ts:5` importe encore `document`. |
| 12 `LLMProvider` : `health_check` sans client, substitution refusée | **corrigé** | Le port ne porte plus que `host` et `default_model_id` (`domain/ports.py:487-502`), et son docstring explique l'absence de type. `infra/docling_agent_reasoning.py` ne lève plus `NotImplementedError` sur le type de provider (grep vide). |

---

## Ecarts constates

Aucun écart CRITICAL, MAJOR ni MINOR.

Les INFO reportées 1 à 10 sont décrites dans le tableau ci-dessus. Leur remédiation est celle du rapport 0.7.4, sauf pour INFO 4 : la fiche `docs/audit/audits/06-solid.md` est hors du périmètre d'écriture de ce re-audit. Les trois INFO suivantes sont nouvelles.

### [INFO] INFO 13 — `DocumentService` s'appuie sur un `ValueError` que le port `PageRasterizer` ne déclare pas (nouveau, introduit par la remédiation)

- **Origine** : `e68ee5a`.
- **Localisation** :
  - `services/document_service.py:236-237` : `except ValueError` → `PageNotFoundError`, donc 404 dans `api/documents.py:161-162` ;
  - port `domain/ports.py:560-562` : `render_page` ne dit rien des exceptions ;
  - contrat écrit seulement sur l'adaptateur : `infra/page_raster.py:25-29` et `:33-37`.
- **Constat** :
  - Les deux autres ports introduits par la remédiation déclarent leurs exceptions : `PdfInspector` (`domain/ports.py:674-681`) et `FileStorage` (`:720-725`). `PageRasterizer` ne le fait pas, alors que le service distingue maintenant les cas d'après elles.
  - Un adaptateur écrit fidèlement contre le port, qui lèverait par exemple `IndexError` pour une page absente, ferait passer `/preview` d'un 404 à un 422 (`DocumentFileError`, `:240-241`). Le cas ne se produit que lorsque le nombre de pages du document est inconnu, puisque la plage est vérifiée avant (`:230-231`).
  - Aucun plantage, d'où le classement en observation. L'item 6.3.2 reste conforme : l'adaptateur actuel lève exactement ce que le service attend.
- **Regle** : 6.3.2 / 6.2.1 (contrat du port), observation.
- **Remediation** : reporter dans le docstring de `PageRasterizer.render_page` la phrase de l'adaptateur (« raises `FileNotFoundError`… `ValueError` when the document has no such page »). **Effort XS, risque nul.**

### [INFO] INFO 14 — `refusals_as_service_errors` associe les refus du domaine par type exact (nouveau, introduit par la remédiation)

- **Origine** : `a98be58`, `6134b6b`.
- **Localisation** : `services/chunk_errors.py:44-48` (table `_REFUSALS`) et `:57` (`_REFUSALS[type(exc)]`). Les classes sont en `domain/chunk_editing.py:39-53`.
- **Constat** :
  - La traduction capture toute la famille `ChunkEditingError` (`:56`), mais cherche la classe exacte dans la table.
  - Une nouvelle sous-classe ajoutée au domaine, ou un `raise ChunkEditingError(...)` direct, lèverait `KeyError` pendant le traitement de l'exception, donc une 500 au message trompeur. Il faudrait modifier le service pour étendre le domaine (OCP).
  - Aujourd'hui la table est exhaustive : les cinq `raise` de `domain/chunk_editing.py` (`:62`, `:75`, `:109`, `:113`, `:118`) visent les trois sous-classes mappées.
  - Ce n'est pas un dispatch entre implémentations de port : 6.3.3 reste conforme.
- **Regle** : 6.2.1 / 6.3.3, observation.
- **Remediation** : parcourir `type(exc).__mro__` jusqu'à une classe connue, avec `ChunkValidationError` par défaut. **Effort XS.**

### [INFO] INFO 15 — Garde-fous partiels : le sens « service → port » n'est vérifié par aucun outil (nouveau relevé)

- **Localisation** :
  - `tests/test_port_conformance.py:29-42` : 12 couples ;
  - `tests/test_architecture.py:169-187` (imports) et `:345-359` (bibliothèques) ;
  - `document-parser/pyproject.toml` : aucune configuration `mypy` ni `pyright`.
- **Constat** :
  1. **Sens « service → port » non vérifié.** MAJ-2 portait sur ce sens : des services qui appelaient des méthodes absentes de leur port. La remédiation verrouille les imports (test AST) et le sens « port → adaptateur » (`test_port_conformance`). Mais un appel `self._stores.foo()` sur un service typé `StoreRepository` passerait tous les tests tant que l'adaptateur SQLite possède `foo`. C'est exactement le scénario de 0.7.4. Aujourd'hui, il n'y en a aucun : c'est mon script AST qui le constate, pas un test.
  2. **`PIL` absent de la liste globale.** `PIL` n'est pas dans `_SERVICES_FORBIDDEN_EXTERNALS` : seuls les 5 modules document-agent l'interdisent (`tests/test_architecture.py:294-305`).
  3. **Couverture partielle de la conformité.** `test_port_conformance` couvre 12 des 26 ports. Pour `PdfInspector` (`tests/test_pdf_inspector.py:31`), `FileStorage` et les autres ports `@runtime_checkable`, seul un `isinstance` est vérifié, c'est-à-dire la présence des noms, pas les signatures.
- **Regle** : 6.2.1 / 6.5.1 (pérennité), observation.
- **Remediation** :
  - un `mypy` (ou `pyright`) ciblé sur `domain/` et `services/` en CI, puisque les services sont maintenant annotés sur des ports ; ou, à défaut, versionner le croisement AST comme test ;
  - ajouter `PIL` à `_SERVICES_FORBIDDEN_EXTERNALS` ;
  - étendre `PAIRS` aux ports restants.
  - **Effort S.**

---

## Delta vs 0.7.4

**Score** : 87 → **100** (+13). **Écarts** : 0/2/0/12 → **0/0/0/13**.

| Écart 0.7.4 | Statut au re-audit |
|-------------|--------------------|
| [MAJ] MAJ-1 `DocumentService` parsing + persistence (6.1.4) | **Corrigé** : PDF par `PageRasterizer`/`PdfInspector`, disque par `FileStorage`, routeur sur l'instance, bibliothèques PDF interdites dans `services/` |
| [MAJ] MAJ-2 ports incomplets ou absents (6.2.1) | **Corrigé** : 12 méthodes + `password=` déclarés, `DocumentVersionRepository`, 5 constructeurs retypés, test AST `TYPE_CHECKING` compris, test de conformité port → adaptateur |
| [INFO] 1, 2, 3, 4, 6, 8, 10 | Inchangées |
| [INFO] 5 Dette SRP | Partiellement corrigée (`ChunkService` découpé ; édition legacy restante dans `AnalysisService`) |
| [INFO] 7 `AnalysisRepository` large | Inchangée (15 méthodes, comme anticipé) |
| [INFO] 9 SRP de l'adaptateur MCP | Partiellement corrigée (`sources_view` découpé ; `apps.py`, `mcp_mount.py` restent) |
| [INFO] 11 `pushToStore` | **Corrigée** |
| [INFO] 12 `LLMProvider` | **Corrigée** |

| Nouvel écart | Origine |
|--------------|---------|
| [INFO] 13 exception de `PageRasterizer` non déclarée au port | Introduit par la remédiation (`e68ee5a`) |
| [INFO] 14 table `_REFUSALS` par type exact | Introduit par la remédiation (`a98be58`, `6134b6b`) |
| [INFO] 15 garde-fous partiels sur le sens service → port | Relevé ; prolonge le constat « aucun garde-fou ne l'attrape » de MAJ-2 en 0.7.4 |

**Régressions** : aucune sur un item du barème. Les deux INFO introduites par la remédiation (13, 14) sont des fragilités de contrat, sans effet observable aujourd'hui.

---

## Ce qui reste pour 100

Le score est déjà à 100. Pour que ce score tienne au prochain gate, sans gain de points :

| Action | INFO | Effort | Risque |
|--------|------|--------|--------|
| `mypy`/`pyright` sur `domain/` + `services/` en CI, ou croisement AST versionné ; `PIL` dans la liste interdite ; `PAIRS` étendu | 15 | S | Faible (faux positifs à l'introduction) |
| Exceptions de `render_page` déclarées dans le port | 13 | XS | Nul |
| `_REFUSALS` par MRO | 14 | XS | Nul |
| Mise à jour de la fiche 06 (`build_converter()`, `bootstrap/`, grep `from persistence`) | 4 | XS | Nul |
| Retrait de l'édition legacy du blob `chunks_json` et de la zone stores/ingestion (0.8.0) | 5, 7 | M | Modéré (contrat HTTP legacy) |

---

## Points positifs

- **Les deux MAJ sont fermés, et la question de lecture stricte de 6.5.1 disparaît.** Aucun import `infra`/`persistence` dans `services/`, même sous `TYPE_CHECKING`, et un test qui l'interdit et qui mord.
- **Les contrats déclarés sont les contrats réels.** Aucun appel hors port, une vérification de conformité port → adaptateur qui compare les signatures, et des ports nouveaux qui documentent leurs exceptions (`PdfInspector`, `FileStorage`).
- **ISP mieux respecté qu'en 0.7.4.** La géométrie PDF a son propre port au lieu d'élargir `PageTextReader`, `LLMProvider` est réduit à ce que son client consomme, et `DocumentVersionRepository` ne reprend pas la méthode sans consommateur.
- **SRP** : `ChunkService` éclaté en trois services typés sur des ports ; `sources_view` découpé comme les outils du cœur MCP.
- **Composition toujours centralisée** : les nouveaux adaptateurs (`LocalFileStorage`, `PdfiumInspector`) ne sont construits que dans `bootstrap/`.
- **Frontend** : un store par feature, sans action étrangère ni cycle d'imports entre `document` et `chunks`.

---

## Verdict partiel : GO

- Score **100/100**, **0 CRITICAL**, **0 MAJOR**, 0 MINOR, 13 INFO.
- Les deux MAJ du rapport 0.7.4 sont corrigés et vérifiés dans le code (6.1.4, 6.2.1).
- La lecture stricte de 6.5.1, laissée au mainteneur en 0.7.4, donne désormais le même résultat que la lecture opérationnelle : il n'y a plus de risque de reclassement en CRIT.
- Pour que le score tienne au prochain gate, le point à traiter en priorité est l'INFO 15 : vérifier par un outil que les services n'appellent que ce que leurs ports déclarent.

---

## Addendum — vérification post-correctifs (HEAD 3f1d1cb, 2026-11-03)

Vérification dans le code de la passe `a4d9679..3f1d1cb` (commits `ad8e2ae` et `618a39a` pour cet audit). Gates du coordinateur sur `3f1d1cb` : ruff et format OK, pytest **1723 passed, 19 skipped**, dont `tests/test_architecture.py`, `tests/test_port_conformance.py` et le nouveau `tests/test_chunk_errors.py` ; vue-tsc OK, vitest 522 passed. Pas de run CI.

### Écarts visés

| Écart | Statut | Preuve (`3f1d1cb`) |
|-------|--------|--------------------|
| INFO 13 — `DocumentService` s'appuie sur un `ValueError` que le port `PageRasterizer` ne déclare pas | **Fermée** | `domain/ports.py:560-567` : `render_page` déclare `FileNotFoundError` (rien n'est stocké), `ValueError` (page absente), et toute autre exception signifie un fichier illisible. C'est exactement la distinction que fait le service (`services/document_service.py:245-246`, `except ValueError` → `PageNotFoundError`). Le port s'aligne ainsi sur `PdfInspector` et `FileStorage`. |
| INFO 14 — `refusals_as_service_errors` associe les refus par type exact | **Fermée** | `services/chunk_errors.py:51-58` (`_refusal_error`) parcourt `type(exc).__mro__` et retombe sur `ChunkValidationError` (400) ; il est appelé par `refusals_as_service_errors` (`:61-67`). Une sous-classe nouvelle, ou un `ChunkEditingError` levé tel quel, donne désormais un 400 et non plus un `KeyError` → 500. Étendre le domaine ne demande plus de modifier le service (OCP). Test : `tests/test_chunk_errors.py:52` (base levée telle quelle). |

### Autres changements de la passe, relus sous l'angle SOLID

- `PageOutOfRangeError`, `PageNotFoundError`, `DocumentFileError` et `ExportNotFoundError` dérivent de `ServiceError` (`document_service.py:41`, `:50`, `:59` ; `export_service.py:115`). Le routeur documents ne connaît plus ces classes : le handler unique les traduit.
- `StoreBackendResolver` reçoit la garde SSRF sous forme de callable injecté (`target_is_blocked`, `services/store_backend_resolver.py:138`, câblé en `bootstrap/factories.py:194`). `services/` n'importe toujours pas `infra` (6.5.1 et 6.5.3 tenus).
- `chunk_push_service.py:20` importe `_new_id` et `_utcnow` de `domain.models`. La dépendance va vers le domaine, donc dans le bon sens ; l'emploi de noms privés est relevé à l'audit 05.

**Régressions** : aucune sur un item du barème.

### Score recalculé

Une seule lecture au re-audit, inchangée : 15 / 15 items, 31 / 31 → **100 / 100**.

| Métrique | Re-audit (`a4d9679`) | Post-correctifs (`3f1d1cb`) |
|----------|----------------------|-----------------------------|
| Score | 100 / 100 | **100 / 100** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 0 | 0 |
| Écarts MINOR | 0 | 0 |
| Écarts INFO | 13 | **11** (INFO 13 et 14 fermées) |

### Verdict partiel après correctifs : GO

Score **100 / 100**, 0 CRITICAL, 0 MAJOR, 0 MINOR, 11 INFO. Pour que le score tienne, la priorité reste l'INFO 15 : faire vérifier par un outil (mypy ou pyright ciblé, ou le croisement AST versionné en test) que les services n'appellent que ce que leurs ports déclarent.

# Rapport d'audit : SOLID

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag `v0.7.3` + 2 commits README)
**Baseline** : `docs/audit/reports/release-0.7.3/06-solid.md` (87/100, 0/2/0/10, GO), audité sur `02adc68`. L'audit 06 n'a pas été rejoué au re-audit 0.7.3 (`release-0.7.3-reaudit/summary.md` : « 87 (inchangé) »).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 15 (27 / 31 pondérés) |
| Score | 87 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 12 |

Détail du calcul :
- Poids conformes : 6.1.1 (2) + 6.1.2 (2) + 6.1.3 (1) + 6.2.2 (2) + 6.2.3 (1) + 6.3.1 (3) + 6.3.2 (2) + 6.3.3 (2) + 6.4.1 (2) + 6.4.2 (2) + 6.5.1 (3) + 6.5.2 (2) + 6.5.3 (3) = **27**.
- Poids total : 6.1 (7) + 6.2 (5) + 6.3 (7) + 6.4 (4) + 6.5 (8) = **31**.
- Items non conformes : 6.1.4 (2) et 6.2.1 (2).
- `27 / 31 * 100 = 87,1` → **87**.

**Delta vs 0.7.3** : **0 point** (87 → 87). Les deux MAJ sont toujours présents, sans changement. Ils ont été revérifiés sur le code actuel, et l'inventaire du MAJ-2 est maintenant exhaustif : 16 sites d'appel au lieu de 13 cités. Les 2 nouvelles INFO sont des écarts **préexistants qui n'avaient pas été relevés** ; ils étaient déjà présents en v0.7.0.

### Ce qui a changé dans le périmètre depuis `02adc68`

`git diff --stat 02adc68 HEAD -- document-parser frontend/src` donne la liste des changements de code :
- `services/analysis_service.py` (+3 lignes) : l'import Docling est désormais exécuté dans un thread (`asyncio.to_thread`, `:180`, commit d1a131f). Les lignes suivantes sont décalées de +3.
- `infra/settings.py` : commentaire seulement.
- Frontend :
  - `ConfigSource` déplacé dans `shared/types.ts:1-5` (8465931) ;
  - libellés `i18n.ts` ;
  - commentaire dans `McpConfigSection.vue`.

`domain/`, `persistence/`, `bootstrap/`, `mcp_adapter/`, `api/` et les autres fichiers de `services/` sont **identiques** à `02adc68`. Aucun de ces changements ne modifie le verdict d'un item.

### Périmètre mesuré

| Surface | 0.7.3 | 0.7.4 |
|---------|-------|-------|
| Ports `Protocol` (`domain/ports.py`) | 21 | 21 (dont 10 `@runtime_checkable`) |
| Classes de la couche `services/` | 17 | 17 |
| Routers REST (`api/`) | 10 | 10 |
| Racines de composition | 2 (`bootstrap/` via `main.py` + `mcp_stdio.py`) | 2 |
| Stores Pinia de feature | 12 + 1 partagé | 12 + 1 partagé (`shared/breadcrumb`) |

---

## Checklist

| # | Item | Poids | Conforme | Statut vs 0.7.3 |
|---|------|-------|----------|-----------------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | ✅ (cf. INFO 5, 6, 9) | = |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | ✅ (cf. INFO 11) | = |
| 6.1.3 | Routes API groupées par ressource | 1 | ✅ | = |
| 6.1.4 | Aucune classe ni aucun module ne cumule des responsabilités hétérogènes (parsing ET persistence) | 2 | ❌ MAJ-1 | = (toujours non conforme) |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier le code existant | 2 | ❌ MAJ-2 | = (toujours non conforme) |
| 6.2.2 | Local/remote extensible via `build_converter()` sans modifier les services | 2 | ✅ | = |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | ✅ | = |
| 6.3.1 | `LocalConverter` et `ServeConverter` interchangeables | 3 | ✅ (cf. INFO 1, 2, 10) | = |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | ✅ | = |
| 6.3.3 | Pas d'`isinstance()` ni de `type()` pour différencier les implémentations | 2 | ✅ (cf. INFO 12) | = |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | ✅ | = |
| 6.4.2 | Aucun port ne force une implémentation à définir des méthodes inutiles | 2 | ✅ (à la limite, cf. INFO 1, 12) | = |
| 6.5.1 | Les services dépendent de ports, pas d'implémentations concrètes | 3 | ✅ (lecture opérationnelle, cf. la note sous MAJ-2) | = |
| 6.5.2 | Injection au composition root | 2 | ✅ (cf. INFO 4) | = |
| 6.5.3 | Pas d'instanciation directe d'adaptateurs dans les services | 3 | ✅ | = |

---

## Vérification des principes

**Méthode.**
- Lecture des sources du working tree à `1de1929`, et commandes de la fiche rejouées, étendues à `from persistence`.
- Trois scripts AST, gardés dans le scratchpad et non versionnés :
  - **typage des attributs** : pour chaque classe de `services/`, le script lit le type déclaré de chaque paramètre du constructeur et le relie à l'attribut `self._x` qui le reçoit ;
  - **croisement avec les ports** : chaque appel `self._x.m(...)` est comparé au `Protocol` correspondant (`Sqlite*` → port homonyme, `OpenSearchStore` → `VectorStore`) ;
  - **signatures** : les arguments nommés et l'arité de chaque appel sont comparés à la signature du port.
- Test ciblé : `pytest tests/test_architecture.py` → 39 passed.

### SRP (6.1)

- **6.1.1 conforme.** Les 17 classes de service n'ont pas changé, à l'exception d'`AnalysisService`, qui passe de 586 à 589 lignes avec le `to_thread` de l'import, toujours dans son cas d'usage.
  - Le découpage document-agent par question reste valable :
    - `NavigationService` (`services/navigation_service.py:50`) ;
    - `CitationService` (`services/citation_service.py:48`) ;
    - `CitationImageService` (`services/citation_image_service.py:32`) ;
    - `SourceService` (`services/source_service.py:75`) ;
    - `ParseLoader` (`services/parse_loader.py:44`) ;
    - `McpConfigService` (`services/mcp_config_service.py:109`).
  - Petites largeurs et dette héritée : INFO 5, 6 et 9.
- **6.1.2 conforme.**
  - Il y a 12 `defineStore` de feature, un par fichier `frontend/src/features/*/store.ts`. Le store partagé est `shared/breadcrumb/store.ts:13`.
  - Le dossier `features/store` n'a pas de store Pinia.
  - Le store MCP a sa propre feature (`features/mcp-config/store.ts:14`). Le batch d'analyses reste dans `features/analysis/store.ts:149` / `:170`.
  - Observation sur une action morte et dupliquée dans le store `document` : INFO 11 (nouvelle).
- **6.1.3 conforme.** Il y a un router par ressource : `analyses`, `config`, `document_chunks`, `document_versions`, `documents`, `graph`, `ingestion`, `mcp`, `reasoning`, `stores`. Ils partagent le préfixe `/api/documents` pour les sous-ressources d'un document. Aucune route n'a été ajoutée depuis 0.7.3.
- **6.1.4 non conforme.** `DocumentService` cumule la lecture et le rendu PDF (pdf2image et pypdfium2) avec le stockage disque et la persistence. → **MAJ-1**, inchangé.

### OCP (6.2)

- **6.2.1 non conforme.** Les services consomment 12 méthodes et 1 argument nommé que leurs ports ne déclarent pas, sur 16 sites d'appel. `VersionService` n'a pas de port. → **MAJ-2**, inchangé, inventaire complété.
- **6.2.2 conforme.**
  - La sélection local/remote est centralisée dans `build_converter()` (`bootstrap/factories.py:44-58`).
  - `AnalysisService` ne lit que la capacité `supports_page_batching` (`services/analysis_service.py:451`) et délègue la fusion à `merge_batches` (`:343`).
  - La fusion Docling reste dans l'adaptateur (`infra/local_converter.py:157-179`).
- **6.2.3 conforme.** L'endpoint `export_document` (`api/documents.py:133-146`) ne reçoit que l'enum `ExportFormat`. La chaîne `if format is …` vit dans le service (`services/export_service.py:59`, `:68`).

### LSP (6.3)

- **6.3.1 conforme (poids 3).**
  - `LocalConverter` (`infra/local_converter.py:187-204`) et `ServeConverter` (`infra/serve_converter.py:70-112`) exposent `convert`, `supports_page_batching` et `merge_batches`, et retournent un `ConversionResult`.
  - Le `document_json=None` possible côté Serve (`infra/serve_converter.py:258`) est prévu par le contrat.
  - Divergences de forme et de fidélité : INFO 1, 2 et 10, toutes inchangées.
- **6.3.2 conforme.**
  - `OllamaProbe.probe` ramène tous les échecs à `LLMHostProbeResult(reachable=False)` (`infra/llm/ollama_probe.py:78-104`).
  - L'adaptateur `DoclingDocumentImporter` lève `ValueError` (`infra/docling_importer.py:29`). L'exception traverse désormais `asyncio.to_thread` (`services/analysis_service.py:180`) et reste traduite en 400 par le router (`api/analyses.py:81-85`).
  - Les erreurs de `PdfPageRasterizer.render_page` (`ValueError`, `FileNotFoundError`, `infra/page_raster.py:27-30`) sont absorbées par la traduction générique de l'adaptateur MCP (`mcp_adapter/tool_errors.py:49-53`).
  - `PageTextReader` : le seul appelant tolère toute exception (`services/source_service.py:157-161`).
- **6.3.3 conforme.** Le grep de la fiche ne trouve dans `services/` que 4 `isinstance`, qui valident des types primitifs de payload :
  - `services/chunk_service.py:218` ;
  - `services/store_service.py:135` et `:139` ;
  - `services/mcp_config_service.py:71`.

  Aucun `type(`. Le garde `provider.type is not OLLAMA` de l'adaptateur de reasoning est hors `services/` et ne sert pas de dispatch : INFO 12.

### ISP (6.4)

- **6.4.1 conforme.** `DocumentConverter` (`domain/ports.py:55`) et `DocumentChunker` (`:92`) sont séparés.
  - L'import a son propre port, `DoclingDocumentImporter` (`:86`).
  - Le rendu et la couche texte sont deux ports distincts : `PageRasterizer` (`:423`) et `PageTextReader` (`:449`).
- **6.4.2 conforme, à la limite.**
  - `merge_batches` est imposé à `ServeConverter`, qui l'implémente en code mort : INFO 1.
  - `LLMProvider.health_check` est imposé sans client : INFO 12, nouvelle.
  - `AnalysisRepository` compte 14 méthodes pour un client MCP qui en utilise 3 : INFO 7.

### DIP (6.5)

- **6.5.1 conforme (poids 3), en lecture opérationnelle.**
  - Le grep `from infra` sur `services/` ne trouve que des imports sous `TYPE_CHECKING` (`services/store_backend_resolver.py:40-42`), plus un commentaire (`services/chunk_service.py:170`).
  - Le grep étendu `from persistence` trouve 7 imports, tous sous `TYPE_CHECKING` :
    - `services/store_backend_resolver.py:43` ;
    - `services/chunk_service.py:43-44` ;
    - `services/store_service.py:23-25` ;
    - `services/version_service.py:32`.
  - Aucun import runtime de `infra/` ni de `persistence/`.
  - En lecture stricte, en revanche, le typage `Sqlite*` et l'absence de port de versions violent 6.5.1. La note sous MAJ-2 détaille ce point.
- **6.5.2 conforme.**
  - Tous les adaptateurs et dépôts sont instanciés dans `bootstrap/builder.py:102-127`, `:215`, `:253` et dans `bootstrap/factories.py`, appelés par `main.py:51-55`.
  - Seconde racine : `mcp_stdio.py:51-70`, qui réutilise les factories.
  - Aucune construction de service dans `api/` ni dans `mcp_adapter/` : le grep `Service(|Resolver(|Loader(|Repository()` y est vide.
- **6.5.3 conforme (poids 3).**
  - Le grep `LocalConverter|ServeConverter|LocalChunker` sur `services/` ne renvoie rien.
  - L'inventaire des instanciations dans `services/` ne contient que des modèles, des VO et des erreurs du projet, plus `pdfium.PdfDocument` (bibliothèque tierce, comptée dans MAJ-1).
  - Les adaptateurs PDF et Docling sont construits dans `bootstrap/factories.py:201-215` et `:298-313`.

---

## Ecarts constates

### [MAJ] MAJ-1 — `DocumentService` cumule parsing / rendu PDF et persistence, en contournant les ports `PageRasterizer` / `PageTextReader`

**Statut vs 0.7.3 : toujours présent, inchangé.** `services/document_service.py` et `api/documents.py` sont identiques à `02adc68`. Dans `analysis_service.py`, seuls les numéros de ligne ont bougé (+3).

- **Localisation** :
  - `document-parser/services/document_service.py:14-15` : `import pypdfium2 as pdfium` et `from pdf2image import convert_from_bytes, pdfinfo_from_bytes`, au niveau du module.
  - `document-parser/services/document_service.py:159-168` : `generate_preview`, rasterisation poppler, `@staticmethod`.
  - `document-parser/services/document_service.py:170-188` : `page_sizes`, ouverture pdfium (#352), `@staticmethod`.
  - `document-parser/services/document_service.py:191-202` : `_persist_and_count`, avec écriture disque `open(…, "wb")` à `:199`.
  - `document-parser/services/document_service.py:205-215` : `_count_pages` via poppler.
  - `document-parser/services/document_service.py:143-147` : `os.realpath` et `os.unlink`.
  - Dépôt : `:108`, `:157`.
  - `document-parser/api/documents.py:188-189` et `:216` : le router appelle `DocumentService.generate_preview` et `DocumentService.page_sizes` **sur la classe**, en contournant l'instance injectée. Il lit lui-même le fichier (`:185-187`, `:213-215`).
  - Secondaire :
    - `document-parser/services/analysis_service.py:17` (`import pypdfium2`) ;
    - `:59-68` (`_count_pdf_pages`) ;
    - `:449`, où la fonction est appelée sur la boucle d'événements, sans thread.
- **Constat** :
  - **Trois raisons de changer.** `DocumentService` en porte au moins trois :
    - le stockage des fichiers ;
    - le CRUD documents via `DocumentRepository` ;
    - la lecture et le rendu PDF : nombre de pages, aperçu PNG, tailles de page.

    C'est exactement le contre-exemple de l'item.
  - **Les ports existent déjà.**
    - `PageRasterizer.render_page` (`domain/ports.py:432`, adaptateur `infra/page_raster.py:26-33`) fait exactement ce que fait `generate_preview` : `convert_from_bytes` puis PNG.
    - L'adaptateur pdfium de `PageTextReader` (`infra/page_text.py:27-38`) prend le verrou process-wide de Docling, parce que « pdfium is not thread-safe » (`infra/page_text.py:7-9`, `:21-24`, `:31`).
  - **Ouvertures pdfium sans verrou.** `page_sizes` (exécuté dans un thread, `api/documents.py:216`) et `_count_pdf_pages` (exécuté sur la boucle, `analysis_service.py:449`) ouvrent pdfium sans ce verrou. Une conversion Docling locale peut donc être en cours au même moment. C'est plausible, mais non démontré.
  - **Le projet connaît la dette.**
    - `tests/test_architecture.py:314` garde `pdf2image` et `pypdfium2` comme « migration candidates ».
    - `:212-214` limite la règle « framework-free » à cinq modules, parce que `document_service.py` « rasterises directly and predates the port ».
- **Regle violee** : item 6.1.4, poids 2.
- **Remediation** :
  1. **Aperçu.** Injecter `PageRasterizer` dans `DocumentService` (`bootstrap/factories.py:219`, `build_document_service`). Remplacer `generate_preview` par une méthode d'instance `async preview(doc, page, dpi)` qui appelle `self._raster.render_page(str(self.resolve_storage_path(doc.storage_path)), page=…, dpi=…)` dans `to_thread`.
  2. **Géométrie.** Ajouter un port de géométrie PDF, par exemple `PdfInspector.page_count(path)` et `page_sizes(path) -> list[PageDetail]`, plutôt que d'élargir `PageTextReader` (ISP). L'implémenter dans `infra/`, sous `_pdfium_lock`. L'injecter dans `DocumentService` et `AnalysisService`.
  3. **Router.** Le router appelle l'instance (`service.preview(...)`, `service.page_sizes(...)`) et ne lit plus le fichier.
  4. **Garde-fou.** Retirer `pdf2image` et `pypdfium2` de `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES`, les ajouter à `_SERVICES_FORBIDDEN_EXTERNALS` (`tests/test_architecture.py:300-314`), et étendre `TestDocumentAgentServicesAreFrameworkFree.MODULES` à `document_service` et `analysis_service`.
  5. **Points d'attention.** Le comptage de pages à l'upload passe aujourd'hui par poppler (`pdfinfo`). S'il passe par pdfium, la tolérance aux PDF malformés peut changer. Les tests qui patchent `services.document_service._count_pages` et `convert_from_bytes` sont à réécrire contre un faux port : `tests/test_document_service.py:53-144`, `tests/test_analysis_service.py:15`, `:305-321`, `:566`.
- **Effort** : M, environ ½ à 1 jour. **Risque de régression** : modéré, sur `/preview`, `/pages` et le comptage de pages à l'upload et en batch. La couverture existe : `tests/test_api_endpoints.py:223-257`, `tests/test_document_service.py`.

### [MAJ] MAJ-2 — Contrats de ports incomplets ou absents : les services consomment 12 méthodes et 1 argument nommé hors protocole, et `VersionService` n'a pas de port

**Statut vs 0.7.3 : toujours présent, inchangé.** Les fichiers concernés sont identiques à `02adc68`, sauf `analysis_service.py`, décalé de +3. L'inventaire est **complété** : 3 sites d'appel n'étaient pas cités en 0.7.3, `store_service.py:257`, `:306` et `version_service.py:145`.

- **Localisation : inventaire exhaustif** (script AST, vérifié ligne par ligne).

  **A. Méthodes appelées par un service mais absentes du `Protocol` déclaré** (12 méthodes, 1 argument nommé, 16 sites d'appel) :

  | Port (`domain/ports.py`) | Méthode manquante | Signature réelle (implémentation concrète) | Site(s) d'appel | Zone |
  |---|---|---|---|---|
  | `AnalysisRepository` (`:207`) | `find_by_document` | `(document_id: str, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]`, `persistence/analysis_repo.py:88` | `services/analysis_service.py:204` (servi par `GET /api/analyses?documentId=`, `api/analyses.py:97`) | **active** |
  | `ChunkPushRepository` (`:197`) | `count_for_document` | `(document_id: str) -> int`, `persistence/chunk_edit_repo.py:171` | `services/chunk_service.py:711` | ingestion (dépréciée) |
  | `ChunkPushRepository` (`:197`) | `find_for_document` | `(document_id: str, *, limit: int = 50, offset: int = 0) -> list[ChunkPush]`, `persistence/chunk_edit_repo.py:147` | `services/chunk_service.py:714` | ingestion |
  | `VectorStore` (`:256`, `@runtime_checkable`) | `search_fulltext` | `(index_name: str, query_text: str, *, k: int = 10, doc_id: str \| None = None) -> list[SearchResult]`, `infra/opensearch_store.py:204` | `services/ingestion_service.py:277` | ingestion |
  | `StoreRepository` (`:128`) | `insert(…, password=)` (argument nommé absent du port, `:131`) | `(store: Store, *, password: str \| None = None) -> None`, `persistence/store_repo.py:67` | `services/store_service.py:231` | stores |
  | `StoreRepository` | `find_by_name` | `(name: str) -> Store \| None`, `persistence/store_repo.py:119` | `services/store_service.py:214`, `:257` | stores |
  | `StoreRepository` | `update` | `(store: Store) -> None`, `persistence/store_repo.py:134` | `services/store_service.py:297` | stores |
  | `StoreRepository` | `clear_default_except` | `(store_id: str) -> None`, `persistence/store_repo.py:164` | `services/store_service.py:233`, `:306` | stores |
  | `StoreRepository` | `delete` | `(store_id: str) -> bool`, `persistence/store_repo.py:174` | `services/store_service.py:395` | stores |
  | `StoreRepository` | `get_connection_password` | `(store_id: str) -> str \| None`, `persistence/store_repo.py:182` | `services/store_backend_resolver.py:128`, `:143` | stores |
  | `StoreRepository` | `set_connection_password` | `(store_id: str, plaintext: str \| None) -> bool`, `persistence/store_repo.py:204` | `services/store_service.py:303` | stores |
  | `DocumentStoreLinkRepository` (`:142`) | `count_by_store` | `() -> dict[str, int]`, `persistence/document_store_link_repo.py:82` | `services/store_service.py:163` | stores |
  | `DocumentRepository` (`:105`) | `find_by_ids` | `(doc_ids: list[str]) -> dict[str, Document]`, `persistence/document_repo.py:106` | `services/store_service.py:361` | stores |

  **B. Port absent.** `domain/ports.py` ne contient aucun `DocumentVersionRepository`.
  - `VersionService` est typé contre `SqliteDocumentVersionRepository` : `services/version_service.py:32` (import sous `TYPE_CHECKING`) et `:87` (constructeur).
  - Méthodes consommées :
    - `find_for_document`, `:99` ;
    - `insert`, `:124` et `:145` ;
    - `find_by_id`, `:154`.
  - Implémentation : `persistence/document_version_repo.py:40`, `:56`, `:65`. `find_latest_for_document` (`:75`) n'est consommé par aucun service.
  - Zone : **active** (historique des versions).

  **C. Services typés contre des classes concrètes** : 4 services ; tous les imports sont sous `TYPE_CHECKING`.

  | Service | Paramètre : type concret | Port à utiliser |
  |---|---|---|
  | `StoreService` | `store_repo: SqliteStoreRepository` (`services/store_service.py:148`) | `StoreRepository` |
  | | `link_repo: SqliteDocumentStoreLinkRepository` (`:149`) | `DocumentStoreLinkRepository` |
  | | `document_repo: SqliteDocumentRepository \| None` (`:150`) ; imports `:23-25` | `DocumentRepository` |
  | `ChunkService` | `store_repo: SqliteStoreRepository \| None` (`services/chunk_service.py:159`) | `StoreRepository` |
  | | `link_repo: SqliteDocumentStoreLinkRepository \| None` (`:160`) ; imports `:43-44` | `DocumentStoreLinkRepository` |
  | `StoreBackendResolver` | `store_repo: SqliteStoreRepository` (`services/store_backend_resolver.py:81`) | `StoreRepository` |
  | | `neo4j_pool: Neo4jDriverPool` (`:82`) et `opensearch_pool: OpenSearchClientPool` (`:83`), appels `.get(...)` à `:129` et `:149` ; imports `infra` `:40-42` | aucun port, à injecter en fabriques `Callable` comme `graph_writer_factory` (`:84`) |
  | | `IngestionTargets.vector_store: OpenSearchStore \| None` (`:61`) | `VectorStore` |
  | `VersionService` | `version_repo: SqliteDocumentVersionRepository` (`services/version_service.py:87`) | à créer : `DocumentVersionRepository` |

- **Constat** :
  - **Effet sur un nouvel adaptateur.** Les ports sont des `Protocol` structurels, et le contrat réel des services est plus large que le contrat déclaré. Un adaptateur écrit fidèlement contre `domain/ports.py` (dépôt Postgres, double de test conforme au port) passerait toute vérification statique. Il lèverait ensuite `AttributeError` sur :
    - `GET /api/analyses?documentId=…` ;
    - l'historique des pushes ;
    - la recherche plein texte ;
    - toute la gestion des stores ;
    - l'historique des versions.

    Ajouter un adaptateur impose donc de modifier `domain/ports.py`, voire les signatures des services : c'est ce que l'item interdit.
  - **Aucun garde-fou ne l'attrape.**
    - Il n'y a pas de type-checker : ni configuration mypy ou pyright dans `document-parser/pyproject.toml`, ni étape dans `.github/workflows/`.
    - La règle pytestarch `services → persistence/infra` (`tests/test_architecture.py:130-143`) est inopérante, comme le test le documente lui-même (`:186-193`, « the rules never see an edge »).
    - Le test AST qui mord (`:206-232`) est limité aux cinq modules document-agent.
    - Vérifié : `pytest tests/test_architecture.py` → **39 passed**, alors que 7 imports `persistence` et 3 imports `infra` sont présents dans `services/`.
  - **Ce qui ne relève pas de la zone dépréciée.** L'essentiel se concentre dans la zone Store/ingestion, dépréciée et retirée en 0.8.0 (`CHANGELOG.md`, section `Deprecated` de 0.7.3). `VersionService` et `AnalysisRepository.find_by_document` n'en font **pas** partie.
- **Regle violee** : item 6.2.1 — « Les ports (`domain/ports.py`) permettent d'ajouter de nouveaux adaptateurs sans modifier le code existant » (poids 2).
- **Note de lecture (6.5.1)** : la note de 0.7.3 est maintenue telle quelle.
  - En lecture stricte, `VersionService` (sans port) et les 4 services typés sur des classes concrètes « dépendent d'implémentations concrètes ». 6.5.1, de poids 3, serait alors non conforme : CRIT, donc NO-GO.
  - Cette lecture n'est **pas** retenue :
    - aucune dépendance runtime : tous les imports sont sous `TYPE_CHECKING`, et l'objet injecté par `bootstrap/` est substituable par duck typing ;
    - lecture acceptée par les gates 0.7.0 et 0.7.3 ;
    - classement MAJ confirmé par la synthèse du re-audit 0.7.3, avec une cible en 0.8.0.

  Si le mainteneur retient la lecture stricte, cet écart devient CRIT.
- **Remediation** (dans l'ordre, applicable directement) :
  1. **`domain/ports.py` : compléter les `Protocol`** avec les 12 méthodes du tableau A et leurs signatures exactes, et ajouter `*, password: str | None = None` à `StoreRepository.insert` (`:131`). Ce changement ne touche que les annotations, sans effet runtime : seul `VectorStore`, parmi les ports concernés, est `@runtime_checkable`, et son seul `isinstance` (`tests/test_opensearch_store.py:91`) vise `OpenSearchStore`, qui implémente déjà `search_fulltext`.
  2. **Créer `DocumentVersionRepository(Protocol)`** avec `insert`, `find_by_id` et `find_for_document`. Ajouter `find_latest_for_document` seulement si un service le consomme (ISP).
  3. **Retyper sur les ports** les constructeurs du tableau C (`StoreService`, `ChunkService`, `StoreBackendResolver`, `VersionService`) et `IngestionTargets.vector_store`. Supprimer les imports `persistence.*` sous `TYPE_CHECKING`.
  4. **Pools de `StoreBackendResolver`** : les injecter en fabriques, `Callable[..., Awaitable[VectorStore]]` et `Callable[..., Awaitable[Any]]`, sur le modèle de `graph_writer_factory`. Comme cette zone part en 0.8.0, ce point peut attendre ; `VersionService` et `find_by_document`, non.
  5. **Poser un garde-fou qui mord** : un test AST qui interdit `persistence` et `infra` dans `services/`, **y compris sous `TYPE_CHECKING`**, sur le modèle de `TestMcpAdapterLayerIsolation` (`tests/test_architecture.py:196-201`). Éventuellement, `mypy` ciblé sur `services/` en CI.
- **Effort** : S pour les étapes 1 à 3 et 5, environ 1 à 2 h : uniquement `domain/ports.py`, des annotations et un test. M si l'on traite aussi l'étape 4. **Risque de régression** : très faible. Annotations et `Protocol` n'ont aucun effet à l'exécution, et aucun port de dépôt n'est `@runtime_checkable`. Le seul risque est un faux positif du nouveau test AST au moment de son introduction.

### [INFO] INFO 1 — `merge_batches` (#344) imposé à `ServeConverter`, qui l'implémente en code mort

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** : `document-parser/domain/ports.py:79-83` ; `document-parser/infra/serve_converter.py:95-98`.
- **Constat** : `ServeConverter` a `supports_page_batching = False` et doit pourtant implémenter `merge_batches`, « Not reached while `supports_page_batching` is False ». C'est le motif ISP classique du drapeau de capacité suivi d'une méthode conditionnelle. L'item reste conforme : l'implémentation n'est pas un stub, et le client utilise les trois membres.
- **Regle** : 6.4.2 (à la limite).
- **Remediation** : optionnelle. Porter la capacité dans un objet dédié (`converter.batching -> PageBatching | None`), ou créer un sous-port `PageBatchingConverter` sélectionné au composition root.

### [INFO] INFO 2 — `supports_page_batching` : `@property` au port, attribut de classe dans les adaptateurs

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** : `document-parser/domain/ports.py:70-77` vs `document-parser/infra/local_converter.py:192` et `document-parser/infra/serve_converter.py:77`.
- **Constat** : la lecture se fait par duck typing (`services/analysis_service.py:451`), sans rupture.
- **Regle** : 6.3.1 (forme du protocole).
- **Remediation** : homogénéiser la forme, en même temps qu'INFO 1.

### [INFO] INFO 3 — `ServeConverter.health_check()` toujours orphelin

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** : `document-parser/infra/serve_converter.py:189`.
- **Constat** : la méthode est absente du port et de `LocalConverter`. Elle n'a aucun appelant : le grep sur `api/`, `services/`, `bootstrap/`, `main.py`, `mcp_stdio.py` et `mcp_adapter/` est vide.
- **Regle** : 6.3.1 / 6.4.2.
- **Remediation** : la supprimer, ou la promouvoir dans le port si un health-check du converter devient nécessaire.

### [INFO] INFO 4 — Composition root : libellés de fiche périmés, deux racines

**Statut vs 0.7.3 : toujours présent, inchangé.** La fiche `docs/audit/audits/06-solid.md` n'a pas été mise à jour.
- **Localisation** :
  - `document-parser/bootstrap/builder.py:70` et `document-parser/bootstrap/factories.py`, appelés par `document-parser/main.py:51-55` ;
  - seconde racine : `document-parser/mcp_stdio.py:48-70` ;
  - fiche : items 6.2.2 (`_build_converter()`) et 6.5.2 (`main.py`), et commande 6.5.1.
- **Constat** : la fiche cite toujours `_build_converter()`, alors que le nom réel est `build_converter()` (`bootstrap/factories.py:44`), et `main.py` comme composition root. La commande 6.5.1 ne cherche que `from infra`, ce qui laisse passer les 7 imports `persistence` de MAJ-2.
- **Regle** : 6.5.2 / 6.2.2 (libellés).
- **Remediation** : mettre à jour la fiche :
  - « composition root : `bootstrap/` (via `main.py` et `mcp_stdio.py`) » ;
  - « `build_converter()` » ;
  - ajouter `grep -rn "from persistence\|import persistence" document-parser/services/` à la commande 6.5.1.

### [INFO] INFO 5 — Dette SRP héritée : `AnalysisService` (édition legacy du blob) et `ChunkService`

**Statut vs 0.7.3 : toujours présent.** `AnalysisService` passe de 586 à 589 lignes (+3, `to_thread`), et ses lignes sont décalées de +3. `ChunkService` est identique.
- **Localisation** :
  - `document-parser/services/analysis_service.py:218` (`rechunk`), `:242` (`update_chunk_text`), `:264` (`delete_chunk`) ;
  - `document-parser/services/chunk_service.py:146` (classe, 1019 lignes), `:540` (`diff_against_store`), `:574` (`push_to_store`), `:693` (`list_pushes`), `:789` (`get_tree`).
- **Constat** : `ChunkService` mêle trois choses :
  - le cycle de vie des chunks ;
  - le push vers les stores ;
  - la projection d'arbre.

  Le retrait de l'ingestion en 0.8.0 obligera à le modifier. L'écart est déjà porté en MAJ par l'audit 03 ; il n'est pas compté deux fois ici.
- **Regle** : 6.1.1 (observation de largeur).
- **Remediation** : profiter du retrait de l'ingestion en 0.8.0 pour :
  - sortir push, diff et historique de `ChunkService` ;
  - sortir `get_tree` vers un service de lecture d'arbre ;
  - déprécier l'édition du blob `chunks_json`.

### [INFO] INFO 6 — `ParseLoader` expose ses dépôts : dépendances cachées de `NavigationService` / `CitationService`

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** :
  - `document-parser/services/parse_loader.py:60-68` (propriétés `analyses` et `documents`) ;
  - consommateurs : `document-parser/services/navigation_service.py:82`, `:87` et `document-parser/services/citation_service.py:198`.
- **Constat** : `self._parses.documents.find_all(…)` et `self._parses.analyses.latest_parsed_ids(…)` contournent l'abstraction. Le constructeur de ces services ne déclare que `parses`, ce qui rend la dépendance réelle invisible (loi de Déméter).
- **Regle** : 6.1.1 / 6.5.1 (dépendances explicites), observation.
- **Remediation** : deux options.
  - Donner à `ParseLoader` deux requêtes nommées, `find_documents(query, limit)` et `latest_version(document_id)`, et retirer les propriétés.
  - Ou injecter explicitement les dépôts là où ils servent.

### [INFO] INFO 7 — `AnalysisRepository` : 14 méthodes pour une surface MCP en lecture seule qui en utilise 3

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** :
  - `document-parser/domain/ports.py:207-240` ;
  - consommateur : `document-parser/services/parse_loader.py:83`, `:89`, `:107` ;
  - `document-parser/mcp_stdio.py:65`.
- **Constat** : la surface document-agent, en lecture seule (`mcp_adapter/server.py:14`), dépend d'un port de 14 méthodes, dont 5 écritures. C'est un problème d'ISP côté client. Si MAJ-2 est corrigé, le port passe à 15 méthodes avec `find_by_document`.
- **Regle** : 6.4.2 (ISP côté client), observation.
- **Remediation** : extraire un port de lecture `ParseReader` (`latest_parsed_ids`, `parsed_document_id`, `parse_json`), implémenté par le même dépôt, et typer `ParseLoader` dessus.

### [INFO] INFO 8 — `PageRasterizer.crop` détourné en transcodeur

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** : `document-parser/services/citation_image_service.py:89-91` ; port `document-parser/domain/ports.py:436-445`.
- **Constat** : `crop(page_png, (0, 0, 10_000, 10_000), fmt="WEBP")` compte sur le clamp de l'adaptateur pour réencoder la page en entier. Le clamp fait partie du contrat, donc il n'y a pas de rupture LSP. Mais le port n'exprime pas l'opération voulue.
- **Regle** : 6.4.2 / 6.3.1 (adéquation du port), observation.
- **Remediation** : `render_page(storage_path, page=…, dpi=…, fmt=…)`, ou une opération `encode(png, fmt)` explicite.

### [INFO] INFO 9 — Découpage SRP hétérogène dans l'adaptateur MCP et son service de config

**Statut vs 0.7.3 : toujours présent, inchangé.** `mcp_adapter/` et `bootstrap/` sont identiques à `02adc68`.
- **Localisation** :
  - `document-parser/mcp_adapter/sources_view.py` (369 lignes) :
    - dataclasses de contrat : `:42-151` ;
    - enregistrement des tools : `:163-209` ;
    - mapping : `:223-335` ;
    - rendu texte : `:338-369`.
  - `document-parser/mcp_adapter/apps.py:74` (contrat `CitationView`) et `:123-228` (enregistrement).
  - `document-parser/services/mcp_config_service.py:186-188` (`server_status`).
  - `document-parser/bootstrap/mcp_mount.py:128-148` (mapping SDK → VO) et `:151-183` (middleware ASGI).
- **Constat** : pour les tools du cœur, le contrat (`wire.py`), la traduction (`wire_mapping.py`) et l'enregistrement (`server.py`) sont séparés. Les cartes MCP Apps reviennent au module mixte. Rien de bloquant.
- **Regle** : 6.1.1 / 6.1.4, observation.
- **Remediation** : aligner les cartes sur le découpage `wire` / `wire_mapping` / enregistrement.

### [INFO] INFO 10 — Fidélité remote vs local : `PageElement.level` toujours 0 côté Docling Serve

**Statut vs 0.7.3 : toujours présent, inchangé.**
- **Localisation** :
  - `document-parser/infra/serve_converter.py:377` (`level=0`) ;
  - vs `document-parser/infra/docling_pages.py:107` (`level=level`).
- **Constat** : le type de retour est le même, mais l'indentation et le badge `L{n}` diffèrent selon le moteur. Le contrat de `PageElement` ne spécifie pas `level`.
- **Regle** : 6.3.1 (postcondition implicite), observation.
- **Remediation** : deux options.
  - Dériver le niveau côté Serve, à partir de la profondeur dans l'arbre `body`.
  - Ou documenter `level` comme optionnel (0 = inconnu).

### [INFO] INFO 11 — Store `document` : action `pushToStore` dupliquée du store `chunks` et morte en production (nouveau)

**Statut vs 0.7.3 : nouveau, préexistant non relevé.** L'action était déjà présente en v0.7.0 (git log `-S`, dc87383).
- **Localisation** :
  - `frontend/src/features/document/store.ts:6` (`import { pushChunksToStore } from '@/features/chunks'`), `:205-214` (`pushToStore`), `:246` (export) ;
  - chemin réellement utilisé : `frontend/src/features/chunks/store.ts:193-202` (`push`), appelé par `frontend/src/features/chunks/ui/ChunksEditor.vue:211` ;
  - seuls appelants de `useDocumentStore().pushToStore` : `frontend/src/features/document/store.test.ts:169-185`.
- **Constat** :
  - Le store `document` porte une action de la feature `chunks` (pousser des chunks vers un store vectoriel), presque identique à `useChunksStore().push`, et sans appelant en production.
  - Il importe pour cela l'API de `chunks`, ce qui crée un cycle d'imports de barrels avec `features/chunks/store.ts:5` (`rechunkDocument` de `@/features/document`).
  - L'item reste conforme : le store `document` gère bien sa feature (bibliothèque et Doc workspace), et l'action est morte, sans effet sur l'état.
- **Regle** : 6.1.2 (observation).
- **Remediation** : supprimer `pushToStore`, l'import `pushChunksToStore` (`document/store.ts:6`) et les deux tests associés (`store.test.ts:169-185`). Effort XS, sans risque runtime : aucun appelant en production. À faire au plus tard avec le retrait de l'ingestion en 0.8.0.

### [INFO] INFO 12 — `LLMProvider` : membre `health_check` sans client, et substituabilité refusée par son seul consommateur (nouveau)

**Statut vs 0.7.3 : nouveau, préexistant non relevé.** Les deux points étaient déjà présents en v0.7.0 : `git show v0.7.0:document-parser/domain/ports.py` (`:337`) et `infra/docling_agent_reasoning.py` (`:137`).
- **Localisation** :
  - port : `document-parser/domain/ports.py:344-375` (`@runtime_checkable`), `health_check` en `:370-374` ;
  - unique implémentation : `document-parser/infra/llm/ollama_provider.py:41` ;
  - unique consommateur : `document-parser/infra/docling_agent_reasoning.py:136-140`.
- **Constat** :
  - **`health_check` n'a pas de client.** Le port impose ce membre, mais aucun code de production ne l'appelle : le grep sur `api/`, `services/`, `bootstrap/`, `infra/` et `main.py` ne trouve que la définition. Seul `tests/test_ollama_provider.py:39-59` l'exerce.
  - **Le consommateur refuse la substitution.** Le seul consommateur du port lève `NotImplementedError` pour tout provider dont `type` n'est pas `OLLAMA`. Le port promet donc une substituabilité que son unique client refuse. C'est assumé et documenté (`domain/ports.py:352-357`, limitation docling-agent), et sans effet runtime, puisqu'un seul provider existe.
  - **Classement.** Ce n'est pas un dispatch entre implémentations dans `services/`, donc 6.3.3 reste conforme. Même cause racine que le MAJ de l'audit 04 (abstraction LLM-provider prématurée, `domain/value_objects.py:167`) : il n'est pas compté deux fois.
- **Regle** : 6.4.2 / 6.3.1 (observation).
- **Remediation** : à traiter avec le MAJ 04. Deux options :
  - réduire le port à ce que le runner consomme (`host`, `default_model_id`) ;
  - ou garder `type` et `health_check`, avec un appelant (`/api/health`) le jour où un second provider existe.

---

## Delta vs 0.7.3

**Score** : 87 → **87** (=). **Écarts** : 0/2/0/10 → **0/2/0/12**.

| Écart 0.7.3 | Statut 0.7.4 |
|-------------|--------------|
| [MAJ] MAJ-1 `DocumentService` parsing + persistence (6.1.4) | **Toujours présent, inchangé.** `document_service.py` et `api/documents.py` sont identiques. Les lignes d'`analysis_service.py` sont décalées de +3 (`:446` → `:449`) |
| [MAJ] MAJ-2 ports incomplets ou absents (6.2.1) | **Toujours présent, inchangé.** Les 13 écarts de méthode sont confirmés. L'inventaire passe à 16 sites d'appel : `store_service.py:257` et `:306`, `version_service.py:145` n'étaient pas cités. `analysis_service.py:201` → `:204` |
| [INFO] 1 `merge_batches` en code mort côté Serve | Toujours présent, inchangé |
| [INFO] 2 `supports_page_batching` @property vs attribut | Toujours présent (`analysis_service.py:448` → `:451`) |
| [INFO] 3 `ServeConverter.health_check()` orphelin | Toujours présent, inchangé |
| [INFO] 4 Libellés de fiche, deux racines | Toujours présent. La fiche n'a pas été mise à jour |
| [INFO] 5 Dette SRP `AnalysisService` / `ChunkService` | Toujours présent (lignes +3) |
| [INFO] 6 `ParseLoader` expose ses dépôts | Toujours présent, inchangé |
| [INFO] 7 `AnalysisRepository` à 14 méthodes | Toujours présent, inchangé |
| [INFO] 8 `crop` en transcodeur | Toujours présent, inchangé |
| [INFO] 9 Découpage SRP de l'adaptateur MCP | Toujours présent, inchangé |
| [INFO] 10 `level=0` côté Serve | Toujours présent, inchangé |

| Nouvel écart | Origine |
|--------------|---------|
| [INFO] 11 `pushToStore` mort et dupliqué dans le store `document` | Préexistant (v0.7.0), non relevé |
| [INFO] 12 `LLMProvider.health_check` sans client, substitution refusée | Préexistant (v0.7.0), non relevé |

Le delta est nul parce que la remédiation 0.7.3 (PR #367, #368) ne visait pas l'audit 06. Ces deux PR n'ont touché que `analysis_service.py` (`to_thread`) et le frontend (`ConfigSource`), sans effet sur un item SOLID. Les deux MAJ étaient planifiés pour la 0.8.0 (synthèse du re-audit 0.7.3, ligne « 06 ×2 »).

---

## Remédiation et quick wins

| Action | Item | Gain | Effort | Risque |
|--------|------|------|--------|--------|
| Compléter les `Protocol` (12 méthodes + `insert(…, password=)`), créer `DocumentVersionRepository`, retyper les 4 constructeurs et `IngestionTargets.vector_store`, ajouter un test AST qui interdit `persistence`/`infra` dans `services/`, même sous `TYPE_CHECKING` | 6.2.1 (poids 2), et 6.5.1 en lecture stricte | **+7 pts** (87 → 94 ; 29/31 = 93,5). Lève MAJ-2 et supprime le risque de reclassement CRIT de 6.5.1 | S (≈ 1 à 2 h) | Très faible : annotations seulement, aucun port de dépôt `@runtime_checkable` |
| Faire passer l'aperçu par `PageRasterizer`, ajouter un port de géométrie PDF (`page_count`, `page_sizes`) sous verrou pdfium, injecter dans `DocumentService` et `AnalysisService`, faire appeler l'instance par le router, durcir `tests/test_architecture.py:300-314` | 6.1.4 (poids 2) | **+7 pts** (→ 94 seul ; **100** avec la ligne précédente) | M (≈ ½ à 1 j) | Modéré : `/preview`, `/pages`, comptage de pages à l'upload et en batch ; tests à réécrire contre un faux port |
| Supprimer `useDocumentStore().pushToStore` et son import | — (INFO 11) | 0 pt | XS | Nul |
| Mettre à jour la fiche 06 (`build_converter()`, `bootstrap/`, grep `from persistence`) | — (INFO 4) | 0 pt, mais le gate suivant détecte MAJ-2 par commande | XS | Nul |

---

## Points positifs

- **Aucune régression SOLID depuis 0.7.3.** La seule modification de service (`asyncio.to_thread` autour de `DoclingDocumentImporter.deserialize`, `services/analysis_service.py:177-180`) passe toujours par le port injecté, et le contrat d'erreur (`ValueError` → 400) est préservé.
- **Adaptateur MCP sans logique, dépendances injectées.** Les services sont résolus à chaque appel par `tools: Callable[[], DocumentTools]` (`mcp_adapter/server.py:95-96`, `bootstrap/mcp_mount.py:93-94`, `mcp_stdio.py:64-70`). Le même `build_mcp_server` sert HTTP et stdio.
- **Services document-agent derrière des ports**, verrouillés par un test AST qui mord (`tests/test_architecture.py:206-232`) : `PageRasterizer`, `PageTextReader`, `DocumentTreeReader`.
- **#344 au bon endroit.** La fusion Docling vit dans l'adaptateur (`infra/local_converter.py:157-179`), avec repli sur `domain.services.merge_results`.
- **Composition centralisée.** Les dépôts et les adaptateurs ne sont instanciés que dans `bootstrap/` et `mcp_stdio.py`. Aucun service n'instancie d'adaptateur.
- **Frontend : un store par feature, ce que l'item exige.** `ConfigSource` (partagé par `admin-config` et `mcp-config`) est désormais rangé dans `shared/types.ts` (remédiation 07 de 0.7.3).

---

## Verdict partiel : GO

- Score **87/100** (≥ 80), **0 CRITICAL**, **2 MAJOR** (≤ 3, donc non bloquant selon master §2), 0 MINOR, 12 INFO.
- Les deux MAJ sont de la dette de contrat et de découpage, sans risque de corruption ni de sécurité, inchangée depuis 0.7.3 et planifiée pour la 0.8.0.
- **Recommandation.** MAJ-2 se lève en S, sans risque runtime, pour +7 points. Comme il porte aussi sur des zones non dépréciées (`VersionService`, `find_by_document`), il mérite d'être traité dès la 0.7.4. Ce correctif clôt en même temps la question de lecture stricte de 6.5.1.
- **Point toujours à trancher par le mainteneur** : en lecture stricte de 6.5.1 (poids 3), le typage `Sqlite*` et l'absence de port de versions seraient un CRIT. Ce rapport garde la lecture opérationnelle des gates 0.7.0 et 0.7.3 (pas de dépendance runtime) et le classe MAJ.

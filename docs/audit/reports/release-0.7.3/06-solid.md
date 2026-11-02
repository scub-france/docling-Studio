# Rapport d'audit : SOLID

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68
**Baseline** : `docs/audit/reports/release-0.7.0/06-solid.md` (100/100, 0/0/0/4, GO) — pas de re-audit 06 en 0.7.0 (audit non touché par la remédiation)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 15 (27 / 31 pondérés) |
| Score | 87 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 10 |

Détail du calcul : poids conformes = 6.1.1 (2) + 6.1.2 (2) + 6.1.3 (1) + 6.2.2 (2) + 6.2.3 (1) + 6.3.1 (3) + 6.3.2 (2) + 6.3.3 (2) + 6.4.1 (2) + 6.4.2 (2) + 6.5.1 (3) + 6.5.2 (2) + 6.5.3 (3) = **27** sur **31**. Items non conformes : 6.1.4 (2), 6.2.1 (2). `27 / 31 * 100 = 87,1` → **87**.

**Delta vs 0.7.0** : **−13 points** (100 → 87). Voir la section « Delta vs 0.7.0 » : des deux MAJ, l'un est un écart **préexistant non détecté** par le gate 0.7.0, l'autre un écart préexistant **aggravé** par 0.7.3. Le nouveau code MCP (services document-agent, `mcp_adapter/`, composition) est, lui, conforme aux cinq principes.

### Périmètre mesuré

| Surface | 0.7.0 | 0.7.3 |
|---------|-------|-------|
| Ports `Protocol` (`domain/ports.py`) | 18 | 21 (+`DoclingDocumentImporter`, `PageRasterizer`, `PageTextReader`) |
| Classes de la couche `services/` | 11 | 17 (+`NavigationService`, `CitationService`, `CitationImageService`, `SourceService`, `ParseLoader`, `McpConfigService`) |
| Routers REST (`api/`) | 9 | 10 (+`api/mcp.py`) |
| Racines de composition | 1 (`bootstrap/` via `main.py`) | 2 (`bootstrap/` via `main.py` + `mcp_stdio.py`) |
| Stores Pinia de feature | 11 | 12 (+`mcp-config`) + 1 store partagé (`shared/breadcrumb`) |

---

## Checklist

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | ✅ (cf. INFO 5, 6, 9) |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | ✅ |
| 6.1.3 | Routes API groupées par ressource | 1 | ✅ |
| 6.1.4 | Aucune classe/module ne cumule des responsabilités hétérogènes (parsing ET persistence) | 2 | ❌ MAJ-1 |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier le code existant | 2 | ❌ MAJ-2 |
| 6.2.2 | Local/remote extensible via `build_converter()` sans modifier les services | 2 | ✅ |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | ✅ |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | ✅ (cf. INFO 1, 2, 10) |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | ✅ |
| 6.3.3 | Pas d'`isinstance()` / `type()` pour différencier les implémentations | 2 | ✅ |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | ✅ |
| 6.4.2 | Aucun port ne force une implémentation à définir des méthodes inutiles | 2 | ✅ (à la limite, cf. INFO 1) |
| 6.5.1 | Les services dépendent de ports, pas d'implémentations concrètes | 3 | ✅ (lecture opérationnelle, cf. note sous MAJ-2) |
| 6.5.2 | Injection au composition root | 2 | ✅ (cf. INFO 4) |
| 6.5.3 | Pas d'instanciation directe d'adaptateurs dans les services | 3 | ✅ |

---

## Vérification des principes

Méthode : lecture des sources du working tree à `02adc68` ; commandes de la fiche rejouées ; deux scripts AST (scratchpad, non versionnés) croisant, pour chaque service, les méthodes appelées sur ses collaborateurs injectés avec les méthodes déclarées par le port correspondant.

### SRP (6.1)

- **6.1.1 conforme** — les six nouvelles classes de service sont découpées par question, ce qui est le bon grain : `NavigationService` (trouver / cartographier / lire, `services/navigation_service.py:50`), `CitationService` (construire / résoudre / vérifier une citation, `services/citation_service.py:48`), `CitationImageService` (politique de rendu : page, échelle de dpi, budget d'octets, `services/citation_image_service.py:32`), `SourceService` (cas d'usage `show_sources`, `services/source_service.py:75`), `ParseLoader` (résolution `(document, version)` + cache, `services/parse_loader.py:44`), `McpConfigService` (précédence env/SQLite + hot-apply, `services/mcp_config_service.py:109`). Les règles de précédence communes aux deux services de config sont factorisées dans `services/config_overrides.py` (`pick`, `parse_*`, `require_writable`) au lieu d'être dupliquées. Dettes héritées et petites largeurs : INFO 5, 6, 9.
- **6.1.2 conforme** — 12 stores de feature, un `defineStore` par feature (`frontend/src/features/*/store.ts`) ; le nouveau panneau MCP a sa propre feature et son propre store (`features/mcp-config/store.ts:14`), distinct d'`admin-config` (reasoning). Le store `shared/breadcrumb/store.ts:13` est un store transverse partagé, pas un store de feature cumulé. Le batch d'analyses (#354) reste dans `features/analysis/store.ts:149` (`runBatch`) / `:170` (`followActive`) : même feature.
- **6.1.3 conforme** — un router par ressource ; ajouts 0.7.3 bien rangés : `GET /api/documents/{id}/pages` dans `api/documents.py:204`, `POST /api/analyses/import` et `GET /api/analyses/summaries` dans `api/analyses.py:73` / `:104`, `/api/config/mcp` dans `api/config.py:75`, `/api/mcp/server` dans son propre `api/mcp.py:16`. Le transport `/mcp` est un adaptateur pilotant distinct, monté par `bootstrap/mcp_mount.py:84`.
- **6.1.4 non conforme** — `DocumentService` (et dans une moindre mesure `AnalysisService`) cumule parsing/rendu PDF et persistence. → **MAJ-1**.

### OCP (6.2)

- **6.2.1 non conforme** — six ports déclarés sont incomplets par rapport à l'usage réel des services et un port manque ; un nouvel adaptateur écrit contre le `Protocol` casserait à l'exécution. → **MAJ-2**.
- **6.2.2 conforme** — sélection local/remote centralisée dans `build_converter()` (`bootstrap/factories.py:44`). `AnalysisService` ne connaît que la capacité (`supports_page_batching`, `services/analysis_service.py:448`) et délègue la fusion au port (`merge_batches`, `services/analysis_service.py:340`) : la fusion des lots #344 (`DoclingDocument.concatenate`) reste dans l'adaptateur (`infra/local_converter.py:157`), le service n'a pas bougé. (La fiche cite encore `_build_converter()`.)
- **6.2.3 conforme** — `export_document` (`api/documents.py:133`) ne reçoit que l'enum `ExportFormat` ; ajouter un format modifie la chaîne `if format is …` du service (`services/export_service.py:59-95`), pas l'endpoint.
- **Chaînes if/elif sur des types** : aucune nouvelle chaîne qui grossirait à chaque feature dans le code 0.7.3. La surface MCP s'étend par enregistrement de tool (`mcp_adapter/server.py:126-200`), le registre de feature flags frontend est une table (`features/feature-flags/store.ts`, `ask` ajouté sans toucher aux autres entrées). Les dispatchs existants sont bornés et préexistants : `StoreKind` dans `services/store_backend_resolver.py:109-115` (ingestion, dépréciée, retirée en 0.8.0) et la chaîne d'export ci-dessus ; les petits dispatchs sur labels Docling (`domain/element_reader.py:143`, `:233`) suivent une taxonomie externe stable.

### LSP (6.3)

- **6.3.1 conforme (poids 3)** — `LocalConverter` (`infra/local_converter.py:187`) et `ServeConverter` (`infra/serve_converter.py:71`) exposent les trois membres du port (`convert`, `supports_page_batching`, `merge_batches`) et rendent un `ConversionResult`. Le `document_json=None` possible côté Serve (`infra/serve_converter.py:258`) reste prévu par le contrat (`str | None`). `ServeConverter.merge_batches` n'est jamais appelé (précondition `supports_page_batching=True` jamais remplie) ; s'il l'était, il rendrait un résultat valide via `merge_results`. Divergences de forme et de fidélité : INFO 1, 2, 10.
- **6.3.2 conforme** — `ReasoningRunner` inchangé depuis 0.7.0 (traduction en `ReasoningParseError`). `LLMHostProbe` « ne lève jamais » : `OllamaProbe.probe` (modifié depuis 0.7.0 par la garde SSRF) mappe toujours les échecs en `LLMHostProbeResult(reachable=False)` (`infra/llm/ollama_probe.py:79-104`). `PageTextReader` : le contrat promet une liste vide pour une page illisible ; le seul appelant tolère toute exception (`services/source_service.py:158-162`). Le nouveau port `DoclingDocumentImporter` ne documente pas d'exception ; l'adaptateur lève `ValueError` (`infra/docling_importer.py:29`), convention `ValueError → 400` du projet, gérée par le router (`api/analyses.py:83-85`).
- **6.3.3 conforme** — grep de la fiche : les `isinstance` de `services/` valident des types primitifs de payload (`services/store_service.py:135`, `:139`, `services/chunk_service.py:218`, `services/mcp_config_service.py:71`), aucun ne distingue des adaptateurs.

### ISP (6.4)

- **6.4.1 conforme** — `DocumentConverter` (`domain/ports.py:55`) et `DocumentChunker` (`domain/ports.py:92`) restent séparés. Le nouveau code continue dans ce sens : l'import d'analyses (#359) a son propre port `DoclingDocumentImporter` (`domain/ports.py:86`) plutôt qu'une méthode de plus sur le converter ; le rendu de page et la couche texte sont deux ports distincts (`PageRasterizer` `:423`, `PageTextReader` `:449`) plutôt qu'un « port PDF » fourre-tout.
- **6.4.2 conforme, à la limite** — `merge_batches` (#344) est imposé à `ServeConverter`, qui l'implémente en code mort. Retenu conforme (ce n'est pas un stub, le client `AnalysisService` utilise les trois membres) mais signalé : INFO 1. `AnalysisRepository` grossit (+4 méthodes) : INFO 7.

### DIP (6.5)

- **6.5.1 conforme (poids 3), lecture opérationnelle** — grep de la fiche `from infra` sur `services/` : uniquement des imports sous `TYPE_CHECKING` (`services/store_backend_resolver.py:40-42`), aucun import runtime de `infra/` ni de `persistence/`. Tous les nouveaux services dépendent de ports : `CitationImageService` → `PageRasterizer` (`services/citation_image_service.py:37`), `SourceService` → `PageTextReader` (`services/source_service.py:83`), `ParseLoader` → `DocumentRepository` / `AnalysisRepository` / `DocumentTreeReader` (`services/parse_loader.py:48-50`), `McpConfigService` → `AppSettingsRepository` + callables injectés (`services/mcp_config_service.py:115-119`). **Mais** voir la note de lecture sous MAJ-2 : le typage contre des classes `Sqlite*` concrètes (préexistant) violerait 6.5.1 en lecture stricte.
- **6.5.2 conforme** — injection centralisée dans `bootstrap.AppStateBuilder` (`bootstrap/builder.py:98`), y compris le nouveau câblage MCP (`_wire_mcp`, `bootstrap/builder.py:228-262`) ; le serveur MCP reçoit ses services par une fonction de résolution injectée (`bootstrap/mcp_mount.py:93-94`, `mcp_adapter/server.py:95-124`). `mcp_stdio.py` est une seconde racine de composition qui **réutilise** les factories (`mcp_stdio.py:51`, `:63-70`) au lieu de dupliquer le câblage. Libellé de la fiche : INFO 4.
- **6.5.3 conforme (poids 3)** — grep `LocalConverter|ServeConverter|LocalChunker` sur `services/` : zéro. Aucun service n'instancie d'adaptateur ; tous les nouveaux adaptateurs (`PdfPageRasterizer`, `PdfPageTextReader`, `DoclingTreeReader`, `DoclingDocumentImporter`) sont construits dans `bootstrap/factories.py:201`, `:298-313`.

---

## Ecarts constates

### [MAJ] MAJ-1 — `DocumentService` cumule parsing / rendu PDF et persistence, aggravé en 0.7.3 alors que les ports existent désormais

- **Localisation** :
  - `document-parser/services/document_service.py:14-15` (`import pypdfium2 as pdfium` — ajouté en 0.7.3 par #352 ; `from pdf2image import convert_from_bytes, pdfinfo_from_bytes`)
  - `document-parser/services/document_service.py:171-188` (`page_sizes`, #352, nouveau en 0.7.3 : ouverture pdfium) et `:160-168` (`generate_preview` : rasterisation poppler)
  - `document-parser/services/document_service.py:191-212` (`_persist_and_count` : écriture disque `open(…, "wb")` ligne 199 + comptage poppler ligne 208), `:147` (`os.unlink`), `:108` / `:157` (dépôt)
  - `document-parser/api/documents.py:189` et `:216` : le router appelle `DocumentService.generate_preview` / `DocumentService.page_sizes` **sur la classe** (méthodes statiques), en contournant l'instance injectée
  - secondaire : `document-parser/services/analysis_service.py:17` + `:59-68` (`_count_pdf_pages` via pdfium), appelé sur la boucle d'événements `:446`
- **Constat** : `DocumentService` porte au moins trois raisons de changer : le stockage des fichiers (écriture, suppression, résolution de chemin `:119`), le CRUD documents via `DocumentRepository`, et la lecture/rendu PDF (comptage de pages, aperçu PNG, et depuis 0.7.3 tailles de page via pdfium). C'est littéralement le contre-exemple de l'item (« un service qui fait du parsing ET de la persistence »). Ce qui en fait un écart de **cette** release : 0.7.3 introduit précisément les ports qui devraient porter ce travail — `PageRasterizer` (`domain/ports.py:423`, adaptateur `infra/page_raster.py:23` qui fait exactement `convert_from_bytes` + PNG) et `PageTextReader` (`domain/ports.py:449`, adaptateur pdfium `infra/page_text.py:27`) — tout en ajoutant un nouvel usage direct de pdfium dans le service (`page_sizes`, #352). Le projet le sait : le test d'architecture garde `pdf2image`/`pypdfium2` comme « migration candidates » des services (`tests/test_architecture.py:314`) et exclut `document_service.py` de la règle « framework-free » parce qu'il « rasterises directly and predates the port » (`tests/test_architecture.py:213-214`). Conséquence concrète du contournement (PLAUSIBLE, à confirmer par l'audit 12) : l'adaptateur pdfium prend le verrou process-wide de Docling parce que « pdfium is not thread-safe » (`infra/page_text.py:7-9`, `:21-24`, `:31`), alors que `page_sizes` (exécuté en thread, `api/documents.py:216`) et `_count_pdf_pages` (exécuté sur la boucle, `services/analysis_service.py:446`) ouvrent pdfium sans ce verrou, potentiellement en concurrence avec une conversion Docling locale en cours.
- **Regle violee** : item 6.1.4 — « Aucune classe ou module ne cumule des responsabilités hétérogènes (ex : un service qui fait du parsing ET de la persistence) » (poids 2). Même constat que l'audit 01 de 0.7.0 (MAJ 1.2.4, dette portée), ici sous l'angle SRP.
- **Remediation** : faire passer l'aperçu par `PageRasterizer.render_page` (il existe déjà) ; ajouter au port de lecture PDF une opération de géométrie (`page_sizes(storage_path) -> list[PageDetail]`, et `page_count`) implantée dans `infra/` sous le verrou pdfium ; injecter ces ports dans `DocumentService` / `AnalysisService` via `bootstrap/factories.py` ; faire appeler le router sur l'instance injectée. Une fois fait, retirer `pdf2image`/`pypdfium2` de `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` et les ajouter à `_SERVICES_FORBIDDEN_EXTERNALS` (`tests/test_architecture.py:314`, `:300`).

### [MAJ] MAJ-2 — Contrats de ports incomplets ou absents : les services consomment 13 méthodes hors protocole et `VersionService` n'a pas de port

- **Localisation** :
  - Méthodes appelées par un service mais absentes du `Protocol` déclaré :
    - `AnalysisRepository` (`domain/ports.py:207`) : `find_by_document` — `services/analysis_service.py:201`
    - `ChunkPushRepository` (`domain/ports.py:197`) : `count_for_document`, `find_for_document` — `services/chunk_service.py:711`, `:714`
    - `VectorStore` (`domain/ports.py:256`) : `search_fulltext` — `services/ingestion_service.py:277`
    - `StoreRepository` (`domain/ports.py:128`) : `find_by_name`, `clear_default_except`, `update`, `set_connection_password`, `delete`, `insert(…, password=)` — `services/store_service.py:214`, `:233`, `:297`, `:303`, `:395`, `:231` ; `get_connection_password` — `services/store_backend_resolver.py:128`, `:143`
    - `DocumentStoreLinkRepository` (`domain/ports.py:142`) : `count_by_store` — `services/store_service.py:163`
    - `DocumentRepository` (`domain/ports.py:105`) : `find_by_ids` — `services/store_service.py:361`
  - Port absent : aucun `DocumentVersionRepository` dans `domain/ports.py` ; `VersionService` est typé contre `SqliteDocumentVersionRepository` (`services/version_service.py:32`, `:87`) et en consomme `find_for_document` / `insert` / `find_by_id` (`:99`, `:124`, `:154`).
  - Services typés contre des classes concrètes (sous `TYPE_CHECKING`) alors que le port existe : `services/store_service.py:148-150`, `services/chunk_service.py:159-160`, `services/store_backend_resolver.py:81-83` (dont les pools `infra`), et `IngestionTargets.vector_store: OpenSearchStore` au lieu de `VectorStore` (`services/store_backend_resolver.py:61`).
- **Constat** : les ports sont des `Protocol` structurels ; le contrat réel des services est plus large que le contrat déclaré. Un adaptateur écrit contre `domain/ports.py` (un dépôt Postgres, un double de test fidèle au port) passerait toute vérification statique et lèverait `AttributeError` sur `GET /api/analyses?documentId=…`, l'historique des pushes, la recherche plein texte, toute la gestion des stores et tout l'historique de versions. Ajouter un adaptateur impose donc de modifier `domain/ports.py`, voire les signatures des services : c'est exactement ce que l'item interdit. Aucun garde-fou ne l'attrape : pas de type-checker en CI (aucune config mypy/pyright dans `document-parser/pyproject.toml`) et la règle pytestarch `services → persistence` est inopérante, comme le documente le test lui-même (« the rules never see an edge … adding `from persistence.database import get_connection` to a `services/` module leaves every rule green », `tests/test_architecture.py:186-193`). Tout est **préexistant** (git blame : avril–mai 2026, avant le gate 0.7.0), non détecté en 0.7.0 parce que la commande de la fiche ne cherche que `from infra`. L'essentiel se concentre dans la zone Store/ingestion, dépréciée et retirée en 0.8.0 ; `VersionService` (historique de versions) et `AnalysisService.find_by_document` ne le sont pas.
- **Regle violee** : item 6.2.1 — « Les ports (`domain/ports.py`) permettent d'ajouter de nouveaux adaptateurs sans modifier le code existant » (poids 2).
- **Note de lecture (6.5.1)** : en lecture stricte, `VersionService` (aucun port) et les services typés `Sqlite*` « dépendent d'implémentations concrètes », ce qui ferait échouer 6.5.1 (poids 3 → CRIT → NO-GO). Ce n'est **pas** retenu ici, pour trois raisons : (a) aucune dépendance runtime — les imports sont sous `TYPE_CHECKING` et l'objet injecté par `bootstrap/` est substituable par duck typing ; (b) le gate 0.7.0 a explicitement accepté ce motif pour `store_backend_resolver.py:40-42` (« jamais du runtime ») ; (c) l'écart est préexistant, accepté par trois gates, et majoritairement en zone dépréciée. Le constat est donc classé sous 6.2.1 (MAJ). Si le mainteneur retient la lecture stricte, cet écart devient CRIT — décision à trancher explicitement.
- **Remediation** : (1) compléter les `Protocol` avec les méthodes réellement consommées (`find_by_document`, `count_for_document` / `find_for_document` sur `ChunkPushRepository`, `search_fulltext`, `count_by_store`, `find_by_ids`, les méthodes CRUD/secret de `StoreRepository`) ; (2) créer `DocumentVersionRepository` dans `domain/ports.py` ; (3) retyper les constructeurs de `StoreService`, `ChunkService`, `StoreBackendResolver`, `VersionService` sur les ports, et `IngestionTargets.vector_store` sur `VectorStore` (le ménage Store/ingestion peut attendre son retrait en 0.8.0, `VersionService` et `AnalysisRepository` non) ; (4) poser un garde-fou qui mord : un test AST comme celui des services document-agent (`tests/test_architecture.py:206-232`) interdisant `persistence`/`infra` même sous `TYPE_CHECKING` dans `services/`, et/ou un `mypy --strict` ciblé sur `services/` en CI.

### [INFO] INFO 1 — `merge_batches` (#344) imposé à `ServeConverter`, qui l'implémente en code mort

- **Localisation** : `document-parser/domain/ports.py:79-83` ; `document-parser/infra/serve_converter.py:95-98`.
- **Constat** : le port ajoute `merge_batches`, « Only called when `supports_page_batching` is True ». `ServeConverter` (flag à `False`) doit l'implémenter et le dit lui-même : « Not reached while `supports_page_batching` is False ». Le couple « drapeau de capacité + méthode valide seulement si le drapeau est vrai » est un motif ISP classique. Retenu conforme à 6.4.2 : l'implémentation n'est pas un stub (`merge_results` rend un résultat valide) et le client utilise les trois membres.
- **Regle** : 6.4.2 (à la limite).
- **Remediation** : optionnel — regrouper la capacité dans un objet dédié (p.ex. `converter.batching -> PageBatching | None`, porteur de `merge`) ou un sous-port `PageBatchingConverter` sélectionné au composition root, ce qui supprime aussi le booléen.

### [INFO] INFO 2 — `supports_page_batching` : `@property` au port, attribut de classe aux adaptateurs (baseline, inchangé)

- **Localisation** : `document-parser/domain/ports.py:70-77` vs `document-parser/infra/local_converter.py:192` et `document-parser/infra/serve_converter.py:77`.
- **Constat** : identique à 0.7.0 ; lecture par duck typing (`services/analysis_service.py:448`), pas de rupture.
- **Regle** : 6.3.1 (forme du protocole).
- **Remediation** : homogénéiser la forme (à traiter avec INFO 1).

### [INFO] INFO 3 — `ServeConverter.health_check()` toujours orphelin (baseline, inchangé)

- **Localisation** : `document-parser/infra/serve_converter.py:189`.
- **Constat** : toujours absent du port et de `LocalConverter`, toujours sans appelant (grep sur `api/`, `services/`, `bootstrap/`, `main.py`, `mcp_stdio.py`, `mcp_adapter/` : nul).
- **Regle** : 6.3.1 / 6.4.2.
- **Remediation** : supprimer, ou promouvoir dans le port si un health-check du converter devient un besoin.

### [INFO] INFO 4 — Composition root : libellés de fiche périmés, et désormais deux racines (baseline, étendu)

- **Localisation** : `document-parser/bootstrap/builder.py:70`, `document-parser/bootstrap/factories.py`, appelés par `document-parser/main.py:51-55` ; seconde racine `document-parser/mcp_stdio.py:48-78` ; fiche `docs/audit/audits/06-solid.md` items 6.2.2 et 6.5.2.
- **Constat** : 6.5.2 cite toujours `main.py` et 6.2.2 `_build_converter()` (nom réel : `build_converter()`, `bootstrap/factories.py:44`). 0.7.3 ajoute une seconde racine, `mcp_stdio.py`, qui construit le strict nécessaire en réutilisant `build_parse_loader` / `build_document_tools` / `env_mcp_config` : conforme à l'esprit, à tracer dans la fiche.
- **Regle** : 6.5.2 / 6.2.2 (libellés).
- **Remediation** : mettre à jour la fiche : « composition root : `bootstrap/` (via `main.py` et `mcp_stdio.py`) », « `build_converter()` » ; et étendre la commande de vérification 6.5.1 à `from persistence` (cf. MAJ-2).

### [INFO] INFO 5 — Dette SRP héritée : `AnalysisService` (édition legacy du blob) et `ChunkService` (baseline, toujours présent)

- **Localisation** : `document-parser/services/analysis_service.py:215` (`rechunk`), `:239` (`update_chunk_text`), `:261` (`delete_chunk`) ; `document-parser/services/chunk_service.py:146` (classe), `:540` (`diff_against_store`), `:574` (`push_to_store`), `:693` (`list_pushes`), `:789` (`get_tree`).
- **Constat** : les méthodes legacy d'`AnalysisService` sont toujours là ; le service passe de 554 à 586 lignes avec l'import d'analyses (#359, `:165`), qui reste un cas d'usage d'analyse. `ChunkService` (1019 lignes, inchangé depuis 0.7.0) mêle cycle de vie des chunks, push vers les stores et projection d'arbre ; le retrait de l'ingestion en 0.8.0 obligera à le modifier, signe de plusieurs raisons de changer. Déjà porté en MAJ par l'audit 03 (dette 0.7.0) : pas de double comptage ici.
- **Regle** : 6.1.1 (observation de largeur).
- **Remediation** : profiter du retrait de l'ingestion en 0.8.0 pour sortir push/diff/historique de `ChunkService`, et `get_tree` vers un service de lecture d'arbre ; déprécier l'édition du blob `chunks_json`.

### [INFO] INFO 6 — `ParseLoader` expose ses dépôts : dépendances cachées de `NavigationService` / `CitationService`

- **Localisation** : `document-parser/services/parse_loader.py:60-68` (propriétés `analyses`, `documents`) ; consommateurs `document-parser/services/navigation_service.py:82`, `:87` et `document-parser/services/citation_service.py:198`.
- **Constat** : `ParseLoader` a été extrait pour que les services ne dépendent plus « des trois mêmes dépôts » (`services/parse_loader.py:3-6`), mais il les republie, et deux services passent au travers (`self._parses.documents.find_all(…)`, `self._parses.analyses.latest_parsed_ids(…)`). Leur constructeur ne déclare que `parses` : la dépendance réelle à `DocumentRepository` / `AnalysisRepository` est invisible (loi de Déméter, DIP « déclaré »).
- **Regle** : 6.1.1 / 6.5.1 (dépendances explicites) — observation.
- **Remediation** : donner à `ParseLoader` les deux requêtes nommées (`find_documents(query, limit)`, `latest_version(document_id)`) et retirer les propriétés, ou injecter explicitement les dépôts là où ils servent.

### [INFO] INFO 7 — `AnalysisRepository` grossit (+4 méthodes en 0.7.3) alors que la surface MCP est en lecture seule

- **Localisation** : `document-parser/domain/ports.py:207-240` (14 méthodes ; ajouts `find_all_summaries` `:214`, `latest_parsed_ids` `:226`, `parsed_document_id` `:228`, `parse_json` `:230`) ; consommateur `document-parser/services/parse_loader.py:83`, `:89`, `:107` ; `document-parser/mcp_stdio.py:65`.
- **Constat** : la surface document-agent, « Read-only » par conception (`mcp_adapter/server.py:14-16`), dépend d'un port de 14 méthodes dont elle n'utilise que 3 ; l'entrée stdio construit donc un dépôt doté de toutes les écritures. Pas de violation de 6.4.2 (l'unique implémentation SQLite utilise tout), mais ISP côté client.
- **Regle** : 6.4.2 (ISP côté client) — observation.
- **Remediation** : extraire un port lecture `ParseReader` (`latest_parsed_ids`, `parsed_document_id`, `parse_json`) implanté par le même dépôt, et typer `ParseLoader` dessus.

### [INFO] INFO 8 — `PageRasterizer.crop` détourné en transcodeur

- **Localisation** : `document-parser/services/citation_image_service.py:89-91` ; port `document-parser/domain/ports.py:436-445`.
- **Constat** : pour réencoder la page en WEBP, le service appelle `crop(page_png, (0, 0, 10_000, 10_000), fmt="WEBP")` et compte sur le clamp de l'adaptateur. Le clamp est au contrat, donc pas de rupture LSP, mais le port n'exprime pas l'opération voulue (rendre une page dans un format).
- **Regle** : 6.4.2 / 6.3.1 (adéquation du port) — observation.
- **Remediation** : `render_page(storage_path, page=…, dpi=…, fmt=…)` ou une opération `encode(png, fmt)` explicite.

### [INFO] INFO 9 — Découpage SRP hétérogène dans le nouvel adaptateur MCP et son service de config

- **Localisation** : `document-parser/mcp_adapter/sources_view.py` (369 lignes : dataclasses de contrat `:42-151`, enregistrement des tools `:163-209`, mapping `:223-335`, rendu texte `:338-369`) ; `document-parser/mcp_adapter/apps.py:73-106` (contrat `CitationView`) + `:123-228` (enregistrement) ; `document-parser/services/mcp_config_service.py:186-188` (`server_status`) ; `document-parser/bootstrap/mcp_mount.py:128-148` (mapping SDK → VO domaine), `:151-169` (middleware ASGI).
- **Constat** : pour les quatre tools du cœur, le contrat (`wire.py`), la traduction (`wire_mapping.py`) et l'enregistrement (`server.py`) sont séparés, et `wire_mapping.py:3-6` explique pourquoi (« mixing the two made a single 370-line module »). Les deux cartes MCP Apps reviennent au module mixte (découpage par feature plutôt que par rôle). `McpConfigService` sert aussi de rapporteur d'état du serveur (simple délégation), et `bootstrap/mcp_mount.py` héberge un middleware et un mapping d'adaptateur en plus du câblage. Rien de bloquant : chaque module reste cohésif autour d'une carte ou du montage.
- **Regle** : 6.1.1 / 6.1.4 — observation.
- **Remediation** : aligner les cartes sur le découpage `wire` / `wire_mapping` / registration ; optionnellement un petit `McpServerStatusService` (ou exposer `status_provider` directement via `deps`).

### [INFO] INFO 10 — Fidélité remote vs local : `PageElement.level` toujours 0 côté Docling Serve (préexistant)

- **Localisation** : `document-parser/infra/serve_converter.py:377` (`level=0`) vs `document-parser/infra/docling_pages.py:107` (`level=level` issu de `iterate_items`) ; consommé par `frontend/src/features/analysis/ui/ResultTabs.vue:49`, `:275`, `:280` et `frontend/src/features/document/ui/ElementProperties.vue:24`.
- **Constat** : même type de retour, mais en mode remote les éléments arrivent sans niveau : indentation et badge `L{n}` différents selon le moteur. Le contrat de `ConversionResult` / `PageElement` ne spécifie pas la sémantique de `level` : pas de rupture LSP au sens de la fiche, mais divergence de fidélité.
- **Regle** : 6.3.1 (postcondition implicite) — observation.
- **Remediation** : dériver le niveau côté Serve (profondeur dans l'arbre `body` du `json_content`, déjà parcouru par `DoclingTreeReader.dfs_order`), ou documenter `level` comme optionnel (0 = inconnu).

---

## Delta vs 0.7.0

**Score** : 100 → **87** (−13). **Écarts** : 0/0/0/4 → **0/2/0/10**.

| Écart 0.7.0 | Statut 0.7.3 |
|-------------|--------------|
| [INFO] `supports_page_batching` @property vs attribut | **Toujours présent**, inchangé → INFO 2 |
| [INFO] `ServeConverter.health_check()` orphelin | **Toujours présent**, inchangé (ligne 183 → 189) → INFO 3 |
| [INFO] Composition root déplacé vers `bootstrap/` (libellé fiche) | **Toujours présent, étendu** : seconde racine `mcp_stdio.py`, fiche non mise à jour → INFO 4 |
| [INFO] `AnalysisService` : méthodes legacy du blob `chunks_json` | **Toujours présent** (lignes 182/206/228 → 215/239/261), service 554 → 586 lignes → INFO 5 |

| Nouvel écart | Origine |
|--------------|---------|
| [MAJ] MAJ-1 `DocumentService` parsing + persistence (6.1.4) | **Préexistant aggravé par 0.7.3** : `pdf2image` déjà présent (signalé en 0.7.0 par l'audit 01, pas par l'audit 06) ; 0.7.3 ajoute `pypdfium2` + `page_sizes` (#352) alors que les ports `PageRasterizer` / `PageTextReader` arrivent dans la même release |
| [MAJ] MAJ-2 ports incomplets / absents (6.2.1) | **Préexistant non détecté** (avril–mai 2026) : la commande de la fiche ne cherche que `from infra`, et la règle pytestarch `services → persistence` est inopérante (`tests/test_architecture.py:186-193`) |
| [INFO] INFO 1, 6, 7, 8, 9 | **Nouveau code 0.7.3** (#344, MCP document-agent, #364) |
| [INFO] INFO 10 | Préexistant, non relevé en 0.7.0 |

Lecture honnête du delta : les −13 points viennent de deux items qui auraient pu tomber dès 0.7.0 (l'un pleinement, l'autre partiellement). Le gros du code nouveau de 0.7.3 (≈ 9 000 lignes backend : services document-agent, `mcp_adapter/`, `bootstrap/mcp_mount.py`, `mcp_stdio.py`, config MCP) n'introduit aucun écart d'item ; il n'apporte que des observations INFO.

---

## Points positifs

- **Adaptateur MCP sans logique, dépendances injectées** : chaque tool se résume à un mapping et une traduction d'erreurs (`mcp_adapter/server.py:134-200`) ; les services sont résolus à chaque appel via `tools: Callable[[], DocumentTools]` fourni par la racine de composition (`bootstrap/mcp_mount.py:93-94`, `mcp_stdio.py:69`). Le même `build_mcp_server` sert HTTP et stdio sans une ligne de câblage dupliquée. DIP exemplaire.
- **Services document-agent découpés par question, infra derrière des ports** : rasterisation (`PageRasterizer`), couche texte (`PageTextReader`), arbre Docling (`DocumentTreeReader`) ; un test AST verrouille ces modules « framework-free » et liste explicitement les services pairs injectés (`tests/test_architecture.py:206-232`). C'est le garde-fou qui manque ailleurs (cf. MAJ-2).
- **#344 fait au bon endroit** : la fusion des lots, qui exige Docling, vit dans l'adaptateur (`infra/local_converter.py:157-179`) derrière le port, avec repli sur `domain.services.merge_results` ; le domaine n'importe toujours pas Docling, le service n'a pas changé.
- **#359 avec un port dédié** : `DoclingDocumentImporter` (`domain/ports.py:86`) plutôt qu'une méthode de plus sur le converter ; l'import réutilise le chemin de finalisation (`services/analysis_service.py:165-189`).
- **Config MCP calquée sur la config reasoning, sans copier-coller** : précédence et parsing partagés (`services/config_overrides.py:79-100`), infra et SDK injectés en callables (`apply_config`, `status_provider`) : le service n'importe ni `infra` ni le SDK (`services/mcp_config_service.py:16-18`). Le hot-apply réutilise le rebind atomique de l'`AppState` gelé (`bootstrap/builder.py:240-246`).
- **Erreurs typées, traduites une fois** : la famille `NavigationServiceError` porte son statut HTTP (`services/navigation_errors.py:13-51`), `ToolErrors` la convertit et masque les crashs (`mcp_adapter/tool_errors.py:29-53`).
- **Frontend** : le panneau MCP a sa feature et son store propres (`features/mcp-config/store.ts:14`), séparés du reasoning ; `ask` entre dans le registre de feature flags sans toucher aux autres entrées.

---

## Verdict partiel : GO

Score **87/100** (≥ 80), **0 CRITICAL**, **2 MAJOR** (≤ 3, non bloquant selon master §2), 0 MINOR, 10 INFO. Les deux MAJ sont de la dette de contrat et de découpage, sans risque de corruption ni de sécurité ; ils rejoignent la dette suivie avec un plan de remédiation (MAJ-1 : router l'aperçu et les tailles de page par les ports PDF déjà livrés ; MAJ-2 : compléter les `Protocol`, créer `DocumentVersionRepository`, poser un garde-fou qui mord). **Point à trancher par le mainteneur** : en lecture stricte de 6.5.1, le typage `Sqlite*` et l'absence de port de versions (MAJ-2) seraient un CRIT ; ce rapport retient la lecture opérationnelle du gate 0.7.0 (pas de dépendance runtime) et le classe MAJ.

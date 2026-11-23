# Rapport d'audit : SOLID

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : working tree de la branche `fix/0.7.4-editor-followups` au commit `a6fb539` (`release/0.7.4` @ `f7fc791`, avec #401 et #402, plus 13 commits de correctifs #391-#400 et le merge).
**Baseline** : `docs/audit/reports/release-0.7.4/06-solid.md` (2026-11-13, `eade7fa`) : 87/100, 0 CRIT, 2 MAJ, 0 MIN, 15 INFO, GO.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 15 (27 / 31 pondérés) |
| Score | 87 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 17 |

Calcul : poids conformes = 2 + 2 + 1 + 2 + 1 + 3 + 2 + 2 + 2 + 2 + 3 + 2 + 3 = **27** sur **31**. Items non conformes : 6.1.4 (2) et 6.2.1 (2). `27 / 31 × 100 = 87,1`, donc **87**.

Même lecture que la baseline, pour que les scores restent comparables : 6.5.1 est jugé en lecture opérationnelle (pas d'import runtime de concrétion `infra/`/`persistence/` dans `services/`, injection au composition root). Voir le point à trancher dans le verdict.

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | oui | `PreviewService` (50 l.) n'a qu'un cas d'usage. `ChunkService` (921 l.) et `AnalysisEditService` (405 l.) restent cohérents (INFO 5, 11). |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | oui | 14 `defineStore`, un par feature. Les diffs des stores `analysis`, `history` et `analysis-editor` restent dans leur feature. |
| 6.1.3 | Routes API groupées par ressource | 1 | oui | Route preview sur `api/documents.py:173`, routes éditeur dans `api/analysis_edits.py`, traduction d'erreurs centralisée dans `api/errors.py`. |
| 6.1.4 | Aucun module ne cumule des responsabilités hétérogènes | 2 | **non** | `DocumentService` fait toujours rendu PDF (pdf2image, pypdfium2) et persistence. `PreviewService` passe par lui en appel statique. MAJ-1. |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier l'existant | 2 | **non** | Le moteur d'édition a maintenant son port (#394). Restent 15 appels hors `Protocol`, aucun port de versions, `graph_writer` et `active_result_service` non typés. MAJ-2. |
| 6.2.2 | Local/remote extensible via `build_converter()` | 2 | oui | `bootstrap/factories.py`, `infra/local_converter.py` et `infra/serve_converter.py` sont inchangés depuis `eade7fa`. |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | oui | `export_document` (`api/documents.py:134`) reçoit `ExportFormat`. Le dispatch par format est fait une seule fois dans `ExportService._export` (`services/export_service.py:75-112`). |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | oui | Fichiers non modifiés. Les constats de la baseline tiennent (INFO 1, 2, 10). |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | oui | Les nouveaux adaptateurs (`PreviewCache`, `DoclingAnalysisEngine`, méthodes batch de `SqliteChunkRepository`, `complete_and_select`) respectent leur port. Le contrat d'exception du moteur n'est pas écrit (INFO 14). |
| 6.3.3 | Pas d'`isinstance()`/`type()` pour différencier les implémentations | 2 | oui | Le grep de la fiche sur `services/` ne trouve que de la validation de payload (`store_service.py:131`, `:135`, `chunk_service.py:205`, `mcp_config_service.py:71`). |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | oui | Inchangé (`domain/ports.py:63`, `:106`). Nouveaux ports étroits : `PreviewImageCache` (2 méthodes) et `AnalysisDocumentEngine` (2 méthodes). |
| 6.4.2 | Aucun port n'impose de méthodes inutiles | 2 | oui | Les 3 méthodes ajoutées à `ChunkRepository` (`ports.py:211-222`) sont implémentées (`persistence/chunk_repo.py:105`, `:118`, `:132`) et utilisées. `merge_batches` reste un cas d'INFO (INFO 1). |
| 6.5.1 | Les services dépendent de ports | 3 | oui (lecture opérationnelle) | Aucun import runtime de `infra/` ou `persistence/` dans `services/`. Restent des typages `Sqlite*` sous `TYPE_CHECKING`, et `PreviewService` dépend de la classe `DocumentService` (cf. MAJ-1, MAJ-2 et le point à trancher). |
| 6.5.2 | Injection au composition root | 2 | oui | `DoclingAnalysisEngine()`, `PreviewCache()` et `PreviewService(...)` sont construits dans `bootstrap/builder.py:131` et `:172`. |
| 6.5.3 | Pas d'instanciation d'adaptateurs dans les services | 3 | oui | Grep `LocalConverter\|ServeConverter\|LocalChunker\|PreviewCache\|DoclingAnalysisEngine\|Sqlite*()` sur `services/` : zéro résultat. |

### Méthode

J'ai lu les sources du working tree à `a6fb539` et parcouru `git diff eade7fa a6fb539` (121 fichiers). J'ai rejoué les trois greps de la fiche. J'ai aussi écrit un script AST, en lecture seule, qui croise chaque `self._x.méthode()` d'un service avec le `Protocol` qui type `x` : c'est la source de la liste de MAJ-2. Je n'ai lancé ni les tests, ni l'application, ni un build. Les résultats de CI cités en contexte (1501 tests backend passés, 586 en frontend) viennent de l'appelant.

---

## Ecarts constates

### [MAJ] MAJ-1 : `DocumentService` cumule rendu PDF et persistence, et `PreviewService` s'appuie dessus en appel statique (reconduit, étendu)

- **Localisation** :
  - `document-parser/services/document_service.py:14-15` : imports `pypdfium2`, `pdf2image` ;
  - `document-parser/services/document_service.py:159-179` : `generate_preview`, une méthode statique qui fait `convert_from_path` et l'encodage PNG/WebP ;
  - `document-parser/services/document_service.py:181-202` : `page_sizes`, méthode statique pdfium ;
  - `document-parser/services/document_service.py:96`, `:147`, `:205-216` : `os.unlink`, écriture disque, `_persist_and_count` ;
  - `document-parser/services/document_service.py:108`, `:140`, `:157` : persistence via les dépôts ;
  - **nouveau** : `document-parser/services/preview_service.py:8` (import runtime de `DocumentService`), `:23` (constructeur typé sur la classe concrète `DocumentService`), `:42-48` (`asyncio.to_thread(DocumentService.generate_preview, ...)`, appelé sur la classe et non sur `self._documents`) ;
  - `document-parser/api/documents.py:14` et `:215` : appel statique `DocumentService.page_sizes` depuis le routeur ;
  - secondaire : `document-parser/services/analysis_service.py:17` (`pypdfium2`).
- **Constat** : la responsabilité n'a pas bougé depuis 0.7.3. #401 a sorti l'orchestration de l'aperçu dans un `PreviewService`, mais le rendu reste dans `DocumentService`. Il est appelé de façon statique, donc sans passer par l'instance injectée. Remplacer le moteur de rendu (poppler par pdfium ou PDF.js côté serveur, ou un double de test) oblige à modifier `DocumentService` ou `PreviewService` : l'injection n'aide pas. Le port `PageRasterizer` (`domain/ports.py:514-536`) existe pourtant, et son adaptateur `PdfPageRasterizer.render_page` (`infra/page_raster.py:26-34`) fait le même `convert_from_path` depuis #398. Il y a donc deux implémentations du rendu d'une page, et le nouveau service a pris celle qui n'est pas derrière un port. Le test d'architecture le reconnaît : `pdf2image` et `pypdfium2` restent dans `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` (`tests/test_architecture.py:210`).
- **Regle violee** : item 6.1.4, « aucune classe ou module ne cumule des responsabilités hétérogènes (ex : parsing ET persistence) », poids 2.
- **Remediation** :
  1. Injecter un `PageRasterizer` dans `PreviewService` au lieu de `DocumentService.generate_preview`, et ajouter le format de sortie au port (`render_page(..., fmt)`) ou appeler `crop` pour le WebP.
  2. Ajouter un port de géométrie (`page_sizes`) implémenté dans `infra/`, et l'injecter dans `DocumentService`, ou dans un service dédié appelé par `api/documents.py:215`.
  3. Faire dépendre `PreviewService` d'un port de lecture de documents (`DocumentRepository` et un résolveur de chemin) plutôt que de `DocumentService`.
  4. Basculer `pdf2image` et `pypdfium2` dans `_SERVICES_FORBIDDEN_EXTERNALS`.

  Effort M.

### [MAJ] MAJ-2 : contrats de ports incomplets ou absents (reconduit, réduit)

- **Localisation**. Méthodes appelées par un service, mais absentes du `Protocol` qui type la dépendance (le script AST les a toutes trouvées, puis je les ai relues à la main) :
  - `AnalysisRepository` (`domain/ports.py:246`) : `find_by_document`, appelé dans `services/analysis_service.py:204` ;
  - `ChunkPushRepository` (`domain/ports.py:236-243`) : `count_for_document` (`services/chunk_service.py:611`) et `find_for_document` (`:614`). Les deux sont implémentés dans `persistence/chunk_push_repo.py:62`, `:86` ;
  - `StoreRepository` (`domain/ports.py:170-181`) : `find_by_name` (`services/store_service.py:210`, `:253`), `clear_default_except` (`:229`, `:302`), `update` (`:293`), `set_connection_password` (`:299`), `delete` (`:391`) et `get_connection_password` (`services/store_backend_resolver.py:128`, `:143`) ;
  - `DocumentStoreLinkRepository` (`domain/ports.py:184-197`) : `count_by_store`, appelé dans `services/store_service.py:159` ;
  - `DocumentRepository` : `find_by_ids`, appelé dans `services/store_service.py:357` ;
  - `VectorStore` : `search_fulltext`, appelé dans `services/ingestion_service.py:277`.

  Services typés sur des concrétions alors qu'un port existe ou manque :
  - `VersionService` est typé `SqliteDocumentVersionRepository` (`services/version_service.py:39`, `:89`) et il n'existe aucun `DocumentVersionRepository`. Méthodes consommées : `:105`, `:133`, `:157`, `:163` ;
  - `ChunkService` : `store_repo: SqliteStoreRepository`, `link_repo: SqliteDocumentStoreLinkRepository` (`services/chunk_service.py:49-50`, `:146-147`) ;
  - `StoreService` : `services/store_service.py:24-26` et `:144-146` ;
  - `StoreBackendResolver` : `services/store_backend_resolver.py:40-43` et `:81`.

  Dépendances sans type :
  - `graph_writer=None` (`services/analysis_edit_service.py:63`), alors que le port `GraphWriter` existe (`domain/ports.py:567`) ;
  - `active_result_service=None` (`services/chunk_service.py:149`, `services/export_service.py:43`). Méthodes appelées : `load_active_result` (`chunk_service.py:371`, `:704`, `export_service.py:138`), `load_editor` (`export_service.py:147`) et l'attribut `.job` de l'`EditorSnapshot`.
- **Constat** : le gros morceau de la baseline est réglé. Le moteur d'édition passe derrière `AnalysisDocumentEngine` (`domain/ports.py:305-331`), et `AnalysisEditService` est typé dessus (`services/analysis_edit_service.py:62`). Aucun type Docling ne traverse plus le service, et l'adaptateur `DoclingAnalysisEngine` compose éditeur et projecteur (`infra/docling_analysis_engine.py:14-60`). `ChunkRepository` a aussi été complété en même temps que son adaptateur (#398). En revanche, aucun des autres ports incomplets n'a bougé. Plusieurs fichiers concernés ont pourtant été touchés dans cet intervalle : `chunk_push_repo.py`, `store_repo.py`, `document_store_link_repo.py`, `document_version_repo.py`, `version_service.py` et `store_service.py` figurent tous dans le diff. Écrire un autre adaptateur, par exemple Postgres, pour les stores, les versions ou les pushes oblige à lire la classe SQLite, puis à modifier `domain/ports.py` : c'est exactement ce que l'item interdit.
- **Regle violee** : item 6.2.1, « les ports permettent d'ajouter de nouveaux adaptateurs sans modifier le code existant », poids 2.
- **Remediation** :
  1. Compléter `AnalysisRepository.find_by_document`, `ChunkPushRepository` (`count_for_document`, `find_for_document`), `StoreRepository` (6 méthodes), `DocumentStoreLinkRepository.count_by_store`, `DocumentRepository.find_by_ids` et `VectorStore.search_fulltext`.
  2. Créer `DocumentVersionRepository`, puis retyper `VersionService`, `ChunkService`, `StoreService` et `StoreBackendResolver` sur les ports.
  3. Typer `graph_writer: GraphWriter | None`, et définir un port de lecture `ActiveAnalysisResult` (`load_active_result`, `load_editor`) pour `ChunkService` et `ExportService`.
  4. Ajouter un garde-fou : un mypy ciblé sur `services/`, ou un test AST qui refuse `persistence.*` même sous `TYPE_CHECKING`. Le script utilisé pour cet audit fait 30 lignes et pourrait servir de test.

  Effort M. Les points 1 et 2 sont mécaniques.

### [INFO] INFO 1 : `merge_batches` imposé à `ServeConverter`, qui l'implémente en code mort (reconduit)

- **Localisation** : `document-parser/domain/ports.py:87-90` ; `document-parser/infra/serve_converter.py:95-98`.
- **Constat** : inchangé.
- **Remediation** : inchangée. Port optionnel `PageBatchMerger`, ou capacité séparée.

### [INFO] INFO 2 : `supports_page_batching` est une `@property` dans le port mais un attribut dans les adaptateurs (reconduit)

- **Localisation** : `document-parser/domain/ports.py:79` ; `document-parser/infra/local_converter.py:192` ; `document-parser/infra/serve_converter.py:77`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 3 : `ServeConverter.health_check()` toujours sans appelant (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:189`.
- **Constat** : aucun appel `.health_check` dans `api/`, `services/`, `bootstrap/`, `infra/` ni `mcp_adapter/`.
- **Remediation** : inchangée.

### [INFO] INFO 4 : composition root hétérogène et libellés de fiche périmés (reconduit, étendu)

- **Localisation** : `docs/audit/audits/06-solid.md` (items 6.2.2 et 6.5.2) ; `document-parser/bootstrap/builder.py:125-134` (`AnalysisEditService`) et `:172` (`PreviewService(document_service, PreviewCache())`).
- **Constat** : la fiche cite toujours `main.py` et `_build_converter()`. Deux services sont construits directement dans `builder.py`, alors que les autres passent par une fonction `build_*` de `bootstrap/factories.py` (`:200`, `:219`, `:231`). C'est sans effet sur le DIP.
- **Remediation** : mettre la fiche à jour. Optionnellement, ajouter `build_preview_service` et `build_analysis_edit_service`.

### [INFO] INFO 5 : dette SRP héritée dans `AnalysisService` (édition legacy du blob) et `ChunkService` (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:218`, `:242`, `:264` ; `document-parser/services/chunk_service.py:133` (classe, fichier de 921 l.).
- **Constat** : les méthodes legacy `rechunk`, `update_chunk_text` et `delete_chunk` sont toujours là. `ChunkService` passe de 935 à 921 lignes : #398 a remplacé des boucles par des écritures groupées. Il garde le CRUD, le push vers les stores, l'historique des pushes, l'arbre et la résolution du résultat actif.
- **Remediation** : inchangée. Extraire `ChunkPushService` (push et historique) et la projection d'arbre.

### [INFO] INFO 6 : `ParseLoader` expose ses dépôts (reconduit)

- **Localisation** : `document-parser/services/parse_loader.py:60-68`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 8 : `PageRasterizer.crop` détourné en transcodeur (reconduit)

- **Localisation** : `document-parser/services/citation_image_service.py:89-91`.
- **Constat** : inchangé. Le même besoin d'encodage WebP existe maintenant dans `DocumentService.generate_preview` (MAJ-1). Un paramètre `fmt` sur `render_page` couvrirait les deux usages.
- **Remediation** : inchangée.

### [INFO] INFO 9 : découpage SRP hétérogène dans l'adaptateur MCP (reconduit)

- **Localisation** : `document-parser/mcp_adapter/sources_view.py`, `document-parser/mcp_adapter/apps.py`.
- **Constat** : fichiers Python non modifiés (le diff ne touche que les `.html` de `mcp_adapter/`).
- **Remediation** : inchangée.

### [INFO] INFO 10 : `PageElement.level` toujours à 0 côté Docling Serve (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:377`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 11 : `AnalysisEditService` sert aussi de résolveur du « résultat actif » et tient un cache mémoire (reconduit)

- **Localisation** : `document-parser/services/analysis_edit_service.py:74`, `:83-86`, `:101-102` (cache `_unedited_projection`) ; `:105-111` (`load_active_result`) ; `:368-380` (`_chunks_stale`, qui lit aussi `ChunkRepository.count_for_document`, `:378`) ; consommateurs : `services/chunk_service.py:371`, `:704`, `services/export_service.py:138`, `:147`.
- **Constat** : inchangé sur le fond. `ChunkService` et `ExportService` dépendent de tout l'éditeur pour une lecture, et cette dépendance n'est pas typée (MAJ-2).
- **Remediation** : extraire un `ActiveResultReader` en lecture seule, typé sur un port.

### [INFO] INFO 12 : la politique d'éditabilité vit dans le projecteur Docling (reconduit, réduit)

- **Localisation** : `document-parser/infra/docling_projector.py:132-147`.
- **Constat** : le projecteur passe de 319 à 229 lignes : l'outline sémantique et `_TEXT_LABELS` sont supprimés. Reste la règle produit « quelles opérations sont permises selon le type d'élément », écrite en infra.
- **Remediation** : déplacer la politique dans `domain/analysis_editing.py`.

### [INFO] INFO 14 : contrat d'exception du port `AnalysisDocumentEngine` non écrit (reconduit, réduit)

- **Localisation** : `document-parser/domain/ports.py:305-331` ; `document-parser/infra/docling_projector.py:84` (`model_validate_json` sans traduction) ; `document-parser/services/analysis_edit_service.py:326-348` (`_project` journalise puis relance tout) ; `document-parser/api/analysis_edits.py:116` (seul `AnalysisEditError` est traduit).
- **Constat** : le cas de la baseline (cache corrompu, donc 500) est réglé par #395/#402. `_project_cache` attrape l'échec et rejoue le flux (`analysis_edit_service.py:297-320`). Mais le port ne dit pas quelles exceptions `project` et `project_serialized` peuvent lever. Côté `project`, l'éditeur traduit ses erreurs en `AnalysisEditError`, pas le projecteur : une erreur du projecteur remonte donc en 500.
- **Remediation** : documenter dans le port que les deux méthodes ne lèvent que `AnalysisEditError`, et traduire dans `DoclingAnalysisEngine`.

### [INFO] INFO 15 : port `DocumentMerger` et adaptateur `DoclingDocumentMerger` sans consommateur (reconduit)

- **Localisation** : `document-parser/domain/ports.py:100` ; `document-parser/infra/docling_merger.py:12`. Aucun import hors `tests/`.
- **Constat** : inchangé. La fusion des lots reste dans `infra/local_converter.py:157`, `:203-204`.
- **Remediation** : inchangée. Câbler le port dans `LocalConverter`, ou supprimer le port et l'adaptateur.

### [INFO] INFO 16 : format d'aperçu choisi par un `if` sur une chaîne (OCP, nouveau)

- **Localisation** : `document-parser/services/document_service.py:161` (`image_format: str = "PNG"`) et `:175-178` (`if image_format == "WEBP" ... else PNG`) ; `document-parser/services/preview_service.py:38` et `:47` (`image_format.upper()`) ; `document-parser/api/documents.py:179` (`Literal["png", "webp"]`) et `:186` (`media_type=f"image/{format}"`) ; `frontend/src/features/document/api.ts:50` (`format=webp` en dur).
- **Constat** : ajouter un format (AVIF, JPEG) oblige à modifier quatre endroits, dont une méthode statique de service. Toute valeur différente de `"WEBP"` produit du PNG en silence. Une valeur hors `Literal` est aujourd'hui impossible côté HTTP, mais un appelant interne n'a aucune garantie. Le format est un `str` libre dans la clé de cache (`domain/ports.py:143`). C'est un dispatch fermé sur des valeurs, pas sur des implémentations, et l'item 6.2.3 vise l'export, pas l'aperçu : observation seulement.
- **Remediation** : un `StrEnum PreviewFormat` portant le `media_type` et les options d'encodage, passé au port de rendu (MAJ-1, point 1).

### [INFO] INFO 17 : la traduction HTTP des sous-classes d'exception dépend de l'ordre des clauses (LSP, nouveau)

- **Localisation** :
  - `document-parser/domain/analysis_editing.py:119` : `AnalysisEditNotFoundError(AnalysisEditUnavailableError)` ;
  - `document-parser/api/errors.py:17-22` et `:30` : table parcourue avec `isinstance`, et `NotFound` (404) qui doit rester avant `Unavailable` (409) ;
  - `document-parser/api/documents.py:189-194` : `PreviewPageOutOfRangeError(ValueError)` (`services/preview_service.py:18`), qui doit être attrapé (400) avant `ValueError` (404) ;
  - `document-parser/services/chunk_service.py:372-373` : la même `AnalysisEditNotFoundError` (« no active analysis ») y devient un 409.
- **Constat** : au sens strict, LSP tient. Les appelants qui attrapent le parent (`chunk_service.py:372`, `:705`, `export_service.py:139`, `:148`) reçoivent la sous-classe et la traitent correctement, ce que la docstring prévoit (`analysis_editing.py:122-124`). Une sous-classe qui reçoit un statut plus précis est un raffinement, pas une rupture de contrat. Le risque est ailleurs : le statut dépend de l'ordre d'une table ou de clauses `except`, sans test qui fige cet ordre côté preview. Et la même erreur « pas d'analyse active » vaut 404 sur l'éditeur et 409 sur `rechunk`.
- **Remediation** : un test paramétré sur `http_error`, qui couvre chaque sous-classe. Une classe `PreviewPageOutOfRangeError` qui ne dérive pas de `ValueError`, ou qui dérive de `ServiceError`. Aligner le statut de « pas d'analyse active » entre les ressources.

### [INFO] INFO 18 : statut HTTP porté par les exceptions de service, et surchargé instance par instance (DIP/LSP, nouveau)

- **Localisation** : `document-parser/services/errors.py:11-19` ; surcharges par instance : `services/chunk_service.py:366`, `:373`, `:380-382`, `:491-494`, `:507-509`, `:516-518`, `:535-537`, `services/version_service.py:173-174`, `:219`, `services/store_service.py:383`, `:389`, `services/parse_loader.py:86`, `:119` ; exceptions hors hiérarchie : `services/preview_service.py:14-19` ; statut ignoré : `api/documents.py:156-157`.
- **Constat** : #396 centralise bien la traduction (`api/errors.py`). Trois limites restent :
  1. **Détail de transport dans les services.** La couche service connaît les codes HTTP, ce qui est un détail du transport. L'adaptateur MCP, second adaptateur entrant, les ignore (`mcp_adapter/tool_errors.py:46`).
  2. **Statut découplé du type.** Le constructeur accepte un `http_status` par instance, donc le type ne détermine plus le statut. `ChunkServiceError("...", http_status=404)` (`chunk_service.py:507-509`) cohabite avec `ChunkNotFoundError` (`:70`). Un appelant qui filtre par type (`except ChunkNotFoundError`) manque ces 404.
  3. **Hiérarchie incomplète.** Les erreurs de `PreviewService` ne dérivent pas de `ServiceError`, contrairement à ce qu'annonce `services/errors.py:3`. Le routeur d'export code 404 en dur au lieu de lire `http_status`.

  Rien de bloquant : le comportement HTTP est testé (`tests/test_api_errors.py`).
- **Remediation** : un type par cas (`ChunkUnavailableError`, `ChunkConflictError`…), sans surcharge par instance. Remplacer `http_status` par une catégorie neutre (`NOT_FOUND`, `CONFLICT`, `UNAVAILABLE`) que `api/errors.py` traduit. Rattacher les erreurs de preview à `ServiceError`.

### [INFO] INFO 19 : `PagePreviewWithOverlay.vue` cumule source de rendu, virtualisation, navigation et surlignage (SRP front, nouveau)

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue` (761 l., script `:137-567`) ; choix canvas PDF.js / image de repli `:96-115`, dupliqué dans `frontend/src/features/document/ui/PdfPagePreview.vue:3-18`.
- **Constat** : le composant choisit la source de rendu (PDF.js ou WebP serveur), virtualise les pages (`shouldRenderPage`, `setupObserver` `:326`, `:392`), gère la saisie de page, les intentions de scroll et le centrage du surlignage, et pose l'overlay. La décision « PDF.js sinon image » est écrite deux fois. Ajouter une troisième source oblige à modifier les deux composants. `usePdfDocument.ts` et `PdfPageCanvas.vue`, en revanche, sont bien isolés.
- **Remediation** : un composant `PdfPageSurface` (canvas ou image de repli) utilisé par les deux vues, et sortir la navigation et le scroll dans un composable.

---

## Delta vs audit du 2026-11-13

**Score** : 87 → **87** (0). **Écarts** : 0/2/0/15 → **0/2/0/17**.

| Écart du 2026-11-13 | Statut à `a6fb539` |
|---------------------|--------------------|
| [MAJ] MAJ-1 `DocumentService` parsing + persistence (6.1.4) | **Toujours présent, étendu.** `DocumentService` est inchangé sur le fond. Le nouveau `PreviewService` (#401) en dépend en appel statique au lieu d'utiliser `PageRasterizer`. |
| [MAJ] MAJ-2 ports incomplets/absents (6.2.1) | **Toujours présent, réduit.** Le moteur d'édition est derrière `AnalysisDocumentEngine` (#394), et `ChunkRepository` est complété (#398). Restent 15 appels hors port, aucun `DocumentVersionRepository`, `graph_writer` et `active_result_service` non typés. |
| [INFO] 1, 2, 3, 6, 9, 10, 15 | Toujours présents, inchangés. |
| [INFO] 4 | Toujours présent, étendu (`PreviewService` construit hors `factories.py`). |
| [INFO] 5 | Toujours présent (`ChunkService` 935 → 921 l.). |
| [INFO] 7 (`update_status(select_analysis=...)`) | **Résolu** (#397) : `complete_and_select` nommé, dans une transaction (`persistence/analysis_repo.py:175-192`, `domain/ports.py:271-273`). |
| [INFO] 8 | Toujours présent. |
| [INFO] 11 | Toujours présent. |
| [INFO] 12 | Réduit : l'outline et `_TEXT_LABELS` sont supprimés. La politique d'éditabilité reste en infra. |
| [INFO] 13 (chaîne de sélection dupliquée dans l'export) | **Résolu** (#397) : `_export` reçoit un résolveur (`services/export_service.py:75-112`). Il reste un repli différent selon le format (`:121-123`, `find_latest_completed` contre `find_latest_completed_by_document`), à voir dans l'audit DRY. |
| [INFO] 14 | Réduit : le cache corrompu est rejoué (#395/#402). Le contrat d'exception du port n'est pas écrit. |

| Nouvel écart | Origine |
|--------------|---------|
| INFO 16 : format d'aperçu par `if` sur une chaîne | #401 (`PreviewService`, WebP) |
| INFO 17 : traduction HTTP dépendante de l'ordre des sous-classes | #395/#396 (`AnalysisEditNotFoundError`), #401 (`PreviewPageOutOfRangeError`) |
| INFO 18 : `http_status` dans les services, surcharges par instance | #396 (`ServiceError`) |
| INFO 19 : `PagePreviewWithOverlay.vue` multi-rôle, choix de source dupliqué | #401 (PDF.js) |

Le score ne bouge pas parce que les deux mêmes items tombent. Le contenu des deux MAJ a changé dans des sens opposés : MAJ-2 perd sa partie la plus lourde (le moteur d'édition), et MAJ-1 gagne un nouveau consommateur. Les correctifs #394, #396 et #397 améliorent nettement le SOLID du code de l'éditeur.

---

## Points positifs

- **Port du moteur d'édition (#394)** : `AnalysisDocumentEngine` (`domain/ports.py:305-331`) a deux méthodes et n'échange que du JSON sérialisé et un `ProjectedAnalysis`. `DoclingAnalysisEngine` garde le `DoclingDocument` dans l'infra (`infra/docling_analysis_engine.py:36-47`). Le constructeur d'`AnalysisEditService` est en mots-clés et typé (`services/analysis_edit_service.py:54-65`).
- **Ports étroits pour le nouveau code (ISP)** : `PreviewImageCache` n'a que `get` et `put` (`domain/ports.py:146-151`). `PreviewCache` est thread-safe et borné en octets (`infra/preview_cache.py:13-40`), et il est injecté au composition root.
- **Port complété avec son adaptateur (#398)** : `soft_delete_many`, `soft_delete_for_document` et `shift_sequences` sont ajoutés à `ChunkRepository` en même temps qu'à `SqliteChunkRepository`. C'est la bonne pratique que MAJ-2 demande ailleurs.
- **Drapeaux remplacés par des opérations nommées (#397)** : `complete_and_select` remplace `update_status(select_analysis=True)`, et `export` / `export_edited` remplacent `export(edited=...)`.
- **Traduction d'erreurs centralisée (#396)** : `api/errors.py:25-31`, appelée par tous les routeurs de service (`document_chunks`, `document_versions`, `stores`, `graph`, `reasoning`, `config`, `analysis_edits`).
- **Frontend PDF.js bien découpé** : `usePdfDocument.ts` gère le cycle de vie du document (annulation par génération, `destroy` au démontage), et `PdfPageCanvas.vue` ne fait que le rendu d'une page. Aucun nouveau store.

---

## Verdict partiel : GO

Score **87/100** (≥ 80), **0 CRITICAL**, **2 MAJOR** (≤ 3, non bloquant selon master §2), 0 MINOR, 17 INFO.

**Point à trancher par le mainteneur** (reconduit) : une lecture stricte de 6.5.1 (« les services dépendent de protocoles abstraits ») ferait tomber l'item, de poids 3, donc en CRIT et en NO-GO. Les motifs seraient `VersionService` typé `SqliteDocumentVersionRepository`, `StoreService`, `ChunkService` et `StoreBackendResolver` typés `Sqlite*` (sous `TYPE_CHECKING`), et, nouveauté, `PreviewService` qui importe et appelle `DocumentService.generate_preview` à l'exécution, sans substitution possible par injection. La partie « éditeur sans port », qui motivait cette question le 2026-11-13, est en revanche levée par #394. Ce rapport garde la lecture opérationnelle de la baseline pour que les scores restent comparables.

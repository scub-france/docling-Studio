# Rapport d'audit : SOLID

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : working tree de la branche `fix/0.7.4-editor-followups` au commit `a12b744`.
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/06-solid.md` : 87/100, 13/15 items, 27/31 pondérés, 0 CRIT, 2 MAJ, 0 MIN, 17 INFO, GO).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 pondérés) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 23 |

Calcul : `31 / 31 × 100 = 100`. Même grille de lecture que le re-audit (6.4.2 tolère `merge_batches` en INFO, 6.5.1 lu sur les concrétions `infra/` et `persistence/`), pour que les scores se comparent. Le point ouvert sur 6.5.1 est tranché plus bas : l'item passe aussi en lecture stricte.

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | oui | `PreviewService` (88 l.) : aperçu et tailles de page, derrière trois ports. `ChunkService` (923 l.) reste la dette connue (INFO 5). |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | oui | Toujours 14 `defineStore`, aucun nouveau. Le diff front touche des renommages et la page d'analyse, pas les frontières des stores. |
| 6.1.3 | Routes API groupées par ressource | 1 | oui | `api/documents.py` ne lit plus de dépôt : la jointure document/stores est passée dans `DocumentService.find_with_store_links` (`services/document_service.py:144-168`). |
| 6.1.4 | Aucun module ne cumule des responsabilités hétérogènes | 2 | oui | Plus aucun rendu PDF dans `services/` : `generate_preview`, `page_sizes`, `_count_pages_in_bytes` ont quitté `DocumentService`. Le rendu passe par `PageRasterizer`, la géométrie par `PdfInspector` (`services/preview_service.py:77`, `:83`). Résidu : I/O disque direct (INFO 24). |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier l'existant | 2 | oui | Script AST : 236 accès `self._dep.méthode` croisés avec leur `Protocol`, 0 hors contrat. `DocumentVersionRepository` existe (`domain/ports.py:285`), plus aucun typage `Sqlite*`, plus aucune dépendance de service non typée. |
| 6.2.2 | Local/remote extensible via `build_converter()` | 2 | oui | `infra/local_converter.py` inchangé, `infra/serve_converter.py` : renommages internes seulement (`_build_headers`, `read_cell_text`). |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | oui | `export_document` (`api/documents.py:108`) délègue à `ExportService` et traduit par `to_http_error` (`:131-132`), plus de 404 codé en dur. |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | oui | Contrat inchangé. INFO 1, 2, 10 reconduits. |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | oui | `PdfiumInspector` respecte la docstring du port (`FileNotFoundError` documenté, `count_pages_in_bytes` ne lève jamais). Le `ValueError` de `render_page` n'est pas écrit dans le port (INFO 21). |
| 6.3.3 | Pas d'`isinstance()`/`type()` pour différencier les implémentations | 2 | oui | Grep de la fiche : 4 résultats, tous de la validation de payload (`store_service.py:129`, `:133`, `chunk_service.py:205`, `mcp_config_service.py:71`). |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | oui | `domain/ports.py:67` et `:110`. Nouveaux ports étroits : `DocumentFileLocator` (2 méthodes), `ActiveAnalysisResultReader` (2), `VectorStorePool` (1), `GraphDriverPool` (1). |
| 6.4.2 | Aucun port n'impose de méthodes inutiles | 2 | oui | Chaque méthode ajoutée est implémentée par l'adaptateur et appelée. `PdfInspector` (3 méthodes) n'impose rien d'inutile à son adaptateur ; côté clients, chacun n'en utilise qu'une (INFO 20). `merge_batches` reste INFO 1. |
| 6.5.1 | Les services dépendent de ports | 3 | oui (lecture stricte comprise) | Aucun import `infra`/`persistence` dans `services/`, `TYPE_CHECKING` compris. Plus d'appel statique sur une classe concrète. Les seules dépendances concrètes restantes sont entre services (INFO 25). |
| 6.5.2 | Injection au composition root | 2 | oui | `PdfiumInspector`, `PdfPageRasterizer`, `PreviewCache`, `SqliteDocumentVersionRepository` construits dans `bootstrap/builder.py:150`, `:176-181` et `bootstrap/factories.py:216`, `:231`. |
| 6.5.3 | Pas d'instanciation d'adaptateurs dans les services | 3 | oui | Grep `LocalConverter\|ServeConverter\|LocalChunker\|PreviewCache\|DoclingAnalysisEngine\|Sqlite*(\|PdfiumInspector\|PdfPageRasterizer` sur `services/` : zéro résultat. |

### Méthode

Lecture du working tree à `a12b744` et de `git diff a6fb539 a12b744` sur `document-parser/` (104 fichiers). Greps de la fiche rejoués. Trois scripts en lecture seule, exécutés avec `document-parser/.venv/bin/python -I` :

1. **Croisement service → Protocol** (`xcheck.py`) : pour chaque classe de `services/`, résout l'annotation de chaque paramètre du constructeur via les imports du module (y compris sous `TYPE_CHECKING`), suit `self._x = param`, puis vérifie chaque `self._x.attr` contre la classe annotée (`hasattr` sur le `Protocol` importé). Résultat : **236 accès conformes, 0 hors `Protocol`** ; **0 typage `Sqlite*`/`infra`** ; **0 paramètre non typé** ; un seul `Any` (`graph_writer_factory: Callable[[Any], GraphWriter]`, `services/store_backend_resolver.py:86`).
2. **Second passage** (`xcheck2.py`) : paramètres de fonctions et champs de dataclass typés sur un port (`IngestionTargets.vector_store`, `.graph_writer`), accédés par variable locale : 0 accès hors contrat. `search_fulltext` (`services/ingestion_service.py:277`) est bien sur `VectorStore` (`domain/ports.py:450`).
3. **Signatures** (`sigs.py`) : `inspect.signature` de chaque méthode de chaque `Protocol` comparée à celle de chaque classe de `infra/`, `persistence/`, `services/` qui l'implémente structurellement. Toutes les méthodes ajoutées par la remédiation correspondent nom, sorte de paramètre, défauts, `async` et annotations : `StoreRepository`/`SqliteStoreRepository`, `DocumentStoreLinkRepository`, `ChunkPushRepository`, `DocumentVersionRepository`/`SqliteDocumentVersionRepository`, `AnalysisRepository`, `DocumentRepository.find_by_ids`, `DocumentFileLocator`/`DocumentService`, `ActiveAnalysisResultReader`/`AnalysisEditService`, `PdfInspector`/`PdfiumInspector`, `PageRasterizer`/`PdfPageRasterizer`. Écarts restants, tous compatibles : `OpenSearchClientPool.get` et `Neo4jDriverPool.get` renvoient un sous-type (covariance), `OpenSearchStore.get_chunks(limit: int | None)` est plus large que le port, `DoclingDocumentImporter.deserialize(document: dict)` contre `dict[str, Any]`, et `supports_page_batching` (INFO 2). Les autres « écarts » du script sont des faux positifs d'appariement structurel (méthode `get` homonyme).

Je n'ai lancé ni les tests, ni l'application, ni un build. Les résultats de CI cités viennent de l'appelant (backend 1559 passés, 15 ignorés ; frontend 605 passés).

---

## Ecarts constates

Aucun écart CRIT, MAJ ou MIN.

### [INFO] INFO 1 : `merge_batches` imposé à `ServeConverter`, qui l'implémente en code mort (reconduit)

- **Localisation** : `document-parser/domain/ports.py:91` ; `document-parser/infra/serve_converter.py:95`.
- **Constat** : inchangé.
- **Remediation** : port optionnel `PageBatchMerger`, ou capacité séparée.

### [INFO] INFO 2 : `supports_page_batching` est une `@property` dans le port mais un attribut dans les adaptateurs (reconduit)

- **Localisation** : `document-parser/domain/ports.py:82-83` ; `document-parser/infra/serve_converter.py:77`.
- **Constat** : inchangé (confirmé par le script de signatures).
- **Remediation** : inchangée.

### [INFO] INFO 3 : `ServeConverter.health_check()` sans appelant (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:189`.
- **Constat** : aucun appel `.health_check` de ce convertisseur dans `api/`, `services/`, `bootstrap/`, `mcp_adapter/`.
- **Remediation** : inchangée.

### [INFO] INFO 4 : composition root hétérogène et libellés de fiche périmés (reconduit, étendu)

- **Localisation** : `docs/audit/audits/06-solid.md` (6.2.2, 6.5.2) ; `document-parser/bootstrap/builder.py:45` (import direct de `infra.pdf_inspector`), `:176-181` (`PreviewService` et `PdfiumInspector()` construits dans le builder) ; `document-parser/bootstrap/factories.py:216`, `:231`, `:307-310` (`_build_pdf_inspector`).
- **Constat** : `PdfiumInspector` est construit à trois endroits, deux fois par la fabrique paresseuse et une fois par un import direct dans le builder. Sans effet sur le DIP (adaptateur sans état), mais la règle « tout passe par `factories.py` » n'est pas suivie.
- **Remediation** : `build_preview_service` dans `factories.py`, réutiliser `_build_pdf_inspector()` ; mettre la fiche à jour.

### [INFO] INFO 5 : dette SRP héritée dans `AnalysisService` (édition legacy) et `ChunkService` (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:223`, `:247`, `:269` ; `document-parser/services/chunk_service.py:133` (923 l.).
- **Constat** : inchangé.
- **Remediation** : extraire `ChunkPushService` et la projection d'arbre.

### [INFO] INFO 6 : `ParseLoader` expose ses dépôts (reconduit)

- **Localisation** : `document-parser/services/parse_loader.py:60-68`.
- **Constat** : inchangé.

### [INFO] INFO 8 : `PageRasterizer.crop` détourné en transcodeur (reconduit)

- **Localisation** : `document-parser/services/citation_image_service.py:90-91`.
- **Constat** : `render_page` accepte maintenant `fmt` (`domain/ports.py:636`), mais en WebP sans perte ; la citation veut du WebP avec perte (`infra/page_raster.py:69`), donc le détour par `crop(..., (0, 0, 10_000, 10_000))` reste.
- **Remediation** : un paramètre de qualité sur `render_page`, ou un `PreviewFormat` qui porte les options d'encodage (cf. INFO 16).

### [INFO] INFO 9 : découpage SRP hétérogène dans l'adaptateur MCP (reconduit)

- **Localisation** : `document-parser/mcp_adapter/sources_view.py`, `document-parser/mcp_adapter/apps.py`.
- **Constat** : le diff n'y fait que des renommages.

### [INFO] INFO 10 : `PageElement.level` toujours à 0 côté Docling Serve (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:377`.

### [INFO] INFO 11 : `AnalysisEditService` sert de lecteur du « résultat actif » et tient un cache mémoire (reconduit, réduit)

- **Localisation** : `document-parser/services/analysis_edit_service.py:68`, `:99` ; port `document-parser/domain/ports.py:360-371`.
- **Constat** : `ChunkService` et `ExportService` dépendent maintenant du port de lecture `ActiveAnalysisResultReader` (`services/chunk_service.py:149`, `services/export_service.py:43`), plus de tout l'éditeur. L'implémentation reste l'éditeur et son cache.
- **Remediation** : extraire l'implémentation de lecture si le cache doit évoluer séparément. Non urgent.

### [INFO] INFO 12 : la politique d'éditabilité vit dans le projecteur Docling (reconduit)

- **Localisation** : `document-parser/infra/docling_projector.py:132-137`.

### [INFO] INFO 14 : contrat d'exception du port `AnalysisDocumentEngine` non écrit (reconduit)

- **Localisation** : `document-parser/domain/ports.py:374-401`.
- **Constat** : les docstrings de `project` et `project_serialized` ne disent toujours pas quelles exceptions sortent.

### [INFO] INFO 15 : port `DocumentMerger` et adaptateur `DoclingDocumentMerger` sans consommateur (reconduit)

- **Localisation** : `document-parser/domain/ports.py:104` ; `document-parser/infra/docling_merger.py:12`. Aucune référence dans `api/`, `services/`, `bootstrap/`, `mcp_adapter/`.

### [INFO] INFO 16 : format d'aperçu choisi par un `if` sur une chaîne (reconduit, déplacé)

- **Localisation** : `document-parser/api/documents.py:154` (`Literal["png", "webp"]`), `:161` (`media_type=f"image/{format}"`) ; `document-parser/services/preview_service.py:66` (`image_format.upper()`) ; `document-parser/infra/page_raster.py:35` (`if fmt.upper() == "WEBP" ... else PNG`) ; `frontend/src/features/document/api.ts:50`.
- **Constat** : le `if` a quitté le service pour l'adaptateur, ce qui est sa bonne place. Le format reste un `str` libre dans le port et la clé de cache ; toute valeur autre que `WEBP` donne du PNG en silence.
- **Remediation** : `StrEnum PreviewFormat` avec `media_type` et options d'encodage.

### [INFO] INFO 17 : traduction HTTP des sous-classes d'exception dépendante de l'ordre (reconduit, réduit)

- **Localisation** : `document-parser/api/errors.py:17-22` ; `document-parser/domain/analysis_editing.py:150`.
- **Constat** : côté preview, c'est réglé : les trois erreurs dérivent de `ServiceError` et portent leur statut (`services/preview_service.py:17-35`). Reste l'ordre « le plus spécifique d'abord » de `_EDIT_ERROR_STATUS`, écrit en commentaire, et le 404/409 différent pour « pas d'analyse active » entre éditeur et `rechunk` (`services/chunk_service.py:373`).

### [INFO] INFO 18 : statut HTTP porté par les exceptions de service, surchargé instance par instance (reconduit, réduit)

- **Localisation** : `document-parser/services/errors.py:11-19` ; 13 surcharges `http_status=` (`services/chunk_service.py:366`, `:373`, `:382`, `:494`, `:509`, `:518`, `:537`, `services/parse_loader.py:86`, `:121`, `services/store_service.py:381`, `:387`, `services/version_service.py:174`, `:219`).
- **Constat** : la hiérarchie est maintenant complète (preview rattaché) et le routeur d'export lit le statut (`api/documents.py:131-132`). Les surcharges par instance restent.

### [INFO] INFO 19 : `PagePreviewWithOverlay.vue` multi-rôle, choix de source dupliqué (reconduit)

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue` (761 l.) ; `frontend/src/features/document/ui/PdfPagePreview.vue`.
- **Constat** : inchangé.

### [INFO] INFO 20 : `PdfiumInspector` mélange pdfium et poppler, et chaque client du port n'en utilise qu'une méthode (nouveau, remédiation)

- **Localisation** : `document-parser/domain/ports.py:654-670` ; `document-parser/infra/pdf_inspector.py:15-16`, `:45-51` (`page_count` par pdfium), `:53-64` (`count_pages_in_bytes` par `pdfinfo_from_bytes`, poppler) ; clients : `services/document_service.py:113` (`count_pages_in_bytes`), `services/analysis_service.py:451` (`page_count`), `services/preview_service.py:77` (`page_sizes`).
- **Constat** : le port est cohérent par sujet (lire la géométrie d'un PDF sans le rendre) et son unique adaptateur implémente tout, donc 6.4.2 tient. Trois points faibles :
  1. le nom `PdfiumInspector` est faux pour `count_pages_in_bytes`, qui passe par poppler ; l'adaptateur dépend donc de deux moteurs ;
  2. le nombre de pages vu à l'upload (poppler) et celui qui pilote le découpage en lots (pdfium) viennent de deux moteurs qui peuvent diverger sur un PDF abîmé ;
  3. les contrats diffèrent dans le même port : `page_count` lève, `count_pages_in_bytes` renvoie `None` et ne lève jamais.
  Le choix est assumé et commenté (garder le comportement d'upload), et testé (`tests/test_pdf_inspector.py`).
- **Remediation** : renommer l'adaptateur (`PdfGeometryInspector`) ou compter les octets avec pdfium (`PdfDocument(bytes)`) sous le même verrou, en vérifiant que la limite d'upload ne change pas.

### [INFO] INFO 21 : `PreviewService` dépend d'un `ValueError` que le port `PageRasterizer` ne promet pas (nouveau, remédiation)

- **Localisation** : `document-parser/services/preview_service.py:81-88` (`except ValueError` → `PreviewPageNotFoundError`) ; `document-parser/domain/ports.py:636-639` (docstring de `render_page`, muette sur les exceptions) ; `document-parser/infra/page_raster.py:29-33` (`FileNotFoundError`, `ValueError`) ; `document-parser/api/documents.py:166-167` (`except ValueError` → 404, devenu inatteignable depuis le service).
- **Constat** : le comportement est correct et testé (`tests/test_preview_service.py:62`), mais un second adaptateur de rendu n'a aucun moyen de savoir qu'il doit lever `ValueError` pour une page absente. Au sens de 6.3.2, c'est le contrat qui est incomplet, pas l'adaptateur qui en sort. La branche `ValueError` du routeur ne sert plus.
- **Remediation** : écrire dans le port « lève `FileNotFoundError` si le fichier manque, `ValueError` si la page n'existe pas » (comme `PdfInspector.page_sizes` le fait déjà), et retirer la branche morte du routeur.

### [INFO] INFO 22 : sans `PdfInspector`, `AnalysisService` désactive le découpage en lots en silence (nouveau, remédiation)

- **Localisation** : `document-parser/services/analysis_service.py:94` (`pdf_inspector: PdfInspector | None = None`), `:448-449` (`return 0`) ; câblage : `document-parser/bootstrap/factories.py:216`.
- **Constat** : avant, le service comptait les pages lui-même ; maintenant une dépendance optionnelle oubliée change le comportement (pas de lots, donc pas de progression ni de borne mémoire) sans erreur ni log. La production la câble ; seuls des tests s'en passent.
- **Remediation** : rendre le paramètre obligatoire, ou journaliser au démarrage quand il manque.

### [INFO] INFO 23 : `StoreBackendResolver` reçoit tout `StoreRepository` pour un mot de passe, et le pilote graphe reste `Any` (nouveau, remédiation)

- **Localisation** : `document-parser/services/store_backend_resolver.py:83`, `:130`, `:145` (seul `get_connection_password` est appelé) ; `:86` (`Callable[[Any], GraphWriter]`) ; `document-parser/domain/ports.py:184-208` (11 méthodes), `:495-509` (`GraphDriverPool.get -> Any`).
- **Constat** : `StoreRepository` reste un dépôt CRUD cohérent d'un seul agrégat, 11 méthodes toutes implémentées et utilisées par `StoreService` ; ce n'est pas une « god interface ». Mais le résolveur, qui ne lit qu'un secret, reçoit le droit d'écrire et supprimer des stores. Le pilote Neo4j est volontairement opaque (`Any`), ce qui affaiblit la vérification de type entre `GraphDriverPool` et la fabrique de `GraphWriter`.
- **Remediation** : un port étroit `StoreSecretReader` (`get_connection_password`) pour le résolveur ; éventuellement un type opaque `GraphDriverHandle` à la place de `Any`.

### [INFO] INFO 24 : `DocumentService` garde l'I/O disque et cumule trois rôles proches (résidu de MAJ-1)

- **Localisation** : `document-parser/services/document_service.py:58-67` (6 dépendances), `:121`, `:198`, `:223-226` (`os.unlink`, `os.makedirs`, `open`), `:144-168` (`find_with_store_links`), `:170-182` (`resolve_storage_path`, `Path.is_file`).
- **Constat** : le rendu PDF est parti, et c'était l'hétérogénéité visée par MAJ-1. Restent : écriture et suppression du fichier téléversé, lecture des documents avec leurs liens de store (jointure remontée du routeur, ce qui ajoute `link_repo` et `store_repo`), et rôle de `DocumentFileLocator` pour `PreviewService`. Tout cela relève de « stocker et retrouver un document » : SRP ne se dégrade pas, mais le fichier ne passe par aucun port de stockage.
- **Remediation** : un port `DocumentFileStore` (`write`, `delete`, `resolve`) si un stockage objet (S3) est envisagé ; sinon rien.

### [INFO] INFO 25 : dépendances concrètes entre services (reconduit implicite, non compté par le re-audit)

- **Localisation** : `document-parser/services/chunk_service.py:136` (`IngestionService`, `StoreBackendResolver`), `document-parser/services/store_service.py:140` (`StoreBackendResolver`), `document-parser/services/navigation_service.py:51`, `document-parser/services/source_service.py:76` (`CitationService`, `NavigationService`, `ParseLoader`).
- **Constat** : ce sont des classes de la même couche, injectées au composition root. Pour la navigation, l'allow-list `PEERS` de `tests/test_architecture.py:132-148` les documente ; pour `ChunkService` et `StoreService`, rien ne les déclare. Ce n'est pas une dépendance à une implémentation d'infrastructure, donc 6.5.1 tient.
- **Remediation** : étendre `PEERS` à `chunk_service` et `store_service`, ou des ports `ChunkIngestor`/`StoreBackendResolution` si un second implémenteur apparaît.

---

## Delta vs re-audit a6fb539

**Score** : 87 → **100** (+13). **Items** : 13/15 → **15/15**. **Écarts** : 0/2/0/17 → **0/0/0/23**.

| Écart du re-audit | Statut à `a12b744` |
|-------------------|--------------------|
| [MAJ] MAJ-1 `DocumentService` rendu PDF + persistence, `PreviewService` en appel statique (6.1.4) | **Résolu.** `services/` n'importe plus `pdf2image` ni `pypdfium2` (grep vide, et les deux sont dans `_SERVICES_FORBIDDEN_EXTERNALS`, `tests/test_architecture.py:194-195`, avec `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` vide, `:202`). `PreviewService` dépend de `DocumentFileLocator`, `PageRasterizer`, `PdfInspector`, `PreviewImageCache` (`services/preview_service.py:39-50`), sans import de `DocumentService`. Le routeur appelle `service.page_sizes` (`api/documents.py:183`). `analysis_service.py` n'importe plus `pypdfium2`. Résidu en INFO 24. |
| [MAJ] MAJ-2 15 appels hors `Protocol`, pas de `DocumentVersionRepository`, typages `Sqlite*`, 3 dépendances non typées (6.2.1) | **Résolu.** 0 appel hors contrat sur 236. `DocumentVersionRepository` (`domain/ports.py:285-294`), `VersionService` typé dessus (`services/version_service.py:89`). Plus de `Sqlite*` dans `services/`, même sous `TYPE_CHECKING`, et le test de couches le verrouille (son scanner `ast.walk` voit les imports sous `TYPE_CHECKING`, `tests/test_architecture.py:71-91`). `graph_writer: GraphWriter \| None` (`services/analysis_edit_service.py:57`), `active_result_service: ActiveAnalysisResultReader \| None` (`services/chunk_service.py:149`, `services/export_service.py:43`). Reste un `Any` assumé (INFO 23). |
| Point à trancher 6.5.1 | **Tranché : conforme même en lecture stricte.** Plus de typage `Sqlite*`, plus d'appel statique sur une classe concrète. Restent seulement des dépendances entre services (INFO 25). |
| [INFO] 1, 2, 3, 5, 6, 9, 10, 12, 14, 15, 19 | Toujours présents, inchangés. |
| [INFO] 4 | Toujours présent, étendu (`PdfiumInspector` construit hors fabrique dans `builder.py:179`). |
| [INFO] 8 | Toujours présent (`render_page` a un `fmt`, mais sans perte). |
| [INFO] 11 | Réduit : port de lecture `ActiveAnalysisResultReader`. |
| [INFO] 16 | Déplacé dans l'adaptateur, inchangé sur le fond. |
| [INFO] 17 | Réduit : partie preview réglée. |
| [INFO] 18 | Réduit : hiérarchie complète, export lit le statut ; 13 surcharges restent. |

| Nouvel écart | Origine |
|--------------|---------|
| INFO 20 : `PdfiumInspector` sur deux moteurs, clients à une méthode | `437058d` |
| INFO 21 : `ValueError` de `render_page` hors contrat, branche morte au routeur | `437058d` |
| INFO 22 : batching désactivé en silence sans inspecteur | `437058d` |
| INFO 23 : résolveur sur tout `StoreRepository`, `GraphDriverPool -> Any` | `437058d` |
| INFO 24 : I/O disque et trois rôles dans `DocumentService` | résidu de MAJ-1, jointure remontée par `25f5d8b` |
| INFO 25 : dépendances concrètes entre services | préexistant, non relevé par le re-audit |

**Régressions** : aucune régression SOLID trouvée. Points vérifiés :
- **LSP des erreurs déplacées sous `ServiceError`** : `PreviewPageOutOfRangeError` n'est plus un `ValueError`. Aucun appelant ne s'appuie dessus : seul `api/documents.py` consomme `PreviewService` (`api/deps.py:39-43`), il attrape `ServiceError` avant `ValueError` (`:164-167`), et `ServiceError` dérive d'`Exception` seul (`services/errors.py:11`). Aucune référence dans `mcp_adapter/`. La seule conséquence est la branche `ValueError` morte (INFO 21).
- **SRP de `DocumentService`** : pas pire. Deux dépôts en plus, mais pour une lecture qui était dans le routeur ; le rendu est parti (INFO 24).
- **ISP de `StoreRepository`** après 6 méthodes : dépôt CRUD d'un agrégat, toutes les méthodes implémentées et consommées (INFO 23 pour le résolveur).
- **Signatures** : toutes les méthodes de port ajoutées correspondent à leur implémentation.

---

## Points positifs

- **Rendu et géométrie derrière des ports** : `PreviewService` ne connaît plus que quatre ports (`services/preview_service.py:39-50`) et masque le chemin serveur dans le message d'erreur (`:85-88`). `PdfPageRasterizer.render_page` sert à la fois l'aperçu et les citations.
- **Contrats complétés avec leurs adaptateurs** : 236 accès de service, tous couverts par leur `Protocol`, signatures identiques à l'implémentation.
- **Garde-fou durable** : `pdf2image` et `pypdfium2` sont dans la liste interdite, la liste de migration est vide, et le test de couches refuse `persistence.*` même sous `TYPE_CHECKING`.
- **Verrou pdfium unique** : `infra/pdfium_lock.py` partage le verrou de Docling quand il est installé ; inspecteur et lecteur de texte l'utilisent tous les deux (`infra/pdf_inspector.py:30`, `:46`, `infra/page_text.py:25`).
- **Ports de lecture étroits** : `DocumentFileLocator` et `ActiveAnalysisResultReader` donnent aux consommateurs le minimum, implémentés par des services existants sans adaptateur supplémentaire.
- **Routeur `documents` sans dépôt** : la jointure document/stores est dans le service, le routeur ne fait que du mapping de réponse.

---

## Verdict partiel : GO

Score **100/100**, **0 CRITICAL**, **0 MAJOR**, 0 MINOR, 23 INFO. Les deux MAJ du re-audit sont résolus dans le code, pas seulement dans les messages de commit, et la question 6.5.1 est close. Les 6 INFO nouveaux (20 à 25) sont des contrats à écrire ou des ports à affiner, aucun ne fait tomber un item.

Non vérifié : comportement à l'exécution (pas d'application lancée), divergence réelle de comptage poppler/pdfium sur des PDF abîmés (INFO 20), et absence d'appelant de `PreviewService` hors de ce dépôt.

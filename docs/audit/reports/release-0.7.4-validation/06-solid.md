# Rapport d'audit : SOLID

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : working tree de la branche `fix/0.7.4-editor-followups` au commit `efc0bc5` (aucune modification locale sous `document-parser/` ni `frontend/src/`).
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/06-solid.md`, commit `a12b744` : 100/100, 15/15 items, 0 CRIT, 0 MAJ, 0 MIN, 23 INFO, GO).

Code non exécuté : aucune suite n'a tourné sur ce commit.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 pondérés) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 29 |

Calcul : `31 / 31 × 100 = 100`. Même grille que le contrôle : un item ne tombe que sur preuve. 6.5.1 est lu en strict (aucun typage `infra`/`persistence`, `TYPE_CHECKING` compris), 6.5.3 vise les adaptateurs, pas les services entre eux.

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | oui | `ChunkService` passe de 923 à 426 l. : la poussée vers les stores est dans `ChunkPushService` (365 l.), l'arbre dans `DocumentTreeService` (78 l.). `ChunkService` garde un rôle de façade (4 méthodes de délégation, `services/chunk_service.py:378-398`) et construit ses deux collaborateurs : c'est une seconde raison de changer pour son constructeur, pas pour son comportement (INFO 26). |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | oui | Toujours 14 `defineStore`. `e03ac99` sort brouillons, piles de commandes et planificateur d'aperçu du store de l'éditeur dans quatre modules simples ; aucun store ajouté. |
| 6.1.3 | Routes API groupées par ressource | 1 | oui | Aucune route ajoutée depuis `a12b744` (`git diff` sur `api/` : aucun `@router` nouveau). `find_summaries_by_document` sert la route existante `GET /api/analyses?documentId=` (`api/analyses.py:120`). |
| 6.1.4 | Aucun module ne cumule des responsabilités hétérogènes | 2 | oui | Plus aucune I/O disque dans `services/` (grep `os.`/`open(`/`pathlib.Path` : seul `PurePath`, manipulation de chaîne, `services/export_service.py:7`) : tout passe par `DocumentFileStore` (`infra/document_file_store.py`). Réserve : l'agrégat `DocumentAnalysisState` porte des drapeaux de suivi de modification (INFO 27). |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier l'existant | 2 | oui | Script AST : **239 accès `self._dep.méthode` conformes, 0 hors `Protocol`**. Les 6 nouveaux ports ou méthodes sont implémentés à l'identique (voir section câblage). |
| 6.2.2 | Local/remote extensible via `build_converter()` | 2 | oui | `infra/local_converter.py` et `infra/serve_converter.py` inchangés depuis `a12b744`. |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | oui | `export_document` délègue toujours à `ExportService` et traduit par `to_http_error` (`api/documents.py:143-144`). |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | oui | Contrat inchangé. INFO 1, 2, 10 reconduits. |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | oui | Le contrat de `PageRasterizer.render_page` est écrit (`domain/ports.py:695-698` : `FileNotFoundError`, `ValueError`), ce qui ferme l'INFO 21. `DocumentFileStore` documente ses exceptions méthode par méthode et l'adaptateur s'y tient. Seul résidu : le `ValueError` de précondition de `replace_for_document` n'est pas écrit dans le port (INFO 28). |
| 6.3.3 | Pas d'`isinstance()`/`type()` pour différencier les implémentations | 2 | oui | Grep de la fiche : 4 résultats, tous de la validation de payload (`store_service.py:129`, `:133`, `chunk_service.py:170`, `mcp_config_service.py:71`). |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | oui | `domain/ports.py:64` et `:107`. |
| 6.4.2 | Aucun port n'impose de méthodes inutiles | 2 | oui | `DocumentFileStore` (6 méthodes) : un seul adaptateur, qui les implémente toutes, et chacune a un client de production (`save`/`discard`/`delete` → `DocumentService`, `has_file` → `ExportService`, `resolve`/`read_fingerprint` → `PreviewService`). Les 16 méthodes d'`AnalysisRepository` ont toutes un appelant. Exception : `DocumentAnalysisStateRepository.save_state` n'est appelé que par les tests (INFO 30). `merge_batches` reste INFO 1. |
| 6.5.1 | Les services dépendent de ports | 3 | oui (lecture stricte) | **0 typage sur une classe `infra`/`persistence`** (constructeurs, `TYPE_CHECKING` compris), **0 paramètre de constructeur non typé**. `CurrentAnalysisReader` est injecté dans 7 services, tous typés sur le port. Dépendances concrètes restantes : entre services seulement (INFO 25, 26). |
| 6.5.2 | Injection au composition root | 2 | oui | Les nouveaux adaptateurs (`LocalDocumentFileStore`, `SqliteDocumentAnalysisRepository`, `CurrentAnalysisResolver`) sont construits dans `bootstrap/builder.py:113`, `:125`, `:177` et `bootstrap/factories.py:220-224`. Réserve : `ChunkService` assemble lui-même `ChunkPushService` et `DocumentTreeService` (INFO 26). |
| 6.5.3 | Pas d'instanciation d'adaptateurs dans les services | 3 | oui | Grep `LocalConverter\|ServeConverter\|LocalChunker\|PreviewCache\|DoclingAnalysisEngine\|Sqlite*(\|PdfiumInspector\|PdfPageRasterizer\|LocalDocumentFileStore` sur `services/` : zéro instanciation (les seules occurrences de `Neo4j`/`OpenSearch` sont des messages et docstrings). Les deux constructions faites par `ChunkService` sont des services, pas des adaptateurs. |

### Méthode

Lecture du working tree à `efc0bc5` et de `git diff a12b744 efc0bc5` sur `document-parser/` (99 fichiers). Greps de la fiche rejoués. Trois scripts AST en lecture seule (`ast.parse` des sources, aucun import de module du projet), lancés par `nice -n 15 document-parser/.venv/bin/python -I` :

1. `xcheck.py` : pour chaque classe de `services/`, annotation de chaque paramètre de constructeur (ou champ de dataclass) résolue par les imports du module, `TYPE_CHECKING` compris ; suivi de `self._x = param` (et `self._x = param or défaut`) ; chaque `self._x.attr` est cherché dans la classe annotée et ses bases du projet. Puis, pour chaque `Protocol` de `domain/`, comparaison de signature (noms, sorte positionnel/keyword-only, défauts, `async`/sync, `@property`) avec toute classe de `infra/`, `persistence/`, `services/`, `mcp_adapter/` et `tests/` qui en porte toutes les méthodes. Enfin, les attributs `self.x = Classe(...)` construits dans un `__init__` de service.
2. `wiring.py` : chaque appel `Nom(...)` vers une classe ou fonction du projet dans `bootstrap/builder.py`, `bootstrap/factories.py`, `bootstrap/mcp_mount.py`, `main.py`, `mcp_stdio.py`, `api/deps.py`, `services/chunk_service.py`, puis dans tous les fichiers de `tests/` : arguments positionnels en trop, mots-clés inconnus, arguments obligatoires manquants (y compris après `*`).
3. `routes.py` : dans `api/*.py`, chaque `service.attr` sur un paramètre typé `deps.XxxDep`, contre la classe de service résolue par `api/deps.py`.

Compléments à la main : les appels passés en `**kwargs` (que le script saute), les clés de `AppStateBuilder._update(...)` contre les champs d'`AppState`, les middlewares de `main.py`, les attributs `settings.*` lus par le composition root, et les faux de `tests/navigation_fixtures.py` et des tests du raisonnement.

---

## Ecarts constates

Aucun écart CRIT, MAJ ou MIN.

### [INFO] INFO 1 : `merge_batches` imposé à `ServeConverter`, qui l'implémente en code mort (reconduit)

- **Localisation** : `document-parser/domain/ports.py:88` ; `document-parser/infra/serve_converter.py:95`.
- **Remediation** : port optionnel `PageBatchMerger`.

### [INFO] INFO 2 : `supports_page_batching` est une `@property` dans le port, un attribut dans les adaptateurs (reconduit)

- **Localisation** : `document-parser/domain/ports.py:79-80` ; `document-parser/infra/serve_converter.py:77` ; `document-parser/infra/local_converter.py:192`.
- **Constat** : confirmé par le script de signatures.

### [INFO] INFO 3 : `ServeConverter.health_check()` sans appelant (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:189`.

### [INFO] INFO 4 : composition root hétérogène (reconduit)

- **Localisation** : `document-parser/bootstrap/builder.py:43-47` (imports directs d'adaptateurs), `:191-197` (`PreviewService` avec `PdfPageRasterizer()`, `PdfiumInspector()`, `PreviewCache()` construits sur place) ; `document-parser/bootstrap/factories.py:318-327` (`_build_pdf_inspector`, `_build_rasterizer` existent pourtant).
- **Constat** : `PdfiumInspector` est toujours construit à trois endroits. Sans effet sur le DIP.
- **Remediation** : `build_preview_service(document_repo, file_store)` dans `factories.py`.

### [INFO] INFO 5 : dette SRP héritée dans `AnalysisService` (édition legacy des chunks) (reconduit, réduit)

- **Localisation** : `document-parser/services/analysis_service.py:228`, `:252`, `:274`.
- **Constat** : la partie `ChunkService` de cet INFO est traitée par `8a60cee` (voir INFO 26 pour ce qui reste). L'édition des chunks d'analyse dans `AnalysisService` est inchangée.

### [INFO] INFO 6 : `ParseLoader` expose son dépôt de documents (reconduit)

- **Localisation** : `document-parser/services/parse_loader.py:68-70` (`@property documents`).

### [INFO] INFO 8 : `PageRasterizer.crop` détourné en transcodeur (reconduit)

- **Localisation** : `document-parser/services/citation_image_service.py:90-91` ; `document-parser/infra/page_raster.py:69`.

### [INFO] INFO 9 : découpage SRP de l'adaptateur MCP (reconduit, réduit)

- **Localisation** : `document-parser/mcp_adapter/sources_view.py` (97 l.), `sources_card.py` (248 l.), `sources_text.py` (47 l.) ; `document-parser/mcp_adapter/apps.py`.
- **Constat** : `8a60cee` sépare la carte des sources, son rendu texte et l'outil MCP ; les nouveaux modules n'importent ni `infra` ni `persistence`. `apps.py` n'a pas été réexaminé.

### [INFO] INFO 10 : `PageElement.level` toujours à 0 côté Docling Serve (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:377`.

### [INFO] INFO 11 : `AnalysisEditService` sert de lecteur du résultat actif et tient le cache (reconduit)

- **Localisation** : `document-parser/services/analysis_edit_service.py:82-91`, `:100`.

### [INFO] INFO 12 : la politique d'éditabilité vit dans le projecteur Docling (reconduit)

- **Localisation** : `document-parser/infra/docling_projector.py:142-156`.

### [INFO] INFO 14 : contrat d'exception du port `AnalysisDocumentEngine` non écrit (reconduit)

- **Localisation** : `document-parser/domain/ports.py:440-468`.

### [INFO] INFO 15 : port `DocumentMerger` sans consommateur (reconduit)

- **Localisation** : `document-parser/domain/ports.py:101` ; `document-parser/infra/docling_merger.py`.

### [INFO] INFO 16 : format d'aperçu choisi par un `if` sur une chaîne (reconduit)

- **Localisation** : `document-parser/api/documents.py:166`, `:175` ; `document-parser/infra/page_raster.py:35`, `:65`.

### [INFO] INFO 17 : traduction HTTP d'exceptions dépendante de l'ordre (reconduit, étendu)

- **Localisation** : `document-parser/api/errors.py:17-22` ; `document-parser/domain/chunk_editing.py:33` ; `document-parser/services/chunk_service.py:274-279`.
- **Constat** : `ChunkMergeGapError` hérite de `ChunkEditingError` mais doit être traduite autrement (409 au lieu de 400). Son seul attrapeur la place avant la classe mère, donc le comportement est juste et le LSP tient (aucun code ne reçoit une `ChunkMergeGapError` en croyant gérer « une erreur de saisie » pour la traiter à tort). Mais c'est le même motif « la plus spécifique d'abord » que `_EDIT_ERROR_STATUS` : un nouvel attrapeur de `ChunkEditingError` qui oublierait la sous-classe rendrait un 400 pour un conflit.
- **Remediation** : faire porter la nature de l'erreur à la classe (`kind = "conflict"`) et traduire sur l'attribut.

### [INFO] INFO 18 : statut HTTP surchargé instance par instance (reconduit)

- **Localisation** : 13 surcharges `http_status=` : `services/chunk_service.py:306`, `:313`, `:322`, `services/chunk_push_service.py:171`, `:192`, `:201`, `:223`, `services/parse_loader.py:95`, `:128`, `services/store_service.py:381`, `:387`, `services/version_service.py:171`, `:199`.
- **Constat** : même nombre qu'au contrôle ; une partie a seulement changé de fichier.

### [INFO] INFO 19 : `PagePreviewWithOverlay.vue` multi-rôle (reconduit, réduit)

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue` (738 l.) ; `frontend/src/features/document/ui/PageRaster.vue` (nouveau) ; `frontend/src/features/document/ui/PdfPagePreview.vue`.
- **Constat** : `18cdf1b` sort le rendu canvas/image dans `PageRaster`. `PdfPagePreview` reste séparé, choix assumé dans le message de commit.

### [INFO] INFO 20 : `PdfiumInspector` sur deux moteurs (reconduit)

- **Localisation** : `document-parser/infra/pdf_inspector.py:16`, `:44-50` (pdfium), `:52-56` (`pdfinfo_from_bytes`, poppler).

### [INFO] INFO 22 : sans `PdfInspector`, `AnalysisService` désactive le découpage en lots en silence (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:95`, `:446`.

### [INFO] INFO 23 : `StoreBackendResolver` reçoit tout `StoreRepository` pour un mot de passe, pilote graphe en `Any` (reconduit)

- **Localisation** : `document-parser/services/store_backend_resolver.py:83`, `:86` ; `document-parser/domain/ports.py:568-575`.

### [INFO] INFO 25 : dépendances concrètes entre services non déclarées (reconduit, étendu)

- **Localisation** : `document-parser/services/chunk_service.py:42-43`, `:59-60` ; `document-parser/services/chunk_push_service.py:28-29` ; `document-parser/services/store_service.py:145` ; allow-list `document-parser/tests/test_architecture.py:132-149`.
- **Constat** : `PEERS` ne couvre toujours que la navigation. `chunk_service` importe maintenant aussi `chunk_push_service`, `document_tree_service` et `chunk_errors`, sans entrée.
- **Remediation** : étendre `PEERS` à `chunk_service`, `chunk_push_service`, `store_service`.

### [INFO] INFO 26 : `ChunkService` façade qui construit ses collaborateurs (nouveau, `8a60cee`)

- **Localisation** : `document-parser/services/chunk_service.py:107-148` (13 paramètres), `:133-148` (construction de `ChunkPushService` et `DocumentTreeService`), `:378-398` (4 délégations) ; `document-parser/bootstrap/factories.py:245-251`.
- **Constat** :
  1. **SRP** : le comportement est bien séparé (chaque service a son sujet), mais 6 des 13 paramètres du constructeur ne servent qu'à être transmis (`analysis_repo`, `tree_reader`, `ingestion_service`, `store_repo`, `link_repo`, `backend_resolver`). Toute nouvelle dépendance de `ChunkPushService` ou `DocumentTreeService` change la signature de `ChunkService` et la fabrique. C'est une seconde raison de changer, limitée au câblage.
  2. **DIP** : `ChunkService` choisit les classes concrètes de ses collaborateurs. Ce ne sont pas des adaptateurs, donc 6.5.3 tient, mais on ne peut ni les remplacer ni les doubler dans un test sans patcher le module. Le docstring du module justifie le choix (« garder un seul service à appeler »).
- **Remediation** : construire `ChunkPushService` et `DocumentTreeService` dans `factories.py` et les injecter, ou exposer deux dépendances `deps.ChunkPushServiceDep` / `deps.DocumentTreeServiceDep` aux routes et retirer les délégations.

### [INFO] INFO 27 : l'agrégat `DocumentAnalysisState` porte du suivi de persistance (nouveau, `4939413`)

- **Localisation** : `document-parser/domain/models.py:119-120` (`selection_changed`, `chunk_source_changed`), `:187-190` (`mark_saved`, « appelé par le dépôt ») ; appelants : `document-parser/persistence/document_analysis_repo.py:106`, `persistence/chunk_repo.py:166`, `persistence/analysis_repo.py:194` ; `persistence/analysis_repo.py:185-188` (le dépôt crée l'état et appelle `select` lui-même).
- **Constat** : les drapeaux sont un mécanisme d'écriture partielle (ne pas écraser une sélection concurrente), donc une préoccupation de persistance logée dans le domaine. Le choix est documenté et ciblé (deux booléens, pas d'unité de travail générique). Par ailleurs `complete_and_select` applique une règle métier (« une analyse terminée devient l'active ») et lève `ValueError` dans la couche de persistance.
- **Remediation** : aucune urgence. Si un second dépôt apparaît, déplacer le suivi dans un instantané pris par le dépôt au chargement, et remonter « terminer puis sélectionner » dans le service.

### [INFO] INFO 28 : `ChunkRepository.replace_for_document` reçoit l'état d'analyse (nouveau, `4939413`)

- **Localisation** : `document-parser/domain/ports.py:293-303` ; `document-parser/persistence/chunk_repo.py:13`, `:139-167` ; `document-parser/persistence/document_analysis_repo.py:50-75` (`write_document_analysis_state`, partagé par trois dépôts).
- **Constat** : pour écrire chunks et provenance dans une transaction, le port des chunks dépend de l'agrégat `DocumentAnalysisState`, et toute implémentation de `ChunkRepository` doit savoir persister cet agrégat. C'est de l'ISP côté implémenteur : la méthode est utilisée (`chunk_service.py:348`, `version_service.py:184`), donc 6.4.2 tient, mais le port mélange deux agrégats. Le `ValueError` levé quand `state.document_id != document_id` (`chunk_repo.py:154-155`) n'est pas écrit dans le docstring du port.
- **Remediation** : écrire la précondition dans le port ; à terme, un port d'unité de travail (`DocumentAnalysisTransaction`) qui regroupe les deux écritures.

### [INFO] INFO 29 : `DocumentFileStore` servi en trois tranches disjointes, chemin d'export non résolu (nouveau, `ac7ac17`)

- **Localisation** : `document-parser/domain/ports.py:146-182` ; clients `services/document_service.py:113`, `:176`, `:187` ; `services/export_service.py:98-101` ; `services/preview_service.py:89-90`, `:106`.
- **Constat** : chaque client utilise un sous-ensemble disjoint du port (3, 1 et 2 méthodes). Un seul adaptateur, qui implémente tout, donc rien d'inutile n'est imposé. Deux remarques : (1) `ExportService` vérifie `has_file(doc.storage_path)` et rend `doc.storage_path` brut au routeur, qui l'ouvre (`api/documents.py:146-151`), alors que `PreviewService` passe par `resolve` : un document téléversé sous Docker et lu depuis l'hôte s'affiche en aperçu mais son export PDF répond 404 ; (2) le routeur lit encore le disque par chemin.
- **Remediation** : `ExportService` appelle `resolve` avant `has_file` et renvoie le chemin résolu ; à terme un `open`/flux sur le port si un stockage objet est visé.

### [INFO] INFO 30 : `DocumentAnalysisStateRepository.save_state` sans client de production (nouveau, `4939413`)

- **Localisation** : `document-parser/domain/ports.py:208-210` ; `document-parser/persistence/document_analysis_repo.py:101-106`.
- **Constat** : grep sur `services/`, `api/`, `mcp_adapter/`, `bootstrap/` : aucun appel. Les écritures de l'état passent toutes par `replace_for_document` ou `complete_and_select`. Seuls les tests l'appellent, pour préparer leurs données.
- **Remediation** : le garder s'il annonce un cas d'usage (sélection manuelle d'une analyse), sinon le sortir du port et le garder comme aide de test.

### [INFO] INFO 31 : ajouter une commande d'édition touche une dizaine de fichiers et la base (OCP, préexistant, non relevé jusqu'ici)

- **Localisation** : `document-parser/domain/analysis_editing.py:18-26` (`CommandType`) ; `document-parser/api/schemas.py:169-213` (6 modèles et l'union discriminée) ; `document-parser/api/analysis_edits.py:87-107` (`if/elif` sur `command.type`) ; `document-parser/infra/docling_editor.py:116-142` (`_apply_one`) ; `document-parser/infra/docling_projector.py:142-156` (opérations supportées) ; `document-parser/persistence/database.py:246-248` (`CHECK(command_type IN (...))`) ; front : `frontend/src/features/analysis-editor/types.ts`, `commands.ts`, `store.ts`, `frontend/src/shared/i18n.ts`.
- **Constat** : l'union a 6 membres (`setCommandActive`, septième valeur de `CommandType`, passe par une autre route). Une huitième commande demande 6 modifications côté backend, 4 côté front, et une migration SQLite pour la contrainte `CHECK` (reconstruction de table). De plus, dans `_to_edit_commands`, le `else` final suppose `moveElement` (`api/analysis_edits.py:100-105`) : un nouveau modèle oublié dans le `if/elif` y tomberait et produirait soit une `AttributeError` (500), soit une charge utile de déplacement. Hors fiche (aucun item OCP ne vise l'éditeur), donc INFO.
- **Remediation** : une méthode `to_payload()` sur chaque modèle de requête à la place du `if/elif`, et un `else: raise` explicite en attendant ; `CommandType` dérivé d'une seule liste ; contrainte `CHECK` remplacée par une validation applicative ou une table de référence.

### [INFO] INFO 32 : `PreviewService` transforme toute exception de lecture en 422 (nouveau, `ac7ac17`)

- **Localisation** : `document-parser/services/preview_service.py:121-138` (`except Exception` → `PreviewFileUnreadableError`, 422).
- **Constat** : la traduction des erreurs d'adaptateur (`FileNotFoundError` → 404, `OSError` → 422) est à sa place dans le service et ne fuit pas le chemin serveur. Mais le dernier `except Exception` couvre aussi les erreurs de programmation levées dans le bloc (mauvaise signature d'un appel de port, attribut absent) : elles deviennent un 422 « Failed to generate preview » au lieu d'un 500. Elles sont journalisées (`logger.exception`), donc visibles, mais le client croit à un PDF illisible. Sur un code qui n'a jamais tourné, c'est là qu'un défaut de câblage se cacherait.
- **Remediation** : limiter le dernier `except` aux exceptions que les adaptateurs déclarent (ou laisser passer `TypeError`/`AttributeError`).

### [INFO] INFO 33 : injection par setter non typée, contrat de docstring périmé, promoteur mort (préexistant, non relevé jusqu'ici)

- **Localisation** : `document-parser/services/analysis_service.py:122-136` (`set_chunk_promoter`, `set_version_recorder`, paramètres non typés) ; `document-parser/services/chunk_service.py:150-153` (docstring : `(document_id, analysis_id)`) contre l'appel à trois arguments `:363-365` (`record_on_rechunk(document_id, source_analysis_id, source_result_hash)`, `services/version_service.py:126-131`) ; `_chunk_promoter` affecté (`analysis_service.py:129`, `bootstrap/builder.py:170`) mais jamais lu.
- **Constat** : ces trois dépendances échappent au croisement service → `Protocol`, qui ne voit que les constructeurs. L'appel réel correspond à `VersionService` (vérifié à la main), seul le docstring ment.
- **Remediation** : un port `VersionRecorder` (deux méthodes) typant les deux setters ; supprimer `set_chunk_promoter` et son appel dans le builder.

---

## Delta vs contrôle

**Score** : 100 → **100** (0). **Items** : 15/15 → **15/15**. **Écarts** : 0/0/0/23 → **0/0/0/29**.

**Régression** : aucune sur les invariants vérifiés par le contrôle. Le croisement AST donne 239 accès conformes (236 au contrôle), 0 hors contrat, 0 typage concret, 0 paramètre de constructeur non typé.

| Écart du contrôle | Statut à `efc0bc5` |
|-------------------|--------------------|
| INFO 1, 2, 3, 6, 8, 10, 11, 12, 14, 15, 16, 18, 20, 22, 23 | Toujours présents, inchangés sur le fond (lignes mises à jour). |
| INFO 4 | Toujours présent : `PreviewService` et ses trois adaptateurs construits dans `builder.py:191-197`. |
| INFO 5 | Réduit : la partie `ChunkService` est traitée par `8a60cee` ; reste l'édition legacy d'`AnalysisService`. Le résidu de façade est l'INFO 26. |
| INFO 9 | Réduit : `sources_view.py` découpé en trois modules. |
| INFO 17 | Étendu à `ChunkMergeGapError`. |
| INFO 19 | Réduit : `PageRaster.vue` extrait. |
| INFO 21 (`ValueError` de `render_page` hors contrat, branche morte au routeur) | **Résolu** : contrat écrit dans le port (`domain/ports.py:695-698`), branche `except ValueError` retirée de la route d'aperçu (`api/documents.py:161-172`). |
| INFO 24 (I/O disque dans `DocumentService`) | **Résolu** : port `DocumentFileStore` et adaptateur `LocalDocumentFileStore` ; plus aucune I/O fichier dans `services/`. Remarque nouvelle sur l'export en INFO 29. |
| INFO 25 | Étendu : trois nouveaux imports de services pairs dans `chunk_service.py` et `chunk_push_service.py`, sans entrée `PEERS`. |

| Nouvel écart | Origine |
|--------------|---------|
| INFO 26 : `ChunkService` façade qui construit ses collaborateurs | `8a60cee` |
| INFO 27 : drapeaux de persistance dans `DocumentAnalysisState`, règle métier dans `complete_and_select` | `4939413` |
| INFO 28 : `ChunkRepository.replace_for_document` dépend de l'état d'analyse | `4939413` |
| INFO 29 : `DocumentFileStore` en trois tranches, export sans `resolve` | `ac7ac17` |
| INFO 30 : `save_state` sans client de production | `4939413` |
| INFO 31 : coût d'ajout d'une commande d'édition | préexistant (déjà là à `a12b744`) |
| INFO 32 : `except Exception` → 422 dans `PreviewService` | `ac7ac17` |
| INFO 33 : setters non typés, docstring périmé, promoteur mort | préexistant |

Points demandés par l'appelant, tranchés :
- **SRP `ChunkService`** : façade avec une seconde raison de changer limitée au constructeur (INFO 26) ; ne fait pas tomber 6.1.1.
- **SRP `DocumentAnalysisState`** : oui, il fait du suivi de modification en plus du comportement métier, assumé et minimal (INFO 27) ; ne fait pas tomber 6.1.4.
- **SRP `PreviewService`** : traduire les exceptions d'adaptateur en erreurs de service est son rôle ; seul l'attrape-tout est trop large (INFO 32).
- **OCP union de commandes** : 10 fichiers et une migration pour une huitième commande (INFO 31).
- **LSP** : `ChunkMergeGapError` substituable, ordre d'attrape correct (INFO 17). Les erreurs d'aperçu ont toutes `ServiceError` pour base ; deux d'entre elles redéfinissent `__init__()` sans argument (`preview_service.py:32`, `:53`), ce qui restreint le constructeur de la base, mais aucun code ne les construit de façon générique. Aucune surcharge de méthode de port qui rétrécisse un contrat : le script ne trouve que des écarts compatibles (attribut au lieu de propriété, `limit: int | None` plus large).
- **ISP** : `DocumentFileStore` (INFO 29), `CurrentAnalysisReader` (3 méthodes ; clients : 4 × `find_current_analysis_id`, 4 × `load_current_analysis`, 1 × `find_current_parse_ids`, aucun client n'en prend plus de deux), `AnalysisRepository` (16 méthodes, toutes appelées, 10 clients), `replace_for_document` (INFO 28).
- **DIP** : services qui construisent des collaborateurs (INFO 26) ; `infra/` : les deux middlewares (`host_guard.py`, `body_limit.py`) n'importent que Starlette, `document_file_store.py` que la stdlib ; les imports `infra → infra` restants sont des aides internes (`bbox`, `docling_pages`, `pdfium_lock`, sous-paquet `neo4j`), aucun `infra → persistence/services/api`.

---

## Vérification statique du câblage et des contrats

**Services → ports** (`xcheck.py`) : 239 accès vérifiés, **0 hors `Protocol`**, **0 typage concret** (`infra`/`persistence`, `TYPE_CHECKING` compris), **0 paramètre de constructeur non typé**. Un seul `Any` de port, déjà connu : `graph_writer_factory: Callable[[Any], GraphWriter]` (`services/store_backend_resolver.py:86`). Les deux collaborateurs construits par `ChunkService` (`_push`, `_tree`) ont été vérifiés de la même façon : 0 méthode absente.

**Signatures port ↔ implémentation** : 28 couples port/implémentation trouvés par appariement structurel, dont toutes les nouveautés de la seconde passe, identiques en noms, sortes, défauts et `async` :
- `DocumentFileStore` ↔ `LocalDocumentFileStore` (6 méthodes, toutes sync comme le port) ;
- `DocumentAnalysisStateRepository` ↔ `SqliteDocumentAnalysisRepository` ;
- `CurrentAnalysisReader` ↔ `CurrentAnalysisResolver` (`services/current_analysis.py`) ;
- `ChunkRepository.replace_for_document` (avec `at` et `state` keyword-only) ↔ `SqliteChunkRepository` ;
- `AnalysisRepository.find_parsed_ids`, `find_summaries_by_document` ↔ `SqliteAnalysisRepository` ;
- `PageRasterizer` ↔ `PdfPageRasterizer`, `PdfInspector` ↔ `PdfiumInspector`, `LLMProvider` (sans `type`) ↔ `OllamaProvider`.

Écarts restants, tous compatibles et déjà connus : `supports_page_batching` attribut au lieu de propriété (`infra/local_converter.py:192`, `infra/serve_converter.py:77`) ; `OpenSearchStore.get_chunks(limit=None)` plus large que le port (`infra/opensearch_store.py:168`). Les autres « différences » sorties par le script sont des faux appariements (`get` homonyme de `PreviewCache`, `find_by_id`/`insert` homonymes entre dépôts, `DoclingAnalysisProjector` qui n'implémente pas `AnalysisDocumentEngine` : c'est `DoclingAnalysisEngine` qui le fait, à l'identique).

**Câblage** (`wiring.py` + lecture) : **0 incohérence** sur 134 appels du composition root (`bootstrap/builder.py`, `bootstrap/factories.py`, `bootstrap/mcp_mount.py`, `main.py`, `mcp_stdio.py`, `api/deps.py`, `services/chunk_service.py`). Vérifié à la main en plus :
- `build_chunk_service(**repos)` (`bootstrap/factories.py:245-251`) : les 11 clés passées par `builder.py:145-157` plus `tree_reader` et `chunker` existent toutes dans `ChunkService.__init__` (`services/chunk_service.py:107-122`), les 6 obligatoires sont fournies ;
- `AnalysisService` keyword-only : `build_analysis_service` passe `converter`, `analysis_repo`, `document_repo` par nom et le reste après `*` (`factories.py:202-216`) ;
- `PreviewService(*, documents, files, rasterizer, inspector, cache)` ↔ `builder.py:191-197` ;
- `ExportService(document_repo, analysis_repo, active_result_service, *, current_analysis, file_store)` ↔ `builder.py:200-206` ;
- `CurrentAnalysisResolver(*, state_repo, analysis_repo)` ↔ `builder.py:125-128` et `mcp_stdio.py:68-71` ;
- les 19 clés de `AppStateBuilder._update(...)` sont des champs d'`AppState` (`api/state.py:64-94`) ; une clé inconnue ferait échouer `dataclasses.replace` au démarrage ;
- `BodySizeLimitMiddleware(app, *, path, max_bytes, detail)` et `ApiHostGuardMiddleware(app, *, allowed_hosts)` ↔ `main.py:96-118` ; `settings.max_import_size_mb` et `settings.api_allowed_hosts` existent (`infra/settings.py:31`, `:111`) ;
- `get_driver`, `close_driver`, `AppStateBuilder` passent par des réexportations de paquet (`infra/neo4j/__init__.py:33`, `bootstrap/__init__.py:8`) : signatures conformes.

**Routes → services** (`routes.py`) : 78 usages `service.méthode` sur une dépendance `deps.XxxDep`, **0 méthode absente** (dont `read_page_sizes` après le renommage de `page_sizes`). Grep des API retirées (`find_latest_completed*`, anciens ports de sélection et de provenance, `.page_sizes(`, `provider.type`, `generate_preview`) dans tout le code et les tests : aucun reste.

**Faux de test** : 1 206 constructions de classes du projet dans `tests/`, **0 incohérence** de signature. Faux comparés aux ports :
- `tests/navigation_fixtures.py` : `FakeAnalysisRepository` (4 méthodes sur 16) et `FakeAnalysisStateRepository` (`find_states` seulement) couvrent tout ce que `ParseLoader` → `CurrentAnalysisResolver.find_current_parse_ids` appelle (`find_states`, `find_latest_parsed_ids`, `find_parsed_ids`, `find_parsed_document_id`, `parse_json`). `find_by_id` manque, mais seul `load_current_analysis` l'appelle et le chemin de navigation ne l'emprunte pas. `FakeRasterizer.render_page` n'a pas `fmt` (`:343`) : le seul appelant sous test, `CitationImageService` (`services/citation_image_service.py:90`), ne le passe pas. `FakeDocumentRepository` couvre `find_all` et `find_by_id`, les deux seuls appels.
- `tests/test_reasoning_service.py:44`, `tests/test_reasoning_api.py:74` : `_FakeCurrentAnalysis` n'a que `load_current_analysis`, seule méthode que `ReasoningService` appelle.
- `tests/test_config_api.py:31`, `tests/test_app_config_service.py:34` : `_FakeRepo` sans `replace_namespace`, que seul `McpConfigService` appelle (`services/mcp_config_service.py:156`) ; ces faux servent `AppConfigService`.
- Préexistant, hors périmètre de la passe : `tests/test_vector_store_port.py:11` `FakeVectorStore` n'a ni `ping` ni `search_fulltext`, alors que son test affirme qu'il « satisfait le protocole » (`:43-46`) ; l'assertion ne vérifie rien (`store is not None`).

**Aucune incohérence ne laisse prévoir d'échec au démarrage** par lecture statique.

---

## Points positifs

- **Plus d'I/O fichier dans les services** : `DocumentFileStore` documente chaque exception, ne fuit pas de chemin serveur dans les messages, et son adaptateur garde la protection contre la suppression hors du répertoire d'upload.
- **Une seule règle pour l'analyse courante** : `CurrentAnalysisReader` remplace des lectures dispersées, sept services le reçoivent typé sur le port, et le résolveur lit en nombre fixe de requêtes.
- **Écritures atomiques nommées** : chunks + provenance, analyse terminée + sélection, chacune dans une transaction, avec le SQL de l'état en un seul endroit.
- **Contrats tenus sans exécution** : 239 accès de service, 28 couples port/implémentation, 134 constructions du composition root et 1 206 dans les tests, sans un écart.
- **Middlewares propres** : `ApiHostGuardMiddleware` et `BodySizeLimitMiddleware` sont de l'ASGI pur, configurés par mots-clés, sans dépendance vers les autres couches.
- **Contrat de `render_page` écrit** et branche morte du routeur retirée.

---

## Verdict partiel : GO

Score **100/100**, 15/15 items, **0 CRITICAL**, **0 MAJOR**, 0 MINOR, 29 INFO. La seconde passe garde les invariants du contrôle (aucun appel hors `Protocol`, aucun typage concret) et ferme deux INFO (21, 24). Les huit nouveaux INFO sont des coûts de câblage ou des contrats à préciser ; aucun ne fait tomber un item.

Non vérifié : comportement à l'exécution (rien n'a tourné : ni tests, ni application, ni build, ni type-check), en particulier les transactions partagées entre dépôts, le comportement réel des middlewares, les doubles `AsyncMock`/`MagicMock` sans `spec` (qui acceptent n'importe quel appel et échappent à l'analyse statique), et le front au-delà du comptage des stores et des fichiers touchés par les commandes d'édition.

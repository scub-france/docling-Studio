# Rapport d'audit : SOLID

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.7.3/06-solid.md` (87/100, 0/2/0/10, GO). Pas de re-audit 06 en 0.7.3.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 15 (27 / 31 pondérés) |
| Score | 87 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 15 |

Détail du calcul : poids conformes = 6.1.1 (2) + 6.1.2 (2) + 6.1.3 (1) + 6.2.2 (2) + 6.2.3 (1) + 6.3.1 (3) + 6.3.2 (2) + 6.3.3 (2) + 6.4.1 (2) + 6.4.2 (2) + 6.5.1 (3) + 6.5.2 (2) + 6.5.3 (3) = **27** sur **31**. Items non conformes : 6.1.4 (2), 6.2.1 (2). `27 / 31 * 100 = 87,1` → **87**.

**Delta vs 0.7.3** : **0 point** (87 → 87). Ce sont les mêmes deux items non conformes, avec les mêmes MAJ, toujours ouverts. MAJ-2 s'étend au nouveau moteur d'édition, qui n'a pas de port. Le reste du code 0.7.4 (ports de persistance, routeur, feature frontend) est conforme.

### Périmètre mesuré

| Surface | 0.7.3 | 0.7.4 |
|---------|-------|-------|
| Ports `Protocol` (`domain/ports.py`) | 21 | 24 (+`DocumentMerger`, `AnalysisSelectionRepository`, `ChunkSourceRepository`, `AnalysisEditRepository` ; −`ChunkEditRepository`) |
| Classes de la couche `services/` | 17 | 18 (+`AnalysisEditService`) |
| Routers REST (`api/`) | 10 | 11 (+`api/analysis_edits.py`) |
| Adaptateurs `infra/` ajoutés | — | `DoclingDocumentEditor`, `DoclingAnalysisProjector`, `DoclingDocumentMerger` |
| Stores Pinia de feature | 12 | 13 (+`analysis-editor`) |

---

## Checklist

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 6.1.1 | Chaque service a une responsabilité unique | 2 | ✅ (cf. INFO 5, 6, 11) |
| 6.1.2 | Chaque store Pinia gère un seul feature | 2 | ✅ |
| 6.1.3 | Routes API groupées par ressource | 1 | ✅ |
| 6.1.4 | Aucune classe/module ne cumule des responsabilités hétérogènes (parsing ET persistence) | 2 | ❌ MAJ-1 (reconduit) |
| 6.2.1 | Les ports permettent d'ajouter des adaptateurs sans modifier le code existant | 2 | ❌ MAJ-2 (reconduit, étendu) |
| 6.2.2 | Local/remote extensible via `build_converter()` sans modifier les services | 2 | ✅ |
| 6.2.3 | Nouveau format d'export sans modifier les endpoints | 1 | ✅ (cf. INFO 13) |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | ✅ (cf. INFO 1, 2, 10) |
| 6.3.2 | Pas d'exceptions hors contrat dans les implémentations de ports | 2 | ✅ (cf. INFO 14) |
| 6.3.3 | Pas d'`isinstance()` / `type()` pour différencier les implémentations | 2 | ✅ |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` séparés | 2 | ✅ |
| 6.4.2 | Aucun port ne force une implémentation à définir des méthodes inutiles | 2 | ✅ (cf. INFO 1, 7) |
| 6.5.1 | Les services dépendent de ports, pas d'implémentations concrètes | 3 | ✅ (lecture opérationnelle, cf. note sous MAJ-2) |
| 6.5.2 | Injection au composition root | 2 | ✅ (cf. INFO 4) |
| 6.5.3 | Pas d'instanciation directe d'adaptateurs dans les services | 3 | ✅ |

---

## Vérification des principes

Méthode : lecture des sources du working tree à `eade7fa`, `git diff 1de1929..HEAD`, commandes de la fiche rejouées (grep). Je n'ai exécuté ni outil, ni test, ni build.

### SRP (6.1)

- **6.1.1 conforme.** `AnalysisEditService` (`services/analysis_edit_service.py:48`, 378 l.) porte le cas d'usage d'édition : charger, prévisualiser, sauvegarder, consulter l'historique, basculer une commande, reconstruire. C'est une seule raison de changer, et les opérations de persistance sont déléguées à trois ports. Il sert aussi de résolveur du « résultat actif » pour d'autres contextes et tient un cache mémoire : INFO 11. Les services existants ne grossissent pas : `ChunkService` passe de 1019 à 935 lignes avec le retrait du journal `ChunkEdit`, et `VersionService` gagne la sélection, qui fait partie de son cas d'usage `restore`.
- **6.1.2 conforme.** 13 stores de feature, un `defineStore` par feature. Le nouveau store `analysis-editor` (`frontend/src/features/analysis-editor/store.ts:14`) ne gère que l'éditeur : file de commandes, historique, brouillon local (`:345`). Le store `document` reçoit le chargement du résultat édité pour son workspace (`features/document/store.ts:25-35`) : cela reste son feature (cf. audit 02 pour la frontière).
- **6.1.3 conforme.** Le nouveau routeur `api/analysis_edits.py` regroupe les six routes de la ressource « éditions d'analyse » sous `/api/documents/{doc_id}/analysis-edit*`. L'export édité est un paramètre de la ressource export existante (`api/documents.py:144`).
- **6.1.4 non conforme.** `DocumentService` cumule toujours parsing/rendu PDF et persistence (fichier non modifié depuis 0.7.3). → **MAJ-1**.

### OCP (6.2)

- **6.2.1 non conforme.** Les ports incomplets de 0.7.3 le sont toujours, `VersionService` n'a toujours pas de port, et le moteur d'édition ajouté en 0.7.4 n'en a pas non plus. → **MAJ-2**.
- **6.2.2 conforme.** `build_converter()` et `bootstrap/factories.py` ne sont pas touchés par la sélection local/remote. `LocalConverter`/`ServeConverter` ne sont pas modifiés.
- **6.2.3 conforme.** `export_document` (`api/documents.py:134`) reçoit toujours `ExportFormat` sans dispatch. Le paramètre `edited` choisit la source du contenu, pas le format. Ajouter un format modifie la chaîne du service, pas l'endpoint. Duplication de la chaîne : INFO 13.
- **Dispatch sur le type de commande** : `infra/docling_editor.py:116-134` (if/elif sur `command_type`) et `api/analysis_edits.py:89-105` (mapping DTO → payload) sont deux chaînes qu'il faut étendre à chaque nouvelle commande, en plus du `Literal` `CommandType` (`domain/analysis_editing.py:13-21`) et de l'union discriminée HTTP. C'est le prix normal d'un langage de commandes fermé et versionné (`command_version`), pas un dispatch sur des implémentations. Observation seulement.

### LSP (6.3)

- **6.3.1 conforme (poids 3).** `infra/local_converter.py` et `infra/serve_converter.py` ne sont pas modifiés depuis 1de1929. Constat 0.7.3 inchangé (INFO 1, 2, 10).
- **6.3.2 conforme.** Les nouveaux adaptateurs de ports respectent leur contrat :
  - `SqliteAnalysisEditRepository.save_commands_and_cache` lève `AnalysisEditConflictError`, une exception du domaine (`persistence/analysis_edit_repo.py:160`) ;
  - `SqliteDocumentAnalysisRepository` ne lève rien de spécifique ;
  - `update_status(select_analysis=True)` lève `ValueError` sur une analyse non terminée (`persistence/analysis_repo.py:177-178`), un chemin que le seul appelant ne peut pas atteindre (`services/analysis_service.py:508`, après `mark_completed`).

  Le moteur d'édition n'a pas de port, donc pas de contrat d'exception au sens de l'item : INFO 14.
- **6.3.3 conforme.** Grep de la fiche sur `services/` : les `isinstance` valident des types de payload (`services/chunk_service.py:209`, `services/store_service.py:135`, `:139`, `services/mcp_config_service.py:71`). `api/analysis_edits.py:110-117` discrimine des classes d'exception du domaine, pas des implémentations. `domain/analysis_editing.py:136-138` (`type(target) is not int`) valide un payload.

### ISP (6.4)

- **6.4.1 conforme.** Inchangé. Le nouveau code continue dans ce sens : la sélection et la source des chunks forment deux ports distincts (`AnalysisSelectionRepository`, `ChunkSourceRepository`, `domain/ports.py:141-154`), alors que la table et l'adaptateur sont communs (`persistence/document_analysis_repo.py:9`). C'est de l'ISP côté client : `ChunkService` ne voit que la source, et `AnalysisEditService` voit les deux.
- **6.4.2 conforme.** `AnalysisEditRepository` (`domain/ports.py:256-274`) : ses six méthodes sont toutes implémentées et utilisées. `merge_batches` sur `ServeConverter` (INFO 1) est inchangé. `AnalysisRepository` gagne un paramètre d'effet de bord (INFO 7).

### DIP (6.5)

- **6.5.1 conforme (poids 3), lecture opérationnelle.** Le grep de la fiche (`from infra` dans `services/`) ne remonte que des imports sous `TYPE_CHECKING` (`services/store_backend_resolver.py:40-43`). Aucun import runtime de `infra/` ni de `persistence/`. `AnalysisEditService` type ses cinq dépôts sur des ports (`services/analysis_edit_service.py:24-32`). **Mais** `editor`, `projector` et `graph_writer` ne sont pas typés (`:59-61`), faute de port pour les deux premiers. Voir la note de lecture sous MAJ-2.
- **6.5.2 conforme.** `AnalysisEditService` est construit dans `bootstrap/builder.py:124-134`, et injecté dans `ChunkService` (`:145`), `ExportService` (`:176`) et `AppState`. Le drapeau `analysis_editor_enabled` est copié de `Settings` à la construction de l'`AppState` (`:91`).
- **6.5.3 conforme (poids 3).** Grep `LocalConverter|ServeConverter|LocalChunker` sur `services/` : zéro. `DoclingDocumentEditor()`, `DoclingAnalysisProjector()` et `SqliteAnalysisEditRepository()` sont instanciés au composition root (`bootstrap/builder.py:129-131`), jamais dans un service.

---

## Ecarts constates

### [MAJ] MAJ-1 — `DocumentService` cumule parsing / rendu PDF et persistence (reconduit de 0.7.3, inchangé)

- **Localisation** :
  - `document-parser/services/document_service.py:14-15` (`pypdfium2`, `pdf2image`), ainsi que `generate_preview`, `page_sizes`, `_persist_and_count`, `os.unlink` et `resolve_storage_path`, aux mêmes lignes qu'en 0.7.3 (fichier non modifié depuis 1de1929) ;
  - `document-parser/api/documents.py:193` et `:220` : appels statiques `DocumentService.generate_preview` / `DocumentService.page_sizes` sur la classe (lignes décalées de +4) ;
  - secondaire : `document-parser/services/analysis_service.py:17` (`pypdfium2`).
- **Constat** : aucun changement depuis 0.7.3. Les ports `PageRasterizer`/`PageTextReader` existent, mais `DocumentService` ne les utilise toujours pas. La question de thread-safety pdfium, relevée en PLAUSIBLE en 0.7.3, reste ouverte. Le nouvel adaptateur `DoclingAnalysisProjector` cumule lui aussi plusieurs rôles (INFO 12), mais il ne fait pas de persistence et ne relève donc pas de cet item.
- **Regle violee** : item 6.1.4 — « Aucune classe ou module ne cumule des responsabilités hétérogènes (ex : un service qui fait du parsing ET de la persistence) » (poids 2).
- **Remediation** : celle de 0.7.3, inchangée : aperçu via `PageRasterizer.render_page`, port de géométrie PDF sous le verrou pdfium, injection dans `DocumentService`/`AnalysisService`, router sur l'instance injectée, puis bascule de `pdf2image`/`pypdfium2` en `_SERVICES_FORBIDDEN_EXTERNALS`. Effort M.

### [MAJ] MAJ-2 — Contrats de ports incomplets ou absents : dette 0.7.3 intacte, et le moteur d'édition 0.7.4 sans port

- **Localisation** :
  - **Reconduit de 0.7.3**, méthodes appelées mais absentes du `Protocol` :
    - `AnalysisRepository` (`domain/ports.py:220`) : `find_by_document`, `services/analysis_service.py:204` ;
    - `ChunkPushRepository` (`domain/ports.py:210-217`) : `count_for_document`, `find_for_document`, `services/chunk_service.py:621`, `:624`. Le dépôt a pourtant été renommé et réécrit dans cette release (`persistence/chunk_push_repo.py:68`, `:92`) sans que le port soit complété ;
    - `StoreRepository`, `DocumentStoreLinkRepository`, `DocumentRepository.find_by_ids`, `VectorStore.search_fulltext` : mêmes appels qu'en 0.7.3 (`services/store_service.py`, `services/ingestion_service.py`, fichiers non modifiés).
  - **Port toujours absent** : aucun `DocumentVersionRepository`. `VersionService` reste typé sur `SqliteDocumentVersionRepository` (`services/version_service.py:38`, `:93`), alors que son constructeur a été réécrit en 0.7.4 (`:91-105`) ; méthodes consommées : `:109`, `:137`, `:161`, `:167`.
  - **Nouveau en 0.7.4** :
    - `DoclingDocumentEditor` (`infra/docling_editor.py:33`) et `DoclingAnalysisProjector` (`infra/docling_projector.py:31`) sans port, consommés par `services/analysis_edit_service.py:59-61` (paramètres non typés) et `:94-98`, `:298-311` ; le contrat réel est défini par `infra/docling_editor.py:25-30` (`MutationResult`) ;
    - `graph_writer` non typé (`services/analysis_edit_service.py:61`), alors que le port `GraphWriter` existe (`domain/ports.py:510`) ;
    - `active_result_service=None` non typé dans `services/chunk_service.py:153` et `services/export_service.py:40`, qui appellent `active_result`, `load_editor` et `.job` (`chunk_service.py:378`, `:714` ; `export_service.py:123`, `:131`).
- **Constat** : la dette de 0.7.3 n'a pas bougé, alors que deux des fichiers concernés (`chunk_push_repo.py`, `version_service.py`) ont été réécrits. Le moteur d'édition reproduit le problème à plus grande échelle : aucun `Protocol`, des paramètres sans type, et un contrat qui n'existe que dans la classe concrète. Le service lit quatre attributs d'un `MutationResult` déclaré en infra et transmet un `DoclingDocument` d'un adaptateur à l'autre. Pour écrire un autre moteur (non-Docling, ou un double de test fidèle), il faut lire `infra/docling_editor.py` et `infra/docling_projector.py`. Pour en faire une abstraction, il faut modifier `domain/ports.py` et le service : c'est exactement ce que l'item interdit. Aucun garde-fou ne l'attrape : pas de type-checker en CI, et pytestarch reste inopérant (`tests/test_architecture.py:186-193`, fichier non modifié).
  Le port `DocumentMerger` (`domain/ports.py:99`), lui, a été ajouté sans consommateur (INFO 15) : la release a créé un port inutilisé et laissé sans port l'adaptateur qui en avait besoin.
- **Regle violee** : item 6.2.1 — « Les ports (`domain/ports.py`) permettent d'ajouter de nouveaux adaptateurs sans modifier le code existant » (poids 2).
- **Note de lecture (6.5.1)** : comme en 0.7.3, une lecture stricte de 6.5.1 (« les services dépendent de protocoles abstraits ») ferait tomber l'item, de poids 3, donc en CRIT. Les motifs seraient `VersionService` typé `Sqlite*` et, désormais, `AnalysisEditService` qui dépend de deux collaborateurs sans protocole. Ce rapport garde la lecture opérationnelle du gate 0.7.0, déjà reconduite en 0.7.3 : pas d'import runtime de concrétion, injection au composition root, substitution par duck typing possible. Le constat est donc classé en 6.2.1. Cette décision reste à trancher par le mainteneur. L'absence de port de l'éditeur est par ailleurs jugée CRIT dans l'audit 01 (item 1.4.1, « chaque adaptateur implémente un port »), dont la formulation ne laisse pas cette latitude.
- **Remediation** :
  1. Port `AnalysisDocumentEditor` (`apply_and_project`, `project_serialized` → `ProjectedAnalysis`) dans `domain/ports.py`, implémenté par un adaptateur qui compose éditeur et projecteur. Typer `AnalysisEditService(editor: AnalysisDocumentEditor, graph_writer: GraphWriter | None)`.
  2. Port de lecture `ActiveAnalysisResult` pour `ChunkService`/`ExportService`.
  3. Créer `DocumentVersionRepository`, et compléter `ChunkPushRepository` (`count_for_document`, `find_for_document`) et `AnalysisRepository.find_by_document`.
  4. Remédiations 0.7.3 restantes, la zone Store/ingestion pouvant attendre 0.8.0.
  5. Garde-fou AST interdisant `persistence`/`infra` dans `services/`, même sous `TYPE_CHECKING`, et/ou `mypy` ciblé sur `services/`.

  Effort M.

### [INFO] INFO 1 — `merge_batches` imposé à `ServeConverter`, qui l'implémente en code mort (reconduit)

- **Localisation** : `document-parser/domain/ports.py:86-90` ; `document-parser/infra/serve_converter.py:95-98`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 2 — `supports_page_batching` : `@property` au port, attribut aux adaptateurs (reconduit)

- **Localisation** : `document-parser/domain/ports.py:77-84` ; `document-parser/infra/local_converter.py:192` ; `document-parser/infra/serve_converter.py:77`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 3 — `ServeConverter.health_check()` toujours orphelin (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:189`.
- **Constat** : inchangé, toujours sans appelant.
- **Remediation** : inchangée.

### [INFO] INFO 4 — Composition root : libellés de fiche périmés (reconduit)

- **Localisation** : `docs/audit/audits/06-solid.md` (items 6.2.2, 6.5.2) ; `document-parser/bootstrap/builder.py`, `document-parser/mcp_stdio.py`.
- **Constat** : la fiche cite toujours `main.py` et `_build_converter()`. En 0.7.4, `AnalysisEditService` est construit directement dans `builder.py:124-134`, sans fabrique dans `factories.py` contrairement aux autres services. C'est sans conséquence, mais hétérogène.
- **Remediation** : inchangée (mettre à jour la fiche). Optionnel : `build_analysis_edit_service(...)` dans `factories.py`.

### [INFO] INFO 5 — Dette SRP héritée : `AnalysisService` (édition legacy du blob) et `ChunkService` (reconduit, réduit)

- **Localisation** : `document-parser/services/analysis_service.py:215`, `:239`, `:261` ; `document-parser/services/chunk_service.py:140` (classe, 935 l.).
- **Constat** : les méthodes legacy d'`AnalysisService` sont toujours là. `ChunkService` perd 84 lignes avec le retrait du journal `ChunkEdit`, mais garde push/diff/historique vers les stores et la projection d'arbre. Il gagne en plus la résolution du résultat actif par l'éditeur (`:376-385`, `:712-718`).
- **Remediation** : inchangée.

### [INFO] INFO 6 — `ParseLoader` expose ses dépôts (reconduit)

- **Localisation** : `document-parser/services/parse_loader.py:60-68`.
- **Constat** : inchangé. `ParseLoader` ne connaît pas la sélection active ni les éditions (cf. audit 02, [MAJ] 2.3.1).
- **Remediation** : inchangée.

### [INFO] INFO 7 — `AnalysisRepository` grossit encore, avec un effet de bord inter-agrégats

- **Localisation** : `document-parser/domain/ports.py:220-253`, `:245` (`update_status(job, *, select_analysis: bool = False)`) ; `document-parser/persistence/analysis_repo.py:175-209`.
- **Constat** : 0.7.3 relevait 14 méthodes, dont seulement 3 utilisées par la surface MCP. 0.7.4 ajoute un booléen qui fait écrire au dépôt d'analyses l'état « analyse active » du document. Un drapeau qui change ce qu'écrit une méthode est un motif ISP/SRP : la sélection a déjà son port (`AnalysisSelectionRepository.select`), que l'appelant pourrait utiliser. Le dépôt garde l'avantage de la transaction unique (statut + sélection).
- **Remediation** : passer par `AnalysisSelectionRepository` dans une unité de travail, ou nommer l'opération (`complete_and_select(job)`) plutôt que de la piloter par un booléen.

### [INFO] INFO 8 — `PageRasterizer.crop` détourné en transcodeur (reconduit)

- **Localisation** : `document-parser/services/citation_image_service.py:89-91`.
- **Constat** : inchangé.
- **Remediation** : inchangée.

### [INFO] INFO 9 — Découpage SRP hétérogène dans l'adaptateur MCP (reconduit)

- **Localisation** : `document-parser/mcp_adapter/sources_view.py`, `document-parser/mcp_adapter/apps.py`.
- **Constat** : inchangé (fichiers non modifiés).
- **Remediation** : inchangée.

### [INFO] INFO 10 — `PageElement.level` toujours 0 côté Docling Serve (reconduit)

- **Localisation** : `document-parser/infra/serve_converter.py:377`.
- **Constat** : inchangé. Le projecteur de l'éditeur reconstruit `pages_json` avec un `level` issu de `iterate_items` (`infra/docling_projector.py:199`). Après une sauvegarde, une analyse Serve passe donc de `level=0` à des niveaux réels : le résultat édité est plus fidèle que la base.
- **Remediation** : inchangée.

### [INFO] INFO 11 — `AnalysisEditService` est aussi le résolveur du « résultat actif » des autres contextes, et tient un cache mémoire

- **Localisation** : `document-parser/services/analysis_edit_service.py:105-111` (`active_result`), `:341-353` (`_chunks_stale`), `:73`, `:81-85`, `:101-102` (`_unedited_projection`) ; consommateurs `document-parser/services/chunk_service.py:378`, `document-parser/services/export_service.py:123`.
- **Constat** : trois responsabilités voisines dans le même service :
  1. éditer ;
  2. dire aux chunks et à l'export quel résultat est actif ;
  3. calculer la péremption des chunks.

  Le service tient aussi un cache d'une entrée de la dernière projection non éditée, porté par une instance singleton partagée par toutes les requêtes. Rien de bloquant : tout tourne autour du « résultat d'une analyse ». Mais `ChunkService` et `ExportService` dépendent désormais de tout l'éditeur pour une simple lecture.
- **Regle** : 6.1.1 — observation.
- **Remediation** : extraire un `ActiveResultReader` (lecture seule : sélection, cache, projection) consommé par l'éditeur, les chunks et l'export, et le typer sur un port (cf. MAJ-2, point 2).

### [INFO] INFO 12 — `DoclingAnalysisProjector` produit cinq vues et une politique métier

- **Localisation** : `document-parser/infra/docling_projector.py:34-81` (`project`) ; `:139-150` (politique d'éditabilité) ; `:205-255` (outline sémantique) ; `:257-289` (sérialisation camelCase / snake_case) ; `:19-28` (`_TEXT_LABELS`, inutilisé).
- **Constat** : une seule méthode produit l'export Markdown, l'export HTML, `pages_json`, le modèle d'éditeur JSON et l'arbre. Elle décide aussi quelles opérations sont permises par type d'élément, ce qui est une règle produit. Chaque vue ayant son propre consommateur, la classe a plusieurs raisons de changer. Elle reste cohésive (une seule source, `DoclingDocument`), et elle ne fait pas de persistence : pas de violation de 6.1.4.
- **Regle** : 6.1.4 — observation.
- **Remediation** : sortir la politique d'éditabilité dans le domaine (cf. audit 02), et la sérialisation du modèle d'éditeur dans `api/schemas.py` (cf. audit 01, 1.3.2) ; supprimer `_TEXT_LABELS`.

### [INFO] INFO 13 — Chaîne de sélection de l'analyse dupliquée dans `ExportService.export`

- **Localisation** : `document-parser/services/export_service.py:73-81` (MD) et `:92-99` (JSON).
- **Constat** : les deux formats répètent le même `if edited / elif analysis_id / elif active_result_service / else latest`, avec deux méthodes de dépôt différentes pour le même repli (`find_latest_completed` contre `find_latest_completed_by_document`). Ajouter un format textuel (p.ex. HTML) obligerait à recopier la chaîne une troisième fois. L'endpoint, lui, n'est pas touché : 6.2.3 conforme.
- **Regle** : 6.2.3 — observation.
- **Remediation** : `_resolve_analysis(doc_id, analysis_id, edited)` appelé une fois avant le dispatch par format.

### [INFO] INFO 14 — Exceptions non traduites du moteur d'édition hors de `_project`

- **Localisation** : `document-parser/infra/docling_projector.py:91` (`DoclingDocument.model_validate_json` sans `try`) ; appelé par `document-parser/services/analysis_edit_service.py:94-98` hors du bloc de journalisation de `_project` (`:298-323`) ; `document-parser/api/analysis_edits.py:117` (relance brute, donc 500).
- **Constat** : `DoclingDocumentEditor.apply` traduit les erreurs Pydantic en `AnalysisEditError` (`infra/docling_editor.py:43-46`, `:53-61`), mais pas `project_serialized`. Un cache corrompu ou écrit par une version incompatible de `docling_core` remonte donc en 500 non journalisé par le service, au lieu de forcer un rejeu. Faute de port, il n'y a pas de contrat d'exception au sens de 6.3.2.
- **Regle** : 6.3.2 — observation.
- **Remediation** : dans le port à créer, documenter que `project_serialized` lève `AnalysisEditError`. Côté service, se rabattre sur `_replay` en cas d'échec du cache.

### [INFO] INFO 15 — Port `DocumentMerger` et adaptateur `DoclingDocumentMerger` sans consommateur

- **Localisation** : `document-parser/domain/ports.py:99-102` ; `document-parser/infra/docling_merger.py:12-40` ; seul import : `document-parser/tests/test_docling_merger.py:6`.
- **Constat** : le port est ajouté en 0.7.4 avec un adaptateur testé, mais il n'est câblé ni dans `bootstrap/` ni dans aucun service. La fusion des lots reste faite par `LocalConverter.merge_batches` (`infra/local_converter.py:174`, dans `merge_batches` `:203`), qui fait lui aussi `DoclingDocument.concatenate`. Il y a donc deux implémentations de la même opération, dont l'une est morte.
- **Regle** : 6.2.1 / 6.4.2 — observation.
- **Remediation** : faire déléguer `LocalConverter.merge_batches` à un `DocumentMerger` injecté, ou supprimer le port et l'adaptateur.

---

## Delta vs 0.7.3

**Score** : 87 → **87** (0). **Écarts** : 0/2/0/10 → **0/2/0/15**.

| Écart 0.7.3 | Statut 0.7.4 |
|-------------|--------------|
| [MAJ] MAJ-1 `DocumentService` parsing + persistence (6.1.4) | **Toujours ouvert**, inchangé (`document_service.py` non modifié) |
| [MAJ] MAJ-2 ports incomplets / absents (6.2.1) | **Toujours ouvert, étendu** : aucun port complété, `VersionService` retouché sans port. Moteur d'édition sans port, `graph_writer` et `active_result_service` non typés. |
| [INFO] 1, 2, 3, 6, 8, 9 | **Toujours présents**, inchangés |
| [INFO] 4 (libellés de fiche) | **Toujours présent** ; construction de `AnalysisEditService` hors `factories.py` |
| [INFO] 5 (SRP héritée) | **Toujours présent**, `ChunkService` réduit (1019 → 935 l.) |
| [INFO] 7 (`AnalysisRepository` grossit) | **Toujours présent, étendu** : drapeau `select_analysis` |
| [INFO] 10 (`level=0` Serve) | **Toujours présent** ; le résultat édité le corrige de fait |

| Nouvel écart | Origine |
|--------------|---------|
| INFO 11, 12, 13, 14, 15 | Nouveau code 0.7.4 (éditeur d'analyse, export édité, merger) |

Lecture honnête du delta : le score ne bouge pas parce que les deux items qui tombent étaient déjà tombés en 0.7.3. Le nouveau code n'est pas neutre pour autant. Il aggrave MAJ-2 avec le plus gros adaptateur ajouté par la release, et il rouvre la question de 6.5.1. Les ports de persistance de l'éditeur, en revanche, sont un bon exemple d'ISP.

---

## Points positifs

- **Ports de persistance de l'éditeur bien découpés (ISP).** La sélection et la source des chunks sont deux ports pour une seule table et un seul adaptateur, et chaque client ne voit que ce qu'il consomme (`ChunkService` → `ChunkSourceRepository`, `VersionService` → les deux). `AnalysisEditRepository` expose une écriture atomique commandes + cache (`save_commands_and_cache`, `BEGIN IMMEDIATE`, `persistence/analysis_edit_repo.py:151`), plutôt que deux méthodes que le service devrait orchestrer.
- **Injection au composition root, sans exception.** Les trois nouveaux adaptateurs et le nouveau dépôt sont construits dans `bootstrap/builder.py:124-134`. Aucun service n'instancie quoi que ce soit (6.5.3).
- **Retrait d'une responsabilité (SRP)** : le journal `ChunkEdit` disparaît de `ChunkService` et de `VersionService` (−84 l. dans `chunk_service.py`), ainsi que son port et son dépôt, sans laisser de code mort.
- **Erreurs typées du domaine traduites une fois** (`api/analysis_edits.py:110-117`). L'adaptateur d'édition traduit ses erreurs Pydantic/Docling en `AnalysisEditError` (`infra/docling_editor.py:43-46`, `:53-61`) : le service ne voit pas d'exception Docling.
- **Frontend** : la feature `analysis-editor` a son propre store, son API et ses commandes pures (`commands.ts`, testées). Elle est consommée par la page via le barrel (`pages/AnalysisDetailPage.vue:74`).
- **Drapeau de déploiement appliqué à l'injection** (`api/deps.py:46-49`) : le service ne connaît pas le drapeau (OCP).

---

## Verdict partiel : GO

Score **87/100** (≥ 80), **0 CRITICAL**, **2 MAJOR** (≤ 3, non bloquant selon master §2), 0 MINOR, 15 INFO. Les deux MAJ sont ceux de 0.7.3, non traités, et MAJ-2 s'étend au moteur d'édition.

**Point à trancher par le mainteneur**, reconduit de 0.7.3 et renforcé : en lecture stricte de 6.5.1, l'éditeur sans port et `VersionService` typé `Sqlite*` feraient de cet audit un NO-GO (CRIT). Le correctif du CRIT 1.4.1 de l'audit 01 (port `AnalysisDocumentEditor`) lève aussi la partie éditeur de cette question.

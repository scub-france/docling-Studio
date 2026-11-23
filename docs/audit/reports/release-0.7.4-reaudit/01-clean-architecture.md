# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` @ `f7fc791`, avec #401 et #402, + 13 commits de correction #391-#400 + merge)

Fiche : `docs/audit/audits/01-clean-architecture.md`, cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Baseline : `docs/audit/reports/release-0.7.4/01-clean-architecture.md` (2026-11-13, `eade7fa`, 69/100, 1 CRIT / 3 MAJ / 1 MIN / 7 INFO).
Méthode : analyse statique de l'arbre de travail (grep, lecture, `git diff eade7fa a6fb539`, `git show eade7fa:…` pour le test d'architecture), plus deux one-liners Python en lecture seule : conformité des signatures des deux nouveaux adaptateurs à leurs ports, et calcul des violations de couches réelles comparées à la liste `_LEGACY_LAYER_IMPORTS`. Ni l'application ni les suites de tests n'ont été lancées (résultats fournis : `pytest` 1501 passed / 15 skipped, ruff propre).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 9 |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` n'importe ni FastAPI, ni aiosqlite, ni lib infra | 3 | Oui | Le grep de la fiche ne renvoie rien. Seuls `analysis_editing.py` (+8 l., nouvelle exception) et `ports.py` ont changé dans `domain/`. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Aucun `open(`, `Path(`, `os`, client HTTP ou SQL dans `domain/`. Les ajouts sont des `Protocol` et un alias de type (`domain/ports.py:143`). |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | 26 `Protocol` (+2 : `PreviewImageCache` `:146`, `AnalysisDocumentEngine` `:305`). Le domaine n'a aucun besoin externe nouveau. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import `pydantic` dans `domain/`. |
| 1.2.1 | `services/` n'importe jamais `fastapi`/`Request`/`Response`/`Depends` | 3 | Oui | Le grep de la fiche (étendu à `starlette`) ne renvoie rien. |
| 1.2.2 | Services → dépôts, jamais de SQL direct | 3 | Oui | Aucun `SELECT`/`INSERT`/`execute(`/`aiosqlite` dans `services/`. |
| 1.2.3 | Les règles métier vivent dans `domain/` | 2 | **Non** | Rien n'a bougé : split/merge et citation dans les services, chaîne de hachage de l'éditeur dupliquée service/dépôt, règles d'édition dans l'adaptateur. Voir [MAJ] n°1. |
| 1.2.4 | Dépendances injectées, pas d'import direct de concrétions | 2 | **Non** | Dette inchangée (PDF libs, `Sqlite*Repository`), et le nouveau `PreviewService` importe la classe concrète `DocumentService` pour appeler une méthode statique pdf2image au lieu du port `PageRasterizer`. Voir [MAJ] n°2. |
| 1.3.1 | Les routes n'importent pas `persistence/` | 3 | Oui | Le grep de la fiche ne renvoie rien. Le test AST `test_layer_imports[api]` le garantit désormais réellement (aucune entrée `api/` dans la liste legacy). |
| 1.3.2 | camelCase/snake_case confiné à `api/schemas.py` | 1 | **Non** | Inchangé. Voir [MIN]. |
| 1.3.3 | Les endpoints délèguent toute la logique aux services | 2 | **Non** | Preview déplacé dans un service (progrès), mais jointure store-links, pages via méthode statique, état de l'historique et drapeau d'export restent dans les routeurs. Voir [MAJ] n°3. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | **Oui** | Corrigé par #394 : `DoclingAnalysisEngine` (`infra/docling_analysis_engine.py:14`) implémente `AnalysisDocumentEngine`, `PreviewCache` (`infra/preview_cache.py:13`) implémente `PreviewImageCache` (signatures vérifiées identiques). `DoclingDocumentEditor`/`DoclingAnalysisProjector` ne sont plus importés que par l'adaptateur composite (`infra/docling_analysis_engine.py:7-8`) et par les tests. |
| 1.4.2 | Config issue de `infra/settings.py` | 2 | Oui | Pas de nouvelle lecture d'environnement hors `settings`. La taille du cache de preview est un défaut de constructeur (même tolérance que `default_limit=1000` en `infra/opensearch_store.py:81`) : voir [INFO]. |

Calcul : poids conformes = 3+3+3+2 (1.1.x) + 3+3 (1.2.1, 1.2.2) + 3 (1.3.1) + 3+2 (1.4.x) = **25 / 32**. Non conformes : 1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2). `25 / 32 × 100 = 78,1`, soit **78**.

---

## Ecarts constates

### [MAJ] Règles métier hors domaine : dette split/merge et citation intacte, flux d'édition et règles d'édition toujours hors `domain/`

- **Localisation** :
  - Dette 0.7.3 : `services/chunk_service.py:274` (`split_chunk`, borne d'offset `:276`) et `:317` (`merge_chunks`, contiguïté `:330`), alors que `domain/chunk_editing.py:114` (`merge`) et `:166` (`split`) ne sont importés que par `tests/test_chunk_editing.py:7`. Citation et lecture budgétée : `services/citation_service.py:202` (`_locate_quote`), `services/navigation_service.py:231` (`_pick`).
  - Flux d'édition, dans le service : chaîne de hachage `services/analysis_edit_service.py:387-405`, recopiée dans `persistence/analysis_edit_repo.py:164` et `:211-215` (même format `previous|sequence|type|version|payload`, même `json.dumps(sort_keys=True, separators=(",", ":"))`) ; base immuable `:162-163` ; séquence attendue `:166-170` et `:218-222`, recopiée dans `persistence/analysis_edit_repo.py:155-157` ; péremption des chunks `:368-380`.
  - Règles d'édition dans l'adaptateur : un seul titre `infra/docling_editor.py:180`, niveaux de titre `:177`, fusion de paragraphes compatibles seulement `:218-221`, déplacement sous un titre `:278`, cycles `:275`, racine protégée `:129` ; politique d'éditabilité `infra/docling_projector.py:132-147`.
  - « Seule une analyse terminée devient active » : `persistence/analysis_repo.py:181-182`, recopiée dans `services/version_service.py:171` et `services/analysis_edit_service.py:290`.
- **Constat** : aucun des points de la baseline n'a été traité. #394 a déplacé le moteur derrière un port, mais n'a pas touché aux règles du flux d'édition ; le hash de flux du cache (`analysis_edit_service.py:94`) dépend toujours de deux implémentations identiques, l'une en service, l'autre en persistance.
- **Regle violee** : item 1.2.3 (poids 2).
- **Remediation** : inchangée. `command_hash`/`stream_hash`, `check_base`, `check_sequence`, `chunks_stale` dans `domain/analysis_editing.py`, appelés par le service et le dépôt ; brancher `domain.chunk_editing` dans `ChunkService` ; extraire `locate_quote`/`pick_within_budget` en fonctions pures du domaine. Effort M.

### [MAJ] Services couplés à des concrétions, et le nouveau `PreviewService` contourne le port `PageRasterizer`

- **Localisation** :
  - Nouveau (#401) : `services/preview_service.py:8` (import runtime de `DocumentService`), `:23` (`documents: DocumentService`, classe concrète), `:42-48` (`asyncio.to_thread(DocumentService.generate_preview, …)`, appel statique), `:36-37` (résolution du chemin et `path.stat` dans le service). Le rendu lui-même est en `services/document_service.py:160-179` (`convert_from_path`, PIL `save`), alors qu'un adaptateur du port existe et fait la même chose : `infra/page_raster.py:26-31` (`PdfPageRasterizer.render_page`, port `domain/ports.py:514`, construit en `bootstrap/factories.py:304-306`).
  - Dette inchangée : `services/document_service.py:14-15` (`pypdfium2`, `pdf2image`), `:182` (`page_sizes`), `:96` et `:147` (`os.unlink`) ; `services/analysis_service.py:17` ; `services/version_service.py:39`/`:89` (`SqliteDocumentVersionRepository`, pas de port `DocumentVersionRepository`) ; `services/store_service.py:24-26`/`:144-146` ; `services/chunk_service.py:49-50`/`:146-147` ; `services/store_backend_resolver.py:40-43`/`:81-83` (pools et store infra, dépôt SQLite).
  - Paramètres non typés : `services/analysis_edit_service.py:63` (`graph_writer=None`, alors que le port `GraphWriter` existe, `domain/ports.py:567`) ; `services/chunk_service.py:149` et `services/export_service.py:43` (`active_result_service=None`, qui appellent `load_active_result`/`load_editor`).
- **Constat** : la dette 0.7.3 est intacte. Le code ajouté depuis le 13/11 l'aggrave sur un point : #401 crée un service de toutes pièces et le câble sur la concrétion `DocumentService` plutôt que sur `PageRasterizer`. Le rendu poppler existe donc en deux exemplaires presque identiques (`document_service.py:168-170` et `page_raster.py:29-31`, tous deux réécrits en `convert_from_path` par #398), l'un derrière un port, l'autre non. Le test d'architecture ne le voit pas : `services → services` n'est contrôlé que pour cinq modules (`tests/test_architecture.py:129-135`).
- **Regle violee** : item 1.2.4 (poids 2).
- **Remediation** : `PreviewService(documents: DocumentRepository, storage: …, rasterizer: PageRasterizer, cache: PreviewImageCache)` ; ajouter le format (`PNG`/`WEBP`) au port `PageRasterizer` et supprimer `DocumentService.generate_preview`. Puis, comme en baseline : port d'inspection PDF pour `page_sizes`/comptage de pages, `DocumentVersionRepository`, typage des `Sqlite*` sur leurs ports, `graph_writer: GraphWriter | None`, port de lecture `ActiveAnalysisResult` pour `ChunkService`/`ExportService`. Effort M.

### [MAJ] Couche HTTP qui orchestre encore : store-links, tailles de page, état de l'historique, drapeau d'export

- **Localisation** :
  - `api/documents.py:41-67` (`_fetch_store_links`, jointure de deux dépôts injectés dans la route), appelé en `:122` ;
  - `api/documents.py:213-215` (résolution du chemin puis `asyncio.to_thread(DocumentService.page_sizes, pdf_path)`, appel statique depuis la route) ;
  - `api/documents.py:148` (règle « `edited=true` exige l'éditeur » dans le routeur, pas dans `ExportService`) ;
  - `api/analysis_edits.py:145-147` (`list_history` puis `active_edit_commands(records)` rejoué dans la route ; `list_history` renvoie un `list` non typé, `services/analysis_edit_service.py:113`) ;
  - `api/analysis_edits.py:58` (`json.loads` du modèle d'éditeur pré-sérialisé par l'infra) ;
  - `api/analyses.py:84` (statut HTTP choisi sur le préfixe du message d'une `ValueError`).
- **Constat** : #401 a retiré de `api/documents.py` la lecture disque et le rendu du preview (`de5fe66`, désormais `PreviewService`) : c'est le seul point de la baseline résolu. Les autres sont identiques, à un décalage de lignes près.
- **Regle violee** : item 1.3.3 (poids 2).
- **Remediation** : `DocumentService.get_with_store_links(doc_id)` et `DocumentService.page_sizes(doc_id)` (méthode d'instance via port) ; `AnalysisEditService.history(...) -> list[HistoryEntry]` avec l'état actif ; `ExportService.export_edited` vérifie le drapeau ; `import_docling_document` lève une `ServiceError` typée 404. Effort S à M.

### [MIN] Les conversions camelCase fuient hors de `api/schemas.py` (inchangé)

- **Localisation** : `api/analysis_edits.py:48-54` (`_serialize_tree`, `elementId`) et `:87-103` (payloads `elementId`/`elementIds`/`targetElementId`) ; `infra/docling_projector.py:54` (`baseAnalysisId`) et `:216-229` (`_element_dict`) ; `domain/analysis_editing.py:140` (`targetSequence`) ; `services/analysis_edit_service.py:235` ; `services/analysis_service.py:48-51` ; `services/version_service.py:60-69` ; `services/chunk_service.py:586`, `:631-638`, `:760-763` ; `api/schemas.py:200-201` (`model: dict`, `tree: list[dict]`).
- **Constat** : identique à la baseline. Le modèle d'éditeur est produit en camelCase par l'infra, persisté tel quel, relu par la même infra et renvoyé en `dict` non typé.
- **Regle violee** : item 1.3.2 (poids 1).
- **Remediation** : inchangée (schémas `EditorElementResponse`/`EditorTreeNodeResponse` depuis `ProjectedAnalysis`, payload de commande v1 documenté comme format durable). Effort S.

### [INFO] Test d'architecture : le scanner bite enfin, quelques angles morts restent

- **Localisation** : `tests/test_architecture.py:55-106` (règles de couches AST et liste legacy exacte), `:109-115` (auto-test du scanner), `:129-135` (contrôle `services → services` limité à 5 modules), `:210` et `:230-236` (`pdf2image`/`pypdfium2` tolérés dans tous les services).
- **Constat** : la réécriture remplace les règles pytestarch, qui ne voyaient aucune arête (constat 0.7.3 et baseline), par un scan AST qui couvre les mêmes six couches (`domain`, `services`, `api`, `infra`, `mcp_adapter`, `persistence`) avec les mêmes interdits. Les 11 violations historiques sont listées par couple exact (source, cible) : un import nouveau échoue. J'ai vérifié en lecture seule que la liste est exacte (aucune violation hors liste, aucune entrée périmée). Les contrôles externes, `Protocol` hors `ports.py` et peers des services agents sont repris à l'identique. Aucune règle de l'ancien fichier n'est perdue. Angles morts : le couplage de service à service n'est contrôlé que pour 5 modules (le `PreviewService → DocumentService` du [MAJ] n°2 passe) ; `bootstrap/` est hors périmètre par conception.
- **Remediation** : étendre le contrôle des peers à tout `services/` avec une liste blanche explicite (comme `_LEGACY_LAYER_IMPORTS`).

### [INFO] Le port `DocumentMerger` n'est toujours câblé nulle part

- **Localisation** : `domain/ports.py:100`, `infra/docling_merger.py:12` ; seul usage : `tests/test_docling_merger.py:6`.
- **Constat** : l'adaptateur implémente bien un port (1.4.1 conforme), mais aucun service ni le composition root ne l'utilise.
- **Remediation** : le brancher à la place de `LocalConverter.merge_batches`, ou le supprimer.

### [INFO] Les erreurs de service portent un statut HTTP, et les erreurs de preview sortent de cette hiérarchie

- **Localisation** : `services/errors.py:14` (`http_status`) et ses sous-classes (`services/chunk_service.py:66-83`, `services/version_service.py:76-81`, `services/export_service.py:152-155`…) ; `services/preview_service.py:14-19` (deux exceptions hors `ServiceError`) ; `api/documents.py:189-202` (six `except` dans la route preview).
- **Constat** : #396 unifie la traduction en un seul point (`api/errors.py:25-31`), ce qui est un progrès net. En contrepartie, la couche service choisit le code HTTP : pas d'import FastAPI (1.2.1 conforme), mais une notion du transport dans les services. Les exceptions de #401 ne suivent pas ce modèle.
- **Remediation** : faire hériter les erreurs de preview de `ServiceError` ; à terme, remplacer `http_status` par une catégorie neutre (`not_found`, `conflict`, `invalid`) traduite dans `api/errors.py`.

### [INFO] Le contexte MCP lit la dernière analyse brute, pendant que Studio sert la sélection active éditée (inchangé)

- **Localisation** : `services/parse_loader.py:89` (`latest_parsed_ids`) et `:107` (`parse_json`), face à `services/analysis_edit_service.py:105-111` (`load_active_result`) et `services/chunk_service.py:369-371`.
- **Constat** : identique à la baseline. Relève surtout de l'audit 02.
- **Remediation** : inchangée.

### [INFO] Couplage entre adaptateurs : `persistence` importe `infra` (inchangé)

- **Localisation** : `persistence/store_repo.py:24`.
- **Constat** : identique, désormais inscrit dans la liste legacy du test (`tests/test_architecture.py:77`).
- **Remediation** : inchangée.

### [INFO] Le domaine lit le schéma JSON de Docling (inchangé)

- **Localisation** : `domain/element_reader.py:85-86` (`$ref`/`cref`) ; `domain/parse_index.py:3-6` assume une projection sur le JSON Docling via `DocumentTreeReader`.
- **Constat** : fichiers non modifiés depuis la baseline.
- **Remediation** : inchangée.

### [INFO] Invariants de la sélection active portés par la persistance

- **Localisation** : `persistence/database.py:96-114` (triggers), `persistence/analysis_repo.py:175-192` (`complete_and_select`, `ValueError` en `:181-182`).
- **Constat** : le port a été clarifié (`update_status` séparé de `complete_and_select`, `domain/ports.py`), mais la règle « terminée et appartenant au document » reste dans le SQL et le dépôt. Relève de l'audit 02.
- **Remediation** : inchangée (fabrique de `DocumentAnalysisSelection` dans le domaine).

### [INFO] Valeurs de configuration hors `infra/settings.py`

- **Localisation** : `infra/secrets/fernet_box.py:126`, `persistence/database.py:22` (`DB_PATH`), `persistence/database.py:342` (`DEFAULT_EMBEDDER`, préexistant, absent de la baseline), `mcp_stdio.py:44` ; nouveau : `infra/preview_cache.py:16` (`max_bytes=64 MiB`, construit sans argument en `bootstrap/builder.py:172`).
- **Constat** : aucune lecture d'environnement nouvelle. La taille du cache de preview n'est pas réglable : c'est un défaut de constructeur, pas une constante métier, donc toléré.
- **Remediation** : passer `DB_PATH`, `STORE_SECRET_KEY`, `DEFAULT_EMBEDDER` par `Settings` ; exposer `PREVIEW_CACHE_MAX_BYTES` si le besoin de réglage apparaît.

### [INFO] Frontend : `shared/` dépend de `features/`, et la feature `document` appelle l'API de l'éditeur (hors barème, inchangé)

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56` ; `frontend/src/features/document/ui/DownloadDropdown.vue:135` (`fetch` direct) ; `frontend/src/features/document/api.ts:20-29` (`fetchDocumentEditedAnalysisResult`).
- **Constat** : identique à la baseline. Relève de l'audit 07.
- **Remediation** : inchangée.

---

## Delta vs audit du 2026-11-13

**Score : 69 → 78 (Δ +9).** 9/13 items conformes au lieu de 8/13. Le CRIT est levé ; les trois MAJ et le MIN restent.

| Écart du 2026-11-13 | Statut à `a6fb539` | Détail |
|---------------------|--------------------|--------|
| [CRIT] Moteur de l'éditeur sans port (1.4.1) | **Résolu** | Port `AnalysisDocumentEngine` (`domain/ports.py:305`), adaptateur composite `infra/docling_analysis_engine.py:14`, service typé `engine: AnalysisDocumentEngine` (`services/analysis_edit_service.py:62`). Plus aucun `DoclingDocument`/`MutationResult` ne traverse le service. Reste : `graph_writer` non typé (`:63`), porté dans le MAJ 1.2.4. |
| [MAJ] Règles métier hors domaine (1.2.3) | **Toujours présent** | Code inchangé ; lignes décalées. |
| [MAJ] Concrétions dans les services (1.2.4) | **Toujours présent, étendu** | Nouveau `PreviewService` sur `DocumentService` concret et rendu statique, à côté du port `PageRasterizer` inutilisé pour ce cas. |
| [MAJ] Couche HTTP qui orchestre (1.3.3) | **Toujours présent, réduit** | Preview sorti du routeur ; store-links, page sizes, historique, drapeau d'export, `analyses.py:84` inchangés. |
| [MIN] camelCase hors `api/schemas.py` (1.3.2) | **Toujours présent** | Inchangé. |
| [INFO] pytestarch inopérant | **Résolu** | Scanner AST effectif, liste legacy exacte, auto-test. Remplacé par un INFO sur les angles morts restants. |
| [INFO] `persistence` → `infra.secrets` | Toujours présent | Désormais tracé par le test. |
| [INFO] Schéma Docling lu dans le domaine | Toujours présent | Inchangé. |
| [INFO] Invariants de sélection en persistance | Toujours présent | Port clarifié (`complete_and_select`), règle inchangée. |
| [INFO] Configuration hors `settings` | Toujours présent | + `DEFAULT_EMBEDDER` (préexistant) et taille du cache de preview. |
| [INFO] MCP sur la parse non éditée | Toujours présent | Inchangé. |
| [INFO] Frontend `shared` → `features` | Toujours présent | Inchangé. |

Nouveaux : [INFO] `DocumentMerger` non câblé (était cité dans le CRIT), [INFO] `http_status` dans les erreurs de service et exceptions de preview hors hiérarchie. Le contournement de `PageRasterizer` par `PreviewService` est intégré au [MAJ] 1.2.4.

---

## Points positifs

- **CRIT levé proprement.** `AnalysisDocumentEngine` a exactement la forme recommandée : deux opérations sur du JSON sérialisé et des VO du domaine. L'adaptateur compose éditeur et projecteur en interne (`infra/docling_analysis_engine.py:36-47`), et le service exécute le moteur hors de la boucle d'événements (`services/analysis_edit_service.py:304`, `:331`).
- **Cache de preview derrière un port.** `PreviewImageCache` (`domain/ports.py:146`) est petit, l'adaptateur est borné et thread-safe (`infra/preview_cache.py:16-40`), injecté depuis le composition root (`bootstrap/builder.py:172`).
- **Route preview allégée.** Lecture disque, cache et rendu ne sont plus dans `api/documents.py` (`:173-202` ne fait que traduire).
- **Test d'architecture effectif.** Pour la première fois depuis 0.7.0, une importation interdite entre couches fait échouer la suite, et le test vérifie qu'il sait la détecter (`tests/test_architecture.py:109-115`).
- **Traduction d'erreurs centralisée.** `api/errors.py:25-31` remplace les `HTTPException(status_code=exc.http_status, …)` recopiés dans chaque routeur.
- **Couches pures inchangées.** Domaine sans framework ni I/O, services sans FastAPI ni SQL, API sans `persistence`, aucun import `docling` hors `infra/`.

---

## Verdict partiel : GO CONDITIONNEL

78/100, dans la plage 60-79, 0 CRITICAL, 3 MAJOR (sous le seuil bloquant de « > 3 MAJ »). Plan de remédiation des MAJ, par coût croissant :

1. `PreviewService` sur `PageRasterizer` (+ format) et suppression de `DocumentService.generate_preview` (1.2.4, effort S : le port et l'adaptateur existent).
2. `AnalysisEditService.history` avec état actif, drapeau d'export dans `ExportService` (1.3.3, effort S).
3. Chaîne de hachage et contrôle de séquence dans `domain/analysis_editing.py`, utilisés par service et dépôt (1.2.3, effort M).
4. Dette 0.7.0/0.7.3 : `DocumentVersionRepository`, port d'inspection PDF, store-links dans le service, `domain.chunk_editing` branché.

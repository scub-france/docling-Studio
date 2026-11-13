# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code

Fiche : `docs/audit/audits/01-clean-architecture.md` — cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Baseline : `docs/audit/reports/release-0.7.3/01-clean-architecture.md` (78/100, 0 CRIT / 3 MAJ / 1 MIN / 6 INFO). Pas de rapport 01 dans `release-0.7.3-reaudit/` : les 3 MAJ étaient portés comme dette.
Méthode : analyse statique (grep, lecture de code, `git diff 1de1929..HEAD`). Je n'ai lancé ni l'application, ni les tests, ni aucun build.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 13 |
| Score | 69 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 7 |

Taille du périmètre à eade7fa :

| Couche | Évolution depuis 0.7.3 (1de1929) |
|--------|----------------------------------|
| `domain/` | 27 modules (+1 : `analysis_editing.py`, 145 l.) ; `ChunkEdit`/`ChunkEditAction` supprimés |
| `domain/ports.py` | 24 `Protocol` (+4 : `DocumentMerger`, `AnalysisSelectionRepository`, `ChunkSourceRepository`, `AnalysisEditRepository` ; −1 : `ChunkEditRepository`) |
| `services/` | +1 : `analysis_edit_service.py` (378 l.) ; `chunk_service`, `export_service`, `version_service` modifiés |
| `infra/` | +3 : `docling_editor.py` (338 l.), `docling_projector.py` (289 l.), `docling_merger.py` (40 l.) |
| `persistence/` | +2 : `analysis_edit_repo.py`, `document_analysis_repo.py` ; `chunk_edit_repo.py` → `chunk_push_repo.py` ; upgrade 0.7.3 en place (#391) |
| `api/` | +1 routeur : `api/analysis_edits.py` (217 l.) |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` n'importe ni FastAPI, ni aiosqlite, ni aucune lib infra | 3 | Oui | Le grep de la fiche ne trouve rien. `domain/analysis_editing.py:7-11` n'importe que `dataclasses`, `datetime`, `typing`. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | `analysis_editing.py` est fait de dataclasses gelées et d'une fonction pure (`active_edit_commands`, `:119-145`). Les deux VO ajoutés à `models.py` (`DocumentAnalysisSelection`, `DocumentChunkSource`, `:77-88`) sont des données. |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | Lu au niveau du domaine, comme en 0.7.0 et 0.7.3 : le domaine n'a aucun besoin externe nouveau. Le contournement côté service (moteur d'édition sans port) est jugé en 1.4.1. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import `pydantic`. La validation Pydantic de `DoclingDocument` reste dans `infra/docling_editor.py:44`. |
| 1.2.1 | `services/` n'importe jamais `fastapi`/`Request`/`Response`/`Depends` | 3 | Oui | Le grep de la fiche ne trouve rien. Les erreurs de l'éditeur sont des exceptions du domaine (`domain/analysis_editing.py:107-116`), traduites en HTTP par le routeur. |
| 1.2.2 | Les services appellent les repos, jamais de SQL direct | 3 | Oui | Aucun `SELECT`/`INSERT`/`execute(`/`get_connection` dans `services/` (seuls hits : `get_connection_password`, méthode de dépôt). |
| 1.2.3 | Les règles métier vivent dans `domain/` | 2 | **Non** | Dette split/merge et citation inchangée. Nouvelles règles de l'éditeur dans le service et dans l'adaptateur infra. Voir [MAJ] n°1. |
| 1.2.4 | Dépendances injectées, pas d'import direct de concrétions | 2 | **Non** | Librairies PDF toujours dans `document_service`/`analysis_service`. `VersionService`, modifié par cette release, reste typé sur `SqliteDocumentVersionRepository`. Voir [MAJ] n°2. |
| 1.3.1 | Les routes n'importent pas `persistence/` | 3 | Oui | Le grep de la fiche ne trouve rien. `api/analysis_edits.py` ne reçoit que `AnalysisEditServiceDep` (`api/deps.py:46-52`). |
| 1.3.2 | camelCase/snake_case confiné à `api/schemas.py` | 1 | **Non** | Dette inchangée, étendue au routeur, à l'adaptateur et au domaine de l'éditeur. Voir [MIN]. |
| 1.3.3 | Les endpoints délèguent toute la logique aux services | 2 | **Non** | Jointure store-links et I/O disque toujours dans `api/documents.py`. Le routeur d'historique rejoue lui-même l'état actif des commandes. Voir [MAJ] n°3. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | **Non** | `DoclingDocumentEditor` et `DoclingAnalysisProjector` n'implémentent aucun protocole : il n'en existe pas. Le service les consomme par duck typing, via un type infra qui transporte un `DoclingDocument`. Voir [CRIT]. |
| 1.4.2 | Config issue de `infra/settings.py`, pas de constantes en dur | 2 | Oui | Le nouveau drapeau `ANALYSIS_EDITOR_ENABLED` est dans `infra/settings.py:126`, `:279-280`, copié dans `AppState` au boot (`bootstrap/builder.py:91`). `ENGINE_VERSION` (`services/analysis_edit_service.py:35`) est une constante de format, pas une configuration. Lectures d'environnement hors `settings` inchangées : voir [INFO]. |

Calcul : poids conformes = 22 sur 32 (1.1.1=3, 1.1.2=3, 1.1.3=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.3.1=3, 1.4.2=2). Items non conformes : 1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2), 1.4.1 (3). `22 / 32 * 100 = 68,75`, soit **69**.

---

## Ecarts constates

### [CRIT] Le moteur de l'éditeur d'analyse n'a pas de port : deux adaptateurs Docling consommés par duck typing, avec un `DoclingDocument` qui traverse le service

- **Localisation** :
  - Adaptateurs sans port : `infra/docling_editor.py:33` (`DoclingDocumentEditor`), `infra/docling_projector.py:31` (`DoclingAnalysisProjector`). Aucun protocole correspondant dans `domain/ports.py` (24 `Protocol`, grep `Editor|Projector` : rien).
  - Contrat défini côté infra : `infra/docling_editor.py:25-30` (`MutationResult`, dont `document: DoclingDocument`).
  - Consommateur : `services/analysis_edit_service.py:59-61` (`editor`, `projector`, `graph_writer=None` sans annotation de type) et `:298-311` (`mutation = self._editor.apply(...)` puis `self._projector.project(mutation.document, logical_ids=mutation.logical_ids, ...)`) ; `:94-98` (`project_serialized`).
  - Câblage : `bootstrap/builder.py:130-131`.
- **Constat** : c'est le cœur fonctionnel de 0.7.4, et c'est le seul couple d'adaptateurs consommé par un service sans port. Le service ne connaît son collaborateur que par la forme de la classe concrète :
  1. il lit quatre attributs d'un `MutationResult` déclaré dans `infra/` ;
  2. il fait passer `mutation.document`, un objet `DoclingDocument`, de l'éditeur au projecteur.

  La composition éditeur → projecteur est donc écrite dans le service, mais son contrat n'existe que dans l'infra. Remplacer l'un des deux adaptateurs (moteur non-Docling, double de test fidèle au port) impose de modifier le service. Aucun contrôle statique ne le verrait : les paramètres ne sont pas typés. Le `GraphWriter` passé au même constructeur n'est pas typé non plus, alors que le port existe (`domain/ports.py:510`) et que `AnalysisService` l'annote (`services/analysis_service.py:92`).
  Les tolérances accordées en 0.7.0 et 0.7.3 (`FernetBox`, `RateLimiterMiddleware`, helpers `docling_pages`/`bbox`) concernaient des helpers techniques que ne consomme aucun service. Elles ne s'appliquent pas ici : ces deux adaptateurs sont injectés dans un cas d'usage, ce qui est précisément le rôle d'un port.
  À l'inverse, le seul port ajouté pour Docling, `DocumentMerger` (`domain/ports.py:99`, adaptateur `infra/docling_merger.py:12`), n'est câblé nulle part : il n'est importé que par `tests/test_docling_merger.py:6`.
- **Regle violee** : item 1.4.1 — « Chaque adaptateur dans `infra/` implémente un protocole de `domain/ports.py` » (poids 3).
- **Remediation** : déclarer dans `domain/ports.py` un port unique, p.ex. `AnalysisDocumentEditor`, avec deux opérations :
  - `apply_and_project(document_json: str, *, base_analysis_id: str, commands: Sequence[EditCommand]) -> ProjectedAnalysis` ;
  - `project_serialized(document_json: str, *, base_analysis_id: str, editor_model_json: str) -> ProjectedAnalysis`.

  L'adaptateur infra compose `DoclingDocumentEditor` + `DoclingAnalysisProjector` en interne, si bien que `DoclingDocument` et `MutationResult` ne sortent plus d'`infra/`. Ensuite, typer `AnalysisEditService(editor: AnalysisDocumentEditor, graph_writer: GraphWriter | None)`. Pour `DocumentMerger` : soit le brancher (il double `LocalConverter.merge_batches`), soit le supprimer avec son adaptateur. Effort M.

### [MAJ] Règles métier hors domaine : split/merge et citation toujours dans les services, règles de l'éditeur réparties entre service, dépôt et adaptateur

- **Localisation** :
  - Dette 0.7.3, inchangée : `services/chunk_service.py:278` (`split_chunk`, validation d'offset `:280`) et `:323` (`merge_chunks`, contiguïté `:335-336`), face à `domain/chunk_editing.py:114` (`merge`) et `:166` (`split`), toujours importé seulement par `tests/test_chunk_editing.py`. Règles de citation et de lecture budgétée : `services/citation_service.py:39`, `:201`, `:229`, `:260` ; `services/navigation_service.py:174`, `:201`, `:231` (fichiers non modifiés depuis 1de1929).
  - Nouveau en 0.7.4, dans le service :
    - chaîne de hachage du flux de commandes : `services/analysis_edit_service.py:360-378`, recopiée dans `persistence/analysis_edit_repo.py:164-170`, `:215-219` ;
    - immuabilité de la base : `:162-163` ;
    - concurrence optimiste par séquence : `:166-170`, recopiée dans `persistence/analysis_edit_repo.py:158-163` ;
    - règle « chunks périmés » : `:341-353`, avec le hash de résultat recalculé dans `services/chunk_service.py:425`.
  - Nouveau en 0.7.4, dans l'adaptateur et le dépôt :
    - règles d'édition : un seul titre `infra/docling_editor.py:180`, niveaux de titre `:177`, compatibilité de fusion `:221`, déplacement seulement sous un titre `:278`, cycles `:275`, racine protégée `:129` ;
    - politique d'éditabilité par type d'élément : `infra/docling_projector.py:139-150` ;
    - « seule une analyse terminée peut devenir active » : `persistence/analysis_repo.py:177-178`, recopiée dans `services/version_service.py:171-178` et `services/analysis_edit_service.py:287`.
- **Constat** :
  1. *Dette reportée.* `git diff 1de1929..HEAD` ne touche ni `split_chunk`/`merge_chunks` (hors retrait des lignes d'audit), ni les services de citation. Aucun des trois points de remédiation 0.7.3 n'a été traité.
  2. *Éditeur.* Le domaine ne porte que les contrats et la résolution des bascules actif/inactif (`domain/analysis_editing.py:119-145`, très bien placée). Toutes les autres règles de l'agrégat « flux d'édition » sont ailleurs : chaîne de hachage, séquence attendue, hash de base immuable, péremption des chunks. Deux d'entre elles sont écrites deux fois, dans le service et dans le dépôt : même format `previous|sequence|type|version|payload`, même sérialisation canonique `json.dumps(sort_keys=True, separators=(",", ":"))`, en `analysis_edit_service.py:366` et `analysis_edit_repo.py:168`. Le cache n'est valide que si les deux copies restent identiques (`analysis_edit_service.py:92`).
  3. Les invariants d'édition sont dans l'adaptateur Docling. Le docstring l'assume (« The adapter deliberately owns all Docling-specific behavior », `infra/docling_editor.py:3-4`), mais « un document n'a qu'un titre », « un niveau de titre est compris entre −1 et 6 » ou « on ne fusionne que des paragraphes » sont des règles produit. Le frontend en recopie d'ailleurs une version divergente : `frontend/src/features/analysis-editor/commands.ts:78` accepte un mélange `text`+`paragraph`, que le backend refuse (`docling_editor.py:219-221`).
- **Regle violee** : item 1.2.3 — « Les règles métier vivent dans `domain/`, pas dans les services » (poids 2).
- **Remediation** :
  1. Dette 0.7.3, à reprendre telle quelle (brancher `domain.chunk_editing`, extraire `locate_quote`/`pick_within_budget`).
  2. Créer dans `domain/analysis_editing.py` :
     - `command_hash(previous, sequence, command)` et `stream_hash(stored, pending)`, appelés par le service et par le dépôt ;
     - `EditStream.check_base(hash)` et `check_sequence(expected, actual)` ;
     - `chunks_stale(source, base_id, result_hash)`.
  3. Exprimer dans le domaine les règles d'édition indépendantes de Docling, en validant les payloads de `EditCommand` (`max_titles`, `HEADING_LEVELS`, `MERGEABLE_TYPES`, `MOVE_TARGET_TYPES`) et la politique `supported_operations(type)`. L'adaptateur ne garde que la mécanique de l'arbre. Le frontend peut lire `supportedOperations` au lieu de recopier la règle.

  Effort M.

### [MAJ] Services couplés à des concrétions : librairies PDF hors port, dépôts typés sur l'implémentation SQLite (inchangé, et `VersionService` retouché sans correction)

- **Localisation** :
  - `services/document_service.py:14-15` (`pypdfium2`, `pdf2image`) ; usages inchangés depuis 0.7.3 (fichier non modifié) : `generate_preview`, `page_sizes`, `_persist_and_count`, `os.unlink`, `resolve_storage_path`.
  - `services/analysis_service.py:17` (`import pypdfium2`).
  - `services/version_service.py:38` et `:93` (`SqliteDocumentVersionRepository`), alors que le constructeur a été réécrit dans cette release (`:91-105`, +3 dépendances typées sur des ports) ; `services/chunk_service.py:48-49`, `:150-151` ; `services/store_service.py:23-25`.
- **Constat** : la dette de 0.7.3 est intacte. Le seul fichier concerné que 0.7.4 a modifié est `version_service.py`. Ses trois nouvelles dépendances (`AnalysisRepository`, `AnalysisSelectionRepository`, `ChunkSourceRepository`) sont typées sur des ports, mais le dépôt de versions reste typé sur sa classe SQLite, et aucun `DocumentVersionRepository` n'a été créé. Les nouveaux paramètres `active_result_service=None` (`services/chunk_service.py:153`, `services/export_service.py:40`) ne sont pas typés : la dépendance de ces deux services envers `AnalysisEditService` (ils appellent `active_result`, `load_editor` puis `.job`) n'est visible qu'au câblage (`bootstrap/builder.py:145`, `:176`). En revanche, `AnalysisEditService` ne fait aucun import runtime de concrétion : ses cinq dépôts sont typés sur des ports (`services/analysis_edit_service.py:24-32`).
- **Regle violee** : item 1.2.4 — « Les services reçoivent leurs dépendances par injection, pas par import direct de concrétions » (poids 2).
- **Remediation** : celle de 0.7.3, inchangée (injecter `PageRasterizer` et un port d'inspection PDF dans `DocumentService`, port `FileStorage`, créer `DocumentVersionRepository`). En plus : déclarer dans `domain/ports.py` un port de lecture `ActiveAnalysisResult` (`active_result(document_id)`, `edited_result(document_id, analysis_id)`) et typer `ChunkService`/`ExportService` dessus. Effort M.

### [MAJ] Couche HTTP qui orchestre : jointure de dépôts et I/O disque dans `api/documents.py`, état de l'historique recalculé dans `api/analysis_edits.py`

- **Localisation** :
  - Dette 0.7.3, inchangée : `api/documents.py:40` (`_fetch_store_links`, appels `:52` et `:57`, jointure `:58`), appelé en `:121` ; preview `:180-193` et pages `:217-220` (lecture disque et appels statiques `DocumentService.generate_preview` / `DocumentService.page_sizes`) ; `api/analyses.py:84` (choix 404/400 sur le préfixe du message).
  - Nouveau en 0.7.4 : `api/analysis_edits.py:155-157` ; `api/analysis_edits.py:60` ; `api/documents.py:147-148`.
- **Constat** :
  1. Dette 0.7.3 : rien n'a bougé, à part un décalage de quatre lignes.
  2. *Historique.* `GET /analysis-edits/history` appelle `service.history(...)` puis rejoue lui-même `active_edit_commands(records)` pour calculer l'état actif de chaque commande (`api/analysis_edits.py:156`). Le service a la même information (il appelle la même fonction en `services/analysis_edit_service.py:223`) mais ne l'expose pas. Le cas d'usage « historique avec états » est donc découpé entre la route et le service, et `history` renvoie un `list` non typé (`:113`).
  3. Plus mineur : `_response` désérialise le modèle d'éditeur (`json.loads(snapshot.projection.editor_model_json)`, `api/analysis_edits.py:60`) parce que le service transmet un JSON pré-sérialisé par l'infra. La règle « `edited=true` exige le drapeau éditeur » est vérifiée dans le routeur d'export (`api/documents.py:147-148`) et non dans `ExportService`, qui l'ignore.
- **Regle violee** : item 1.3.3 — « Les endpoints délèguent toute la logique aux services » (poids 2).
- **Remediation** : celle de 0.7.3 pour `api/documents.py`. En plus : `AnalysisEditService.history(...) -> list[HistoryEntry]` avec l'état `active` calculé par le service. `ProjectedAnalysis` porte le modèle d'éditeur en VO (`elements`, déjà présent) et le routeur le sérialise. Effort S pour la partie éditeur, M pour la dette.

### [MIN] Les conversions camelCase fuient hors de `api/schemas.py`, et l'éditeur en ajoute dans le routeur, l'adaptateur et le domaine

- **Localisation** :
  - Dette 0.7.3, inchangée : `services/chunk_service.py:774-777`, `services/analysis_service.py:48-51`, `services/version_service.py:59-68` ; consommateur `api/analyses.py:176-177`, `:199-200`.
  - Nouveau en 0.7.4 :
    - `api/analysis_edits.py:50-56` (`_tree` construit `elementId` à la main) et `:89-105` (payloads `elementId`/`elementIds`/`targetElementId`) ;
    - `infra/docling_projector.py:61` (`baseAnalysisId`) et `:257-271` (`_element_dict` : `selfRef`, `parentId`, `headingLevel`, `supportedOperations`, `nonEditableReason`), relus en `:93` ;
    - `domain/analysis_editing.py:132-133` (`targetSequence`) ;
    - `api/schemas.py` : `AnalysisEditorResponse.model: dict`, `tree: list[dict]`.
- **Constat** : l'éditeur fait du format front son format persistant. Le modèle d'éditeur est sérialisé en camelCase par l'adaptateur infra, stocké tel quel dans le cache (`editor_model_json`), relu en camelCase par ce même adaptateur, puis renvoyé au client sous forme de `dict` non typé. Les payloads de commande sont persistés avec des clés camelCase (`payload_json`) que lit aussi le domaine. Le schéma Pydantic ne fait donc aucune conversion pour ces champs. Les requêtes, elles, sont proprement typées : union discriminée `AnalysisEditCommandRequest` (`api/schemas.py`).
- **Regle violee** : item 1.3.2 — « Les transformations camelCase/snake_case restent dans `api/schemas.py` » (poids 1).
- **Remediation** : schémas `EditorElementResponse`/`EditorTreeNodeResponse` construits depuis `ProjectedAnalysis.elements`/`tree` (VO déjà présents) avec l'`alias_generator`. Le cache peut garder un JSON propre à la persistance, en snake_case, dans `persistence/`. Pour les payloads de commande, le camelCase est désormais un format durable : le documenter comme tel (version de commande 1) plutôt que de le migrer. Effort S.

### [INFO] Le contexte MCP lit la parse brute et la « dernière » analyse, pendant que Studio sert la sélection active et ses éditions

- **Localisation** : `services/parse_loader.py:89` (`latest_parsed_ids`) et `persistence/analysis_repo.py:170` (`SELECT document_json FROM analysis_jobs`) face à `services/analysis_edit_service.py:105-111` (`active_result`) et `services/chunk_service.py:376-385`.
- **Constat** : 0.7.4 introduit une sélection d'analyse active côté backend et des éditions durables. Chunks, export et workspace passent par la sélection et ses éditions, tandis que le serveur MCP continue de citer la dernière analyse terminée, sans les éditions. Les deux chemins restent cohérents avec les ports (pas d'écart d'item), mais un agent MCP peut citer un texte que l'utilisateur a corrigé dans Studio. Le point relève surtout de l'audit 02 (2.3.1).
- **Remediation** : faire résoudre la parse courante du `ParseLoader` par le même port de lecture que l'éditeur (cf. [MAJ] n°2), ou documenter que MCP sert la parse non éditée.

### [INFO] Les règles pytestarch du test d'architecture ne vérifient toujours rien (inchangé)

- **Localisation** : `tests/test_architecture.py:178-193` (fichier non modifié depuis 1de1929).
- **Constat** : identique à 0.7.3. Le nouveau service `analysis_edit_service.py` n'est pas couvert par le contrôle AST « framework-free » (`:206-232`) : rien n'aurait détecté un import `docling` ou `infra` ajouté à l'éditeur.
- **Remediation** : inchangée (scanner `ast` par couche), et ajouter `analysis_edit_service.py` à la liste des services sans framework.

### [INFO] Couplage entre adaptateurs : `persistence` importe `infra` (inchangé)

- **Localisation** : `persistence/store_repo.py:25`.
- **Constat** : identique à 0.7.0 et 0.7.3. Le code concerne l'ingestion, dépréciée en 0.8.0.
- **Remediation** : inchangée.

### [INFO] Le domaine lit le schéma JSON de Docling (inchangé)

- **Localisation** : `domain/parse_index.py:3-6`, `domain/element_reader.py:85-86` (fichiers non modifiés).
- **Constat** : identique à 0.7.3.
- **Remediation** : inchangée.

### [INFO] Invariants de la sélection active portés par la persistance

- **Localisation** : `persistence/database.py:96-114` (triggers `document_analysis_state_validate_*`), `persistence/analysis_repo.py:177-178`, `:202-209`.
- **Constat** : l'invariant « l'analyse active appartient au document » est garanti par deux triggers SQL. L'invariant « elle est terminée » est garanti par `ValueError` dans `update_status`, qui écrit aussi la sélection du document dans la même transaction que le statut de l'analyse. C'est robuste (aucune écriture ne peut contourner un trigger), mais une règle métier vit dans le schéma SQL et un dépôt d'agrégat écrit l'état d'un autre agrégat. Le point relève surtout de l'audit 02 (2.4.2/2.4.3).
- **Remediation** : garder les triggers comme filet de sécurité, et porter la règle dans le domaine (fabrique `DocumentAnalysisSelection.of(document, analysis)` qui refuse une analyse étrangère ou non terminée).

### [INFO] Valeurs de configuration lues hors de `infra/settings.py` (inchangé)

- **Localisation** : `infra/secrets/fernet_box.py:126` ; `persistence/database.py:22` (`DB_PATH`) ; `mcp_stdio.py:44`.
- **Constat** : identique à 0.7.3. Le nouveau drapeau `ANALYSIS_EDITOR_ENABLED`, lui, passe bien par `Settings`.
- **Remediation** : inchangée.

### [INFO] Frontend : `shared/` dépend de `features/`, et la feature `document` appelle l'API de l'éditeur (hors barème)

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56` (inchangé) ; `frontend/src/features/document/ui/DownloadDropdown.vue:135` (`fetch` direct, inchangé) ; nouveau : `frontend/src/features/document/api.ts:20-29` (`fetchDocumentEditedAnalysisResult` sur `/api/documents/{id}/analysis-editor`).
- **Constat** : la nouvelle feature `analysis-editor` est propre : `ui → store → api → @/shared/api/http`, barrel `index.ts`, consommée par `pages/AnalysisDetailPage.vue:74` via le barrel. En revanche, la feature `document` réimplémente un appel à l'endpoint de l'éditeur au lieu de passer par ce barrel. Ce point relève de l'audit 07.
- **Remediation** : exposer `fetchEditedResult` depuis `@/features/analysis-editor` et le consommer depuis `document/store.ts`.

---

## Delta vs 0.7.3

**Score : 78 → 69 (Δ −9).** 8/13 items conformes au lieu de 9/13. Le nouvel item non conforme est 1.4.1, de poids 3 : il ouvre le premier CRITICAL de cet audit depuis 0.7.0.

| Écart 0.7.3 | Statut en 0.7.4 | Détail |
|-------------|-----------------|--------|
| [MAJ] Règles métier dans les services : split/merge, citation, lecture budgétée (1.2.3) | **Toujours ouvert, étendu** | Code de dette inchangé. Nouvelles règles de flux d'édition dans le service et le dépôt, règles d'édition dans l'adaptateur. |
| [MAJ] Concrétions dans les services : librairies PDF, `Sqlite*Repository` (1.2.4) | **Toujours ouvert** | `document_service.py` non modifié. `version_service.py` réécrit sans créer `DocumentVersionRepository`. Nouveaux `active_result_service` non typés. |
| [MAJ] Couche HTTP qui orchestre `api/documents.py` (1.3.3) | **Toujours ouvert, étendu** | Code identique (lignes décalées de +4). Calcul de l'état de l'historique dans `api/analysis_edits.py:156`. |
| [MIN] camelCase hors `api/schemas.py` (1.3.2) | **Toujours ouvert, étendu** | Modèle d'éditeur camelCase construit en infra et dans le routeur, persisté et relu. |
| [INFO] pytestarch inopérant | Toujours présent | Le nouveau service n'est pas sous garde AST. |
| [INFO] `persistence` → `infra.secrets` | Toujours présent | Inchangé. |
| [INFO] Schéma Docling lu dans le domaine | Toujours présent | Inchangé. |
| [INFO] Configuration hors `settings` | Toujours présent | Inchangé. Le nouveau drapeau respecte la règle. |
| [INFO] Frontend `shared`/`pages` → `features` | Toujours présent, étendu | La feature `document` appelle l'API de l'éditeur. |

Nouveaux en 0.7.4 : [CRIT] moteur d'édition sans port (1.4.1), [INFO] MCP sur la parse non éditée, [INFO] invariants de sélection dans la persistance.

---

## Points positifs

- **Domaine de l'éditeur pur et petit.** `domain/analysis_editing.py` ne contient que des VO gelés et une fonction pure. La résolution append-only des bascules actif/inactif (`active_edit_commands`, `:119-145`) y est bien placée et elle est réutilisée par le service et le routeur, sans être dupliquée.
- **Ports de persistance bien découpés.** `AnalysisSelectionRepository` et `ChunkSourceRepository` (`domain/ports.py:141-154`) sont deux petits ports implémentés par un même adaptateur (`persistence/document_analysis_repo.py:9`). `AnalysisEditRepository` (`:256`) expose une écriture atomique commandes + cache (`save_commands_and_cache`, `BEGIN IMMEDIATE` en `persistence/analysis_edit_repo.py:151`).
- **Aucun type Docling importé hors `infra/`.** `services/` et `domain/` restent sans import `docling`. Toute la manipulation de l'arbre est confinée dans `infra/docling_editor.py`/`docling_projector.py`. L'écart [CRIT] porte sur l'absence de contrat, pas sur une fuite d'import.
- **Le journal d'audit des chunks est retiré proprement.** `ChunkEdit`, `ChunkEditAction`, `ChunkEditRepository` et leurs appels sont supprimés de toutes les couches (domaine, port, service, câblage), et non laissés en code mort.
- **Erreurs typées traduites une fois.** `AnalysisEditError`/`ConflictError`/`UnavailableError` (`domain/analysis_editing.py:107-116`) deviennent 400/409 dans un seul `_raise` (`api/analysis_edits.py:110-117`). Le routeur ne lit pas les messages, au contraire de `api/analyses.py:84`.
- **Drapeau de déploiement propre.** `ANALYSIS_EDITOR_ENABLED` vient de `Settings`, il est copié dans l'`AppState` gelé et appliqué à l'injection (`api/deps.py:46-49`) : le service ignore le drapeau.
- **API sans persistence** (1.3.1) et **services sans framework ni SQL** (1.2.1, 1.2.2) : toujours conformes, y compris pour `api/analysis_edits.py` et `services/analysis_edit_service.py`.

---

## Verdict partiel : NO-GO

Il y a un écart CRITICAL (1.4.1) : selon la règle absolue du master §3, c'est un NO-GO quel que soit le score (69/100, dans la plage 60-79). Il y a aussi trois écarts MAJOR, ce qui ne dépasse pas à lui seul le seuil « > 3 MAJ ».

Le CRIT est circonscrit, et peu coûteux à lever : un `Protocol` dans `domain/ports.py`, un adaptateur qui compose éditeur et projecteur, et le typage du constructeur de `AnalysisEditService`. Aucun comportement ne change. Une fois ce point corrigé, l'audit repasserait à 78 (GO CONDITIONNEL), avec les trois mêmes MAJ que 0.7.0 et 0.7.3, toujours non traités. Ordre recommandé :

1. Port `AnalysisDocumentEditor` et typage de `AnalysisEditService` (1.4.1, lève le NO-GO).
2. Déplacer dans le domaine la chaîne de hachage et la règle de péremption, aujourd'hui dupliquées entre service et dépôt (1.2.3).
3. Faire renvoyer l'état actif par `AnalysisEditService.history` (1.3.3).
4. Dette 0.7.0/0.7.3 : `PageRasterizer` dans `DocumentService`, `DocumentVersionRepository`, store-links dans le service.

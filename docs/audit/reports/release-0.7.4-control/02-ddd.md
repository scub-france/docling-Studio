# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a12b744` (arbre de travail)

Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`docs/audit/reports/release-0.7.4-reaudit/02-ddd.md` : 83/100, 0 CRIT / 2 MAJ / 12 MIN / 9 INFO, GO).

Référence : fiche `docs/audit/audits/02-ddd.md`, barème `docs/audit/master.md` §2, §3, §5.
Méthode : lecture statique de l'arbre de travail, `grep`, `git diff a6fb539 a12b744` (15 commits). Ni application, ni tests, ni build lancés par cet audit. Résultats obtenus par ailleurs sur `a12b744` : ruff propre, pytest 1559 passés / 15 ignorés, eslint / prettier / `vue-tsc` propres, vitest 605 passés, `vite build` OK. Même grille de lecture que le re-audit, pour que les scores se comparent.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 17 |
| Score | 83 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 2 |
| Écarts MINOR | 12 |
| Écarts INFO | 11 |

Score = (30 / 36) × 100 = 83,3 → **83**. Items non conformes : 2.3.1 (poids 2), 2.4.3 (2), 2.2.4 (1), 2.3.3 (1). Inchangé par rapport à `a6fb539`.

Comme dans les audits précédents, une partie des [MIN] et [INFO] sont des dégradations relevées sur des items restés conformes ; seuls 2.2.4 et 2.3.3 sont des items de poids 1 non conformes.

### Métriques de périmètre (`a6fb539` → `a12b744`)

| Mesure | a6fb539 | a12b744 |
|--------|---------|---------|
| Modules `document-parser/domain/*.py` | 27 | 27 |
| Dataclasses `frozen=True` dans `domain/` | 62 | 64 (+`EditHistoryEntry`, +`EditorSnapshot` déplacé du service) |
| Dataclasses mutables (`@dataclass` nu) dans `domain/` | 7 | 7 |
| `Protocol` dans `domain/ports.py` | 26 | 32 (+`DocumentFileLocator`, `DocumentVersionRepository`, `ActiveAnalysisResultReader`, `VectorStorePool`, `GraphDriverPool`, `PdfInspector`) |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| Imports `pypdfium2` / `pdf2image` dans `services/` | 1 module (`document_service.py`) | 0 (deux mentions en commentaire seulement) |
| `domain/models.py` | 314 l. | 314 l. |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 147 | 147 |
| Classes `*Manager/Handler/Processor/Helper/Util` | 0 | 0 |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Contextes inchangés. L'aperçu PDF est désormais derrière ses ports (`document-parser/services/preview_service.py:42-45`, `domain/ports.py:148`, `:654`) ; `DocumentService` ne fait plus d'aperçu (`services/document_service.py:1`). |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `models.py` stable (314 l.). `EditorSnapshot` rejoint `domain/analysis_editing.py:121`, dans son contexte. |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Chunks et export dépendent maintenant d'un port typé `ActiveAnalysisResultReader` (`domain/ports.py:360`, `services/chunk_service.py:149`, `services/export_service.py:43`). Restent : le port publie `EditorSnapshot.job` (une `AnalysisJob` forgée), et des contrats en tuples ([MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI (MIN) | `history` passe par le barrel `@/features/analysis` (`frontend/src/features/history/api.ts:2-5`). La feature `document` rappelle toujours l'endpoint de l'éditeur (`frontend/src/features/document/api.ts:26`) ([MIN]). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI (MIN) | Entités inchangées. `EditorSnapshot` fabrique toujours un `AnalysisJob` à identité `working:{doc}:{base}` (`services/analysis_edit_service.py:352-368`) ([MIN]). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | Les deux nouvelles dataclasses du domaine sont gelées. `SourceHop` toujours muté (`domain/source_map.py:202-203`) ([MIN]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | Aucun `save`/`update` sur un VO ; `DocumentStoreLinkView` (`services/document_service.py:47`) est un read model sans méthode. |
| 2.2.4 | Entités porteuses de comportement | 1 | **NON** | `EditStream` (`domain/analysis_editing.py:57-61`) reste un sac de quatre champs ; séquence et chaîne de hachage toujours dans le service et le dépôt. Voir [MIN]. |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Trois définitions de « l'analyse courante » toujours en place (non ciblé par la remédiation). « Historique » désigne désormais trois choses. Voir [MAJ] n°1 et [MIN]. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | Les renommages verbe-d'abord gardent le nom métier (`list_section_refs`, `read_element_text`, `build_span_ref`, `hash_chunkset`, `find_preamble_range`, `read_glyphs`) ; 0 classe générique. Voir [INFO] sur les renommages. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | `STATUS_PATH/READ/CITED` (`domain/source_map.py:44-46`), `STATUS_UNREAD` (`domain/source_bar.py:20`), `operation: str` (`services/analysis_edit_service.py:329`), `EditorElement.type: str` (`domain/analysis_editing.py:75`). Voir [MIN]. |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | Racines inchangées. L'état « analyse active / source des chunks » est jugé en 2.4.3. |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Aucun état invalide persisté. Le hash de résultat a maintenant une seule définition dans le domaine (`domain/analysis_editing.py:129-135`). Les règles d'édition et de sélection restent hors domaine ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | **NON** | Aucun changement : `complete_and_select` dans le dépôt d'`AnalysisJob`, `restore` et `rechunk_document` en écritures séparées. Voir [MAJ] n°2. |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Les nouveaux ports de dépôt renvoient des entités (`DocumentVersionRepository`, `domain/ports.py`) ; `AnalysisJob` partiellement hydratée reconduite ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | Commandes HTTP traduites en `EditCommand` ; toutes les erreurs de service, aperçu, export et import compris, traduites en un point (`document-parser/api/errors.py:28-31`, `api/documents.py:131-132`, `:164-165`, `api/analyses.py:84-85`). |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | 0 import Docling ; `pypdfium2`/`pdf2image` sortis de `document_service.py` vers `infra/pdf_inspector.py` ; `store_backend_resolver` typé sur `VectorStore` et des ports de pool (`services/store_backend_resolver.py:39-45`, `:63`, `:84-85`). Reste le schéma Docling lu dans le domaine ([MIN]). |

---

## Écarts constatés

### [MAJ] Langage ubiquitaire : « l'analyse courante » a toujours trois définitions (inchangé)

- **Localisation** :
  - **sélection active** : `document-parser/domain/models.py:78-80` (`DocumentAnalysisSelection`), `document-parser/services/analysis_edit_service.py:99-102` (`load_active_result`), `:285` ;
  - **dernière terminée** : `document-parser/services/parse_loader.py:89` (MCP, `find_latest_parsed_ids`), `document-parser/services/navigation_service.py:87`, `document-parser/services/citation_service.py:198`, `document-parser/services/reasoning_service.py:97` (Ask), `document-parser/services/export_service.py:122-123` (deux méthodes de port différentes selon le format), `document-parser/services/chunk_service.py:377`, `:708` ; ports `document-parser/domain/ports.py:314`, `:316` ;
  - **première version de l'historique** : `frontend/src/features/document/store.ts:152`, `:180` (`versions[0]`) ;
  - homonymie « version » : `document-parser/domain/anchors.py:7-11` et `document-parser/services/parse_loader.py:73` (`version_id` = id d'analyse) vs `document-parser/domain/models.py:294` (`DocumentVersion`) ;
  - vocabulaire de l'éditeur : `setCommandActive` (`document-parser/domain/analysis_editing.py:24`) vs `"reapply"`/`"revert"` (`document-parser/services/analysis_edit_service.py:230`) vs « Annuler » / « Réappliquer » (`frontend/src/shared/i18n.ts:524-525`), « Annuler » repris pour l'undo local (`:552`).
- **Constat** : la remédiation ne visait pas ce point et ne l'a pas touché. Les renommages ont seulement préfixé les méthodes (`latest_parsed_ids` → `find_latest_parsed_ids`) ; les deux méthodes `find_latest_completed` et `find_latest_completed_by_document` coexistent toujours. Effet inchangé : après une correction sauvegardée, Studio affiche, chunke et exporte le texte édité de l'analyse sélectionnée, tandis que MCP et Ask servent la dernière analyse terminée, texte d'origine.
- **Règle violée** : 2.3.1 (poids 2).
- **Remédiation** : celle du re-audit. La sélection active comme seule définition (`ParseLoader`, `ReasoningService`, `NavigationService`, `CitationService` résolvent `version_id=None` par `AnalysisSelectionRepository` et lisent le résultat édité) ; supprimer les replis « latest » d'`ExportService`/`ChunkService` ; le frontend lit la sélection renvoyée par le backend ; un terme unique pour la bascule ; glossaire. Effort M.

### [MAJ] L'état « analyse active + source des chunks » du document est toujours modifié sans racine (inchangé)

- **Localisation** :
  - `document-parser/persistence/analysis_repo.py:175-192` (`complete_and_select` : le dépôt d'`AnalysisJob` écrit `document_analysis_state`), appelé par `document-parser/services/analysis_service.py:528` ;
  - `document-parser/services/version_service.py:160-203` (`restore` : `soft_delete_for_document` `:179`, `insert_many` `:187`, `clear_selection`/`select` `:192-194`, `clear_chunk_source`/`set_chunk_source` `:198-200`) ;
  - `document-parser/services/chunk_service.py:362-418` (`rechunk_document` : suppression `:388`, insertion `:404`, `set_chunk_source` `:416`) ;
  - `document-parser/domain/ports.py:168`, `:176` : deux ports pour la même ligne, une seule implémentation (`document-parser/persistence/document_analysis_repo.py:9`).
- **Constat** : aucune modification depuis `a6fb539` hormis des renommages internes (`_utcnow` → `_get_utc_now`). Pas d'entité `DocumentAnalysisState`, écritures séparées dans `restore` (un échec entre `:187` et `:192` laisse des chunks restaurés avec l'ancienne sélection, PLAUSIBLE, chemin d'erreur non vérifié).
- **Règle violée** : 2.4.3 (poids 2).
- **Remédiation** : modéliser `DocumentAnalysisState(document_id, active_analysis_id, chunks_source)` avec `select`, `clear`, `chunks_generated` ; un port unique ; `restore` et `rechunk` en une unité de travail. Effort M.

### [MIN] `EditStream` reste anémique ; la chaîne de hachage est toujours écrite deux fois, désormais sous le même nom (item non conforme)

- **Localisation** : `document-parser/domain/analysis_editing.py:57-61` ; `document-parser/services/analysis_edit_service.py:384-403` (`_hash_stream`, `_hash_command(previous, sequence, command, payload)`) ; `document-parser/persistence/analysis_edit_repo.py:165`, `:211-215` (`_hash_command(previous, sequence, kind, version, payload)`).
- **Constat** : le fond est inchangé. Le renommage `_command_hash` → `_hash_command` a donné le même nom aux deux copies, avec des signatures différentes : la duplication est plus difficile à voir, pas résolue. Une divergence invaliderait toujours le cache en silence.
- **Règle violée** : 2.2.4 (poids 1).
- **Remédiation** : une fonction `hash_command` dans `domain/analysis_editing.py`, à côté de `hash_result`, utilisée par le service et le dépôt ; `EditStream.append(...)`, `EditStream.accepts_base(hash)`. Effort S.

### [MIN] Statuts et genres du contexte navigation en chaînes nues (inchangé, item non conforme)

- **Localisation** : `document-parser/domain/source_map.py:44-48` ; `document-parser/domain/source_bar.py:20-22` ; `operation: str` (`document-parser/services/analysis_edit_service.py:329`) ; `EditorElement.type: str` (`document-parser/domain/analysis_editing.py:75`).
- **Constat** : inchangé (les fichiers `source_map.py` et `navigation.py` ont été modifiés, uniquement par des renommages de fonctions).
- **Règle violée** : 2.3.3 (poids 1).
- **Remédiation** : `SourceStatus`, `OutlineNodeKind`, `OutlineMode` ; `Literal["preview", "save", "replay"]` pour l'opération.

### [MIN] « Historique » nomme trois concepts ; l'alias explicite `deleteHistoryEntry = deleteAnalysis` (nouveau, introduit par la remédiation)

- **Localisation** : `frontend/src/features/history/api.ts:2-5` (`fetchAnalysisSummaries as fetchHistory`, `deleteAnalysis as deleteHistoryEntry`) ; `document-parser/domain/analysis_editing.py:48` (`EditHistoryEntry` = une commande d'édition) ; `frontend/src/features/analysis-editor/types.ts:66` et `document-parser/api/schemas.py:222` (`AnalysisEditHistoryEntry…`) ; `frontend/src/pages/DocIngestTab.logic.ts:181` (`toHistoryEntry` = un push de chunks).
- **Constat** : `450dad6` a bien supprimé la duplication de l'appel HTTP, mais en ré-exportant les fonctions de l'analyse sous un autre nom : le code dit maintenant en toutes lettres qu'une « entrée d'historique » est une analyse. En parallèle, `437058d` crée dans le domaine `EditHistoryEntry`, où une « entrée d'historique » est une commande d'édition, et l'API la publie sous un troisième nom (`AnalysisEditHistoryEntryResponse`). Le même mot couvre donc une analyse, une commande d'édition et un push de chunks.
- **Règle violée** : 2.3.1 (déjà non conforme) — dégradation.
- **Remédiation** : côté front, appeler `fetchAnalysisSummaries`/`deleteAnalysis` sous leur nom dans le store `history` ; côté éditeur, un seul nom de bout en bout (`EditHistoryEntry` ou `AnalysisEditHistoryEntry`), à poser dans le glossaire.

### [MIN] Invariants d'édition et de sélection hors du domaine (inchangé)

- **Localisation** : règles d'édition en infra : `document-parser/infra/docling_editor.py` ; politique d'éditabilité : `document-parser/infra/docling_projector.py` ; « analyse active terminée et appartenant au document », écrit quatre fois : `document-parser/persistence/database.py:96-114`, `document-parser/persistence/analysis_repo.py:181-182`, `document-parser/services/version_service.py:166-174`, `document-parser/services/analysis_edit_service.py:279-297` ; `DocumentAnalysisSelection` sans fabrique (`document-parser/domain/models.py:78-80`).
- **Constat** : les fichiers ont été touchés par des renommages seulement. Aucun état invalide persisté : item maintenu conforme.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : `DocumentAnalysisSelection.of(document_id, analysis)` qui refuse une analyse étrangère ou non terminée ; fabriques validantes pour `EditCommand`.

### [MIN] `EditorSnapshot` fabrique toujours un `AnalysisJob` à identité forgée, désormais publié par un port du domaine

- **Localisation** : `document-parser/services/analysis_edit_service.py:352-368` (`id=f"working:{document.id}:{base.id}"` `:356`) ; `document-parser/domain/analysis_editing.py:121-126` ; `document-parser/domain/ports.py:360-372` ; consommé par `document-parser/services/chunk_service.py:704`, `document-parser/services/export_service.py:136-138`.
- **Constat** : le défaut est inchangé, et il est maintenant inscrit dans le domaine : `EditorSnapshot` a quitté le module de service pour `domain/analysis_editing.py`, et le nouveau port `ActiveAnalysisResultReader` le renvoie. Le domaine publie donc une `AnalysisJob` jamais persistée, née `COMPLETED`, comme contrat de lecture.
- **Règle violée** : 2.2.1 — conforme ; dégradation.
- **Remédiation** : VO `EditedAnalysisResult(base_analysis_id, document_json, markdown, pages_json, ...)` renvoyé par le port ; DTO HTTP dédié.

### [MIN] Frontières inter-contextes : côté front, la feature `document` rappelle l'éditeur (réduit)

- **Localisation** : `frontend/src/features/document/api.ts:20-29` ; `frontend/src/features/document/store.ts:25-35`.
- **Constat** : la partie backend est résolue : `active_result_service` est typé sur `ActiveAnalysisResultReader` dans `ChunkService` et `ExportService`, et les dépôts `Sqlite*` ont disparu des signatures de service (`services/chunk_service.py:146-149`, `services/version_service.py:89`). Reste la feature `document` qui appelle `GET /analysis-editor` sans passer par `frontend/src/features/analysis-editor/api.ts`.
- **Règle violée** : 2.1.4 — conforme ; dégradation.
- **Remédiation** : exposer la lecture du résultat édité depuis le barrel de l'éditeur.

### [MIN] « Document introuvable » : six classes au lieu de cinq ; l'aperçu est rentré dans `ServiceError` (réduit et aggravé)

- **Localisation** : `document-parser/services/chunk_service.py:74` (`DocumentNotFoundError`), `document-parser/services/navigation_errors.py:21` (`DocumentNotFoundError`, homonyme), `document-parser/services/preview_service.py:17` (`PreviewDocumentNotFoundError`), `document-parser/services/analysis_service.py:59` (`ImportDocumentNotFoundError`, **nouveau**), `document-parser/services/export_service.py:152` (`ExportNotFoundError`), `document-parser/domain/analysis_editing.py:150` (`AnalysisEditNotFoundError`).
- **Constat** : la partie « erreurs d'aperçu hors `ServiceError` » est résolue (`preview_service.py:17-35`, traduites par `api/errors.py`). Mais `437058d` a ajouté une sixième classe pour le même concept métier, au lieu de réutiliser une existante. Toutes sont des 404 du même fait : le document n'existe pas.
- **Règle violée** : 2.3.1 (déjà non conforme) / 2.1.3 — dégradation.
- **Remédiation** : une `DocumentNotFoundError` unique dans `services/errors.py`, dont les familles héritent ou qu'elles lèvent directement.

### [MIN] Le schéma JSON Docling est lu dans le domaine (inchangé)

- **Localisation** : `document-parser/domain/ports.py` (`DocumentTreeReader`, `list_dfs_order`) ; `document-parser/domain/element_reader.py` ; `document-parser/domain/parse_index.py` ; `EditorElement.self_ref` (`document-parser/domain/analysis_editing.py:71-76`).
- **Constat** : inchangé (renommages seulement). Seule réserve sur 2.5.3.
- **Règle violée** : 2.5.3 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] Règles cœur du contexte citation dans les services (inchangé)

- **Localisation** : `document-parser/services/citation_service.py` ; `document-parser/services/navigation_service.py` ; `document-parser/domain/navigation.py`.
- **Constat** : inchangé sur le fond (renommages seulement).
- **Règle violée** : 2.4.2 — conforme ; dégradation.

### [MIN] Un value object est muté après construction (inchangé)

- **Localisation** : `document-parser/domain/source_map.py:97`, `:202-203`.
- **Constat** : `hop.cited.append(...)` toujours présent.
- **Règle violée** : 2.2.2 — conforme ; dégradation.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse (inchangé)

- **Localisation** : `document-parser/persistence/analysis_repo.py:12-31` ; `document-parser/domain/ports.py:310-322`.
- **Constat** : inchangé ; le nouveau `find_by_document` renvoie des `AnalysisJob` complètes.
- **Règle violée** : 2.5.1 — conforme ; dégradation.
- **Remédiation** : un VO `AnalysisSummary` côté domaine.

### [MIN] Contrats inter-couches en tuples (réduit : la déduction par message a disparu, un tuple de plus)

- **Localisation** : `document-parser/services/source_service.py:94-95`, `:172`, `:192`, `:271` ; **nouveau** `document-parser/services/document_service.py:144-146` (`find_with_store_links -> tuple[Document, list[DocumentStoreLinkView]] | None`).
- **Constat** : `api/analyses.py` ne déduit plus le 404 du préfixe du message : l'import lève une erreur typée (`services/analysis_service.py:175`, `:185`), traduite par `api/errors.py` (`api/analyses.py:84-85`). En revanche `25f5d8b` ajoute un contrat en tuple pour le document et ses liens, à côté d'un read model (`DocumentStoreLinkView`) qui aurait pu le porter.
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** : un read model `DocumentWithStoreLinks(document, links)` ; des VO pour les lectures et citations de `source_service`.

### [INFO] `PreviewImageKey` : clé de cache technique dans `domain/ports.py` (inchangé)

- **Localisation** : `document-parser/domain/ports.py:157` ; construction `document-parser/services/preview_service.py:62-63`.
- **Constat** : inchangé. Le service fait toujours lui-même le `stat()` du fichier pour bâtir la clé.

### [INFO] Les erreurs de service portent un statut HTTP (élargi)

- **Localisation** : `document-parser/services/errors.py:11-19` ; nouvelles classes `document-parser/services/preview_service.py:20`, `:29`, `:35`, `document-parser/services/analysis_service.py:62`, `:68`.
- **Constat** : la remédiation a rangé aperçu et import dans `ServiceError`, ce qui unifie la traduction, mais étend la politique « le service choisit le code HTTP » à cinq classes de plus. Les erreurs de l'éditeur, elles, restent sans HTTP. Deux politiques coexistent toujours.

### [INFO] `hash_result` vit dans le module de l'éditeur, la règle de fraîcheur dans le service

- **Localisation** : `document-parser/domain/analysis_editing.py:129-135` ; importé par `document-parser/services/chunk_service.py:23` ; règle `document-parser/services/analysis_edit_service.py:370-382`.
- **Constat** : résidu du [MIN] résolu. Une seule définition du hash, c'est l'essentiel. Mais le contexte chunks importe le module d'édition pour un concept qui appartient à `DocumentChunkSource`, et « des chunks sont à jour si leur source a le même hash » reste écrit dans le service.
- **Remédiation** : `DocumentChunkSource.for_result(...)` et `DocumentChunkSource.matches(analysis_id, document_json)`.

### [INFO] Ports du domaine satisfaits par un service, ou opaques

- **Localisation** : `document-parser/domain/ports.py:148-153` (`DocumentFileLocator`, implémenté par `DocumentService`, `document-parser/services/document_service.py:170`, renvoie un `Path`) ; `document-parser/domain/ports.py:495-509` (`GraphDriverPool.get -> Any`).
- **Constat** : `DocumentFileLocator` est un contrat entre deux services d'application plus qu'un port vers l'extérieur, et expose un chemin de fichier. `GraphDriverPool` rend le pilote opaque, choix documenté. Rien de faux ; à surveiller si d'autres ports « service vers service » apparaissent dans `domain/ports.py`.

### [INFO] Renommages verbe-d'abord : langage préservé, deux traces

- **Localisation** : `0c97a1a`, `4bd6e0c` ; `document-parser/services/analysis_edit_service.py:177`, `:187` ; `docs/design/204-auto-stale-chunk-hash.md:71`, `docs/design/363-mcp-chunkless-rag-simplification.md:231`.
- **Constat** : vérifié sur toutes les signatures modifiées de `domain/` (environ 50) et du front : le nom métier est conservé à chaque fois (section, élément, span, préambule, chunkset, glyphes, outline, heading). Aucun concept n'a perdu son nom au profit d'un verbe générique, et aucun ancien nom de fonction ne subsiste dans le code. Deux traces mineures : dans `save`, la même valeur s'appelle `projection_hash` puis est rangée dans `result_hash` ; les documents de conception historiques citent encore `chunkset_hash()` et `containing_chain` (le champ `ChunkPush.chunkset_hash`, lui, reste cohérent avec `hash_chunkset`).

### [INFO] Immutabilité superficielle des VO de l'éditeur (inchangé)

- **Localisation** : `document-parser/domain/analysis_editing.py:29-33`, `:101`.

### [INFO] `models.py` multi-contextes (inchangé)

- **Localisation** : `document-parser/domain/models.py:77-87`.

### [INFO] `GraphPayload` toujours mutable (inchangé)

- **Localisation** : `document-parser/domain/value_objects.py:270-271`.

### [INFO] L'import d'une analyse Docling n'existe pas dans le modèle (inchangé)

- **Localisation** : `document-parser/services/analysis_service.py:187-189`.

### [INFO] La garde d'architecture n'interdit toujours pas Docling au domaine (inchangé)

- **Localisation** : `document-parser/tests/test_architecture.py:183`.

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP (inchangé)

- **Localisation** : `document-parser/mcp_adapter/wire.py:27`, `:223`.

---

## Points positifs

- Une seule définition du hash de résultat (`domain/analysis_editing.py:129`), utilisée par l'éditeur et le chunking : le risque de `chunks_stale` faux par divergence de calcul a disparu.
- Chunks et export dépendent d'un port typé (`ActiveAnalysisResultReader`) et non plus d'un paramètre sans type ; plus aucun dépôt `Sqlite*` dans les signatures de service.
- `pypdfium2`/`pdf2image` sortis des services derrière `PdfInspector` ; `store_backend_resolver` typé sur les ports (la dette listée dans `test_architecture.py` a disparu).
- Toutes les erreurs de service, aperçu, export et import compris, sont traduites en un seul point ; plus de 404 déduit d'un préfixe de message.
- L'API de l'historique d'édition ne résout plus elle-même l'état des commandes : `list_history_entries` le fait dans le service (`services/analysis_edit_service.py:114-120`).
- Les renommages massifs n'ont pas abîmé le langage du domaine.

---

## Delta vs re-audit a6fb539

**Score** : 83 → **83** (±0). Items conformes : 13/17 → 13/17. Écarts : 0 CRIT / 2 MAJ / 12 MIN / 9 INFO → **0 CRIT / 2 MAJ / 12 MIN / 11 INFO**. Aucun item ne bascule. Attendu : la remédiation ne visait ni 2.3.1 ni 2.4.3, et les items de poids 1 non conformes (2.2.4, 2.3.3) n'ont pas été traités.

| Écart du re-audit | Statut sur a12b744 | Preuve |
|-------------------|--------------------|--------|
| [MAJ] 2.3.1 Trois définitions de l'analyse courante | **Inchangé** | `parse_loader.py:89`, `reasoning_service.py:97`, `export_service.py:122-123`, `document/store.ts:152`, `:180` |
| [MAJ] 2.4.3 État document-level sans racine | **Inchangé** | `analysis_repo.py:175-192`, `version_service.py:179-200`, `chunk_service.py:388-416` |
| [MIN] 2.2.4 `EditStream` anémique, chaîne de hachage en double | **Inchangé** (les deux copies portent maintenant le même nom) | `analysis_edit_service.py:399`, `analysis_edit_repo.py:211` |
| [MIN] 2.3.3 Statuts en chaînes nues | **Inchangé** | `source_map.py:44-46`, `analysis_edit_service.py:329` |
| [MIN] Hash du résultat calculé dans deux services | **Résolu** | `domain/analysis_editing.py:129` ; `chunk_service.py:415`, `analysis_edit_service.py:382` ; résidu en [INFO] |
| [MIN] Invariants hors domaine (2.4.2) | **Inchangé** | renommages seulement |
| [MIN] `EditorSnapshot` à identité forgée (2.2.1) | **Inchangé, ancré** : déplacé dans le domaine et publié par un port | `domain/analysis_editing.py:121`, `domain/ports.py:360` |
| [MIN] Frontières non typées (2.1.3/2.1.4) | **Réduit** : backend typé ; front inchangé | `chunk_service.py:149`, `export_service.py:43` ; `document/api.ts:26` |
| [MIN] « Document introuvable » ×5, aperçu hors `ServiceError` | **Réduit et aggravé** : aperçu dans `ServiceError` ; sixième classe ajoutée | `preview_service.py:17`, `analysis_service.py:59` |
| [MIN] Schéma Docling dans le domaine | **Inchangé** | — |
| [MIN] Règles de citation dans les services | **Inchangé** | — |
| [MIN] `SourceHop` muté | **Inchangé** | `source_map.py:202-203` |
| [MIN] `AnalysisJob` partiellement hydratée | **Inchangé** | `analysis_repo.py:12-31` |
| [MIN] Contrats en tuples / par message | **Réduit** : déduction par message supprimée ; un tuple ajouté | `api/analyses.py:84-85` ; `document_service.py:144-146` |
| [INFO] `PreviewImageKey` | Inchangé | |
| [INFO] Statut HTTP dans les erreurs de service | Élargi (5 classes de plus) | |
| [INFO] Types infra sous `TYPE_CHECKING` dans `store_backend_resolver` | **Résolu** | `store_backend_resolver.py:39-45` |
| [INFO] ×6 autres (VO éditeur, `models.py`, `GraphPayload`, import Docling, garde d'architecture, enum MCP) | Inchangés | |

**Nouveaux écarts** :
- [MIN] « Historique » nomme trois concepts ; alias `deleteHistoryEntry = deleteAnalysis` (`frontend/src/features/history/api.ts:2-5`, `domain/analysis_editing.py:48`) ;
- [INFO] `hash_result` dans le module de l'éditeur, règle de fraîcheur dans le service ;
- [INFO] ports « service vers service » ou opaques (`DocumentFileLocator`, `GraphDriverPool`) ;
- [INFO] renommages : langage préservé, deux traces (`projection_hash`/`result_hash`, docs de conception).

**Régressions introduites par la remédiation** (aucune ne fait basculer un item) :
1. `ImportDocumentNotFoundError` (`services/analysis_service.py:59`, `437058d`) : sixième classe pour « document introuvable ».
2. Alias `fetchHistory`/`deleteHistoryEntry` sur les fonctions de l'analyse (`frontend/src/features/history/api.ts:2-5`, `450dad6`) et `EditHistoryEntry` dans le domaine (`437058d`) : « historique » devient triple.
3. `EditorSnapshot` (avec son `AnalysisJob` forgée) déplacé dans le domaine et rendu par un port (`25f5d8b`/`437058d`) : le défaut 2.2.1 devient un contrat.
4. `_command_hash` → `_hash_command` (`0c97a1a`) : les deux copies de la chaîne de hachage portent le même nom avec des signatures différentes.
5. `find_with_store_links` renvoie un tuple (`services/document_service.py:146`, `25f5d8b`).

Points non vérifiés : les chemins d'erreur de `restore` (atomicité, PLAUSIBLE) ; le comportement réel de MCP/Ask après une édition (déduit du code, pas observé).

---

## Verdict partiel : GO

Score 83 ≥ 80 et 0 CRIT. Les deux MAJ (2.3.1, 2.4.3) restent sous le seuil bloquant (> 3) et n'ont pas bougé. La remédiation a résolu deux écarts (hash unique, types infra dans le résolveur) et en a réduit trois, mais en a introduit cinq petits, tous [MIN]/[INFO]. Le score ne bouge pas, ce qui est cohérent avec son périmètre. Priorité 0.8.0 inchangée : la sélection active comme seule définition de l'analyse courante, MCP et Ask compris.

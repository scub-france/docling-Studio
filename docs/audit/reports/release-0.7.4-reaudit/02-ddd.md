# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` `f7fc791`, avec #401 et #402, + 13 commits locaux #391-#400 + merge)

Référence : fiche `docs/audit/audits/02-ddd.md`, baseline `docs/audit/reports/release-0.7.4/02-ddd.md` (2026-11-13 @ `eade7fa` : 75/100, 1 CRIT / 2 MAJ / 10 MIN / 6 INFO, NO-GO).
Méthode : analyse statique de l'arbre de travail (lecture, `grep`, `git diff eade7fa a6fb539`). Ni application, ni tests, ni build lancés par cet audit. Résultats déjà obtenus par ailleurs sur `a6fb539` : ruff propre, pytest 1501 passés / 15 ignorés, vitest 586 passés, `vue-tsc` et `vite build` OK.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 17 |
| Score | 83 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 2 |
| Écarts MINOR | 12 |
| Écarts INFO | 9 |

Score = (30 / 36) × 100 = 83,3 → **83**. Items non conformes : 2.3.1 (poids 2), 2.4.3 (2), 2.2.4 (1), 2.3.3 (1).

Comme dans les audits précédents, certains [MIN] et [INFO] sont des dégradations relevées sur des items restés conformes. Seuls 2.2.4 et 2.3.3 sont des items de poids 1 non conformes.

### Métriques de périmètre (`eade7fa` → `a6fb539`)

| Mesure | 13/11 | 18/11 |
|--------|-------|-------|
| Modules `document-parser/domain/*.py` | 27 | 27 |
| Dataclasses `frozen=True` dans `domain/` | 62 | 62 |
| Dataclasses mutables (`@dataclass` nu) dans `domain/` | 7 | 7 |
| `Protocol` dans `domain/ports.py` | 24 | 26 (+`PreviewImageCache`, +`AnalysisDocumentEngine`) |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 (désormais interdit pour `services/`, `tests/test_architecture.py:198-199`) |
| `domain/models.py` | 314 l. | 314 l. |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 147 | 147 |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Contextes inchangés. Le contexte édition d'analyse gagne un port moteur (`domain/ports.py:305`) et un adaptateur dédié (`infra/docling_analysis_engine.py:14`). L'aperçu PDF est isolé dans son propre service (`services/preview_service.py:22`). |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `models.py` stable (314 l.). Aucun nouveau modèle transverse. |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Le moteur Docling a maintenant un contrat typé (`AnalysisDocumentEngine`). Reste : `active_result_service=None` non typé dans `ChunkService`/`ExportService`, et contrats en tuples ([MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI (MIN) | Pas d'import profond inter-features. Nouveau read model `AnalysisSummary` (`shared/types.ts:85`). Reste : la feature `document` rappelle l'endpoint de l'éditeur ([MIN]). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI (MIN) | Entités inchangées. `EditorSnapshot` fabrique toujours un `AnalysisJob` à identité forgée, désormais unique par analyse de base ([MIN]). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | Aucune nouvelle dataclass mutable. `SourceHop` toujours muté ([MIN] reconduit), payloads `dict` ([INFO]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | Aucun `save`/`update` sur un VO ; les écritures passent par les dépôts. |
| 2.2.4 | Entités porteuses de comportement | 1 | **NON** | `EditStream` reste un sac de quatre champs ; séquence et chaîne de hachage vivent dans le service et le dépôt. Voir [MIN]. |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Trois définitions de « l'analyse courante » toujours en place ; homonymie « version » non traitée. Voir [MAJ] n°1. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `grep -E "class \w*(Manager\|Handler\|Processor\|Helper\|Util)\b"` sur `domain services infra api` : 0. Nouveaux noms métier : `AnalysisDocumentEngine`, `PreviewImageCache`, `AnalysisEditNotFoundError`. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Statuts et genres du contexte navigation en chaînes nues (fichiers inchangés). Voir [MIN]. |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | Racines inchangées. L'absence de racine pour l'état « analyse active / source des chunks » est jugée en 2.4.3. |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Aucun état invalide persisté (rejeu avant écriture, triggers SQL, `complete_and_select` refuse une analyse non terminée). Mais ces invariants restent hors du domaine ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | **NON** | Amélioré (sélection atomique à la complétion), mais l'état document-level est toujours écrit par trois chemins sans racine, dont `restore` en écritures séparées. Voir [MAJ] n°2. |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Dépôts renvoient des types du domaine. `AnalysisJob` partiellement hydratée reconduite ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | Commandes HTTP traduites en `EditCommand` ; erreurs du domaine traduites en HTTP dans l'API seule (`api/errors.py:17-31`). |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | **CRIT du 13/11 résolu** : le service ne voit plus que `str`, `EditCommand` et `ProjectedAnalysis` (`services/analysis_edit_service.py:62`, `:331-336`) ; `MutationResult`/`DoclingDocument` restent dans `infra/docling_analysis_engine.py:36-47`. Restent le schéma Docling lu dans le domaine ([MIN]) et des types infra sous `TYPE_CHECKING` dans `store_backend_resolver` ([INFO]). |

---

## Écarts constatés

### [MAJ] Langage ubiquitaire : « l'analyse courante » a toujours trois définitions, et l'homonymie « version » reste ouverte

- **Localisation** :
  - **sélection active** (définition voulue) : `document-parser/domain/models.py:77-80` (`DocumentAnalysisSelection`), `document-parser/services/analysis_edit_service.py:105-111` (`load_active_result`), `:283-286` ;
  - **dernière terminée** : `document-parser/services/parse_loader.py:89` (MCP, `latest_parsed_ids`), `document-parser/services/export_service.py:121-123` (deux méthodes de port différentes selon le format : `find_latest_completed` pour MD, `find_latest_completed_by_document` pour JSON), `document-parser/services/chunk_service.py:375-377`, `:708` ; ports `document-parser/domain/ports.py:259`, `:261` ;
  - **première version de l'historique** : `frontend/src/features/document/store.ts:159-162`, `:187-191` (`versions[0].analysisId`) ;
  - homonymie « version » (reconduit, fichiers inchangés) : `document-parser/domain/anchors.py:7-11` vs `document-parser/domain/models.py:294` (`DocumentVersion`) ; `document-parser/services/parse_loader.py:70-73` (`version_id` = id d'analyse) ;
  - vocabulaire de l'éditeur : `document-parser/domain/analysis_editing.py:20` (`setCommandActive`) vs `document-parser/services/analysis_edit_service.py:228` (`"reapply"`/`"revert"`) vs `frontend/src/shared/i18n.ts:524-525` (« Annuler » / « Réappliquer ») ; le même libellé « Annuler » désigne aussi l'annulation locale non sauvegardée (`frontend/src/shared/i18n.ts:552`) ; résultat projeté nommé `projection` (`analysis_edit_service.py:45`), `result` (`frontend/src/features/analysis-editor/types.ts:52`, `:60`) et `working` (`analysis_edit_service.py:354`).
- **Constat** : aucune des remédiations du 13/11 n'a été faite sur ce point. Les commits #391-#402 n'ont pas touché `parse_loader.py`, ni `document/store.ts`. `ExportService` a été réécrit (#396/#397) mais conserve ses deux replis « latest » distincts. Conséquence inchangée : après une correction sauvegardée, Studio affiche, chunke et exporte le texte édité de l'analyse sélectionnée, tandis que le serveur MCP sert la dernière analyse terminée, texte d'origine, avec des `ref` qui ont pu changer après un déplacement. Côté UI, « Annuler » couvre deux opérations différentes (revert d'une édition sauvegardée, qui ajoute une commande au flux, et undo local). `job` hors `AnalysisJob` : 147 occurrences, stable.
- **Règle violée** : 2.3.1 — vocabulaire métier cohérent entre domain, services, API et frontend (poids 2).
- **Remédiation** :
  1. Faire de la sélection active la seule définition : `ParseLoader` résout `version_id=None` par `AnalysisSelectionRepository` et lit le résultat édité ; supprimer les replis « latest » d'`ExportService`/`ChunkService` ; fusionner `find_latest_completed` et `find_latest_completed_by_document`.
  2. Le frontend lit la sélection renvoyée par le backend au lieu de `versions[0]`.
  3. Un terme pour la bascule (p. ex. « désactiver / réactiver une édition ») dans le domaine, l'API et l'UI ; réserver « Annuler » à l'undo local.
  4. Glossaire dans la doc : analysis = parse ≠ DocumentVersion ; selection = analyse active ; edited result = projection des commandes actives.

  Effort M.

### [MAJ] L'état « analyse active + source des chunks » du document est toujours modifié sans racine

- **Localisation** :
  - `document-parser/persistence/analysis_repo.py:175-192` (`complete_and_select` : le dépôt de `AnalysisJob` écrit `document_analysis_state`), appelé par `document-parser/services/analysis_service.py:508` ;
  - `document-parser/services/version_service.py:179-203` (`restore` : `soft_delete_for_document`, `insert_many`, `select`/`clear_selection`, `set_chunk_source`/`clear_chunk_source`, quatre appels de dépôt) ;
  - `document-parser/services/chunk_service.py:388-418` (`rechunk_document` : suppression, insertion, puis `set_chunk_source`) ;
  - `document-parser/domain/ports.py:154-167` : deux ports pour la même ligne, implémentés par une seule classe (`document-parser/persistence/document_analysis_repo.py:9`).
- **Constat** : progrès réel. Le drapeau `update_status(job, select_analysis=True)` a disparu au profit d'une méthode nommée, atomique, qui refuse une analyse non terminée (`analysis_repo.py:181-182`). Mais le fond n'a pas changé :
  - il n'existe toujours ni entité `DocumentAnalysisState`, ni transition portée par `Document` ;
  - le dépôt d'un agrégat (`AnalysisJob`) écrit toujours l'état d'un autre (le document) ;
  - `restore` enchaîne toujours des écritures séparées. Un échec entre le remplacement des chunks (`version_service.py:179-187`) et la sélection (`:191-203`) laisse des chunks restaurés avec une sélection et une source de chunks antérieures, donc un `chunks_stale` faux (PLAUSIBLE, chemin d'erreur non vérifié ici).
- **Règle violée** : 2.4.3 — les modifications d'un agrégat passent par sa racine (poids 2).
- **Remédiation** : celle du 13/11. Modéliser `DocumentAnalysisState(document_id, active_analysis_id, chunks_source)` avec `select`, `clear`, `chunks_generated` ; un port unique `DocumentAnalysisStateRepository.save(state)` ; `restore` et `rechunk` en une unité de travail. Effort M.

### [MIN] `EditStream` reste anémique ; la chaîne de hachage est toujours écrite deux fois (item non conforme)

- **Localisation** : `document-parser/domain/analysis_editing.py:43-48` ; règles hors entité : `document-parser/services/analysis_edit_service.py:162-163` (base immuable), `:166-170` et `document-parser/persistence/analysis_edit_repo.py:154-158` (séquence attendue), `document-parser/services/analysis_edit_service.py:387-405` et `document-parser/persistence/analysis_edit_repo.py:164-170`, `:211-215` (chaîne de hachage).
- **Constat** : inchangé depuis le 13/11. `_command_hash` (service) et `_hash_command` (dépôt) produisent le même format sans source commune. Une divergence invaliderait silencieusement le cache (`analysis_edit_service.py:94`), qui serait alors rejoué à chaque chargement.
- **Règle violée** : 2.2.4 — entités porteuses de comportement (poids 1).
- **Remédiation** : `EditStream.append(...)`, `EditStream.accepts_base(hash)` et une fonction `command_hash` unique dans `domain/analysis_editing.py`. Effort S.

### [MIN] Statuts et genres du contexte navigation en chaînes nues (reconduit, item non conforme)

- **Localisation** : `document-parser/domain/source_map.py:44-48` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/domain/navigation.py:188`, `:247` ; `document-parser/domain/outline_builder.py:198` (fichiers non modifiés) ; nouveau code : `operation: str` (`document-parser/services/analysis_edit_service.py:327`), `EditorElement.type: str` (`document-parser/domain/analysis_editing.py:62`).
- **Constat** : inchangé.
- **Règle violée** : 2.3.3 — statuts métier explicites (poids 1).
- **Remédiation** : `SourceStatus`, `OutlineNodeKind`, `OutlineMode` ; `Literal["preview", "save", "replay", "load"]` pour l'opération.

### [MIN] Le hash du résultat qui date les chunks est calculé dans deux services

- **Localisation** : `document-parser/services/chunk_service.py:415` (`hashlib.sha256(job.document_json.encode("utf-8"))`) ; `document-parser/services/analysis_edit_service.py:380`, `:383-384` (`_hash_text`).
- **Constat** : `DocumentChunkSource.result_hash` est écrit par `ChunkService` et comparé par `AnalysisEditService` pour décider `chunks_stale`. Les deux contextes recalculent chacun le hash, de leur côté. La règle « des chunks sont à jour si leur source a le même hash de résultat » est un invariant métier, mais il n'est défini nulle part comme tel. Changer l'un des deux calculs rendrait tous les chunks « obsolètes » (ou jamais), sans erreur.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : `DocumentChunkSource.for_result(document_id, analysis_id, document_json)` et `DocumentChunkSource.matches(analysis_id, document_json)` dans le domaine, utilisés par les deux services.

### [MIN] Invariants d'édition et de sélection hors du domaine (reconduit, partiellement amélioré)

- **Localisation** :
  - règles d'édition en infra : `document-parser/infra/docling_editor.py:129`, `:177`, `:180`, `:221`, `:275`, `:278` ; politique d'éditabilité : `document-parser/infra/docling_projector.py:132-143` ;
  - « analyse active terminée et appartenant au document », écrit quatre fois : `document-parser/persistence/database.py:96-114` (triggers), `document-parser/persistence/analysis_repo.py:181-182`, `document-parser/services/version_service.py:166-174`, `document-parser/services/analysis_edit_service.py:278-294` ;
  - règle de fusion recopiée côté front : `frontend/src/features/analysis-editor/commands.ts:83-90` vs `document-parser/infra/docling_editor.py:218-221`.
- **Constat** : la divergence de la règle de fusion est corrigée (#395 : le front exige désormais un même type, comme le backend). La règle reste néanmoins dupliquée : le front n'utilise pas `supportedOperations` que le backend publie (`docling_projector.py:227`). `EditCommand.payload` reste un `dict` libre et `DocumentAnalysisSelection` se construit avec n'importe quel id. Aucun état invalide n'est persisté : item maintenu conforme, comme le 13/11.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : fabriques validantes dans `domain/analysis_editing.py`, `DocumentAnalysisSelection.of(document_id, analysis)` qui refuse une analyse étrangère ou non terminée ; constantes de fusion dans le domaine.

### [MIN] `EditorSnapshot` fabrique toujours un `AnalysisJob` à identité forgée (partiellement amélioré)

- **Localisation** : `document-parser/services/analysis_edit_service.py:350-366` ; exposé par `document-parser/api/analysis_edits.py:28-31`, `:64` ; consommé par `document-parser/services/chunk_service.py:375`, `:704`, `document-parser/services/export_service.py:138`, `:147`.
- **Constat** : l'id devient `working:{document_id}:{base_id}` : la collision entre deux analyses d'un même document est corrigée (#395). Mais l'objet reste une entité `AnalysisJob` jamais persistée, née `COMPLETED` sans cycle de vie, publiée telle quelle comme `AnalysisResponse.id`.
- **Règle violée** : 2.2.1 — conforme ; dégradation.
- **Remédiation** : VO `EditedAnalysisResult(base_analysis_id, ...)` dans le domaine, et un DTO HTTP dédié.

### [MIN] Frontières inter-contextes non typées : `active_result_service` et la feature `document` (reconduit)

- **Localisation** : `document-parser/services/chunk_service.py:149`, `:369-377`, `:702-708` ; `document-parser/services/export_service.py:43`, `:119-148` ; `frontend/src/features/document/api.ts:20-29` ; `frontend/src/features/document/store.ts:25-35`.
- **Constat** : inchangé. Chunks et export dépendent du contexte édition par un paramètre sans type, et lisent `.job` / `.base_analysis_id` d'un `EditorSnapshot` défini dans un module de service. La feature `document` réappelle `GET /analysis-editor` au lieu de passer par `frontend/src/features/analysis-editor/api.ts:10`.
- **Règle violée** : 2.1.3 / 2.1.4 — conformes ; dégradation.
- **Remédiation** : port de lecture `ActiveAnalysisResult` dans `domain/ports.py` renvoyant `EditedAnalysisResult` ; côté front, exposer la lecture du résultat édité depuis le barrel de l'éditeur.

### [MIN] « Document introuvable » défini cinq fois ; les erreurs d'aperçu restent hors de `ServiceError` (nouveau)

- **Localisation** : `document-parser/services/chunk_service.py:74` (`DocumentNotFoundError`), `document-parser/services/navigation_errors.py:21` (`DocumentNotFoundError`, homonyme), `document-parser/services/preview_service.py:14` (`PreviewDocumentNotFoundError(Exception)`), `document-parser/services/export_service.py:152` (`ExportNotFoundError`), `document-parser/domain/analysis_editing.py:119` (`AnalysisEditNotFoundError`) ; base commune `document-parser/services/errors.py:11` ; `document-parser/services/preview_service.py:18` (`PreviewPageOutOfRangeError(ValueError)`).
- **Constat** : #396 a posé une base unique `ServiceError`, traduite en un seul point (`api/errors.py:25-31`). Le service d'aperçu, ajouté par #401 en parallèle, ne l'utilise pas : ses deux erreurs dérivent de `Exception`/`ValueError` et sont traduites à la main (`document-parser/api/documents.py:189-192`). Plus largement, le concept métier « ce document n'existe pas » porte cinq classes différentes, dont deux homonymes dans deux modules.
- **Règle violée** : 2.3.1 (déjà non conforme) / 2.1.3 — dégradation.
- **Remédiation** : une `DocumentNotFoundError` unique (domaine ou `services/errors.py`) ; faire dériver les erreurs d'aperçu de `ServiceError`.

### [MIN] Le schéma JSON Docling est lu dans le domaine (reconduit)

- **Localisation** : `document-parser/domain/ports.py:470` (`DocumentTreeReader`) ; `document-parser/domain/element_reader.py:85-86`, `:172-214` ; `document-parser/domain/parse_index.py:54` ; `EditorElement.self_ref` (`document-parser/domain/analysis_editing.py:60`) et ids logiques `{base_id}:{self_ref}` (`document-parser/infra/docling_editor.py:84`).
- **Constat** : inchangé. C'est désormais la seule réserve sur 2.5.3, qui redevient conforme.
- **Règle violée** : 2.5.3 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] Règles cœur du contexte citation dans les services (reconduit)

- **Localisation** : `document-parser/services/citation_service.py:39`, `:201-277` ; `document-parser/services/navigation_service.py:231-276` ; `document-parser/domain/navigation.py:154-178` (fichiers non modifiés).
- **Constat** : inchangé.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] Un value object est muté après construction (reconduit)

- **Localisation** : `document-parser/domain/source_map.py:202-203`, `:285`.
- **Constat** : inchangé (`hop.cited.append(...)`).
- **Règle violée** : 2.2.2 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse (reconduit)

- **Localisation** : `document-parser/persistence/analysis_repo.py:12-31` ; `document-parser/domain/ports.py:252-254`, `:263-265`.
- **Constat** : inchangé. Côté frontend, en revanche, #401 introduit un vrai read model `AnalysisSummary` (`frontend/src/shared/types.ts:85-97`) : le backend pourrait suivre.
- **Règle violée** : 2.5.1 — conforme ; dégradation.
- **Remédiation** : un VO `AnalysisSummary` côté domaine pour `find_all_summaries`.

### [MIN] Contrats inter-couches en tuples et par texte de message (reconduit)

- **Localisation** : `document-parser/services/source_service.py:91-96` ; `document-parser/api/analyses.py:84`.
- **Constat** : inchangé. `api/analyses.py:84` déduit encore le 404 du préfixe du message, alors qu'`api/errors.py` existe maintenant.
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** : erreurs typées, traduites par `api/errors.py`.

### [INFO] `PreviewImageKey` : une clé de cache technique dans `domain/ports.py`

- **Localisation** : `document-parser/domain/ports.py:142-151` ; construction `document-parser/services/preview_service.py:36-38`.
- **Constat** : le port `PreviewImageCache` a sa place dans `domain/ports.py` (convention vérifiée par `tests/test_architecture.py:247`). Sa clé, en revanche, n'est pas un concept métier : un tuple positionnel de six primitives dont le chemin absolu du fichier et `st_mtime_ns`. Le service la construit lui-même après un `stat()` du fichier. Rien de faux aujourd'hui, mais le domaine publie un détail de stockage, et un ordre de champs erroné ne serait pas détecté par le typage (quatre `int` consécutifs).
- **Règle violée** : 2.3.2 / 2.2.2 — observation.
- **Remédiation** : VO gelé `PagePreviewKey(source_fingerprint, page, dpi, image_format)`, ou laisser l'adaptateur calculer l'empreinte du fichier (`get(document, page, dpi, format)`).

### [INFO] Les erreurs de service portent un statut HTTP

- **Localisation** : `document-parser/services/errors.py:11-19` ; p. ex. `document-parser/services/chunk_service.py:373`, `document-parser/services/version_service.py:172-174`.
- **Constat** : la couche application choisit 404/409. À l'inverse, les erreurs du domaine (éditeur) ignorent HTTP et sont mappées dans l'API (`api/errors.py:15-22`), ce qui est le bon modèle. Deux politiques coexistent.
- **Remédiation** : à terme, des erreurs typées par nature (not found, conflict, invalid) mappées dans `api/errors.py`.

### [INFO] Types infra sous `TYPE_CHECKING` dans un service (pré-existant)

- **Localisation** : `document-parser/services/store_backend_resolver.py:40-43`, `:61`, `:81-83` ; dette enregistrée dans `document-parser/tests/test_architecture.py:71-74`.
- **Constat** : `IngestionTargets.vector_store` est typé `OpenSearchStore`, et le résolveur prend des pools infra. Inchangé depuis 0.6.1, connu et listé comme dette. En lecture stricte de 2.5.3, c'est un type infra exposé à un service ; ce n'est pas retenu comme non-conformité (pas de type Docling, injection par le constructeur, pas d'import à l'exécution).
- **Remédiation** : typer sur `VectorStore` (`domain/ports.py`) et des fabriques de pools.

### [INFO] Immutabilité superficielle des VO de l'éditeur (reconduit)

- **Localisation** : `document-parser/domain/analysis_editing.py:29`, `:89`.
- **Constat** : inchangé.
- **Remédiation** : `MappingProxyType` ou payloads typés.

### [INFO] `models.py` multi-contextes (reconduit)

- **Localisation** : `document-parser/domain/models.py:77-87`.
- **Constat** : inchangé.
- **Remédiation** : déplacer avec la modélisation `DocumentAnalysisState`.

### [INFO] `GraphPayload` toujours mutable (reconduit)

- **Localisation** : `document-parser/domain/value_objects.py:270-271`.
- **Constat** : inchangé.

### [INFO] L'import d'une analyse Docling n'existe pas dans le modèle (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:182-186`.
- **Constat** : inchangé.

### [INFO] La garde d'architecture n'interdit toujours pas Docling au domaine (reconduit, réduit)

- **Localisation** : `document-parser/tests/test_architecture.py:193`.
- **Constat** : `docling`/`docling_core` sont désormais interdits aux services (`:198-199`), mais pas au domaine.
- **Remédiation** : ajouter `docling`, `docling_core` à `_DOMAIN_FORBIDDEN_EXTERNALS`.

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP (reconduit)

- **Localisation** : `document-parser/mcp_adapter/wire.py:27`, `:223`.
- **Constat** : inchangé.

---

## Points positifs

- Le CRIT du 13/11 est corrigé proprement : port `AnalysisDocumentEngine` dans le domaine (`domain/ports.py:305-332`), adaptateur composite en infra (`infra/docling_analysis_engine.py:14-60`), service typé sur le port, projection hors de la boucle d'événements (`analysis_edit_service.py:329-336`). La garde d'architecture interdit désormais `docling` aux services.
- Hiérarchie d'erreurs de l'éditeur dans le domaine, sans HTTP, avec `AnalysisEditNotFoundError` qui reste un `AnalysisEditUnavailableError` ; traduction HTTP en un seul point (`api/errors.py`).
- Sélection d'une analyse terminée rendue atomique et explicite (`complete_and_select`), au lieu d'un drapeau booléen.
- Identité du résultat de travail unique par analyse de base ; règle de fusion front/back réalignée.
- Cache corrompu traité comme projection reconstructible (`analysis_edit_service.py:297-320`) : le flux de commandes reste la seule source de vérité, conforme à la docstring du domaine.
- Read model `AnalysisSummary` côté frontend pour les listes ; aucune dépendance profonde entre features.

---

## Delta vs audit du 2026-11-13

**Score** : 75 → **83** (+8). Items conformes : 12/17 → 13/17. Écarts : 1 CRIT / 2 MAJ / 10 MIN / 6 INFO → **0 CRIT / 2 MAJ / 12 MIN / 9 INFO**.

| Écart du 13/11 | Statut au 18/11 |
|----------------|-----------------|
| [CRIT] 2.5.3 Type Docling / `MutationResult` à travers le service | **Résolu** (#394). Item 2.5.3 conforme (+3). |
| [MAJ] 2.3.1 Trois définitions de l'analyse courante, homonymie « version » | **Toujours présent**. Aucun fichier concerné modifié sur ce point ; s'y ajoute le double sens de « Annuler » dans l'UI. |
| [MAJ] 2.4.3 État document-level sans racine | **Toujours présent, atténué** : `select_analysis=True` remplacé par `complete_and_select` atomique ; `restore` et `rechunk` inchangés. |
| [MIN] 2.2.4 `EditStream` anémique, hash écrit deux fois | **Toujours présent**. |
| [MIN] 2.3.3 Statuts en chaînes nues | **Toujours présent**. |
| [MIN] Invariants hors domaine (2.4.2) | **Toujours présent, atténué** : divergence de la règle de fusion corrigée (#395), duplication maintenue. |
| [MIN] `EditorSnapshot` à identité forgée (2.2.1) | **Toujours présent, atténué** : id unique par analyse de base. |
| [MIN] Frontières non typées (2.1.3/2.1.4) | **Toujours présent**. |
| [MIN] Schéma Docling dans le domaine | **Toujours présent** (redevient la seule réserve sur 2.5.3). |
| [MIN] Règles de citation dans les services | **Toujours présent**. |
| [MIN] `SourceHop` muté | **Toujours présent**. |
| [MIN] `AnalysisJob` partiellement hydratée | **Toujours présent** ; le drapeau inter-agrégats du port a disparu. |
| [MIN] Contrats en tuples / par message | **Toujours présent**. |
| [INFO] ×6 | Tous présents ; garde d'architecture réduite (Docling interdit aux services). |

Nouveaux écarts (code ajouté depuis `eade7fa`) :
- [MIN] hash de la source des chunks calculé dans deux services (`chunk_service.py:415` / `analysis_edit_service.py:383-384`) ;
- [MIN] « document introuvable » en cinq classes, erreurs d'aperçu (#401) hors de `ServiceError` ;
- [INFO] `PreviewImageKey`, clé technique en tuple dans `domain/ports.py` (#401) ;
- [INFO] statut HTTP porté par les erreurs de service (#396) ;
- [INFO] types infra dans `store_backend_resolver` (pré-existant, relevé pour la première fois dans cet audit).

Origine des +8 points : 2.5.3 redevient conforme (+3 sur 36). Aucun item ne bascule dans l'autre sens.

---

## Verdict partiel : GO

Score 83 ≥ 80 et 0 CRIT. Les deux MAJ (2.3.1, 2.4.3) restent sous le seuil bloquant (> 3) mais sont ouverts depuis 0.7.3 pour le premier : à planifier en 0.8.0, en commençant par faire de la sélection active la seule définition de l'analyse courante (MCP compris), car c'est le seul écart avec un effet visible pour l'utilisateur (MCP cite le texte non édité).

# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code

Référence : fiche `docs/audit/audits/02-ddd.md`, baseline `docs/audit/reports/release-0.7.3/02-ddd.md` (92/100, 0 CRIT / 1 MAJ / 6 MIN / 5 INFO, GO). Pas de fichier 02 dans `release-0.7.3-reaudit/` : l'audit n'avait pas été ré-audité.
Méthode : analyse statique (lecture du code, `grep`, `git diff 1de1929..HEAD`). Je n'ai exécuté ni l'application, ni les tests, ni aucun build.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 17 |
| Score | 75 / 100 |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 2 |
| Écarts MINOR | 10 |
| Écarts INFO | 6 |

Score = (27 / 36) × 100 = 75,0 → **75**. Items non conformes : 2.5.3 (poids 3), 2.3.1 (2), 2.4.3 (2), 2.2.4 (1), 2.3.3 (1).

Comme en 0.7.3, les [MIN] comptent aussi des dégradations relevées sur des items restés conformes. Seuls 2.2.4 et 2.3.3 sont des items de poids 1 non conformes.

### Métriques de périmètre (0.7.3 `1de1929` → 0.7.4 `eade7fa`)

| Mesure | 0.7.3 | 0.7.4 |
|--------|-------|-------|
| Modules `document-parser/domain/*.py` | 26 | 27 (+`analysis_editing.py`) |
| Dataclasses `frozen=True` dans `domain/` | 53 | 62 (les 9 nouvelles sont gelées ; `ChunkEdit` supprimée) |
| Dataclasses mutables dans `domain/` | 7 | 7 (inchangé) |
| `Protocol` dans `domain/ports.py` | 21 | 24 |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| `domain/models.py` | 331 l. | 314 l. (−`ChunkEdit`, +`DocumentAnalysisSelection`, +`DocumentChunkSource`) |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 123 | 147 |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Nouveau contexte **édition d'analyse**, présent dans toutes les couches : domaine `domain/analysis_editing.py`, service `services/analysis_edit_service.py`, dépôt `persistence/analysis_edit_repo.py`, adaptateurs `infra/docling_editor.py`/`docling_projector.py`, routeur `api/analysis_edits.py`, feature `frontend/src/features/analysis-editor/`. Le journal d'audit des chunks (`ChunkEdit`) disparaît proprement. |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `models.py` passe de 331 à 314 l. Les concepts de l'éditeur ont leur module. Seuls deux petits VO document-level y sont ajoutés (`:77-88`, cf. [INFO]). |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Commandes HTTP en union discriminée Pydantic (`AnalysisEditCommandRequest`), mappées en `EditCommand` (`api/analysis_edits.py:86-107`). Erreurs typées (`domain/analysis_editing.py:107-116`). Dégradation : `ChunkService`/`ExportService` consomment l'éditeur par un paramètre non typé, en piochant `.job` dans son snapshot ([MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI (MIN) | `features/analysis-editor` est le miroir du contexte : `EditorElement`, `EditorTreeNode`, `AnalysisEditCommand`, `baseAnalysisId` (`types.ts`), store et API dédiés, barrel `index.ts`. Dégradation : la feature `document` rappelle elle-même l'endpoint de l'éditeur et choisit l'analyse active ([MIN]). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI (MIN) | Entités inchangées. `EditStream`/`StoredEditCommand` ont une identité (`analysis_id`, `id` + `sequence`). Dégradation : `EditorSnapshot` fabrique un `AnalysisJob` à identité forgée, sans cycle de vie ([MIN]). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | 9/9 nouvelles dataclasses du domaine gelées (`domain/analysis_editing.py:24-104`, `domain/models.py:77-88`). Immutabilité superficielle seulement : `payload: dict`, `reference_changes: dict` ([INFO]). `SourceHop` toujours muté ([MIN], reconduit). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | Aucun `save`/`update` sur les VO. Les écritures passent par `AnalysisEditRepository`, `AnalysisSelectionRepository` et `ChunkSourceRepository`. |
| 2.2.4 | Entités porteuses de comportement | 1 | **NON** | Le flux d'édition est une entité anémique : toutes ses règles (chaîne de hachage, séquence attendue, base immuable) vivent dans le service et le dépôt. Voir [MIN] « `EditStream` anémique ». |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Écart 0.7.3 toujours ouvert. S'y ajoutent trois définitions concurrentes de « l'analyse courante » d'un document. Voir [MAJ] n°1. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `grep "class \w*(Manager\|Handler\|Processor\|Helper\|Util)"` : 0. Noms métier : `EditStream`, `EditCommand`, `ProjectedAnalysis`, `DocumentAnalysisSelection`, `DocumentChunkSource`. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Statuts du trail et genres d'outline toujours en chaînes nues (fichiers non modifiés). Voir [MIN] reconduit. Le nouveau code utilise des `Literal` (`CommandType`, `domain/analysis_editing.py:13-21` ; `placement` dans `api/schemas.py`), ce qui est correct. |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | Racines inchangées. `EditStream` est la racine du flux (commandes et cache rattachés à `analysis_id`, écriture atomique `save_commands_and_cache`). La racine de l'état « analyse active / source des chunks » est, elle, ambiguë : jugé en 2.4.3. |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Aucun état invalide n'est persisté : toute commande est rejouée et validée avant l'écriture, et la sélection est gardée par des triggers SQL. Mais aucun de ces invariants n'est dans le domaine ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | **NON** | L'état document-level « analyse active + source des chunks » est écrit par trois services et deux dépôts, dont le dépôt d'un autre agrégat, sans racine et sans transaction commune. Voir [MAJ] n°2. |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Les nouveaux dépôts renvoient des types du domaine (`EditStream`, `StoredEditCommand`, `EditedAnalysisCache`, `DocumentAnalysisSelection`), jamais de `Row`. `AnalysisJob` partiellement hydratée : reconduit ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | Union discriminée validée par Pydantic, puis traduite en `EditCommand` du domaine (`api/analysis_edits.py:86-107`). Le domaine ne voit jamais un modèle Pydantic. |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | **NON** | `DoclingDocumentEditor.apply` renvoie au service un `MutationResult` défini en infra, qui porte un `DoclingDocument` ; le service le transmet au projecteur. Voir [CRIT]. |

---

## Écarts constatés

### [CRIT] Un type Docling et un type infra traversent `AnalysisEditService`

- **Localisation** :
  - `document-parser/infra/docling_editor.py:25-30` (`MutationResult`, `document: DoclingDocument`) et `:74` (`return MutationResult(document, current_refs, changes)`) ;
  - `document-parser/services/analysis_edit_service.py:298-311` : `mutation = self._editor.apply(...)`, puis `self._projector.project(mutation.document, logical_ids=mutation.logical_ids, reference_changes=mutation.reference_changes, warnings=mutation.warnings)` ;
  - `document-parser/infra/docling_projector.py:34-41` (`project(self, document: Any, ...)`) ;
  - `document-parser/services/analysis_edit_service.py:59-61` (`editor`, `projector` non typés).
- **Constat** : la commande de la fiche (`grep "from docling" services/`) ne remonte rien, et le service n'importe effectivement aucun type Docling. Mais l'item demande plus que l'absence d'import : « pas de types Docling exposés aux services ». Or, à l'exécution :
  - le service reçoit un objet `DoclingDocument` vivant, emballé dans un `MutationResult` déclaré dans `infra/` ;
  - il lit quatre attributs de cet objet infra ;
  - il fait lui-même la jonction entre la sortie Docling de l'éditeur et l'entrée Docling du projecteur.

  Le service est donc le point de passage d'un objet Docling entre deux adaptateurs. Ce n'est pas un VO du domaine : `ProjectedAnalysis` existe, mais il n'est produit qu'en bout de chaîne. Remplacer l'éditeur ou le projecteur par une implémentation non-Docling casserait le service. Aucun port ne décrit ce contrat (cf. audit 01, [CRIT] 1.4.1, même cause racine). L'objet est opaque pour le service, ce qui limite l'impact. Mais le contrat de l'item est enfreint à la lettre comme à l'esprit : l'anti-corruption Docling, que l'importeur (`DoclingDocumentImporter`) et le lecteur d'arbre (`DocumentTreeReader`) respectaient, s'arrête ici au milieu du service.
- **Règle violée** : 2.5.3 — « Les adaptateurs infra ne leakent pas leurs types internes vers les services (pas de types Docling exposés aux services) » (poids 3).
- **Remédiation** : un seul port dans `domain/ports.py` (`AnalysisDocumentEditor.apply_and_project(document_json, base_analysis_id, commands) -> ProjectedAnalysis`, et `project_serialized`), implémenté par un adaptateur qui compose éditeur et projecteur. `DoclingDocument` et `MutationResult` restent dans `infra/`, et le service ne manipule plus que `str`, `EditCommand` et `ProjectedAnalysis`. Ajouter `docling`/`docling_core` à `_SERVICES_FORBIDDEN_EXTERNALS` ne suffit pas à le garantir (pas d'import) : typer le constructeur sur le port. Effort M.

### [MAJ] Langage ubiquitaire : l'homonymie « version » reste ouverte, et « l'analyse courante » d'un document a désormais trois définitions

- **Localisation** :
  - Reconduit de 0.7.3 (fichiers non modifiés) : `document-parser/domain/anchors.py:7-11` vs `document-parser/domain/models.py:294`, `:309` ; `document-parser/services/parse_loader.py:70` vs `document-parser/services/version_service.py:164` ; `document-parser/domain/source_map.py:79-80`, `:154`, `:313` ; `document-parser/services/navigation_config.py:18-25`.
  - Nouveau en 0.7.4, trois définitions de « l'analyse courante » :
    - **sélection active** : `document-parser/domain/models.py:77-81` (`DocumentAnalysisSelection`), `document-parser/services/analysis_edit_service.py:105-111` (`active_result`), `document-parser/persistence/database.py:88-94` (`active_analysis_id`) ;
    - **dernière terminée** : `document-parser/services/parse_loader.py:89` (MCP), `document-parser/services/export_service.py:81`, `:99` et `document-parser/services/chunk_service.py:385` (repli quand l'éditeur n'est pas câblé) ;
    - **dernière version de l'historique** : `frontend/src/features/document/store.ts:159-162` (`versions[0].analysisId`).
  - Nouveau en 0.7.4, termes de l'éditeur : `document-parser/services/analysis_edit_service.py:228` (`"reapply" if active else "revert"`) vs `domain/analysis_editing.py:20` (`setCommandActive`) vs `frontend/src/shared/i18n.ts:523-527` (« Annuler » / « Réappliquer ») ; `document-parser/services/analysis_edit_service.py:327` (`id=f"working:{document.id}"`).
- **Constat** :
  1. **Reconduit.** Le `version_id` de l'ancre MCP désigne toujours un `AnalysisJob`, et `DocumentVersion` reste une autre entité. Les remédiations 1 et 2 de 0.7.3 (renommage `parse_id`, `SourceHop` → `SourceRound`) ne sont pas faites.
  2. **La remédiation 3 de 0.7.3 a été traitée à moitié, et l'écart s'est aggravé.** 0.7.3 demandait de « décider dans le domaine ce qu'est la parse courante ». 0.7.4 crée bien un concept explicite, la sélection active (`DocumentAnalysisSelection`), tenue par le backend (« the backend, rather than the frontend, owns which immutable analysis is active », `version_service.py:195-196`). Mais ce concept n'est pas adopté partout :
     - le contexte navigation/MCP résout toujours la « latest » (`parse_loader.py:89`) et lit la colonne `analysis_jobs.document_json` brute (`persistence/analysis_repo.py:170`), sans les éditions sauvegardées ;
     - `ExportService` et `ChunkService` gardent un repli « latest completed », par deux méthodes de port distinctes pour la même notion (`find_latest_completed` en `export_service.py:81`, `find_latest_completed_by_document` en `:99`) ;
     - le workspace frontend déduit l'analyse active de la première version de l'historique (`document/store.ts:159-162`), et non de la sélection backend.

     La conséquence PLAUSIBLE signalée en 0.7.3 devient concrète : une fois une correction sauvegardée dans l'éditeur, Studio affiche, chunke et exporte le texte corrigé, tandis qu'un agent MCP cite le texte d'origine de la même analyse, avec une ancre de `ref` qui a pu changer après un déplacement (`reference_changes`, `infra/docling_editor.py:69-73`).
  3. **Vocabulaire de l'éditeur.** Une même opération s'appelle `setCommandActive` dans le domaine et l'API, « revert/reapply » dans le service et « Annuler/Réappliquer » dans l'UI. Le résultat projeté s'appelle `projection` (service), `result` (API, `AnalysisEditSaveResponse.result`), `working` (id forgé) et `edited` (paramètre d'export). « Chunk source » (domaine) et « chunk provenance » (docstring `analysis_edit_service.py:344-346`) désignent le même concept. Ces écarts restent mineurs à côté du point 2.
  4. `job` hors `AnalysisJob` : 123 → 147 occurrences dans `api/` + `services/`.
- **Règle violée** : 2.3.1 — « Le vocabulaire métier est cohérent entre domain, services, API et frontend » (poids 2).
- **Remédiation** :
  1. Faire de la sélection active **la** définition de l'analyse courante :
     - `ParseLoader` résout `version_id=None` par `AnalysisSelectionRepository` et sert le résultat édité, par le même port de lecture que `ChunkService`/`ExportService` ;
     - supprimer les replis « latest » ;
     - fusionner `find_latest_completed`/`find_latest_completed_by_document` ;
     - le frontend lit la sélection renvoyée par le backend.
  2. Choisir un terme pour la bascule (`setCommandActive` ↔ revert/reapply) et l'utiliser partout.
  3. Reprendre les remédiations 1-2 de 0.7.3, et ajouter le glossaire attendu : analysis = parse ≠ DocumentVersion ; selection = analyse active ; edited result = projection des commandes actives.

  Effort M.

### [MAJ] L'état « analyse active + source des chunks » du document est modifié sans racine, par trois services et deux dépôts, en transactions séparées

- **Localisation** :
  - `document-parser/persistence/analysis_repo.py:175-209` : `update_status(job, select_analysis=True)` écrit `document_analysis_state` dans la transaction de l'analyse, appelé par `document-parser/services/analysis_service.py:508` ;
  - `document-parser/services/version_service.py:186-211` : `restore` enchaîne soft-delete des chunks, insertion, `select`/`clear_selection` puis `set_chunk_source`/`clear_chunk_source`, soit quatre dépôts et autant de commits ;
  - `document-parser/services/chunk_service.py:422-428` (`set_chunk_source` après rechunk) ;
  - `document-parser/domain/ports.py:141-154` : deux ports pour la même ligne, implémentés par une seule classe (`document-parser/persistence/document_analysis_repo.py:9`) ;
  - `document-parser/persistence/database.py:88-94`.
- **Constat** : la table `document_analysis_state` est une composante du document (clé `document_id`, `ON DELETE CASCADE`). Le code le reconnaît : « History restore is an aggregate operation » (`version_service.py:195`). Pourtant, aucune racine ne la porte :
  - `Document` l'ignore ;
  - il n'existe ni entité `DocumentAnalysisState`, ni méthode `Document.select_analysis(...)` ;
  - les deux VO `DocumentAnalysisSelection`/`DocumentChunkSource` sont écrits séparément.

  Trois chemins la modifient directement :
  1. **Le dépôt de l'agrégat `AnalysisJob`**, par un drapeau booléen, écrit l'état d'un autre agrégat.
  2. `VersionService.restore`, en quatre écritures non atomiques. Un échec entre le remplacement des chunks (`:186-194`) et la sélection (`:197-202`) laisse un document dont les chunks viennent de la version restaurée, mais dont l'analyse active et la source des chunks sont celles d'avant. L'indicateur `chunks_stale` (`analysis_edit_service.py:341-353`) mentira alors dans un sens ou dans l'autre (PLAUSIBLE, chemin d'erreur non testé ici).
  3. `ChunkService.rechunk_document`, après ses propres écritures de chunks.

  Ce n'est pas le contournement toléré en 0.7.0 (`update_progress`/`update_chunks`, à l'intérieur d'un même agrégat) : c'est une écriture inter-agrégats sans racine.
- **Règle violée** : 2.4.3 — « Les modifications d'un agrégat passent par sa racine, pas par manipulation directe de ses composants internes » (poids 2).
- **Remédiation** :
  1. Modéliser `DocumentAnalysisState(document_id, active_analysis_id, chunks_source)` dans le domaine, avec les transitions `select(analysis)`, `clear()` et `chunks_generated(from_analysis, result_hash)`.
  2. Un port unique `DocumentAnalysisStateRepository.save(state)`.
  3. Retirer `select_analysis` de `AnalysisRepository.update_status` : `AnalysisService` appelle la transition, puis le dépôt d'état.
  4. Faire de `restore` une opération transactionnelle, p.ex. `ChunkRepository.replace_all(document_id, chunks, state)` ou une unité de travail.

  Effort M.

### [MIN] `EditStream` est une entité anémique : ses invariants vivent dans le service et le dépôt (item non conforme)

- **Localisation** : `document-parser/domain/analysis_editing.py:43-48` (`EditStream`, quatre champs, aucune méthode) ; règles hors entité :
  - `document-parser/services/analysis_edit_service.py:162-163` (base immuable) ;
  - `:166-170` et `document-parser/persistence/analysis_edit_repo.py:158-163` (séquence attendue) ;
  - `:360-378` et `document-parser/persistence/analysis_edit_repo.py:164-170`, `:215-219` (chaîne de hachage, écrite deux fois).
- **Constat** : le flux d'édition append-only est l'objet central du contexte, celui qui fait de l'édition une donnée durable. Ses règles sont pertinentes et stables :
  - on n'ajoute qu'à la séquence attendue ;
  - chaque commande chaîne le hash de la précédente ;
  - la base ne change jamais.

  Aucune n'est portée par `EditStream`. La seule logique du domaine est la résolution des bascules (`active_edit_commands`), qui est une fonction libre, bien écrite. La chaîne de hachage est implémentée deux fois, dans `_command_hash` et dans `_hash_command`, avec le même format et la même sérialisation canonique. Une divergence invaliderait silencieusement tout le cache (`analysis_edit_service.py:92`).
- **Règle violée** : 2.2.4 — les entités portent du comportement métier quand c'est pertinent (poids 1).
- **Remédiation** : `EditStream.append(stored, pending, expected_sequence) -> list[PendingRecord]` (contrôle de séquence et chaîne de hachage), `EditStream.accepts_base(hash)`, et `stream_hash(...)` dans le domaine. Le dépôt persiste les enregistrements calculés au lieu de les recalculer. Effort S.

### [MIN] Statuts et genres du contexte navigation en chaînes nues (reconduit de 0.7.3, item non conforme)

- **Localisation** : `document-parser/domain/source_map.py:44-48`, `:67-75` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/domain/navigation.py:188`, `:247` ; `document-parser/domain/outline_builder.py:198` (fichiers non modifiés depuis 1de1929).
- **Constat** : inchangé. Le code neuf de 0.7.4 type ses énumérations (`CommandType`, `placement`), mais `operation: str` (`"preview"|"save"|"replay"`, `services/analysis_edit_service.py:298`) et `EditorElement.type: str` (labels Docling, `domain/analysis_editing.py:62`) restent des chaînes.
- **Règle violée** : 2.3.3 — statuts métier explicites (poids 1).
- **Remédiation** : celle de 0.7.3 (`SourceStatus`, `OutlineNodeKind`, `OutlineMode`).

### [MIN] Invariants d'édition et de sélection répartis entre infra, persistance et services ; aucun dans le domaine

- **Localisation** :
  - règles d'édition en infra : `document-parser/infra/docling_editor.py:129`, `:177`, `:180`, `:221`, `:275`, `:278` ; politique d'éditabilité en `document-parser/infra/docling_projector.py:139-150` ;
  - invariant « analyse active terminée et appartenant au document », écrit quatre fois : `document-parser/persistence/database.py:96-114` (triggers), `document-parser/persistence/analysis_repo.py:177-178`, `document-parser/services/version_service.py:171-178`, `document-parser/services/analysis_edit_service.py:280-287` ;
  - règle de fusion recopiée côté front, divergente : `frontend/src/features/analysis-editor/commands.ts:78` vs `document-parser/infra/docling_editor.py:219-221`.
- **Constat** : aucun état invalide n'est persisté aujourd'hui. `save` rejoue et valide toutes les commandes avant d'écrire, et un trigger SQL interdit une sélection étrangère. L'item est donc maintenu conforme, selon le même raisonnement qu'en 0.7.3. Mais aucun de ces invariants n'est dans le domaine :
  - `EditCommand.payload` est un `dict[str, Any]` libre ;
  - `DocumentAnalysisSelection` se construit avec n'importe quel id ;
  - le port `AnalysisSelectionRepository.select` accepte une analyse non terminée.

  La règle « seuls des paragraphes de même type se fusionnent » existe en deux versions : le front accepte `text`+`paragraph`, le backend les refuse. L'utilisateur voit donc le bouton actif, puis une erreur 400. En lecture stricte (« protégés **dans le domaine** »), l'item 2.4.2 serait non conforme et ouvrirait un second CRIT. Ce n'est pas retenu, pour rester cohérent avec 0.7.3, mais c'est à trancher.
- **Règle violée** : 2.4.2 — conforme ; dégradation (recoupe audit 01, 1.2.3).
- **Remédiation** : fabriques validantes dans `domain/analysis_editing.py` (`EditCommand.replace_text(element_id, text)`, etc.), constantes `HEADING_LEVELS`/`MERGEABLE_TYPES` et `supported_operations(type)` dans le domaine, `DocumentAnalysisSelection.of(document_id, analysis)` qui refuse une analyse étrangère ou non terminée. Le front lit `supportedOperations` au lieu de recopier la règle.

### [MIN] `EditorSnapshot` fabrique un `AnalysisJob` à identité forgée

- **Localisation** : `document-parser/services/analysis_edit_service.py:325-339` (`AnalysisJob(id=f"working:{document.id}", status=COMPLETED, ...)`) ; consommateurs `document-parser/api/analysis_edits.py:30-47`, `:65`, `:199`, `document-parser/services/chunk_service.py:714`, `document-parser/services/export_service.py:123`, `:131`.
- **Constat** : le résultat projeté de l'éditeur est transporté dans une instance de l'entité `AnalysisJob`. Son id `working:{document_id}` n'est pas unique : deux analyses de base d'un même document produisent le même id. Il n'est jamais persisté et ne correspond à aucune ligne. L'instance naît `COMPLETED` sans passer par `mark_running`/`mark_completed`. L'API publie cet id (`AnalysisResponse.id`, `api/analysis_edits.py:32`) ; le frontend ne l'utilise pas aujourd'hui (seul `contentMarkdown` est lu, `AnalysisEditor.vue:279`). Il s'agit d'un modèle de lecture déguisé en entité, comme `find_all_summaries` en 0.7.3, mais cette fois avec une identité forgée.
- **Règle violée** : 2.2.1 — conforme (l'entité garde identité et cycle de vie) ; dégradation.
- **Remédiation** : un VO `EditedAnalysisResult(base_analysis_id, content_markdown, content_html, pages_json, document_json)` dans le domaine, renvoyé par `active_result`/`load_editor`, et un DTO HTTP dédié (ou `AnalysisResponse` avec `id=base_analysis_id` et un champ `edited: true`).

### [MIN] Frontières inter-contextes non typées : `active_result_service`, et la feature `document` qui rappelle l'éditeur

- **Localisation** : `document-parser/services/chunk_service.py:153`, `:376-385`, `:712-714` ; `document-parser/services/export_service.py:40`, `:120-131` ; `frontend/src/features/document/api.ts:20-29` ; `frontend/src/features/document/store.ts:25-35`.
- **Constat** : le contexte chunks et l'export dépendent du contexte édition par un paramètre `active_result_service=None` sans type. Ils appellent `active_result`/`load_editor`, puis prennent `.job` dans un `EditorSnapshot`, qui est un type des services de l'éditeur. Le contrat entre contextes n'est donc décrit nulle part. Côté front, la feature `document` réimplémente l'appel `GET /analysis-editor` et fusionne elle-même le résultat édité dans l'`Analysis` de base, au lieu de passer par le barrel `@/features/analysis-editor`. La feature éditeur a pourtant son propre `api.ts:15`.
- **Règle violée** : 2.1.3 / 2.1.4 — conformes ; dégradation.
- **Remédiation** : un port de lecture `ActiveAnalysisResult` dans `domain/ports.py`, qui renvoie le VO `EditedAnalysisResult` (cf. [MIN] précédent). Côté front, exposer `fetchEditedResult` depuis la feature éditeur.

### [MIN] Le schéma JSON Docling est lu dans le domaine (reconduit de 0.7.3)

- **Localisation** : `document-parser/domain/ports.py:412` (`DocumentTreeReader`) ; `document-parser/domain/element_reader.py:85-86`, `:172-214` ; `document-parser/domain/parse_index.py:54` (fichiers du domaine non modifiés).
- **Constat** : inchangé. Il vaut désormais aussi pour l'éditeur, qui adresse les éléments par `self_ref` Docling (`EditorElement.self_ref`, identifiants logiques `{base_id}:{self_ref}` en `infra/docling_editor.py:84`).
- **Règle violée** : 2.5.3 — dégradation de 0.7.3, désormais incluse dans un item non conforme.
- **Remédiation** : celle de 0.7.3.

### [MIN] Règles cœur du contexte citation dans les services (reconduit de 0.7.3)

- **Localisation** : `document-parser/services/citation_service.py:39`, `:201-277` ; `document-parser/services/navigation_service.py:231-276` ; `document-parser/domain/navigation.py:154-178` (fichiers non modifiés).
- **Constat** : inchangé.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] Un value object `frozen` est muté après construction (reconduit de 0.7.3)

- **Localisation** : `document-parser/domain/source_map.py:202-203`, `:285`.
- **Constat** : inchangé.
- **Règle violée** : 2.2.2 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse (reconduit de 0.7.3)

- **Localisation** : `document-parser/persistence/analysis_repo.py:18-35` ; `document-parser/domain/ports.py:227`, `:239-243`.
- **Constat** : inchangé. Le port gagne en plus un drapeau d'effet de bord inter-agrégats (`update_status(..., select_analysis=...)`, `domain/ports.py:245`), traité dans le [MAJ] n°2.
- **Règle violée** : 2.5.1 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [MIN] Contrats inter-couches en tuples et par texte de message (reconduit de 0.7.3)

- **Localisation** : `document-parser/services/source_service.py:91-96` ; `document-parser/api/analyses.py:84`.
- **Constat** : inchangé. Le nouveau routeur de l'éditeur, lui, traduit des erreurs typées (`api/analysis_edits.py:110-117`), ce qui est le bon modèle.
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** : celle de 0.7.3.

### [INFO] Immutabilité superficielle des nouveaux VO

- **Localisation** : `document-parser/domain/analysis_editing.py:29` (`payload: dict[str, Any]`), `:89` (`reference_changes: dict[str, str]`).
- **Constat** : `frozen=True` n'empêche pas `command.payload["text"] = ...`. Ce n'est pas exploité aujourd'hui : le service ne mute pas les payloads, et l'adaptateur les lit seulement.
- **Règle violée** : 2.2.2 — observation.
- **Remédiation** : `MappingProxyType`, ou des payloads typés par commande (cf. fabriques ci-dessus).

### [INFO] `models.py` multi-contextes (reconduit, réduit)

- **Localisation** : `document-parser/domain/models.py:77-88`.
- **Constat** : le fichier diminue (331 → 314 l.), mais les deux VO document-level de l'éditeur y sont ajoutés plutôt que dans `analysis_editing.py` ou un module `document_state.py`. `AnalysisJob.document_filename` est inchangé.
- **Règle violée** : 2.1.2 — observation.
- **Remédiation** : les déplacer avec la modélisation `DocumentAnalysisState` ([MAJ] n°2).

### [INFO] `GraphPayload` toujours mutable (reconduit)

- **Localisation** : `document-parser/domain/value_objects.py:270-271`.
- **Constat** : inchangé (ligne 284 → 270 après le retrait de `ChunkEditAction`).
- **Remédiation** : inchangée.

### [INFO] L'import d'une analyse Docling n'existe pas dans le modèle (reconduit)

- **Localisation** : `document-parser/services/analysis_service.py:179-184`.
- **Constat** : inchangé. Une analyse importée devient aussi, maintenant, sélection active et base éditable, sans attribut d'origine.
- **Remédiation** : inchangée.

### [INFO] La garde d'architecture n'interdit pas Docling au domaine (reconduit)

- **Localisation** : `document-parser/tests/test_architecture.py:297` (fichier non modifié).
- **Constat** : inchangé. Elle ne détecterait pas non plus le [CRIT] ci-dessus, qui passe sans import.
- **Remédiation** : inchangée.

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP (reconduit)

- **Localisation** : `document-parser/mcp_adapter/wire.py:27`, `:223`.
- **Constat** : inchangé.
- **Remédiation** : inchangée.

---

## Delta vs 0.7.3

**Score** : 92 → **75** (−17). Items conformes : 15/17 → 12/17. Écarts : 0 CRIT / 1 MAJ / 6 MIN / 5 INFO → **1 CRIT / 2 MAJ / 10 MIN / 6 INFO**.

| Écart 0.7.3 | Statut en 0.7.4 |
|-------------|-----------------|
| [MAJ] 2.3.1 homonymie « version » / « parse » / round-hop-iteration | **Toujours ouvert, aggravé** : remédiations 1-2 non faites. La 3 (« parse courante ») a été traitée à moitié : la sélection active existe, mais MCP, les replis services et le front gardent leur propre définition. |
| [MIN] 2.3.3 statuts en chaînes nues | **Toujours ouvert**, inchangé. |
| [MIN] Schéma Docling lu dans le domaine (2.5.3) | **Toujours présent**, inchangé. L'item 2.5.3 tombe désormais pour une autre raison ([CRIT]). |
| [MIN] Règles de citation dans les services (2.4.2) | **Toujours présent**, inchangé. |
| [MIN] `SourceHop` muté (2.2.2) | **Toujours présent**, inchangé. |
| [MIN] `AnalysisJob` partiellement hydratée (2.5.1) | **Toujours présent**, et `update_status` gagne un effet de bord inter-agrégats. |
| [MIN] Contrats en tuples et par message (2.1.3) | **Toujours présent**, inchangé. |
| [INFO] ×5 | Tous toujours présents. `models.py` diminue. |

Origine des −17 points, uniquement le code nouveau de 0.7.4 (contexte édition d'analyse) :
- 2.5.3 : −3 (type Docling dans le service) ;
- 2.4.3 : −2 (état document-level sans racine) ;
- 2.2.4 : −1 (`EditStream` anémique).

Les deux items déjà non conformes en 0.7.3 (2.3.1, 2.3.3) restent non conformes. Aucune régression sur le code 0.7.3 : entités, cycle de vie, dépôts et anti-corruption existants sont intacts, et le contexte navigation n'a pas été touché.

---

## Points positifs

- **L'édition est modélisée comme un flux de commandes durable, pas comme une mutation du résultat** (2.1.1, 2.2.2). « The edit stream is the durable user intent. Rendered analysis data is only a materialized projection » (`domain/analysis_editing.py:3-4`) : l'analyse de base reste immuable, et le résultat se reconstruit à tout moment (`rebuild`). Les commandes sont versionnées (`command_version`) et adressées par des identifiants logiques stables. C'est un modèle de domaine solide.
- **Bascules append-only dans le domaine** : annuler ou réappliquer une modification ajoute un événement `setCommandActive` au lieu d'effacer l'historique. La fonction pure qui résout l'état (`active_edit_commands`) valide la cible, le type et la version (`:131-141`).
- **9/9 nouvelles dataclasses du domaine gelées**, et aucune entité mutable ajoutée.
- **Anti-corruption HTTP propre** (2.5.2) : union discriminée Pydantic par type de commande (`api/schemas.py`, `AnalysisEditCommandRequest`), traduite en `EditCommand`. Erreurs typées 400/409 sans lecture de message.
- **La sélection active devient un concept backend explicite** : la décision de 0.7.3 est amorcée, avec un VO, un port, des triggers d'intégrité, et `restore` qui ne délègue plus ce choix au frontend (`version_service.py:195-201`).
- **Retrait propre du journal `ChunkEdit`** dans toutes les couches (domaine, port, services, schéma SQL via l'upgrade #391).
- **Frontend miroir du vocabulaire backend** pour l'éditeur (`EditorElement`, `EditorTreeNode`, `baseAnalysisId`, `appliedThroughSequence`), dans une feature isolée derrière son barrel.

---

## Verdict partiel : NO-GO

Il y a un écart CRITICAL (2.5.3) : selon la règle absolue du master §3, c'est un NO-GO quel que soit le score (75/100, dans la plage 60-79). Il y a aussi deux MAJOR (2.3.1 reconduit et aggravé ; 2.4.3 nouveau).

Le CRIT a la même cause racine que le [CRIT] 1.4.1 de l'audit 01, et se corrige par le même changement : un port qui compose éditeur et projecteur et renvoie un `ProjectedAnalysis`. Ce changement fait remonter l'audit à 83, au seuil du GO (≥ 80), mais avec deux MAJ à planifier :
- unifier la notion d'analyse courante, MCP compris (2.3.1) ;
- modéliser `DocumentAnalysisState` et rendre `restore` atomique (2.4.3).

**Point à trancher par le mainteneur** : en lecture stricte de 2.4.2 (« invariants protégés **dans le domaine** »), les règles d'édition en infra et l'invariant de sélection en SQL ouvriraient un second CRIT. Ce rapport retient, comme en 0.7.3, le critère « aucun état invalide n'est créable », et les classe en [MIN].

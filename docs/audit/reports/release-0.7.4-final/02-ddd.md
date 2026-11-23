# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a744f48` (arbre de travail)

Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (`docs/audit/reports/release-0.7.4-validation/02-ddd.md` : 89/100, 14/17, 0 CRIT / 1 MAJ / 13 MIN / 12 INFO, GO).

Référence : fiche `docs/audit/audits/02-ddd.md`, barème `docs/audit/master.md` §2, §3, §5.
Méthode : lecture statique de l'arbre de travail, `rg`, `git diff efc0bc5 a744f48`, `git show`, `git blame`. Ni application, ni tests, ni lint, ni build lancés. Les messages de commit n'ont pas servi de preuve : chaque affirmation ci-dessous renvoie au code. Suites déclarées par le mainteneur sur ce commit (non relancées ici) : backend ruff propre, 1773 passés / 15 ignorés ; frontend propre, 604 tests dans 71 fichiers.

Périmètre réel du cycle : `efc0bc5..a744f48` compte neuf commits, pas cinq. En plus de `73ceaf3`, `da6603d`, `894bba4`, `914246e`, `a744f48`, il contient `89c33f0` (tests, lint), `1cd8413` (CI, e2e), `cf67dbb` (rapports de validation) et `60234e4` (suppression de composants non montés, dont `pages/DocIngestTab.logic.ts`). `60234e4` compte pour cet audit : il retire un des trois sens d'« historique » et son message dit que le chemin de chargement du workspace dans le store `document` n'est plus monté par aucun écran, ce qui se vérifie (voir D4).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 14 / 17 |
| Score | 89 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 12 |
| Écarts INFO | 15 |

Score = (32 / 36) × 100 = 88,9 → **89**. Items non conformes : 2.3.1 (poids 2), 2.2.4 (1), 2.3.3 (1).

**Lecture appliquée pour 2.3.1** (stricte, la même que la validation) : l'item reste **non conforme**. Les quatre étapes demandées par la validation sont faites, et le défaut le plus grave (un même mot pour deux contenus au niveau des méthodes) a disparu. Mais la lecture stricte retenait aussi l'homonymie « version », inchangée, et deux noms pour un concept ; or il y en a toujours deux officiels (« active » / « current », déclarés synonymes dans le code), deux de passage (« default », « latest »), les types de ports restent coupés selon le contenu (`CurrentAnalysisReader` pour l'original, `ActiveAnalysisResultReader` pour l'édité), et `workspaceActiveAnalysis` désigne côté front l'analyse affichée, pas l'analyse active du document.
**Lecture alternative** (la barre est la remédiation en quatre étapes de la validation ; le reste devient [MIN]) : 2.3.1 conforme, 34/36 → **94**, 15/17, 0 MAJ.

**Sensibilité sur 2.4.3** : l'agrégat est désormais un enregistrement gelé sans méthode d'écriture. Je le garde conforme (voir l'item). Si l'on exige que toute modification passe par une méthode de la racine, 2.4.3 bascule : 30/36 → **83**, toujours GO.

### Métriques de périmètre (`efc0bc5` → `a744f48`)

| Mesure | efc0bc5 | a744f48 |
|--------|---------|---------|
| Modules `document-parser/domain/*.py` | 29 | 28 (−`hashing.py`, −`lifecycle_aggregation.py`, +`quote_location.py`) |
| Dataclasses `frozen=True` dans `domain/` | 68 | 68 |
| Dataclasses mutables (`@dataclass` nu) dans `domain/` | 8 | 7 (`DocumentAnalysisState` gelé) |
| `Protocol` dans `domain/ports.py` | 32 | 32 |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| `domain/models.py` | 436 l. | 415 l. |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 149 | 146 |
| Classes `*Manager/Handler/Processor/Helper/Util` | 0 | 0 |
| Lecteurs backend qui choisissent eux-mêmes « la dernière analyse » | 0 | 0 |
| Définitions front de l'analyse courante | 1 + repli `versions[0]` | 1, sans repli (sur un chemin qu'aucun écran ne monte) |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Inchangés. La localisation d'une citation rejoint le contexte navigation dans le domaine (`domain/quote_location.py`, `domain/navigation.py:382` `pick_within_budget`). |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `models.py` redescend à 415 lignes (436) : `DocumentAnalysisSelection`, les drapeaux et les méthodes d'écriture de l'agrégat sont partis. |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | `EditorSnapshot.job` forgée et contrats en tuples inchangés ; un tuple de quatre de plus dans le domaine (`domain/navigation.py:387`) ([MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI (MIN) | La feature `document` appelle toujours `GET /analysis-editor` (`frontend/src/features/document/api.ts:19-28`) ([MIN]). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI (MIN) | `AnalysisJob` porte maintenant les prédicats de sélection (`domain/models.py:184-195`). `EditorSnapshot` forge toujours `working:{doc}:{base}` (`services/analysis_edit_service.py:341`) ([MIN]). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | `DocumentAnalysisState` et `DocumentChunkSource` gelés (`domain/models.py:89`, `:98`). `SourceHop` toujours muté (`domain/source_map.py:203`) ([MIN]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | L'agrégat n'a plus ni drapeau ni `mark_saved` ; aucune méthode d'écriture. |
| 2.2.4 | Entités porteuses de comportement | 1 | **NON** | `AnalysisJob` gagne trois prédicats, l'agrégat deux décisions. Mais `EditStream` (`domain/analysis_editing.py:58-63`) reste un sac de quatre champs gelés, sans méthode. Voir [MIN]. |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Réduit : méthodes nommées par contenu, docs MCP et docstrings corrigées, repli `versions[0]` supprimé. Restent deux noms officiels et deux noms de passage pour un concept, des types de ports coupés selon le contenu, `workspaceActiveAnalysis` homonyme, l'homonymie « version ». Voir [MAJ]. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `select_after_deleting`, `can_be_current_of`, `locate_quote`, `AnalysisNotSelectableError` : noms métier. 0 classe générique. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Inchangé : `STATUS_PATH/READ/CITED` (`domain/source_map.py:44-46`), `STATUS_UNREAD` (`domain/source_bar.py:20`), `operation: str` (`services/analysis_edit_service.py:317`), `EditorElement.type: str` (`domain/analysis_editing.py:76`, `:89`). |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | `DocumentAnalysisState` (`domain/models.py:98-141`) reste la racine de l'état du document, lu entier par `find_state` / `find_states`. |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | « Terminée et du document » est maintenant une règle de domaine, `AnalysisJob.can_be_current_of` (`domain/models.py:188`), appelée par le résolveur, la restauration, l'arbre, l'export ; `complete_and_select` refuse une analyse non terminée (`persistence/analysis_repo.py:177`). « Les deux colonnes ou aucune » tient par construction (`chunk_source: DocumentChunkSource | None`, `domain/models.py:113`). Reste : l'agrégat ne vérifie pas que sa source appartient au document ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | OUI (MIN) | Les écritures passent par trois opérations nommées de dépôt (`complete_and_select`, `delete`, `replace_for_document`) et un seul module SQL (`persistence/document_analysis_repo.py`). La décision de suppression est dans l'agrégat (`select_after_deleting`). Mais la racine n'a plus de méthode d'écriture : les fonctions SQL prennent des ids nus, et les décisions de restauration et de rechunk sont dans le service et dans un booléen `keep_selection` ([MIN]). |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Le dépôt d'état rend l'agrégat. `AnalysisJob` partiellement hydratée inchangée (`persistence/analysis_repo.py:17-35`) ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | Inchangé. |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | 0 import Docling dans `services/`. Schéma JSON Docling toujours lu dans le domaine (`domain/document_tree.py:58-139`) ([MIN]). |

---

## Écarts constatés

### [MAJ] « L'analyse courante » : un contenu par nom, mais toujours plusieurs noms pour le concept (réduit)

- **Localisation** :
  - **résolu** : `load_current_original` (`document-parser/domain/ports.py:231`, `services/current_analysis.py:69`) et `load_current_edited` (`domain/ports.py:454`, `services/analysis_edit_service.py:100`) disent ce qu'ils rendent et se renvoient l'un à l'autre ; `_resolve_original_analysis` a disparu ; `docs/mcp-server.md:154`, `:161-164`, `:221` disent que MCP lit l'analyse active, texte d'origine, et quand `version_id` vaut `null` ; `api/document_chunks.py:164`, `:181-183` parlent de l'analyse courante ; le repli `versions[0]` est supprimé (`frontend/src/features/document/store.ts:18-24`) ;
  - **deux noms officiels, déclarés synonymes** : « active » pour la colonne, l'agrégat, les erreurs, la doc et le CHANGELOG (`domain/models.py:111`, `services/analysis_edit_service.py:108`, `docs/user-guide.md:104`, `CHANGELOG.md` « Active analysis on the document API ») ; « current » pour la règle, le port, le champ d'API (`domain/models.py:144`, `domain/ports.py:216`, `api/schemas.py` `current_analysis_id`). Le code l'écrit lui-même : « The active analysis is the document's current analysis » (`domain/models.py:103-106`), « current (active) » (`domain/models.py:185`), et le CHANGELOG : « returns `currentAnalysisId`, the document's active analysis » ;
  - **types de ports encore coupés selon le contenu** : `CurrentAnalysisReader` rend l'original, `ActiveAnalysisResultReader` l'édité (`domain/ports.py:216`, `:447`), injecté sous le nom `active_result_service` (`services/chunk_service.py:56`, `services/export_service.py:47`, `services/document_tree_service.py:37`). Le renommage s'est arrêté aux méthodes ;
  - **deux noms de passage** : « default » — `_resolve_default_analysis` rend l'analyse demandée telle quelle **ou** l'analyse courante éditée (`services/export_service.py:125-129`), `shared/types.ts:49` « reads by default », `services/parse_loader.py:74`, `docs/mcp-server.md:154` ; « latest » — `workspaceLatestAnalysis` est un alias de `workspaceActiveAnalysis` (`frontend/src/features/document/store.ts:73`), lu seulement par les tests ;
  - **homonyme front** (non relevé par la validation) : `workspaceActiveAnalysis` reçoit, sur le seul chemin monté, l'analyse ouverte par `AnalysisDetailPage` (`frontend/src/pages/DocParseTab.vue:372`, `store.ts:265-266`), pas l'analyse active du document ; le commentaire `DocParseTab.vue:444-450` parle de « active analysis » et d'un tiroir History qu'aucun écran ne monte. `analysisStore.currentAnalysis` reste l'analyse ouverte ou en cours dans Studio (`features/analysis/store.ts:32`, `pages/DocWorkspacePage.vue:140`) ;
  - **commentaires faux** : `store.ts:148-149` « Without a current analysis the newest version is pinned, as before » contredit `pickWorkspaceVersion` (`store.ts:22`) ; `docs/user-guide.md:119` dit que « the last remaining completed analysis » devient active, le CHANGELOG et le code ajoutent « that has a Docling document » (`persistence/analysis_repo.py:262-263`) ;
  - **homonymie « version »** inchangée : `version_id` = id d'analyse (`services/parse_loader.py:78-86`, `services/citation_service.py:69`) vs `DocumentVersion` (`domain/models.py:381`).
- **Constat** : le choix de l'analyse a une seule définition, backend et front (le front ne garde plus de repli). Ce qu'un lecteur obtient (original ou édité) se lit désormais dans le nom de la méthode. Mais le concept garde deux noms officiels, que le code déclare équivalents au lieu d'en retenir un, et en gagne un troisième (« default ») avec ce cycle. Au niveau des types, le découpage « current = original, active = édité » que la validation reprochait existe encore. Et le front emploie « active » pour l'analyse affichée, qui n'est souvent pas l'analyse active du document — exactement le cas que la doc utilisateur signale (« not always the one on screen », `docs/user-guide.md:104`).
- **Règle violée** : 2.3.1 (poids 2).
- **Remédiation (la moins chère)** : (1) retenir un mot, « active » côté utilisateur et doc puisque c'est celui de la doc et du CHANGELOG, et écrire dans `domain/models.py` que `current_analysis_id` est le nom d'API du même concept ; (2) renommer `ActiveAnalysisResultReader` → `CurrentEditedResultReader` (ou fondre les deux lectures dans un port) et `active_result_service` en conséquence ; (3) `_resolve_default_analysis` → `_resolve_export_analysis` ; (4) côté front, `workspaceActiveAnalysis` → `workspaceAnalysis` (c'est l'analyse affichée), supprimer `workspaceLatestAnalysis`, corriger `store.ts:148-149` et `DocParseTab.vue:444-450` ; (5) aligner `docs/user-guide.md:119`. Effort S. L'homonymie « version » (contrat MCP public) peut attendre 0.8.0, mais tant qu'elle reste la lecture stricte ne passe pas.

### [MIN] L'agrégat `DocumentAnalysisState` : invariants tenus, racine en lecture seule (réduit, item conforme)

- **Localisation** : `document-parser/domain/models.py:89-141` ; `document-parser/persistence/document_analysis_repo.py:69-115` ; `document-parser/persistence/analysis_repo.py:200-238` ; `document-parser/persistence/chunk_repo.py:131-171` ; `document-parser/services/version_service.py:181-197` ; `document-parser/services/chunk_service.py:221-230`.
- **Constat** :
  - *Ce qui est résolu* : les quatre demandes de la validation sur l'agrégat sont faites ou rendues sans objet. `DocumentAnalysisSelection`, la propriété `selection`, les drapeaux, `mark_saved` et `save_state` ont disparu. La source des chunks est un VO optionnel : « les deux colonnes ou aucune » tient par construction dans le domaine, par le CHECK en base (`persistence/database.py:93`), et `_row_to_state` (`document_analysis_repo.py:47-58`) comme `DocumentVersion.chunk_source` (`domain/models.py:403-413`) lisent une paire incomplète comme « aucune ». L'objet est gelé : `state.active_analysis_id = x` lève une erreur au lieu de se perdre.
  - *Invariants* : un enregistrement gelé ne peut pas être mis dans un état invalide après construction ; à la construction, rien n'est vérifié (`chunk_source.document_id` peut différer de `document_id` ; seul `replace_for_document` le refuse, `chunk_repo.py:146-147`). `DocumentChunkSource.document_id` duplique l'identité de la racine sans contrôle.
  - *`select_after_deleting`* : décision pure, correcte, testée (`tests/test_analysis_deletion.py:130`). Mais le dépôt refait le test « est-ce l'analyse active ? » avant de l'appeler (`analysis_repo.py:229`) : la branche « garder la sélection » de la méthode (`models.py:138-139`) ne sert qu'aux tests, et la règle est écrite deux fois.
  - *`are_chunks_stale`* : la règle « pas de source → périmé s'il y a des chunks » est réécrite dans le service (`services/analysis_edit_service.py:362-366`), qui n'appelle l'agrégat que lorsqu'une source existe (pour éviter de hacher). Deux écritures d'une règle de domaine.
  - *Écritures* : la racine ne porte plus aucune transition. `write_selection`, `adopt_selection`, `write_chunk_source` prennent des ids nus ; la décision de restauration (adopter le repli quand le document n'a pas de ligne) est dans le service, lue hors transaction (`version_service.py:184-187`), celle du rechunk dans un booléen `keep_selection` passé au dépôt de chunks (`chunk_service.py:229`, `chunk_repo.py:157-160`). Le SQL n'existe qu'une fois, les transactions sont justes ; c'est la place des décisions qui est hors racine.
- **Règle violée** : 2.4.3 / 2.4.2 — conformes ; réserve.
- **Remédiation** : `__post_init__` qui refuse une source d'un autre document ; supprimer la branche morte ou le test dupliqué dans `delete` ; faire porter les décisions par l'agrégat (`state.after_restore(version, fallback_id)`, `state.after_rechunk(source)`) qui rendent le nouvel état, et un dépôt qui écrit la différence. Effort S.

### [MIN] `EditStream` reste anémique (inchangé, item non conforme)

- **Localisation** : `document-parser/domain/analysis_editing.py:58-63` ; règles en fonctions libres `:134`, `:152-180`.
- **Règle violée** : 2.2.4 (poids 1).
- **Remédiation** : `EditStream.append(commands, expected_sequence)` et `EditStream.accepts_base(hash)`.

### [MIN] Statuts et genres du contexte navigation en chaînes nues (inchangé, item non conforme)

- **Localisation** : `document-parser/domain/source_map.py:44-48` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/services/analysis_edit_service.py:317` ; `document-parser/domain/analysis_editing.py:76`, `:89`.
- **Règle violée** : 2.3.3 (poids 1).
- **Remédiation** : `SourceStatus`, `OutlineNodeKind` ; `Literal["preview", "save", "replay"]`.

### [MIN] « Historique » nomme encore deux concepts, trois dans les commentaires (réduit)

- **Localisation** : `frontend/src/features/history/api.ts:2-5` (liste d'analyses) ; `document-parser/domain/analysis_editing.py:49` (`EditHistoryEntry`, commandes d'édition) ; versions du document appelées « History » dans `services/chunk_service.py:185-187`, `domain/models.py:382`, `frontend/src/pages/DocParseTab.vue:446`, `frontend/src/features/document/ui/HistoryDrawer.vue` (non monté).
- **Constat** : `toHistoryEntry` est parti avec `pages/DocIngestTab.logic.ts` (`60234e4`). Restent la liste d'analyses et l'historique d'édition ; le troisième sens (versions) ne vit plus que dans des commentaires et un composant qu'aucun écran ne monte.
- **Règle violée** : 2.3.1 — dégradation.

### [MIN] `EditorSnapshot` fabrique un `AnalysisJob` à identité forgée (inchangé)

- **Localisation** : `document-parser/services/analysis_edit_service.py:340-353` ; `document-parser/domain/ports.py:454`.
- **Règle violée** : 2.2.1 — dégradation.

### [MIN] La feature `document` rappelle l'endpoint de l'éditeur (inchangé)

- **Localisation** : `frontend/src/features/document/api.ts:19-28`, `frontend/src/features/document/store.ts:41`.
- **Règle violée** : 2.1.4 — dégradation.

### [MIN] « Document introuvable » : six classes (inchangé)

- **Localisation** : `document-parser/services/chunk_errors.py:30`, `services/navigation_errors.py:21`, `services/preview_service.py:27`, `services/analysis_service.py:59`, `services/export_service.py:154`, `domain/analysis_editing.py:199`.
- **Règle violée** : 2.3.1 / 2.1.3 — dégradation.

### [MIN] Le schéma JSON Docling est lu dans le domaine (inchangé)

- **Localisation** : `document-parser/domain/document_tree.py:58-139` ; garde d'architecture sans Docling pour le domaine (`tests/test_architecture.py:183`).
- **Règle violée** : 2.5.3 — dégradation.

### [MIN] Règles du contexte citation dans les services (réduit)

- **Localisation** : `document-parser/services/citation_service.py` (246 l.), `document-parser/services/navigation_service.py` (251 l.).
- **Constat** : la localisation d'une citation (`domain/quote_location.py`) et le découpage par budget (`domain/navigation.py:382-421`) sont passés dans le domaine ; le service garde l'orchestration et le contrôle de longueur des citations (`citation_service.py:72-80`).
- **Règle violée** : 2.4.2 — dégradation.

### [MIN] Un value object est muté après construction (inchangé)

- **Localisation** : `document-parser/domain/source_map.py:202-203`.

### [MIN] `AnalysisJob` partiellement hydratée (inchangé)

- **Localisation** : `document-parser/persistence/analysis_repo.py:17-35`, `:46-51`.

### [MIN] Contrats inter-couches en tuples (légèrement aggravé)

- **Localisation** : `document-parser/services/document_service.py:133-135` ; `document-parser/services/source_service.py` ; nouveau : `document-parser/domain/navigation.py:387` (`tuple[list[ResolvedElement], int, bool, str | None]`).

### [INFO] Un rechunk dont l'analyse disparaît en route répond 500 (nouveau, introduit par la correction de D1)

- **Localisation** : `document-parser/persistence/chunk_repo.py:157-167` ; `document-parser/services/chunk_service.py:223-230`.
- **Constat** : `adopt_selection` peut lever `AnalysisNotSelectableError` (document sans ligne, analyse supprimée pendant le chunking). La restauration la traduit en 409 (`version_service.py:196-197`), le rechunk non : 500. Rare.
- **Remédiation** : attraper l'erreur dans `rechunk_document` et lever `ChunkServiceError(..., http_status=409)`.

### [INFO] La décision de restauration lit l'état hors transaction (nouveau)

- **Localisation** : `document-parser/services/version_service.py:184-187`.
- **Constat** : « pas de ligne → adopter le repli » est décidé sur un `find_state` séparé, puis écrit par `write_selection` (pas `adopt_selection`). Une ligne créée entre les deux (une analyse qui se termine) serait écrasée par le repli. Fenêtre très courte ; sans conséquence pire que l'ordre inverse des deux écritures.

### [INFO] `currentAnalysisId` vaut `null` pour deux raisons (non relevé avant)

- **Localisation** : `document-parser/api/schemas.py` (`current_analysis_id`), `frontend/src/shared/types.ts:49-51`, `CHANGELOG.md` (« always `null` » sur la liste et l'upload).
- **Constat** : sur `GET /api/documents/{id}`, `null` = pas d'analyse active ; sur la liste et l'upload, `null` = non calculé. Documenté, mais un même champ porte deux sens.

### [INFO] Message d'erreur du créneau `current_analysis`

- **Localisation** : `document-parser/api/deps.py:42-43` (« Document service not available » pour le lecteur de l'analyse courante).

### [INFO] Repli du résolveur et rattrapage 0.7.3 ne choisissent pas tout à fait pareil (inchangé)

- **Localisation** : `document-parser/persistence/analysis_repo.py:249-266` (exige un parse, ordre `completed_at`) vs `document-parser/persistence/database.py:300-311` (préfère un parse, accepte sans). La succession après suppression utilise la première définition, ce qui est cohérent avec le repli.

### [INFO] Restaurer une version n'existe que par l'API (nouveau constat)

- **Localisation** : `frontend/src/features/document/ui/HistoryDrawer.vue` (non monté), `frontend/src/features/document/store.ts:150-276` (chemin `loadWorkspace` / `setWorkspaceVersion` non monté : `DocParseTab` reçoit toujours `:analysis`, `frontend/src/pages/AnalysisDetailPage.vue:55-60`).
- **Constat** : la doc le dit (`CHANGELOG.md`, `docs/mcp-server.md:161-162`). Le concept « analyse active » n'est montré par aucun écran ; l'utilisateur ne le connaît que par la doc. À décider côté produit.

### [INFO] `hash_result` vit dans le module de l'éditeur (inchangé)

- **Localisation** : `document-parser/domain/analysis_editing.py:134`, importé par `services/chunk_service.py:21`.

### [INFO] Inchangés

`PreviewImageKey` technique (`domain/ports.py:187`) ; statut HTTP porté par les erreurs de service ; ports « service vers service » ; immutabilité superficielle des VO de l'éditeur ; `GraphPayload` mutable (`domain/value_objects.py:258`) ; garde d'architecture sans Docling pour le domaine ; enum du domaine publiée dans le contrat MCP.

---

## Points positifs

- Supprimer l'analyse active choisit la suivante dans la même transaction, avec un verrou pris d'entrée (`BEGIN IMMEDIATE`, `persistence/analysis_repo.py:219-238`) ; la décision est une méthode pure de l'agrégat, le SQL reste dans le dépôt ; six tests couvrent les cas (`tests/test_analysis_deletion.py`).
- L'agrégat est gelé, sans drapeaux : plus de modification perdue en silence. La paire « source des chunks » est un VO ; l'invariant « les deux ou aucune » tient par le type.
- « Terminée et du document » est une règle de domaine nommée (`can_be_current_of`) au lieu de cinq conditions écrites à la main.
- Les méthodes de lecture disent leur contenu : `load_current_original` / `load_current_edited`, avec renvoi croisé dans les docstrings.
- D1, D2, D3, D5 corrigés avec un test chacun ; D4 corrigé dans le store avec deux tests.
- Code mort retiré du domaine (`domain/hashing.py`, `domain/lifecycle_aggregation.py`, écritures de `chunk_editing`) sans référence restante.
- La doc MCP dit enfin ce que MCP lit (analyse active, texte d'origine) et quand `version_id` vaut `null`.

---

## Delta vs validation

**Score** : 89 → **89** (0). Items conformes : 14/17 → 14/17. Écarts : 0 CRIT / 1 MAJ / 13 MIN / 12 INFO → **0 CRIT / 1 MAJ / 12 MIN / 15 INFO**. Aucun item ne bascule. 2.3.1 reste non conforme sous la lecture stricte ; 94 sous la lecture alternative.

| Écart de la validation | Statut sur a744f48 | Preuve |
|------------------------|--------------------|--------|
| [MAJ] 2.3.1 Une règle, pas encore un vocabulaire | **Réduit** : méthodes par contenu, docs/docstrings corrigées, repli front supprimé ; restent active/current, types de ports, « default », `workspaceActiveAnalysis`, « version » | `domain/ports.py:216`, `:447`, `:231`, `:454` ; `services/export_service.py:125` ; `store.ts:37`, `:73`, `:148` |
| [MIN] Agrégat ouvert | **Réduit** : gelé, VO de source, Selection et drapeaux supprimés ; décisions d'écriture hors racine | `domain/models.py:98-141` ; `services/version_service.py:184` |
| [MIN] 2.2.4 `EditStream` anémique | **Inchangé** | `domain/analysis_editing.py:58-63` |
| [MIN] 2.3.3 Statuts en chaînes nues | **Inchangé** | `domain/source_map.py:44-46` |
| [MIN] « Historique » ×3 | **Réduit** (×2 + commentaires) | `features/history/api.ts:2-5` ; `domain/analysis_editing.py:49` |
| [MIN] Invariant de sélection hors domaine | **Résolu** (règle `can_be_current_of`, reste fondu dans le MIN agrégat) | `domain/models.py:188` |
| [MIN] `EditorSnapshot` forgée | **Inchangé** | `services/analysis_edit_service.py:341` |
| [MIN] Front `document` → éditeur | **Inchangé** | `frontend/src/features/document/api.ts:19-28` |
| [MIN] « Document introuvable » ×6 | **Inchangé** | `services/chunk_errors.py:30` |
| [MIN] Schéma Docling dans le domaine | **Inchangé** | `domain/document_tree.py:58-139` |
| [MIN] Règles de citation dans les services | **Réduit** | `domain/quote_location.py`, `domain/navigation.py:382` |
| [MIN] `SourceHop` muté | **Inchangé** | `domain/source_map.py:203` |
| [MIN] `AnalysisJob` partiellement hydratée | **Inchangé** | `persistence/analysis_repo.py:17-35` |
| [MIN] Contrats en tuples | **Légèrement aggravé** | `domain/navigation.py:387` |
| [INFO] Source des chunks crée une ligne vide (D1) | **Résolu** | `persistence/document_analysis_repo.py:90-103`, `chunk_repo.py:157-158` |
| [INFO] Intégrité en 500 (D3) | **Résolu** sur la restauration ; reproduit sur le rechunk (nouvel INFO) | `chunk_repo.py:161-167`, `version_service.py:196` |
| [INFO] Repli vs rattrapage | **Inchangé** | `database.py:300-311` |
| [INFO] `models.py` grossit | **Résolu** (415 l.) | — |
| [INFO] `hash_result` dans l'éditeur | **Inchangé** | `domain/analysis_editing.py:134` |
| [INFO] ×7 inchangés | Inchangés | |

**Défauts probables D1-D5 de la validation** :

| Défaut | Statut | Preuve |
|--------|--------|--------|
| D1 — premier rechunk sans ligne d'état efface l'analyse courante | **Résolu** : `adopt_selection` crée la ligne avec l'analyse chunkée, sans toucher une ligne existante | `persistence/document_analysis_repo.py:90-103`, `chunk_repo.py:157-158`, `services/chunk_service.py:224-230` ; test `tests/test_chunk_service.py:498` |
| D2 — restauration sans analyse, issue dépendante de la source | **Résolu** : sans ligne, la restauration sélectionne le repli ; avec ligne, elle efface la sélection, dans les deux cas indépendamment de la source | `services/version_service.py:183-187` ; test `tests/test_version_service.py:235` |
| D3 — analyse supprimée entre contrôle et écriture → 500 | **Résolu** pour la restauration (409 via `AnalysisNotSelectableError`) ; même chemin non traduit sur le rechunk (INFO) | `persistence/chunk_repo.py:161-167`, `services/version_service.py:196-197` ; test `tests/test_version_service.py:262` |
| D4 — workspace ouvre une analyse non courante ou supprimée | **Résolu dans le code**, sans effet visible : le chemin `loadWorkspace` n'est monté par aucun écran | `frontend/src/features/document/store.ts:22`, `:172-176`, `:206-208` ; `pages/AnalysisDetailPage.vue:55-60` ; tests `store.test.ts:305`, `:448` |
| D5 — version à moitié renseignée → 500 | **Résolu** : paire incomplète = aucune source | `domain/models.py:403-413` ; test `tests/test_version_service.py:287` |

**Les cinq régressions attribuées à la première remédiation** :

| Régression | Statut | Preuve |
|------------|--------|--------|
| 1. `ImportDocumentNotFoundError`, sixième classe | **Inchangé** | `services/analysis_service.py:59` |
| 2. Alias `fetchHistory` / `deleteHistoryEntry` | **Inchangé** | `frontend/src/features/history/api.ts:3-4` |
| 3. `EditorSnapshot` forgée publiée par un port | **Inchangé** | `services/analysis_edit_service.py:341`, `domain/ports.py:454` |
| 4. Deux `_hash_command` homonymes | **Résolu** (déjà à la validation ; `domain/hashing.py` supprimé, aucune référence restante) | `domain/analysis_editing.py:152` |
| 5. `find_with_store_links` renvoie un tuple | **Inchangé** | `services/document_service.py:133-135` |

**Régressions introduites par ce cycle** : aucune qui fasse basculer un item. Petites : le rechunk qui répond 500 si l'analyse disparaît en route (INFO, introduit par la correction de D1) ; un troisième nom pour le concept (« default », `services/export_service.py:125`) ; le commentaire `frontend/src/features/document/store.ts:148-149`, laissé tel quel, contredit la correction de D4 ; un tuple de quatre dans le domaine (`domain/navigation.py:387`).

**Décompte de « l'analyse courante »** :

| Où | Définition (quelle analyse) | Noms employés |
|----|-----------------------------|---------------|
| Domaine | `resolve_current_analysis_id` (`domain/models.py:143-161`) : la sélection, sinon la dernière avec parse s'il n'y a pas de ligne | current, active, selection |
| Successeur après suppression | `select_after_deleting` (`domain/models.py:129-141`) + SQL du repli : même critère que le repli | active, selection |
| Services (10 lecteurs + route document) | la règle du domaine, via `CurrentAnalysisResolver` | current ; `ActiveAnalysisResultReader` / `active_result_service` pour l'édité ; « default » à l'export |
| API | `currentAnalysisId` (détail seulement ; `null` sur liste et upload) | current |
| Front, store `document` | `doc.currentAnalysisId`, sans repli (chemin non monté) | current ; `workspaceActiveAnalysis` = analyse affichée ; `workspaceLatestAnalysis` alias |
| Front, Studio | `analysisStore.currentAnalysis` = analyse ouverte/en cours (homonyme) | current |
| `docs/user-guide.md:104`, `:119` | conforme, « active » ; `:119` omet « avec un document Docling » | active |
| `docs/mcp-server.md:154`, `:161`, `:221` | conforme, « active » et « current » dans la même page | active, current |
| `CHANGELOG.md` | conforme | active (champ `currentAnalysisId`) |

Définitions : **1** (contre 1 + un repli front à la validation). Contenus : **2**, nommés désormais au niveau des méthodes (original pour Ask et MCP, édité pour l'éditeur, l'arbre, l'export par défaut et le rechunk). Noms : **2 officiels** (active, current) + **2 de passage** (default, latest) + **2 homonymes front** (`workspaceActiveAnalysis`, `analysisStore.currentAnalysis`).

---

## Relecture du chemin de suppression et de l'agrégat

Fichiers relus ligne à ligne : `domain/models.py`, `domain/ports.py`, `domain/exceptions.py`, `persistence/document_analysis_repo.py`, `persistence/analysis_repo.py`, `persistence/chunk_repo.py` (écriture d'état), `persistence/database.py:84-114`, `:296-311`, `services/current_analysis.py`, `services/version_service.py`, `services/chunk_service.py:177-235`, `services/export_service.py:60-145`, `services/analysis_edit_service.py:100-110`, `:265-285`, `:340-366`, `frontend/src/features/document/store.ts`, `frontend/src/pages/DocParseTab.vue:325-455`.

- **Suppression** : `BEGIN IMMEDIATE`, lecture du document, lecture de l'état sur la même connexion, `DELETE` (la clé étrangère passe la sélection à NULL si `PRAGMA foreign_keys = ON`, posé par `database.py:362`), calcul du repli après le `DELETE` (l'analyse supprimée ne peut donc pas être choisie), écriture de la sélection, `commit`. Analyse inconnue : `rollback`, `False`. Document sans ligne : rien n'est écrit, le repli continue de jouer. Décision dans le domaine, SQL dans le dépôt, une transaction : conforme à ce qui était demandé.
- **Triggers** : l'upsert du successeur déclenche `validate_update` ; le successeur appartient au document par construction de la requête.
- **Placeholders** : `_SELECT_SQL` 2/2, `_ADOPT_SQL` 2/2, `_CLEAR_SELECTION_SQL` 1/1, `_RECORD_CHUNK_SOURCE_SQL` 3/3, `_CLEAR_CHUNK_SOURCE_SQL` 1/1, repli `IN (...)` sur la liste passée.
- **Gel** : aucun code de production n'assigne un champ de `DocumentAnalysisState` (seuls des constructeurs) ; pas de `replace()` sur l'agrégat.

Non vérifié (lecture seule) : l'exécution de ces chemins ; le comportement de `BEGIN IMMEDIATE` sous aiosqlite avec le mode de transaction par défaut du module `sqlite3` ; le résultat réel des suites (chiffres du mainteneur, non relancés) ; les écrans, l'application n'ayant pas tourné.

---

## Verdict partiel : GO

Score 89 ≥ 80, 0 CRIT, 1 MAJ (seuil bloquant : > 3). Le troisième cycle fait ce que la validation demandait sur le comportement : D1 à D5 corrigés avec tests, suppression de l'analyse active traitée dans le domaine et en une transaction, agrégat gelé dont l'invariant de source tient par le type, repli front supprimé, docs MCP justes. Le MAJ restant est de vocabulaire : un concept, deux noms officiels et deux de passage, des types de ports encore coupés selon le contenu, un homonyme front, et « version » ; il se corrige à l'effort S par des renommages, sauf « version » qui touche le contrat MCP. Aucune régression ne fait basculer un item.

# Rapport de re-audit : DDD (Domain-Driven Design)

> **Re-audit de `claude/nifty-turing-fmn3wo` @ `a4d9679` — score 92 → 94**

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Type** : re-audit après remédiation
**Référence** : rapport initial `release-0.7.4/02-ddd.md` (code `1de1929`, rapport `e6047c2` ; 92/100, GO, 0 CRIT, 1 MAJ, 6 MIN, 5 INFO)
**Remédiation examinée** : `git log e6047c2..a4d9679` (100 commits ; `e6047c2` = `1de1929` + les rapports, aucun changement de code entre les deux). Commits pertinents pour cet audit :

| Commit | Objet | Effet DDD |
|--------|-------|-----------|
| `44d0e2f` | `SourceStatus`, `OutlineNodeKind`, `OutlineMode` en StrEnum ; `GraphPayload` gelé | 2.3.3, INFO 2.2.2 |
| `6daaa7c` | `SourceHop` → `SourceRound` dans le domaine, le fil MCP garde `hops` / `hop_id` | 2.3.1 |
| `b35816a` | Glossaire `docs/architecture/glossary.md` | 2.3.1 |
| `2deb5f4` | Suppression de `HistoryDrawer.vue` (et de `history.kind.*`) | 2.3.1 |
| `9432eb8`, `a2dbb0c` | `domain/citation_match.py`, `domain/read_budget.py` | 2.4.2 |
| `a98be58`, `c488ae7`, `7ae77c2`, `ba70bb6`, `2d102b0`, `8633608`, `2892b8c`, `6134b6b` | Règles d'édition de chunks, hash, arbre, sérialisation et `EditJournal` dans le domaine ; `ChunkService` découpé | 2.1.1, 2.4.2, 2.5.3 |
| `cb1e3b9` | `ServiceError` unique, `DocumentNotFoundError` partagé, plus de 404/400 au texte du message | 2.1.3 |
| `39dcda5`, `e331670`, `e68ee5a` | Ports complétés (`DocumentVersionRepository`, pools, `FileStorage`, `PdfInspector`) | 2.5.x |

Méthode : analyse statique (lecture du code, `grep`, inventaire AST des enums, `git diff e6047c2..HEAD`), commandes de la fiche, chaque écart 0.7.4 re-vérifié dans le code actuel. Aucune exécution de l'application. Suites de tests non relancées : résultats du coordinateur sur HEAD — backend `ruff check` / `ruff format --check` OK, pytest **1673 passed, 19 skipped** ; frontend vue-tsc OK, vitest **522 passed** (53 fichiers).

---

## Score de compliance

| Métrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 15 / 17 | **16 / 17** |
| Score | 92 / 100 | **94 / 100** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 1 | 1 (partiellement corrigé) |
| Écarts MINOR | 6 | 5 |
| Écarts INFO | 5 | 7 |

Score = (34 / 36) × 100 = 94,4 → **94**. Seul l'item 2.3.1 (poids 2) reste non conforme. Poids total 36 = 3+3+2+2 (2.1) + 2+2+3+1 (2.2) + 2+1+1 (2.3) + 2+3+2 (2.4) + 2+2+3 (2.5).

**Lecture de l'item 2.3.1** : même lecture qu'en 0.7.4 (le rapport initial conditionnait le +5 au glossaire **et** au renommage interne du jeton `version_id`, ou à défaut de `DocumentVersion`). Le glossaire est livré, le renommage ne l'est pas, et « History » garde deux sens dans le backend et le CHANGELOG (voir [MAJ]). Lecture alternative, si l'on admet qu'un glossaire / context map suffit pour un homonyme figé par un contrat public (précédent : la dualité `AnalysisJob` / `job` jugée « contenue et documentée » en 0.7.0) : 2.3.1 OUI (MIN), score **36 / 36 = 100**. Le score retenu est 94.

### Métriques de périmètre

| Mesure | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) |
|--------|-------------------|----------------------|
| Modules `document-parser/domain/*.py` | 26 | **30** (+ `chunk_serialization`, `citation_match`, `doc_tree`, `read_budget`) |
| Lignes `domain/` | 4 259 | 5 092 |
| Dataclasses `frozen=True` dans `domain/` | 53 | **58** |
| Dataclasses mutables dans `domain/` | 7 (6 entités + `GraphPayload`) | **6** (les entités, `models.py:37`, `:78`, `:142`, `:182`, `:226`, `:311`) |
| `StrEnum` dans `domain/` (AST) | 9 | **11** (+3 navigation, −`LLMProviderType`) |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| Imports hors stdlib / `domain.*` dans `domain/` | 0 | 0 |
| `domain/models.py` | 331 lignes | 331 lignes |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 123 | 134 (+9 `analysis_service.py`, +6 `document_tree_service.py`, −4 `chunk_service.py`) |
| `hop` dans `domain/` + `services/` (code) | `SourceHop`, `hop_id`, `hops`… | **0** (1 mention en docstring, `source_map.py:91`) |
| `sources_app.html` : `hop` / `round` | 54 / 77 | 54 / 77 (inchangé : la carte lit le fil, qui garde `hops`) |

---

## Évaluation item par item

| # | Item | Poids | 0.7.4 | Re-audit | Justification |
|---|------|-------|-------|----------|---------------|
| 2.1.1 | Contextes identifiés et isolés | 3 | OUI | OUI | **Amélioré** : le contexte chunk a ses règles dans le domaine (`chunk_editing.py`, `chunk_serialization.py`, `hashing.py`, `doc_tree.py`) et trois services distincts (`chunk_service.py` 311 l., `chunk_push_service.py` 339 l., `document_tree_service.py` 60 l.). Navigation : `citation_match.py`, `read_budget.py`. |
| 2.1.2 | Pas de god object | 3 | OUI | OUI | `models.py` à 331 lignes, aucun concept ajouté. INFO reconduit. |
| 2.1.3 | Frontières explicites | 2 | OUI (MIN) | OUI (MIN) | Discrimination 404/400 par texte supprimée (`api/analyses.py:139-145`). Restent les tuples de `SourceService.show` et `ValueError` pour un document Docling invalide. MIN partiellement corrigé. |
| 2.1.4 | Front = mêmes contextes | 2 | OUI | OUI | Inchangé ; `StoreConfig` typé (`features/store/api.ts`), tiroir mort supprimé. |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI | OUI | Inchangé (`mark_running` `analysis_service.py:177`). |
| 2.2.2 | VO immutables | 2 | OUI (MIN) | OUI (MIN) | 58 dataclasses gelées, `GraphPayload` gelé (`value_objects.py:271`). `SourceRound` toujours muté après construction (MIN inchangé). Nouveaux VO gelés : `BudgetedRead` (`read_budget.py:43-44`), `EditJournal` (`chunk_editing.py:158`). |
| 2.2.3 | Pas de persistance dans les VO | 3 | OUI | OUI | Aucune méthode `save/update/delete`. `chunk_serialization.py` est un module de fonctions pures sans I/O (voir INFO formes de fil). |
| 2.2.4 | Entités porteuses de comportement | 1 | OUI | OUI | Inchangé ; les règles split / merge (`chunk_editing.py:66`, `:96`) sont des fonctions pures du domaine plutôt que des méthodes d'agrégat, ce que l'item admet (« quand c'est pertinent »). |
| 2.3.1 | Vocabulaire cohérent | 2 | **NON** | **NON** | Partiellement corrigé : round unifié dans le domaine, glossaire publié, tiroir « History » supprimé. Restent l'homonyme `version_id` (deux services, même signature) et « History » = versions dans le backend et le CHANGELOG. Voir [MAJ]. |
| 2.3.2 | Noms du domaine | 1 | OUI | OUI | `grep -rnE "class \w*(Manager\|Handler\|Processor\|Helper\|Util)\b"` sur `domain/ services/ mcp_adapter/ api/` : 0. |
| 2.3.3 | Statuts explicites | 1 | **NON** | **OUI** | **Corrigé** : `CitationStatus`, `OutlineMode`, `OutlineNodeKind`, `SourceStatus` (`navigation.py:22`, `:41`, `:49`, `:58`) ; champs typés (`source_map.py:77`, `:126`, `:145`, `:147`, `:162` ; `navigation.py:222`, `:285`, `:308`) ; `source_bar.py:24` importe l'enum. Résidu en INFO. |
| 2.4.1 | Racines d'agrégat | 2 | OUI | OUI | Inchangé. Le chunkset est remplacé en une transaction par `replace_chunkset(document_id, …)` (`version_service.py:161-170`). |
| 2.4.2 | Invariants dans le domaine | 3 | OUI (MIN) | OUI (MIN) | **Amélioré** : `locate_quote` (`citation_match.py:32`), `pick_within_budget` (`read_budget.py:91`), règles split / merge avec refus typés (`chunk_editing.py:39-52`). Restent `Citation` sans fabrique, `CitationCheck.valid` redondant, `OutlineNode` né sans URI. MIN partiellement corrigé. |
| 2.4.3 | Modifications via la racine | 2 | OUI | OUI | Pas de nouvelle mutation hors racine ; setters de `store_service.py:272-307` (contexte déprécié) préexistants et acceptés. Aucune écriture de `status` / `lifecycle_state` hors domaine (`grep` : 0) ; seule écriture SQL après `transition_to` (`analysis_service.py:386`, `:395`). |
| 2.5.1 | Repositories → entités | 2 | OUI (MIN) | OUI (MIN) | Inchangé : `AnalysisJob` partiellement hydratée par `find_all_summaries`. |
| 2.5.2 | Anti-corruption HTTP | 2 | OUI | OUI | Inchangé ; config de store et nœuds de graphe typés (`api/schemas.py:361`, `api/graph.py:28`, `:42`). |
| 2.5.3 | Infra ne leake pas | 3 | OUI (MIN) | OUI (MIN) | 0 import `docling` dans `domain/` et `services/`. `_title` passé dans le domaine (`element_reader.py:240`), mobilier de page déclaré 2 fois au lieu de 3. Mais `doc_tree.py` ajoute un module du domaine qui lit le JSON Docling brut, avec une docstring qui dit le contraire. MIN partiellement corrigé. |

Calcul : conformes = 2.1.1 (3) + 2.1.2 (3) + 2.1.3 (2) + 2.1.4 (2) + 2.2.1 (2) + 2.2.2 (2) + 2.2.3 (3) + 2.2.4 (1) + 2.3.2 (1) + 2.3.3 (1) + 2.4.1 (2) + 2.4.2 (3) + 2.4.3 (2) + 2.5.1 (2) + 2.5.2 (2) + 2.5.3 (3) = **34** ; non conforme = 2.3.1 (2). Score = 34 / 36 = **94**.

---

## Écarts constatés

### [MAJ] Langage ubiquitaire : `version_id` reste homonyme dans le backend, « History » garde deux sens

**Statut vs 0.7.4 : partiellement corrigé.** Trois des quatre volets sont traités ; le plus lourd (homonyme `version_id`) est documenté mais pas levé, et l'homonyme « History » subsiste côté backend et dans le CHANGELOG de la remédiation.

- **Ce qui est corrigé** (vérifié dans le code) :
  - **Round / hop** : le domaine dit round partout — `SourceRound` (`domain/source_map.py:86`), `round_id`, `SourceNode.round_ids` (`:150`), `SourceTotals.rounds`. Plus aucun identifiant `hop` dans `domain/` ni `services/` (1 mention en docstring, `source_map.py:91`, qui explique le nom du fil). La traduction round → hop est isolée dans l'adaptateur (`mcp_adapter/sources_mapping.py:60`, `:86-89`, `:112`, `:141`), le contrat publié garde `hops` / `hop_id` / `hop_ids` (`mcp_adapter/sources_wire.py:12`, `:45`, `:54`, `:79`, `:91`, `:125`). Même schéma que celui recommandé.
  - **Glossaire / context map** publié et dans la navigation du site (`docs/architecture/glossary.md`, `mkdocs.yml:44`) : analysis = parse = même id (`:12-13`), avertissement sur `version_id` (`:16-28`), round / hop / iteration (`:45`, `:50-58`), deux sens de « citation » (`:59-61`), History = liste des analyses, OCR ≠ analyse (`:65-68`).
  - **Tiroir « History »** : `HistoryDrawer.vue` et les clés `history.kind.*` (dont le libellé « OCR » d'une version `analysis`) supprimés (`2deb5f4`) ; au front, « History » ne désigne plus que la page `/history` des analyses.
- **Ce qui reste** :
  1. **Homonyme `version_id`** (inchangé dans le code, désormais documenté). Dans le contexte navigation, `version_id` est l'id d'une `AnalysisJob` (`domain/anchors.py:7-11`) ; `ParseLoader.load(document_id, version_id)` (`services/parse_loader.py:70`). Dans le contexte versioning, `VersionService.restore(document_id, version_id)` (`services/version_service.py:131`) et la route `/{doc_id}/versions/{version_id}/restore` (`api/document_versions.py:49-60`) attendent un `DocumentVersion.id`. Deux services de la même couche, même signature, deux identifiants différents. Le glossaire le dit (`glossary.md:16-19`) et justifie le statu quo par le contrat MCP (`:21-25`), puis ajoute que renommer une seule couche « would add a third name rather than remove one » (`:25-28`). Cette justification contredit le traitement round / hop, où le domaine a été renommé et le fil conservé. La conséquence PLAUSIBLE relevée en 0.7.4 est inchangée : la « parse courante » de la navigation est la dernière analyse complétée (`citation_service.py:205-208`), le restore laisse le pointeur d'analyse active au front (`version_service.py:132-135`).
  2. **« History » = versions de document dans le backend et dans la remédiation elle-même**. Le glossaire pose « History (`/history`) lists analyses. It is not the list of document versions » (`glossary.md:65-66`). Or :
     - `domain/models.py:321` décrit `DocumentVersion` comme « what the History drawer » affiche — composant supprimé ;
     - `services/analysis_service.py:108` (« appends a frozen pair to History »), `services/version_service.py:7`, `:79` (« The document's history »), `:137` (« a history row ») ;
     - `CHANGELOG.md:22-23` (`[Unreleased]`) : « History restore », « The History list no longer loads the snapshots: `GET /api/documents/{id}/versions` », puis `:26` « the History page … `GET /api/analyses/summaries` » : deux sens à trois lignes d'écart.
  3. **Front** : `fetchHistory()` / `deleteHistoryEntry()` non renommés (`features/history/api.ts:8-14`), et `fetchHistory` appelle désormais le même endpoint que `fetchAnalysisSummaries()` (`features/analysis/api.ts:50-52`, depuis `e9bb312`) : deux noms pour la même lecture. Couvert par le glossaire (« History lists analyses »), résidu mineur.
  4. Dualité `AnalysisJob` / `job` : 123 → 134 occurrences dans `api/` + `services/` (découpage de `analysis_service.py`, nouveau `document_tree_service.py:46-58`). Documentée (`glossary.md:12`), même lecture qu'en 0.7.0 : observation. `ChunkNotFoundError(f"Analysis not found: …")` (`document_tree_service.py:49`) nomme une analyse introuvable par une erreur de chunk.
- **Règle violée** : 2.3.1 — « Le vocabulaire métier est cohérent entre domain, services, API et frontend » (poids 2).
- **Remédiation** (par effort croissant) :
  1. **S** — Renommer le paramètre côté versioning : `VersionService.restore(document_id, document_version_id)` (`version_service.py:131-175`) et la variable de chemin de la route (`api/document_versions.py:49-60` ; l'URL ne change pas, le nom de variable n'est pas exposé). `version_id` ne désigne alors plus, dans tout le backend, que le jeton de parse, comme l'affirme le glossaire. Aucun impact sur le contrat MCP.
  2. **S** — Dire « versions » et non « History » pour `DocumentVersion` : `models.py:321`, `analysis_service.py:108`, `version_service.py:7`, `:79`, `:137`, et `CHANGELOG.md:22-23` avant le gel.
  3. **S, optionnel** — `features/history/api.ts` : réutiliser `fetchAnalysisSummaries` / renommer en `deleteAnalysis`.
  4. **M, optionnel** — `version_id` → `parse_id` dans `domain/` et `services/`, fil MCP inchangé (`wire.py`), comme pour round / hop.

  Les points 1 et 2 suffisent à rendre 2.3.1 conforme (résidus documentés : `version_id` = parse sur le fil, `iteration` dans Ask, `hop` sur la carte) : **94 → 100**.

### [MIN] Le schéma JSON Docling est lu dans le domaine, contre le contrat du port `DocumentTreeReader`

**Statut vs 0.7.4 : partiellement corrigé, et étendu à un module de plus.**

- **Localisation** : `document-parser/domain/ports.py:506-515` ; `document-parser/domain/doc_tree.py:3-5`, `:52`, `:62`, `:103-104`, `:138-156` ; `document-parser/domain/element_reader.py:86`, `:157` ; `document-parser/domain/navigation.py:365` ; `document-parser/domain/page_regions.py:42`
- **Corrigé** : `_title` a quitté `source_service.py` pour le domaine (`element_reader.document_title`, `:240-260`, appelé `source_service.py:133`) ; le mobilier de page n'est plus déclaré que deux fois, toutes deux dans le domaine (`_EMPTY_LABELS`, `navigation.py:365` ; `_FURNITURE`, `page_regions.py:42`) au lieu de trois ; `heading_level` est partagé par l'arbre et l'outline MCP (`parse_index.py:231-244`, `2a6cf40`).
- **Reste** : le port promet toujours que « the adapter encapsulates every Docling-specific assumption (label taxonomy, parent.$ref/cref shape, …) » (`ports.py:512-514`). Le nouveau `domain/doc_tree.py` (déplacé de `services/chunk_service.py`, où il lisait déjà `$ref` / `cref`) affirme « Every docling-shaped access goes through the injected `DocumentTreeReader` port » (`:3-5`), puis lit lui-même `body` (`:52`, `:81`), `$ref` / `cref` (`:62`, `:104`), `children` (`:103`), `label`, `text`, `name` (`:138-156`). La lecture du schéma Docling dans le domaine passe de 4 à 5 modules (`element_reader`, `parse_index`, `navigation`, `page_regions`, `doc_tree`). Aucun type Docling importé : conforme à la lettre.
- **Règle violée** : 2.5.3 — conforme ; dégradation (poids 3).
- **Remédiation** : assumer la relation Conformist dans la docstring du port et corriger celle de `doc_tree.py` (S) ; un seul `FURNITURE_LABELS` (S) ; à terme, `children_of` / `label_kind` sur le port.

### [MIN] Règles cœur du contexte citation : la localisation et le budget sont dans le domaine, les VO de citation restent sans invariant propre

**Statut vs 0.7.4 : partiellement corrigé.**

- **Corrigé** : la localisation d'une citation (`locate_quote`, `_locate_across`, `_trim_left`, seuil `MIN_QUOTE_CHARS`) est dans `domain/citation_match.py:29-110` ; le service ne fait plus que charger la parse et formuler le verdict (`citation_service.py:23`, `:79`, `:133`). La découpe au budget (`refs_to_read`, `pick_within_budget`, `read_span_ref`) est dans `domain/read_budget.py:56-158`, appelée `navigation_service.py:151-157`. Les deux modules n'importent que `domain.*` et la stdlib.
- **Reste** : `Citation` (`domain/navigation.py:189-203`) sans fabrique ni `__post_init__`, construite par `CitationService.build` (`citation_service.py:172`) ; `CitationCheck.valid` redondant avec `status` (`navigation.py:206-214`, six constructions à la main `citation_service.py:100-161`) ; `OutlineNode` né avec `uri=""` (`outline_builder.py:111`, `:138`, `:196`) puis complété par `_stamp` (`navigation_service.py:123`, `:186-192`) ; l'invariant « une réponse = une parse » gardé par le service (`_single_pin`, `source_service.py:242`). Toujours une seule voie de construction : aucun état invalide produit aujourd'hui.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : `CitationCheck.valid` en propriété dérivée du statut (S) ; fabrique `Citation.of(anchor, element, quote)` (S) ; jeton de version passé à `build_outline` (M).

### [MIN] Un value object `frozen` est muté après sa construction

**Statut vs 0.7.4 : inchangé** (renommé : `SourceHop` → `SourceRound`).

- **Localisation** : `document-parser/domain/source_map.py:85-109`, `:211-213`, `:295`
- **Constat** : `SourceRound` est `frozen=True` (`:85`), mais `build_source_map` ajoute des URI à `round_.cited` après sa création (`round_.cited.append(anchor.uri)`, `:213`). `_Trail.nodes` passe toujours la liste interne `self.reached[...]` par référence à `SourceNode.round_ids` (`:295`), alors que `source_bar.py:59` en fait une copie. Le même module utilise `replace(...)` dans `_rounds` (`:320`). Le commit de typage (`44d0e2f`) et celui du renommage (`6daaa7c`) ont réécrit ces lignes sans traiter le point.
- **Règle violée** : 2.2.2 — conforme ; dégradation.
- **Remédiation** (S) : rassembler les citations par round avant de construire les `SourceRound`, ou `replace(round_, cited=[...])` ; `list(...)` à `:295` ; à terme, collections des VO en `tuple[...]`.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse

**Statut vs 0.7.4 : inchangé**, et la projection partielle sert désormais trois écrans.

- **Localisation** : `document-parser/domain/ports.py:306`, `:324-328` ; `document-parser/persistence/analysis_repo.py:10-28`, `:39-45`, `:68-76` ; `document-parser/api/schemas.py:172` ; `frontend/src/shared/types.ts:84`
- **Constat** : `find_all_summaries` renvoie des `AnalysisJob` sans contenu (`_SELECT_SUMMARY`, `analysis_repo.py:39-45`) : une analyse `COMPLETED` y a `content_markdown = None`, état que `mark_completed` ne produit pas. `_row_to_job` tolère toujours l'absence de chaque colonne de contenu (`... if "x" in keys else None`, `:16-23`). Le concept « résumé d'analyse » existe en API (`AnalysisSummaryResponse`) et au front (`AnalysisSummary`), pas dans le domaine. La remédiation 0.7.4 (#audit-12) fait charger ces résumés par la bibliothèque, la page History et l'accueil (`features/analysis/api.ts:50`, `store.ts:68`, `:188`, `pages/DocsLibraryPage.vue:352`). Le port expose toujours `latest_parsed_ids -> dict[str, str]`, `parsed_document_id -> str | None`, `parse_json -> str | None`.
- **Règle violée** : 2.5.1 — conforme (ni `Row` ni dict de ligne renvoyé) ; dégradation.
- **Remédiation** (M) : VO `AnalysisSummary` dans le domaine renvoyé par `find_all_summaries`, `_row_to_job` strict ; port de lecture dédié au contexte navigation.

### [MIN] Contrats inter-couches en tuples ; `ValueError` pour un document Docling invalide

**Statut vs 0.7.4 : partiellement corrigé.**

- **Corrigé** : le routeur ne lit plus le texte du message. Un document inconnu lève `DocumentNotFoundError` (`analysis_service.py:137`, `:165`), répondu 404 par le handler unique (`api/errors.py:24-30`) ; `import_analysis` n'attrape plus que `ValueError` → 400 (`api/analyses.py:139-145`).
- **Reste** :
  - `SourceService.show` prend toujours `list[tuple[str, str, str]]` / `list[tuple[str, str]]` (`source_service.py:85-96`, `:189`), alors que le domaine définit `SourceRead` et `SourceCited` (`source_map.py:54`, `:66`) ; l'adaptateur convertit les dicts en tuples positionnels (`mcp_adapter/sources_view.py:61-67`, `:97-104`) ; le statut circule en `str | None` (`source_service.py:167`, `:185-186`).
  - Un document Docling invalide ou trop gros reste un `ValueError` (`infra/docling_importer.py:18`, `:83`, `:96`) ; « importer non configuré » un `RuntimeError` (`analysis_service.py:168`), répondu 500. L'`InvalidDoclingDocumentError` proposée n'existe pas.
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** (S) : passer `SourceRead` / `SourceCited` à `show(...)` ; `InvalidDoclingDocumentError(ServiceError)` à 400.

### [INFO] Résidu du typage des statuts : producteurs en littéraux, enums rétrogradées aux frontières

**Nouveau (issu de la remédiation 2.3.3)**, sans effet sur l'item.

- **Localisation** : `document-parser/domain/outline_builder.py:57`, `:68`, `:113`, `:140`, `:198` ; `document-parser/domain/outline_locate.py:30`, `:38` ; `document-parser/mcp_adapter/sources_mapping.py:33` ; `document-parser/services/navigation_service.py:92` ; `document-parser/services/source_service.py:167`, `:185-186` ; `document-parser/domain/read_budget.py:33`, `:60` ; `document-parser/domain/navigation.py:227-229`, `:292-294`, `:313-315` ; `document-parser/domain/source_map.py:79-82`
- **Constat** : le producteur de l'outline, pourtant dans le domaine et importateur de `domain.navigation`, passe encore `mode="pages"`, `kind="section"`… ; `containing_chain(mode: str)` compare `mode == "pages"` ; `sources_card` aussi. Les services rétrogradent l'enum en chaîne (`str(doc.lifecycle_state)`, `check.status.value`) puis quatre `__post_init__` la re-promeuvent (« A caller may pass the plain value; the field holds the member »). Sans risque (un `StrEnum` refuse une valeur inconnue et égale sa chaîne), mais quatre coercitions servent surtout à laisser des producteurs internes passer des chaînes. Le mode de lecture `include` reste une chaîne validée contre un tuple (`READ_MODES`), alors qu'il est un `Literal` sur le fil (`mcp_adapter/server.py:173`).
- **Règle violée** : 2.3.3 — observation.
- **Remédiation** (S) : passer les membres (`OutlineMode.PAGES`, `OutlineNodeKind.SECTION`…) dans `outline_builder.py`, `mode: OutlineMode` dans `outline_locate.py`, puis retirer les coercitions devenues inutiles.

### [INFO] L'erreur « document inconnu » partagée vit dans le contexte navigation, et n'est pas encore la seule

**Nouveau (issu de `cb1e3b9` / `6134b6b`).**

- **Localisation** : `document-parser/services/navigation_errors.py:8-10`, `:18`, `:24-25` ; `document-parser/services/analysis_service.py:27` ; `document-parser/services/chunk_errors.py:18`, `:64` ; `document-parser/services/version_service.py:185` ; `document-parser/services/export_service.py:61` ; `document-parser/api/documents.py:105`, `:115`, `:172`, `:194`
- **Constat** : `DocumentNotFoundError` est annoncée comme « the one "unknown document" error of the backend » (`navigation_errors.py:8-10`) mais hérite de `NavigationServiceError` : les contextes analysis et chunk lèvent une erreur de la famille navigation, celle que l'adaptateur MCP transforme en erreur d'outil. Elle n'est pas non plus la seule : `VersionServiceError(..., http_status=404)` (`version_service.py:185`), `ExportNotFoundError` (`export_service.py:61`) et quatre `HTTPException(404)` du routeur documents disent la même chose autrement.
- **Règle violée** : 2.1.3 — observation (noyau partagé hébergé par un contexte).
- **Remédiation** (S) : `DocumentNotFoundError(ServiceError)` dans `services/errors.py` (noyau partagé), réexportée par `navigation_errors` ; `VersionService._require_doc` la lève.

### [INFO] Le domaine produit des formes de fil et de persistance

**Nouveau (issu du découpage de `ChunkService`).**

- **Localisation** : `document-parser/domain/doc_tree.py:7-8`, `:27` ; `document-parser/api/document_chunks.py:156` ; `document-parser/domain/chunk_serialization.py:1-21`, `:31-56`
- **Constat** : `build_doc_tree` renvoie des `dict` « `DocTreeNode`-shaped … which the API returns as is » (`doc_tree.py:7-8`), dépaquetés tels quels par le routeur (`DocTreeNodeResponse(**node)`). `chunk_serialization` fixe dans le domaine les clés camelCase des colonnes `chunks_json`, `chunks_snapshot`, `chunk_edits.before/after` et du payload d'ingestion. Cohérent avec des entités qui portent déjà ces JSON en chaîne (`AnalysisJob.chunks_json`, `DocumentVersion.chunks_snapshot`), pur et sans I/O : l'item 2.2.3 reste conforme.
- **Règle violée** : 2.2.3 / 2.5.2 — observation.
- **Remédiation** : VO `DocTreeNode` gelé dans le domaine, mis en forme par le DTO ; garder `chunk_serialization` tant que les entités transportent du JSON.

### [INFO] `models.py` multi-contextes et champ joint sur l'entité

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `document-parser/domain/models.py:78-96` ; `document-parser/services/analysis_service.py:140`, `:175`
- **Constat** : cinq contextes dans `models.py` ; `AnalysisJob.document_filename` renseigné à la main par le service.
- **Remédiation** : inchangée.

### [INFO] L'import d'une analyse Docling (#359) n'existe pas dans le modèle

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `document-parser/services/analysis_service.py:157-185`
- **Constat** : PENDING → RUNNING → COMPLETED simulé (`:174-179`) ; une analyse importée reste indiscernable d'une analyse convertie.
- **Remédiation** : inchangée (`AnalysisJob.imported(...)`, attribut `origin`).

### [INFO] La garde d'architecture n'interdit pas Docling au domaine

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `document-parser/tests/test_architecture.py:342`
- **Constat** : `_DOMAIN_FORBIDDEN_EXTERNALS = {"fastapi", "sqlalchemy", "httpx", "opensearchpy"}`, alors que la liste des services interdit `docling` / `docling_core` (`:345-348`). La remédiation a ajouté une garde AST sur `services/` (`39dcda5`), pas sur `domain/`. Pureté vérifiée par inventaire : 0 import hors stdlib / `domain.*`.
- **Remédiation** : inchangée (S, aucun import à migrer).

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `document-parser/mcp_adapter/wire.py:215-223` ; `document-parser/domain/navigation.py:22`
- **Constat** : `VerificationResult.status: CitationStatus`. Les trois nouvelles enums ne sont pas publiées sur le fil : les tests épinglent `str` dans les payloads (`44d0e2f`).
- **Remédiation** : inchangée.

---

## Delta vs 0.7.4

**Score** : 92 → **94** (+2). Items conformes : 15/17 → 16/17. Écarts : 0 CRIT / 1 MAJ / 6 MIN / 5 INFO → 0 CRIT / 1 MAJ / 5 MIN / 7 INFO.

| Écart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] 2.3.1 Langage ubiquitaire | **Partiellement corrigé** | Round : `source_map.py:86`, `sources_mapping.py:86-89`. Glossaire : `glossary.md`. Tiroir supprimé (`2deb5f4`). Restent `version_service.py:131` vs `parse_loader.py:70`, « History » `models.py:321`, `CHANGELOG.md:22-23`. |
| [MIN] 2.3.3 Statuts en chaînes nues | **Corrigé** | `navigation.py:22-71`, champs typés ; résidu INFO |
| [MIN] 2.5.3 Schéma Docling dans le domaine | **Partiellement corrigé** | `element_reader.py:240`, 2 déclarations du mobilier ; nouveau `doc_tree.py:3-5` vs `:62` |
| [MIN] 2.4.2 Règles de citation dans les services | **Partiellement corrigé** | `citation_match.py:32`, `read_budget.py:91` ; restent `navigation.py:189-214`, `outline_builder.py:111` |
| [MIN] 2.2.2 `SourceHop` muté | **Inchangé** | `source_map.py:213`, `:295` |
| [MIN] 2.5.1 Hydratation partielle | **Inchangé** | `analysis_repo.py:16-23`, `:39-45` |
| [MIN] 2.1.3 Tuples / message | **Partiellement corrigé** | `api/analyses.py:139-145` ; restent `source_service.py:85-96`, `docling_importer.py:83` |
| [INFO] `GraphPayload` mutable | **Corrigé** | `value_objects.py:271` |
| [INFO] `models.py` multi-contextes | Inchangé | — |
| [INFO] Import sans origine | Inchangé | — |
| [INFO] Garde d'architecture domaine | Inchangé | `test_architecture.py:342` |
| [INFO] `CitationStatus` sur le fil | Inchangé | `wire.py:223` |

**Nouveaux constats** (aucun CRIT, MAJ ni MIN) : 3 INFO — résidu du typage des statuts, `DocumentNotFoundError` hébergée par le contexte navigation, formes de fil / persistance produites par le domaine. **Régression** : aucune. Le seul recul est documentaire : la docstring de `domain/doc_tree.py:3-5` affirme un encapsulage que le code ne fait pas (compté dans le MIN 2.5.3), et le CHANGELOG de la remédiation reproduit l'homonyme « History » que le glossaire vient de lever (compté dans le MAJ).

**Nouveaux modules du domaine, vérifiés** : `chunk_serialization`, `citation_match`, `doc_tree`, `read_budget` et `chunk_editing` (`EditJournal`) n'importent que la stdlib et `domain.*` (inventaire : `__future__`, `typing`, `dataclasses`, `collections`, `datetime`, `re`, `enum`, `uuid`, `urllib`, `unicodedata`, `hashlib`) ; aucun I/O ; leurs dataclasses sont gelées (`BudgetedRead`, `EditJournal`). `EditJournal` est l'unique fabrique de `ChunkEdit` hors hydratation (`chunk_editing.py:211` ; `persistence/chunk_edit_repo.py:20`).

---

## Pistes de remédiation (gain de score)

| Action | Item | Gain | Effort | Risque |
|--------|------|------|--------|--------|
| Paramètre `document_version_id` côté versioning (`version_service.py:131-175`, `api/document_versions.py:49-60`, URL inchangée) + « versions » au lieu de « History » pour `DocumentVersion` (`models.py:321`, `analysis_service.py:108`, `version_service.py:7`, `:79`, `:137`, `CHANGELOG.md:22-23`) | 2.3.1 (poids 2) | **94 → 100** (+6) | S | Faible : renommages internes, aucun contrat public touché |
| Membres d'enum dans `outline_builder.py` / `outline_locate.py`, retrait des coercitions | INFO 2.3.3 | 0 point | S | Nul |
| `replace(round_, cited=…)` / `list(...)` dans `source_map.py` | MIN 2.2.2 | 0 point (−1 MIN) | S | Faible |
| `CitationCheck.valid` dérivé, `InvalidDoclingDocumentError`, `SourceRead` / `SourceCited` dans `show(...)` | MIN 2.4.2 / 2.1.3 | 0 point (−2 MIN) | S-M | Faible |
| Docstrings `DocumentTreeReader` et `doc_tree.py` alignées sur le code, `FURNITURE_LABELS` unique | MIN 2.5.3 | 0 point | S | Nul |
| `DocumentNotFoundError` dans `services/errors.py` ; `_DOMAIN_FORBIDDEN_EXTERNALS` complété | INFO | 0 point (−2 INFO) | S | Nul |

---

## Points positifs

- **Domaine toujours strictement pur** malgré +4 modules et +833 lignes : 0 import hors stdlib / `domain.*`, 0 import `docling` dans `domain/` et `services/`.
- **Typage des statuts propre et sans casse du contrat** (`44d0e2f`) : un `SourceStatus` partagé par `source_map` et `source_bar` (le renommage silencieux relevé en 0.7.4 est désormais impossible) ; le commentaire faux `"section" | "page"` a disparu au profit d'un `OutlineNodeKind` à trois membres incluant `PREAMBLE` ; les tests épinglent des `str` sur le fil MCP.
- **Round / hop traité selon le schéma recommandé** : domaine renommé, contrat publié inchangé, traduction isolée dans `sources_mapping.py`, et documentée dans le glossaire comme dans `sources_wire.py:12`.
- **Glossaire / context map** de bonne facture : il dit quel nom le nouveau code emploie, pourquoi l'ancien reste, et quelle couche traduit.
- **Règles métier rapatriées dans le domaine** (2.4.2, 2.1.1) : localisation de citation, budget de lecture, split / merge / insertion avec refus typés (`chunk_editing.py:39-52`) traduits en erreurs de service par une seule table (`chunk_errors.py:44-57`) ; hash de chunkset unique (`hashing.py:42`) ; un seul module de sérialisation des chunks. Le docstring de `chunk_editing.py:8-14` trace la divergence des règles mortes qu'il remplace.
- **Agrégat chunkset écrit atomiquement** : retrait, ajout et journal en une transaction (`replace_chunkset`), et un restore décode son instantané avant de supprimer quoi que ce soit (`version_service.py:146-153`).
- **Ports complétés** (`39dcda5`) : `DocumentVersionRepository`, `FileStorage`, `PdfInspector`, pools ; plus aucun type `Sqlite*` ou infra dans les annotations de `services/`, garanti par un test AST.

---

## Verdict partiel : GO

Score 94 ≥ 80, 0 CRITICAL, 1 MAJOR (langage ubiquitaire, partiellement corrigé, sans risque de corruption de données). Le score progresse de +2 grâce au typage des statuts ; trois MIN sur six sont partiellement corrigés, aucun écart n'est aggravé. Pour atteindre 100 : deux renommages internes de faible effort (paramètre `document_version_id` côté versioning, « versions » au lieu de « History » dans le backend et le CHANGELOG), sans toucher au contrat MCP.

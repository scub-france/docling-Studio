# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

Référence : fiche `docs/audit/audits/02-ddd.md`, baseline `docs/audit/reports/release-0.7.0/02-ddd.md`
(aucun fichier 02 dans `release-0.7.0-reaudit/` : l'audit 02 n'avait pas été re-audité, score 100 inchangé).
Méthode : analyse statique (lecture du code, `grep`, `git diff caddf30..HEAD`), aucune exécution de l'application ni des suites de tests.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 17 |
| Score | 92 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 6 |
| Écarts INFO | 5 |

Score = (33 / 36) × 100 = 91,7 → **92**. Items non conformes : 2.3.1 (poids 2) et 2.3.3 (poids 1).

### Métriques de périmètre (0.7.2 `caddf30` → 0.7.3 `02adc68`)

| Mesure | 0.7.2 | 0.7.3 |
|--------|-------|-------|
| Modules `document-parser/domain/*.py` | 14 | 26 |
| Lignes `domain/` | 2 043 | 4 259 |
| Dataclasses `frozen=True` dans `domain/` | 25 | 53 (les 28 nouvelles sont toutes gelées) |
| Dataclasses mutables dans `domain/` | 7 (6 entités + `GraphPayload`) | 7 (inchangé) |
| `StrEnum` dans `domain/` | 8 | 9 (`CitationStatus`) |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| `domain/models.py` | 331 lignes | 331 lignes (inchangé) |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 103 | 123 |

Le domaine n'a pas changé entre 0.7.0 et 0.7.2 (diff backend vide) : la baseline 0.7.0 vaut pour 0.7.2.

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Contextes document, analysis, chunk, reasoning, versioning, config, store/ingestion (déprécié 0.8.0, inchangé), plus le nouveau contexte **navigation / citation** (MCP) : domaine `domain/anchors.py`, `navigation.py`, `parse_index.py`, `element_reader.py`, `outline_builder.py`, `outline_locate.py`, `spans.py`, `source_map.py`, `source_bar.py`, `page_regions.py`, `quote_marks.py` ; services `parse_loader`, `navigation_service`, `citation_service`, `citation_image_service`, `source_service` ; adaptateur `mcp_adapter/`. Contexte en lecture seule sur l'agrégat `AnalysisJob`. |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `domain/models.py` inchangé (331 l.) ; aucun nouveau concept n'y a été ajouté. `navigation.py` (385 l.) ne regroupe que les VO du contexte navigation. |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Contrat MCP publié séparé du domaine (`mcp_adapter/wire.py:1-17`, traduction dans `wire_mapping.py`) ; DTO HTTP `McpConfigResponse.from_view` / `McpServerResponse.from_status` (`api/schemas.py`) ; nouveaux ports `DoclingDocumentImporter` (`domain/ports.py:86-89`), `PageRasterizer`, `PageTextReader` renvoyant des VO du domaine. Dégradation : contrats en tuples et discrimination par texte de message (voir [MIN] « Contrats inter-couches »). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI | `features/mcp-config` est le miroir de `domain/mcp_config.py` + `/api/config/mcp` + `/api/mcp/server` (bornes recopiées, `frontend/src/features/mcp-config/types.ts:58-62`) ; `features/analysis` porte summaries / import / progress ; Settings compose les sections via les barrels. Le contexte navigation n'a pas de feature front : son UI est la carte MCP Apps servie par l'adaptateur, ce qui est cohérent avec son consommateur (l'hôte MCP). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI | Entités inchangées. L'import #359 rejoue le cycle de vie : `AnalysisJob.mark_running()` puis `mark_completed()` (`services/analysis_service.py:182`, `:478`) et la transition du `Document`. |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | 28/28 nouvelles dataclasses du domaine gelées, dont `DocumentAnchor` (`domain/anchors.py:54`), `BoundingBox` (`domain/navigation.py:39`), `McpRuntimeConfig` (`domain/mcp_config.py:40`). Exceptions : `GraphPayload` (carry-over, [INFO]) et `SourceHop` muté après construction ([MIN]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | Aucune méthode `save/update/delete/insert` sur un VO ; `chunk_editing.insert/update/delete` restent des fonctions pures ; les écritures ne sont que sur les ports. |
| 2.2.4 | Entités porteuses de comportement | 1 | OUI | Entités inchangées. Les nouveaux VO portent du comportement : `BoundingBox.pixel_box/page_fraction/union` (`domain/navigation.py:63-151`), `PageRegion.joins/merged` (`domain/page_regions.py:55-73`), `DocumentAnchor.parse/uri` (`domain/anchors.py:62-86`), `SourceTotals.percent`. |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | « version » désigne deux entités, « parse » en est un troisième nom, et un pas de boucle s'appelle round / hop / iteration. Voir [MAJ]. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `grep "class \w*(Manager|Handler|Processor|Helper|Util)"` sur `domain/ services/ mcp_adapter/ api/` : 0. Noms métier : `ParseLoader`, `CitationService`, `SourceService`, `DocumentAnchor`, `SourceMap`, `DocumentOutline`. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Statuts du trail (`path/read/cited/unread`), genres et modes d'outline en chaînes nues, dupliquées entre modules ; `CitationStatus` rabaissé en `str`. Voir [MIN] « Statuts et genres ». |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | Racines `Document`, `AnalysisJob`, `Store`, `DocumentVersion` inchangées ; `McpRuntimeConfig` est la racine du nouvel agrégat de config, une route par agrégat (`api/config.py`, `api/mcp.py`). |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Invariants d'entités toujours gardés (`domain/models.py:98-139`, `domain/lifecycle.py`) ; validation pure de la config MCP (`domain/mcp_config.py:107-123`) ; grammaire d'ancre validée (`domain/anchors.py:66-86`). Dégradation : règles de vérification de citation et de budget dans les services, VO de citation sans auto-validation ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | OUI | Aucune nouvelle mutation hors racine : l'import passe par `mark_*`, la config par le service et `replace_namespace` (une transaction). Les contournements `update_progress` / `update_chunks` du port (`domain/ports.py:234-236`) préexistaient et ont été acceptés en 0.7.0. |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Pas de `Row` ni de dict de ligne renvoyé. Dégradation : `AnalysisJob` partiellement hydratée par `find_all_summaries` et projections primitives (`parse_json`, `latest_parsed_ids`) ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | DTO `from_view` / `from_status` ; `ImportAnalysisRequest.document: dict` validé par l'adaptateur infra (`infra/docling_importer.py:16-29`), qui renvoie un `ConversionResult` du domaine. Le routeur MCP construit le VO comme le fait déjà celui de reasoning (`api/config.py:84`). |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | 0 import `docling` dans `domain/` et `services/` ; importeur, rasteriseur et lecteur de texte renvoient des VO du domaine. Dégradation : le schéma JSON Docling est lu dans le domaine, contre le contrat du port ([MIN]). |

---

## Écarts constatés

### [MAJ] Langage ubiquitaire : « version » est homonyme, et un même pas de boucle s'appelle round, hop ou iteration

- **Localisation** :
  - `document-parser/domain/anchors.py:7-11` vs `document-parser/domain/models.py:312`, `:328`
  - `document-parser/services/parse_loader.py:70` vs `document-parser/services/version_service.py:148` et `document-parser/api/document_versions.py:64`
  - `document-parser/services/citation_service.py:292`
  - `document-parser/domain/ports.py:226-230`
  - `document-parser/domain/source_map.py:79-80`, `:154`, `:313`
  - `document-parser/mcp_adapter/sources_view.py:341`
  - `document-parser/services/navigation_config.py:18-25`, `document-parser/domain/mcp_config.py:27-28`
  - `document-parser/domain/value_objects.py:186-188`, `:259`
  - `frontend/src/shared/types.ts:231-235`, `frontend/src/features/admin-config/store.ts:23`
- **Constat** :
  1. **Homonymie « version ».** Dans le contexte navigation / MCP, `version_id` est l'id d'un `AnalysisJob` : « Today it is the id of the analysis run » (`anchors.py:7-11`), ce que confirme le deep link `{base}/analyses/{version_id}` (`citation_service.py:292`). Cet id est publié aux agents dans chaque ancre `dstudio://doc/{document_id}@{version_id}#{ref}` et dans `DocumentRow.version_id` (`mcp_adapter/wire.py:85`). Dans le contexte versioning (#267), `DocumentVersion` (`models.py:312`) est une **autre entité**, avec son propre `id` et un champ `analysis_id` (`models.py:328`). `VersionService.restore(document_id, version_id)` (`version_service.py:148`) et la route `/{doc_id}/versions/{version_id}/restore` (`api/document_versions.py:64`) attendent un `DocumentVersion.id`. La signature est la même que `ParseLoader.load(document_id, version_id)` (`parse_loader.py:70`), mais l'entité désignée n'est pas la même. Côté front, `DocumentVersion.id` et `DocumentVersion.analysisId` sont deux champs distincts (`types.ts:231-235`) : l'`analysisId` du front est le `version_id` de l'ancre. Un troisième terme, « parse », désigne aussi l'analyse : `ParseLoader`, `LoadedParse`, et `parse_json(job_id)` / `parsed_document_id(job_id)` (`ports.py:228-230`), où « parse » et « job » apparaissent dans la même signature.
     Conséquence PLAUSIBLE (non vérifiée à l'exécution) : la « parse courante » du contexte navigation est la dernière analyse complétée (`_superseding_parse`, `citation_service.py:196-199`). Après un restore de `DocumentVersion`, l'analyse active du workspace est tenue par le front (`version_service.py:149-152`). `STALE_VERSION` peut alors désigner comme courante une parse que Studio n'affiche pas.
  2. **Trois noms pour un pas de la boucle Chunkless RAG.** `SourceHop` est documenté comme « One round: one section read » (`source_map.py:79-80`) et ses ids valent `h1, h2…` (`source_map.py:313`). Pourtant `SourceTotals.rounds` (`source_map.py:154`), `max_rounds` (`mcp_config.py:44`), le prompt et la carte (« Rounds: », `sources_view.py:341`) disent « round ». La carte HTML (`mcp_adapter/sources_app.html`) mélange les deux : 54 mots `hop` / `hops` / `hop_id` / `hopsOf` pour 16 `round` / `rounds`. Le contexte reasoning (Ask) appelle la même notion `iteration` / `reason` / `section_ref` (`value_objects.py:186-188` ; front `maxIterations`, `admin-config/store.ts:23`), alors que le MCP dit `round` / `why` / `ref`. Le code affirme pourtant qu'il s'agit de « deux runners d'une même idée » (`navigation_config.py:18-25`, `mcp_config.py:27-28`), et le panneau Settings affiche côte à côte « maxIterations » (Ask) et « Tours max » (MCP). « Citation » désigne aussi deux choses : un self_ref nu côté reasoning (`value_objects.py:259`), un VO complet (ancre, quote, hash) côté MCP (`domain/navigation.py:154-168`).
  3. La dualité `AnalysisJob` / `job`, notée [INFO] en 0.7.0, s'est étendue : 103 → 123 occurrences de `job` hors `AnalysisJob` dans `api/` + `services/` (import #359, summaries #354).
- **Règle violée** : 2.3.1 — « Le vocabulaire métier est cohérent entre domain, services, API et frontend » (poids 2).
- **Remédiation** :
  1. Renommer, côté code, le jeton d'ancre en `parse_id` (ou `analysis_id`). Le segment `@{…}` de l'URI reste opaque et inchangé pour les agents, et le contrat wire peut garder `version_id` le temps d'une dépréciation. À défaut, renommer `DocumentVersion` en `DocumentSnapshot` / `HistoryEntry`. Ajouter un glossaire (analysis = parse = jeton de version d'ancre ≠ DocumentVersion) dans `docs/`.
  2. Fixer un seul terme pour le pas de boucle (« round ») : `SourceHop` → `SourceRound`, `hop_id` → `round_id` dans le domaine. Aligner au moins les libellés Settings entre Ask et MCP.
  3. Décider dans le domaine ce qu'est la « parse courante » d'un document (dernière analyse complétée, ou analyse active du workspace).

### [MIN] Statuts et genres du contexte navigation en chaînes nues, dupliquées et non typées

- **Localisation** : `document-parser/domain/source_map.py:44-48`, `:67-75` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/services/source_service.py:186` ; `document-parser/domain/navigation.py:188`, `:247`, `:266` ; `document-parser/domain/outline_builder.py:34`, `:198` ; `document-parser/domain/outline_locate.py:38` ; `document-parser/services/navigation_service.py:92`
- **Constat** : le seul statut typé du contexte est `CitationStatus` (StrEnum, `navigation.py:20`). Les statuts du trail `path` / `read` / `cited` sont des constantes `str` dans `source_map.py:44-48`. `source_bar.py:20-22` les redéclare en littéraux (`_INHERITED = "read"`, `_UNMARKED = {None, "path"}`) : renommer `STATUS_READ` casserait `source_bar` sans erreur. `SourceCited.status` est un `str | None` documenté comme « a `CitationStatus` value » (`source_map.py:67-75`), alimenté par `check.status.value` (`source_service.py:186`). Le commentaire de type `kind: str  # "section" | "page"` (`navigation.py:247`) est faux : le builder émet une troisième valeur, `kind="preamble"` (`outline_builder.py:198`). `mode` (`"sections"` | `"pages"`) est un `str` comparé en littéral dans trois modules (`outline_locate.py:38`, `source_map.py:187`, `mcp_adapter/sources_view.py:226`). `DocumentSummary.lifecycle_state` rabaisse l'enum `DocumentLifecycleState` en `str` (`navigation.py:188`, `navigation_service.py:92`).
- **Règle violée** : 2.3.3 — statuts métier explicites (poids 1). Le vocabulaire est clair, mais pas porté par un type, contrairement à la convention StrEnum suivie partout ailleurs dans le domaine (9 StrEnum).
- **Remédiation** : `SourceStatus(StrEnum)` (UNREAD / PATH / READ / CITED) dans un module commun importé par `source_map` et `source_bar` ; `OutlineNodeKind` (SECTION / PAGE / PREAMBLE) et `OutlineMode` (SECTIONS / PAGES) ; typer `SourceCited.status: CitationStatus | None` et `DocumentSummary.lifecycle_state: DocumentLifecycleState`. La conversion en `str` reste dans `wire_mapping.py` / `sources_view.py`.

### [MIN] Le schéma JSON Docling est lu dans le domaine, contre le contrat du port `DocumentTreeReader`

- **Localisation** : `document-parser/domain/ports.py:379-387` ; `document-parser/domain/element_reader.py:85-86`, `:143`, `:148`, `:156-157`, `:172-214` ; `document-parser/domain/parse_index.py:54`, `:181`, `:201` ; `document-parser/domain/navigation.py:315`, `:319` ; `document-parser/domain/page_regions.py:42` ; `document-parser/services/source_service.py:54`, `:234-255` ; doublon `document-parser/infra/docling_tree.py:78`, `:140`, `:219`, `:243`
- **Constat** : le port affirme que « the adapter encapsulates every Docling-specific assumption (label taxonomy, parent.$ref/cref shape, …) » (`ports.py:379-387`). Or le domaine navigation lit lui-même les dicts Docling bruts stockés dans `DocumentIndex.by_ref: dict[str, dict[str, Any]]` (`parse_index.py:54`) :
  - la forme `$ref` / `cref` des enfants et des légendes (`element_reader.py:86`, `:157`), recopiée de `infra/docling_tree.py` ;
  - le payload des tableaux (`grid`, `table_cells`, `start_row_offset_idx`, `element_reader.py:172-214`) ;
  - la taxonomie des labels (`title`, `section_header`, `table`, `document_index`, `picture`, `chart`, `list_item`).

  Le « mobilier de page » (`page_header` / `page_footer`) est déclaré trois fois sous deux noms : `_EMPTY_LABELS` (`navigation.py:319`) et `_FURNITURE` (`page_regions.py:42` et `source_service.py:54`). La détection du titre du document (`_title`, `source_service.py:234-255`) applique cette taxonomie dans un service. Aucun type Docling n'est importé, donc l'item est conforme à la lettre. Mais l'anti-corruption de la parse n'est faite qu'à moitié : le domaine adopte le format Docling (relation Conformist) sans le déclarer.
- **Règle violée** : 2.5.3 — conforme à la lettre ; écart de qualité sur l'esprit (poids 3).
- **Remédiation** : soit assumer la relation Conformist (le format Docling est le langage publié de la parse) et le documenter dans `ports.py` en retirant la promesse contraire, soit étendre le port (`children_of`, `captions_of`, `table_rows`, `label_kind`) et faire construire par l'adaptateur un VO `ParsedElement`. Dans les deux cas, centraliser `FURNITURE_LABELS` dans un seul module du domaine et y déplacer `_title`.

### [MIN] Règles cœur du contexte citation dans les services ; VO de citation sans invariant auto-protégé

- **Localisation** : `document-parser/services/citation_service.py:39`, `:163-187`, `:201-277` ; `document-parser/services/navigation_service.py:231-268`, `:270-276` ; `document-parser/domain/navigation.py:154-178` ; `document-parser/domain/outline_builder.py:111`, `:138`, `:196` ; `document-parser/services/source_service.py:266-279`
- **Constat** : la promesse métier du serveur MCP, « the server, not the model, is the source of truth » (`citation_service.py:6-7`), repose sur deux règles : l'algorithme qui localise une citation (`_locate_quote` / `_locate_across` / `_trim_left`, `:201-277`, seuil `MIN_QUOTE_CHARS` `:39`) et la découpe au budget de lecture (`_pick`, `navigation_service.py:231-264`). Ce sont des fonctions pures, mais elles vivent en méthodes statiques ou privées des services. Les VO, eux, ne protègent pas leurs invariants :
  - `Citation` porte à la fois `uri` et `document_id` / `version_id` / `ref`, plus `quote_hash`, sans `__post_init__` : leur cohérence ne tient qu'au fait que `CitationService.build` est le seul constructeur (`:163-187`) ;
  - `CitationCheck` porte `valid` et `status`, redondants : rien n'empêche `valid=True, status=QUOTE_DRIFT` (`navigation.py:171-178`) ;
  - `OutlineNode` naît dans le domaine avec `uri=""`, une ancre invalide, que seul le service complète ensuite (`_stamp`, `navigation_service.py:270-276`).

  L'invariant « une réponse = une parse » (`_single_pin`, `source_service.py:266-279`) est lui aussi gardé dans le service. Aucun état invalide n'est produit aujourd'hui (une seule voie de construction, testée), d'où l'item maintenu conforme.
- **Règle violée** : 2.4.2 — conforme ; dégradation (recoupe l'audit 01, item 1.2.3).
- **Remédiation** : déplacer la localisation de citation dans `domain/` (`locate_quote(index, ref, claimed)`) et `_pick` dans `domain/navigation.py` (`pick_within_budget`) ; faire de `Citation.of(anchor, element, quote)` la fabrique unique, avec `uri` dérivée de `DocumentAnchor` ; faire de `CitationCheck.valid` une propriété dérivée du statut ; passer le jeton de version à `build_outline` pour que les nœuds naissent complets.

### [MIN] Un value object `frozen` est muté après sa construction

- **Localisation** : `document-parser/domain/source_map.py:202-203`, `:285`
- **Constat** : `SourceHop` est déclaré `frozen=True`, mais `build_source_map` ajoute des URI à `hop.cited` après sa création (`hop.cited.append(anchor.uri)`), sur l'instance même renvoyée dans `SourceMap.hops`. `_Trail.nodes` passe par référence sa liste interne `self.reached[...]` à `SourceNode.hop_ids` (`:285`), alors que `source_bar.py:59` fait une copie avec `list(...)`. La mutation reste confinée au builder, mais elle contredit la garantie annoncée par `frozen=True`, que le même module respecte ailleurs (`replace(...)`, `:310`).
- **Règle violée** : 2.2.2 — conforme (28/28 nouveaux VO gelés) ; dégradation.
- **Remédiation** : rassembler les citations par hop dans un `dict[str, list[str]]` local avant de construire les `SourceHop` (ou `replace(hop, cited=[...])`) ; typer les collections des VO en `tuple[...]` pour une immutabilité profonde.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse

- **Localisation** : `document-parser/domain/ports.py:214-216`, `:224-230` ; `document-parser/persistence/analysis_repo.py:24-35`, `:47-52`, `:78-87` ; `document-parser/api/schemas.py:145` ; `frontend/src/shared/types.ts:78`
- **Constat** : `find_all_summaries` renvoie des `AnalysisJob` sans contenu. Une analyse `COMPLETED` y a `content_markdown = None`, état que `mark_completed` ne produit jamais. `_row_to_job` tolère désormais l'absence de chaque colonne (`... if "x" in keys else None`, `analysis_repo.py:24-35`) : toute requête partielle fabrique en silence une entité trompeuse. Le concept « résumé d'analyse » existe en API (`AnalysisSummaryResponse`, `schemas.py:145`) et au front (`AnalysisSummary`, `types.ts:78`), mais pas dans le domaine. Le même port expose aussi trois projections primitives pour le contexte navigation : `latest_parsed_ids -> dict[str, str]`, `parsed_document_id -> str | None`, `parse_json -> str | None` (`ports.py:224-230`). Elles sont justifiées par la performance (commentaire `ports.py:224-225`), mais la « parse » reste sans type.
- **Règle violée** : 2.5.1 — conforme (ni `Row` ni dict de ligne renvoyé) ; dégradation.
- **Remédiation** : un VO `AnalysisSummary` dans le domaine, renvoyé par `find_all_summaries`, et un `_row_to_job` strict pour les entités complètes. Envisager un port de lecture dédié (`ParseReader` : `latest(document_ids)`, `owner(parse_id)`, `json(parse_id)`) qui isole le contexte navigation de l'agrégat `AnalysisJob`.

### [MIN] Contrats inter-couches en types primitifs et par texte de message

- **Localisation** : `document-parser/services/source_service.py:91-96` ; `document-parser/mcp_adapter/sources_view.py:177-180`, `:212-220` ; `document-parser/services/analysis_service.py:173`, `:176` ; `document-parser/api/analyses.py:83-85`
- **Constat** : le cas d'usage `SourceService.show` prend des `list[tuple[str, str, str]]` et `list[tuple[str, str]]`, alors que le domaine définit `SourceRead` et `SourceCited`. L'adaptateur convertit les dicts en tuples positionnels, si bien qu'une inversion de `why` et `found` passerait inaperçue. Pour l'import Docling (#359), le service lève `ValueError` (document absent ou invalide) et `RuntimeError` (importeur absent), et le routeur choisit entre 404 et 400 selon `str(e).startswith("Document not found:")` (`api/analyses.py:84`). La frontière repose donc sur le libellé d'un message, contrairement aux erreurs typées avec `http_status` des contextes navigation (`services/navigation_errors.py`) et config (`services/config_overrides.py`).
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** : des VO d'entrée nommés pour `show(...)` ; des erreurs typées `DocumentNotFoundError` / `InvalidDoclingDocumentError` (avec `http_status`) pour l'import.

### [INFO] `GraphPayload` toujours mutable (reconduit de 0.7.0)

- **Localisation** : `document-parser/domain/value_objects.py:284`
- **Constat** : seul VO non gelé du domaine, inchangé depuis 0.7.0 ; les 28 VO ajoutés en 0.7.3 respectent la convention. `GraphPayload` est produit par le lecteur Neo4j. S'il fait partie du périmètre Neo4j retiré en 0.8.0 (PLAUSIBLE, non vérifié), l'écart disparaîtra avec lui.
- **Règle violée** : 2.2.2 — observation.
- **Remédiation** : `frozen=True`, ou laisser partir avec le retrait Neo4j.

### [INFO] `models.py` multi-contextes et champ joint sur l'entité (reconduit de 0.7.0)

- **Localisation** : `document-parser/domain/models.py:79-96` ; `document-parser/services/analysis_service.py:180`
- **Constat** : `models.py` héberge toujours les entités de cinq contextes et `AnalysisJob.document_filename` (champ joint « not persisted separately », l. 95-96). L'import #359 reprend le même `job.document_filename = doc.filename` (`analysis_service.py:180`). En revanche, la recommandation de 0.7.0 a été suivie pour le code neuf : les nouveaux contextes ont leurs propres modules et `models.py` n'a pas grossi.
- **Règle violée** : 2.1.2 — observation.
- **Remédiation** : inchangée (découpage par contexte si le fichier grossit, champ joint dans un DTO de lecture).

### [INFO] L'import d'une analyse Docling (#359) n'existe pas dans le modèle

- **Localisation** : `document-parser/services/analysis_service.py:179-184`
- **Constat** : l'import est bien conçu (port, adaptateur, cycle de vie rejoué), mais le service enchaîne PENDING → RUNNING → COMPLETED pour simuler une conversion. Une analyse importée est indiscernable d'une analyse convertie : pas d'attribut d'origine, pas de fabrique dédiée, et `DocumentVersionKind.ANALYSIS` pour l'entrée d'historique.
- **Règle violée** : aucune (2.2.4, suggestion).
- **Remédiation** : fabrique `AnalysisJob.imported(document_id, ...)` et attribut `origin` (CONVERTED / IMPORTED) si la distinction devient utile (historique, audit).

### [INFO] La garde d'architecture n'interdit pas Docling au domaine

- **Localisation** : `document-parser/tests/test_architecture.py:297`
- **Constat** : `_DOMAIN_FORBIDDEN_EXTERNALS = {fastapi, sqlalchemy, httpx, opensearchpy}` n'interdit ni `docling` / `docling_core`, ni `mcp`, ni `pydantic`, ni `aiosqlite`, alors que la liste des services interdit `docling` (l. 300-309). La pureté actuelle est vérifiée par grep (0 import), mais aucun test ne la garantit.
- **Règle violée** : 2.5.3 — observation.
- **Remédiation** : ajouter `docling`, `docling_core`, `mcp`, `pydantic`, `aiosqlite`, `pypdfium2` à la liste du domaine.

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP

- **Localisation** : `document-parser/mcp_adapter/wire.py:27`, `:223` ; `document-parser/domain/navigation.py:20-21`
- **Constat** : `VerificationResult.status` est typé `CitationStatus`, l'enum du domaine (« the enum the wire contract publishes »). C'est un choix assumé et documenté, mais il crée une exception à la règle que `wire.py` s'impose (« Deliberately *not* the domain types », l. 3) : renommer une valeur de l'enum casse les agents connectés.
- **Règle violée** : 2.1.3 — observation.
- **Remédiation** : un `Literal` (ou une enum) propre au wire, traduit dans `wire_mapping.py`.

---

## Delta vs 0.7.0

**Score** : 100 → **92** (−8). Items conformes : 17/17 → 15/17. Écarts : 0 CRIT / 0 MAJ / 0 MIN / 3 INFO → 0 CRIT / 1 MAJ / 6 MIN / 5 INFO.

| Écart 0.7.0 | Statut en 0.7.3 |
|-------------|-----------------|
| [INFO] `GraphPayload` seul VO non immutable (`value_objects.py:284`) | **Toujours présent**, inchangé (reconduit en [INFO]). |
| [INFO] Dualité `AnalysisJob` / `job` vs « analysis » | **Toujours présent, aggravé** : 103 → 123 occurrences, et intégré à une dérive plus large du langage (homonyme « version », « parse », round / hop / iteration). C'est l'une des causes du **[MAJ] 2.3.1**. |
| [INFO] `models.py` regroupe cinq contextes ; `document_filename` sur l'entité | **Toujours présent**, inchangé (331 l.) ; les nouveaux contextes ont été placés hors de `models.py` (recommandation suivie pour le code neuf). Reconduit en [INFO]. |

Origine des points perdus : uniquement le code nouveau de 0.7.3, dans le contexte navigation / MCP (2.3.1, −2 de poids ; 2.3.3, −1 de poids). Aucune régression sur le code 0.7.0 : les entités, le cycle de vie, les repositories et l'anti-corruption existants sont intacts.

Dette MAJ reportée de 0.7.0 (9 MAJ de `release-0.7.0-reaudit/summary.md`) : aucune n'appartient à l'audit 02. Le [MIN] « Règles cœur du contexte citation dans les services » reproduit, dans le nouveau contexte, le schéma déjà relevé par l'audit 01 pour les règles split / merge de `chunk_service.py`.

---

## Points positifs

- **Les nouveaux concepts MCP sont modélisés dans `domain/`, pas en dicts dans les adaptateurs** (2.1.1, 2.2.2) : 11 modules purs (~2 200 lignes) sans framework ni I/O. L'ancre est un VO `DocumentAnchor` dont la grammaire est validée par `parse` (`domain/anchors.py:54-86`). La géométrie est un VO `BoundingBox` qui gère l'origine des coordonnées (`domain/navigation.py:39-151`). Outline, spans, source map, régions et marques de citation sont des fonctions pures sur des VO, et le budget de lecture (`read_cost`, `clip_to_tokens`) est défini dans le domaine.
- **28/28 nouvelles dataclasses du domaine sont `frozen=True`** (53 au total) ; aucune entité mutable n'a été ajoutée.
- **Anti-corruption MCP exemplaire** (2.1.3, 2.5.2) : le contrat publié est explicitement distinct du domaine (`mcp_adapter/wire.py:1-17`), la traduction est isolée (`wire_mapping.py`), le texte des documents est neutralisé, et les rejets sont des erreurs typées porteuses d'un `http_status` (`services/navigation_errors.py`).
- **Frontière du contexte navigation gardée par des tests** : liste blanche des services pairs (`tests/test_architecture.py:230-247`) ; `mcp_adapter` interdit d'importer `api` / `infra` / `persistence` (`:179-201`).
- **La config MCP suit le modèle de l'agrégat reasoning** (2.4.1, 2.4.2) : VO et validation pure dans le domaine (`domain/mcp_config.py:40-123`), précédence env / db dans le service, remplacement transactionnel des overrides, une route par agrégat (`/api/config/mcp`, `/api/mcp/server`). Le front est le miroir exact du vocabulaire (`maxRounds`, `maxReadTokens`, `studioBaseUrl`, `frontend/src/features/mcp-config/types.ts`).
- **Import Docling (#359) propre** (2.2.1, 2.5.3) : nouveau port `DoclingDocumentImporter` (`domain/ports.py:86-89`), adaptateur infra qui renvoie un `ConversionResult` du domaine, et service qui rejoue le cycle de vie de l'entité et la transition du `Document`, sans raccourci d'état.
- **Fusion des lots (#344) passée derrière un port** (`DocumentConverter.merge_batches`, `domain/ports.py:79-83`) : le domaine n'importe toujours pas Docling (`domain/services.py:23-30`).
- **« ref » cohérent du backend au frontend** : le deep link `?ref=&page=` devient `focusRef` / `page` (`frontend/src/app/router/routes.ts:46-47`). Le serveur réduit un span à son premier membre et omet les refs de page virtuelles avant de les publier (`services/citation_service.py:288-291`), si bien que le viewer ne reçoit qu'un vrai `self_ref`.
- **Contexte store / ingestion** (déprécié, retrait en 0.8.0) : inchangé et toujours conforme.

---

## Verdict partiel : GO

Score 92 ≥ 80, 0 CRITICAL, 1 MAJOR (langage ubiquitaire, sans risque de corruption de données). Le MAJ et les six MIN concernent tous le contexte navigation / MCP introduit en 0.7.3 et sont à traiter dans un cycle 0.7.x / 0.8.0.

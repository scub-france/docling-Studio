# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `release/0.7.4` @ `1de1929` (tag `v0.7.3` + 2 commits README)

Référence : fiche `docs/audit/audits/02-ddd.md`. Baseline : `docs/audit/reports/release-0.7.3/02-ddd.md` (score 92, sur `02adc68`). L'audit 02 n'a pas été re-audité dans `release-0.7.3-reaudit/` (score 92 conservé).
Méthode : analyse statique (lecture du code, `grep`, `git diff 02adc68..HEAD`), commandes de vérification de la fiche. Aucune exécution de l'application ni des suites de tests (exécutées par le coordinateur).

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

Score = (33 / 36) × 100 = 91,7 → **92**. Items non conformes : 2.3.1 (poids 2) et 2.3.3 (poids 1). Poids total 36 = 3+3+2+2 (2.1) + 2+2+3+1 (2.2) + 2+1+1 (2.3) + 2+3+2 (2.4) + 2+2+3 (2.5).

### Ce qui a changé dans le périmètre depuis le 1er audit 0.7.3 (`02adc68` → `1de1929`)

`git diff --stat 02adc68..HEAD -- document-parser frontend/src` : 13 fichiers, dont **aucun dans `document-parser/domain/`**. Seuls deux changements touchent le code du périmètre DDD :

| Changement | Fichier | Effet DDD |
|------------|---------|-----------|
| Import Docling (#359) déporté hors de l'event loop (PR #367, `d1a131f`) | `document-parser/services/analysis_service.py:177-180` | Neutre : le port `DoclingDocumentImporter` est appelé via `asyncio.to_thread`, son contrat (`deserialize(dict) -> ConversionResult`, `domain/ports.py:86-89`) est inchangé. Décale de +3 les lignes suivantes du fichier. |
| `ConfigSource` déplacé de `features/admin-config` vers `shared/types.ts` (PR #367, `8465931`) | `frontend/src/shared/types.ts:1-5`, `features/admin-config/types.ts:1`, `features/mcp-config/types.ts:1` | Positif (2.1.4) : le type commun aux deux contextes de config est dans le noyau partagé, comme côté back (`domain/app_config.py:17`, importé par `domain/mcp_config.py:25`). Décale de +6 les lignes de `shared/types.ts`. |

Les autres fichiers (`infra/settings.py`, `citation_app.html`, `i18n.ts`, `McpConfigSection.vue`, `pyproject.toml`, `uv.lock`, `Dockerfile`) ne changent que des commentaires, libellés ou dépendances, sans effet sur le modèle.

### Métriques de périmètre

| Mesure | 0.7.3 (`02adc68`) | 0.7.4 (`1de1929`) |
|--------|-------------------|-------------------|
| Modules `document-parser/domain/*.py` | 26 | 26 |
| Lignes `domain/` | 4 259 | 4 259 |
| Dataclasses `frozen=True` dans `domain/` | 53 | 53 |
| Dataclasses mutables dans `domain/` | 7 (6 entités + `GraphPayload`) | 7 (inchangé : `models.py:37`, `:78`, `:142`, `:182`, `:226`, `:311`, `value_objects.py:284`) |
| `StrEnum` dans `domain/` | 9 | 9 |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| Imports hors stdlib/`domain.*` dans `domain/` | 0 | 0 |
| `domain/models.py` | 331 lignes | 331 lignes |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 123 | 123 |
| `job` dans `frontend/src` (hors tests) | — | 2, en commentaires uniquement (`features/document/api.ts:60`, `pages/DocParseTab.vue:416`) |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Inchangé depuis 0.7.3 : document, analysis, chunk, reasoning, versioning, config, store/ingestion (déprécié), navigation/citation (MCP). Domaine navigation dans 11 modules purs (`domain/anchors.py`, `navigation.py`, `parse_index.py`, `element_reader.py`, `outline_builder.py`, `outline_locate.py`, `spans.py`, `source_map.py`, `source_bar.py`, `page_regions.py`, `quote_marks.py`). |
| 2.1.2 | Pas de god object partagé | 3 | OUI | `domain/models.py` toujours à 331 lignes, aucun nouveau concept ajouté. Voir [INFO] reconduit sur le découpage physique. |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Contrat MCP distinct du domaine (`mcp_adapter/wire.py:3`), DTO `from_view` / `from_status` (`api/schemas.py:786`, `:837`), ports renvoyant des VO. Dégradation inchangée : contrats en tuples et discrimination par texte de message (voir [MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI | `features/mcp-config` miroir de `domain/mcp_config.py` (bornes `features/mcp-config/types.ts:58-61`) ; **amélioré** : `ConfigSource` passe dans `shared/types.ts:5`, symétrique de `domain/app_config.py:17`. Imports inter-features uniquement via les barrels ; le cycle `document` ↔ `analysis` / `chunks` est suivi par l'audit 07. |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI | Entités inchangées. L'import rejoue le cycle de vie : `mark_running()` (`services/analysis_service.py:185`) puis `mark_completed()` (`:481`). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | 53 dataclasses gelées. Exceptions inchangées : `GraphPayload` ([INFO]) et `SourceHop` muté après construction ([MIN]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | Aucune méthode `save/update/delete/insert` sur un VO ; écritures uniquement via les ports (`domain/ports.py`). |
| 2.2.4 | Entités porteuses de comportement | 1 | OUI | `Document.transition_to` (`domain/models.py:49-75`), `AnalysisJob.mark_*` (`:98-139`) ; VO navigation porteurs de comportement (`BoundingBox.pixel_box/page_fraction/union`, `domain/navigation.py:63`, `:93`, `:121` ; `PageRegion.joins/merged`, `domain/page_regions.py:55`, `:66`). |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Inchangé : homonymie « version », trois noms pour l'analyse (analysis / job / parse), round / hop / iteration. Constat complété : « History » désigne aussi deux concepts au front. Voir [MAJ]. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `grep -rnE "class \w*(Manager\|Handler\|Processor\|Helper\|Util)\b"` sur `domain/ services/ mcp_adapter/ api/` : 0. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Inchangé : statuts du trail, genres et modes d'outline en chaînes nues ; `CitationStatus` rabaissé en `str` à deux endroits (un de plus relevé : `SourcePassage.status`). Voir [MIN]. |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | Racines `Document`, `AnalysisJob`, `Store`, `DocumentVersion`, `McpRuntimeConfig` (`domain/mcp_config.py:41`) inchangées. |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Machine à états `domain/lifecycle.py:26-72` + `assert_transition` ; gardes `AnalysisJob.mark_*` (`domain/models.py:98-139`) ; `validate_mcp_config` (`domain/mcp_config.py:107-123`) ; grammaire d'ancre (`domain/anchors.py:66-86`). Aucune écriture directe de `status` / `lifecycle_state` hors domaine (`grep` sur `services/ api/ mcp_adapter/ infra/` : 0) ; seule écriture SQL du cycle de vie via `update_lifecycle` après `transition_to` (`services/analysis_service.py:394-403`). Dégradation inchangée : règles de citation dans les services ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | OUI | Pas de nouvelle mutation hors racine. Les setters directs de `store_service.py:260-294` (contexte déprécié) et `chunk_service.py:296-299` préexistaient à 0.7.0 et avaient été acceptés par la baseline. |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Aucun `Row` ni dict de ligne renvoyé. Dégradation inchangée : `AnalysisJob` partiellement hydratée et projections primitives ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | DTO `from_view` / `from_status` ; `ImportAnalysisRequest.document: dict` validé par l'adaptateur (`infra/docling_importer.py:16-29`), qui renvoie un `ConversionResult` du domaine. |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | 0 import `docling` dans `domain/` et `services/`. Dégradation inchangée : le schéma JSON Docling est lu dans le domaine ([MIN]). Les imports `pypdfium2` / `pdf2image` dans `services/document_service.py:14-15` et `services/analysis_service.py:17` sont des concrétions hors port, suivies par les audits 01 et 06 (pas de type infra exposé aux services au sens de l'item). |

Calcul : items conformes = 2.1.1 (3) + 2.1.2 (3) + 2.1.3 (2) + 2.1.4 (2) + 2.2.1 (2) + 2.2.2 (2) + 2.2.3 (3) + 2.2.4 (1) + 2.3.2 (1) + 2.4.1 (2) + 2.4.2 (3) + 2.4.3 (2) + 2.5.1 (2) + 2.5.2 (2) + 2.5.3 (3) = **33** ; non conformes = 2.3.1 (2) + 2.3.3 (1) = 3. Score = 33 / 36 = **92**.

---

## Écarts constatés

### [MAJ] Langage ubiquitaire : « version » et « History » sont homonymes, un même pas de boucle s'appelle round, hop ou iteration

**Statut vs 0.7.3 : inchangé** (code identique). Constat complété par une homonymie « History » côté front, antérieure (présente dès `v0.6.1`) et non relevée jusqu'ici.

- **Localisation** :
  - `document-parser/domain/anchors.py:7-11` vs `document-parser/domain/models.py:311-331` (`DocumentVersion`, `analysis_id` à `:328`)
  - `document-parser/services/parse_loader.py:70` vs `document-parser/services/version_service.py:148` et `document-parser/api/document_versions.py:64`
  - `document-parser/services/citation_service.py:292`
  - `document-parser/domain/ports.py:224-230`
  - `document-parser/domain/source_map.py:79-80`, `:153`, `:313`
  - `document-parser/mcp_adapter/sources_view.py:341`
  - `document-parser/services/navigation_config.py:18-24`, `document-parser/domain/mcp_config.py:27-28`
  - `document-parser/domain/value_objects.py:186-188`, `:259`
  - `frontend/src/shared/types.ts:237-245`, `frontend/src/features/admin-config/store.ts:23`
  - (nouveau) `frontend/src/features/history/api.ts:4-9`, `frontend/src/pages/HistoryPage.vue:4` vs `frontend/src/features/document/ui/HistoryDrawer.vue:12`, `:16`, `:41` ; `frontend/src/features/document/api.ts:76` ; `frontend/src/shared/i18n.ts:261`, `:291`, `:989`, `:1019`
- **Constat** :
  1. **Homonymie « version »** (inchangée). Dans le contexte navigation / MCP, `version_id` est l'id d'un `AnalysisJob` (« Today it is the id of the analysis run », `anchors.py:7-8`), ce que confirme le deep link `{base}/analyses/{version_id}` (`citation_service.py:292`) ; il est publié aux agents dans chaque ancre et dans `DocumentRow.version_id` (`mcp_adapter/wire.py:85`). Dans le contexte versioning, `DocumentVersion` (`models.py:312`) est une autre entité, avec son propre `id` et un champ `analysis_id` (`:328`). `VersionService.restore(document_id, version_id)` (`version_service.py:148`) et la route `/{doc_id}/versions/{version_id}/restore` (`document_versions.py:64`) attendent un `DocumentVersion.id`, avec la même signature que `ParseLoader.load(document_id, version_id)` (`parse_loader.py:70`), qui attend un id d'analyse. Côté front, `DocumentVersion.id` et `DocumentVersion.analysisId` sont distincts (`types.ts:237-245`). Troisième nom de l'analyse : « parse » (`ParseLoader`, `LoadedParse`, `parse_json(job_id)` / `parsed_document_id(job_id)`, `ports.py:228-230`), où « parse » et « job » cohabitent dans la même signature.
     Conséquence PLAUSIBLE (non vérifiée à l'exécution, inchangée) : la « parse courante » du contexte navigation est la dernière analyse complétée (`_superseding_parse`, `citation_service.py:196-199`), alors qu'après un restore de `DocumentVersion` l'analyse active est tenue par le front (`version_service.py:149-152`).
  2. **Trois noms pour un pas de la boucle Chunkless RAG** (inchangé). `SourceHop` est « One round: one section read » (`source_map.py:80`), ids `h1, h2…` (`:313`), mais `SourceTotals.rounds` (`:153`), `max_rounds` (`mcp_config.py:44`) et la carte (« Rounds: », `sources_view.py:341`) disent « round ». `mcp_adapter/sources_app.html` : 54 occurrences `hop*` pour 16 `round(s)` (recompté). Le contexte reasoning dit `iteration` / `reason` / `section_ref` (`value_objects.py:186-188` ; front `maxIterations`, `admin-config/store.ts:23`), alors que le code affirme qu'il s'agit des « two runners of one idea » (`navigation_config.py:21`, `mcp_config.py:27-28`). « Citation » désigne un self_ref nu côté reasoning (`value_objects.py:259`) et un VO complet côté MCP (`domain/navigation.py:154-168`).
  3. **Homonymie « History »** (complément, antérieur à 0.7.3). La page `/history` (`HistoryPage.vue:4`, titre `history.title`) liste des **analyses** : `fetchHistory()` appelle `/api/analyses` et `deleteHistoryEntry(id)` supprime une analyse (`features/history/api.ts:4-9`). Le tiroir `HistoryDrawer.vue` porte le **même titre** `history.title` (`:12`, `:16`) mais liste des **`DocumentVersion`** (`/api/documents/{id}/versions`, `features/document/api.ts:76`), et y affiche une version de type `analysis` sous le libellé « OCR » (`history.kind.analysis`, `i18n.ts:291`, `:1019`) : un quatrième nom de l'analyse côté UI. Le domaine nomme le même objet « History drawer » (`models.py:321`) et « workspace History timeline » (`analysis_service.py:490`).
  4. Dualité `AnalysisJob` / `job` : stable à 123 occurrences dans `api/` + `services/`. Le front, lui, est cohérent (« analysis » partout, 2 `job` en commentaires).
- **Règle violée** : 2.3.1 — « Le vocabulaire métier est cohérent entre domain, services, API et frontend » (poids 2).
- **Remédiation** (inchangée, complétée) :
  1. Publier un glossaire / context map dans `docs/` (analysis = run = parse = jeton `@version` d'ancre ≠ `DocumentVersion` ; « History » = historique des versions d'un document ≠ liste des analyses).
  2. Renommer côté code le jeton d'ancre en `parse_id` (ou `analysis_id`) dans `domain/` et `services/`, en gardant `version_id` sur le fil MCP (`wire.py`) le temps d'une dépréciation ; à défaut, renommer `DocumentVersion` en `DocumentSnapshot`.
  3. Un seul terme pour le pas de boucle : `SourceHop` → `SourceRound`, `hop_id` → `round_id` dans le domaine, la carte gardant ses champs `hop_id` / `hops` (`sources_view.py:63-143`) tant que le contrat n'est pas versionné.
  4. Front : donner au tiroir un titre propre (« Versions ») et remplacer « OCR » par « Analyse » ; renommer `fetchHistory` / `deleteHistoryEntry` en `fetchAnalyses` / `deleteAnalysis`.

### [MIN] Statuts et genres du contexte navigation en chaînes nues, dupliquées et non typées

**Statut vs 0.7.3 : inchangé** (une localisation supplémentaire relevée : `SourcePassage.status`).

- **Localisation** : `document-parser/domain/source_map.py:44-48`, `:64-75`, `:116` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/services/source_service.py:186` ; `document-parser/domain/navigation.py:188`, `:247`, `:266` ; `document-parser/domain/outline_builder.py:57`, `:68`, `:198` ; `document-parser/domain/outline_locate.py:38` ; `document-parser/mcp_adapter/sources_view.py:226` ; `document-parser/services/navigation_service.py:92`
- **Constat** : seul `CitationStatus` est typé (StrEnum, `navigation.py:20`). Les statuts du trail `path` / `read` / `cited` sont des constantes `str` (`source_map.py:44-46`), redéclarées en littéraux dans `source_bar.py:20-22` (`_INHERITED = "read"`, `_UNMARKED = {None, "path"}`) : renommer `STATUS_READ` casserait `source_bar` sans erreur. `SourceCited.status` (`source_map.py:75`) et `SourcePassage.status` (`:116`, non relevé en 0.7.3) sont des `str | None` alors qu'ils portent une valeur `CitationStatus`, alimentée par `check.status.value` (`source_service.py:186`). Le commentaire `kind: str  # "section" | "page"` (`navigation.py:247`) est faux : le builder émet `kind="preamble"` (`outline_builder.py:198`). `mode` (`"sections"` | `"pages"`, `navigation.py:266`) est comparé en littéral dans trois modules (`outline_locate.py:38`, `source_map.py:187`, `sources_view.py:226`). `DocumentSummary.lifecycle_state: str` (`navigation.py:188`) rabaisse l'enum `DocumentLifecycleState` (`navigation_service.py:92`).
- **Règle violée** : 2.3.3 — statuts métier explicites (poids 1) ; contraire à la convention StrEnum suivie ailleurs (9 StrEnum dans le domaine).
- **Remédiation** : `SourceStatus(StrEnum)` (UNREAD / PATH / READ / CITED) dans un module commun importé par `source_map` et `source_bar` ; `OutlineNodeKind` (SECTION / PAGE / PREAMBLE) et `OutlineMode` (SECTIONS / PAGES) ; typer `SourceCited.status`, `SourcePassage.status` en `CitationStatus | None` et `DocumentSummary.lifecycle_state` en `DocumentLifecycleState`. Un `StrEnum` reste égal à sa chaîne : la sérialisation et les tests existants (`tests/test_source_map.py:14-16`, comparaisons à `STATUS_*`) ne changent pas.

### [MIN] Le schéma JSON Docling est lu dans le domaine, contre le contrat du port `DocumentTreeReader`

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/domain/ports.py:378-387` ; `document-parser/domain/element_reader.py:86`, `:157`, `:195-210` ; `document-parser/domain/parse_index.py:54`, `:84-98` ; `document-parser/domain/navigation.py:319` ; `document-parser/domain/page_regions.py:42`, `:88` ; `document-parser/services/source_service.py:54`, `:234-255`
- **Constat** : le port promet que « the adapter encapsulates every Docling-specific assumption (label taxonomy, parent.$ref/cref shape, …) » (`ports.py:384-386`). Le domaine lit pourtant lui-même les dicts Docling bruts de `DocumentIndex.by_ref: dict[str, dict[str, Any]]` (`parse_index.py:54`) : forme `$ref` / `cref` (`element_reader.py:86`, `:157`), payload des tableaux (`grid`, `table_cells`, `start_row_offset_idx`, `:195-210`), taxonomie des labels. Le mobilier de page (`page_header` / `page_footer`) est déclaré trois fois sous deux noms : `_EMPTY_LABELS` (`navigation.py:319`), `_FURNITURE` (`page_regions.py:42`, `source_service.py:54`). `_title` (`source_service.py:234`) applique cette taxonomie dans un service. Aucun type Docling importé : l'item est conforme à la lettre, mais la relation Conformist n'est pas déclarée.
- **Règle violée** : 2.5.3 — conforme ; écart de qualité sur l'esprit (poids 3).
- **Remédiation** : assumer la relation Conformist dans la docstring du port (en retirant la promesse contraire), ou étendre le port (`children_of`, `captions_of`, `table_rows`, `label_kind`) ; dans les deux cas, un seul `FURNITURE_LABELS` dans le domaine et `_title` déplacé dans `domain/`.

### [MIN] Règles cœur du contexte citation dans les services ; VO de citation sans invariant auto-protégé

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/services/citation_service.py:39`, `:163-187`, `:201-277` ; `document-parser/services/navigation_service.py:231-268`, `:270-276` ; `document-parser/domain/navigation.py:154-178` ; `document-parser/domain/outline_builder.py:111`, `:138`, `:196` ; `document-parser/services/source_service.py:266-279`
- **Constat** : la localisation d'une citation (`_locate_quote` / `_locate_across` / `_trim_left`, `citation_service.py:202`, `:230`, `:261`, seuil `MIN_QUOTE_CHARS` `:39`) et la découpe au budget (`_pick`, `navigation_service.py:231`) sont des fonctions pures logées dans les services. `Citation` (`navigation.py:155-168`) porte `uri` et `document_id` / `version_id` / `ref` sans `__post_init__` (0 dans le module) ; `CitationCheck` porte `valid` et `status` redondants (`:171-178`) ; `OutlineNode` naît avec `uri=""` (`outline_builder.py:111`, `:138`, `:196`), complété par `_stamp` (`navigation_service.py:270`). L'invariant « une réponse = une parse » est gardé dans le service (`_single_pin`, `source_service.py:266`). Aucun état invalide produit aujourd'hui (une seule voie de construction), d'où l'item maintenu conforme.
- **Règle violée** : 2.4.2 — conforme ; dégradation (recoupe l'audit 01).
- **Remédiation** : `locate_quote(...)` et `pick_within_budget(...)` dans `domain/` ; fabrique unique `Citation.of(anchor, element, quote)` ; `CitationCheck.valid` en propriété dérivée du statut ; jeton de version passé à `build_outline`.

### [MIN] Un value object `frozen` est muté après sa construction

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/domain/source_map.py:202-203`, `:285`
- **Constat** : `SourceHop` est `frozen=True` (`:78-79`), mais `build_source_map` ajoute des URI à `hop.cited` après sa création (`hop.cited.append(anchor.uri)`, `:203`). `_Trail.nodes` passe la liste interne `self.reached[...]` par référence à `SourceNode.hop_ids` (`:285`), alors que `source_bar.py:59` en fait une copie (`list(...)`). Le même module utilise `replace(...)` ailleurs (`:310`).
- **Règle violée** : 2.2.2 — conforme ; dégradation.
- **Remédiation** : construire les `SourceHop` après avoir rassemblé les citations (ou `replace(hop, cited=[...])`) ; collections des VO en `tuple[...]`.

### [MIN] `AnalysisJob` partiellement hydratée et projections primitives sur le port d'analyse

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/domain/ports.py:214-216`, `:224-230` ; `document-parser/persistence/analysis_repo.py:18-36`, `:47-52`, `:78-86` ; `document-parser/api/schemas.py:145` ; `frontend/src/shared/types.ts:84-96`
- **Constat** : `find_all_summaries` renvoie des `AnalysisJob` sans contenu : une analyse `COMPLETED` y a `content_markdown = None`, état que `mark_completed` ne produit jamais. `_row_to_job` tolère l'absence de chaque colonne de contenu (`... if "x" in keys else None`, `analysis_repo.py:24-31`), si bien que toute requête partielle fabrique en silence une entité trompeuse. Le concept « résumé d'analyse » existe en API (`AnalysisSummaryResponse`, `schemas.py:145`) et au front (`AnalysisSummary`, `types.ts:84`), pas dans le domaine. Le port expose aussi `latest_parsed_ids -> dict[str, str]`, `parsed_document_id -> str | None`, `parse_json -> str | None` (`ports.py:226-230`).
- **Règle violée** : 2.5.1 — conforme (ni `Row` ni dict de ligne renvoyé) ; dégradation.
- **Remédiation** : VO `AnalysisSummary` dans le domaine renvoyé par `find_all_summaries`, `_row_to_job` strict ; port de lecture `ParseReader` dédié au contexte navigation.

### [MIN] Contrats inter-couches en types primitifs et par texte de message

**Statut vs 0.7.3 : inchangé** (le passage en `asyncio.to_thread` ne change pas les exceptions propagées).

- **Localisation** : `document-parser/services/source_service.py:91-96` ; `document-parser/mcp_adapter/sources_view.py:177-180`, `:212-220` ; `document-parser/services/analysis_service.py:173`, `:176` ; `document-parser/api/analyses.py:83-85` ; `document-parser/infra/docling_importer.py:28-29`
- **Constat** : `SourceService.show` prend des `list[tuple[str, str, str]]` / `list[tuple[str, str]]` (`source_service.py:91-96`) alors que le domaine définit `SourceRead` et `SourceCited` ; l'adaptateur convertit les dicts en tuples positionnels (`sources_view.py:177-180`, `:212-220`). Pour l'import Docling, le service lève `ValueError` (document absent, `analysis_service.py:173` ; document invalide, relevé par l'adaptateur `docling_importer.py:29`) ou `RuntimeError` (`:176`), et le routeur choisit 404 / 400 sur `str(e).startswith("Document not found:")` (`api/analyses.py:84`).
- **Règle violée** : 2.1.3 — conforme ; dégradation.
- **Remédiation** : VO d'entrée nommés pour `show(...)` ; erreurs typées `DocumentNotFoundError` / `InvalidDoclingDocumentError` avec `http_status`, comme `services/navigation_errors.py`.

### [INFO] `GraphPayload` toujours mutable

**Statut vs 0.7.3 : inchangé** (reconduit depuis 0.7.0).

- **Localisation** : `document-parser/domain/value_objects.py:284`
- **Constat** : seul VO non gelé du domaine. Il est construit à deux endroits (`infra/neo4j/queries.py:168`, `:255`) et jamais muté ensuite (`grep` des affectations / `append` sur ses champs dans `infra/`, `services/`, `api/` : 0). `frozen=True` est donc sans effet de bord.
- **Règle violée** : 2.2.2 — observation.
- **Remédiation** : `@dataclass(frozen=True)`, ou laisser partir avec le retrait Neo4j (0.8.0).

### [INFO] `models.py` multi-contextes et champ joint sur l'entité

**Statut vs 0.7.3 : inchangé** (reconduit depuis 0.7.0).

- **Localisation** : `document-parser/domain/models.py:78-96` ; `document-parser/services/analysis_service.py:148`, `:183`
- **Constat** : `models.py` héberge les entités de cinq contextes ; `AnalysisJob.document_filename` est un champ joint « not persisted separately » (`:95-96`), renseigné à la main par le service (`analysis_service.py:148`, `:183`).
- **Règle violée** : 2.1.2 — observation.
- **Remédiation** : découpage par contexte si le fichier grossit ; champ joint dans un DTO de lecture.

### [INFO] L'import d'une analyse Docling (#359) n'existe pas dans le modèle

**Statut vs 0.7.3 : inchangé** (lignes décalées de +3).

- **Localisation** : `document-parser/services/analysis_service.py:182-187`
- **Constat** : le service enchaîne PENDING → RUNNING → COMPLETED pour simuler une conversion ; une analyse importée est indiscernable d'une analyse convertie (pas d'attribut d'origine, `DocumentVersionKind.ANALYSIS` pour l'historique).
- **Règle violée** : aucune (2.2.4, suggestion).
- **Remédiation** : fabrique `AnalysisJob.imported(...)` et attribut `origin` (CONVERTED / IMPORTED) si la distinction devient utile.

### [INFO] La garde d'architecture n'interdit pas Docling au domaine

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/tests/test_architecture.py:297`
- **Constat** : `_DOMAIN_FORBIDDEN_EXTERNALS = {"fastapi", "sqlalchemy", "httpx", "opensearchpy"}` n'interdit ni `docling` / `docling_core`, ni `mcp`, `pydantic`, `aiosqlite`, `pypdfium2`, alors que la liste des services interdit `docling` (`:300-309`). La pureté actuelle est vérifiée par inventaire (le domaine n'importe que la stdlib et `domain.*`), mais aucun test ne la garantit.
- **Règle violée** : 2.5.3 — observation.
- **Remédiation** : ajouter ces paquets à `_DOMAIN_FORBIDDEN_EXTERNALS` (aucun import existant à migrer).

### [INFO] Une enum du domaine est publiée telle quelle dans le contrat MCP

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/mcp_adapter/wire.py:27`, `:223` ; `document-parser/domain/navigation.py:20`
- **Constat** : `VerificationResult.status` est typé `CitationStatus`, exception assumée à la règle « Deliberately *not* the domain types » (`wire.py:3`) : renommer une valeur casse les agents connectés.
- **Règle violée** : 2.1.3 — observation.
- **Remédiation** : un `Literal` propre au wire, traduit dans `wire_mapping.py`.

---

## Delta vs 0.7.3

**Score** : 92 → **92** (=). Items conformes : 15/17 → 15/17. Écarts : 0 CRIT / 1 MAJ / 6 MIN / 5 INFO → 0 CRIT / 1 MAJ / 6 MIN / 5 INFO.

| Écart 0.7.3 | Statut 0.7.4 | Commentaire |
|-------------|--------------|-------------|
| [MAJ] 2.3.1 Langage ubiquitaire (version / parse / round-hop-iteration) | **Inchangé** | Code identique ; constat complété par l'homonymie « History » (antérieure, non relevée). |
| [MIN] 2.3.3 Statuts en chaînes nues | **Inchangé** | `SourcePassage.status` ajouté aux localisations. |
| [MIN] 2.5.3 Schéma Docling lu dans le domaine | **Inchangé** | — |
| [MIN] 2.4.2 Règles de citation dans les services | **Inchangé** | — |
| [MIN] 2.2.2 `SourceHop` muté | **Inchangé** | — |
| [MIN] 2.5.1 Hydratation partielle / projections primitives | **Inchangé** | — |
| [MIN] 2.1.3 Tuples / discrimination par message | **Inchangé** | `to_thread` sans effet sur le contrat d'erreur. |
| [INFO] `GraphPayload` mutable | **Inchangé** | Vérifié sans mutation post-construction. |
| [INFO] `models.py` multi-contextes | **Inchangé** | — |
| [INFO] Import sans origine | **Inchangé** | — |
| [INFO] Garde d'architecture domaine | **Inchangé** | — |
| [INFO] `CitationStatus` publié sur le fil | **Inchangé** | — |

Aucun écart corrigé ni aggravé : la remédiation 0.7.3 (PR #367, #368) visait les audits 07, 08, 10, 11 et 12 et ne touche pas `domain/`. Aucun nouvel écart introduit par le code ; un constat antérieur a été complété.

---

## Pistes de remédiation à faible risque (gain de score)

| Action | Item | Gain | Effort | Risque |
|--------|------|------|--------|--------|
| `SourceStatus`, `OutlineNodeKind`, `OutlineMode` en StrEnum ; `SourceCited.status` / `SourcePassage.status` en `CitationStatus \| None` ; `DocumentSummary.lifecycle_state` en `DocumentLifecycleState` | 2.3.3 (poids 1) | 33→34/36 : **92 → 94** (+2) | S | Faible : un `StrEnum` est égal à sa chaîne, sérialisation inchangée |
| Glossaire / context map + renommages internes (`SourceHop` → `SourceRound`, jeton d'ancre → `parse_id` dans domaine/services, fil MCP inchangé) + titre du tiroir « Versions » et libellé « Analyse » au lieu de « OCR » | 2.3.1 (poids 2) | seul : **92 → 97** (+5) ; avec 2.3.3 : **100** (+8) | M | Modéré (nombreux tests du contexte navigation) ; élevé seulement si l'on renomme `version_id` sur le fil MCP (breaking pour les agents) |
| `GraphPayload` `frozen=True` ; `_DOMAIN_FORBIDDEN_EXTERNALS` complété | INFO 2.2.2 / 2.5.3 | 0 point (−2 INFO) | S | Nul |
| Construire `SourceHop` après collecte des citations | MIN 2.2.2 | 0 point (−1 MIN) | S | Faible |
| Erreurs typées pour l'import Docling | MIN 2.1.3 | 0 point (−1 MIN, partiel) | S | Faible (le routeur et 2 tests à adapter) |

---

## Points positifs

- **Domaine strictement pur** (2.2.3, 2.5.3) : inventaire des imports de `domain/*.py` = stdlib (`typing`, `dataclasses`, `enum`, `re`, `uuid`, `hashlib`, `urllib.parse`, `unicodedata`, `datetime`, `json`, `collections.abc`) + `domain.*` uniquement ; 0 import `docling` dans `domain/` et `services/`.
- **Immutabilité des VO** (2.2.2) : 53 dataclasses `frozen=True` ; seules les 6 entités et `GraphPayload` restent mutables.
- **Cycle de vie protégé dans l'agrégat** (2.4.2) : aucune affectation directe de `status` / `lifecycle_state` hors domaine ; l'unique écriture SQL du cycle de vie suit `Document.transition_to` (`services/analysis_service.py:394-403`) et une transition refusée est absorbée explicitement au lieu de produire un état invalide (`:395-401`).
- **La remédiation 0.7.3 respecte le modèle** : l'import passe hors event loop sans court-circuiter le port (`services/analysis_service.py:180`), avec un test dédié (`tests/test_analysis_service.py`, `test_import_deserializes_off_the_event_loop`) ; `ConfigSource` rejoint le noyau partagé front (`shared/types.ts:5`), symétrique du back (`domain/app_config.py:17`).
- **Front aligné sur le vocabulaire « analysis »** : hors tests, `job` n'apparaît que dans 2 commentaires ; `AnalysisStatus` (`shared/types.ts:63`) et `DocumentLifecycleState` (`:18-24`) sont des miroirs exacts des enums backend.
- **Anti-corruption MCP** (2.1.3, 2.5.2) : contrat publié distinct du domaine (`mcp_adapter/wire.py:3`), traduction isolée (`wire_mapping.py`), erreurs typées avec `http_status` (`services/navigation_errors.py`), frontière du contexte navigation gardée par des tests (`tests/test_architecture.py:178`, liste blanche des pairs `:231-247`).
- **Config MCP modélisée comme l'agrégat reasoning** (2.4.1, 2.4.2) : VO et validation pure dans le domaine (`domain/mcp_config.py:41`, `:107-123`), bornes recopiées au front (`features/mcp-config/types.ts:58-61`).

---

## Verdict partiel : GO

Score 92 ≥ 80, 0 CRITICAL, 1 MAJOR (langage ubiquitaire, sans risque de corruption de données). Aucun écart corrigé ni aggravé depuis 0.7.3 : le domaine est identique octet pour octet. Le MAJ et les six MIN restent de la dette du contexte navigation / MCP, à planifier pour 0.8.0 ; le typage des statuts (2.3.3) est le gain le moins risqué (+2).

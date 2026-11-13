# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code

> **Score 67 / 100 — inchange vs 0.7.3 (67).** Les trois MAJ de 0.7.3 sont toujours
> ouverts et tous trois aggraves a la marge (`_parse_iso` x8, fallbacks de couleur
> divergents dans l'editeur, 7e famille d'erreurs avec son propre mapping HTTP). L'editeur
> d'analyse ajoute une **troisieme implementation** de la conversion
> `DoclingDocument → pages`, dont le vocabulaire de types diverge des deux autres et qui
> alimente desormais l'espace document : nouveau MAJ. Avec 4 MAJ, l'audit depasse le seuil
> bloquant du master (> 3).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 4 |
| Ecarts MINOR | 15 |
| Ecarts INFO | 6 |

| # | Item | Poids | Conforme | Evolution vs 0.7.3 |
|---|------|-------|----------|--------------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | **Non** | Aggrave : `_parse_iso` x8, conversion Docling → pages x3 (divergente), pile de titres x4, repetitions internes de l'editeur |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui | Types de l'editeur feature-scoped (`domain/analysis_editing.py`, `features/analysis-editor/types.ts`), `Analysis`/`Page` repris de `shared/types.ts` |
| 5.3 | Pas de magic numbers/strings eparpilles — constantes nommees et centralisees | 2 | **Non** | Aggrave : +10 replis de couleur en dur, `792.0`/`612.0` a cote de `DEFAULT_PAGE_*`, `{"text","paragraph"}` x4 |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui | Inchange (garde « modifications non enregistrees » en 2 copies, sous le seuil) |
| 5.5 | Appels API sans duplication de config HTTP — `shared/api/http.ts` | 2 | Oui | `analysis-editor/api.ts` passe par `apiFetch` ; aucun nouveau `fetch()` brut |
| 5.6 | Schemas Pydantic transforment le domain, ne le redefinissent pas | 2 | Oui | Nouveaux DTO de l'editeur en transformation (`_history_entry`, `_response`) |
| 5.7 | Regles de validation a un seul endroit (pas de desaccord front/back) | 1 | Oui | Regles de fusion et niveaux de titre ecrits des deux cotes mais **en accord** (cf. INFO) |

Poids total de la checklist : 12. Poids conformes : 8 (items 5.1 et 5.3, poids 2 chacun,
restent non conformes). `score = 8 / 12 * 100 = 66,7 → 67`.
**Delta vs 0.7.3 : 0 point** (67 → 67).

### Compteurs de duplication

Methode : analyse statique (grep, `git grep`, lecture), aucun detecteur de duplication lance.
Base 0.7.3 remesuree sur `git archive 1de1929`.

| Compteur | 0.7.3 (`1de1929`) | 0.7.4 (`eade7fa`) |
|----------|-------------------|-------------------|
| Definitions `_parse_iso` / `_parse_dt` / `_dt` dans `persistence/` (+ parse inline) | 7 (+1) | **8** (+1) |
| References `var(--color-*)` (namespace jamais defini) | 33 | 33 |
| Litteraux `#d1d5db` / `#6b7280` / `#dc2626` | 7 / 12 / 11 | 7 / 12 / 11 |
| Replis `var(--warning, #…)` | 3 | **7** |
| Replis hex en dur pour des tokens lus par `getComputedStyle` (canvas) | 0 | **6** |
| Bases `XServiceError` avec `__init__(message, *, http_status=None)` identique | 6 | 6 (+ famille `AnalysisEditError` sans `http_status`) |
| Sites `HTTPException(status_code=<err>.http_status, …)` dans `api/` | 16 | 16 (+ `_raise` a codes en dur, relaye par 6 `try/except`) |
| Implementations `DoclingDocument → list[PageDetail]` | 2 | **3** |
| Algorithme « pile de titres » (`while stack and stack[-1][0] >= level`) cote backend | 3 | **4** |
| Construction de `?analysisId=` dans le front | 2 | **9** |
| `Query(default=None, alias="analysisId")` dans `api/` | 2 | **8** |
| Parse booleen `.lower() in ("1","true","yes","on")` dans `infra/settings.py` | 8 | **9** |
| SFC definissant `@keyframes spin` | 17 | 17 |

---

## Ecarts constates

### [MAJ] Helper de parsing ISO-datetime copie-colle dans 8 repositories (reconduit, aggrave)

- **Localisation** : `document-parser/persistence/analysis_repo.py:11`, `document-parser/persistence/document_repo.py:12` (+ parse inline `:29`), `document-parser/persistence/chunk_repo.py:14`, `document-parser/persistence/chunk_push_repo.py:12` (ex-`chunk_edit_repo.py`), `document-parser/persistence/document_store_link_repo.py:12`, `document-parser/persistence/document_version_repo.py:13`, `document-parser/persistence/store_repo.py:29`, **nouveau** `document-parser/persistence/analysis_edit_repo.py:19` (`_dt`)
- **Constat** : aucune des 7 copies n'a ete factorisee ; le nouveau repository de l'editeur en ecrit une 8e sous un troisieme nom (`_dt`), variante non optionnelle avec coercition UTC. La divergence de `analysis_repo._parse_dt` (`:11-15`, sans coercition UTC) persiste alors que `analysis_repo.py` a encore ete modifie en 0.7.4 (`update_status`, `:175`).
- **Regle violee** : item 5.1 — bloc quasi-identique present bien plus de 3 fois (poids 2).
- **Remediation** : inchangee — `parse_iso(value: str | datetime | None) -> datetime | None` (UTC par defaut) dans `persistence/_datetime.py`, consomme par les 8 `_row_to_*` et le parse inline de `document_repo`. Effort S.

### [MAJ] Couleurs UI en dur et tokens non definis ou contournes (reconduit, aggrave par l'editeur)

- **Localisation** : sites 0.7.3 inchanges (`frontend/src/features/store/ui/StoreForm.vue:389` …, `Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue`, `GraphView.vue:576`, `IngestLaunchDialog.vue`, `AppBreadcrumb.vue`, `ComingSoonShell.vue`, `ReasoningConfigSection.vue`, `DocumentUpload.vue:174`, `McpConfigSection.vue:662`, `:1040`, `:1046`) ; **nouveau** : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:540`, `:571`, `:591`, `:592` (`var(--warning, #d97706)`), `frontend/src/features/document/ui/BboxCanvas.vue:156`, `:172`, `:173`, `:174`, `:175` (replis `'#22c55e'`, `'#f97316'`, `'#1a1a1d'`, `'#ececef'`, `'#3f3f46'`), `:194` (`'#18181b'` en dur)
- **Constat** : les compteurs 0.7.3 n'ont pas bouge (33 `--color-*`, 7/12/11 litteraux). L'editeur reproduit le meme anti-pattern sous deux formes :
  - `var(--warning, #d97706)` : le repli `#d97706` n'est ni la valeur sombre (`#eab308`, `app/App.vue:98`) ni la valeur claire (`#ca8a04`, `App.vue:129`) du token ;
  - `BboxCanvas.vue` lit les tokens par `getComputedStyle` et recopie en repli les **valeurs du theme sombre** de `App.vue:82-96` ; en theme clair, un echec de lecture afficherait des pastilles sombres. Le texte des pastilles selectionnees est `'#18181b'` en dur (c'est le `--text` du theme clair, `App.vue:120`) : c'est le token `--on-accent` demande en 0.7.3, toujours absent.
- **Regle violee** : item 5.3 — « Pas de magic numbers ou magic strings eparpilles — les constantes sont nommees et centralisees » (poids 2).
- **Remediation** : inchangee pour l'existant (`var(--border)` / `--text-muted` / `--accent` / `--error`, suppression des replis). Pour l'editeur : `var(--warning)` sans repli ; ajouter `--on-accent` (clair + sombre) dans `App.vue` ; dans `BboxCanvas.vue`, un helper `readToken(canvas, name)` sans repli en dur (les tokens sont toujours definis sur `:root`). Effort S pour l'editeur, M pour l'ensemble.

### [MAJ] Contrat d'erreur service → HTTP recopie : 7e famille, mapping a codes en dur (reconduit, aggrave)

- **Localisation** : bases 0.7.3 inchangees (`services/store_service.py:34`, `graph_service.py:25`, `chunk_service.py:65-72`, `version_service.py:69`, `reasoning_service.py:27`, `navigation_errors.py:13`) et 16 sites de mapping ; **nouveau** : `document-parser/domain/analysis_editing.py:107-116` (`AnalysisEditError(ValueError)` et deux sous-classes, sans `http_status`), `document-parser/api/analysis_edits.py:110-117` (`_raise`, codes 409/409/400 en dur), relaye par six blocs identiques `try: … except Exception as exc: _raise(exc)` (`:126-129`, `:139-142`, `:154-159`, `:170-181`, `:191-205`, `:214-217`) ; traductions paralleles de la meme erreur : `document-parser/services/chunk_service.py:379-380` (→ `ChunkServiceError(http_status=409)`), `document-parser/services/export_service.py:124-125` (→ `ExportNotFoundError`, servi en 404 par `api/documents.py:151-152`)
- **Constat** : au lieu de reutiliser la base « erreur avec indice HTTP » deja recopiee six fois, l'editeur cree une 7e famille, sans indice, et deplace le choix du code HTTP dans le routeur. Consequence de l'absence de contrat unique : la **meme** `AnalysisEditUnavailableError` (« This document has no active analysis ») est servie en 409 par l'editeur, en 409 via `ChunkServiceError` par les chunks, et en 404 via `ExportNotFoundError` par l'export ; et `_require_document` (`analysis_edit_service.py:274`) leve « Document not found » en `AnalysisEditUnavailableError`, donc en **409** au lieu de 404.
- **Regle violee** : item 5.1 — bloc identique 6 fois (bases) et 16 + 6 fois (mapping) sans factorisation (poids 2).
- **Remediation** : inchangee dans son principe — une base `ServiceError` (`http_status` + constructeur) dans `services/errors.py` et un seul `@app.exception_handler(ServiceError)`. Pour l'editeur : faire heriter `AnalysisEditError` de cette base avec `http_status=400` / `409` sur les sous-classes, ajouter `AnalysisDocumentNotFoundError(404)`, supprimer `_raise` et les six `try/except`. Effort M (S pour le seul editeur).

### [MAJ] Conversion `DoclingDocument → pages` ecrite trois fois, avec un vocabulaire de types divergent (nouveau)

- **Localisation** : `document-parser/infra/docling_pages.py:28-38` (`_ELEMENT_TYPE_MAP`, par classe : `ListItem → "list"`, legende → `"text"`), `:48-65` (`extract_pages_detail`, `iterate_items()` par defaut), `:89-92` (repli `DEFAULT_PAGE_WIDTH/HEIGHT`) ; `document-parser/infra/serve_converter.py:269` (`_extract_pages_from_docling_document`, sur dict brut) ; **nouveau** `document-parser/infra/docling_projector.py:170-203` (`_pages` : type = label brut via `_label` `:101-103`, donc `"list_item"`, `"paragraph"`, `"caption"`, `"page_header"`…, `iterate_items(with_groups=True, traverse_pictures=True)` `:43`, repli `PageDetail(page_no, 612.0, 792.0)` `:192`, `level` = niveau de titre `:199`) et `:273-289` (`_page_dict`, reecriture de `dataclasses.asdict` utilise par `services/analysis_service.py:467`) ; consommateurs : `frontend/src/features/document/store.ts:25-35` (`fetchWorkspaceAnalysis` remplace `pagesJson` par celui du projecteur des que le flag editeur est actif — par defaut, `infra/settings.py:126` — et que l'analyse a un `document_json`), `frontend/src/shared/types.ts:153-163` (`ElementType` : `'list'`, pas `'list_item'` ni `'paragraph'`), `frontend/src/shared/elementColors.ts:14-34` (`colorFor` → gris « inconnu » hors palette)
- **Constat** : #359 avait factorise la conversion dans `docling_pages.py` (« Shared Docling-to-page mapping for conversion and imported analyses »), en laissant une seconde copie dans `serve_converter.py` (INFO 0.7.3). Le projecteur de l'editeur en ecrit une **troisieme**, avec d'autres choix : type issu du label Docling au lieu de la table par classe, parcours incluant groupes et contenu des images, autre semantique de `level`, constantes de page en dur. Pour un **meme document non edite**, le `pagesJson` de l'analyse (conversion) et celui de l'espace document (projection) different donc ; deduit statiquement (non execute) : les elements de liste passent de `list` (couleur cyan, filtre « list » de la barre des calques) a `list_item` (gris « inconnu », hors `ElementType`), les legendes de `text` a `caption`, et des textes internes aux images apparaissent comme boites supplementaires.
- **Regle violee** : item 5.1 — logique quasi-identique 3 fois sans factorisation, avec derive deja effective (poids 2).
- **Remediation** : faire appeler `extract_pages_detail(document)` par le projecteur (le document edite est un `DoclingDocument` valide) et serialiser par `asdict` comme `analysis_service.py:467` ; si les types plus fins du projecteur sont voulus, les introduire **dans** `_ELEMENT_TYPE_MAP` et dans `ElementType`/`ELEMENT_COLORS` en une fois. Faire de meme pour `serve_converter.py` (`DoclingDocument.model_validate(json_content)` puis `extract_pages_detail`). Effort S a M. Corriger ce seul ecart ramene l'audit a 3 MAJ.

### [MIN] Repetitions internes du service et de l'API de l'editeur (nouveau)

- **Localisation** : `document-parser/services/analysis_edit_service.py:76-79`, `:115-118`, `:126-129`, `:249-252` (meme bloc de 4 lignes : document → base → flux → commandes) ; `stored[-1].sequence if stored else 0` x8 (`:80`, `:132`, `:166`, `:218`, `:254`, `:362`, `:368`, `document-parser/domain/analysis_editing.py:125`) ; controle de sequence x3 avec deux libelles differents (`analysis_edit_service.py:166-170`, `:218-222`, `document-parser/persistence/analysis_edit_repo.py:158-163`) ; construction du cache a 10 champs x2 (`analysis_edit_service.py:176-187`, `:256-267`) ; `Query(default=None, alias="analysisId")` x6 (`document-parser/api/analysis_edits.py:124`, `:137`, `:152`, `:168`, `:189`, `:212`)
- **Constat** : le service a ete ecrit methode par methode sans extraire ses invariants. Le controle de sequence optimiste est fait deux fois par le service avant d'etre refait (seule version qui compte) dans la transaction du repository.
- **Regle violee** : item 5.1, ampleur limitee a deux fichiers.
- **Remediation** : `_load_stream(document_id, analysis_id) -> (document, base, stream, stored)`, `_last_sequence(stored)` (ou propriete sur une liste typee), `_check_sequence(actual, expected)`, `_cache_from(base, projection, sequence, stream_hash)` ; un alias `AnalysisIdQuery = Annotated[str | None, Query(alias="analysisId")]` dans `api/deps.py`. Effort S.

### [MIN] Formule de hash des commandes ecrite deux fois, dans deux couches (nouveau)

- **Localisation** : `document-parser/services/analysis_edit_service.py:366` et `:374-378` (`_command_hash`) ; `document-parser/persistence/analysis_edit_repo.py:168` et `:215-219` (`_hash_command`)
- **Constat** : la serialisation canonique du payload (`json.dumps(sort_keys=True, separators=(",", ":"))`) et la formule `sha256(f"{previous}|{sequence}|{type}|{version}|{payload}")` existent en deux copies. Le repository fait foi a l'ecriture, le service recalcule la meme chaine pour predire `command_stream_hash` du cache. Si l'une change sans l'autre, aucun test de type ne le voit : tous les caches sont juges perimes et l'editeur rejoue silencieusement a chaque chargement.
- **Regle violee** : item 5.1 (deux copies seulement, mais dont la synchronisation conditionne la validite du cache).
- **Remediation** : une fonction pure `command_hash(previous, sequence, command)` dans `domain/analysis_editing.py`, importee par le service et le repository. Effort S.

### [MIN] Algorithme de pile de titres recopie quatre fois cote backend (nouveau pour la 4e copie)

- **Localisation** : `document-parser/domain/outline_builder.py:94`, `document-parser/domain/parse_index.py:102`, `document-parser/services/chunk_service.py:843-852`, **nouveau** `document-parser/infra/docling_projector.py:224-242` ; equivalent front `frontend/src/features/analysis/sectionParenting.ts:31`
- **Constat** : chaque vue (plan MCP, `heading_path`, arbre de document, arbre de l'editeur) refait « depiler tant que le niveau du sommet est >= au niveau courant, rattacher au sommet ». Les quatre variantes different sur la racine sentinelle (`len(stack) > 1` contre `stack`) et sur ce qui compte comme titre (`HEADING_LABELS` en `domain/navigation.py:315`, litteral `{"title", "section_header"}` en `chunk_service.py:843`, `isinstance(SectionHeaderItem) or label == "title"` en `docling_projector.py:231`).
- **Regle violee** : item 5.1 (4 copies, logique courte).
- **Remediation** : un generateur pur `nest_by_heading(items, level_of, is_heading)` dans `domain/`, reutilise par les quatre ; `HEADING_LABELS` comme seule definition des titres.

### [MIN] Mapping `AnalysisJob → AnalysisResponse` recopie et appel d'API duplique entre features (nouveau)

- **Localisation** : `document-parser/api/analysis_edits.py:30-47` (`_analysis`) copie verbatim de `document-parser/api/analyses.py:25-42` (`_to_response`) ; `frontend/src/features/document/api.ts:20-28` (`fetchDocumentEditedAnalysisResult`) contre `frontend/src/features/analysis-editor/api.ts:9-18` (`fetchAnalysisEditor`, meme endpoint) ; construction de `?analysisId=` x9 (`analysis-editor/api.ts:14`, `:26`, `:38`, `:49`, `:62`, `:76`, `document/api.ts:24`, `:74`, `:90`)
- **Constat** : 17 lignes de mapping identiques dans deux routeurs (s'ajoute a la redeclaration `AnalysisSummaryResponse` relevee en 0.7.3) ; la feature `document` rappelle l'endpoint de l'editeur par son propre client au lieu de passer par le barrel `@/features/analysis-editor`, et telecharge tout le modele d'editeur pour n'en garder que `result`.
- **Regle violee** : item 5.1 (deux copies du mapping, neuf de la query).
- **Remediation** : `AnalysisResponse.from_job(job)` (classmethod dans `api/schemas.py`) utilise par les deux routeurs ; exporter `fetchAnalysisEditor` depuis `@/features/analysis-editor` ; helper `withAnalysisId(path, analysisId)` dans `shared/api/`.

### [MIN] Magic numbers et strings de l'editeur (nouveau)

- **Localisation** : `document-parser/infra/docling_projector.py:132`, `:192` (`792.0`, `612.0` alors que `DEFAULT_PAGE_WIDTH/HEIGHT` existent `domain/value_objects.py:14-15`) ; ensemble `{"text", "paragraph"}` ecrit 4 fois (`document-parser/infra/docling_editor.py:220`, `document-parser/infra/docling_projector.py:143`, `frontend/src/features/analysis-editor/commands.ts:78`, `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:354`) alors que `docling_projector.py:19-28` declare un `_TEXT_LABELS` jamais utilise et que le serveur publie deja `supportedOperations` ; bornes de niveau `-1`/`6` (`docling_editor.py:176`, `ElementEditPanel.vue:29-31`) ; delais `400` ms (`analysis-editor/store.ts:108`), `4000` ms (`AnalysisEditor.vue:428`), seuil `1000` elements (`AnalysisEditor.vue:490`) ; codes 409/400 en dur (`api/analysis_edits.py:112-116`)
- **Regle violee** : item 5.3 (deja non conforme), non bloquant.
- **Remediation** : reutiliser `DEFAULT_PAGE_*` ; `MERGEABLE_LABELS` cote backend et, cote front, `isMergeable = supportedOperations.includes('mergeText')` (comme `isMovable`, `AnalysisEditor.vue:356-357`) ; `MIN_HEADING_LEVEL`/`MAX_HEADING_LEVEL` exposes ; constantes nommees en tete du store et du SFC.

### [MIN] Pont JSON-RPC MCP Apps recopie dans les deux cartes HTML (reconduit, inchange)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:690-800`, `document-parser/mcp_adapter/sources_app.html:984-1188`
- **Remediation** : inchangee (`mcp_adapter/app_bridge.js` injecte au chargement).

### [MIN] Import d'une analyse Docling recopie dans trois composants (reconduit, inchange)

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:40-57`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:67-85`, `frontend/src/features/document/ui/DocumentUpload.vue:105-123`
- **Remediation** : inchangee (`useAnalysisImport()`).

### [MIN] Defauts, bornes et parsing d'env des budgets MCP / Ask non centralises (reconduit, +1 parse booleen)

- **Localisation** : sites 0.7.3 inchanges ; parse booleen en ligne : `document-parser/infra/settings.py` 9 occurrences (+ `ANALYSIS_EDITOR_ENABLED`, `:279-280`) contre `document-parser/services/config_overrides.py:21`
- **Remediation** : inchangee (`_env_bool(name, default)`).

### [MIN] Vocabulaire des labels Docling recopie (reconduit, etendu)

- **Localisation** : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` (`{"page_header","page_footer"}` x3) ; `document-parser/domain/navigation.py:315` vs `document-parser/services/chunk_service.py:843` ; **nouveau** : `document-parser/infra/docling_projector.py:101-103` (`_label`, troisieme facon de normaliser un label apres `label_of` et le `.lower() or "text"` de `chunk_service`), `frontend/src/features/analysis-editor/ui/EditableStructureNode.vue:170-172` (`'title' || 'section_header'`)
- **Remediation** : inchangee (`FURNITURE_LABELS`, `HEADING_LABELS`, `label_of` exposes et importes partout).

### [MIN] Bloc de style `.field-*` des formulaires de store (reconduit, inchange)

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue:78-108`, `OpenSearchConfigForm.vue:61-91`, `StoreForm.vue:383-405`
- **Remediation** : aucune (perimetre retire en 0.8.0).

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO et value objects (reconduit, inchange)

- **Localisation** : `document-parser/api/schemas.py` (`PipelineOptionsRequest`, `ChunkingOptionsRequest`, decales par les DTO de l'editeur), `document-parser/domain/value_objects.py`, `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`
- **Remediation** : inchangee.

### [MIN] Primitives CSS recopiees : spinner, boutons primaires, interrupteurs (reconduit)

- **Localisation** : `@keyframes spin` dans 17 SFC (inchange) ; boutons primaires et interrupteurs comme en 0.7.3
- **Remediation** : inchangee (`shared/ui/AppSpinner.vue`, `AppButton.vue`, `AppSwitch.vue`).

### [MIN] Palette de la vue graphe Neo4j recopiee trois fois (reconduit, perimetre deprecie)

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue:134-147`, `NodeDetailsPanel.vue:113-132`, `features/analysis/legendFilters.ts:34-77`
- **Remediation** : inchangee (suppression en 0.8.0).

### [MIN] `api/analyses.py` : mapping de chunks x3 et resume d'analyse redeclare (reconduit)

- **Localisation** : `document-parser/api/analyses.py:149`, `:173`, `:196` ; `document-parser/api/schemas.py` (`AnalysisSummaryResponse` vs `AnalysisResponse`)
- **Remediation** : inchangee ; le `from_job` propose plus haut couvre aussi `_to_response`.

### [MIN] Helpers `_utcnow` / `_new_id` recopies, deux formats d'identifiant (reconduit)

- **Localisation** : `document-parser/domain/models.py:28-34`, `document-parser/domain/chunk_editing.py:29-34`, `document-parser/services/chunk_service.py:95-100`, `document-parser/services/version_service.py:43-48` ; nouveau site en ligne : `document-parser/persistence/analysis_edit_repo.py:176-177` (`uuid.uuid4().hex`, `datetime.now(UTC)`)
- **Remediation** : inchangee (`new_id()` / `utcnow()` publics dans `domain/models.py`).

---

### [INFO] Validation de l'editeur ecrite des deux cotes, en accord (5.7 juge conforme)

- **Localisation** : fusion : `frontend/src/features/analysis-editor/commands.ts:71-82` vs `document-parser/infra/docling_editor.py:210-221` ; niveaux de titre : `frontend/src/features/analysis-editor/ui/ElementEditPanel.vue:29-31` vs `document-parser/infra/docling_editor.py:174-177` ; placement : `document-parser/api/schemas.py` (`Literal["before","after","inside"]`) vs `docling_editor.py:271`
- **Constat** : les regles concordent aujourd'hui ; le front pre-valide pour l'UX, le backend fait foi. Le serveur publie deja `supportedOperations` par element, ce qui permettrait au front de ne plus recopier la regle de fusion.
- **Remediation** : deriver `canMerge` de `supportedOperations` (voir MIN magic strings).

### [INFO] Contrat du modele d'editeur ecrit a la main, hors Pydantic (5.6 juge conforme)

- **Localisation** : `document-parser/infra/docling_projector.py:257-271` (`_element_dict`, cles camelCase ecrites a la main), `document-parser/api/analysis_edits.py:50-56` (`_tree`), `document-parser/api/schemas.py` (`AnalysisEditorResponse.model: dict`, `tree: list[dict]`) ; miroir front `frontend/src/features/analysis-editor/types.ts:22-46`
- **Constat** : il n'y a pas de redefinition du domaine par un schema, mais l'inverse : le contrat publie n'a pas de schema (OpenAPI dit `dict`), et les cles camelCase sont produites dans l'adaptateur infra alors que `_CamelModel` le fait ailleurs. Un champ ajoute a `EditorElement` doit etre reporte a la main a trois endroits.
- **Remediation** : `EditorElementResponse(_CamelModel)` / `EditorTreeNodeResponse` avec `from_domain`, et un modele persiste en objet plutot qu'en JSON pre-serialise.

### [INFO] Formatage de dates : helper partage toujours ignore (reconduit et etendu)

- **Localisation** : `frontend/src/shared/format.ts:26` (`formatAbsolute`, 0 appelant) ; `frontend/src/pages/AnalysisDetailPage.vue:92-96` et `frontend/src/pages/AnalysisLibraryPage.vue:159` (copies exactes) ; nouveau : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:388-392` (variante `dateStyle: 'short'`)
- **Constat** : trois implementations identiques et une variante d'un helper partage existant. Sous l'angle 5.4 / 5.1, petite duplication.
- **Remediation** : `formatAbsolute(iso, style = 'medium')` et suppression des copies.

### [INFO] Parse de `pagesJson` recopie dans le front

- **Localisation** : `frontend/src/features/analysis-editor/types.ts:82-89` (`pagesFromAnalysis`), `frontend/src/features/analysis/store.ts:39`, `frontend/src/features/analysis/ui/InspectResultTabs.vue:65`
- **Remediation** : exporter `pagesFromAnalysis` depuis `shared/` et l'utiliser partout.

### [INFO] Garde « modifications non enregistrees » en deux copies

- **Localisation** : `frontend/src/features/analysis-editor/ui/AnalysisEditor.vue:466-468` (`confirmLeave`), `frontend/src/pages/AnalysisDetailPage.vue:87-90` (`closeEditor`)
- **Remediation** : exposer `confirmLeave()` depuis le store ou un composable `useUnsavedGuard(store)`.

### [INFO] `fetch()` brut dans DownloadDropdown (reconduit, inchange)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:135`
- **Constat** : toujours le seul `fetch()` hors `shared/api/http.ts`, justifie (`blob()` + `content-disposition`). 5.5 reste conforme.

---

## Delta vs 0.7.3

Base : `release/0.7.3` @ `02adc68` (score 67, 3 MAJ / 10 MIN / 5 INFO).

| Ecart 0.7.3 | Niveau | Statut en 0.7.4 | Verification |
|-------------|--------|-----------------|--------------|
| `_parse_iso` x7 + divergence UTC `analysis_repo` | MAJ | **Toujours ouvert, aggrave** | 8 definitions (+ `analysis_edit_repo._dt`) ; `analysis_repo.py:11-15` toujours sans UTC |
| Couleurs UI en dur, tokens `--color-*` inexistants | MAJ | **Toujours ouvert, aggrave** | compteurs inchanges ; +4 `var(--warning, #d97706)`, +6 replis hex dans `BboxCanvas.vue` ; `--on-accent` toujours absent |
| Contrat d'erreur service → HTTP (6 bases, 16 sites) | MAJ | **Toujours ouvert, aggrave** | 7e famille `AnalysisEditError` sans `http_status`, `_raise` a codes en dur, 6 `try/except` ; meme erreur servie en 409 ou 404 selon la route |
| Pont MCP Apps en double | MIN | Toujours ouvert, inchange | `mcp_adapter/` intact |
| Import d'analyse x3 | MIN | Toujours ouvert, inchange | |
| Defauts MCP/Ask, parse booleen | MIN | Toujours ouvert | parse booleen 8 → 9 |
| Labels Docling recopies | MIN | Toujours ouvert, etendu | + `_label` du projecteur, + test de titre dans `EditableStructureNode.vue` |
| `.field-*` formulaires de store | MIN | Toujours ouvert, inchange | |
| Bornes de chunking / defauts DTO | MIN | Toujours ouvert, inchange | |
| Primitives CSS | MIN | Toujours ouvert, inchange | 17 spinners |
| Palette graphe Neo4j x3 | MIN | Toujours ouvert, inchange | |
| `api/analyses.py` mapping x3 / resume | MIN | Toujours ouvert, etendu | `_to_response` recopie dans `api/analysis_edits.py:30` |
| `_utcnow` / `_new_id` x4 | MIN | Toujours ouvert | + site en ligne dans `analysis_edit_repo.py` |
| `fetch()` brut DownloadDropdown | INFO | Inchange | ligne 133 → 135 |
| Constantes de troncature | INFO | Inchange | integre au suivi, non re-detaille |
| Config MCP vs Ask | INFO | Inchange | integre au suivi, non re-detaille |
| DTO MCP en miroir du domain | INFO | Inchange | integre au suivi, non re-detaille |
| Deux extractions Docling → pages | INFO | **Promu MAJ** | troisieme copie divergente ajoutee par l'editeur |

**Nouveaux ecarts 0.7.4** : 1 MAJ (conversion Docling → pages x3 divergente), 5 MIN
(repetitions internes de l'editeur, formule de hash x2, pile de titres x4, mapping
`AnalysisResponse` / appel d'API inter-features, magic numbers/strings de l'editeur),
5 INFO (validation front/back en accord, contrat du modele hors Pydantic, formatage de
dates, parse de `pagesJson`, garde de sortie).

**Score : 67 → 67 (delta 0).** Les items 5.1 et 5.3 etaient deja non conformes ; aucun
autre item ne bascule. Le nombre de MAJ passe de 3 a 4.

---

## Points positifs

- **Client HTTP toujours centralise** : `features/analysis-editor/api.ts` passe integralement par `apiFetch` ; aucun nouveau `fetch()` brut.
- **Types derives, pas redeclares** : le front de l'editeur reprend `Analysis` et `Page` de `shared/types.ts` ; l'union `AnalysisEditCommand` (`types.ts:8-20`) est la seule definition front des commandes ; le backend a une seule `CommandType` (`domain/analysis_editing.py:13-21`), le CHECK SQL (`database.py:246-248`) en est le miroir documente.
- **Logique de file factorisee et testee** : `commands.ts` (`coalesceCommands`, `inReadingOrder`, `mergeValidationMessage`) est l'unique implementation, consommee par le store et couverte par `commands.test.ts`.
- **Reutilisation du viewer et du repere** : l'editeur reutilise `PagePreviewWithOverlay` / `BboxCanvas` et `infra/bbox.to_topleft_list` au lieu de reecrire un canvas et une conversion de coordonnees.
- **Une seule resolution de l'analyse active** : `AnalysisEditService.active_result` est le point unique utilise par l'editeur, le rechunk (`chunk_service.py:376-385`) et l'export (`export_service.py:121-125`).
- **Fusion des lots par l'outil Docling** : `infra/docling_merger.py` (40 l.) delegue a `DoclingDocument.concatenate`.
- **Suppression de doublons morts** : retrait de `ChunkEdit` / `ChunkEditAction` / `chunk_edits`, qui doublaient l'historique de versions sans etre lus.

---

## Verdict partiel : NO-GO

Aucun ecart CRITICAL (la checklist DRY n'a pas d'item de poids 3). Score **67 / 100**,
dans la tranche GO CONDITIONNEL (60-79), identique a 0.7.3. Mais **4 ecarts MAJOR non
resolus**, soit au-dela du seuil bloquant du master (§2 : « Bloquant si > 3 ecarts MAJOR
non resolus ») : verdict **NO-GO** en application stricte.

Le chemin le plus court vers GO CONDITIONNEL est de corriger le nouveau MAJ (conversion
Docling → pages : le projecteur appelle `extract_pages_detail`, effort S a M), ce qui
ramene l'audit a 3 MAJ. Les trois MAJ reconduits restent mecaniques (helper `parse_iso`,
tokens CSS + `--on-accent`, base `ServiceError` + handler FastAPI) et doivent etre planifies
explicitement : ils sont reportes depuis 0.7.0 (deux d'entre eux) et 0.7.3.

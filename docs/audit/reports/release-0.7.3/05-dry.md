# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

> **Score 67 / 100 — inchange vs re-audit 0.7.0 (67).** Les deux MAJ portes en dette
> depuis 0.7.0 (`_parse_iso` x7, couleurs UI non tokenisees) sont toujours ouverts, a
> l'identique. Le serveur MCP n'introduit aucune duplication bloquante (budgets
> centralises, regles d'override factorisees, cablage HTTP/stdio partage), mais ajoute
> une 6e copie d'un contrat d'erreur deja recopie 5 fois, desormais remonte en MAJ.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 10 |
| Ecarts INFO | 5 |

| # | Item | Poids | Conforme | Evolution vs re-audit 0.7.0 |
|---|------|-------|----------|-----------------------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | **Non** | Toujours tenu en echec par `_parse_iso` x7 ; s'y ajoutent le contrat d'erreur service x6 (+1 en 0.7.3) et l'import d'analyse x3 (nouveau, #359) |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui | Inchange — `AnalysisSummary` derive par `Pick<Analysis>` ; types MCP feature-scoped |
| 5.3 | Pas de magic numbers/strings eparpilles — constantes nommees et centralisees | 2 | **Non** | Couleurs UI en dur toujours presentes (+3 litteraux dans `McpConfigSection.vue`) ; defauts MCP/Ask et labels Docling recopies |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui | Inchange (aucun composable mal place ; les duplications reactives sont traitees en 5.1) |
| 5.5 | Appels API sans duplication de config HTTP — `shared/api/http.ts` | 2 | Oui | Inchange — `mcp-config/api.ts` passe par `apiFetch` |
| 5.6 | Schemas Pydantic transforment le domain, ne le redefinissent pas | 2 | Oui | Inchange — schemas MCP en `from_view` / `from_status` |
| 5.7 | Regles de validation a un seul endroit (pas de desaccord front/back) | 1 | Oui | Inchange — bornes MCP alignees front/back, validation ecrite cote domain uniquement |

Poids total de la checklist : 12. Poids conformes : 8 (les items 5.1 et 5.3, poids 2
chacun, restent non conformes). `score = 8 / 12 * 100 = 66,7 → 67`.
**Delta vs re-audit 0.7.0 : 0 point** (67 → 67).

### Compteurs de duplication

Methode : aucun detecteur de duplication n'est installe (ni `jscpd` dans
`frontend/node_modules`, ni `pylint`/`symilar` dans `.venv`). Analyse statique par un
script jetable de fenetres glissantes (6 lignes normalisees, hors blancs, commentaires et
imports) sur `document-parser/` (hors `.venv`, `tests`, `migrations`) et `frontend/src/`
(hors `*.test.*`), complete par `difflib` sur les paires suspectes et par `git grep` sur
les refs `94eec28` (re-audit 0.7.0) et `caddf30` (0.7.2).

| Compteur | 0.7.0 (`94eec28`) | 0.7.3 (`02adc68`) |
|----------|-------------------|-------------------|
| Definitions `_parse_iso` / `_parse_dt` dans `persistence/` (+ parse inline) | 7 (+1) | 7 (+1) |
| References `var(--color-*)` (namespace jamais defini) | 33 | 33 |
| Litteraux `#d1d5db` / `#6b7280` / `#dc2626` (casse exacte) | 7 / 12 / 11 | 7 / 12 / 11 |
| Usages `var(--error)` | 32 | 42 |
| Bases `XServiceError` avec `__init__(message, *, http_status=None)` identique | 5 | **6** |
| Sites de mapping `HTTPException(status_code=<err>.http_status, …)` dans `api/` | 14 | **16** |
| SFC definissant `.spinner` + `@keyframes spin` | 16 | 17 |
| Parse booleen `.lower() in ("1","true","yes","on")` dans `infra/settings.py` | 5 | 8 |
| Ensemble `{"page_header","page_footer"}` redeclare | 0 | 3 |

---

## Ecarts constates

### [MAJ] Helper de parsing ISO-datetime copie-colle dans 7 repositories (non resolu, inchange)

- **Localisation** : `document-parser/persistence/analysis_repo.py:11`, `document-parser/persistence/document_repo.py:12` (+ parse inline `:27-31`), `document-parser/persistence/chunk_repo.py:14`, `document-parser/persistence/chunk_edit_repo.py:13`, `document-parser/persistence/document_store_link_repo.py:12`, `document-parser/persistence/document_version_repo.py:13`, `document-parser/persistence/store_repo.py:29`
- **Constat** : les 7 definitions relevees en 0.7.0 sont toujours la, aucune n'a ete factorisee. Quatre sont strictement identiques (garde `None`/`""`, `datetime.fromisoformat`, coercition `tzinfo`→UTC), `document_version_repo` en garde une variante non optionnelle, `store_repo` une variante `str | datetime`. `document_repo._row_to_document` (`:27-31`) refait meme le parse a la main sur `created_at` alors que le helper du fichier est 15 lignes plus haut. La divergence de `analysis_repo._parse_dt` (`:11-15`, pas de coercition UTC) persiste. Aggravant : `analysis_repo.py` a ete retouche en 0.7.3 (`find_all_summaries` pour #354, `latest_parsed_ids` / `parse_json` pour le MCP) sans converger, et la nouvelle route `GET /api/analyses/summaries` reutilise `_row_to_job`, donc herite de la divergence. Celle-ci reste latente : les ecritures font `str()` de datetimes UTC aware (`analysis_repo.py:64`, `:195`), seule une ligne ecrite naive la declencherait.
- **Regle violee** : item 5.1 — bloc quasi-identique present bien plus de 3 fois sans factorisation (poids 2).
- **Remediation** : un unique `parse_iso(value: str | datetime | None) -> datetime | None` (UTC par defaut) dans `persistence/database.py` ou `persistence/_datetime.py`, consomme par tous les `_row_to_*`, y compris le parse inline de `document_repo` ; aligner `analysis_repo` sur la coercition UTC.

### [MAJ] Couleurs UI en dur et tokens `--color-*` non definis, eparpilles (non resolu, +3 litteraux en 0.7.3)

- **Localisation** : `frontend/src/features/store/ui/StoreForm.vue:389` `:394` `:401` `:405` `:414` `:454` `:475` `:487` `:503`, `frontend/src/features/store/ui/Neo4jConfigForm.vue:94` `:99` `:103` `:107`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:77` `:82` `:86` `:90`, `frontend/src/features/analysis/ui/GraphView.vue:576`, `frontend/src/pages/IngestLaunchDialog.vue:327` `:345` `:357` ; meme anti-pattern hors du perimetre cite en 0.7.0 : `frontend/src/shared/breadcrumb/AppBreadcrumb.vue:43` `:44` `:66` `:90`, `frontend/src/shared/ui/ComingSoonShell.vue:46` `:73` `:80`, `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:329` `:348` `:369`, `frontend/src/features/document/ui/DocumentUpload.vue:174` ; nouveau en 0.7.3 : `frontend/src/features/mcp-config/ui/McpConfigSection.vue:662` `:1040` `:1046`
- **Constat** : les compteurs sont identiques a 0.7.0 (33 references au namespace inexistant `--color-*`, `#d1d5db` x7, `#6b7280` x12, `#dc2626` x11), les formulaires de store n'ont pas ete touches depuis 0.7.2. Le namespace fantome produit des replis divergents pour un meme token : `--color-text-muted` retombe sur `#6b7280` (`StoreForm.vue:401`) ou `#9ca3af` (`AppBreadcrumb.vue:43`), `--color-border` sur `#d1d5db`, `#e5e7eb` (`ComingSoonShell.vue:46`) ou `#1a1a1d` (`AppBreadcrumb.vue:44`). `ReasoningConfigSection.vue` consomme un `--danger` qui n'existe pas (le systeme definit `--error`, `App.vue:97` / `:128`), et `DocumentUpload.vue:174` replie `var(--error, #e53e3e)` sur un rouge different du token. La 0.7.3 ajoute dans la nouvelle section MCP un bouton dont le texte est `#0a0a0b` en dur (`McpConfigSection.vue:1040`, `:1046`) et un curseur `#ffffff` (`:662`), quand les autres boutons sur accent ecrivent `white` (`DocsLibraryPage.vue:655`, `DocsNewPage.vue:379`). Correction du re-audit 0.7.0 : `--error` n'etait pas « consomme nulle part » (32 usages `var(--error)` a `94eec28`, 42 aujourd'hui) ; le token est bien adopte, ce sont les sites residuels qui posent probleme.
- **Regle violee** : item 5.3 — « Pas de magic numbers ou magic strings eparpilles — les constantes sont nommees et centralisees » (poids 2).
- **Remediation** : remplacer `var(--color-border, …)` / `var(--color-text-muted, …)` / `var(--color-primary, …)` par `var(--border)` / `var(--text-muted)` / `var(--accent)`, `var(--danger, …)` par `var(--error)`, le litteral `#dc2626` par `var(--error)` ; ajouter un token `--on-accent` (texte sur fond accent) dans `App.vue` (clair + sombre) et le consommer dans `McpConfigSection` et les `.btn-primary`. Aucun repli en dur ne doit subsister. Les fichiers `store/ui/*` et `IngestLaunchDialog.vue` relevent de l'ingestion depreciee (retiree en 0.8.0) : leur suppression levera une partie des occurrences.

### [MAJ] Contrat d'erreur service → HTTP recopie : base d'erreur x6 et mapping x16

- **Localisation** : bases — `document-parser/services/store_service.py:34`, `document-parser/services/graph_service.py:25`, `document-parser/services/chunk_service.py:60`, `document-parser/services/version_service.py:69`, `document-parser/services/reasoning_service.py:27`, `document-parser/services/navigation_errors.py:13` (nouveau en 0.7.3) ; mapping — `document-parser/api/config.py:51` `:60` `:71` `:93` `:102`, `document-parser/api/stores.py:105` `:114` `:139` `:162` `:172` `:184` `:197`, `document-parser/api/graph.py:70`, `document-parser/api/reasoning.py:37`, `document-parser/api/document_chunks.py:61`, `document-parser/api/document_versions.py:47`
- **Constat** : chaque service redeclare la meme classe de base « erreur avec indice HTTP » : un attribut de classe `http_status` et un `__init__(self, message, *, http_status=None)` dont le corps (`super().__init__(message)` puis surcharge conditionnelle de `self.http_status`) est identique dans les six fichiers. Le MCP en ajoute une sixieme copie (`NavigationServiceError`) au lieu de reutiliser une base commune ; `config_overrides.AppConfigError` (`services/config_overrides.py:25`) en est une septieme variante sans constructeur. Cote routeurs, la traduction `except XError as exc: raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc` est ecrite 14 fois en ligne, plus deux helpers locaux identiques `_raise_for` ; la 0.7.3 en ajoute deux (`api/config.py:93`, `:102`, routes MCP). Ce bloc n'avait pas ete releve en 0.7.0 alors qu'il y comptait deja 5 bases et 14 sites ; c'est une dette preexistante que la 0.7.3 aggrave.
- **Regle violee** : item 5.1 — bloc identique present 6 fois (et un mapping 16 fois) sans factorisation (poids 2).
- **Remediation** : une base unique `ServiceError(Exception)` (`http_status` + constructeur) dans `services/errors.py`, dont heritent les familles `Store*`, `Graph*`, `Chunk*`, `Version*`, `Reasoning*`, `Navigation*`, `AppConfig*` ; un seul `@app.exception_handler(ServiceError)` enregistre au bootstrap qui produit la reponse, ce qui retire les `try/except` des routeurs. L'adaptateur MCP (`mcp_adapter/tool_errors.py:29`) peut capturer la meme base.

### [MIN] Pont JSON-RPC MCP Apps recopie dans les deux cartes HTML (nouveau)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:690-800` et `:1065-1177` ; `document-parser/mcp_adapter/sources_app.html:984-1188` ; tokens : `document-parser/mcp_adapter/citation_app.html:13-33`
- **Constat** : les deux pages MCP Apps embarquent chacune leur copie du pont hote : `post`, `call` (timeout 8000), `settle`, `PROTOCOL_VERSION` + `handshake`, `applyHostContext`, `applyContainerDimensions`, `reportSize`, `extract` et l'ecouteur `message` (filtre `event.source`, `ui/resource-teardown`, `host-context-changed`). `difflib` mesure environ 120 lignes normalisees identiques en blocs de 4 lignes ou plus, le reste etant des variantes (nom d'app, champ discriminant de `extract`). Un correctif du contrat SEP-1865 (cf. commit `345e2cb`) doit donc etre fait deux fois. En outre `citation_app.html` recopie a la main les tokens clairs de `frontend/src/app/App.vue:111-130` (« Same names, same values »), sans lien mecanique. Deux copies seulement : sous le seuil 3+ de l'item.
- **Regle violee** : item 5.1 (duplication a deux exemplaires, ampleur notable), non bloquant.
- **Remediation** : extraire `mcp_adapter/app_bridge.js` (et un `app_tokens.css` si la carte doit suivre la charte) et l'inliner au chargement dans `apps.py` / `sources_view.py`, qui lisent deja le HTML par `read_text` ; l'empreinte de `_versioned_uri` (`apps.py:50`) couvrira alors aussi le pont.

### [MIN] Import d'une analyse Docling recopie dans trois composants (nouveau, #359)

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:40-57`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:67-85`, `frontend/src/features/document/ui/DocumentUpload.vue:105-123`
- **Constat** : la meme sequence (lire le fichier, `JSON.parse`, `importAnalysis(documentId, document)`, message `(e as Error).message || t('analysisImport.failed')`) est ecrite trois fois dans le commit `ec3eb00`. Les deux premieres copies sont verbatim, chacune avec ses propres refs `importing` / `error` ; la troisieme passe par `store.error`.
- **Regle violee** : item 5.1 (bloc quasi-identique 3 fois), ampleur limitee (environ 15 lignes).
- **Remediation** : un composable `useAnalysisImport()` exporte par le barrel `@/features/analysis` (ou par `shared/composables/` s'il sert au-dela), qui renvoie `{ importing, error, importFile(documentId, file) }`.

### [MIN] Defauts, bornes et parsing d'env des budgets MCP / Ask non centralises (nouveau)

- **Localisation** : plafond de tours 5 — `document-parser/services/navigation_config.py:25`, `document-parser/infra/settings.py:109` `:273`, `frontend/src/features/mcp-config/store.ts:17` ; plafond Ask 5 — `document-parser/infra/settings.py:61` `:233`, `document-parser/infra/docling_agent_reasoning.py:136`, `frontend/src/features/admin-config/store.ts:23` ; bornes 1/20 — `document-parser/domain/mcp_config.py:29-30` vs `document-parser/domain/app_config.py:22-23` ; plafond de lecture 4000 — `document-parser/services/navigation_config.py:32`, `document-parser/infra/settings.py:106` `:272`, `frontend/src/features/mcp-config/store.ts:17` ; largeur d'image — `document-parser/mcp_adapter/apps.py:199` `:206`, `document-parser/mcp_adapter/sources_view.py:205`, `document-parser/services/citation_image_service.py:45` ; parse booleen — `document-parser/infra/settings.py:229` `:245` `:247` `:250` `:252` `:259` `:269` `:271` vs `document-parser/services/config_overrides.py:21`
- **Constat** : aucun code de boucle n'est duplique entre le MCP et Ask (le serveur est sans etat, la boucle est decrite dans le prompt), mais leurs constantes le sont. La docstring de `navigation_config.py:18-24` et celle de `prompts.py:16-17` affirment que le plafond MCP est « le meme defaut que la boucle Ask » ; rien ne les lie : `MAX_ROUNDS = 5` et `reasoning_max_iterations = 5` sont deux litteraux independants, recopies une fois de plus dans `from_env` et dans le formulaire du front. Les bornes `MAX_ROUNDS_MIN/MAX` (« Same bounds as the reasoning loop's iteration cap », `mcp_config.py:27-28`) redeclarent `1`/`20` au lieu d'aliaser `MAX_ITERATIONS_MIN/MAX`. Le clamp `max(120, min(max_width, 1600))` est ecrit deux fois, avec un defaut 320 repete. Le parse booleen d'env passe de 5 a 8 copies en ligne dans `Settings.from_env` (+3 pour `MCP_ENABLED`, `MCP_APPS_ENABLED`, `MCP_CITATION_CARD`) alors que `config_overrides.py:21` porte deja ce tuple.
- **Regle violee** : item 5.3 (constantes non centralisees), non bloquant.
- **Remediation** : declarer `DEFAULT_MAX_ROUNDS` / `DEFAULT_READ_TOKENS` dans `domain/mcp_config.py` (et `MAX_ROUNDS_MIN = MAX_ITERATIONS_MIN` si l'egalite est voulue), faire deriver `Settings` (champ et `from_env`) et `NavigationConfig` de ces constantes, initialiser le formulaire du front a `null` jusqu'au `load()` ; mettre les bornes de largeur dans `NavigationConfig` ; un helper `_env_bool(name, default)` dans `infra/settings.py`.

### [MIN] Vocabulaire des labels Docling recopie (nouveau pour l'essentiel)

- **Localisation** : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` ; `document-parser/domain/navigation.py:315` vs `document-parser/services/chunk_service.py:927` ; `document-parser/domain/parse_index.py:189` vs `document-parser/services/chunk_service.py:925` `:957`
- **Constat** : l'ensemble `frozenset({"page_header", "page_footer"})` est redeclare trois fois dans le nouveau code MCP sous deux noms (`_FURNITURE`, `_EMPTY_LABELS`). L'ensemble des titres `{"title", "section_header"}` existe nomme (`HEADING_LABELS`) et en litteral dans `chunk_service`. Le MCP introduit un helper `label_of` que `chunk_service` ne reutilise pas (`(item.get("label") or "").lower() or "text"` recopie en ligne).
- **Regle violee** : item 5.3 (magic strings repetees 3+ fois), non bloquant.
- **Remediation** : exposer `FURNITURE_LABELS` et `HEADING_LABELS` depuis `domain/parse_index.py`, a cote de `label_of`, et les importer partout.

### [MIN] Bloc de style `.field-*` et pont reactif v-model dupliques dans les formulaires de store (non resolu, inchange)

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue:78-108` et `:53`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:61-91` et `:40`, `frontend/src/features/store/ui/StoreForm.vue:383-405`
- **Constat** : inchange depuis 0.7.0 (fichiers non modifies depuis 0.7.2). Le perimetre store / ingestion est deprecie et retire en 0.8.0.
- **Regle violee** : item 5.1 (duplication d'ampleur limitee), non bloquant.
- **Remediation** : ne pas investir ; la suppression en 0.8.0 resout l'ecart.

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO Pydantic et value objects (non resolu, inchange)

- **Localisation** : `document-parser/api/schemas.py:165-194` et `:220-239` (decales par les nouveaux schemas), `document-parser/domain/value_objects.py:102-132`, `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`
- **Constat** : les DTO redeclarent toujours les defauts des value objects (`do_ocr=True`, `table_mode="accurate"`, `images_scale=1.0`, `max_tokens=512`, `merge_peers=True`), et `64`/`8192` sont ecrits a la fois dans le validateur (`schemas.py:238`) et dans le template, sans `CHUNK_MAX_TOKENS_MIN/MAX`.
- **Regle violee** : item 5.3, recoupe 5.6. Non bloquant.
- **Remediation** : inchangee (deriver les defauts des DTO depuis le domain ; constantes de bornes exposees au front, sur le modele `MAX_ITERATIONS_*` / `MAX_ROUNDS_*`).

### [MIN] Primitives CSS recopiees composant par composant : spinner, boutons primaires, interrupteurs

- **Localisation** : `.spinner` + `@keyframes spin` dans 17 SFC, dont `frontend/src/features/analysis/ui/AnalysisProgressBar.vue:90` (nouveau), `frontend/src/features/document/ui/DocumentUpload.vue:197`, `frontend/src/pages/DocWorkspacePage.vue:282` ; boutons primaires : `frontend/src/pages/DocsLibraryPage.vue:648`, `frontend/src/pages/DocsNewPage.vue:373`, `frontend/src/features/store/ui/StoreForm.vue:435`, `frontend/src/features/mcp-config/ui/McpConfigSection.vue:1037`, `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:305` ; interrupteurs : `frontend/src/features/chunking/ui/ChunkPanel.vue:435`, `frontend/src/pages/StudioPage.vue:1377`, `frontend/src/features/mcp-config/ui/McpConfigSection.vue:633`
- **Constat** : aucun composant ni classe globale pour ces primitives. Le spinner est recopie dans 17 fichiers (16 en 0.7.0). Le bouton primaire existe en 5 definitions dont la couleur de texte diverge (`white`, `#0a0a0b`, contour accent, et un fond `var(--color-primary, #2563eb)` bleu dans `StoreForm` qui n'est pas l'accent). Trois implementations d'interrupteur, la 0.7.3 en ajoutant une. Duplication preexistante, scoped CSS.
- **Regle violee** : item 5.1 (duplication CSS 3+ fois), classee MIN comme le `.field-*` de 0.7.0 (scoped CSS, sans logique).
- **Remediation** : `@keyframes spin` + `.spinner` globaux dans `App.vue` (ou `shared/ui/AppSpinner.vue`) ; `shared/ui/AppButton.vue` et `AppSwitch.vue` (ou classes globales `.btn`, `.btn--primary`) consommant `--accent` / `--on-accent`.

### [MIN] Palette de la vue graphe Neo4j recopiee trois fois (preexistant, perimetre deprecie)

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue:134-147`, `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:113-132`, `frontend/src/features/analysis/legendFilters.ts:34-77`
- **Constat** : `NODE_COLORS`, `KIND_COLORS` et les couleurs des puces de legende redeclarent la meme table type → hex ; le commentaire de `NodeDetailsPanel.vue:111-112` assume la copie. Ce sont les memes valeurs que `shared/elementColors.ts:14` (`#F97316`, `#3B82F6`, `#8B5CF6`, `#22C55E`, `#06B6D4`, `#EC4899`, `#14B8A6`, `#EAB308`), reindexees par label Neo4j. La resolution de l'ecart palette (05a) au re-audit 0.7.0 n'avait pas couvert cette famille. La vue graphe Neo4j est depreciee (CHANGELOG, section Deprecated) et retiree en 0.8.0, d'ou la classe MIN plutot que MAJ.
- **Regle violee** : item 5.1 / 5.3, non bloquant.
- **Remediation** : supprimer avec l'ingestion en 0.8.0 ; si la vue survit, deriver les trois tables de `ELEMENT_COLORS`.

### [MIN] `api/analyses.py` : mapping de chunks x3 et resume d'analyse redeclare (partiellement nouveau, #354)

- **Localisation** : `document-parser/api/analyses.py:149` `:173` `:196` ; `document-parser/api/analyses.py:39-41` vs `:122-124` ; `document-parser/api/schemas.py:127` vs `:145`
- **Constat** : la construction de `ChunkResponse` est ecrite trois fois, dont deux strictement identiques a partir de dicts (`update_chunk_text`, `delete_chunk`). Nouveau en 0.7.3 : `AnalysisSummaryResponse` redeclare 10 champs d'`AnalysisResponse` au lieu d'en etre la base, et `list_analysis_summaries` recopie le formatage `str(x) if x else None` de `_to_response`. Le front a fait le bon choix pour le meme besoin (`AnalysisSummary = Pick<Analysis, …>`, `shared/types.ts:78`).
- **Regle violee** : item 5.1 / esprit 5.6, non bloquant.
- **Remediation** : `class AnalysisResponse(AnalysisSummaryResponse)` et un `_summary_fields(job)` partage ; un helper `_chunk_from_dict(c)` pour les deux routes d'edition.

### [MIN] Helpers `_utcnow` / `_new_id` recopies x4, avec deux formats d'identifiant

- **Localisation** : `document-parser/domain/models.py:29-34`, `document-parser/domain/chunk_editing.py:31-36`, `document-parser/services/chunk_service.py:90-95`, `document-parser/services/version_service.py:37-42`
- **Constat** : quatre copies de chaque helper (preexistant, 8 definitions deja en 0.7.0). `_new_id` renvoie `str(uuid4())` (36 caracteres) dans `models.py` / `chunk_service.py` et `uuid4().hex` (32 caracteres) dans `chunk_editing.py` / `version_service.py` : un `ChunkEdit` cree par l'editeur (`chunk_service.py:478`) et un `ChunkEdit` cree par une restauration de version (`version_service.py:166`) n'ont pas le meme format d'id. Meme famille de derive que `_parse_iso`.
- **Regle violee** : item 5.1, non bloquant.
- **Remediation** : `new_id()` et `utcnow()` publics dans `domain/models.py` (un seul format), importes par les services.

### [INFO] `fetch()` brut dans DownloadDropdown hors du client HTTP centralise (inchange)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:133`
- **Constat** : seul `fetch()` hors de `shared/api/http.ts`, toujours justifie (lecture `blob()` + `content-disposition`). Aucune config HTTP recopiee, l'item 5.5 reste conforme.
- **Regle violee** : item 5.5 — observation.
- **Remediation** : optionnelle, un helper `downloadBlob(url)` dans `shared/api/` si un second appelant apparait.

### [INFO] Petites constantes de troncature repetees dans l'infra (inchange)

- **Localisation** : `document-parser/infra/neo4j/queries.py:104` `:128` (`[:200]`, perimetre deprecie), `document-parser/infra/docling_agent_reasoning.py:188` `:204` `:218` (`query[:120]`)
- **Constat** : inchange, repetitions locales a leur fichier.
- **Regle violee** : item 5.3 — observation.
- **Remediation** : constantes de module si ces valeurs doivent rester coherentes.

### [INFO] Config MCP vs config Ask : regles communes factorisees, residus paralleles

- **Localisation** : `document-parser/domain/mcp_config.py:94` vs `document-parser/domain/app_config.py:77` ; `document-parser/services/mcp_config_service.py:156` vs `document-parser/services/app_config_service.py:103` ; `document-parser/services/mcp_config_service.py:69` vs `document-parser/services/app_config_service.py:106` ; `frontend/src/features/mcp-config/store.ts` vs `frontend/src/features/admin-config/store.ts` ; `frontend/src/features/mcp-config/ui/McpConfigSection.vue:24` `:162` `:223` `:265` vs `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:15` `:40` `:81` `:106`
- **Constat** : le risque de doublon entre la config MCP et la config admin existante est bien traite : la precedence env/db, les parseurs et les erreurs vivent une seule fois dans `services/config_overrides.py`. Restent des paires paralleles (2 copies, sous le seuil) : `validate_base_url` et `validate_host_url` font la meme verification `urlparse` / schema / `netloc` / longueur ; la politique d'ecriture diverge pour un meme concept d'override (Ask ecrit le jeu complet par `set_many`, MCP seulement les valeurs differentes de l'env par `replace_namespace`, cf. `16f8d1e`), donc une valeur egale a l'env est un override cote Ask mais pas cote MCP ; deux stores Pinia de meme squelette, seul celui du MCP ayant factorise `write()` ; le badge « valeur surchargee » est rendu 8 fois sous deux formes (`source-badge` « db », `changed-badge` « modifie »).
- **Regle violee** : item 5.1 — observation.
- **Remediation** : au retour d'Ask (`ASK_MODE=visible`), aligner la config reasoning sur la politique MCP (diff seulement), un `validate_http_url(url, *, allow_empty)` commun et un composant `ConfigFieldRow` partage.

### [INFO] DTO du fil MCP en miroir des value objects du domain (accepte)

- **Localisation** : `document-parser/mcp_adapter/sources_view.py:52` `:71` `:88` `:102` `:113` vs `document-parser/domain/source_map.py:79` `:103` `:125` `:144` et `document-parser/domain/source_bar.py:26`
- **Constat** : `PassageOut`, `SourceHopOut`, `SourceNodeOut`, `SourceSegmentOut`, `SourceTotalsOut` reprennent champ pour champ `SourcePassage`, `SourceHop`, `SourceNode`, `SourceSegment`, `SourceTotals`. C'est un contrat publie (le SDK derive le schema de sortie des outils, cf. `mcp_adapter/wire.py:3-6`) et la projection transforme (`neutralise`, `deep_link`, arrondi des regions, `max_rounds` / `over_cap`) : conforme a l'esprit de 5.6, comme `api/schemas.py`. A surveiller : un champ ajoute au domain doit etre reporte a la main.
- **Regle violee** : item 5.6 — observation, l'item reste conforme.
- **Remediation** : aucune ; un test de parite des champs suffirait a prevenir la derive.

### [INFO] Deux extractions DoclingDocument → pages coexistent

- **Localisation** : `document-parser/infra/docling_pages.py:48` vs `document-parser/infra/serve_converter.py:269`
- **Constat** : #359 a bien extrait `docling_pages.extract_pages_detail` pour la conversion locale et l'import. Le moteur Docling Serve garde une implementation parallele sur dict brut, avec sa propre table de labels (`serve_converter.py:52`), son propre rendu Markdown des tableaux et `level=0` partout la ou le chemin local calcule le niveau. Deux copies, preexistantes.
- **Regle violee** : item 5.1 — observation.
- **Remediation** : `DoclingDocument.model_validate(json_content)` puis `extract_pages_detail`, comme le fait deja `DoclingDocumentImporter`, pour supprimer la seconde implementation.

---

## Delta vs 0.7.0

Base : re-audit `release/0.7.0 @ 94eec28` (score 67, 2 MAJ / 2 MIN / 2 INFO).

| Ecart 0.7.0 | Niveau | Statut en 0.7.3 | Verification |
|-------------|--------|-----------------|--------------|
| 05a — Palette `ELEMENT_COLORS` redeclaree 4x | MAJ | **Resolu (reste resolu)** | Definition unique `frontend/src/shared/elementColors.ts:14` ; famille voisine non couverte : palette du graphe Neo4j x3 (nouveau MIN, perimetre deprecie) |
| 05b — `_parse_iso` / `_parse_dt` x7 + divergence UTC `analysis_repo` | MAJ | **Toujours present, inchange** | 7 definitions + parse inline ; `analysis_repo.py:11-15` sans coercition UTC, repo retouche en 0.7.3 sans converger |
| 05c — Couleurs UI en dur, tokens `--color-*` inexistants | MAJ | **Toujours present, aggrave a la marge** | Compteurs identiques ; +3 litteraux dans `McpConfigSection.vue` |
| `.field-*` + pont v-model des formulaires de store | MIN | **Toujours present, inchange** | Fichiers non modifies depuis 0.7.2 ; disparait avec l'ingestion en 0.8.0 |
| Bornes de chunking / defauts DTO | MIN | **Toujours present, inchange** | Numeros de ligne decales dans `schemas.py` |
| `fetch()` brut `DownloadDropdown` | INFO | **Inchange** | Ligne 131 → 133 |
| Constantes de troncature | INFO | **Inchange** | — |

**Nouveaux ecarts 0.7.3** : 1 MAJ (contrat d'erreur service x6 / mapping x16 — dette preexistante non relevee, a laquelle la 0.7.3 ajoute une copie), 8 MIN (pont MCP Apps, import #359, defauts MCP/Ask, labels Docling, primitives CSS, palette graphe, `api/analyses.py`, `_utcnow` / `_new_id`), 3 INFO (config MCP vs Ask, DTO MCP miroirs, extraction pages Serve).

**Score : 67 → 67 (delta 0).** Les items 5.1 et 5.3 etaient deja non conformes ; les nouveaux ecarts ne font basculer aucun autre item.

---

## Points positifs

- **Override de config factorise des sa deuxieme utilisation** : `services/config_overrides.py` porte une seule fois la precedence env → `app_settings` (`pick`, `parse_int_between`, `parse_bool`, `require_writable`, erreurs `AppConfig*`), consommee par `AppConfigService` et `McpConfigService`. Le risque de doublon entre config MCP et config admin est traite a la racine.
- **Cablage MCP partage entre HTTP et stdio** : `bootstrap/factories.py` (`env_mcp_config`, `build_parse_loader`, `build_document_tools`) et `mcp_adapter.build_mcp_server` sont consommes a l'identique par `bootstrap/mcp_mount.py` et `mcp_stdio.py`, sans recopie.
- **Budgets du MCP en un seul endroit** : `services/navigation_config.py` (`NavigationConfig`) est lu par le loader, la navigation, la citation, l'image et les sources ; un seul `ParseLoader` indexe une parse pour les quatre services ; estimation de tokens (`domain/navigation.py:327` / `:345`), parsing d'ancre (`domain/anchors.py`) et neutralisation (`mcp_adapter/wire.py`, 22 usages) sont centralises.
- **Pas de seconde implementation de la boucle Ask** : le MCP ne reimplemente pas la boucle RAG cote serveur ; la procedure est declarative (`mcp_adapter/prompts.py`), executee par le client avec les memes outils.
- **Viewer partage apres #352** : `DocWorkspacePage.vue` a supprime sa barre d'outils et sa navigation de page au profit de `PagePreviewWithOverlay`, desormais commun a l'espace document, a l'onglet Parse et a l'onglet Chunks.
- **Mapping Docling partage apres #359** : `infra/docling_pages.py` sert a la fois la conversion locale et l'import d'analyses.
- **Types derives plutot que redeclares** : `AnalysisSummary = Pick<Analysis, …>` (`shared/types.ts:78`) ; types MCP feature-scoped dans `features/mcp-config/types.ts`.
- **Validation sans desaccord** : bornes MCP definies cote domain (`domain/mcp_config.py:29-35`), miroir aligne cote front (`features/mcp-config/types.ts:59-62`), DTO `McpConfigUpdateRequest` sans bornes concurrentes : une seule regle ecrite.
- **Client HTTP toujours integralement centralise** : tous les `features/*/api.ts`, y compris `mcp-config/api.ts`, passent par `apiFetch`.
- **Primitives d'accordeon partagees** : `shared/ui/AccordionSection.vue`, `AccordionRow.vue`, `accordion.ts` structurent les sections de Settings au lieu d'une mise en page par section.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL (la checklist DRY n'a pas d'item de poids 3). Score **67 / 100**
(tranche 60-79), identique au re-audit 0.7.0. Trois MAJ, sous le seuil bloquant (> 3) :
les deux portes en dette depuis 0.7.0 (`_parse_iso` x7 avec divergence UTC latente,
couleurs UI non tokenisees), qui n'ont pas bouge, et le contrat d'erreur service → HTTP
recopie (6 bases, 16 sites de mapping), preexistant et aggrave d'une copie par le MCP.
Les trois corrections sont mecaniques (helper pur, tokens CSS, base d'exception + handler
FastAPI) et sans reprise fonctionnelle. Le nouveau code MCP est globalement bien factorise ;
ses ecarts sont mineurs (pont JSON-RPC des deux cartes, constantes de budgets, labels
Docling). Condition : plan de remediation des 3 MAJ dans le cycle 0.7.x / 0.8.0, la
suppression de l'ingestion en 0.8.0 levant d'elle-meme une partie des ecarts couleur et
des MIN du perimetre store / graphe.

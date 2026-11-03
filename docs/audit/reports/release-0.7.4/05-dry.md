# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag `v0.7.3` + 2 commits README)

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`
(hors `*.test.*`). Baseline : rapport 0.7.3 (`docs/audit/reports/release-0.7.3/05-dry.md`,
commit `02adc68`, score 67). L'audit 05 n'a pas ete re-audite en 0.7.3-reaudit (score
reconduit tel quel).

Delta de code depuis la baseline (`02adc68..1de1929`) : remediation PR #367 et #368, 13
fichiers sous `document-parser/` et `frontend/src/` dont `uv.lock`. Aucun ne touche une
duplication relevee en 0.7.3 :
- `services/analysis_service.py:180` : l'import Docling passe par `asyncio.to_thread` ;
- `infra/settings.py:92-96` : commentaire seulement (decale de +1 les lignes suivantes du fichier) ;
- `mcp_adapter/citation_app.html:2` : `lang="fr"` ;
- `frontend/src/features/mcp-config/ui/McpConfigSection.vue:410-411` : commentaire sur 2 lignes (decale de +1 les lignes suivantes) ;
- `ConfigSource` deplace de `features/admin-config/types.ts` vers `frontend/src/shared/types.ts:5` (gain DRY, cf. points positifs).

> **Score 67 / 100 — inchange vs 0.7.3 (67).** Les trois MAJ de 0.7.3 sont re-verifies sur le
> code actuel et **tous ouverts a l'identique** (`_parse_iso` x7 + divergence UTC, couleurs UI
> non tokenisees, contrat d'erreur service → HTTP recopie) : aucun compteur n'a bouge. Leur
> inventaire est desormais exhaustif (fichier:ligne) pour permettre la remediation sans
> nouvelle recherche. La passe complementaire releve 6 MIN et 1 INFO **preexistants mais non
> releves jusqu'ici** (serialisation de chunk x4, journal `ChunkEdit` x10, regles split/merge
> en double avec un module domaine mort, `formatDate` x4, squelette d'action des stores Pinia,
> double format de date sur le fil) ; aucun ne fait basculer un item.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 16 |
| Ecarts INFO | 6 |

| # | Item | Poids | Conforme | Evolution vs 0.7.3 |
|---|------|-------|----------|--------------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | **Non** | Inchange — tenu en echec par deux MAJ : `_parse_iso` x7 et contrat d'erreur (6 bases, 16 mappings). Nouveaux MIN de meme famille (serialisation chunk x4, `ChunkEdit` x10, `formatDate` x4, actions Pinia) |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui | Renforce — `ConfigSource` deplace dans `shared/types.ts:5` (remediation 07) ; aucune redeclaration d'un type de `shared/types.ts` dans les features |
| 5.3 | Pas de magic numbers/strings eparpilles — constantes nommees et centralisees | 2 | **Non** | Inchange — couleurs UI : 33 `var(--color-*)`, 10 `#dc2626` bruts, 3 `--danger`, 24 replis en dur sur tokens definis, 3 litteraux MCP |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui | Inchange (aucun composable mal place ; les duplications de logique d'action sont traitees en 5.1) |
| 5.5 | Appels API sans duplication de config HTTP — `shared/api/http.ts` | 2 | Oui | Inchange — 11 `features/*/api.ts` passent par `apiFetch` ; seul `fetch()` brut : `DownloadDropdown.vue:133` (INFO) |
| 5.6 | Schemas Pydantic transforment le domain, ne le redefinissent pas | 2 | Oui | Inchange — `api/schemas.py` non modifie depuis `02adc68` ; `from_view` / `from_status` / `from_trace` |
| 5.7 | Regles de validation a un seul endroit (pas de desaccord front/back) | 1 | Oui | Inchange — bornes MCP / Ask / chunking alignees front/back ; limite d'upload servie par `/api/health` |

Poids total de la checklist : 12. Poids conformes : 2 (5.2) + 1 (5.4) + 2 (5.5) + 2 (5.6) +
1 (5.7) = 8. Items non conformes : 5.1 (2) et 5.3 (2).
`score = 8 / 12 * 100 = 66,7 → 67`. **Delta vs 0.7.3 : 0 point** (67 → 67).

### Compteurs de duplication

Methode : aucun detecteur installe (ni `jscpd`, ni `pylint`/`symilar`). Script jetable de
fenetres glissantes (4 et 6 lignes normalisees, hors blancs, commentaires et imports) sur
`document-parser/` (hors `.venv`, `tests`, `migrations`) et `frontend/src/` (hors `*.test.*`),
`difflib` sur les paires suspectes, commandes de la fiche 05, et `git grep` sur `02adc68` et
`1de1929` pour chaque compteur.

| Compteur | 0.7.3 (`02adc68`) | 0.7.4 (`1de1929`) |
|----------|-------------------|-------------------|
| Definitions `_parse_iso` / `_parse_dt` dans `persistence/` (+ parse inline) | 7 (+1) | 7 (+1) |
| Repli `or datetime.now(UTC)` sur une date lue en base | 5 | 5 |
| References `var(--color-*)` (namespace jamais defini) | 33 | 33 |
| Litteraux `#d1d5db` / `#6b7280` / `#dc2626` (casse exacte, `App.vue` inclus) | 7 / 12 / 11 | 7 / 12 / 11 |
| `var(--danger, …)` (token inexistant) | 3 | 3 |
| Replis en dur `var(--<token defini>, #hex)` | 24 | 24 |
| Usages `var(--error)` | 42 | 42 |
| Bases `XServiceError` avec `__init__(message, *, http_status=None)` identique | 6 | 6 |
| Sites `HTTPException(status_code=<err>.http_status, …)` dans `api/` (inline + `_raise_for`) | 14 + 2 | 14 + 2 |
| SFC redefinissant `@keyframes spin` | 17 | 17 |
| Parse booleen `.lower() in ("1","true","yes","on")` dans `infra/settings.py` | 8 | 8 |
| Ensemble `{"page_header","page_footer"}` redeclare | 3 | 3 |
| Constructions `ChunkEdit(` dans `services/` (nouveau compteur) | 10 | 10 |
| Serialiseurs Chunk → dict camelCase dans `services/` (nouveau compteur) | 4 | 4 |
| `function formatDate` locales dans `frontend/src` (nouveau compteur) | 4 | 4 |
| `str(<datetime>)` dans `api/` (nouveau compteur) | 13 | 13 |
| `(e as Error).message` dans `frontend/src` (nouveau compteur) | 41 | 41 |

Tous les compteurs sont identiques entre `02adc68` et `1de1929` : aucune regression, aucune
correction.

---

## Ecarts constates

### [MAJ] Helper de parsing ISO-datetime copie-colle dans 7 repositories, divergence UTC

**Statut vs 0.7.3 : non resolu, inchange** (fichiers `persistence/*` non modifies depuis `02adc68`).

- **Localisation** (inventaire exhaustif) :
  - definitions :
    - `document-parser/persistence/analysis_repo.py:11-15` (`_parse_dt`, **sans coercition UTC**) — appels `:32`, `:33`, `:34` ;
    - `document-parser/persistence/document_repo.py:12-18` (`_parse_iso`) — appel `:40` ; **parse inline** `:27-31` sur `created_at` ;
    - `document-parser/persistence/chunk_repo.py:14-20` — appels `:37`, `:38`, `:39` ;
    - `document-parser/persistence/chunk_edit_repo.py:13-19` — appels `:29`, `:45` ;
    - `document-parser/persistence/document_store_link_repo.py:12-18` — appel `:28` ;
    - `document-parser/persistence/document_version_repo.py:13-17` (variante non optionnelle) — appel `:28` ;
    - `document-parser/persistence/store_repo.py:29-35` (`_parse_dt`, variante `str | datetime`) — appels `:59`, `:60` ;
  - repli silencieux `or datetime.now(UTC)` sur une colonne lue : `analysis_repo.py:34`, `chunk_repo.py:37`, `:38`, `chunk_edit_repo.py:29`, `:45`.
- **Constat** : les 7 definitions et le parse inline sont toujours la. Quatre sont strictement identiques (`document_repo`, `chunk_repo`, `chunk_edit_repo`, `document_store_link_repo` : garde `None`/`""`, `fromisoformat`, `tzinfo`→UTC). `analysis_repo._parse_dt` reste le seul a ne pas forcer UTC (`return datetime.fromisoformat(value)`), et `_row_to_job` (`:18`) sert toutes les lectures du repo, dont `find_all_summaries` (`:78-86`, route `/api/analyses/summaries`). La divergence reste latente : les ecritures font `str()` de datetimes UTC aware (`analysis_repo.py:64`, `:195`, `:196`) et le defaut SQL naif `datetime('now')` de `analysis_jobs.created_at` (`persistence/database.py:82`) n'est jamais declenche, l'`INSERT` fournissant la valeur.
- **Regle violee** : item 5.1 — bloc quasi-identique present 7 fois sans factorisation (poids 2).
- **Remediation** : un unique `parse_iso(value: str | datetime | None) -> datetime | None` (UTC par defaut) dans `persistence/database.py` ou `persistence/_datetime.py`, importe par les 7 `_row_to_*` ; supprimer le parse inline `document_repo.py:27-31` ; `document_version_repo` et `store_repo` l'appellent aussi (la variante `datetime` en entree est un cas du meme helper). Aligner `analysis_repo` sur la coercition UTC. Optionnel : remplacer les replis `or datetime.now(UTC)` sur colonnes `NOT NULL` par une erreur explicite.
- **Effort** : S (1 helper, 7 fichiers, ~40 lignes supprimees). **Risque de regression** : faible — seul changement de comportement, `AnalysisJob.started_at/completed_at/created_at` sortent aware pour une ligne ecrite naive, cas inexistant en pratique ; les tests de repository existants couvrent les lectures.

### [MAJ] Couleurs UI en dur, tokens `--color-*` / `--danger` non definis, replis divergents

**Statut vs 0.7.3 : non resolu, inchange** (memes compteurs ; `McpConfigSection.vue` decale de +1 ligne). Inventaire complete de 24 replis en dur sur tokens definis, preexistants et non listes en 0.7.3.

- **Localisation** (inventaire exhaustif, 74 sites dans 14 SFC) :
  - **(a) namespace fantome `var(--color-*)` — 33** :
    - `frontend/src/shared/ui/ComingSoonShell.vue:45` `:46` `:55` `:56` `:67` `:73` `:80` `:87` `:88` `:98` ;
    - `frontend/src/shared/breadcrumb/AppBreadcrumb.vue:43` `:44` `:45` `:66` `:76` `:81` `:90` ;
    - `frontend/src/features/store/ui/StoreForm.vue:389` `:397` `:401` `:414` `:438` `:453` `:454` `:475` `:482` `:487` ;
    - `frontend/src/features/store/ui/OpenSearchConfigForm.vue:77` `:86` ;
    - `frontend/src/features/store/ui/Neo4jConfigForm.vue:94` `:103` ;
    - `frontend/src/pages/IngestLaunchDialog.vue:257` `:357` ;
  - **(b) litteraux bruts du rouge d'erreur `#dc2626` — 10** (valeur de `--error` en clair, `App.vue:128`) :
    - `frontend/src/features/store/ui/StoreForm.vue:394` `:405` `:503` ;
    - `frontend/src/features/store/ui/OpenSearchConfigForm.vue:82` `:90` ;
    - `frontend/src/features/store/ui/Neo4jConfigForm.vue:99` `:107` ;
    - `frontend/src/features/analysis/ui/GraphView.vue:576` ;
    - `frontend/src/pages/IngestLaunchDialog.vue:327` `:345` ;
    - et `#6b7280` brut : `frontend/src/pages/IngestLaunchDialog.vue:315` ;
  - **(c) token inexistant `var(--danger, #f87171)` — 3** : `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:329` `:348` `:369` ;
  - **(d) replis en dur sur tokens definis — 24** (complement d'inventaire) :
    - `frontend/src/shared/ui/AppSidebar.vue:290` `:291` (`--success, #22c55e`), `:295` `:296` (`--error, #ef4444`) ;
    - `frontend/src/features/document/ui/DocumentUpload.vue:174` (`--error, #e53e3e`) ;
    - `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:325` `:374` (`--success, #4ade80`) ;
    - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:119` `:120` (`--warning, #ca8a04`) ;
    - `frontend/src/features/ingestion/ui/IngestPanel.vue:231` `:245` `:256` `:290` `:311` (`--success, #22c55e`) ;
    - `frontend/src/pages/IngestLaunchDialog.vue:199` (`--bg-surface, #fff`), `:225` `:234` `:239` `:303` (`--text-muted, #6b7280`), `:259` (`--bg-elevated, #f9fafb`), `:298` (`--text, #111827`), `:368` `:369` (`--accent, #2563eb`) ;
    - `frontend/src/pages/DocumentsPage.vue:428` (`--warning, #f59e0b`) ;
  - **(e) texte / curseur sur fond accent en dur — 3** : `frontend/src/features/mcp-config/ui/McpConfigSection.vue:663` (`#ffffff`), `:1041` `:1047` (`#0a0a0b`).
- **Constat** : `App.vue:78-131` definit les tokens (`--border`, `--text-muted`, `--accent`, `--error`, `--success`, `--warning`, `--bg-surface`, …) en sombre et en clair ; aucun `--color-*` ni `--danger` n'y existe. Les 33 references au namespace fantome tombent donc toujours sur leur repli, et ce repli diverge pour un meme nom : `--color-text-muted` → `#6b7280` (`StoreForm.vue:401`) ou `#9ca3af` (`AppBreadcrumb.vue:43`) ; `--color-border` → `#d1d5db` (`StoreForm.vue:389`), `#e5e7eb` (`ComingSoonShell.vue:46`, `IngestLaunchDialog.vue:257`) ou `#1a1a1d` (`AppBreadcrumb.vue:44`). Ces composants ne suivent donc pas le theme clair/sombre. Les replis sur tokens definis sont du code mort (le token existe toujours) mais encodent des valeurs fausses : `--accent` replie sur un bleu `#2563eb` alors que l'accent est orange `#f97316` (`IngestLaunchDialog.vue:368`), `--warning` sur `#f59e0b` ou `#ca8a04` selon le fichier, `--error` sur `#ef4444` ou `#e53e3e`. `ReasoningConfigSection.vue` consomme `--danger`, qui n'existe pas (le systeme definit `--error`). Le bouton primaire MCP ecrit `#0a0a0b` (valeur de `--bg` sombre) quand les autres boutons sur accent ecrivent `white` (`DocsLibraryPage.vue:655`, `DocsNewPage.vue:379`). 41 des 74 sites sont dans le perimetre deprecie (ingestion, stores, graphe Neo4j — CHANGELOG `[0.7.3]` › Deprecated) : `features/store/ui/*` (21), `IngestLaunchDialog.vue` (14), `IngestPanel.vue` (5), `GraphView.vue` (1).
- **Regle violee** : item 5.3 — « Pas de magic numbers ou magic strings eparpilles — les constantes sont nommees et centralisees » (poids 2).
- **Remediation** : (a) `var(--color-border, …)` → `var(--border)`, `--color-text-muted` → `--text-muted`, `--color-text` → `--text`, `--color-surface` → `--bg-surface`, `--color-bg-muted` → `--bg-elevated`, `--color-accent` / `--color-primary` → `--accent`, `--color-accent-soft` → `--accent-muted` ; (b) `#dc2626` → `var(--error)` ; (c) `var(--danger, …)` → `var(--error)` ; (d) supprimer tous les replis (`var(--success)`, `var(--error)`, …) ; (e) ajouter `--on-accent` dans `App.vue` (clair + sombre) et le consommer dans `McpConfigSection` et les `.btn-primary`. Les 41 sites du perimetre deprecie disparaissent avec la suppression de l'ingestion en 0.8.0 ; les 33 autres (`ComingSoonShell`, `AppBreadcrumb`, `ReasoningConfigSection`, `DocumentUpload`, `McpConfigSection`, `AppSidebar`, `StaleStoresStrip`, `DocumentsPage`) peuvent etre traites tout de suite.
- **Effort** : M pour les 74 sites (remplacements mecaniques, 14 SFC) ; S pour les 33 sites hors perimetre deprecie. **Risque de regression** : nul fonctionnellement, visuel modere — les teintes changent la ou le repli etait utilise (`AppBreadcrumb`, `ComingSoonShell` passent sur la palette du theme ; `--text-muted` vaut `#63636e` / `#a1a1aa` au lieu de `#6b7280`). Verification visuelle clair + sombre requise ; aucun test unitaire n'asserte ces styles.

### [MAJ] Contrat d'erreur service → HTTP recopie : base d'erreur x6 (+1) et mapping x16

**Statut vs 0.7.3 : non resolu, inchange** (`services/*` et `api/*` concernes non modifies depuis `02adc68`). Inventaire complete des chemins « introuvable » non types, preexistants.

- **Localisation** (inventaire exhaustif) :
  - **bases recopiees (6)**, corps de `__init__` identique (`super().__init__(message)` puis surcharge conditionnelle de `self.http_status`) :
    - `document-parser/services/store_service.py:34-42` (`StoreServiceError`, defaut 400) ;
    - `document-parser/services/graph_service.py:25-33` (`GraphServiceError`, 500) ;
    - `document-parser/services/chunk_service.py:60-66` (`ChunkServiceError`, 400) ;
    - `document-parser/services/version_service.py:69-75` (`VersionServiceError`, 400) ;
    - `document-parser/services/reasoning_service.py:27-35` (`ReasoningServiceError`, 500) ;
    - `document-parser/services/navigation_errors.py:13-21` (`NavigationServiceError`, 500) ;
    - 7e variante sans constructeur : `document-parser/services/config_overrides.py:25-28` (`AppConfigError`, 500) ;
  - **mapping inline `except XError as exc: raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc` (14)** :
    - `document-parser/api/config.py:51` `:60` `:71` `:93` `:102` (clauses `except` en `:48` `:59` `:70` `:92` `:101`) ;
    - `document-parser/api/stores.py:105` `:114` `:139` `:162` `:172` `:184` `:197` ;
    - `document-parser/api/graph.py:70` ;
    - `document-parser/api/reasoning.py:37` ;
  - **helpers locaux `_raise_for` identiques (2)** :
    - `document-parser/api/document_chunks.py:61-62`, appele 11 fois : `:76` `:90` `:110` `:120` `:134` `:147` `:167` `:184` `:198` `:212` `:235` ;
    - `document-parser/api/document_versions.py:47-48`, appele 2 fois : `:59` `:77` ;
  - **complement : « document introuvable » exprime de 6 facons** (memes routeurs, meme contrat) :
    - deux classes homonymes `DocumentNotFoundError` : `services/chunk_service.py:73` et `services/navigation_errors.py:24` ;
    - `VersionServiceError(…, http_status=404)` : `services/version_service.py:205` ;
    - `ValueError("Document not found: …")` : `services/analysis_service.py:145`, `:173` ;
    - `ExportNotFoundError` (base sans `http_status`) : `services/export_service.py:57`, classe `:109` ;
    - `HTTPException(404, "Document not found")` litteral apres un `None` du service : `api/documents.py:120` `:130` `:174` `:210` ; « Analysis not found » : `api/analyses.py:135` `:214`, `api/ingestion.py:34` ;
  - **complement : mapping de `ValueError` au cas par cas** : `api/analyses.py:67-68` (→ 404), `:83-85` (**404 si le message commence par `"Document not found:"`**, sinon 400), `:146-147`, `:170-171`, `:193-194` (→ 400), `api/documents.py:97-98` (→ 400), `:192-193` (→ 404) ; et les blocs `FileNotFoundError` → 404 « PDF file not found on disk » / `Exception` → 422 « Failed to read PDF file » recopies entre `/preview` (`api/documents.py:194-201`) et `/pages` (`:217-221`).
- **Constat** : chaque service redeclare la meme base « erreur avec indice HTTP » au lieu d'heriter d'une base commune, et chaque routeur retraduit cette base a la main (14 sites inline, 2 helpers prives identiques). Aucun `@app.exception_handler` n'est enregistre (`main.py:83-116`). Les services sans erreur typee poussent le contrat dans le routeur : `api/analyses.py:84` decide du code HTTP en comparant le **texte** du message a celui ecrit dans `services/analysis_service.py:173` — un changement de libelle change le code de statut. L'adaptateur MCP filtre sur la seule famille navigation (`mcp_adapter/tool_errors.py:46`), ce qui est voulu.
- **Regle violee** : item 5.1 — bloc identique present 6 fois (base) et 16 fois (mapping) sans factorisation (poids 2).
- **Remediation** : une base unique `ServiceError(Exception)` (`http_status` + constructeur) dans `services/errors.py` ; re-parenter `Store*`, `Graph*`, `Chunk*`, `Version*`, `Reasoning*`, `Navigation*`, `AppConfig*` (et `ExportNotFoundError`) ; un seul `@app.exception_handler(ServiceError)` dans `main.py` qui renvoie `{"detail": str(exc)}` avec `exc.http_status` ; supprimer les 14 `try/except` et les 2 `_raise_for`. Dans un second temps, une `DocumentNotFoundError(ServiceError)` partagee (404) levee par `analysis_service`, `version_service`, `chunk_service`, `parse_loader`, ce qui supprime le test sur le prefixe du message (`api/analyses.py:84`). `ToolErrors` garde son filtre sur `NavigationServiceError`.
- **Effort** : M (1 module, 7 familles re-parentees, 1 handler, ~50 lignes de `try/except` supprimees). **Risque de regression** : moyen — le contrat HTTP (codes et `{"detail": …}`) doit rester identique ; 11 fichiers de test backend assertent des codes 4xx/5xx et couvrent la plupart des routes. Points d'attention : ne pas elargir le filtre MCP a la base commune, et garder l'ordre des `except` des routes qui mappent aussi `ValueError`/`OSError`.

### [MIN] Pont JSON-RPC MCP Apps recopie dans les deux cartes HTML

**Statut vs 0.7.3 : non resolu, inchange** (seule la ligne 2 de `citation_app.html` a change).

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:690-800` et `:1065-1177` ; `document-parser/mcp_adapter/sources_app.html:984-1088` et `:1089-1188` ; tokens : `document-parser/mcp_adapter/citation_app.html:13-33` vs `frontend/src/app/App.vue:110-130`
- **Constat** : `post`, `call` (timeout 8000), `settle`, `PROTOCOL_VERSION = "2026-01-26"`, `handshake`, `applyHostContext`, `applyContainerDimensions`, `reportSize`, `extract` et l'ecouteur `message` (`ui/resource-teardown`, `host-context-changed`) existent dans les deux pages (`citation_app.html:690` `:701` `:713` `:732` `:737` `:768` `:787` `:1065` `:1105` `:1123` ; `sources_app.html:984` `:1000` `:1012` `:1028` `:1033` `:1061` `:1071` `:1089` `:1125` `:1143`). `difflib` mesure 112 lignes normalisees identiques en blocs de 4 lignes ou plus (61 + 51). Deux copies : sous le seuil 3+.
- **Regle violee** : item 5.1 (duplication a deux exemplaires, ampleur notable), non bloquant.
- **Remediation** : extraire `mcp_adapter/app_bridge.js` et l'inliner au chargement dans `apps.py:67` / `sources_view.py:39` (qui lisent deja le HTML par `read_text`) ; `_versioned_uri` (`apps.py:50`) couvrira alors le pont.

### [MIN] Import d'une analyse Docling recopie dans trois composants

**Statut vs 0.7.3 : non resolu, inchange.**

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:40-57`, `frontend/src/features/document/ui/DocumentActionsMenu.vue:67-85`, `frontend/src/features/document/ui/DocumentUpload.vue:105-123`
- **Constat** : meme sequence (lire le fichier, `JSON.parse`, `importAnalysis(documentId, document)`, `(e as Error).message || t('analysisImport.failed')`) ; les deux premieres copies sont verbatim, chacune avec ses refs `importing` / `error`.
- **Regle violee** : item 5.1 (bloc quasi-identique 3 fois), ampleur limitee (~15 lignes).
- **Remediation** : composable `useAnalysisImport()` exporte par le barrel `@/features/analysis`, renvoyant `{ importing, error, importFile(documentId, file) }`.

### [MIN] Defauts, bornes et parsing d'env des budgets MCP / Ask non centralises

**Statut vs 0.7.3 : non resolu, inchange** (lignes de `infra/settings.py` decalees de +1 apres `:89`). Complement : le schema « defaut ecrit deux fois » couvre tout `Settings.from_env`.

- **Localisation** : plafond de tours 5 — `document-parser/services/navigation_config.py:25`, `document-parser/infra/settings.py:110` `:274`, `frontend/src/features/mcp-config/store.ts:17` ; plafond Ask 5 — `document-parser/infra/settings.py:61` `:234`, `document-parser/infra/docling_agent_reasoning.py:136`, `frontend/src/features/admin-config/store.ts:23` ; bornes 1/20 — `document-parser/domain/mcp_config.py:29-30` vs `document-parser/domain/app_config.py:22-23` (miroirs front `frontend/src/features/mcp-config/types.ts:59-60` vs `frontend/src/features/admin-config/types.ts:40-41`) ; plafond de lecture 4000 — `document-parser/services/navigation_config.py:32`, `document-parser/infra/settings.py:107` `:273`, `frontend/src/features/mcp-config/store.ts:17` ; largeur d'image — `document-parser/mcp_adapter/apps.py:199` `:206`, `document-parser/mcp_adapter/sources_view.py:201` `:205`, `document-parser/services/citation_image_service.py:45` ; parse booleen — `document-parser/infra/settings.py:230` `:246` `:248` `:251` `:253` `:260` `:270` `:272` vs `document-parser/services/config_overrides.py:21` ; defauts recopies en chaine — `document-parser/infra/settings.py:204-276` (33 `os.environ.get(NAME, "<defaut>")`, ex. `max_file_size_mb` `:28`/`:216`, `default_table_mode` `:25`/`:213`)
- **Constat** : `MAX_ROUNDS = 5` et `reasoning_max_iterations = 5` sont deux litteraux independants malgre les docstrings qui les disent egaux (`navigation_config.py:18-24`) ; `MAX_ROUNDS_MIN/MAX` redeclarent `1`/`20` au lieu d'aliaser `MAX_ITERATIONS_MIN/MAX` ; le clamp `max(120, min(max_width, 1600))` est ecrit deux fois ; 8 parses booleens en ligne alors que `config_overrides._TRUE_VALUES` existe ; chaque champ de `Settings` a son defaut ecrit deux fois (attribut du dataclass + chaine de `from_env`).
- **Regle violee** : item 5.3 (constantes non centralisees), non bloquant.
- **Remediation** : `DEFAULT_MAX_ROUNDS` / `DEFAULT_READ_TOKENS` dans `domain/mcp_config.py` (et `MAX_ROUNDS_MIN = MAX_ITERATIONS_MIN` si voulu) ; bornes de largeur dans `NavigationConfig` ; helpers `_env_bool(name, default)` / `_env_int(name, default)` dans `infra/settings.py` lisant le defaut du champ (`dataclasses.fields`) ; formulaire front initialise a `null` jusqu'au `load()`.

### [MIN] Vocabulaire des labels Docling recopie

**Statut vs 0.7.3 : non resolu, inchange.**

- **Localisation** : `document-parser/domain/page_regions.py:42`, `document-parser/domain/navigation.py:319`, `document-parser/services/source_service.py:54` ; `document-parser/domain/navigation.py:315` vs `document-parser/services/chunk_service.py:927` ; `document-parser/domain/parse_index.py:189` vs `document-parser/services/chunk_service.py:925` `:957`
- **Constat** : `frozenset({"page_header", "page_footer"})` redeclare 3 fois sous deux noms (`_FURNITURE`, `_EMPTY_LABELS`) ; `{"title", "section_header"}` existe nomme (`HEADING_LABELS`) et en litteral dans `chunk_service` ; `label_of` non reutilise par `chunk_service` (`(item.get("label") or "").lower() or "text"` x2).
- **Regle violee** : item 5.3 (magic strings repetees 3+ fois), non bloquant.
- **Remediation** : exposer `FURNITURE_LABELS` et `HEADING_LABELS` depuis `domain/parse_index.py`, a cote de `label_of`, et les importer partout.

### [MIN] Bloc de style `.field-*` et pont reactif v-model dupliques dans les formulaires de store

**Statut vs 0.7.3 : non resolu, inchange** (fichiers non modifies depuis 2026-08-08, perimetre deprecie).

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue:78-108` et `:52-53`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:61-91` et `:40`, `frontend/src/features/store/ui/StoreForm.vue:375-405`
- **Constat** : inchange ; perimetre store / ingestion retire en 0.8.0.
- **Regle violee** : item 5.1 (duplication d'ampleur limitee), non bloquant.
- **Remediation** : ne pas investir ; la suppression en 0.8.0 resout l'ecart.

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO Pydantic et value objects

**Statut vs 0.7.3 : non resolu, inchange.** Complement d'inventaire : 2e template front et litteraux `table_mode`.

- **Localisation** : `document-parser/api/schemas.py:165-194` et `:220-239`, `document-parser/domain/value_objects.py:102-132`, `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`, `frontend/src/features/chunking/ui/ChunkPanel.vue:38-39` (complement) ; `"accurate"` / `"fast"` sans enum : `document-parser/domain/value_objects.py:104`, `document-parser/services/analysis_service.py:75`, `document-parser/api/schemas.py:170` `:200-201`, `document-parser/infra/settings.py:25` `:175` `:213`, `document-parser/infra/local_converter.py:54`, `frontend/src/shared/types.ts:53`, `frontend/src/pages/StudioPage.vue:578`
- **Constat** : les DTO redeclarent les defauts des value objects (`do_ocr=True`, `table_mode="accurate"`, `images_scale=1.0`, `max_tokens=512`, `merge_peers=True`) ; `64`/`8192` sont ecrits dans le validateur (`schemas.py:238-239`) et dans deux templates. Le couple `("accurate", "fast")` est valide a deux endroits (`schemas.py:200`, `settings.py:175`) et compare en litteral dans l'adaptateur (`local_converter.py:54`).
- **Regle violee** : item 5.3, recoupe 5.6. Non bloquant.
- **Remediation** : deriver les defauts des DTO depuis le domain ; `CHUNK_MAX_TOKENS_MIN/MAX` exposes au front (modele `MAX_ITERATIONS_*`) ; un `TableMode(StrEnum)` dans `domain/value_objects.py`.

### [MIN] Primitives UI recopiees composant par composant : spinner, boutons primaires, interrupteurs, icones

**Statut vs 0.7.3 : non resolu, inchange** (`McpConfigSection.vue` decale de +1). Complement : `.spinner-sm` x3 et icone document SVG x4.

- **Localisation** :
  - `@keyframes spin` dans 17 SFC (dont 15 avec une classe `.spinner`) : `frontend/src/features/document/ui/DocTreeRail.vue:146`, `frontend/src/features/document/ui/DocumentUpload.vue:197`, `frontend/src/features/chunks/ui/ChunksPanel.vue:296`, `frontend/src/features/chunks/ui/ChunksEditor.vue:617`, `frontend/src/features/ingestion/ui/IngestPanel.vue:341`, `frontend/src/features/analysis/ui/ResultTabs.vue:579`, `frontend/src/features/analysis/ui/AnalysisPanel.vue:150`, `frontend/src/features/analysis/ui/GraphView.vue:652`, `frontend/src/features/analysis/ui/AnalysisProgressBar.vue:90`, `frontend/src/features/chunking/ui/ChunkPanel.vue:796`, `frontend/src/pages/DocsNewPage.vue:326`, `frontend/src/pages/SearchPage.vue:143`, `frontend/src/pages/DocWorkspacePage.vue:282`, `frontend/src/pages/StudioPage.vue:1445`, `frontend/src/pages/DocsLibraryPage.vue:497`, `frontend/src/pages/DocParseTab.vue:789`, `frontend/src/pages/DocChunkTab.vue:236` ; `.spinner-sm` : `frontend/src/features/ingestion/ui/IngestPanel.vue:332`, `frontend/src/features/chunking/ui/ChunkPanel.vue:787`, `frontend/src/pages/StudioPage.vue:881` ;
  - boutons primaires : `frontend/src/pages/DocsLibraryPage.vue:648`, `frontend/src/pages/DocsNewPage.vue:373`, `frontend/src/features/store/ui/StoreForm.vue:435`, `frontend/src/features/mcp-config/ui/McpConfigSection.vue:1038`, `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:305` ;
  - interrupteurs : `frontend/src/features/chunking/ui/ChunkPanel.vue:435`, `frontend/src/pages/StudioPage.vue:1377`, `frontend/src/features/mcp-config/ui/McpConfigSection.vue:634` ;
  - icone document SVG inline `<svg class="doc-icon" viewBox="0 0 20 20">` : `frontend/src/features/document/ui/DocWorkspaceHeader.vue:4`, `frontend/src/features/document/ui/DocumentList.vue:12`, `frontend/src/pages/StudioPage.vue:142`, `frontend/src/pages/DocsLibraryPage.vue:108`.
- **Constat** : aucun composant ni classe globale pour ces primitives. Le bouton primaire existe en 5 definitions dont la couleur de texte diverge (`white`, `#0a0a0b`, contour accent, fond bleu `--color-primary` dans `StoreForm`). Trois implementations d'interrupteur. Duplication scoped CSS / markup sans logique.
- **Regle violee** : item 5.1 (duplication CSS 3+ fois), classee MIN (scoped CSS, sans logique).
- **Remediation** : `@keyframes spin` + `.spinner` globaux dans `App.vue` (ou `shared/ui/AppSpinner.vue`) ; `shared/ui/AppButton.vue`, `AppSwitch.vue`, `DocIcon.vue` consommant `--accent` / `--on-accent`.

### [MIN] Palette de la vue graphe Neo4j recopiee trois fois (perimetre deprecie)

**Statut vs 0.7.3 : non resolu, inchange.**

- **Localisation** : `frontend/src/features/analysis/ui/GraphView.vue:134-147`, `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:113-132`, `frontend/src/features/analysis/legendFilters.ts:34-77`
- **Constat** : `NODE_COLORS`, `KIND_COLORS` et les puces de legende redeclarent la meme table (memes valeurs que `shared/elementColors.ts:14`, reindexees par label Neo4j) ; le commentaire `NodeDetailsPanel.vue:111-112` assume la copie. Vue depreciee, retiree en 0.8.0.
- **Regle violee** : item 5.1 / 5.3, non bloquant.
- **Remediation** : supprimer avec l'ingestion en 0.8.0 ; sinon deriver les tables de `ELEMENT_COLORS`.

### [MIN] `api/analyses.py` : mapping de chunks x3 et resume d'analyse redeclare

**Statut vs 0.7.3 : non resolu, inchange.**

- **Localisation** : `document-parser/api/analyses.py:149` `:173` `:196` ; `document-parser/api/analyses.py:36-41` vs `:119-124` ; `document-parser/api/schemas.py:127` vs `:145`
- **Constat** : construction de `ChunkResponse` ecrite trois fois (deux strictement identiques a partir de dicts, `:173` et `:196`) ; `AnalysisSummaryResponse` redeclare 10 champs d'`AnalysisResponse` ; `list_analysis_summaries` recopie le formatage `str(x) if x else None` de `_to_response`. Le front derive (`AnalysisSummary = Pick<Analysis, …>`, `shared/types.ts:84`).
- **Regle violee** : item 5.1 / esprit 5.6, non bloquant.
- **Remediation** : `class AnalysisResponse(AnalysisSummaryResponse)` et un `_summary_fields(job)` partage ; un `_chunk_from_dict(c)` pour les deux routes d'edition.

### [MIN] Helpers `_utcnow` / `_new_id` recopies x4, avec deux formats d'identifiant

**Statut vs 0.7.3 : non resolu, inchange.** Complement : la divergence touche aussi les ids de `Chunk`.

- **Localisation** : `document-parser/domain/models.py:29-34`, `document-parser/domain/chunk_editing.py:31-36`, `document-parser/services/chunk_service.py:90-95`, `document-parser/services/version_service.py:37-42` ; usage divergent : `document-parser/services/version_service.py:215` vs `document-parser/domain/models.py:242`
- **Constat** : `_new_id` renvoie `str(uuid4())` (36 caracteres) dans `models.py` / `chunk_service.py` et `uuid4().hex` (32) dans `chunk_editing.py` / `version_service.py`. Outre les `ChunkEdit` (`chunk_service.py:478` vs `version_service.py:166`), un `Chunk` restaure depuis une version recoit un id hex (`version_service.py:215`) quand tous les autres chunks recoivent l'id 36 caracteres du `default_factory` (`models.py:242`).
- **Regle violee** : item 5.1, non bloquant.
- **Remediation** : `new_id()` et `utcnow()` publics dans `domain/models.py` (un seul format), importes par les services.

### [MIN] Serialisation Chunk ↔ dict camelCase recopiee dans trois services (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant (identique a `02adc68`), non releve en 0.7.3.

- **Localisation** : Chunk → dict : `document-parser/services/analysis_service.py:43-52` (`_chunk_to_dict`), `document-parser/services/chunk_service.py:98-109` (`_chunk_to_audit_dict`), `document-parser/services/chunk_service.py:851-862` (`_chunk_to_ingestion_dict`), `document-parser/services/version_service.py:45-66` (`_serialize_chunks`) ; dict → Chunk : `document-parser/services/chunk_service.py:112-138` (`_bbox_from_dict`, `_doc_item_from_dict`, `_analysis_chunk_to_canonical`), `document-parser/services/version_service.py:208-226` (`_chunk_from_snapshot`)
- **Constat** : la forme `text / headings / sourcePage / tokenCount / bboxes / docItems` est ecrite 4 fois, et les docstrings assument la copie : `chunk_service.py:852-854` (« modeled after `analysis_service._chunk_to_dict` »), `version_service.py:46-48` (« Mirrors `_chunk_to_dict` in ChunkService — kept independent to avoid an import cycle », reference perimee : `_chunk_to_dict` vit dans `analysis_service`). La derive est deja la : `_chunk_to_audit_dict` serialise `docItems` par `asdict` → cle `self_ref` (`:108`) quand les trois autres ecrivent `selfRef` ; `tokenCount` vaut `c.token_count or 0` dans `_chunk_to_ingestion_dict` (`:859`) et peut etre `null` ailleurs (`:106`, `version_service.py:58`, `analysis_service.py:49`) ; `_doc_item_from_dict` accepte les deux cles (`:118`), `_chunk_from_snapshot` seulement `selfRef` (`version_service.py:223`).
- **Regle violee** : item 5.1 (bloc quasi-identique 4 fois), classe MIN (~10 lignes par copie, sans consommateur front des instantanes d'audit).
- **Remediation** : `chunk_to_wire(c) -> dict` et `chunk_from_wire(raw, document_id) -> Chunk` dans un module sans dependance de service (ex. `domain/chunk_wire.py`), consommes par les trois services — ce qui leve aussi le motif « import cycle » invoque par `version_service`.

### [MIN] Journal `ChunkEdit` construit a la main x10, remplacement de chunkset recopie avec instantanes divergents (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant, non releve.

- **Localisation** : `ChunkEdit(` : `document-parser/services/chunk_service.py:232` `:270` `:302` `:323` `:373` `:432` `:477` `:505`, `document-parser/services/version_service.py:165` `:184` ; remplacement complet de chunkset : `document-parser/services/chunk_service.py:472-514` (rechunk) vs `document-parser/services/version_service.py:160-193` (restore)
- **Constat** : 10 appels `await self._edits.insert(ChunkEdit(id=_new_id(), document_id=…, chunk_id=…, action=…, actor=…, at=…, before/after=…))` ecrits a la main. La sequence « soft-delete + DELETE journalise par chunk existant, `insert_many` + INSERT journalise par nouveau chunk » est ecrite deux fois ; la copie de restore n'enregistre ni `before` ni `after`, la copie de rechunk enregistre `before=_chunk_to_audit_dict(c)` (`:484`) et `after=_chunk_to_audit_dict(c)` (`:512`). Le journal d'audit contient donc des entrees avec ou sans instantane selon le chemin.
- **Regle violee** : item 5.1 (construction repetee 10 fois ; sequence en 2 copies divergentes), non bloquant.
- **Remediation** : un `_journal(document_id, chunk_id, action, actor, at, *, before=None, after=None)` partage (ou une methode de port `ChunkEditRepository.record(...)`) et un `replace_chunkset(document_id, new_chunks, actor)` unique appele par rechunk et restore.

### [MIN] Regles split / merge ecrites deux fois : module domaine non utilise vs service (nouveau, preexistant ; recoupe 01)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant. Recoupe le MAJ 01 « regles split/merge dans le service » (`services/chunk_service.py:335`), vu ici sous l'angle duplication.

- **Localisation** : `document-parser/domain/chunk_editing.py:46-216` (`insert` `:46`, `update` `:80`, `delete` `:104`, `merge` `:116`, `split` `:169`) ; `document-parser/services/chunk_service.py:335-391` (`split_chunk`), `:393-449` (`merge_chunks`)
- **Constat** : `domain/chunk_editing.py` n'est importe par aucun module de production (`git grep chunk_editing` hors `tests/` : 0 ; seul `tests/test_chunk_editing.py` l'utilise). Le service reimplemente les memes operations avec des regles differentes : merge — le domaine prend le plus petit `source_page` (`chunk_editing.py:147`) et accepte des chunks non contigus, le service prend celui du premier (`chunk_service.py:421`), exige la contiguite (`:406`), concatene `bboxes` / `doc_items` (`:412`) et somme les tokens (`:414`) ; split — le domaine ne propage ni `bboxes` ni `doc_items`, le service les propage (`:354`, `:363`). Les tests du domaine valident donc des regles qui ne sont pas celles livrees.
- **Regle violee** : item 5.1 (deux implementations divergentes d'une meme regle metier), non bloquant au titre de 5.1 (2 copies).
- **Remediation** : faire du domaine la source unique (aligner `chunk_editing.merge/split` sur les regles livrees, puis les appeler depuis `ChunkService`), ou supprimer `domain/chunk_editing.py` et ses tests s'il n'a pas vocation a servir. A arbitrer avec la remediation du MAJ 01.

### [MIN] Formatage de date local x4 malgre `shared/format.ts` (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant (copies `AnalysisDetailPage` / `AnalysisLibraryPage` introduites en 0.7.3), non releve.

- **Localisation** : `frontend/src/pages/AnalysisDetailPage.vue:52-56`, `frontend/src/pages/AnalysisLibraryPage.vue:158-162`, `frontend/src/features/history/ui/HistoryList.vue:71-74`, `frontend/src/pages/DocumentsPage.vue:179-182` ; helper existant : `frontend/src/shared/format.ts:26-37` (`formatAbsolute`)
- **Constat** : deux pages recopient le corps de `formatAbsolute` (`Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })`) sans son `try/catch` ; deux autres utilisent `toLocaleString()`. Une meme date s'affiche donc en deux formats selon la page.
- **Regle violee** : item 5.1 (4 copies alors que le helper partage existe), ampleur limitee.
- **Remediation** : importer `formatAbsolute` depuis `@/shared/format` dans les quatre fichiers.

### [MIN] Squelette d'action asynchrone recopie dans les stores Pinia (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant, non releve.

- **Localisation** : `frontend/src/features/chunks/store.ts:51-63` et `:65-77` (`updateText` / `updateTitle`, identiques au champ pres), `:79-93`, `:95-109`, `:111-122` (10 `catch`) ; `frontend/src/features/document/store.ts` (8 `catch`), `frontend/src/features/analysis/store.ts` (7), `frontend/src/features/chunking/store.ts` (3), `frontend/src/features/history/store.ts` (2) ; idiome `(e as Error).message ||` : 41 occurrences dans 16 fichiers
- **Constat** : chaque action reecrit `flag = true; try { … } catch (e) { error.value = (e as Error).message || 'Failed to X'; console.error('Failed to X', e) } finally { flag = false }`, le libelle etant duplique dans la meme action (22 `console.error('Failed…` dans ces 5 stores).
- **Regle violee** : item 5.1 (bloc quasi-identique 3+ fois), classe MIN (boilerplate de quelques lignes).
- **Remediation** : un helper `runAction(flag, error, fallback, fn)` (ou `shared/composables/useAsyncAction.ts`) et `errorMessage(e, fallback)` dans `shared/` ; fusionner `updateText` / `updateTitle` en `updateChunk(docId, chunkId, patch)`.

### [MIN] Datetime → texte ecrit en ligne x13 dans `api/`, deux formats sur le fil (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant, pendant en ecriture du MAJ `_parse_iso`.

- **Localisation** : `str(<datetime>)` : `document-parser/api/analyses.py:39` `:40` `:41` `:122` `:123` `:124`, `document-parser/api/documents.py:33` `:35` `:63`, `document-parser/api/document_chunks.py:56` `:57`, `document-parser/api/document_versions.py:43`, `document-parser/api/stores.py:52`, `document-parser/services/version_service.py:61` `:62` ; `.isoformat()` : `document-parser/services/chunk_service.py:738` (`GET /api/documents/{id}/chunks/pushes`), `document-parser/services/navigation_service.py:95` (MCP)
- **Constat** : le choix du format de sortie est refait a chaque champ. `str(datetime)` produit `2026-11-03 10:00:00+00:00` (separateur espace), `.isoformat()` produit `2026-11-03T10:00:00+00:00` : l'API REST expose donc deux formats pour un meme type de champ (`pushedAt` de `/chunks/pushes` vs `pushedAt` de `api/documents.py:63`).
- **Regle violee** : item 5.1 (expression repetee 13 fois) / 5.3, non bloquant.
- **Remediation** : un `to_iso(dt: datetime | None) -> str | None` partage avec `parse_iso` (cf. MAJ), ou un type `AwareDatetime` serialise par Pydantic dans `api/schemas.py`.

### [INFO] `fetch()` brut dans DownloadDropdown hors du client HTTP centralise

**Statut vs 0.7.3 : inchange.**

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:133`
- **Constat** : seul `fetch()` hors de `shared/api/http.ts`, justifie (lecture `blob()` + `content-disposition`). Aucune config HTTP recopiee.
- **Regle violee** : item 5.5 — observation.
- **Remediation** : optionnelle, `downloadBlob(url)` dans `shared/api/` si un second appelant apparait.

### [INFO] Petites constantes de troncature repetees dans l'infra

**Statut vs 0.7.3 : inchange.**

- **Localisation** : `document-parser/infra/neo4j/queries.py:104` `:128` (`[:200]`, perimetre deprecie), `document-parser/infra/docling_agent_reasoning.py:188` `:204` `:218` (`query[:120]`)
- **Constat** : repetitions locales a leur fichier.
- **Regle violee** : item 5.3 — observation.
- **Remediation** : constantes de module si ces valeurs doivent rester coherentes.

### [INFO] Config MCP vs config Ask : regles communes factorisees, residus paralleles

**Statut vs 0.7.3 : inchange.**

- **Localisation** : `document-parser/domain/mcp_config.py:94` vs `document-parser/domain/app_config.py:77` ; `document-parser/services/mcp_config_service.py:156` vs `document-parser/services/app_config_service.py:103` ; `document-parser/services/mcp_config_service.py:69` vs `document-parser/services/app_config_service.py:106` ; `frontend/src/features/mcp-config/store.ts` vs `frontend/src/features/admin-config/store.ts` ; `frontend/src/features/mcp-config/ui/McpConfigSection.vue:24` `:162` `:223` `:265` vs `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:15` `:40` `:81` `:106`
- **Constat** : precedence env/db, parseurs et erreurs vivent une seule fois dans `services/config_overrides.py`. Restent des paires paralleles (2 copies) : `validate_base_url` / `validate_host_url`, politique d'ecriture divergente (`set_many` complet cote Ask, `replace_namespace` des seules differences cote MCP), deux stores Pinia de meme squelette (seul le MCP factorise `write()`, `mcp-config/store.ts:61`), badge « valeur surchargee » rendu 8 fois sous deux formes.
- **Regle violee** : item 5.1 — observation.
- **Remediation** : au retour d'Ask, aligner sur la politique MCP, un `validate_http_url(url, *, allow_empty)` commun et un composant `ConfigFieldRow` partage.

### [INFO] DTO du fil MCP en miroir des value objects du domain (accepte)

**Statut vs 0.7.3 : inchange.**

- **Localisation** : `document-parser/mcp_adapter/sources_view.py:52` `:71` `:88` `:102` `:113` vs `document-parser/domain/source_map.py:79` `:103` `:125` `:144` et `document-parser/domain/source_bar.py:26`
- **Constat** : contrat publie (schema de sortie des outils, `mcp_adapter/wire.py:1-6`) avec transformation (`neutralise`, `deep_link`, arrondis) : conforme a l'esprit de 5.6. Un champ ajoute au domain doit etre reporte a la main.
- **Regle violee** : item 5.6 — observation, l'item reste conforme.
- **Remediation** : un test de parite des champs.

### [INFO] Deux extractions DoclingDocument → pages coexistent

**Statut vs 0.7.3 : inchange.**

- **Localisation** : `document-parser/infra/docling_pages.py:48` vs `document-parser/infra/serve_converter.py:269` (table de labels propre `:52`)
- **Constat** : le moteur Docling Serve garde une implementation parallele sur dict brut (labels, rendu Markdown des tableaux, `level=0`). Deux copies.
- **Regle violee** : item 5.1 — observation.
- **Remediation** : `DoclingDocument.model_validate(json_content)` puis `extract_pages_detail`, comme `DoclingDocumentImporter`.

### [INFO] Redondances front sous le seuil (nouveau, preexistant)

**Statut vs 0.7.3 : nouveau dans ce rapport** — preexistant.

- **Localisation** : `frontend/src/features/reasoning/api.ts:26` vs `frontend/src/shared/api/http.ts:9` ; `frontend/src/features/document/store.ts:75-79` vs `frontend/src/pages/DocsNewPage.vue:163-167` ; `frontend/src/features/document/ui/DocumentActionsMenu.vue:87-91` vs `frontend/src/features/document/ui/DownloadDropdown.vue:191-198`
- **Constat** : `runReasoning` repasse `'Content-Type': 'application/json'` deja pose par `apiFetch` (redondant, sans divergence : 5.5 reste conforme) ; le controle de taille d'upload `maxMb * 1024 * 1024` est ecrit deux fois avec deux messages (anglais en dur dans le store, i18n `upload.tooLarge` dans la page) ; le « clic a l'exterieur » des menus est ecrit deux fois.
- **Regle violee** : items 5.5 / 5.1 — observation (2 copies chacune).
- **Remediation** : retirer l'en-tete redondant ; `exceedsUploadLimit(file, maxMb)` dans `shared/format.ts` ; `onClickOutside` en composable si un 3e menu apparait.

---

## Delta vs 0.7.3

Base : `release/0.7.3 @ 02adc68` (score 67, 3 MAJ / 10 MIN / 5 INFO).

| Ecart 0.7.3 | Niveau | Statut en 0.7.4 | Verification |
|-------------|--------|-----------------|--------------|
| `_parse_iso` / `_parse_dt` x7 + divergence UTC `analysis_repo` | MAJ | **Toujours present, inchange** | 7 definitions + parse inline, `analysis_repo.py:11-15` sans UTC ; `persistence/*` non modifie |
| Couleurs UI en dur, tokens `--color-*` / `--danger` | MAJ | **Toujours present, inchange** | 33 / 10 / 3 identiques ; inventaire complete (24 replis sur tokens definis) |
| Contrat d'erreur service → HTTP (6 bases, 16 mappings) | MAJ | **Toujours present, inchange** | memes lignes ; complement « document introuvable » x6 et mapping par prefixe de message |
| Pont JSON-RPC MCP Apps | MIN | **Inchange** | seule la ligne 2 de `citation_app.html` a change |
| Import d'analyse x3 | MIN | **Inchange** | memes lignes |
| Defauts / bornes / parse env MCP-Ask | MIN | **Inchange** | lignes `settings.py` +1 ; complement `from_env` (33 defauts recopies) |
| Labels Docling | MIN | **Inchange** | memes lignes |
| `.field-*` formulaires de store | MIN | **Inchange** | perimetre deprecie |
| Bornes de chunking / defauts DTO | MIN | **Inchange** | complement `ChunkPanel.vue:38-39`, litteraux `table_mode` |
| Primitives CSS | MIN | **Inchange** | `McpConfigSection` +1 ; complement `.spinner-sm` x3, icone SVG x4 |
| Palette graphe Neo4j x3 | MIN | **Inchange** | perimetre deprecie |
| `api/analyses.py` chunks x3 / resume | MIN | **Inchange** | memes lignes |
| `_utcnow` / `_new_id` x4 | MIN | **Inchange** | complement : ids de `Chunk` restaures en hex (`version_service.py:215`) |
| `fetch()` brut `DownloadDropdown` | INFO | **Inchange** | `:133` |
| Constantes de troncature | INFO | **Inchange** | — |
| Config MCP vs Ask | INFO | **Inchange** | — |
| DTO MCP miroirs | INFO | **Inchange** | — |
| Extraction pages Serve | INFO | **Inchange** | — |

**Nouveaux ecarts 0.7.4** (tous preexistants, identiques a `02adc68`, non releves en 0.7.3) :
6 MIN (serialisation chunk x4, journal `ChunkEdit` x10 + remplacement de chunkset divergent,
split/merge domaine mort vs service, `formatDate` x4, squelette d'action Pinia, datetime → texte
x13 / deux formats) et 1 INFO (redondances front sous le seuil). Aucune regression introduite
par `02adc68..1de1929`.

**Score : 67 → 67 (delta 0).** Les items 5.1 et 5.3 etaient deja non conformes ; les nouveaux
ecarts ne font basculer aucun autre item.

---

## Remediation : effort, risque et gain de score

Le score est binaire par item. 5.1 est tenu par **deux** MAJ (`_parse_iso`, contrat d'erreur) :
corriger l'un sans l'autre ne rapporte aucun point. 5.3 est tenu par le seul MAJ couleurs.
Convention reprise des rapports precedents : un item bascule a « conforme » quand plus aucun
ecart de niveau MAJ ne le tient, les MIN d'ampleur limitee restant tolerees.

| Action | Item | Effort | Risque | Gain |
|--------|------|--------|--------|------|
| `parse_iso` unique + alignement UTC de `analysis_repo` | 5.1 | S | Faible | 0 seul ; **+17 avec la ligne suivante** |
| Base `ServiceError` + `@app.exception_handler` + suppression des 14 `try/except` et 2 `_raise_for` | 5.1 | M | Moyen | 0 seul ; **+17 avec la ligne precedente** (67 → 83) |
| Tokens couleur : 74 sites (dont 41 dans le perimetre deprecie) + `--on-accent` | 5.3 | M (S pour les 33 sites hors deprecie) | Visuel modere | **+17** (67 → 83) une fois les 74 sites traites ou supprimes |
| Les trois MAJ | 5.1 + 5.3 | M | Moyen | **67 → 100** (12 / 12) |

Quick wins sans effet sur la note mais a cout tres faible :
- `var(--danger, …)` → `var(--error)` (`ReasoningConfigSection.vue:329` `:348` `:369`) et suppression des 24 replis en dur : quelques minutes, prepare le basculement de 5.3 ;
- `formatDate` x4 → `formatAbsolute` (`shared/format.ts:26`) : 4 imports ;
- `useAnalysisImport()` : leve le MIN import x3 ;
- `FURNITURE_LABELS` / `HEADING_LABELS` / `label_of` exposes depuis `domain/parse_index.py` ;
- `new_id()` / `utcnow()` publics dans `domain/models.py` (un seul format d'id) ;
- `_env_bool` dans `infra/settings.py` (8 parses → 1).

---

## Points positifs

- **Config d'override factorisee des sa deuxieme utilisation** : `services/config_overrides.py` porte une seule fois la precedence env → `app_settings` (`require_writable` `:43`, `parse_bool` `:51`, `parse_int_between` `:66`, `pick` `:79`, erreurs `AppConfig*`), consommee par `AppConfigService` et `McpConfigService`.
- **Type partage remonte dans `shared/`** : la remediation 0.7.3 a deplace `ConfigSource` dans `frontend/src/shared/types.ts:5` ; `admin-config` et `mcp-config` l'importent au lieu qu'une feature depende de l'autre. Aucune redeclaration d'un type de `shared/types.ts` dans les features.
- **Cablage MCP partage entre HTTP et stdio** : `bootstrap/factories.py` (`env_mcp_config` `:241`, `build_parse_loader` `:255`, `build_document_tools` `:270`) consomme a l'identique par `bootstrap/mcp_mount.py` et `mcp_stdio.py`.
- **Budgets MCP en un seul endroit** : `services/navigation_config.py` (`NavigationConfig`) lu par le loader, la navigation, la citation, l'image et les sources ; estimation de tokens unique (`domain/navigation.py:327`).
- **Pas de seconde boucle Ask** : la procedure MCP est declarative (`mcp_adapter/prompts.py`), executee par le client avec les memes outils.
- **Palette d'elements unique** : `frontend/src/shared/elementColors.ts:14` (`ELEMENT_COLORS`), consommee par les composants d'analyse depuis le re-audit 0.7.0.
- **Types derives plutot que redeclares** : `AnalysisSummary = Pick<Analysis, …>` (`shared/types.ts:84`).
- **Validation sans desaccord** : bornes MCP / Ask definies cote domain, miroirs front alignes (`features/mcp-config/types.ts:59-62`, `features/admin-config/types.ts:40-41`) ; limite d'upload servie par le backend.
- **Client HTTP integralement centralise** : les 11 `features/*/api.ts` passent par `apiFetch` (`shared/api/http.ts`).
- **Primitives d'accordeon et de pagination partagees** : `shared/ui/AccordionSection.vue`, `AccordionRow.vue`, `accordion.ts`, `shared/composables/usePagination.ts`, `shared/ui/PaginationBar.vue`.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL (la checklist DRY n'a pas d'item de poids 3). Score **67 / 100** (tranche
60-79), identique a 0.7.3. Trois MAJ, sous le seuil bloquant (> 3), tous reconduits a
l'identique : `_parse_iso` x7 avec divergence UTC latente (dette depuis 0.7.0), couleurs UI non
tokenisees (dette depuis 0.7.0), contrat d'erreur service → HTTP recopie (dette relevee en
0.7.3). Aucun n'a ete traite par la remediation 0.7.3, qui ne visait pas l'audit 05. Les 6 MIN et
1 INFO nouveaux sont des duplications preexistantes non relevees jusqu'ici, sans regression
introduite depuis `02adc68`. Condition : plan de remediation des 3 MAJ. Le couple `_parse_iso` +
contrat d'erreur (S + M) fait seul passer 5.1 a conforme (+17) ; les tokens couleur font passer
5.3 (+17), en partie gratuitement avec la suppression de l'ingestion en 0.8.0.

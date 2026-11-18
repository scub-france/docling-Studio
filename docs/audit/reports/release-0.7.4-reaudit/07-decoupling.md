# Rapport d'audit : Découplage

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : working tree de la branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` @ `f7fc791`, avec les PR #401 et #402, + 13 commits locaux #391-#400 + merge)
**Baseline** : `release-0.7.4/07-decoupling.md` (2026-11-13, `eade7fa`, 91/100, GO, 0 CRIT, 1 MAJ, 1 MIN)
**Delta examiné** : `git diff eade7fa a6fb539` (121 fichiers). Changements qui touchent le découplage : rendu des pages par PDF.js (requêtes Range sur le PDF brut), route `/preview` avec `format=png|webp` et `Cache-Control`, cache de previews (port `PreviewImageCache`), listes chargées en « summaries », port `AnalysisDocumentEngine` (#394), mapping d'erreurs centralisé `api/errors.py` (#396), 404 de l'éditeur (#395/#402).

Méthode : lecture statique du working tree. Les suites n'ont pas été relancées (résultats fournis sur `a6fb539` : ruff propre, pytest 1501 passés / 15 skips, eslint, prettier, `vue-tsc` propres, vitest 586 passés, `vite build` OK). Contrôle 7.2.2 : scan `grep` des imports `@/features/…` et relatifs `../../<feature>` dans `frontend/src/features/` hors tests. Couverture `response_model` : scan AST des décorateurs de `document-parser/api/*.py`.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 12 |

Calcul : somme des poids = 35 ; non conforme : 7.4.2 (poids 2). Poids conformes = 33. `33 / 35 × 100 = 94,29` → **94**. Même grille et même lecture des items que la baseline (91), scores comparables.

| Item | Poids | Conforme | Justification (arbre `a6fb539`) |
|------|-------|----------|----------------------------------|
| 7.1.1 REST-only front/back | 3 | oui | PDF.js lit le PDF par `GET /api/documents/{id}/export?format=pdf` (`frontend/src/features/document/ui/usePdfDocument.ts:25-30`) ; aucun fichier ni base partagés |
| 7.1.2 Types TS = schémas Pydantic | 3 | oui | `AnalysisSummary` (`frontend/src/shared/types.ts:85-97`) = `AnalysisSummaryResponse` (`document-parser/api/schemas.py:233-245`) champ pour champ ; types de l'éditeur alignés sur la forme produite (`infra/docling_projector.py:54-55,216-229`) |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | oui | nouveaux appels dans `features/history/api.ts:4-6`, `features/analysis/api.ts:51-53`, `features/document/api.ts:49-51,68-77` ; seul `feature-flags/store.ts:170` appelle `apiFetch` hors `api.ts` (antérieur) |
| 7.1.4 Back testable sans front | 2 | oui | `tests/test_analysis_edits_api.py:10,176,183,195` (TestClient, 404/409) ; `tests/test_api_endpoints.py:277-287` (webp), `:496-521` (summaries) |
| 7.1.5 Pas de logique métier dupliquée | 2 | oui | règles de fusion front = garde UX, le back revalide (`infra/docling_editor.py:217-221`) ; voir INFO |
| 7.2.1 Feature = store + api + ui | 2 | oui | `features/document/ui/{PdfPageCanvas.vue,PdfPagePreview.vue,usePdfDocument.ts}` restent dans `document` ; structure des features inchangée |
| 7.2.2 Frontière barrel + ESLint | 3 | oui | 15 imports inter-features, tous par barrel : `analysis/ui/StructureViewer.vue:64` et `analysis-editor/ui/AnalysisEditor.vue:315` → `document` ; `document/index.ts:2,8` exporte `getPreviewUrl`, `PdfPagePreview` ; règle `frontend/eslint.config.js:28-55` inchangée |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | oui | `AnalysisSummary` ajouté dans `shared/types.ts:85` ; aucun import de `features/*/types` hors de sa feature |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | oui | `document/store.ts:27` → `isEnabled()` ; `reasoning/store.ts:51,55` → action `focusElement` ; `admin-config/store.ts:80,95` → `reload()` |
| 7.3.1 Repos → objets du domaine | 2 | oui | `persistence/analysis_repo.py:72` `find_all_summaries -> list[AnalysisJob]` ; `persistence/analysis_edit_repo.py:52` |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | oui | `grep "from docling\|import docling" services/ domain/` vide ; le `DoclingDocument` ne transite plus par le service (`domain/ports.py:305-332`, `infra/docling_analysis_engine.py:14-19`) |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | oui | aucun SQL ni `aiosqlite` dans `services/`, `api/`, `domain/` ; restent les annotations `Sqlite*Repository` (INFO reconduit) |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | oui | aucune importation `fastapi`/`starlette` dans `services/`, `domain/` ; traduction en un point `api/errors.py:17-31` ; voir INFO `http_status` |
| 7.4.1 Ports = signatures claires, types domaine | 2 | oui | nouveaux ports `PreviewImageCache` (`domain/ports.py:143-151`), `AnalysisDocumentEngine` (`:305-332`), `find_all_summaries` (`:253-255`) |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **non** | `api/schemas.py:200,201,227` (éditeur) et `:437` (store) inchangés ; `api/graph.py:33` |
| 7.4.3 Format de réponse cohérent | 1 | oui | éditeur : introuvable → 404, conflit/indisponible → 409, commande invalide → 400 (`api/errors.py:17-22`) ; enveloppe `{detail}` partout |

---

## Écarts constatés

### [MAJ] `dict` non typé dans les schémas de réponse de l'éditeur et des stores (item 7.4.2)

- **Localisation** :
  - `document-parser/api/schemas.py:200` (`AnalysisEditorResponse.model: dict`), `:201` (`tree: list[dict]`), `:227` (`AnalysisEditHistoryEntryResponse.payload: dict`), `:437` (`StoreResponse.config: dict`, classe `:422`) ; `document-parser/api/graph.py:33` (`GraphNode`, `extra: "allow"`).
  - Production du format : `document-parser/infra/docling_projector.py:216-229` (`_element_dict`, clés camelCase écrites à la main), `:69` (`editor_model_json=json.dumps(model)`), persistance `document-parser/persistence/database.py:265` (`editor_model_json TEXT`), relecture `document-parser/api/analysis_edits.py:58` (`json.loads`), arbre `document-parser/api/analysis_edits.py:48-54` (`_serialize_tree -> dict`).
  - Miroirs front écrits à la main : `frontend/src/features/analysis-editor/types.ts:22-57`, `:71` (`payload: Record<string, unknown>`).
- **Constat** : inchangé depuis le 2026-11-13 (`schemas.py` n'apparaît pas dans `git diff eade7fa a6fb539`). Le modèle d'éléments, l'arbre et le payload de l'historique ne sont pas décrits dans l'OpenAPI. Les noms de champs sont fixés par un adaptateur infra et stockés tels quels en base : un renommage dans `_element_dict` casse le front sans erreur de type ni test de contrat, et exige d'invalider les caches persistés. Aujourd'hui les deux côtés concordent (vérifié champ par champ : `id`, `selfRef`, `parentId`, `type`, `text`, `headingLevel`, `children`, `provenance{page,bbox}`, `editable`, `supportedOperations`, `nonEditableReason`, `baseAnalysisId`, `elements`), donc pas de bug fonctionnel.
- **Règle violée** : 7.4.2 (poids 2).
- **Remédiation** : `EditorElementResponse`, `EditorTreeNodeResponse`, `EditorModelResponse` construits dans `api/analysis_edits.py` depuis `ProjectedAnalysis.elements` / `.tree` (dataclasses du domaine) ; ne plus persister le format filaire, ou le versionner ; `payload` en union discriminée réutilisant les `*EditRequest` (`schemas.py:147-191`). `StoreResponse.config` : modèle par type de store en 0.8.0. Effort M.

### [INFO] Le PDF.js du front repose sur la route d'export pour lire le PDF brut, sans contrat Range explicite

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts:25-30` (`url: getExportUrl(id, 'pdf')`, `disableStream`, `disableAutoFetch`, `rangeChunkSize: 262144`) ; route servante `document-parser/api/documents.py:134-163` (`FileResponse`) ; proxy `nginx.conf.template:23-30` ; dépendance `document-parser/pyproject.toml:10` (`fastapi>=0.115.0,<1.0.0`).
- **Constat** : le support des requêtes `Range` vient de Starlette (`FileResponse`), version verrouillée `starlette 1.6.0` dans `uv.lock` et installée en `uv sync --frozen` par les Dockerfiles. nginx transmet l'en-tête `Range` par défaut et ne compresse que `application/json` : la chaîne fonctionne. Mais rien ne la documente ni ne la teste : aucun test backend n'envoie `Range` ni n'attend un 206, et la borne basse de `pyproject.toml` admet des Starlette sans Range (PDF.js retomberait alors sur un téléchargement complet, plus lent mais correct). La route « export » sert aussi de source de lecture du viewer : un changement de l'export PDF (filigrane, conversion) changerait l'affichage.
- **Suggestion** : un test `TestClient` sur `export?format=pdf` avec `Range: bytes=0-1023` → 206 + `Accept-Ranges` ; ou une route `GET /api/documents/{id}/file` dédiée au contenu brut.

### [INFO] Deux features connaissent l'endpoint `/api/analyses/summaries`

- **Localisation** : `frontend/src/features/history/api.ts:4-6` et `frontend/src/features/analysis/api.ts:51-53`.
- **Constat** : nouveau. Pas d'import croisé, mais le même contrat est appelé depuis deux clients. Même cas que le client de l'éditeur dans `document` (ci-dessous).
- **Suggestion** : `history` consomme `fetchAnalysisSummaries` exporté par le barrel `@/features/analysis` (`features/analysis/index.ts:1`).

### [INFO] Le client HTTP de l'éditeur reste dupliqué dans la feature `document`

- **Localisation** : `frontend/src/features/document/api.ts:20-29` (`fetchDocumentEditedAnalysisResult`, forme `{ result: Analysis }`), appelé par `frontend/src/features/document/store.ts:28` ; client propriétaire `frontend/src/features/analysis-editor/api.ts:10-19`.
- **Constat** : reconduit sans changement.

### [INFO] La page de détail reconstruit une `Analysis` à partir d'un summary

- **Localisation** : `frontend/src/pages/AnalysisDetailPage.vue:109-118`.
- **Constat** : nouveau. Pour afficher vite les pages, la page charge **toute** la liste des summaries, cherche l'id, puis fabrique une `Analysis` avec des valeurs inventées (`hasDocumentJson: false`, contenus `null`) avant de recharger l'analyse complète. Le comportement dépend de la limite de la liste (`persistence/analysis_repo.py:72`, `limit=200`) : au-delà, le premier rendu rapide est perdu (sans erreur, la page retombe sur `fetchAnalysis`). Pas de bug fonctionnel, mais le front comble un manque de route (pas de `GET /api/analyses/{id}/summary`).

### [INFO] Les erreurs du service de preview restent hors de la famille `ServiceError` (#396)

- **Localisation** : `document-parser/services/preview_service.py:14-19` (`Exception` / `ValueError`) ; mapping local `document-parser/api/documents.py:189-200`.
- **Constat** : toutes les autres familles passent par `api/errors.py:http_error` ; la preview garde son mapping propre, plus deux `except` génériques (`ValueError` → 404, `Exception` → 422). Cohérent fonctionnellement, mais à aligner.

### [INFO] Les services portent des codes HTTP (`http_status`)

- **Localisation** : `document-parser/services/errors.py:11-19` et 9 autres modules de `services/` (`grep -rln http_status services` = 10 fichiers).
- **Constat** : les services n'importent ni FastAPI ni Starlette, la traduction en `HTTPException` est faite en un seul point (`api/errors.py:25-31`), donc 7.3.4 reste conforme. Mais le vocabulaire HTTP (404, 409, 503) vit dans la couche service : un transport non-HTTP (MCP) doit le réinterpréter. Le domaine de l'éditeur montre l'alternative : des classes d'erreur sans code, mappées dans `api/errors.py:17-22`.

### [INFO] Séquence d'historique inconnue → 400, pas 404

- **Localisation** : `document-parser/services/analysis_edit_service.py:224-225` (`AnalysisEditError`, « Saved edit #n does not exist ») ; route `PATCH /api/documents/{doc_id}/analysis-edits/history/{sequence}` (`document-parser/api/analysis_edits.py:152`).
- **Constat** : la ressource adressée par le chemin est introuvable mais répond 400. Le front n'est pas trompé : seul `409:` déclenche le bandeau de conflit (`frontend/src/features/analysis-editor/store.ts:295`), le reste va dans `historyError`. Non bloquant.

### [INFO] Règles de fusion recopiées côté front, désormais avec la règle « même label »

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:84-91` vs `document-parser/infra/docling_editor.py:217-221`.
- **Constat** : garde UX ajoutée par #395 pour éviter un 400 ; le back reste l'autorité. Le back publie `supportedOperations` par élément (`infra/docling_projector.py:227`), qui pourrait porter la règle.

### [INFO] La route `/preview` ne documente pas ses réponses binaires

- **Localisation** : `document-parser/api/documents.py:173-187`.
- **Constat** : pas de `response_model` (normal pour un binaire) ni de `responses=` décrivant `image/png` / `image/webp` et `Cache-Control` ; le contrat du nouveau paramètre `format` n'apparaît dans l'OpenAPI que comme enum de requête. Même cas pour `export` (`:134`). Le scan AST ne trouve que ces deux routes et deux `DELETE` de `api/stores.py:168,189` sans `response_model`.

### [INFO] Constats reconduits sans changement (2)

| # | Constat | Localisation vérifiée sur `a6fb539` |
|---|---------|-------------------------------------|
| 1 | Pages et shell important en profondeur les internes de features (`store`, `api`, `ui`) | `frontend/src/pages/DocParseTab.vue:178-190`, `pages/DocWorkspacePage.vue:62-72`, `pages/DocsLibraryPage.vue:209-214`, `pages/AnalysisDetailPage.vue:75,77`, `shared/ui/AppSidebar.vue:55-56`. En léger recul : `StudioPage.vue` et `AnalysisDetailPage.vue:69-70` passent désormais par les barrels |
| 2 | Services annotés avec des repos SQLite concrets | `services/store_service.py:24-26`, `services/chunk_service.py:49-50`, `services/version_service.py:39`, `services/store_backend_resolver.py:43` |

Autres constats de la baseline revérifiés, toujours présents, sans évolution : cycle de barrels `document` ↔ `analysis` (`features/document/store.ts:5`, `features/analysis/ui/AnalysisPanel.vue:61`, et désormais `analysis/ui/StructureViewer.vue:64`) ; bornes MCP recopiées (`features/mcp-config/types.ts:59-62`) ; code HTTP dérivé du texte d'exception (`api/analyses.py:83`) ; URL SPA construite par le back (`services/citation_service.py:292`) ; couplage Starlette dans `bootstrap/mcp_mount.py:41-42,118` ; champs orphelins `Document.stores?` / `chunksStale?` (`shared/types.ts:45,48`) ; règle ESLint sans motif pour `../../<feature>/<fichier>.ts` racine (`eslint.config.js:28-55`). Ils sont regroupés ici et non recomptés un par un.

---

## Delta vs audit du 2026-11-13

| Constat du 2026-11-13 | Statut à `a6fb539` | Preuve |
|-----------------------|--------------------|--------|
| [MAJ] 7.4.2 `dict` dans les réponses de l'éditeur et des stores | **Toujours présent** | `api/schemas.py:200,201,227,437` inchangés |
| [MIN] 7.4.3 document/analyse inconnus → 409 | **Résolu** (#395/#402) | `domain/analysis_editing.py:119` (`AnalysisEditNotFoundError`), levée en `services/analysis_edit_service.py:274,281,285,289`, mappée 404 en `api/errors.py:18` ; testé `tests/test_analysis_edits_api.py:176,183` |
| [INFO] `DoclingDocument` qui transite par le service, pas de port | **Résolu** (#394) | port `domain/ports.py:305-332`, adaptateur `infra/docling_analysis_engine.py:14-19`, service typé `services/analysis_edit_service.py:62` |
| [INFO] Port `DocumentMerger` non câblé | Non revérifié en détail (hors delta) | — |
| [INFO] Client de l'éditeur dupliqué dans `document` | Toujours présent | `features/document/api.ts:20-29` |
| [INFO] Règles de fusion recopiées | Toujours présent, étendu (règle « même label ») | `analysis-editor/commands.ts:84-91` |

Nouveaux constats (tous INFO) : contrat Range implicite du viewer PDF.js ; endpoint summaries appelé par deux features ; `Analysis` reconstruite côté page ; erreurs de preview hors `ServiceError` ; `http_status` dans les services ; 400 pour séquence inconnue ; `/preview` non documentée. Aucun nouvel écart CRIT, MAJ ou MIN.

Score : **91 → 94** (+3, item 7.4.3 redevenu conforme).

---

## Points positifs

- **Contrats front/back des routes changées alignés** : `AnalysisSummary` (`shared/types.ts:85-97`) est un `Pick` d'`Analysis` qui correspond exactement à `AnalysisSummaryResponse` ; `format=webp` côté front (`features/document/api.ts:50`) correspond au `Literal["png", "webp"]` du back (`api/documents.py:179`).
- **Codes d'erreur de l'éditeur propres** : la hiérarchie du domaine distingue introuvable / conflit / indisponible / invalide, le mapping HTTP est en un seul point (`api/errors.py:17-22`), et le front ne traite en conflit que le 409.
- **Le moteur Docling de l'éditeur est derrière un port** (`AnalysisDocumentEngine`) : plus aucun objet Docling dans la couche service.
- **Cache de preview derrière un port** (`PreviewImageCache`, `domain/ports.py:146`), implémenté en infra (`infra/preview_cache.py:13`), câblé au bootstrap (`bootstrap/builder.py:172`).
- **Nouveau code front rangé dans sa feature** : PDF.js est confiné à `features/document/ui/`, exposé par le barrel (`PdfPagePreview`), et `StudioPage.vue` n'importe plus `features/document/api` en profondeur.
- **Couverture `response_model`** : toutes les routes JSON en ont une ; seules les routes binaires (`export`, `preview`) et deux `DELETE` n'en ont pas.

---

## Verdict partiel : GO

Score **94/100**, **0 CRIT**, **1 MAJ** (7.4.2, ouvert depuis 0.7.3, sous le seuil master de > 3), **0 MIN**, 12 INFO. Aucun désaccord de contrat front/back constaté sur les routes modifiées par #401/#402.

Suivi recommandé :
1. [MAJ] 7.4.2 — typer `model`, `tree`, `payload` de l'éditeur avant que des clients externes ne s'appuient dessus (M).
2. [INFO] — test de contrat `Range` → 206 sur `export?format=pdf`, ou route dédiée au fichier brut (S).
3. [INFO] — `history` réutilise `fetchAnalysisSummaries` du barrel `analysis` (XS).

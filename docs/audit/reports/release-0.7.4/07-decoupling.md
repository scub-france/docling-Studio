# Rapport d'audit : Découplage

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Baseline** : `release-0.7.3-reaudit/07-decoupling.md` (94/100, GO, 0 CRIT, 1 MAJ, 0 MIN, 12 INFO) et `release-0.7.3/07-decoupling.md` (89/100)
**Delta examiné** : `git diff 1de1929..eade7fa` (97 fichiers). Changement principal : éditeur d'analyse durable (PR #319/#388 + correctifs #391, #392, #393), derrière `ANALYSIS_EDITOR_ENABLED`.

Méthode : lecture statique du working tree uniquement. ESLint, `vue-tsc` et pytest n'ont **pas** été lancés (consigne : machine occupée). Les commandes de la fiche ont été rejouées en `grep` ; le contrôle 7.2.2 est un scan des imports `@/features/…` et relatifs de `frontend/src/features/` hors tests.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 14 / 16 |
| Score | 91 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 1 |
| Écarts INFO | 18 |

Détail du calcul : somme des poids = 35 ; non conformes : 7.4.2 (poids 2) et 7.4.3
(poids 1) = 3. Poids conformes = 32. `32 / 35 * 100 = 91,43` → **91**.

| Item | Poids | Statut 0.7.4 | Évolution vs re-audit 0.7.3 | Preuve (arbre `eade7fa`) |
|------|-------|--------------|-----------------------------|--------------------------|
| 7.1.1 REST-only front/back | 3 | Conforme | = | nouveau client `frontend/src/features/analysis-editor/api.ts:1-83` via `apiFetch` ; aucun fichier ni base partagés |
| 7.1.2 Types TS = schémas Pydantic | 3 | Conforme | = | `features/analysis-editor/types.ts:8-80` ↔ `document-parser/api/schemas.py:147-232` (union discriminée par `type`, mêmes champs camelCase) ; `HealthResponse.analysis_editor_enabled` (`schemas.py:82`) ↔ `features/feature-flags/store.ts:29` ; `DocumentVersion.chunksSource*` (`shared/types.ts:243-244` ↔ `schemas.py:632-633`) |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | Conforme | = | `features/analysis-editor/api.ts` ; voir INFO « client de l'éditeur dupliqué dans `document` » |
| 7.1.4 Back testable sans front | 2 | Conforme | = | `document-parser/tests/test_analysis_editor_feature_flag.py` (TestClient), `tests/test_api_endpoints.py` |
| 7.1.5 Pas de logique métier dupliquée | 2 | Conforme | = | règles de fusion front = garde UX, le back reste l'autorité (`infra/docling_editor.py:204-221`) ; INFO |
| 7.2.1 Feature = store + api + ui | 2 | Conforme | = | `features/analysis-editor/{api.ts,store.ts,types.ts,commands.ts,ui/,index.ts}` |
| 7.2.2 Frontière barrel + ESLint | 3 | Conforme | = | `analysis-editor/ui/AnalysisEditor.vue:303` → barrel `../../document` ; `document/store.ts:7` → `@/features/feature-flags` ; 0 import profond entre features ; règle `frontend/eslint.config.js:28-55` inchangée |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | Conforme | = | `analysis-editor/types.ts:1` importe `Analysis`, `Page` de `shared/types` ; aucun type de l'éditeur consommé par une autre feature |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | Conforme | = | `document/store.ts:27` appelle `useFeatureFlagStore().isEnabled(...)`, fonction exposée ; `analysis-editor/store.ts` n'utilise aucun autre store |
| 7.3.1 Repos → objets du domaine | 2 | Conforme | = | `persistence/analysis_edit_repo.py:24-60` (`EditStream`, `StoredEditCommand`, `EditedAnalysisCache`) ; `persistence/document_analysis_repo.py:17-21,52-60` |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme (avec réserve) | = | `grep "from docling\|import docling" services/` vide ; réserve en INFO (objet `DoclingDocument` qui transite par le service) |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | Conforme | = | SQL de l'éditeur dans `persistence/analysis_edit_repo.py` et `persistence/database.py:235-269,292-331` ; aucun SQL dans `services/` |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | Conforme | = | erreurs de domaine (`domain/analysis_editing.py:107-116`) mappées en HTTP dans `api/analysis_edits.py:110-117` ; garde de flag en `api/deps.py:46-49` |
| 7.4.1 Ports = signatures claires, types domaine | 2 | Conforme | = | nouveaux ports `domain/ports.py:141-154` (`AnalysisSelectionRepository`, `ChunkSourceRepository`), `:256-274` (`AnalysisEditRepository`), `:99-102` (`DocumentMerger`) ; tous typés domaine |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **Non conforme [MAJ]** | = (écart **étendu** par l'éditeur) | `api/schemas.py:200-201,227` en plus de `:437` et `api/graph.py:32` |
| 7.4.3 Format de réponse cohérent | 1 | **Non conforme [MIN]** | **régression** | `services/analysis_edit_service.py:274` + `api/analysis_edits.py:113-114` : document absent → 409 |

---

## Écarts constatés

### [MAJ] `dict` non typé dans les schémas de réponse — écart étendu par l'éditeur (item 7.4.2)

- **Localisation** :
  - nouveau : `document-parser/api/schemas.py:200` (`AnalysisEditorResponse.model: dict`),
    `:201` (`tree: list[dict]`), `:227` (`AnalysisEditHistoryEntryResponse.payload: dict`) ;
    forme du `model` fabriquée à la main dans l'adaptateur infra
    `document-parser/infra/docling_projector.py:58-63,258-271` (`_element_dict`, clés
    camelCase) puis persistée telle quelle (`editor_model_json`,
    `persistence/database.py:265`) et relue par `api/analysis_edits.py:60`
    (`json.loads`) ; arbre construit par `api/analysis_edits.py:50-56` (`_tree -> dict`).
  - inchangé : `api/schemas.py:437` (`StoreResponse.config: dict`, classe `:422`),
    `api/graph.py:32` (`extra="allow"`).
  - miroirs front : `frontend/src/features/analysis-editor/types.ts:22-57` (types précis,
    donc écrits à la main sans source OpenAPI), `:71` (`payload: Record<string, unknown>`).
- **Constat** : le contrat le plus riche de la release (modèle d'éléments, arbre, payload
  des commandes) n'est pas publié dans l'OpenAPI. Le front le décrit précisément, mais rien
  ne relie cette description au backend : un renommage dans `_element_dict` casse le front
  sans qu'aucun type ni test de contrat ne le signale. De plus, le format filaire est produit
  par une couche infra et **stocké en base** (`edited_analysis_cache.editor_model_json`) :
  changer la représentation HTTP exige de toucher l'adaptateur Docling et d'invalider les
  caches persistés. Les deux anciennes surfaces (ingestion) sont inchangées.
- **Règle violée** : 7.4.2 (poids 2).
- **Remédiation** : modèles Pydantic `EditorElementResponse`, `EditorTreeNodeResponse`,
  `EditorModelResponse` construits dans `api/analysis_edits.py` depuis
  `ProjectedAnalysis.elements` / `.tree` (déjà des dataclasses du domaine,
  `domain/analysis_editing.py:57-90`) ; ne plus persister le format filaire (ou le
  versionner) ; `payload` en union discriminée réutilisant les classes `*EditRequest`
  (`schemas.py:147-191`). Ingestion : solder en 0.8.0 comme prévu. Effort M.

### [MIN] Codes d'erreur des routes de l'éditeur : « document introuvable » répond 409, pas 404 (item 7.4.3)

- **Localisation** : `document-parser/services/analysis_edit_service.py:271-275`
  (`_require_document` lève `AnalysisEditUnavailableError`), `:277-292` (analyse
  inconnue ou d'un autre document : même erreur) ; mapping
  `document-parser/api/analysis_edits.py:110-117` (`Conflict` et `Unavailable` → 409).
  Consommateur : `frontend/src/features/analysis-editor/store.ts:265,299` (tout `409:` est
  traité comme un conflit de séquence).
- **Constat** : partout ailleurs un document ou une analyse inconnus donnent 404 (ex.
  `services/export_service.py:62,111-117` → `api/documents.py`, chunks via
  `ChunkNotFoundError`). Les six routes de l'éditeur renvoient 409, le même code que le
  conflit d'édition concurrente. Le front ne peut pas distinguer « quelqu'un a sauvegardé
  avant vous » de « ce document a été supprimé » ou « cette analyse n'a pas de JSON
  Docling » : il affiche le bandeau de conflit (« recharger / copier / jeter ») dans les
  trois cas.
- **Règle violée** : 7.4.3 (poids 1, « codes d'erreur normalisés »).
- **Remédiation** : `DocumentNotFoundError` / analyse inconnue → 404 ; `Unavailable`
  (pas de JSON canonique) → 409 ou 422 avec un `detail` distinct ; garder 409 pour le seul
  `AnalysisEditConflictError`. Effort S.

### [INFO] Le service de l'éditeur dépend d'adaptateurs sans port ; un `DoclingDocument` transite par lui (réserve sur 7.3.2)

- **Localisation** : `document-parser/services/analysis_edit_service.py:59-61`
  (`editor`, `projector`, `graph_writer` non typés), `:300-311` (`mutation.document`
  passé du premier adaptateur au second) ; `infra/docling_editor.py:26-30`
  (`MutationResult.document: DoclingDocument`) ; `infra/docling_projector.py:33-41`
  (`document: Any`). Même schéma pour `active_result_service=None`
  (`services/chunk_service.py:153`, `services/export_service.py:40`).
- **Constat** : la lettre de 7.3.2 est respectée (aucun import ni type `docling.*` dans
  `services/`, et le service n'appelle aucune méthode de l'objet). Mais l'adaptateur
  `DoclingDocumentEditor` rend bien au service un type de sa bibliothèque, et il n'existe
  aucun port pour l'éditeur ni le projecteur dans `domain/ports.py` : le contrat
  service ↔ infra n'est garanti que par le duck typing. Si le service se mettait à lire
  `mutation.document`, aucun outil ne le signalerait.
- **Suggestion** : un port unique `AnalysisEditEngine.apply_and_project(document_json,
  *, base_analysis_id, commands) -> ProjectedAnalysis` (et `project_serialized`), qui
  garde le `DoclingDocument` dans l'infra ; il rend aussi trivial le passage en thread
  demandé par l'audit 12.

### [INFO] Le client HTTP de l'éditeur est dupliqué dans la feature `document`

- **Localisation** : `frontend/src/features/document/api.ts:20-29`
  (`fetchDocumentEditedAnalysisResult` appelle `/analysis-editor` et suppose la forme
  `{ result: Analysis }`), appelé par `features/document/store.ts:25-34` ; client
  propriétaire : `features/analysis-editor/api.ts:9-18`.
- **Constat** : pas d'import croisé (7.2.2 conforme), mais deux features connaissent le
  même endpoint. Un changement du contrat de l'éditeur doit être reporté dans `document`.
- **Suggestion** : exporter une fonction de lecture du résultat depuis le barrel
  `@/features/analysis-editor`, ou un endpoint dédié « résultat actif » côté back.

### [INFO] Règles de fusion et d'ordre de lecture recopiées côté front

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:59-82`
  (`inReadingOrder`, `mergeValidationMessage`) vs `document-parser/infra/docling_editor.py:89-99`
  (`_in_document_order`, #392) et `:219-221` (labels fusionnables).
- **Constat** : garde UX, le back revalide et réordonne. Le back publie pourtant déjà
  `supportedOperations` par élément (`infra/docling_projector.py:139-149`), que le front
  pourrait utiliser au lieu de recopier la liste de labels.

### [INFO] Champ de contrat orphelin `Document.chunksStale?`

- **Localisation** : `frontend/src/shared/types.ts:48`.
- **Constat** : aucun schéma `DocumentResponse` ne le publie et aucun code front ne le lit
  (la valeur utile est `AnalysisEditorResponse.chunksStale`). Même cas que `stores?`
  (`:45`, INFO 9).

### [INFO] Port `DocumentMerger` et adaptateur `DoclingDocumentMerger` non câblés

- **Localisation** : `document-parser/domain/ports.py:99-102`,
  `document-parser/infra/docling_merger.py:12` ; aucun usage hors tests
  (`grep DoclingDocumentMerger` hors `tests/`).
- **Constat** : contrat publié sans consommateur. À câbler (fusion des lots #344) ou
  retirer.

### [INFO] Feature-flag côté front : échec fermé, bien isolé

- **Localisation** : `frontend/src/features/feature-flags/store.ts:133-135,186`
  (`analysisEditorEnabled` vaut `false` tant que `/api/health` ne l'annonce pas).
- **Constat** : bon découplage de version : un front récent face à un back 0.7.3 masque
  l'éditeur au lieu d'appeler des routes absentes. Noté comme point positif.

### [INFO] Constats reconduits sans changement (12)

Localisations revérifiées sur `eade7fa` pour les fichiers que le delta a touchés ; les
autres fichiers ne figurent pas dans `git diff --stat 1de1929..eade7fa`.

| # | Constat | Localisation vérifiée | Évolution |
|---|---------|-----------------------|-----------|
| 1 | `shared/ui/AppSidebar.vue` importe deux stores de features | `frontend/src/shared/ui/AppSidebar.vue:55-56` | = |
| 2 | Cycle de barrels `document` ↔ `analysis` (et ↔ `chunks`) | `features/document/store.ts:5-6`, `document/ui/DocumentUpload.vue:49`, `document/ui/DocumentActionsMenu.vue:41` | = ; s'y ajoute l'arête `analysis-editor → document` (`AnalysisEditor.vue:303`), sans cycle |
| 3 | Pages important en profondeur les internes de features | `frontend/src/pages/AnalysisDetailPage.vue:72-75` (nouveau : `../features/feature-flags/store`, `../features/document/ui/DownloadDropdown.vue`) | = (étendu) |
| 4 | Bornes MCP recopiées côté front | `features/mcp-config/types.ts:58-62` | = |
| 5 | Code HTTP dérivé du texte d'une exception (import) | `api/analyses.py:83` | = |
| 6 | Contrat d'URL implicite backend → SPA (deep links MCP) | `services/citation_service.py:292` | = |
| 7 | Couplage HTTP étendu à `bootstrap/mcp_mount.py` | `bootstrap/mcp_mount.py:41-42,118` | = |
| 8 | Deux casses pour la notion de page | `features/document/api.ts:55-64` | = (lignes décalées) |
| 9 | Champ orphelin `Document.stores?` | `frontend/src/shared/types.ts:45` | = (+ `chunksStale?`, ci-dessus) |
| 10 | Pré-validation de taille côté front | `features/document/store.ts` (garde UX) | = |
| 11 | Règle ESLint plus étroite que « barrel uniquement » | `frontend/eslint.config.js:28-55` | = |
| 12 | Services annotés avec des repos SQLite concrets | `services/store_service.py:23-25,148-150`, `services/chunk_service.py:48-49`, `services/version_service.py:38,93` | = |

---

## Statut des écarts du re-audit 0.7.3

| Écart 0.7.3 | Statut à `eade7fa` |
|-------------|--------------------|
| [MAJ] 7.4.2 `dict` dans les réponses (ingestion) | **Toujours ouvert**, et étendu à l'éditeur (`schemas.py:200-201,227`) |
| 12 INFO | Reconduits (tableau ci-dessus) |
| — | **Nouveau [MIN]** 7.4.3 : 409 pour « document introuvable » sur les routes de l'éditeur |

---

## Points positifs

- **Nouvelle feature front exemplaire sur la structure** : `analysis-editor/` a son
  `api.ts`, son store, ses types et son barrel ; elle ne consomme `document` que par son
  barrel et ne touche à aucun autre store.
- **Domaine pur pour l'éditeur** : `domain/analysis_editing.py` ne dépend de rien
  (dataclasses + `Literal`), et toute la logique Docling est dans `infra/docling_editor.py`
  et `infra/docling_projector.py`, comme le dit leur docstring.
- **Ports de persistance propres** : sélection d'analyse, provenance des chunks et flux
  d'édition ont chacun un `Protocol` typé domaine ; la transaction d'append + cache est
  derrière `save_commands_and_cache` (`persistence/analysis_edit_repo.py:138-207`).
- **Le back porte la sélection active** : la restauration d'une version choisit
  l'analyse active côté serveur (`services/version_service.py:196-213`), au lieu de la
  laisser au front comme en 0.7.3.
- **Flag front en échec fermé** vis-à-vis d'un back plus ancien.

---

## Verdict partiel : GO

Score **91/100** (94 → 91, −3 points de poids : 7.4.3). **0 CRIT**, **1 MAJ** (7.4.2,
déjà ouvert et désormais étendu à l'éditeur) sous le seuil master de > 3, **1 MIN**
(409 pour « introuvable »).

Suivi recommandé :
1. [MAJ] 7.4.2 — typer `AnalysisEditorResponse.model` / `tree` et le `payload` de
   l'historique avant que des clients externes ne s'appuient sur l'éditeur (M).
2. [MIN] 7.4.3 — 404 pour document/analyse introuvables sur les routes de l'éditeur (S).
3. [INFO] — un port `AnalysisEditEngine` pour sortir le `DoclingDocument` du service ; il
   sert aussi la remédiation de l'audit 12.

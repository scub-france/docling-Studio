# Rapport d'audit : Découplage

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `efc0bc5`

Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/07-decoupling.md`, `a12b744`, 94/100, 0 CRIT / 1 MAJ / 0 MIN / 13 INFO).

Code non exécuté : aucune suite n'a tourné sur ce commit.

Fiche : `docs/audit/audits/07-decoupling.md`. Delta examiné : `git log b5f8c7f..efc0bc5` (15 commits), `git diff b5f8c7f efc0bc5` sur `document-parser/`, `frontend/src/`, `e2e/`, `CHANGELOG.md`.

Méthode : lecture de l'arbre de travail et des deux côtés du diff (`git show b5f8c7f:<chemin>`), sans checkout. L'application n'a pas été importée et l'OpenAPI n'a pas été générée (consigne). Deux scripts en lecture seule, AST seulement, sur deux copies extraites par `git archive` dans le scratchpad :

- liste des routes de `api/*.py` (méthode, chemin, nom du handler, `response_model`, `status_code`) et de tous les champs annotés des classes de `api/` aux deux commits ;
- inventaire des chaînes littérales de `document-parser/` hors tests et hors docstrings aux deux commits (messages `detail`, clés JSON, SQL, en-têtes).

Le reste à la main : middlewares de `main.py`, services appelés par les routes modifiées, projecteur de l'éditeur, types et lecteurs côté front, specs Karate `e2e/api` et `e2e/ui`.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 19 |

Calcul : somme des poids = 35 ; non conforme : 7.4.2 (poids 2). `33 / 35 × 100 = 94,29` → **94**.

Lecture appliquée pour 7.4.2 : la même que le contrôle, item binaire. La fiche dit « pas de `dict` ou `Any` dans les responses » ; il en reste deux (`StoreResponse.config`, `GraphNode` en `extra="allow"`), donc l'item reste non conforme. Lecture alternative : juger l'item sur le périmètre que visait l'écart MAJ (éditeur) et accepter les deux restes, documentés et volontaires. 7.4.2 passerait conforme : **100/100**, 0 MAJ.

| Item | Poids | Conforme | Justification (working tree `efc0bc5`) |
|------|-------|----------|----------------------------------------|
| 7.1.1 REST-only front/back | 3 | oui | aucun fichier ni base partagés ; nouveaux appels (`summaries?documentId=`, `currentAnalysisId`) passent par l'API REST ; nginx inchangé |
| 7.1.2 Types TS = schémas Pydantic | 3 | oui | `EditorElementResponse` (`api/schemas.py:237`) = `EditorElement` (`frontend/src/features/analysis-editor/types.ts:22`) champ pour champ, mêmes nullables ; `EditorTreeNodeResponse` (`:266`) = `EditorTreeNode` (`types.ts:36`) ; `current_analysis_id` (`api/schemas.py:123`) = `currentAnalysisId?: string \| null` (`shared/types.ts:51`). Le payload d'historique reste `Record<string, unknown>` côté TS (`types.ts:71`), plus lâche que l'union Pydantic, sans contradiction (voir INFO) |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | oui | `fetchDocumentAnalysisSummaries` dans `features/analysis/api.ts:64-68` ; aucun nouvel appel HTTP hors `api.ts` (seuls `feature-flags/store.ts:170` et `document/ui/DownloadDropdown.vue:135`, antérieurs) |
| 7.1.4 Back testable sans front | 2 | oui | routes inchangées dans leur forme ; middlewares ASGI purs, testables par `TestClient` |
| 7.1.5 Pas de logique métier dupliquée | 2 | oui | pas de bornes recopiées côté front ; règle « même label » : garde UX front (`analysis-editor/commands.ts:90`), le back revalide (`domain/analysis_editing.py:256-258`). Le repli du front quand `currentAnalysisId` est `null` diverge de la règle du back : relevé en INFO (voir « Accord front / back ») |
| 7.2.1 Feature = store + api + ui | 2 | oui | nouveaux modules rangés dans leur feature (`analysis-editor/{commandStacks,pendingDraft,previewScheduler,mergeSelection}.ts`, `analysis-editor/ui/{AnalysisEditHistoryPanel,EditorBanners}.vue`, `document/ui/{PageRaster.vue,BboxCanvas.logic.ts}`) ; `shared/cssTokens.ts` partagé |
| 7.2.2 Frontière barrel + ESLint | 3 | oui | 16 imports inter-features dans `features/` hors tests, tous par barrel (`@/features/<f>` ou `../../document`) ; aucun `index.ts` modifié entre `b5f8c7f` et `efc0bc5` ; les nouveaux composants n'importent que leur feature et `shared/` |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | oui | `currentAnalysisId` ajouté à `Document` dans `shared/types.ts:49-51` |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | oui | `document/store.ts:6-8` importe une fonction d'API (`fetchAnalysis`) et des actions, comme avant ; `pickWorkspaceVersion` est une fonction pure (`document/store.ts:16`) |
| 7.3.1 Repos → objets du domaine | 2 | oui | `persistence/document_analysis_repo.py` rend des `DocumentAnalysisState` ; `find_summaries_by_document` rend des `AnalysisJob` (`persistence/analysis_repo.py:83`) |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | oui | `grep "from docling\|import docling\|pypdfium2\|pdf2image\|from PIL" services/ domain/` vide |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | oui | aucun SQL ni `aiosqlite` dans `services/` ou `domain/` ; plus aucune annotation `Sqlite*` dans `services/` |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | oui | aucun import `fastapi`/`starlette` dans `services/` ou `domain/`. Deux nouveaux modules Starlette dans `infra/` (`host_guard.py`, `body_limit.py`), sur le modèle de `infra/rate_limiter.py` déjà admis au contrôle : INFO |
| 7.4.1 Ports = signatures claires, types domaine | 2 | oui | nouveaux ports `DocumentFileStore` (`domain/ports.py:146`), `DocumentAnalysisStateRepository` (`:197`), `CurrentAnalysisReader` (`:213`) en types du domaine ou primitifs ; `GraphDriverPool.get -> Any` inchangé (`:575`) |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **non** | l'éditeur est typé ; restent `StoreResponse.config: dict` (`api/schemas.py:590`) et `GraphNode` en `extra="allow"` (`api/graph.py:33`) |
| 7.4.3 Format de réponse cohérent | 1 | oui | erreurs des routes en `{detail}` ; le 413 de l'import est en `{detail}` (`infra/body_limit.py:65-66`) ; le 421 du contrôle `Host` est en texte brut, en dehors des routes et opt-in : INFO. Lecture stricte (le 421 casse l'enveloppe) : 7.4.3 non conforme, MIN, score 91 |

---

## Écarts constatés

### [MAJ] `dict` non typé dans deux schémas de réponse (item 7.4.2)

- **Localisation** : `document-parser/api/schemas.py:590` (`StoreResponse.config: dict`) ; `document-parser/api/graph.py:28-33` (`GraphNode`, `model_config = {"extra": "allow"}`).
- **Constat** : **réduit**. `efc0bc5` type tout l'éditeur : `AnalysisEditorResponse.model` → `AnalysisEditorModelResponse` (`api/schemas.py:259`), `tree` → `list[EditorTreeNodeResponse]` (`:266`), `AnalysisEditHistoryEntryResponse.payload` → union de sept modèles (`:364-372`, `:380`), tous en `extra="forbid"`. `_serialize_tree -> dict` est remplacé par `_to_tree_node_response` (`api/analysis_edits.py:49-55`). Restent les deux champs laissés volontairement (commit `efc0bc5`) : la configuration d'un store, polymorphe selon son type, et les nœuds du graphe Neo4j.
- **Règle violée** : 7.4.2 (poids 2), lecture binaire du contrôle.
- **Remédiation** : `StoreResponse.config` en union par `kind` de store ; `GraphNode` avec des propriétés déclarées, ou laissé tel quel jusqu'au retrait du module Neo4j prévu en 0.8.0. Effort S à M.

### [INFO] Le null de `currentAnalysisId` n'a pas le même sens des deux côtés (bug fonctionnel probable)

- **Localisation** : back `document-parser/domain/models.py:207-208` (une ligne d'état dont l'analyse active est `NULL` = pas d'analyse courante, sans repli), `persistence/database.py:90` (`ON DELETE SET NULL`), `services/reasoning_service.py:103-105` (Ask → 404) ; front `frontend/src/features/document/store.ts:16-24` (`pickWorkspaceVersion` retombe sur la version la plus récente), `:172` et `:206` (`doc.currentAnalysisId ?? version?.analysisId`).
- **Constat** : nouveau (`4939413`). Après suppression de l'analyse active, le back n'a plus d'analyse courante : Ask répond 404 `"No completed analysis with document_json for <id>"`, les outils MCP sans ancre n'ont rien, comme l'annonce le CHANGELOG. Le workspace, lui, ouvre la dernière version et charge son analyse. L'utilisateur voit une analyse dans la vue Parse et Ask refuse de lire le document. Deuxième cas : si aucune version ne porte l'analyse courante, le front charge l'analyse courante mais épingle `versions[0]` dans l'historique (`store.ts:170-172`), donc la ligne marquée active n'est pas celle qui est affichée.
- **Suggestion** : décider d'une seule règle. Soit le workspace affiche un état « aucune analyse courante » quand `currentAnalysisId` est `null` et qu'une ligne d'état existe, soit le back expose le repli. Lecture stricte de 7.1.5 (règle métier recopiée et divergente) : 7.1.5 non conforme, MAJ, score 89.

### [INFO] `/preview` : statuts et `detail` changés, absents du CHANGELOG

- **Localisation** : `document-parser/api/documents.py:161-177` (seul `except ServiceError`) ; `document-parser/services/preview_service.py:80-97`, `:121-139` (`_translate_pdf_read_errors`).
- **Constat** : nouveau (`ac7ac17`). À `b5f8c7f`, la route attrapait tout : `ValueError` → 404 `str(e)`, `FileNotFoundError` → 404, `OSError` → 422 `"Failed to read PDF file"`, toute autre exception → 422 `"Failed to generate preview"`. Désormais seules les erreurs levées en lisant le PDF sont traduites. Une erreur de base de données ou du cache répond 500 au lieu de 422 : c'est voulu, le message de commit le dit. Une `ValueError` hors rendu répond 422 `"Failed to generate preview"` dans le bloc de lecture, ou 500 avant (`find_by_id`), au lieu de 404 avec le texte de l'exception : le message de commit ne le nomme pas. Aucun adaptateur actuel ne lève de `ValueError` à ces endroits (`infra/document_file_store.py:57-69`), donc ce n'est pas observable aujourd'hui. Les cas nominaux (200, 400 hors plage, 404 document, 404 page, 404 fichier absent, 422 PDF illisible) sont identiques.
- **Suggestion** : une ligne au CHANGELOG (« erreur interne de preview/pages : 500 au lieu de 422 »).

### [INFO] 421 et 413 : ce que voit le front

- **Localisation** : `document-parser/infra/host_guard.py:110-112` (`PlainTextResponse("Invalid Host header", 421)`), ajouté le plus à l'extérieur (`main.py:116-118`), donc sans en-têtes CORS ; `infra/body_limit.py:65-67` (413 JSON `{"detail": "Docling JSON too large (max N MB)"}`), à l'intérieur de CORS (`main.py:92-101`) ; front `frontend/src/shared/api/http.ts:16-18`, `:26-27` ; `Dockerfile:61` et `docker-compose.yml:213` (`NGINX_MAX_BODY_SIZE=200M`), `docker-compose.yml:174` (`MAX_IMPORT_SIZE_MB` 200).
- **Constat** : nouveau. Le 421 n'est pas en JSON : le front affiche `API error: 421`, sans explication. Il ne touche que des `Host` non listés, et la vue Studio passe par nginx ou par un `Host` loopback, toujours accepté. Le 413 de l'import est lu correctement en développement (`413: Docling JSON too large (max 200 MB)`, affiché par `analysis/ui/AnalysisImportButton.vue:53`, `document/ui/DocumentActionsMenu.vue`, `document/ui/DocumentUpload.vue:120-121`). Derrière nginx, avec les valeurs par défaut, les deux limites sont égales (200 Mio) : nginx coupe en premier avec sa page HTML, et le front n'affiche que `API error: 413`.
- **Suggestion** : 421 en `{"detail": ...}` pour `/api` ; une valeur par défaut de `NGINX_MAX_BODY_SIZE` un peu au-dessus de `MAX_IMPORT_SIZE_MB`.

### [INFO] Un 422 de borne à l'enregistrement remplace tout l'éditeur

- **Localisation** : bornes `document-parser/api/schemas.py:155-166`, `:172`, `:177-178`, `:202`, `:217-219` ; front `frontend/src/features/analysis-editor/store.ts:263-266` (save → `error`), `ui/AnalysisEditor.vue:118` (`v-else-if="store.error"`) ; preview `store.ts:224-226` (bandeau).
- **Constat** : nouveau. Le front n'a pas de borne côté client et n'en a pas besoin : 1 000 000 caractères par texte, 100 000 ids par fusion ou suppression, 10 000 commandes par requête sont hors d'atteinte en usage normal (la sélection de fusion ne prend que des paragraphes, les commandes sont regroupées par `coalesceCommands`). Si un 422 arrive à l'enregistrement, l'éditeur entier laisse place au message brut de Pydantic (`422: body.commands.0.text: String should have at most 1000000 characters`). Les commandes en attente restent dans le stockage local. Au preview, le même 422 s'affiche dans le bandeau.
- **Suggestion** : traiter un 422 d'enregistrement comme `previewError`, dans un bandeau, sans masquer l'éditeur.

### [INFO] Les réponses de l'éditeur valident aussi en production

- **Localisation** : `document-parser/api/analysis_edits.py:59-62` (`AnalysisEditorModelResponse.model_validate(...)`), commentaire `api/schemas.py:223-225` ; projecteur `infra/docling_projector.py:219-232`.
- **Constat** : nouveau. Le commentaire annonce qu'une clé ajoutée par le projecteur sans le contrat « doit faire échouer les tests ». Elle fera aussi échouer en production toutes les routes qui renvoient le modèle (`GET analysis-editor`, `POST preview`, `PATCH history/{seq}`, `POST rebuild`) avec un 500. Aujourd'hui, les onze clés émises (`id`, `selfRef`, `parentId`, `type`, `text`, `headingLevel`, `children`, `provenance{page,bbox}`, `editable`, `supportedOperations`, `nonEditableReason`) correspondent exactement au modèle, et elles n'ont pas changé depuis `051ec3f` (introduction de l'éditeur, absent de 0.7.3). Les caches d'éditions déjà persistés ont donc la bonne forme. Les payloads stockés aussi : `_to_edit_commands` (`api/analysis_edits.py:87-108`) et le basculement (`services/analysis_edit_service.py:195-196`) écrivent toujours toutes les clés, et chaque forme ne correspond qu'à un seul des sept modèles.
- **Suggestion** : rien à changer si ce choix est assumé ; le dire dans le commentaire.

### [INFO] `currentAnalysisId` vaut `null` aussi dans la liste

- **Localisation** : `document-parser/api/schemas.py:120-123` (« Only on `GET /api/documents/{id}` ») ; `api/documents.py:87-90` (la liste construit la même réponse sans le champ, donc `null`) ; `frontend/src/shared/types.ts:49-51`.
- **Constat** : nouveau. La liste et l'upload émettent `"currentAnalysisId": null`, comme `storeLinks`. Dans la liste, `null` ne veut donc pas dire « pas d'analyse courante ». Aucun consommateur ne lit le champ depuis la liste : seuls `loadWorkspace` et `reloadWorkspaceVersions` le lisent, après `fetchDocument` (`document/store.ts:170-172`, `:198-206`). Pas de bug aujourd'hui. Même famille : `GET /api/analyses/summaries?documentId=` (valeur vide) renvoie la liste non filtrée (`api/analyses.py:119-123`) ; le front encode toujours un id non vide (`features/analysis/api.ts:66`).

### [INFO] Payload d'historique typé côté back, libre côté front

- **Localisation** : `frontend/src/features/analysis-editor/types.ts:71` ; lecteurs `ui/AnalysisEditHistoryPanel.vue:15-16` (`payload.active`, `payload.targetSequence`), `:75-80` (affichage générique des clés).
- **Constat** : nouveau. Les clés lues existent dans `SetCommandActivePayloadResponse` (`api/schemas.py:355-361`). L'union du back n'a pas de pendant TS.
- **Suggestion** : union discriminée par `commandType` dans `types.ts`.

### [INFO] Deux middlewares Starlette de plus dans `infra/`

- **Localisation** : `document-parser/infra/host_guard.py:22-28`, `infra/body_limit.py:13-18`.
- **Constat** : nouveau. Même modèle que `infra/rate_limiter.py`. Aucun service ni le domaine ne les importent : 7.3.4 reste conforme. Un changement de framework HTTP toucherait trois fichiers de `infra/` en plus de `api/` et `main.py`.

### [INFO] Constats du contrôle reconduits sans changement

| # | Constat | Localisation vérifiée sur `efc0bc5` |
|---|---------|-------------------------------------|
| 1 | Contrat `Range` du viewer porté par la route d'export | `api/documents.py:117-157` ; borne `pyproject.toml:10` (`fastapi>=0.115.0`) inchangée |
| 2 | Client HTTP de l'éditeur dupliqué dans `document` | `features/document/api.ts:20`, appelé par `features/document/store.ts:44` |
| 3 | La page de détail reconstruit une `Analysis` depuis un summary | `pages/AnalysisDetailPage.vue:107-128` ; charge toute la liste (200 lignes au plus) pour trouver un id |
| 4 | Les services portent des codes HTTP (`http_status`) | 14 fichiers de `services/` (12 au contrôle, en comptant `errors.py`) : déplacements vers `chunk_errors.py` et `chunk_push_service.py`, sans nouveau code |
| 5 | Séquence d'historique inconnue → 400 | `services/analysis_edit_service.py:186` (`AnalysisEditError`, sous-classe de `ValueError`) |
| 6 | Règles de fusion recopiées côté front | `analysis-editor/commands.ts:90` ; règle back déplacée dans `domain/analysis_editing.py:256-258` |
| 7 | `/preview` et `/export` ne documentent pas leurs réponses binaires | `api/documents.py:117,160` |
| 8 | Port `GraphDriverPool.get -> Any` | `domain/ports.py:575` |
| 9 | `parseAnalysisPages` réexporté par le barrel `analysis-editor` | `features/analysis-editor/types.ts:89` |
| 10 | Pages et shell importent les internes des features | `pages/*.vue`, `app/*` ; `DocsLibraryPage.vue:212` remplace `fetchDocumentAnalyses` par `fetchDocumentAnalysisSummaries` au même chemin profond, même compte |
| 11 | Autres constats regroupés du contrôle | cycle de barrels `document` ↔ `analysis` (`document/store.ts:6`, `analysis/ui/AnalysisPanel.vue:61`, `analysis/ui/StructureViewer.vue:64`) ; bornes MCP recopiées (`features/mcp-config/types.ts`) ; couplage Starlette de `bootstrap/mcp_mount.py` ; champs orphelins `Document.stores?` (`shared/types.ts:45`) ; motif ESLint sans cas `../../<feature>/<fichier>` |

---

## Delta vs contrôle

| Constat du contrôle (`a12b744`) | Statut à `efc0bc5` | Preuve |
|--------------------------------|--------------------|--------|
| [MAJ] 7.4.2 `dict` dans les réponses éditeur / stores | **Réduit**, toujours non conforme | éditeur typé `api/schemas.py:237-372` ; restent `:590` et `api/graph.py:33` |
| [INFO] Contrat `Range` implicite | Inchangé | `pyproject.toml:10` |
| [INFO] Client éditeur dupliqué dans `document` | Inchangé | `features/document/api.ts:20` |
| [INFO] `Analysis` reconstruite par la page de détail | Inchangé | `pages/AnalysisDetailPage.vue:107-128` |
| [INFO] Deux `except` génériques dans `/preview` | **Résolu** | `api/documents.py:169-172` ne garde que `except ServiceError` ; traduction en un point, `services/preview_service.py:121-139` |
| [INFO] `http_status` dans les services | Inchangé (fichiers déplacés) | 14 fichiers |
| [INFO] Séquence inconnue → 400 | Inchangé | `services/analysis_edit_service.py:186` |
| [INFO] Règles de fusion recopiées | Inchangé | `commands.ts:90` / `domain/analysis_editing.py:256` |
| [INFO] `/preview`, `/export` sans réponses documentées | Inchangé | `api/documents.py:117,160` |
| [INFO] `GraphDriverPool.get -> Any` | Inchangé | `domain/ports.py:575` |
| [INFO] `parseAnalysisPages` réexporté | Inchangé | `analysis-editor/types.ts:89` |
| [INFO] `/pages` 500 → 422 sur erreur inattendue | **Résolu** | `services/preview_service.py:103-108` : `find_by_id` hors du bloc de traduction, une erreur de base répond 500 |
| [INFO] Imports profonds depuis `pages/` et constats regroupés | Inchangés | voir tableau ci-dessus |

Nouveaux constats (INFO) : null de `currentAnalysisId` interprété différemment ; `/preview` statuts hors CHANGELOG ; 421 et 413 vus par le front ; 422 de borne qui masque l'éditeur ; validation en production des réponses de l'éditeur ; `currentAnalysisId: null` dans la liste ; payload d'historique non typé côté TS ; deux middlewares Starlette dans `infra/`. Aucun nouvel écart CRIT, MAJ ou MIN.

Score : **94 → 94** (=). 7.4.2 est réduit mais garde deux `dict` ; aucun autre item ne change d'état.

---

## Contrats modifiés

Comparaison `b5f8c7f` → `efc0bc5` de `api/*.py`, `api/schemas.py`, `main.py` et des services appelés. Aucune route ajoutée ni supprimée, aucun handler renommé (operationIds identiques par construction : mêmes noms de fonctions décorées), aucun champ ni alias Pydantic renommé ou supprimé (scan AST des classes de `api/`). Outils et prompts MCP : `mcp_adapter/server.py` et `mcp_adapter/prompts.py` absents du diff ; `sources_view.py` garde ses deux outils, le code déplacé dans `sources_card.py` et `sources_text.py` est identique ligne à ligne (seule différence : `“` écrit en littéral).

| Route / surface | Ce qui change | Voulu ? | CHANGELOG `[Unreleased]` |
|-----------------|---------------|---------|--------------------------|
| `GET /api/documents/{id}` | + `currentAnalysisId: string \| null` (sélection active, ou dernière analyse parsée pour un document sans ligne d'état) | voulu (`4939413`) | oui (« Doc workspace opens the active analysis ») |
| `GET /api/documents`, `POST /api/documents/upload` | + `currentAnalysisId: null` sur chaque document (même schéma, champ jamais rempli) | effet de bord du schéma partagé, sans conséquence | non |
| `GET /api/documents/{id}/analysis-editor`, `POST …/analysis-edits/preview`, `PATCH …/analysis-edits/history/{sequence}`, `POST …/analysis-edits/rebuild` | réponse `model` et `tree` typés, `extra="forbid"` ; JSON identique ; une clé imprévue du projecteur donnerait 500 | voulu (`efc0bc5`) | oui (« Analysis editor API schemas ») |
| `GET …/analysis-edits/history` | `payload` typé (union de 7 modèles) ; JSON identique | voulu | oui |
| `POST …/analysis-edits`, `POST …/analysis-edits/preview` (requêtes) | bornes : id et séparateur ≤ 1 000, texte ≤ 1 000 000, listes d'ids ≤ 100 000, commandes ≤ 10 000 ; 422 au-delà | voulu | oui |
| `GET /api/analyses/summaries` | + paramètre `documentId` (alias), filtré et sans plafond ; sans paramètre : 200 plus récentes, comme avant | voulu | oui (« Analysis summaries by document ») |
| `POST /api/analyses/import` | 413 `{"detail": "Docling JSON too large (max N MB)"}` au-delà de `MAX_IMPORT_SIZE_MB` (200 par défaut, 0 = pas de limite), avant la validation du corps | voulu | oui (« Import size limit ») |
| `/api/*` (toutes) | 421 texte `Invalid Host header` si `API_ALLOWED_HOSTS` est défini et que le `Host` n'est ni listé ni loopback ; rien si non défini | voulu | oui (Security) |
| `GET /api/documents/{id}/preview` | erreur hors lecture du PDF (base, cache) : 500 au lieu de 422 ; `ValueError` hors rendu : 422 `"Failed to generate preview"` (ou 500 avant la lecture) au lieu de 404 `str(e)` ; nominal identique | 500 voulu (message de `ac7ac17`) ; 404 → 422 non nommé, non observable avec les adaptateurs actuels | non |
| `GET /api/documents/{id}/pages` | erreur de base : 500 au lieu de 422 (retour au comportement de `a6fb539`) ; nominal identique | voulu (`ac7ac17`) | non |
| `POST /api/documents/{id}/reasoning` (Ask) | lit l'analyse courante au lieu de la dernière terminée ; 404 si l'analyse active a été supprimée ; mêmes statuts et même `detail` | voulu (`4939413`) | oui |
| MCP `verify_citation` (`stale_version`) | sens : « l'ancre ne vise plus la parse courante » ; texte du `detail` : `…pins a parse that is no longer current: <id> is.` au lieu de `…pins an earlier parse: <id> is now the current one.` | voulu (`4939413`, `c9ea953`) | oui (sens), texte non cité |
| MCP outils sans ancre (`get_outline`, `read_element`, `find_documents`…) | lisent l'analyse courante | voulu | oui |
| Config admin (`providerType`) | inchangé dans l'API (`api/schemas.py:940`, `:955`) ; seule l'énumération interne `LLMProviderType` et la propriété `OllamaProvider.type` disparaissent | voulu | oui (Deprecated `LLM_PROVIDER_TYPE`) |
| Routes de chunks | messages et statuts identiques (`chunk_errors.py`, règles dans `domain/chunk_editing.py` avec les mots de l'ancien service) | voulu, sans changement | sans objet |
| Éditeur : conflits de séquence | deux libellés conservés (`domain/analysis_editing.py:209-212`) | sans changement | sans objet |

Seule différence non annoncée et non nommée : le 404 → 422 d'une `ValueError` hors rendu dans `/preview`, inatteignable aujourd'hui. Le passage à 500 des erreurs internes de `/preview` et `/pages` est voulu mais absent du CHANGELOG.

---

## Accord front / back

| Surface | Back | Front | Accord |
|---------|------|-------|--------|
| Modèle de l'éditeur | `api/schemas.py:228-262` : 11 clés par élément, `text`, `parentId`, `headingLevel`, `nonEditableReason` nullables et toujours émis ; `bbox` 4 nombres | `analysis-editor/types.ts:3-46`, mêmes clés et nullables ; le front lit `id`, `type`, `editable`, `text`, `selfRef`, `provenance`, `supportedOperations`, `headingLevel`, `nonEditableReason` | oui. Les `self_ref` en snake_case lus dans `AnalysisEditor.vue:264,378` viennent de `pages_json`, pas du modèle |
| Arbre | `EditorTreeNodeResponse` (`api/schemas.py:266-273`) | `EditorTreeNode` (`types.ts:36-41`) ; lit `elementId`, `label`, `type`, `children` | oui |
| Payloads d'historique | 7 modèles, toutes clés émises, `null` pour les cibles de déplacement absentes | `AnalysisEditHistoryPanel.vue:15-16` lit `payload.active`, `payload.targetSequence` ; `:75-80` affiche les autres clés | oui ; `active: bool \| None` émis en `null` pour `setCommandActive`, type TS `boolean \| null` (`types.ts:74`) |
| `currentAnalysisId` | nom camelCase, `str \| None`, rempli seulement sur `GET /{id}`, `null` ailleurs | `shared/types.ts:51` optionnel et nullable ; lu seulement après `fetchDocument` | types d'accord ; **sens du `null` divergent** (INFO, `document/store.ts:16-24,172,206` vs `domain/models.py:207-208`) |
| Summaries filtrés | `documentId` en alias de requête (`api/analyses.py:110`) | `?documentId=${encodeURIComponent(docId)}` (`features/analysis/api.ts:66`), utilisé par `DocsLibraryPage.vue:345` ; `fetchDocumentAnalyses` n'a plus aucun appelant | oui ; même compte qu'avant (l'ancien appel `/api/analyses?documentId=` n'avait pas de plafond non plus) |
| Bornes de l'éditeur | 422 au-delà | pas de borne client ; 422 affiché brut, et à l'enregistrement il masque l'éditeur (`AnalysisEditor.vue:118`) | contrat compatible, présentation à revoir (INFO) |
| 413 import | JSON `{detail}` | `http.ts:24-29` lit `detail` | oui en direct ; derrière nginx aux valeurs par défaut, nginx répond avant (INFO) |
| 421 `Host` | texte brut, sans CORS | `http.ts:27` ignore le corps non JSON : `API error: 421` | message générique (INFO) |

Aucun champ lu par le front qui ne serait pas émis par un modèle `forbid`, aucun nullable que le front supposerait présent. Un seul désaccord de sens : le `null` de `currentAnalysisId`.

### Specs e2e

| Spec | Ce qu'elle vérifie | Toujours valide ? |
|------|--------------------|-------------------|
| `e2e/api/src/test/resources/documents/preview.feature:7-45` | 200 PNG, DPI, 400 `out of range`, 404 document inconnu | oui : cas nominaux inchangés |
| `e2e/api/.../documents/crud.feature:28`, `upload.feature:13` | `match response contains docSchema` (`common/data/schemas/document.json`, 6 clés) | oui : `contains` tolère `currentAnalysisId` |
| `e2e/api/.../workflows/full-happy-path.feature:23` | preview 200 | oui |
| `e2e/api/.../analyses/*.feature`, `health/health.feature` | routes non modifiées | oui |
| `e2e/ui/.../analyses/analysis-editor.feature` (≈ l. 49-55) | `GET analysis-editor` : `appliedThroughSequence`, `model.elements[*].text` | oui : JSON identique |
| `e2e/ui/.../documents/doc-history-drawer.feature:52-61` | la plus récente des deux analyses est active, puis l'ancienne après « Set as current » | oui par lecture : l'analyse terminée devient active (`persistence/analysis_repo.py:179-194`), le workspace épingle sa version |

Aucune spec ne vérifie un 422 ou un 500 de `/preview`, le summaries filtré, l'import, ni n'envoie de `Host` étranger ; la CI ne définit ni `API_ALLOWED_HOSTS` ni `MAX_IMPORT_SIZE_MB`. **Aucune spec ne devrait échouer** du fait des contrats modifiés.

### Non vérifié sans exécution

- Que Pydantic valide bien chaque payload stocké contre l'union non discriminée (sélection « smart ») et le sérialise avec les alias camelCase, et que FastAPI accepte l'aller-retour `model_dump` → revalidation avec `extra="forbid"` : relu, pas exécuté.
- Que `Field(max_length=...)` sur les listes et `Annotated[str, Field(max_length=...)]` répondent bien 422 avec le message attendu.
- L'OpenAPI réel (non généré, consigne) : noms de schémas, `anyOf` du payload, paramètre `documentId`.
- L'ordre réel des middlewares (413 avec en-têtes CORS, 421 sans) et le comportement de nginx face aux 413.
- Les réponses MCP réelles et les tests backend existants qui construiraient des réponses de l'éditeur à la main.

---

## Points positifs

- **L'éditeur a enfin un contrat HTTP** : modèle, arbre et historique typés, avec les mêmes noms et nullables que les types TypeScript, et un JSON inchangé.
- **Aucun renommage caché** : routes, handlers, champs et alias Pydantic, outils et prompts MCP identiques ; les changements de contrat sont nommés dans les commits et, sauf `/preview` et `/pages`, dans le CHANGELOG.
- **Erreurs de preview en un point** : la route ne garde qu'un `except ServiceError` ; les deux INFO du contrôle sur `/preview` et `/pages` sont résolus.
- **Une seule notion d'« analyse courante » côté back** : Ask, MCP, l'éditeur, l'export et le workspace lisent la même résolution (`services/current_analysis.py`).
- **Frontières front tenues malgré cinq refactorings** : aucun barrel modifié, tous les imports inter-features passent par `index.ts`.
- **Nouvelles options sans effet par défaut** : `API_ALLOWED_HOSTS` vide ne change rien, `MAX_IMPORT_SIZE_MB` est aligné sur nginx.

---

## Verdict partiel : GO

Score **94/100** (inchangé), 15/16 items conformes, **0 CRIT**, **1 MAJ** (7.4.2, réduit à `StoreResponse.config` et `GraphNode`), **0 MIN**, 19 INFO. Lecture alternative de 7.4.2 : 100/100. Les contrats changés le sont volontairement, et le front et le back s'accordent sur les types. Le point à traiter avant la release est fonctionnel : le `null` de `currentAnalysisId` ne veut pas dire la même chose pour le workspace et pour Ask/MCP.

Suivi recommandé :
1. [INFO, bug probable] Aligner le workspace sur la règle du back quand `currentAnalysisId` est `null` (S).
2. [INFO] CHANGELOG : erreurs internes de `/preview` et `/pages` en 500 (XS).
3. [INFO] 421 en `{detail}` ; `NGINX_MAX_BODY_SIZE` au-dessus de `MAX_IMPORT_SIZE_MB` par défaut (XS).
4. [MAJ] 7.4.2 — typer `StoreResponse.config` par type de store en 0.8.0 (M).

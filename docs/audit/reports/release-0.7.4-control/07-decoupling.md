# Rapport d'audit : Découplage

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : working tree de la branche `fix/0.7.4-editor-followups` @ `a12b744`
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`release-0.7.4-reaudit/07-decoupling.md`, 94/100, 0 CRIT, 1 MAJ, 12 INFO)
**Delta examiné** : `git log a6fb539..a12b744` (15 commits), `git diff a6fb539 a12b744` (232 fichiers, dont 115 sous `frontend/src`, `document-parser/api`, `mcp_adapter`, `nginx`).

Méthode : lecture du working tree et des diffs ; aucun checkout. Le contrat HTTP et MCP a été comparé par génération, pas par lecture des messages de commit :

- **OpenAPI** : `app.openapi()` généré aux deux commits (copie de `a6fb539` extraite par `git archive` dans le scratchpad, même `.venv`, `DB_PATH`/`UPLOAD_DIR` pointés vers le scratchpad, routeur `ingestion` ajouté à la main pour qu'il figure dans le document). Les deux JSON triés font 119 864 octets et sont **identiques octet pour octet** (45 chemins, 58 operationIds, 75 schémas).
- **MCP** : `build_mcp_server` construit aux deux commits pour les 4 combinaisons `apps` × `citation_card`, `list_tools()` + `list_prompts()` sérialisés : **identiques** (noms, descriptions, schémas d'entrée et de sortie, `_meta`/URI `ui://`). Texte `instructions` : hash SHA-256 identique aux deux commits.
- **Littéraux backend** : scan AST de tout `document-parser/` hors tests aux deux commits (chaînes hors docstrings, champs annotés des classes, noms d'arguments nommés).
- **Littéraux frontend** : scan des chaînes `'…'`, `"…"`, `` `…` `` de `frontend/src` hors tests aux deux commits.
- **Statuts et `detail`** non visibles dans l'OpenAPI : relecture des routes modifiées et des services qu'elles appellent, à `a6fb539` (`git show`) et dans le working tree.

Les suites n'ont pas été relancées (résultats fournis sur `a12b744` : ruff propre, pytest 1559 passés / 15 skips, eslint, prettier, `vue-tsc` propres, vitest 605 passés, `vite build` OK).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 13 |

Calcul : somme des poids = 35 ; non conforme : 7.4.2 (poids 2). `33 / 35 × 100 = 94,29` → **94**. Même grille et même lecture que le re-audit `a6fb539`.

| Item | Poids | Conforme | Justification (working tree `a12b744`) |
|------|-------|----------|----------------------------------------|
| 7.1.1 REST-only front/back | 3 | oui | le viewer lit toujours le PDF par `getExportUrl(id, 'pdf')` (`frontend/src/features/document/ui/usePdfDocument.ts:29`, `features/document/api.ts:68`) ; aucun fichier ni base partagés ; nginx ajoute `location /assets/` (fichiers statiques du front), sans toucher `/api/` ni `/mcp` (`nginx.conf.template:26-48`) |
| 7.1.2 Types TS = schémas Pydantic | 3 | oui | `api/schemas.py` et `frontend/src/shared/types.ts` inchangés depuis `a6fb539` ; OpenAPI identique ; `AnalysisSummary` (`shared/types.ts:85`) = `AnalysisSummaryResponse` (`api/schemas.py:233`) |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | oui | `features/history/api.ts:2-5` réexporte `fetchAnalysisSummaries`/`deleteAnalysis` du barrel `analysis` (`features/analysis/index.ts:3`, `features/analysis/api.ts:51-61`) ; appels hors `api.ts` inchangés et antérieurs (`feature-flags/store.ts`, `analysis/graphApi.ts`, `document/ui/DownloadDropdown.vue:135`) |
| 7.1.4 Back testable sans front | 2 | oui | nouveau `tests/test_document_export_range.py:77-90` (TestClient, `Range` → 206) ; routes inchangées dans leur forme |
| 7.1.5 Pas de logique métier dupliquée | 2 | oui | inchangé : règle « même label » front (`analysis-editor/commands.ts:87`) = garde UX, le back revalide (`infra/docling_editor.py:219-220`) |
| 7.2.1 Feature = store + api + ui | 2 | oui | structure des features inchangée ; `parseAnalysisPages` placé dans `shared/analysisPages.ts:4` |
| 7.2.2 Frontière barrel + ESLint | 3 | oui | 15 imports inter-features dans `features/`, tous par barrel (`@/features/<f>` ou `../../document`), dont le nouveau `features/history/api.ts:5` → `@/features/analysis` ; `frontend/eslint.config.js` inchangé |
| 7.2.3 Types partagés dans `shared/types.ts` | 2 | oui | `shared/types.ts` inchangé ; aucun import de `features/*/types` hors de sa feature |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | oui | inchangé : `document/store.ts:28` → `isEnabled()`, `admin-config/store.ts:80,95` → `reload()`, `reasoning/store.ts:22` → actions |
| 7.3.1 Repos → objets du domaine | 2 | oui | `persistence/analysis_repo.py:131,150` : seuls les noms changent (`find_latest_parsed_ids`, `find_parsed_document_id`), mêmes retours |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | oui | `grep "from docling\|import docling" services/ domain/` vide ; `pypdfium2`, `pdf2image`, `PIL` absents de `services/` et `domain/` (sortis vers `infra/pdf_inspector.py`, `infra/page_raster.py`) |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | oui | aucun SQL ni `aiosqlite` hors `persistence/` ; plus aucune annotation `Sqlite*` dans `services/` (services typés sur les ports, `domain/ports.py:148,184,211`) |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | oui | aucune importation `fastapi`/`starlette` dans `services/`, `domain/` ; traduction en un point `api/errors.py:25-31` |
| 7.4.1 Ports = signatures claires, types domaine | 2 | oui | nouveaux ports `DocumentFileLocator` (`domain/ports.py:148`), `PageRasterizer` (`:627`), `PdfInspector` (`:654`) en types du domaine (`PageDetail`, `Document`, `bytes`) ; exception `GraphDriverPool.get -> Any` (`:502-509`), voir INFO |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **non** | `api/schemas.py:200,201,227,437` inchangés (fichier absent du diff) ; `api/graph.py:33` |
| 7.4.3 Format de réponse cohérent | 1 | oui | statuts et `detail` des routes modifiées inchangés (voir section contrats) ; enveloppe `{detail}` partout |

---

## Écarts constatés

### [MAJ] `dict` non typé dans les schémas de réponse de l'éditeur et des stores (item 7.4.2)

- **Localisation** : `document-parser/api/schemas.py:200` (`AnalysisEditorResponse.model: dict`), `:201` (`tree: list[dict]`), `:227` (`AnalysisEditHistoryEntryResponse.payload: dict`), `:437` (`StoreResponse.config: dict`) ; `document-parser/api/graph.py:33` (`extra: "allow"`) ; arbre sérialisé à la main `document-parser/api/analysis_edits.py:44` (`_serialize_tree -> dict`).
- **Constat** : **inchangé**. La remédiation ne visait pas cet item : `api/schemas.py` n'apparaît pas dans `git diff a6fb539 a12b744`. Le modèle d'éléments, l'arbre et le payload de l'historique restent absents de l'OpenAPI ; leurs noms de champs sont fixés par `infra/docling_projector.py` et persistés tels quels.
- **Règle violée** : 7.4.2 (poids 2).
- **Remédiation** : inchangée — `EditorElementResponse`, `EditorTreeNodeResponse`, `EditorModelResponse`, `payload` en union discriminée des `*EditRequest`, puis `StoreResponse.config` par type de store en 0.8.0. Effort M.

### [INFO] Le contrat `Range` du viewer PDF.js est maintenant testé, mais reste porté par la route d'export

- **Localisation** : `document-parser/tests/test_document_export_range.py:77-90` ; route `document-parser/api/documents.py:107-140` ; `document-parser/pyproject.toml:10` (`fastapi>=0.115.0,<1.0.0`).
- **Constat** : **réduit**. Un test envoie `Range: bytes=0-1023` et `bytes=1024-2047` et attend un 206 avec la tranche : une régression de Starlette serait vue. Restent : la borne basse de `pyproject.toml` n'est pas resserrée, et la route « export » sert toujours de source de lecture au viewer.

### [INFO] Le client HTTP de l'éditeur reste dupliqué dans la feature `document`

- **Localisation** : `frontend/src/features/document/api.ts:19-29` (`fetchDocumentEditedAnalysisResult`), appelé par `features/document/store.ts:29` ; client propriétaire `features/analysis-editor/api.ts`.
- **Constat** : inchangé.

### [INFO] La page de détail reconstruit toujours une `Analysis` à partir d'un summary

- **Localisation** : `frontend/src/pages/AnalysisDetailPage.vue:107-128` (`buildAnalysisFrame`, `loadAnalysisFrame`).
- **Constat** : inchangé sur le fond, code découpé (450dad6). La page charge toute la liste des summaries pour en trouver un, et invente `hasDocumentJson: false` et des contenus `null`. Le manque d'une route `GET /api/analyses/{id}/summary` demeure.

### [INFO] Preview : les erreurs passent par `ServiceError`, mais deux `except` génériques restent dans la route

- **Localisation** : `document-parser/services/preview_service.py:17-35` (trois classes `ServiceError`) ; `document-parser/api/documents.py:164-175`.
- **Constat** : **réduit**. Les erreurs de preview rejoignent la famille `ServiceError` et `to_http_error`. La route garde `except ValueError` → 404 avec `str(e)` et `except Exception` → 422. Le `ValueError` de l'adaptateur (`infra/page_raster.py:33`, message avec le chemin serveur) est intercepté par le service et réécrit sans chemin (`preview_service.py:85-88`), donc le `detail` exposé ne change pas.

### [INFO] Les services portent des codes HTTP (`http_status`), désormais dans 12 modules

- **Localisation** : `document-parser/services/errors.py:11-19` ; nouveaux porteurs `services/preview_service.py:20,29,35`, `services/analysis_service.py:62,68` (`ImportDocumentNotFoundError`, `InvalidDoclingDocumentError`).
- **Constat** : inchangé sur le principe, étendu à deux familles (10 → 12 fichiers de `services/`). Toujours sans import FastAPI : 7.3.4 reste conforme. Un transport non-HTTP doit réinterpréter ces codes.

### [INFO] Séquence d'historique inconnue → 400, pas 404

- **Localisation** : `document-parser/services/analysis_edit_service.py:227` ; route `api/analysis_edits.py:148`.
- **Constat** : inchangé.

### [INFO] Règles de fusion recopiées côté front

- **Localisation** : `frontend/src/features/analysis-editor/commands.ts:87` vs `document-parser/infra/docling_editor.py:219-220`.
- **Constat** : inchangé.

### [INFO] Les routes binaires `/preview` et `/export` ne documentent pas leurs réponses

- **Localisation** : `document-parser/api/documents.py:107,148`.
- **Constat** : inchangé (OpenAPI identique à `a6fb539`).

### [INFO] Nouveau port `GraphDriverPool` qui renvoie `Any`

- **Localisation** : `document-parser/domain/ports.py:495-509`.
- **Constat** : nouveau (437d058). Le driver Neo4j est volontairement opaque pour les services (docstring) et transmis tel quel à une fabrique de `GraphWriter`. Pas de type Neo4j qui fuit, mais la signature ne dit rien. 7.4.1 reste conforme : c'est un handle opaque, pas une donnée métier.
- **Suggestion** : un `NewType("GraphDriver", object)` ou un `Protocol` vide dans le domaine, pour nommer le handle.

### [INFO] Un utilitaire de `shared/` est réexporté par le barrel d'une feature

- **Localisation** : `frontend/src/features/analysis-editor/types.ts:89` (`export { parseAnalysisPages } from '../../shared/analysisPages'`), consommé via `features/analysis-editor` par `frontend/src/pages/AnalysisDetailPage.vue:76-80` ; les autres consommateurs importent `shared/` directement (`features/analysis/store.ts:11`, `features/document/store.ts:5`, `features/analysis/ui/InspectResultTabs.vue:40`).
- **Constat** : nouveau. Pas d'import d'internes, mais l'API publique de `analysis-editor` expose un helper qui ne lui appartient pas.
- **Suggestion** : retirer la réexportation ; la page importe `../shared/analysisPages`.

### [INFO] `/pages` : une erreur inattendue de la recherche du document répond 422 au lieu de 500

- **Localisation** : `document-parser/api/documents.py:178-190` ; service `document-parser/services/preview_service.py:70-77`.
- **Constat** : nouveau, seule différence de comportement HTTP trouvée. À `a6fb539`, `service.find_by_id` était appelé hors du `try` : une exception de base de données remontait en 500. Elle est désormais dans `service.page_sizes`, à l'intérieur du `try`, et tombe dans `except Exception` → 422 `"Failed to read PDF file"`. Les cas nominaux (200, 404 `"Document not found"`, 404 `"PDF file not found on disk"`, 422 sur PDF illisible) sont identiques. Hors contrat documenté et non observable en fonctionnement normal.
- **Suggestion** : laisser passer les erreurs non PDF (`except (OSError, ValueError)` ou équivalent) pour garder le 500.

### [INFO] Constat reconduit sans changement

| # | Constat | Localisation vérifiée sur `a12b744` |
|---|---------|-------------------------------------|
| 1 | Pages et shell important en profondeur les internes de features (`store`, `api`, `ui`) | même nombre d'imports profonds par fichier qu'à `a6fb539` dans `pages/*.vue`, `pages/*.ts`, `app/App.vue` ; ex. `pages/DocParseTab.vue:178-190`, `pages/StudioPage.vue:510-516`, `pages/AnalysisDetailPage.vue:75,81` |

Autres constats regroupés du re-audit, revérifiés présents et non recomptés : cycle de barrels `document` ↔ `analysis` (`features/document/store.ts:6`, `features/analysis/ui/AnalysisPanel.vue:61`, `analysis/ui/StructureViewer.vue:64`) ; bornes MCP recopiées (`features/mcp-config/types.ts`) ; URL SPA construite par le back ; couplage Starlette dans `bootstrap/mcp_mount.py` ; champs orphelins `Document.stores?` / `chunksStale?` (`shared/types.ts`, inchangé) ; motif ESLint sans cas `../../<feature>/<fichier>.ts` (`eslint.config.js` inchangé). Le code HTTP dérivé du texte d'exception (`api/analyses.py:83` à `a6fb539`) est **résolu** : l'import lève des erreurs typées (`api/analyses.py:85-88`).

---

## Contrats : vérification de non-régression

| Surface | Méthode | Résultat |
|---------|---------|----------|
| OpenAPI complet (chemins, méthodes, operationIds, paramètres, schémas, codes déclarés) | `app.openapi()` aux deux commits, JSON trié, `diff` | **Identique** octet pour octet (45 chemins, 58 operationIds, 75 schémas, routeur `ingestion` inclus) |
| Noms des handlers de route (operationIds FastAPI) | liste des 58 operationIds aux deux commits ; `git diff -- document-parser/api` | **Identiques**. Aucun handler renommé ; seuls `http_error` → `to_http_error` (`api/errors.py:25`) et des helpers privés (`_fetch_store_links` supprimé, `_to_store_link_response` ajouté `api/documents.py:26`) changent |
| Champs et alias Pydantic | `api/schemas.py` absent du diff ; schémas OpenAPI identiques | **Inchangés** |
| Champs des dataclasses / classes annotées du backend | scan AST aux deux commits | aucun champ supprimé ni renommé ; ajouts `DocumentStoreLinkView.{store,state,last_push_at}` (`services/document_service.py:47-52`) et `EditHistoryEntry.{record,active}` (`domain/analysis_editing.py:47-54`), internes |
| Chaînes du backend (clés de dict, colonnes SQL, `detail`, en-têtes) | scan AST des littéraux hors docstrings aux deux commits | 5 chaînes disparues : `'Document not found:'` (préfixe du test de texte supprimé dans `api/analyses.py`, le message levé reste `f"Document not found: {id}"`, `services/analysis_service.py:175`), `'Store repository not available'` et `'Document/store link repository not available'` (dépendances supprimées de `api/deps.py`, les repos sont désormais câblés dans `DocumentService`, `bootstrap/factories.py:220-232`), `'document_exists'` et `'env_reasoning_config'` (entrées `__all__` de fonctions internes renommées). Aucune clé JSON, colonne ni en-tête touchés ; `deps_present`, `deep_link`, `heading_level`, `chunkset_hash`, `element_text`, `parent_ref` présents à l'identique |
| Statuts et `detail` des routes modifiées | relecture route + service aux deux commits | `GET /api/documents/{id}` : 404 `"Document not found"`, slug de store avec repli sur l'id (`services/document_service.py:144-168`), identique. `/export` : `ExportNotFoundError` reste la seule `ServiceError` levée (404, `str(exc)`), garde éditeur 404 `"Analysis editor is disabled"` via `deps.ensure_analysis_editor_enabled` (`api/deps.py:53-56`, `api/documents.py:123-124`) avant le service, comme avant. `/preview` : 404 `"Document not found"`, 400 `"Page N out of range (…)"`, 404 `"Page N not found"`, 404 `"PDF file not found on disk"`, 422 : identiques. `/pages` : identique hors le cas 500 → 422 décrit en INFO. `/analyses/import` : 404 `"Document not found: <id>"` et 400 `str(e)` identiques (`api/analyses.py:84-88`). Historique de l'éditeur : `active` calculé par la même fonction (`resolve_active_edit_commands`, ex-`active_edit_commands`), même valeur `None` pour les événements `setCommandActive` |
| Empreintes persistées (`result_hash`, staleness des chunks) | relecture | `hash_result` (`domain/analysis_editing.py:129-135`) = ancien `_hash_text` et ancien calcul inline : SHA-256 hex de l'UTF-8. Aucune invalidation des caches persistés |
| MCP : outils, prompts, schémas, instructions | `list_tools()` / `list_prompts()` sérialisés aux deux commits, 4 configurations ; hash des `instructions` | **Identiques**. Outils : `find_documents`, `get_outline`, `read_element`, `verify_citation`, `show_sources`, `get_source_page`, `show_citation`, `get_citation_image`. Prompt `chunkless_rag` : la fonction devient `render_chunkless_rag` mais le nom est fixé par `name="chunkless_rag"` (`mcp_adapter/prompts.py:61`), donc inchangé |
| Clés de stockage navigateur | relecture + scan des littéraux frontend | `analysis-editor-pending:${documentId}:${baseAnalysisId}` (`features/analysis-editor/store.ts:347`) identique ; `STORAGE_KEYS` (`shared/storage/keys.ts`) inchangé, `readStorageItem`/`writeStorageItem` (`features/settings/store.ts:7,15`) lisent les mêmes clés `docling-theme` / `docling-locale` |
| Clés i18n, noms de routes, chemins d'API côté front | scan des littéraux `frontend/src` hors tests aux deux commits | aucune clé i18n, nom de route ni URL d'API supprimé ou ajouté ; les seules chaînes disparues sont des couleurs hexadécimales (remplacées par des tokens), `'[]'` et des expressions de template renommées (`globalIndex` → `toGlobalIndex`, `icon` → `buildIconAttrs`, etc.) |
| Barrels exportés entre features | `git diff` des `index.ts` | seul ajout : `deleteAnalysis` dans `features/analysis/index.ts:3` ; rien de retiré ; renommage `modeFlags` → `getModeFlags` du store `feature-flags` avec son seul appelant `app/router/index.ts:52` (vérifié par `vue-tsc`) |
| nginx | `git diff` des deux templates | `location /assets/` (cache 1 an, en-têtes de sécurité répétés à l'identique) et `gzip_types` élargi aux JS/CSS/SVG. `/api/` et `/mcp` inchangés ; `application/pdf` toujours hors gzip, donc les réponses 206 du viewer ne sont pas touchées ; `frontend/public/` ne contient pas de dossier `assets/`, aucun fichier non empreinté n'est mis en cache immuable |

Conclusion : l'affirmation « aucun contrat d'API changé » est **vérifiée** pour l'OpenAPI, les champs JSON, les noms d'outils et de prompts MCP, les clés de stockage, les clés i18n et les noms de routes. Une seule différence de comportement HTTP, hors contrat documenté : `/pages` répond 422 au lieu de 500 sur une erreur inattendue de lecture du document en base.

Non vérifié : les réponses réelles en exécution (aucune app lancée, conformément à la consigne) ; le comportement de nginx (configuration lue, pas exécutée) ; le contenu des réponses MCP au-delà des schémas déclarés (les fonctions de mapping `to_*_result` ont été renommées, leur corps relu dans le diff sans changement de clés).

---

## Delta vs re-audit a6fb539

| Constat du re-audit (`a6fb539`) | Statut à `a12b744` | Preuve |
|--------------------------------|--------------------|--------|
| [MAJ] 7.4.2 `dict` dans les réponses éditeur / stores | **Inchangé** | `api/schemas.py:200,201,227,437`, fichier absent du diff |
| [INFO] Contrat `Range` implicite du viewer | **Réduit** | test `tests/test_document_export_range.py:77-90` ; borne `pyproject.toml:10` inchangée |
| [INFO] Endpoint summaries appelé par deux features | **Résolu** | `features/history/api.ts:2-5` réexporte depuis `@/features/analysis` |
| [INFO] Client de l'éditeur dupliqué dans `document` | Inchangé | `features/document/api.ts:19-29` |
| [INFO] `Analysis` reconstruite par la page de détail | Inchangé (code découpé) | `pages/AnalysisDetailPage.vue:107-128` |
| [INFO] Erreurs de preview hors `ServiceError` | **Réduit** | `services/preview_service.py:17-35` ; `except` génériques restants `api/documents.py:166-175` |
| [INFO] `http_status` dans les services | Inchangé, étendu (10 → 12 fichiers) | `services/preview_service.py`, `services/analysis_service.py:62,68` |
| [INFO] Séquence inconnue → 400 | Inchangé | `services/analysis_edit_service.py:227` |
| [INFO] Règles de fusion recopiées | Inchangé | `analysis-editor/commands.ts:87` |
| [INFO] `/preview` sans réponses documentées | Inchangé | OpenAPI identique |
| [INFO] Imports profonds depuis `pages/` et le shell | Inchangé | mêmes comptes par fichier |
| [INFO] Services annotés avec des repos SQLite concrets | **Résolu** | aucun `Sqlite` dans `services/` ; ports `domain/ports.py:148,184,211` |
| Regroupé : code HTTP dérivé du texte d'exception (`api/analyses.py:83`) | **Résolu** | `api/analyses.py:84-88`, `services/analysis_service.py:59-68` |

Nouveaux constats (INFO) : port `GraphDriverPool.get -> Any` ; `parseAnalysisPages` réexporté par le barrel `analysis-editor` ; `/pages` 500 → 422 sur erreur inattendue. Aucun nouvel écart CRIT, MAJ ou MIN.

Score : **94 → 94** (=). Aucun item n'a changé d'état : la remédiation ne visait pas 7.4.2, seul item non conforme.

---

## Points positifs

- **Contrat externe figé, vérifié par génération** : OpenAPI et catalogue MCP identiques aux deux commits malgré deux commits de renommage transverses.
- **Les routes ne parlent plus aux repos** : `get_document` passe par `DocumentService.find_with_store_links` (`services/document_service.py:144`) ; les dépendances `StoreRepoDep` / `DocumentStoreLinkRepoDep` disparaissent de `api/deps.py`.
- **Les bibliothèques PDF sortent des services** : `pypdfium2`, `pdf2image` derrière `PdfInspector` / `PageRasterizer` (`domain/ports.py:627,654`), câblés au bootstrap (`bootstrap/builder.py:176-181`).
- **Services typés sur les ports** : plus aucune annotation `Sqlite*Repository` dans `services/`.
- **Import d'analyse typé** : le statut ne dépend plus d'un préfixe de message.
- **Un seul client pour les summaries** : `history` passe par le barrel `analysis`.
- **Contrat `Range` du viewer testé**.

---

## Verdict partiel : GO

Score **94/100** (inchangé), 15/16 items conformes, **0 CRIT**, **1 MAJ** (7.4.2, ouvert depuis 0.7.3, sous le seuil master de > 3), **0 MIN**, 13 INFO. L'affirmation de la remédiation « aucun contrat d'API changé » est confirmée ; seule nuance, `/pages` répond 422 au lieu de 500 sur une erreur inattendue de base de données.

Suivi recommandé :
1. [MAJ] 7.4.2 — typer `model`, `tree`, `payload` de l'éditeur (M).
2. [INFO] — restreindre le `except Exception` de `/pages` pour rendre le 500 aux erreurs non PDF (XS).
3. [INFO] — retirer la réexportation de `parseAnalysisPages` du barrel `analysis-editor` (XS).

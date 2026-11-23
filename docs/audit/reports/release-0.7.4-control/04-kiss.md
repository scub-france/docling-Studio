# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a12b744`, arbre de travail.
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539.

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`.
Delta examine : `git log a6fb539..a12b744` (15 commits), `git diff a6fb539 a12b744`
(104 fichiers backend, 94 fichiers front). La remediation ne visait aucun ecart KISS ; ce
controle juge surtout la structure qu'elle a ajoutee (ports, adaptateur, erreurs, dataclasses,
decoupage front, jetons CSS).
Methode : lecture du code de l'arbre de travail, grep, `git diff`/`git show` en lecture seule.
Application non lancee, suites non relancees (resultats fournis : ruff OK, pytest 1559 OK /
15 skipped, eslint, prettier, vue-tsc OK, vitest 605 OK, vite build OK).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 8 |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 15 |

Poids total : 12. Poids conformes : 9 (4.2, poids 2, et 4.5, poids 1, non conformes).
`score = 9 / 12 * 100 = 75`. Meme lecture que le re-audit (4.8 conforme a la limite).

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:78`). Les 6 nouveaux ports sont des `Protocol` sans factory ni registre ; 4 sont imposes par `tests/test_architecture.py:55-68` et `:186-202` |
| 4.2 | Resout le probleme actuel, pas hypothetique | 2 | **Non** | MAJ LLM-provider inchange (`domain/value_objects.py:153-163`) ; plomberie editeur, carte de citation et cache d'apercu inchanges |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui | Nouveaux relais minces (`features/history/api.ts:2-5`, `DocumentService` comme `DocumentFileLocator`) en INFO ; `ensure_analysis_editor_enabled` factorise 3 appels (`api/deps.py:53`) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui | Verrou pdfium repris de Docling (`infra/pdfium_lock.py:12-15`) ; `color-mix()` CSS natif ; rien de maison ajoute |
| 4.5 | Configuration simple | 1 | **Non** | Config MCP en couches inchangee : `infra/settings.py` et `domain/mcp_config.py` hors diff ; `mcp_config_service.py`, `mcp_stdio.py`, `bootstrap/mcp_mount.py` seulement renommes |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Chemin apercu : route → `PreviewService` → ports (`services/preview_service.py:52-88`), meme profondeur qu'avant ; la methode statique `DocumentService.generate_preview` a disparu |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui | Grep fiche : rien hors `setattr` trivial `main.py:53` |
| 4.8 | Structures de donnees les plus simples | 1 | Oui (limite) | `AnalysisDetailPage` garde 200 resumes pour en trouver un et l'aller-retour `JSON.stringify` (`pages/AnalysisDetailPage.vue:112`, `:123`) ; reste en INFO comme au re-audit (lecture stricte : non conforme, 67) |

### Metriques de perimetre

| Mesure | a6fb539 | a12b744 |
|--------|---------|---------|
| `Protocol` dans `domain/ports.py` | 26 | 32 (+6) |
| Lignes de `domain/ports.py` | 633 | 766 |
| Exceptions tolerees `_LEGACY_LAYER_IMPORTS` | 11 | 1 (`tests/test_architecture.py:66-68`) |
| `pdf2image` / `pypdfium2` importes par `services/` | oui (candidats a migrer) | non, interdits (`tests/test_architecture.py:194-195`, `:202`) |
| Rasteriseurs PDF → image | 2 | 1 (`infra/page_raster.py:26-41`) |
| Branches `except` de la route `/preview` | 7 | 6 (`api/documents.py:164-175`) |
| Cache d'apercu | 64 Mo, `Lock` | inchange (`infra/preview_cache.py:16`, `:20`) |
| Greps de la fiche (4.1 / 4.7) | `AppStateBuilder` / `setattr` | identiques |

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable) — reconduit, inchange

- **Localisation** : `document-parser/domain/value_objects.py:153` (`LLMProviderType`, membre unique `OLLAMA` `:163`), `document-parser/domain/ports.py:547` (`LLMProvider`, tag `type` `:564`, deplace par les ajouts de ports, contenu identique), `document-parser/infra/docling_agent_reasoning.py:137-138` (garde `NotImplementedError`), `document-parser/bootstrap/factories.py:103` (second garde par chaine), `document-parser/infra/settings.py:55` et `:234` (`LLM_PROVIDER_TYPE`), `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:153`
- **Constat** : aucune ligne de fond modifiee. Le plan de remediation la reporte explicitement en 0.8.0 avec depreciation (`docs/audit/reports/release-0.7.4-reaudit/remediation-plan.md:46`). Cinquieme release consecutive.
- **Regle violee** : item 4.2 (poids 2).
- **Remediation** : inchangee. Assumer Ollama en dur, ou garder le port `LLMProvider` sans dispatch. Effort S.

---

### [MIN] Repli serveur des apercus equipe comme un chemin principal — reconduit, reduit

- **Localisation** : `document-parser/infra/preview_cache.py:13-40` (LRU 64 Mo, `Lock` `:20`), `document-parser/services/preview_service.py:64` et `:67` (`get`/`put` sur la boucle d'evenements, hors `to_thread`), `document-parser/domain/ports.py:156-170` (port du cache), `docs/design/pdf-loading-performance.md` (toujours muet sur PDF.js)
- **Constat** : ce qui baisse : le double rasteriseur a disparu, `PreviewService` passe par le port `PageRasterizer` qui accepte le WebP (`infra/page_raster.py:26-41`) ; ses erreurs entrent dans `ServiceError` (`services/preview_service.py:17-35`) ; `docs/configuration.md:132-144` dit enfin que PDF.js est le chemin principal et l'image un repli, avec le cache de 64 Mo. Ce qui reste : le cache de 64 Mo par processus optimise toujours un chemin pris seulement quand PDF.js echoue, sans mesure de frequence ; le `Lock` protege des appels faits uniquement depuis la boucle d'evenements ; le document de conception n'a pas ete mis a jour.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : retirer le `Lock` ; retirer le cache ou le borner bien plus bas tant que la frequence du repli n'est pas mesuree ; aligner `docs/design/pdf-loading-performance.md` sur `docs/configuration.md`. Effort S.

### [MIN] Editeur d'analyse : plomberie pour des besoins non exprimes — reconduit, inchange

- **Localisation** : `document-parser/persistence/database.py:258` (`edited_analysis_cache`), `document-parser/services/analysis_edit_service.py:90` et `:299` (`_project_cache`), `:156` (`engine_version` ecrit, jamais compare), `:250` (`rebuild`) ; `document-parser/infra/docling_analysis_engine.py:45-46` et `document-parser/api/schemas.py:206-207` (`warnings`, `reference_changes`) ; `frontend/src/features/analysis-editor/types.ts:15` (`beforeElementId`) et `:56` (`referenceChanges`, lu nulle part) ; `frontend/src/features/analysis-editor/api.ts:71` (`rebuildAnalysisEdits`, sans appelant)
- **Constat** : rien retire. La remediation a seulement deplace le calcul d'etat de l'historique dans le service (`list_history_entries`, `services/analysis_edit_service.py:114-120`), ce qui est un bon deplacement mais ne touche pas la plomberie speculative.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : inchangee (servir les colonnes du cache ou les retirer ; retirer `warnings`/`referenceChanges`, `beforeElementId`, le client `rebuild` ; documenter ou retirer `engine_version`/`previous_hash`). Effort M.

### [MIN] Configuration MCP en couches — reconduit, inchange

- **Localisation** : `document-parser/infra/settings.py:90-122`, `:259-280` (dont `:276` `MCP_MAX_READ_TOKENS` et `:279` `ANALYSIS_EDITOR_ENABLED` sans helper booleen), `document-parser/domain/mcp_config.py:44`, `:107-113`, `document-parser/services/mcp_config_service.py`, `document-parser/services/navigation_config.py:32`, `document-parser/mcp_stdio.py`
- **Constat** : `git diff a6fb539 a12b744` est vide pour `infra/settings.py` et `domain/mcp_config.py` ; les autres fichiers n'ont que des renommages (`_overrides` → `_compute_overrides`, `db_path` → `resolve_db_path`, `env_mcp_config` → `build_env_mcp_config`). Trois representations pour quatre reglages, bornes en double.
- **Regle violee** : item 4.5 (poids 1).
- **Remediation** : inchangee (une seule source des bornes et defauts dans `domain/mcp_config.py`, helper `_env_bool`, `ASK_MODE` booleen).

### [MIN] Carte de citation desactivee par defaut et maintenue — reconduit, inchange

- **Localisation** : `document-parser/infra/settings.py:274` (`MCP_CITATION_CARD=false`), `document-parser/mcp_adapter/citation_app.html` (hors diff, 1 256 l.), `document-parser/mcp_adapter/apps.py` (renommages seulement)
- **Constat** : aucun changement de fond. La fonctionnalite reste eteinte par defaut et couverte par `show_sources`.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : retirer la carte ou statuer et l'activer.

---

### [INFO] Deux ports non imposes par une regle de couche : `DocumentFileLocator` et `ActiveAnalysisResultReader` (nouveau)

- **Localisation** : `document-parser/domain/ports.py:148-153` (`DocumentFileLocator`), seul appelant `document-parser/services/preview_service.py:42`, seule implementation `DocumentService` (`services/document_service.py:140`, `:170`) ; `document-parser/domain/ports.py:360-371` (`ActiveAnalysisResultReader`), appelants `services/export_service.py:43` et `services/chunk_service.py:149`, seule implementation `AnalysisEditService`
- **Constat** : `services → services` n'est pas interdit par `_LAYER_RULES` (`tests/test_architecture.py:55-62`) et la regle « pas de service pair » ne couvre que cinq modules (`:119-125`), pas l'apercu, l'export ni le chunking. Ces deux ports ne sont donc pas exiges. Ils restent la forme la moins chere pour typer : `TestPortConvention` impose qu'un `Protocol` vive dans `domain/ports.py`, `ActiveAnalysisResultReader` remplace un parametre non type (`active_result_service=None` a `a6fb539`) et `DocumentFileLocator` evite d'exposer tout `DocumentService` a l'apercu. Cout : 6 et 12 lignes, pas de classe ni de cablage de plus. Juges acceptables, pas speculatifs ; a ne pas generaliser.
- **Remediation** : aucune obligatoire.

### [INFO] `PdfInspector` : port justifie, cablage en trois endroits et une branche morte (nouveau)

- **Localisation** : `document-parser/domain/ports.py:653-669`, `document-parser/infra/pdf_inspector.py:24-64` ; instanciations `document-parser/bootstrap/builder.py:45` et `:179` (import direct de l'adaptateur), `document-parser/bootstrap/factories.py:216`, `:231`, `:307-310` (`_build_pdf_inspector`) ; `document-parser/services/analysis_service.py:94` et `:448-449` (`pdf_inspector: PdfInspector | None = None`, « without one (some tests) ») ; `document-parser/tests/test_architecture.py:113-116` (docstring perimee)
- **Constat** : le port est impose (`pdf2image` et `pypdfium2` sont desormais interdits dans `services/`, `tests/test_architecture.py:194-195`) et a trois appelants (`DocumentService`, `AnalysisService`, `PreviewService`). Trois methodes, deux bibliotheques (pdfium pour la geometrie, poppler pour compter un upload en memoire, `pdf_inspector.py:53-56`), choix documente pour ne pas changer ce qu'un upload accepte. Trois ecarts de simplicite mineurs : l'adaptateur sans etat est construit trois fois par deux chemins differents (import direct dans `builder.py`, fabrique dans `factories.py`) ; `AnalysisService` garde un `None` qui n'existe que pour des tests et desactive le decoupage en lots s'il manque ; la docstring de `TestDocumentAgentServicesAreFrameworkFree` affirme encore que `document_service.py` compte les pages avec pdf2image.
- **Remediation** : une seule fabrique `_build_pdf_inspector` utilisee aussi par `builder.py` ; rendre `pdf_inspector` obligatoire et passer un faux dans les tests ; corriger la docstring.

### [INFO] Route `/preview` : echelle d'exceptions reduite mais pas videe (nouveau, residuel de l'INFO « erreurs hors `ServiceError` »)

- **Localisation** : `document-parser/api/documents.py:164-175`, `document-parser/services/preview_service.py:85-88`
- **Constat** : les erreurs du service passent par `to_http_error`. Restent cinq branches apres `ServiceError`, dont `except ValueError → 404` que plus rien ne leve : le seul `ValueError` du chemin (rasteriseur) est converti en `PreviewPageNotFoundError` par le service. `page_sizes` (`:184-189`) garde la meme forme.
- **Remediation** : retirer la branche `ValueError` ; envisager une seule branche `OSError` → 422.

### [INFO] Une meme teinte exprimee de deux facons, par le meme commit (nouveau)

- **Localisation** : `frontend/src/app/App.vue:99` (`--warning-muted: rgba(234, 179, 8, 0.1)`, absent du theme clair `:119-138` ou `--warning` change), utilise `features/document/ui/DocTreeNode.vue:133`, `features/chunks/ui/StaleStoresStrip.vue:118` ; `color-mix(in srgb, var(--warning) 10%, transparent)` dans `features/analysis-editor/ui/AnalysisEditor.vue:638` et `pages/DocumentsPage.vue:429`
- **Constat** : `1516a0c` ajoute cinq jetons (`--warning-muted`, `--on-accent`, `--on-bright`, `--banner-bg`, `--shadow-lg`) ; tous sont utilises (2, 6, 3, 1, 1 fois) et repondent a un besoin reel (17 jetons references sans definition, 71 replis litteraux supprimes). C'est une simplification. Mais le meme commit introduit deux mecanismes pour la teinte « warning a 10 % » : un jeton fige en RGB du theme sombre et `color-mix()` qui suit le theme. `color-mix()` existait deja (9 usages a `a6fb539`). `--banner-bg` et `--shadow-lg` sont des jetons a un seul usage, acceptables au nom de la regle « toute couleur vient d'un jeton ».
- **Remediation** : garder un seul mecanisme : remplacer `var(--warning-muted)` par le `color-mix()` et supprimer le jeton (ou le definir aussi en theme clair).

### [INFO] `features/history/api.ts` reduit a des alias de re-export (nouveau, 4.3 juge conforme)

- **Localisation** : `frontend/src/features/history/api.ts:2-5`, appelants `frontend/src/features/history/store.ts:13`, `:22`
- **Constat** : la duplication des appels HTTP a disparu (bien). Il reste un module qui renomme `fetchAnalysisSummaries` en `fetchHistory` et `deleteAnalysis` en `deleteHistoryEntry` pour un seul store. Couche de noms sans logique, cout negligeable.
- **Remediation** : facultatif, importer directement depuis `@/features/analysis` dans le store.

### [INFO] Ouverture d'une analyse en deux temps — reconduit, code plus lisible (4.6/4.8 a la limite)

- **Localisation** : `frontend/src/pages/AnalysisDetailPage.vue:105-152` (`buildAnalysisFrame`, `loadAnalysisFrame`, `loadFullAnalysis`, `showFrame`), `:112` (`JSON.stringify`), `:123` (recherche dans les resumes), `frontend/src/shared/analysisPages.ts:4-13` ; `document-parser/persistence/analysis_repo.py:72` (`limit=200`)
- **Constat** : le `onMounted` passe d'un `try/catch` imbrique a trois issues a quatre lignes lineaires ; le comportement (repli si le cadre echoue, erreur si l'analyse complete echoue) est identique. Le decoupage en quatre aides est proportionne et chacune a un role. Le fond ne change pas : 200 resumes telecharges pour en trouver un, un `Page[]` serialise puis reparse (`parseAnalysisPages`, factorise mais toujours un aller-retour), et l'analyse complete n'est demandee qu'apres le cadre (`:147-149`), soit trois requetes en sequence.
- **Remediation** : inchangee (`GET /api/analyses/{id}/summary` lance en parallele ; passer `Page[]` sans chaine).

### [INFO] Chemins de repli jamais pris en production — reconduit, etendu

- **Localisation** : `document-parser/services/export_service.py:43`, `:119`, `:143` ; `document-parser/services/chunk_service.py:149`, `:369`, `:702` ; nouveau : `document-parser/services/analysis_service.py:94`, `:448-449`
- **Constat** : `ActiveAnalysisResultReader | None = None` garde le `None` alors que `bootstrap/builder.py:187` l'injecte toujours ; la remediation ajoute le meme schema pour `PdfInspector`.

### [INFO] Priorisation de la page courante — reconduit, inchange

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14`, `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:238-256` (`registerImage`/`registerPdf`), `:289-318`, `:326`
- **Constat** : justifiee ; les gestionnaires jumeaux image/PDF sont toujours la.

### [INFO] Port moteur de l'editeur : relais `project_serialized` — reconduit

- **Localisation** : `document-parser/infra/docling_analysis_engine.py:49`

### [INFO] Flux de commandes event-sourced avec chaine de hash — reconduit

- **Localisation** : `document-parser/persistence/database.py:233-269`, `document-parser/persistence/analysis_edit_repo.py`

### [INFO] Introspection d'une API privee Docling — reconduit

- **Localisation** : `document-parser/infra/docling_editor.py:237`, `:293`, `:313` (`_move_subtree`)

### [INFO] Aller-retours JSON dans le projecteur — reconduit

- **Localisation** : `document-parser/infra/docling_projector.py` (`json.dumps`/`json.loads`), `document-parser/api/analysis_edits.py`

### [INFO] Pont MCP Apps ecrit a la main en deux copies — reconduit

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:770-850`, `document-parser/mcp_adapter/sources_app.html:1156-1230`

### [INFO] Aides mortes et relais sans valeur ajoutee — reconduit

- **Localisation** : `document-parser/mcp_adapter/wire.py:72` et `document-parser/mcp_adapter/wire_mapping.py:42` (`_neutralise_all` en double), `document-parser/services/analysis_edit_service.py:324` (`_replay`), autres references du re-audit renommees mais presentes

### [INFO] Residuels : `crop` a boite sentinelle, repli de chemin de dev, `ReasoningStepKind`/`health_check` — reconduits

- **Localisation** : `document-parser/services/citation_image_service.py:91`, `document-parser/services/document_service.py:170-182` (`resolve_storage_path`, desormais aussi via `DocumentFileLocator`), `document-parser/domain/value_objects.py:193`, `document-parser/domain/ports.py:572`

---

## Delta vs re-audit a6fb539

Score : **75 → 75 (0)**. Items conformes : 6/8 → 6/8. Memes items non conformes (4.2, 4.5),
meme lecture de 4.8 (limite). La remediation ne visait pas KISS ; elle n'a fait basculer aucun
item, ni dans un sens ni dans l'autre.

### Ecarts du re-audit

| Ecart a6fb539 | Statut a a12b744 | Detail |
|---------------|------------------|--------|
| [MAJ] Abstraction LLM-provider (4.2) | **Inchange** | Reporte en 0.8.0 par le plan de remediation |
| [MIN] Repli serveur equipe comme principal (4.2) | **Reduit** | Rasteriseur unique, erreurs `ServiceError`, role documente dans `docs/configuration.md` ; cache 64 Mo, `Lock` inutile et design doc inchanges |
| [MIN] Plomberie de l'editeur (4.2) | **Inchange** | |
| [MIN] Configuration MCP en couches (4.5) | **Inchange** | Renommages seulement |
| [MIN] Carte de citation desactivee (4.2) | **Inchange** | |
| [INFO] Priorisation, gestionnaires jumeaux | Inchange | |
| [INFO] Deux rasteriseurs dont un hors port | **Resolu** | `DocumentService.generate_preview` supprime, `PageRasterizer.render_page(fmt=)` |
| [INFO] Erreurs d'apercu hors `ServiceError` | **Resolu** (residuel en INFO) | Branche `ValueError` morte dans la route |
| [INFO] Ouverture d'analyse en deux temps | **Reduit** (lisibilite) | Fond inchange : 200 resumes, JSON, requetes en sequence |
| [INFO] Relais du port moteur | Inchange | |
| [INFO] Event-sourced, introspection, JSON projecteur, pont MCP, aides mortes, residuels | Inchanges | |
| [INFO] Replis jamais pris | **Aggrave** (legerement) | `pdf_inspector: PdfInspector | None` ajoute le meme schema |

### Nouveaux ecarts

Aucun CRIT, MAJ ni MIN. Cinq INFO : ports non imposes (`DocumentFileLocator`,
`ActiveAnalysisResultReader`) ; cablage et branche morte de `PdfInspector` ; echelle
d'exceptions residuelle de `/preview` ; teinte warning en deux mecanismes ; alias de
`history/api.ts`.

### Complexite ajoutee par la remediation

| Structure | Commit | Impose par une regle ? | Verdict |
|-----------|--------|------------------------|---------|
| `PdfInspector` (`domain/ports.py:653`) + `PdfiumInspector` (`infra/pdf_inspector.py:24`) | `437058d`, `25f5d8b` | Oui : `pdf2image`/`pypdfium2` interdits dans `services/` (`tests/test_architecture.py:194-195`) ; 3 appelants | **Justifie** (cablage a unifier, voir INFO) |
| `infra/pdfium_lock.py` (un objet) | `437058d` | Non, mais partage par 2 adaptateurs (`infra/page_text.py:18`, `infra/pdf_inspector.py:19`) ; evite de copier le `try/except ImportError` | **Justifie**, forme minimale |
| `DocumentVersionRepository` (`domain/ports.py:285`) | `437058d` | Oui : retire `("services/version_service.py", "persistence.document_version_repo")` de la liste tolere | **Justifie** |
| `VectorStorePool`, `GraphDriverPool` (`domain/ports.py:481`, `:495`) | `437058d` | Oui : retire 3 imports `infra` de `store_backend_resolver.py` | **Justifie** ; `GraphDriverPool.get -> Any` garde le pilote opaque, c'est le choix le plus simple |
| `DocumentFileLocator` (`domain/ports.py:148`) | `437058d` | Non (`services → services` permis) ; 1 implementation, 1 appelant | **Acceptable**, 6 lignes, typage etroit ; pas speculatif mais pas exige |
| `ActiveAnalysisResultReader` (`domain/ports.py:360`) | `437058d` | Non ; 1 implementation, 2 appelants ; remplace un parametre non type | **Acceptable** |
| Methodes ajoutees aux ports existants (`StoreRepository`, `ChunkPushRepository`, `VectorStore.search_fulltext`, ...) | `437058d` | Formalisent des appels deja faits hors `Protocol` | **Justifie**, pas de comportement nouveau |
| `PreviewPageNotFoundError`, `ImportDocumentNotFoundError`, `InvalidDoclingDocumentError` (`services/preview_service.py:32`, `services/analysis_service.py:59`, `:65`) | `437058d`, `25f5d8b` | Remplacent un aiguillage 404/400 sur le debut d'un message (`api/analyses.py` a `a6fb539`) et une fuite de chemin serveur | **Justifie**, plus simple que le texte compare |
| `DocumentStoreLinkView` (`services/document_service.py:46-53`) + `find_with_store_links` | `25f5d8b` | Sort la jointure de la route, retire 2 dependances de repository de `api/deps.py` | **Justifie** |
| `EditHistoryEntry` (`domain/analysis_editing.py:48-53`) + `list_history_entries` | `25f5d8b` | Sort le calcul d'etat de la route | **Justifie** ; `list_history` garde 2 appelants internes |
| `DocumentService` a 6 dependances (`services/document_service.py:58-72`) | `25f5d8b` | Consequence des deux deplacements ci-dessus | **Acceptable** ; a surveiller si d'autres jointures y arrivent |
| `AnalysisDetailPage` en 4 aides (`pages/AnalysisDetailPage.vue:105-152`) | `450dad6` | — | **Justifie** : moins de branches qu'avant, meme comportement |
| `history/api.ts` en re-exports (`features/history/api.ts:2-5`) | `450dad6` | — | **Justifie** pour la duplication retiree ; alias superflus (INFO) |
| 5 jetons CSS + `color-mix()` | `1516a0c` | — | **Justifie** dans l'ensemble ; doublon `--warning-muted` / `color-mix()` non justifie (INFO) |

Bilan : la remediation n'a pas introduit de sur-ingenierie. Quatre ports sur six sont exiges
par le test d'architecture, et la remediation a retire en contrepartie 10 exceptions tolerees
et un rasteriseur. Les deux ports non exiges sont minces et typent du code deja la. Les seuls
excedents sont de detail (cablage en double, `None` pour les tests, deux mecanismes pour une
teinte, alias de noms).

---

## Points positifs

- **Moins de dette de couche** : `_LEGACY_LAYER_IMPORTS` passe de 11 a 1 entree (`tests/test_architecture.py:66-68`) et `services/` n'importe plus aucune bibliotheque PDF (`:194-195`, `:202`).
- **Un seul rendu de page** : `PreviewService` et la navigation partagent `PdfPageRasterizer.render_page` (`infra/page_raster.py:26-41`).
- **Un seul verrou pdfium** partage avec Docling (`infra/pdfium_lock.py:12-15`), au lieu d'une copie par adaptateur.
- **Routes plus minces** : plus de choix 404/400 sur le prefixe d'un message (`api/analyses.py:85-88`), plus de jointure dans `get_document` (`api/documents.py:87-94`), garde editeur en une fonction (`api/deps.py:53-56`).
- **Front** : `onMounted` de `AnalysisDetailPage` lineaire ; une seule implementation des appels de l'historique ; 17 jetons non definis et 71 replis litteraux supprimes.

---

## Non verifie

- Rendu visuel des changements de jetons (`1516a0c` dit lui-meme ne pas avoir ete verifie en navigateur), en particulier `--warning-muted` en theme clair : application non lancee.
- Frequence reelle du repli serveur des apercus : aucune mesure dans le depot.
- Absence d'autres appelants de `PdfInspector` hors depot (scripts, notebooks) : non recherchee.
- Suites de tests non relancees ; resultats fournis par l'appelant.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL. Un ecart MAJOR (abstraction LLM-provider, reporte en 0.8.0), sous le
seuil bloquant (> 3). Score 75 / 100, identique au re-audit. La remediation n'a pas degrade
la simplicite. Pour repasser 4.2 conforme il faut toujours traiter ensemble le MAJ, la carte
de citation, la plomberie de l'editeur et le cache du repli d'apercu.

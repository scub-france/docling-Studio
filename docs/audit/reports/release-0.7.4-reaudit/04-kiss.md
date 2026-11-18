# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audite** : branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` @ `f7fc791` avec PR #401 et #402, + 13 commits locaux #391-#400 + merge), arbre de travail.

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`.
Reference : audit du 2026-11-13 @ `eade7fa` (75/100, 0 CRIT, 1 MAJ). Delta examine :
`git log eade7fa..a6fb539` (29 commits) et `git diff eade7fa a6fb539 --stat` (121 fichiers,
+6 467 / −986). Accent sur la PR #401 : rendu PDF.js dans le navigateur avec chargement par
plages, apercu PNG/WebP serveur garde en repli derriere `PreviewService` + `PreviewCache`,
priorisation de la page courante.
Methode : analyse statique et commandes en lecture seule (grep, git log/diff/show, wc).
Application non lancee. Suites de tests non relancees (resultats fournis : ruff, pytest
1501 OK, eslint, prettier, vue-tsc, vitest 586 OK, vite build OK).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 8 |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 13 |

Poids total : 12. Poids conformes : 9 (4.2, poids 2, et 4.5, poids 1, non conformes).
`score = 9 / 12 * 100 = 75`.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul ; le port `AnalysisDocumentEngine` et le port `PreviewImageCache` sont des `Protocol` imposes par la regle d'import `services -/-> infra` (`tests/test_architecture.py:57`), sans factory ni registre |
| 4.2 | Resout le probleme actuel, pas hypothetique | 2 | **Non** | MAJ LLM-provider inchange (4e release) + plomberie editeur + carte de citation (enrichie) + repli serveur equipe comme un chemin principal |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui | Relais isoles (`DoclingAnalysisEngine.project_serialized`, aides MCP mortes), en INFO comme au baseline |
| 4.4 | Outils standard avant solutions maison | 1 | Oui | PDF.js (`pdfjs-dist`) au lieu d'un rendu maison ; plages HTTP servies par `FileResponse` de Starlette 1.0 (`accept-ranges`) via la route d'export existante ; LRU sur `OrderedDict` (pas d'equivalent stdlib borne en octets) |
| 4.5 | Configuration simple | 1 | **Non** | Config MCP en couches inchangee (aucun fichier de config MCP modifie depuis `eade7fa`) |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Chemin apercu : route → `PreviewService` → `DocumentService` + cache, une couche de plus justifiee par la regle d'architecture ; INFO sur le double rasteriseur et le chargement en deux temps de `AnalysisDetailPage` |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui | Grep fiche : rien hors `setattr` trivial `main.py:53` ; introspection `_move_subtree` inchangee et documentee |
| 4.8 | Structures de donnees les plus simples | 1 | Oui (limite) | Aller-retours JSON reconduits en INFO ; le nouvel aller-retour `JSON.stringify`/`JSON.parse` de `AnalysisDetailPage` est classe INFO pour garder la lecture du baseline (lecture stricte : 4.8 non conforme, score 67) |

### Metriques de perimetre

| Mesure | eade7fa | a6fb539 |
|--------|---------|---------|
| Chemins de rendu de page cote front | 1 (`<img>` `/preview`) | **2** (canvas PDF.js principal, `<img>` `/preview` en repli si `pdfFailed`) |
| Code du repli serveur ajoute par #401 | — | `PreviewService` 50 l. + `PreviewCache` 40 l. + port 10 l. (`domain/ports.py:142-151`) |
| Code PDF.js front | — | `PdfPageCanvas.vue` 101 + `PdfPagePreview.vue` 48 + `usePdfDocument.ts` 47 = 196 l. |
| `PagePreviewWithOverlay.vue` | 726 l. | 761 l. |
| Budget memoire du cache d'apercu | — | 64 Mo par processus (`infra/preview_cache.py:16`), non configurable |
| Rasteriseurs PDF → image | 2 | 2 (`DocumentService.generate_preview`, `PdfPageRasterizer.render_page`) |
| `citation_app.html` (carte desactivee par defaut) | 1 177 l. | 1 256 l. |
| Greps de la fiche (4.1 / 4.7) | `AppStateBuilder` / `setattr` trivial | identiques |

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable) — reconduit, inchange

- **Localisation** : `document-parser/domain/value_objects.py:153` (`LLMProviderType`, membre unique `OLLAMA` `:163`), `document-parser/domain/ports.py:436` (`LLMProvider`, tag `type` `:453`), `document-parser/infra/docling_agent_reasoning.py:137-138` (garde `NotImplementedError`), `document-parser/bootstrap/factories.py:103` (second garde par chaine), `document-parser/infra/settings.py:55` et `:234` (`LLM_PROVIDER_TYPE`), `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:153` (« Provider: … »)
- **Constat** : aucune ligne modifiee depuis le baseline ; memes numeros de ligne. Enum a un membre, tag de type consomme par un seul garde, variable d'env, double garde factory + runner, champ remonte au panneau d'admin. Quatrieme release consecutive ou la dette est reportee.
- **Regle violee** : item 4.2 (poids 2).
- **Remediation** : assumer Ollama en dur (supprimer l'enum, le tag `type`, `LLM_PROVIDER_TYPE`, le double garde et `providerType`) ou garder le port `LLMProvider` sans dispatch. Effort S.

---

### [MIN] Repli serveur des apercus equipe comme un chemin principal (nouveau, PR #401)

- **Localisation** :
  - repli seul : `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:96-114` (`<img>` rendu seulement si `pdfFailed`), `:317` (une erreur PDF.js bascule toute la visionneuse), `frontend/src/features/document/ui/PdfPagePreview.vue:3-18` ;
  - equipement du repli : `document-parser/infra/preview_cache.py:13-40` (LRU 64 Mo + `Lock`), `document-parser/domain/ports.py:142-151` (port), `document-parser/services/preview_service.py:22-50`, `document-parser/services/document_service.py:175-176` (WebP sans perte), `document-parser/api/documents.py:187` (`Cache-Control: immutable`), `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:109` (`fetchpriority`, ne s'applique qu'au `<img>` de repli) ;
  - justification : `docs/design/pdf-loading-performance.md` (0 occurrence de « PDF.js » ou « range »).
- **Constat** : l'historique de #401 montre l'ordre des choix. Le cache serveur (`0e47663`, 15:01), les apercus WebP bornes (`3a9bfdd`, 16:05) et la priorisation (`204ad9b`, 16:21) ont ete construits pour le chemin `<img>` alors principal. PDF.js est arrive ensuite (`24ae5f5`, 18:54 ; `87476a8`, 19:29) et a relegue ce chemin au repli : dans les 7 visionneuses (`StudioPage`, `StructureViewer`, `PagePreview`, `AnalysisEditor` ×2, `DocParseTab`, `DocChunkTab`, `DocWorkspacePage`), l'image n'est demandee que si PDF.js echoue. Le port du cache (`80552d1`, 20:12) et `PreviewService` (`de5fe66`) ont ete ajoutes **apres** cette relegation. Le document de conception justifie le cache par des mesures de l'ancien chemin principal (« Page 1 preview, repeat request 2.0 s ») et ne mentionne pas PDF.js. Resultat : 64 Mo de RAM reserves par processus, un service et un port pour un chemin que l'UI n'emprunte qu'en cas d'echec, sans mesure de sa frequence.
  Le `Lock` de `PreviewCache` (`infra/preview_cache.py:20`) protege des appels faits uniquement depuis la boucle d'evenements (`services/preview_service.py:39` et `:49`, hors `to_thread`) : il ne sert a rien aujourd'hui.
- **Jugement par sous-question** :
  - *Double chemin* : justifie. PDF.js peut echouer (worker, PDF corrompu ou protege) et `/preview` reste une API publique testee (`e2e/api/src/test/resources/documents/preview.feature:10`). Garder un repli est le choix simple.
  - *Cache* : non justifie en l'etat. Il optimise le repli, pas le chemin courant.
  - *Port pour un cache de 40 lignes* : pas de la sur-ingenierie en soi. Un `Protocol` de deux methodes est la forme la moins chere qui respecte `tests/test_architecture.py:57`. Le probleme est ailleurs : le rasteriseur, lui, contourne le port `PageRasterizer` existant (voir INFO double rasteriseur).
  - *Priorisation* : justifiee (voir INFO), elle s'applique aussi aux canvas PDF.js.
- **Regle violee** : item 4.2 (poids 2, deja non conforme par le MAJ). Classe MIN : cout en code et en memoire, pas de risque fonctionnel.
- **Remediation** : retirer `PreviewCache` + port, ou le garder borne bien plus bas, et mesurer la frequence du repli avant de l'optimiser. Retirer le `Lock`. Mettre a jour `docs/design/pdf-loading-performance.md` (PDF.js principal, serveur en repli, role du cache). Effort S.

### [MIN] Editeur d'analyse : plomberie pour des besoins non exprimes — reconduit, inchange

- **Localisation** :
  - cache : `document-parser/persistence/database.py:258-269` (`edited_analysis_cache`, 10 colonnes), `document-parser/persistence/analysis_edit_repo.py:59` (`_CACHE_UPSERT`), `document-parser/services/analysis_edit_service.py:96` et `:297-320` (`_project_cache` → `project_serialized`), `document-parser/infra/docling_projector.py:76-91` (reprojection complete) ;
  - `warnings` : `document-parser/infra/docling_editor.py:30`, `document-parser/domain/analysis_editing.py:90`, `document-parser/api/schemas.py:206`, `frontend/src/features/analysis-editor/types.ts:55` ; desormais aussi propage par le nouvel adaptateur `document-parser/infra/docling_analysis_engine.py:46` ;
  - `referenceChanges` : calcule `document-parser/infra/docling_editor.py:63-74`, transporte `infra/docling_analysis_engine.py:45`, `api/schemas.py:207`, `frontend/src/features/analysis-editor/types.ts:56`, lu nulle part dans `frontend/src` ;
  - `engine_version` : `document-parser/services/analysis_edit_service.py:38` et `:154`, jamais compare ; `previous_hash` : `document-parser/persistence/analysis_edit_repo.py:160-196`, jamais relu ;
  - reconstruction : `document-parser/api/analysis_edits.py:198-205`, `services/analysis_edit_service.py:248`, client `frontend/src/features/analysis-editor/api.ts:71` sans appelant ;
  - second protocole de deplacement : `document-parser/infra/docling_editor.py:295`, `api/schemas.py:168`, `api/analysis_edits.py:100`, `frontend/src/features/analysis-editor/types.ts:15`, alors que l'UI n'emet que `targetElementId` + `placement` (`frontend/src/features/analysis-editor/store.ts:197-200`).
- **Constat** : #394-#400 n'ont rien retire. Sur cache valide, `content_markdown`, `content_html`, `pages_json`, `result_hash`, `updated_at` ne sont toujours pas relus : la reponse est reprojetee. Le port moteur de #394 recopie `warnings` et `reference_changes` dans un fichier de plus. #395 ajoute un repli « cache corrompu → rejeu » (`analysis_edit_service.py:297-320`), utile, qui confirme que le cache n'economise que le rejeu.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : inchangee (servir les colonnes stockees ou les retirer ; retirer `warnings`/`referenceChanges` du contrat ; retirer ou documenter `engine_version`/`previous_hash` ; brancher ou retirer `rebuild` ; retirer `beforeElementId`). Effort M.

### [MIN] Configuration MCP en couches — reconduit, inchange

- **Localisation** : `document-parser/infra/settings.py:90-122` et `:259-280`, `document-parser/domain/mcp_config.py:44` et `:107-113`, `document-parser/services/mcp_config_service.py:55`, `:84-93`, `:100`, `document-parser/services/navigation_config.py:32` et `:70`, `document-parser/mcp_stdio.py:63-78`, `document-parser/infra/settings.py:67` et `:182-183` (`ASK_MODE` a deux valeurs texte)
- **Constat** : `git diff --stat eade7fa a6fb539` est vide pour `infra/settings.py`, `domain/mcp_config.py`, `services/mcp_config_service.py`, `services/navigation_config.py`, `bootstrap/mcp_mount.py`, `mcp_stdio.py`. Seul `api/config.py` change (passage a `http_error`, sans effet sur la config). Trois representations pour quatre knobs, `MCP_MAX_READ_TOKENS` en double (`settings.py:107`, `navigation_config.py:32`), `ANALYSIS_EDITOR_ENABLED` (`settings.py:279`) toujours sans helper `_env_bool`.
- **Regle violee** : item 4.5 (poids 1).
- **Remediation** : inchangee (une seule source des bornes et defauts dans `domain/mcp_config.py`, `max_rounds` en env seul, stdio respecte `enabled`, `ASK_MODE` booleen, helper `_env_bool`).

### [MIN] Carte de citation desactivee par defaut, et maintenant traduite — reconduit, aggrave

- **Localisation** : `document-parser/infra/settings.py:119` et `:274` (`MCP_CITATION_CARD=false`), `document-parser/mcp_adapter/apps.py:141-142` et `:146`, `document-parser/mcp_adapter/citation_app.html` (1 256 l., +79 depuis `eade7fa`), `document-parser/services/citation_service.py:57`
- **Constat** : la fonctionnalite reste couverte par `show_sources` et eteinte par defaut. Le commit `256c494` (#397) lui a pourtant ajoute un dictionnaire EN/FR complet (`MESSAGES`, `citation_app.html:409`) : on investit dans un code que le deploiement par defaut ne charge pas.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : retirer la carte, ou statuer dans le design #363 et l'activer. Ne plus la maintenir en l'etat.

---

### [INFO] Priorisation de la page courante : justifiee, lecture perfectible (nouveau)

- **Localisation** : `frontend/src/features/document/ui/PagePreviewWithOverlay.logic.ts:14-30` (`pageInRenderWindow`, 6 parametres positionnels dont 2 booleens), `frontend/src/features/document/ui/PagePreviewWithOverlay.vue:197-199` (3 `Set` d'etat), `:238-256` (`registerImage` / `registerPdf` quasi identiques), `:289-318` (`onImageLoad` / `onPdfReady`, `onImageError` / `onPdfError`), `:326-335` (`shouldRenderPage`)
- **Constat** : la fenetre de rendu (page courante, une precedente, deux suivantes, suivantes seulement apres la page courante) tient en ~15 lignes de logique pure testee, et repose sur une mesure (`docs/design/pdf-loading-performance.md`, TTFB 4,6–6,8 s quand trois rendus froids partent ensemble). Elle s'applique aussi aux canvas PDF.js via `shouldRenderPage`, ce qui reste pertinent avec le chargement par plages. Pas de file d'attente ni d'ordonnanceur : simple et proportionne. Le cout est dans le composant : deux jeux de gestionnaires presque jumeaux pour les deux chemins.
- **Remediation** : un objet d'options pour `pageInRenderWindow` ; fusionner `registerImage`/`registerPdf` et `onImageLoad`/`onPdfReady` en un gestionnaire « page prete » commun.

### [INFO] Deux rasteriseurs PDF, dont un hors port (nouveau dans le chemin apercu)

- **Localisation** : `document-parser/services/document_service.py:15` (import `pdf2image` dans un service) et `:160-179` (`generate_preview`), appele par `document-parser/services/preview_service.py:42-48` ; port existant `document-parser/domain/ports.py:514` (`PageRasterizer.render_page`) et `document-parser/infra/page_raster.py:26-36`
- **Constat** : #401 a cree un port pour le cache de 40 lignes, mais le rendu, qui est l'adaptateur d'infrastructure, passe par une methode statique de `DocumentService` alors que `PageRasterizer` fait deja la meme chose (meme `convert_from_path`, meme garde `is_file`, #398). Deux implementations du rendu d'une page. 4.6 reste conforme (une couche de plus seulement), mais le port n'apporte pas la simplicite attendue.
- **Remediation** : `PreviewService` depend de `PageRasterizer` (ajouter le format WebP a `render_page`) ; supprimer `DocumentService.generate_preview`. Recoupe les audits 01 et 05.

### [INFO] Erreurs du `PreviewService` hors de la base `ServiceError` introduite en meme temps (nouveau)

- **Localisation** : `document-parser/services/preview_service.py:14-19`, `document-parser/api/documents.py:182-202` (7 branches `except`), `document-parser/services/errors.py:11`, `document-parser/api/errors.py:25`
- **Constat** : #396 a cree une base d'erreur unique et un traducteur HTTP central. Le service d'apercu, ajoute ensuite, definit deux exceptions a part et la route garde une echelle de 7 `except`, dont `ValueError` generique → 404 apres `PreviewPageOutOfRangeError(ValueError)` → 400. Lisible mais contraire a la simplification qui vient d'etre faite.
- **Remediation** : deriver les deux erreurs de `ServiceError` (404 / 400) et utiliser `http_error`.

### [INFO] Ouverture d'une analyse en deux temps avec un objet `Analysis` fabrique (nouveau, 4.6/4.8 a la limite)

- **Localisation** : `frontend/src/pages/AnalysisDetailPage.vue:107-141`, `:88-94` ; `document-parser/persistence/analysis_repo.py:72` (`limit=200`)
- **Constat** : pour afficher plus tot le squelette des pages, la page telecharge la liste de toutes les analyses (`/api/analyses/summaries`, 200 dernieres), y cherche la sienne, appelle `/pages`, fabrique un `Analysis` avec `pagesJson: JSON.stringify(pages)`, `hasDocumentJson: false` et des contenus `null`, que `previewPages` reparse aussitot, puis demande l'analyse complete. Trois requetes sequentielles au lieu d'une, une serialisation aller-retour d'un tableau, et un objet de domaine temporairement faux (le bouton d'edition est desactive pendant ce temps). Au-dela de 200 analyses, la recherche echoue silencieusement et la page retombe sur le chemin normal. Le bloc `catch` a trois issues. C'est un contournement de l'absence d'un manifeste par analyse (phase 2 du document de conception).
- **Remediation** : un `GET /api/analyses/{id}/summary` (ou la phase 2), lance en parallele de `fetchAnalysis` ; passer `Page[]` au lieu d'une chaine.

### [INFO] Port moteur de l'editeur : un relais pur (nouveau, 4.3 juge conforme)

- **Localisation** : `document-parser/infra/docling_analysis_engine.py:49-60` (`project_serialized` delegue tel quel), `document-parser/domain/ports.py:305-331`
- **Constat** : le port (#394) est justifie : plus aucun type Docling ne traverse le service et le travail part en thread. `project` compose editeur + projecteur ; `project_serialized` n'ajoute rien. Cout faible.
- **Remediation** : aucune obligatoire.

### [INFO] Flux de commandes event-sourced avec chaine de hash (reconduit, 4.1 juge conforme)

- **Localisation** : `document-parser/persistence/database.py:233-269`, `document-parser/persistence/analysis_edit_repo.py:160-196`
- **Constat** : inchange. Besoin exprime (annulation au milieu de l'historique, base immuable), implementation lineaire ; la chaine `previous_hash` reste sans verificateur.

### [INFO] Introspection d'une API privee Docling (reconduit, 4.7 juge conforme)

- **Localisation** : `document-parser/infra/docling_editor.py:316-329`
- **Constat** : inchange, isole et commente.

### [INFO] Aller-retours JSON dans le projecteur (reconduit, 4.8 juge conforme)

- **Localisation** : `document-parser/infra/docling_projector.py:68-69` (`json.dumps`), `:85` (`json.loads`), `document-parser/api/analysis_edits.py:58` (`json.loads` du modele a chaque reponse), `document-parser/infra/docling_projector.py:202-213` (`freeze`)
- **Constat** : inchange.

### [INFO] Chemins de repli jamais pris en production (reconduit, 4.6 juge conforme)

- **Localisation** : `document-parser/services/export_service.py:43`, `:119`, `:143` ; `document-parser/services/chunk_service.py:149`, `:369`
- **Constat** : `active_result_service=None` reste possible alors que `bootstrap/builder.py` l'injecte toujours.

### [INFO] Pont MCP Apps ecrit a la main en deux copies (reconduit)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:770-850`, `document-parser/mcp_adapter/sources_app.html:1156-1230`
- **Constat** : inchange sur le fond ; #397 a modifie les deux fichiers en parallele (i18n), ce qui illustre le cout de la double copie.

### [INFO] Aides mortes et relais sans valeur ajoutee (reconduit, inchange)

- **Localisation** : `document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`, `document-parser/mcp_adapter/server.py:90`, `document-parser/mcp_adapter/prompts.py:52`, `document-parser/services/mcp_config_service.py:100`, `document-parser/services/app_config_service.py:144`, `document-parser/services/analysis_edit_service.py:322-324` (`_replay`)

### [INFO] Residuels reconduits : `crop` a boite sentinelle, repli de chemin de dev, `ReasoningStepKind`/`StepId`/`health_check`

- **Localisation** : `document-parser/services/citation_image_service.py:91` ; `document-parser/services/document_service.py:119-131` (desormais aussi sur le chemin apercu via `services/preview_service.py:36`) ; `document-parser/domain/value_objects.py:193`, `document-parser/api/schemas.py:656`, `document-parser/domain/ports.py:461` (`health_check` sans appelant hors adaptateur)

---

## Delta vs audit du 2026-11-13

Score : **75 → 75 (0)**. Items conformes : 6/8 → 6/8. Memes items non conformes (4.2, 4.5).
Les commits #394-#400 n'ont traite aucun ecart KISS ; ils simplifient ailleurs (voir points
positifs). La PR #401 ajoute un ecart MIN sous 4.2 et plusieurs INFO sans faire basculer
d'item (4.8 a la limite, voir tableau).

| Ecart du 2026-11-13 | Statut au 2026-11-18 | Detail |
|---------------------|----------------------|--------|
| [MAJ] Abstraction LLM-provider prematuree (4.2) | **Toujours present** | Lignes identiques, 4e report |
| [MIN] Plomberie speculative de l'editeur (4.2) | **Toujours present** | Etendu d'un fichier par le port moteur (`docling_analysis_engine.py:45-46`) |
| [MIN] Configuration MCP en couches (4.5) | **Toujours present** | Aucun fichier de config MCP modifie |
| [MIN] Carte de citation desactivee (4.2) | **Toujours present, aggrave** | +79 lignes d'i18n dans `citation_app.html` |
| [INFO] Flux event-sourced, chaine de hash | Toujours present | |
| [INFO] Introspection `_move_subtree` | Toujours present | |
| [INFO] Aller-retours JSON du projecteur | Toujours present | |
| [INFO] Replis jamais pris (export, chunk) | Toujours present | |
| [INFO] Pont MCP Apps en deux copies | Toujours present | |
| [INFO] Aides mortes / relais | Toujours present | |
| [INFO] `crop` residuel, repli de dev, `ReasoningStepKind`/`StepId`/`health_check` | Toujours presents | |

Nouveaux ecarts : [MIN] repli serveur des apercus equipe comme un chemin principal (4.2) ;
[INFO] priorisation, double rasteriseur, erreurs d'apercu hors `ServiceError`, ouverture
d'analyse en deux temps, relais du port moteur.

---

## Points positifs

- **PDF.js reutilise l'existant** : le rendu navigateur charge le PDF par la route d'export deja presente (`frontend/src/features/document/ui/usePdfDocument.ts:25-30`, `getExportUrl(id, 'pdf')`) ; Starlette `FileResponse` sert les plages HTTP sans code serveur nouveau. Une bibliotheque standard plutot qu'un rendu maison.
- **Composable unique** : `usePdfDocument.ts` (47 l.) et `PdfPageCanvas.vue` (101 l.) sont partages par les 7 visionneuses ; le repli est local et automatique.
- **Simplifications #396/#398** : un seul analyseur ISO (`persistence/iso_datetime.py`, 27 l.) remplace des copies par repository ; une seule base d'erreurs (`services/errors.py`, 19 l.) et un seul traducteur HTTP (`api/errors.py:25-31`, une table au lieu de branches) ; ecritures SQL par lots (`persistence/chunk_repo.py`, `soft_delete_many`, `shift_sequences`) ; rendu poppler par chemin au lieu de lire tout le PDF (`infra/page_raster.py:26-31`).
- **Port moteur (#394)** : `AnalysisDocumentEngine` sort Docling du service sans pattern supplementaire ; le calcul part en thread (`services/analysis_edit_service.py:326-331`).
- **Compression nginx** : 5 lignes (`nginx.conf.template:4-8`) au lieu d'une compression applicative.
- **Listes legeres** : `fetchAnalysisSummaries` remplace la liste complete dans l'historique et la bibliotheque (#401, `85450a4`).

---

## Non verifie

- Frequence reelle du repli serveur en production (aucune mesure dans le depot) : le jugement sur le cache repose sur le code et l'historique, pas sur des chiffres.
- Comportement de PDF.js derriere le proxy nginx de production (plages HTTP) : application non lancee.
- La reecriture de `tests/test_architecture.py` (`de5fe66`, liste d'exceptions tolerees) releve de l'audit 01 et n'est pas jugee ici.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL. Un ecart MAJOR (abstraction LLM-provider, reconduit depuis 0.7.0),
sous le seuil bloquant (> 3). Score 75 / 100 (60-79). Conditions : planifier le MAJ en 0.8.0 ;
pour la 0.7.4, au minimum mettre a jour `docs/design/pdf-loading-performance.md` et decider
du sort de `PreviewCache` ; pour repasser 4.2 conforme il faut traiter ensemble le MAJ, la
carte de citation, la plomberie de l'editeur et l'equipement du repli d'apercu.

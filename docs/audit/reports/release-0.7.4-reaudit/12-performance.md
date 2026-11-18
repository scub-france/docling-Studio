# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` `f7fc791` avec PR #401 et #402, plus les correctifs #391-#400), lu dans l'arbre de travail.
**Baseline** : `release-0.7.4/12-performance.md` (2026-11-13, `eade7fa`) : 52/100, NO-GO, 1 CRIT, 2 MAJ.

Méthode : lecture statique du code, plus des micro-mesures isolées
(`document-parser/.venv/bin/python`, Python 3.12.2, machine 16 cœurs) sur des données
synthétiques : un `DoclingDocument` construit en mémoire (28 pages / 448 éléments, et
300 pages / 7 800 éléments, `document_json` de 6,24 Mo), et une page raster 1275×1650
dessinée avec PIL. Aucune application lancée, aucun réseau. Chaque chiffre est marqué
**mesuré** (micro-mesure ci-dessus) ou **estimé**. Les durées mesurées dépendent de la
machine et d'un document synthétique (texte seul, sans tableaux ni images) : ce sont
des ordres de grandeur.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 10 / 13 |
| Score | 86 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 6 |
| Écarts INFO | 9 |

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 12.1.1 | Pas de requête N+1 | 2 | Oui | Rechunk, restauration, fusion et décalage passent chacun par un seul `UPDATE` ou un `executemany` (`persistence/chunk_repo.py:66-71,105-151`). Reste `show_sources` (borné, voir MIN). |
| 12.1.2 | Fichiers temporaires supprimés | 2 | Oui | Pas de fichier temporaire applicatif ; refus de page count → `os.unlink` en thread (`services/document_service.py:96`). |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` respectée | 2 | Oui | `infra/settings.py:24,215` → `services/analysis_service.py:100,424`. |
| 12.1.4 | Opérations longues hors event loop | 3 | Oui | Les deux seuls appels au moteur passent par `asyncio.to_thread` (`services/analysis_edit_service.py:304-309,331-336`) ; rendu de page, tailles de page, conversion, chunking, import aussi. Test dédié `tests/test_analysis_editing.py:641`. |
| 12.1.5 | Pas de fichier entier en mémoire | 2 | Oui | Poppler et pdfium ouvrent le PDF par chemin (`services/document_service.py:170,190`, `infra/page_raster.py:31`) ; le PDF part au navigateur par `FileResponse` avec `Range`. |
| 12.2.1 | Watchers avec cleanup | 2 | Oui | `PdfPageCanvas.vue:77-89`, `usePdfDocument.ts:40-44`, `BboxCanvas.vue:254-275`. |
| 12.2.2 | Listeners retirés au démontage | 2 | Oui | `AnalysisEditor.vue:505-513`, `StudioPage.vue:675-676`, `TableModal.vue:46-47`, `DownloadDropdown.vue:200-204`. |
| 12.2.3 | Annulation / debounce | 1 | Oui | Aperçu différé de 400 ms et annulable (`features/analysis-editor/store.ts:105-113,206-207`) ; rendu PDF.js annulé (`PdfPageCanvas.vue:39-48,87`). |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | Fenêtre de rendu de 4 pages au plus (`PagePreviewWithOverlay.logic.ts:14-30`), `shallowRef` sur le document PDF (`usePdfDocument.ts:8`). |
| 12.2.5 | Assets lourds optimisés | 1 | **Non** | `frontend/public/logo.png` (878 643 octets) servi en favicon (`frontend/index.html:7`). |
| 12.3.1 | Cache nginx des statiques | 1 | **Non** | Aucun `expires` / `Cache-Control` (`nginx.conf.template:19-21`, `frontend/nginx.conf.template`). |
| 12.3.2 | Réponses API de taille raisonnable | 1 | **Non** | Réponses de l'éditeur redondantes (13,8 Mo mesurés à 300 pages), double chargement au workspace. |
| 12.3.3 | Health check léger | 1 | Oui | `SELECT 1` (`document-parser/main.py:130-139`). |

Poids total = 21. Non conformes : 12.2.5 (1) + 12.3.1 (1) + 12.3.2 (1) = 3.
Poids conformes = 18. `18 / 21 * 100 = 85,7` → **86 / 100**.

### Appels bloquants ou CPU atteignables depuis une route `async`

| Appel | Localisation | Sur la loop ? | Coût |
|---|---|---|---|
| Rejeu + projection (`engine.project`) | `services/analysis_edit_service.py:331-336` | Non (`to_thread`) | 173 ms (28 p.), 2 974 ms (300 p.), mesuré |
| Projection du cache (`project_serialized`) | `services/analysis_edit_service.py:304-309` | Non (`to_thread`) | 93 ms / 2 153 ms, mesuré |
| Rendu de page poppler + encodage WebP sans perte | `services/preview_service.py:42-48` → `services/document_service.py:160-179` | Non | encodage : 36 ms WebP sans perte vs 71 ms PNG (16 Kio vs 68 Kio), mesuré |
| `stat` du PDF pour la clé de cache | `services/preview_service.py:37` | Non | — |
| Tailles de page pdfium | `api/documents.py:215` | Non | — |
| Conversion, fusion de lots, chunking, import Docling | `infra/local_converter.py:201,204`, `infra/local_chunker.py:106`, `services/analysis_service.py:180` | Non | — |
| Index de parse (MCP) | `services/parse_loader.py:108` | Non | — |
| `json.loads(editor_model_json)` + construction et sérialisation de la réponse éditeur | `api/analysis_edits.py:57-68` + FastAPI | **Oui** | ~1 ms (28 p.), **115 ms** (300 p.), mesuré |
| `json.loads(document_json)` + `_build_tree_nodes` (arbre) | `services/chunk_service.py:712-716` | **Oui** | 67 ms (300 p.), mesuré |
| `sha256` du `document_json` | `services/analysis_edit_service.py:83,148,175,380`, `services/chunk_service.py:415` | **Oui** | 0,1 ms / 2,6 ms, mesuré |
| `_count_pdf_pages` (pdfium) | `services/analysis_service.py:449` → `:59-68` | **Oui** | ms, estimé (ouverture du xref seulement) |
| `Path.is_file` / `resolve_storage_path` | `services/preview_service.py:36`, `services/export_service.py:86`, `api/documents.py:214` | **Oui** | µs, estimé |
| `pages_json = json.dumps(...)` à la fin d'une analyse | `services/analysis_service.py:467` | **Oui** | linéaire, une fois par analyse, estimé faible |

Aucun appel restant sur la loop n'est une opération longue au sens de 12.1.4 : ce sont
des traitements linéaires, sous 120 ms pour 300 pages (mesuré). Le plus lourd
(réponse de l'éditeur) découle de la taille de la réponse et est traité sous 12.3.2.

---

## Écarts constatés

### [MIN] Réponses de l'éditeur volumineuses et redondantes ; double chargement au workspace (item 12.3.2)

- **Localisation** : `document-parser/api/schemas.py:199-207` (`AnalysisEditorResponse` : `model`, `tree`, `result` complet) ; `document-parser/api/analysis_edits.py:57-68` ; renvoyée par chaque aperçu (`frontend/src/features/analysis-editor/store.ts:105-106` → `:206-223`). Workspace : `frontend/src/features/document/store.ts:25-34` (analyse de base complète via `fetchAnalysis`, puis réponse complète de l'éditeur, pour garder trois champs). Suppression d'un document : `frontend/src/pages/DocsLibraryPage.vue:345` charge la liste **complète** des analyses du document (`/api/analyses?documentId=`, `features/analysis/api.ts:63-65`) pour n'en lire que la longueur.
- **Constat** : mesuré sur le document synthétique de 300 pages : corps de réponse de **13,76 Mo** par chargement ou aperçu (0,78 Mo à 28 pages), dont modèle 4,75 Mo, `document_json` non renvoyé mais pages 2,71 Mo, Markdown 1,90 Mo, HTML 1,95 Mo. La construction et la sérialisation de cette réponse prennent **115 ms sur l'event loop** (mesuré, `_to_editor_response` + `serialize_response` + `JSONResponse`), à chaque aperçu. Le texte du document part ~5 fois par réponse. La liste `/summaries` (#354) règle en revanche le polling des listes (voir points positifs).
- **Règle violée** : 12.3.2 (poids 1).
- **Remédiation** : un endpoint « résultat actif » léger (Markdown, pages) pour le workspace ; aperçu sans `contentHtml` (non affiché) ni `result.pagesJson` en double du modèle ; `tree` en ids + type ; un compteur d'analyses par document pour la suppression. Effort M.

### [MIN] Logo PNG 1024×1024 (858 Kio) servi en favicon — inchangé (item 12.2.5)

- **Localisation** : `frontend/public/logo.png` (878 643 octets), `frontend/index.html:7`. Un `frontend/public/favicon.svg` (270 octets) existe mais n'est pas référencé.
- **Règle violée** : 12.2.5 (poids 1).
- **Remédiation** : référencer `favicon.svg` ; compresser le logo (< ~100 Kio). Effort S.

### [MIN] Nginx sans cache des statiques, et gzip limité au JSON (item 12.3.1)

- **Localisation** : `nginx.conf.template:4-8` (`gzip_types application/json` seulement), `:19-21` (aucun `expires` ni `Cache-Control`) ; `frontend/nginx.conf.template` (ni gzip ni cache).
- **Constat** : inchangé. #401 ajoute deux gros fichiers chargés à l'ouverture d'un PDF : `pdf-*.js` 501 336 octets (149 748 en gzip) et `pdf.worker.min-*.js` 1 228 596 octets (385 585 en gzip), mesurés sur `frontend/dist/assets` du build courant. Servis sans compression et sans cache explicite (le navigateur revalide au mieux par heuristique). Le chunk `pdf-*.js` est bien chargé à la demande (`import('pdfjs-dist')`, `usePdfDocument.ts:22` ; absent de `dist/index.html`).
- **Règle violée** : 12.3.1 (poids 1).
- **Remédiation** : `location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }`, `no-cache` sur `index.html` ; `gzip_types` étendu à `application/javascript text/css image/svg+xml` (sans `application/pdf`, pour garder les requêtes `Range`). Penser à répéter les `add_header` de sécurité dans le nouveau bloc. Effort S.

### [MIN] `show_sources` refait la résolution de parse pour chaque citation — inchangé (hors checklist)

- **Localisation** : `document-parser/services/source_service.py:102` (`_check` par citation) → `services/citation_service.py:99` → `services/parse_loader.py:78,83-90`.
- **Constat** : l'index de parse est en cache LRU (`parse_loader.py:99-111`), donc le coût par citation se réduit à 2-3 requêtes légères ; le nombre de citations est borné (`source_service.py:188-196`). N+1 borné, conservé en MIN comme dans la baseline ; n'entre pas dans 12.1.1.
- **Remédiation** : charger la parse une fois par appel. Effort S.

### [MIN] pdfium appelé sans le verrou partagé avec Docling — inchangé (hors checklist, PLAUSIBLE)

- **Localisation** : `document-parser/services/document_service.py:190` (`page_sizes`, exécuté en thread par `api/documents.py:215`) ; `services/analysis_service.py:59-68` (`_count_pdf_pages`, appelé sur la loop `:449`). Le verrou existe : `infra/page_text.py:21-24,31`.
- **Constat** : pdfium n'est pas thread-safe (`infra/page_text.py:7`). Depuis #398, `page_sizes` tourne dans un thread de travail, donc potentiellement en parallèle d'une conversion Docling qui utilise pdfium. Risque de plantage natif, non reproduit.
- **Remédiation** : prendre `_pdfium_lock` dans `page_sizes` et `_count_pdf_pages` ; passer `_count_pdf_pages` en thread. Effort S.

### [MIN] Suivi des analyses à 3 s sans plafond de durée — inchangé (hors checklist)

- **Localisation** : `frontend/src/features/analysis/store.ts:177-188` (`followActive`), appelé par `pages/AnalysisLibraryPage.vue:138`.
- **Constat** : la requête est désormais légère (`/summaries`), mais une analyse restée `RUNNING` après un crash du backend fait poller indéfiniment.
- **Remédiation** : plafond de durée comme `MAX_POLLING_DURATION` du polling unitaire (`store.ts:38,137`). Effort S.

### [INFO] Reliquat de CPU sur l'event loop (mesuré)

- **Localisation** : voir le tableau des appels ci-dessus ; principaux postes : réponse de l'éditeur `api/analysis_edits.py:57-68` (115 ms à 300 p.), arbre `services/chunk_service.py:712-716` (67 ms à 300 p.), `sha256` répétés `services/analysis_edit_service.py:83,148,175,380` (2,6 ms chacun à 300 p.).
- **Constat** : linéaire, sous le dixième de seconde pour un gros document. À regrouper dans le thread de projection (le service pourrait rendre le modèle déjà décodé et le hash déjà calculé) si les documents grossissent.

### [INFO] Projections parallèles non bornées, pool de threads partagé, GIL

- **Localisation** : `services/analysis_edit_service.py` (aucun sémaphore) ; `asyncio.to_thread` partout utilise l'exécuteur par défaut (`min(32, os.cpu_count() + 4)` en Python 3.12) ; un seul worker uvicorn (`Dockerfile:65`).
- **Constat** : les conversions (jusqu'à 3, plusieurs minutes chacune), les projections (~3 s CPU à 300 p., mesuré), les rendus de page et les index MCP se partagent le même pool. La projection est du Python pur : elle tient le GIL, donc plusieurs aperçus ou ouvertures de workspace en parallèle ralentissent aussi la loop, sans la geler. Chaque projection garde en mémoire deux copies du document (`docling_projector.py:57`) plus les exports (estimé : quelques dizaines de Mo pour 300 pages). Non mesuré en charge.
- **Suggestion** : sémaphore d'éditeur (1-2) ; exécuteur dédié pour les conversions.

### [INFO] Cache mono-slot `_unedited_projection` partagé entre documents

- **Localisation** : `services/analysis_edit_service.py:74,82-86,101-102`.
- **Constat** : un seul tuple pour tout le processus (le service est un singleton, `bootstrap/builder.py:125`), clé `(analysis_id, hash)` vérifiée : pas de résultat faux possible, l'écriture concurrente est sans danger. Deux onglets sur deux documents s'évincent l'un l'autre ; une analyse éditée relance `project_serialized` (2,2 s à 300 p., mesuré, en thread) à chaque ouverture de workspace, export md/json ou arbre. Mémoire bornée à un `ProjectedAnalysis` (~11 Mo de chaînes à 300 p., mesuré sur les tailles des champs).

### [INFO] Cache de previews : sain, sans coalescence des requêtes

- **Localisation** : `infra/preview_cache.py:16-40`, `services/preview_service.py:36-49`.
- **Constat** : LRU borné à 64 Mo, comptage en octets correct (ancienne valeur retirée, éviction jusqu'au plafond, image plus grande que le plafond ignorée), verrou `threading.Lock`, clé invalidée par taille + `mtime_ns`. Deux requêtes simultanées sur la même page manquante rendent deux fois (pas de *single-flight*). Les previews raster ne servent plus qu'en repli quand PDF.js échoue (`PagePreviewWithOverlay.vue:104-106`, `PdfPagePreview.vue:12-14`).

### [INFO] PDF.js : un document par visionneuse, comportement derrière nginx non vérifié

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts:7-46` ; `features/analysis-editor/ui/AnalysisEditor.vue:107` (visionneuse pendant le chargement) puis `:274` (après chargement) ; `nginx.conf.template:23-30`.
- **Constat** : chaque visionneuse ouvre son propre `PDFDocumentProxy`. Dans l'éditeur, la fin du chargement démonte la première et en monte une seconde : le document est détruit (`destroy()` bien appelé, `usePdfDocument.ts:20,41-44`) puis rouvert (quelques requêtes de 256 Kio de plus, estimé). Les `Range` sont correctement servis : `FileResponse` de Starlette 1.0.0 gère `Range` (`.venv/.../starlette/responses.py:362-372`), nginx transmet l'en-tête et ne compresse pas le PDF. Non vérifié sans lancer l'app : ce que nginx (`proxy_buffering` par défaut) lit du backend quand PDF.js abandonne la première requête complète.

### [INFO] Coûts quadratiques du rejeu — déclassé de MIN (hors checklist)

- **Localisation** : `document-parser/infra/docling_editor.py:142-163` (`_is_descendant` pour chaque paire), `:90`, `:214` (`_in_document_order` à chaque `mergeText`), `:332`.
- **Constat** : code inchangé, mais il s'exécute désormais dans un thread : il ne gèle plus la loop. Reste un coût CPU pour de longues sélections ou des centaines de fusions rejouées.

### [INFO] Réactivité profonde sur les réponses de l'éditeur

- **Localisation** : `frontend/src/features/analysis-editor/store.ts:17,19` (`ref<AnalysisEditorResponse>` pour `saved` et `preview`).
- **Constat** : la réponse entière (modèle de 7 800 éléments, arbre, chaînes de plusieurs Mo à 300 p.) est rendue réactive en profondeur. Les proxys sont créés à l'accès, donc le coût suit ce que la vue parcourt. Non mesuré. `shallowRef` suffirait, la réponse étant remplacée en bloc.

### [INFO] Minuteur d'aperçu non annulé au démontage de l'éditeur — inchangé

- **Localisation** : `frontend/src/features/analysis-editor/store.ts:33,105-106` (store Pinia global) ; `ui/AnalysisEditor.vue:509-513` (`onBeforeUnmount` n'appelle ni `clearTimeout` ni `abort`). `discard()` (`store.ts:302-304`) le fait, mais seulement sur abandon explicite.
- **Constat** : quitter l'éditeur moins de 400 ms après une frappe envoie encore un aperçu (une projection serveur inutile).

### [INFO] Observations reportées de 0.7.0 — inchangées

- Connexion SQLite neuve par appel, pas de WAL (`persistence/database.py:358-373`) ; chaque requête `Range` de PDF.js ouvre une connexion (`services/export_service.py:81`). Upload lu en mémoire, borné par `max_file_size` (`services/document_service.py:75`).

---

## Delta vs audit du 2026-11-13

| Écart du 2026-11-13 | Statut à `a6fb539` | Preuve |
|---|---|---|
| [CRIT] 12.1.4 rejeu / projection sur l'event loop | **Résolu** | `services/analysis_edit_service.py:304-309,331-336` ; seuls appels au moteur (grep sur `.project(`, `project_serialized`, `_engine.`) ; test `tests/test_analysis_editing.py:641` |
| [MAJ] 12.1.5 PDF entier relu par page rendue | **Résolu** | `services/document_service.py:170` (`convert_from_path`, une page), `:190` (pdfium par chemin), `infra/page_raster.py:31` ; `PreviewService` passe le chemin (`services/preview_service.py:42-48`) |
| [MAJ] 12.1.1 une requête par chunk | **Résolu** | `persistence/chunk_repo.py:118-151` (un `UPDATE` chacun) ; appelants `services/chunk_service.py:351,388,404,744`, `services/version_service.py:179,187` |
| [MIN] 12.3.2 réponses de l'éditeur, double chargement | **Ouvert**, quantifié (13,76 Mo, 115 ms sur la loop à 300 p.) ; `/summaries` corrige la partie liste | — |
| [MIN] 12.2.5 logo | Ouvert | — |
| [MIN] 12.3.1 cache nginx | Ouvert, aggravé par les 1,7 Mo de PDF.js non compressés | — |
| [MIN] `show_sources` | Ouvert | — |
| [MIN] pdfium hors verrou | Ouvert ; `page_sizes` désormais en thread, donc concurrent de Docling | — |
| [MIN] suivi 3 s sans borne | Ouvert | — |
| [MIN] coûts quadratiques du rejeu | Déclassé en INFO (hors loop) | — |
| [INFO] liste complète des analyses dans `features/analysis/store.ts` | **Résolu** (#354/#401) : `fetchAnalysisSummaries` (`store.ts:61,181`) | — |

Score : **52 → 86** (+7 points de poids : 12.1.4 +3, 12.1.5 +2, 12.1.1 +2). CRIT 1 → 0, MAJ 2 → 0.

---

## Points positifs

- **Moteur de l'éditeur derrière un port et hors loop** (#394) : `DoclingAnalysisEngine` (`infra/docling_analysis_engine.py:14-60`) est le seul point d'entrée Docling du service, appelé uniquement via `asyncio.to_thread`, avec un test qui vérifie le thread.
- **Écritures SQL groupées** (#398) : plus aucune boucle d'écriture par chunk ; les commandes d'édition sont insérées dans une transaction `BEGIN IMMEDIATE` avec contrôle de séquence (`persistence/analysis_edit_repo.py:147-198`), ce qui règle aussi les sauvegardes concurrentes.
- **Rendu PDF côté navigateur** (#401) : PDF.js en chargement par plages de 256 Kio sans préchargement automatique (`usePdfDocument.ts:25-30`), chunk chargé à la demande, `destroy()` au changement de document et au démontage, rendu annulé et attendu avant de réutiliser le canvas (`PdfPageCanvas.vue:39-48`), au plus 4 pages rendues autour de la page courante.
- **Liste des analyses légère** : `/api/analyses/summaries` sélectionne seulement les colonnes de statut (`persistence/analysis_repo.py:41-46,72-80`), un seul appel par tick de polling ; les listes complètes sont limitées à 200 lignes (`analysis_repo.py:62`).
- **Cache de previews correct** : LRU en octets, thread-safe, clé invalidée par `mtime`. L'encodage WebP sans perte est plus rapide et plus compact que PNG sur une page de texte (36 ms / 16 Kio contre 71 ms / 68 Kio, mesuré).
- Acquis conservés : sémaphore des conversions, health check `SELECT 1`, conversion / chunking / import en thread.

---

## Verdict partiel : GO

Score **86/100** (≥ 80), 0 CRIT, 0 MAJ. Les 6 MIN sont à traiter au prochain cycle ;
les plus rentables : cache + gzip nginx (S), favicon (S), verrou pdfium (S), puis
l'endpoint « résultat actif » léger pour le workspace et l'aperçu (M).

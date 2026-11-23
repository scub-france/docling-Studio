# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a12b744`, lu dans l'arbre de travail.
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur a6fb539 (`release-0.7.4-reaudit/12-performance.md` : 86/100, 10/13 items, 0 CRIT, 0 MAJ, 6 MIN).

Méthode : lecture du code (pas des messages de commit), `git diff a6fb539 a12b744` sur les
fichiers touchés, lecture du code de Docling installé dans `document-parser/.venv`
(docling 2.95.0, pypdfium2 4.30.0), et micro-mesures isolées avec
`document-parser/.venv/bin/python` (Python 3.12, machine 16 cœurs) sur des PDF synthétiques
générés avec pdfium (28 et 300 pages US Letter, 55 lignes de texte Helvetica par page,
28 Ko et 303 Ko). Les adaptateurs mesurés sont ceux de l'application
(`infra/pdf_inspector.py`, `infra/page_text.py`) importés tels quels. Aucune application
lancée, aucun réseau, aucune suite de tests relancée. Chaque chiffre est marqué
**mesuré** ou **estimé** ; les durées mesurées sont des ordres de grandeur (document
texte seul, sans images ni tableaux).

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 95 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 3 |
| Écarts INFO | 11 |

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre à `a12b744`) |
|---|------|-------|----------|---------------|
| 12.1.1 | Pas de requête N+1 | 2 | Oui | Écritures de chunks groupées (`persistence/chunk_repo.py:70,76,112,125`). `find_with_store_links` : 1 lecture document + 1 lecture des liens + au plus 1 `find_all` des stores, seulement s'il y a des liens (`services/document_service.py:152-168`) — même nombre de requêtes qu'avant le déplacement depuis la route. `show_sources` reste en MIN (borné). |
| 12.1.2 | Fichiers temporaires supprimés | 2 | Oui | Refus de page count → `os.unlink` en thread (`services/document_service.py:121`). |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` respectée | 2 | Oui | `bootstrap/factories.py:209` → `services/analysis_service.py:101` (sémaphore), pris à `:429`. |
| 12.1.4 | Opérations longues hors event loop | 3 | Oui | Projection et rejeu en `to_thread` (`services/analysis_edit_service.py:306,333`) ; conversion (`infra/local_converter.py:201,204`) ; tailles de page (`services/preview_service.py:77`) ; rendu (`:82`) ; comptage pour le batching désormais en thread (`services/analysis_service.py:451`, ex-`_count_pdf_pages` synchrone, supprimé) ; lecture des glyphes MCP (`services/source_service.py:170`) ; upload écrit + compté en un seul `to_thread` (`services/document_service.py:108-114`). |
| 12.1.5 | Pas de fichier entier en mémoire | 2 | Oui | pdfium et poppler ouvrent le PDF par chemin (`infra/pdf_inspector.py:31,47`, `infra/page_raster.py:31`, `infra/page_text.py:26`). |
| 12.2.1 | Watchers avec cleanup | 2 | Oui | `BboxCanvas.vue:258-279`, `usePdfDocument.ts:43-46`. |
| 12.2.2 | Listeners retirés au démontage | 2 | Oui | `AnalysisEditor.vue:509-513`, `StudioPage.vue:673-676`. |
| 12.2.3 | Annulation / debounce | 1 | Oui | Aperçu différé de 400 ms (`features/analysis-editor/store.ts:105-106`), annulé au démontage de l'éditeur (`AnalysisEditor.vue:513` → `store.ts:303-307`). |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | Inchangé ; `parseAnalysisPages` factorisé sans computed supplémentaire (voir effets). |
| 12.2.5 | Assets lourds optimisés | 1 | **Oui** | `frontend/public/logo.png` : 256×256, 61 510 octets (mesuré, `file` + `ls`), contre 1024×1024 / 878 643 octets. Affiché à 72 px au plus et en favicon (`frontend/index.html:7`). Reste perfectible (INFO). |
| 12.3.1 | Cache nginx des statiques | 1 | **Oui** | `location /assets/ { expires 1y; Cache-Control "public, immutable"; try_files $uri =404; }` dans les deux templates (`nginx.conf.template:26-34`, `frontend/nginx.conf.template:26-34`), `gzip_types` étendu à JS/CSS/SVG (`:5`). Couvre tous les fichiers fingerprintés émis par Vite. `index.html` n'est pas pris par ce bloc (bon), mais n'a pas non plus de `no-cache` explicite (INFO). |
| 12.3.2 | Réponses API de taille raisonnable | 1 | **Non** | Non ciblé ; inchangé : `AnalysisEditorResponse` renvoie toujours modèle + arbre + résultat complet (`document-parser/api/schemas.py:199-207`), double chargement au workspace (`frontend/src/features/document/store.ts:26-36`), liste complète pour compter (`frontend/src/pages/DocsLibraryPage.vue:345`). |
| 12.3.3 | Health check léger | 1 | Oui | `SELECT 1` (`document-parser/main.py:130-136`). |

Poids total = 21. Non conforme : 12.3.2 (1). Poids conformes = 20.
`20 / 21 * 100 = 95,2` → **95 / 100**.

### Appels pdfium et poppler atteignables depuis une route `async` (après remédiation)

| Appel | Localisation | Sur la loop ? | Verrou pdfium ? | Durée du verrou (mesuré, synthétique) |
|---|---|---|---|---|
| Tailles de page (`GET /api/documents/{id}/pages`) | `api/documents.py:179-183` → `services/preview_service.py:77` → `infra/pdf_inspector.py:27-43` | Non | Oui, tout le document | 9,7 ms (28 p.), **106 ms (300 p.)** |
| Comptage pour le batching | `services/analysis_service.py:469` → `:451` → `infra/pdf_inspector.py:45-51` | Non (avant : **oui**) | Oui | 0,07 ms / 0,20 ms |
| Glyphes MCP (`show_sources`) | `services/source_service.py:153-170` → `infra/page_text.py:24-32` | Non | Oui, par page lue | 9,0 ms par page |
| Comptage à l'upload (poppler `pdfinfo`) | `services/document_service.py:108-114` → `infra/pdf_inspector.py:53-65` | Non | **Non** (vérifié : appel exécuté verrou tenu par le même thread, sans blocage) | 10-11 ms de sous-processus |
| Rendu de page (poppler) | `services/preview_service.py:82` → `infra/page_raster.py:26-41` | Non | Non (poppler, pas pdfium) | — |

---

## Écarts constatés

### [MIN] Réponses de l'éditeur volumineuses et redondantes ; double chargement au workspace — inchangé (item 12.3.2)

- **Localisation** : `document-parser/api/schemas.py:199-207` ; `document-parser/api/analysis_edits.py:53-64` (`_to_editor_response`, `json.loads` du modèle sur la loop) ; `frontend/src/features/document/store.ts:26-36` ; `frontend/src/pages/DocsLibraryPage.vue:345` → `frontend/src/features/analysis/api.ts:63-65`.
- **Constat** : code inchangé depuis `a6fb539` (le refactor `25f5d8b` ne touche que les noms d'erreur et l'historique dans ce fichier). Les chiffres du re-audit restent valables : 13,76 Mo par chargement ou aperçu et 115 ms sur l'event loop à 300 pages (mesurés sur `a6fb539`, non remesurés ici, code identique).
- **Règle violée** : 12.3.2 (poids 1).
- **Remédiation** : endpoint « résultat actif » léger pour le workspace ; aperçu sans `contentHtml` ni `result.pagesJson` en double ; arbre réduit ; compteur d'analyses par document. Effort M.

### [MIN] `show_sources` refait la résolution de parse pour chaque citation — inchangé (hors checklist)

- **Localisation** : `document-parser/services/source_service.py:102` (`_check` par citation, `:172`) ; index en cache `services/parse_loader.py:58`.
- **Constat** : N+1 borné par le nombre de citations, chaque tour réduit à quelques requêtes légères grâce au cache LRU. S'y ajoute, depuis la remédiation, une ouverture du PDF par page citée, chacune sous le verrou pdfium (`infra/page_text.py:25-26`) — mémorisée par page dans l'appel (`source_service.py:154-163`), donc bornée.
- **Remédiation** : charger la parse une fois par appel ; ouvrir le PDF une fois pour toutes les pages lues. Effort S.

### [MIN] Suivi des analyses à 3 s sans plafond de durée — inchangé (hors checklist)

- **Localisation** : `frontend/src/features/analysis/store.ts:171-182` (`followActive`, sans borne), alors que le polling unitaire a `MAX_POLLING_DURATION` (`:39,131`).
- **Constat** : requête légère (`/summaries`), mais une analyse restée `RUNNING` après un crash du backend fait poller indéfiniment.
- **Remédiation** : même plafond de durée que le polling unitaire. Effort S.

### [INFO] Verrou pdfium partagé : attentes possibles derrière Docling, et maintien long par `page_sizes` (nouveau, effet de la remédiation)

- **Localisation** : `document-parser/infra/pdfium_lock.py:12-15` (verrou de Docling, `threading.Lock` non réentrant — vérifié : `pdfium_lock is docling.utils.locks.pypdfium2_lock` vaut `True` dans le venv) ; `infra/pdf_inspector.py:30-43,46-51` ; `infra/page_text.py:25-32` ; côté Docling : `.venv/.../docling/backend/docling_parse_backend.py:176,192,207,230,260,280`, `pypdfium2_backend.py:47,141,150,252,277,315,322,371,387,392,417,425,429,436`.
- **Constat** : Docling prend le verrou **par appel** pdfium (ouverture du document, `load_page`, `get_size`, rendu d'une page, fermeture), jamais pour toute une conversion ; le texte du backend par défaut (docling-parse) est lu hors verrou. Une requête de tailles de page, un comptage pour le batching ou une lecture de glyphes MCP attend donc au plus un appel Docling en cours. Rendu verrouillé d'une page synthétique : 3,6 ms à l'échelle 1,5 et 10,5 ms à l'échelle 3 (**mesuré**) ; pages riches en images ou vecteurs : dizaines à centaines de ms (**estimé**). Simulation d'une conversion (ouverture de page, taille, rendu, fermeture sous verrou, puis 2 à 20 ms hors verrou) : `page_sizes` 300 p. passe de 106 à 98-129 ms, `page_count` reste sous 25 ms, une lecture de glyphes passe de 9 à 10-36 ms (**mesuré**). Le `threading.Lock` n'est pas équitable : dans un test artificiel où un thread reprend le verrou en boucle sans pause, les attentes montent à 6 s (`page_count`) et 74 s (`page_sizes`) (**mesuré**) ; Docling travaille hors verrou entre deux appels (inférence, docling-parse), ce cas extrême n'est donc pas attendu en production (**estimé**, non vérifiable sans lancer une vraie conversion). Dans l'autre sens, `page_sizes` tient le verrou pendant tout le parcours des pages : 106 ms à 300 pages (**mesuré**), pendant lesquels les threads de conversion attendent. Cas limite hérité de Docling : un thread de conversion abandonné après timeout peut rester bloqué dans un appel pdfium en tenant le verrou (`standard_pdf_pipeline.py:630-635`) ; tout appel de l'inspecteur attendrait alors sans limite, et le comptage pour le batching s'exécute sous le sémaphore d'analyse (`analysis_service.py:429-432` → `:469`).
- **Interblocage** : aucun chemin trouvé. Aucune section verrouillée n'appelle un autre détenteur du verrou (`page_sizes`, `page_count`, `read_glyphs` n'appellent que pypdfium2) ; `count_pages_in_bytes` ne prend pas le verrou (vérifié en l'appelant verrou tenu : 13,9 ms, pas de blocage) ; aucune section verrouillée n'attend l'event loop (aucun `run_coroutine_threadsafe` / `from_thread` dans `document-parser/` hors `.venv`) ; Docling n'appelle pas les adaptateurs de l'application. Le rendu poppler (`infra/page_raster.py`) n'utilise pas pdfium.
- **Suggestion** : lire les tailles par `pdf.get_page_size(i)` (`FPDF_GetPageSizeByIndexF`, sans charger les pages) : 2,6 ms au lieu de 106 ms à 300 pages, résultats identiques sur le document synthétique (**mesuré**) — le verrou est alors tenu 40 fois moins longtemps. Optionnel : `acquire(timeout=…)` dans l'inspecteur pour ne pas bloquer un thread sans limite si Docling laisse un thread coincé.

### [INFO] `index.html` sans en-tête de cache explicite (nouveau, reliquat de 12.3.1)

- **Localisation** : `nginx.conf.template:19-21`, `frontend/nginx.conf.template:19-21` (`location /` sans `Cache-Control`).
- **Constat** : `index.html` n'est pas mis en cache un an (bon), mais il part sans `no-cache` : le navigateur peut le garder par heuristique (10 % de l'âge de `Last-Modified`). Après une mise à jour, un `index.html` périmé référence des fichiers `/assets/` qui n'existent plus ; le nouveau bloc répond alors 404 (`try_files $uri =404`, préférable au renvoi de `index.html` en `text/html` d'avant). Risque déjà présent avant la remédiation. `logo.png` et `favicon.svg`, à la racine de `dist`, ne sont pas sous `/assets/` et ne profitent pas du cache long (heuristique seulement) ; sans impact notable.
- **Suggestion** : `location = /index.html { add_header Cache-Control "no-cache"; … }` (en répétant les en-têtes de sécurité), ou `add_header Cache-Control "no-cache"` dans `location /`.

### [INFO] Logo encore surdimensionné pour son usage ; `favicon.svg` non référencé (reliquat de 12.2.5)

- **Localisation** : `frontend/public/logo.png` ; `frontend/index.html:7` ; `frontend/src/app/App.vue:19`, `pages/StudioPage.vue:5`, `pages/HomePage.vue:5`.
- **Constat** : 61 510 octets, quasi incompressible en gzip (61 227 octets au niveau 4, **mesuré**). Le même logo en WebP qualité 85 : 9 820 octets en 256 px, 4 672 octets en 144 px (**mesuré**, Pillow). `frontend/public/favicon.svg` (270 octets) existe toujours sans être utilisé.

### [INFO] Reliquat de CPU sur l'event loop — inchangé (mesures du re-audit)

- **Localisation** : `api/analysis_edits.py:53-64` (115 ms à 300 p.), `services/chunk_service.py:712-716` (67 ms à 300 p.), `sha256` `services/analysis_edit_service.py:386,403` et `services/chunk_service.py:778` (2,6 ms à 300 p.). Mesures du re-audit, code inchangé.
- **Constat** : `_count_pdf_pages` n'est plus sur la loop (amélioration). Le reste est linéaire et sous 120 ms pour 300 pages.

### [INFO] Projections parallèles non bornées, pool de threads partagé, GIL — inchangé

- **Localisation** : `services/analysis_edit_service.py` (pas de sémaphore) ; `asyncio.to_thread` partout (exécuteur par défaut, `min(32, cpu+4)` threads).
- **Constat** : depuis la remédiation, les appels de l'inspecteur qui attendent le verrou pdfium occupent eux aussi un thread de ce pool pendant l'attente (au plus un appel Docling, voir plus haut).

### [INFO] Cache mono-slot `_unedited_projection` partagé entre documents — inchangé

- **Localisation** : `services/analysis_edit_service.py:68,78,96`.

### [INFO] Cache de previews sans coalescence des requêtes — inchangé

- **Localisation** : `services/preview_service.py:61-68`, `infra/preview_cache.py`.

### [INFO] PDF.js : un document par visionneuse — inchangé

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts:23,43-46`.

### [INFO] Coûts quadratiques du rejeu, hors loop — inchangé

- **Localisation** : `document-parser/infra/docling_editor.py` (`_is_descendant`, `_in_document_order`).

### [INFO] Réactivité profonde sur les réponses de l'éditeur — inchangé

- **Localisation** : `frontend/src/features/analysis-editor/store.ts` (`ref` sur `saved` et `preview`). `shallowRef` suffirait.

### [INFO] Observations reportées de 0.7.0 — inchangées

- Connexion SQLite par appel, pas de WAL ; upload lu en mémoire, borné par `max_file_size` (`services/document_service.py:96`).

---

## Delta vs re-audit a6fb539

| Écart du re-audit (`a6fb539`) | Statut à `a12b744` | Preuve |
|---|---|---|
| [MIN] 12.2.5 logo 878 Ko en favicon | **Résolu** (item conforme) ; reliquat INFO | `frontend/public/logo.png` 256×256, 61 510 o |
| [MIN] 12.3.1 pas de cache nginx, gzip JSON seul | **Résolu** (item conforme) ; reliquat INFO `index.html` | `nginx.conf.template:5,26-34`, `frontend/nginx.conf.template:5,26-34`. JS + CSS de `dist/assets` : 2 915 624 o → 950 548 o en gzip niveau 4 (**mesuré**, Python `gzip`) ; worker PDF.js 1 228 596 → 401 350 o |
| [MIN] 12.3.2 réponses de l'éditeur, double chargement | **Inchangé** (non ciblé) | `api/schemas.py:199-207`, `features/document/store.ts:26-36` |
| [MIN] pdfium hors verrou partagé avec Docling | **Résolu** | `infra/pdf_inspector.py:30,46` sous `infra/pdfium_lock.py` (= verrou de Docling) ; `_count_pdf_pages` supprimé, remplacé par `services/analysis_service.py:441-454` en thread. Nouveau coût d'attente : INFO ci-dessus |
| [MIN] `followActive` sans borne | **Inchangé** | `features/analysis/store.ts:171-182` |
| [MIN] `show_sources` par citation | **Inchangé** | `services/source_service.py:102` |
| [INFO] Minuteur d'aperçu non annulé au démontage | **Résolu** | `AnalysisEditor.vue:513` → `store.ts:303-307` (timer + `abort`). L'annulation coupe la requête côté client ; une projection déjà lancée côté serveur va à son terme (thread non interruptible). |
| [INFO] `_count_pdf_pages` sur la loop (tableau du re-audit) | **Résolu** | `services/analysis_service.py:451` |
| Autres INFO | Inchangés | — |

Score : **86 → 95** (+1 point de poids : 12.2.5 +1, 12.3.1 +1 ; 18/21 → 20/21). MIN 6 → 3 ; CRIT 0, MAJ 0 inchangés. INFO 9 → 11 (2 résolus, 3 reliquats ou effets nouveaux, dont 1 sur le verrou pdfium).

---

## Effets de la remédiation sur la performance et la concurrence

**Nginx (`397ff32`).** Le bloc `/assets/` correspond exactement à ce que Vite émet :
`dist/index.html` ne référence que `/assets/index-*.js` et `/assets/index-*.css`, tous les
chunks et feuilles sont fingerprintés dans `dist/assets/` ; les seuls fichiers à la racine
sont `index.html`, `logo.png` et `favicon.svg`, non fingerprintés et donc à juste titre hors
du cache d'un an. `try_files $uri =404` évite qu'un asset manquant reçoive `index.html` en
200, qui aurait alors été mis en cache un an sous un nom d'asset. Les en-têtes de sécurité
sont bien répétés dans le bloc (sinon `add_header` les aurait masqués). Type MIME du `.js` :
le template est inclus dans le bloc `http` qui charge `mime.types` (Debian
`python:3.12-slim` pour l'image racine, `nginx:alpine` pour `frontend/Dockerfile:9`) ; selon
la version, `js` y est `application/javascript` ou `text/javascript` : **les deux** sont dans
`gzip_types`, donc le JS est compressé dans les deux images (**estimé** : non vérifié sans
lancer les conteneurs). Le PDF n'est pas dans `gzip_types` : les requêtes `Range` de PDF.js
restent servies telles quelles. Aucun effet négatif identifié ; coût CPU de gzip niveau 4
négligeable, et nul pour les visites suivantes grâce au cache.

**Verrou pdfium (`437058d`, `25f5d8b`).** Correction attendue (plus de pdfium concurrent de
Docling) au prix d'attentes bornées par un appel Docling (quelques ms à quelques centaines
de ms, voir l'INFO dédiée) ; pas d'interblocage. Seul vrai coût introduit : `page_sizes`
tient le verrou 106 ms à 300 pages (**mesuré**) et bloque d'autant les threads de
conversion ; réductible à 2,6 ms avec `get_page_size`. Le comptage pour le batching n'est
plus sur la loop. Sans inspecteur, `_count_pages` renvoie 0 et désactive le batching ; ce
chemin n'est pas atteignable en production : l'unique construction hors tests passe
toujours `pdf_inspector=_build_pdf_inspector()` (`bootstrap/factories.py:203-217`, seul
appelant `bootstrap/builder.py:122`). L'upload garde l'écriture et le comptage poppler dans un
seul `to_thread` (`services/document_service.py:108-114`), sans verrou pdfium.

**Services (`25f5d8b`).** `find_with_store_links` : mêmes requêtes qu'avant (document, liens,
un `find_all` des stores seulement s'il y a des liens). `list_history_entries`
(`services/analysis_edit_service.py:114-120`) : appelle `list_history` (document, base,
stream, commandes) puis `resolve_active_edit_commands` une fois, exactement ce que faisait
la route (`git diff a6fb539 a12b744 -- document-parser/api/analysis_edits.py`) ; pas de
projection ni de rejeu ajouté.

**Frontend (`450dad6`, `1eb3043`, `1516a0c`).** `parseAnalysisPages`
(`frontend/src/shared/analysisPages.ts:4-9`) remplace trois `JSON.parse` en ligne par la même
fonction, dans les trois mêmes computed (`features/analysis/store.ts:44`,
`features/document/store.ts:61`, `features/analysis-editor/store.ts:38`) plus
`pages/AnalysisDetailPage.vue:92` déjà présent : pas de parse supplémentaire. `BboxCanvas.vue`
appelait déjà `getComputedStyle(canvas)` une fois par `draw()` à `a6fb539` (même condition :
`nextRef` ou ordre de lecture affiché) ; la remédiation retire les couleurs de repli et passe
de 5 à 6 `getPropertyValue` (`BboxCanvas.vue:157-179`). `draw()` est regroupé par
`requestAnimationFrame` (`:53-58`), donc au plus une fois par frame. Coût : une
`CSSStyleDeclaration` et 6 lectures de propriétés personnalisées sur un style déjà calculé,
de l'ordre de la microseconde à quelques dizaines (**estimé**, non mesuré : pas de navigateur
lancé), négligeable devant le tracé des rectangles. Pas de mise en cache nécessaire ; un
cache par changement de thème ajouterait un état à invalider pour un gain non mesurable.

**Régressions de performance ou de concurrence introduites : aucune constatée.** Le seul
coût nouveau est l'attente bornée sur le verrou pdfium, contrepartie de la correction d'un
risque de plantage natif, et le maintien de 106 ms par `page_sizes` (INFO, correctif S).

**Non vérifiable sans lancer l'application** : type MIME effectif du `.js` et compression
réellement appliquée dans chaque image ; en-têtes servis pour `index.html` ; durée réelle des
appels verrouillés de Docling sur de vrais PDF (pages scannées, `generate_page_images`,
`images_scale` > 1) et donc l'attente réelle d'une requête de tailles de page pendant une
conversion ; comportement d'un thread Docling abandonné après timeout ; coût réel de
`getComputedStyle` dans le navigateur.

---

## Points positifs

- Le verrou pdfium est réellement **le même objet** que celui de Docling dans l'image locale, et un verrou propre en mode remote (`infra/pdfium_lock.py:12-15`) ; toutes les entrées pdfium de l'application passent par lui, aucune ne l'imbrique.
- Le comptage poppler de l'upload reste hors verrou, ce qui évite qu'un upload attende une conversion.
- Cache nginx limité aux fichiers fingerprintés, avec 404 strict sur les assets manquants et en-têtes de sécurité conservés ; gzip qui divise par trois le JS et le CSS servis (2,9 Mo → 0,95 Mo, **mesuré**).
- Le dernier appel pdfium synchrone sur l'event loop a disparu.
- Le refactor service/route n'a ajouté ni requête ni projection.

---

## Verdict partiel : GO

Score **95/100** (≥ 80), 0 CRIT, 0 MAJ, 3 MIN. Aucune régression de performance ou de
concurrence introduite par la remédiation. À traiter au prochain cycle : 12.3.2 (M), plafond
de `followActive` (S), `show_sources` (S), et `get_page_size` dans `page_sizes` (S).

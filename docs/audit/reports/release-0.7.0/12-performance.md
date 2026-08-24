# Rapport d'audit : Performance

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 76 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 4 |

Detail du calcul : poids total de la checklist = 21 (12.1 : 2+2+2+3+2 = 11 ;
12.2 : 2+2+1+1+1 = 7 ; 12.3 : 1+1+1 = 3). Items non conformes : 12.1.1 (poids 2),
12.2.5 (poids 1), 12.3.1 (poids 1), 12.3.2 (poids 1) => 5 points non conformes.
Poids conformes = 16. Score = 16 / 21 = 76,2 => **76 / 100**.

---

## Ecarts constates

### [MAJ] Requetes N+1 dans `StoreService` — une requete SQLite unitaire par iteration de boucle

- **Localisation** : `document-parser/services/store_service.py:163-164` (`list_stores`) et `document-parser/services/store_service.py:359-360` (`list_documents`)
- **Constat** : deux cas d'usage bouclent en emettant une requete DB unitaire par
  element, chacune ouvrant une nouvelle connexion aiosqlite :
  - `list_stores` (l.160-177) : apres `self._stores.find_all()`, la boucle
    `for store in stores` appelle `await self._links.find_for_store(store.id)`
    (l.164) **uniquement pour en faire `len(links)`** (l.172). C'est N+1 requetes
    la ou un unique `SELECT store_id, COUNT(*) ... GROUP BY store_id` suffirait,
    et le `find_for_store` remonte toutes les colonnes des liens alors que seul le
    compte est utilise.
  - `list_documents` (l.344-370) : la boucle `for link in links` appelle
    `await self._documents.find_by_id(link.document_id)` (l.360) pour resoudre le
    seul `doc.filename`. C'est N+1 requetes la ou un `WHERE id IN (...)` unique
    resoudrait tous les noms en un aller-retour.
- **Facteur aggravant** : chaque appel de repository ouvre puis referme une
  connexion SQLite neuve (`persistence/database.py:273-280`, `get_connection`),
  avec `PRAGMA foreign_keys = ON` a chaque fois. Dans ces boucles, le cout
  d'ouverture/fermeture de connexion se paie donc a chaque iteration en plus de
  la requete elle-meme.
- **Regle violee** : 12.1.1 — "Pas de requete N+1 — les acces DB sont optimises
  (pas de boucle avec requete unitaire)" (poids 2).
- **Remediation** : remplacer les deux boucles par une requete ensembliste. Pour
  `list_stores`, un `COUNT(*) ... GROUP BY store_id` renvoye en un seul appel
  repository. Pour `list_documents`, un `find_by_ids(ids)` (`WHERE id IN (...)`)
  puis un mapping `id -> filename` en memoire. Le pattern correct existe deja
  ailleurs dans le code (`ChunkService.list_pushes`, `services/chunk_service.py:715-727`,
  utilise un cache `store_cache` pour ne resoudre chaque store qu'une fois) — il
  suffit de l'appliquer ici.

---

### [MIN] Logo PNG 1024x1024 (~858 Ko) non optimise, servi en topbar et en favicon

- **Localisation** : `frontend/public/logo.png` (1024x1024, 8-bit RGB, 858 643 octets), reference dans `frontend/src/app/App.vue:19`, `frontend/src/pages/StudioPage.vue:5`, `frontend/src/pages/HomePage.vue:5` et `frontend/index.html:7`
- **Constat** : le meme PNG 1024x1024 de ~858 Ko est charge comme icone de barre
  de titre (affichee a une taille d'icone), comme visuel d'import, comme hero, et
  comme favicon (`<link rel="icon" type="image/png" href="/logo.png">`). Un
  favicon de 858 Ko / 1024 px est tres largement surdimensionne ; un `favicon.svg`
  (270 octets) existe deja dans `frontend/public/` mais n'est pas utilise comme
  icone. Couple a l'absence de cache statique (cf. 12.3.1), l'asset est
  re-telecharge a chaque visite.
- **Regle violee** : 12.2.5 — "Les assets lourds (images, fonts) sont optimises"
  (poids 1).
- **Remediation** : servir une version compressee/redimensionnee (ou un SVG) pour
  la topbar/hero, pointer `rel="icon"` sur `favicon.svg`, et compresser le PNG
  source (pngquant/oxipng) — un logo 1024 px peut descendre sous ~60-100 Ko sans
  perte visible.

---

### [MIN] Nginx ne configure aucun cache pour les fichiers statiques

- **Localisation** : `frontend/nginx.conf.template` (fichier entier, l.1-26) et `nginx.conf.template` (racine, l.1-26)
- **Constat** : les deux templates nginx servent le SPA (`location /`) sans aucune
  directive `expires` / `Cache-Control` ni bloc `location ~* \.(js|css|png|woff2|...)$`.
  Vite emet pourtant des noms de fichiers content-hashes (immutables), cas ideal
  pour un `Cache-Control: public, max-age=31536000, immutable`. En l'etat chaque
  asset (dont `logo.png` ci-dessus) est revalide/retelecharge a chaque navigation.
- **Regle violee** : 12.3.1 — "Nginx a une configuration de cache pour les fichiers
  statiques" (poids 1).
- **Remediation** : ajouter un `location ~* \.(js|css|woff2?|png|svg|jpg)$ { expires 1y;
  add_header Cache-Control "public, immutable"; }` (assets hashes) et `Cache-Control:
  no-cache` cible sur `index.html`, dans les deux templates.

---

### [MIN] La liste des analyses renvoie les colonnes lourdes (markdown, HTML, pages, chunks) pour chaque job

- **Localisation** : `document-parser/api/analyses.py:71-81` (`list_analyses` -> `_to_response`), `document-parser/api/analyses.py:23-40` (`_to_response`), `document-parser/persistence/analysis_repo.py:59-67` (`find_all`, `SELECT aj.*`)
- **Constat** : `GET /api/analyses` mappe chaque job via `_to_response`, qui
  serialise `content_markdown`, `content_html`, `pages_json` et `chunks_json`
  (l.29-32) pour **chaque** job renvoye (jusqu'a `limit=200`, `find_all`). Cote DB,
  `find_all` fait `SELECT aj.*` (`analysis_repo.py:40`, `_SELECT_WITH_DOC`), ce qui
  charge aussi `document_json` (la colonne la plus volumineuse) en memoire avant
  de la jeter au moment de la reponse — le schema documente d'ailleurs ces quatre
  colonnes comme "heavy" et leur eclatement dans une table `analysis_artifacts`
  comme un follow-up (`persistence/database.py:63-66`). Une vue "liste" charge
  donc potentiellement plusieurs Mo de HTML/markdown complets. Bon point associe :
  `document_json` n'est deliberement PAS renvoye au client (`has_document_json:
  bool` a la place, l.33) — l'optimisation est amorcee mais partielle.
- **Regle violee** : 12.3.2 — "Les reponses API sont de taille raisonnable (pas
  d'envoi de donnees inutiles)" (poids 1).
- **Remediation** : introduire une projection "resume" pour la liste (id, statut,
  filename, timestamps, progression, drapeaux `has_*`) et ne renvoyer le contenu
  complet que sur `GET /api/analyses/{id}`. Cote repo, un `SELECT` de colonnes
  explicites (sans `document_json` ni contenus) pour le chemin liste.

---

### [INFO] Upload et preview chargent le fichier entier en memoire

- **Localisation** : `document-parser/api/documents.py:82-90` (upload — `content = b"".join(chunks)`), `document-parser/services/document_service.py:64-106` + `:154-165`, `document-parser/api/documents.py:181` (preview — `read_bytes`)
- **Constat** : l'upload lit le corps par tranches de 64 Ko puis les concatene en
  un unique `bytes` (l.90), et l'ecriture disque se fait bien par tranches
  (`_persist_and_count`, l.162-164) — mais le fichier complet reside malgre tout en
  memoire, tout comme le comptage de pages (`pdfinfo_from_bytes`), la preview
  (`convert_from_bytes`) et le `ServeConverter` (`infra/serve_converter.py:113`,
  `path.read_bytes`). Ces bibliotheques (poppler / Docling Serve) exigent les octets
  complets : le chargement est donc "avec necessite", et il est borne par
  `MAX_FILE_SIZE_MB` (`document_service.py:72-73`, rejet 413 en amont
  `api/documents.py:79`). Item 12.1.5 considere conforme, note pour tracabilite.
- **Regle concernee** : 12.1.5 (poids 2, conforme). Suggestion : si le batching
  page-par-page devient le mode nominal, envisager un passage par un chemin disque
  temporaire pour la conversion afin de ne jamais materialiser tout le PDF en RAM.

---

### [INFO] Aucun mode WAL sur SQLite ; une connexion neuve par appel repository

- **Localisation** : `document-parser/persistence/database.py:265-280` (`get_db` / `get_connection`)
- **Constat** : chaque methode de repository ouvre une connexion aiosqlite via
  `get_connection()` et la referme immediatement — pas de pool. De plus, aucun
  `PRAGMA journal_mode=WAL` n'est active : en journal rollback par defaut, les
  ecritures (progression d'analyse, upserts de liens) serialisent davantage avec
  les lectures concurrentes de l'UI. Les index en revanche sont bien couverts
  (`idx_dsl_store`, `idx_analysis_jobs_doc_status`, index composites sur
  `chunk_pushes`, etc.), donc les requetes unitaires restent indexees.
- **Regle concernee** : 12.1.1 / concurrence (informatif). Suggestion : activer
  WAL au boot (`init_db`) et evaluer une connexion long-vivante partagee (aiosqlite
  serialise deja les acces) pour reduire l'overhead d'ouverture, notamment dans les
  boucles signalees en [MAJ].

---

### [INFO] Pas d'annulation (AbortController) des requetes API superseder

- **Localisation** : `frontend/src/` (aucune occurrence de `AbortController` / `AbortSignal`), debounce present dans `frontend/src/pages/DocsLibraryPage.vue:158-163` (recherche) et `frontend/src/features/chunks/ui/ChunksEditor.vue:239-249` (auto-save)
- **Constat** : item 12.2.3 exige "annulation OU debounce quand pertinent". Le
  debounce est present la ou il compte (recherche a la frappe, sauvegarde de
  chunk). Il n'y a en revanche aucun `AbortController` pour annuler une requete
  devenue obsolete (ex. changement rapide de document pendant un chargement, ou
  soumission repetee du panneau Ask reasoning). Item considere conforme (le
  debounce couvre les cas pertinents) ; note pour amelioration future.
- **Regle concernee** : 12.2.3 (poids 1, conforme).

---

### [INFO] Debounce de sauvegarde de chunk sans nettoyage a l'unmount

- **Localisation** : `frontend/src/features/chunks/ui/ChunksEditor.vue:239-249`
- **Constat** : `saveTimer` (setTimeout 600 ms) est bien `clearTimeout`e avant
  chaque re-armement (l.242), mais aucun `onUnmounted`/`onBeforeUnmount` ne
  l'annule : si le composant est demonte dans la fenetre de 600 ms suivant une
  frappe, le `setTimeout` se declenche encore et emet un `updateText` apres
  demontage. Ce n'est pas une fuite memoire (le timer se declenche une seule fois,
  le store survit), d'ou le classement INFO — mais un `onBeforeUnmount(() =>
  clearTimeout(saveTimer))` fermerait proprement le cas.
- **Regle concernee** : 12.2.1 / 12.2.2 (conformes par ailleurs).

---

## Points positifs

- **Operations longues non bloquantes (12.1.4, poids 3 — conforme)** : toute la
  charge CPU/IO lourde traverse `asyncio.to_thread` — conversion Docling
  (`infra/local_converter.py:295`), chunking (`infra/local_chunker.py:106`),
  lecture PDF distante (`infra/serve_converter.py:113`), run reasoning
  `run_with_trace` (`infra/docling_agent_reasoning.py:194`), ecriture d'upload et
  comptage de pages (`services/document_service.py:84`), rasterisation de preview
  (`api/documents.py:181-183`). Le convertisseur local protege l'unique
  `DoclingConverter` (non thread-safe) par un lock avec timeout
  (`local_converter.py:53, 228-233`).
- **Semaphore de concurrence (12.1.3, conforme)** : `MAX_CONCURRENT_ANALYSES`
  (`infra/settings.py:22, 159`, defaut 3, valide `>= 1`) est injecte et respecte
  par un `asyncio.Semaphore` qui encadre effectivement `_run_analysis`
  (`services/analysis_service.py:98, 388`).
- **Rebuild a chaud du runner reasoning (#317) sobre** : la reconstruction du
  runner passe par un unique `dataclasses.replace` + rebind atomique du container
  (`bootstrap/builder.py:78-82, 179-188`), declenchee **uniquement** sur ecriture
  de config (`services/app_config_service.py:117-137, 175-185`) ou au boot
  (`apply_effective`), jamais par requete. Le container est immuable
  (`api/state.py`), pas de reconstruction couteuse dans le chemin chaud. Le health
  check ne bloque jamais sur l'hote Ollama (`main.py:134-137`).
- **Nettoyage frontend systematique (12.2.1 / 12.2.2, conformes)** : les trois
  `addEventListener` ont leur `removeEventListener` symetrique en
  `onUnmounted`/`onBeforeUnmount` (`DownloadDropdown.vue:195-201`,
  `TableModal.vue:46-47`, `StudioPage.vue:554-555 / 569-570 / 680-683`). Tous les
  observers (`ResizeObserver`, `IntersectionObserver`) appellent `disconnect()`
  (`BboxOverlay.vue:207`, `BboxCanvas.vue:197-198`, `PagePreviewWithOverlay.vue:431-432`),
  le `requestAnimationFrame` est annule (`BboxCanvas.vue:197`). Les timers de
  polling (analyses, ingestion) s'auto-terminent (statut terminal / retries max /
  timeout) et sont stoppes au demontage (`analysis/store.ts:108-117` + `StudioPage.vue:681` ;
  `ingestion/store.ts:34-39` + `AppSidebar.vue:172-177`).
- **Rendu tables / timeline efficace (12.2.4, conforme)** : `MarkdownViewer`
  memoise le parse+sanitize dans un `computed` (`MarkdownViewer.vue:15-25`), et
  `TraceTimeline` derive `steps` / `timed` / `bars` / `ticks` en `computed` avec
  la logique pure extraite et testee (`timeline.logic.ts`), `v-for` avec `:key`
  stable (`TraceTimeline.vue:46-53, 91-94`).
- **Health check leger (12.3.3, conforme)** : `SELECT 1` de connectivite + lecture
  de settings, aucune charge (`main.py:106-115`).
- **Nettoyage des temporaires (12.1.2, conforme)** : les uploads vont directement
  au stockage permanent, les uploads hors-limite sont `os.unlink`es
  (`document_service.py:88-96`), la suppression de document nettoie le fichier
  disque avec garde anti-traversee (`document_service.py:116-140`) ; l'export PDF
  reutilise le fichier stocke sans creer de temporaire (`services/export_service.py:49`).
- **Index SQLite bien couverts** : chaque acces des boucles N+1 signalees frappe
  malgre tout un index (`idx_dsl_store`, `documents(id)` PK) — le probleme est le
  nombre d'aller-retours, pas des scans de table.

---

## Verdict partiel : GO CONDITIONNEL

Score 76/100 (bande 60-79), **0 ecart CRITICAL**, 1 ecart MAJOR (<= 3, non
bloquant au sens du master). Conditions de levee recommandees avant merge :

1. Corriger les N+1 de `StoreService.list_stores` / `list_documents` [MAJ] par
   une requete ensembliste (COUNT groupe + `WHERE id IN (...)`).
2. Introduire une projection "resume" pour `GET /api/analyses` afin de ne pas
   renvoyer HTML/markdown/pages/chunks complets en vue liste [MIN 12.3.2].
3. Ajouter le cache statique nginx et optimiser `logo.png`/favicon [MIN 12.3.1 +
   12.2.5] — corrections a faible risque, gros gain per-visite.

# Rapport d'audit : Performance & Ressources

> **Re-audit de release/0.7.3 @ e01fd95 — score 52 → 67**

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Type** : re-audit apres remediation (audit initial = 52/100, `release/0.7.3 @ 02adc68`)

Perimetre : delta `02adc68..e01fd95` (PR #367, 11 commits). Un seul commit touche la
performance : `d1a131f perf(analysis): run the Docling import off the event loop (#audit-12)`
(`services/analysis_service.py` +3/-1, un test). Le reste est sans effet sur cet audit :
montees de version de dependances (`7246efe` : uv, PyJWT, certifi, mcp, aiohttp, multidict,
urllib3, opentelemetry-api), doc/changelog, `ConfigSource` deplace dans `shared/types.ts`
(type seul), `lang="fr"` de `citation_app.html`. Aucun autre fichier audite en 0.7.3 n'a change
(`git diff --stat 02adc68..e01fd95` sur `api/`, `services/`, `persistence/`, `domain/`,
`infra/page_raster.py`, `bootstrap/`, `frontend/src/`, `frontend/public/`, templates nginx :
seuls les fichiers ci-dessus apparaissent). L'analyse initiale est donc **reprise telle quelle
pour les fichiers inchanges** ; toutes les citations ci-dessous ont ete reverifiees a `e01fd95`
(decalage de +3 lignes apres la l.177 de `analysis_service.py`, de +2 dans `Dockerfile`).

Methode : lecture du code ; `tests/test_analysis_service.py` execute (37 passed, dont le
nouveau test) ; mesures indicatives par scripts hors depot (application non lancee). Les
ordres de grandeur non mesures restent marques PLAUSIBLE.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 8 / 13 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 6 |
| Ecarts INFO | 7 |

### Detail par item

| # | Item | Poids | Initial (02adc68) | Re-audit (e01fd95) |
|---|------|-------|-------------------|--------------------|
| 12.1.1 | Pas de requete N+1 | 2 | Non | Non |
| 12.1.2 | Fichiers uploades temporaires supprimes | 2 | Oui | Oui |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` configuree et respectee | 2 | Oui | Oui |
| 12.1.4 | Operations longues hors event loop | 3 | Non | **Oui** |
| 12.1.5 | Pas de fichier entier en memoire sans necessite | 2 | Non | Non |
| 12.2.1 | Watchers Vue avec cleanup | 2 | Oui | Oui |
| 12.2.2 | Event listeners supprimes dans `onUnmounted` | 2 | Oui | Oui |
| 12.2.3 | Annulation ou debounce des requetes | 1 | Oui | Oui |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | Oui |
| 12.2.5 | Assets lourds optimises | 1 | Non | Non |
| 12.3.1 | Cache nginx pour les fichiers statiques | 1 | Non | Non |
| 12.3.2 | Reponses API de taille raisonnable | 1 | Non | Non |
| 12.3.3 | Health check leger | 1 | Oui | Oui |

Poids total = 21 (12.1 : 2+2+2+3+2 = 11 ; 12.2 : 2+2+1+1+1 = 7 ; 12.3 : 1+1+1 = 3).
Non conformes : 12.1.1 (2) + 12.1.5 (2) + 12.2.5 (1) + 12.3.1 (1) + 12.3.2 (1) = 7.
Poids conformes = 14. `score = 14 / 21 * 100 = 66,7` => **67 / 100**.

Delta vs audit initial : +3 (12.1.4, poids 3, l'ecart MAJOR "import sur l'event loop" est
leve). 11 -> 14 points conformes, 7/13 -> 8/13 items : **52 -> 67**.

---

## Verification de la remediation

| # | Statut | Preuves a e01fd95 |
|---|--------|-------------------|
| 12.1.1 | **Toujours non conforme** (non traite) | Boucles inchangees : `services/chunk_service.py:474-486`, `:503-514`, `:229-241`, `:836-842` ; `services/version_service.py:161-173`, `:180-192` ; une connexion par appel `persistence/database.py:265-280` ; `show_sources` `services/source_service.py:102` -> `citation_service.py:99` -> `parse_loader.py:78`, `:83` |
| 12.1.2 | Conforme (inchange) | `services/document_service.py:96` (`os.unlink` sous `asyncio.to_thread`) |
| 12.1.3 | Conforme (inchange) | `infra/settings.py:24`, `:212` ; `services/analysis_service.py:100` (`asyncio.Semaphore`), `:424` (`async with self._semaphore`) |
| 12.1.4 | **Conforme — corrige** | `services/analysis_service.py:177-180` (`await asyncio.to_thread(self._docling_importer.deserialize, document)`) ; test `tests/test_analysis_service.py:224-246` ; detail et reliquat ci-dessous |
| 12.1.5 | **Toujours non conforme** (non traite) | `infra/page_raster.py:27-28` ; `api/documents.py:185-190` + `services/document_service.py:162` ; `api/documents.py:213-216` + `services/document_service.py:176` ; re-rendu par palier `services/citation_image_service.py:89-91`, `:126-130` |
| 12.2.1 | Conforme (inchange) | aucun fichier `.vue`/`.ts` a logique modifie ; `AnalysisLibraryPage.vue:169`, `PagePreviewWithOverlay.vue:522-525` |
| 12.2.2 | Conforme (inchange) | idem ; `DocumentActionsMenu.vue:91-92`, `AnalysisProgressBar.vue:36-40` |
| 12.2.3 | Conforme (inchange) | debounces et gardes de requete perimee, `DocWorkspacePage.vue:144-174` |
| 12.2.4 | Conforme (inchange) | cf. rapport initial ; INFO polling maintenu |
| 12.2.5 | Non conforme (inchange) | `frontend/public/logo.png` = 878 643 octets ; `frontend/index.html:7` |
| 12.3.1 | Non conforme (inchange) | `nginx.conf.template:13-15`, `frontend/nginx.conf.template:13-15` |
| 12.3.2 | Non conforme (inchange) | `frontend/src/features/analysis/store.ts:54` (`api.fetchAnalyses()`) ; `frontend/src/pages/DocsLibraryPage.vue:345` |
| 12.3.3 | Conforme (inchange) | `document-parser/main.py:134` (`SELECT 1`) |

### [RESOLU] 12.1.4 — Import d'analyse Docling execute sur l'event loop (#359)

- **Etait** : `[MAJ]` (poids 3, contextualise CRIT -> MAJ) —
  `self._docling_importer.deserialize(document)` appele en synchrone dans la coroutine
  `import_docling_document` (`analysis_service.py:177` a `02adc68`) : validation et trois
  exports sur la loop, toutes les requetes figees pendant l'import.
- **Correctif** : `services/analysis_service.py:180` —
  `result = await asyncio.to_thread(self._docling_importer.deserialize, document)`, commente
  l.177-179. Part desormais dans un thread de travail tout ce que fait
  `infra/docling_importer.py:18-26` : `DoclingDocument.model_validate` (l.18),
  `extract_pages_detail` (l.19), `export_to_markdown()` (l.22), `export_to_html()` (l.23),
  `export_to_dict()` + `json.dumps` (l.26). Meme schema que les convertisseurs
  (`infra/local_converter.py:201`, `:204`) et le chunker (`infra/local_chunker.py:106`).
- **Test** : `tests/test_analysis_service.py:224-246`
  (`test_import_deserializes_off_the_event_loop`) verifie que l'importeur ne voit pas de loop
  en cours (`asyncio.get_running_loop()` leve), donc qu'il tourne bien dans un thread. Execute :
  `tests/test_analysis_service.py` 37 passed. Le test s'arrete a `deserialize` (il leve
  avant la persistance) : il ne couvre pas `_finalize_analysis`, ce qui est coherent avec le
  perimetre du correctif.
- **Ce qui reste sur la loop pour un import** (verifie ligne a ligne) :

| Etape | Localisation | Nature | Cout |
|-------|--------------|--------|------|
| Lecture du corps JSON | `api/analyses.py:73-76` (`ImportAnalysisRequest`, `api/schemas.py:272-276`, `document: dict`) ; FastAPI `await request.json()` -> Starlette `json.loads(body)` | framework, C, lineaire | mesure : 5 ms pour 0,9 Mo |
| `pages_json` | `services/analysis_service.py:467` (`json.dumps([asdict(p) for p in result.pages])`) | `asdict` recursif en Python pur, lineaire en elements de page | mesure : 1 ms (21 p., 192 elements) ; 52 ms en synthetique pour 500 p. x 40 elements (7 Mo) |
| Version | `analysis_service.py:496-498` -> `services/version_service.py:114-124` (`_serialize_chunks`, l.45) | relit et serialise le chunkset **vivant** | borne par le nombre de chunks existants, pas par la taille du document importe |
| Persistance | `analysis_service.py:184-187`, `:508`, `:511` | aiosqlite : le SQL s'execute dans le thread de la connexion (`persistence/database.py:265-270`) | hors loop |
| Graphe | `analysis_service.py:531` -> `:535-553` -> `infra/neo4j/graph_adapter.py:49-61` -> `infra/neo4j/tree_writer.py:84-122` (`json.loads` complet, `build_collapse_index`, `iter_items`, `dfs_order`) | Python pur sur la loop, lineaire | mesure : 7 ms (221 elements). **Uniquement si Neo4j est branche** : `bootstrap/builder.py:177-179` renvoie `(None, None)` sans driver, `infra/settings.py:33` (`neo4j_uri = ""`, desactive), `docker-compose.yml:176` (`NEO4J_URI: ${NEO4J_URI:-}`) |
| Reponse | `api/analyses.py:87` -> `_to_response` l.25-42 (markdown, HTML, `pages_json`) | serialisation pydantic-core de chaines, lineaire | non mesure, faible |

  Mesure indicative sur un DoclingDocument reel de 21 pages (0,9 Mo, hors depot) :
  `deserialize` = **167 ms dans le thread**, contre ~6 ms restant sur la loop (~13 ms avec le
  graphe Neo4j), soit plus de 90 % du CPU de l'import sorti de la loop. Le thread partage le
  GIL avec la loop : elle reste servie (bascule toutes les 5 ms par defaut), avec une latence
  degradee mais plus de gel — meme compromis que pour la conversion Docling.
- **Verdict item** : **conforme**. Le travail lourd et proportionnel au document (validation
  pydantic de tout l'arbre + trois exports) est hors loop ; le reliquat est lineaire, d'un
  ordre de grandeur plus faible, et en partie optionnel (Neo4j). Seconde moitie de la
  remediation proposee non appliquee : `pages_json` (l.467) reste sur la loop, comme pour les
  analyses normales — c'etait deja un INFO a l'audit initial et il le reste (voir
  "[INFO] Reliquat CPU sur l'event loop").

---

## Ecarts constates (restants)

### [MAJ] Fichier PDF entier relu en memoire (et recopie sur disque) pour chaque page rendue — inchange

- **Localisation** :
  - `document-parser/infra/page_raster.py:26-28` (rasters MCP) : `Path(storage_path).read_bytes()`
    puis `convert_from_bytes(...)`.
  - `document-parser/api/documents.py:185-190` + `services/document_service.py:160-162`
    (`/preview`, viewer du doc workspace).
  - `document-parser/api/documents.py:213-216` + `services/document_service.py:171-176`
    (`/pages`) : `read_bytes` puis `pdfium.PdfDocument(file_content)`.
- **Constat** : aucun de ces fichiers n'a change depuis `02adc68`. Pour une page, tout le PDF
  (jusqu'a `MAX_FILE_SIZE_MB` = 50 Mo, `infra/settings.py:28`) est lu en RAM puis reecrit dans
  un fichier temporaire par `pdf2image.convert_from_bytes` avant l'appel a poppler ;
  `CitationImageService._shrink_to_budget` re-rend depuis zero a chaque palier de dpi
  (`services/citation_image_service.py:89-91`, `:126-130`). Le chemin de fichier suffit, et le
  code le fait deja ailleurs (`infra/page_text.py:32`, `services/analysis_service.py:62`).
- **Regle violee** : 12.1.5 (poids 2).
- **Remediation** : `convert_from_path(storage_path, first_page=page, last_page=page, dpi=dpi)`
  dans `page_raster.py` et `generate_preview` ; `pdfium.PdfDocument(path)` dans `page_sizes`
  (sous le verrou pdfium).

### [MAJ] Boucles d'ecriture une-requete-par-chunk — inchange (carry-over 0.6.2)

- **Localisation** : `document-parser/services/chunk_service.py:474-486` et `:503-514`
  (`rechunk_document`), `:229-241` (`promote_from_analysis_if_empty`), `:836-842`
  (`_shift_sequences`) ; `document-parser/services/version_service.py:161-173` et `:180-192`
  (`restore`).
- **Constat** : inchange. Chaque `soft_delete` / `_edits.insert` / `update` ouvre sa propre
  connexion aiosqlite et son propre `commit` (`persistence/database.py:265-280`,
  `persistence/chunk_repo.py:104-111`, `persistence/chunk_edit_repo.py:58-79`) : ~3N
  connexions et transactions pour un rechunk ou une restauration de N chunks.
- **Regle violee** : 12.1.1 (poids 2).
- **Remediation** : `soft_delete_many` / `insert_many` en `executemany` dans une transaction
  (le pattern existe : `chunk_repo.insert_many`) ; `_shift_sequences` en un seul
  `UPDATE ... SET sequence = sequence + 1 WHERE document_id = ? AND sequence >= ?`.

### [MIN] `show_sources` recharge la meme parse pour chaque citation — inchange

- **Localisation** : `services/source_service.py:102` -> `services/citation_service.py:99` ->
  `services/parse_loader.py:78`, `:83` ; puis `source_service.py:107` et
  `navigation_service.py:110`.
- **Constat / regle** : 2N + 4 connexions par appel pour relire les memes lignes ; N plafonne
  a 50 (`services/navigation_config.py:60`). 12.1.1 (deja non conforme), contextualise MIN.
- **Remediation** : resoudre l'epinglage et charger la parse une fois, verifier les citations
  contre cette `LoadedParse`.

### [MIN] La bibliotheque d'analyses charge toujours la liste complete — inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:54` (`api.fetchAnalyses()`),
  appele par `frontend/src/pages/AnalysisLibraryPage.vue:135-138` (montage l.168) ;
  `document-parser/api/analyses.py:90-100` + `_to_response` l.25-42 ;
  `frontend/src/pages/DocsLibraryPage.vue:345`.
- **Regle violee** : 12.3.2 (poids 1).
- **Remediation** : `load()` sur `fetchAnalysisSummaries()` ; un compte plutot que la liste
  complete avant suppression.

### [MIN] Logo PNG 1024x1024 (~858 Kio) non optimise, servi en topbar et en favicon — inchange

- **Localisation** : `frontend/public/logo.png` (878 643 octets), `frontend/index.html:7`.
- **Regle violee** : 12.2.5 (poids 1).
- **Remediation** : `rel="icon"` sur `favicon.svg`, logo compresse (< ~100 Kio).

### [MIN] Nginx ne configure aucun cache pour les fichiers statiques — inchange

- **Localisation** : `nginx.conf.template:13-15`, `frontend/nginx.conf.template:13-15`.
- **Regle violee** : 12.3.1 (poids 1).
- **Remediation** : `expires 1y` + `Cache-Control "public, immutable"` sur les assets
  content-hashes, `no-cache` sur `index.html`, dans les deux templates.

### [MIN] pdfium appele hors du verrou partage avec Docling (hors checklist, PLAUSIBLE) — inchange

- **Localisation** : `services/document_service.py:176` (`page_sizes`) ;
  `services/analysis_service.py:59-68` (`_count_pdf_pages`, appele sur l'event loop l.449).
- **Constat** : le verrou process-wide de `infra/page_text.py:7-9, 21-31` n'est pas pris ici.
  Risque PLAUSIBLE de crash natif en moteur local. N'affecte pas le score.
- **Remediation** : meme `_pdfium_lock` (a factoriser dans `infra/`) ; `_count_pdf_pages`
  sous `asyncio.to_thread`.

### [MIN] Le suivi a 3 s n'a pas de borne de duree (hors checklist) — inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:170-181` (`followActive`) vs
  `MAX_POLLING_DURATION` l.31 ; pas de reconciliation au boot des lignes `PENDING`/`RUNNING`.
- **Remediation** : marquer `FAILED` les analyses orphelines au demarrage ; plafond de duree
  sur `followActive`. N'affecte pas le score.

### [INFO] Reliquat CPU sur l'event loop (mis a jour apres le correctif 12.1.4)

- **Localisation** : `services/analysis_service.py:467` (`pages_json`, toutes les analyses et
  l'import) ; `infra/neo4j/tree_writer.py:84-122` (pretraitement de l'arbre, seulement si
  Neo4j est branche) ; `infra/serve_converter.py:137-139` et `:236-258` (moteur distant :
  `response.json()`, `_parse_response`, `json.dumps`) ; `domain/outline_builder.py:51` et
  `:125-133` (`get_outline` en mode pages, O(pages x elements)).
- **Constat** : travaux lineaires en taille de document restes sur la loop. Mesures sur
  l'import : quelques ms pour 21 pages, ~50 ms PLAUSIBLE pour 500 pages (`pages_json`
  synthetique). D'un ordre de grandeur sous ce que l'import faisait avant le correctif ;
  12.1.4 reste conforme.
- **Suggestion** : `asyncio.to_thread` pour `pages_json`, `_parse_response` et le
  pretraitement de `tree_writer.write_document` (la construction des listes avant la
  transaction) ; memoiser dans l'index les couts par element et l'appartenance aux pages.

### [INFO] Imports desormais paralleles, hors du semaphore d'analyse (nouveau, effet du correctif)

- **Localisation** : `services/analysis_service.py:165-192` (`import_docling_document`) ; le
  semaphore n'entoure que `_run_analysis` (l.424).
- **Constat** : avant le correctif, la loop bloquee serialisait de fait les imports. Ils
  tournent maintenant en parallele dans l'executeur par defaut, chacun avec son jeu de
  travail (dict du corps + `DoclingDocument` + markdown + HTML + JSON), pour un corps
  accepte jusqu'a 200 Mo (`Dockerfile:61`, `docker-compose.yml:208`). Le GIL limite le gain
  CPU ; le pic memoire, lui, s'additionne. Action manuelle, bornee par le rate limit par IP
  (`infra/settings.py:29`) : INFO. 12.1.3 reste conforme (le semaphore vise les conversions).
- **Suggestion** : passer `deserialize` sous `self._semaphore` (ou un semaphore d'import a 1).

### [INFO] Polling des resumes : continue onglet masque, sans garde de requete en vol, re-rend toute la table — inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:172-180` ;
  `frontend/src/features/analysis/batch.ts:28-32` ;
  `frontend/src/pages/AnalysisLibraryPage.vue:52, 158-162`.

### [INFO] `/summaries` : les colonnes legeres sont stockees apres les colonnes lourdes (PLAUSIBLE) — inchange

- **Localisation** : `persistence/analysis_repo.py:47-52` vs `persistence/database.py:67-81`.
- **Suggestion** : index couvrant, a valider par `EXPLAIN QUERY PLAN`.

### [INFO] Budgets memoire/CPU du serveur MCP : bornes, mais larges — inchange

- **Localisation** : `services/navigation_config.py:36-54` ; `services/parse_loader.py:99-111` ;
  `infra/page_raster.py:31-33, 61` ; `services/citation_image_service.py:72-79`.

### [INFO] Fusion des lots (#344) : pic memoire en fin d'analyse longue — inchange

- **Localisation** : `services/analysis_service.py:307-343` (`results.append`, l.332) ;
  `infra/local_converter.py:157-180` (l.173).

### [INFO] Observations reportees de 0.7.0, toujours presentes — inchange

- Connexion neuve par appel, pas de WAL (`persistence/database.py:265-280`) ; pas
  d'`AbortController` (12.2.3 conforme) ; timers non annules
  (`features/chunks/ui/ChunksEditor.vue:239-249`, `pages/DocsLibraryPage.vue:239-245`) ;
  upload en memoire borne (`api/documents.py:84-90`).

---

## Delta vs audit initial

| Ecart initial (02adc68) | Statut a e01fd95 |
|---|---|
| [MAJ] Import Docling sur l'event loop (12.1.4) | **Corrige** : `analysis_service.py:180` + test `tests/test_analysis_service.py:224-246` ; reliquat `pages_json` en INFO |
| [MAJ] PDF entier relu par page rendue (12.1.5) | **Toujours ouvert**, fichiers inchanges |
| [MAJ] Boucles une-requete-par-chunk (12.1.1) | **Toujours ouvert**, fichiers inchanges |
| [MIN] N+1 `show_sources` | Toujours present |
| [MIN] Bibliotheque sur la liste complete (12.3.2) | Toujours present |
| [MIN] Logo / favicon (12.2.5) | Toujours present |
| [MIN] Pas de cache nginx (12.3.1) | Toujours present |
| [MIN] pdfium hors verrou | Toujours present (`_count_pdf_pages` l.449) |
| [MIN] Suivi a 3 s sans borne | Toujours present |
| [INFO] CPU pre-existant sur la loop | Mis a jour : reliquat de l'import ajoute, mesure |
| [INFO] Polling, `/summaries`, budgets MCP, fusion des lots, reports 0.7.0 | Inchanges |
| — | **Nouveau [INFO]** : imports paralleles hors semaphore (effet de bord du correctif) |

---

## Points positifs

- **Correctif minimal et bien cible** : une ligne, au bon endroit, alignee sur les
  convertisseurs et le chunker ; le commentaire (`analysis_service.py:177-179`) dit pourquoi.
- **Test de non-regression qui teste la propriete, pas l'implementation** : il verifie
  l'absence de loop en cours dans l'importeur plutot que l'appel a `asyncio.to_thread`
  (`tests/test_analysis_service.py:225-246`).
- **Persistance de l'import inchangee** : meme chemin `_finalize_analysis` que les analyses
  normales (version, statut, cycle de vie, graphe), donc pas de divergence introduite.
- Points positifs du rapport initial toujours valables (fichiers inchanges) : polling batch
  par `/summaries`, MCP sans etat, parse cachee avec `json.loads`/index hors loop
  (`parse_loader.py:105-108`), rasters hors loop, semaphore (`analysis_service.py:100, 424`)
  et health check (`main.py:129-137`) corrects.

---

## Verdict partiel : GO CONDITIONNEL

Score **67/100** (bande 60-79), **0 ecart CRITICAL**, **2 ecarts MAJOR** (<= 3, non bloquant
en nombre). Le MAJ "import sur l'event loop" est leve et verifie dans le code, avec un test.
Les deux MAJ restants n'ont pas ete traites par la PR #367 ; plan de remediation :

1. Rendus de page sur le chemin du fichier (`page_raster.py`, `generate_preview`,
   `page_sizes`) [MAJ 12.1.5] -> +2 => 76.
2. Ecritures de chunks en `executemany` dans une transaction, `_shift_sequences` en un
   `UPDATE` [MAJ 12.1.1] (et parse chargee une fois dans `show_sources` [MIN]) -> +2 => 86 (GO).

Recommandes a faible risque : `pages_json` sous `asyncio.to_thread` et l'import sous le
semaphore [INFO], verrou pdfium sur `page_sizes` / `_count_pdf_pages` [MIN], reconciliation
au boot des analyses orphelines [MIN].

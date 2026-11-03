# Rapport d'audit : Performance & Ressources (re-audit)

**Release** : 0.7.4 (re-audit apres remediation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (100 commits de remediation depuis `e6047c2`)

Baseline : `reports/release-0.7.4/12-performance.md` (67/100, 2 MAJ + 7 MIN + 9 INFO, code audite
`1de1929`, rapport commite en `e6047c2`). Perimetre identique : `document-parser/` (hors `.venv/`,
`__pycache__/`, `tests/`), `frontend/src/`, `nginx.conf.template`, `frontend/nginx.conf.template`,
`frontend/public/`, `frontend/index.html`.

**Meme lecture des items qu'en 0.7.4** (granularite binaire, critere de 12.1.4 inchange, severite
contextualisee comme en 0.7.3 / 0.7.4). Le seul point ou une autre lecture serait defendable
(reliquat N+1 de `show_sources`, 12.1.1) est signale avec les deux scores.

Methode :
- Lecture du code a `a4d9679` ; chaque ecart 0.7.4 re-verifie dans le code, pas dans les messages
  de commit. Recherche des regressions sur les fichiers ajoutes ou modifies
  (`git diff --stat e6047c2..HEAD`), dont `infra/pdf_inspector.py`, `infra/pdfium_lock.py`,
  `infra/file_storage.py`, `infra/ssrf_guard.py`, `services/chunk_push_service.py`,
  `services/document_tree_service.py`, `persistence/timestamps.py`, `mcp_adapter/sources_*.py`.
- Balayage AST de tous les `await` situes dans une boucle ou une comprehension (`services/`, `api/`,
  `mcp_adapter/`, `persistence/`, `infra/`, `bootstrap/`).
- Tests cibles : `test_page_raster.py`, `test_pdf_inspector.py`, `test_chunk_repos.py`,
  `test_chunk_service.py`, `test_version_service.py`, `test_document_versions_api.py`,
  `test_document_service.py`, `test_source_service.py`, `test_analysis_service.py`,
  `test_api_endpoints.py` : **265 passed**. Suites completes non relancees ; resultats du
  coordinateur sur HEAD : pytest 1673 passed / 19 skipped, vitest 522 passed, ruff, eslint,
  prettier, vue-tsc, vite build OK, `npm audit --omit=dev` 0 vulnerabilite.
- Mesures indicatives par scripts hors depot (scratchpad, venv du projet, PDF et DoclingDocument
  synthetiques, SQLite temporaire avec les vrais repositories) ; les deux templates nginx lances
  dans un nginx 1.24 local (backend factice). Application complete non lancee, images Docker non
  construites. Ce qui n'a pas ete mesure est marque PLAUSIBLE.
- `git status` propre apres les mesures : aucun fichier du depot modifie hors ce rapport.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 90 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 11 |

### Detail par item

| # | Item | Poids | 0.7.4 (1de1929) | Re-audit (a4d9679) | Ecarts rattaches |
|---|------|-------|-----------------|--------------------|------------------|
| 12.1.1 | Pas de requete N+1 / acces DB optimises | 2 | Non | **Non** | [MIN] reliquat N+1 `show_sources` (une requete `latest_parsed_ids` par citation verifiee) |
| 12.1.2 | Fichiers uploades temporaires supprimes | 2 | Oui | **Oui** | — |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` configuree et respectee | 2 | Oui | **Oui** | [INFO] imports hors semaphore |
| 12.1.4 | Operations longues hors event loop | 3 | Oui | **Oui** | [INFO] reliquat CPU ; [INFO] DNS de la sonde Ollama |
| 12.1.5 | Pas de fichier entier en memoire sans necessite | 2 | Non | **Oui** | — (MAJ leve) |
| 12.2.1 | Watchers Vue avec cleanup | 2 | Oui | **Oui** | — |
| 12.2.2 | Event listeners supprimes au demontage | 2 | Oui | **Oui** | — |
| 12.2.3 | Annulation ou debounce des requetes | 1 | Oui | **Oui** | [INFO] reports 0.7.0 |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | **Oui** | [INFO] polling des resumes |
| 12.2.5 | Assets lourds optimises | 1 | Non | **Oui** | [INFO] favicon |
| 12.3.1 | Cache nginx pour les fichiers statiques | 1 | Non | **Oui** | — (MIN leve) |
| 12.3.2 | Reponses API de taille raisonnable | 1 | Non | **Oui** | [INFO] historique des versions sans `LIMIT` |
| 12.3.3 | Health check leger | 1 | Oui | **Oui** | — |

Justification par item :

- **12.1.1 — Non conforme (reste).** Les trois motifs de 0.7.4 sont traites : ecritures de chunks en
  lot et en une transaction (MAJ leve), `GET /versions` compte en SQL (MIN leve), `show_sources`
  charge la parse une fois (MIN partiellement leve). Mais il reste une boucle avec requete unitaire :
  `services/source_service.py:104` appelle `_check` par citation, qui appelle
  `CitationService.verify_citation_in` (`services/citation_service.py:104`), qui fait
  `_superseding_parse` (`:147`) -> `latest_parsed_ids([document_id])` (`:207`), une connexion
  aiosqlite et une requete fenetree par citation verifiee, toujours avec le meme argument. Meme
  lecture qu'en 0.7.0-reaudit (« aucun N+1 residuel » exige pour declarer l'item conforme) et qu'en
  0.7.4 (le N+1 de `show_sources` figurait parmi les motifs de non-conformite) : l'item reste
  **Non**. Severite contextualisee MIN comme en 0.7.3 / 0.7.4 (N <= 50, requete indexee, un appel par
  reponse d'agent ; mesure : 59 ms pour 49 citations).
- **12.1.2 — Conforme.** Fichier refuse supprime sous `to_thread` (`services/document_service.py:145`) ;
  `convert_from_path` sans `pdfcairo` ne cree aucun temporaire (`pdf2image.py:176-179`, sortie de
  `pdftoppm` lue sur stdout) ; `pdfinfo_from_bytes` / `convert_from_bytes` (et leurs `mkstemp`) ne
  sont plus appeles ; `grep tempfile|mkstemp|NamedTemporaryFile` vide sur `api/ services/ infra/
  mcp_adapter/ bootstrap/ main.py`.
- **12.1.3 — Conforme.** `infra/settings.py:29`, `:145-147`, `:252` ; `bootstrap/factories.py:202` ;
  `services/analysis_service.py:89` (`asyncio.Semaphore`), `:416` (`async with self._semaphore`).
- **12.1.4 — Conforme.** Tous les appels pdfium / poppler sont dans un thread : rendu `/preview`
  (`services/document_service.py:235` -> `_render` `:261-263`), `/pages` (`:255` -> `:265-266`),
  upload (`:138` -> `_store_and_count` `:268-276`), comptage avant lot
  (`services/analysis_service.py:461`, auparavant sur la loop), rasters MCP
  (`services/citation_image_service.py:72-79`), couche texte (`services/source_service.py:163`). La
  garde SSRF des stores resout le DNS sous `to_thread` (`services/store_service.py:348-352`). Le
  reliquat CPU lineaire reste INFO selon le critere 0.7.3 / 0.7.4 (re-mesure ci-dessous, sans
  regression) ; la resolution DNS de la sonde Ollama sur la loop est pre-existante (INFO).
- **12.1.5 — Conforme (bascule).** Les quatre sites du MAJ ouvrent le PDF stocke par son chemin
  (detail en « Ecarts leves »). Restent en memoire, comme en 0.7.4 sans ecart : le corps de l'upload
  (borne par `MAX_FILE_SIZE_MB`, `api/documents.py:72-79`) et l'envoi au moteur distant
  (`infra/serve_converter.py:119`, sous `to_thread`).
- **12.2.1 / 12.2.2 — Conformes.** Fichiers concernes inchanges hors renommage
  (`PagePreviewWithOverlay.vue:366-394`) ; chaque `addEventListener` a son `removeEventListener`
  (`DocumentActionsMenu.vue:98-99`, `DownloadDropdown.vue:198-202`, `TableModal.vue:46-47`,
  `StudioPage.vue:554-555` / `:682-683`), observers deconnectes (`PagePreviewWithOverlay.vue:527-528`,
  `BboxCanvas.vue:198`, `BboxOverlay.vue:196`), intervals arretes (`AnalysisLibraryPage.vue:169`,
  `StudioPage.vue:681`, `AppSidebar.vue:176-177`, `AnalysisProgressBar.vue:39`).
- **12.2.3 / 12.2.4 — Conformes.** Inchanges (debounces, gardes de requete perimee, computed).
- **12.2.5 — Conforme (bascule).** `frontend/public/logo.png` : 256x256, **56 782 octets** (au lieu de
  1024x1024 / 878 643), affiche a 28-72 px CSS (`App.vue:259-260`, `HomePage.vue:138-139`,
  `StudioPage.vue:707-708`), donc 2x net jusqu'a 128 px. Sous le seuil de ~100 Kio fixe en 0.7.4.
- **12.3.1 — Conforme (bascule).** `location /assets/` avec `Cache-Control "public, max-age=31536000,
  immutable"` et `location = /index.html` en `no-cache`, dans les deux templates
  (`nginx.conf.template:29-45`, `frontend/nginx.conf.template:29-45`) ; verifie en execution (voir
  « Ecarts leves »).
- **12.3.2 — Conforme (bascule).** Bibliotheque d'analyses, History et compteur de la Home sur
  `GET /api/analyses/summaries` ; suppression de document comptee sur les resumes.
- **12.3.3 — Conforme.** `document-parser/main.py:131-170` : `SELECT 1` + lecture de settings et
  d'etat en memoire ; exclu du rate limiter (`infra/rate_limiter.py:59`).

Calcul :
- Poids total = 21 (12.1 : 2+2+2+3+2 = 11 ; 12.2 : 2+2+1+1+1 = 7 ; 12.3 : 1+1+1 = 3).
- Non conformes : 12.1.1 (2) = 2. Poids conformes = 19. `score = 19 / 21 * 100 = 90,5` =>
  **90 / 100**.
- **Autre lecture possible** (non retenue) : si l'on tolere le reliquat de 12.1.1 comme le reliquat
  CPU de 12.1.4 (borne, quelques dizaines de ms), l'item bascule et le score est **21 / 21 = 100**.
  Elle romprait avec 0.7.0-reaudit, ou l'item n'a ete declare conforme qu'une fois tous les appels
  sortis des boucles ; d'ou 90 retenu.

Delta vs 0.7.4 : **67 -> 90 (+23,8)**, 8/13 -> 12/13 items. Quatre items basculent : 12.1.5 (+9,5),
12.2.5, 12.3.1, 12.3.2 (+4,8 chacun). C'est exactement le palier « quick wins » prevu par le plan
0.7.4 (90) ; 12.1.1 ne bascule pas malgre la levee de son MAJ, a cause du reliquat.

---

## Verification des ecarts 0.7.4

| Ecart 0.7.4 | Statut a a4d9679 | Preuves (code actuel) |
|---|---|---|
| [MAJ] PDF entier relu et recopie par page rendue (12.1.5) | **Corrige** | `infra/page_raster.py:19`, `:31-40` (`convert_from_path(storage_path, ...)`) ; `infra/pdf_inspector.py:25-47` (`pdfium.PdfDocument(storage_path)`) ; `services/document_service.py:261-266`, `:275-281` ; plus aucun `read_bytes` / `convert_from_bytes` / `pdfinfo_from_bytes` dans le code applicatif |
| [MAJ] Ecritures de chunks une-requete-par-chunk (12.1.1) | **Corrige** | `persistence/chunk_repo.py:80-111` (`replace_chunkset` : `executemany` x3, un `commit`, `rollback`), `:113-127` (`shift_sequences` en un `UPDATE`) ; `persistence/chunk_edit_repo.py:57-64` ; call sites `services/chunk_service.py:114`, `:136-146`, `:190-199`, `:215-221`, `:249-255`, `:305-311` ; `services/version_service.py:150-170` |
| [MIN] `show_sources` recharge la parse par citation (12.1.1) | **Partiellement corrige** | parse chargee une fois `services/source_service.py:103`, `verify_citation_in` `services/citation_service.py:104-114`, `outline_of(parse)` `source_service.py:106` ; **reste** `latest_parsed_ids` par citation verifiee (`citation_service.py:147`, `:205-208`) |
| [MIN] `GET /versions` charge toutes les snapshots (12.1.1) | **Corrige** | `persistence/document_version_repo.py:34-39` (`json_array_length` en SQL, snapshot non selectionne), `:70-80` ; `api/document_versions.py:44-45` ; `restore` compte sans re-decoder (`services/version_service.py:178-180`, `api/document_versions.py:60-61`) |
| [MIN] Bibliotheque sur la liste complete (12.3.2) | **Corrige** | `frontend/src/features/analysis/store.ts:63-75` ; `features/history/api.ts:8-10` (History et Home : `pages/HomePage.vue:91`) ; `pages/DocsLibraryPage.vue:348-363` + `DocsLibraryPage.logic.ts:34-43` ; `persistence/analysis_repo.py:39-44`, `:70-78` |
| [MIN] Logo / favicon (12.2.5) | **Corrige** (logo) ; favicon : voir INFO | `frontend/public/logo.png` 256x256, 56 782 o ; `frontend/index.html:7` |
| [MIN] Pas de cache nginx (12.3.1) | **Corrige** | `nginx.conf.template:29-45`, `frontend/nginx.conf.template:29-45` |
| [MIN] pdfium hors verrou (hors checklist) | **Corrige** | `infra/pdfium_lock.py:16-19` (verrou de Docling, ou verrou propre sans Docling) ; `infra/pdf_inspector.py:26`, `:34` ; `infra/page_text.py:24` ; `_count_pdf_pages` sous `to_thread` (`services/analysis_service.py:452-464`) ; test `tests/test_pdf_inspector.py:98` |
| [MIN] Suivi a 3 s sans borne (hors checklist) | **Inchange** | `frontend/src/features/analysis/store.ts:184-195` (aucun plafond, vs `MAX_POLLING_DURATION` `:40` du seul polling unitaire) ; aucune reconciliation `PENDING`/`RUNNING` au boot (`grep` vide dans `bootstrap/`, `main.py`, `persistence/`, `services/`) |
| [INFO] Reliquat CPU sur la loop | Inchange (re-mesure, sans regression) | voir INFO |
| [INFO] `/preview` et `/pages` sans cache HTTP | **Corrige** | `api/documents.py:33`, `:173-177`, `:195` ; tests `tests/test_api_endpoints.py:278`, `:329`, `:359`, `:377` (en-tete pose sur succes, absent sur erreur) |
| [INFO] Aucune compression HTTP | **Corrige** | `nginx.conf.template:9-14`, `frontend/nginx.conf.template:9-14` ; `gzip off` sur `/mcp` (`:74`) |
| [INFO] Imports hors semaphore | Inchange | `services/analysis_service.py:172` vs `:416` |
| [INFO] Polling des resumes | Inchange | `store.ts:184-195` ; `batch.ts:25-35` ; `AnalysisLibraryPage.vue:52`, `:158-162` |
| [INFO] `/summaries` colonnes legeres apres les lourdes | Inchange (PLAUSIBLE) | `persistence/analysis_repo.py:39-44` vs `persistence/database.py:67-81` |
| [INFO] Budgets memoire/CPU MCP | Inchange | `services/citation_image_service.py:89-91`, `:125-130` ; `infra/page_raster.py:38-40` puis `:51` |
| [INFO] Fusion des lots | Inchange | `services/analysis_service.py:324` ; `infra/local_converter.py:172-177` |
| [INFO] Reports 0.7.0 | Partiellement corrige | petits appels bloquants de `delete` / `resolve_storage_path` desormais sous `to_thread` (`services/document_service.py:209`, `:235`, `:255`) ; le reste inchange (voir INFO) |

---

## Ecarts constates (ouverts)

### [MIN] `show_sources` : une requete `latest_parsed_ids` par citation verifiee (reliquat N+1) — statut vs 0.7.4 : partiellement corrige ; contextualise MAJ -> MIN

- **Localisation** : `document-parser/services/source_service.py:104`
  (`cited_anchors = [await self._check(parse, anchor, quote) for anchor, quote in quoted]`) ->
  `:181` (`self._citations.verify_citation_in(parse, anchor, quote)`) ->
  `services/citation_service.py:147` (`current = await self._superseding_parse(...)`) -> `:207`
  (`self._parses.analyses.latest_parsed_ids([document_id])`) -> `persistence/analysis_repo.py:129-146`
  (connexion neuve + requete `ROW_NUMBER() OVER (PARTITION BY ...)`).
- **Constat** : la remediation 0.7.4 a ete appliquee telle que proposee (parse chargee une fois,
  variante `verify_citation_in`, `outline_of(parse)`) ; la parse n'est plus relue. Mais
  `verify_citation_in` garde la verification « parse supplantee » de `verify_citation`, et la refait
  pour chaque citation dont la citation est trouvee, alors que toutes les ancres epinglent le meme
  `(document, version)` (`_single_pin`, `source_service.py:242-255`) : la reponse est identique a
  chaque tour. Le N+1 sur la parse (2N + 4 connexions en 0.7.4) devient un N+1 sur une requete plus
  legere (N + 3 a froid, N + 2 a chaud).
- **Mesure** : appels de repository comptes sur les faux repos des tests (`ParseLoader` reel) —
  1 / 10 / 49 citations verifiees => `find_by_id` 1, `parsed_document_id` 1, `parse_json` 1,
  `latest_parsed_ids` **1 / 10 / 49**. Cout SQLite reel (base temporaire, 20 documents x 10
  analyses) : 2,2 ms pour 1 appel, **59 ms pour 49** (mediane de 7).
- **Regle violee** : 12.1.1 (poids 2) — « pas de boucle avec requete unitaire ». Contextualise MIN,
  comme en 0.7.3 / 0.7.4 : N plafonne a 50 (`services/navigation_config.py:60`), un appel par reponse
  d'agent, requete indexee (`idx_analysis_jobs_doc_status`, `persistence/database.py:86`). L'item
  reste compte non conforme dans le score (precedent : 12.2.1 en 0.6.1, compte non conforme avec un
  ecart contextualise MIN).
- **Remediation** (S, ~10 lignes + un test, risque faible) : calculer la parse courante une fois.
  - `CitationService` : rendre `_superseding_parse` public (`superseding_parse`) et donner a
    `verify_citation_in` un parametre `current: str | None` passe par l'appelant ;
    `verify_citation` (`citation_service.py:92-102`) l'appelle une fois avant de deleguer.
  - `SourceService.show` (`source_service.py:103-104`) : `current = await
    self._citations.superseding_parse(document_id, version_id)` apres le `load`, puis le passer a
    `_check` / `verify_citation_in`.
  - Test : etendre `tests/test_source_service.py:306-363` (`TestOneParsePerCall`) en comptant
    `latest_parsed_ids` (1 appel pour 3 citations) ; les statuts `STALE_VERSION` sont deja couverts
    par les tests de `verify_citation` (`tests/test_navigation_service.py`).
  - Gain : 12.1.1 bascule, **+9,5 => 100 / 100**.

### [MIN] Le suivi a 3 s n'a pas de borne de duree (hors checklist) — statut vs 0.7.4 : inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:184-195` (`followActive`, aucun
  plafond ; seul le polling unitaire a `MAX_POLLING_DURATION`, `:40`, `:139-144`) ; aucune
  reconciliation au demarrage des lignes `PENDING` / `RUNNING` (taches en memoire,
  `services/analysis_service.py:90`, `:142-154`).
- **Constat** : inchange depuis 0.7.3. Un redemarrage du backend pendant un lot laisse des analyses
  actives pour toujours ; la bibliotheque ouverte interroge alors `/summaries` toutes les 3 s sans
  fin. La requete est desormais legere (resumes) mais compte toujours dans le rate limit.
- **Remediation** : marquer `FAILED` les analyses `PENDING` / `RUNNING` dans le lifespan ; plafond de
  duree sur `followActive`. N'affecte pas le score.

### [INFO] Reliquat CPU sur l'event loop — statut vs 0.7.4 : inchange, re-mesure

- **Localisation** : `services/analysis_service.py:519` (`pages_json`) ;
  `services/document_tree_service.py:47-60` (`GET /api/documents/{id}/tree`,
  `api/document_chunks.py:145-155` : `json.loads` + `build_doc_tree` sur la loop, et
  `find_by_id` / `find_latest_completed_by_document` en `SELECT aj.*` pour n'utiliser que
  `document_json`) ; `infra/serve_converter.py` (parse de la reponse distante) ;
  `domain/outline_builder.py` (mode pages) ; `infra/neo4j/tree_writer.py` (si Neo4j branche).
- **Mesure** : `get_tree` deplace dans `domain/doc_tree.py` ; mesure cote a cote sur la meme machine,
  DoclingDocument synthetique : 20 pages (0,8 Mo) 5 ms a HEAD vs 8 ms pour l'ancien code ; 500 pages
  x 40 elements (20 Mo) **274 ms a HEAD vs 255 ms** pour l'ancien code (bruit de mesure ; 212 ms
  mesures en 0.7.4 sur une autre execution). Pas de regression ; meme ordre que `pages_json`.
- **Suggestion** : `asyncio.to_thread` pour `get_tree` et `pages_json` ; lire `document_json` seul
  (`persistence/analysis_repo.py:158-165`, `parse_json`) apres un controle d'appartenance leger.

### [INFO] Resolution DNS de la sonde Ollama sur l'event loop (nouveau releve, pre-existant)

- **Localisation** : `document-parser/infra/llm/ollama_probe.py:35`
  (`resolved_target_is_blocked(host)`, synchrone dans `async def probe`) -> `infra/ssrf_guard.py:51`
  (`socket.getaddrinfo`). Appele par `services/app_config_service.py:134` (test de connexion
  Settings > Ask).
- **Constat** : la garde existait deja en `e6047c2` (`_resolved_target_is_blocked`, meme
  `getaddrinfo`) : pas une regression. La remediation l'a factorisee dans `infra/ssrf_guard.py` et l'a
  bien deportee pour les stores (`services/store_service.py:348-352`, `to_thread`), mais pas pour la
  sonde Ollama. Une resolution lente (DNS injoignable : jusqu'a plusieurs secondes, PLAUSIBLE) gele
  toutes les requetes pendant ce temps. Route d'administration, un appel par clic.
- **Suggestion** : `if await asyncio.to_thread(resolved_target_is_blocked, host):`
  (`ollama_probe.py:35`). Effort S.

### [INFO] Historique des versions : liste sans `LIMIT` ni retention (nouveau releve)

- **Localisation** : `persistence/document_version_repo.py:34-39` (`ORDER BY created_at DESC`, sans
  `LIMIT`) ; insertion d'un chunkset complet a chaque analyse et chaque rechunk
  (`services/version_service.py:97-108`, `:118-129`).
- **Constat** : le correctif du MIN est en place et efficace : le snapshot ne quitte plus SQLite.
  Mesure (20 versions x 500 chunks, 6,7 Mo de snapshots) : **10,7 ms** de latence, **1,6 ms** de CPU
  sur le thread de la loop. Mais `json_valid` + `json_array_length` relisent toujours chaque
  snapshot dans SQLite : cout lineaire en volume d'historique, sans borne ni retention.
- **Suggestion** : colonne `chunk_count` ecrite a l'insertion (lecture O(1) par ligne) et/ou `LIMIT`
  sur la liste ; politique de retention a decider.

### [INFO] `/pages` et le comptage de pages attendent le verrou pdfium de Docling (nouveau, PLAUSIBLE)

- **Localisation** : `infra/pdf_inspector.py:26`, `:34` ; `infra/pdfium_lock.py:17`.
- **Constat** : effet voulu du correctif « pdfium hors verrou » (surete des threads). Pendant une
  conversion locale, `/pages` (33 ms de travail mesures) et `_count_pdf_pages` peuvent attendre une
  operation pdfium de Docling. Docling prend le verrou par operation (`docling/backend/
  pypdfium2_backend.py`, une quinzaine de `with pypdfium2_lock:` courts), donc l'attente est courte ;
  non mesure (Docling absent du venv de test). `/preview` (poppler) n'est pas concerne.

### [INFO] Favicon = logo PNG de 57 Ko ; `favicon.svg` orphelin (nouveau, residuel de 12.2.5)

- **Localisation** : `frontend/index.html:7` (`rel="icon" type="image/png" href="/logo.png"`) ;
  `frontend/public/favicon.svg` (270 octets, non reference). Les fichiers de `public/` hors
  `/assets/` n'ont pas de `Cache-Control` explicite (revalidation heuristique, `ETag` /
  `Last-Modified` de nginx).
- **Constat** : choix assume par le CHANGELOG (« it is also the favicon »). Le logo est deja
  optimise en PNG (`optimize` ne gagne rien) ; mesures : PNG 256 couleurs 25 Ko, WEBP q85 10 Ko,
  favicon 32 px 2 Ko. N'affecte pas 12.2.5.

### [INFO] Imports paralleles, hors du semaphore d'analyse — statut vs 0.7.4 : inchange

- **Localisation** : `services/analysis_service.py:157-182` (`deserialize` sous `to_thread`, `:172`) ;
  le semaphore n'entoure que `_run_analysis` (`:416`). Desormais borne en entree : corps <= 200 Mo
  (`api/analyses.py:35`, `:45-78`) et cellules de tableaux <= `MAX_IMPORT_TABLE_CELLS`
  (`infra/docling_importer.py:33-65`, controle dans le thread). Reste la concurrence non bornee des
  imports.

### [INFO] Polling des resumes — statut vs 0.7.4 : inchange

- **Localisation** : `frontend/src/features/analysis/store.ts:184-195` (`setInterval` sans garde de
  requete en vol, continue onglet masque) ; `batch.ts:25-35` ; `AnalysisLibraryPage.vue:52`,
  `:158-162` (un `Intl.DateTimeFormat` construit par ligne).

### [INFO] `/summaries` : colonnes legeres stockees apres les lourdes (PLAUSIBLE) — statut vs 0.7.4 : inchange

- **Localisation** : `persistence/analysis_repo.py:39-44` vs `persistence/database.py:67-81`.
  Plus sollicite qu'en 0.7.4 (bibliotheque, History, Home, suppression), toujours borne a 200 lignes.

### [INFO] Budgets memoire/CPU du serveur MCP : bornes, mais larges — statut vs 0.7.4 : inchange

- **Localisation** : `services/citation_image_service.py:89-91`, `:125-130` (re-rendu complet a chaque
  palier de dpi) ; `infra/page_raster.py:38-40` puis `:51` (PNG encode puis redecode pour le WEBP) ;
  aucun semaphore ni cache serveur autour des rendus poppler ; `convert_from_path` lance toujours
  `pdfinfo` + `pdftoppm` par page. Etape 3 (optionnelle, M) du plan 0.7.4 non faite ;
  `services/navigation_config.py:44-54`.

### [INFO] Fusion des lots : pic memoire en fin d'analyse longue — statut vs 0.7.4 : inchange

- **Localisation** : `services/analysis_service.py:324` ; `infra/local_converter.py:172-177`.

### [INFO] Observations reportees de 0.7.0 — statut vs 0.7.4 : partiellement traite

- Corrige : `DocumentService.delete` et la resolution du chemin stocke passent sous `to_thread`
  (`services/document_service.py:209`, `:235` -> `:261-263`, `:255` -> `:265-266`).
- Inchange : connexion neuve par appel, pas de `journal_mode=WAL` (`persistence/database.py:265-280`) ;
  pas d'`AbortController` ; minuteurs a un coup non annules (`ChunksEditor.vue` `saveTimer`,
  `DocsLibraryPage.vue` `searchTimer`) ; upload lu en memoire, borne (`api/documents.py:72-79`).

---

## Ecarts leves — verification detaillee

### [MAJ] 12.1.5 — PDF relu et recopie par page rendue : corrige

- **Rasters MCP** : `infra/page_raster.py:33-35` (`Path(storage_path).is_file()` puis
  `convert_from_path(storage_path, first_page=page, last_page=page, dpi=dpi)`), appele dans le
  thread de `services/citation_image_service.py:72-79`.
- **`/preview`** : `api/documents.py:158` -> `services/document_service.py:219-241` : un seul
  `to_thread` (`:235`) qui resout le chemin et rend (`:261-263`, port `PageRasterizer`).
- **`/pages`** : `api/documents.py:187` -> `services/document_service.py:243-259` -> `:265-266` ->
  `infra/pdf_inspector.py:33-47` (`PdfDocument(storage_path)` sous `pdfium_lock`).
- **Upload** : `services/document_service.py:138` -> `:268-276` -> `:278-284` ->
  `infra/pdf_inspector.py:25-31` (pdfium par chemin, au lieu de `pdfinfo_from_bytes`) ; un PDF
  illisible reste accepte avec `page_count=None` (`:282-284`), comme avant.
- **Mesure** (PDF synthetique 17 pages, 48,2 Mo, page 9 a 150 dpi, mediane de 5, un processus par
  variante ; « ecrit » = `write_bytes` du processus Python) :

  | Chemin | Code 0.7.4 (reproduit) | HEAD (adaptateurs reels) |
  |--------|------------------------|--------------------------|
  | Rendu d'une page | 495 ms, RSS 93 Mio, 48,2 Mo ecrits | **449 ms, RSS 63 Mio, 0 Mo ecrit** |
  | Tailles de page (`/pages`) | 51 ms, RSS 360 Mio | **33 ms, RSS 85 Mio** |
  | Comptage a l'upload | 105 ms, RSS 80 Mio, 48,2 Mo ecrits | **0,1 ms, RSS 39 Mio, 0 Mo ecrit** |

  Coherent avec le CHANGELOG (115 -> 67 Mio par page, 59 -> 33 ms pour les tailles).
- **Tests** : `tests/test_page_raster.py:43-74` (dont `test_reads_the_stored_file_in_place`, `:62`),
  `tests/test_pdf_inspector.py:30-98` (dont l'attente du verrou partage, `:98`), adaptations de
  `tests/test_document_service.py`. Le manque releve en 0.7.4 (aucun test direct de
  `PdfPageRasterizer`) est comble.

### [MAJ] 12.1.1 — Ecritures de chunks une-requete-par-chunk : corrige

- **Repository** : `persistence/chunk_repo.py:80-111` (`replace_chunkset` : retrait par
  `executemany`, insertion par `executemany`, journal par `write_edits`
  (`persistence/chunk_edit_repo.py:57-64`), un `commit`, `rollback` sur exception) ; `:113-127`
  (`shift_sequences` en un `UPDATE ... sequence = sequence + 1`, sans conflit : l'index
  `idx_chunks_doc_seq` n'est pas UNIQUE, `persistence/database.py:154`).
- **Call sites** : promotion `services/chunk_service.py:114-116` ; ajout `:136` + `:141-146` ; split
  `:190-199` ; merge `:215-221` (plus de `soft_delete` en boucle) ; rechunk `:249-255` ; restore
  `services/version_service.py:160-170` (snapshot decode avant toute ecriture, `:150-153`) ;
  `_shift_sequences` `:305-311` (saute l'UPDATE quand on ajoute en fin). Le balayage AST ne trouve
  plus aucune ecriture dans une boucle.
- **Mesure** (SQLite temporaire, vrais repositories, script du coordinateur adapte aux signatures de
  HEAD, N = 500, mediane de 3) : rechunk **42 ms**, restore **42 ms**, ajout en tete **17 ms**, fusion
  des 500 chunks **18 ms**. En 0.7.4 : ~3 s pour les seuls retraits + journal de 500 chunks ;
  CHANGELOG : 4,6 s -> 0,1 s (rechunk), 4,5 s -> 0,06 s (restore).
- **Integrite** : la promesse « audit + ecriture dans la meme transaction » est maintenant vraie pour
  les operations multi-chunks ; test `tests/test_chunk_repos.py:171`
  (`test_failure_rolls_everything_back`), manque signale en 0.7.4. `update_chunk` / `delete_chunk`
  (un chunk) ecrivent toujours le chunk puis la ligne d'audit sur deux connexions
  (`services/chunk_service.py:167-168`, `:174-177`) : constant, pas un N+1 ; documente
  (`persistence/chunk_edit_repo.py`, docstring de `SqliteChunkEditRepository`).
- Ajout et split restent en deux transactions (`shift_sequences` puis `replace_chunkset`) : un echec
  du second laisse un trou de sequence, que l'invariant d'ordre autorise (commentaire
  `services/chunk_service.py:186-188`). Pas un ecart de performance.

### [MIN] `GET /versions` : corrige (voir aussi l'INFO de retention)

`persistence/document_version_repo.py:34-39`, `:70-80` ; le snapshot n'est jamais selectionne,
`json_valid` protege d'un snapshot corrompu. Restore : le compte vient du snapshot deja decode
(`services/version_service.py:178-180`), l'API ne re-decode plus (`api/document_versions.py:60-61`).
Mesure : 10,7 ms de latence, 1,6 ms de CPU sur la loop (20 versions x 500 chunks) ; 0.7.4 :
55 ms de CPU sur la loop (jeu de 14,2 Mo).

### [MIN] Bibliotheque sur la liste complete (12.3.2) : corrige

- Bibliotheque : `frontend/src/features/analysis/store.ts:63-75` (`fetchAnalysisSummaries`) ; le
  type de la liste est `AnalysisSummary[]` (`:32`).
- History et compteur de la Home : `features/history/api.ts:8-10`, `features/history/store.ts:13`,
  `pages/HomePage.vue:91`.
- Suppression d'un document : `pages/DocsLibraryPage.vue:348-363` -> `DocsLibraryPage.logic.ts:34-43` :
  compte sur les resumes ; la liste complete du document n'est relue que si les resumes atteignent la
  page de 200 (`:17`, `:39-42`), pour ne jamais sous-estimer. Repli rare et borne.
- `GET /api/analyses` (liste complete) reste expose (`api/analyses.py:150-161`) mais n'est plus appele
  par le frontend (`grep` : seul `fetchDocumentAnalyses` en repli).

### [MIN] Cache nginx (12.3.1) et [INFO] compression : corriges, verifies en execution

Les deux templates (`${NGINX_MAX_BODY_SIZE}` = 200M, racine et backend remplaces) passent
`nginx -t` et ont ete servis par nginx 1.24 avec `Accept-Encoding: gzip` :

| Requete | Statut | `Cache-Control` | `Content-Encoding` | En-tetes de securite |
|---------|--------|-----------------|--------------------|----------------------|
| `/`, `/index.html`, route SPA `/docs/abc` | 200 | `no-cache` | gzip | presents |
| `/assets/app-<hash>.js` | 200 | `public, max-age=31536000, immutable` | gzip | presents |
| `/assets/absent.js` | **404** (plus l'app shell) | — | — | presents |
| `/api/x` (JSON > 1 Ko) | 200 | celui du backend | gzip | presents |

Resultats identiques pour `nginx.conf.template` et `frontend/nginx.conf.template`. Les en-tetes de
securite repetes dans chaque `location` qui pose un `add_header` sont bien presents (piege releve en
0.7.4). `/mcp` reste non compresse et non bufferise (`:73-74`). Les images Docker elles-memes n'ont
pas ete construites ici.

### [INFO] `/preview` et `/pages` sans cache HTTP : corrige

`api/documents.py:28-33` (`private, max-age=86400`, justifie par l'immuabilite d'un PDF stocke sous
un id neuf), pose sur succes seulement (`:173-177`, `:195`) ; tests `tests/test_api_endpoints.py:278`,
`:329`, `:359`, `:377`. La cle du rate limiter (autre volet de cette INFO) releve de l'audit 08 :
dans l'image unique nginx ajoute l'adresse du pair et uvicorn prend la plus a droite non fiable
(`nginx.conf.template:47-56`) ; en Compose a deux conteneurs, le backend limite par l'adresse du
proxy tant que `FORWARDED_ALLOW_IPS` n'est pas renseigne (`frontend/nginx.conf.template:47-51`,
aucun `FORWARDED_ALLOW_IPS` dans `docker-compose.yml`).

### [MIN] pdfium hors verrou : corrige

`infra/pdfium_lock.py:16-19` reutilise `docling.utils.locks.pypdfium2_lock` quand Docling est
installe (le meme objet que Docling prend), un `threading.Lock` sinon ; pris par
`infra/pdf_inspector.py:26`, `:34` et `infra/page_text.py:24`. `_count_pdf_pages` n'est plus sur la
loop (`services/analysis_service.py:461`).

---

## Regressions et nouveaux appels bloquants / N+1 introduits par la remediation

Aucune regression de performance trouvee. Points verifies :

- **Garde SSRF des stores** (nouvelle) : resolution DNS sous `to_thread`
  (`services/store_service.py:348-352`), a la creation, a la mise a jour et avant chaque test de
  connexion. La sonde Ollama, elle, resout sur la loop : pre-existant (INFO ci-dessus).
- **`FileStorage`** (nouveau port, `infra/file_storage.py`) : synchrone par conception, toujours appele
  dans un thread (`services/document_service.py:138`, `:145`, `:209`, `:235`, `:255` ;
  `services/export_service.py:64`). Aucun appel direct depuis un handler async (`grep` sur `api/`,
  `services/`, `mcp_adapter/`). `save` ecrit par tranches de 64 Ko (`:29-35`).
- **Verrou pdfium partage** : pas de reentrance (une seule ouverture de document par prise) ; effet
  d'attente possible pendant une conversion locale (INFO PLAUSIBLE).
- **`verify_citation_in`** : supprime le rechargement de la parse mais conserve une requete par
  citation (le [MIN] ouvert).
- **Balayage AST des `await` en boucle** : seuls restent `source_service.py:104` (le MIN),
  `chunk_push_service.py:283` (une requete par store distinct, memoisee — deja en point positif en
  0.7.4), la boucle de lots `analysis_service.py:305-325` (une requete de controle et de progression
  par lot, voulu), et des boucles d'infrastructure hors base (`neo4j`, `embedding_client`, retries de
  `serve_converter`).
- **Construction de l'arbre deplacee** (`domain/doc_tree.py`) : temps identique a l'ancien code
  (mesure cote a cote).
- **`_BoundedBodyRoute`** (`api/analyses.py:45-78`) : compte le corps pendant la lecture au lieu de le
  lire puis le mesurer ; aucun cout supplementaire.

---

## Points positifs

- **Les deux MAJ reconduits depuis 0.6.2 et 0.7.3 sont leves**, avec des gains mesures d'un a deux
  ordres de grandeur (rechunk 500 chunks : ~3-4,6 s -> 42 ms ; ecritures disque par page rendue :
  48 Mo -> 0).
- **Les remediations suivent le plan 0.7.4 point par point** : `replace_chunkset` / `shift_sequences`
  / `write_edits`, verrou factorise `infra/pdfium_lock.py`, `Cache-Control` sur `/preview` et
  `/pages`, `json_array_length`, resumes partout, `immutable` + `no-cache` + gzip dans les deux
  templates.
- **Atomicite gagnee au passage** : un rechunk, une restauration, une fusion ou un split en echec ne
  laissent plus de chunkset a moitie remplace (test de rollback `tests/test_chunk_repos.py:171`).
- **Les manques de tests releves en 0.7.4 sont combles** : test direct de l'adaptateur de rendu
  (`tests/test_page_raster.py`), de l'inspecteur et du verrou (`tests/test_pdf_inspector.py`), des
  en-tetes de cache (succes et erreur), du rollback.
- **Tous les appels PDF hors loop**, y compris le comptage avant lot qui y etait encore.
- **Health check toujours leger**, lectures de liste toujours bornees (`LIMIT 200` sur documents et
  analyses, editions et pushes pagines), parse MCP chargee une fois et cachee
  (`services/parse_loader.py:99-135`).
- **Frontend sans fuite** : listeners, observers et intervals inchanges et nettoyes.

---

## Ce qui reste pour 100

| Ordre | Action | Item | Effort | Risque | Score apres |
|-------|--------|------|--------|--------|-------------|
| 1 | Calculer la parse courante une fois dans `SourceService.show` et la passer a `verify_citation_in` (+ test de comptage de `latest_parsed_ids`) | 12.1.1 | S | Faible | **100** |

Recommandes hors score : borne de duree sur `followActive` et reconciliation au boot des analyses
orphelines (le seul autre MIN) ; `to_thread` pour la sonde Ollama, `get_tree` et `pages_json` ;
`chunk_count` stocke et `LIMIT` / retention sur les versions ; `favicon.svg` ou un favicon de 32 px ;
semaphore et cache borne autour des rendus MCP (etape 3 du plan 0.7.4).

---

## Verdict partiel : GO

Score **90/100** (>= 80), **0 ecart CRITICAL**, **0 ecart MAJOR**, 2 MINOR, 11 INFO. Gain de
**+23,8 points** sur 0.7.4 (67 -> 90) : les deux MAJ et cinq des sept MIN sont leves, un MIN est
partiellement leve, un MIN hors checklist est inchange ; aucune regression. Le seul item non conforme
(12.1.1) tient a un reliquat d'une requete legere par citation dans `show_sources` (59 ms pour 49
citations) ; sa correction (S) donne 100. Lu de facon tolerante, ce reliquat donnerait deja 100.

---

## Addendum — vérification post-correctifs (HEAD 3f1d1cb, 2026-11-03)

Verification dans le code de la passe `a4d9679..3f1d1cb` (commit `db43a21` pour cet audit). Gates du coordinateur sur `3f1d1cb` : pytest **1723 passed, 19 skipped**, vitest 522 passed, ruff, eslint, prettier, vue-tsc, build OK. Pas de run CI. Tests cibles relances localement (dont `tests/test_source_service.py`) : passes.

### Ecart vise : [MIN] 12.1.1, reliquat N+1 de `show_sources`

**Statut : ferme.**

- `SourceService.show` pose la question « une parse plus recente supplante-t-elle celle-ci ? » **une fois par appel**, apres le chargement unique de la parse et seulement s'il y a des citations : `services/source_service.py:106-110` (`superseded_by = await self._citations.superseding_parse(...) if quoted else None`).
- La reponse est passee a chaque verification : `:111-114`. `_check` (`:175`) est desormais synchrone, et la boucle ne contient plus aucun `await`.
- `CitationService.verify_citation_in` (`services/citation_service.py:105-119`) recoit `superseded_by` et ne fait aucune I/O (« Reads nothing: no I/O »). `superseding_parse` (`:211-216`) est l'unique appel a `latest_parsed_ids`. `verify_citation` (outil MCP unitaire, `:92-103`) l'appelle une fois avant de deleguer.
- **Test** : `tests/test_source_service.py:306` (`TestOneParsePerCall`), avec un repository qui compte les appels a `latest_parsed_ids` :
  - 3 citations : `latest_lookups == [[DOC_ID]]` (`:379`) ;
  - parse supplantee : un seul appel, et chaque citation trouvee est marquee `stale_version` (`:381-389`) ;
  - aucune citation : aucun appel (`:391-394`).

  Le compte du re-audit (1 / 10 / 49 appels pour 1 / 10 / 49 citations) devient **1 / 1 / 1**.
- **Nuance** : l'appel a lieu des qu'il y a une citation, meme si aucune n'est trouvee (avant : seulement pour les citations trouvees). Au plus 1 requete legere par carte : sans effet.

### Regressions

Aucune. Balayage AST des `await` en boucle ou en comprehension sur les 22 fichiers backend modifies par la passe (hors tests). Il ne trouve que des sites anterieurs, deja juges au re-audit :
- la boucle de lots de `services/analysis_service.py:305-325` ;
- les stores dedoublonnes de l'historique des push, `services/chunk_push_service.py:289` ;
- des iterables de comprehension evalues une fois (`api/analyses.py:196`, `services/document_service.py:196`) ;
- les lectures de corps par morceaux (`api/analyses.py:62`, `api/documents.py:69`).

Les autres changements de la passe vont dans le bon sens ou sont neutres :
- le plafond de corps de `/api/analyses` passe de 200 a 50 Mo (`api/analyses.py:45`), ce qui borne le pic memoire d'un import (≈ 2,2 Go d'apres `:31-44`) ;
- le budget de grilles est verifie sur le JSON brut avant validation (`infra/docling_importer.py:172`) ;
- le test de connexion d'un store fait une resolution DNS de plus, hors boucle d'evenements (`store_backend_resolver.py:163`), ce qui est negligeable.

L'INFO « imports hors semaphore » est inchangee. L'audit 08 chiffre le cout d'un import juste sous le budget : 641 octets → ≈ 10 s, ≈ 220 Mo, ≈ 25 Mo ecrits.

### Score recalcule

| Lecture | Re-audit (`a4d9679`) | Post-correctifs (`3f1d1cb`) |
|---------|----------------------|-----------------------------|
| Retenue (« aucun N+1 residuel ») | 90 (19 / 21) | **100** (21 / 21) |
| Tolerante (reliquat borne accepte) | 100 | 100 |

| Metrique | Re-audit | Post-correctifs |
|----------|----------|-----------------|
| Items conformes | 12 / 13 | **13 / 13** |
| Score | 90 / 100 | **100 / 100** |
| Ecarts CRITICAL | 0 | 0 |
| Ecarts MAJOR | 0 | 0 |
| Ecarts MINOR | 2 | **1** (suivi a 3 s sans borne de duree, `frontend/src/features/analysis/store.ts:184-195`, inchange) |
| Ecarts INFO | 11 | 11 |

### Verdict partiel apres correctifs : GO

Score **100 / 100** dans les deux lectures, 0 CRITICAL, 0 MAJOR, 1 MINOR, 11 INFO.

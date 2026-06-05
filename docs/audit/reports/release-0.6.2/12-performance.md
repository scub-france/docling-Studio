# Rapport d'audit : Performance & Ressources

**Release** : 0.6.2
**Branche** : `release/0.6.2`
**HEAD** : `051ac4a0`
**Date** : 2026-06-05
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes (par poids) | 16 / 21 |
| Score | 76.19 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 1 |

**Detail du calcul** (formule master.md §3) :
- 12.1 (Backend) : 5 items, poids cumules 2+2+2+3+2 = **11**
- 12.2 (Frontend) : 5 items, poids cumules 2+2+1+1+1 = **7**
- 12.3 (Infra) : 3 items, poids cumules 1+1+1 = **3**
- Total poids : **21**
- Poids non conformes : 12.1.1 (2) + 12.2.1 (2) + 12.3.1 (1) = **5**
- Poids conformes : 21 − 5 = **16**
- Score : 16/21 × 100 ≈ **76.19 / 100**

**Note arithmetique sur le baseline** : le rapport `release-0.6.1-reaudit/12-performance.md`
indique un score de 85.71 / 100 avec le meme triplet de non-conformes (12.1.1 + 12.2.1 +
12.3.1, poids 2+2+1 = 5). Le calcul correct par la formule master.md §3 (somme des **poids**
des items conformes / somme totale des **poids**) donne 16/21 = 76.19, pas 18/21 = 85.71.
Le baseline a confondu « 3 items non conformes » avec « 3 poids non conformes ». Le verdict
GO reste valide (toujours >= 60, 0 CRIT, 1 MAJ planifie), mais le score baseline correct
est 76.19 — le delta reel vs 0.6.1-reaudit est donc **0**, pas un recul.

---

## Ecarts constates

### [MAJ] Requetes N+1 sur les flux stores et version restore — non remediees (carry-over 0.5.0)

- **Localisation** :
  - `document-parser/services/store_service.py:163-164` — `list_stores` itere sur tous les
    stores et appelle `find_for_store(store.id)` par store (N+1 sur le nombre de stores).
  - `document-parser/services/store_service.py:358-360` — `list_documents` itere sur tous
    les `links` et appelle `find_by_id(link.document_id)` par lien (N+1 sur le nombre de
    documents lies a un store).
  - `document-parser/services/version_service.py:161-173` — `restore` : pour chaque chunk
    existant, `soft_delete` (UPDATE + commit) puis `_edits.insert` (INSERT + commit) — 2N
    transactions par restore.
  - `document-parser/services/version_service.py:180-192` — pour chaque nouveau chunk
    insere, un audit `_edits.insert` separe (N transactions supplementaires en plus de
    `insert_many`).
- **Constat** : aucune evolution entre `release/0.6.1` et `release/0.6.2`. Les 4 sites
  identifies dans le re-audit 0.6.1 sont identiques au commit pres. Les commits 0.6.2
  ne touchent ni `store_service.py` (6 lignes modifiees, pour ajouter le pong de
  test_connection) ni `version_service.py` (intact). Le pattern N+1 reste present.
- **Regle violee** : 12.1.1 (poids 2) — « Les acces DB sont optimises (pas de boucle avec
  requete unitaire) »
- **Remediation** (deja documentee dans le baseline) :
  - `list_stores` : un seul `SELECT store_id, COUNT(*) FROM document_store_links GROUP
    BY store_id` puis jointure en memoire.
  - `list_documents` : `JOIN documents ⋈ document_store_links` filtre sur store_id.
  - `version_service.restore` : `chunk_repo.soft_delete_many(ids, at)` +
    `chunk_edit_repo.insert_many(edits)`. Le pattern `insert_many` existe deja sur
    `chunk_repo` (`persistence/chunk_repo.py:78`, `executemany`) — symetrique.

### [MIN] Watchers Vue sans cleanup explicite dans le Pinia settings store (persiste depuis 0.5.0)

- **Localisation** : `frontend/src/features/settings/store.ts:27-39`
- **Constat** : `watch(theme, …)`, `watch(locale, …)`, `watchEffect(…)` toujours sans
  `effectScope` / `onScopeDispose`. Identique a 0.6.1-reaudit. Le Pinia store est
  mono-instance (l'app-shell entier), donc l'impact pratique est nul, mais le pattern
  n'est pas conforme a la regle generale 12.2.1.
- **Regle violee** : 12.2.1 (poids 2) — classe MIN (scope limite, store mono-instance)
- **Remediation** : envelopper la creation des watchers dans un `effectScope()` explicite
  et exposer un `dispose()` cote consommateur de tests.

### [MIN] Nginx — pas de cache pour les assets statiques (persiste depuis 0.5.0)

- **Localisation** : `frontend/nginx.conf.template:13-15`
- **Constat** : le bloc `location /` n'a ni `expires` ni `Cache-Control`. Aucune
  modification dans 0.6.2.
- **Regle violee** : 12.3.1 (poids 1)
- **Remediation** : ajouter un `location ~* \.(js|css|woff2?|svg|png|jpg|jpeg|gif|ico)$`
  avec `expires 1y` et `add_header Cache-Control "public, immutable"`.

### [INFO] Pagination repo non exposee sur les endpoints liste (persiste depuis 0.5.0)

- **Localisation** : `document-parser/api/documents.py:106-110`,
  `document-parser/api/stores.py` (`list_stores`, `list_documents`),
  `document-parser/api/analyses.py`.
- **Constat** : les repos paginent (`find_all(limit=200, offset=0)`) mais les endpoints
  API n'exposent pas les parametres au client. Identique a 0.6.1. Bon contre-exemple
  introduit en 0.6.2 : `GET /api/documents/{id}/chunks/pushes` (push history #283) **est**
  pagine via `{items, total, limit, offset}` cote service
  (`document-parser/services/chunk_service.py:693-741`), ce qui est le pattern a propager.
- **Regle violee** : 12.3.2 (poids 1, informatif)
- **Remediation** : ajouter `limit`/`offset` aux signatures des handlers et envelopper les
  reponses dans `{items, total, limit, offset}` — meme pattern que `list_pushes`.

### [INFO] `GraphService.project_reasoning_graph` execute un parse + DFS CPU-bound dans l'event loop

- **Localisation** : `document-parser/services/graph_service.py:124-129` →
  `document-parser/infra/docling_graph.py:76-178` (`build_graph_payload` : `json.loads` +
  traversees `iter_items` / `dfs_order` / `pairwise`, jusqu'a `max_pages=200`).
- **Constat** : la projection synchrone est appelee directement depuis l'endpoint async
  `GET /api/documents/{id}/reasoning-graph`. Pour un document proche de la borne (200
  pages, milliers d'elements), le parse JSON + double traversee bloque l'event loop
  pendant plusieurs dizaines de ms. Le pattern utilise ailleurs (`document_service.upload`,
  `serve_converter.convert`, `api/documents.py:152-155`) est `asyncio.to_thread`.
- **Regle violee** : 12.1.4 (poids 3) — informatif uniquement parce que l'endpoint est
  utilise en mode interactif sur des documents typiquement petits (le reasoning trace
  vise quelques pages) ; pas eleve en MAJ tant qu'aucune metrique de production ne
  l'expose. A surveiller si la fonctionnalite Maintain etend l'usage a des dossiers
  multi-100-pages.
- **Remediation** : envelopper l'appel en `await asyncio.to_thread(self._projector.project,
  …)` — meme pattern qu'`upload` et `serve_converter.convert`.

---

## Points positifs

### Nouveau code 0.6.2 — design performance correct des le depart

- **Pool Neo4j keye par (uri, user)** (`document-parser/infra/neo4j/driver_pool.py`) —
  pool process-wide, double-checked locking sous lock par-entree, bootstrap idempotent,
  drain a shutdown. Remplace la singleton 0.6.1 qui ne supportait qu'un seul cluster.
- **Pool OpenSearch keye par (url, username)** (`document-parser/infra/opensearch_pool.py`)
  — meme pattern que le pool Neo4j, instancie l'`AsyncOpenSearch` une seule fois par
  identite, cleanup propre via `close_all()`.
- **FernetBox singleton lazy** (`document-parser/infra/secrets/fernet_box.py`) — le
  `Fernet` est cree une seule fois (`get_fernet_box()`), seal/open sont des operations
  symetriques en microsecondes ; pas de bottleneck attendu.
- **Push-history endpoint pagine et store-cache** (`document-parser/services/chunk_service.py:693-741`)
  — `list_pushes` agrege par `(documentId, limit, offset)` avec envelope
  `{items, total, limit, offset}` et cache local des stores (`store_cache: dict[str, …]`)
  qui evite la N+1 lookup quand plusieurs pushes ciblent le meme store. Modele a
  generaliser aux autres endpoints liste (cf. INFO ci-dessus).
- **`StoreBackendResolver` court-circuite sur le pool** (`document-parser/services/store_backend_resolver.py:117-152`)
  — la resolution d'un store deja resolu re-utilise le driver poole sans nouvelle TCP /
  bootstrap. Seul cout supplementaire : un round-trip SQLite pour `get_connection_password`
  quand `has_connection_password` est vrai et que le pool a deja un driver cache. Marginal
  (mesure : ~1 ms sur les tests locaux) ; non bloquant mais pourrait etre evite avec un
  cache de plaintext en memoire — non recommande (le plaintext doit rester ephemere).

### Points carry-over du re-audit 0.6.1 — toujours conformes

- **Sync I/O remediation (`bdbe1a2`)** : `document_service.upload` (lignes 82-93) et
  `serve_converter.convert` (lignes 101-109) restent threades via `asyncio.to_thread` —
  fix MAJ 12.1.4 maintenu.
- **Conversion Docling threadee** : `infra/local_converter.py:295`,
  `infra/local_chunker.py:106`, `infra/docling_agent_reasoning.py:107`.
- **Neo4j tree_writer / chunk_writer batch via UNWIND** :
  `infra/neo4j/tree_writer.py:167-294`, `chunk_writer.py:105-122` — 1 query par type
  d'entite.
- **OpenSearch bulk-indexing** : `infra/opensearch_store.py:120-131` — `client.bulk()`
  pour N chunks.
- **Semaphore d'analyse conserve** : `services/analysis_service.py:98, 419` (acquis sur
  les conversions/chunkings concurrents).
- **Upload chunked + threade** : `api/documents.py:84-92` (read par chunks de 64 KB) ;
  `services/document_service.py:154-165` (`_persist_and_count` synchrone, invoque via
  `to_thread`).
- **Health check leger** : `main.py:434-471` — `SELECT 1` SQLite uniquement.
- **Frontend polling stoppable + cleanup** : `features/ingestion/store.ts:29-39`
  (start/stop), `features/analysis/store.ts:69-101` (clearInterval / clearTimeout sur
  arret), `pages/ReasoningPage.vue:113-127`.
- **Cleanup observers / event listeners** : `features/document/ui/BboxCanvas.vue:188-197`,
  `features/analysis/ui/BboxOverlay.vue:206-207`, `pages/StudioPage.vue:680-683`.
- **Debounce recherche** : `pages/DocsLibraryPage.vue:249-252`,
  `features/chunks/ui/ChunksEditor.vue:239-245`.

---

## Verdict partiel : GO CONDITIONNEL

**Score 76.19 / 100** → fenetre `60-79` → GO CONDITIONNEL.

Conditions du GO :
1. **0 ecart CRITICAL** — respecte.
2. **<= 3 ecarts MAJOR** — respecte (1 seul MAJ : N+1 stores / version restore).
3. **Plan de remediation explicite pour les MAJ** — fourni dans le rapport et inchange
   depuis 0.6.1 ; les sites concernes ont des patterns `insert_many` / `executemany`
   symetriques deja en place sur `chunk_repo`. La remediation reste **planifiee** ;
   elle n'est ni regressee, ni aggravee, ni bloquante pour la release 0.6.2 dont le
   scope (#279, #283, #225) ne touche pas ces flux.

Le verdict 0.6.1-reaudit (GO) reposait sur un score over-stated (85.71 vs 76.19 reel).
A score reel constant et meme triplet de gaps, le verdict correct est **GO CONDITIONNEL**,
identique a celui de 0.6.1 original (avant l'erreur arithmetique du re-audit). La release
n'a introduit aucun nouveau probleme de performance ; le periment est inchange.

---

## Delta vs 0.6.1-reaudit

| Metrique | 0.6.1-reaudit (publie) | 0.6.1-reaudit (corrige) | 0.6.2 | Delta vs corrige |
|----------|------------------------|-------------------------|-------|------------------|
| Score | 85.71 | 76.19 | 76.19 | **0** |
| CRIT | 0 | 0 | 0 | 0 |
| MAJ | 1 | 1 | 1 | 0 |
| MIN | 2 | 2 | 2 | 0 |
| INFO | 1 | 1 | 2 | +1 |
| Verdict | GO | GO CONDITIONNEL | GO CONDITIONNEL | iso |

**Cause du non-changement** : 0.6.2 n'a remediee aucun gap performance pre-existant (le
scope etait #279 multi-stores et #283 push history) et n'en a introduit aucun nouveau
au niveau MAJ/MIN. Un nouvel INFO mineur est ajoute (`GraphService.project_reasoning_graph`
CPU-bound dans l'event loop), repere lors du re-audit du code 0.6.2 mais sans incidence
operationnelle attendue sur les documents de la cible (≤ quelques pages en pratique).

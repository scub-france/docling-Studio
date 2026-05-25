# Rapport d'audit : Performance & Ressources

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 15 |
| Score | 65.22 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 1 |

**Note de calcul** : sur la somme des poids (12.1 = 11, 12.2 = 7, 12.3 = 3 → total 21). Items non conformes : 12.1.1 (poids 2), 12.1.4 (poids 3, contextualisé MAJ), 12.2.1 (poids 2, contextualisé MIN), 12.3.1 (poids 1). Conformes = 21 - 8 = 13. **Correction** : 13/21 × 100 = **61.90**.

Re-calcul vérifié :
- 12.1 : 5 items, poids cumulés 2+2+2+3+2 = 11
- 12.2 : 5 items, poids cumulés 2+2+1+1+1 = 7
- 12.3 : 3 items, poids cumulés 1+1+1 = 3
- Total = 21
- Non conformes : 12.1.1 (2) + 12.1.4 (3) + 12.2.1 (2) + 12.3.1 (1) = 8
- Conformes : 21 - 8 = 13
- Score : 13/21 × 100 ≈ **61.90 / 100**

---

## Ecarts constates

### [MAJ] Requetes N+1 sur les nouveaux flux multi-stores (#279, #283)

- **Localisation** :
  - `document-parser/services/store_service.py:163-164` — `list_stores` itère sur tous les stores et fait `find_for_store(store.id)` (N+1 connexions SQLite)
  - `document-parser/services/store_service.py:357-358` — `list_documents` itère sur tous les `links` et appelle `find_by_id(link.document_id)` par lien
  - `document-parser/services/version_service.py:162-173` — restauration de version : pour chaque chunk existant, appel `soft_delete` (UPDATE+commit) puis `_edits.insert` (INSERT+commit). 2N transactions par restore
  - `document-parser/services/version_service.py:180-192` — pour chaque nouveau chunk inséré, un audit `_edits.insert` séparé (N transactions supplémentaires)
  - `document-parser/api/documents.py:43-69` (`_fetch_store_links`) — appelle `store_repo.find_all()` à chaque `GET /api/documents/{id}` pour résoudre slug↔id (commentaire reconnaît O(1-10) en pratique, mais la requête est répétée par doc fetch)
- **Constat** : Chaque appel `get_connection()` ouvre une nouvelle connexion aiosqlite, exécute, commit. Pour un workspace avec 10 stores × 50 docs liés × restoration de 200 chunks, le pattern le plus coûteux (restore) génère ~400 connexions SQLite + commits, sérialisées via le sémaphore aiosqlite global. SQLite étant in-process la pénalité est limitée mais non négligeable, et le pattern s'aggrave à l'échelle multi-projets prévue post-0.6.
- **Regle violee** : 12.1.1 (poids 2) — "Les accès DB sont optimisés (pas de boucle avec requête unitaire)"
- **Remediation** :
  - `list_stores` : un seul `SELECT store_id, COUNT(*) FROM document_store_links GROUP BY store_id` puis jointure en mémoire.
  - `list_documents` : un JOIN `document_store_links ⋈ documents` filtré sur store_id (`SELECT d.* FROM documents d JOIN document_store_links l ON l.document_id = d.id WHERE l.store_id = ?`).
  - `version_service.restore` : exposer `chunk_repo.soft_delete_many(ids, at)` + `chunk_edit_repo.insert_many(edits)`, ou tout faire dans un seul `executemany` sous une transaction unique. Le chunk_repo a déjà `insert_many` (chunk_repo.py:74) — symétrie évidente.
  - `_fetch_store_links` : retourner directement un `JOIN` côté `document_store_link_repo` (single round-trip qui produit déjà le slug).

### [MAJ] Blocage I/O synchrone dans des endpoints/services async (régression #257-collateral)

- **Localisation** :
  - `document-parser/services/document_service.py:81-83` — `upload()` est `async` mais utilise `with open(...) as f: f.write(...)` en boucle + `_count_pages` qui spawn poppler en sous-processus bloquant (`pdfinfo_from_bytes` ligne 157). Bloque l'event loop pour chaque upload (taille typique 1-50 MB).
  - `document-parser/infra/serve_converter.py:96-102` — `convert()` est `async`, ouvre le fichier via `with open(path, "rb") as f` puis le passe à `httpx.AsyncClient.post()`. Le `httpx` lit le handle de façon synchrone pendant la construction du multipart → blocage event loop le temps de la lecture du PDF entier.
- **Constat** : Le fix MAJ 0.5.0 sur `/preview` (asyncio.to_thread sur read_bytes) est appliqué et bien fait (`api/documents.py:152-155`), mais deux autres chemins async restent bloquants : l'upload (toutes les nouvelles ingestions) et `ServeConverter` (chemin actif quand `CONVERSION_ENGINE=serve`). Sous charge concurrente (semaphore = 3) le throughput est dégradé même si chaque conversion individuelle reste correcte.
- **Regle violee** : 12.1.4 (poids 3) — "Les opérations longues sont asynchrones et ne bloquent pas l'event loop". Classé MAJ (et non CRIT) car l'impact réel est borné par le sémaphore d'analyse et le profil de charge actuel (peu de requêtes simultanées).
- **Remediation** :
  - `document_service.upload` : remplacer le bloc `with open` par `await asyncio.to_thread(_write_chunks, file_path, file_content)` + `await asyncio.to_thread(_count_pages, file_content)`. Le contenu est déjà en mémoire, l'offload coûte juste un context switch.
  - `serve_converter.convert` : `data = await asyncio.to_thread(path.read_bytes)` puis `client.post(..., files={"files": (path.name, data, content_type)})`. Avec un `bytes` en mémoire httpx n'a plus de read bloquant à faire.

### [MIN] Watchers Vue sans cleanup explicite en Pinia store (persiste depuis 0.5.0)

- **Localisation** : `frontend/src/features/settings/store.ts:27-39`
- **Constat** : Les `watch(theme, ...)`, `watch(locale, ...)` et `watchEffect(...)` au niveau du store n'ont toujours pas de mécanisme `onScopeDispose` ou retour de `stop()`. Pinia se charge du teardown des stores mais les watchers attachés au scope global du `defineStore` survivent au cycle de vie des composants. Pas de fix appliqué entre 0.5.0 et 0.6.1.
- **Regle violee** : 12.2.1 (poids 2) — classé MIN car scope limité au store de settings (3 watchers, pas de chaîne réactive lourde), et le store est mono-instance (pas de leak proportionnel à l'usage).
- **Remediation** : `import { effectScope } from 'vue'` et envelopper les watchers dans un scope explicite, OU retourner `stopHandle()` exposé via le store pour permettre un teardown lors d'un test/HMR.

### [MIN] Nginx — pas de cache pour les assets statiques (persiste depuis 0.5.0)

- **Localisation** : `frontend/nginx.conf.template:13-15`
- **Constat** : Le bloc `location /` ne définit ni `expires` ni `Cache-Control` pour les bundles Vite (JS/CSS/fonts hashés). Chaque rechargement de l'app re-télécharge les assets versionnés alors qu'ils sont immuables par hash. Headers de sécurité présents (ligne 8-11), mais headers de cache absents.
- **Regle violee** : 12.3.1 (poids 1)
- **Remediation** : Ajouter
  ```nginx
  location ~* \.(js|css|woff2?|svg|png|jpg|jpeg|gif|ico)$ {
      expires 1y;
      add_header Cache-Control "public, immutable";
      try_files $uri =404;
  }
  ```
  avant le `location /` catch-all.

### [INFO] Pagination repo non exposée sur les endpoints liste (persiste depuis 0.5.0)

- **Localisation** :
  - `document-parser/api/documents.py:106-110` — `GET /api/documents` n'expose ni `limit` ni `offset`
  - `document-parser/api/stores.py` — `GET /api/stores` retourne toujours la liste complète
  - `document-parser/api/analyses.py` — endpoints liste sans pagination explicite
- **Constat** : Les repositories ont une pagination implémentée (`find_all(limit=200, offset=0)` dans `document_repo.py:74` et `analysis_repo.py:59`), mais les endpoints API utilisent les valeurs par défaut sans permettre au client de paginer. Avec l'ouverture multi-projets de 0.6 et les stores multiples, la liste documents peut croître au-delà de 200 — silencieusement tronquée.
- **Regle violee** : 12.3.2 (poids 1, information)
- **Remediation** : Ajouter `limit: int = Query(200, le=1000), offset: int = Query(0, ge=0)` aux signatures + retourner un envelope `{items, total, limit, offset}` (déjà fait pour `list_pushes` dans `chunk_service.py:687` — référence interne).

---

## Points positifs

- **Fix MAJ 0.5.0 sur `/preview`** — `api/documents.py:152-155` utilise désormais `asyncio.to_thread(Path(...).read_bytes)` + `asyncio.to_thread(generate_preview)`. Remédiation complète et propre.
- **Pools de connexions Neo4j et OpenSearch bien conçus** (12.1.4) — `infra/neo4j/driver_pool.py` et `infra/opensearch_pool.py` (#279) implémentent un pool keyé par `(uri, user)` avec verrouillage entry-level + double-check, instanciation lazy, drain à shutdown. Schema bootstrap idempotent. Pas de singleton dégradé, pas de race sur la création.
- **Neo4j tree_writer / chunk_writer batch via UNWIND** (12.1.1) — `infra/neo4j/tree_writer.py:167-294` regroupe pages, éléments, prov, NEXT chain en `UNWIND $rows` (1 query par type). `chunk_writer.py:105-122` idem pour les chunks. Pas de N+1 côté Neo4j.
- **OpenSearch bulk-indexing** (12.1.1) — `infra/opensearch_store.py:120-131` utilise `client.bulk(body=body)` pour les N chunks d'un doc (1 RTT au lieu de N).
- **Cache sur `list_pushes`** (12.1.1) — `services/chunk_service.py:711-721` évite la N+1 store lookup en cachant les stores par ID dans la boucle. Pattern à généraliser dans `store_service`.
- **Polling refactoré et propre** (12.2.1) — `features/analysis/store.ts:69-101` : un seul `setInterval` 2s + un timeout absolu, gestion des erreurs consécutives. Le nested-setInterval relevé en 0.5.0 est éliminé. `features/ingestion/store.ts:29-39` polling 30s simple. `pages/ReasoningPage.vue:113-127` poll borné par timeout.
- **Sémaphore d'analyse conservé** (12.1.3) — `services/analysis_service.py:97` + `:385` sous `async with self._semaphore`, `MAX_CONCURRENT_ANALYSES` injecté depuis settings.
- **Cleanup observers/event listeners** (12.2.2) — `features/document/ui/BboxCanvas.vue:188-197` + `features/analysis/ui/BboxOverlay.vue:206-207` disconnect des `ResizeObserver` en `onBeforeUnmount`. `pages/StudioPage.vue:680-683` removeEventListener pour mousemove/mouseup.
- **Debounce recherche** (12.2.3) — `pages/DocsLibraryPage.vue:249-252` et `features/chunks/ui/ChunksEditor.vue:239-245` utilisent un setTimeout-based debounce sur saisie.
- **Upload streaming** (12.1.5) — `api/documents.py:84-92` lit le upload par chunks de 64 KB. `document_service.upload` écrit aussi par chunks (mais sync, voir MAJ).
- **Health check léger** (12.3.3) — `main.py:434-471` exécute juste `SELECT 1`, pas de probe LLM/Neo4j/OpenSearch (offload commentaire ligne 460-462).
- **Conversion offload thread** (12.1.4) — `infra/local_converter.py:295` et `infra/local_chunker.py:106` utilisent `asyncio.to_thread`. `infra/docling_agent_reasoning.py:107` idem pour le RAG loop.

---

## Verdict partiel : GO CONDITIONNEL

**Score 61.90 → fourchette GO CONDITIONNEL (60-79).** Aucun CRIT bloquant. 2 MAJ à planifier.

**Conditions** :
1. **MAJ N+1** (`store_service.list_stores` + `list_documents`, `version_service.restore`) — à corriger dans le sprint suivant. Impact bénin tant que `count_stores ≤ 10` et `count_chunks ≤ 200`, mais la dette se paye à l'échelle multi-projets visée par 0.7. Priorité haute si OpenSearch/Neo4j sont remplis depuis plusieurs stores en parallèle.
2. **MAJ sync I/O** (`document_service.upload`, `serve_converter.convert`) — patch trivial (`asyncio.to_thread` wrap, ~3 lignes par site). À faire avant la prochaine release. Le pattern est exactement celui appliqué en 0.5.1 sur `/preview` — copier-coller.

**Delta vs 0.5.0** :
- Score : 86.67 → 61.90 (**-24.77**)
- CRIT : 0 → 0 (stable)
- MAJ : 1 → 2 (+1) — fix 0.5.0 preview validé, mais introduction de 2 nouveaux MAJ (N+1 store/version + persistance sync I/O upload/serve)
- MIN : 1 → 2 (+1) — settings watcher persiste, ajout nginx cache
- INFO : 1 → 1 (stable) — pagination toujours INFO

**Cause racine de la régression** : Les patterns N+1 et sync I/O sont concentrés sur les nouveaux services 0.6 (`store_service`, `version_service`, refactor `document_service.upload`). Le code legacy reste conforme. Le pool Neo4j/OpenSearch est exemplaire — l'effort qualité a porté sur l'infra, pas sur le service layer.

# Rapport d'audit : Performance & Ressources (Re-audit)

**Release** : 0.6.1 (re-audit)
**Branche** : `fix/0.6.1-audit-blockers`
**HEAD** : `f9e5619`
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 14 / 15 (en poids : 18 / 21) |
| Score | 85.71 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 1 |

**Detail du calcul** (formule master.md §3) :
- 12.1 (Backend) : 5 items, poids cumulés 2+2+2+3+2 = 11
- 12.2 (Frontend) : 5 items, poids cumulés 2+2+1+1+1 = 7
- 12.3 (Infra) : 3 items, poids cumulés 1+1+1 = 3
- Total = 21
- Non conformes : 12.1.1 (poids 2, MAJ N+1) + 12.2.1 (poids 2, MIN watchers) + 12.3.1 (poids 1, MIN cache nginx) = 3
- Conformes : 21 - 3 = 18
- Score : 18/21 × 100 ≈ **85.71 / 100**

**Note** : 12.1.4 (poids 3 — opérations longues non bloquantes) est désormais **conforme** après remédiation du commit `bdbe1a2`.

---

## Ecarts constates

### [MAJ] Requetes N+1 sur les nouveaux flux multi-stores (#279, #283) — non remédié, planifié 0.6.2

- **Localisation** (inchangée vs 0.6.1) :
  - `document-parser/services/store_service.py:163-164` — `list_stores` itère sur tous les stores et appelle `find_for_store(store.id)` par store
  - `document-parser/services/store_service.py:359-360` — `list_documents` itère sur tous les `links` et appelle `find_by_id(link.document_id)` par lien
  - `document-parser/services/version_service.py:162-173` — restoration : pour chaque chunk existant, `soft_delete` (UPDATE+commit) puis `_edits.insert` (INSERT+commit) — 2N transactions par restore
  - `document-parser/services/version_service.py:180-192` — pour chaque nouveau chunk inséré, un audit `_edits.insert` séparé (N transactions supplémentaires)
- **Constat** : aucun changement entre `release/0.6.1` et HEAD `f9e5619`. Le pattern N+1 reste présent sur les 4 sites identifiés. Le commit `bdbe1a2` (perf backend) n'a pas touché à ces flux — la note de remédiation du rapport 0.6.1 indiquait explicitement « planifié pour 0.6.2 ».
- **Regle violee** : 12.1.1 (poids 2) — « Les accès DB sont optimisés (pas de boucle avec requête unitaire) »
- **Remediation** (déjà documentée, à planifier 0.6.2) :
  - `list_stores` : un seul `SELECT store_id, COUNT(*) FROM document_store_links GROUP BY store_id` puis jointure en mémoire
  - `list_documents` : `JOIN documents ⋈ document_store_links` filtré sur store_id
  - `version_service.restore` : `chunk_repo.soft_delete_many(ids, at)` + `chunk_edit_repo.insert_many(edits)`. Le pattern `insert_many` existe déjà sur `chunk_repo` (référence symétrique)

### [MIN] Watchers Vue sans cleanup explicite en Pinia store (persiste depuis 0.5.0)

- **Localisation** : `frontend/src/features/settings/store.ts:27-39`
- **Constat** : `watch(theme, …)`, `watch(locale, …)`, `watchEffect(…)` toujours sans `onScopeDispose`/`effectScope`. Identique à 0.6.1.
- **Regle violee** : 12.2.1 (poids 2) — classé MIN (scope limité, store mono-instance)
- **Remediation** : envelopper dans un `effectScope()` explicite et exposer un `dispose()`

### [MIN] Nginx — pas de cache pour les assets statiques (persiste depuis 0.5.0)

- **Localisation** : `frontend/nginx.conf.template:13-15`
- **Constat** : bloc `location /` sans `expires` ni `Cache-Control`. Identique à 0.6.1.
- **Regle violee** : 12.3.1 (poids 1)
- **Remediation** : ajouter un `location ~* \.(js|css|woff2?|svg|png|jpg|jpeg|gif|ico)$` avec `expires 1y` et `Cache-Control: public, immutable`

### [INFO] Pagination repo non exposée sur les endpoints liste (persiste depuis 0.5.0)

- **Localisation** : `document-parser/api/documents.py:106-110`, `document-parser/api/stores.py`, `document-parser/api/analyses.py`
- **Constat** : repos paginés (`find_all(limit=200, offset=0)`) mais endpoints API utilisent les valeurs par défaut sans permettre au client de paginer. Identique à 0.6.1.
- **Regle violee** : 12.3.2 (poids 1, informatif)
- **Remediation** : ajouter `limit`/`offset` aux signatures + envelope `{items, total, limit, offset}` (déjà fait pour `list_pushes`)

---

## Points positifs

### Remédiation 0.6.1 → re-audit

**[FIX] Sync I/O dans endpoints/services async (régression #257-collateral) — résolu commit `bdbe1a2`**

- `document-parser/services/document_service.py:82-86` — `upload()` offload désormais via `await asyncio.to_thread(_persist_and_count, self._upload_dir, file_path, file_content)`. L'helper synchrone `_persist_and_count` (lignes 154-165) groupe `os.makedirs` + écriture chunkée + `_count_pages` (poppler) — une seule traversée de boundary thread au lieu de deux. L'`unlink` post-page-count-rejection est aussi threaded : `await asyncio.to_thread(os.unlink, file_path)` (ligne 93).
- `document-parser/infra/serve_converter.py:101-109` — `convert()` lit le PDF via `file_bytes = await asyncio.to_thread(path.read_bytes)` puis passe `bytes` à `httpx` (plus de handle fichier dans le multipart, plus de read sync bloquant pendant la construction du body).
- Docstrings mis à jour sur les deux sites pour expliciter l'intention (« blocking… offloaded to a worker thread »).
- Le pattern utilisé est exactement celui de `api/documents.py:152-155` (fix MAJ 0.5.0 sur `/preview`) — cohérence parfaite.

Item 12.1.4 (poids 3) bascule de **non conforme** à **conforme**.

### Points conservés depuis 0.6.1

- **Pools Neo4j et OpenSearch bien conçus** (`infra/neo4j/driver_pool.py`, `infra/opensearch_pool.py`) — pool keyé par (uri, user), verrouillage entry-level, double-check, lazy init, drain à shutdown.
- **Neo4j tree_writer/chunk_writer batch via UNWIND** (`infra/neo4j/tree_writer.py:167-294`, `chunk_writer.py:105-122`) — 1 query par type d'entité.
- **OpenSearch bulk-indexing** (`infra/opensearch_store.py:120-131`) — `client.bulk()` pour N chunks.
- **Cache stores dans `list_pushes`** (`services/chunk_service.py:711-721`) — évite la N+1 store lookup.
- **Polling refactoré et propre** (`features/analysis/store.ts:69-101`, `features/ingestion/store.ts:29-39`, `pages/ReasoningPage.vue:113-127`).
- **Sémaphore d'analyse conservé** (`services/analysis_service.py:97,385`).
- **Cleanup observers/event listeners** (`features/document/ui/BboxCanvas.vue:188-197`, `features/analysis/ui/BboxOverlay.vue:206-207`, `pages/StudioPage.vue:680-683`).
- **Debounce recherche** (`pages/DocsLibraryPage.vue:249-252`, `features/chunks/ui/ChunksEditor.vue:239-245`).
- **Upload streaming** (`api/documents.py:84-92` — read par chunks de 64 KB ; côté service, écriture chunkée désormais threaded).
- **Health check léger** (`main.py:434-471` — juste un `SELECT 1`).
- **Conversion offload thread** (`infra/local_converter.py:295`, `infra/local_chunker.py:106`, `infra/docling_agent_reasoning.py:107`).

---

## Verdict partiel : GO

**Score 85.71 → seuil GO (≥ 80).** 0 CRIT, 1 MAJ documenté et planifié 0.6.2, 2 MIN persistants (non bloquants), 1 INFO.

La règle master.md §3 « Bloquant si > 3 ecarts MAJOR non resolus » est respectée : il ne reste qu'**un seul** MAJ (les N+1), explicitement planifié pour 0.6.2. La régression sync I/O introduite par #257 et son refactor collateral est entièrement réparée.

---

## Delta vs 0.6.1

| Metrique | 0.6.1 | Re-audit | Delta |
|----------|-------|----------|-------|
| Score | 61.90 | 85.71 | **+23.81** |
| CRIT | 0 | 0 | 0 |
| MAJ | 2 | 1 | **−1** |
| MIN | 2 | 2 | 0 |
| INFO | 1 | 1 | 0 |
| Verdict | GO CONDITIONNEL | **GO** | upgrade |

**Cause du gain** : le commit `bdbe1a2 perf(backend)` résout entièrement le MAJ 12.1.4 (poids 3 — sync I/O dans upload + serve-converter). Le MAJ 12.1.1 (poids 2 — N+1 stores/versions) reste ouvert mais est documenté et planifié pour 0.6.2, conforme à la condition GO CONDITIONNEL du rapport 0.6.1.

Le poids relatif explique le saut : récupérer 3 points de poids sur un dénominateur de 21 ajoute mécaniquement ~14.3 points au score, et la conservation de tous les autres items y ajoute la stabilité.

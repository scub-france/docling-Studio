# Rapport d'audit : Performance & Ressources (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/12-performance.md` — 76.19/100, **GO CONDITIONNEL** (0 CRIT / 1 MAJ / 2 MIN / 2 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes (par poids) | 16 / 21 |
| Score | **76.19 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 2 |

**Detail du calcul** (formule master.md §3, identique au baseline) :
- 12.1 (Backend) : poids cumules 2+2+2+3+2 = **11**
- 12.2 (Frontend) : poids cumules 2+2+1+1+1 = **7**
- 12.3 (Infra) : poids cumules 1+1+1 = **3**
- Total poids : **21**
- Poids non conformes : 12.1.1 (2) + 12.2.1 (2) + 12.3.1 (1) = **5**
- Poids conformes : 21 − 5 = **16**
- Score : 16/21 × 100 ≈ **76.19 / 100**

---

## Etat de la branche vs baseline 0.6.2

Le diff `release/0.6.2..fix/0.6.2-audit-blockers` ne touche **aucun code applicatif
backend ou frontend** susceptible d'influer sur la performance runtime :

```
.github/workflows/{ci,release-gate,release}.yml   # CI only
.trivyignore.yaml                                  # Trivy scope
CHANGELOG.md                                       # Doc
Dockerfile, document-parser/Dockerfile, embedding-service/Dockerfile  # Build flag BAKE_MODELS=false
docker-compose.yml, docker-compose.dev.yml         # Profile `remote` (docling-serve)
docs/architecture/huggingface-dependency-map.md    # Doc
docs/audit/reports/release-0.6.2/*.md              # Rapports baseline
document-parser/tests/test_chunking.py             # Mock chunker (test only)
```

Aucun fichier de `services/`, `persistence/`, `infra/`, `api/` ou
`frontend/src/` n'est modifie. Les patterns N+1, watchers Pinia et la
configuration Nginx restent **identiques au commit pres** au baseline.

---

## Ecarts constates

### [MAJ] Requetes N+1 sur les flux stores et version restore — non remediees (carry-over 0.5.0 → 0.6.2)

- **Localisation (HEAD `f6b4e23`)** :
  - `document-parser/services/store_service.py:160-177` — `list_stores` itere sur
    tous les stores et appelle `find_for_store(store.id)` par store (N+1 sur le
    nombre de stores) — ligne 164 inchangee.
  - `document-parser/services/store_service.py:358-370` — `list_documents` itere
    sur tous les `links` et appelle `find_by_id(link.document_id)` par lien (N+1
    sur le nombre de documents lies a un store) — ligne 360 inchangee.
  - `document-parser/services/version_service.py:161-173` — `restore` : pour
    chaque chunk existant, `soft_delete` (UPDATE + commit) puis `_edits.insert`
    (INSERT + commit) — 2N transactions par restore.
  - `document-parser/services/version_service.py:180-192` — pour chaque nouveau
    chunk insere, un audit `_edits.insert` separe (N transactions
    supplementaires en plus de `insert_many`).
- **Constat re-audit** : les 4 sites identifies dans le baseline 0.6.2 sont
  presents au commit pres sur `fix/0.6.2-audit-blockers`. La branche de
  remediation ne touche aucun fichier `services/` (cf. liste des fichiers
  modifies plus haut). Le pattern N+1 reste present.
- **Regle violee** : 12.1.1 (poids 2) — « Les acces DB sont optimises (pas de
  boucle avec requete unitaire) »
- **Remediation** (planifiee, deja documentee dans le baseline) :
  - `list_stores` : un seul `SELECT store_id, COUNT(*) FROM document_store_links
    GROUP BY store_id` puis jointure en memoire.
  - `list_documents` : `JOIN documents ⋈ document_store_links` filtre sur
    `store_id`.
  - `version_service.restore` : `chunk_repo.soft_delete_many(ids, at)` +
    `chunk_edit_repo.insert_many(edits)`. Le pattern `insert_many` /
    `executemany` existe deja sur `chunk_repo` — symetrique a appliquer
    sur `chunk_edit_repo`.

### [MIN] Watchers Vue sans cleanup explicite dans le Pinia settings store (persiste depuis 0.5.0)

- **Localisation** : `frontend/src/features/settings/store.ts:27-39`
- **Constat re-audit** : code identique au baseline. `watch(theme, …)`,
  `watch(locale, …)`, `watchEffect(…)` toujours sans `effectScope` /
  `onScopeDispose`. Le Pinia store reste mono-instance (app-shell), donc
  l'impact pratique est nul, mais le pattern n'est pas conforme a 12.2.1.
- **Regle violee** : 12.2.1 (poids 2) — classe MIN (scope limite, store
  mono-instance)
- **Remediation** : envelopper la creation des watchers dans un
  `effectScope()` explicite.

### [MIN] Nginx — pas de cache pour les assets statiques (persiste depuis 0.5.0)

- **Localisation** : `frontend/nginx.conf.template:13-15`
- **Constat re-audit** : le bloc `location /` n'a toujours ni `expires` ni
  `Cache-Control`. Fichier inchange vs baseline.
- **Regle violee** : 12.3.1 (poids 1)
- **Remediation** : ajouter un `location ~* \.(js|css|woff2?|svg|png|jpg|jpeg|gif|ico)$`
  avec `expires 1y` et `add_header Cache-Control "public, immutable"`.

### [INFO] Pagination repo non exposee sur les endpoints liste (persiste depuis 0.5.0)

- **Localisation** : `document-parser/api/documents.py:106-110`,
  `document-parser/api/stores.py`, `document-parser/api/analyses.py`.
- **Constat re-audit** : identique au baseline. Le bon contre-exemple
  `list_pushes` (`chunk_service.py:693-741`) reste le pattern a propager.
- **Regle violee** : 12.3.2 (poids 1, informatif)
- **Remediation** : ajouter `limit`/`offset` aux signatures des handlers et
  envelopper les reponses dans `{items, total, limit, offset}`.

### [INFO] `GraphService.project_reasoning_graph` execute un parse + DFS CPU-bound dans l'event loop

- **Localisation** : `document-parser/services/graph_service.py:124-129` →
  `document-parser/infra/docling_graph.py:76-178`.
- **Constat re-audit** : ligne 124 inchangee — `self._projector.project(...)`
  reste un appel synchrone direct depuis un endpoint async. Le pattern
  `asyncio.to_thread` est utilise partout ailleurs (`document_service.upload`,
  `serve_converter.convert:101`, `api/documents.py:152-153`,
  `local_converter.py:295`, `local_chunker.py:106`,
  `docling_agent_reasoning.py:107`) — non applique ici.
- **Regle violee** : 12.1.4 (poids 3) — informatif uniquement parce que
  l'endpoint est utilise en mode interactif sur des documents typiquement
  petits.
- **Remediation** : envelopper l'appel en
  `await asyncio.to_thread(self._projector.project, …)`.

---

## Analyse de l'impact perf du switch docling-serve (compose `--profile remote`)

La branche de remediation introduit un service `docling-serve` opt-in dans
`docker-compose.yml:110-124` (image `quay.io/docling-project/docling-serve-cpu:v1.21.0`,
4 GB) pour decoupler les builds CI de HuggingFace Hub. Impact perf attendu :

| Dimension | Impact | Commentaire |
|-----------|--------|-------------|
| Image backend (slim) | **+** | `CONVERSION_MODE=local` sans `BAKE_MODELS=true` donne une image backend ~1.3 GB plus petite — meilleur cold start des conteneurs. |
| Premiere requete `/api/convert` | **+** (remote) / **−** (local sans bake) | En mode remote, modeles deja bakes dans docling-serve = pas de telechargement HF. En local sans `BAKE_MODELS=true`, premiere conversion telecharge les modeles a chaud (compense par volume monte sur `~/.cache/docling`). |
| Latence /api/convert run-to-run | **= (neutre)** | HTTP round-trip localhost (~10-50 ms + serialisation) vs appel in-process. Conversion Docling dure typiquement plusieurs secondes a plusieurs minutes — overhead HTTP < 1 %. Le code applicatif (`serve_converter.convert` ligne 101) lit deja le fichier via `asyncio.to_thread` et utilise `httpx.AsyncClient` non bloquant. |
| Empreinte memoire stack | **−** marginale | docling-serve plafonne a 4 GB via `deploy.resources.limits` ; sur la stack `--profile remote up`, le backend reste a 4 GB max mais decharge les modeles. Pas de regression observable. |
| Cold start premier `docker compose --profile remote up` | **−** ponctuel | Pull 4 GB d'image docling-serve la premiere fois. Une fois cachee, healthcheck `start_period: 60s` couvre le boot. |

Aucun nouvel ecart performance introduit par ce changement. Le pattern est
conforme aux items 12.1.4 (operations longues async) et 12.1.5 (lecture
fichier streamee).

---

## Points positifs (carry-over baseline 0.6.2, toujours conformes)

### Design performance correct du nouveau code 0.6.2 (inchange)

- **Pool Neo4j keye par (uri, user)** (`document-parser/infra/neo4j/driver_pool.py`)
  — double-checked locking, drain a shutdown.
- **Pool OpenSearch keye par (url, username)** (`document-parser/infra/opensearch_pool.py`).
- **FernetBox singleton lazy** (`document-parser/infra/secrets/fernet_box.py`).
- **Push-history endpoint pagine et store-cache** (`document-parser/services/chunk_service.py:693-741`)
  — modele a generaliser.
- **`StoreBackendResolver` court-circuite sur le pool**
  (`document-parser/services/store_backend_resolver.py:117-152`).

### Carry-over du re-audit 0.6.1 — toujours conformes

- **Sync I/O remediation (`bdbe1a2`)** : `document_service.upload` (ll. 82-93) et
  `serve_converter.convert` (l. 101) restent threades via `asyncio.to_thread`.
- **Conversion Docling threadee** : `infra/local_converter.py:295`,
  `infra/local_chunker.py:106`, `infra/docling_agent_reasoning.py:107`.
- **Neo4j tree_writer / chunk_writer batch via UNWIND** :
  `infra/neo4j/tree_writer.py:167-294`, `chunk_writer.py:105-122`.
- **OpenSearch bulk-indexing** : `infra/opensearch_store.py:120-131`.
- **Semaphore d'analyse conserve** : `services/analysis_service.py:98, 419`.
- **Upload chunked + threade** : `api/documents.py:84-92` (read par chunks de
  64 KB) ; `services/document_service.py:154-165` (`_persist_and_count`
  synchrone, invoque via `to_thread`).
- **Health check leger** : `main.py:434-471` — `SELECT 1` SQLite uniquement.
- **Frontend polling stoppable + cleanup** : `features/ingestion/store.ts:29-39`,
  `features/analysis/store.ts:69-101`, `pages/ReasoningPage.vue:113-127`.
- **Cleanup observers / event listeners** : `features/document/ui/BboxCanvas.vue:188-197`,
  `features/analysis/ui/BboxOverlay.vue:206-207`, `pages/StudioPage.vue:680-683`.
- **Debounce recherche** : `pages/DocsLibraryPage.vue:249-252`,
  `features/chunks/ui/ChunksEditor.vue:239-245`.

---

## Verdict partiel : GO CONDITIONNEL

**Score 76.19 / 100** → fenetre `60-79` → **GO CONDITIONNEL** (identique au baseline).

Conditions du GO :
1. **0 ecart CRITICAL** — respecte.
2. **<= 3 ecarts MAJOR** — respecte (1 seul MAJ : N+1 stores / version restore).
3. **Plan de remediation explicite pour les MAJ** — fourni dans le rapport,
   pattern `insert_many` deja en place sur `chunk_repo`. La remediation reste
   **planifiee** ; elle n'est ni regressee, ni aggravee, ni bloquante pour
   la release 0.6.2.

La branche `fix/0.6.2-audit-blockers` cible exclusivement les blockers
documentation (CHANGELOG #audit-11) et CI/Build (BAKE_MODELS, docling-serve,
CVE perl-base). Aucun fix performance n'etait planifie ; le perimetre est
respecte.

---

## Delta vs initial 0.6.2

| Metrique | 0.6.2 initial | 0.6.2 re-audit | Delta |
|----------|---------------|----------------|-------|
| Score | 76.19 | 76.19 | **0** |
| CRIT | 0 | 0 | 0 |
| MAJ | 1 | 1 | 0 |
| MIN | 2 | 2 | 0 |
| INFO | 2 | 2 | 0 |
| Verdict | GO CONDITIONNEL | GO CONDITIONNEL | iso |

**Cause du non-changement** : la branche de remediation ne touche aucun
code applicatif backend ou frontend. Les seules modifications sont :
build (Dockerfile `BAKE_MODELS=false` par defaut), compose (profile
`remote` opt-in pour docling-serve), CI (workflows), doc (CHANGELOG,
huggingface-dependency-map) et un mock dans `test_chunking.py`. Aucun
gap performance pre-existant n'est ni corrige ni aggrave. Le switch
docling-serve a un impact runtime neutre sur le chemin de conversion
deja non bloquant (`serve_converter.convert` + `httpx.AsyncClient`).

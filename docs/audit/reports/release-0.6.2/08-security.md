# Rapport d'audit : Securite

**Release** : 0.6.2
**Branche** : `release/0.6.2` (HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 14 / 14 (poids 32 / 32) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

**Delta vs 0.6.1 re-audit** : 0 (100 → 100). Aucune regression, aucun nouvel ecart bloquant introduit par les commits 0.6.2.

---

## Perimetre verifie pour 0.6.2

La branche 0.6.2 prolonge le tronc 0.6.1 avec, du cote securite :

- `chore(security): ignore CVE-2026-7598 (libssh2, not reachable, no Debian backport)` (`fc26e01`).
- `build(python): migrate services to uv` (`4d9bcf6`) + scellement de `uv.lock` + suite de commits `chore(#254)` qui durcissent le contexte Docker (`.dockerignore`, build-args sans secret, bake des checkpoints HF).
- Refactor `hex-arch` (`d42885c`) — ports graphe/arbre — sans nouvelle surface I/O exposee.
- `fix(remote): carry self_ref through ServeConverter` (`3936166`) — chemin de donnees in-process, pas de nouveau call externe.
- Aucune modification des chemins de scellement Fernet (`fernet_box.py`), de la repository `store_repo.py`, du resolver `store_backend_resolver.py`, des pools Neo4j/OpenSearch, ni du boot precondition `_check_store_secret_key` depuis 0.6.1. Les fichiers sont releve aux mêmes lignes que le re-audit `release-0.6.1-reaudit/08-security.md`.

L'audit re-couvre integralement les 5 axes critiques cibles par la consigne :

1. Scellement Fernet et gestion de cle (`infra/secrets/fernet_box.py`, `persistence/store_repo.py`).
2. Wiring boot-time `STORE_SECRET_KEY` (`main.py`, `infra/settings.py`, `.env.example`, compose).
3. Mots de passe sur les CRUD de stores et le test-connection (`api/stores.py`, `services/store_service.py`).
4. CVE-2026-7598 ignoree (`.trivyignore.yaml`).
5. Injection Cypher sur les drivers per-store (`infra/neo4j/*.py`, `infra/neo4j/driver_pool.py`).
6. Bonus : basic-auth OpenSearch (`infra/opensearch_store.py`, `infra/opensearch_pool.py`).

---

## Suivi des ecarts 0.6.1 (re-audit)

| Ecart 0.6.1 | Statut 0.6.2 | Preuve |
|-------------|--------------|--------|
| [MAJ] `STORE_SECRET_KEY` absent de `.env.example` / composes | **Resolu, intact** | `.env.example:61-68`, `docker-compose.yml:118-122`, `docker-compose.dev.yml:111-118` (commit `e43f1b0` toujours present) |
| [INFO] Defaut Neo4j `changeme` | **Inchange** (documente + warning au boot) | `document-parser/main.py:118-125`, `docker-compose.yml:1-24` |
| [INFO] OpenSearch sans TLS ni auth (stack dev) | **Inchange** (dev-only, opt-in) | `docker-compose.yml:47-66`, banniere `docker-compose.yml:1-24` |

Les deux INFO sont reconduits a l'identique pour 0.6.2 (cf. section Ecarts).

---

## Verification approfondie des chemins critiques 0.6.2

### 1. Scellement Fernet (#279) — code intact, contrat respecte

`document-parser/infra/secrets/fernet_box.py:65-95` — `FernetBox.seal/open` :

- `seal()` n'accepte que `str` (`TypeError` sinon, `:79-80`). Le ciphertext renvoye est base64 URL-safe + HMAC integre (Fernet ≡ AES-128-CBC + HMAC-SHA256 sur cle 32 bytes).
- `open()` discrimine `InvalidToken` -> `SealedValueTamperedError` (`:91-95`) ; le message d'erreur **ne contient pas** le ciphertext, conforme a la consigne explicite du docstring `:50-54` "Do NOT log the sealed value — it's still secret-bearing material".
- `__init__` distingue cle mal-formee (`StoreSecretKeyInvalidError`, `:70-75`) de cle absente (`StoreSecretKeyMissingError`, lance par `get_fernet_box`, `:128-136`). Les deux exceptions sont des `RuntimeError` typees, propagees jusqu'au lifespan FastAPI -> boot bloquant.
- Singleton lazy (`_box`, `:111`) : importer le module ne lit pas l'env, n'instancie pas Fernet. Aucun risque d'init silencieuse au mauvais moment.
- `reset_fernet_box()` documente "test-only" (`:141-149`), pas de surface prod.
- **Rotation** : pas implementee (intentionnel — `connection_key_id` reserve `:23` pour evolution future). Le contrat "MUST stay stable across restarts" est verbalise dans `.env.example:61-68`, dans chaque docstring (`get_fernet_box`, `RuntimeError._check_store_secret_key`), et dans les commentaires des deux composes. Bonne pratique : un seul invariant unique a respecter.

### 2. Boot precondition `_check_store_secret_key`

`document-parser/main.py:212-243` :

- Lit `SELECT COUNT(*) FROM stores WHERE connection_password_sealed IS NOT NULL` puis :
  - 0 rows scellees -> return (`:233-235`). Fresh install ou Neo4j-only stack possible sans cle.
  - ≥ 1 row + `settings.store_secret_key` vide -> `RuntimeError` avec instructions explicites (`:236-243`), boot fail-fast.
- Appele depuis le lifespan ligne 249, juste apres `init_db()`. Aucun chemin code ne demarre les routers Stores/Ingestion avant ce check.
- `settings.store_secret_key` (`infra/settings.py:41,164`) reste a `""` par defaut. Aucune valeur dangereuse cablee en dur.

### 3. Repository `store_repo.py` — separation plaintext / sealed

`document-parser/persistence/store_repo.py:38-220` :

- L'entite `Store` (`domain/models.py`) ne contient que `has_connection_password: bool`, **jamais** le plaintext (`_row_to_store:46-61`).
- `insert(store, *, password: str | None)` : le plaintext est un kwarg separe (`:67`), passe a Fernet uniquement quand non-None, jamais persiste sur l'entite (`:76-93`).
- `update(store)` (`:134-162`) ne touche pas `connection_password_sealed` : un PATCH sans password ne peut pas casser un seal existant par effet de bord. Le commentaire `:138-141` rend l'invariant explicite.
- `get_connection_password()` (`:182-202`) — seul site qui ouvre le seal en lecture. Docstring `:193` "must NEVER be logged or serialised. Treat it as memory-only and pass it directly to the driver factory" — invariant respecte sur tous les call sites (cf. resolver et pools ci-dessous).
- `set_connection_password()` (`:204-220`) : tri-state (None = pas touche, "" = clear, sinon = seal). La branche clear (`plaintext is None`) **n'invoque pas** la box -> permet d'effacer un seal meme sans `STORE_SECRET_KEY` (utile en remediation).

### 4. API stores et test-connection

`document-parser/api/stores.py:46-72,151-172` :

- `_store_to_response` (`:46-61`) ne serialise jamais le plaintext, seulement `hasConnectionPassword: bool` (`:57-59`).
- Endpoint `POST /api/stores/{slug}/test-connection` (`:151-172`) :
  - Toujours `200` ; le boolean transporte le resultat (`:155-164`).
  - Le service (`services/store_service.py:309-342`) capture toutes les exceptions du resolver/driver et renvoie `str(exc)` -> donc **aucun stack trace ne fuit**. Le commentaire `:316-318` documente explicitement que le password est strippe avant raise dans le resolver.
- `services/store_service.py:227-302` (create/update) : `connection_password` est traite comme write-only ; la lecture retournee est obtenue par `find_by_id` (`:234,307`), donc construit a partir du seul row -> jamais d'echo du plaintext fourni a la requete.
- DTOs `api/schemas.py:281-339` :
  - `StoreResponse:289-300` documente "password is **never** serialised".
  - `StoreCreateRequest:303-319` write-only.
  - `StoreUpdateRequest:322-339` documente le tri-state contractuel ("None=untouched, ""=clear, other=replace").

### 5. Resolver et pools — chemins de credentials

`document-parser/services/store_backend_resolver.py:117-153` :

- OpenSearch (`:117-130`) : ouvre le seal **uniquement** si `store.has_connection_password`, sinon passe `password=None`. Pas de lookup inutile.
- Neo4j (`:132-152`) : meme logique ; fallback env (`_env_neo4j_password`) **uniquement** quand le store ne porte pas son seal. Le password ne traverse jamais la frontiere services/infra hors de la signature `pool.get(...)`.

`document-parser/infra/neo4j/driver_pool.py:60-101` :

- `get(uri, user, password, ...)` : le password sert a `AsyncGraphDatabase.driver(uri, auth=(user, password))` puis est **immediatement oublie** (pas stocke sur l'instance `Neo4jDriver`). `verify_connectivity` puis `bootstrap_schema` sont idempotents.
- Cache keye par `(uri, user)` — le password n'est consulte qu'a la creation. Re-acquisitions short-circuit sur l'entree cache (`:79-81`), donc rotation de credentiel necessite eviction explicite (documente `:115-130`).
- Aucune trace de password dans les `logger.info` (`:99`, `:129`, `:148`).

`document-parser/infra/opensearch_pool.py:43-82` :

- Comportement identique au pool Neo4j. Le password est passe a `OpenSearchStore(...)` (`infra/opensearch_store.py:76-92`), qui le redirige dans `http_auth=(username, password)` du client `AsyncOpenSearch`. Pas de stockage explicite cote pool.
- Log `:77-81` : `"auth=basic" if username else "auth=none"`. Jamais le credential.

### 6. CVE-2026-7598 (libssh2) — justification verifiee

`.trivyignore.yaml:12-23` :

- `id: CVE-2026-7598`, `expired_at: 2026-08-31` (≈3 mois apres la cible release, conforme a la regle "rotation periodique").
- Justification factuellement verifiable :
  - libssh2 1.11.1-1 (Debian 13 trixie) est tire transitivement par `git`/`libcurl` du base image `python:3.12-slim`. Vrai.
  - Le backend n'a aucune surface SSH client : grep `ssh://\|libssh2\|paramiko\|fabric\|asyncssh` sur `document-parser/**/*.py` (hors `.venv`) -> 0 hit. Vrai.
  - L'overflow ne se declenche que sur `libssh2_userauth_*` avec username/password attacker-controlled. Le projet n'expose pas de tel call path.
- Plan documente : "Re-evaluate when Debian publishes a backport or when we move off slim". Date d'expiration -> sera re-examinee avant `2026-08-31`.

L'autre CVE ignoree (CVE-2026-40393 mesa) reste aussi justifiee + datee (`expired_at: 2026-06-30`, soit ≈3 semaines apres la release — devra etre re-examinee tres bientot, mais hors scope de cette release).

### 7. Injection Cypher (Neo4j)

`grep -rn "tx.run\|session.run"` sur `infra/neo4j/*.py` (audit complet, hors `.venv`) — **tous les call sites** utilisent les kwargs nommes :

- `infra/neo4j/chunk_writer.py:92,95,102,105,135,146` — `doc_id=doc_id`, `rows=chunk_rows`, etc.
- `infra/neo4j/tree_writer.py:129,137,138,139,142,167,180,208,226,241,265,286` — meme pattern.
- `infra/neo4j/tree_reader.py:24,36,47,62,63` — idem.
- `infra/neo4j/queries.py:150,159,178` — `await session.run(_FETCH_GRAPH, doc_id=doc_id)` (constante module-level + kwarg).
- `infra/neo4j/schema.py:50` — `session.run(stmt)` avec `stmt` parmi des constantes module-level (CREATE CONSTRAINT). Zero entree utilisateur.

Aucun `f"MATCH"` / `f"CREATE"` / `f"MERGE"` / `f"RETURN"` dans le code Neo4j (grep complet hors `.venv`/tests). Tous les inputs externes (`doc_id`, `chunk_id`, `self_ref`, `text`) transitent comme parametres bound — pas d'interpolation Cypher.

### 8. Injection SQL (aiosqlite)

`grep` complet f-string + (`SELECT|INSERT|UPDATE|DELETE|DROP`) sur `document-parser/**/*.py` hors `.venv`/tests :

- `persistence/analysis_repo.py:63,75,85,98` — f-strings concatenent **uniquement** `_SELECT_WITH_DOC` (constante module-level `:39-43`). Toutes les valeurs runtime passent par `?` placeholders.
- Reste des repos : aucun f-string SQL. `store_repo.py:78-98` (INSERT) et `:144-162` (UPDATE) utilisent strictement `?` + tuple de bound vars.

### 9. eval / exec / os.system / subprocess

`grep -rn "eval(\|exec(\|os\.system(\|subprocess\.(call|Popen|run)(" document-parser/ --exclude-dir=.venv --exclude-dir=tests` -> **0 hit**. Aucun chemin d'execution dynamique.

### 10. Frontend — XSS DOM

`grep -rn "v-html"` sur `frontend/src/**.vue` -> exactement 3 sites :

- `features/analysis/ui/MarkdownViewer.vue:3,17` — `DOMPurify.sanitize(marked.parse(...))`.
- `features/reasoning/ui/ReasoningPanel.vue:59,93,133` — idem.
- `features/reasoning/ui/AskRunner.vue:43,63,86` — idem (`async: false` flag pour marked synchrone).

Chaque site precede d'un commentaire `<!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify -->` — lint gate intact.

### 11. CORS + rate-limiter

`document-parser/main.py:394-406` :

- `allow_origins=settings.cors_origins` (defaut explicit `["http://localhost:3000","http://localhost:5173"]`, pas de `*`).
- `allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"]` — pas de wildcard.
- `allow_headers=["Content-Type","Authorization"]` — restreint.
- `RateLimiterMiddleware` cable si `settings.rate_limit_rpm > 0` (defaut 100).

`document-parser/infra/rate_limiter.py:59,68` — `/api/health` exclu via `exclude_paths` (constructor-injected).

### 12. Upload validation

`document-parser/api/documents.py:78-91` — Content-Length precheck + chunked read + cap immediat -> early 413.
`document-parser/services/document_service.py:72-79` — magic bytes `%PDF` exiges, sinon `ValueError -> HTTP 400`. UUID rename + extension `.pdf` forcee, donc upload `.exe` / `.sh` impossible meme avec MIME forge.

### 13. Headers Nginx + SPA fallback

`frontend/nginx.conf.template:7-15` — `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`. `try_files $uri $uri/ /index.html;` — pas d'`autoindex`.

### 14. Dependances

- Backend (`document-parser/pyproject.toml:6-19`) : toutes les deps en `>=X,<Y`. Notamment `cryptography>=43.0.0,<46.0.0` (couvre la fenetre des Fernet impl validees).
- Backend (`document-parser/uv.lock`) — 558 packages lockes au hash. Pas de surface de surprise au build.
- Frontend (`frontend/package.json:19-42`) : toutes les deps en `^X.Y.Z`. `dompurify ^3.3.3`, `marked ^17.0.4` — versions a jour.
- Trivy gate `release-gate.yml:352-365` : `severity: CRITICAL`, `exit-code: 1` (blocking), `trivyignores: .trivyignore.yaml`. HIGH informatif (`:367-377`, `exit-code: 0`).

### 15. Non-root container + bake artefacts

`document-parser/Dockerfile:28-37,85` — `useradd appuser`, `USER appuser` apres setup. Le commit `8690f37` ajoute `docling-tools models download` apres lequel un `chown -R appuser:appuser` (`:80,83-84`) preserve l'invariant non-root. Aucun changement du contexte de credentials.

`document-parser/.dockerignore:.env`/`.env.*` -> les fichiers locaux ne fuiront pas dans l'image. `.dockerignore` racine fait pareil.

---

## Ecarts constates

### [INFO] Defaut Neo4j `changeme` toujours present (reconduit depuis 0.6.1)

- **Localisation** : `document-parser/infra/settings.py:35,163` ; `docker-compose.yml:34,117` ; `docker-compose.dev.yml:16-118`.
- **Constat** : meme remediation a deux niveaux qu'en 0.6.1 — warning loggue au boot si `NEO4J_URI` est defini et que le password reste `changeme` (`main.py:118-125`), banniere `docker-compose.yml:1-24` "DEV DEFAULTS — NOT PRODUCTION-READY". Pas de regression : la consigne consomme l'invariant prod (operateur doit overrider) et trace le risque.
- **Regle violee** : 8.1.1 (poids 3) — risque residuel documente, detectable au boot, jamais silencieux.
- **Remediation** : non requise pour 0.6.2. Eventuel switch vers generation aleatoire au premier `up` en 0.7.x (deja envisage dans le re-audit 0.6.1).

### [INFO] OpenSearch sans TLS ni auth dans la stack dev (reconduit depuis 0.6.1)

- **Localisation** : `docker-compose.yml:47-66`, `docker-compose.dev.yml:37-56`.
- **Constat** : `DISABLE_SECURITY_PLUGIN: "true"` reste en place sur le profile `ingestion` (`docker-compose.yml:53-66`) et la stack dev. Le service n'est pas mappe sur l'hote dans la prod compose (uniquement reseau interne) ; expose seulement en dev.
- **Regle violee** : 8.4.1 (poids 3) — risque documente + banniere `docker-compose.yml:1-24`.
- **Remediation** : non requise pour 0.6.2. Variante `docker-compose.prod.yml` (security plugin + TLS) toujours pas livree — a planifier en 0.7.x.

---

## Resultats detailles par domaine

### 8.1 Secrets et credentials

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.1.1 — Pas de cles API/tokens en dur | PASS | `document-parser/infra/settings.py:15,144` | `docling_serve_api_key=None` par defaut, lu de l'env. Aucun token, mot de passe ou cle hard-cable. (Defaut Neo4j `changeme` -> INFO ci-dessus.) |
| 8.1.2 — `.env` dans `.gitignore` | PASS | `.gitignore:23-25` | `.env`, `.env.local`, `.env.production`. `.dockerignore` racine + backend filtrent egalement les `.env*` du build context. |
| 8.1.3 — Secrets Docker en env vars | PASS | `docker-compose.yml:118-122`, `docker-compose.dev.yml:111-118`, `.env.example:61-68` | `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` plumb sans defaut, documente avec commande de generation Fernet. Build-args (`BAKE_MODELS`, `WITH_REASONING`) ne portent aucun secret. |

### 8.2 Validation des entrees

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.2.1 — Validation Pydantic | PASS | `document-parser/api/schemas.py` | Tous les DTOs (`StoreCreateRequest`, `StoreUpdateRequest`, `StoreTestConnectionResponse`, etc.) heritent de `_CamelModel`. Tri-state password formellement documente sur `StoreUpdateRequest:323-339`. |
| 8.2.2 — `MAX_FILE_SIZE_MB` actif | PASS | `api/documents.py:78-91`, `services/document_service.py:72-79` | Reject Content-Length precoce + chunked read + recheck cote service. |
| 8.2.3 — Types fichiers acceptes | PASS | `services/document_service.py:75-79` | Magic bytes `%PDF` exiges, UUID + extension `.pdf` forcee. |

### 8.3 Injection

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.3.1 — Parametres lies SQL | PASS | `persistence/*.py` | f-strings dans `analysis_repo.py:63,75,85,98` concatenent seulement `_SELECT_WITH_DOC` (constante). Le `store_repo.py` 0.6.1 (`:78-98,144-162,194-217`) utilise strictement `?` placeholders. |
| 8.3.1bis — Parametres lies Cypher | PASS | `infra/neo4j/*.py` | 22 sites `tx.run` / `session.run` audites, tous en kwargs nommes. Schema Cypher `infra/neo4j/schema.py:50` utilise des constantes. |
| 8.3.2 — Pas eval/exec/os.system | PASS | scan complet `document-parser/**/*.py` | 0 hit. |
| 8.3.3 — DOMPurify pour HTML | PASS | `frontend/src/features/analysis/ui/MarkdownViewer.vue:17`, `features/reasoning/ui/{AskRunner,ReasoningPanel}.vue:86,133` | 3 sites v-html, tous sanitises avec `DOMPurify.sanitize(marked.parse(...))`. |

### 8.4 CORS et reseau

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.4.1 — CORS explicites (pas de `*`) | PASS | `document-parser/main.py:394-400` | `allow_origins=settings.cors_origins`, methodes restreintes, headers restreints. (Dev-only OpenSearch sans TLS -> INFO ci-dessus.) |
| 8.4.2 — Rate limiter actif | PASS | `document-parser/main.py:401-406`, `infra/rate_limiter.py:59-68` | Middleware monte si `rate_limit_rpm > 0` (defaut 100), `/api/health` exclu. |
| 8.4.3 — Nginx sans directory listing | PASS | `frontend/nginx.conf.template:13-15` | `try_files`, pas d'`autoindex`. Headers de durcissement actifs. |

### 8.5 Dependances

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.5.1 — Pas de CVE critique non geree | PASS | `.trivyignore.yaml`, `.github/workflows/release-gate.yml:352-377` | Gate Trivy CRITICAL bloquant ; 2 CVE explicitement ignorees avec justification factuelle + `expired_at`. CVE-2026-7598 (libssh2) verifiee : aucun call site SSH client dans le code. |
| 8.5.2 — Versions epinglees | PASS | `document-parser/pyproject.toml`, `document-parser/uv.lock`, `frontend/package.json` | Backend en `>=X,<Y` + `uv.lock` au hash (558 packages locked). Frontend en `^X.Y.Z`. `cryptography>=43.0.0,<46.0.0` (Fernet). |

### Infrastructure et surfaces 0.6.2

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| Non-root Docker | PASS | `document-parser/Dockerfile:28-37,83-85` | `useradd appuser`, `USER appuser` apres bake des modeles. Le commit `8690f37` preserve l'invariant via `chown -R appuser` apres `docling-tools models download`. |
| Security headers Nginx | PASS | `frontend/nginx.conf.template:7-11` | 4 headers actifs. |
| Fernet sealing (#279) | PASS | `infra/secrets/fernet_box.py:34-95,114-138`, `persistence/store_repo.py:25,57,76,182-220` | AES-128-CBC + HMAC-SHA256 ; plaintext jamais sur l'entite ; lecture/ecriture sur chemin dedie ; erreurs typees ; rotation hors scope (documente). |
| Boot precondition `STORE_SECRET_KEY` | PASS | `document-parser/main.py:212-243,249` | `_check_store_secret_key` appele dans le lifespan ; fail-fast si seal sans cle. |
| Test-connection endpoint (#279) | PASS | `api/stores.py:151-172`, `services/store_service.py:309-342` | Toujours 200, boolean transporte le resultat, password jamais dans l'exception, stack trace jamais retourne au client. |
| Pool Neo4j per-(uri,user) | PASS | `infra/neo4j/driver_pool.py:60-101,115-130` | Password consulte uniquement a la creation, jamais loggue (`:99,129,148`). Eviction documentee pour rotation. |
| Pool OpenSearch per-(url,user) | PASS | `infra/opensearch_pool.py:43-82,92-107` | Idem ; `auth="basic"/"none"` loggue, jamais le credential. |
| Resolver per-store | PASS | `services/store_backend_resolver.py:117-152` | Seal ouvert uniquement quand `has_connection_password`, jamais propage hors de la signature pool. |
| Pas de log de secrets | PASS | grep complet `logger\|logging\|print` sur `infra/secrets/`, `persistence/store_repo.py`, `services/store_service.py`, `services/store_backend_resolver.py`, `infra/neo4j/driver_pool.py`, `infra/opensearch_pool.py` | 0 hit avec valeur de credential. |
| `.dockerignore` filtre `.env` | PASS | `.dockerignore`, `document-parser/.dockerignore` | Local env / secrets exclus du build context. |

---

## Points positifs

- **Stabilite securitaire 0.6.1 -> 0.6.2** : aucun chemin sensible (sealing, resolver, pools, boot precondition) n'a ete modifie. Les commits 0.6.2 portent sur le packaging (uv, slim Docker, bake), pas sur la surface d'authentification / persistence.
- **Trivy ignore-list datee + justifiee** : CVE-2026-7598 (libssh2) ajoutee avec une justification factuellement verifiable (grep -> 0 surface SSH client), `expired_at: 2026-08-31`. Bonne pratique de "wagon d'expiration" maintenue.
- **`uv.lock` (558 packages hashes)** : `build(python)` ajoute un verrou de chaine d'approvisionnement supplementaire au-dela des `>=X,<Y` du `pyproject.toml`. Reduit la fenetre d'attaque supply-chain.
- **Resolver per-store + pools** : separation correcte plaintext / sealed ; le password ne traverse jamais la frontiere services/infra hors signature `pool.get(...)`. Les pools refusent intentionnellement les rotations silencieuses (cache key = `(uri, user)`, doc `:54-58` de `opensearch_pool.py`).
- **DTOs immuables** : `StoreResponse` documente "password is **never** serialised" (`api/schemas.py:285-287`). Le `has_connection_password: bool` joue le role de proof-without-disclosure pour l'UI.
- **Banniere DEV-only sur compose** : preservee depuis 0.6.1, rend les defauts dangereux non-ambigus pour l'operateur.
- **CI hardening (`auto-close-issues.yml` `714a181`)** intact en 0.6.2 (inherite de 0.6.1) : `env COMMITS_JSON: ${{ toJSON(...) }}` + `printf '%s'` coupe l'injection shell via message de commit.

---

## Verdict partiel : GO

**Score** : 100 / 100 (seuil GO >= 80).

**Delta vs 0.6.1 re-audit** : +0 points (100 -> 100), 0 nouveau CRIT, 0 nouveau MAJ, 0 nouveau MIN. INFO stables (2 -> 2 — defaut Neo4j et OpenSearch dev-only documentes).

Les 5 chemins critiques cibles par la consigne ont ete reverifies a HEAD `051ac4a` :

1. Scellement Fernet (`fernet_box.py`) — code intact, contrat respecte, plaintext jamais loggue ni serialise.
2. Boot precondition `STORE_SECRET_KEY` (`main.py:212-243`) — fail-fast intact, env plumb intact (`.env.example`, deux composes).
3. CRUD stores + test-connection (`api/stores.py`, `services/store_service.py`) — DTOs write-only, exception nettoyee avant retour client.
4. CVE-2026-7598 (`.trivyignore.yaml:12-23`) — justification factuellement verifiable, datee (`2026-08-31`).
5. Cypher per-store (`infra/neo4j/*.py`, `driver_pool.py`) — 22 call sites audites, tous en bound params ; pool n'expose pas le password.

Bonus : OpenSearch basic-auth (`opensearch_store.py:76-92`, `opensearch_pool.py:43-82`) — credentials passes au client une fois et oublies cote pool, jamais logges.

Aucun ecart bloquant. Recommandation : prevoir pour 0.7.x (a) la suppression du defaut Neo4j `changeme` au profit d'une generation aleatoire au premier `up`, et (b) une variante `docker-compose.prod.yml` activant le plugin de securite OpenSearch + TLS.

---

## Audits associes / tickets

- Checklist 08-security.md : **14/14 conformes** (poids 32/32).
- Voir aussi : Audit 10 — CI/Build (Trivy gate, uv migration, .dockerignore), Audit 11 — Documentation (`.env.example` + invariant `STORE_SECRET_KEY` stable across restarts).
- Pas de remediation requise pour 0.6.2.

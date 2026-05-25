# Rapport d'audit : Securite

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 17.5 / 18 |
| Score | 93 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

---

## Suivi des ecarts 0.5.0

| Ecart 0.5.0 | Statut 0.6.1 | Preuve |
|-------------|--------------|--------|
| [MAJ] Hardcoded `neo4j_password="changeme"` (`infra/settings.py:35,163`) | **Partiellement remedie** (downgraded to [INFO]) | Defaut conserve mais boot warning ajoute `document-parser/main.py:118-125` ; `docker-compose.yml:1-24` declare explicitement le statut dev-only |
| [MAJ] OpenSearch security plugin disabled (`docker-compose.yml`) | **Remedie** | `docker-compose.yml:1-24,47-52` ajoute un bandeau "DEV DEFAULTS — NOT PRODUCTION-READY" + commentaires en tete de chaque service exposant la dette |
| [INFO] Rate limiter desactivable | Inchange (par design) | `infra/rate_limiter.py:59` exclut `/api/health`, defaut 100 RPM |

---

## Ecarts constates

### [MAJ] `STORE_SECRET_KEY` absent de `.env.example` et des docker-compose

- **Localisation** : `.env.example` (manquant), `docker-compose.yml:97-113` (manquant), `docker-compose.dev.yml:96-110` (manquant)
- **Constat** : Le boot precondition `_check_store_secret_key` (`document-parser/main.py:212-243`) leve `RuntimeError` si une ligne `stores.connection_password_sealed` est non-NULL alors que `STORE_SECRET_KEY` est vide. Or :
  - `STORE_SECRET_KEY` n'est documente dans aucun `.env.example` (la cle n'apparait nulle part dans le fichier).
  - Aucun des `docker-compose*.yml` ne propage `STORE_SECRET_KEY` dans l'environnement du conteneur `document-parser`.
  - Le frontend permet pourtant via `POST /api/stores` de creer un store avec un `connectionPassword` (cf. `document-parser/api/stores.py:94-114` + `frontend/src/features/stores/...`).

  Un operateur suivant la doc cree son premier store avec password, l'API repond 201 (le code dans `SqliteStoreRepository.insert` ne lit la cle qu'au moment du seal — qui fonctionnera car la variable d'env shell de l'operateur peut etre vide → `Fernet("")` echoue ; ou si la cle est presente dans le shell mais pas dans le compose, le boot suivant explose et le backend ne redemarre plus). La porte est ouverte a un boot bloque par auto-corruption configurationnelle, ou pire, un seal avec une cle non persistee → tous les passwords sont perdus au prochain restart.
- **Regle violee** : 8.1.3 — Secrets Docker passes par variables d'environnement (poids 2). La cle Fernet est un secret critique qui doit etre cable explicitement.
- **Remediation** :
  1. Ajouter dans `.env.example` une section dediee avec la commande de generation Fernet et l'avertissement "obligatoire des qu'un store a un password".
  2. Ajouter `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` au bloc env de `document-parser` dans `docker-compose.yml` et `docker-compose.dev.yml`.
  3. Optionnel : refuser la creation d'un store avec `connectionPassword` en API si `settings.store_secret_key` est vide, plutot que de laisser `FernetBox` lever une `StoreSecretKeyInvalidError` opaque (cf. `infra/secrets/fernet_box.py:65-75`).

### [INFO] Defaut Neo4j `changeme` toujours present (downgrade depuis 0.5.0 [MAJ])

- **Localisation** : `document-parser/infra/settings.py:35,163`, `docker-compose.yml:34,108`, `docker-compose.dev.yml:16,110`
- **Constat** : La valeur defaut est conservee pour preserver le DX "docker compose up = ca marche". La remediation est faite a deux niveaux :
  1. `document-parser/main.py:118-125` emet un `logger.warning` au boot si `NEO4J_URI` est defini et que le password est reste `changeme`.
  2. `docker-compose.yml:1-24` declare en tete de fichier que les defauts sont dev-only et liste les pre-requis pour la prod (rotation `NEO4J_PASSWORD`, re-activation OpenSearch security, isolation reseau, TLS).
- **Regle violee** : 8.1.1 (poids 3) — mais le risque residuel est documente et detectable (warning), pas silencieux.
- **Remediation** : Pas requise pour 0.6.1. Suivre l'evolution en 0.7.x (potentiellement supprimer le defaut et basculer sur une generation aleatoire au premier `up` si la variable est absente).

### [INFO] OpenSearch sans TLS ni auth dans la stack dev

- **Localisation** : `docker-compose.yml:53-66`, `docker-compose.dev.yml:37-56`
- **Constat** : `DISABLE_SECURITY_PLUGIN: "true"` est conserve sur la stack `ingestion`-profile (donc opt-in) et la stack dev. Le commentaire en haut de `docker-compose.yml` (`:1-24`) explicite que c'est un defaut dev et liste la marche a suivre pour la prod.
- **Regle violee** : 8.4.1 (poids 3) — mais le risque est documente et le service n'est expose que sur `localhost` par defaut (pas de port mapping dans `docker-compose.yml`, seulement dans `docker-compose.dev.yml`).
- **Remediation** : Fournir une variante `docker-compose.prod.yml` activant security plugin + TLS dans une release ulterieure.

---

## Resultats detailles par domaine

### 8.1 Secrets et credentials

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.1.1 — Pas de cles API/tokens en dur | PASS | `document-parser/infra/settings.py:14` | `docling_serve_api_key=None` par defaut, lu de l'env |
| 8.1.2 — `.env` dans `.gitignore` | PASS | `.gitignore:24-27` | `.env`, `.env.local`, `.env.production` listes |
| 8.1.3 — Secrets Docker en env vars | PARTIAL | `docker-compose.yml:97-113`, `.env.example` | `NEO4J_PASSWORD` correct mais `STORE_SECRET_KEY` non plumbed — voir [MAJ] ci-dessus |

### 8.2 Validation des entrees

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.2.1 — Validation Pydantic | PASS | `document-parser/api/schemas.py` | Tous les DTOs utilisent Pydantic + `@field_validator` (ex `schemas.py:285-340` pour les stores) |
| 8.2.2 — `MAX_FILE_SIZE_MB` actif | PASS | `document-parser/api/documents.py:78-91`, `services/document_service.py:68` | Reject early via `Content-Length`, puis chunked read avec coupe immediate, plus check final cote service |
| 8.2.3 — Types fichiers acceptes | PASS | `document-parser/services/document_service.py:71` | Magic bytes `%PDF` exiges, fichier renomme en UUID + extension `.pdf` forcee |

### 8.3 Injection

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.3.1 — Parametres lies SQL | PASS | `document-parser/persistence/*.py` | Tous les SQL emis vers aiosqlite utilisent `?`. Les rares f-strings (`analysis_repo.py:63,75,85,98`, `chunk_repo.py:122`) concatenent un fragment SQL constant module-level (`_SELECT_WITH_DOC`) ou un sous-clause statique — zero valeur utilisateur dans la chaine |
| 8.3.1bis — Parametres lies Cypher | PASS | `document-parser/infra/neo4j/*.py` | `tx.run(...)` avec kwargs nommes (`doc_id=doc_id`), pas d'interpolation. `schema.py:50` itere sur un tuple de constantes |
| 8.3.2 — Pas eval/exec/os.system | PASS | scan complet `document-parser/**/*.py` | Aucun match pour `eval(`, `exec(`, `os.system(`, `subprocess.call`, `subprocess.Popen` |
| 8.3.3 — DOMPurify pour HTML | PASS | `frontend/src/features/analysis/ui/MarkdownViewer.vue:9,17`, `features/reasoning/ui/AskRunner.vue:63,86`, `features/reasoning/ui/ReasoningPanel.vue:93,133` | Les 3 sites `v-html` enchainent `DOMPurify.sanitize(marked.parse(...))` |

### 8.4 CORS et reseau

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.4.1 — CORS explicites (pas de `*`) | PASS | `document-parser/main.py:361-367` | `allow_origins=settings.cors_origins`, defaut `["http://localhost:3000","http://localhost:5173"]`, methodes restreintes a `GET,POST,PATCH,DELETE,OPTIONS` |
| 8.4.2 — Rate limiter actif | PASS | `document-parser/main.py:369-374`, `infra/rate_limiter.py:59-68` | Middleware monte si `rate_limit_rpm > 0` (defaut 100), `/api/health` exclu |
| 8.4.3 — Nginx sans directory listing | PASS | `frontend/nginx.conf.template:13-15` | `try_files $uri $uri/ /index.html;` (SPA fallback), pas d'`autoindex` |

### 8.5 Dependances

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.5.1 — Pas de CVE critique non geree | PASS | `.trivyignore.yaml`, `.github/workflows/release-gate.yml:349-372` | Gate Trivy CRITICAL bloquant ; 2 CVE explicitement justifiees + datees (`expired_at`) : CVE-2026-40393 (mesa, transitif `libgl1`), CVE-2026-7598 (libssh2, pas de surface SSH dans le code) |
| 8.5.2 — Versions epinglees | PASS | `document-parser/requirements.txt`, `frontend/package.json` | Toutes les deps backend sont en `>=X,<Y` ; deps frontend en `^X.Y.Z`. Nouvelle dep 0.6.1 : `cryptography>=43.0.0,<46.0.0` (Fernet) |

### Infrastructure et nouvelles surfaces 0.6.1

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| Non-root Docker | PASS | `document-parser/Dockerfile:24,33,55` | `useradd appuser`, `USER appuser` apres setup |
| Security headers Nginx | PASS | `frontend/nginx.conf.template:7-11` | `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy` |
| Fernet sealing store passwords (#279) | PASS | `infra/secrets/fernet_box.py:57-95`, `persistence/store_repo.py:67-220` | AES-128-CBC + HMAC-SHA256 via `cryptography.fernet` ; plaintext jamais sur l'entite `Store`, jamais serialise en reponse (`api/stores.py:88,117`, `schemas.py:283-300` — seul `hasConnectionPassword: bool` est expose) ; lecture/ecriture dediee via `get_connection_password()` / `set_connection_password()` |
| Boot precondition `STORE_SECRET_KEY` | PASS partiel | `document-parser/main.py:212-243,249` | Le backend refuse de booter si des secrets scelles existent sans cle — bon. Manque le plumbing env (voir [MAJ]) |
| Erreurs typees Fernet | PASS | `infra/secrets/fernet_box.py:34-54` | `StoreSecretKeyMissingError`, `StoreSecretKeyInvalidError`, `SealedValueTamperedError` discriminent les modes d'erreur (cle absente vs corrompue vs ciphertext altere) |
| OpenSearch http_auth | PASS | `infra/opensearch_store.py:85-90`, `infra/opensearch_pool.py:43-82` | `http_auth=(user, pass)` quand fourni ; TLS auto-detecte via scheme `https://` ; pool keye sur `(url, username)` — le password n'est consulte qu'a la creation du client |
| Auto-close-issues CI hardening | PASS | `.github/workflows/auto-close-issues.yml:21-24` (working tree mod) | Migration depuis `commits='${{ toJSON(...) }}'` vers `env COMMITS_JSON` + `printf '%s'` — coupe une injection shell via message de commit (caractere apostrophe non-echappe) |
| Pas de log de secrets | PASS | scan `logger\.|logging\.` sur `password|secret|sealed|api_key|token` | Aucune occurrence. `opensearch_pool.py:80,105` log seulement `"basic"` vs `"none"`, pas le credential |

---

## Points positifs

- **Fernet sealing (#279)** : implementation propre — wrapper minimal `FernetBox` qui isole `cryptography`, erreurs typees, singleton lazy, plaintext jamais sur l'entite, write/read paths separes (`set_connection_password` vs `update`).
- **Boot precondition** : `_check_store_secret_key` refuse de demarrer si des secrets scelles sont presents sans cle — fail-fast au lieu d'erreurs runtime opaques au premier push.
- **DEV-only contract** sur `docker-compose.yml` : bandeau en tete + commentaires par service explicitant les defauts dangereux et la marche a suivre pour la prod. Repond a la remediation 0.5.0 sur OpenSearch security.
- **Trivy gate** + ignore-list datee : `.trivyignore.yaml` documente chaque CVE ignoree (raison + `expired_at`) — les ignores ne moisissent pas.
- **Auto-close-issues injection** : `working tree` corrige une injection shell potentielle via `github.event.commits` — defense en profondeur sur la CI.
- **Cypher bound params** : tous les `tx.run(...)` Neo4j utilisent les kwargs `name=value`, pas d'interpolation.
- **SQL bound params** : aiosqlite avec `?` placeholders systematiquement ; les rares f-strings concatenent des constantes module-level.
- **CORS** : configuration explicite, methodes restreintes, pas de wildcard.
- **Upload validation** : Content-Length + chunked read + magic bytes + UUID rename + page count limit.

---

## Verdict partiel : GO CONDITIONNEL

**Score** : 93 / 100 (seuil GO >= 80, GO CONDITIONNEL si MAJ resolvable)

**Delta vs 0.5.0** : +2 points (91 → 93), -1 ecart MAJ (2 → 1), +1 INFO (1 → 2). Les deux MAJ 0.5.0 sont remedies (Neo4j password downgrade en INFO via boot warning + dev-only banner ; OpenSearch security documente comme dev-only). Un nouveau MAJ apparait sur le perimetre 0.6.1 (plumbing env `STORE_SECRET_KEY`).

**Condition requise avant merge** :

1. **[MAJ-1]** Plumber `STORE_SECRET_KEY` :
   - ajouter une section dediee dans `.env.example` (commande de generation + obligation des qu'un store a un password) ;
   - ajouter `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` au bloc env `document-parser` de `docker-compose.yml` et `docker-compose.dev.yml`.

   Effort : 10 min. Sans cela, un operateur peut creer un store avec password via l'API, sceller avec une cle non persistee, et perdre tous les credentials au prochain restart (ou bloquer le boot).

**Pas de blocage GO** : Zero `[CRIT]`, un seul `[MAJ]` corrigeable trivialement, deux `[INFO]` documentes et tracables.

---

## Audits associes / tickets

- 08-security.md checklist : 17.5 / 18 conformes (8.1.3 partiel)
- Suivre [MAJ-1] dans un ticket de remediation post-audit pre-merge
- Voir aussi : Audit 10 — CI/Build (Trivy gate), Audit 11 — Documentation (`.env.example`)

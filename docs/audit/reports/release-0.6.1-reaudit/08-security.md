# Rapport d'audit : Securite (re-audit)

**Release** : 0.6.1
**Branche** : `fix/0.6.1-audit-blockers` (HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 18 / 18 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

---

## Suivi des ecarts 0.6.1

| Ecart 0.6.1 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] `STORE_SECRET_KEY` absent de `.env.example` et des `docker-compose*.yml` | **Remedie** | Commit `3818933` — `ops(stores): plumb STORE_SECRET_KEY through env example + compose (#audit-08)` |
| [INFO] Defaut Neo4j `changeme` toujours present | Inchange (documente, warning au boot) | `document-parser/main.py:118-125` warning conserve, banniere DEV-only `docker-compose.yml:1-24` |
| [INFO] OpenSearch sans TLS ni auth dans la stack dev | Inchange (dev-only, opt-in) | Banniere `docker-compose.yml:1-24` + service expose seulement en dev |

---

## Verification de la remediation [MAJ-1]

### `.env.example`

`/.env.example:61-68` :

```env
# Fernet key for store-credential sealing-at-rest (#279).
# REQUIRED as soon as any store row holds an encrypted secret — boot fails
# otherwise (see document-parser/main.py:_check_store_secret_key). MUST stay
# stable across restarts; rotating the key invalidates every existing
# sealed value. Leave unset only on a fresh stack that hasn't sealed
# anything yet. Generate a fresh key with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# STORE_SECRET_KEY=
```

Conforme : variable documentee, commande de generation Fernet inline, invariant "MUST stay stable across restarts" explicite, lien vers le boot precondition.

### `docker-compose.yml`

`docker-compose.yml:109-113` :

```yaml
      # Fernet sealing-at-rest for store credentials (#279). No default —
      # boot fails if sealed rows exist without this set. Generate with:
      #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
      # MUST stay stable across restarts.
      STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}
```

Conforme : aucune valeur par defaut, propagation explicite, commentaire dedie.

### `docker-compose.dev.yml`

`docker-compose.dev.yml:111-114` :

```yaml
      # Fernet sealing-at-rest for store credentials (#279). See .env.example
      # for the one-liner to generate a key. No default on purpose: a dev
      # who creates a sealed store must persist the key in their own .env.
      STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}
```

Conforme : meme convention que prod, renvoi vers `.env.example` pour la generation.

### Boot precondition intact

`document-parser/main.py:212-243` — `_check_store_secret_key()` :

- Compte `stores WHERE connection_password_sealed IS NOT NULL`.
- Si 0, return (no-op pour fresh install / Neo4j-only stack).
- Si > 0 et `settings.store_secret_key` vide, leve `RuntimeError` avec message d'instruction explicite (`Set STORE_SECRET_KEY ... or null the connection_password_sealed columns manually if the seal is lost.`).
- Appele depuis le lifespan, ligne 249, juste apres `init_db()`.

`document-parser/infra/settings.py:41,164` — `store_secret_key: str = ""` (defaut vide) + binding `os.environ.get("STORE_SECRET_KEY", "")`. Aucune valeur defaut dangereuse.

---

## Ecarts constates

### [INFO] Defaut Neo4j `changeme` toujours present (downgrade depuis 0.5.0 [MAJ])

- **Localisation** : `document-parser/infra/settings.py:35,163`, `docker-compose.yml:34,108`, `docker-compose.dev.yml:16,110`
- **Constat** : Valeur defaut conservee pour preserver le DX `docker compose up = ca marche`. Remediation a deux niveaux :
  1. `document-parser/main.py:118-125` — `logger.warning` au boot si `NEO4J_URI` defini et password reste `changeme`.
  2. `docker-compose.yml:1-24` — bandeau "DEV DEFAULTS — NOT PRODUCTION-READY" + prerequis prod (rotation `NEO4J_PASSWORD`, re-activation OpenSearch security, isolation reseau, TLS).
- **Regle violee** : 8.1.1 (poids 3) — risque residuel documente et detectable, pas silencieux.
- **Remediation** : Pas requise pour 0.6.1. Eventuellement supprimer le defaut et basculer sur generation aleatoire au premier `up` en 0.7.x.

### [INFO] OpenSearch sans TLS ni auth dans la stack dev

- **Localisation** : `docker-compose.yml:53-66`, `docker-compose.dev.yml:37-56`
- **Constat** : `DISABLE_SECURITY_PLUGIN: "true"` conserve sur la stack `ingestion`-profile (opt-in) et la stack dev. Commentaire en tete de `docker-compose.yml:1-24` explicite que c'est un defaut dev et liste la marche a suivre pour la prod.
- **Regle violee** : 8.4.1 (poids 3) — risque documente, service expose uniquement sur `localhost` (pas de port mapping dans `docker-compose.yml`, seulement dans `docker-compose.dev.yml`).
- **Remediation** : Fournir une variante `docker-compose.prod.yml` activant security plugin + TLS dans une release ulterieure.

---

## Resultats detailles par domaine

### 8.1 Secrets et credentials

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.1.1 — Pas de cles API/tokens en dur | PASS | `document-parser/infra/settings.py:14` | `docling_serve_api_key=None` par defaut, lu de l'env |
| 8.1.2 — `.env` dans `.gitignore` | PASS | `.gitignore:23-25` | `.env`, `.env.local`, `.env.production` listes |
| 8.1.3 — Secrets Docker en env vars | **PASS (remedie)** | `docker-compose.yml:109-113`, `docker-compose.dev.yml:111-114`, `.env.example:61-68` | `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` cable sans defaut, documente avec commande de generation |

### 8.2 Validation des entrees

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.2.1 — Validation Pydantic | PASS | `document-parser/api/schemas.py` | Tous les DTOs utilisent Pydantic + `@field_validator` |
| 8.2.2 — `MAX_FILE_SIZE_MB` actif | PASS | `document-parser/api/documents.py:78-91`, `services/document_service.py:68` | Reject early via `Content-Length`, puis chunked read avec coupe immediate, plus check final cote service |
| 8.2.3 — Types fichiers acceptes | PASS | `document-parser/services/document_service.py:71` | Magic bytes `%PDF` exiges, fichier renomme en UUID + extension `.pdf` forcee |

### 8.3 Injection

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.3.1 — Parametres lies SQL | PASS | `document-parser/persistence/*.py` | Tous les SQL emis vers aiosqlite utilisent `?`. F-strings dans `analysis_repo.py:63,75,85,98` et `chunk_repo.py:122` concatenent uniquement le fragment constant module-level `_SELECT_WITH_DOC` ou des sous-clauses statiques — zero valeur utilisateur dans la chaine |
| 8.3.1bis — Parametres lies Cypher | PASS | `document-parser/infra/neo4j/*.py` | `tx.run(...)` avec kwargs nommes (`doc_id=doc_id`), pas d'interpolation |
| 8.3.2 — Pas eval/exec/os.system | PASS | scan complet `document-parser/**/*.py` | Aucun match pour `eval(`, `exec(`, `os.system(`, `subprocess.call`, `subprocess.Popen` |
| 8.3.3 — DOMPurify pour HTML | PASS | `frontend/src/features/analysis/ui/MarkdownViewer.vue:9,17`, `features/reasoning/ui/AskRunner.vue:63,86`, `features/reasoning/ui/ReasoningPanel.vue:93,133` | Les 3 sites `v-html` enchainent `DOMPurify.sanitize(marked.parse(...))` |

### 8.4 CORS et reseau

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.4.1 — CORS explicites (pas de `*`) | PASS | `document-parser/main.py:396` | `allow_origins=settings.cors_origins`, defaut `["http://localhost:3000","http://localhost:5173"]`, methodes restreintes a `GET,POST,PATCH,DELETE,OPTIONS` |
| 8.4.2 — Rate limiter actif | PASS | `document-parser/main.py:369-374`, `infra/rate_limiter.py:59-68` | Middleware monte si `rate_limit_rpm > 0` (defaut 100), `/api/health` exclu |
| 8.4.3 — Nginx sans directory listing | PASS | `frontend/nginx.conf.template:13-15` | `try_files $uri $uri/ /index.html;` (SPA fallback), pas d'`autoindex` |

### 8.5 Dependances

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.5.1 — Pas de CVE critique non geree | PASS | `.trivyignore.yaml`, `.github/workflows/release-gate.yml:349-372` | Gate Trivy CRITICAL bloquant ; 2 CVE explicitement justifiees + datees (`expired_at`) : CVE-2026-40393 (mesa, transitif `libgl1`), CVE-2026-7598 (libssh2, pas de surface SSH dans le code) |
| 8.5.2 — Versions epinglees | PASS | `document-parser/requirements.txt`, `frontend/package.json` | Toutes les deps backend sont en `>=X,<Y` ; deps frontend en `^X.Y.Z`. Dep 0.6.1 : `cryptography>=43.0.0,<46.0.0` (Fernet) |

### Infrastructure et surfaces 0.6.1

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| Non-root Docker | PASS | `document-parser/Dockerfile:24,33,55` | `useradd appuser`, `USER appuser` apres setup |
| Security headers Nginx | PASS | `frontend/nginx.conf.template:7-11` | `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy` |
| Fernet sealing store passwords (#279) | PASS | `infra/secrets/fernet_box.py:57-95`, `persistence/store_repo.py:67-220` | AES-128-CBC + HMAC-SHA256 via `cryptography.fernet` ; plaintext jamais sur l'entite `Store`, jamais serialise en reponse (`api/stores.py:88,117`, `schemas.py:283-300` — seul `hasConnectionPassword: bool` est expose) ; lecture/ecriture dediee via `get_connection_password()` / `set_connection_password()` |
| Boot precondition `STORE_SECRET_KEY` | **PASS (full)** | `document-parser/main.py:212-243,249` | Le backend refuse de booter si des secrets scelles existent sans cle. Le plumbing env est desormais en place ([MAJ-1] remedie) |
| Erreurs typees Fernet | PASS | `infra/secrets/fernet_box.py:34-54` | `StoreSecretKeyMissingError`, `StoreSecretKeyInvalidError`, `SealedValueTamperedError` discriminent les modes d'erreur (cle absente vs corrompue vs ciphertext altere) |
| OpenSearch http_auth | PASS | `infra/opensearch_store.py:85-90`, `infra/opensearch_pool.py:43-82` | `http_auth=(user, pass)` quand fourni ; TLS auto-detecte via scheme `https://` ; pool keye sur `(url, username)` — le password n'est consulte qu'a la creation du client |
| Auto-close-issues CI hardening | PASS | `.github/workflows/auto-close-issues.yml:17-24` (commit `714a181`) | Migration vers `env COMMITS_JSON: ${{ toJSON(...) }}` + `printf '%s' "$COMMITS_JSON"` — coupe l'injection shell via message de commit (apostrophe non-echappee dans inline `${{ }}` interpolation) |
| Pas de log de secrets | PASS | scan `logger\.|logging\.` sur `password|secret|sealed|api_key|token` | Aucune occurrence. `opensearch_pool.py:80,105` log seulement `"basic"` vs `"none"`, pas le credential |

---

## Points positifs

- **[MAJ-1] remedie proprement** : commit `3818933` plumb la variable sans defaut, ajoute la commande de generation Fernet dans `.env.example`, et documente l'invariant "MUST stay stable across restarts" cote env example + compose. Le boot precondition (`main.py:212-243`) reste la garantie fail-fast.
- **Fernet sealing (#279)** : wrapper minimal `FernetBox` qui isole `cryptography`, erreurs typees, singleton lazy, plaintext jamais sur l'entite, write/read paths separes.
- **DEV-only contract** sur `docker-compose.yml` : bandeau en tete + commentaires par service explicitant les defauts dangereux et la marche a suivre pour la prod.
- **Trivy gate** + ignore-list datee : `.trivyignore.yaml` documente chaque CVE ignoree (raison + `expired_at`).
- **Auto-close-issues injection** (commit `714a181`) : `env COMMITS_JSON` + `printf '%s'` coupe l'injection shell via `github.event.commits`.
- **Cypher bound params** : tous les `tx.run(...)` Neo4j utilisent les kwargs `name=value`, pas d'interpolation.
- **SQL bound params** : aiosqlite avec `?` placeholders systematiquement ; les rares f-strings concatenent des constantes module-level.
- **CORS** : configuration explicite, methodes restreintes, pas de wildcard.
- **Upload validation** : Content-Length + chunked read + magic bytes + UUID rename + page count limit.

---

## Verdict partiel : GO

**Score** : 100 / 100 (seuil GO >= 80)

**Delta vs 0.6.1** : +7 points (93 → 100), -1 ecart MAJ (1 → 0), 0 CRIT, 0 MIN, INFO stables (2 → 2).

L'unique MAJ du premier audit est integralement remediee par le commit `3818933` :

1. `.env.example:61-68` documente la variable avec la commande de generation Fernet, l'invariant "stable across restarts", et le lien vers le boot precondition.
2. `docker-compose.yml:109-113` et `docker-compose.dev.yml:111-114` propagent `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` sans defaut.
3. Le boot precondition `_check_store_secret_key` (`main.py:212-243`) garantit qu'aucun backend ne demarre avec des secrets scelles + cle manquante.

Aucun nouvel ecart introduit par les autres commits de la branche (`f9e5619` hex-arch refactor, `4fbf3b8` changelog, `313f9a9` push vocabulary, `bdbe1a2` async I/O, `68cfdf1` test fix, `e11a567` version bump). Les deux INFO restants (Neo4j defaut, OpenSearch dev-only) sont documentes et tracables pour 0.7.x.

---

## Audits associes / tickets

- 08-security.md checklist : **18 / 18 conformes**
- Le ticket [MAJ-1] est ferme par `3818933`
- Voir aussi : Audit 10 — CI/Build (Trivy gate + auto-close hardening), Audit 11 — Documentation (`.env.example` documente)

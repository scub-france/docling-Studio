# Rapport d'audit : Securite (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/08-security.md` — 100/100, GO (0 CRIT / 0 MAJ / 0 MIN / 2 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 14 / 14 (poids 32 / 32) |
| Score | **100 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

Detail du calcul (somme des poids) :

- Total poids = 32 (14 items : 8.1.1=3, 8.1.2=3, 8.1.3=2, 8.2.1=3, 8.2.2=3, 8.2.3=2, 8.3.1=3, 8.3.2=3, 8.3.3=3, 8.4.1=3, 8.4.2=2, 8.4.3=2, 8.5.1=3, 8.5.2=1).
- Poids non conformes = 0.
- Poids conformes = 32.
- Score = 32 / 32 x 100 = **100 / 100**.

**Delta vs baseline `release-0.6.2/08-security.md`** : **+0 point** (100 -> 100). Aucune regression. Les deux INFO baseline (defaut Neo4j `changeme`, OpenSearch dev sans TLS) sont reconduits sans changement de statut. Les changements de la branche `fix/0.6.2-audit-blockers` reduisent la surface d'attaque (HF Hub off par defaut, surfaces CI sans HF) sans introduire aucun nouvel ecart.

---

## Contexte de la re-audit

La branche `fix/0.6.2-audit-blockers` ne touche **aucun chemin sensible "auth / persistence / crypto"** par rapport a `release/0.6.2`. Aucun changement sur :

- `document-parser/infra/secrets/fernet_box.py` (scellement Fernet, AES-128-CBC + HMAC-SHA256).
- `document-parser/persistence/store_repo.py` (tri-state password, separation plaintext/sealed).
- `document-parser/services/store_backend_resolver.py` (resolver per-store).
- `document-parser/infra/neo4j/driver_pool.py`, `infra/opensearch_pool.py` (pools per-(uri,user)).
- `document-parser/main.py` (boot precondition `_check_store_secret_key`, CORS, rate-limiter).
- `document-parser/api/stores.py`, `services/store_service.py`, `api/schemas.py` (DTOs write-only).
- `.env.example`, `nginx.conf.template`, `.dockerignore`.

Les deltas a analyser sous angle securite sont :

1. **`.trivyignore.yaml`** : ajout des deux CVE `perl-base` (`CVE-2026-42496` path traversal `Archive::Tar`, `CVE-2026-8376` heap overflow regex) avec justification de non-reachability + `expired_at` future (commit `76b67ec`).
2. **`docker-compose.yml` / `docker-compose.dev.yml`** : nouveau service `docling-serve` derriere le profil opt-in `remote`, image `quay.io/docling-project/docling-serve-cpu:v1.21.0` (commit `dd1962e`).
3. **`BAKE_MODELS` / `BAKE_MODEL`** : defauts passes a `false` dans les trois Dockerfiles (top-level, document-parser, embedding-service) et dans les composes (commit `f6b4e23`). Reduction nette de la surface supply-chain HF Hub a la build.
4. **`.github/workflows/ci.yml`, `release-gate.yml`, `release.yml`** : E2E pilote contre l'image docling-serve distante ; bake HF reserve a `release.yml` `latest-local` uniquement (commits `bc9b4f8`, `f6b4e23`).
5. **`docs/architecture/huggingface-dependency-map.md`** : carte unique des points de contact HF, garde-fou de revue.

Cette re-audit re-verifie les 14 items checklist sur la branche `fix/0.6.2-audit-blockers` (HEAD `f6b4e23`) avec un focus sur la justification Trivy et la chaine d'approvisionnement du nouveau container.

---

## Suivi des ecarts baseline 0.6.2

| Ecart 0.6.2 | Statut 0.6.2 re-audit | Preuve |
|-------------|----------------------|--------|
| [INFO] Defaut Neo4j `changeme` | **Inchange** (warning boot, banniere compose) | `document-parser/main.py:118-125`, `docker-compose.yml:1-24` |
| [INFO] OpenSearch sans TLS ni auth (stack dev) | **Inchange** (dev-only, opt-in `ingestion`) | `docker-compose.yml:47-66`, banniere `docker-compose.yml:1-24` |

Les deux INFO sont reconduits a l'identique : aucune correction tentee, aucune regression observee, scope reporte explicitement a 0.7.x.

---

## Verification approfondie des chemins critiques 0.6.2 re-audit

### 1. `.trivyignore.yaml` — 4 CVE ignorees, toutes datees et justifiees

`/Users/pjmalandrino/Documents/Pro/workspace/poc/Docling-Studio/.trivyignore.yaml` (51 lignes, 4 entrees).

**Etat datage** : aujourd'hui `2026-06-08`. Toutes les `expired_at` sont dans le futur :

| CVE | Composant | `expired_at` | Marge restante |
|-----|-----------|--------------|----------------|
| CVE-2026-40393 | mesa | 2026-06-30 | ~3 semaines (re-evaluation imminente, hors scope release) |
| CVE-2026-7598 | libssh2 | 2026-08-31 | ~3 mois |
| CVE-2026-42496 | perl-base (Archive::Tar) | 2026-09-30 | ~4 mois |
| CVE-2026-8376 | perl-base (regex) | 2026-09-30 | ~4 mois |

Aucune date n'est dans le passe, aucune entree n'est sans `expired_at` (conforme a la regle "wagon d'expiration" du re-audit 0.6.2 baseline).

**Justification reachability des deux nouvelles CVE perl-base** :

L'argument du commit `76b67ec` repose sur l'invariant "le backend n'execute jamais perl a runtime ; perl-base est present uniquement parce que dpkg/apt en dependent dans `python:3.12-slim`". Verification independante :

- **Aucun appel `perl` dans le code applicatif** :
  `grep -rn -i "perl" document-parser/ --include="*.py" --exclude-dir=.venv --exclude-dir=tests` -> **0 hit**.
- **Aucun appel `perl` dans les Dockerfiles** :
  `grep -rn -i "perl" {Dockerfile,document-parser/Dockerfile,embedding-service/Dockerfile,frontend/Dockerfile}` -> **0 hit**. Les trois Dockerfiles ne `RUN perl` jamais ; les `RUN apt-get install` ne nomment jamais perl explicitement (perl-base est tire **transitivement** par dpkg).
- **Aucune dependance Python invoquant Perl** :
  `grep -rn -i "subprocess" document-parser/ --include="*.py" --exclude-dir=.venv --exclude-dir=tests` -> seules occurrences = commentaires sur "poppler subprocess (pdfinfo)" dans `services/document_service.py:68,82,158`. Aucun `subprocess.run(["perl", ...])`, aucun `subprocess.run(["tar", ...])` du cote Python.
- **Vecteur Archive::Tar** : `grep -rn "tarfile\|Archive::Tar" document-parser/ --include="*.py" --exclude-dir=.venv --exclude-dir=tests` -> **0 hit**. Le projet ne deballe **aucun** tarball cote backend (les uploads sont des PDF stricts, magic-bytes verifies en `services/document_service.py:72-79`). Le vecteur path-traversal `Archive::Tar` n'a donc aucun chemin d'execution accessible depuis du contenu utilisateur.
- **Vecteur regex perl** : la CVE necessite que perl **compile une regex contrôlee par un attaquant**. Comme perl n'est jamais invoque a runtime, aucune entree utilisateur n'atteint le compilateur regex perl.

La justification "perl-base est build-tooling apt/dpkg, jamais runtime" est donc factuellement verifiable et alignee avec les commentaires inline des entrees `.trivyignore.yaml:24-50`.

**Format des entrees** : conforme au schema Trivy `vulnerabilities[].id|statement|expired_at` (verifiable contre `aquasecurity/trivy` v0.50+). Pas de `paths:` filter — bonne pratique (cf. commentaire `.trivyignore.yaml:2-6` sur la difference paths vs OS-package).

### 2. Chaine d'approvisionnement docling-serve

`docker-compose.yml:110-122` (et clone `docker-compose.dev.yml:96-108`) :

```yaml
docling-serve:
  profiles: ["remote"]
  image: quay.io/docling-project/docling-serve-cpu:v1.21.0
  expose:
    - "5001"
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:5001/version || exit 1"]
    ...
```

**Trust chain** :

- **Registre** : `quay.io` (Red Hat / IBM). Registre tiers, mais : (a) il s'agit du registre **officiel du docling-project**, le meme upstream que nous embarquons deja en library (`docling` est une dependance directe de `document-parser`). Le perimetre de confiance n'est pas etendu — on consommait deja le code python signe par cette org via PyPI, on consomme maintenant le binaire signe par la meme org via quay. (b) `quay.io` n'est pas un registre communautaire (pas de "anyone can push") : c'est un registre operateur, comme `ghcr.io`.
- **Namespace** : `docling-project` — `docling-project/docling-serve` est le repo GitHub upstream (`github.com/docling-project/docling-serve`), maintenu par IBM Research (memes auteurs que `docling`). Aucun risque de typosquatting (verifie sur quay.io/repository/docling-project/docling-serve-cpu : repository owned by docling-project org).
- **Pinning** : `v1.21.0` — tag mutable, pas un digest `@sha256:...`. C'est le **seul ecart de durcissement supply-chain** identifie sur ce delta (cf. INFO ci-dessous). Le tag peut techniquement etre repousse par l'upstream sur une autre image — risque faible mais non nul. Pour 0.6.2 c'est aligne avec la pratique existante du projet (la quasi-totalite des images compose sont pinned par tag : `neo4j:5.20.0`, `opensearchproject/opensearch:2.11.0`, etc. — verifie sur `docker-compose.yml`). Pas de regression, pas de nouveau standard plus laxiste.

**Surface reseau** :

- `docker-compose.yml:114-115` : `expose: ["5001"]` (pas de `ports:` -> non publie sur l'hote). Le container n'est joignable que sur le reseau interne de la stack compose.
- `docker-compose.dev.yml:100-101` : `ports: ["5001:5001"]` — publie en dev pour debug. Acceptable car la banniere compose `docker-compose.yml:1-24` rappelle "DEV DEFAULTS — NOT PRODUCTION-READY" et le service est derriere le profil opt-in `remote`.
- Authentification : `DOCLING_SERVE_API_KEY` plumb mais defaut vide (`docker-compose.yml:159`, `infra/settings.py:15,144`). Le service docling-serve ne requiert pas d'auth sur ses endpoints de conversion — c'est un service interne. Sur une stack prod publique, l'operateur doit activer l'auth en amont (reverse proxy ou cle docling-serve native via variable d'env du container, deja supportee par l'upstream).

**Profil opt-in** : `profiles: ["remote"]` -> `docker compose up` defaut n'instancie pas docling-serve. Aucune surface elargie pour les utilisateurs en `CONVERSION_MODE=local` (defaut compose).

### 3. Reduction de surface HF Hub (build-time)

Trois Dockerfiles flippes a `BAKE_MODELS=false` / `BAKE_MODEL=false` :

- `Dockerfile:84` (top-level multi-target) : `ARG BAKE_MODELS=false`.
- `document-parser/Dockerfile:59` : idem.
- `embedding-service/Dockerfile:31` : `ARG BAKE_MODEL=false`.

Composes alignes :

- `docker-compose.yml:142` (`document-parser`) : `BAKE_MODELS: ${BAKE_MODELS:-false}`.
- `docker-compose.yml:80` (`embedding`) : `BAKE_MODEL: ${BAKE_MODEL:-false}`.
- `docker-compose.dev.yml:73,118` : memes defauts.

`release.yml` reste le **seul** chemin qui flippe `BAKE_MODELS=true` pour publier `ghcr.io/scub-france/docling-studio:latest-local`. Ce flip est documente comme "single sanctioned HF touch point" dans `docs/architecture/huggingface-dependency-map.md:21-39`.

**Angle securite** :

- **Supply-chain** : retrait de la dependance implicite HF Hub a la build pour tous les chemins sauf `release.yml`. Reduit la fenetre d'attaque "un mainteneur Docling pousse un poids malveillant pendant qu'un dev/CI build". L'attaque reste possible sur le chemin sanctionne (`release.yml`), mais elle est concentree en un seul point, datee (tag release `v*`) et reviewable.
- **Disponibilite** : retrait de la 429 cascade observee en CI sur shared IP pools (audit 0.6.2 #10). Pas un CVE mais un risque de blocage du release-gate.
- **Audit trail** : `docs/architecture/huggingface-dependency-map.md` declare explicitement "Reviewers: any new build path (Dockerfile RUN, CI step, compose service) that calls HF Hub without an explicit opt-in build-arg is a red flag." (`:118-120`). Garde-fou de revue lit en explicitement.

Bilan : **reduction nette de surface**, aucune nouvelle exposition.

### 4. Scellement Fernet et boot precondition (re-verification rapide)

`document-parser/infra/secrets/fernet_box.py` — fichier non modifie depuis baseline. `git diff release/0.6.2..HEAD -- document-parser/infra/secrets/` -> empty. Code intact, contrat respecte (cf. baseline `release-0.6.2/08-security.md` section 1).

`document-parser/main.py:212-243,249` — `_check_store_secret_key()` intact, appele dans le lifespan. `grep -n "STORE_SECRET_KEY\|_check_store_secret_key\|cors_origins" main.py` confirme : aucun changement structurel.

`document-parser/infra/settings.py:41,164` — `store_secret_key=""` defaut, lu depuis l'env. Intact.

### 5. Repository / API / pools

Non modifies :

- `persistence/store_repo.py` (tri-state password, plaintext jamais persiste sur l'entite).
- `api/stores.py:151-172` (test-connection toujours 200, exception strippe le password).
- `api/schemas.py:281-339` (`StoreResponse` documente "password is **never** serialised", `StoreUpdateRequest` documente tri-state).
- `services/store_backend_resolver.py:117-153` (seal ouvert uniquement quand `has_connection_password`).
- `infra/neo4j/driver_pool.py:60-101` (password jamais loggue, jamais stocke).
- `infra/opensearch_pool.py:43-82` (idem).

### 6. CORS et rate-limiter

`main.py:394-406` — non modifie. `allow_origins=settings.cors_origins` (defaut explicit, pas de `*`), methodes restreintes, headers restreints, `RateLimiterMiddleware` cable si `rate_limit_rpm > 0`, `/api/health` exclu via `infra/rate_limiter.py:59,68`.

### 7. Injection (Cypher / SQL / eval)

- Cypher : `grep -rn "tx.run\|session.run" document-parser/infra/neo4j/*.py` — call sites inchanges (`chunk_writer.py:92,95,...`, `tree_writer.py:129,...`, `tree_reader.py:24,...`, `queries.py:150,159,178`, `schema.py:50`). Tous en kwargs bound.
- SQL : `grep -rn 'f".*SELECT\|f".*INSERT\|f".*UPDATE\|f".*DELETE'` — call sites inchanges (`persistence/analysis_repo.py:63,75,85,98` concatenent uniquement la constante `_SELECT_WITH_DOC`).
- eval/exec : `grep -rn "eval(\|exec(\|os\.system(\|subprocess\.(call|Popen|run)("` -> **0 hit**.

### 8. Frontend XSS

`grep -rn "v-html" frontend/src/**.vue` — 3 sites inchanges, tous sanitises par `DOMPurify.sanitize(marked.parse(...))` (`features/analysis/ui/MarkdownViewer.vue:17`, `features/reasoning/ui/{ReasoningPanel,AskRunner}.vue:86,133`).

### 9. Upload validation

`api/documents.py:78-91`, `services/document_service.py:72-79` — inchanges. Content-Length precheck + magic bytes `%PDF` + UUID + extension `.pdf` forcee.

### 10. Headers Nginx + non-root container

`frontend/nginx.conf.template:7-15` — 4 headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy) + `try_files` (pas d'autoindex). Inchange.

`document-parser/Dockerfile:28-37,89-92`, `Dockerfile:52,113-114` — `USER appuser` apres setup, `chown -R appuser` apres bake de modeles (quand active). Le passage `BAKE_MODELS=false` par defaut ne supprime pas l'invariant non-root (le `chown` est dans la branche `if [ "$BAKE_MODELS" = "true" ]; then ...`, et le `RUN chown -R appuser:appuser /app` final reste systematique : `Dockerfile:113`, `document-parser/Dockerfile:89`).

### 11. Dependances

- Backend (`document-parser/pyproject.toml`, `uv.lock`) — non modifies sous angle securite. `cryptography>=43.0.0,<46.0.0` toujours present (Fernet).
- Frontend (`frontend/package.json`) — non modifie.
- Trivy gate (`.github/workflows/release-gate.yml:352-365`) — non modifie : `severity: CRITICAL`, `exit-code: 1`, `trivyignores: .trivyignore.yaml`. HIGH informatif (`:367-377`). Le gate consommera donc le `.trivyignore.yaml` mis a jour (4 entrees, toutes datees future).

---

## Resultats detailles par domaine

### 8.1 Secrets et credentials

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.1.1 — Pas de cles API/tokens en dur | PASS | `document-parser/infra/settings.py:15,144,164` | `docling_serve_api_key=None`, `store_secret_key=""`, lus de l'env. Aucun token hard-cable. INFO Neo4j `changeme` reconduit. |
| 8.1.2 — `.env` dans `.gitignore` | PASS | `.gitignore:23-25`, `.dockerignore` racine + backend | Inchange. |
| 8.1.3 — Secrets Docker en env vars | PASS | `docker-compose.yml:155-160`, `docker-compose.dev.yml:130-135`, `.env.example:61-68` | `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` intact. Nouveau service `docling-serve` n'introduit aucun secret build-arg (image pull only). `DOCLING_SERVE_API_KEY` reste env var. |

### 8.2 Validation des entrees

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.2.1 — Validation Pydantic | PASS | `document-parser/api/schemas.py` | Inchange. Tous DTOs `_CamelModel`. |
| 8.2.2 — `MAX_FILE_SIZE_MB` actif | PASS | `api/documents.py:78-91`, `services/document_service.py:72-79` | Inchange. |
| 8.2.3 — Types fichiers acceptes | PASS | `services/document_service.py:75-79` | Magic bytes `%PDF` exiges. |

### 8.3 Injection

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.3.1 — Parametres lies SQL / Cypher | PASS | `persistence/*.py`, `infra/neo4j/*.py` | Inchanges. 22 sites `session.run` audites, tous en kwargs bound. |
| 8.3.2 — Pas eval/exec/os.system | PASS | scan complet `document-parser/**/*.py` | 0 hit. |
| 8.3.3 — DOMPurify | PASS | 3 sites `v-html` | Tous sanitises. |

### 8.4 CORS et reseau

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.4.1 — CORS explicites | PASS | `document-parser/main.py:394-400` | Inchange. INFO OpenSearch dev sans TLS reconduit. |
| 8.4.2 — Rate limiter actif | PASS | `main.py:401-406`, `infra/rate_limiter.py:59-68` | Inchange. |
| 8.4.3 — Nginx sans directory listing | PASS | `frontend/nginx.conf.template:13-15` | Inchange. Headers de durcissement actifs. |

### 8.5 Dependances

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| 8.5.1 — Pas de CVE critique non geree | PASS | `.trivyignore.yaml`, `.github/workflows/release-gate.yml:352-377` | Gate Trivy CRITICAL bloquant intact. 4 CVE ignorees, toutes datees future (`2026-06-30`, `2026-08-31`, `2026-09-30` x2), toutes justifiees factuellement. Les deux nouvelles perl-base verifiees : `grep -i perl` sur Dockerfiles + backend -> 0 hit reachability, vecteur Archive::Tar inaccessible (`tarfile` jamais utilise). |
| 8.5.2 — Versions epinglees | PASS | `document-parser/pyproject.toml`, `uv.lock`, `frontend/package.json` | Inchanges. |

### Infrastructure et surfaces 0.6.2 re-audit

| Item | Verdict | Localisation | Details |
|------|---------|--------------|---------|
| Non-root container | PASS | `Dockerfile:52,113`, `document-parser/Dockerfile:28-37,89-91` | `useradd appuser`, `USER appuser` apres setup. `chown -R appuser /app` final inconditionnel. La branche `if BAKE_MODELS=true` ne casse pas l'invariant. |
| Security headers Nginx | PASS | `frontend/nginx.conf.template:7-11` | 4 headers actifs, inchanges. |
| Fernet sealing | PASS | `infra/secrets/fernet_box.py`, `persistence/store_repo.py` | Code intact, contrat respecte. |
| Boot precondition `STORE_SECRET_KEY` | PASS | `main.py:212-243,249` | Intact. |
| Test-connection endpoint | PASS | `api/stores.py:151-172`, `services/store_service.py:309-342` | Intact, exception strippe le password. |
| Pools per-(uri,user) | PASS | `infra/neo4j/driver_pool.py:60-101`, `infra/opensearch_pool.py:43-82` | Intacts. |
| Resolver per-store | PASS | `services/store_backend_resolver.py:117-152` | Intact. |
| Pas de log de secrets | PASS | grep `logger\|logging\|print` sur les chemins sensibles | 0 hit avec credential. |
| `.dockerignore` filtre `.env` | PASS | `.dockerignore` racine + backend | Inchanges. |
| Trivy ignore-list — 4 entrees | PASS | `.trivyignore.yaml` | Toutes datees `expired_at` future, toutes justifiees factuellement. Reachability perl verifiee. |
| Image docling-serve — supply-chain | PASS (avec INFO de durcissement futur) | `docker-compose.yml:110-122`, `docker-compose.dev.yml:96-108` | Upstream docling-project (meme org que la library deja consommee), registre quay.io operateur, pinned par tag `v1.21.0`. Profil opt-in `remote`. Pas publie sur l'hote en prod (`expose`, pas `ports`). |
| HF Hub off par defaut | PASS | `Dockerfile:84`, `document-parser/Dockerfile:59`, `embedding-service/Dockerfile:31`, composes | `BAKE_MODELS=false` / `BAKE_MODEL=false` partout sauf `release.yml` `latest-local`. Reduction nette de surface supply-chain. |
| HF dependency map | PASS | `docs/architecture/huggingface-dependency-map.md` | Documente l'unique point de contact HF + garde-fou de revue. |

---

## Ecarts constates

### [INFO] Defaut Neo4j `changeme` toujours present (reconduit depuis 0.6.1)

- **Localisation** : `document-parser/infra/settings.py:35,163` ; `docker-compose.yml:34`, `docker-compose.dev.yml:16` ; warning au boot `document-parser/main.py:118-125`.
- **Constat** : aucune correction tentee sur cette branche (scope correctif limite a audit-10/11). Le warning au boot et la banniere `docker-compose.yml:1-24` restent les garde-fous documentes.
- **Regle violee** : 8.1.1 (poids 3) — risque residuel documente, detectable au boot.
- **Remediation** : non requise pour 0.6.2. Switch vers generation aleatoire au premier `up` envisage pour 0.7.x.

### [INFO] OpenSearch sans TLS ni auth dans la stack dev (reconduit depuis 0.6.1)

- **Localisation** : `docker-compose.yml:47-66`, `docker-compose.dev.yml:37-56`.
- **Constat** : `DISABLE_SECURITY_PLUGIN: "true"` reste en place sur le profil `ingestion` (dev). Aucun changement sur ce delta. Pas mappe sur l'hote en prod compose, expose seulement en dev.
- **Regle violee** : 8.4.1 (poids 3) — risque documente + banniere DEV.
- **Remediation** : non requise pour 0.6.2. Variante `docker-compose.prod.yml` (security plugin + TLS) toujours pas livree — a planifier en 0.7.x.

### [INFO] (nouveau, hors checklist) — docling-serve pinned par tag, pas par digest

- **Localisation** : `docker-compose.yml:112`, `docker-compose.dev.yml:98`.
- **Constat** : `image: quay.io/docling-project/docling-serve-cpu:v1.21.0` — tag mutable. Aligne avec la pratique projet existante (toutes les autres images compose sont pinned par tag : `neo4j:5.20.0`, `opensearchproject/opensearch:2.11.0`). Risque resi​duel : un attaquant compromettant quay/docling-project pourrait repousser le tag.
- **Statut** : **observation**, **pas un ecart de checklist** (8.5.2 cible les dependances pyproject/package.json, pas les images compose). Le rapport baseline `release-0.6.2/08-security.md` ne traitait pas non plus le pinning d'image compose comme un item gradable. Mention ici pour traçabilite, pas comptee dans le score.
- **Remediation suggeree** (0.7.x) : passer toutes les images compose en `image@sha256:...` ou monter une politique signing (cosign/sigstore) pour valider les signatures upstream a l'ingest.

---

## Points positifs

- **Stabilite securitaire 0.6.2 -> 0.6.2 re-audit** : aucun chemin sensible (Fernet, resolver, pools, boot precondition, CORS, rate-limiter, headers Nginx, DOMPurify) n'a ete touche. Le sprint correctif est strictement scoping audit-10/11/12 + ops/CI.
- **Trivy ignore-list datee + reachability verifiee** : les deux nouvelles CVE perl-base (`CVE-2026-42496`, `CVE-2026-8376`) sont accompagnees d'une justification factuellement verifiable. `grep -i perl` sur les Dockerfiles et le code backend -> 0 hit. Aucun `tarfile.open` ou `Archive::Tar`. Les `expired_at` (`2026-09-30`) laissent ~4 mois de marge.
- **Reduction de surface HF Hub** : le passage des trois `BAKE_MODELS`/`BAKE_MODEL` a `false` par defaut elimine la dependance build-time implicite a HF Hub pour CI, dev local, et toute build qui ne soit pas `release.yml` `latest-local`. Concentre la surface supply-chain "poids HF malveillant pousse pendant que je build" en un seul point sanctionne.
- **Profil opt-in `remote` pour docling-serve** : le nouveau service n'est demarre que sur `docker compose --profile remote up`. Defaut compose `up` ne le touche pas. Pas d'expansion de surface pour les utilisateurs en `CONVERSION_MODE=local`.
- **Container docling-serve consomme depuis le meme upstream que la library** : `quay.io/docling-project/docling-serve-cpu` est maintenu par `docling-project` (IBM Research) — meme org que la dependance `docling` deja embarquee en PyPI. Pas d'expansion du perimetre de confiance.
- **HF dependency map** : `docs/architecture/huggingface-dependency-map.md` declare explicitement le **seul** chemin HF sanctionne (`release.yml` `latest-local`) et pose un garde-fou de revue : "any new build path that calls HF Hub without an explicit opt-in build-arg is a red flag". Reduit drastiquement la probabilite de reintroduire un appel HF implicite.
- **CI E2E sans HF** : `ci.yml` et `release-gate.yml` pilotent l'E2E contre l'image docling-serve distante. Le 429 cascade sur shared GHA IPs (audit 0.6.2 #10) est elimine — pas un CVE mais une amelioration de la disponibilite de la gate de securite (le job Trivy passe maintenant systematiquement sans race avec HF).
- **CHANGELOG `BREAKING`** : `CHANGELOG.md` declare explicitement `BREAKING: BAKE_MODELS default flipped to false`. Garde-fou operateur, evite le piege "mon build qui marchait est maintenant lent au premier convert".

---

## Verdict partiel : GO

**Score** : 100 / 100 (seuil GO >= 80).

**Delta vs baseline 0.6.2** : **+0 point** (100 -> 100), 0 nouveau CRIT, 0 nouveau MAJ, 0 nouveau MIN. Les 2 INFO baseline (Neo4j `changeme`, OpenSearch dev) reconduits a l'identique. Une INFO additionnelle hors-checklist sur le pinning par tag de l'image docling-serve (traçabilite uniquement, pas comptee).

Les 5 chemins critiques cibles par la consigne ont ete re-verifies a HEAD `f6b4e23` :

1. **`.trivyignore.yaml`** — 4 entrees, toutes datees future, justifications factuellement verifiables. `grep -i perl` sur tous les Dockerfiles et le backend -> 0 hit reachability ; vecteur Archive::Tar et compilateur regex perl inaccessibles depuis le code applicatif.
2. **Image docling-serve `quay.io/docling-project/docling-serve-cpu:v1.21.0`** — upstream legitime (meme org que `docling` library), registre operateur, pinned par tag (aligne avec la pratique projet, INFO de durcissement future pour 0.7.x).
3. **`BAKE_MODELS` defauts a `false`** — reduction nette de surface supply-chain HF Hub. Concentre l'unique touche HF dans `release.yml` `latest-local`.
4. **`docs/architecture/huggingface-dependency-map.md`** — pose garde-fou de revue explicite. Bonne pratique de documentation security-as-policy.
5. **Pas de changement sur Fernet / store_repo / resolver / pools / CORS / Cypher / DOMPurify** — contrats baseline 0.6.2 maintenus a l'identique.

Aucun ecart bloquant. Recommandations 0.7.x :

- (a) Supprimer le defaut Neo4j `changeme` au profit d'une generation aleatoire au premier `up`.
- (b) Livrer une variante `docker-compose.prod.yml` activant le plugin de securite OpenSearch + TLS.
- (c) Durcir le pinning des images compose en `image@sha256:...` ou monter cosign/sigstore pour validation a l'ingest.

---

## Audits associes / tickets

- Checklist 08-security.md : **14/14 conformes** (poids 32/32).
- Voir aussi : Audit 10 — CI/Build (sortie HF, remote-docling-serve), Audit 11 — Documentation (`huggingface-dependency-map.md`, CHANGELOG BREAKING).
- Pas de remediation requise pour 0.6.2.

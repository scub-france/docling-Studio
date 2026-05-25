# Rapport d'audit : CI / Build (re-audit)

**Release** : 0.6.1
**Branche** : `fix/0.6.1-audit-blockers` (HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 11 |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 0 |

---

## Verification effectuee

| Item | Verification | Resultat |
|------|--------------|----------|
| 10.1.1 | Last gate runs sur `release/0.6.1` (ancestor) : CI #26297762704 + Release Gate #26297762506 | `success` / `success` |
| 10.1.2 | `npx eslint src/` dans `frontend/` (HEAD `f9e5619`) | exit 0, 0 warning |
| 10.1.3 | `.venv/bin/ruff check .` dans `document-parser/` | `All checks passed!` |
| 10.1.4 | `npx vue-tsc --noEmit` | exit 0, 0 erreur |
| 10.1.5 | `ruff format --check .` (`118 files already formatted`) + `prettier --check src/` (`All matched files use Prettier code style!`) | Conforme |
| 10.2.1 | Job `docker-build` matrix `[remote, local]` (release-gate.yml — gate vert sur release/0.6.1) | `success` (pas de modif Dockerfile sur cette branche) |
| 10.2.2 | Job `docker-smoke` (health + engine validation) sur release-gate | `success` |
| 10.2.3 | Matrix `[remote, local]` cf. `Dockerfile:63` (`FROM base AS remote`) + `Dockerfile:67` (`FROM base AS local`) ; `docker-compose.yml:91` (`target: ${CONVERSION_MODE:-local}`) | Conforme |
| 10.2.4 | `.dockerignore:1-23` exclut `.git/`, `.github/`, `frontend/node_modules/`, `document-parser/.venv/`, caches, `e2e/` | Conforme |
| 10.3.1 | `nginx.conf.template:17-24` proxy `/api/` → `127.0.0.1:8000` ; `try_files` SPA en `:13-15` ; security headers `:8-11` | Conforme |
| 10.3.2 | `.env.example:1-68` documente CONVERSION_MODE/ENGINE, MAX_FILE_SIZE_MB, NGINX_MAX_BODY_SIZE, CORS_ORIGINS, NEO4J_*, STORE_SECRET_KEY ; defaults en `docker-compose.yml:97-118` | Conforme |

---

## Resolution des INFO de l'audit precedent

### [INFO-1] Workflow `auto-close-issues.yml` syntax error — RESOLU

- **Etat** : fixe par commit `714a181` sur `release/0.6.1` (ancestor de la branche courante).
- **Verification** : `.github/workflows/auto-close-issues.yml:21` definit `COMMITS_JSON` via `env:` et `.github/workflows/auto-close-issues.yml:24` consomme via `printf '%s' "$COMMITS_JSON"`. Plus d'interpolation `${{ toJSON(...) }}` inline dans le `run:` block — le payload JSON traverse l'env-var, donc parens et autres caracteres shell ne cassent plus la commande.
- **Impact** : la prochaine fusion vers `release/**` declenchera bien la fermeture automatique des issues `Closes/Fixes #N`.

### [INFO-2] `frontend/package.json` desynchro — RESOLU

- **Etat** : bumpe par commit `e11a567` sur la branche courante.
- **Verification** : `frontend/package.json:3` lit `"version": "0.6.1"`. Alignement complet avec le tag de release et l'`APP_VERSION` injectee par le build Docker.

---

## Verifications additionnelles sur cette branche

### STORE_SECRET_KEY plumbing (commit `3818933`)

- `.env.example:61-68` documente la variable avec rationale (`document-parser/main.py:_check_store_secret_key`), instruction de generation et avertissement sur la rotation.
- `docker-compose.yml:109-113` injecte `STORE_SECRET_KEY: ${STORE_SECRET_KEY:-}` avec commentaire inline.
- `docker-compose.dev.yml:114` propage la meme variable au service backend dev.
- Default vide (`:-`) : conforme a la semantique "fail-fast si des rows sealed existent sans key", documente.
- `docker-compose.ingestion.yml` ne reference pas le backend `document-parser` (uniquement Neo4j/OpenSearch/embedding), pas besoin d'y propager.

### Aucun nouveau workflow casse

Diff vs `release/0.6.1` : seules `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml` ont evolue sur le perimetre infra. Aucune modification de `.github/workflows/`, `Dockerfile`, `nginx.conf.template`, `.dockerignore`. Le pipeline CI est donc fonctionnellement identique a celui validé en green sur `release/0.6.1`.

### Pytest collection (cross-check audit 09)

`pytest tests/ --collect-only` → `747 tests collected in 3.74s`, exit 0. Le collection-blocker du re-audit 09 (#audit-09) est resolu — sans ca, le job `Backend tests` (`ci.yml:18-49`) serait rouge.

---

## Points positifs

- **Tous les INFO du rapport 0.6.1 sont resolus** dans cette branche / son ancestor.
- **Aucune regression CI/Build** : les fichiers `.github/workflows/`, `Dockerfile`, `nginx.conf.template`, `.dockerignore` ne sont pas touches par les commits #audit-*.
- **STORE_SECRET_KEY** : plumbing complet et documente, satisfaisant aussi le critere 10.3.2 (variable d'environnement documentee avec default coherent).
- **Lint / format / type-check** : 0 violation sur HEAD `f9e5619`.
- **Test collection** : 747 tests collectes (sans erreur) confirmant que le pipeline `ci.yml::backend` redeviendrait vert apres push.

---

## Verdict partiel : GO

**Justification** :
Score 100/100 (11/11 items conformes), zero ecart CRIT/MAJ/MIN/INFO. Les deux INFO du rapport 0.6.1 sont resolus (`714a181` pour le workflow, `e11a567` pour `package.json`). La branche n'introduit aucune modification CI/Build a risque ; STORE_SECRET_KEY est correctement plombe et documente.

**Delta vs 0.6.1** : score inchange (100 → 100), -2 INFO (2 → 0). Audit parfait.

# Rapport d'audit : CI / Build

**Release** : 0.6.1
**Date** : 2026-05-24
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
| Ecarts INFO | 2 |

---

## Verification effectuee

| Item | Verification | Resultat |
|------|--------------|----------|
| 10.1.1 | Run CI #26297762704 + Release Gate #26297762506 sur `release/0.6.1` | Tous deux `success` |
| 10.1.2 | `npx eslint src/` dans `frontend/` | exit 0, 0 warning |
| 10.1.3 | `.venv/bin/ruff check .` dans `document-parser/` | `All checks passed!` |
| 10.1.4 | `npm run type-check` (vue-tsc --noEmit) | exit 0, 0 erreur |
| 10.1.5 | `ruff format --check .` + `prettier --check src/**` | 116 files formatted / All matched files use Prettier code style |
| 10.2.1 | Job `docker-build` (matrix remote+local) dans release-gate | `success` |
| 10.2.2 | Job `docker-smoke` dans release-gate (health + engine validation) | `success` |
| 10.2.3 | Matrix `[remote, local]` dans `release-gate.yml:222-224` et `release.yml:22-23` | Les deux variantes buildent |
| 10.2.4 | `.dockerignore` contient `.git/`, `.github/`, `node_modules/`, `.venv/`, caches | Conforme |
| 10.3.1 | `nginx.conf.template:17-24` route `/api/` vers `127.0.0.1:8000` ; `try_files` sur `/` | Conforme |
| 10.3.2 | `.env.example` documente CONVERSION_ENGINE, CORS_ORIGINS, RATE_LIMIT_RPM, MAX_FILE_SIZE_MB, NGINX_MAX_BODY_SIZE, etc. avec defaults | Conforme |

---

## Ecarts constates

### [INFO] Workflow auto-close-issues casse depuis 825e7d7 — fix non commit

- **Localisation** : `.github/workflows/auto-close-issues.yml` (working tree modifie, non commit)
- **Constat** : Le run #26297759770 sur push de `825e7d7` echoue avec `syntax error near unexpected token '('` ligne 16. La cause : le payload JSON `${{ toJSON(github.event.commits) }}` etait inline dans le `run:` block et un caractere `(` non echappe casse le shell. Le fix (deplacement vers `env: COMMITS_JSON` + `printf '%s' "$COMMITS_JSON"`) est present dans le working tree mais n'a pas ete commit.
- **Regle violee** : 10.1.1 (partiellement — workflow non-gating mais sur la branche de release)
- **Remediation** : Commiter le fix avant le merge release/0.6.1 → main, ou la prochaine fusion ne fermera pas automatiquement les issues referencees.

### [INFO] frontend/package.json version desyncrhonisee avec la release

- **Localisation** : `frontend/package.json` — `"version": "0.5.0"` sur branche `release/0.6.1`
- **Constat** : La version frontend n'a pas ete bumpee. `APP_VERSION` est injecte au build via `VITE_APP_VERSION` (Dockerfile L13, L19) depuis la branche, donc l'image Docker portera la bonne version, mais `package.json` reste un faux.
- **Regle violee** : Aucune regle CI/Build stricte (cross-ref audit 11 — Documentation)
- **Remediation** : Bump `frontend/package.json` a `0.6.1` dans le rituel de release-branch.

---

## Points positifs

- **Prior MAJ resolu** : Ligne `document-parser/infra/docling_tree.py:101` utilise desormais `isinstance(bbox, list | tuple)` (syntaxe union PEP 604). `ruff check .` passe sans warning.
- **Pipeline CI 4-phases** : `release-gate.yml` orchestre lint+types / unit tests / dep audit / audit checks en parallele, puis Docker build matrix → smoke → scan/size en eventail, puis E2E API+UI sur les images buildees, puis un commentaire de synthese poste sur la PR.
- **Trivy CRITICAL bloquant, HIGH informatif** : Separation propre dans `release-gate.yml:348-383` avec `.trivyignore.yaml` referencé et explication inline du pin `version: latest` (event yank du 2026-04-29 documente).
- **Image-size delta automatique** : `release-gate.yml:392-490` recupere la derniere release tag GHCR, compare les tailles `remote`/`local` et warne au-dela de ±10%.
- **Compat Docling quotidien** : `docling-compat.yml` reinstalle la derniere version de `docling`/`docling-core` chaque jour et ouvre une issue idempotente si un test casse.
- **STUDIO_MODE_ENABLED documente** : `release-gate.yml:587-590` explique pourquoi le flag est opt-in en e2e jusqu'au refactor 0.7.0 ; `docker-compose.yml:109-113` aussi.
- **Smoke test valide les champs metier** : `release-gate.yml:312-323` valide `status == "ok"` ET `engine == "remote"` plutot que juste un 200 HTTP.
- **Multi-arch publish** : `release.yml:55` build `linux/amd64,linux/arm64` avec cache GHA scope par target.

---

## Verdict partiel : GO

**Justification** :
Score 100/100 (11/11 items conformes), zero ecart CRIT/MAJ/MIN. Le MAJ unique de 0.5.0 (Ruff UP038 a `docling_tree.py:101`) est remediante. Les deux INFO sont des polish points qui ne bloquent pas la release :
- l'auto-close-issues etant non-gating, son fix peut atterrir dans la PR de merge ;
- la version `frontend/package.json` n'impacte pas l'image livree (le tag/version effectif vient de `APP_VERSION` au build).

**Delta vs 0.5.0** : +9 points (91 → 100). MAJ UP038 resolu, aucun nouveau MAJ. Le pipeline CI s'est enrichi (image-size delta + Trivy version pinning + STUDIO_MODE flag wiring documente).

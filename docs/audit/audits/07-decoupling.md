# Audit 07 — Decouplage

**Objectif** : verifier le decouplage entre frontend et backend, entre features, et la clarte des contrats d'interface.

**Cible** : `document-parser/`, `frontend/src/`, `docker-compose.yml`, `nginx.conf`

---

## Checklist

### 7.1 Decouplage Frontend / Backend

| # | Item | Poids |
|---|------|-------|
| 7.1.1 | Le frontend communique avec le backend uniquement via l'API REST — pas de couplage par fichier partage, DB partagee, ou import croise | 3 |
| 7.1.2 | Le contrat API est stable — les types TypeScript frontend correspondent aux schemas Pydantic backend | 3 |
| 7.1.3 | Le frontend peut tourner avec un mock du backend (les appels API sont isoles dans des fichiers `api.ts` par feature) | 2 |
| 7.1.4 | Le backend peut etre teste sans le frontend (endpoints testables via `httpx` / `TestClient`) | 2 |
| 7.1.5 | Pas de logique metier dupliquee entre front et back (ex: validation faite cote back ET reinventee cote front) | 2 |

### 7.2 Decouplage inter-features (Frontend)

| # | Item | Poids |
|---|------|-------|
| 7.2.1 | Chaque feature (`features/analysis`, `features/document`, ...) a son propre store, API client et composants UI | 2 |
| 7.2.2 | Les features ne s'importent qu'a travers leur **barrel public `index.ts`** (ou `shared/`) — aucun import dans les internes (`store`/`api`/`ui`) d'une autre feature ; invariant impose par la regle ESLint `no-restricted-imports` | 3 |
| 7.2.3 | Les types partages entre features sont dans `shared/types.ts`, pas dans une feature specifique | 2 |
| 7.2.4 | Un store Pinia n'accede pas directement au state d'un autre store (sauf via des getters exposes) | 2 |

### 7.3 Decouplage inter-couches (Backend)

| # | Item | Poids |
|---|------|-------|
| 7.3.1 | Les repos (`persistence/`) retournent des objets du domaine, pas des dicts ou des Row SQLite | 2 |
| 7.3.2 | Les adaptateurs infra n'exposent pas les types de leurs libs internes aux services (pas de types `docling.*` dans les signatures de services) | 3 |
| 7.3.3 | Le changement de base de donnees (SQLite -> PostgreSQL) ne necessite de modifier que `persistence/` | 2 |
| 7.3.4 | Le changement de framework HTTP (FastAPI -> autre) ne necessite de modifier que `api/` et `main.py` | 2 |

### 7.4 Contrats et interfaces

| # | Item | Poids |
|---|------|-------|
| 7.4.1 | Les ports dans `domain/ports.py` definissent des signatures claires avec des types du domaine | 2 |
| 7.4.2 | Les schemas Pydantic (`api/schemas.py`) documentent le contrat HTTP — pas de `dict` ou `Any` dans les responses | 2 |
| 7.4.3 | Les reponses API ont un format coherent (enveloppe, codes d'erreur normalises) | 1 |

---

## Commandes de verification

```bash
# 7.2.2 — Imports croises entre features
grep -rn "from.*features/" frontend/src/features/ --include="*.ts" --include="*.vue" | grep -v "node_modules" | grep -v "__tests__"

# 7.2.4 — Store qui accede au state d'un autre store
grep -rn "useDocumentStore\|useAnalysisStore\|useChunkingStore\|useHistoryStore\|useSettingsStore" frontend/src/features/ --include="*.ts" | grep -v "index.ts"

# 7.3.2 — Types docling qui leakent
grep -rn "from docling\|import docling" document-parser/services/ --include="*.py"

# 7.4.2 — dict ou Any dans les reponses API
grep -rn "-> dict\|-> Any\|Dict\[str, Any\]" document-parser/api/ --include="*.py"
```

---

## Regles de notation

- Tout item de poids 3 non conforme = ecart `[CRIT]`
- Tout item de poids 2 non conforme = ecart `[MAJ]`
- Tout item de poids 1 non conforme = ecart `[MIN]`

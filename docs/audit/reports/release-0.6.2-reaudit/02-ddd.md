# Rapport d'audit : Domain-Driven Design (DDD) — re-audit

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`, HEAD `f6b4e23`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.6.2/02-ddd.md` (97/100, GO, 0/0/1/0)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 17 / 18 |
| Score | 97 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

Detail du calcul (poids totaux = 35) — identique a la baseline :

- Items poids 3 conformes : 2.1.1, 2.1.2, 2.2.3, 2.4.2, 2.5.3 (15/15).
- Items poids 2 conformes : 2.1.3, 2.1.4, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.3, 2.5.1, 2.5.2 (18/18).
- Items poids 1 conformes : 2.2.4, 2.3.2, 2.3.3 (3/3).
- Carry-over 0.5.0 / 0.6.1 / 0.6.1-reaudit / 0.6.2 sur 2.4.2 (immutabilite type-system des entites mutables) reste en MIN — invariant protege par les methodes de transition, pas par le type.

```
score = (35 - 1) / 35 * 100 ≈ 97.1 → 97
```

---

## Perimetre du diff vs baseline 0.6.2

Entre `051ac4a` (HEAD 0.6.2 audit initial) et `f6b4e23` (HEAD fix branch), les changements sont **exclusivement ops/CI/docs/tests** :

- `.github/workflows/{ci.yml,release-gate.yml,release.yml}`, `.trivyignore.yaml`
- `Dockerfile`, `document-parser/Dockerfile`, `embedding-service/Dockerfile`
- `docker-compose.yml`, `docker-compose.dev.yml`
- `CHANGELOG.md`, nouveau `docs/architecture/huggingface-dependency-map.md`
- Rapports d'audit 0.6.2 (initial + reaudit en cours)
- `document-parser/tests/test_chunking.py` : un seul test bascule de l'instanciation `LocalChunker()` reelle vers un `AsyncMock` du port `DocumentChunker`

**Zero modification** dans `document-parser/{domain,services,api,persistence,infra}/` ni dans `frontend/src/`. Le poste DDD du code est strictement identique a la baseline.

---

## Verification par item

Toutes les citations de la baseline restent valides (aucun fichier `domain/`, `services/`, `api/`, `persistence/`, `frontend/src/` modifie). Resume :

### 2.1 Bounded Contexts

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 2.1.1 | Contextes metier identifies et isoles | 3 | OK — inchange |
| 2.1.2 | Pas de god object partage entre contextes | 3 | OK — inchange |
| 2.1.3 | Frontieres entre contextes explicites (DTOs / ports) | 2 | OK — **renforce** par le passage du test `test_rechunk_with_serve_document_json` a un mock du port `DocumentChunker` (`document-parser/tests/test_chunking.py:478-500`) — demontre la testabilite des ports |
| 2.1.4 | Frontend respecte les memes bounded contexts | 2 | OK — inchange |

### 2.2 Entites et Value Objects

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 2.2.1 | Entites = identite + cycle de vie | 2 | OK — inchange |
| 2.2.2 | Value objects immutables | 2 | OK — inchange |
| 2.2.3 | Pas de persistence dans les VO | 3 | OK — inchange |
| 2.2.4 | Entites portent du comportement metier | 1 | OK — inchange |

### 2.3 Ubiquitous Language

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 2.3.1 | Vocabulaire coherent domain ↔ services ↔ API ↔ frontend ↔ docs | 2 | OK — voir verifications nouvelles ci-dessous |
| 2.3.2 | Noms refletent le domaine, pas le generique | 1 | OK — `grep -nE "\b(Manager\|Handler\|Processor)\b"` sur `CHANGELOG.md`, `docs/architecture/huggingface-dependency-map.md`, `docker-compose.yml` : ZERO match |
| 2.3.3 | Statuts metier explicites (StrEnum) | 1 | OK — inchange |

**Verifications nouvelles 2.3.1 (vocabulaire dans les nouveaux artefacts)** :

- `CHANGELOG.md` `[0.6.2]` utilise systematiquement les termes du domaine : `/api/convert`, `/api/reasoning`, `ChunkPush` (ligne 54 reference l'agregat correctement), `chunks`, `analysis`, `store`. Les occurrences `job` restantes (lignes 154, 195) appartiennent aux sections `[0.6.0]` / `[0.5.x]` et designent `AnalysisJob` ou des batches (vocabulaire legitime) — aucune nouvelle introduction de `job` dans la section 0.6.2.
- `docs/architecture/huggingface-dependency-map.md` utilise `infra/local_chunker.py`, `infra/local_converter.py`, `embedding-service/main.py`, `/api/convert`, `/api/reasoning`, `CONVERSION_ENGINE=local/remote` — tous termes alignes sur le code (`document-parser/infra/`, `document-parser/api/routes_convert.py`, etc.).
- Nouveau service compose `docling-serve` (`docker-compose.yml:110`) suit la convention kebab-case existante (`document-parser`, `embedding`, `neo4j`, `opensearch`, `frontend`) et reprend le nom officiel de l'image upstream (`quay.io/docling-project/docling-serve-cpu`). Aucun terme generique.

### 2.4 Agregats et invariants

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 2.4.1 | Chaque agregat a une racine claire | 2 | OK — inchange |
| 2.4.2 | Invariants metier proteges dans le domaine | 3 | OK avec MIN — inchange |
| 2.4.3 | Modifications passent par la racine | 2 | OK — inchange |

### 2.5 Repositories et anti-corruption

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 2.5.1 | Repositories manipulent des entites du domaine | 2 | OK — **renforce** : le test refactor mock le port `DocumentChunker` typant les `ChunkResult` retournes, confirmant que la frontiere du port traite des VO domaine |
| 2.5.2 | Anti-corruption HTTP via Pydantic | 2 | OK — inchange |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OK — inchange |

---

## Ecarts constates

### [MIN] Entites mutables hors du service (carry-over 0.5.0 → 0.6.2)

Strictement identique a la baseline. Voir `docs/audit/reports/release-0.6.2/02-ddd.md` section "Ecarts constates" pour le detail (`document-parser/domain/models.py:37,78,142,182,226,311`). Aucun changement de code depuis la baseline. Remediation toujours recommandee pour 0.7.x.

---

## Points positifs

- **Zero regression DDD** : aucun fichier `domain/`, `services/`, `api/`, `persistence/`, `frontend/src/` touche entre `051ac4a` et `f6b4e23`.
- **Renforcement 2.1.3 / 2.5.1** : le refactor de `test_rechunk_with_serve_document_json` (commit `bc9b4f8`) cesse d'instancier un `LocalChunker` reel et mock le port `DocumentChunker`. C'est un exemple canonique de la valeur des ports — un test qui n'a plus besoin du HuggingFace Hub parce qu'il opere a la frontiere du domaine.
- **Vocabulaire `ChunkPush` preserve** dans le CHANGELOG (`[0.6.1] - Push-chunks wire vocabulary`, ligne 54) : aucune regression du renommage `jobId → pushId` opere en 0.6.1.
- **Nouvelle documentation alignee** : `docs/architecture/huggingface-dependency-map.md` parle de `LocalChunker`, `LocalConverter`, `embedding-service`, jamais en termes generiques.
- **Nouveau service compose** : `docling-serve` suit la convention de nommage existante (kebab-case, derive du nom de l'image officielle).

---

## Verdict partiel : GO

**Justification** :

- Score 97/100 (>= 80) — identique a la baseline.
- 0 ecart CRITICAL.
- 0 ecart MAJOR.
- 1 ecart MINOR carry-over (immutabilite type-system des entites), recommande pour 0.7.x.

**Delta vs baseline 0.6.2** : **+0 (97 → 97)**.

La branche `fix/0.6.2-audit-blockers` n'a touche aucun fichier du perimetre DDD code. Les nouveaux artefacts (CHANGELOG, doc HF, compose `docling-serve`, refactor test) sont conformes au vocabulaire metier et a la separation ports/adapters. Le seul changement avec impact technique sur DDD (refactor test) **renforce** 2.1.3 et 2.5.1.

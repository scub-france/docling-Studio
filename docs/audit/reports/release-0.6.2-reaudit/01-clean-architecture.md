# Rapport d'audit : Hexagonal Architecture (ports & adapters) — Re-audit

**Release** : 0.6.2
**Branche** : `fix/0.6.2-audit-blockers` (HEAD `f6b4e23`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.6.2/01-clean-architecture.md` (97/100, GO, 0/0/1/1)

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 1 |
| Écarts INFO | 1 |

Détail du calcul (somme des poids) :

- Total poids = 32
- Poids conformes = 31 (1.1.1=3, 1.1.2=3, 1.1.3=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.2.3=2, 1.2.4=2, 1.3.1=3, 1.3.3=2, 1.4.1=3, 1.4.2=2)
- Poids non conformes = 1 (1.3.2=1)
- Score = 31 / 32 × 100 = **96.875 → 97 / 100**

---

## Périmètre du re-audit

Les huit commits de remédiation `release/0.6.2..fix/0.6.2-audit-blockers` ne touchent **aucun fichier de production backend** dans `domain/`, `services/`, `api/`, `infra/`, ni `persistence/`. Vérification :

```
git log --oneline release/0.6.2..HEAD -- \
    document-parser/domain/ document-parser/services/ \
    document-parser/api/ document-parser/infra/ \
    document-parser/persistence/
→ (zéro commit)
```

Les seuls fichiers backend modifiés sont :

- `document-parser/Dockerfile` — `ARG BAKE_MODELS=true → false` (build-time concern, sans impact code applicatif).
- `document-parser/tests/test_chunking.py` — mock du port `DocumentChunker` au lieu d'instancier `LocalChunker` (renforce l'hexagonal, ne le viole pas).

Le reste de la remédiation est : docs (`docs/audit/reports/release-0.6.2/*`, `docs/architecture/huggingface-dependency-map.md`, `CHANGELOG.md`), CI (`.github/workflows/*.yml`), compose (`docker-compose*.yml`, profil `remote` ajoutant le service `docling-serve`), images (`Dockerfile`, `embedding-service/Dockerfile`), Trivy (`.trivyignore.yaml`). Aucune de ces zones n'est dans le périmètre d'audit-01.

Le re-audit consiste donc à : (1) re-jouer les vérifs grep du baseline pour confirmer la stabilité ; (2) qualifier le bascule docling-serve (consommé via `ServeConverter`, déjà existant) ; (3) qualifier les nouveaux fichiers (compose, doc) hors couche application.

---

## Écarts constatés

### [MIN] Transformations camelCase contournées dans les schemas inline de `api/graph.py` et `api/reasoning.py` (inchangé vs initial 0.6.2)

- **Localisation** :
  - `document-parser/api/graph.py:30-53` — `GraphNode`, `GraphEdge`, `GraphResponse` (vérifié : `class GraphNode(BaseModel)` l.30, `class GraphEdge(BaseModel)` l.38, `class GraphResponse(BaseModel)` l.46).
  - `document-parser/api/reasoning.py:30-48` — `ReasoningRunRequest`, `ReasoningIterationResponse`, `ReasoningResultResponse` (vérifié : l.30, l.36, l.45).
- **Constat** : Identique au rapport initial 0.6.2 et au re-audit 0.6.1. `document-parser/api/schemas.py:24-30` continue d'exposer `_CamelModel(BaseModel)` avec `alias_generator=_to_camel`, partagé par toutes les autres réponses (`HealthResponse`, `DocumentResponse`, etc.). Les six schemas locaux des routes graph et reasoning héritent toujours de `BaseModel` brut. Périmètre `fix/0.6.2-audit-blockers` strictement orienté blockers CI/build/security : aucun commit ne traite ce MIN.
- **Règle violée** : 1.3.2 — *Les transformations camelCase/snake_case restent dans `api/schemas.py`* (poids 1).
- **Remédiation** : Déplacer ces six classes dans `api/schemas.py` en faisant hériter `_CamelModel`, ou les redéfinir localement avec la même `ConfigDict`. Coordonner avec les stores Pinia `features/graph` et `features/reasoning` (changement de contrat). Reportable au prochain cycle — sans impact bloquant.

---

### [INFO] Accès direct à `os.environ` dans deux modules `infra/` au lieu de passer par `infra/settings.py` (inchangé vs initial 0.6.2)

- **Localisation** :
  - `document-parser/infra/secrets/fernet_box.py:126` — `raw = os.environ.get("STORE_SECRET_KEY")` (lecture, vérifié à HEAD).
  - `document-parser/infra/docling_agent_reasoning.py:61` — `os.environ["OLLAMA_HOST"] = provider.host` (écriture forcée pour la lib `docling-agent`, vérifié à HEAD).
- **Constat** : Identique au rapport initial. Deux exceptions documentées par leurs docstrings respectifs (factory paresseuse process-wide pour `fernet_box`, contrainte API upstream non négociable pour `docling-agent` côté `OLLAMA_HOST`). `infra/settings.py` reste la source canonique pour tout le reste du code (notamment `local_converter.py` et `serve_converter.py`).
- **Règle visée** : 1.4.2 — *Les valeurs de config viennent de `infra/settings.py`* (poids 2). L'item reste **conforme** au scoring : il s'agit d'exceptions documentées, pas de constantes en dur.
- **Remédiation suggérée** : Inchangée vs initial. (1) Router la lecture `STORE_SECRET_KEY` via `settings.store_secret_key` quand `settings` est garanti construit à l'import. (2) `OLLAMA_HOST` dépend de la PR upstream `docling-agent` (cf. mémoire utilisateur `project_docling_agent_pr.md`). Aucune action requise pour 0.6.2.

---

## Points positifs

- **Aucune régression introduite par la remédiation.** `git log --oneline release/0.6.2..HEAD -- document-parser/{domain,services,api,infra,persistence}/` → zéro commit. Les huit commits de fix touchent exclusivement Docker, CI, compose, Trivy, docs et un seul test (`test_chunking.py`). Le périmètre application reste figé sur l'état audité initialement.
- **Hexagonal layering intact à HEAD `f6b4e23`.** Vérifications re-jouées :
  - `grep -rn "from fastapi\|from aiosqlite\|from pydantic\|import fastapi\|import aiosqlite\|import pydantic" document-parser/domain/` → zéro hit (item 1.1.1).
  - `grep -rn "from fastapi\|import fastapi" document-parser/services/` → zéro hit (item 1.2.1).
  - `grep -rn "from persistence\|import persistence" document-parser/api/` → zéro hit (item 1.3.1).
  - `grep -rn '^from infra\|^import infra' document-parser/services/ document-parser/api/` → zéro hit top-level.
  - `grep -rn 'from infra\|import infra' document-parser/services/ document-parser/api/` → 6 hits identiques au baseline (3 sous `if TYPE_CHECKING:` dans `services/store_backend_resolver.py:40-42`, 1 commentaire l.94, 1 fragment de docstring `chunk_service.py:170`, 1 mot dans `analysis_service.py:4` au sens « infrastructure » général).
  - `grep -rn 'class.*Protocol\b' document-parser/services/ document-parser/api/ document-parser/infra/ document-parser/persistence/` → zéro hit.
- **`ServeConverter` correctement positionné comme adapter du port `DocumentConverter`.** Le bascule docling-serve de la remédiation 0.6.2 (compose, CI E2E) consomme `infra/serve_converter.py` (`class ServeConverter:` l.58). La docstring du module l.3 confirme « This adapter implements the DocumentConverter port by calling a remote ». Aucun nouveau code n'est ajouté côté backend — seul le mode d'exécution (in-process `LocalConverter` vs HTTP `ServeConverter`) change selon `DOCLING_CONVERTER` (`infra/settings.py`). Le port `DocumentConverter` reste défini à `domain/ports.py:52`. Zéro fuite cross-couche introduite par le passage à docling-serve : c'est précisément le pattern hexagonal qui rend ce switch trivial — l'`AnalysisService` ne sait pas si le `DocumentConverter` injecté est local ou distant.
- **Nouveaux fichiers livrés en remédiation : tous hors couche application.**
  - `docs/architecture/huggingface-dependency-map.md` — pure documentation (120 lignes Markdown), sans code, hors périmètre `document-parser/`.
  - `docker-compose.yml`, `docker-compose.dev.yml` — infrastructure d'orchestration containers (service `docling-serve` ajouté sous profil `remote`). Ne fait pas partie de la cible audit-01.
  - `document-parser/Dockerfile` — change uniquement `ARG BAKE_MODELS=true → false`, contrôle build-time pour la fenêtre HF Hub. Aucun impact sur les couches `domain/services/api/infra`.
- **Test `test_chunking.py::test_rechunk_with_serve_document_json` durci au passage.** Le test mocke désormais le port `DocumentChunker` (`chunker = AsyncMock(); chunker.chunk = AsyncMock(...)`) au lieu d'instancier `LocalChunker`. C'est une amélioration hexagonale : la frontière est désormais le port domaine, pas l'adapter concret. La docstring l.481-489 explique la motivation (rate-limit HF Hub) et renvoie vers `test_local_chunker.py` pour l'intégration réelle.
- **Ports stables.** `domain/ports.py` héberge toujours `DocumentConverter` (l.52), `DocumentChunker` (l.77), `DocumentRepository` (l.90), `StoreRepository` (l.111), `DocumentStoreLinkRepository` (l.125), `ChunkRepository` (l.141), `ChunkEditRepository` (l.164), `ChunkPushRepository` (l.180), `AnalysisRepository` (l.190), `EmbeddingService` (l.213), `VectorStore` (l.225), `LLMProvider` (l.280), `DocumentTreeReader` (l.313), `GraphReader` (l.344), `GraphWriter` (l.356), `DocumentGraphProjector` (l.394), `ReasoningRunner` (l.414). Inventaire identique au baseline.
- **Test architecture pytestarch en place et inchangé.** `document-parser/tests/test_architecture.py` continue de durcir l'ensemble : `_PYTESTARCH_EXCLUSIONS` l.38, `TestDomainLayerIsolation` l.112, `_DOMAIN_FORBIDDEN_EXTERNALS` l.196 (`fastapi`, `sqlalchemy`, `httpx`, `opensearchpy`), `_SERVICES_FORBIDDEN_EXTERNALS` l.197 (`fastapi`), `test_no_protocol_outside_domain_ports` l.226. CI inchangée : le run installe `requirements-test.txt` et exécute le test. Régression CRIT future bloquée par le pipeline.
- **Exceptions INFO `os.environ` confirmées comme exceptions documentées.** `fernet_box.py:126` et `docling_agent_reasoning.py:61` vérifiés à HEAD, citations stables. Ce n'est pas une dégradation, c'est la même observation reportée.

---

## Delta vs audit initial 0.6.2

| Item | Initial 0.6.2 | Re-audit 0.6.2 | Cause |
|------|---------------|----------------|-------|
| 1.1.1 → 1.4.1 (sauf 1.3.2) | ✅ | ✅ | Aucune régression. Zéro modification de code dans `domain/services/api/infra/persistence/`. |
| 1.3.2 (camelCase) | ❌ MIN | ❌ MIN | Inchangé — hors périmètre des fix blockers, reportable. |
| 1.4.2 (config infra) | ✅ + INFO | ✅ + INFO | Inchangé — exceptions documentées stables. |
| Score | 97 / 100 | 97 / 100 | **Aucun delta**. |
| CRIT / MAJ / MIN / INFO | 0 / 0 / 1 / 1 | 0 / 0 / 1 / 1 | **Aucun delta**. |
| Verdict | GO | GO | Audit-01 jamais bloquant, la remédiation ne le touche pas. |

**Delta numérique : 0**.

---

## Vérifications exécutées

```
# Périmètre backend touché par la remédiation
git log --oneline release/0.6.2..HEAD -- \
    document-parser/domain/ document-parser/services/ \
    document-parser/api/ document-parser/infra/ \
    document-parser/persistence/
→ (zéro commit)

# 1.1.1 — Domain ne doit importer aucune lib infra
grep -rn "from fastapi\|from aiosqlite\|from pydantic\|import fastapi\|import aiosqlite\|import pydantic" document-parser/domain/
→ (zéro hit)

# 1.2.1 — Services ne doivent pas importer FastAPI
grep -rn "from fastapi\|import fastapi" document-parser/services/
→ (zéro hit)

# 1.3.1 — API ne doit pas importer persistence
grep -rn "from persistence\|import persistence" document-parser/api/
→ (zéro hit)

# Sites d'import infra dans services/ et api/ — top-level
grep -rn '^from infra\|^import infra' document-parser/services/ document-parser/api/
→ (zéro hit)

# Sites d'import infra incluant lazy / typing-only
grep -rn 'from infra\|import infra' document-parser/services/ document-parser/api/
→ 6 hits dont 3 sous `if TYPE_CHECKING:` dans store_backend_resolver.py:40-42,
  1 commentaire l.94, 1 docstring chunk_service.py:170, 1 mot dans analysis_service.py:4.

# Protocol interdit hors domain/ports.py
grep -rn 'class.*Protocol\b' document-parser/services/ document-parser/api/ document-parser/infra/ document-parser/persistence/
→ (zéro hit)

# ServeConverter adapter
grep -n "class ServeConverter\|DocumentConverter" document-parser/infra/serve_converter.py
→ l.3 docstring "implements the DocumentConverter port", l.58 class ServeConverter

# INFO citations stables
grep -n "STORE_SECRET_KEY\|OLLAMA_HOST\|os.environ" \
    document-parser/infra/secrets/fernet_box.py \
    document-parser/infra/docling_agent_reasoning.py
→ fernet_box.py:126 et docling_agent_reasoning.py:61 confirmés à HEAD
```

---

## Verdict partiel : GO

Score 97 / 100, **zéro delta vs audit initial 0.6.2**. La remédiation `fix/0.6.2-audit-blockers` ne touche aucun fichier de production backend (`document-parser/{domain,services,api,infra,persistence}/`) : son périmètre est exclusivement Docker/CI/compose/Trivy/docs/un-test. L'unique écart MIN (1.3.2 camelCase sur 6 schemas inline `api/graph.py` + `api/reasoning.py`) reste inchangé — hors scope blockers, reportable. L'INFO non-bloquant (deux accès directs `os.environ` dans `infra/secrets/fernet_box.py:126` et `infra/docling_agent_reasoning.py:61`) reste documenté et borné aux exceptions identifiées. Le bascule docling-serve consommé par `ServeConverter` est précisément l'exemple-école d'un switch d'adapter sans toucher au domaine : il valide a posteriori l'architecture hexagonale. La règle absolue `master.md §3` (zéro CRIT) reste satisfaite. Verdict identique au rapport initial : **GO**.

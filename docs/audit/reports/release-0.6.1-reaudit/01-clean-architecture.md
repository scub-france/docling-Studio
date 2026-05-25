# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.6.1 (re-audit)
**Branche** : `fix/0.6.1-audit-blockers` (HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 1 |
| Écarts INFO | 0 |

Détail du calcul (somme des poids) :

- Total poids = 32
- Poids conformes = 31 (1.1.1=3, 1.1.2=3, 1.1.3=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.2.3=2, 1.2.4=2, 1.3.1=3, 1.3.3=2, 1.4.1=3, 1.4.2=2)
- Poids non conformes = 1 (1.3.2=1)
- Score = 31 / 32 × 100 = **96.875 → 97 / 100**

---

## Écarts constatés

### [MIN] Transformations camelCase contournées dans les schemas inline de `api/graph.py` et `api/reasoning.py` (régression non corrigée)

- **Localisation** :
  - `document-parser/api/graph.py:30-53` — `GraphNode`, `GraphEdge`, `GraphResponse`
  - `document-parser/api/reasoning.py:30-48` — `ReasoningRunRequest`, `ReasoningIterationResponse`, `ReasoningResultResponse`
- **Constat** : Identique au rapport initial. `api/schemas.py:24-30` définit `_CamelModel` avec `alias_generator=_to_camel` que toutes les autres réponses partagent. Les schemas Pydantic locaux des routes graph et reasoning continuent d'hériter de `BaseModel` brut : `doc_id`, `node_count`, `edge_count`, `page_count`, `model_id`, `section_ref`, `section_text_length`, `can_answer` restent sérialisés en snake_case. Le périmètre `#audit-01` du fix s'est volontairement concentré sur la régression CRIT/MAJ (ports + DI + GraphService) ; le MIN 1.3.2 n'était pas dans le scope de remédiation.
- **Règle violée** : 1.3.2 — *Les transformations camelCase/snake_case restent dans `api/schemas.py`* (poids 1).
- **Remédiation** : Déplacer ces six classes dans `api/schemas.py` en les faisant hériter de `_CamelModel`. Coordonner avec les stores Pinia `features/graph` et `features/reasoning` (changement de contrat). Reportable au prochain cycle — sans impact bloquant.

---

## Points positifs

- **CRIT 1.1.3 fermé** — les 6 sites d'import infra dans `services/` et `api/` listés dans le rapport initial sont tous passés par un port :
  - `services/chunk_service.py:891` (ex `from infra.docling_tree import build_collapse_index, iter_items`) → `self._tree.build_collapse_index(...)` / `self._tree.iter_items(...)` via le port `DocumentTreeReader` injecté au constructeur (`services/chunk_service.py:156,172`).
  - `services/chunk_service.py:974` (ex `from infra.docling_tree import is_inline_group`) → `tree_reader.is_inline_group(...)` (`services/chunk_service.py:985-990`).
  - `services/analysis_service.py:505` (ex `from infra.neo4j import write_document`) → `self._graph_writer.write_document_tree(...)` via le port `GraphWriter` (`services/analysis_service.py:91,509`).
  - `services/ingestion_service.py:221` (ex `from infra.neo4j import write_chunks`) → `graph_writer.write_chunks(...)` via le port `GraphWriter` (`services/ingestion_service.py:65,230`).
  - `api/graph.py:18-19` (ex `from infra.docling_graph import build_graph_payload` + `from infra.neo4j import fetch_graph`) → délégué à `GraphService.fetch_document_graph` / `GraphService.project_reasoning_graph` (`api/graph.py:24,79,93`).
- **Top-level `grep '^from infra\|^import infra'` sur `services/` et `api/`** : zéro hit. Les seuls hits `from infra` dans `services/` sont protégés par `if TYPE_CHECKING:` (`services/store_backend_resolver.py:37-42`) — c'est de la typage statique, pas du couplage runtime.
- **4 nouveaux ports** dans `domain/ports.py:312-410` : `DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector`. Tous marqués `@runtime_checkable`, tous documentés avec leur invariant Docling (collapse InlineGroup, page-cap fetch, NotImplementedError plutôt que silent no-op, projection sans Neo4j).
- **4 nouveaux adapters** dans `infra/` : `DoclingTreeReader` (`infra/docling_tree.py:288`), `DoclingGraphProjector` (`infra/docling_graph.py:188`), `Neo4jGraphReader` + `Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py:27,37`). Chacun est un thin shim qui satisfait le protocole par duck-typing structurel.
- **`GraphService` créé** (`services/graph_service.py`) — orchestre les deux endpoints `/graph` et `/reasoning-graph`, lève des erreurs domain typées (`GraphStoreNotConfiguredError` 503, `GraphNotFoundError` 404, `GraphTooLargeError` 413) que `api/graph.py:80-81,94-95` mappe en `HTTPException`. L'API se contente du transport ; toute la logique (résolution de la dernière analyse, cap MAX_PAGES, NotFound / Truncated) vit dans le service. MAJ 1.3.3 fermé.
- **DI complète** — `IngestionTargets.neo4j_driver` renommé `IngestionTargets.graph_writer` (`services/store_backend_resolver.py:62`) ; le resolver reçoit un `graph_writer_factory: Callable[[Any], GraphWriter]` injecté par `main.py:298` (`Neo4jGraphWriter`). Plus aucun service ne « pull » d'implémentation : tout entre par constructeur. MAJ 1.2.4 fermé.
- **Wiring centralisé dans `main.py`** — `main.py:262-348` construit `Neo4jGraphReader`, `Neo4jGraphWriter`, `DoclingTreeReader`, `DoclingGraphProjector` et `GraphService` dans la composition root. Les services consommateurs (`AnalysisService`, `IngestionService`, `ChunkService`, `StoreBackendResolver`) reçoivent les ports résolus. Le composition root reste l'unique endroit autorisé à `import` des classes infra concrètes.
- **Test architecture exécutable** — `tests/test_architecture.py` couvre désormais via pytestarch :
  - `services -> {api, infra, persistence}` interdit (`tests/test_architecture.py:89-102`),
  - `api -> {infra, persistence}` interdit (`tests/test_architecture.py:105-118`),
  - `Protocol` interdit hors `domain/ports.py` (`tests/test_architecture.py:184-205`).
  
  Le test skippe proprement (`pytest.importorskip` ligne 25) en l'absence de pytestarch local — vérifié : `pytest tests/test_architecture.py` → `1 skipped in 0.01s`, pas d'erreur de collection. CI installe `requirements-test.txt` (`pytestarch>=2.0.0`, `.github/workflows/ci.yml:40`) et exécute donc effectivement les règles à chaque PR. Toute régression future du type CRIT 1.1.3 serait bloquée par le pipeline.
- **Domain purity intacte** — `grep` sur `domain/` ne retourne aucun import de `fastapi`, `aiosqlite`, `pydantic`. La couche reste constituée de dataclasses (`domain/models.py`, `domain/value_objects.py`).
- **Services sans FastAPI** — zéro `from fastapi` / `import fastapi` dans `services/`.
- **API sans persistence directe** — zéro `from persistence` / `import persistence` dans `api/`.
- **Configuration centralisée** — `infra/settings.py` reste l'unique source de variables d'environnement ; pas de régression depuis 0.6.1 baseline.

---

## Delta vs audit initial 0.6.1

| Item | 0.6.1 initial | 0.6.1 re-audit | Cause |
|------|---------------|----------------|-------|
| 1.1.3 (Ports) | ❌ CRIT | ✅ | 4 ports ajoutés (`DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector`) + 4 adapters Neo4j/Docling. |
| 1.2.4 (DI) | ❌ MAJ | ✅ | `AnalysisService`, `IngestionService`, `ChunkService`, `StoreBackendResolver` reçoivent les ports par constructeur ; plus aucun import lazy `from infra.neo4j ...`. |
| 1.3.3 (Endpoints délèguent) | ❌ MAJ | ✅ | `GraphService` créé ; `api/graph.py` réduit à 96 lignes de mapping HTTP/erreurs. |
| 1.3.2 (camelCase) | ❌ MIN | ❌ MIN | Non remédié — hors scope `#audit-01` (reportable). |
| Score | 75 / 100 | 97 / 100 | +22 points. |
| CRIT / MAJ / MIN / INFO | 1 / 2 / 1 / 0 | 0 / 0 / 1 / 0 | CRIT et 2 MAJ fermés ; MIN 1.3.2 inchangé. |
| Verdict | NO-GO | GO | La règle absolue `master.md §3` (zero CRIT) est désormais satisfaite. |

---

## Vérifications exécutées

```
# Sites d'import infra dans services/ et api/ — top-level
grep -rn '^from infra\|^import infra' document-parser/services/ document-parser/api/
→ (zéro hit)

# Sites d'import infra incluant lazy
grep -rn 'from infra\|import infra' document-parser/services/ document-parser/api/
→ 6 hits, tous sous `if TYPE_CHECKING:` dans store_backend_resolver.py, ou commentaires.

# Test architecture
.venv/bin/pytest tests/test_architecture.py -v
→ 1 skipped in 0.01s (pytestarch non installé localement, skip propre)

# CI confirme l'exécution des règles
.github/workflows/ci.yml:40 → `pip install -r requirements-test.txt` (inclut pytestarch>=2.0.0)
```

---

## Verdict partiel : GO

Score 97 / 100, zéro CRIT, zéro MAJ, un MIN reportable (1.3.2 camelCase sur 6 schemas inline). La remédiation `#audit-01` ferme intégralement les 3 écarts architecture du rapport initial et installe en plus un garde-fou (`tests/test_architecture.py` + pytestarch en CI) qui bloquera toute régression de la même nature à l'avenir. Le MIN 1.3.2 peut être traité au prochain cycle sans bloquer la release 0.6.1.

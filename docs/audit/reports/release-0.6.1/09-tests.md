# Rapport d'audit : Tests

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 14 |
| Score | 85 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

**Calcul** : poids total 27. Items non conformes : 9.1.1 (poids 3, CRIT) + 9.3.5 (poids 1, MIN). Score = (27 - 4) / 27 × 100 = 85.

---

## Ecarts constates

### [CRIT] 2 modules de tests backend echouent au collect

- **Localisation** :
  - `document-parser/tests/test_local_converter.py:18`
  - `document-parser/tests/test_architecture.py:22`
- **Constat** :
  - `test_local_converter.py` importe `_encode_picture_b64` depuis `infra.local_converter`, mais ce symbole n'existe plus dans le module (refactoring non propage au test). Resultat : `ImportError: cannot import name '_encode_picture_b64' from 'infra.local_converter'`. Le `pytest.importorskip("docling")` ne protege pas — l'import echoue avant.
  - `test_architecture.py:22` requiert `pytestarch>=2.0.0,<3.0.0` declare dans `requirements-test.txt`, mais le paquet n'est pas installe dans le venv courant. Si l'image CI installe la dependance, l'item passe en CI ; localement les 2 echouent collect. A verifier dans le workflow CI.
- **Reproduction** :
  ```
  cd document-parser && .venv/bin/pytest tests/ --co -q
  # 747 tests collected, 2 errors in 5.35s
  ```
- **Regle violee** : 9.1.1 — Tous les tests backend passent (`pytest tests/ -v`)
- **Remediation** :
  1. `test_local_converter.py` : retirer le test obsolete ou re-exposer `_encode_picture_b64` dans `infra.local_converter` (la fonction d'encodage base64 PNG existait avant un refactoring).
  2. `test_architecture.py` : ajouter `pytestarch` au build CI (verifier `requirements-test.txt` est installe) ou retirer la dependance.
- **Poids** : 3 (CRIT) — un test qui ne collecte pas n'a aucune valeur ; en CI strict, la suite entiere est marquee rouge.

### [MIN] Assertions vagues `assert X is not None` — regression vs 0.5.0

- **Localisation** : 50 occurrences sur 23 fichiers backend, parmi lesquelles :
  - `document-parser/tests/test_repos.py:45,91,103,122,138,233`
  - `document-parser/tests/test_store_repo.py:44,69,106,122,129,197,217,398`
  - `document-parser/tests/test_chunk_service.py:462,476,531,554,584,659`
  - `document-parser/tests/test_chunk_repos.py:91,103,206`
  - `document-parser/tests/test_api_stores.py:140,160,182,356`
  - `document-parser/tests/test_store_backend_resolver.py:128,242`
  - `document-parser/tests/test_reasoning_api.py:158,168,180`
  - `document-parser/tests/test_chunk_editing.py:108`
  - `document-parser/tests/test_chunk_service.py:119,200`
  - `document-parser/tests/test_analysis_service.py:354`
  - `document-parser/tests/test_local_converter.py:70`
  - `document-parser/tests/test_serve_converter.py:98`
  - `document-parser/tests/test_ingestion_service.py:119`
  - `document-parser/tests/test_chunking.py:276`
  - `document-parser/tests/test_vector_store_port.py:47`
  - `document-parser/tests/test_opensearch_store.py:110`
  - `document-parser/tests/neo4j/test_tree_writer.py:204`
  - `document-parser/tests/neo4j/test_chunk_writer.py:97,181`
  - `document-parser/tests/neo4j/test_document_roundtrip.py:24`
  - Frontend : `frontend/src/app/router/router.test.ts:97` (`expect(...).toBeDefined()`)
- **Constat** : 50 assertions backend testent uniquement l'existence (`assert X is not None`), sans verifier le contenu, l'identifiant, ou les proprietes de X. Regression vs 0.5.0 (18 occurrences) : +32 nouvelles assertions vagues, principalement dans les tests des nouvelles features 0.6.x (store_repo, chunk_service, api_stores, store_backend_resolver, reasoning_api). Le verdict 0.5.0 (MAJ) n'a donc pas ete adresse ; au contraire, le pattern a essaime.
- **Justification du downgrade MAJ → MIN** : la fiche d'audit `09-tests.md` definit 9.3.5 avec poids 1, donc l'ecart est class MIN par les regles de notation (poids 1 = MIN). Le rapport 0.5.0 l'avait incorrectement marque MAJ.
- **Regle violee** : 9.3.5 — Les assertions sont specifiques (pas juste `assert result is not None`)
- **Remediation** : Remplacer par des assertions ciblees, exemple :
  ```python
  # Avant
  assert found is not None
  # Apres
  assert found is not None and found.id == doc.id
  assert found.lifecycle_state == "READY"
  ```
- **Poids** : 1 (MIN) — n'invalide pas les tests, reduit la valeur des regressions detectables.

---

## Points positifs

1. **Croissance de la couverture** : `document-parser/tests/` passe de 29 a 46 fichiers (+17), 12 125 lignes au total. 38 fichiers de tests frontend (vs 23 en 0.5.0) avec 400 tests verts.

2. **Couverture explicite des nouvelles features 0.6.x** :
   - **Store backends** : `test_store_service.py` (528 LOC), `test_api_stores.py` (361 LOC), `test_store_repo.py`, `test_store_backend_resolver.py` (340 LOC), `frontend/src/features/store/api.test.ts`.
   - **Version history / lifecycle** : `test_lifecycle.py`, `test_lifecycle_aggregation.py`, `test_version_service.py` (145 LOC), `frontend/src/features/history/store.test.ts`, `frontend/src/__tests__/integration/history-navigation.test.ts`.
   - **Chunk editing/service** : `test_chunk_editing.py`, `test_chunk_service.py`, `test_chunk_repos.py`.
   - **Reasoning** : `test_reasoning_api.py`, `test_docling_agent_reasoning.py`, `frontend/src/features/reasoning/store.test.ts`.

3. **Tests d'integration ciblee (9.3.4)** :
   - Backend : TestClient FastAPI avec mocks de services pour endpoints, AsyncMock des repos pour services.
   - Frontend : Pinia stores instancies reellement, API mockee.
   - `frontend/src/__tests__/integration/history-navigation.test.ts` couvre le flow inter-stores.

4. **E2E Karate UI etoffes pour 0.6.x** : 18 features UI + 13 features API + 5 helpers. La nouvelle drawer history est couverte (`documents/doc-history-drawer.feature` — referencee a issue #267). Les chunk-mode (#266), upload, delete, error-states, batch-progress, pipeline-options ont tous une feature dediee. Helpers `ui-wait-analysis.feature`, `cleanup-by-name.feature` permettent l'isolation entre scenarios.

5. **Pas d'anti-patterns (9.3.1)** : 0 `.only`, `fdescribe`, ou `fit(` dans les 38 fichiers frontend.

6. **Skips justifies (9.3.2)** :
   - `test_serve_converter.py:480` : `@pytest.mark.skipif(not _has_docling(), reason="docling library not installed")` (justification claire).
   - `neo4j/conftest.py:35` : `pytest.skip(f"Neo4j not reachable at {uri}: {exc}")` (gate infra).
   Aucun skip sans justification.

7. **Determinisme (9.3.3)** : pytest avec `asyncio_mode = auto`, Vitest avec `vi.useFakeTimers()` dans les tests d'orchestration. Helpers Karate `retry until ... == 'COMPLETED'` evitent les `sleep` fixes.

8. **732 tests backend passent + 15 skips legitimes** (en ignorant les 2 fichiers en erreur de collect).

9. **Nommage explicite (9.3.6)** : `test_two_analyses_drawer_lists_both_set_older_as_current`, `test_run_analysis_marks_failed_on_error`, `test_concurrent_analyses`, etc.

10. **Couverture endpoints (9.2.1, 9.2.2)** : tous les nouveaux endpoints 0.6.1 (`/api/stores/*`, `/api/documents/{id}/chunks/*`, `/api/documents/{id}/history`) ont au moins un happy path et des cas d'erreur (400/404). Voir `test_api_stores.py` pour CRUD + error paths.

---

## Verdict partiel : NO-GO

**Justification** :
- Score 85/100 — au dessus du seuil GO (>= 80).
- **MAIS regle absolue master.md §3** : "tout ecart `[CRIT]` non resolu = **NO-GO** quel que soit le score".
- Le CRIT est facilement remediable (5 minutes) :
  - soit retablir `_encode_picture_b64` dans `infra/local_converter.py`,
  - soit supprimer `tests/test_local_converter.py` si la fonction a ete intentionnellement retiree,
  - soit ajouter `pip install pytestarch` au step CI ou retirer le test d'architecture.
- Apres correction du CRIT : score 96/100, verdict GO.

**Conditions de levee du NO-GO** :
1. Corriger l'import casse dans `test_local_converter.py:18` (decision : retablir le symbole ou supprimer le test).
2. Garantir que `pytestarch` est installe en CI (verifier le step `pip install -r requirements-test.txt` du workflow).
3. Re-executer `.venv/bin/pytest tests/ -v` — la suite doit collecter 0 erreur.

**Delta vs 0.5.0** :
- Couverture en hausse (29 → 46 fichiers backend, 23 → 38 frontend, 400 tests UI verts).
- Nouvelles features 0.6.x bien couvertes (stores, history, lifecycle, chunk editing).
- Regression sur 9.3.5 (assertions vagues 18 → 50) — pattern qui se propage avec les nouveaux tests.
- Nouveau CRIT (collection errors) absent en 0.5.0.

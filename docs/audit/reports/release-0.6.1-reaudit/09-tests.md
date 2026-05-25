# Rapport d'audit : Tests (re-audit)

**Release** : 0.6.1 (re-audit sur `fix/0.6.1-audit-blockers`)
**Branche** : `fix/0.6.1-audit-blockers` @ `f9e5619`
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 96 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

**Calcul** : poids total 27. Seul item non conforme : 9.3.5 (poids 1, MIN). Score = (27 − 1) / 27 × 100 = 96,3 → **96**.

**Delta vs 0.6.1 initial** : 85 → 96 (**+11**), CRIT 1 → 0, MAJ 0 → 0, MIN 1 → 1, INFO 0 → 0. Verdict **NO-GO → GO**.

---

## Verification de la remediation CRIT

### CRIT-09 « 2 modules de tests backend echouent au collect » — **FERME**

- `document-parser/tests/test_local_converter.py` : **supprime** (commit `68cfdf1`). La fonction `_encode_picture_b64` avait disparu du SUT lors d'un refactoring anterieur ; le fichier de test obsolete avait ete `.gitignore`-d au lieu d'etre supprime.
  - Verification : `find document-parser/tests -name 'test_local_converter.py'` → 0 resultat.
  - Verification : la ligne `document-parser/tests/test_local_converter.py` n'apparait plus dans `.gitignore` (cf. diff du commit `68cfdf1`, `.gitignore | 1 -`).
- `document-parser/tests/test_architecture.py:23-26` : import `pytestarch` enveloppe dans `pytest.importorskip(...)` avec message explicite (« `pip install -r requirements-test.txt` to enforce layer rules »). Pattern aligne sur l'import `docling` du meme repo. Collecte propre meme sans la dependance ; le verrou architectural reste actif en CI (qui installe `requirements-test.txt`).

**Reproduction (collecte)** :
```
cd document-parser && .venv/bin/pytest tests/ --collect-only -q 2>&1 | tail -3
# 747 tests collected in 3.15s   (0 erreur)
```

**Reproduction (run complet)** :
```
cd document-parser && .venv/bin/pytest tests/ -q
# 732 passed, 16 skipped, 5 warnings in 7.27s
```

→ Item 9.1.1 **conforme**.

---

## Verification des verrous touches par le refactor #audit-01

Le refactor « route graph + tree access through ports » (`f9e5619`) a etendu la signature de `ChunkService` (parametre `tree_reader: DocumentTreeReader`) et introduit `services/graph_service.py`. Les tests ont ete adaptes en consequence — pas de regression silencieuse :

- `document-parser/tests/test_chunk_service.py:40-42` : import + instanciation d'une shim `DoclingTreeReader` partagee, injectee dans toutes les fixtures et constructions ad-hoc de `ChunkService` (lignes 83, 451, 502, 580, 615, 652 …). Note interne « Stateless shim — safe to share across the entire test module ».
- `document-parser/tests/test_graph_api.py:18-19,66-72` : import de `DoclingGraphProjector` + `GraphService`, fixture `client` reconstruit `app.state.graph_service` avec `graph_reader=None` pour prouver que `/reasoning-graph` reste decouple de Neo4j (verifie le point cle du refactor : `/graph` 503 propre + `/reasoning-graph` 200).
- `document-parser/tests/test_store_backend_resolver.py:134,248` : assertions adaptees au nouveau type `IngestionTargets(graph_writer=...)` (anciennement `neo4j_driver`).

Les 732 tests passent sans modification de plus de surface.

---

## Detail item par item

| # | Item | Poids | Statut | Note |
|---|------|-------|--------|------|
| 9.1.1 | Tous les tests backend passent | 3 | OK | 732 passed, 16 skipped, 0 error |
| 9.1.2 | Tous les tests frontend passent | 3 | OK | inchange depuis 0.6.1 (400 tests, 38 fichiers) |
| 9.1.3 | E2E Karate UI passent | 2 | OK | 40 features (source) + 18 UI scenarios, helpers `ui-wait-analysis`/`cleanup-by-name` |
| 9.2.1 | Endpoints API : happy path | 2 | OK | `/api/stores/*`, `/api/documents/{id}/chunks/*`, `/api/documents/{id}/history` couverts |
| 9.2.2 | Endpoints API : cas d'erreur | 2 | OK | `test_api_stores.py` couvre 400/404 ; size-validation feature dediee |
| 9.2.3 | Services testes (orchestration) | 2 | OK | `test_chunk_service.py` (732 LOC), `test_store_service.py`, `test_version_service.py`, `test_analysis_service.py` |
| 9.2.4 | Domain teste (bbox, VO) | 1 | OK | `test_bbox.py`, `test_models.py`, `test_schemas.py` |
| 9.2.5 | Composants Vue critiques testes | 2 | OK | 38 fichiers `.test.ts(x)` ; integration `history-navigation.test.ts` |
| 9.3.1 | Pas de `.only`/`fdescribe`/`fit` | 3 | OK | 0 occurrence frontend |
| 9.3.2 | Skips justifies | 1 | OK | `test_serve_converter.py` (`@pytest.mark.skipif _has_docling`), `neo4j/conftest.py` (gate infra), `test_architecture.py` (`importorskip`) |
| 9.3.3 | Determinisme | 2 | OK | `asyncio_mode = auto`, fake-timers Vitest, Karate retry-until |
| 9.3.4 | Integration vs mock complet | 2 | OK | TestClient FastAPI + AsyncMock des repos ; Pinia stores instancies reels |
| 9.3.5 | Assertions specifiques | 1 | **MIN** | 49 occurrences backend + 1 frontend = 50 (vs 50 en 0.6.1) |
| 9.3.6 | Nommage explicite des tests | 1 | OK | `test_first_version_has_empty_chunks_snapshot`, `test_run_analysis_marks_failed_on_error`, etc. |

---

## Ecarts constates

### [MIN] Assertions vagues `assert X is not None` — non adresse depuis 0.6.1

- **Localisation** : 49 occurrences backend reparties sur 22 fichiers + 1 frontend (`frontend/src/app/router/router.test.ts:97`). Principaux foyers :
  - `document-parser/tests/test_chunk_service.py:124,205,468,482,538,540,541,545,561,592,669` (11)
  - `document-parser/tests/test_store_repo.py:44,69,106,122,129,197,217,398` (8)
  - `document-parser/tests/test_repos.py:45,91,103,105,122,138,233` (7)
  - `document-parser/tests/test_api_stores.py:140,160,182,356` (4)
  - `document-parser/tests/test_reasoning_api.py:158,168,180` (3)
  - `document-parser/tests/test_chunk_repos.py:91,103,206` (3)
  - `document-parser/tests/neo4j/test_chunk_writer.py:97,181` (2)
  - `document-parser/tests/test_store_backend_resolver.py:134,248` (2)
  - Autres : `test_serve_converter.py:98`, `test_chunking.py:276`, `test_analysis_service.py:354`, `test_chunk_editing.py:108`, `neo4j/test_tree_writer.py:204`, `test_vector_store_port.py:47`, `test_opensearch_store.py:110`, `neo4j/test_document_roundtrip.py:24`, `test_ingestion_service.py:119`
- **Constat** : 50 assertions testent uniquement l'existence (`assert X is not None`), sans verifier le contenu. Compte stable vs 0.6.1 initial (50) : la suppression de `test_local_converter.py:70` a ete compensee par l'ajout de `test_chunk_service.py:538-545,540,541,545,561,592,669` (nouveaux tests `TestPushToStore` lies au refactor push-chunks). Le MIN n'a pas ete adresse mais n'a pas non plus essaime.
- **Regle violee** : 9.3.5 — Les assertions sont specifiques.
- **Remediation** : pattern habituel
  ```python
  # Avant
  assert link is not None
  # Apres
  assert link is not None
  assert link.chunkset_hash == expected_hash
  assert link.lifecycle_state == "ATTACHED"
  ```
  A cibler en priorite : `test_chunk_service.py:538-545,669` (3 lignes consecutives `assert link.X is not None` qui pourraient devenir une assertion d'egalite sur le snapshot complet).
- **Poids** : 1 (MIN) — non bloquant. A integrer dans le prochain cycle de qualite de tests.

---

## Points positifs (delta vs 0.6.1 initial)

1. **CRIT-09 ferme proprement** : ni surface backend modifiee ni regression de couverture (le test supprime testait un SUT qui n'existait plus, ce n'etait pas un trou de couverture). Le verrou pytestarch reste actif en CI et silencieux localement sans la dep.
2. **Refactor #audit-01 entierement teste** : `ChunkService(tree_reader=...)`, `GraphService(graph_reader=..., graph_projector=...)`, `IngestionTargets(graph_writer=...)` sont tous instancies dans les tests adaptes. Le test `test_graph_api.py` valide explicitement le decouplage `/reasoning-graph` ↔ Neo4j (clef du refactor).
3. **Aucune nouvelle assertion vague nette** : malgre l'ajout de ~17 lignes dans `test_chunk_service.py` pour `TestPushToStore`, le compteur global reste a 50. Pattern stable, pas en propagation.
4. **732 tests verts en 7,27 s** localement, run reproductible.

---

## Verdict partiel : **GO**

**Justification** :
- Score 96/100 — au-dessus du seuil GO (≥ 80).
- 0 ecart CRITICAL → regle absolue `master.md` §3 satisfaite.
- 0 ecart MAJOR → seuil bloquant > 3 MAJ non atteint.
- 1 ecart MINOR (assertions vagues) — non bloquant, a tracker pour 0.6.2.

**Aucune condition de levee** : le seul ecart restant est un MIN documente et stable.

**Delta vs 0.6.1 initial (85 / CRIT 1 / MAJ 0 / MIN 1 / INFO 0 / NO-GO)** :

| Metrique | 0.6.1 | re-audit | Delta |
|----------|-------|----------|-------|
| Score | 85 | 96 | **+11** |
| CRIT | 1 | 0 | **−1** (ferme) |
| MAJ | 0 | 0 | 0 |
| MIN | 1 | 1 | 0 (stable) |
| INFO | 0 | 0 | 0 |
| Verdict | NO-GO | **GO** | **levee** |

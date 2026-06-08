# Rapport d'audit : Tests (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/09-tests.md` — 96/100, GO (0 CRIT / 0 MAJ / 1 MIN / 0 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 (poids 26 / 27) |
| Score | **96 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

**Calcul** : total des poids = 27 (14 items : 9.1.1=3, 9.1.2=3, 9.1.3=2, 9.2.1=2, 9.2.2=2, 9.2.3=2, 9.2.4=1, 9.2.5=2, 9.3.1=3, 9.3.2=1, 9.3.3=2, 9.3.4=2, 9.3.5=1, 9.3.6=1). Seul item non conforme : 9.3.5 (poids 1, MIN). Score = (27 − 1) / 27 × 100 = 96,3 → **96**.

**Delta vs baseline `release-0.6.2/09-tests.md`** : **+0 point** (96 → 96). Aucune regression. Le CRIT 0.6.2 baseline #10 (« `test_rechunk_with_serve_document_json` tente d'attaquer HuggingFace Hub depuis un unit test ») est clos par `29ab575` : la collecte reste a 768 tests / 0 erreur, le run reste 753 passed / 15 skipped, et la suite `test_chunking.py` (38 tests) passe desormais en **0,35 s** (vs 3,64 s baseline, le `LocalChunker` materialisait un `HybridChunker` qui tirait `sentence-transformers/all-MiniLM-L6-v2` depuis HF Hub). Le MIN historique sur les assertions vagues (49 occurrences backend) reste inchange.

---

## Contexte de la re-audit

La branche `fix/0.6.2-audit-blockers` introduit 8 commits par rapport a `release/0.6.2`. Seul **un commit touche le repertoire `document-parser/tests/`** :

| Commit | Touche | Resume |
|--------|--------|--------|
| `29ab575` | `document-parser/tests/test_chunking.py` (+15 / −3) | Mocke le `DocumentChunker` port dans `TestRemoteChunkingPath::test_rechunk_with_serve_document_json` pour clore le CRIT-10 baseline 0.6.2 (test qui exigeait un tokenizer HF a runtime). |

Les autres commits (`307caf7`, `bc9b4f8`, `dd1962e`, `76b67ec`, `2403027`, `f6b4e23`) modifient CI / compose / Trivy / CHANGELOG / Dockerfiles : **aucune** trace dans `document-parser/tests/`, `frontend/src/**/*.test.*` ou `e2e/`. Verifie :

```
git diff release/0.6.2..HEAD --name-only -- document-parser/tests/ frontend/src/ e2e/
# document-parser/tests/test_chunking.py   (1 seul fichier)
```

L'aire de la re-audit se concentre donc sur :

1. **Verifier que la fix `29ab575` n'a pas casse la collection** (cible : >= 768 tests collectes, 0 erreur).
2. **Verifier qu'aucun nouveau skip n'a ete introduit** par la fix.
3. **Verifier que le test continue d'exercer ce qu'il pretend** (rechunk en mode remote sur un `document_json` Serve).
4. **Reconduire les autres items** (collection front, e2e, qualite), en l'absence de tout autre delta.

---

## Suivi des ecarts baseline 0.6.2

| Ecart 0.6.2 | Statut 0.6.2 re-audit | Preuve |
|-------------|----------------------|--------|
| [MIN] Assertions vagues `assert X is not None` (49 occurrences backend, 17 fichiers) | **Inchange** (49 / 17 verifies) | `grep -rn "assert.*is not None$\|assert.*!= None$" document-parser/tests/ --include="*.py" \| wc -l` -> 49 ; ventilation par fichier identique au baseline (cf. § ecart MIN ci-dessous). |

L'unique MIN baseline est reconduit a l'identique : aucune correction tentee dans le scope `fix/0.6.2-audit-blockers`, aucune regression observee (la fix `29ab575` n'a pas ajoute de `is not None`).

Note : `test_chunking.py` continue de contenir 1 occurrence (`test_chunking.py:276`, `assert data["chunksJson"] is not None`) deja decomptee au baseline — la modification 29ab575 n'a ni ajoute ni retire de cette categorie.

---

## Verification ciblee — fix CRIT-10 (`29ab575`)

### Avant / apres

`document-parser/tests/test_chunking.py:480-520`, classe `TestRemoteChunkingPath` :

**Avant** (release/0.6.2, ligne 481-482) :
```python
from infra.local_chunker import LocalChunker
chunker = LocalChunker()
```
- `LocalChunker()` → `_chunk_sync` → `HybridChunker(tokenizer=...)` → `AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")` → HF Hub call.
- Sur GHA shared runners : 429 / network blocked → `OSError: We couldn't connect to 'https://huggingface.co'` (CI run #27005192862 cite dans le commit message).
- Localement : passe parce que le cache HF est chaud.

**Apres** (`29ab575`, ligne 480-499) :
```python
chunker = AsyncMock()
chunker.chunk = AsyncMock(
    return_value=[ChunkResult(text="stub", source_page=1, token_count=1)]
)
```
- Plus aucun import de `infra.local_chunker` ; le port `DocumentChunker` est mocke a la frontiere hexagonale.
- Le test exerce ce qu'annonce sa docstring : `AnalysisService.rechunk()` sur un `document_json` Serve, sans toucher au reseau public.
- L'integration reelle `LocalChunker` reste couverte par `tests/test_local_chunker.py` (verifie present, 20 tests) et la suite e2e.

### Effet mesure

| Metrique | Baseline 0.6.2 | Re-audit | Delta |
|----------|----------------|----------|-------|
| `pytest tests/test_chunking.py` | 38 passed (~3,64 s, dependant cache HF) | 38 passed en **0,35 s** | −90 % temps, +0 reseau |
| Collection totale `pytest --collect-only` | 768 tests, 13,36 s | **768 tests, 5,85 s** | identique |
| Run total `pytest tests/ -q` | 753 passed / 15 skipped / 0 error / 5 warn | **753 passed / 15 skipped / 0 error / 4 warn** | identique (1 warning de moins, hors scope direct) |

```
cd document-parser && .venv/bin/pytest --collect-only 2>&1 | tail -1
# 768 tests collected in 5.85s
cd document-parser && .venv/bin/pytest tests/ -q 2>&1 | tail -1
# 753 passed, 15 skipped, 4 warnings in 8.27s
```

Conformite avec les regles 9.1.1 (run propre), 9.3.2 (aucun nouveau skip), 9.3.3 (determinisme : le mock supprime la derniere dependance reseau cachee de la suite unitaire), 9.3.4 (integration reelle : le port boundary est explicite).

---

## Verification des items de la checklist (fiche `09-tests.md`)

### 9.1 — Execution

#### 9.1.1 — Tests backend passent (poids 3, **OK**)

```
cd document-parser && .venv/bin/pytest --collect-only 2>&1 | tail -1
# 768 tests collected in 5.85s
cd document-parser && .venv/bin/pytest tests/ -q 2>&1 | tail -1
# 753 passed, 15 skipped, 4 warnings in 8.27s
```

- **768** tests collectes (== baseline 0.6.2).
- **753 passed, 15 skipped, 0 error** — identique au baseline.
- Les 15 skips sont tous gardes par `skipif` ou `importorskip` (cf. 9.3.2).
- Les warnings restants : `DeprecationWarning` `docling_core.HybridChunker` (lib upstream) + `RuntimeWarning` coroutine non-await sur `test_pipeline_options` (faux positif `AsyncMock`, non-bloquant). **1 warning de moins** vs baseline car le mock du chunker dans `test_chunking.py` ne traverse plus le code chemin qui emettait un `DeprecationWarning` HF transitif (effet de bord positif).

#### 9.1.2 — Tests frontend passent (poids 3, **OK**)

```
cd frontend && npm run test:run 2>&1 | tail -5
#  Test Files  38 passed (38)
#       Tests  400 passed (400)
#       Duration  632ms
```

Stable vs baseline : 38 fichiers / 400 tests / ~0,63 s.

#### 9.1.3 — Tests e2e Karate UI passent (poids 2, **OK**)

```
find e2e/ui/src/test/resources -name "*.feature" | wc -l   # 24
find e2e/api/src/test/resources -name "*.feature" | wc -l  # 16
```
Total : **40 features sources** (chiffre baseline 0.6.2). Aucune feature ajoutee, supprimee ou renommee sur la branche.

Le rerouting CI E2E (`bc9b4f8`) vers le container `docling-serve` distant n'affecte ni les features Karate ni leur execution locale ; le harnais reste `mvn` / `karate.config.js`.

### 9.2 — Couverture

#### 9.2.1 — Happy path par endpoint (poids 2, **OK**)

Aucune nouvelle route, aucun retrait. Tous les endpoints `api/` ont un test happy path (cf. baseline, integralement reconduit).

#### 9.2.2 — Cas d'erreur 400/404/413/429 (poids 2, **OK**)

Aucun delta. `tests/test_api_stores.py` (400/404), `tests/test_graph_api.py` (404), `tests/test_ingestion_api.py` (413), `tests/test_rate_limiter.py` (429) inchanges sur la branche.

#### 9.2.3 — Services d'orchestration testes (poids 2, **OK**)

Aucun delta. Le mock du chunker dans `test_chunking.py::TestRemoteChunkingPath` est plus aligne avec la regle de couverture orchestration (test = service + port, integration chunker = `test_local_chunker.py`).

#### 9.2.4 — Domain (bbox, value objects) (poids 1, **OK**)

Aucun delta. `test_bbox.py`, `test_models.py`, `test_schemas.py`, `test_hashing.py`, `test_fernet_box.py`, `test_vector_schema.py` inchanges.

#### 9.2.5 — Composants Vue critiques (poids 2, **OK**)

Aucun delta. 38 fichiers `.test.ts(x)` cote frontend, identiques au baseline.

### 9.3 — Qualite des tests

#### 9.3.1 — Pas de `.only` / `fdescribe` / `fit` (poids 3, **OK**)

```
grep -rn "\.only\|fdescribe\|fit(" frontend/src/ --include="*.test.*"
# (vide)
```
0 occurrence. Aucun delta vs baseline.

#### 9.3.2 — Skips justifies (poids 1, **OK**)

```
grep -rn "@pytest.mark.skip\|pytest.skip\|importorskip" document-parser/tests/
```
6 occurrences (== baseline) :
- `tests/test_serve_converter.py:520` : `@pytest.mark.skipif(not _has_docling(), ...)` — guard extra optionnel.
- `tests/test_robustness.py:154` : `pytest.importorskip("docling", ...)` — guard extra optionnel.
- `tests/test_architecture.py:23` : `pytest.importorskip("pytestarch", ...)` — guard dev-only.
- `tests/test_pipeline_options.py:14` : `pytest.importorskip("docling", ...)` — guard extra optionnel.
- `tests/neo4j/conftest.py:16,35` : `pytest.importorskip("neo4j")` + `pytest.skip(f"Neo4j not reachable at {uri}: {exc}")` — gate infra.

La fix `29ab575` **n'a introduit aucun nouveau skip** : le test reste actif (et passe systematiquement, plus tributaire du reseau).

#### 9.3.3 — Determinisme (poids 2, **OK** ⇧)

`pytest.ini` impose `asyncio_mode = auto` ; fake-timers Vitest ; helpers Karate `ui-wait-analysis` / `retry until`.

**Amelioration palpable vs baseline** : la fix `29ab575` retire la **derniere dependance reseau cachee** de la suite unitaire backend. Avant, `test_rechunk_with_serve_document_json` etait deterministe **uniquement avec un cache HF chaud** (faux negatif local / vrai positif CI). Apres, il est deterministe sans condition (mock cote port). Item reste OK ; sa note ne change pas (item categoriel), mais sa robustesse de fait progresse.

#### 9.3.4 — Integration reelle (poids 2, **OK**)

`TestClient` FastAPI + repos in-memory ou `AsyncMock` cibles ; Pinia stores reels dans `__tests__/integration/history-navigation.test.ts` ; Karate frappe le backend live. La fix `29ab575` mocke au niveau du **port** `DocumentChunker`, en accord avec la regle (« mock cible, pas mock complet ») — l'integration `LocalChunker` reelle est couverte par `tests/test_local_chunker.py` (20 tests) et la suite e2e.

#### 9.3.5 — Assertions specifiques (poids 1, **MIN** — inchange)

```
grep -rn "assert.*is not None$\|assert.*!= None$" document-parser/tests/ --include="*.py" | wc -l
# 49
grep -rn "assert.*is not None$\|assert.*!= None$\|expect.*toBeTruthy()$" frontend/src/ --include="*.test.*"
# (vide)
```

- Backend : **49** (== baseline). Distribution par fichier verifiee, **strictement identique** :

| Fichier | Occurrences |
|---------|-------------|
| `document-parser/tests/test_chunk_service.py` | 11 |
| `document-parser/tests/test_store_repo.py` | 8 |
| `document-parser/tests/test_repos.py` | 7 |
| `document-parser/tests/test_api_stores.py` | 4 |
| `document-parser/tests/test_reasoning_api.py` | 3 |
| `document-parser/tests/test_chunk_repos.py` | 3 |
| `document-parser/tests/test_store_backend_resolver.py` | 2 |
| `document-parser/tests/neo4j/test_chunk_writer.py` | 2 |
| `document-parser/tests/{test_vector_store_port,test_serve_converter,test_opensearch_store,test_ingestion_service,test_chunking,test_chunk_editing,test_analysis_service}.py` + `neo4j/{test_tree_writer,test_document_roundtrip}.py` | 1 chacun |
| **Total** | **49** |

- Frontend : **0** (== baseline, le `router.test.ts:97` migre a `toBeDefined()` lors de 0.6.2 reste tel quel).

La fix `29ab575` n'a touche aucune de ces 49 lignes (verifie : aucune occurrence ajoutee ou supprimee dans `test_chunking.py`, le `is not None` ligne 276 etait deja la et y reste).

#### 9.3.6 — Nommage explicite (poids 1, **OK**)

Aucun delta. La fix `29ab575` conserve le nom `test_rechunk_with_serve_document_json` et **clarifie sa docstring** (« the chunker is mocked at the port boundary … ») en accord avec la regle.

---

## Verification de non-regression sur les autres axes du re-audit

| Axe | Verification | Resultat |
|-----|--------------|----------|
| Architecture guard `tests/test_architecture.py` | `cd document-parser && .venv/bin/pytest tests/test_architecture.py 2>&1 \| tail -1` | 20 passed (inchange) |
| Suite `test_chunking.py` (cible directe fix) | `cd document-parser && .venv/bin/pytest tests/test_chunking.py -q` | **38 passed en 0,35 s** (vs ~3,64 s baseline) |
| Comportement run global | `cd document-parser && .venv/bin/pytest tests/ -q` | 753 passed / 15 skipped / 4 warnings en 8,27 s (vs 753/15/5 baseline) |
| Frontend | `cd frontend && npm run test:run` | 38 files / 400 tests en 632 ms |
| E2E feature count | `find e2e -name "*.feature"` | 40 features (24 UI + 16 API) |

Aucune regression detectee. Le run unitaire backend gagne marginalement en stabilite (1 warning HF de moins suite a la suppression du chemin LocalChunker → HybridChunker dans ce test) et en vitesse (la suite `test_chunking.py` passe de ~3,6 s a 0,35 s, soit ~3,3 s gagnees sur le wall-clock total).

---

## Ecarts constates

### [MIN] Assertions vagues `assert X is not None` — heritage stable, inchange depuis 0.6.0

- **Localisation** : 49 occurrences backend reparties sur 17 fichiers (decompte verifie `2026-06-08`, distribution strictement identique au baseline 0.6.2) :
  - `document-parser/tests/test_chunk_service.py:124,205,468,482,538,540,541,545,561,592,669` (11)
  - `document-parser/tests/test_store_repo.py:44,69,106,122,129,197,217,398` (8)
  - `document-parser/tests/test_repos.py:45,91,103,105,122,138,233` (7)
  - `document-parser/tests/test_api_stores.py:140,160,182,356` (4)
  - `document-parser/tests/test_reasoning_api.py:158,168,180` (3)
  - `document-parser/tests/test_chunk_repos.py:91,103,206` (3)
  - `document-parser/tests/test_store_backend_resolver.py:134,248` (2)
  - `document-parser/tests/neo4j/test_chunk_writer.py:97,181` (2)
  - 9 autres fichiers a 1 occurrence (`test_vector_store_port.py:47`, `test_serve_converter.py:98`, `test_chunking.py:276`, `test_analysis_service.py:354`, `test_chunk_editing.py:108`, `test_opensearch_store.py:110`, `test_ingestion_service.py:119`, `neo4j/test_tree_writer.py:204`, `neo4j/test_document_roundtrip.py:24`).
- **Constat** : 49 assertions testent uniquement l'existence (`assert X is not None`), sans verifier le contenu. **Inchange vs baseline 0.6.2** : la fix `29ab575` n'a ni ajoute ni retire d'occurrence (le port mocke retourne un `ChunkResult` deterministe ; le test assertait deja un comportement sur ce retour via `update_chunks.assert_called_once_with(...)`, pas via `is not None`).
- **Regle violee** : 9.3.5 — Les assertions sont specifiques.
- **Remediation** : pattern habituel, foyer prioritaire `test_chunk_service.py:538-545` (4 lignes consecutives `assert link.X is not None` candidates a une assertion d'egalite sur snapshot complet).
- **Poids** : 1 (MIN) — non bloquant, a integrer dans le prochain cycle qualite. Identifie depuis 0.6.0, stable.

---

## Points positifs (delta vs baseline `release-0.6.2/09-tests.md`)

1. **CRIT-10 clos sans dette** : le test `test_rechunk_with_serve_document_json` ne tente plus de joindre HuggingFace Hub depuis un unit test. Mock cote port `DocumentChunker` (AsyncMock + `ChunkResult` deterministe), docstring re-ecrite pour expliquer la frontiere hexagonale, integration reelle reportee explicitement a `test_local_chunker.py` + e2e. Resolution de l'unique CRIT du re-audit 0.6.2 baseline #10 sans toucher au comportement de production.
2. **Determinisme renforce de fait** : la suite unitaire backend n'a plus **aucune** dependance reseau cachee. Tous les chemins qui touchaient `huggingface.co` (transitivement via `LocalChunker → HybridChunker → AutoTokenizer`) sont desormais soit explicitement skippes (`pytest.importorskip("docling")`), soit mockes au niveau du port. Item 9.3.3 reste OK ; sa robustesse de fait progresse.
3. **Run plus rapide** : `test_chunking.py` passe de ~3,64 s a 0,35 s (gain ~90 %), grace a l'elimination du chargement `AutoTokenizer` (qui pesait ~3 s a froid). Sur la suite complete, le wall-clock baisse de ~9,6 s a ~8,3 s.
4. **Aucune regression de couverture** : 768 tests collectes, 753 passed, 15 skipped, 0 error — chiffres a l'octet pres identiques au baseline. Pas de fichier de test retire, pas de nouveau skip introduit.
5. **MIN reconduit a l'identique, pas d'essaimage** : les 49 assertions vagues backend sont strictement aux memes lignes que dans le baseline. La fix CRIT n'a ni cree ni resorbe d'occurrence — comportement chirurgical, scope respecte.

---

## Verdict partiel : **GO**

**Justification** :
- Score 96/100 — au-dessus du seuil GO (>= 80).
- 0 ecart CRITICAL → regle absolue `master.md` §3 satisfaite (CRIT-10 baseline clos par `29ab575`).
- 0 ecart MAJOR → seuil bloquant > 3 MAJ non atteint.
- 1 ecart MINOR (assertions vagues) — non bloquant, stable depuis 0.6.0, inchange dans le scope re-audit.

**Aucune condition de levee** : seul ecart restant deja documente, sans propagation.

**Delta vs baseline `release-0.6.2/09-tests.md` (96 / CRIT 0 / MAJ 0 / MIN 1 / INFO 0 / GO)** :

| Metrique | Baseline 0.6.2 | 0.6.2 re-audit | Delta |
|----------|----------------|----------------|-------|
| Score | 96 | 96 | **0** |
| CRIT | 0 | 0 | 0 |
| MAJ | 0 | 0 | 0 |
| MIN | 1 | 1 | 0 (stable) |
| INFO | 0 | 0 | 0 |
| Verdict | GO | **GO** | maintenu |

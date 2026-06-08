# Rapport d'audit : Clean Code (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/03-clean-code.md` — 72/100, GO CONDITIONNEL (0/1/3/0)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 10 / 14 (somme des poids conformes 13 / 18) |
| Score | **72 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 0 |

### Detail

| # | Item | Poids | Statut | Delta vs baseline |
|---|------|-------|--------|-------------------|
| 3.1.1 | Fonctions = verbes d'action | 1 | OK | = |
| 3.1.2 | Variables expriment l'intention | 1 | OK | = |
| 3.1.3 | Code en anglais / i18n separe | 2 | OK | = |
| 3.1.4 | Pas d'abbreviations ambigues | 1 | OK | = |
| 3.2.1 | Single Responsibility | 2 | **KO** | = |
| 3.2.2 | Fonctions <= 30 lignes | 1 | **KO** | = |
| 3.2.3 | <= 4 parametres | 1 | **KO** | = |
| 3.2.4 | Pas de flag arguments | 1 | OK | = |
| 3.2.5 | `get_*` sans side-effects | 2 | OK | = |
| 3.3.1 | Fichiers <= 300 lignes | 1 | **KO** | = |
| 3.3.2 | Un concept par fichier | 2 | OK | = |
| 3.3.3 | Imports ordonnes | 1 | OK | = |
| 3.4.1 | Code auto-documentant | 1 | OK | = |
| 3.4.2 | Pas de code commente | 1 | OK | = |

**Calcul** : poids conformes (1+1+2+1+1+2+2+1+1+1 = 13) / poids total (18) × 100 = 72.2 → **72 / 100**.

---

## Contexte du re-audit

La fenetre de remediation `fix/0.6.2-audit-blockers` (8 commits depuis `051ac4a`) cible exclusivement les blockers CI/Securite/Docs identifies au tour 1 :

- `307caf7`, `29ab575` — CRIT-10 (BAKE_MODELS gate + mock chunker port en test).
- `2403027` — CRIT-11 (CHANGELOG 0.6.2 + BREAKING).
- `76b67ec` — Trivy ignore CVE perl-base.
- `dd1962e`, `bc9b4f8`, `f6b4e23` — coupure des deps HuggingFace Hub implicites + bascule E2E sur Docling Serve remote.

`git log 051ac4a..HEAD -- <fichiers Clean Code flagges>` renvoie **zero commit** sur les 11 fichiers cites au tour 1 (`chunk_service.py`, `main.py`, `tree_writer.py`, `chunk_writer.py`, `StudioPage.vue`, `store_service.py`, `analysis_service.py`, `store_backend_resolver.py`, `ports.py`, `models.py`, `schemas.py`). Le seul fichier Python production-adjacent touche est `document-parser/tests/test_chunking.py` (+12/-2 lignes, mock chunker au niveau du port `DocumentChunker` au lieu de `LocalChunker()` direct).

Verification mecanique au HEAD `f6b4e23` :

| Fichier | Lignes baseline | Lignes HEAD | Delta |
|---------|-----------------|-------------|-------|
| `services/chunk_service.py` | 1014 | 1014 | 0 |
| `services/analysis_service.py` | 553 | 553 | 0 |
| `main.py` | 504 | 504 | 0 |
| `api/schemas.py` | 493 | 493 | 0 |
| `domain/ports.py` | 442 | 442 | 0 |
| `services/store_service.py` | 391 | 391 | 0 |
| `domain/models.py` | 331 | 331 | 0 |
| `infra/neo4j/tree_writer.py` | 310 | 310 | 0 |
| `frontend/src/pages/StudioPage.vue` | 1450 | 1450 | 0 |

Ancrages de fonctions verifies identiques (`grep -n`) :
- `chunk_service.py` : `__init__@149`, `promote_from_analysis_if_empty@205`, `update_chunk@285`, `split_chunk@335`, `merge_chunks@393`, `rechunk_document@451`, `push_to_store@574`, `list_pushes@693`.
- `main.py` : `lifespan@247`, `_build_ingestion_service@145`, `_build_reasoning_runner@434`.
- `infra/neo4j/tree_writer.py` : `write_document@69`. `infra/neo4j/chunk_writer.py` : `write_chunks@55`.

Top frontend inchange (StudioPage 1450L, i18n.ts 1287L, DocsLibraryPage 849L, ChunkPanel 801L, GraphView 695L, ResultTabs 690L, ChunksEditor 622L).

Conclusion : **le bilan Clean Code 0.6.2 est strictement identique a celui du tour 1**.

---

## Note sur la modification de `tests/test_chunking.py`

Le commit `29ab575` (CRIT-10) remplace dans `test_rechunk_with_serve_document_json` l'instanciation directe `LocalChunker()` par un `AsyncMock` typique de la fixture du port `DocumentChunker`. Bilan Clean Code de la modification :

- **3.1.3 (anglais)** : OK — docstring etendue en anglais expliquant le pourquoi (rate-limit HF Hub sur CI partagee).
- **3.4.1 (commentaires "pourquoi")** : OK — le bloc cite explicitement la motivation (`makes a unit test depend on public network and gets 429-rate-limited on shared CI runners`), pas le mecanisme.
- **3.2.2 (taille)** : neutre — le test passe de 24 a 36 lignes, sous le seuil.
- **3.2.5 / SRP** : neutre — c'est un test, hors scope Single Responsibility de production.
- **3.4.2 (code commente)** : OK — aucun bloc commente, juste deux commentaires `#` d'intention.

Aucun nouvel ecart introduit ; la modification ameliore meme marginalement l'hygiene de test (utilisation du port plutot que de l'adapter concret).

---

## Ecarts constates

Tous les ecarts ci-dessous sont **strictement identiques** a la baseline `release-0.6.2/03-clean-code.md`. Voir ce dernier pour le detail complet et la remediation.

### [MAJ] Violations du Single Responsibility — handlers fourre-tout (inchange)

- `document-parser/services/chunk_service.py:574` `push_to_store` — 119 lignes (574-692).
- `document-parser/services/chunk_service.py:451` `rechunk_document` — 89 lignes (451-539).
- `document-parser/main.py:247` `lifespan` — 187 lignes (247-433).
- `document-parser/infra/neo4j/tree_writer.py:69` `write_document` — 242 lignes (69-310).
- `document-parser/infra/neo4j/chunk_writer.py:55` `write_chunks` — ~113 lignes.
- **Regle violee** : 3.2.1 (poids 2).

### [MIN] Fonctions de plus de 30 lignes (inchange)

- 12 fonctions backend >30L (cf. baseline §"Fonctions de plus de 30 lignes"), zero changement structurel.
- **Regle violee** : 3.2.2 (poids 1).

### [MIN] Fonctions avec plus de 4 parametres (inchange)

- `ChunkService.__init__@149` — 12 parametres.
- `store_service.update_store` — 10 params ; `create_store` — ~9 params.
- `analysis_service.__init__` — 8 params.
- `store_backend_resolver.__init__` — 7 params.
- `tree_writer.write_document@69` — 7 params.
- **Regle violee** : 3.2.3 (poids 1).

### [MIN] Fichiers source de plus de 300 lignes (inchange)

- Backend 8/8 fichiers >300L (top : `chunk_service.py` 1014L, `analysis_service.py` 553L, `main.py` 504L).
- Frontend top inchange : `StudioPage.vue` 1450L, `i18n.ts` 1287L (catalogue mono-concept), `DocsLibraryPage.vue` 849L.
- **Regle violee** : 3.3.1 (poids 1).

---

## Points positifs

- **Zero code commente, zero TODO/FIXME/XXX, zero `console.log`, zero `debugger`** sur tout le scope `document-parser/` + `frontend/src/`. Discipline maintenue.
- **Imports ordonnes** : `ruff check .` (rule `I` isort) passe au vert sur la branche.
- **Nommage** : verbes d'action systematiques, pas d'abbreviations ambigues hors `l/t/r/b` legitimes (kwargs Docling Serve bbox).
- **Auto-documentation `pourquoi`** : meme dans le code de test ajoute par `29ab575`, le commentaire explique l'intention (rate-limit HF) et non le mecanisme.
- **Code en anglais homogene** — toutes les chaines visibles transitent par `frontend/src/shared/i18n.ts`.
- **Concept par fichier (3.3.2)** : meme les fichiers >300L restent mono-concept.
- **Ruff pipeline** : `ruff check .` + `ruff format --check .` passent.

---

## Verdict partiel : GO CONDITIONNEL (inchange)

Score **72 / 100**, 0 CRITICAL, **1 MAJOR**, 3 MINOR. **Strictement identique au tour 1 (72/0/1/3/0)**.

**Delta vs baseline `release-0.6.2/03-clean-code.md`** : **0 point**. La fenetre de remediation n'a pas — et n'avait pas a — toucher Clean Code (focus blockers CI/Sec/Docs). La trajectoire reste plate.

**Conditions de remontee a GO (>=80) — inchangees** : voir baseline. Le compteur "cycles sans action" est desormais a **cinq** pour `StudioPage.vue` et `tree_writer.write_document` (a planifier en 0.7.0).

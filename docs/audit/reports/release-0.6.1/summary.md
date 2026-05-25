# Synthese d'audit — Release 0.6.1

**Date** : 2026-05-24
**Branche** : `release/0.6.1`
**Commit audite** : `825e7d7`
**Auditeur** : claude-code

---

## Tableau de bord

| #  | Audit                | Score   | CRIT  | MAJ | MIN | INFO | Verdict          |
|----|----------------------|---------|-------|-----|-----|------|------------------|
| 01 | Clean Architecture   | 75      | **1** | 2   | 1   | 0    | **NO-GO**        |
| 02 | DDD                  | 92      | 0     | 1   | 1   | 0    | GO               |
| 03 | Clean Code           | 72      | 0     | 1   | 3   | 0    | GO CONDITIONNEL  |
| 04 | KISS                 | 87.5    | 0     | 0   | 1   | 3    | GO               |
| 05 | DRY                  | 75      | 0     | 0   | 2   | 2    | GO CONDITIONNEL  |
| 06 | SOLID                | 90      | 0     | 0   | 1   | 1    | GO               |
| 07 | Decouplage           | 74      | 0     | 2   | 3   | 0    | GO CONDITIONNEL  |
| 08 | Securite             | 93      | 0     | 1   | 0   | 2    | GO CONDITIONNEL  |
| 09 | Tests                | 85      | **1** | 0   | 1   | 0    | **NO-GO**        |
| 10 | CI / Build           | **100** | 0     | 0   | 0   | 2    | GO               |
| 11 | Documentation        | **44**  | **2** | 2   | 0   | 1    | **NO-GO**        |
| 12 | Performance          | 61.90   | 0     | 2   | 2   | 1    | GO CONDITIONNEL  |

**Score global (moyenne simple)** : **79.1 / 100** (vs 84.2 en 0.5.0 → -5.1)
**Ecarts CRITICAL totaux** : **4** (vs 1 en 0.5.0)
**Ecarts MAJOR totaux** : **11** (vs 12 en 0.5.0)
**Ecarts MINOR totaux** : 15 (vs 8 en 0.5.0)
**Ecarts INFO totaux** : 12 (vs 6 en 0.5.0)

---

## Ecarts CRITICAL (tous audits confondus)

1. **[01] Les services et la couche API contournent `domain/ports.py` en important directement des modules `infra/`** — `document-parser/services/analysis_service.py:505`, `document-parser/services/ingestion_service.py:221`, `document-parser/services/chunk_service.py:891,974`, `document-parser/api/graph.py:18-19`
   Le scope 0.6 (Neo4j graph storage, `docling_tree`, `docling_graph`) a ete branche sans etendre `domain/ports.py`. Violation directe de l'architecture hexagonale documentee dans `docs/architecture/` et testee par `tests/test_architecture.py` (qui lui-meme ne tourne plus — voir audit 09). **Bloquant absolu**.

2. **[09] 2 modules de tests backend echouent au collect**
   - `document-parser/tests/test_local_converter.py:18` importe `_encode_picture_b64` qui n'existe plus dans le module cible.
   - `document-parser/tests/test_architecture.py:22` requiert `pytestarch` absent du `pyproject.toml`.
   Resultat : le verrou architectural cense detecter precisement le CRIT #1 ci-dessus est silencieux. **Bloquant absolu** (regle absolue master.md §3).

3. **[11] CHANGELOG.md sans section `[0.6.0]` ni `[0.6.1]`** — `CHANGELOG.md:7`
   Derniere entree = `## [0.5.1] - 2026-04-30`. Aucune entree `[Unreleased]`. Environ 75 commits du scope 0.6.x sont totalement non documentes (workspace multi-doc, store CRUD + Fernet sealing #279, version history #283, master feature flags, Karate UI e2e, vocabulaire `analysis`, drop de la migration machinery). Tagger 0.6.1 depuis ce HEAD livrerait un changelog mensonger. **Meme regression qu'en 0.5.0 (1 CRIT non corrige preventivement)**. **Bloquant absolu**.

4. **[11] Breaking changes 0.6.x non identifies** — `CHANGELOG.md`, `docs/`
   Le rename de vocabulaire (`job` -> `analysis`), la suppression de la migration machinery, le format de payload des stores, et le bump des flags par defaut ne sont pas marques `BREAKING` ni accompagnes d'un guide de migration. Risque utilisateur reel. **Bloquant absolu**.

---

## Top blockers (poids 3 / poids 2)

### Bloquants (poids 3 / CRITICAL) — voir section ci-dessus

### Majeurs (poids 2) — a remediar pour passer a GO

- **[01] `api/graph.py` n'a pas de service** — `document-parser/api/graph.py:18-19`
  Endpoints orchestrent eux-memes la logique metier + schemas Pydantic snake_case inline. Creer `GraphService` dans `services/` et router via le port.
- **[01] Services injectes mais aussi importateurs directs de concretions infra** — meme localisation que CRIT #1.
- **[02] Ubiquitous language "job" vs "push" sur l'endpoint push-chunks** — `document-parser/domain/models.py:285`, `document-parser/api/schemas.py:438` (`PushChunksResponse.job_id`), `document-parser/services/chunk_service.py:680`, `frontend/src/features/chunks/ui/ChunksEditor.vue:215`, `frontend/src/shared/i18n.ts:534,1161`
  Renommer `jobId` -> `pushId` (mirror exact du fix 0.5.0 sur `analysis`).
- **[03] Violations SRP — handlers fourre-tout** — `document-parser/services/chunk_service.py::push_to_store` (~118L), `rechunk_document` (~88L), `document-parser/main.py::lifespan` (154L), `document-parser/infra/neo4j/tree_writer.py::write_document` (242L)
  Decouper en fonctions privees < 30L.
- **[07] Couplage UI direct entre features** — `frontend/src/features/reasoning/**` -> `features/analysis/{GraphView,StructureViewer}` ; `features/chunks/**` -> `features/document/StatusBadge` ; `features/chunking/**` -> `features/analysis/**`
  Passer les composants partages dans `shared/` ou inverser la dependance.
- **[07] Couche `api` importe directement `infra`** — `document-parser/api/graph.py:18-19` (`infra.neo4j`, `infra.docling_graph`). Meme cause racine que CRIT #1.
- **[08] `STORE_SECRET_KEY` absent de `.env.example` et docker-compose** — `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml`
  Un operateur qui lance la prod sans definir la cle Fernet scelle des passwords stores avec une cle ephemere -> credentials perdus au prochain redemarrage. Ajouter la cle (obligatoire, sans defaut) + verifier au boot.
- **[11] `frontend/package.json` toujours a `0.5.0`** — `frontend/package.json:3`
  Bumper a `0.6.1` (recurrence exacte du MAJ 0.5.0).
- **[11] Modifications fonctionnelles 0.6.x non documentees** — `CHANGELOG.md`
  Resolu en meme temps que le CRIT #3.
- **[12] Requetes N+1 sur les flux multi-stores** — `document-parser/services/store_service.py:163-164` (list_stores), `document-parser/services/store_service.py:357-358` (list_documents), `document-parser/services/version_service.py:162-192` (restore : soft_delete + edit insert par chunk)
  Batcher en une seule query par store / restore.
- **[12] Blocage I/O synchrone dans des endpoints/services async** — `document-parser/services/document_service.py:81-83` (sync `open()` + `subprocess` poppler dans `async upload`), `document-parser/infra/serve_converter.py:96-102` (sync `open()` passe a httpx)
  Wrapper dans `asyncio.to_thread(...)`.

---

## Quick wins (poids 1 — ameliorations rapides)

- **[01] Schemas Pydantic snake_case inline dans `api/graph.py`** — extraire dans `api/schemas.py` avec convention camelCase comme les autres modules.
- **[02] Entites domaine mutables** — `AnalysisJob`, `Chunk` (`document-parser/domain/models.py`) — passer en `frozen=True` (carry-over 0.5.0).
- **[03] Top 3 fichiers a decouper** — `frontend/src/views/StudioPage.vue` 1450L (3e audit sans action), `frontend/src/features/chunks/ui/ChunkPanel.vue`, `frontend/src/features/document/ResultTabs.vue`. 28 fichiers front + 8 fichiers back > 300L.
- **[04] Wrapper trivial `_to_response`** — etendu de 1 a 5 routers (`documents.py:29`, `stores.py:46/64/78`, `analyses.py:31`, `document_versions.py:38`) — remplacer par `Pydantic.model_validate(..., from_attributes=True)`.
- **[05] Litteraux `table_mode` / `chunker_type` dupliques** sur 6 fichiers backend — extraire en `Enum`.
- **[05] Pattern de polling re-duplique** — `frontend/src/features/reasoning/.../ReasoningPage.vue:113` (3e occurrence depuis 0.5.0) — extraire un composable `usePolling()`.
- **[06] 4 sites consomment `infra.docling_tree` / `infra.neo4j` sans port** — introduire `DocumentTreeReader` et `GraphChunkWriter` dans `domain/ports.py`.
- **[09] Vague assert `X is not None`** — passe de 18 a 50 occurrences. Ajouter une assertion sur la valeur.
- **[12] `frontend/src/features/settings/store.ts:27-39`** — watchers `setInterval+setTimeout` sans cleanup (carry-over 0.5.0).
- **[10] Bug syntaxe `auto-close-issues.yml`** — fix dans le working tree mais non commit.

---

## Verdict final : **NO-GO**

**Justification** : **4 ecarts CRITICAL non resolus** sur les audits 01 (architecture), 09 (tests), 11 (documentation x2) → regle absolue master.md §3 : `tout ecart [CRIT] non resolu = NO-GO quel que soit le score`.

Note complementaire : avec **11 ecarts MAJOR** (seuil master.md §2 = bloquant si > 3 non resolus), le release serait egalement bloque meme sans CRIT.

Le score global (79.1/100) est en-dessous du seuil GO inconditionnel (80) et masque une **double regression structurelle** :
1. **Audit 01** : l'integration Neo4j de 0.6 a court-circuite les ports hexagonaux, **et** le test architectural qui l'aurait detecte est lui-meme casse (audit 09).
2. **Audit 11** : la lecon de 0.5.0 (CHANGELOG manquant) n'a pas ete capitalisee. La situation a **empire** (2 CRIT au lieu de 1).

### Conditions pour passer a GO

**Bloquants absolus (4 actions, ~3 h)** :
1. **[09]** Reparer la collection de tests :
   - `document-parser/tests/test_local_converter.py:18` — supprimer/adapter l'import de `_encode_picture_b64`.
   - `document-parser/tests/test_architecture.py:22` — ajouter `pytestarch` aux dev deps.
2. **[01]** Etendre `domain/ports.py` avec `GraphReader`/`GraphWriter` (+ adapter Neo4j en infra). Reecrire `api/graph.py` via un nouveau `GraphService`. Reecrire les 4 sites services qui importent directement `infra.docling_tree`/`infra.neo4j`/`infra.docling_graph`.
3. **[11]** Ajouter au `CHANGELOG.md` une section `## [0.6.0] - YYYY-MM-DD` (rattrapage) **et** `## [0.6.1] - 2026-05-24` avec sous-sections `Added` / `Changed` / `Fixed` listant le scope reel.
4. **[11]** Identifier explicitement les breaking changes 0.6.x (rename vocabulary `job` -> `analysis`, drop migration machinery, evolution payload stores, bump des feature flags par defaut) sous une rubrique `BREAKING` du CHANGELOG, avec guide de migration.

**Pour passer de GO CONDITIONNEL a GO (4 actions, ~1 h)** :
5. **[11]** Bumper `frontend/package.json` a `0.6.1`.
6. **[08]** Ajouter `STORE_SECRET_KEY` (Fernet) a `.env.example`, `docker-compose.yml` et `docker-compose.dev.yml` avec exigence boot non-vide.
7. **[12]** Wrapper l'upload sync de `services/document_service.py:81-83` et `infra/serve_converter.py:96-102` dans `asyncio.to_thread(...)`.
8. **[02]** Renommer `jobId` -> `pushId` cote API + frontend pour aligner sur le vocabulaire `analysis`/`push`.

**Pour solder la dette structurelle (avant 0.6.2)** :
9. **[12]** Batcher les requetes N+1 sur stores et version restore.
10. **[07]** Casser le couplage `reasoning` <-> `analysis` via composants `shared/`.
11. **[03]** Decouper les 4 handlers > 80L et au moins `StudioPage.vue`.

**Recommandation** : appliquer les 4 bloquants absolus + les 4 actions GO CONDITIONNEL, puis re-auditer **uniquement** les audits 01, 09, 11 (commande : `Re-audite uniquement les ecarts CRITICAL et MAJOR du rapport docs/audit/reports/release-0.6.1/summary.md`). Les MAJ restants des audits 07, 08, 12 peuvent etre planifies pour 0.6.2 sans bloquer le tag.

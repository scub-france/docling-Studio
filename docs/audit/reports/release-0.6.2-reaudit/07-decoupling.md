# Rapport d'audit : Decouplage (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/07-decoupling.md` — 73/100, GO CONDITIONNEL (0 CRIT / 1 MAJ / 3 MIN / 1 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 16 (24 / 33 ponderes) |
| Score | **73 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 1 |

Detail du calcul (somme des poids) :

- Total poids = 33 (16 items : 7.1.1=3, 7.1.2=3, 7.1.3=2, 7.1.4=2, 7.1.5=2, 7.2.1=2, 7.2.2=3, 7.2.3=2, 7.2.4=2, 7.3.1=2, 7.3.2=3, 7.3.3=2, 7.3.4=2, 7.4.1=2, 7.4.2=2, 7.4.3=1)
- Poids non conformes = 9 (7.1.3=2, 7.2.2=3, 7.2.3=2, 7.4.2=2)
- Poids conformes = 24
- Score = 24 / 33 x 100 = **72.7 -> 73 / 100**

**Delta vs baseline `release-0.6.2/07-decoupling.md`** : **0 point** (73 -> 73). Aucune regression, aucune progression. Les ecarts UI heritage de 0.6.0/0.6.1 (cycle analysis <-> reasoning, `RechunkOptions` partage, mock API, `dict` config) sont transportes a l'identique, et le sprint correctif de la branche `fix/0.6.2-audit-blockers` n'a touche que ops/CI/docs + un test mock.

---

## Contexte de la re-audit

La branche `fix/0.6.2-audit-blockers` ne contient **aucune modification de code applicatif** (`document-parser/services/`, `document-parser/api/`, `document-parser/domain/`, `document-parser/infra/`, `frontend/src/`) par rapport a `release/0.6.2` :

```
$ git diff release/0.6.2..HEAD --stat -- document-parser/ frontend/
 document-parser/Dockerfile             | 16 ++++++++++------
 document-parser/tests/test_chunking.py | 18 +++++++++++++++---
```

Les seuls deltas pertinents pour le decouplage sont :

1. **`document-parser/Dockerfile`** : `ARG BAKE_MODELS=true` -> `ARG BAKE_MODELS=false` (#audit-10). Aucun impact sur les couches applicatives.
2. **`document-parser/tests/test_chunking.py:478-500`** : remplacement de `LocalChunker()` par un mock du port `DocumentChunker` (#audit-10). C'est un *renforcement* du decouplage : le test mocke desormais a la frontiere du port plutot que d'instancier l'adaptateur concret.
3. **`docker-compose.yml` + `docker-compose.dev.yml`** : ajout du service `docling-serve` (image `quay.io/docling-project/docling-serve-cpu:v1.21.0`) derriere le profil `remote`, expose via les variables `DOCLING_SERVE_URL` / `DOCLING_SERVE_API_KEY`. Aucun nouveau import cote `document-parser/` ; le port `DocumentConverter` + l'adaptateur `infra/serve_converter.py` etaient deja en place depuis 0.6.0.
4. **`.github/workflows/ci.yml`** : E2E pilote desormais via le container docling-serve distant. Aucun impact sur les couches.
5. **`docs/architecture/huggingface-dependency-map.md` + `CHANGELOG.md`** : documentation, hors perimetre code.

Aucun code de feature frontend n'a ete ajoute ni renomme. Les imports cross-feature, les types partages dans `features/document/`, le pattern API client, et les `dict` dans les schemas Pydantic restent strictement identiques a la baseline 0.6.2.

---

## Suivi des ecarts baseline 0.6.2

| Ecart 0.6.2 | Statut 0.6.2 re-audit | Preuve |
|-------------|----------------------|--------|
| [MAJ] Couplage UI direct entre features (7.2.2) | **REPORTE — identique** | Les 14 lignes d'imports cross-features sont inchangees : `frontend/src/features/reasoning/ui/DocumentView.vue:34-35`, `ReasoningWorkspace.vue:87`, `ReasoningDocPicker.vue:82-83`, `analysis/ui/GraphView.vue:67` (cycle), `analysis/ui/AnalysisPanel.vue:61,63`, `analysis/ui/BboxOverlay.vue:39`, `analysis/ui/StructureViewer.vue:64-65`, `chunking/ui/ChunkPanel.vue:228`, `chunks/ui/StaleStoresStrip.vue:35`. `shared/ui/` contient toujours uniquement `AppSidebar.vue`, `ComingSoonShell.vue`, `PaginationBar.vue`, `index.ts`, `navActive.ts` + `navActive.test.ts`. |
| [MIN] `RechunkOptions` partage via `document/api.ts` (7.2.3) | **REPORTE — identique** | `frontend/src/features/document/api.ts:36` definit toujours l'interface. Imports inchanges : `frontend/src/features/chunks/ui/StrategyPopover.vue:128`, `frontend/src/features/chunks/ui/ChunksPanel.vue:96`. `colorFor` toujours dans `document/elementColors.ts` consomme par `chunks/ui/ChunksPanel.vue:98`. |
| [MIN] Pattern de mock API non explicite (7.1.3) | **REPORTE — identique** | `grep "ApiClient\|apiClient" frontend/src/shared/` = zero match. Les 11 features exposent toujours des fonctions libres au-dessus de `apiFetch` (`frontend/src/features/*/api.ts`). |
| [MIN] `dict` non-type pour `config` (7.4.2) | **REPORTE — identique** | `document-parser/api/schemas.py:296` (`StoreResponse.config: dict`), `:315` (`StoreCreateRequest.config: dict = Field(default_factory=dict)`), `:335` (`StoreUpdateRequest.config: dict | None`). |
| [INFO] `shared/ui/AppSidebar.vue` importe deux stores de features | **REPORTE — identique** | `frontend/src/shared/ui/AppSidebar.vue:55-56` importe toujours `useFeatureFlagStore` et `useIngestionStore`. |

---

## Verification des items 7.x sur HEAD

### 7.1 — Front / Back

- **7.1.1 conforme** : Communication exclusivement REST via `frontend/src/shared/api/http.ts::apiFetch`. `grep "from.*document-parser\|from.*../../../document-parser" frontend/src/` = zero match. Pas de fichier partage, pas de DB partagee.
- **7.1.2 conforme** : Schemas Pydantic alignes 1:1 avec types TS. Le nouveau couple compose docling-serve passe par le contrat HTTP existant (`DocumentConverter` port) — aucun nouveau schema. Camelisation centralisee dans `_CamelModel` inchangee.
- **7.1.3 NON CONFORME** : voir MIN-01 (report).
- **7.1.4 conforme** : Le backend est testable sans frontend. La modification `tests/test_chunking.py:480-500` *renforce* meme cette propriete : le test mocke maintenant le port `DocumentChunker` au lieu d'instancier `LocalChunker()`, evitant un appel reseau HF Hub.
- **7.1.5 conforme** : Validations server-side preservees. `connectionForm.logic.ts` (UI) fait du field-level guard uniquement.

### 7.2 — Inter-features (Frontend)

- **7.2.1 conforme** : Structure `features/<name>/{api.ts,store.ts,ui/}` respectee. Aucune nouvelle feature ajoutee.
- **7.2.2 NON CONFORME** : voir MAJ-01 (report).
- **7.2.3 NON CONFORME** : voir MIN-02 (report).
- **7.2.4 conforme** : Aucun store ne deref directement le state d'un autre store. Pattern de composition cote Vue.

### 7.3 — Inter-couches (Backend)

- **7.3.1 conforme** : Repos retournent du domaine, inchange.
- **7.3.2 conforme** : `grep "from docling\|import docling" document-parser/services/` = zero match. `grep "from neo4j\|import neo4j\|from opensearchpy" document-parser/{services,domain}/` = zero match. La nouvelle consommation `docling-serve` reste **proprement isolee dans `infra/serve_converter.py`** (port adapter pattern existant 0.6.0). Les variables d'env `DOCLING_SERVE_URL` / `DOCLING_SERVE_API_KEY` sont chargees via `infra/settings.py` (lignes 14-15, 143-144), branchees dans `main.py:54-57` (composition root). **Zero leakage vers services/ ou domain/.**
- **7.3.3 conforme** : Aucun import `aiosqlite` hors `persistence/`. Inchange.
- **7.3.4 conforme** : `grep "from infra\|import infra" document-parser/api/` = zero match. L'invariant `TestApiLayerIsolation` continue de verrouiller la regle.

### 7.4 — Contrats

- **7.4.1 conforme** : `domain/ports.py` documente les `Protocol` avec types du domaine. Aucune nouvelle port introduite par le fix-branch.
- **7.4.2 NON CONFORME** : voir MIN-03 (report).
- **7.4.3 conforme** : Format de reponse coherent (FastAPI default envelope + camelCase). Inchange.

---

## Ecarts constates

> **Note** : Les 5 ecarts ci-dessous sont strictement identiques a la baseline `release-0.6.2/07-decoupling.md`. Les localisations, regles violees et remediations sont reportees en l'etat. Le seul changement de fond est l'item 7.1.4 (qui passe de "conforme" a "conforme et renforce") grace au mock au niveau du port `DocumentChunker` dans `tests/test_chunking.py:489-493`.

### [MAJ] Couplage UI direct entre features (analysis <-> reasoning, chunks -> document, chunking -> analysis, analysis -> document)

- **Localisation** :
  - `frontend/src/features/reasoning/ui/DocumentView.vue:34-35` — `import StructureViewer from '../../analysis/ui/StructureViewer.vue'` + `import { useAnalysisStore } from '../../analysis/store'`
  - `frontend/src/features/reasoning/ui/ReasoningWorkspace.vue:87` — `import GraphView from '../../analysis/ui/GraphView.vue'`
  - `frontend/src/features/reasoning/ui/ReasoningDocPicker.vue:82-83` — `useAnalysisStore` + `useDocumentStore`
  - `frontend/src/features/analysis/ui/GraphView.vue:67` — `import { reasoningOverlayStyles } from '../../reasoning/graphReasoningOverlay'` (**cycle** analysis <-> reasoning)
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35` — `import StatusBadge from '../../document/ui/StatusBadge.vue'`
  - `frontend/src/features/chunking/ui/ChunkPanel.vue:228` — `import { useAnalysisStore } from '../../analysis/store'`
  - `frontend/src/features/analysis/ui/AnalysisPanel.vue:61,63` — `useDocumentStore` + `DocumentUpload/DocumentList/PagePreview` depuis `document/index`
  - `frontend/src/features/analysis/ui/BboxOverlay.vue:39` — `computeScale/bboxToRect/pointInRect` depuis `document/bboxScaling`
  - `frontend/src/features/analysis/ui/StructureViewer.vue:64-65` — `getPreviewUrl` + `computeScale/bboxToRect/pointInRect` depuis `document/api` + `document/bboxScaling`
- **Constat** : Inchange depuis la baseline 0.6.2. Le sprint de remediation `fix/0.6.2-audit-blockers` n'a touche ni `frontend/src/features/`, ni `frontend/src/shared/ui/`. Le diff `git diff release/0.6.2..HEAD -- frontend/` = vide.
- **Regle violee** : 7.2.2 — Les features ne s'importent pas mutuellement.
- **Remediation** : Inchangee depuis baseline :
  1. Promouvoir `GraphView.vue`, `StructureViewer.vue`, `StatusBadge.vue` dans `frontend/src/shared/ui/`.
  2. Pour le cycle analysis <-> reasoning : extraire `graphReasoningOverlay.ts` vers `shared/graph/` ou injecter les styles via props.
  3. Pour `useAnalysisStore` consomme par chunking/reasoning : exposer un composable `useAnalysisFor(docId)` dans `shared/composables/`.
  4. Pour `bboxScaling.ts` / `linkedView.ts` partages par chunks <-> document <-> analysis : extraire dans `shared/document/`.

### [MIN] `RechunkOptions` et `colorFor` partages via `features/document/`

- **Localisation** :
  - `frontend/src/features/document/api.ts:36` — definition de `RechunkOptions`
  - `frontend/src/features/document/elementColors.ts:32` — definition de `colorFor`
  - `frontend/src/features/chunks/ui/StrategyPopover.vue:128` — `import type { RechunkOptions } from '../../document/api'`
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:96` — meme import + `:98` `colorFor` depuis `document/elementColors`
- **Constat** : Inchange. Aucune trace de `RechunkOptions` ou `colorFor` dans `frontend/src/shared/`.
- **Regle violee** : 7.2.3 — Les types partages entre features sont dans `shared/types.ts`.
- **Remediation** : Deplacer `RechunkOptions` vers `frontend/src/shared/types.ts` et `colorFor` vers `frontend/src/shared/elementColors.ts`. Garder `rechunkDocument` dans `document/api.ts`.

### [MIN] Frontend API client toujours sans pattern de mock explicite

- **Localisation** : `frontend/src/features/{analysis,document,chunking,chunks,history,search,store,ingestion,reasoning,feature-flags,settings}/api.ts` — fonctions libres au-dessus de `apiFetch`. `frontend/src/shared/api/` n'expose aucune interface `ApiClient`.
- **Constat** : Report identique depuis 0.5.0 (4eme cycle). Les tests continuent de mocker via `vi.mock('./api')` ou `vi.mock('../../shared/api/http')` — convention coherente mais implicite.
- **Regle violee** : 7.1.3 — Le frontend peut tourner avec un mock du backend.
- **Remediation** : Documenter explicitement le pattern (README par feature) ou introduire une couche `ApiClient` injectable dans `shared/api/`.

### [MIN] `dict` non-type pour `config` des stores dans les schemas Pydantic

- **Localisation** : `document-parser/api/schemas.py:296` (`StoreResponse.config: dict`), `:315` (`StoreCreateRequest.config: dict = Field(default_factory=dict)`), `:335` (`StoreUpdateRequest.config: dict | None = None`)
- **Constat** : Inchange.
- **Regle violee** : 7.4.2 — Les schemas Pydantic documentent le contrat HTTP — pas de `dict` ou `Any` dans les responses.
- **Remediation** : Introduire `Neo4jStoreConfig` / `OpenSearchStoreConfig` Pydantic discrimines par `kind` (`Field(discriminator='kind')`).

### [INFO] `shared/ui/AppSidebar.vue` importe deux stores de features (`feature-flags`, `ingestion`)

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56`
- **Constat** : Couplage **inverse** `shared/` -> `features/` inchange. Impact pratique limite (singleton de presentation).
- **Regle violee** : Pas d'item explicite (entre 7.2.2 et l'esprit du layering). Classe INFO.
- **Remediation** : Injecter ces deux signaux via un composable `useAppStatus()` dans `shared/composables/`. Non bloquant.

---

## Points positifs

- **Decouplage Frontend / Backend impeccable** : Communication exclusivement REST via `shared/api/http.ts::apiFetch`. `grep "from.*document-parser" frontend/src/` = zero match. Inchange.
- **Nouvelle dependance docling-serve correctement isolee** : L'introduction du container `docling-serve` (`docker-compose.yml:110-156`, `docker-compose.dev.yml:96-131`) ne genere **aucun nouveau couplage** dans le code applicatif. Tout passe par :
  1. Le port `DocumentConverter` (`domain/ports.py`) — contrat stable.
  2. L'adaptateur `infra/serve_converter.py` — seul fichier qui parle HTTP au container.
  3. Les variables d'env `DOCLING_SERVE_URL` / `DOCLING_SERVE_API_KEY` chargees dans `infra/settings.py:14-15,143-144`.
  4. Le cablage dans `main.py:54-57` (composition root).
  C'est exactement le pattern hexagonal : un nouveau backend exterieur sans aucune fuite vers les couches superieures.
- **Test mock renforce le decouplage** : `document-parser/tests/test_chunking.py:489-493` mocke desormais le port `DocumentChunker` (`AsyncMock` avec `.chunk = AsyncMock(...)`) au lieu d'instancier `LocalChunker()`. C'est une amelioration **architecturalement saine** : le test est independant de l'adaptateur concret et de ses dependances reseau (HF Hub).
- **Architecture hexagonale backend tenue** :
  - `grep "from infra\|import infra" document-parser/api/` = zero match.
  - `grep "from docling\|import docling" document-parser/services/` = zero match.
  - `grep "from neo4j\|import neo4j\|from opensearchpy" document-parser/{services,domain}/` = zero match.
  - Les invariants `tests/test_architecture.py` continuent de verrouiller la grille.
- **Aucune regression sur les inter-features frontend** : Le diff frontend vs `release/0.6.2` est rigoureusement vide. Les 14 imports cross-feature documentes en baseline restent au meme niveau.
- **Pages comme composition root** : Pattern preserve. `pages/StudioPage.vue`, `pages/DocWorkspacePage.vue`, `pages/DocIngestTab.vue`, `pages/DocParseTab.vue`, `pages/DocChunkTab.vue` agregent plusieurs features sans creer de coupling entre elles.

---

## Verdict partiel : GO CONDITIONNEL

**Score 73/100** : Au-dessus du seuil NO-GO (60), en-dessous du seuil GO (80). Zero CRIT, **un MAJ** (7.2.2 couplage UI inter-features) restant, non-bloquant individuellement (regle "bloquant si > 3 MAJ" non atteinte).

**Bilan du fix-branch `fix/0.6.2-audit-blockers`** :
- Aucune regression sur le decouplage (diff applicatif = vide).
- Un **renforcement marginal** sur 7.1.4 (test backend desormais independent de l'adaptateur concret + de HF Hub).
- Une **demonstration en production** du pattern hexagonal : `docling-serve` ajoute en compose sans toucher services/ ou domain/, parce que le port `DocumentConverter` et son adaptateur `ServeConverter` etaient deja en place.
- Aucune progression sur les 4 ecarts heritage (MAJ + 3 MIN), conformes au scope du fix-branch qui ne devait toucher que les blockers `audit-10` / `audit-11` (CI/build, docs).

**Conditions de levee** (inchangees vs baseline 0.6.2) :
1. **[MAJ 7.2.2 — UI couplage inter-features]** Planifier en 0.6.3 (ou plus tot) : promouvoir `GraphView` / `StructureViewer` / `StatusBadge` dans `shared/ui/`, briser le cycle `analysis <-> reasoning`, extraire `bboxScaling` / `linkedView` vers `shared/document/`. Acceptable de shipper 0.6.2 avec la dette si trackee en issue.
2. **[MIN]** Les 3 MIN (RechunkOptions partage, mock API, dict de config) restent compatibles avec un cycle 0.6.3.
3. **[INFO]** Reverse import `shared -> features` dans AppSidebar a ouvrir comme issue tracker (low priority).

**Delta vs baseline `release-0.6.2/07-decoupling.md`** : **0 point** (73 -> 73). Decouplage stable, sans regression. Le fix-branch a tenu sa promesse (scope ops/CI/docs) en ne creant aucun nouveau couplage applicatif, et a meme renforce un test au niveau du port.

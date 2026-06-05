# Rapport d'audit : Decouplage

**Release** : 0.6.2
**Branche** : `release/0.6.2` (HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**Baseline** : `docs/audit/reports/release-0.6.1-reaudit/07-decoupling.md` (73/100, 0 CRIT / 1 MAJ / 3 MIN / 0 INFO, GO CONDITIONNEL)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 16 (24 / 33 ponderes) |
| Score | 73 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 1 |

Detail du calcul (somme des poids) :

- Total poids = 33 (16 items : 7.1.1=3, 7.1.2=3, 7.1.3=2, 7.1.4=2, 7.1.5=2, 7.2.1=2, 7.2.2=3, 7.2.3=2, 7.2.4=2, 7.3.1=2, 7.3.2=3, 7.3.3=2, 7.3.4=2, 7.4.1=2, 7.4.2=2, 7.4.3=1)
- Poids non conformes = 9 (7.1.3=2, 7.2.2=3, 7.2.3=2, 7.4.2=2)
- Poids conformes = 24
- Score = 24 / 33 x 100 = **72.7 -> 73 / 100**

**Delta vs 0.6.1 (re-audit)** : 0 points (73 -> 73). Aucune regression, aucune progression sur les ecarts ouverts. 1 INFO nouvellement documente (pre-existant non flague auparavant : `shared/ui/AppSidebar.vue` importe deux stores de features).

---

## Contexte

La branche `release/0.6.2` introduit trois axes fonctionnels qui pesent sur le decouplage :

1. **#283 — Ingest tab redesign** : nouvelle page `frontend/src/pages/DocIngestTab.vue` (CTA + history-driven shell), composant utilitaire `IngestLaunchDialog.vue` co-localise dans `pages/`, et nouvel endpoint `GET /api/documents/{id}/chunks/pushes`.
2. **#279 — Store form / credentials in DB** : nouveau composant `frontend/src/features/store/ui/StoreForm.vue` + sous-formulaires `StoreConfigForm` / `Neo4jConfigForm` / `OpenSearchConfigForm`, fonction pure `connectionForm.logic.ts`, endpoint `POST /api/stores/{slug}/test-connection`.
3. **#285 — Pending-push badge** : badge ajoute sur la CTA d'ingest dans `pages/DocIngestTab.vue` (re-use de `buildRows` existant).

Les commits backend (#225, #279, #283) ont aussi durci `services/store_service.py` (Fernet box) et `infra/{neo4j,opensearch}_pool.py` (pools per `(uri, user)`), sans changer le contrat de port.

Aucun de ces deltas ne touche aux fichiers qui portaient les ecarts ouverts en 0.6.1 :
- `frontend/src/features/reasoning/ui/{DocumentView,ReasoningWorkspace,ReasoningDocPicker}.vue`
- `frontend/src/features/analysis/ui/{GraphView,StructureViewer,AnalysisPanel,BboxOverlay}.vue`
- `frontend/src/features/chunking/ui/ChunkPanel.vue`
- `frontend/src/features/chunks/ui/{StaleStoresStrip,StrategyPopover,ChunksPanel}.vue`
- `frontend/src/features/document/{api.ts,elementColors.ts}`
- `document-parser/api/schemas.py:296,315,335`

Les ecarts 0.6.1 sont donc transportes a l'identique.

---

## Suivi des ecarts 0.6.1

| Ecart 0.6.1 | Statut 0.6.2 | Preuve |
|-------------|--------------|--------|
| [MAJ] Couplage UI direct entre features (7.2.2) | **REPORTE** | Tous les imports cibles persistent au meme emplacement : `frontend/src/features/reasoning/ui/DocumentView.vue:34-35`, `frontend/src/features/reasoning/ui/ReasoningWorkspace.vue:87`, `frontend/src/features/reasoning/ui/ReasoningDocPicker.vue:82-83`, `frontend/src/features/analysis/ui/GraphView.vue:67`, `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35`, `frontend/src/features/chunking/ui/ChunkPanel.vue:228`, `frontend/src/features/analysis/ui/AnalysisPanel.vue:61,63`, `frontend/src/features/analysis/ui/BboxOverlay.vue:39`, `frontend/src/features/analysis/ui/StructureViewer.vue:64-65`. Aucun composant n'a ete promu dans `shared/ui/` (toujours `AppSidebar.vue`, `ComingSoonShell.vue`, `PaginationBar.vue` + `index.ts` + `navActive`). |
| [MIN] `RechunkOptions` partage via `document/api.ts` (7.2.3) | **REPORTE** | `frontend/src/features/document/api.ts:36` definit toujours l'interface. Imports inchanges : `frontend/src/features/chunks/ui/StrategyPopover.vue:128`, `frontend/src/features/chunks/ui/ChunksPanel.vue:96`. Idem pour `colorFor` (`frontend/src/features/chunks/ui/ChunksPanel.vue:98` <- `frontend/src/features/document/elementColors.ts:32`). |
| [MIN] Pattern de mock API non explicite (7.1.3) | **REPORTE** | `grep "ApiClient\|apiClient" frontend/src/shared/` = zero match. Les 11 features (`analysis`, `chunking`, `chunks`, `document`, `feature-flags`, `history`, `ingestion`, `reasoning`, `search`, `settings`, `store`) exposent toujours des fonctions libres au-dessus de `apiFetch` (`frontend/src/features/*/api.ts`). |
| [MIN] `dict` non-type pour `config` (7.4.2) | **REPORTE** | `document-parser/api/schemas.py:296` (`StoreResponse.config: dict`), `:315` (`StoreCreateRequest.config: dict = Field(default_factory=dict)`), `:335` (`StoreUpdateRequest.config: dict | None`). |

---

## Verification des items 7.x sur HEAD

### 7.1 — Front / Back

- **7.1.1 conforme** : Communication exclusivement REST via `frontend/src/shared/api/http.ts::apiFetch`. `grep "from.*document-parser\|from.*../../../document-parser" frontend/src/` = zero match. Pas de fichier partage, pas de DB partagee.
- **7.1.2 conforme** : Les schemas Pydantic backend (camelCase via `alias_generator`) alignes 1:1 avec les types TS. Exemples nouveaux 0.6.2 : `ChunkPushEntryResponse` / `ChunkPushListResponse` (`document-parser/api/schemas.py:451,471`) <-> `ChunkPushEntry` (`frontend/src/features/chunks/api.ts`). `StoreTestConnectionResponse` (`document-parser/api/schemas.py:342`) <-> `StoreTestConnectionResult` (`frontend/src/features/store/api.ts`). Aligned 1:1.
- **7.1.3 NON CONFORME** : voir MIN-01.
- **7.1.4 conforme** : Le backend est testable sans frontend (`document-parser/tests/test_*_endpoints.py`, `httpx.AsyncClient`).
- **7.1.5 conforme** : Les validations restent server-side. `connectionForm.logic.ts` (UI) fait du field-level guard (URI vide, password requis), pas du metier duplique.

### 7.2 — Inter-features (Frontend)

- **7.2.1 conforme** : Chaque feature `frontend/src/features/<name>/` a `api.ts` + `store.ts` (ou stateless) + `ui/`. La nouvelle feature `store/` (#279) respecte ce contrat : `store/api.ts`, `store/ui/StoreForm.vue`, `store/ui/connectionForm.logic.ts`. Pas de store Pinia inutile (ce sont des Vue components stateless + appels API directs depuis les pages).
- **7.2.2 NON CONFORME** : voir MAJ-01.
- **7.2.3 NON CONFORME** : voir MIN-02.
- **7.2.4 conforme** : Aucun store ne deref directement le state d'un autre store. Les acces inter-stores se font cote composant Vue (les composants importent les deux stores).

### 7.3 — Inter-couches (Backend)

- **7.3.1 conforme** : Les repos retournent des dataclasses du domaine. Verifie sur les 9 repos modifies en 0.6.2 (`document_repo`, `chunk_repo`, `chunk_audit_repo`, `chunk_push_repo`, `store_repo`, `document_store_link_repo`, `analysis_repo`, etc.). Exemple : `persistence/store_repo.py` retourne `Store` (`domain/models.py`), pas un `Row` SQLite.
- **7.3.2 conforme** : `grep "from docling\|import docling" document-parser/services/` = zero match. `grep "from neo4j\|import neo4j\|from opensearchpy" document-parser/{services,domain}/` = zero match. Toutes les libs externes sont cantonnees dans `infra/`. Les mentions de "Fernet" dans `services/store_service.py:228` et `domain/models.py:152` sont des docstrings, pas des imports.
- **7.3.3 conforme** : Le changement de DB n'impacterait que `persistence/`. Aucun import `aiosqlite` hors `persistence/database.py` + `persistence/*_repo.py` (verifie via grep).
- **7.3.4 conforme** : `grep "from infra\|import infra" document-parser/api/` = zero match (statut hotfix 0.6.1 preserve). Le test invariant `TestApiLayerIsolation` (`document-parser/tests/test_architecture.py:144`) verrouille la regle.

### 7.4 — Contrats

- **7.4.1 conforme** : `domain/ports.py` documente les `Protocol` avec types du domaine. Les ports `GraphReader` / `DocumentGraphProjector` ajoutes en 0.6.1 sont stables. La nouvelle port pour `services.store_resolver.StoreBackend` (#279) est definie dans `domain/ports.py` aussi.
- **7.4.2 NON CONFORME** : voir MIN-03.
- **7.4.3 conforme** : Format de reponse coherent (FastAPI default envelope + camelCase). Nouvel endpoint `GET /chunks/pushes` retourne le meme pattern d'enveloppe paginee `{items, total, limit, offset}` (`document-parser/api/document_chunks.py:240-244`) deja utilise pour les chunks et l'historique.

---

## Ecarts constates

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
- **Constat** : Inchange depuis 0.6.1 (re-audit). Le sprint 0.6.2 a livre 3 features fonctionnelles (Ingest tab redesign #283, store form #279, pending-push badge #285) sans toucher au refactor de promotion vers `shared/ui/`. Le diff `grep "from.*['\"]\.\./\.\./" frontend/src/features/` aujourd'hui rend les **memes 14 lignes** que la baseline 0.6.1 (cycle `analysis <-> reasoning` inclus). Le repertoire `shared/ui/` contient toujours uniquement `AppSidebar.vue`, `ComingSoonShell.vue`, `PaginationBar.vue` + `navActive.ts` — aucun composant metier promu.
- **Note positive** : Les nouvelles features 0.6.2 (`store/ui/StoreForm.vue`, `store/ui/Neo4jConfigForm.vue`, `store/ui/OpenSearchConfigForm.vue`, `ingestion/ui/IngestPanel.vue`) **n'introduisent aucun nouveau couplage inter-features** : leurs imports vont exclusivement vers `shared/` et leur propre feature. Verifie via `grep "from.*['\"]\.\./\.\./" frontend/src/features/store/ frontend/src/features/ingestion/` qui ne renvoie que des imports `shared/`.
- **Note d'attenuation** : Les pages (`frontend/src/pages/*.vue`) consomment plusieurs features (pattern composition root), ce qui est **acceptable** selon la regle 7.2.2 (les pages ne sont pas des "features"). C'est l'agregation correcte. Exemples : `pages/DocIngestTab.vue:130-131` consomme `chunks/api` + `store/api`, `pages/StudioPage.vue:512-522` agrege 6 features. Non penalise.
- **Regle violee** : 7.2.2 — Les features ne s'importent pas mutuellement.
- **Remediation** : Inchangee depuis la baseline :
  1. Promouvoir `GraphView.vue`, `StructureViewer.vue`, `StatusBadge.vue` dans `frontend/src/shared/ui/`.
  2. Pour le cycle analysis <-> reasoning : extraire `graphReasoningOverlay.ts` vers `shared/graph/` ou injecter les styles via props.
  3. Pour `useAnalysisStore` consomme par chunking/reasoning : exposer un composable `useAnalysisFor(docId)` dans `shared/composables/`.
  4. Pour `bboxScaling.ts` / `linkedView.ts` partages par chunks <-> document <-> analysis : extraire dans `shared/document/` (transversal au DocWorkspace, deja co-localise dans `pages/DocChunkTab.vue:79`, `pages/DocParseTab.vue:123`).

### [MIN] `RechunkOptions` et `colorFor` partages via `features/document/`

- **Localisation** :
  - `frontend/src/features/document/api.ts:36` — definition de `RechunkOptions`
  - `frontend/src/features/document/elementColors.ts:32` — definition de `colorFor`
  - `frontend/src/features/chunks/ui/StrategyPopover.vue:128` — `import type { RechunkOptions } from '../../document/api'`
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:96` — meme import + `:98` `colorFor` depuis `document/elementColors`
- **Constat** : Inchange. La regle 7.2.3 exige que les types partages entre features vivent dans `shared/types.ts`. Aucune trace de `RechunkOptions` ou `colorFor` dans `frontend/src/shared/` (verifie via grep).
- **Regle violee** : 7.2.3 — Les types partages entre features sont dans `shared/types.ts`.
- **Remediation** : Deplacer `RechunkOptions` vers `frontend/src/shared/types.ts` et `colorFor` vers `frontend/src/shared/elementColors.ts`. Garder `rechunkDocument` dans `document/api.ts`.

### [MIN] Frontend API client toujours sans pattern de mock explicite

- **Localisation** : `frontend/src/features/{analysis,document,chunking,chunks,history,search,store,ingestion,reasoning,feature-flags,settings}/api.ts` — fonctions libres au-dessus de `apiFetch`. `frontend/src/shared/api/` n'expose aucune interface `ApiClient`.
- **Constat** : Report identique depuis 0.5.0 (3eme cycle). Le sprint 0.6.2 n'introduit pas d'abstraction injectable. Les tests continuent de mocker via `vi.mock('./api')` (voir `frontend/src/__tests__/integration/history-navigation.test.ts`, et les `*api.test.ts` co-localises qui stubent `apiFetch` via `vi.mock('../../shared/api/http')`).
- **Regle violee** : 7.1.3 — Le frontend peut tourner avec un mock du backend.
- **Remediation** : Documenter explicitement le pattern (README par feature) ou introduire une couche `ApiClient` injectable dans `shared/api/`. Acceptable en l'etat : la convention `vi.mock` est consistante et chaque feature isole bien son contrat HTTP.

### [MIN] `dict` non-type pour `config` des stores dans les schemas Pydantic

- **Localisation** : `document-parser/api/schemas.py:296` (`StoreResponse.config: dict`), `:315` (`StoreCreateRequest.config: dict = Field(default_factory=dict)`), `:335` (`StoreUpdateRequest.config: dict | None = None`)
- **Constat** : Inchange. Le sprint #279 a ajoute les champs `connection_uri` / `connection_username` / `connection_password` proprement types (`str | None`), mais le `config: dict` historique persiste. Le champ est intrinsequement heterogene (Neo4j vs OpenSearch vs futurs backends), mais au minimum un `dict[str, Any]` explicite ou un `RootModel` discrimine ameliorerait l'auto-documentation OpenAPI.
- **Regle violee** : 7.4.2 — Les schemas Pydantic documentent le contrat HTTP — pas de `dict` ou `Any` dans les responses.
- **Remediation** : Introduire `Neo4jStoreConfig` / `OpenSearchStoreConfig` Pydantic discrimines par `kind` (`Field(discriminator='kind')`).

### [INFO] `shared/ui/AppSidebar.vue` importe deux stores de features (`feature-flags`, `ingestion`)

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56`
  ```
  import { useFeatureFlagStore } from '../../features/feature-flags/store'
  import { useIngestionStore } from '../../features/ingestion/store'
  ```
- **Constat** : Couplage **inverse** `shared/` -> `features/` (la couche basse importe une couche haute). Pre-existant (introduit en 0.6.0 via commit `daaea86` pour le polling OpenSearch et reinforce en 0.6.0 via `4f38791` pour le gate `ingestionEnabled`), **non flague** dans les baselines precedentes — releve cette fois car le perimetre 0.6.2 (Ingest tab + push badge) renforce la centralite de `useIngestionStore`. Strictement parlant, la regle 7.2.2 vise les imports inter-features ; cet ecart ressort plutot d'un principe de layering. Impact pratique limite : la sidebar est un singleton de presentation, pas une feature au sens DDD.
- **Regle violee** : Pas d'item explicite (entre 7.2.2 et l'esprit du layering). Classe INFO.
- **Remediation** : Injecter ces deux signaux via le store global de l'app shell (ex : `shared/app/state.ts`) ou exposer un composable `useAppStatus()` dans `shared/composables/` qui agrege les deux signaux. Non bloquant — la connaissance par `AppSidebar` du flag d'ingestion est conceptuellement legitime, c'est l'import direct du store qui rompt la direction des dependances.

---

## Points positifs

- **Decouplage Frontend / Backend toujours impeccable** : Communication exclusivement REST via `shared/api/http.ts::apiFetch`. Aucun import croise front <-> back. `grep "from.*document-parser" frontend/src/` = zero match.
- **Nouveaux endpoints 0.6.2 alignes 1:1 avec les types TS** :
  - `GET /api/documents/{id}/chunks/pushes` (`document-parser/api/document_chunks.py:223`) <-> `ChunkPushEntry` (`frontend/src/features/chunks/api.ts`).
  - `POST /api/stores/{slug}/test-connection` (`document-parser/api/stores.py`) <-> `StoreTestConnectionResult` (`frontend/src/features/store/api.ts:1`).
  - Camelisation centralisee dans `_CamelModel` (`document-parser/api/schemas.py`).
- **Architecture hexagonale backend tenue** :
  - `grep "from infra\|import infra" document-parser/api/` = zero match (statut 0.6.1 preserve).
  - `grep "from docling\|import docling" document-parser/services/` = zero match.
  - `grep "from neo4j\|import neo4j\|from opensearchpy" document-parser/{services,domain}/` = zero match.
  - Les invariants `tests/test_architecture.py` (`TestApiLayerIsolation`, `TestServicesLayerIsolation`, `TestDomainLayerIsolation`, `TestInfraLayerIsolation`, `TestPersistenceLayerIsolation`, `TestPortConvention`) verrouillent la grille a chaque PR.
- **Aucun nouveau couplage inter-features cote frontend** : Les 3 features fonctionnelles 0.6.2 (`store/ui/{StoreForm,Neo4jConfigForm,OpenSearchConfigForm,StoreConfigForm}.vue`, `ingestion/ui/IngestPanel.vue`, `pages/DocIngestTab.vue` + `IngestLaunchDialog.vue`) consomment exclusivement `shared/` et leur propre feature. Aucune importation crosshair vers `analysis/`, `chunking/`, `chunks/`, `document/`, `reasoning/` n'a ete ajoutee.
- **Nouvelles features backend 0.6.2 (Fernet box, pools per `(uri, user)`) respectent la regle de couches** : `services/store_service.py` n'importe ni `cryptography` ni `neo4j` (le sealing est delegue a `infra/secret_box.py`, le pool a `infra/neo4j_pool.py` via le port `services.store_resolver.StoreBackend`).
- **Repos retournent du domaine** : `persistence/{store,document_store_link,chunk_push,document,analysis,chunk,chunk_audit}_repo.py` retournent des dataclasses (`Store`, `DocumentStoreLink`, `ChunkPush`, ...) — `persistence/store_repo.py` notamment construit un `Store` avec ses champs et la `Fernet`-encrypted password expose via `seal/` accessor distinct.
- **Stores Pinia respectent 7.2.4** : Chaque store de feature ne reference que son propre state. Les acces inter-stores se font cote composant Vue (`pages/DocWorkspacePage.vue:94-98` agrege analysis + chunks + document + feature-flags, `pages/DocIngestTab.vue` agrege chunks + store cote API uniquement).
- **Pages comme composition root** : Le pattern utilise consistantement (`pages/StudioPage.vue:512-522` agrege 6 features, `pages/DocParseTab.vue:119-127` agrege 3 features) est la maniere correcte de cabler des features sans les coupler.

---

## Verdict partiel : GO CONDITIONNEL

**Score 73/100** : Au-dessus du seuil NO-GO (60), en-dessous du seuil GO (80). Zero CRIT, **un MAJ** (7.2.2 couplage UI inter-features) restant, non-bloquant individuellement (regle "bloquant si > 3 MAJ" non atteinte).

**Progression** :
- Aucune regression : les nouveaux features 0.6.2 ne creent pas de couplage inter-features.
- Aucune progression : le refactor de promotion vers `shared/ui/` planifie en 0.6.1 n'a pas ete amorce sur le sprint 0.6.2.
- 1 INFO ajoute (`shared/ui/AppSidebar.vue` importe deux stores de features) qui pourrait etre adresse en meme temps que le MAJ.

**Conditions de levee** (inchangees vs 0.6.1) :
1. **[MAJ 7.2.2 — UI couplage inter-features]** Planifier en 0.6.3 (ou plus tot) : promouvoir `GraphView` / `StructureViewer` / `StatusBadge` dans `shared/ui/`, briser le cycle `analysis <-> reasoning`, extraire `bboxScaling` / `linkedView` vers `shared/document/`. Acceptable de shipper 0.6.2 avec la dette si trackee en issue.
2. **[MIN]** Les 3 MIN (RechunkOptions partage, mock API, dict de config) restent compatibles avec un cycle 0.6.3.
3. **[INFO]** Reverse import `shared -> features` dans AppSidebar a ouvrir comme issue tracker (low priority).

**Delta vs 0.6.1 re-audit** : **0 point** (73 -> 73). Decoupling stable, sans regression. Le sprint 0.6.2 a tenu sa promesse en ne creant aucun nouveau couplage, mais la dette UI heritee de 0.6.0/0.6.1 reste a payer.

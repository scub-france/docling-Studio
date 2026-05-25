# Rapport d'audit : Decouplage

**Release** : 0.6.1 (re-audit)
**Branche** : `fix/0.6.1-audit-blockers` (HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 16 |
| Score | 73 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 0 |

Detail du calcul (somme des poids) :

- Total poids = 33 (16 items : 7.1.1=3, 7.1.2=3, 7.1.3=2, 7.1.4=2, 7.1.5=2, 7.2.1=2, 7.2.2=3, 7.2.3=2, 7.2.4=2, 7.3.1=2, 7.3.2=3, 7.3.3=2, 7.3.4=2, 7.4.1=2, 7.4.2=2, 7.4.3=1)
- Poids non conformes = 9 (7.1.3=2, 7.2.2=3, 7.2.3=2, 7.4.2=2)
- Poids conformes = 24
- Score = 24 / 33 × 100 = **72.7 → 73 / 100**

Delta vs 0.6.1 initial (74/100, 0 CRIT / 2 MAJ / 3 MIN / 0 INFO) :

- **-1 pt** sur le score brut recalcule (formule poids stricte applique uniformement).
- **MAJ -1** : `api/graph.py -> infra` est ferme (CRIT-01 implemente, voir reaudit 01).
- **MAJ inchange** : couplage UI inter-features non remediee par ce hotfix.
- **3 MIN inchanges** : `RechunkOptions` partage, pattern mock API, `dict` non-type pour `config`.

Note methodologique : le rapport 0.6.1 initial affiche 74/100 ; le recalcul strict de la formule (poids fail = 11 sur 33) donne 67/100 a date 0.6.1. La progression reelle de cette re-audit est donc **+6 pts** sur la grille appliquee de maniere homogene, grace a la cloture du MAJ backend.

---

## Suivi des ecarts 0.6.1

| Ecart 0.6.1 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] `api/graph.py` -> `infra.neo4j` + `infra.docling_graph` (7.3.4) | **RESOLU** | `document-parser/api/graph.py:24` n'importe plus que `from services.graph_service import GraphService, GraphServiceError`. Wiring via `app.state.graph_service` (`document-parser/main.py:341-343`). Ports `GraphReader` / `DocumentGraphProjector` definis dans `domain/ports.py:344-410`. `grep "from infra\|import infra" document-parser/api/` retourne zero match. |
| [MAJ] Couplage UI direct entre features (7.2.2) | **REPORTE** | Tous les imports cibles persistent : `frontend/src/features/reasoning/ui/DocumentView.vue:34-35` (StructureViewer + useAnalysisStore), `frontend/src/features/reasoning/ui/ReasoningWorkspace.vue:87` (GraphView), `frontend/src/features/reasoning/ui/ReasoningDocPicker.vue:82-83` (useAnalysisStore + useDocumentStore), `frontend/src/features/analysis/ui/GraphView.vue:67` (reasoningOverlayStyles — couplage bidirectionnel), `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35` (StatusBadge), `frontend/src/features/chunking/ui/ChunkPanel.vue:228` (useAnalysisStore), `frontend/src/features/analysis/ui/AnalysisPanel.vue:61,63` (useDocumentStore + DocumentUpload/DocumentList/PagePreview). |
| [MIN] `RechunkOptions` partage via `document/api.ts` (7.2.3) | **REPORTE** | `frontend/src/features/document/api.ts:36` definit toujours l'interface ; `frontend/src/features/chunks/ui/StrategyPopover.vue:128` + `frontend/src/features/chunks/ui/ChunksPanel.vue:96` l'importent toujours via `'../../document/api'`. Idem pour `colorFor` (`frontend/src/features/chunks/ui/ChunksPanel.vue:98`). |
| [MIN] Pattern de mock API non explicite (7.1.3) | **REPORTE** | `frontend/src/shared/` ne contient aucune interface `ApiClient` (grep zero match). Les 9 `features/*/api.ts` exposent toujours des fonctions libres au-dessus de `apiFetch`. |
| [MIN] `dict` non-type pour `config` (7.4.2) | **REPORTE** | `document-parser/api/schemas.py:296,315,335` exposent toujours `config: dict` dans `StoreResponse`, `StoreCreateRequest`, `StoreUpdateRequest`. |

---

## Ecarts constates

### [MAJ] Couplage UI direct entre features (analysis <-> reasoning, chunks -> document, chunking -> analysis, analysis -> document)

- **Localisation** :
  - `frontend/src/features/reasoning/ui/DocumentView.vue:34-35` — `import StructureViewer from '../../analysis/ui/StructureViewer.vue'` + `import { useAnalysisStore } from '../../analysis/store'`
  - `frontend/src/features/reasoning/ui/ReasoningWorkspace.vue:87` — `import GraphView from '../../analysis/ui/GraphView.vue'`
  - `frontend/src/features/reasoning/ui/ReasoningDocPicker.vue:82-83` — `useAnalysisStore` + `useDocumentStore` consommes par une 3eme feature
  - `frontend/src/features/analysis/ui/GraphView.vue:67` — `import { reasoningOverlayStyles } from '../../reasoning/graphReasoningOverlay'` (**cycle** analysis <-> reasoning)
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35` — `import StatusBadge from '../../document/ui/StatusBadge.vue'`
  - `frontend/src/features/chunking/ui/ChunkPanel.vue:228` — `import { useAnalysisStore } from '../../analysis/store'`
  - `frontend/src/features/analysis/ui/AnalysisPanel.vue:61,63` — `useDocumentStore` + composants de `document/index`
  - `frontend/src/features/analysis/ui/BboxOverlay.vue:39`, `frontend/src/features/analysis/ui/StructureViewer.vue:64-65` — `getPreviewUrl` + `computeScale`/`bboxToRect`/`pointInRect` depuis `document/bboxScaling` et `document/api`
- **Constat** : Inchange depuis 0.6.1. La feature `reasoning` (introduite en 0.6) consomme directement des composants Vue et des stores de `analysis` et `document` ; reciproquement, `analysis/ui/GraphView.vue` importe `reasoningOverlayStyles` depuis `reasoning/`, etablissant un couplage **bidirectionnel**. La regle 7.2.2 exige que la communication inter-features passe par `shared/` ou par props/events Vue. Le repertoire `frontend/src/shared/ui/` ne contient que `AppSidebar.vue`, `ComingSoonShell.vue`, `PaginationBar.vue` — aucun composant metier promu. Le hotfix `fix/0.6.1-audit-blockers` n'a pas adresse ce point (focus backend `#audit-01`/`#audit-02`/`#audit-08`/`#audit-11`/`#audit-12`).
- **Regle violee** : 7.2.2 — Les features ne s'importent pas mutuellement.
- **Remediation** : Inchangee — proposition 0.6.2 :
  1. Promouvoir `GraphView.vue`, `StructureViewer.vue`, `StatusBadge.vue` dans `frontend/src/shared/ui/`.
  2. Pour le cycle analysis <-> reasoning : extraire `graphReasoningOverlay.ts` vers `shared/graph/` ou injecter les styles via props.
  3. Pour `useAnalysisStore` consomme par chunking/reasoning : exposer un composable `useAnalysisFor(docId)` dans `shared/composables/`.

### [MIN] `RechunkOptions` est defini dans `features/document/api.ts` mais consomme par la feature `chunks`

- **Localisation** :
  - `frontend/src/features/document/api.ts:36` — definition de l'interface
  - `frontend/src/features/chunks/ui/StrategyPopover.vue:128` — `import type { RechunkOptions } from '../../document/api'`
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:96` — meme import
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:98` — `import { colorFor } from '../../document/elementColors'` (meme symptome)
- **Constat** : Inchange. La regle 7.2.3 stipule que les types partages entre features doivent vivre dans `shared/types.ts`. Aucune trace de `RechunkOptions` ou `colorFor` dans `frontend/src/shared/`.
- **Regle violee** : 7.2.3 — Les types partages entre features sont dans `shared/types.ts`.
- **Remediation** : Deplacer `RechunkOptions` (et `colorFor`) vers `frontend/src/shared/types.ts` / `frontend/src/shared/`. Garder la fonction `rechunkDocument` dans `document/api.ts`.

### [MIN] Frontend API client toujours sans pattern de mock explicite

- **Localisation** : `frontend/src/features/{analysis,document,chunking,chunks,history,search,store,ingestion,reasoning}/api.ts` — fonctions libres au-dessus de `apiFetch`. `frontend/src/shared/api/` n'expose aucune interface `ApiClient`.
- **Constat** : Report identique du MIN 0.6.1 et 0.5.0. Le hotfix n'introduit pas d'abstraction injectable. Les tests continuent de mocker via `vi.mock('./api')` (voir `frontend/src/__tests__/integration/history-navigation.test.ts`).
- **Regle violee** : 7.1.3 — Le frontend peut tourner avec un mock du backend.
- **Remediation** : Inchangee — documenter explicitement le pattern (README par feature) ou introduire une couche `ApiClient` injectable dans `shared/api/`.

### [MIN] `dict` non-type pour `config` des stores dans les schemas Pydantic

- **Localisation** : `document-parser/api/schemas.py:296` (`StoreResponse.config: dict`), `:315` (`StoreCreateRequest.config: dict = Field(default_factory=dict)`), `:335` (`StoreUpdateRequest.config: dict | None = None`)
- **Constat** : Inchange. Le champ est intrinsequement heterogene (Neo4j vs OpenSearch vs futurs backends) ; au minimum un `dict[str, Any]` explicite ou un `RootModel` discrimine ameliorerait l'auto-documentation OpenAPI.
- **Regle violee** : 7.4.2 — Les schemas Pydantic documentent le contrat HTTP — pas de `dict` ou `Any` dans les responses.
- **Remediation** : Introduire `Neo4jStoreConfig` / `OpenSearchStoreConfig` Pydantic discrimines par `kind` (`Field(discriminator='kind')`).

---

## Points positifs

- **CRIT-01 ferme proprement** : `document-parser/api/graph.py:24` n'importe que `services.graph_service.GraphService`. Le docstring du module documente explicitement "No infra imports (#audit-01)". Ports `GraphReader`, `GraphWriter`, `DocumentGraphProjector` definis dans `domain/ports.py:344-410`. Le service `services/graph_service.py:81-82` injecte `graph_reader` (optionnel) + `graph_projector` (obligatoire) sur signature ; wiring fait dans `main.py:341-343` avec les adaptateurs `Neo4jGraphReader` / `Neo4jGraphWriter` (`main.py:262-265`).
- **`grep "from infra\|import infra" document-parser/api/` = zero match** : la couche HTTP backend respecte desormais strictement la regle 7.3.4 + l'invariant `TestApiLayerIsolation` (`tests/test_architecture.py`).
- **Decouplage Frontend/Backend toujours solide** : Communication exclusivement REST via `shared/api/http.ts::apiFetch`. Aucun import croise front <-> back.
- **Stores Pinia respectent 7.2.4** : Chaque store de feature ne reference que son propre store (`useReasoningStore` dans `reasoning/ui/*.vue`, `useChunksStore` dans `chunks/ui/ChunksPanel.vue:99`, `useChunkingStore` dans `chunking/ui/ChunkPanel.vue:227`). Les acces inter-stores se font via les composants UI ou via mock dans `__tests__/integration/`.
- **Hexagonal Architecture backend respecte** : Services importent uniquement `domain.*` (verifie pour `graph_service.py`, `analysis_service.py`, `chunk_service.py`, etc.). Aucun `from docling` / `import docling` dans `services/` ni `domain/`.
- **Repos retournent du domaine** : `persistence/{document,analysis,store}_repo.py` retournent des dataclasses du domaine.
- **Ports clairement typees** : Le nouveau `GraphReader` / `DocumentGraphProjector` (`domain/ports.py:344-410`) suit le meme contrat `Protocol` que les ports existants (`ReasoningRunner`, etc.).
- **Schemas TS reasoning aligned 1:1 avec docling-agent** : `frontend/src/features/reasoning/types.ts:9-17`.

---

## Verdict partiel : GO CONDITIONNEL

**Score 73/100** : Au-dessus du seuil NO-GO (60), en-dessous du seuil GO (80). Zero CRIT, **un seul MAJ restant** (vs 2 en 0.6.1 initial), non-bloquant individuellement (regle "bloquant si > 3 MAJ" non atteinte).

**Progression** :
- MAJ backend `api/graph.py -> infra` **ferme** par CRIT-01 (port `GraphReader` + service + wiring complet).
- 4 ecarts ouverts (1 MAJ + 3 MIN) tous **portes vers 0.6.2** sans regression.

**Conditions de levee** (inchangees vs 0.6.1) :
1. **[MAJ 7.2.2 — UI couplage inter-features]** Planifier en 0.6.2 : promouvoir `GraphView`/`StructureViewer`/`StatusBadge` dans `shared/ui/`, briser le cycle analysis <-> reasoning. Acceptable de shipper 0.6.1 avec la dette si trackee en issue.
2. **[MIN]** Les 3 MIN (RechunkOptions partage, mock API, dict de config) peuvent etre adresses en 0.6.2.

Le hotfix `fix/0.6.1-audit-blockers` a tenu sa promesse cote backend pour cet audit : suppression du couplage `api -> infra` sur le perimetre graph via ports/adapters proprement implementes. Le couplage UI inter-features reste le seul axe d'amelioration significatif pour 0.6.2.

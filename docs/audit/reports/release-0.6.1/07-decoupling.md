# Rapport d'audit : Decouplage

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 15 |
| Score | 74 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 0 |

Delta vs 0.5.0 : **-12 pts** (86 -> 74), 0 CRIT inchange, +1 MAJ, +2 MIN.

---

## Suivi des ecarts 0.5.0

| Ecart 0.5.0 | Statut 0.6.1 | Preuve |
|-------------|--------------|--------|
| [MAJ] Inter-store coupling dans `features/history/navigation.test.ts` (7.2.2) | **RESOLU** | Test deplace dans `frontend/src/__tests__/integration/history-navigation.test.ts` avec docstring explicite ("Lives under `src/__tests__/integration/` because importing real stores from three sibling features would be a feature-isolation violation in any single-feature test file"). Le repertoire `frontend/src/features/history/` ne contient plus aucun `navigation*` (ls verifie). |
| [MIN] Pas de pattern de mock API explicite (7.1.3) | **REPORTE** | Aucun changement structurel : les `features/*/api.ts` exposent toujours des fonctions libres au-dessus de `apiFetch` (`frontend/src/features/{analysis,document,chunking,chunks,history,search,store,ingestion,reasoning}/api.ts`). Mock toujours possible via `vi.mock` au cas par cas mais aucune interface `ApiClient` injectable. |

---

## Ecarts constates

### [MAJ] Couplage UI direct entre features (analysis <-> reasoning, chunks -> document, chunking -> analysis)

- **Localisation** :
  - `frontend/src/features/reasoning/ui/DocumentView.vue:34-35` — `import StructureViewer from '../../analysis/ui/StructureViewer.vue'` + `useAnalysisStore`
  - `frontend/src/features/reasoning/ui/ReasoningWorkspace.vue:87` — `import GraphView from '../../analysis/ui/GraphView.vue'`
  - `frontend/src/features/reasoning/ui/ReasoningDocPicker.vue:82-83` — `useAnalysisStore` + `useDocumentStore` consommes par une 3eme feature
  - `frontend/src/features/analysis/ui/GraphView.vue:67` — `import { reasoningOverlayStyles } from '../../reasoning/graphReasoningOverlay'`
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35` — `import StatusBadge from '../../document/ui/StatusBadge.vue'`
  - `frontend/src/features/chunking/ui/ChunkPanel.vue:228` — `import { useAnalysisStore } from '../../analysis/store'` (deja present en 0.5.0, non flag a l'epoque)
  - `frontend/src/features/analysis/ui/AnalysisPanel.vue:61,63` — `useDocumentStore` + composants importes depuis `../../document/index`
- **Constat** : La feature `reasoning` (nouvelle en 0.6) importe directement des composants Vue (`GraphView`, `StructureViewer`) et des stores (`useAnalysisStore`, `useDocumentStore`) appartenant a `analysis` et `document`. Reciproquement, `analysis/ui/GraphView.vue` importe `reasoningOverlayStyles` depuis `reasoning/` : c'est un couplage **bidirectionnel** entre analysis et reasoning (un changement de l'un casse l'autre). Idem pour `chunks` qui importe `StatusBadge` de `document`. La regle 7.2.2 demande que la communication inter-features passe par `shared/` ou par props/events Vue ; ici la composition se fait par import physique de composants prives de la feature voisine.
- **Regle violee** : 7.2.2 — Les features ne s'importent pas mutuellement.
- **Remediation** :
  1. Promouvoir `GraphView.vue`, `StructureViewer.vue`, `StatusBadge.vue` dans `frontend/src/shared/ui/` (ce sont des composants de rendu reutilisables, pas de la logique metier d'une feature).
  2. Pour la dependance bidirectionnelle analysis<->reasoning : extraire `graphReasoningOverlay.ts` vers `shared/graph/` ou injecter les styles via props pour briser le cycle.
  3. Pour `useAnalysisStore` consomme par chunking/reasoning : exposer un composable `useAnalysisFor(docId)` dans `shared/composables/` qui encapsule la lecture, ou passer les analyses en props depuis la page.

### [MAJ] Couche `api` importe directement `infra` (api/graph.py -> infra.neo4j, infra.docling_graph)

- **Localisation** : `document-parser/api/graph.py:18-19`
  ```python
  from infra.docling_graph import build_graph_payload
  from infra.neo4j import fetch_graph
  ```
- **Constat** : Le routeur `/api/documents/{id}/graph` et `/reasoning-graph` court-circuitent la couche `services` et invoquent directement les adaptateurs `infra`. Cette dependance viole la regle documentee dans `document-parser/tests/test_architecture.py:99-112` (`TestApiLayerIsolation` : `api` ne doit pas importer de `infra`). Le test pytestarch correspondant n'est pas execute (module `pytestarch` absent du venv local — cf audit 10), donc la violation passe sans declenchement. Consequence : changer le backend graph (Neo4j -> autre) implique de toucher api/ ET de redefinir le contrat, alors que la regle 7.3.4 vise a localiser ce changement dans `services` + `infra`.
- **Regle violee** : 7.3.4 — Le changement de framework HTTP ne necessite de modifier que `api/` et `main.py` (corollaire : reciproquement, changer un adapter infra ne doit pas toucher api/).
- **Remediation** :
  1. Definir un port `GraphReader` dans `domain/ports.py` avec `async fetch(doc_id, max_pages) -> GraphPayload`.
  2. Creer `services/graph_service.py` qui injecte le port et fait l'orchestration (`fetch_graph` Neo4j OU `build_graph_payload` depuis SQLite selon l'endpoint).
  3. `api/graph.py` ne depend plus que de `services.graph_service` et de schemas Pydantic.
  4. Brancher `pytestarch` dans la CI (`pip install pytestarch` ou ajout aux deps de dev) pour que la regle existante echoue ouvertement a la prochaine violation.

### [MIN] `RechunkOptions` est defini dans `features/document/api.ts` mais consomme par la feature `chunks`

- **Localisation** :
  - `frontend/src/features/document/api.ts:36-44` — definition de l'interface
  - `frontend/src/features/chunks/ui/StrategyPopover.vue:128` — `import type { RechunkOptions } from '../../document/api'`
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:96` — meme import
- **Constat** : Le type est partage entre deux features (`document` et `chunks`) mais reside dans le fichier API d'une seule. La regle 7.2.3 stipule que les types partages doivent vivre dans `shared/types.ts`.
- **Regle violee** : 7.2.3 — Les types partages entre features sont dans `shared/types.ts`.
- **Remediation** : Deplacer `RechunkOptions` (et eventuellement `colorFor`, importe similairement par `chunks/ui/ChunksPanel.vue:98` depuis `features/document/elementColors`) vers `shared/types.ts` / `shared/`. Garder la fonction `rechunkDocument` dans `document/api.ts`.

### [MIN] Frontend API client toujours sans pattern de mock explicite

- **Localisation** : `frontend/src/features/{analysis,document,chunking,chunks,history,search,store,ingestion,reasoning}/api.ts` — toujours des fonctions libres au-dessus de `apiFetch`.
- **Constat** : Report identique du MIN 0.5.0 — aucune evolution structurelle. Les tests mockent via `vi.mock('./api')` (vu dans `__tests__/integration/history-navigation.test.ts:15-32`) mais il n'existe toujours pas d'interface `ApiClient` injectable rendant le pattern architecturalement explicite.
- **Regle violee** : 7.1.3 — Le frontend peut tourner avec un mock du backend.
- **Remediation** : Inchangee — soit documenter explicitement le pattern de mock (README de chaque feature), soit introduire une couche `ApiClient` injectable dans `shared/api/`.

### [MIN] `dict` non-type pour `config` des stores dans les schemas Pydantic

- **Localisation** : `document-parser/api/schemas.py:296,315,335`
  ```python
  class StoreResponse(_CamelModel):
      config: dict
  class StoreCreateRequest(_CamelModel):
      config: dict = Field(default_factory=dict)
  class StoreUpdateRequest(_CamelModel):
      config: dict | None = None
  ```
- **Constat** : Trois schemas Pydantic exposent `config: dict` (equivalent `dict[str, Any]`) au lieu d'un union de modeles types par `StoreKind`. Le champ est intrinsequement heterogene (config Neo4j vs OpenSearch vs futurs backends) ce qui explique le choix, mais la regle 7.4.2 demande "pas de `dict` ou `Any` dans les responses". Au minimum un `dict[str, Any]` ou un `RootModel` discrimine ameliorerait l'auto-documentation OpenAPI.
- **Regle violee** : 7.4.2 — Les schemas Pydantic documentent le contrat HTTP — pas de `dict` ou `Any` dans les responses.
- **Remediation** : Introduire `Neo4jStoreConfig`/`OpenSearchStoreConfig` Pydantic models discrimines par `kind` (Discriminated Union via `Field(discriminator='kind')`). Reservoir d'amelioration documentation/typage cote frontend.

---

## Points positifs

- **Remediation 0.5.0 propre** : `frontend/src/__tests__/integration/history-navigation.test.ts:1-6` documente explicitement la raison d'etre du repertoire `__tests__/integration/` — c'est exactement la solution proposee dans le rapport precedent (extraction hors d'une feature unique). Le test fonctionne en mockant l'API et en activant tous les stores reels.
- **Decouplage Frontend/Backend toujours solide** : Communication exclusivement REST via `shared/api/http.ts::apiFetch` (utilise par les 9 `features/*/api.ts`). Aucun import croise front<->back. Camel/snake mapping centralise par `_to_camel` dans `api/schemas.py:19-21`.
- **Hexagonal Architecture backend respecte (sauf graph.py)** :
  - Services importent uniquement `domain.*` (verifie pour `analysis_service.py`, `chunk_service.py`, `store_service.py`, `version_service.py`, `document_service.py`).
  - Imports `from persistence.*` dans services sont tous sous `TYPE_CHECKING:` (`store_service.py:22`, `chunk_service.py:33`, `version_service.py:26`, `store_backend_resolver.py:36`) — couplage **statique uniquement**, runtime injecte les concretes.
  - Aucun `from docling` / `import docling` dans `services/` ni `domain/` (grep verifie). Tous les usages sont confines a `infra/local_chunker.py`, `infra/local_converter.py`, `infra/serve_converter.py`, `infra/bbox.py`, `infra/docling_agent_reasoning.py`.
- **Repos retournent du domaine** : `persistence/{document,analysis,store}_repo.py` retournent des dataclasses `Document`, `AnalysisJob`, `Store` (verifie par grep ligne 36/20/46). Aucun `dict` / Row SQLite ne fuit.
- **Ports clairement typees** : `api/reasoning.py:24` n'importe que `from domain.ports import ReasoningParseError, ReasoningRunner` ; le runner est wire via `app.state.reasoning_runner`. Zero coupling api -> infra pour reasoning.
- **Tests d'architecture en place (mais non executes)** : `document-parser/tests/test_architecture.py` enforce via `pytestarch` les regles `api -> no infra`, `services -> no fastapi`, etc. Cadre prevu, juste non execute en CI locale (cf MAJ #2 remediation 4).
- **Schemas TS reasoning aligned 1:1 avec docling-agent** : `frontend/src/features/reasoning/types.ts:9-17` documente explicitement le choix snake_case pour eviter le re-mapping silencieux d'un drift upstream.
- **Backend testable sans frontend** : `tests/test_api_endpoints.py:1-14` utilise FastAPI `TestClient` ; 46 fichiers de tests dans `document-parser/tests/`.

---

## Verdict partiel : GO CONDITIONNEL

**Score 74/100** : Au-dessus du seuil NO-GO (60), en-dessous du seuil GO (80). Zero CRIT, deux MAJ non-bloquants individuellement (regle "bloquant si > 3 MAJ" non atteinte).

**Conditions de levee** :
1. **[MAJ 7.2.2 — UI couplage inter-features]** Au minimum, etablir un plan de remediation pour la 0.6.2 : promouvoir `GraphView`/`StructureViewer`/`StatusBadge` dans `shared/ui/`, briser le cycle analysis<->reasoning. Acceptable de shipper 0.6.1 avec la dette si trackee en issue.
2. **[MAJ 7.3.4 — api/graph.py -> infra]** Brancher `pytestarch` dans la CI immediate (`pip install pytestarch` + ajout au workflow tests) pour figer la regression ; refactor vers `services/graph_service.py` planifie en 0.6.2.
3. **[MIN]** Les 3 MIN (RechunkOptions partage, mock API, dict de config) peuvent etre adresses dans 0.6.2 sans bloquer la release.

Le code 0.6.1 reste solide sur l'essentiel : front<->back REST propre, backend hexagonal, repos retournant du domaine, ports typees. Les regressions de score viennent toutes de **la nouvelle feature `reasoning`** qui compose tres directement avec `analysis` et `document` — c'est un signal de design a corriger avant que d'autres features s'agglomerent autour du meme pattern.

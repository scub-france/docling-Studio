# Rapport d'audit : Decouplage

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 16 |
| Score | 80 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

Detail du calcul : somme des poids = 35 ; poids conformes = 28 (non conformes :
7.2.2 poids 3, 7.2.3 poids 2, 7.4.2 poids 2 = 7). `28 / 35 * 100 = 80`.

| Item | Poids | Statut |
|------|-------|--------|
| 7.1.1 REST-only front/back | 3 | Conforme |
| 7.1.2 Types TS = schemas Pydantic | 3 | Conforme |
| 7.1.3 Front mockable (api.ts par feature) | 2 | Conforme |
| 7.1.4 Back testable sans front (TestClient) | 2 | Conforme |
| 7.1.5 Pas de logique metier dupliquee | 2 | Conforme |
| 7.2.1 Feature = store + api + ui | 2 | Conforme |
| 7.2.2 Pas d'import croise entre features | 3 | **Non conforme [CRIT]** |
| 7.2.3 Types partages dans `shared/types.ts` | 2 | **Non conforme [MAJ]** |
| 7.2.4 Store n'accede pas au state d'un autre store | 2 | Conforme |
| 7.3.1 Repos retournent des objets du domaine | 2 | Conforme |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme |
| 7.3.3 Changement de DB confine a `persistence/` | 2 | Conforme |
| 7.3.4 Changement HTTP confine a `api/` + `main.py` | 2 | Conforme |
| 7.4.1 Ports = signatures claires + types domaine | 2 | Conforme |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | **Non conforme [MAJ]** |
| 7.4.3 Format de reponse coherent | 1 | Conforme |

---

## Ecarts constates

### [CRIT] Imports croises systemiques entre features frontend (item 7.2.2)

> **Resolu (Option B, barrel boundary)** sur `fix/release-0.7.0-audit-blockers` :
> les briques partagees (`MarkdownViewer`, `StatusBadge`, `bboxScaling`) ont ete
> extraites vers `shared/`, tous les acces inter-features passent desormais par
> les barrels publics `@/features/<name>` (ou `@/shared`), et l'invariant est
> impose par la regle ESLint `no-restricted-imports`.

- **Localisation** : `frontend/src/features/reasoning/store.ts:3` (+ ~19 autres, liste ci-dessous)
- **Constat** : L'item 7.2.2 exige que les features ne s'importent pas
  mutuellement, la communication devant passer par `shared/` ou par les
  props/events Vue. Le working tree contient au contraire un maillage dense
  d'imports directs inter-features, y compris **bidirectionnels**
  (`document` ↔ `analysis`, `document` ↔ `chunks`). La commande de verification
  de la fiche (`grep "from.*features/"`) ne les detecte pas parce que le code
  utilise des chemins relatifs (`../document/store`) plutot que l'alias
  `@/features/…` ; l'intention de l'item est neanmoins clairement violee.
  Imports croises releves (hors tests) :
  - `frontend/src/features/reasoning/store.ts:3` → `../document/store` (store)
  - `frontend/src/features/reasoning/kindColors.ts:10` → `../document/elementColors`
  - `frontend/src/features/document/store.ts:5` → `../analysis/api`
  - `frontend/src/features/document/store.ts:6` → `../chunks/api`
  - `frontend/src/features/document/ui/TableModal.vue:36` → `../../analysis/ui/MarkdownViewer.vue`
  - `frontend/src/features/document/ui/ElementProperties.vue:150` → `../../analysis/ui/MarkdownViewer.vue`
  - `frontend/src/features/analysis/ui/AnalysisPanel.vue:61` → `../../document/store` (store)
  - `frontend/src/features/analysis/ui/AnalysisPanel.vue:63` → `../../document/index`
  - `frontend/src/features/analysis/ui/StructureViewer.vue:64-65` → `../../document/api`, `../../document/bboxScaling`
  - `frontend/src/features/analysis/ui/BboxOverlay.vue:39` → `../../document/bboxScaling`
  - `frontend/src/features/chunking/ui/ChunkPanel.vue:228` → `../../analysis/store` (store)
  - `frontend/src/features/chunks/store.ts:4` → `../document/api`
  - `frontend/src/features/chunks/ui/ChunksPanel.vue:96,98` → `../../document/api`, `../../document/elementColors`
  - `frontend/src/features/chunks/ui/StrategyPopover.vue:128` → `../../document/api`
  - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:35` → `../../document/ui/StatusBadge.vue`
  - `frontend/src/features/settings/ui/SettingsPanel.vue:73-74` → `../../feature-flags/store`, `../../admin-config/ui/ReasoningConfigSection.vue`
  - `frontend/src/features/admin-config/store.ts:10` → `../feature-flags/store`
- **Regle violee** : 7.2.2 (poids 3) — « Les features ne s'importent pas
  mutuellement — la communication passe par `shared/` ou par les props/events Vue ».
- **Remediation** : Deux options non exclusives. (1) Extraire les briques
  effectivement partagees vers `shared/` : helpers de rendu (`document/bboxScaling`,
  `document/elementColors`), `MarkdownViewer.vue`, `StatusBadge.vue`, l'etat de
  focus citation, et le type `RechunkOptions`. (2) Si `document` est assume comme
  feature « coeur » du workspace, formaliser cette exception dans la fiche 07
  (barriere d'import explicite : seuls les barrels `index.ts` publics sont
  importables) et faire transiter TOUT acces via ces barrels — aujourd'hui la
  majorite des imports plonge dans les internes (`../document/store`,
  `../document/api`, `../document/ui/…`), pas dans `../document/index`.

### [MAJ] Type partage `RechunkOptions` loge dans une feature au lieu de `shared/` (item 7.2.3)

- **Localisation** : `frontend/src/features/document/api.ts:40`
- **Constat** : `RechunkOptions` est defini dans la feature `document` mais
  consomme par la feature `chunks` en trois points
  (`chunks/store.ts:4`, `chunks/ui/ChunksPanel.vue:96`,
  `chunks/ui/StrategyPopover.vue:128`). Un type partage entre features doit vivre
  dans `shared/types.ts`. A noter que les autres types de contrat croises
  (`DocChunk`, `ChunkDiff`, `PushSummary`, `DocTreeNode`, `DocumentVersion`) sont,
  eux, correctement centralises dans `shared/types.ts` — l'ecart est cible.
- **Regle violee** : 7.2.3 (poids 2) — « Les types partages entre features sont
  dans `shared/types.ts`, pas dans une feature specifique ».
- **Remediation** : Deplacer `interface RechunkOptions` vers
  `frontend/src/shared/types.ts` et reexporter/importer depuis la ; laisser
  `document/api.ts` importer le type depuis `shared/`.

### [MAJ] `dict` non type dans un schema de reponse (item 7.4.2)

- **Localisation** : `document-parser/api/schemas.py:310` (`StoreResponse.config: dict`)
- **Constat** : L'item 7.4.2 demande qu'aucune reponse n'utilise `dict` ou `Any`.
  Le schema de reponse `StoreResponse` expose `config: dict` (ligne 310) : le
  contrat du config store (polymorphe selon `kind` : neo4j vs opensearch) n'est
  pas type cote wire, alors que le frontend modelise pourtant ces formes
  (`Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue`). Corroborant : le modele de
  reponse `GraphNode` autorise des champs arbitraires via
  `model_config = {"extra": "allow"}` (`document-parser/api/graph.py:32`), ce qui
  ouvre egalement le contrat cote noeud. La commande de verification de la fiche
  (`grep "-> dict|-> Any|Dict[str, Any]"`) ne capte pas ces cas car ils sont au
  niveau *champ*, pas au niveau annotation de retour. Ecart reel mais a risque
  contenu (champs polymorphes assumes par conception).
- **Regle violee** : 7.4.2 (poids 2) — « pas de `dict` ou `Any` dans les responses ».
- **Remediation** : Typer `StoreResponse.config` via une union discriminee
  (`Neo4jConfig | OpenSearchConfig`) ou au minimum un modele `StoreConfig`
  dedie par `kind` ; pour `GraphNode`, remplacer `extra="allow"` par les
  attributs cytoscape effectivement emis (ou un sous-modele `data` type).

### [INFO] Champ de contrat orphelin `stores?` cote frontend

- **Localisation** : `frontend/src/shared/types.ts:39`
- **Constat** : L'interface `Document` declare `stores?: string[]` (« added in
  E1 #203 ») mais le schema backend `DocumentResponse`
  (`document-parser/api/schemas.py:91-107`) n'emet plus ce champ (seul
  `store_links` / `storeLinks` est peuple, cf. #283). Le champ est optionnel donc
  inoffensif a l'execution, mais c'est un residu de contrat mort qui brouille la
  correspondance TS ↔ Pydantic.
- **Regle concernee** : 7.1.2 (informatif — le reste du contrat correspond).
- **Remediation** : Supprimer `stores?: string[]` de l'interface `Document`.

### [INFO] Pre-validation de taille de fichier dupliquee cote front

- **Localisation** : `frontend/src/features/document/store.ts:75-79`
- **Constat** : Le front rejette un fichier trop volumineux avant l'upload. Ce
  n'est pas une reinvention de logique metier (7.1.5) puisque la limite provient
  de la config serveur (`appMaxFileSizeMb`, alimentee par `/health`) et sert
  uniquement de garde UX ; le backend reste l'autorite. Signale pour tracabilite.
- **Regle concernee** : 7.1.5 (informatif — considere conforme).
- **Remediation** : Aucune action requise.

---

## Points positifs

- **Contrat reasoning (#303) type de bout en bout.** Les DTOs
  `ReasoningTraceResponse` / `ReasoningStepResponse` / `ReasoningStepPayloadResponse`
  (`document-parser/api/schemas.py:538-616`) mirroient champ par champ les value
  objects du domaine (`domain/value_objects.py:225-273`) et correspondent
  exactement aux types TS (`frontend/src/features/reasoning/types.ts`) : aucun
  `dict`/`Any`, `StepId` promu en `RootModel` type dans l'OpenAPI, et l'enum
  `ReasoningStepKind` identique cote back (`value_objects.py:207-222`) et front.
- **Aliasing camelCase centralise.** `_CamelModel` (`schemas.py:39-46`) porte la
  conversion snake_case → camelCase pour tous les DTOs ; les requetes tolerent
  les deux casses via `AliasChoices`, ce qui evite toute derive de contrat.
- **Routeur reasoning a couplage zero.** `api/reasoning.py` n'importe ni
  docling-agent, ni mellea, ni docling-core ; il ne fait que mapper les DTOs et
  traduire les erreurs typees du service en codes HTTP.
- **Isolation infra/domaine solide (7.3.2).** Aucun `import docling` dans
  `services/` ; les types Docling sont encapsules derriere les ports
  (`DocumentTreeReader`, `GraphReader`) et le domaine expose `GraphPayload`
  plutot que des types de driver.
- **Ports nets, orientes domaine (7.4.1).** `domain/ports.py` definit des
  Protocols avec des types du domaine uniquement (imports sous `TYPE_CHECKING`),
  y compris `ReasoningRunner` et `LLMProvider`.
- **Repos retournent des objets du domaine (7.3.1).** Ex. `document_repo.py`
  mappe chaque Row via `_row_to_document` et renvoie `Document` / `list[Document]`.
- **Couches HTTP et DB confinees.** Aucun `fastapi` dans `services/` ou `domain/`
  (7.3.4) ; `aiosqlite` cantonne a `persistence/` — les seules mentions hors
  couche sont des commentaires (7.3.3).
- **Front mockable / back testable.** Chaque feature isole ses appels dans
  `api.ts` sur `shared/api/http` (7.1.3) ; la suite backend s'appuie sur
  `TestClient`/`httpx` (`tests/test_reasoning_api.py`, `test_api_stores.py`, …) (7.1.4).

---

## Verdict partiel : NO-GO

Le score de compliance est de **80/100**, mais la regle absolue du master
s'applique : l'ecart **[CRIT] 7.2.2** (imports croises systemiques entre features
frontend) est non resolu, ce qui impose un **NO-GO** quel que soit le score.

Conditions de levee :
1. Resoudre le [CRIT] 7.2.2 — extraire vers `shared/` les briques partagees
   (helpers de rendu, `MarkdownViewer`, `StatusBadge`, etat de focus, `RechunkOptions`)
   OU formaliser dans la fiche 07 une exception « feature coeur `document` » avec
   passage oblige par les barrels `index.ts` publics.
2. Traiter les deux [MAJ] (7.2.3 `RechunkOptions` vers `shared/` ; 7.4.2 typer
   `StoreResponse.config` et resserrer `GraphNode`) ou fournir un plan de
   remediation date.

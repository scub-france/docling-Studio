# Rapport d'audit : KISS (Keep It Simple, Stupid) — Re-audit

**Release** : 0.6.1 (re-audit)
**Branche** : `fix/0.6.1-audit-blockers` (HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 8 |
| Score | 87.5 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 3 |

Delta vs 0.6.1 : **stable** (87.5 → 87.5, 0/0/1/3 → 0/0/1/3). La
remediation portait sur l'audit hexagonal (#audit-01), DDD vocabulary
(#audit-02), perf I/O (#audit-12), sec env (#audit-08), docs (#audit-11)
et tests (#audit-09) — aucune cible KISS. Le re-audit verifie que les
nouvelles abstractions introduites par la remediation ne degradent pas
la simplicite du code.

**Verdict** : les 4 nouveaux ports + 3 adaptateurs introduits par
#audit-01 sont **minimalistes et justifies** (un consommateur reel par
port, adapter = thin shim sans logique). Le 6eme `_to_response` ajoute
dans `api/graph.py` n'aggrave **pas** le MIN existant : contrairement
aux 5 wrappers signales en 0.6.1 (copie 1:1 d'attributs), celui-ci
realise une vraie conversion (dict -> Pydantic model). MIN herite
inchange.

---

## Ecarts constates

### [MIN] Trivial `_to_response` wrappers (herite 0.6.1, non corrige)
- **Localisation** :
  - `document-parser/api/documents.py:29-40` (`_to_response`)
  - `document-parser/api/stores.py:46-61` (`_store_to_response`)
  - `document-parser/api/stores.py:64-75` (`_info_to_response`)
  - `document-parser/api/stores.py:78-85` (`_doc_entry_to_response`)
  - `document-parser/api/analyses.py:31-48` (`_to_response`)
  - `document-parser/api/document_versions.py:38` (`_to_response`)
- **Constat** : Inchange depuis le rapport 0.6.1 — les 5 routers
  conservent leurs wrappers triviaux. La remediation n'a pas cible KISS.
  Le 6eme wrapper ajoute dans `api/graph.py:64-73` est **legitime** : il
  convertit `payload.nodes` (list de `dict`) en `list[GraphNode]` via
  `GraphNode(**n)`, ce qui sort du pattern "copie 1:1" — il n'aggrave
  pas la dette.
- **Regle violee** : Item 4.3 — Pas de fonction wrapper qui ne fait
  qu'appeler une autre fonction sans valeur ajoutee
- **Remediation** : voir rapport 0.6.1 (Pydantic `model_validate` +
  `from_attributes=True`).

### [INFO] Redundant property accessors in DocumentService (herite, inchange)
- **Localisation** : `document-parser/services/document_service.py:55-61`
- **Constat** : Pas touche par la remediation. Toujours signale comme
  [INFO] dans le rapport 0.6.1.
- **Regle violee** : Item 4.3.

### [INFO] DocumentConfig / IngestionConfig dataclass overhead (herite, inchange + extension)
- **Localisation** :
  - `document-parser/services/document_service.py:28-34`
  - `document-parser/services/ingestion_service.py:33-39`
  - **Nouveau** : `document-parser/services/graph_service.py:67-71`
    (`GraphServiceConfig`, 1 seul champ `max_pages`)
- **Constat** : Le pattern "petite dataclass de config" introduit en
  0.6.0 s'etend a `GraphService` avec **1 seul champ** (`max_pages: int`).
  La justification donnee dans le module ("design §8.4 enforces") rend
  l'extension defensible, mais l'unique champ aurait pu rester un
  parametre kwarg de `__init__`. Reste en [INFO] : meme rationale
  d'uniformite que les deux autres configs, impact maintenabilite nul.
- **Regle violee** : Item 4.8 — Structures de donnees les plus simples
  possibles.
- **Remediation** : a regrouper avec les deux autres petites configs
  dans un futur cleanup KISS, ou accepter le pattern comme convention
  inter-services.

### [INFO] Analysis store polling with nested setInterval/setTimeout (herite, inchange)
- **Localisation** : `frontend/src/features/analysis/store.ts:69-101`
- **Constat** : Pas touche par la remediation (frontend hors scope des
  audit blockers cible CRIT/MAJOR backend). Inchange depuis 0.6.1.
- **Regle violee** : Item 4.6.

---

## Points positifs (delta remediation)

- **Les 4 nouveaux ports** (`DocumentTreeReader`, `GraphReader`,
  `GraphWriter`, `DocumentGraphProjector`) dans
  `document-parser/domain/ports.py:312-410` sont tous **justifies par un
  consommateur reel** et **minimalistes** :
  - `DocumentTreeReader` (3 methodes : `iter_items`, `is_inline_group`,
    `build_collapse_index`) — consomme par `ChunkService._build_tree_nodes`
    (`services/chunk_service.py:880`), qui auparavant importait directement
    `infra.docling_tree`. Surface minimale, pas de generic.
  - `GraphReader` (1 methode : `fetch`) — consomme par `GraphService`.
    Plus simple impossible.
  - `GraphWriter` (3 methodes : `write_document_tree`, `write_chunks`,
    `ping`) — chacune correspond a un cas d'usage distinct (post-analyse,
    post-ingestion, test-connection). Aucune methode optionnelle, pas
    d'abstraction speculative.
  - `DocumentGraphProjector` (1 methode : `project`) — consomme par
    `GraphService.project_reasoning_graph`.
  - Aucun port n'expose une API "au cas ou" — chaque methode a un site
    d'appel.

- **Les 3 adaptateurs** sont des **thin shims** (zero logique metier) :
  - `DoclingTreeReader` (`infra/docling_tree.py:288-301`) : 3 methodes,
    chacune une ligne `return free_function(...)`. La logique reste dans
    les fonctions libres du module (re-utilisees par les peers
    `infra/docling_graph.py` et `infra/neo4j/tree_writer.py`).
  - `DoclingGraphProjector` (`infra/docling_graph.py:188-204`) : 1
    methode, 1 appel `return build_graph_payload(...)`.
  - `Neo4jGraphReader` / `Neo4jGraphWriter`
    (`infra/neo4j/graph_adapter.py:27-75`) : meme pattern, 1 ligne par
    methode pour deleguer aux query/writer functions existantes. Seule
    exception : `ping()` ajoute un `try/except` pour normaliser en bool —
    justifie (l'underlying driver throw, mais le port specifie "should
    not throw").

- **`GraphService`** (`services/graph_service.py`) : 3 exceptions
  typees (`GraphStoreNotConfiguredError`, `GraphNotFoundError`,
  `GraphTooLargeError`) avec `http_status` integre. Pourrait paraitre
  sur-ingenierie, mais c'est en realite le **moyen le plus simple** de
  decoupler la logique service du mapping HTTP — alternative serait soit
  un dict `{type_err: status_code}` cote API, soit des `HTTPException`
  remontes depuis le service (anti-pattern hexagonal). Trois sous-classes
  pour trois cas d'erreur distincts = ratio justifie.

- **Le nouveau `_to_response` dans `api/graph.py:64-73`** :
  contrairement aux 5 wrappers triviaux signales en 0.6.1, celui-ci
  realise une **conversion reelle** (dict bruts -> `GraphNode(**n)` /
  `GraphEdge(**e)`). Le mapping ne pourrait pas etre genere par
  `model_validate(from_attributes=True)` puisque la source est
  `list[dict]`, pas un ORM-like. Aligne avec le seul wrapper legitime
  (`api/document_chunks.py:53`).

- **Aucun design pattern complexe** introduit par la remediation :
  Factory/Strategy/Observer/Builder/Singleton toujours absents
  (grep zero hit). Les nouveaux `Protocol` sont des **structural types**
  Python standards, pas des ABCs avec heritage.

- **Aucune meta-programmation** ajoutee (grep zero hit sur
  `__metaclass__`, `__init_subclass__`, `__class_getitem__`).

- **`graph_writer_factory`** dans `StoreBackendResolver.__init__`
  (`services/store_backend_resolver.py:84,96`) : un `Callable` injecte
  depuis `main.py` pour eviter que `services/` runtime-importe
  `infra/`. Approche minimaliste (pas de `Factory` class), correcte du
  point de vue hexagonal et KISS.

---

## Verdict partiel : GO

**Justification** : Score 87.5/100 maintenu, zero CRIT/MAJ. Le seul
[MIN] est herite et non aggrave par la remediation — le 6eme
`_to_response` ajoute fait reellement plus que copier des attributs. Les
4 ports + 3 adaptateurs introduits pour resoudre CRIT-01 (Hexagonal
Architecture) sont minimalistes : surface API reduite, thin shim
delegation, un consommateur reel par port. La remediation n'a pas
derive vers la sur-ingenierie. Le [INFO] sur `GraphServiceConfig`
(dataclass a 1 champ) est l'unique nouvelle observation, mais reste
acceptable au nom de l'uniformite avec `DocumentConfig` /
`IngestionConfig`. Pas de regression KISS.

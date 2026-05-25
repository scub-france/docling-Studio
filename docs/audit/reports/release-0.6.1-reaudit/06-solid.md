# Rapport d'audit : SOLID (re-audit)

**Release** : 0.6.1 (re-audit sur `fix/0.6.1-audit-blockers`)
**Date** : 2026-05-25
**Auditeur** : claude-code
**Commit HEAD** : `f9e5619`
**Baseline** : `docs/audit/reports/release-0.6.1/06-solid.md` (90/100, 0/0/1/1, GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 ponderes) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

**Delta vs 0.6.1** : +10 points (90 → 100). 1 MIN ferme, 1 INFO maintenu.

---

## Remediation des ecarts du rapport 0.6.1

| Ecart 0.6.1 | Statut re-audit | Preuve |
|-------------|------------------|--------|
| [MIN] DIP — imports infra inlines (`infra.docling_tree`, `infra.neo4j`) dans `chunk_service`, `ingestion_service`, `analysis_service` | **Resolu** | Quatre nouveaux ports ajoutes par #audit-01 dans `domain/ports.py:313-410` : `DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector`. Adaptateurs concrets : `DoclingTreeReader` (`infra/docling_tree.py:288`), `DoclingGraphProjector` (`infra/docling_graph.py:188`), `Neo4jGraphReader` + `Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py:27,37`). Les services consomment les ports : `chunk_service.py:156` (`tree_reader: DocumentTreeReader`), `ingestion_service.py:65` (`graph_writer: GraphWriter`), `analysis_service.py:91` (`graph_writer: GraphWriter`), nouveau `graph_service.py:77-88` (port-only). |
| [INFO] LSP — `@property` au port vs attribut de classe aux adaptateurs pour `supports_page_batching` | **Maintenu** | `domain/ports.py:67-74` declare encore `@property`, `infra/local_converter.py:286` et `infra/serve_converter.py:64` declarent encore l'attribut. Compatibilite Protocol structurelle au runtime confirmee par usage `analysis_service.py:415`. Non-bloquant — reporte au cycle suivant. |

**Verification globale** :

```
$ grep -rn "from infra\.\|import infra\." document-parser/services/ --include="*.py"
document-parser/services/store_backend_resolver.py:40:    from infra.neo4j.driver_pool import Neo4jDriverPool   # TYPE_CHECKING
document-parser/services/store_backend_resolver.py:41:    from infra.opensearch_pool import OpenSearchClientPool # TYPE_CHECKING
document-parser/services/store_backend_resolver.py:42:    from infra.opensearch_store import OpenSearchStore     # TYPE_CHECKING
```

Les 3 occurrences residuelles sont toutes sous `if TYPE_CHECKING:` (lignes 37-43) — aucun import runtime de `infra` dans `services/`. **MIN clos.**

```
$ grep -rn "isinstance" document-parser/services/ --include="*.py"
document-parser/services/store_service.py:135: isinstance(index_name, str)
document-parser/services/store_service.py:139: isinstance(index_name, str)
document-parser/services/chunk_service.py:218: isinstance(raw_chunks, list)
```

Trois `isinstance` portent sur des types primitifs (`str`, `list`) — aucune discrimination d'adaptateur. **6.3.3 conforme.**

```
$ grep -rn "LocalConverter\|ServeConverter\|LocalChunker\|OpenSearchStore" document-parser/services/ --include="*.py"
document-parser/services/store_backend_resolver.py:11:  # docstring
document-parser/services/store_backend_resolver.py:42: # TYPE_CHECKING import
document-parser/services/store_backend_resolver.py:61:    vector_store: OpenSearchStore | None = None  # type annotation only
```

Aucune instanciation. **6.5.3 conforme.**

---

## Ecarts constates

### [INFO] LSP — declaration `@property` vs attribut de classe pour `supports_page_batching`

- **Localisation** :
  - `document-parser/domain/ports.py:67-74` — declare `@property def supports_page_batching(self) -> bool`
  - `document-parser/infra/local_converter.py:286` — `supports_page_batching: bool = True` (attribut de classe)
  - `document-parser/infra/serve_converter.py:64` — `supports_page_batching: bool = False` (attribut de classe)
- **Constat** : Inchange depuis le rapport 0.6.1. Le `Protocol` declare un `@property`, les deux adaptateurs declarent un attribut simple. Le contrat fonctionne au runtime (acces `converter.supports_page_batching` retourne un `bool` dans les deux cas) et `analysis_service.py:415` consomme proprement la valeur. Toutefois la forme diverge — `mypy --strict` pourrait raler.
- **Regle violee** : Aucune (forme stricte de 6.3.1 — meme contrat de retour respecte).
- **Remediation** : Harmoniser sur l'attribut simple (supprimer `@property` dans le port) OU rendre les deux adaptateurs `@property`. Un test de typage en CI eviterait la regression. **Non-bloquant** pour le release 0.6.1.

---

## Points positifs

1. **DIP totale — services purement ports** : Apres #audit-01, plus aucun `from infra.*` runtime dans `document-parser/services/`. La couche service ne connait que :
   - 11 ports historiques (`DocumentConverter`, `DocumentChunker`, `DocumentRepository`, `StoreRepository`, `DocumentStoreLinkRepository`, `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `AnalysisRepository`, `EmbeddingService`, `VectorStore`)
   - 4 nouveaux ports (`DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector`)
   - Plus `LLMProvider`, `ReasoningRunner`.
2. **SRP — `GraphService` extrait proprement** : Nouveau `document-parser/services/graph_service.py` (132 LOC) qui orchestre les deux projections graph (`/api/documents/{id}/graph` et `/api/documents/{id}/reasoning-graph`). Avant #audit-01, l'orchestration etait dans `api/graph.py`. Service mono-responsabilite, 4 exceptions typees (`GraphStoreNotConfiguredError`, `GraphNotFoundError`, `GraphTooLargeError`, `GraphServiceError`) avec `http_status` integre — l'API se contente de mapper.
3. **SRP confirme — 8 services bien delimitee** : `AnalysisService` (553 LOC), `ChunkService` (1014), `DocumentService` (178), `GraphService` (132), `IngestionService` (297), `StoreBackendResolver` (152), `StoreService` (391), `VersionService` (227). Aucun god service ; le plus volumineux (`ChunkService`) reste coherent autour des chunks first-class.
4. **OCP — Composition root scellee** : `main.py` instancie les 8 adaptateurs concrets (`LocalConverter:64`, `ServeConverter:55`, `LocalChunker:76`, `OpenSearchStore:174`, `Neo4jGraphReader:265`, `Neo4jGraphWriter:264`, `DoclingTreeReader:321`, `DoclingGraphProjector:346`) et injecte les ports. Ajouter un `PostgresVectorStore` ou un `JanusGraphWriter` ne touche aucun service.
5. **DIP — Factory pattern pour adaptateurs runtime-dependants** : `StoreBackendResolver` recoit un `graph_writer_factory: Callable[[Any], GraphWriter]` (ligne 84) injecte avec `Neo4jGraphWriter` (`main.py:298`). Le resolver instancie l'adaptateur a la volee (`store_backend_resolver.py:150`) sans connaitre la classe concrete — pattern propre pour les adaptateurs per-store.
6. **LSP — Substitution transparente confirmee** : `LocalConverter` et `ServeConverter` interchangeables ; `Neo4jGraphWriter.ping()` swallows les exceptions et retourne `False` (`infra/neo4j/graph_adapter.py:66-75`) — meme contrat que `VectorStore.ping()` declare dans `domain/ports.py:273-276`.
7. **LSP — Adaptateurs port-only sans logique** : `DoclingTreeReader` et `DoclingGraphProjector` sont des shims stateless purs (15 LOC chacun) qui delegent aux fonctions libres existantes. Aucun risque de divergence comportementale entre le port et l'implementation.
8. **ISP — Ports finement segreges** : Le nouveau `GraphReader` ne porte que `fetch()`, le `GraphWriter` porte `write_document_tree` + `write_chunks` + `ping()` (3 methodes, toutes utilisees), le `DocumentGraphProjector` ne porte que `project()`. Aucun "god port" ; chaque port a 1-3 methodes maximum (sauf `VectorStore` et `ChunkRepository` qui ont 6-7 methodes, mais toutes utilisees).
9. **ISP — `GraphWriter` documente le contrat anti-no-op** : Le docstring (`domain/ports.py:362-368`) precise explicitement "Adapters that don't support both paths still must implement them (raise NotImplementedError rather than silently no-op so the caller can decide whether to fail)" — l'ISP est preserve par contrat explicite plutot que par defaut silencieux.
10. **DIP — Aucune fuite infra dans `api/`** : `grep -rn "from infra" document-parser/api/ --include="*.py"` retourne **0 match**. L'API depend exclusivement de services et schemas.
11. **S — Routes API et stores Pinia** : 8 routers (`analyses.py`, `document_chunks.py`, `document_versions.py`, `documents.py`, `graph.py`, `ingestion.py`, `reasoning.py`, `stores.py`) et 10 stores Pinia (31-234 LOC chacun) — un router = une ressource DDD, un store = une feature.

---

## Verdict partiel : GO

**Score** : 100 / 100 (delta +10 vs 0.6.1).
**Ecarts CRITICAL** : 0 — release autorisee.
**Ecarts MAJOR** : 0.
**Ecarts MINOR** : 0 (MIN du rapport 0.6.1 ferme par #audit-01).
**Ecarts INFO** : 1 (LSP `@property` vs attribut — reporte au prochain cycle, non-bloquant).

Le SOLID est maintenant exemplaire sur le perimetre `services/` / `domain/` / `infra/`. La remediation #audit-01 a non seulement ferme le MIN DIP mais aussi clarifie la frontiere hexagonale au point qu'aucun service ne reference plus `infra/` au runtime. Le seul ecart restant est cosmetique (typage Protocol vs attribut de classe pour `supports_page_batching`) et n'impacte ni le contrat fonctionnel ni le tests.

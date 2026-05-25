# Rapport d'audit : SOLID

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 14 / 15 (28 / 31 ponderes) |
| Score | 90 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 1 |

---

## Remediation des ecarts du rapport 0.5.0

| Ecart 0.5.0 | Statut 0.6.1 | Preuve |
|-------------|--------------|--------|
| [MAJ] `isinstance(self._converter, ServeConverter)` dans `analysis_service.py:356` | **Resolu** | `domain/ports.py:65-72` declare `supports_page_batching` au port `DocumentConverter`. `services/analysis_service.py:412` consomme `self._converter.supports_page_batching` — plus aucun `isinstance` sur adaptateur. `infra/local_converter.py:286` (`True`) et `infra/serve_converter.py:63` (`False`) implementent l'attribut. Aucun import infra residuel pour la discrimination. |
| [MIN] `self._vector_store._client.info()` dans `ingestion_service.py:197` | **Resolu** | `domain/ports.py` ajoute `VectorStore.ping()` (cf. usages `services/ingestion_service.py:287`). Plus aucun acces a `_client` prive depuis les services (`grep -rn "_vector_store\._\|_client\." services/` → 0 match). |

Les deux corrections promises dans le rapport precedent sont livrees et testees implicitement par le pipeline.

---

## Ecarts constates

### [MIN] DIP — imports infra inlines (fonctions utilitaires)

- **Localisation** :
  - `document-parser/services/chunk_service.py:891` — `from infra.docling_tree import build_collapse_index, iter_items`
  - `document-parser/services/chunk_service.py:974` — `from infra.docling_tree import is_inline_group`
  - `document-parser/services/ingestion_service.py:221` — `from infra.neo4j import write_chunks`
  - `document-parser/services/analysis_service.py:505` — `from infra.neo4j import write_document`
- **Constat** : Plusieurs services importent au runtime des fonctions concretes depuis `infra/` (parseur docling, writers Neo4j). Il ne s'agit pas d'instanciation d'adaptateur (donc pas une violation de 6.5.3) mais la couche service depend d'helpers infra sans contrat de port. La couche domain definit deja des ports `DocumentConverter`, `VectorStore`, `DocumentChunker` ; en revanche les fonctions d'extraction d'arbre Docling et les writers Neo4j n'ont pas de port explicite.
- **Regle violee** : 6.5.1 — "Les services dependent de protocoles abstraits (ports), pas d'implementations concretes" — partiellement viole, le reste du flux passe bien par des ports.
- **Remediation** : Introduire deux ports complementaires : `DocumentTreeReader` (operations `iter_items`, `is_inline_group`, `build_collapse_index` sur un `DoclingDocument` serialise) et `GraphChunkWriter` / `GraphDocumentWriter` (operations `write_chunks(doc_id, chunks_json)` et `write_document(doc)`). Injecter ces ports dans la composition root et supprimer les imports `from infra.*` des services.

### [INFO] LSP — declaration `@property` vs attribut de classe pour `supports_page_batching`

- **Localisation** :
  - `document-parser/domain/ports.py:65-72` — declare `@property def supports_page_batching(self) -> bool`
  - `document-parser/infra/local_converter.py:286` — `supports_page_batching: bool = True` (attribut de classe)
  - `document-parser/infra/serve_converter.py:63` — `supports_page_batching: bool = False` (attribut de classe)
- **Constat** : Le Protocol declare un `@property`, les deux adaptateurs declarent un attribut simple. Python Protocol structural fonctionne au runtime car l'acces `converter.supports_page_batching` retourne un `bool` dans les deux cas (`runtime_checkable` matche la presence du nom). Toutefois, le contrat de port et les implementations divergent en forme, ce qui peut surprendre un mainteneur et casser un `mypy` strict avec `--strict-equality`.
- **Regle violee** : Aucune (forme stricte de 6.3.1 — meme contrat de retour respecte).
- **Remediation** : Harmoniser sur l'attribut simple (supprimer `@property` dans le port et garder la valeur statique) OU rendre les deux adaptateurs `@property`. Un test de typage sur les ports en CI eviterait la regression.

---

## Points positifs

1. **S — Services parfaitement segregees** : `AnalysisService` (analyses), `DocumentService` (uploads/metadata), `ChunkService` (chunks canoniques), `IngestionService` (vector store + Neo4j), `StoreService` (CRUD stores), `VersionService` (versions documentaires), `StoreBackendResolver` (resolution Store→backend). Sept services, sept responsabilites — aucun god service.
2. **S — Chunks first-class** : Le nouveau `ChunkService` (1003 LOC) reste cohesif autour des chunks ; les helpers tree (`_build_tree_nodes`) servent `get_tree()` qui projette les chunks au format outline — responsabilite adjacente acceptable.
3. **S — Routes API per ressource** : `documents.py`, `analyses.py`, `document_chunks.py`, `document_versions.py`, `ingestion.py`, `stores.py`, `reasoning.py`, `graph.py` — un router = une ressource DDD.
4. **S — Stores Pinia atomiques** : 10 stores feature (`analysis`, `chunking`, `chunks`, `document`, `feature-flags`, `history`, `ingestion`, `reasoning`, `search`, `settings`) entre 31 et 234 LOC. Aucun store god.
5. **O — Extensibilite via composition root** : `_build_converter()`, `_build_chunker()`, `_build_repos()`, `_build_ingestion_service()`, `_build_document_service()`, `_build_reasoning_runner()` permettent l'ajout d'un nouvel adaptateur sans toucher les services.
6. **L — Substitution transparente LocalConverter/ServeConverter** : Apres remediation, le service n'a plus connaissance de la nature du converter ; le port expose `supports_page_batching` et le service interroge ce contrat (`analysis_service.py:412`).
7. **L — Aucune discrimination par `isinstance` sur adaptateur** : `grep` confirme 3 occurrences de `isinstance`, toutes sur des types de donnees primitives (str, list, dict) — jamais sur un port.
8. **I — Ports finement segreges** : `DocumentConverter`, `DocumentChunker`, `DocumentRepository`, `StoreRepository`, `DocumentStoreLinkRepository`, `ChunkRepository`, `ChunkEditRepository`, `ChunkPushRepository`, `AnalysisRepository`, `EmbeddingService`, `VectorStore` — 11 ports, chacun avec un focus etroit. Aucun port n'oblige une implementation a fournir une methode inutilisee.
9. **D — Composition root respectee** : Les adaptateurs concrets (`LocalConverter`, `ServeConverter`, `LocalChunker`, `OpenSearchStore`) ne sont instancies que dans `main.py` (lignes 52-76, 172-174). Les routes API recuperent les services via `Depends(_get_service)` qui lit `request.app.state.*`.
10. **D — `StoreBackendResolver` proprement injecte** : Bien qu'il manipule les pools infra (`Neo4jDriverPool`, `OpenSearchClientPool`), ils sont injectes via le constructeur (`store_backend_resolver.py:74-91`). Les imports `from infra.*` sont sous `TYPE_CHECKING` uniquement — aucune dependance runtime sur l'infra.
11. **TYPE_CHECKING discipline** : Imports infra dans les services restent au plus minimum (cf. liste des 6 imports infra runtime dans services). Les imports de typage sont systematiquement isoles sous `TYPE_CHECKING`.

---

## Verdict partiel : GO

**Score** : 90 / 100 (delta +5 vs 0.5.0).
**Ecarts CRITICAL** : 0 — release autorisee.
**Conditions** : aucune bloquante. Le MIN et l'INFO peuvent etre traites au cycle suivant.

Les deux ecarts du rapport 0.5.0 ([MAJ] LSP et [MIN] ISP) sont integralement remediates. Le seul ecart neuf est un MIN DIP autour des helpers `infra.docling_tree` et `infra.neo4j` qui meriteraient leur propre port (`DocumentTreeReader`, `GraphChunkWriter`).

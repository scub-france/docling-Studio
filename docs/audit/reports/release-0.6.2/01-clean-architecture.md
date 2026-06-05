# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.6.2
**Branche** : `release/0.6.2` (HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 1 |
| Écarts INFO | 1 |

Détail du calcul (somme des poids) :

- Total poids = 32
- Poids conformes = 31 (1.1.1=3, 1.1.2=3, 1.1.3=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.2.3=2, 1.2.4=2, 1.3.1=3, 1.3.3=2, 1.4.1=3, 1.4.2=2)
- Poids non conformes = 1 (1.3.2=1)
- Score = 31 / 32 × 100 = **96.875 → 97 / 100**

---

## Écarts constatés

### [MIN] Transformations camelCase contournées dans les schemas inline de `api/graph.py` et `api/reasoning.py` (régression non corrigée — inchangé vs 0.6.1)

- **Localisation** :
  - `document-parser/api/graph.py:30-53` — `GraphNode`, `GraphEdge`, `GraphResponse`
  - `document-parser/api/reasoning.py:30-48` — `ReasoningRunRequest`, `ReasoningIterationResponse`, `ReasoningResultResponse`
- **Constat** : Identique au re-audit 0.6.1. `document-parser/api/schemas.py:24-30` définit `_CamelModel` avec `alias_generator=_to_camel` (via `_to_camel` ligne 19) que toutes les autres réponses partagent (`HealthResponse`, `DocumentResponse`, `AnalysisResponse`, `ChunkResponse`, `IngestionResponse`, etc. — `api/schemas.py:34-362`). Les six schemas Pydantic locaux des routes graph et reasoning continuent d'hériter de `BaseModel` brut : `doc_id`, `node_count`, `edge_count`, `page_count`, `model_id`, `section_ref`, `section_text_length`, `can_answer` restent sérialisés en snake_case. Le périmètre `#audit-01` du fix 0.6.1 s'est volontairement concentré sur la régression CRIT/MAJ ; aucun commit 0.6.2 n'a remédié ce MIN.
- **Règle violée** : 1.3.2 — *Les transformations camelCase/snake_case restent dans `api/schemas.py`* (poids 1).
- **Remédiation** : Déplacer ces six classes dans `api/schemas.py` en les faisant hériter de `_CamelModel`. Coordonner avec les stores Pinia `features/graph` et `features/reasoning` (changement de contrat). Reportable au prochain cycle — sans impact bloquant.

---

### [INFO] Accès direct à `os.environ` dans deux modules `infra/` au lieu de passer par `infra/settings.py`

- **Localisation** :
  - `document-parser/infra/secrets/fernet_box.py:126` — `raw = os.environ.get("STORE_SECRET_KEY")` (lecture)
  - `document-parser/infra/docling_agent_reasoning.py:61` — `os.environ["OLLAMA_HOST"] = provider.host` (écriture forcée pour la lib docling-agent)
- **Constat** : Les deux variables sont déjà exposées via `infra/settings.py:41` (`store_secret_key`) et `infra/settings.py:51` (`ollama_host`) avec binding `os.environ.get(...)` aux lignes 164 et 168. Les deux modules consommateurs court-circuitent volontairement `settings` :
  - `fernet_box.py` lit l'env directement parce qu'il sert de factory paresseuse process-wide et doit pouvoir lever `StoreSecretKeyMissingError` même si `settings` n'est pas initialisé (le boot-time check `main.py:212-243` couvre déjà le chemin standard) ;
  - `docling_agent_reasoning.py` ne lit pas l'env — il l'écrit, parce que la lib `docling-agent` upstream interroge `os.environ["OLLAMA_HOST"]` à chaque appel et n'accepte pas d'override par paramètre (cf. mémoire utilisateur `project_docling_agent_pr.md`).
- **Règle visée** : 1.4.2 — *Les valeurs de config viennent de `infra/settings.py`, pas de constantes en dur* (poids 2). L'item reste **conforme** (le commentaire INFO ne pèse pas dans le score) parce qu'il s'agit de deux exceptions documentées, pas de constantes en dur. Aucune valeur magique n'apparait, et `settings` reste la source canonique pour le reste du code (`local_converter.py:105,228-240`, `serve_converter.py`, etc.).
- **Remédiation suggérée** : (1) router la lecture `STORE_SECRET_KEY` via `settings.store_secret_key` une fois que `settings` est garanti construit à l'import — chantier mineur cosmétique. (2) Pour `OLLAMA_HOST`, la résolution propre est l'API publique upstream (PR docling-agent traquée par `project_docling_agent_pr.md`) ; rien à faire côté Docling Studio tant qu'elle n'est pas mergée. Aucune action requise pour 0.6.2.

---

## Points positifs

- **Régressions infra-leak : zéro.** `grep -rn '^from infra\|^import infra' document-parser/services/ document-parser/api/` → aucun hit top-level. Les seuls hits `from infra` dans `services/` sont protégés par `if TYPE_CHECKING:` dans `services/store_backend_resolver.py:37-43` (`Neo4jDriverPool`, `OpenSearchClientPool`, `OpenSearchStore`, `SqliteStoreRepository`) — typage statique uniquement, zéro couplage runtime. Pareil dans `api/` : zéro hit. Le verrou architecture posé en 0.6.1 tient.
- **Ports stables et étendus.** `domain/ports.py` continue d'héberger l'intégralité des Protocols : `DocumentConverter` (l.52), `DocumentChunker` (l.77), repositories (`DocumentRepository` l.90, `StoreRepository` l.111, `DocumentStoreLinkRepository` l.125, `ChunkRepository` l.141, `ChunkEditRepository` l.164, `ChunkPushRepository` l.180, `AnalysisRepository` l.190), services I/O (`EmbeddingService` l.213, `VectorStore` l.225, `LLMProvider` l.280), et les 4 ports `#audit-01` issus de la remédiation 0.6.1 (`DocumentTreeReader` l.313, `GraphReader` l.344, `GraphWriter` l.356, `DocumentGraphProjector` l.394) + `ReasoningRunner` l.414. Tous marqués `@runtime_checkable` à partir de `EmbeddingService`.
- **Adapters concrets en place et nommés.** `LocalConverter` (`infra/local_converter.py:281`), `ServeConverter` (`infra/serve_converter.py:58`), `LocalChunker` (`infra/local_chunker.py:98`), `OpenSearchStore` (`infra/opensearch_store.py:62`), `EmbeddingClient` (`infra/embedding_client.py:19`), `Neo4jGraphReader`/`Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py:27,37`), `DoclingTreeReader` (`infra/docling_tree.py:288`), `DoclingGraphProjector` (`infra/docling_graph.py:188`), `DoclingAgentReasoningRunner` (`infra/docling_agent_reasoning.py:41`). Chacun documente son port cible en docstring.
- **`Protocol` interdit hors `domain/ports.py` : conforme.** Recherche manuelle `grep -rn 'class.*Protocol\b' document-parser/services/ document-parser/api/ document-parser/infra/ document-parser/persistence/` → aucun hit. Le test `tests/test_architecture.py::TestPortConvention::test_no_protocol_outside_domain_ports` (l.223-243) le verrouille automatiquement.
- **Domain purity intacte.** `grep -rn 'from fastapi|from aiosqlite|from pydantic|import fastapi|import aiosqlite|import pydantic' document-parser/domain/` → zéro hit. `domain/models.py` et `domain/value_objects.py` restent intégralement composés de `@dataclass` (`models.py:37-312`, `value_objects.py:79-155`) et `StrEnum` (`models.py:22`, `value_objects.py:18-65`).
- **Services sans FastAPI.** `grep -rn 'from fastapi|import fastapi' document-parser/services/` → zéro hit. Zéro usage de `Request`, `Depends`, `HTTPException`, `app.state` dans `services/`.
- **API sans persistence directe.** `grep -rn 'from persistence|import persistence' document-parser/api/` → zéro hit. Toutes les routes passent par les services injectés via `request.app.state` (ex. `api/graph.py:56-61` → `GraphService`, `api/reasoning.py:55-69` → `ReasoningRunner` + `AnalysisRepository`).
- **Services sans SQL.** Aucun import `sqlite3` / `aiosqlite` dans `services/`. Les seuls hits du pattern `INSERT|UPDATE|DELETE` dans `services/chunk_service.py:236,274,306,455,509` et `services/version_service.py:188` sont des références aux valeurs de l'enum `ChunkEditAction.INSERT/UPDATE/DELETE` (`domain/value_objects.py:65`), pas des requêtes SQL.
- **Wiring centralisé dans `main.py` (composition root unique).** `main.py:258-348` construit dans l'ordre : `Neo4jGraphWriter` + `Neo4jGraphReader` (l.262-265), `Neo4jDriverPool`, `OpenSearchClientPool`, `StoreBackendResolver` avec `graph_writer_factory=Neo4jGraphWriter` (l.288-298), `DoclingTreeReader` (l.318), `DoclingGraphProjector` + `GraphService` (l.336-345). `ReasoningRunner` + `LLMProvider` (`infra/docling_agent_reasoning.py`, `infra/llm/ollama_provider.py`) résolus en bas du module (l.427-429). Les services consommateurs (`AnalysisService`, `IngestionService`, `ChunkService`, `StoreBackendResolver`, `GraphService`) reçoivent les ports résolus par constructeur — DI complète, aucun `from infra...` lazy dans le code applicatif.
- **GraphService stable.** `services/graph_service.py:81-87` confirme l'injection par constructeur de `GraphReader | None` + `DocumentGraphProjector` + `AnalysisRepository`. Les endpoints HTTP (`api/graph.py:76-96`) restent à 96 lignes au total dont 21 d'imports/setup, le reste = mapping `GraphServiceError → HTTPException` et sérialisation `GraphPayload → GraphResponse`. La logique métier (résolution dernière analyse, cap MAX_PAGES, NotFound/Truncated) vit dans le service.
- **Configuration centralisée pour le runtime.** `infra/settings.py` reste l'unique source pour `MAX_PAGE_COUNT`, `MAX_FILE_SIZE`, `LOCK_TIMEOUT`, `DOCUMENT_TIMEOUT`, `OLLAMA_HOST`, `STORE_SECRET_KEY`, etc. Tous les modules `infra/*` opérationnels passent par `from infra.settings import settings` (ex. `local_converter.py:47,105,228,237-240`). Pas de constantes magiques ; les `default_limit: int = 1000` de `opensearch_store.py:81` et `opensearch_pool.py:50` sont des paramètres par défaut de constructeur (overridables), pas des constantes hard-codées.
- **Test architecture exécutable et durci en 0.6.2.** `tests/test_architecture.py:73-77` continue d'utiliser pytestarch (`get_evaluable_architecture`) + une liste d'exclusions enrichie (`_PYTESTARCH_EXCLUSIONS` l.41-67) qui couvre `.venv`, caches, `data/`, `uploads/` et fichiers binaires divers. Les classes de tests vérifient explicitement chaque sens d'isolation (`TestDomainLayerIsolation`, `TestServicesLayerIsolation`, `TestApiLayerIsolation`, `TestInfraLayerIsolation`, `TestPersistenceLayerIsolation` l.112-189), les externes interdits par couche (`_DOMAIN_FORBIDDEN_EXTERNALS = {"fastapi", "sqlalchemy", "httpx", "opensearchpy"}` l.196 ; `_SERVICES_FORBIDDEN_EXTERNALS = {"fastapi"}` l.197), et `TestPortConvention.test_no_protocol_outside_domain_ports` (l.226-243). Le test skippe proprement (`pytest.importorskip` l.25-28) en l'absence de pytestarch local. CI installe `requirements-test.txt` (`.github/workflows/ci.yml:40`) et exécute donc effectivement les règles à chaque PR. Régression CRIT 1.1.3 future bloquée par le pipeline.
- **`StoreBackendResolver` durci pour les nouveaux stores `#279`.** L'IngestionTargets (`services/store_backend_resolver.py:48-62`) reste `(vector_store: OpenSearchStore | None, graph_writer: GraphWriter | None)`. La nouvelle fonctionnalité « test connection » de 0.6.2 (`store_service.py:335-336`) passe par `targets.graph_writer.ping()` — donc par le port `GraphWriter.ping()` (`domain/ports.py:387-391`), pas par le driver Neo4j brut. Aucune fuite supplémentaire introduite par le périmètre `#279`.

---

## Delta vs re-audit 0.6.1

| Item | 0.6.1 re-audit | 0.6.2 | Cause |
|------|----------------|-------|-------|
| 1.1.1 → 1.4.1 | ✅ | ✅ | Aucune régression. Verrou test_architecture.py tient. |
| 1.3.2 (camelCase) | ❌ MIN | ❌ MIN | Inchangé — non remédié, reportable. |
| 1.4.2 (config infra) | ✅ | ✅ + INFO | Conforme, mais 2 accès `os.environ` hors `settings` observés (`fernet_box.py:126`, `docling_agent_reasoning.py:61`). Exceptions documentées, pas de hard-coded value. |
| Score | 97 / 100 | 97 / 100 | Stable. |
| CRIT / MAJ / MIN / INFO | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 1 | +1 INFO (observation, non bloquant). |
| Verdict | GO | GO | Aucune régression architecture. |

---

## Vérifications exécutées

```
# 1.1.1 — Domain ne doit importer aucune lib infra
grep -rn "from fastapi\|from aiosqlite\|from pydantic\|import fastapi\|import aiosqlite\|import pydantic" document-parser/domain/
→ (zéro hit)

# 1.2.1 — Services ne doivent pas importer FastAPI
grep -rn "from fastapi\|import fastapi" document-parser/services/
→ (zéro hit)

# 1.3.1 — API ne doit pas importer persistence
grep -rn "from persistence\|import persistence" document-parser/api/
→ (zéro hit)

# Sites d'import infra dans services/ et api/ — top-level
grep -rn '^from infra\|^import infra' document-parser/services/ document-parser/api/
→ (zéro hit)

# Sites d'import infra incluant lazy
grep -rn 'from infra\|import infra' document-parser/services/ document-parser/api/
→ 6 hits dont 3 sous `if TYPE_CHECKING:` dans store_backend_resolver.py:40-42 (typing only),
  2 dans des commentaires/docstrings, 1 dans analysis_service.py:4 (docstring).

# Protocol interdit hors domain/ports.py
grep -rn 'class.*Protocol\b' document-parser/services/ document-parser/api/ document-parser/infra/ document-parser/persistence/
→ (zéro hit)

# 1.4.2 — Constantes hard-codees dans infra/ (hors settings.py)
grep -rn "= ['\"]http\|= [0-9]\{4,\}" document-parser/infra/ --include="*.py" | grep -v settings.py
→ 2 hits = parametres default_limit=1000 dans opensearch_*.py — overridable, pas hard-coded.

# Test architecture
.venv/bin/pytest tests/test_architecture.py -v
→ skippe proprement si pytestarch absent ; CI installe requirements-test.txt et exécute les règles.
```

---

## Verdict partiel : GO

Score 97 / 100, zéro CRIT, zéro MAJ, un MIN inchangé (1.3.2 camelCase sur 6 schemas inline `api/graph.py` + `api/reasoning.py`), un INFO non-bloquant (deux accès directs `os.environ` dans `infra/secrets/fernet_box.py` et `infra/docling_agent_reasoning.py` — exceptions documentées). La remédiation `#audit-01` posée en 0.6.1 (4 ports + 4 adapters + GraphService + DI complète + test pytestarch en CI) tient sans régression sous le périmètre 0.6.2 (qui ajoute essentiellement des chantiers Docker/uv et la finalisation `#279` côté stores). Les modifications `services/store_backend_resolver.py` et `services/graph_service.py` n'introduisent aucune fuite infra. La règle absolue `master.md §3` (zero CRIT) reste satisfaite. Le MIN 1.3.2 peut être traité au prochain cycle sans bloquer la release 0.6.2.

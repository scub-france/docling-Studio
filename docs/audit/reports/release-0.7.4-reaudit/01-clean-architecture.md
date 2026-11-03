# Rapport de re-audit : Hexagonal Architecture (ports & adapters)

> **Re-audit de la 0.7.4 sur `claude/nifty-turing-fmn3wo` @ `a4d9679` : score 78 → 97, 3 MAJ → 0 MAJ.**

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Type** : re-audit après remédiation
**Référence** : rapport initial `docs/audit/reports/release-0.7.4/01-clean-architecture.md` (code `1de1929`, rapports commités en `e6047c2` ; `git diff 1de1929 e6047c2 -- document-parser frontend/src` est vide). 78/100, GO CONDITIONNEL, 0 CRIT, 3 MAJ, 1 MIN, 7 INFO.
**Remédiation examinée** : `git log e6047c2..a4d9679` (100 commits). Commits qui touchent cet audit :
- ports et dépôts : `39dcda5` (dépôts complétés, `DocumentVersionRepository`, pools, test AST des imports de `services/`, `tests/test_port_conformance.py`), `e68ee5a` (`PdfInspector`, PDF derrière des ports), `e331670` (`FileStorage`) ;
- routeurs : `cba03bf` (store-links dans `DocumentService`), `155294a` (dépendances de dépôts retirées de l'API), `99a9153` et `f6bced3` (taille des snapshots), `cb1e3b9` (gestionnaire d'erreurs unique, `DocumentNotFoundError` typée) ;
- règles métier : `a98be58` (split/merge), `9432eb8` (citations), `a2dbb0c` (lecture budgétée), `c488ae7` (hash de chunkset), `7ae77c2` et `2a6cf40` (arbre du document, niveau de titre), `ba70bb6` (sérialisation des chunks) ;
- découpage : `e95c75d`, `c925943` (`ChunkPushService`) ; documentation : `f1749a2` (règles réellement vérifiées par le test d'architecture).

Fiche : `docs/audit/audits/01-clean-architecture.md`. Cible : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).

**Méthode** : analyse statique (grep, lecture du code à `a4d9679`, `git diff`, `git show e6047c2:…`), plus trois scripts AST gardés dans le scratchpad et non versionnés :
- inventaire des imports par couche (`domain/`, `services/`) ;
- type déclaré de chaque paramètre de constructeur des 19 classes de `services/` ;
- croisement de chaque appel `self._x.m(...)` (et de ses arguments nommés) avec le `Protocol` déclaré pour `_x`.

Tests lancés : uniquement `pytest tests/test_architecture.py tests/test_port_conformance.py` → **69 passed**. Résultats du coordinateur sur `a4d9679`, cités sans les avoir rejoués : `ruff check` OK, `ruff format --check` OK, pytest **1673 passed, 19 skipped** ; aucun run CI ni Release Gate n'a encore tourné sur cette branche.

---

## Score de compliance

| Metrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 9 / 13 | **12 / 13** |
| Score | 78 / 100 | **97 / 100** |
| Ecarts CRITICAL | 0 | 0 |
| Ecarts MAJOR | 3 | **0** |
| Ecarts MINOR | 1 | 1 |
| Ecarts INFO | 7 | 10 |

**Calcul** :
- Poids conformes : 1.1.1 = 3, 1.1.2 = 3, 1.1.3 = 3, 1.1.4 = 2, 1.2.1 = 3, 1.2.2 = 3, 1.2.3 = 2, 1.2.4 = 2, 1.3.1 = 3, 1.3.3 = 2, 1.4.1 = 3, 1.4.2 = 2, soit **31**.
- Poids total : 32. Seul item non conforme : 1.3.2 (poids 1).
- `31 / 32 × 100 = 96,9`, soit **97**.

Lecture des items : **la même qu'au rapport 0.7.4**. Trois lectures plus strictes sont possibles ; elles ne sont pas retenues, et leur effet est chiffré dans la section « Lectures alternatives ».

### Taille du périmètre

Mesurée par `find <couche> -name '*.py' -not -path '*/__pycache__/*'`.

| Couche | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) |
|--------|-------------------|----------------------|
| `domain/` | 26 modules, 4 259 lignes | 30 modules, 5 092 lignes (+ `chunk_serialization`, `citation_match`, `doc_tree`, `read_budget`) |
| `domain/ports.py` | 21 `Protocol` | 26 `Protocol`, dont 12 `@runtime_checkable` (+ `DocumentVersionRepository`, `VectorStorePool`, `GraphDriverPool`, `PdfInspector`, `FileStorage`) |
| `services/` | 22 modules, 5 060 lignes | 26 modules, 4 798 lignes (+ `chunk_errors`, `chunk_push_service`, `document_tree_service`, `errors`) |
| `mcp_adapter/` | 10 modules, 1 485 lignes | 13 modules, 1 547 lignes |
| `infra/` | 30 modules, 3 971 lignes | 34 modules, 4 193 lignes (+ `file_storage`, `pdf_inspector`, `pdfium_lock`, `ssrf_guard`) |
| `api/` | 14 modules, 2 384 lignes | 15 modules, 2 429 lignes (+ `errors`) |
| `persistence/` | 10 modules, 1 473 lignes | 11 modules, 1 542 lignes (+ `timestamps`) |
| `bootstrap/` | 4 modules, 869 lignes | 4 modules, 905 lignes |

La logique a quitté `services/` (−262 lignes, malgré 4 modules de plus) pour `domain/` (+833 lignes).

### Détail item par item

| # | Item | Poids | Conforme | Statut vs 0.7.4 | Justification |
|---|------|-------|----------|-----------------|---------------|
| 1.1.1 | `domain/` n'importe ni FastAPI, ni aiosqlite, ni aucune lib infra | 3 | Oui | inchangé | Le grep de la fiche ne trouve rien. Inventaire AST des imports de `domain/` : `collections`, `dataclasses`, `datetime`, `enum`, `hashlib`, `re`, `typing`, `unicodedata`, `urllib`, `uuid`, et `domain.*`. Les 4 nouveaux modules n'ajoutent aucune dépendance. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | inchangé | Aucun `open(`, `os.`, `Path(`, `logging`, socket ni SQL dans `domain/`. Seuls effets de bord : `uuid4` et `datetime.now` (`domain/models.py:30,34`, `domain/chunk_editing.py:155`), qui ne sont pas des I/O. `domain/hashing.py` et `domain/chunk_serialization.py` se déclarent purs, et le sont. |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | inchangé | Le nouveau `build_doc_tree(doc_data, tree_reader: DocumentTreeReader)` (`domain/doc_tree.py:27`) suit le même schéma que `parse_index`. Lecture inchangée : l'item est jugé au niveau du domaine. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | inchangé | Aucune occurrence de `pydantic` ni de `BaseModel`. `DocumentVersionEntry` est une `@dataclass(frozen=True)` (`domain/ports.py:273-283`). |
| 1.2.1 | `services/` n'importe jamais `fastapi`/`Request`/`Response`/`Depends` | 3 | Oui | inchangé | Grep vide, ni `starlette` ni `Depends`. Le contrat d'erreur commun (`services/errors.py:44-56`) porte un code HTTP entier, sans rien importer de FastAPI ; la convention `http_status` existait déjà en 0.7.4 (`chunk_service`, `graph_service`, `store_service`). |
| 1.2.2 | Les services appellent les repos, jamais de SQL direct | 3 | Oui | inchangé | Aucun `SELECT`/`INSERT`/`execute(`/`aiosqlite`/`get_connection` dans `services/`. Le comptage des chunks d'un snapshot est fait en SQL dans le dépôt (`persistence/document_version_repo.py:70`), pas dans le service. |
| 1.2.3 | Les règles métier vivent dans `domain/` | 2 | **Oui** | **corrigé** | Les cinq points du [MAJ] n°1 sont dans le domaine et appelés par les services. Il reste des règles résiduelles que le rapport 0.7.4 n'avait pas retenues : voir [INFO] n°9. Détail plus bas. |
| 1.2.4 | Dépendances injectées, pas d'import direct de concrétions | 2 | **Oui** | **corrigé** | Les 19 classes de `services/` sont typées sur des ports, et aucun module de `services/` n'importe `infra`, `persistence`, `pdf2image` ni `pypdfium2`, même sous `TYPE_CHECKING`. Un résidu fonctionnel subsiste : la résolution du chemin stocké n'est faite que par `DocumentService` ([INFO] n°8). Détail plus bas. |
| 1.3.1 | Les routes n'importent pas `persistence/` | 3 | Oui | inchangé | Grep de la fiche sur `api/` vide. `api/deps.py` n'expose plus que des services (`StoreRepoDep`/`DocumentStoreLinkRepoDep` retirés, `155294a`). La sonde `/api/health` de `main.py` est inchangée ([INFO] n°7). |
| 1.3.2 | camelCase/snake_case confiné à `api/schemas.py` | 1 | **Non** | **partiellement corrigé** | `chunk_service` et `version_service` ne construisent plus de camelCase. Restent `analysis_service`, `chunk_push_service`, des lectures dans `ingestion_service`/`store_service`, et le format persisté, désormais centralisé dans `domain/chunk_serialization.py`. Voir [MIN]. |
| 1.3.3 | Les endpoints délèguent toute la logique aux services | 2 | **Oui** | **corrigé** | Les quatre points du [MAJ] n°3 sont dans les services, et les routeurs ne font plus que mapper DTO et erreurs typées. Détail plus bas. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | inchangé, périmètre élargi | Un adaptateur complet par port, vérifié par script pour les 26 ports (le script contrôle les noms des membres). Nouveaux couples : `LocalFileStorage`→`FileStorage`, `PdfiumInspector`→`PdfInspector`. Les pools, tolérés sans port jusqu'ici, en ont un : `OpenSearchClientPool`→`VectorStorePool`, `Neo4jDriverPool`→`GraphDriverPool`. Restent sans port, comme toléré depuis 0.7.0 : `FernetBox`, `RateLimiterMiddleware`, et la fonction `resolved_target_is_blocked`, injectée comme `Callable` (`bootstrap/builder.py:162-165`). |
| 1.4.2 | Config issue de `infra/settings.py`, pas de constantes en dur | 2 | Oui | inchangé | Le grep de la fiche ne remonte que les deux mêmes valeurs par défaut de paramètre (`infra/opensearch_store.py:81`, `infra/opensearch_pool.py:50`). Les nouveaux réglages (`MAX_IMPORT_TABLE_CELLS`…) passent par `settings`. Un plafond codé en dur apparaît dans `api/` ([INFO] n°4). |

---

## Statut des écarts du rapport 0.7.4

### [MAJ] n°1 (1.2.3) — Règles métier dans les services → **corrigé**

| Point 0.7.4 | Statut | Preuve dans le code actuel |
|-------------|--------|----------------------------|
| 1. Split/merge dans `ChunkService`, divergent du module orphelin `domain/chunk_editing.py` | **corrigé** | Le service appelle le domaine : `services/chunk_service.py:183` (`chunk_editing.split`), `:212` (`chunk_editing.merge`), `:134` (`sequence_after`) et `:245` (`chunkset_from_results`). Il ne reste qu'une implémentation : `domain/chunk_editing.py:66` et `:96`. Les divergences sont tranchées dans le domaine : le split garde bboxes et doc items et laisse le nombre de tokens inconnu (`:66-82`) ; le merge concatène bboxes et doc items et somme les tokens connus (`:96-130`). Le comportement a été figé par des tests avant le déplacement (`02fdaf0`). |
| 2. Appariement des citations dans `CitationService` | **corrigé** | `domain/citation_match.py:29` (`MIN_QUOTE_CHARS`), `:32` (`locate_quote`), `:63` (`_locate_across`), `:94` (`_trim_left`). Le service importe (`services/citation_service.py:23`) et appelle (`:79`, `:133`). |
| 3. Lecture budgétée et heuristique de titre | **corrigé** | `domain/read_budget.py:56` (`refs_to_read`), `:91` (`pick_within_budget`), `:135` (`read_span_ref`), appelés en `services/navigation_service.py:151-157`. Le titre du document est calculé par `domain/element_reader.py:240` (`document_title`), appelé en `services/source_service.py:133`. |
| 4. Hash de chunkset : règle du service contre module de domaine mort | **corrigé** | Une seule règle, dans le domaine : `domain/hashing.py:43` (`chunkset_hash`), appelée en `services/chunk_push_service.py:241`. Le domaine a repris la règle réellement écrite (id, texte, `updated_at`) et supprimé la variante « contenu seul » que rien n'appelait. Le docstring `:14-21` explique ce choix : les hashes déjà stockés restent comparables. Les deux options du rapport 0.7.4 sont respectées dans l'esprit (une seule règle, documentée). |
| 5. Niveau de titre dupliqué dans `_build_tree_nodes` | **corrigé** | L'arbre est sorti du service vers `domain/doc_tree.py`, qui utilise `parse_index.heading_level` (`domain/doc_tree.py:16`, `:71` ; règle en `domain/parse_index.py:231`). Le `ValueError` latent sur un niveau non numérique disparaît (`2a6cf40`). `DocumentTreeService` (`services/document_tree_service.py:38-60`) ne fait plus que charger l'analyse. |

### [MAJ] n°2 (1.2.4) — Services couplés à des concrétions → **corrigé** (avec un résidu en INFO)

| Point 0.7.4 | Statut | Preuve dans le code actuel |
|-------------|--------|----------------------------|
| 1. `pypdfium2`/`pdf2image` dans `document_service` et `analysis_service` | **corrigé** | Aucun import de ces paquets dans `services/` : l'inventaire AST ne trouve que la stdlib, `domain` et `services`. `DocumentService` reçoit `files: FileStorage`, `rasterizer: PageRasterizer` et `pdf: PdfInspector` (`services/document_service.py:86-111`). `AnalysisService` reçoit `pdf_inspector: PdfInspector` (`services/analysis_service.py:82`) et compte les pages dans un thread (`:452-464`). Le câblage est fait dans `bootstrap/factories.py:193-210`, `:220-235` et `:318-321`. Garde-fou : les deux paquets sont dans `_SERVICES_FORBIDDEN_EXTERNALS` (`tests/test_architecture.py:353-358`), et `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` est vide (`:365`). |
| 1 bis. Thread-safety pdfium (PLAUSIBLE en 0.7.4) | **corrigé** | Toutes les ouvertures pdfium prennent le verrou unique `infra/pdfium_lock.py:16-19` (celui de Docling quand il est installé) : `infra/pdf_inspector.py:26` et `:33`, `infra/page_text.py:24`. Le comptage de pages de l'analyse ne tourne plus sur la boucle d'événements (`services/analysis_service.py:461`). |
| 2. Système de fichiers dans `DocumentService` | **corrigé** | `DocumentService` ne contient plus aucun `os.`, `open(` ni `Path`. Écriture, résolution et suppression sont dans `infra/file_storage.py:21-59`. Le garde-fou « suppression uniquement sous `upload_dir` » a suivi la suppression : `realpath` des deux côtés (`:51-59`). |
| 3. `export_service` touche le disque | **corrigé** | `services/export_service.py:64` appelle `self._files.exists`. Le `Path` restant (`:8`) ne sert qu'à prendre le `.stem` d'un nom de fichier (`:126`), sans I/O. |
| 4. Dépôts typés sur `Sqlite*`, pas de `DocumentVersionRepository` | **corrigé** | Le port existe (`domain/ports.py:286-296`). `VersionService` est typé dessus (`services/version_service.py:66-71`) ; `StoreService` (`services/store_service.py:155`), `ChunkPushService` (`services/chunk_push_service.py:60-76`) et `DocumentService` sont typés sur des ports. Le script AST qui lit les constructeurs ne trouve aucune annotation `Sqlite*`, `OpenSearch*` ni `Neo4j*` dans les 19 classes. |
| 5. `store_backend_resolver` typé sur `infra.*`, appels hors port dans `chunk_service` | **corrigé** | `services/store_backend_resolver.py:37-45` n'importe que `domain.ports`. `IngestionTargets.vector_store: VectorStore` (`:63`). Les pools sont typés `GraphDriverPool`/`VectorStorePool` (`:84-85`, ports en `domain/ports.py:420` et `:436`), au lieu des fabriques `Callable` proposées en 0.7.4 : c'est une variante équivalente. `count_for_document` et `find_for_document` sont dans `ChunkPushRepository` (`domain/ports.py:260`, `:270`). Le croisement AST de tous les appels `self._x.m(...)` de `services/` avec le `Protocol` déclaré ne trouve **aucune méthode ni aucun argument nommé hors contrat**. |
| Garde-fou (remédiation 0.7.4 point 4) | **en place** | `TestServicesReachAdaptersThroughPortsOnly` (`tests/test_architecture.py:169-187`) refuse tout import de `api`, `bootstrap`, `infra` ou `persistence` dans `services/`, y compris sous `TYPE_CHECKING`. J'ai rejoué son scanner sur une copie de `services/` dans le scratchpad, en y ajoutant un import `persistence` sous `TYPE_CHECKING` : l'import est signalé. |
| Constat 3 : règle de résolution du chemin appliquée à moitié | **partiellement corrigé** | La règle est maintenant dans un port (`FileStorage.resolve`, `domain/ports.py:714-718` ; adaptateur `infra/file_storage.py:40-49`), mais seul `DocumentService` l'appelle (`services/document_service.py:262`, `:266`). Voir [INFO] n°8. Ce résidu ne relève pas du texte de l'item (aucune concrétion n'est importée) ; il n'est donc pas compté contre 1.2.4. Voir aussi « Lectures alternatives ». |

### [MAJ] n°3 (1.3.3) — Couche HTTP qui orchestre → **corrigé**

| Point 0.7.4 | Statut | Preuve dans le code actuel |
|-------------|--------|----------------------------|
| 1. Jointure store-links dans le routeur | **corrigé** | `DocumentService.find_with_store_links` (`services/document_service.py:168-195`) fait la jointure `slug_by_id`. Le routeur se contente d'appeler et de mapper (`api/documents.py:100-107`). `grep RepoDep api/` est vide. |
| 2. I/O disque, `to_thread` et plage de pages dans `/preview` et `/pages` | **corrigé** | `render_preview` (`services/document_service.py:219-241`) porte la règle « page hors plage » (`:230-231`) et le passage par un thread (`:235`) ; `page_sizes` est en `:243-259`. Les handlers `api/documents.py:149-177` et `:180-198` appellent l'instance injectée et traduisent les erreurs typées (`PageOutOfRangeError` → 400, `PageNotFoundError`/`FileNotFoundError` → 404, `OSError`/`DocumentFileError` → 422). Plus de lecture de fichier, plus d'appel statique sur la classe. |
| 3. 404/400 choisi d'après le libellé du message | **corrigé** | `AnalysisService.create`/`import_docling_document` lèvent `DocumentNotFoundError` (`services/analysis_service.py:137`, `:164` ; classe en `services/navigation_errors.py:24`, `http_status = 404`). Le gestionnaire unique `api/errors.py:24-30` est enregistré en `main.py:90`. `api/analyses.py:121-128` et `:139-145` n'inspectent plus aucun message. |
| 4. `json.loads` du snapshot dans `api/document_versions.py` | **corrigé** | Le routeur n'importe plus `json` (`api/document_versions.py:13-20`). Le nombre de chunks vient de `DocumentVersionEntry.chunk_count` (`domain/ports.py:273-283`). Il est compté en SQL pour la liste (`persistence/document_version_repo.py:70`) et par le service lors d'une restauration (`services/version_service.py:150-153`, `:178-180`). |

Ce qui reste de logique dans les routeurs relève du transport HTTP, comme en 0.7.4 : le plafond de corps de `/api/analyses` (`api/analyses.py:31-82`, voir [INFO] n°4), la lecture par blocs de l'upload (`api/documents.py:65-79`), et la correspondance `title` → `headings` (`api/document_chunks.py:94-95`, antérieure).

---

## Ecarts constates

### [MIN] Les conversions snake_case → camelCase fuient toujours hors de `api/schemas.py`

- **Statut vs 0.7.4** : **partiellement corrigé** ; l'item reste non conforme. `services/chunk_service.py` et `services/version_service.py` ne construisent plus aucune clé camelCase (grep vide). Les sites restants ont été déplacés ou centralisés, mais pas supprimés.
- **Localisation** :
  1. Services, construction :
     - `services/analysis_service.py:43-52` (`_chunk_to_dict`, écrit en `:225` et `:501`) ;
     - `services/chunk_push_service.py:95-109` (diff : `"chunkId"`, `"textDiff"`), `:157` (`"pushId"`), `:327-339` (historique : `"documentId"`, `"storeSlug"`, `"chunksetHash"`, `"pushedAt"`…). Ces sites viennent de `chunk_service.py:555-569`, `:686` et `:731-738` (`e95c75d`).
  2. Services, lecture inverse :
     - `services/ingestion_service.py:192-193` ;
     - **relevé en plus (antérieur)** : `services/store_service.py:135`, `:139` (`config.get("indexName")`), déjà présent à `e6047c2:services/store_service.py:134,138`.
  3. Domaine : `domain/chunk_serialization.py:32-99`. Le format persisté (journal, ingestion, snapshot, et le lecteur `chunk_from_dict`) y est maintenant centralisé.
  4. Adaptateur : `infra/neo4j/chunk_writer.py:75-80` (inchangé).
  5. Consommateur API : `api/analyses.py:234-240` et `:257-263` (`c.get("sourcePage")`, `c.get("tokenCount")`), `api/document_chunks.py:167` (`ChunkDiffResponse(**d)`), `:179-180` (`result["pushId"]`), `:199` (`ChunkPushEntryResponse(**entry)`).
- **Constat** :
  - Les services construisent toujours à la main des dicts au format du contrat front, que le routeur relit ou déverse dans un schéma Pydantic.
  - Le format persisté a quitté les services, mais pour `domain/` et non pour `persistence/` comme le proposait le rapport 0.7.4. Le module est pur et documente chaque forme (`domain/chunk_serialization.py:1-22`) ; le domaine connaît désormais l'orthographe des colonnes JSON.
  - Le « noyau camelCase » est écrit à deux endroits. `domain/chunk_serialization.py:85-93` le construit pour un `Chunk`. Son docstring (`:14-16`) rappelle que l'analyse écrit le même noyau dans `analysis_jobs.chunks_json` : c'est `services/analysis_service.py:43-52`, une seconde copie, pour un `ChunkResult`.
- **Regle violee** : item 1.3.2 — « Les transformations camelCase/snake_case restent dans `api/schemas.py` » (poids 1).
- **Remediation** :
  - Faire retourner des value objects par `ChunkPushService.diff_against_store`/`push_to_store`/`list_pushes` et par `AnalysisService.update_chunk_text`/`delete_chunk`, et laisser l'`alias_generator` de `api/schemas.py` produire le camelCase.
  - Brancher `_chunk_to_dict` d'`AnalysisService` sur `domain/chunk_serialization.py` (une variante `ChunkResult`), pour qu'il ne reste qu'un seul écrivain du noyau.
  - Déplacer éventuellement `chunk_serialization` vers `persistence/`, sans changer les octets écrits.
  - **Effort M, risque modéré** : formats persistés et relectures (`ingestion_service.py:192-193`, `infra/neo4j/chunk_writer.py:75-80`) à garder compatibles.

### [INFO] n°1 — Règles pytestarch : `services/` vérifié pour de bon, les autres couches toujours pas

- **Statut vs 0.7.4** : **partiellement corrigé**.
- **Ce qui est corrigé** :
  - Le scanner `ast` remplace la règle pytestarch pour `services/`, y compris sous `TYPE_CHECKING` (`tests/test_architecture.py:146-187`).
  - `docs/architecture.md:68-79` dit maintenant quelles directions sont vérifiées (« Checked : Yes/No ») et pourquoi les autres ne le sont pas (`f1749a2`).
- **Ce qui reste** :
  - Les règles pytestarch de `domain → couches` (`:114-127`), `api` (`:190-203`), `infra` (`:206-219`) et `persistence` (`:322-335`) ne voient toujours aucune arête. `TestPersistenceLayerIsolation` passe alors que `persistence/store_repo.py:24` importe `infra.secrets` : les 69 tests ciblés passent.
  - Le docstring du module annonce toujours ces règles comme « Rules enforced » (`tests/test_architecture.py:6-14`), sans les nuances de `docs/architecture.md`.
  - Hors barème : `tests/` est hors cible de la fiche.
- **Remediation** : étendre `_imports_of_layer` (`:146-166`) aux quatre couches restantes, puis traiter ce qui apparaîtra (au moins `persistence → infra`). Aligner le docstring `:6-14`. **Effort S.**

### [INFO] n°2 — Couplage entre adaptateurs : `persistence` importe `infra`

- **Statut vs 0.7.4** : **inchangé** (la ligne est passée de `:25` à `:24`).
- **Localisation** : `persistence/store_repo.py:24` (`from infra.secrets import get_fernet_box`).
- **Constat** :
  - Toujours le chiffrement des mots de passe de stores, dans une zone dépréciée en 0.8.0.
  - Nouveau : la documentation affirme le contraire. `docs/architecture.md:68`, « A layer never imports what this table lists », et `:77` (`persistence` : jamais `infra`).
- **Remediation** (facultatif) : un port `SecretBox`, ou une note dans `docs/architecture.md` jusqu'au retrait de l'ingestion.

### [INFO] n°3 — Le domaine lit directement le schéma JSON de Docling, contrairement à ce qu'annoncent ses docstrings

- **Statut vs 0.7.4** : **inchangé, périmètre étendu par la remédiation**.
- **Localisation** :
  - inchangé : `domain/parse_index.py:3-6` (docstring) contre `:120`, `:166`, `:204-208`, `:217`, `:225` ; `domain/element_reader.py:85-86`, `:156-157`, `:179`, `:195`, `:199` ;
  - **nouveau module, même contradiction** : `domain/doc_tree.py:3-5` (« Every docling-shaped access goes through the injected `DocumentTreeReader` port ») contre `:48` (`self_ref`), `:52` (`body`), `:62` et `:103-104` (`$ref`/`cref`), `:81` (`children`), `:137-157` (`label`, `text`, `name`).
- **Constat** :
  - Le code déplacé depuis `ChunkService._build_tree_nodes` a gardé ses accès directs au format Docling, et a pris le docstring de `parse_index`.
  - `build_doc_tree` renvoie des dicts au format de l'API (`{"ref", "type", "label", "children"}`, `:7-8`, `:118-130`), que le routeur passe tels quels à `DocTreeNodeResponse(**node)` (`api/document_chunks.py:156`), et non des value objects.
  - Les items 1.1.1 et 1.1.2 ne sont pas touchés : pas d'import, pas d'I/O.
- **Remediation** (facultatif) : corriger les trois docstrings pour décrire le compromis réel, ou faire normaliser les éléments par `DocumentTreeReader`. Faire retourner un VO `DocTreeNode`.

### [INFO] n°4 — Valeurs de configuration lues hors de `infra/settings.py`

- **Statut vs 0.7.4** : **inchangé, plus un site introduit par la remédiation**.
- **Localisation** :
  - inchangés : `infra/secrets/fernet_box.py:126` (`STORE_SECRET_KEY`, alors que `settings.store_secret_key` existe, `infra/settings.py:58`, `:269`) ; `persistence/database.py:26` (`DB_PATH`) et `:249` (`DEFAULT_EMBEDDER`) ; `mcp_stdio.py:44` ; `services/navigation_config.py:44-45` et `:52-54` ;
  - **nouveau (`c59b076`)** : `api/analyses.py:35`, `_MAX_BODY_BYTES = 200 * 1024 * 1024` codé en dur.
- **Constat** :
  - Le commentaire `api/analyses.py:31-34` aligne ce plafond sur la valeur par défaut de nginx. Or le plafond nginx est configurable : `NGINX_MAX_BODY_SIZE`, `nginx.conf.template:59`, `docker-compose.yml:211`, `.env.example:34`.
  - Un opérateur qui relève `NGINX_MAX_BODY_SIZE` pour importer un gros JSON Docling verra donc le backend refuser au-delà de 200 MB. `SECURITY.md:67` présente les deux plafonds comme égaux.
  - La lecture 0.7.4 de 1.4.2 (pas de constante d'URL ni d'hôte dans `infra/`) est conservée : l'item reste conforme.
- **Remediation** : un réglage `max_request_body_mb` dans `Settings`, lu par `api/analyses.py`, avec la même valeur par défaut que `NGINX_MAX_BODY_SIZE`. Pour le reste, celle du rapport 0.7.4. **Effort S.**

### [INFO] n°5 — Frontend : `shared/` dépend de `features/`, et des pages font des imports profonds (hors barème)

- **Statut vs 0.7.4** : **inchangé**. `frontend/eslint.config.js` n'a pas changé (`git diff --stat e6047c2..HEAD` vide), et `AppSidebar.vue` n'a changé que dans son CSS.
- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56` ; `frontend/src/pages/DocWorkspacePage.vue:62-63`, `:70-72`, `SearchPage.vue:54-56`, `AnalysisDetailPage.vue:39`, `:45`, `DocsNewPage.vue:86`. `IngestLaunchDialog.vue` a été supprimé (`2deb5f4`).
- **Remediation** : celle du rapport 0.7.4 (motifs ESLint `**/features/*/store|api|ui/*`, barrels).

### [INFO] n°6 — `DownloadDropdown.vue` fait un `fetch()` direct (hors barème)

- **Statut vs 0.7.4** : **inchangé**. `frontend/src/features/document/ui/DownloadDropdown.vue:133`.

### [INFO] n°7 — La sonde `/api/health` exécute du SQL depuis le point d'entrée

- **Statut vs 0.7.4** : **inchangé**. `main.py:41` (`from persistence.database import get_connection`), `main.py:131-137` (`SELECT 1`). Même classement INFO, par cohérence avec le statut de composition root de `main.py`.

### [INFO] n°8 — `FileStorage.resolve` n'est appliqué que par `DocumentService` (nouveau, résidu du [MAJ] n°2)

- **Statut** : **nouveau relevé**. C'est la suite du constat 3 du [MAJ] n°2 de 0.7.4 : la règle a maintenant un port, mais pas tous ses appelants.
- **Localisation** :
  - appliquée : `services/document_service.py:262` (aperçu) et `:266` (tailles de page) ;
  - chemin brut, sans `resolve` :
    - lancement d'analyse : `services/analysis_service.py:146` (`doc.storage_path` passé à `_run_analysis`, puis au convertisseur et à `_count_pdf_pages` `:452-464`). `AnalysisService` ne reçoit pas `FileStorage` (`:71-83`) ;
    - export PDF : `services/export_service.py:64-67`. `exists` est testé sur le chemin enregistré, puis ce même chemin est renvoyé au `FileResponse` ;
    - rasters MCP : `services/citation_image_service.py:74` ;
    - couche texte MCP : `services/source_service.py:142`, `:155`.
- **Constat** :
  - Le docstring du port (`domain/ports.py:697-701`) et l'adaptateur (`infra/file_storage.py:40-49`) décrivent le cas visé : un document enregistré sous `/app/uploads/…` dans Docker, puis relu depuis un worktree sur l'hôte.
  - Dans ce cas, l'aperçu et `/pages` fonctionnent ; l'analyse, l'export PDF (404 « PDF file not found ») et les cartes MCP échouent (PLAUSIBLE, limité au développement hors Docker, non reproduit).
  - Le rapport 0.7.4 proposait que `FileStorage` serve aussi `AnalysisService` et l'adaptateur raster (remédiation point 3) : c'est fait pour `ExportService` (`exists`), pas pour les autres.
- **Remediation** : injecter `FileStorage` dans `AnalysisService`, `ExportService`, `CitationImageService` et `SourceService`, et appeler `resolve` avant de passer le chemin à un port. Ou résoudre une fois au chargement (`ParseLoader.load` pour les deux services MCP). **Effort S, risque faible.**

### [INFO] n°9 — Règles résiduelles dans les services, non retenues par la lecture 0.7.4 (nouveau relevé, antérieures)

- **Statut** : **nouveau relevé**. Les trois points existaient à `e6047c2` et ont été vus par le rapport 0.7.4, qui ne les a pas comptés en 1.2.3.
- **Localisation** :
  - `services/chunk_push_service.py:80-110` (`diff_against_store`) : classe chaque chunk en `added`/`modified`/`unchanged`/`removed` en comparant `updated_at` à `pushed_at`. Ce code a été déplacé tel quel depuis `chunk_service.py:540`, que le rapport 0.7.4 citait pour son camelCase seulement. Zone d'ingestion, dépréciée.
  - `services/navigation_service.py:194-202` (`_excerpt_title`) : heuristique de titre d'un extrait (titre de section, « Page n », dernier titre de section, nom de fichier). C'est la même nature que `_title`, déplacé dans le domaine ; elle était déjà en `e6047c2:services/navigation_service.py:279`.
  - `services/analysis_service.py:234-275` (`update_chunk_text`, `delete_chunk`) : édition du blob `chunks_json` (texte, drapeaux `modified`/`deleted`). Dette déjà portée en INFO 5 de l'audit 06.
- **Constat** : ce sont des fonctions pures sur des objets du domaine, logées dans des services. Elles sont plus petites que les cinq points corrigés, et la première disparaîtra avec l'ingestion en 0.8.0.
- **Remediation** (facultatif) : `domain/chunk_editing.py` ou un module `domain/store_sync.py` pour le diff ; `domain/element_reader.py` pour `_excerpt_title` ; dépréciation de l'édition du blob. **Effort S chacun.**

### [INFO] n°10 — `AppState.analysis_repo` : un dépôt publié pour l'API que rien ne lit (nouveau relevé, antérieur)

- **Statut** : **nouveau relevé**. L'emplacement était déjà présent à `e6047c2:api/state.py:60`, sans lecteur dans `api/` non plus.
- **Localisation** : `api/state.py:56-57` (« Repositories reached directly by the API layer. »), alimenté en `bootstrap/builder.py:168`.
- **Constat** :
  - `grep "state.analysis_repo"` ne trouve aucun lecteur.
  - La remédiation a retiré `store_repo` et `document_store_link_repo` de cet état (`155294a`), mais pas celui-ci. Le commentaire invite un routeur à contourner les services ; l'item 1.3.1 n'est pas touché, puisqu'il s'agit d'un port.
- **Remediation** : supprimer l'emplacement et son alimentation. **Effort XS, risque nul.**

---

## Lectures alternatives (non retenues)

Le score de 97 applique la lecture du rapport 0.7.4. Effet des lectures plus strictes, sur 32 :

| Lecture | Item | Score |
|---------|------|-------|
| Retenue (même lecture qu'en 0.7.4) | 1.3.2 seul non conforme | **97** |
| Les règles résiduelles de l'[INFO] n°9 comptent en 1.2.3 | + 1.2.3 (2) | 91 |
| Le critère de fermeture écrit en 0.7.4 pour le [MAJ] n°2 (« points 1 à 4 au minimum », dont `FileStorage` dans `AnalysisService`) est appliqué à la lettre ([INFO] n°8) | + 1.2.4 (2) | 91 |
| Les deux ci-dessus | + 1.2.3, 1.2.4 | 84 |
| Lecture stricte de 1.4.2, déjà évoquée en 0.7.4 (`fernet_box.py:126`, et désormais `api/analyses.py:35`) | + 1.4.2 (2) | 91 |

Toutes ces lectures laissent le verdict à GO (≥ 80) et ne créent aucun écart CRITICAL.

---

## Delta vs 0.7.4

**Score : 78 → 97 (+19).** Items conformes 9/13 → 12/13 : 1.2.3, 1.2.4 et 1.3.3 passent conformes ; 1.3.2 reste non conforme.

| Écart 0.7.4 | Statut au re-audit | Preuve principale |
|-------------|--------------------|-------------------|
| [MAJ] n°1 Règles métier dans les services (1.2.3) | **Corrigé** | `domain/chunk_editing.py:66,96` ; `domain/citation_match.py:32` ; `domain/read_budget.py:56,91,135` ; `domain/hashing.py:43` ; `domain/doc_tree.py:71` |
| [MAJ] n°2 Concrétions dans les services (1.2.4) | **Corrigé** (résidu `resolve` → [INFO] n°8) | Constructeurs typés sur des ports ; `tests/test_architecture.py:169-187`, `:353-365` ; `infra/pdfium_lock.py` |
| [MAJ] n°3 Orchestration dans `api/documents.py` (1.3.3) | **Corrigé** | `services/document_service.py:168-259` ; `api/errors.py:24-30` ; `domain/ports.py:273-283` |
| [MIN] camelCase hors `api/schemas.py` (1.3.2) | **Partiellement corrigé** | Retiré de `chunk_service`/`version_service` ; reste `analysis_service.py:43-52`, `chunk_push_service.py:95-109,157,327-339`, `domain/chunk_serialization.py` |
| [INFO] n°1 pytestarch inopérant | Partiellement corrigé | `services/` vérifié par AST ; `domain`/`api`/`infra`/`persistence` toujours non |
| [INFO] n°2 `persistence` → `infra.secrets` | Inchangé | `persistence/store_repo.py:24` ; contredit `docs/architecture.md:77` |
| [INFO] n°3 Schéma Docling lu dans le domaine | Inchangé, étendu | `domain/doc_tree.py:3-5` |
| [INFO] n°4 Config hors `settings` | Inchangé, + 1 site | `api/analyses.py:35` (`c59b076`) |
| [INFO] n°5 Frontend `shared`/`pages` | Inchangé | |
| [INFO] n°6 `DownloadDropdown.vue` `fetch()` | Inchangé | `:133` |
| [INFO] n°7 `/api/health` SQL dans `main.py` | Inchangé | `main.py:131-137` |
| — | **Nouveau [INFO] n°8** | `resolve` appliqué par un seul service |
| — | **Nouveau [INFO] n°9** | Règles résiduelles antérieures |
| — | **Nouveau [INFO] n°10** | `AppState.analysis_repo` sans lecteur (antérieur) |

**Régressions introduites par la remédiation** : aucune sur un item du barème. Trois effets de bord mineurs, tous classés INFO :
- un plafond de corps codé en dur dans `api/analyses.py:35` ([INFO] n°4) ;
- un docstring inexact recopié dans `domain/doc_tree.py:3-5` ([INFO] n°3) ;
- le format persisté des chunks placé dans `domain/` plutôt que `persistence/` ([MIN]).

---

## Ce qui reste pour 100

| Action | Item | Gain | Effort | Risque |
|--------|------|------|--------|--------|
| VO pour diff/push/historique de push et pour l'édition legacy des chunks ; un seul écrivain du noyau camelCase (`chunk_serialization`) | 1.3.2 (1) | +3,1 → **100** | M | modéré : formats persistés à garder compatibles |

Hors barème mais recommandé, par rendement :
1. [INFO] n°8 : `FileStorage.resolve` dans les quatre autres consommateurs du chemin stocké (S).
2. [INFO] n°1 : étendre le scanner AST aux couches `domain`/`api`/`infra`/`persistence` (S). C'est ce qui fera tenir ces frontières, et le premier écart qu'il remontera est déjà connu ([INFO] n°2).
3. [INFO] n°10 et docstrings de l'[INFO] n°3 (XS).
4. [INFO] n°4 : `max_request_body_mb` dans `Settings` (S).

---

## Points positifs

- **Les trois MAJ, reportés depuis 0.7.0, sont fermés.** Chaque point a une preuve dans le code, pas seulement dans les messages de commit.
- **Le contrat déclaré est désormais le contrat réel.** Les ports couvrent tout ce que les services appellent : le croisement AST ne trouve aucun écart. `tests/test_port_conformance.py:29-83` vérifie, pour 12 couples port/adaptateur, les noms, la nature et la présence de valeur par défaut de chaque paramètre.
- **Un garde-fou qui mord** sur `services/`, `TYPE_CHECKING` compris (`tests/test_architecture.py:169-187`), et une documentation qui dit ce qui est vérifié et ce qui ne l'est pas (`docs/architecture.md:68-79`).
- **PDF et disque entièrement derrière des ports**, avec un verrou pdfium unique pour tout le processus (`infra/pdfium_lock.py`). La question de thread-safety PLAUSIBLE de 0.7.4 est réglée à la source.
- **Routeurs minces** : un gestionnaire d'erreurs unique (`api/errors.py`), plus de `try/except` par famille d'erreurs, plus de discrimination par libellé.
- **Domaine toujours pur** malgré +833 lignes : stdlib et `domain.*` seulement.
- **`ChunkService` découpé** en édition (311 lignes), push (`ChunkPushService`, 339) et arbre (`DocumentTreeService`, 60), chacun typé sur des ports.

---

## Verdict partiel : GO

- Score **97/100** (≥ 80), **0 CRITICAL**, **0 MAJOR**, 1 MINOR, 10 INFO.
- Les trois écarts MAJOR du rapport 0.7.4 sont corrigés et vérifiés dans le code. Le seul écart restant est le MINOR camelCase (1.3.2), non bloquant.
- Les lectures plus strictes, détaillées ci-dessus, donnent entre 84 et 91. Elles laissent toutes le verdict à GO.

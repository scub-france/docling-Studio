# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `release/0.7.4` @ `1de1929` (audité sur `claude/nifty-turing-fmn3wo`, identique)

Fiche : `docs/audit/audits/01-clean-architecture.md`. Cible : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Baseline : `docs/audit/reports/release-0.7.3/01-clean-architecture.md` (78/100, sur `02adc68`). L'audit 01 n'a pas été ré-audité après la remédiation 0.7.3 (`release-0.7.3-reaudit/summary.md` : « 78 (inchangé) »).

**Méthode** : analyse statique uniquement (grep, lecture de code, `git diff`, `git show <tag>:<fichier>`). Je n'ai lancé ni l'application ni les suites de tests. Le clone est superficiel (`git rev-parse --is-shallow-repository` = `true`, frontière au 2026-08-08). Pour dater un écart, j'ai donc lu le fichier au tag `v0.7.0` (`git show v0.7.0:…`) plutôt que de m'appuyer sur `git blame`.

**Ce qui a changé dans le périmètre depuis l'audit 0.7.3** :
- `git diff v0.7.3..HEAD -- document-parser/` est **vide**. Le backend de la 0.7.4 est identique, octet pour octet, au tag `v0.7.3`. Les deux seuls commits depuis le tag (`0465e70`, `1de1929`) touchent `README.md` et des GIF.
- `git diff 02adc68..HEAD -- document-parser/` (le commit du 1er audit 0.7.3, comparé au code actuel) donne 7 fichiers. Les seuls changements de code applicatif sont :
  - `services/analysis_service.py:177-180` : l'import Docling passe par `asyncio.to_thread` ;
  - le commentaire `infra/settings.py:89-96`.

  Le reste ne touche pas l'architecture : `Dockerfile` (`uv`), `pyproject.toml`/`uv.lock` (`mcp>=2.2.0`), `mcp_adapter/citation_app.html` (`lang="fr"`) et un test.

Conséquence : tous les écarts 0.7.3 sont re-vérifiés ci-dessous sur le code actuel. Aucun n'est corrigé ni aggravé. En relisant plus large que la fiche, j'ai trouvé des localisations **antérieures** qui n'avaient pas été relevées. Je les rattache aux écarts existants (statut « inchangé, périmètre précisé ») ou je les ajoute en INFO. Aucune ne vient de code introduit en 0.7.4.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 7 |

Taille du périmètre à `1de1929` (mesurée par `find … -name '*.py' | wc -l`) :

| Couche | Taille | Évolution depuis 0.7.3 (`02adc68`) |
|--------|--------|------------------------------------|
| `domain/` | 26 modules, 4 259 lignes | aucune |
| `domain/ports.py` | 21 `Protocol` | aucune |
| `services/` | 22 modules, 5 060 lignes | +3 lignes (`analysis_service.py`, `to_thread`) |
| `mcp_adapter/` | 10 modules `.py`, 1 485 lignes | aucune (hors `lang` du template HTML) |
| `infra/` | 30 modules, 3 971 lignes | commentaire `settings.py` uniquement |
| `api/` | 14 modules, 2 384 lignes | aucune |
| `persistence/` | 10 modules, 1 473 lignes | aucune |
| `bootstrap/` | 4 modules, 869 lignes | aucune |

### Détail item par item

| # | Item | Poids | Conforme | Statut vs 0.7.3 | Justification |
|---|------|-------|----------|-----------------|---------------|
| 1.1.1 | `domain/` n'importe ni FastAPI, ni aiosqlite, ni aucune lib infra | 3 | Oui | inchangé | Le grep de la fiche ne trouve rien. Inventaire des imports de `domain/` : stdlib (`typing`, `dataclasses`, `datetime`, `re`, `enum`, `uuid`, `hashlib`, `json`, `unicodedata`, `urllib.parse`) et `domain.*`, rien d'autre. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | inchangé | Aucun `open(`, `os.`, `Path(`, `pathlib`, socket, HTTP, `subprocess` ni SQL dans `domain/`. `urllib.parse.urlparse` (`domain/app_config.py:15`, `domain/mcp_config.py:22`) est du parsing pur. Seuls effets de bord : `datetime.now`/`uuid4` (`domain/models.py:30,34`, `domain/chunk_editing.py:32,36`), qui ne sont pas des I/O. |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | inchangé | Le domaine reçoit ses besoins externes par des ports, par exemple `build_index(doc_data, tree_reader: DocumentTreeReader)` (`domain/parse_index.py:80`). Comme en 0.7.0 et 0.7.3, l'item est lu au niveau du domaine. Les contournements de port côté services relèvent de 1.2.4. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | inchangé | Aucune occurrence de `pydantic` ni de `BaseModel` dans `domain/`. |
| 1.2.1 | `services/` n'importe jamais `fastapi`/`Request`/`Response`/`Depends` | 3 | Oui | inchangé | Le grep de la fiche ne trouve rien, ni `starlette`, ni `Depends`. |
| 1.2.2 | Les services appellent les repos, jamais de SQL direct | 3 | Oui | inchangé | Aucun `SELECT`/`INSERT`/`DELETE FROM`/`execute(`/`aiosqlite` dans `services/`. Les seules occurrences du grep sont des commentaires (`chunk_service.py:455,597`, `version_service.py:158`) et la méthode de dépôt `get_connection_password` (`store_backend_resolver.py:128,143`). |
| 1.2.3 | Les règles métier vivent dans `domain/` | 2 | **Non** | inchangé, périmètre précisé | Split/merge, appariement des citations et lecture budgétée sont toujours dans les services. Deux doublons domaine/service, antérieurs et non relevés jusqu'ici, s'y ajoutent : le hash de chunkset et le niveau de titre. Voir [MAJ] n°1. |
| 1.2.4 | Dépendances injectées, pas d'import direct de concrétions | 2 | **Non** | inchangé, périmètre précisé | `pypdfium2`/`pdf2image`/système de fichiers sont toujours dans `document_service`/`analysis_service`, et les services restent typés sur `Sqlite*Repository`. Relevés en plus, tous antérieurs : `store_backend_resolver` typé sur des classes `infra.*`, appels hors port dans `chunk_service`, `export_service` qui touche le disque. Voir [MAJ] n°2. |
| 1.3.1 | Les routes n'importent pas `persistence/` | 3 | Oui | inchangé | Le grep de la fiche sur `api/` ne trouve rien, `api/` ne voit que des ports (`api/documents.py:18`, `api/deps.py:90-105`). La sonde `/api/health` définie dans `main.py` (composition root) exécute du SQL, mais elle est hors de `api/` : voir [INFO] n°7. |
| 1.3.2 | camelCase/snake_case confiné à `api/schemas.py` | 1 | **Non** | inchangé, périmètre précisé | Des dicts camelCase sont toujours construits dans les services, et sur plus de sites que la liste 0.7.3. Voir [MIN]. |
| 1.3.3 | Les endpoints délèguent toute la logique aux services | 2 | **Non** | inchangé, périmètre précisé | La jointure store-links, les I/O disque de `/preview` et `/pages` et la discrimination d'erreur par libellé sont toujours dans les routeurs. Relevé en plus : décodage du snapshot JSON dans `api/document_versions.py:33`. Voir [MAJ] n°3. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | inchangé | 30 modules, mêmes classes qu'en 0.7.3. Correspondances : `LocalConverter`/`ServeConverter`→`DocumentConverter`, `LocalChunker`→`DocumentChunker`, `DoclingDocumentImporter`→port homonyme, `DoclingTreeReader`→`DocumentTreeReader`, `EmbeddingClient`→`EmbeddingService`, `OpenSearchStore`→`VectorStore`, `Neo4jGraphReader`/`Writer`→`GraphReader`/`GraphWriter`, `OllamaProbe`→`LLMHostProbe`, `OllamaProvider`→`LLMProvider`, `DoclingAgentReasoningRunner`→`ReasoningRunner`, `PdfPageRasterizer`→`PageRasterizer`, `PdfPageTextReader`→`PageTextReader`. Les pools (`Neo4jDriverPool`, `OpenSearchClientPool`), `FernetBox` et `RateLimiterMiddleware` restent sans port, comme toléré depuis 0.7.0. |
| 1.4.2 | Config issue de `infra/settings.py`, pas de constantes en dur | 2 | Oui | inchangé | Le grep de la fiche ne remonte que deux valeurs par défaut de paramètre (`infra/opensearch_store.py:81`, `infra/opensearch_pool.py:50`, `default_limit: int = 1000`). Les lectures d'environnement hors `settings` n'ont pas bougé : voir [INFO] n°4. |

**Calcul** :
- Poids conformes : 1.1.1 = 3, 1.1.2 = 3, 1.1.3 = 3, 1.1.4 = 2, 1.2.1 = 3, 1.2.2 = 3, 1.3.1 = 3, 1.4.1 = 3, 1.4.2 = 2, soit **25**.
- Poids total : 32. Items non conformes : 1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2).
- `25 / 32 × 100 = 78,1`, soit **78**.

---

## Ecarts constates

### [MAJ] n°1 — Règles métier dans les services : split/merge, citations et lecture budgétée, plus deux doublons orphelins du domaine

- **Statut vs 0.7.3** : **inchangé**. Aucune ligne modifiée dans les fichiers concernés depuis `02adc68`. **Périmètre précisé** : deux doublons domaine/service, antérieurs, n'avaient pas été relevés (points 4 et 5).
- **Localisation** :
  1. Split/merge (dette 0.7.0) :
     - `services/chunk_service.py:335` (`split_chunk`) : validation `:337`, découpe `:346-347` ;
     - `services/chunk_service.py:393` (`merge_chunks`) : contiguïté `:405`, concaténation `:408`, cumul des tokens `:414` ;
     - face au module orphelin `domain/chunk_editing.py:116` (`merge`) et `:169` (`split`).
  2. Citations (0.7.3) : `services/citation_service.py:39` (`MIN_QUOTE_CHARS`), `:202` (`_locate_quote`), `:230` (`_locate_across`), `:261` (`_trim_left`). Ce sont les lignes `def` ; le rapport 0.7.3 citait les décorateurs `@staticmethod`, une ligne plus haut.
  3. Lecture budgétée (0.7.3) : `services/navigation_service.py:174` (`_span_uri`), `:201` (`_refs_to_read`), `:231` (`_pick`). Heuristique de titre : `services/source_service.py:234` (`_title`).
  4. **Nouveau relevé (antérieur)**, hash de chunkset :
     - le service applique sa propre règle, `services/chunk_service.py:865-882` (`_compute_chunkset_hash`), utilisée en `:623` puis enregistrée sur le lien en `:762` (`link.mark_ingested(hash_=…)`) ;
     - la règle de domaine documentée, `domain/hashing.py:43` (`chunkset_hash`), n'est importée que par `tests/test_hashing.py:5`.
  5. **Nouveau relevé (antérieur)**, niveau de titre : `services/chunk_service.py:927-928` (règle `title` → 0, `section_header` → `max(int(level), 1)` dans `_build_tree_nodes`) duplique `domain/parse_index.py:179` (`heading_level`).
- **Constat** :
  1. *Split/merge.* `domain.chunk_editing` n'est toujours importé que par `tests/test_chunk_editing.py:7`. Le service garde sa propre implémentation, et les deux versions divergent toujours (bboxes, doc_items, token_count).
  2. *Citations.* Le seuil de 10 caractères et la recherche en trois passes (élément, éléments couverts, fenêtres consécutives, puis rognage à gauche) sont des `@staticmethod` purs sur `DocumentIndex`, logés dans le service. La correspondance au niveau des glyphes est, elle, bien dans le domaine (`domain/quote_marks.py`, `domain/anchors.py`).
  3. *Lecture budgétée.* Plusieurs règles sont des fonctions pures, mais elles vivent dans `NavigationService` :
     - la sélection d'éléments sous un budget de tokens, avec reprise par curseur (`_pick`, `:243-264`) ;
     - la grammaire du curseur `ref@offset` (`_refs_to_read`, `:221-229`) ;
     - la règle qui ne publie un span que si toutes ses références ont été lues (`_span_uri`, `:192-199`).
  4. *Hash de chunkset (nouveau relevé).* Les deux règles s'opposent :
     - `domain/hashing.py:1-21` documente la règle canonique : le hash est « recorded on each `DocumentStoreLink` at push time ». Il porte sur texte, page et titres, et exclut explicitement les dates, au motif que « Idempotent re-pipelines on identical input bump `updated_at` without semantic change » ;
     - le service enregistre sur ce même lien un hash différent, calculé sur `id`, `text` et `updated_at` (`chunk_service.py:876-880`). Il fait donc précisément ce que le domaine écarte.

     Le fichier `domain/hashing.py` contient déjà `chunkset_hash` au tag `v0.7.0`, et `chunk_service.py` y appelle déjà `_compute_chunkset_hash` : l'écart est antérieur. Pas d'impact fonctionnel mesurable aujourd'hui : aucun code ne compare ce hash (`grep chunkset_hash` dans `domain/`, `services/`, `persistence/` et `api/` ne trouve que des écritures et des lectures pour affichage). La dette est la même que pour `chunk_editing` : un module de domaine mort, et une règle divergente dans le service. Le code concerné est celui de l'ingestion, dépréciée en 0.8.0.
  5. *Niveau de titre (nouveau relevé).* La règle de `chunk_service.py:928` existait déjà au tag `v0.7.0`. `domain/parse_index.py` n'existait pas au tag `v0.7.0` (`git show` : « exists on disk, but not in 'v0.7.0' ») ; il a été ajouté entre 0.7.0 et 0.7.3 sans que le service soit branché dessus. Les deux versions divergent : celle du domaine tolère un `level` non numérique (`except (TypeError, ValueError)`, `parse_index.py:185`), celle du service lève `ValueError`.

  Comme en 0.7.3, il faut le dire : l'essentiel de la logique de navigation est bien dans le domaine (`outline_builder`, `element_reader`, `source_map`, `spans`, `quote_marks`…). La dérive reste partielle.
- **Regle violee** : item 1.2.3 — « Les règles métier vivent dans `domain/`, pas dans les services » (poids 2).
- **Remediation** :
  1. `ChunkService.split_chunk`/`merge_chunks` → appeler `domain.chunk_editing.split`/`merge`, après avoir aligné ces fonctions sur bboxes, doc_items et token_count. Supprimer ensuite le doublon. **Effort M, risque modéré** : comportement visible des éditions de chunks, 13 références de tests à revoir.
  2. Extraire `_locate_quote`/`_locate_across`/`_trim_left` et `MIN_QUOTE_CHARS` vers `domain/citation_match.py`. **Effort S, risque faible** : méthodes statiques pures, il suffit de les déplacer.
  3. Extraire `_pick`/`_refs_to_read`/`_span_uri` vers `domain/element_reader.py` ou `domain/navigation.py`, en leur passant `DocumentIndex` au lieu de `LoadedParse`. Même chose pour `_title`. **Effort M, risque faible à modéré.**
  4. Hash : choisir une seule règle. Soit `ChunkService` appelle `domain.hashing.chunkset_hash` (les hashes déjà stockés changent, mais rien ne les compare), soit on supprime `domain/hashing.py` et on documente la règle réelle. **Effort S, risque faible.** On peut aussi attendre le retrait de l'ingestion en 0.8.0.
  5. `_build_tree_nodes` → utiliser `domain.parse_index.heading_level`/`label_of`. **Effort S, risque faible** : cela supprime aussi un `ValueError` latent.

  Fermer l'item suppose les cinq points : **effort global L**.

### [MAJ] n°2 — Services couplés à des concrétions : librairies PDF et système de fichiers hors port, dépôts et pools typés sur l'implémentation

- **Statut vs 0.7.3** : **inchangé**. `services/document_service.py` est identique à `02adc68`, et `analysis_service.py` n'a bougé qu'en `:177-180`. **Périmètre précisé** : quatre localisations antérieures n'avaient pas été relevées (points 3, 4 et 5 ci-dessous).
- **Localisation** :
  1. Librairies PDF :
     - `services/document_service.py:14` (`import pypdfium2 as pdfium`) et `:15` (`from pdf2image import convert_from_bytes, pdfinfo_from_bytes`) ;
     - usages dans `document_service.py` : `:162` (`convert_from_bytes`), `:176` (`pdfium.PdfDocument`), `:208` (`pdfinfo_from_bytes`) ;
     - `services/analysis_service.py:17` (`import pypdfium2`), usage `:62`, appelé en `:449`.
  2. Système de fichiers dans `DocumentService` : `:83` et `:198-201` (`os.makedirs`, `open(…, "wb")`), `:96` et `:147` (`os.unlink`), `:106` (`os.path.abspath`), `:119-131` (`resolve_storage_path`, `Path.is_file`), `:144-148` (`os.path.realpath`/`exists`).
  3. **Nouveau relevé (antérieur)** : `services/export_service.py:7` et `:60` (`Path(doc.storage_path).is_file()`).
  4. Dépôts typés sur la concrétion :
     - `services/version_service.py:32` et `:87` (`SqliteDocumentVersionRepository`, sans port) ;
     - `services/store_service.py:23-25` et `:148-150` ;
     - `services/chunk_service.py:43-44` et `:159-160`.
  5. **Nouveau relevé (antérieur)** :
     - `services/store_backend_resolver.py:40-43`, sous `TYPE_CHECKING`. Les concrétions `infra.neo4j.driver_pool.Neo4jDriverPool`, `infra.opensearch_pool.OpenSearchClientPool`, `infra.opensearch_store.OpenSearchStore` et `persistence.store_repo.SqliteStoreRepository` servent de types en `:61` (`IngestionTargets.vector_store: OpenSearchStore`, alors que le port `VectorStore` existe, `domain/ports.py:256`) et en `:81-83` ;
     - `services/chunk_service.py:711` et `:714` appellent `count_for_document` et `find_for_document`, absents du port `ChunkPushRepository` (`domain/ports.py:197-204`).
- **Constat** :
  1. *Contournement du port PDF.* Le port `PageRasterizer` (`domain/ports.py:423`) et son adaptateur `infra/page_raster.py:26-33`, qui fait `read_bytes` puis `convert_from_bytes` puis PNG, existent. Pourtant `DocumentService.generate_preview` (`:159-168`) duplique ce code au lieu de l'utiliser. `build_document_service` (`bootstrap/factories.py:219-228`) n'injecte toujours aucun port PDF. Le test d'architecture assume cette dette : `pdf2image` et `pypdfium2` restent dans `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` (`tests/test_architecture.py:314`), et `TestDocumentAgentServicesAreFrameworkFree` exclut `document_service.py`, qui « predates the port » (`:213-214`). La docstring de `analysis_service.py:3-4` annonce « Uses injected ports … decoupled from infrastructure implementations », alors que le module importe `pypdfium2` en `:17`.
  2. *Conséquence PLAUSIBLE, thread-safety pdfium.*
     - L'adaptateur `infra/page_text.py:7-9,21-24,31` explique que pdfium n'est pas thread-safe, et il prend le verrou partagé avec Docling (`docling.utils.locks.pypdfium2_lock`).
     - Deux appels de service ouvrent pdfium sans ce verrou :
       - `DocumentService.page_sizes`, depuis un thread de travail (`api/documents.py:216`) ;
       - `analysis_service._count_pdf_pages`, appelé **de façon synchrone sur la boucle d'événements** (`analysis_service.py:449`), alors que d'autres analyses (jusqu'à 3 par défaut, `:56`) peuvent faire tourner Docling dans des threads.
     - Non vérifié localement : `docling` n'est pas installé dans `.venv` (seul `docling_core` y est), je n'ai donc pas pu lire `docling/utils/locks.py`. L'impact est à confirmer par l'audit 12.
  3. *Règle de stockage appliquée à moitié (nouveau constat, conséquence directe).*
     - `resolve_storage_path` (`document_service.py:119-131`, #359) sait retrouver un fichier enregistré sous `/app/uploads/…` quand le backend tourne sur l'hôte. Ses seuls appelants sont les deux routes `api/documents.py:186` et `:214` (`grep resolve_storage_path`).
     - Les autres consommateurs de `Document.storage_path` utilisent le chemin brut :
       - l'export PDF (`export_service.py:60,63`) ;
       - le lancement d'analyse (`analysis_service.py:154`) ;
       - les rasters MCP (`citation_image_service.py:74`) ;
       - la couche texte (`source_service.py:146`).
     - Dans le scénario décrit par la docstring (`document_service.py:122-125`), l'aperçu fonctionne donc alors que l'export, l'analyse et les cartes MCP échouent (PLAUSIBLE, limité au développement hors Docker). Une règle de localisation de fichier qui vit dans une méthode de service appelée par le routeur, au lieu d'un port de stockage, n'est appliquée que là où on pense à l'appeler.
  4. *Dépôts.*
     - `VersionService` est typé sur `SqliteDocumentVersionRepository` : il n'existe aucun `DocumentVersionRepository` dans `domain/ports.py`.
     - `StoreService` utilise des méthodes absentes du port `StoreRepository` (`domain/ports.py:128-139`) : `update` (`:297`), `delete` (`:395`), `find_by_name` (`:214`, `:257`), `clear_default_except` (`:233`, `:306`) et `set_connection_password` (`:303`). S'y ajoutent `count_by_store` sur le dépôt des liens (`:163`) et `find_by_ids` sur le dépôt documents (`:361`, absent de `DocumentRepository`).
     - `StoreBackendResolver` appelle `get_connection_password` (`:128`, `:143`), absent du port lui aussi.
     - À l'inverse, `ChunkService` est typé sur `SqliteStoreRepository`/`SqliteDocumentStoreLinkRepository` (`:159-160`), alors qu'il n'appelle que des méthodes du port (`find_by_id`, `find_by_slug`, `find_one`, `upsert`). En revanche, il appelle deux méthodes absentes de `ChunkPushRepository` alors qu'il est typé sur ce port (`:153`, `:711`, `:714`).
     - Aucun vérificateur de types ne tourne : pas de `mypy`/`pyright` dans `pyproject.toml`, `.github/workflows/` ni `.pre-commit-config.yaml`. Ces contrats incomplets ne sont donc détectés nulle part.
     - Tous ces imports sont sous `TYPE_CHECKING`, et l'injection se fait dans `bootstrap/` : aucun import runtime. Mais le contrat est celui de l'adaptateur, pas celui du domaine.
     - `store_backend_resolver.py:40-43` est identique au tag `v0.7.0`. La partie stores et ingestion est dépréciée en 0.8.0.
- **Regle violee** : item 1.2.4 — « Les services reçoivent leurs dépendances par injection, pas par import direct de concrétions » (poids 2).
- **Remediation** :
  1. Injecter `PageRasterizer` dans `DocumentService` (`bootstrap/factories.py:219`) et supprimer `generate_preview`. **Effort S, risque faible** : même pipeline pdf2image/PNG. Les tests `tests/test_document_service.py:136-149`, qui patchent `services.document_service.convert_from_bytes`, sont à réécrire.
  2. Créer un port `PdfInspector` (`page_sizes`, `page_count`) implémenté dans `infra/` **sous le verrou pdfium**, puis y migrer `DocumentService.page_sizes`, `_count_pages` et `analysis_service._count_pdf_pages`. **Effort M, risque modéré** : le comptage à l'upload passe aujourd'hui par poppler (`pdfinfo`), et les PDF malformés peuvent compter différemment sous pdfium. Ce point règle aussi la question de thread-safety PLAUSIBLE.
  3. Créer un port `FileStorage` (`save`, `delete`, `resolve`, `exists`), utilisé par `DocumentService`, `ExportService` et `AnalysisService`, et par l'adaptateur raster. **Effort M, risque modéré** : il faut conserver le garde-fou « suppression uniquement sous `upload_dir` » (`document_service.py:144-149`).
  4. Retirer `pdf2image`/`pypdfium2` de `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` et les ajouter à `_SERVICES_FORBIDDEN_EXTERNALS`. **Effort S.**
  5. Retyper `ChunkService` (`:159-160`) sur `StoreRepository`/`DocumentStoreLinkRepository` : il suffit de changer les annotations. **Effort S, risque nul.** Ajouter `count_for_document`/`find_for_document` à `ChunkPushRepository`. **Effort S.**
  6. Créer `DocumentVersionRepository`, compléter `StoreRepository`/`DocumentStoreLinkRepository`/`DocumentRepository`, et typer `IngestionTargets.vector_store` sur `VectorStore`. **Effort M.** Ce point peut attendre 0.8.0 pour la partie stores, vouée au retrait.

  Fermer l'item suppose les points 1 à 4 au minimum, plus le typage des dépôts : **effort global L**.

### [MAJ] n°3 — Couche HTTP qui orchestre : jointure de deux dépôts, I/O disque et règles dans `api/documents.py`

- **Statut vs 0.7.3** : **inchangé**. `api/documents.py` et `api/analyses.py` n'ont pas changé depuis `02adc68`. **Périmètre précisé** : un point antérieur n'avait pas été relevé (point 4 de la Localisation).
- **Localisation** :
  1. Store-links (dette 0.7.0) : `api/documents.py:40-66` (`_fetch_store_links`), appelé par `get_document` (`:110-122`), qui reçoit `link_repo`/`store_repo` via `api/deps.py:90-105`.
  2. Preview et pages (0.7.3) :
     - `api/documents.py:176-180` (validation de la plage de pages) ;
     - `api/documents.py:185-190` (preview) et `:212-216` (`GET /pages`, #352) ;
     - import runtime de la classe concrète `api/documents.py:14`.
  3. Contrat d'erreur par libellé (0.7.3) : `api/analyses.py:84` (`str(e).startswith("Document not found:")`), qui dépend du message levé en `services/analysis_service.py:173`.
  4. **Nouveau relevé (antérieur)** : `api/document_versions.py:30-35`. Le routeur décode lui-même le snapshot persisté (`json.loads(version.chunks_snapshot)`) pour en calculer la taille. Le code est identique au tag `v0.7.0`.
- **Constat** :
  1. *Store-links.* Le routeur appelle lui-même deux dépôts (`link_repo.find_for_document` `:52`, `store_repo.find_all` `:57`), puis fait la jointure `slug_by_id` (`:58`). Le code est identique à 0.7.0 et 0.7.3.
  2. *Preview et pages.*
     - Les deux handlers font la lecture disque eux-mêmes (`service.resolve_storage_path(doc.storage_path).read_bytes` passé à `asyncio.to_thread`).
     - Ils choisissent aussi le passage par un thread, puis appellent les méthodes **statiques de la classe** `DocumentService` (`:189`, `:216`) au lieu de l'instance injectée.
     - La règle « page hors plage » (`:176-180`) est dans le routeur.
     - Le cas d'usage « obtenir l'image ou les dimensions des pages d'un document » reste donc découpé entre l'API et le service. C'est aussi pour cela que la règle de résolution du chemin n'est appliquée que là (voir [MAJ] n°2, constat 3).
  3. *Erreur d'import.* Le choix entre 404 et 400 dépend du préfixe du message. Un type `DocumentNotFoundError` existe déjà dans deux modules de services (`services/navigation_errors.py:24`, `services/chunk_service.py:73`), mais `AnalysisService` lève un `ValueError` générique.
  4. *Snapshot de version.* Le routeur connaît le format de stockage (une chaîne JSON, `domain/models.py:329`) et en tire une donnée dérivée. C'est une petite fuite de logique, du même type que les précédentes.

  Note : l'item 1.3.1 reste conforme. Il n'y a aucun import de `persistence/` : ce sont des ports.
- **Regle violee** : item 1.3.3 — « Les endpoints délèguent toute la logique aux services » (poids 2).
- **Remediation** :
  1. Créer `DocumentService.get_with_store_links(doc_id)`, avec injection de `StoreRepository` et `DocumentStoreLinkRepository` dans `build_document_service`. Retirer ensuite `StoreRepoDep`/`DocumentStoreLinkRepoDep` des handlers. Ils ne sont utilisés que là : `grep RepoDep api/` ne trouve que `api/documents.py:114-115`. **Effort S, risque faible** : le test `tests/test_api_endpoints.py:42-46`, qui injecte les deux dépôts dans l'état, est à adapter.
  2. Créer `async DocumentService.render_preview(doc_id, page, dpi)` et `async DocumentService.page_sizes(doc_id)`. Ils portent la lecture du fichier (de préférence via le port de stockage), la validation de plage, et `to_thread`. Le routeur ne fait plus que traduire les erreurs typées en codes HTTP. **Effort S-M, risque faible** : 5 tests API (`tests/test_api_endpoints.py:209-264`) à adapter, et le contrat HTTP (404, 400, 422) est inchangé.
  3. Lever `DocumentNotFoundError` (un type commun aux services) dans `AnalysisService.create`/`import_docling_document`, et la mapper sur 404 dans le routeur. **Effort S, risque faible** : `tests/test_api_endpoints.py:524,561` simulent aujourd'hui `ValueError("Document not found: …")`.
  4. Exposer `chunks_snapshot_size` depuis le service (ou par une propriété de `DocumentVersion`), et retirer `json` de `api/document_versions.py`. **Effort S, risque nul.**

  Fermer l'item suppose les quatre points : **effort global M** (une demi-journée à une journée, tests compris).

### [MIN] Les conversions snake_case → camelCase fuient toujours hors de `api/schemas.py`

- **Statut vs 0.7.3** : **inchangé**. **Périmètre précisé** : la liste 0.7.3 était incomplète, les sites en plus sont antérieurs.
- **Localisation** :
  1. Déjà listés en 0.7.3 :
     - `services/chunk_service.py:105-108` et `:858-861` ;
     - `services/analysis_service.py:47-51` ;
     - `services/version_service.py:53-61`.
  2. **Relevés en plus** :
     - `services/chunk_service.py:555-569` (`"chunkId"`, `"textDiff"` du diff de push), `:686` (`"pushId"`), `:731-738` (`"documentId"`, `"storeId"`, `"storeSlug"`, `"chunksetHash"`, `"pushedAt"`…) ;
     - lectures inverses en `chunk_service.py:118,134-137`, `version_service.py:220-226` et `ingestion_service.py:193` ;
     - côté adaptateur : `infra/neo4j/chunk_writer.py:75-80`.
  3. Côté consommateur API :
     - `api/analyses.py:173-181` et `:196-204` (relecture de `"sourcePage"`/`"tokenCount"`) ;
     - `api/document_chunks.py:199` (`ChunkDiffResponse(**d)`), `:214` (`result["pushId"]`) et `:237` (`ChunkPushEntryResponse(**entry)`).
- **Constat** :
  - Les services construisent à la main des dicts au format du contrat front. Le routeur relit ensuite ces clés camelCase, ou les déverse telles quelles dans un schéma Pydantic. Le mapping se fait donc en aller-retour entre les deux couches.
  - Une partie de ce camelCase est aussi le **format persisté** : `chunks_json` est écrit via `_chunk_to_dict` (`analysis_service.py:233`, `:473`), et `chunks_snapshot` via `_serialize_chunks` (`version_service.py:45`). C'est ce qui rend la correction moins triviale qu'il n'y paraît.
  - En positif : les contrats MCP et de configuration restent confinés à `api/schemas.py` et `mcp_adapter/wire.py`.
- **Regle violee** : item 1.3.2 — « Les transformations camelCase/snake_case restent dans `api/schemas.py` » (poids 1).
- **Remediation** :
  - Faire retourner aux services des value objects (`ChunkResult`, `Chunk`, `ChunkDiff`, `ChunkPushEntry`), et laisser l'`alias_generator` de `api/schemas.py` faire la conversion.
  - Déplacer la sérialisation du format persisté (`chunks_json`, `chunks_snapshot`) dans `persistence/`, sans changer les octets écrits, pour garder la compatibilité des bases existantes.
  - **Effort M, risque modéré** : les formats persistés et les relectures (`version_service.py:220-226`, `ingestion_service.py:193`, `infra/neo4j/chunk_writer.py:75-80`) doivent rester compatibles.

### [INFO] n°1 — Les règles pytestarch du test d'architecture ne vérifient rien

- **Statut vs 0.7.3** : **inchangé**.
- **Localisation** :
  - `tests/test_architecture.py:6-14` : docstring qui annonce les règles ;
  - `:114-176` et `:277-290` : règles pytestarch ;
  - `:185-193` : aveu de l'inopérance ;
  - à confronter à `persistence/store_repo.py:25`.
- **Constat** :
  - Le test le reconnaît lui-même : le dossier racine `document-parser` n'est pas un package importable, et « adding `from persistence.database import get_connection` to a `services/` module leaves every rule green » (`:190-192`).
  - `TestPersistenceLayerIsolation` passe alors que `persistence/store_repo.py:25` importe `infra.secrets`.
  - Seuls les contrôles par `ast` sont effectifs : `mcp_adapter`, services document-agent, librairies externes, convention de ports.
  - Remplacer naïvement les règles par `_collect_imports` (`:92-106`) ferait aussi remonter les imports sous `TYPE_CHECKING` vers `persistence` et `infra` de 4 services (voir [MAJ] n°2), puisque le collecteur parcourt tout l'AST.
  - Ce point est hors barème : `tests/` est hors cible de la fiche.
- **Remediation** : remplacer les règles pytestarch par le scanner `ast`, une règle par couche, en ignorant ou en consignant explicitement les blocs `TYPE_CHECKING`. Traiter ensuite les écarts qui apparaîtront, à commencer par `persistence -> infra`.

### [INFO] n°2 — Couplage entre adaptateurs : `persistence` importe `infra`

- **Statut vs 0.7.3** : **inchangé**.
- **Localisation** : `persistence/store_repo.py:25` (`from infra.secrets import get_fernet_box`).
- **Constat** : identique à 0.7.0 et 0.7.3. Ce chiffrement concerne les stores d'ingestion, dépréciés en 0.8.0.
- **Remediation** (facultatif) : un port `SecretBox`, ou laisser le code disparaître avec l'ingestion en 0.8.0.

### [INFO] n°3 — Le domaine lit directement le schéma JSON de Docling, contrairement à ce qu'annonce son docstring

- **Statut vs 0.7.3** : **inchangé**.
- **Localisation** : le docstring `domain/parse_index.py:3-6` affirme le contraire de ce que font :
  - `domain/parse_index.py:86` et `:194` (`self_ref`), `:115`, `:130-134` et `:165` (`page_no`), `:173` (`coord_origin`) ;
  - `domain/element_reader.py:85-86` (`children`/`$ref`/`cref`), `:156-157` (`captions`), `:179`, `:195` et `:199` (`data`/`grid`/`table_cells`).
- **Constat** :
  - Le docstring dit « Every docling-shaped access goes through the injected `DocumentTreeReader` port ». En réalité, le port ne fait que le parcours, et le domaine lit lui-même les clés du format Docling.
  - Les items 1.1.1 et 1.1.2 ne sont pas violés : pas d'import, pas d'I/O.
  - La couche anti-corruption reste partielle.
- **Remediation** (facultatif) : faire normaliser les éléments en value objects par `DocumentTreeReader`, ou corriger le docstring pour décrire le compromis réel.

### [INFO] n°4 — Valeurs de configuration lues hors de `infra/settings.py`

- **Statut vs 0.7.3** : **inchangé**.
- **Localisation** :
  - `infra/secrets/fernet_box.py:126` : `os.environ.get("STORE_SECRET_KEY")`, alors que `settings.store_secret_key` existe (`infra/settings.py:46`, `:228`) et sert déjà au contrôle de démarrage (`bootstrap/factories.py:138`) ;
  - `persistence/database.py:26` (`DB_PATH`) et `:249` (`DEFAULT_EMBEDDER`, absent de `Settings`) ;
  - `mcp_stdio.py:44` (troisième copie du défaut `./data/docling_studio.db`) ;
  - `services/navigation_config.py:44-45` et `:52-54` : taille du cache d'index et budgets de raster codés en dur et non surchargeables, alors que le commentaire `:42-43` demande à l'opérateur de dimensionner son worker d'après eux.
- **Constat** :
  - Ce sont les mêmes lignes qu'en 0.7.3, et il y a toujours trois sources de vérité pour `DB_PATH`.
  - `mcp_stdio.py:49-50` justifie la sienne : `persistence` et `settings` lisent `DB_PATH` à l'import.
  - La fiche ne contient pas de constantes d'URL ou d'hôte codées en dur dans `infra/`, donc 1.4.2 est jugé conforme, comme en 0.7.3.
  - En lecture stricte (« les valeurs de config viennent de `infra/settings.py` »), `fernet_box.py:126` rendrait 1.4.2 non conforme : 23/32, soit 72.
- **Remediation** :
  - `get_fernet_box` lit `settings.store_secret_key`, en gardant la lecture paresseuse ;
  - `persistence/database.py` lit `settings.db_path` ;
  - ajouter `default_embedder` à `Settings` ;
  - exposer `index_cache_size`/`index_cache_max_chars` en variables d'environnement, si l'opérateur doit vraiment les dimensionner.

### [INFO] n°5 — Frontend : `shared/` dépend de `features/`, et des pages font des imports profonds (hors barème)

- **Statut vs 0.7.3** : **inchangé**. `git diff 02adc68..HEAD` ne touche ni `frontend/eslint.config.js`, ni `AppSidebar.vue`, ni `pages/`.
- **Localisation** :
  - `frontend/src/shared/ui/AppSidebar.vue:55-56` (`../../features/feature-flags/store`, `../../features/ingestion/store`) ;
  - `frontend/src/pages/DocWorkspacePage.vue:62-63,70`, `SearchPage.vue:54-56`, `AnalysisDetailPage.vue:39,44`, `DocsNewPage.vue:86`, `IngestLaunchDialog.vue:115`.
- **Constat** :
  - La fiche 01 ne couvre pas le frontend.
  - `shared/` importe des stores de features, ce qui inverse la dépendance attendue.
  - Les motifs ESLint (`frontend/eslint.config.js:33-49`) ne couvrent qu'un ou deux segments relatifs : ils ne détectent ni `../../features/<x>/store` depuis `shared/`, ni `../features/<x>/api` depuis `pages/`.
  - En positif : la remédiation 0.7.3 a déplacé `ConfigSource` dans `frontend/src/shared/types.ts`, ce qui supprime un accès croisé entre features.
  - Ce point relève surtout de l'audit 07.
- **Remediation** (facultatif) : ajouter les motifs `'**/features/*/store'`, `'**/features/*/api'` et `'**/features/*/ui/*'`. Faire passer `AppSidebar` par les barrels.

### [INFO] n°6 — `DownloadDropdown.vue` fait un `fetch()` direct (hors barème)

- **Statut vs 0.7.3** : **inchangé**. Toujours à la même ligne.
- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:133` (`const response = await fetch(url)`).
- **Constat** : la feature contourne la couche `api/` et `@/shared/api/http`. Le point est présent depuis 0.7.0.
- **Remediation** (facultatif) : passer par une fonction `downloadExport()` dans `features/document/api`.

### [INFO] n°7 — La sonde `/api/health` exécute du SQL depuis le point d'entrée (nouveau relevé, antérieur)

- **Statut vs 0.7.3** : **nouveau relevé**. Le point est antérieur : `main.py` du tag `v0.7.0` contient déjà `from persistence.database import get_connection` et `SELECT 1`.
- **Localisation** : `main.py:40` (`from persistence.database import get_connection`), `main.py:128-137` (`@app.get("/api/health")` puis `db.execute("SELECT 1")`).
- **Constat** :
  - C'est une route HTTP qui ouvre une connexion et exécute du SQL, sans port ni service.
  - Elle vit dans `main.py`, la composition root, et non dans `api/`. Le grep de 1.3.1 ne la voit pas, et les audits précédents la tolèrent de fait.
  - L'impact est nul sur le métier, puisqu'il s'agit d'une sonde technique. En lecture stricte de 1.3.1 (« les routes n'importent pas `persistence/` »), ce serait un écart de poids 3.
  - Je le classe en INFO, par cohérence avec le statut de composition root reconnu à `main.py` depuis 0.6.1.
- **Remediation** (facultatif) : ajouter un `ping()` à un port existant, ou un port `HealthProbe` câblé dans `bootstrap/`, et déplacer la route dans `api/health.py`.

---

## Delta vs 0.7.3

**Score : 78 → 78 (Δ 0).** Mêmes 9/13 items conformes, mêmes 4 items non conformes (1.2.3, 1.2.4, 1.3.2, 1.3.3). Le backend de la 0.7.4 est identique au tag `v0.7.3`. La remédiation 0.7.3 (#367, #368) ne visait pas l'audit 01.

| Écart 0.7.3 | Statut en 0.7.4 | Détail |
|-------------|-----------------|--------|
| [MAJ] Règles métier dans les services (1.2.3) | **Inchangé, périmètre précisé** | Aucune ligne modifiée. Ajout de 2 doublons domaine/service antérieurs : `chunkset_hash` (`domain/hashing.py:43` vs `chunk_service.py:865`) et `heading_level` (`parse_index.py:179` vs `chunk_service.py:928`). |
| [MAJ] Concrétions dans les services (1.2.4) | **Inchangé, périmètre précisé** | `document_service.py` identique. Relevé en plus : `store_backend_resolver.py:40-43,61,81-83`, `export_service.py:60`, appels hors port `chunk_service.py:711,714` et `store_service.py:361`. Règle `resolve_storage_path` appliquée par 2 appelants seulement. |
| [MAJ] Orchestration et I/O dans `api/documents.py` (1.3.3) | **Inchangé, périmètre précisé** | Identique. Relevé en plus : `api/document_versions.py:33` (`json.loads` du snapshot). |
| [MIN] camelCase dans les services (1.3.2) | **Inchangé, périmètre précisé** | Mêmes lignes, plus 3 sites `chunk_service` non listés (diff, push, liste des push). |
| [INFO] pytestarch inopérant | Inchangé | |
| [INFO] `persistence` → `infra.secrets` | Inchangé | |
| [INFO] Schéma Docling lu dans le domaine | Inchangé | |
| [INFO] Config hors `settings` | Inchangé | |
| [INFO] Frontend `shared`/`pages` | Inchangé | `ConfigSource` déplacé dans `shared/types.ts` (remédiation 07). |
| [INFO] `DownloadDropdown.vue` `fetch()` | Inchangé | Ligne 133. |
| — | **Nouveau [INFO]** | Sonde `/api/health` qui exécute du SQL dans `main.py` (antérieur à 0.7.0). |

Changement positif dans le périmètre, sans effet sur le barème : l'import Docling (#359) passe maintenant par `asyncio.to_thread` et par le port `DoclingDocumentImporter` (`services/analysis_service.py:180`).

---

## Quick wins et trajectoire de score

Les items sont binaires : une correction partielle ne change pas le score. Gain par item fermé (sur 32) :

| Action | Item fermé | Gain | Score obtenu | Effort | Risque |
|--------|-----------|------|--------------|--------|--------|
| [MAJ] n°3 en entier : `get_with_store_links`, `render_preview`/`page_sizes` dans le service, `DocumentNotFoundError` typée, taille de snapshot calculée côté service | 1.3.3 (2) | **+6,25** | **84 (GO)** | M (4 sous-tâches S) | faible : contrat HTTP inchangé, ~8 tests API à adapter |
| + [MAJ] n°2 points 1 à 5 (port raster injecté, `PdfInspector` sous verrou, `FileStorage`, typage des dépôts) | 1.2.4 (2) | +6,25 | 91 | L | modéré : comptage de pages, suppression sécurisée |
| + [MAJ] n°1 en entier | 1.2.3 (2) | +6,25 | 97 | L | modéré : split/merge |
| + [MIN] camelCase hors services | 1.3.2 (1) | +3,1 | 100 | M | modéré : formats persistés |

Corrections à risque nul ou faible, qui réduisent le périmètre des MAJ sans changer le score à elles seules :
- retyper `ChunkService` (`chunk_service.py:159-160`) sur les ports : annotations seulement ;
- ajouter `count_for_document`/`find_for_document` à `ChunkPushRepository` (`domain/ports.py:197`) ;
- injecter `PageRasterizer` dans `DocumentService` et supprimer `generate_preview` ;
- extraire l'appariement des citations vers `domain/citation_match.py` ;
- brancher `_build_tree_nodes` sur `domain.parse_index.heading_level`.

---

## Points positifs

- **Domaine toujours pur** : 26 modules, 21 ports, seulement la stdlib et `domain.*`, ni Pydantic ni I/O (items 1.1.1 à 1.1.4).
- **Le serveur MCP respecte toujours ports & adapters.**
  - `mcp_adapter/` n'importe que `services`, `domain`, le SDK `mcp`, `pydantic` et la stdlib, jamais `api`, `infra` ni `persistence`.
  - C'est vérifié par un vrai contrôle `ast` (`tests/test_architecture.py:197-203`).
  - Chaque outil se résume à résoudre le service, l'appeler, puis mapper le résultat (`mcp_adapter/server.py:126-200`).
- **Les ports récents sont injectés au bon endroit.**
  - `CitationImageService` et `SourceService` reçoivent `PageRasterizer` et `PageTextReader` depuis `bootstrap/factories.py:286-292,298-307`.
  - L'import Docling passe par `DoclingDocumentImporter` (`domain/ports.py:86`, `infra/docling_importer.py:13`), et il tourne désormais hors de la boucle d'événements (`services/analysis_service.py:180`), sans que le service connaisse Docling.
- **Configuration MCP exemplaire** : les règles de validation sont dans le domaine (`domain/mcp_config.py:94`), le service orchestre sans connaître ni infra ni le SDK, et le routeur `api/config.py` ne fait que mapper les DTO.
- **Garde-fous honnêtes** : `TestDocumentAgentServicesAreFrameworkFree` et l'inventaire `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` (`tests/test_architecture.py:314`) rendent la dette PDF visible et empêchent qu'elle disparaisse en silence.
- **API sans persistence** (1.3.1), **services sans framework ni SQL** (1.2.1, 1.2.2), **un port par adaptateur** (1.4.1) : toujours conformes.

---

## Verdict partiel : GO CONDITIONNEL

- **Aucun écart CRITICAL** : les sept items de poids 3 sont conformes.
- **Score de 78/100**, dans la plage 60-79.
- **Trois écarts MAJOR**, ce qui ne déclenche pas la règle « > 3 MAJ » pour cet audit.

Le code audité est celui du tag `v0.7.3`. Les trois MAJ sont **les mêmes qu'en 0.7.0 et 0.7.3**, reportés une troisième fois sans être traités. Cette relecture élargit leur périmètre avec du code antérieur qui n'avait pas été relevé, sans rien ajouter de nouveau.

Plan de remédiation recommandé, par ordre de rendement :
1. **[MAJ] n°3 (1.3.3)** : effort M et risque faible. C'est le seul MAJ qu'on peut fermer en une PR, et il fait passer l'audit 01 à **84 (GO)**.
2. **[MAJ] n°2 (1.2.4)** : commencer par injecter `PageRasterizer` et créer `PdfInspector` sous le verrou pdfium, ce qui règle aussi la question de thread-safety PLAUSIBLE ; finir par le port `FileStorage`, qui applique enfin `resolve_storage_path` partout.
3. **[MAJ] n°1 (1.2.3)** : extraire les citations (S), puis brancher split/merge sur `domain/chunk_editing.py` (M). Hash et niveau de titre : unifier, ou attendre le retrait de l'ingestion en 0.8.0.
4. **[INFO] n°1** : rendre les règles de couche réellement vérifiantes, pour que ces frontières tiennent une fois corrigées.

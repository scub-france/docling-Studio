# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

Fiche : `docs/audit/audits/01-clean-architecture.md` — cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Baseline : `docs/audit/reports/release-0.7.0/01-clean-architecture.md` (78/100). Il n'y a pas de rapport 01 dans `release-0.7.0-reaudit/` : l'audit 01 n'avait pas été ré-audité, il gardait son score et ses 3 MAJ comme dette.
Méthode : analyse statique (grep, lecture de code, `git diff v0.7.0..HEAD`, `git blame`). Je n'ai lancé ni l'application ni les suites de tests.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 6 |

Taille du périmètre à 02adc68 :

| Couche | Taille | Évolution depuis v0.7.0 |
|--------|--------|-------------------------|
| `domain/` | 26 modules, 4 259 lignes | +11 modules purs (navigation, ancres, parse index, source map…) |
| `domain/ports.py` | 21 `Protocol` | +3 : `DoclingDocumentImporter`, `PageRasterizer`, `PageTextReader` |
| `services/` | 22 modules, 5 057 lignes | +11 modules (services document-agent, config MCP) |
| `mcp_adapter/` | 10 modules `.py`, 1 485 lignes, plus 2 templates HTML | nouveau (adaptateur primaire MCP) |
| `infra/` | 30 modules | +4 : `docling_importer`, `docling_pages`, `page_raster`, `page_text` |
| `api/` | 14 modules, 2 384 lignes | +1 routeur (`api/mcp.py`) |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` n'importe ni FastAPI, ni aiosqlite, ni aucune lib infra | 3 | Oui | Le grep de la fiche ne trouve rien. Les 26 modules n'importent que la stdlib et `domain.*`. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Aucun `open`, `os.*`, `Path`, HTTP ni SQL dans `domain/`. Seuls effets de bord : `datetime.now` et `uuid4` (`domain/models.py:30,34`), qui ne sont pas des I/O. |
| 1.1.3 | Toute interaction externe passe par un protocole de `domain/ports.py` | 3 | Oui | Le domaine reçoit ses besoins externes par des ports (`DocumentTreeReader` est injecté dans `build_index`, `domain/parse_index.py:80`). Comme en 0.7.0, l'item est lu au niveau du domaine : les contournements de port côté services relèvent de 1.2.4. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import `pydantic` : uniquement des `@dataclass(frozen=True)` et des `StrEnum`. |
| 1.2.1 | `services/` n'importe jamais `fastapi`/`Request`/`Response`/`Depends` | 3 | Oui | Le grep de la fiche ne trouve rien, ni `starlette`. Les erreurs portent un simple indice `http_status` (`services/navigation_errors.py:13`), comme le veut la convention existante. |
| 1.2.2 | Les services appellent les repos, jamais de SQL direct | 3 | Oui | Aucun `SELECT`, `INSERT`, `execute(` ni `get_connection` dans `services/`. |
| 1.2.3 | Les règles métier vivent dans `domain/` | 2 | **Non** | Split/merge toujours dans le service (dette 0.7.0). Nouvelles règles de citation et de lecture logées dans les services. Voir [MAJ] n°1. |
| 1.2.4 | Dépendances injectées, pas d'import direct de concrétions | 2 | **Non** | Librairies PDF et système de fichiers toujours dans `document_service`/`analysis_service`, avec en plus `pypdfium2` (#352). Voir [MAJ] n°2. |
| 1.3.1 | Les routes n'importent pas `persistence/` | 3 | Oui | Le grep de la fiche ne trouve rien. `api/` ne voit que des ports (`api/deps.py:15`). |
| 1.3.2 | camelCase/snake_case confiné à `api/schemas.py` | 1 | **Non** | Des dicts camelCase sont toujours construits dans les services. Voir [MIN]. |
| 1.3.3 | Les endpoints délèguent toute la logique aux services | 2 | **Non** | Jointure store-links toujours dans le routeur. Les routes preview et pages font maintenant des I/O disque. Voir [MAJ] n°3. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | Les 4 nouveaux adaptateurs correspondent chacun à un port : `PdfPageRasterizer`→`PageRasterizer`, `PdfPageTextReader`→`PageTextReader`, `DoclingDocumentImporter`→port homonyme ; `docling_pages` sert de helper aux converters. `FernetBox` et `RateLimiterMiddleware` restent sans port, comme toléré en 0.7.0. |
| 1.4.2 | Config issue de `infra/settings.py`, pas de constantes en dur | 2 | Oui | Le grep de la fiche ne remonte que des valeurs par défaut de paramètres. Les nouvelles clés (`MCP_*`, `ASK_MODE`) sont dans `infra/settings.py:67` et `:90-122`. Quelques lectures d'environnement contournent `settings` : voir [INFO]. |

Calcul : poids conformes = 25 sur 32 (1.1.1=3, 1.1.2=3, 1.1.3=3, 1.1.4=2, 1.2.1=3, 1.2.2=3, 1.3.1=3, 1.4.1=3, 1.4.2=2). Items non conformes : 1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2). `25 / 32 * 100 = 78,1`, soit **78**.

---

## Ecarts constates

### [MAJ] Règles métier dans les services : split/merge toujours dupliqués, citation et lecture budgétée ajoutées hors domaine

- **Localisation** :
  - Dette 0.7.0, inchangée : `services/chunk_service.py:335` (`split_chunk`) et `services/chunk_service.py:393` (`merge_chunks`), face au module orphelin `domain/chunk_editing.py:116` (`merge`) et `domain/chunk_editing.py:169` (`split`).
  - Nouveau en 0.7.3 : `services/citation_service.py:39` (`MIN_QUOTE_CHARS`), `:201` (`_locate_quote`), `:229` (`_locate_across`), `:260` (`_trim_left`) ; `services/navigation_service.py:174` (`_span_uri`), `:201` (`_refs_to_read`), `:231` (`_pick`) ; `services/source_service.py:234` (`_title`).
- **Constat** :
  1. *Split/merge.* `git diff v0.7.0..HEAD` ne montre aucun changement sur ces deux fichiers. `domain.chunk_editing` n'est importé que par `tests/test_chunk_editing.py:7`, aucun module applicatif ne l'utilise. Le service garde sa propre implémentation : validation d'offset `:337`, découpe `:346-347`, contiguïté `:405`, concaténation `:408`. Les deux versions divergent toujours (bboxes, doc_items, token_count).
  2. *Citations.* Ce qui fait qu'une citation est « vérifiée » est une règle cœur du produit (« the server, not the model, is the source of truth », docstring `citation_service.py:5-7`). Or le seuil de 10 caractères, la recherche en trois passes (élément, puis éléments couverts, puis fenêtres d'éléments consécutifs) et le rognage à gauche du span sont des `@staticmethod` purs sur `DocumentIndex`. Ils vivent dans le service. La correspondance au niveau des glyphes est, elle, bien dans le domaine (`domain/quote_marks.py`), et `normalise_quote` dans `domain/anchors.py`.
  3. *Lecture budgétée.* Plusieurs règles sont des fonctions pures du domaine logées dans `NavigationService` : la sélection d'éléments sous un budget de tokens avec reprise par curseur (`_pick`), la grammaire du curseur `ref@offset` (`_refs_to_read`), et la règle qui ne publie un span que si toutes ses références ont été lues (`_span_uri`). Même chose pour l'heuristique de titre du document (`source_service._title`).
  Il faut le dire : l'essentiel de la logique de navigation a bien été placé dans le domaine (11 modules purs ajoutés : `outline_builder`, `element_reader`, `source_map`, `spans`, `quote_marks`…). La dérive reste partielle, mais elle reproduit le schéma signalé en 0.7.0.
- **Regle violee** : item 1.2.3 — « Les règles métier vivent dans `domain/`, pas dans les services » (poids 2).
- **Remediation** :
  1. Faire appeler `domain.chunk_editing.split`/`merge` par `ChunkService.split_chunk`/`merge_chunks`, après avoir enrichi ces fonctions avec bboxes, doc_items et token_count. Supprimer ensuite le doublon.
  2. Extraire `_locate_quote`/`_locate_across`/`_trim_left` et `MIN_QUOTE_CHARS` vers un module de domaine (p.ex. `domain/citation_match.py`), et `_pick`/`_refs_to_read`/`_span_uri` vers `domain/element_reader.py` ou `domain/navigation.py`. Les services ne gardent que le chargement de la parse et l'assemblage du résultat.

### [MAJ] Services couplés à des concrétions : librairies PDF et système de fichiers hors port, dépôts typés sur l'implémentation SQLite

- **Localisation** :
  - `services/document_service.py:14` (`import pypdfium2 as pdfium`, ajouté par #352) et `:15` (`from pdf2image import convert_from_bytes, pdfinfo_from_bytes`) ; usages `:162` (`convert_from_bytes`), `:176` (`pdfium.PdfDocument`), `:208` (`pdfinfo_from_bytes`), `:199` (`open(...)`), `:147` (`os.unlink`), `:119-131` (`resolve_storage_path`, `Path.is_file`, ajouté par #359).
  - `services/analysis_service.py:17` (`import pypdfium2`), usage `:62`.
  - Dépôts typés sur la concrétion : `services/version_service.py:32` et `:87` (`SqliteDocumentVersionRepository`, sans port) ; `services/store_service.py:23-25` et `:148-150` ; `services/chunk_service.py:43-44`.
- **Constat** :
  1. *Dette 0.7.0 aggravée.* `DocumentService` ne dépend plus seulement de poppler (`pdf2image`) mais aussi de pdfium : `page_sizes` (#352), lignes `:170-188`. S'y ajoute une résolution de chemin disque (`resolve_storage_path`, #359). Le paradoxe est nouveau : le port `PageRasterizer` existe désormais (`domain/ports.py:423`) avec son adaptateur `infra/page_raster.py:23`, qui fait exactement `convert_from_bytes` + PNG, mais `DocumentService.generate_preview` (`:159-168`) en duplique le code au lieu de l'utiliser. Le test d'architecture le reconnaît : `pdf2image` et `pypdfium2` y sont listés comme « migration candidates » (`tests/test_architecture.py:314`), et le contrôle sur les services document-agent exclut `document_service.py` parce qu'il « predates the port » (`tests/test_architecture.py:206-214`).
  2. *Conséquence PLAUSIBLE.* L'adaptateur `infra/page_text.py:7-9,21-24` explique que pdfium n'est pas thread-safe et prend le verrou partagé avec Docling. `DocumentService.page_sizes` ouvre pdfium sans ce verrou, depuis un thread de travail (`api/documents.py:216`), pendant que des analyses Docling peuvent tourner. Contourner le port fait perdre cette connaissance (impact à confirmer par l'audit 12).
  3. *Dépôts.* `VersionService` est typé sur `SqliteDocumentVersionRepository` et il n'existe aucun `DocumentVersionRepository` dans `domain/ports.py`. `StoreService` utilise des méthodes absentes du port `StoreRepository` (`domain/ports.py:128-139`) : `update` (`store_service.py:297`), `delete` (`:395`), `find_by_name` (`:214`), `clear_default_except` (`:233`), `set_connection_password` (`:303`), et `count_by_store` sur le dépôt des liens (`:163`). Les imports restent sous `TYPE_CHECKING` et l'injection se fait bien dans `bootstrap/`, donc aucun import runtime. Mais le contrat est celui de l'adaptateur, pas celui du domaine. Ce point est antérieur à 0.7.0 (blame de mai 2026) et n'avait pas été relevé. La partie stores relève de l'ingestion, dépréciée en 0.8.0.
- **Regle violee** : item 1.2.4 — « Les services reçoivent leurs dépendances par injection, pas par import direct de concrétions » (poids 2).
- **Remediation** :
  1. Injecter `PageRasterizer` dans `DocumentService` (`bootstrap/factories.py:219`) et supprimer `generate_preview`.
  2. Ajouter au port, ou créer, `page_sizes(storage_path)` et `page_count(...)` (p.ex. un port `PdfInspector`), implémentés dans `infra/` sous le verrou pdfium. Y migrer `analysis_service._count_pdf_pages`.
  3. Placer l'écriture et la suppression du fichier uploadé ainsi que `resolve_storage_path` derrière un port `FileStorage`.
  4. Retirer `pdf2image`/`pypdfium2` de `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` et les ajouter à `_SERVICES_FORBIDDEN_EXTERNALS`.
  5. Créer `DocumentVersionRepository` et compléter `StoreRepository`/`DocumentStoreLinkRepository`, puis typer les services sur ces ports. Le point 5 peut attendre 0.8.0 pour la partie stores, vouée au retrait.

### [MAJ] Couche HTTP qui orchestre : jointure de deux dépôts et I/O disque dans `api/documents.py`

- **Localisation** :
  - Dette 0.7.0, inchangée : `api/documents.py:40` (`_fetch_store_links`), appelé par `get_document` en `api/documents.py:111-122`, qui reçoit `link_repo`/`store_repo` via `api/deps.py:90-105`.
  - Nouveau en 0.7.3 : `api/documents.py:185-190` (preview) et `api/documents.py:212-216` (`GET /api/documents/{id}/pages`, #352) ; import de la classe concrète `api/documents.py:14` ; `api/analyses.py:84`.
- **Constat** :
  1. *Store-links.* Le routeur appelle toujours lui-même deux dépôts (`link_repo.find_for_document` `:52`, `store_repo.find_all` `:57`) puis fait la jointure `slug_by_id` (`:58`). Le code est identique à 0.7.0.
  2. *Preview et pages.* Les deux handlers font eux-mêmes la lecture disque : `service.resolve_storage_path(doc.storage_path).read_bytes` passé à `asyncio.to_thread`. Ils choisissent aussi de déporter le travail dans un thread, puis appellent des méthodes statiques de la **classe** `DocumentService` (`DocumentService.generate_preview` `:189`, `DocumentService.page_sizes` `:216`) au lieu de l'instance injectée. La validation métier de la plage de pages (`:176-180`) est également dans le routeur. Le cas d'usage « obtenir l'image ou les dimensions des pages d'un document » est donc découpé entre l'API et le service. La route `/pages` est nouvelle en 0.7.3 et reprend le schéma existant de `/preview` au lieu de le corriger.
  3. *Mineur.* `api/analyses.py:84` choisit entre 404 et 400 selon le préfixe du message d'erreur (`str(e).startswith("Document not found:")`) : le contrat d'erreur dépend du libellé produit par le service (#359).
  Note : l'item 1.3.1 reste conforme. Aucun import de `persistence/`, ce sont des ports.
- **Regle violee** : item 1.3.3 — « Les endpoints délèguent toute la logique aux services » (poids 2).
- **Remediation** :
  1. Créer `DocumentService.get_with_store_links(doc_id)`, avec injection des dépôts store et link, puis retirer `StoreRepoDep`/`DocumentStoreLinkRepoDep` des handlers.
  2. Créer `async DocumentService.render_preview(doc_id, page, dpi)` et `async DocumentService.page_sizes(doc_id)`. Ils portent la lecture du fichier (via le port de stockage), la validation de plage et le passage par `to_thread`. Le routeur ne fait plus que traduire les erreurs typées en codes HTTP.
  3. Lever une erreur typée `DocumentNotFoundError` pour l'import plutôt que d'analyser le message.

### [MIN] Les conversions snake_case → camelCase fuient toujours hors de `api/schemas.py`

- **Localisation** : `services/chunk_service.py:105-108` et `:858-861`, `services/analysis_service.py:47-51`, `services/version_service.py:53-62`. Côté consommateur : `api/analyses.py:174-180`.
- **Constat** : mêmes lignes qu'en 0.7.0. Les services construisent à la main des dicts au format du contrat front (`"sourcePage"`, `"tokenCount"`, `"docItems"`/`"selfRef"`, `"chunkId"`, `"documentId"`, `"createdAt"`). Le routeur relit ensuite ces clés camelCase pour reconstruire un `ChunkResponse` (`api/analyses.py:176-177`). Le mapping du format d'échange se fait donc en aller-retour entre les deux couches. À noter en positif : les nouveaux schémas MCP et de configuration restent confinés à `api/schemas.py` (`McpConfigResponse.from_view`, `McpServerResponse.from_status`) et à `mcp_adapter/wire.py`.
- **Regle violee** : item 1.3.2 — « Les transformations camelCase/snake_case restent dans `api/schemas.py` » (poids 1).
- **Remediation** : faire retourner des value objects (`ChunkResult`, `Chunk`) par les services et laisser l'`alias_generator` de `api/schemas.py` faire la conversion. Si besoin, garder le camelCase uniquement pour le format persisté (`chunks_json`), dans `persistence/`.

### [INFO] Les règles pytestarch du test d'architecture ne vérifient rien

- **Localisation** : `tests/test_architecture.py:178-193` (le docstring le reconnaît), `tests/test_architecture.py:277` (`TestPersistenceLayerIsolation`), à confronter à `persistence/store_repo.py:25`.
- **Constat** : le test le dit lui-même. Les règles pytestarch (`TestDomainLayerIsolation`, `TestServicesLayerIsolation`, `TestApiLayerIsolation`, `TestInfraLayerIsolation`, `TestPersistenceLayerIsolation`) ne voient aucune arête, parce que le dossier racine `document-parser` n'est pas un package importable : « adding `from persistence.database import get_connection` to a `services/` module leaves every rule green » (`:190-192`). La preuve est dans le code : `persistence/store_repo.py:25` importe `infra.secrets`, ce que la règle `persistence -> infra` interdit, et le test passe quand même. Seuls les contrôles par `ast` sont effectifs : `mcp_adapter`, services document-agent, librairies externes, convention de ports. Le docstring de tête (`:6-14`) annonce donc des garanties qui ne sont pas tenues. Ce point est hors barème (les `tests/` sont hors cible de la fiche).
- **Remediation** : remplacer les règles pytestarch par le scanner `ast` déjà utilisé pour `mcp_adapter` (`_collect_imports`), une règle par couche. Il faudra traiter ou consigner explicitement les écarts que cela fera apparaître, à commencer par `persistence -> infra`.

### [INFO] Couplage entre adaptateurs : `persistence` importe `infra` (inchangé)

- **Localisation** : `persistence/store_repo.py:25` (`from infra.secrets import get_fernet_box`).
- **Constat** : identique à 0.7.0. Ce chiffrement concerne les stores d'ingestion, dépréciés en 0.8.0.
- **Remediation** (facultatif) : un port `SecretBox`, ou laisser disparaître le code avec l'ingestion en 0.8.0.

### [INFO] Le domaine lit directement le schéma JSON de Docling, contrairement à ce qu'annonce son docstring

- **Localisation** : `domain/parse_index.py:3-6` (docstring) face à `domain/parse_index.py:86` (`self_ref`), `:115` et `:130-134` (`page_no`), `:173` (`coord_origin`) ; `domain/element_reader.py:85-86` (`children`/`$ref`/`cref`), `:156` (`captions`), `:195-199` (`data.grid`/`table_cells`).
- **Constat** : le docstring affirme « Every docling-shaped access goes through the injected `DocumentTreeReader` port ». En réalité le port ne fait que le parcours (`iter_items`, `dfs_order`, `iter_provs`, `iter_pages`), et le domaine lit lui-même les clés propres au format Docling. Les items 1.1.1 et 1.1.2 ne sont pas violés (pas d'import, pas d'I/O). En revanche, la couche anti-corruption n'est que partielle : un changement de schéma Docling, comme le passage à Docling Serve v1.37.0 dans cette release, se répercute directement dans le domaine.
- **Remediation** (facultatif) : faire normaliser les éléments en value objects par `DocumentTreeReader` (ref, label, text, provs, enfants, cellules), ou corriger le docstring pour décrire le compromis réel.

### [INFO] Valeurs de configuration lues hors de `infra/settings.py`

- **Localisation** : `infra/secrets/fernet_box.py:126` (`os.environ.get("STORE_SECRET_KEY")`, alors que `settings.store_secret_key` existe, `infra/settings.py:46`) ; `persistence/database.py:26` (`DB_PATH`) et `:249` (`DEFAULT_EMBEDDER`, absent de `Settings`) ; `mcp_stdio.py:44` (troisième copie du défaut `./data/docling_studio.db`, nouveau) ; `services/navigation_config.py:44-45` et `:52-54` (taille du cache d'index et budgets de raster codés en dur, non surchargeables, alors que le commentaire `:41-43` dit qu'un opérateur doit dimensionner son worker d'après eux).
- **Constat** : les trois premières lectures sont antérieures à 0.7.0 (blame d'avril-mai 2026) et étaient passées sous le grep de la fiche. `mcp_stdio.py` justifie la sienne : `persistence` et `settings` lisent `DB_PATH` à l'import (`:49-50`). La fiche ne contient pas de constantes d'URL ou d'hôte codées en dur dans `infra/`, donc 1.4.2 est jugé conforme, mais il y a désormais trois sources de vérité pour `DB_PATH`. En lecture stricte (« les valeurs de config viennent de `infra/settings.py` »), `fernet_box.py:126` rendrait l'item 1.4.2 non conforme : 23/32, soit 72.
- **Remediation** : faire lire `settings.store_secret_key` à `get_fernet_box` (en gardant une lecture paresseuse) et `settings.db_path` à `persistence/database.py`, et ajouter `default_embedder` à `Settings`. Exposer `index_cache_size`/`index_cache_max_chars` en variables d'environnement s'ils doivent vraiment être dimensionnés par l'opérateur.

### [INFO] Frontend : `shared/` dépend de `features/` et des pages font des imports profonds (hors barème)

- **Localisation** : `frontend/src/shared/ui/AppSidebar.vue:55-56` (`../../features/feature-flags/store`, `../../features/ingestion/store`) ; `frontend/src/pages/DocWorkspacePage.vue:62` (`../features/document/api`, avec `fetchDocumentPages`, nouveau en 0.7.3), plus 6 autres imports `pages/* -> features/*/api`. Fetch direct toujours présent dans `frontend/src/features/document/ui/DownloadDropdown.vue:133` (déjà en 0.7.0, alors à la ligne 131).
- **Constat** : la fiche 01 ne couvre pas le frontend. Côté positif, la nouvelle feature `mcp-config` est exemplaire (`ui -> store -> api -> @/shared/api/http`, accès croisé uniquement via le barrel `@/features/admin-config`), et aucun import profond entre features n'a été trouvé hors tests. En revanche, `shared/` importe des stores de features, ce qui inverse la dépendance attendue (antérieur, avril 2026). Les motifs de la règle ESLint (`'../../*/store'`, `eslint.config.js:33-49`) ne couvrent qu'un seul segment et ne détectent donc ni `../../features/<x>/store` depuis `shared/`, ni `../features/<x>/api` depuis `pages/`. Ce point relève surtout de l'audit 07.
- **Remediation** (facultatif) : ajouter des motifs `'**/features/*/store'`, `'**/features/*/api'` et `'**/features/*/ui/*'` (barrel uniquement). Faire passer `AppSidebar` par les barrels, ou injecter ses données depuis `app/`.

---

## Delta vs 0.7.0

**Score : 78 → 78 (Δ 0).** Mêmes 9/13 items conformes, mêmes 4 items non conformes (1.2.3, 1.2.4, 1.3.2, 1.3.3). La nature des écarts a toutefois évolué : les trois MAJ sont toujours ouverts, et deux d'entre eux se sont étendus avec du code nouveau.

| Écart 0.7.0 | Statut en 0.7.3 | Détail |
|-------------|-----------------|--------|
| [MAJ] split/merge dans `chunk_service`, `domain/chunk_editing.py` mort (1.2.3) | **Toujours présent, s'étend à du code nouveau** | Aucune ligne modifiée dans les deux fichiers depuis v0.7.0. Règles de citation et de lecture budgétée ajoutées dans `citation_service`/`navigation_service`. |
| [MAJ] librairies PDF hors port dans `document_service` / `analysis_service` (1.2.4) | **Toujours présent, aggravé** | + `pypdfium2` dans `document_service` (#352), + `resolve_storage_path` (#359). Le port `PageRasterizer` existe maintenant mais `generate_preview` ne l'utilise pas. Typage sur `Sqlite*Repository` relevé à cette occasion (antérieur à 0.7.0). |
| [MAJ] orchestration de 2 dépôts dans `api/documents.py` (1.3.3) | **Toujours présent, aggravé** | `_fetch_store_links` identique. La nouvelle route `/pages` (#352) reproduit le schéma de `/preview` (I/O disque et statique concret dans le routeur). |
| [MIN] camelCase dans les services (1.3.2) | **Toujours présent, inchangé** | Mêmes lignes. Les nouveaux contrats MCP et config respectent la règle. |
| [INFO] `persistence` → `infra.secrets` | **Toujours présent** | `persistence/store_repo.py:25`. Code d'ingestion, déprécié en 0.8.0. |
| [INFO] `DownloadDropdown.vue` `fetch()` direct | **Toujours présent** | Passé de la ligne 131 à la ligne 133. |

Nouveaux INFO 0.7.3 : règles pytestarch qui ne vérifient rien, schéma Docling lu dans le domaine, configuration lue hors `settings`, frontières frontend `shared`/`pages`.

---

## Points positifs

- **Domaine toujours pur malgré +11 modules.** Les nouveaux modules (`navigation`, `anchors`, `parse_index`, `element_reader`, `outline_builder`, `outline_locate`, `source_map`, `source_bar`, `page_regions`, `quote_marks`, `spans`, `mcp_config`) n'importent que la stdlib et `domain.*`, sans I/O ni Pydantic. Items 1.1.1 à 1.1.4 conformes.
- **Le serveur MCP respecte ports & adapters.** `mcp_adapter/` est un adaptateur primaire mince :
  - il n'importe que `services.*`, `domain.*`, le SDK `mcp` et `pydantic`, jamais `api`, `infra` ni `persistence` ;
  - c'est vérifié par un vrai contrôle `ast` (`tests/test_architecture.py:197-203`) ;
  - chaque outil se résume à résoudre le service, l'appeler, mapper vers `wire.py` puis `compact` (`mcp_adapter/server.py:126-200`) ;
  - le mapping vers le format d'échange est isolé dans `wire.py`/`wire_mapping.py`.
- **Ports ajoutés au bon endroit.**
  - Le rendu raster (`PageRasterizer`) et la lecture de la couche texte PDF (`PageTextReader`) sont portés pour les nouveaux services : `CitationImageService` et `SourceService` les reçoivent par injection (`bootstrap/factories.py:286-292`).
  - L'import d'analyses Docling (#359) passe par le port `DoclingDocumentImporter` (`domain/ports.py:86`, `infra/docling_importer.py:13`).
- **Configuration MCP exemplaire (#364).**
  - Les règles de validation sont dans le domaine (`domain/mcp_config.py:94-123`).
  - Le service orchestre la précédence base/env sans connaître infra ni le SDK : le rebuild est injecté par `apply_config`, la description par `status_provider` (`services/mcp_config_service.py:112-128`).
  - Le routeur `api/config.py` ne fait que mapper les DTO.
- **Composition root propre et dupliquée à dessein.** `bootstrap/builder.py:228-262` câble la config MCP comme celle du raisonnement. `mcp_stdio.py` est un second point d'entrée de composition, assumé et documenté, qui ne construit que les trois dépôts nécessaires. `bootstrap/mcp_mount.py` garde la transport security et le contrôle 503 hors des services.
- **Garde-fous ciblés et honnêtes.** `TestDocumentAgentServicesAreFrameworkFree` (`tests/test_architecture.py:206`) interdit PIL, pdf2image et fastapi dans les cinq services document-agent, avec une liste explicite des dépendances entre services. L'inventaire `_SERVICES_EXTERNAL_MIGRATION_CANDIDATES` rend visible la dette PDF au lieu de la masquer.
- **API sans persistence** (1.3.1) et **services sans framework ni SQL** (1.2.1, 1.2.2) : toujours conformes, y compris pour les nouveaux routeurs `api/mcp.py` et `api/config.py`.

---

## Verdict partiel : GO CONDITIONNEL

Aucun écart CRITICAL : les sept items de poids 3 (pureté du domaine, ports, sens des dépendances, adaptateurs) restent conformes, y compris pour tout le périmètre MCP. Le score de 78/100 est dans la plage 60-79. Il y a trois écarts MAJOR, ce qui ne déclenche pas à lui seul la règle « > 3 MAJ » pour cet audit.

Il faut noter que les trois MAJ sont **les mêmes qu'en 0.7.0**, qu'ils ont été reportés comme dette sans être traités, et que deux se sont étendus avec du code nouveau (#352, #359, services document-agent). Plan de remédiation recommandé, par ordre de rendement :

1. Injecter `PageRasterizer` dans `DocumentService` et créer un port d'inspection PDF (`page_sizes`/`page_count`) sous le verrou pdfium. Cela ferme l'essentiel de 1.2.4 et la question de thread-safety PLAUSIBLE (item 1.2.4).
2. Déplacer la lecture de fichier et la jointure store-links de `api/documents.py` vers `DocumentService` (item 1.3.3).
3. Brancher `ChunkService` sur `domain/chunk_editing.py` et extraire la correspondance de citations vers le domaine (item 1.2.3).
4. Rendre les règles pytestarch réellement vérifiantes, pour que ces frontières tiennent une fois corrigées (INFO).

# Rapport d'audit : SOLID

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code
**Commit HEAD** : `6aaf98f`
**Baseline** : `docs/audit/reports/release-0.6.2/06-solid.md` (100/100, 0/0/0/1, GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 ponderes) |
| Score | 100 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 4 |

**Delta vs 0.6.2** : 0 point (100 -> 100). La surface SOLID de 0.7.0 s'etend
(nouvelle couche `bootstrap/`, `ReasoningService`, ports `ReasoningRunner` /
`LLMProvider` / `LLMHostProbe` / `AppSettingsRepository`) tout en restant
integralement conforme aux 5 principes.

---

## Contexte

0.7.0 introduit le trace de reasoning v2 (#303) et la config runtime (#317).
Les changements structurants sur la surface SOLID :

- **Composition root extrait** de `main.py` vers `bootstrap/` :
  `AppStateBuilder` (`bootstrap/builder.py`) + les factories d'adaptateurs
  (`bootstrap/factories.py`), publiant un conteneur `AppState` typé et frozen
  (`api/state.py`).
- **`ReasoningService`** (`services/reasoning_service.py`) : nouvel orchestrateur
  de cas d'usage entre le router et le port `ReasoningRunner`.
- **Nouveaux ports** : `ReasoningRunner`, `LLMProvider`, `LLMHostProbe`,
  `AppSettingsRepository` (`domain/ports.py`), implantés côté infra par
  `DoclingAgentReasoningRunner`, `OllamaProvider`, `OllamaProbe`.

L'audit a ouvert et vérifié chaque fichier de la surface (ports, AppState/
AppStateBuilder, factories, les 10 services, les 2 converters, l'adaptateur de
reasoning, les adaptateurs Neo4j). Les commandes de vérification de la fiche ont
été rejouées sur le working tree HEAD.

---

## Verification des principes

### SRP (6.1)

- **6.1.1 & 6.1.4 conforme** — chaque service porte une responsabilité de cas
  d'usage unique et ne cumule ni parsing-brut ni persistence : tout passe par
  des ports / repos injectés. `ReasoningService` (`services/reasoning_service.py:63`)
  se limite au séquencement d'un run (valider la query, résoudre la dernière
  analyse, chronométrer, projeter via `domain.trace_builder`) et n'importe pas
  `infra/`.

  | Service | Responsabilité unique |
  |---------|-----------------------|
  | `AnalysisService` | Pipeline d'analyse Docling |
  | `AppConfigService` | Config runtime reasoning (env + override SQLite) |
  | `ChunkService` | CRUD chunks first-class + audit trail |
  | `DocumentService` | CRUD documents |
  | `ExportService` | Export document (pdf / md / json) |
  | `GraphService` | Orchestration `/graph` |
  | `IngestionService` | Embed + push vector + graph |
  | `ReasoningService` | Séquencement d'un run de reasoning |
  | `StoreBackendResolver` | `Store` -> `IngestionTargets` |
  | `StoreService` | CRUD stores + test_connection |
  | `VersionService` | Snapshots (analyse, chunks) |

- **6.1.2 conforme** — 11 stores Pinia (`frontend/src/features/*/store.ts`),
  un `defineStore` distinct par feature (admin-config, analysis, chunking,
  chunks, document, feature-flags, history, ingestion, reasoning, search,
  settings) ; aucune feature ne porte deux stores.
- **6.1.3 conforme** — routers REST groupés par ressource
  (`api/documents.py`, `api/analyses.py`, `api/document_chunks.py`,
  `api/document_versions.py`, `api/stores.py`, `api/graph.py`,
  `api/ingestion.py`, `api/reasoning.py`, `api/config.py`).

### OCP (6.2)

- **6.2.1 conforme** — les ports sont des `Protocol` (`domain/ports.py`) :
  ajouter un adaptateur (nouveau converter, nouveau `LLMProvider`) se fait sans
  toucher le code existant, la liaison vivant dans `bootstrap/factories.py`.
- **6.2.2 conforme** — la sélection local/remote est centralisée dans
  `build_converter()` (`bootstrap/factories.py:36`) ; `AnalysisService` consomme
  le port `DocumentConverter` et ne connaît ni `LocalConverter` ni
  `ServeConverter`. (La fiche cite `_build_converter()` ; le mécanisme existe
  sous le nom public `build_converter()`.)
- **6.2.3 conforme** — l'endpoint `export_document` (`api/documents.py:135`) ne
  reçoit que l'enum `ExportFormat` ; ajouter un format n'impacte pas le handler.

### LSP (6.3)

- **6.3.1 conforme (poids 3)** — `LocalConverter` (`infra/local_converter.py:281`)
  et `ServeConverter` (`infra/serve_converter.py:70`) exposent le même contrat :
  `convert(...) -> ConversionResult` + `supports_page_batching`.
  `ConversionResult.document_json` est `str | None`
  (`domain/value_objects.py:125`) : le `None` que `ServeConverter` peut renvoyer
  (`infra/serve_converter.py:252`) est prévu par le contrat et géré côté appelant
  (`services/analysis_service.py:434`, `:506`). Substituabilité vérifiée.
- **6.3.2 conforme** — `DoclingAgentReasoningRunner` traduit bien les échecs
  amont en `ReasoningParseError` comme l'exige le contrat du port
  (`infra/docling_agent_reasoning.py:195` et `:214`) ; les autres exceptions
  remontent telles quelles vers le mapping HTTP du router.
- **6.3.3 conforme** — aucun `isinstance()` / `type()` de dispatch entre
  implémentations dans `services/`. Les rares `isinstance`
  (`services/store_service.py:135,139`, `services/chunk_service.py:218`) valident
  des types primitifs (str / list) de payloads, pas des adaptateurs.

### ISP (6.4)

- **6.4.1 conforme** — `DocumentConverter` (`domain/ports.py:53`) et
  `DocumentChunker` (`domain/ports.py:78`) sont deux ports distincts ; idem pour
  la ségrégation lecture/écriture graphe `GraphReader` / `GraphWriter`
  (`domain/ports.py:376,388`).
- **6.4.2 conforme** — aucun adaptateur n'est forcé de stubber une méthode
  inutilisée : `Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py:37`) implémente
  réellement `write_document_tree`, `write_chunks` et `ping` (pas de
  `NotImplementedError`). Le `NotImplementedError` évoqué dans la docstring du
  port reste une consigne pour d'hypothétiques futurs adaptateurs.

### DIP (6.5)

- **6.5.1 conforme (poids 3)** — les services dépendent de protocoles :
  `ReasoningService.__init__` prend `runner: ReasoningRunner`
  (`services/reasoning_service.py:66`) ; grep `from infra.` sur `services/` ne
  ramène que des imports sous `TYPE_CHECKING`
  (`services/store_backend_resolver.py:40-42`), jamais du runtime.
- **6.5.2 conforme** — l'injection est centralisée dans le composition root
  `bootstrap.AppStateBuilder` (`bootstrap/builder.py:84`), invoqué depuis le
  lifespan de `main.py` (`main.py:49-50`). Le câblage post-construction
  (`set_chunk_promoter`, `set_version_recorder`) reste dans le builder
  (`bootstrap/builder.py:123,126`), pas dans les services.
- **6.5.3 conforme (poids 3)** — grep `LocalConverter|ServeConverter|LocalChunker`
  sur `services/` : zéro occurrence. Aucun service n'instancie d'adaptateur ; les
  liaisons infra sont injectées en factory (`graph_writer_factory` de
  `StoreBackendResolver`, `apply_config` / `probe` / `diagnostics_provider` de
  `AppConfigService`).

---

## Ecarts constates

### [INFO] `supports_page_batching` : `@property` au port, attribut de classe aux adaptateurs
- **Localisation** : `document-parser/domain/ports.py:69` (déclaré `@property`) vs
  `document-parser/infra/local_converter.py:286` et
  `document-parser/infra/serve_converter.py:76` (attribut de classe `bool`).
- **Constat** : le port `DocumentConverter` déclare `supports_page_batching` en
  `@property`, les deux adaptateurs l'implémentent en variable de classe. Le site
  d'appel (`services/analysis_service.py:415`) lit l'attribut par duck-typing,
  donc aucune rupture à l'exécution — seulement une divergence de forme entre le
  contrat déclaré et son implémentation.
- **Regle** : 6.3.1 (même protocole).
- **Remediation** : optionnel — homogénéiser (exposer une `@property` côté
  adaptateurs, ou typer le membre du protocole en attribut) pour aligner forme et
  contrat.

### [INFO] `ServeConverter.health_check()` : méthode orpheline, asymétrique entre adaptateurs
- **Localisation** : `document-parser/infra/serve_converter.py:183`.
- **Constat** : `ServeConverter` porte `health_check()`, absente du port
  `DocumentConverter` (`domain/ports.py:53`) et de `LocalConverter`. Aucun
  appelant ne l'invoque via le port (grep `health_check` sur `api/`, `services/`,
  `bootstrap/`, `main.py` : nul). Pas de risque de substituabilité (rien ne
  l'appelle sur un `DocumentConverter` générique), mais c'est une asymétrie /
  méthode morte.
- **Regle** : 6.4.2 (pas de méthode superflue) / 6.3.1.
- **Remediation** : supprimer la méthode inutilisée, ou la promouvoir dans le
  port si un health-check de converter devient un besoin réel.

### [INFO] Composition root déplacé de `main.py` vers `bootstrap/`
- **Localisation** : `document-parser/bootstrap/builder.py:62`,
  `document-parser/bootstrap/factories.py`, invoqués par
  `document-parser/main.py:49-50`.
- **Constat** : l'item 6.5.2 est libellé « l'injection se fait dans `main.py` ».
  Depuis 0.7.0 l'injection vit dans `bootstrap.AppStateBuilder`, appelé par le
  lifespan de `main.py`. C'est une évolution intentionnelle et documentée (un
  composition root unique, typé et frozen), pleinement conforme à l'esprit du
  principe — signalé pour tracer l'écart au libellé de la fiche.
- **Regle** : 6.5.2 (injection au composition root).
- **Remediation** : mettre à jour le libellé de `06-solid.md` (6.5.2) pour citer
  `bootstrap/` comme composition root en plus de `main.py`.

### [INFO] `AnalysisService` : méthodes legacy d'édition du blob `chunks_json`
- **Localisation** : `document-parser/services/analysis_service.py:206`
  (`update_chunk_text`), `:228` (`delete_chunk`), `:182` (`rechunk`).
- **Constat** : `AnalysisService` (554 lignes) conserve des méthodes d'édition du
  payload legacy `analysis.chunks_json` qui recoupent le domaine de
  `ChunkService` (chunks first-class #205). La responsabilité centrale du service
  reste « cas d'usage d'analyse » (6.1.1 conforme), mais ces méthodes sont des
  candidates naturelles à extraction / dépréciation.
- **Regle** : 6.1.1 (responsabilité unique) — observation de largeur, pas une
  violation.
- **Remediation** : à traiter côté Clean Code / dette (audit 03) — déprécier les
  éditions de blob au profit de `ChunkService` une fois les appelants migrés.

---

## Points positifs

- **Ports bien pensés et documentés** : `ReasoningRunner` déclare explicitement
  son contrat d'exceptions (traduction obligatoire vers `ReasoningParseError`,
  `domain/ports.py:426`), et l'adaptateur le respecte à la lettre
  (`infra/docling_agent_reasoning.py:195,214`) — DIP + LSP exemplaires.
- **`AppState` typé et frozen** (`api/state.py:48`) : remplace l'`app.state`
  non typé de FastAPI ; le rewiring runtime (#317) passe par un
  `dataclasses.replace` atomique (`bootstrap/builder.py:78`) plutôt qu'une série
  d'écritures dispersées.
- **DIP tenu jusqu'au bout** : les services qui ont besoin d'un adaptateur le
  reçoivent en factory injectée (`graph_writer_factory` dans
  `StoreBackendResolver`, `apply_config` / `probe` / `diagnostics_provider` dans
  `AppConfigService`) — `services/` n'importe jamais `infra/` au runtime.
- **Ségrégation lecture/écriture du graphe** (`GraphReader` / `GraphWriter`)
  et séparation nette `DocumentConverter` / `DocumentChunker` : ISP respecté
  sans god-interface.
- **`build_reasoning_runner`** (`bootstrap/factories.py:79`) gère l'extensibilité
  provider de façon fermée-à-la-modification : un provider non supporté tombe sur
  un warning + `None`, l'app boote proprement.

---

## Verdict partiel : GO

Score 100/100, 0 CRITICAL, 0 MAJOR, 0 MINOR. Les 4 INFO sont des observations
sans risque de release (une divergence de forme port/adaptateur, une méthode
morte, un écart de libellé de fiche, une piste de refactor legacy). Les 5
principes SOLID sont intégralement respectés sur toute la surface backend de
0.7.0, y compris les nouveaux composants (bootstrap, ReasoningService, ports de
reasoning / config).

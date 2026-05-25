# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 (poids 9 / 12) |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 2 |

---

## Suivi des ecarts de la release 0.5.0

| Ecart 0.5.0 | Statut 0.6.1 |
|-------------|--------------|
| [MAJ] Magic API URL hardcoded `frontend/src/features/settings/store.ts:23` | **RESOLU** — `apiFetch` ne prend que des chemins relatifs (`/api/...`), aucun localhost en front (sauf placeholder UI dans `StoreForm.vue:298`, voir MIN ci-dessous). |
| [MAJ] localStorage keys non centralisees `store.ts:24-27` | **RESOLU** — extraites dans `frontend/src/shared/storage/keys.ts` (`STORAGE_KEYS.theme`, `.locale`), consommees par `features/settings/store.ts:24-31`. |
| [MIN] Magic string `"uploaded"` en backend `document-parser/api/schemas.py:49` | **RESOLU** — constante nommee `DOCUMENT_STATUS_UPLOADED` declaree `schemas.py:16`, utilisee `schemas.py:80`. |
| [INFO] `table_mode` / `chunker_type` litteraux dupliques | **PERSISTE** — non corrige (voir MIN ci-dessous). |
| [INFO] Logique de polling dupliquee | **AGGRAVEE** — 3 occurrences au lieu de 2 (voir MIN ci-dessous). |

---

## Ecarts constates

### [MIN] Litteraux `table_mode` / `chunker_type` non centralises

- **Localisation** :
  - `document-parser/api/schemas.py:124` (`default="accurate"`), `schemas.py:154` (`("accurate", "fast")`)
  - `document-parser/api/schemas.py:172` (`default="hybrid"`), `schemas.py:185` (`("hybrid", "hierarchical")`)
  - `document-parser/domain/value_objects.py:103` (`table_mode: str = "accurate"`), `value_objects.py:129` (`chunker_type: str = "hybrid"`)
  - `document-parser/infra/settings.py:20` (`default_table_mode: str = "accurate"`), `settings.py:113` (`not in ("accurate", "fast")`), `settings.py:149` (env-default)
  - `document-parser/infra/local_converter.py:91` (`options.table_mode == "accurate"`)
  - `document-parser/infra/local_chunker.py:88` (`options.chunker_type == "hierarchical"`)
- **Constat** : Les memes ensembles de valeurs valides apparaissent en 6+ fichiers. L'INFO recommande dans le rapport 0.5.0 (creer `domain/constants.py`) n'a pas ete realise. Un typo dans l'un des 6 endroits passerait silencieusement les validateurs Pydantic mais casserait `local_converter.py:91` (fallback `FAST`).
- **Regle violee** : Item 5.3 (poids 2) — Les magic strings doivent etre nommees et centralisees.
- **Severite** : MIN (et non MAJ) car la validation Pydantic centralisee garantit la coherence au runtime de l'API. La duplication reste un risque de drift latent.
- **Remediation** : Creer `document-parser/domain/constants.py` avec `TABLE_MODES = ("accurate", "fast")`, `CHUNKER_TYPES = ("hybrid", "hierarchical")`, et constantes `TABLE_MODE_DEFAULT`, `CHUNKER_TYPE_DEFAULT`. Importer dans `api/schemas.py`, `domain/value_objects.py`, `infra/settings.py`, `infra/local_converter.py`, `infra/local_chunker.py`.

### [MIN] Logique de polling dupliquee dans 3 stores/pages

- **Localisation** :
  - `frontend/src/features/analysis/store.ts:69-112` (setInterval 2s + retry 3x + timeout 15min)
  - `frontend/src/features/ingestion/store.ts:16-39` (setInterval recurrent, intervalle parametrable)
  - `frontend/src/pages/ReasoningPage.vue:113-127` (setInterval 500ms wait-until-idle + timeout 10min)
- **Constat** : Trois implementations independantes du pattern `setInterval` + `clearInterval` + gestion de timeout. La structure (timer ref, start/stop, timeout) est identique meme si les politiques (retry, intervalle, condition d'arret) different. C'etait deja un INFO en 0.5.0 ; une troisieme occurrence est apparue dans `ReasoningPage.vue` en 0.6.1.
- **Regle violee** : Item 5.4 (poids 1) — La logique reactive partagee devrait etre dans `shared/composables/`.
- **Remediation** : Extraire `usePoller(fn, { intervalMs, timeoutMs, maxRetries, until })` dans `frontend/src/shared/composables/usePoller.ts`. Les 3 callsites se ramenent a un appel parameter. Beneficie aussi a 5.4 (test unitaire centralise du teardown).

### [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE`

- **Localisation** :
  - `document-parser/api/documents.py:19` (`_READ_CHUNK_SIZE = 64 * 1024`)
  - `document-parser/services/document_service.py:25` (`_UPLOAD_CHUNK_SIZE = 64 * 1024`)
- **Constat** : Memes valeurs (`64 KB`), meme concept (streaming de fichier), nommees differemment dans deux modules. Le router lit en `64KB`, le service ecrit en `64KB` — un changement de l'un sans l'autre serait silencieux.
- **Regle violee** : Item 5.3 (poids 2) — Constantes liees a la meme operation (upload streaming) devraient pointer vers la meme source.
- **Severite** : INFO car les deux constantes sont module-private (`_` prefixe) et chacune sert un cas distinct (lecture multipart cote API vs ecriture disque cote service). Pas de risque immediat, mais drift possible.
- **Remediation** : Promouvoir `FILE_STREAM_CHUNK_SIZE = 64 * 1024` dans `document-parser/domain/constants.py` (ou `services/constants.py`) et l'importer dans les deux fichiers.

### [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue`

- **Localisation** : `frontend/src/features/store/ui/StoreForm.vue:298` (`'bolt://localhost:7687'`, `'http://localhost:9200'`)
- **Constat** : Deux placeholders d'input (Neo4j / OpenSearch) en dur dans le template. Ne fuient pas dans le runtime (ce sont des hints visuels, pas des valeurs par defaut) mais constituent neanmoins des magic strings non centralisees. Les schemes correspondants sont deja dans `connectionForm.logic.ts:10-19` (`NEO4J_URI_SCHEMES`, `OPENSEARCH_URI_SCHEMES`).
- **Regle violee** : Item 5.3 (poids 2) — magic strings non nommees.
- **Severite** : INFO (placeholders d'UI, aucun impact metier).
- **Remediation** : Exporter `NEO4J_URI_PLACEHOLDER = 'bolt://localhost:7687'` et `OPENSEARCH_URI_PLACEHOLDER = 'http://localhost:9200'` depuis `connectionForm.logic.ts`, importer dans `StoreForm.vue`.

---

## Points positifs

- Les 2 MAJ et le MIN du rapport 0.5.0 sont **tous resolus** (`STORAGE_KEYS`, `DOCUMENT_STATUS_UPLOADED`, suppression du localhost frontend).
- Centralisation HTTP exemplaire : `frontend/src/shared/api/http.ts` est le **seul** point d'appel `fetch(...)` en frontend (verifie par `grep -rn "fetch(" frontend/src/ --include="*.ts" --include="*.vue" | grep -v "http.ts"` → 0 resultat).
- `STORAGE_KEYS` (`frontend/src/shared/storage/keys.ts`) parfaitement DRY : 1 declaration, type `as const`, type derive `StorageKey`.
- Enums backend bien factorises : `DocumentLifecycleState`, `StoreKind`, `DocumentStoreLinkState`, `ChunkEditAction`, `AnalysisStatus`, `LLMProviderType` (`domain/value_objects.py`, `domain/models.py`) — aucune duplication des labels.
- Types frontend equivalents declares en union litteraux dans `frontend/src/shared/types.ts:13-17,57,182` — type-safe par construction (toute typo casse `vue-tsc`).
- Validation centralisee URI/passwords (`features/store/ui/connectionForm.logic.ts`) : 1 module pur, 2 callsites (`StoreForm.vue`), testable sans DOM.
- Schemas Pydantic ne dupliquent pas les modeles : `_CamelModel` + `AliasChoices` font la transformation ; les dataclasses de `domain/value_objects.py` restent pures.
- Queries SQL partagees : `_SELECT_WITH_DOC` (`persistence/analysis_repo.py`) reutilisee 5 fois (confirme par `grep -c "_SELECT_WITH" persistence/analysis_repo.py`).
- Helpers `_to_response` correctement scopes par-router (`api/documents.py`, `api/stores.py`, `api/document_chunks.py`) — chaque routeur possede son mapping, pas de cross-coupling.

---

## Verdict partiel : GO CONDITIONNEL

**Justification** :
- Score 75 / 100 (seuil GO: 80) → en-dessous de GO mais zero CRITICAL et zero MAJOR.
- Les deux MAJ du cycle precedent ont ete remedies — la dette MAJ DRY est purgee.
- Les 2 MIN restants ciblent des constantes domaine (`table_mode` / `chunker_type`) et un pattern reactif (`usePoller`) qui peuvent etre traites dans le prochain cycle sans risque immediat.
- Les 2 INFO sont des nice-to-have (placeholders d'UI, naming d'une constante de buffer).

**Conditions pour GO inconditionnel (prochain cycle)** :
1. Creer `document-parser/domain/constants.py` pour centraliser `TABLE_MODES`, `CHUNKER_TYPES` (+ valeurs par defaut) et reduire le risque de drift entre `api/schemas.py`, `domain/value_objects.py` et `infra/settings.py`.
2. Extraire `usePoller` dans `frontend/src/shared/composables/usePoller.ts` pour resorber la duplication entre `features/analysis/store.ts`, `features/ingestion/store.ts` et `pages/ReasoningPage.vue`.

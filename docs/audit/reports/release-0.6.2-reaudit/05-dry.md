# Rapport d'audit : DRY (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/05-dry.md` — 75/100, GO CONDITIONNEL (0 CRIT / 0 MAJ / 2 MIN / 3 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 (poids 9 / 12) |
| Score | **75 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 4 |

### Detail par item (fiche `docs/audit/audits/05-dry.md`)

| # | Item | Poids | Statut | Delta vs baseline |
|---|------|-------|--------|-------------------|
| 5.1 | Aucun bloc 3+ fois sans factorisation | 2 | OK | = |
| 5.2 | Types partages centralises | 2 | OK | = |
| 5.3 | Pas de magic numbers / magic strings | 2 | **KO** (MIN herite) | = |
| 5.4 | Composables partages | 1 | **KO** (MIN herite) | = |
| 5.5 | Centralisation HTTP | 2 | OK | = |
| 5.6 | Schemas Pydantic != domain | 2 | OK | = |
| 5.7 | Validation a un seul endroit | 1 | OK | = |

**Calcul** (formule ponderee master.md §3) : poids conformes (2+2+2+2+1) = 9 / 12 × 100 = 75,00 → **75 / 100**. Identique au baseline.

---

## Contexte du re-audit

La fenetre `fix/0.6.2-audit-blockers` (8 commits depuis `release/0.6.2 @ 051ac4a`) cible les blockers tour 1 (CI/Securite/Docs). Le diff backend applicatif est ZERO ligne :

```bash
$ git diff release/0.6.2..HEAD -- document-parser/api/ document-parser/services/ \
    document-parser/domain/ document-parser/infra/ document-parser/persistence/ \
    document-parser/main.py
# 0 ligne
```

Aucun des 5 sites identifies par le baseline (litteraux `table_mode`/`chunker_type`, polling stores, `_READ_CHUNK_SIZE`, placeholders URI `StoreForm.vue`, helpers Cytoscape) n'est touche par la fenetre — leur statut est mecaniquement conserve.

Les surfaces effectivement modifiees par la fenetre, pertinentes pour DRY :

| Element | Type | Impact DRY |
|---------|------|------------|
| `dd1962e` — service `docling-serve` ajoute a `docker-compose.yml` ET `docker-compose.dev.yml` | Compose | Bloc de service quasi-identique x2 — voir analyse |
| `f6b4e23` — `Dockerfile:72-111` et `document-parser/Dockerfile:47-87` : commentaire + `ARG BAKE_MODELS=false` + `RUN if` identiques | Build infra | Gating bake quasi-copie-colle x2 — voir analyse |
| `f6b4e23` — defauts `BAKE_MODELS=${BAKE_MODELS:-false}` + `BAKE_MODEL=${BAKE_MODEL:-false}` dans les deux compose | Compose | Memes defauts ENV duplicques |
| `f6b4e23` — `docs/architecture/huggingface-dependency-map.md` (120 lignes) | Doc | Consolide la rationale HF en un point unique (positif DRY doc) |
| `29ab575` — `tests/test_chunking.py::test_rechunk_with_serve_document_json` mock AsyncMock | Tests | Hors cible audit |

---

## Suivi des ecarts du baseline 0.6.2

| Ecart 0.6.2 | Statut a `f6b4e23` |
|-------------|---------------------|
| [MIN] Litteraux `table_mode` / `chunker_type` non centralises | **PERSISTE** — `document-parser/domain/` n'a toujours pas de `constants.py`. Les 9 sites identifies au baseline sont strictement les memes : `api/schemas.py:124,155,172,186`, `domain/value_objects.py:104,130`, `infra/settings.py:20,113,149`, `infra/local_converter.py:91`, `infra/local_chunker.py:88`, `services/analysis_service.py:74`. (`infra/serve_converter.py:155` reprend `options.table_mode` sans litteral — passthrough.) |
| [MIN] Polling duplique dans 3 stores/pages | **PERSISTE** — `frontend/src/shared/composables/` contient toujours uniquement `usePagination.{ts,test.ts}`. Sites inchanges : `features/analysis/store.ts:11,12,72,94`, `features/ingestion/store.ts:16,31,59`, `pages/ReasoningPage.vue:117`. |
| [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE` (`64 * 1024`) | **PERSISTE** — `api/documents.py:19`, `services/document_service.py:26` inchanges. |
| [INFO] Placeholders d'URL hardcodes dans `StoreForm.vue` | **PERSISTE** — `frontend/src/features/store/ui/StoreForm.vue:297-299` inchanges. |
| [INFO] Helpers Cytoscape dupliques `_element_node` / `_page_node` (`infra/docling_graph.py` / `infra/neo4j/queries.py`) | **PERSISTE** — sites inchanges (32-73 / 88-134). |

Aucun ecart resorbe. Le contenu des MIN/INFO baselines est conserve mot pour mot.

---

## Verifications terrain a HEAD `f6b4e23`

```bash
# 5.3 — Litteraux table_mode / chunker_type backend
$ grep -rn 'table_mode\|chunker_type' document-parser/{api,domain,infra,services} \
    --include="*.py" | grep -v tests | wc -l
# 14 hits (3 dans serve_converter.py = passthroughs, 11 reels) — strictement identique au baseline

# 5.4 — composables shared
$ ls frontend/src/shared/composables/
# usePagination.test.ts  usePagination.ts   (pas de usePoller.ts)

# 5.4 — sites de polling (setInterval) dans stores + pages
$ grep -rn 'setInterval' frontend/src --include="*.ts" --include="*.vue"
# frontend/src/features/analysis/store.ts:11,72
# frontend/src/features/ingestion/store.ts:16,31
# frontend/src/pages/ReasoningPage.vue:117
# (memes 3 sites)

# 5.5 — fetch hors http.ts
$ grep -rn 'fetch(' frontend/src --include="*.ts" --include="*.vue" | grep -v 'http.ts\|node_modules'
# 0 hit
```

---

## Analyse des nouvelles surfaces

### Service `docling-serve` ajoute aux deux compose (dd1962e)

`docker-compose.yml:110-124` et `docker-compose.dev.yml:96-110` partagent :
- meme image pinnee `quay.io/docling-project/docling-serve-cpu:v1.21.0`
- meme `profiles: ["remote"]`
- meme healthcheck (`curl -sf http://localhost:5001/version`, intervalle/timeout/retries/start_period identiques)
- meme `deploy.resources.limits.memory: 4g`
- meme commentaire de rationale (le dev renvoie a la version prod : `Same opt-in pattern as docker-compose.yml — see that file for the full rationale`)

**Difference unique** : exposition reseau — `expose: ["5001"]` (prod, port interne au reseau Docker) vs `ports: ["5001:5001"]` (dev, port mappe sur l'hote pour debug curl direct).

Question DRY : est-ce un nouveau ecart MIN ?

Reponse : NON. Raisons :
1. La duplication compose `prod` vs `dev` est **un pattern structurel deja en place** : `neo4j`, `opensearch`, `embedding`, `document-parser` apparaissent deja deux fois dans les deux fichiers (~150 lignes redondantes). Le baseline 05 n'a jamais flag cette duplication, signe d'une convention acceptee dans le projet (les deux fichiers servent deux scenarios distincts et la factorisation via `extends:` / fichier override ne paie pas la complexite). L'ajout `docling-serve` suit la convention, ne l'aggrave pas de facon disproportionnee.
2. La difference `expose` / `ports` est **semantique, pas cosmetique** : c'est exactement ce qui distingue les deux fichiers — prod isole le service derriere le reseau interne, dev l'expose pour iteration locale. Une factorisation forcee qui supprimerait cette difference serait une regression de clarte.
3. Le commentaire dev renvoie explicitement au prod (`Same opt-in pattern as docker-compose.yml — see that file for the full rationale`) — la rationale n'est pas dupliquee, le service oui mais avec intention.

**Surface acceptable.** Pas de nouvel ecart formel ; signale en INFO pour tracabilite.

### Gating `BAKE_MODELS` dupliquue entre `Dockerfile` et `document-parser/Dockerfile` (f6b4e23)

Les deux Dockerfiles, qui coexistent intentionnellement (single-image full-stack `Dockerfile` racine + backend-only `document-parser/Dockerfile` pour scenarios microservice), repetent **mot pour mot** :

```dockerfile
# 8 lignes de commentaire identique :
#   Pre-fetch the Docling model checkpoints into the image so the very
#   first /api/convert is instant ...
#   Default is `false` so no build ever depends on HuggingFace Hub by
#   accident. `release.yml` flips this to `true` only when publishing
#   the `latest-local` end-user image (single sanctioned HF touch point
#   for the project — see docs/architecture/huggingface-dependency-map.md).
ARG BAKE_MODELS=false
ARG WITH_REASONING=false
# ...
RUN if [ "$WITH_REASONING" = "true" ]; then \
        uv sync --frozen --no-dev --group local --group reasoning; \
    else \
        uv sync --frozen --no-dev --group local; \
    fi

RUN if [ "$BAKE_MODELS" = "true" ]; then \
        mkdir -p /home/appuser/.cache/docling \
        && docling-tools models download \
             --output-dir /home/appuser/.cache/docling/models --quiet \
        && chown -R appuser:appuser /home/appuser/.cache; \
    fi
```

Aux differences pres :
- ordre `USER root` / `USER appuser` (le backend-only re-toggle, le single-image laisse `appuser` final)
- commentaire de `tool.uv.sources` reference `document-parser/pyproject.toml` (single-image) vs `pyproject.toml` (backend-only) — meme contenu, chemin different

C'est une copie-colle infra explicite, et le diff `release/0.6.2..f6b4e23` montre les **memes 16 lignes ajoutees/modifiees a chaque fichier** (`Dockerfile | 16 +-`, `document-parser/Dockerfile | 16 +-`).

Severite : **INFO**, pas MIN. Raisons :
1. Dockerfile multi-stage Docker n'a pas de mecanisme natif de factorisation entre fichiers (pas d'`include`, les `--from=` sont cross-stage pas cross-file). La seule factorisation reelle serait via un script shell genere ou un dockerfile template — sur-ingenierie pour 20 lignes.
2. Le risque de drift est reel mais detecte : un `docling-tools models download` qui evoluerait dans un seul fichier produirait des images divergentes, attrapees par les tests d'image au CI. Pas un risque silencieux.
3. La doc `docs/architecture/huggingface-dependency-map.md` ajoutee par `f6b4e23` consolide la rationale **une fois**, citee par les deux Dockerfiles — la duplication portee par les commentaires de tete est en partie compensee par le pointeur unique vers la doc.

Ajout d'un nouveau INFO **non bloquant**, voir section dediee.

### Defauts ENV `BAKE_MODELS=${BAKE_MODELS:-false}` dans les deux compose

`docker-compose.yml:142` et `docker-compose.dev.yml:119` : meme expression. Idem pour `BAKE_MODEL` (embedding) lignes 81 et 76. C'est une consequence directe du point precedent (duplication compose acceptee). Pas d'ecart formel — signale au sein du meme INFO.

### Doc `huggingface-dependency-map.md` (positif DRY)

Le commit `f6b4e23` introduit 120 lignes documentaires consolidant en **un seul endroit** : (a) la liste des touch points HF Hub sanctionnes, (b) la matrice runtime/build des dependances, (c) la procedure pour mirror HF / desactiver bake. Avant ce commit, la rationale etait eparpillee dans les `README.md`, le `CHANGELOG.md`, et inline dans les Dockerfiles. C'est une amelioration DRY (factorisation de connaissance) — pas un ecart, point positif documente plus bas.

---

## Ecarts constates

### [MIN] Litteraux `table_mode` / `chunker_type` non centralises (herite baseline)

- **Localisation** (inchangee) :
  - `document-parser/api/schemas.py:124` (`default="accurate"`), `:155` (`("accurate", "fast")`)
  - `document-parser/api/schemas.py:172` (`default="hybrid"`), `:186` (`("hybrid", "hierarchical")`)
  - `document-parser/domain/value_objects.py:104` (`table_mode: str = "accurate"`), `:130` (`chunker_type: str = "hybrid"`)
  - `document-parser/infra/settings.py:20,113,149`
  - `document-parser/infra/local_converter.py:91` (`options.table_mode == "accurate"`)
  - `document-parser/infra/local_chunker.py:88` (`options.chunker_type == "hierarchical"`)
  - `document-parser/services/analysis_service.py:74` (`default_table_mode: str = "accurate"`)
- **Constat** : Statu quo strict vs baseline. Le diff `release/0.6.2..f6b4e23` ne touche aucun de ces fichiers (`document-parser/{api,domain,infra,services}/` est a 0 ligne dans la fenetre).
- **Regle violee** : Item 5.3 (poids 2).
- **Remediation** : reportable au prochain cycle — creer `document-parser/domain/constants.py` (`TABLE_MODES = ("accurate", "fast")`, `CHUNKER_TYPES = ("hybrid", "hierarchical")`, defauts associes), importer dans les 9 sites. Idealement migrer vers `Literal[...]` ou `StrEnum`.

### [MIN] Logique de polling dupliquee dans 3 stores/pages (herite baseline)

- **Localisation** (inchangee) :
  - `frontend/src/features/analysis/store.ts:72` (`setInterval` 2 s) + `:94` (`setTimeout` retry/timeout)
  - `frontend/src/features/ingestion/store.ts:31` (`setInterval(checkAvailability, intervalMs)`)
  - `frontend/src/pages/ReasoningPage.vue:117` (`window.setInterval` 500 ms, timeout `Date.now() - started > timeoutMs` ligne 121+)
- **Constat** : Inchange. `frontend/src/shared/composables/` ne contient que `usePagination.{ts,test.ts}`. Aucun `usePoller` ajoute par la fenetre de fix (frontend non touche).
- **Regle violee** : Item 5.4 (poids 1).
- **Remediation** : extraire `useAsyncPoller(fn, { intervalMs, timeoutMs, maxRetries, until })` dans `shared/composables/usePoller.ts`. Les 3 sites se reduisent a un appel parametre. Couvrir Vitest avec timers fakes.

---

## Ecarts INFO

### [INFO] Doublon `_READ_CHUNK_SIZE` / `_UPLOAD_CHUNK_SIZE` (`64 * 1024`) — herite

- `document-parser/api/documents.py:19` et `document-parser/services/document_service.py:26`. Memes 64 KB, deux noms differents pour deux usages contigus (read upload puis flush disk). Inchange.
- Remediation : `services/constants.py::FILE_STREAM_CHUNK_SIZE`.

### [INFO] Placeholders URI hardcodes dans `StoreForm.vue` — herite

- `frontend/src/features/store/ui/StoreForm.vue:297-299` : `bolt://localhost:7687` / `http://localhost:9200`. Inchange. Aucun export `NEO4J_URI_PLACEHOLDER` / `OPENSEARCH_URI_PLACEHOLDER` dans `features/store/connectionForm.logic.ts`.
- Remediation : exporter les constantes depuis le `.logic.ts`.

### [INFO] Helpers Cytoscape dupliques `_element_node` / `_page_node` — herite

- `document-parser/infra/docling_graph.py:32-73` (`_element_node` / `_page_node` / `_edge`) vs `document-parser/infra/neo4j/queries.py:88-134` (`_element_node` / `_page_node` / `_chunk_node` / `_edge_id`). Inchange. Cles de sortie identiques cote contrat Cytoscape, entrees differentes (dict Docling vs row Neo4j).
- Remediation : extraire un constructeur partage `_cytoscape_element_node({...})` dans `infra/cytoscape_schema.py`.

### [INFO] Gating `BAKE_MODELS` quasi-identique entre `Dockerfile` racine et `document-parser/Dockerfile` (NOUVEAU dans 0.6.2-fix)

- **Localisation** :
  - `Dockerfile:72-111` (target `local`) — commentaire 8 lignes + `ARG BAKE_MODELS=false` + `ARG WITH_REASONING=false` + bloc `RUN if [ "$WITH_REASONING" = "true" ]; then ... ` + bloc `RUN if [ "$BAKE_MODELS" = "true" ]; then ... docling-tools models download ...`.
  - `document-parser/Dockerfile:47-87` (target `local`) — meme contenu mot pour mot, hors ordre `USER root`/`USER appuser` propre au backend-only et chemin `pyproject.toml` (vs `document-parser/pyproject.toml`).
  - Memes defauts `BAKE_MODELS=${BAKE_MODELS:-false}` et `BAKE_MODEL=${BAKE_MODEL:-false}` repetes dans `docker-compose.yml:142,81` et `docker-compose.dev.yml:119,76`.
- **Constat** : `f6b4e23` introduit la meme modification de gating en 16 lignes identiques sur les deux Dockerfiles (`git show --stat f6b4e23`). La coexistence des deux Dockerfiles est intentionnelle (single-image full-stack vs backend microservice). Aucun mecanisme natif Docker ne permet de factoriser un bloc cross-Dockerfile sans introduire un template/generator (sur-ingenierie pour 20 lignes). Le risque de drift est reel mais attrapable par les tests d'image en CI ; la doc `docs/architecture/huggingface-dependency-map.md` (ajoutee par le meme commit) centralise la rationale, ce qui mitige la dette de comprehension.
- **Severite** : INFO. La duplication concerne de l'infra de build (poids DRY faible — pas de logique metier), elle est documentee et tracee, et la factorisation aurait un cout disproportionne.
- **Remediation possible (non requise)** : si une troisieme variante apparait (par ex. un Dockerfile GPU local), basculer vers un `Dockerfile.local-stage.partial` inclus via `--build-context` ou un docker-bake.hcl partage. A re-evaluer au prochain cycle si la duplication s'etend ou si un drift est observe.

### Note sur la duplication compose `prod` / `dev` (statu quo non flag)

`docker-compose.yml` et `docker-compose.dev.yml` partagent ~150 lignes redondantes (neo4j, opensearch, embedding, document-parser, et maintenant docling-serve). Le baseline 05 a toujours considere cette duplication comme un pattern accepte (deux scenarios d'execution distincts, factorisation via `extends:` paie mal sa complexite). L'ajout `docling-serve` suit la meme convention ; le commentaire de tete dans la version dev pointe explicitement vers la version prod pour la rationale, donc seul le bloc declaratif est duplique, pas la documentation. **Non flag** comme nouveau ecart — l'INFO precedent couvre le nouveau bout de duplication infra dans la fenetre.

---

## Points positifs

- **Zero regression DRY backend code applicatif.** Le diff `release/0.6.2..f6b4e23` sur `document-parser/{api,services,domain,infra,persistence,main.py}` fait **0 ligne**. Les 5 ecarts baseline gardent strictement leur statut, aucun nouveau cas de duplication backend introduit.
- **Centralisation HTTP frontend intacte.** `grep 'fetch(' frontend/src` hors `http.ts` retourne 0 ligne — `shared/api/http.ts` reste le point unique. Item 5.5 conforme.
- **Nouvelle consolidation documentaire DRY-positive.** `docs/architecture/huggingface-dependency-map.md` (120 lignes) factorise la rationale HF Hub jusque-la eparpillee entre `README.md`, `CHANGELOG.md` et les commentaires inline des Dockerfiles. C'est exactement le mouvement DRY attendu cote knowledge management : un point de verite, des references depuis les sites consommateurs (les Dockerfiles citent la doc).
- **Le test modifie (`test_chunking.py`) substitue un `AsyncMock` au mock manuel `LocalChunker()`** — dans la mesure ou cela touche DRY, c'est une **reduction** de duplication test (suppression d'une implementation parallele de comportement, au profit du port abstrait `DocumentChunker` mocke directement). Plus aligne avec 5.6 (les schemas / mocks ne re-implementent pas le domain).
- **Verification mecanique a HEAD** : meme nombre de hits que le baseline pour les patterns DRY-risque (`grep table_mode|chunker_type`, `grep setInterval`, `grep fetch(`). Statu quo strict.

---

## Verdict partiel : **GO CONDITIONNEL**

**Justification** :
- Score 75/100 — identique au baseline `release-0.6.2/05-dry.md`, sous le seuil GO (80).
- 0 CRIT, 0 MAJ — les 2 MIN persistent sans nouveau MAJ/CRIT.
- 1 nouveau INFO (gating `BAKE_MODELS` duplique entre les deux Dockerfiles) **non bloquant** — l'analyse montre que la factorisation aurait un cout disproportionne (Dockerfile multi-file n'a pas de mecanisme natif de factorisation), et la doc HF dep map mitige la dette de comprehension.
- Les 3 INFO baseline sont strictement herites.
- Aucune resorption — la fenetre de fix ne touche aucun des 5 sites identifies.

**Delta vs baseline `release-0.6.2/05-dry.md`** :
- Score : **= 75** (statu quo strict).
- CRIT / MAJ / MIN : **= 0 / 0 / 2**.
- INFO : **+1** (gating BAKE_MODELS duplique sur les deux Dockerfiles, nouveau dans la fenetre de fix). Total INFO : **3 herites + 1 nouveau = 4**.
- Items conformes : **= 5/7** (ponderation 9/12).

**Conditions pour GO inconditionnel (prochain cycle)** — inchangees vs baseline + nouvelle obs :
1. Creer `document-parser/domain/constants.py` (`TABLE_MODES`, `CHUNKER_TYPES`, defauts) et migrer les 9 sites — leve le MIN 5.3.
2. Extraire `frontend/src/shared/composables/usePoller.ts` et migrer les 3 stores/pages — leve le MIN 5.4.

Optionnel (INFO) :
3. `FILE_STREAM_CHUNK_SIZE` centralise.
4. Placeholders URI dans `connectionForm.logic.ts`.
5. Schema Cytoscape partage `infra/cytoscape_schema.py`.
6. Surveiller la duplication du gating `BAKE_MODELS` entre Dockerfiles — basculer vers `docker-bake.hcl` ou `--build-context` si une 3eme variante apparait.

**DELTA_VS_INITIAL** : **+0** (score inchange).

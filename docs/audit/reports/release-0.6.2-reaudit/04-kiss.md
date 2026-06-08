# Rapport d'audit : KISS (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/04-kiss.md` — 92/100, GO (0/0/1/3)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 8 (somme des poids conformes 11 / 12) |
| Score | **92 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 3 |

### Detail par item

| # | Item | Poids | Statut | Delta vs baseline |
|---|------|-------|--------|-------------------|
| 4.1 | Pas de design pattern complexe | 2 | OK | = |
| 4.2 | Code resout le probleme actuel | 2 | OK | = |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | **KO** | = |
| 4.4 | Outils standard avant solutions maison | 1 | OK | = |
| 4.5 | Config simple | 1 | OK | = |
| 4.6 | Pas d'indirection inutile | 2 | OK (1 INFO frontend) | = |
| 4.7 | Pas de meta-programmation | 2 | OK | = |
| 4.8 | Structures de donnees simples | 1 | OK (2 INFO dataclass) | = |

**Calcul** (formule ponderee master.md §3) : poids conformes (2+2+1+1+2+2 = 10... item 4.3 KO=1 manque) = 11 / 12 × 100 = 91.67 → **92 / 100**. Identique a la baseline a l'arrondi pres.

---

## Contexte du re-audit

La fenetre `fix/0.6.2-audit-blockers` (8 commits depuis `051ac4a`) cible exclusivement les blockers CI/Securite/Docs identifies au tour 1. Aucun commit ne touche le code applicatif backend (`api/`, `services/`, `domain/`, `infra/`, `persistence/`, `main.py`).

`git diff release/0.6.2..HEAD -- document-parser/api/ document-parser/services/ document-parser/domain/ document-parser/infra/ document-parser/persistence/ document-parser/main.py` renvoie **zero ligne**.

Le perimetre KISS pertinent dans la fenetre :

| Element | Type | Impact KISS |
|---------|------|-------------|
| `dd1962e` — service `docling-serve` dans `docker-compose.yml` | Ops/compose, opt-in profil `remote` | Entree de 15 lignes (4.5 config simple) |
| `f6b4e23` — flip `BAKE_MODELS=true` → `false` dans `document-parser/Dockerfile:62` + `Dockerfile:103` + `embedding-service/Dockerfile` gate `BAKE_MODEL` | Build infra | 4.5 config simple (1 build-arg) |
| `f6b4e23` — `docs/architecture/huggingface-dependency-map.md` (120 lignes) | Doc | Hors perimetre KISS code (`document-parser/`, `frontend/src/`) |
| `f6b4e23` — `release.yml:66` ternaire `${{ matrix.target == 'local' && 'true' || 'false' }}` | CI | 4.5 config simple (1 ligne) |
| `29ab575` — `tests/test_chunking.py::test_rechunk_with_serve_document_json` : mock `AsyncMock` au lieu de `LocalChunker()` reel | Test only | Pas d'impact KISS (test, hors cible audit) |

---

## Verifications terrain

```bash
# 4.1 — patterns complexes (cible : document-parser/, hors .venv, __pycache__)
grep -rn "class.*Factory\|class.*Strategy\|class.*Observer\|class.*Builder\|class.*Singleton" \
  document-parser --include="*.py" --exclude-dir=.venv --exclude-dir=__pycache__
# → 1 hit : document-parser/tests/test_fernet_box.py:89 (`TestModuleSingleton`)
#   = test du comportement du singleton lazy FernetBox, pas un pattern de prod.

# 4.7 — meta-programmation
grep -rn "__metaclass__\|__init_subclass__\|__class_getitem__" \
  document-parser --include="*.py" --exclude-dir=.venv --exclude-dir=__pycache__
# → 0 hit

# 4.3 — wrappers triviaux ciblés (suivi spec, inchanges)
grep -n "_to_response\|_store_to_response\|_info_to_response\|_doc_entry_to_response" \
  document-parser/api/{documents,stores,analyses,document_versions}.py
# → 5 wrappers triviaux (memes localisations qu'en baseline)

# Backend non touche par fix/0.6.2-audit-blockers
git diff release/0.6.2..HEAD -- document-parser/api/ document-parser/services/ \
  document-parser/domain/ document-parser/infra/ document-parser/persistence/ \
  document-parser/main.py
# → 0 ligne
```

---

## Analyse des nouvelles surfaces (4.1, 4.2, 4.5, 4.6)

### Service `docling-serve` dans `docker-compose.yml` (dd1962e)

`docker-compose.yml:96-124` — 15 lignes, opt-in via le profil `remote` :

- Image officielle pinnee (`quay.io/docling-project/docling-serve-cpu:v1.21.0`) — pas de build custom, pas de Dockerfile maison, pas de wrapper script. **Standard `docker compose` + image upstream**.
- Pas d'override d'environnement, pas de healthcheck custom : un `curl -sf http://localhost:5001/version` reutilise le pattern deja en place pour `embedding` et `opensearch`.
- `profiles: ["remote"]` : meme mecanique deja appliquee aux profils `ingestion` (Neo4j, OpenSearch, embedding). Aucune nouvelle convention introduite.
- Conforme **4.4 (outils standard)** et **4.5 (config simple)** : aucune abstraction.

### Doc `huggingface-dependency-map.md` (f6b4e23)

Hors perimetre direct (cible KISS = `document-parser/` + `frontend/src/`), mais touche **4.2** (le code resout le probleme actuel — la doc accompagne le fix). Texte structure (table de touch points sanctionnes + table runtime + procedure de deploiement), zero artifact technique surdimensionne (pas de script generateur, pas de schema YAML, pas d'export Mermaid). **Pas de sur-ingenierie documentaire.**

### `release.yml:66` — ternaire `BAKE_MODELS` par matrice

```yaml
build-args: |
  APP_VERSION=${{ steps.version.outputs.value }}
  BAKE_MODELS=${{ matrix.target == 'local' && 'true' || 'false' }}
```

Question posee : ce ternaire est-il la maniere la plus simple d'exprimer "bake uniquement sur la cible local" ?

Alternatives evaluees :

| Approche | Cout | Simplicite |
|----------|------|------------|
| Ternaire actuel | 1 ligne | Idiome GitHub Actions canonique pour "valeur dependante d'un element de matrice". Lecture directe : "si la cible est local, alors true, sinon false". |
| `matrix.include` ajoutant `BAKE_MODELS` par ligne | +5 lignes minimum (declarer `include:` + 2 entrees explicites + maintenance dupliquee `target: remote` / `target: local`) | Plus verbeux, dupliquerait la liste des cibles |
| 2 steps `docker/build-push-action` avec `if: matrix.target == 'local'` | +20 lignes (duplication complete du step) | Duplication massive |
| Variable d'env workflow-level + override step-level | Complexe (matrix + env scoping) | Moins lisible |

Le ternaire est **conforme 4.5** : un seul build-arg, une seule ligne, evaluation pure cote GitHub Actions. C'est la forme la plus minimaliste. **Aucune sur-ingenierie introduite.**

### Verification que les flags `BAKE_MODELS` / `WITH_REASONING` restent des simples build-args

`document-parser/Dockerfile:55` et `:62` : `ARG BAKE_MODELS=false`, consomme uniquement par un `RUN` conditionne par `if [ "$BAKE_MODELS" = "true" ]`. Pas de couche d'abstraction Python, pas de helper script, pas de hook compose. Standard Docker. **Conforme 4.5.**

---

## Ecarts constates

### [MIN] Wrappers `_to_response` triviaux (herite 0.6.1 → 0.6.2 → fix)

- **Localisation** (inchangee depuis baseline 0.6.2) :
  - `document-parser/api/documents.py:29` — `_to_response`
  - `document-parser/api/stores.py:46` — `_store_to_response`
  - `document-parser/api/stores.py:64` — `_info_to_response`
  - `document-parser/api/stores.py:78` — `_doc_entry_to_response`
  - `document-parser/api/analyses.py:31` — `_to_response`
  - `document-parser/api/document_versions.py:38` — `_to_response` (semi-trivial avec `json.loads` defensif)
- **Constat** : Strictement inchange. Le diff `release/0.6.2..f6b4e23` ne touche aucun routeur API.
- **Regle violee** : 4.3 (poids 1).
- **Remediation** : reportable au prochain cycle — `model_config = ConfigDict(from_attributes=True)` + `model_validate` ou helper centralise dans `api/schemas.py`. Impact maintenabilite faible, surface circonscrite.

---

## Ecarts INFO (observations sans poids)

### [INFO] Accesseurs property redondants dans `DocumentService` (herite)

- **Localisation** : `document-parser/services/document_service.py:56-62`.
- **Constat** : Inchange. `max_file_size` / `max_file_size_mb` exposes en `@property`. Justifie pour les reponses 413 cote `api/documents.py`. Zone grise 4.3.

### [INFO] Petites dataclasses de config (herite)

- **Localisation** : `document_service.py:29-35`, `ingestion_service.py:33-38`, `graph_service.py:67-71`.
- **Constat** : Convention `@dataclass Config` inter-services (3 occurrences), inchangee. 4.8.

### [INFO] Polling analyse frontend `setInterval` + `setTimeout` (herite)

- **Localisation** : `frontend/src/features/analysis/store.ts:69-101`.
- **Constat** : Inchange. 4.6.

---

## Points positifs

- **Aucune regression KISS dans la fenetre de fix.** Le diff backend (`document-parser/api/`, `services/`, `domain/`, `infra/`, `persistence/`, `main.py`) vs `release/0.6.2` fait **0 ligne**. Tout le KISS du code applicatif est conserve a l'identique.
- **Le test modifie (`test_chunking.py:480`) simplifie le test plutot que de le complexifier** : remplacement de `LocalChunker()` (3 lignes implicites + dependance HF Hub) par un `AsyncMock` de 3 lignes au niveau du port `DocumentChunker`. C'est exactement le pattern le plus simple pour un test unitaire — pas de fixture custom, pas de stub class manuelle, juste `unittest.mock.AsyncMock` (stdlib, 4.4).
- **Le flip `BAKE_MODELS` default false** elimine un couplage implicite (chaque build touchait HF Hub par defaut) et simplifie le contrat : un seul build-arg explicite gouverne le bake, plus de surprise. Aligne avec 4.2 (resoudre le probleme actuel : couper la dependance HF Hub des builds CI).
- **Le service `docling-serve` ajoute 15 lignes opt-in** sans aucune abstraction custom (image upstream, healthcheck standard, profil compose existant). Pas de strategie/factory pour basculer local/remote — le backend a deja `CONVERSION_ENGINE=local|remote` cote `infra/`, le compose hisse simplement le service distant a portee de `--profile remote`.
- **Le ternaire `release.yml:66`** est l'idiome GitHub Actions canonique pour "valeur dependante de matrix", choisi correctement parmi 4 alternatives plus verbeuses.
- **La doc `huggingface-dependency-map.md`** est descriptive plate (tables + procedure), sans schema generateur ni manifest YAML. KISS doc-side.
- **Verification mecanique a HEAD `f6b4e23`** : 0 hit `Factory|Strategy|Observer|Builder|Singleton` (hors test `TestModuleSingleton`), 0 hit `__metaclass__|__init_subclass__|__class_getitem__`. Statu quo strict vs baseline.

---

## Verdict partiel : **GO**

**Justification** : Score 92/100 identique a la baseline `release-0.6.2/04-kiss.md`. Zero CRIT/MAJ, un seul MIN (4.3) strictement herite et signale depuis 0.6.0. Les 3 INFO sont strictement herites, sur les memes localisations.

**Delta vs baseline `release-0.6.2/04-kiss.md`** : items identiquement conformes/non-conformes (7/8 inchanges), memes 3 INFO. La fenetre de fix n'a touche aucun fichier KISS-evalue : 0 ligne sur `document-parser/api|services|domain|infra|persistence|main.py`, seul `tests/test_chunking.py` modifie (hors cible). Les nouvelles surfaces (service compose `docling-serve`, ternaire `release.yml`, doc HF dep map) sont minimalistes : chacune est la forme la plus directe pour son besoin, aucune abstraction superflue.

**Delta de fond** : 0 (statu quo strict).

**DELTA_VS_INITIAL** : +0.

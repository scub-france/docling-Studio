# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.6.2
**Branche** : `release/0.6.2` (HEAD `051ac4a`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**Baseline** : `f9e5619` — rapport `release-0.6.1-reaudit/04-kiss.md` (87.5 / 100 sous formule non pondérée, GO)

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 7 / 8 |
| Score | **92 / 100** |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 1 |
| Écarts INFO | 3 |

Détail du calcul (formule pondérée master.md §3) :

- Total poids = 12 (4.1=2, 4.2=2, 4.3=1, 4.4=1, 4.5=1, 4.6=2, 4.7=2, 4.8=1)
- Poids conformes = 11 (tout sauf 4.3)
- Poids non conformes = 1 (4.3=1)
- Score = 11 / 12 × 100 = **91.67 → 92 / 100**

**Note sur le delta** : le rapport `0.6.1-reaudit` reportait 87.5 / 100
en utilisant la formule non pondérée `items_OK / items_total` (7 / 8).
Ce rapport utilise la formule pondérée définie dans `master.md §3`,
cohérente avec les rapports `01-clean-architecture` et `03-clean-code`
de 0.6.2. À items identiquement conformes/non conformes, le score
calculé monte mécaniquement à 92 / 100. **Aucune régression de fond** :
exactement le même item (4.3) reste KO, classé MIN, sur le même
périmètre de wrappers triviaux.

### Détail par item

| # | Item | Poids | Statut | Delta vs 0.6.1-reaudit |
|---|------|-------|--------|------------------------|
| 4.1 | Pas de design pattern complexe | 2 | OK | = |
| 4.2 | Code résout le problème actuel | 2 | OK | = |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | **KO** | = (hérité, non corrigé) |
| 4.4 | Outils standard avant solutions maison | 1 | OK | = |
| 4.5 | Config simple | 1 | OK | = |
| 4.6 | Pas d'indirection inutile | 2 | OK (1 INFO frontend) | = |
| 4.7 | Pas de méta-programmation | 2 | OK | = |
| 4.8 | Structures de données simples | 1 | OK (2 INFO dataclass) | = |

---

## Vérifications terrain

```bash
# 4.1 — patterns complexes
grep -rn "class.*Factory\|class.*Strategy\|class.*Observer\|\
class.*Builder\|class.*Singleton" document-parser --include="*.py" \
  --exclude-dir=.venv --exclude-dir=__pycache__
# → 1 hit, document-parser/tests/test_fernet_box.py:89
#   `class TestModuleSingleton` = test de comportement du singleton
#   lazy du FernetBox. Pas un pattern Singleton dans le code de prod.

# 4.7 — méta-programmation
grep -rn "__metaclass__\|__init_subclass__\|__class_getitem__" \
  document-parser --include="*.py" --exclude-dir=.venv \
  --exclude-dir=__pycache__
# → 0 hit

# 4.3 — wrappers triviaux ciblés (suivi spec)
grep -n "_to_response\|_store_to_response\|_info_to_response\|\
_doc_entry_to_response" document-parser/api/{documents,stores,\
analyses,document_versions}.py
# → 5 wrappers triviaux toujours présents (cf. écart MIN ci-dessous)
```

---

## Écarts constatés

### [MIN] Wrappers `_to_response` triviaux (hérité 0.6.1, non corrigé)

- **Localisation** :
  - `document-parser/api/documents.py:29-40` — `_to_response`
  - `document-parser/api/stores.py:46-61` — `_store_to_response`
  - `document-parser/api/stores.py:64-75` — `_info_to_response`
  - `document-parser/api/stores.py:78-85` — `_doc_entry_to_response`
  - `document-parser/api/analyses.py:31-48` — `_to_response`
  - `document-parser/api/document_versions.py:38-53` — `_to_response`
    (avec micro-logique JSON parse pour `snapshot_size`, frontière du
    pattern "1:1 copie")
- **Constat** : Inchangé depuis le re-audit 0.6.1. Le périmètre des
  commits 0.6.2 (uv migration #254, dockerfile slim, fix `self_ref`
  `serve_converter`) n'a pas touché les routers API. Les 4 wrappers
  vraiment triviaux (`documents.py`, les trois de `stores.py`,
  `analyses.py`) restent une copie 1:1 d'attributs domaine vers leur
  équivalent Pydantic. Le wrapper de `document_versions.py:38-53` est
  semi-trivial (ajoute un `json.loads` défensif pour calculer
  `snapshot_size`), justifié.
- **Règle violée** : 4.3 — Pas de fonction wrapper qui ne fait qu'appeler
  une autre fonction sans valeur ajoutée (poids 1).
- **Remédiation** : voir rapport 0.6.1 — utiliser `model_validate` avec
  `model_config = ConfigDict(from_attributes=True)` sur les schemas
  Pydantic, OU centraliser dans `api/schemas.py` une fonction de mapping
  paramétrée. Reportable au prochain cycle (impact maintenabilité faible,
  périmètre bien circonscrit).

---

## Écarts INFO (observations sans poids)

### [INFO] Accesseurs property redondants dans `DocumentService` (hérité, inchangé)

- **Localisation** : `document-parser/services/document_service.py:56-62`
- **Constat** : `max_file_size` et `max_file_size_mb` exposés en
  `@property` alors qu'ils ne font que renvoyer `self._max_file_size` /
  `self._config.max_file_size_mb`. Inchangé depuis 0.6.1.
- **Règle visée** : 4.3 (zone grise — utilisé par `api/documents.py` pour
  surfacer la valeur dans les réponses 413, justification d'API publique
  encapsulée).

### [INFO] Petites dataclasses de config (hérité, inchangé)

- **Localisation** :
  - `document-parser/services/document_service.py:29-35`
    (`DocumentConfig`, 3 champs)
  - `document-parser/services/ingestion_service.py:33-38`
    (`IngestionConfig`, 2 champs)
  - `document-parser/services/graph_service.py:67-71`
    (`GraphServiceConfig`, 1 seul champ `max_pages`)
- **Constat** : Le pattern `@dataclass Config` est désormais une
  convention inter-services (3 occurrences). `GraphServiceConfig` à 1
  champ aurait pu rester un kwarg `__init__`, mais l'uniformité avec les
  deux autres configs et la justification documentée
  ("design §8.4 enforces") rendent le pattern acceptable. Inchangé vs
  0.6.1-reaudit.
- **Règle visée** : 4.8 — Structures de données les plus simples
  possibles. Garder le pattern explicitement comme convention de
  services/, ou refactor à `kwargs` dans un futur cycle KISS.

### [INFO] Polling analyse frontend avec `setInterval` + `setTimeout` (hérité, inchangé)

- **Localisation** : `frontend/src/features/analysis/store.ts:69-101`
- **Constat** : Implémentation manuelle d'un poller avec compteur
  `consecutiveErrors`, `pollingInterval` + `pollingTimeout`. Lisible mais
  pourrait s'appuyer sur un composable Vue ou une lib (`@vueuse/core`
  `useIntervalFn`). Hors périmètre des changements 0.6.2.
- **Règle visée** : 4.6 — Pas d'indirection inutile.

---

## Points positifs

- **Aucune régression KISS introduite par 0.6.2**. Les changements
  backend des commits depuis `f9e5619` sont :
  - `4d9bcf6` (migration uv) — purement build, aucun impact code.
  - `d1ed61e` (groupe de dépendances reasoning) — purement
    `pyproject.toml`.
  - `3936166` (`serve_converter`: carry `self_ref`) — ajout d'un champ à
    `PageElement` + propagation, 19 lignes, conforme KISS (aucune
    abstraction ajoutée).
  - `d29360d` (test architecture) — test only.
  - `#254` commits (Docker slim, model bake, .dockerignore) — infra.
- **Aucun design pattern complexe** dans le code de prod : grep zéro
  `Factory`/`Strategy`/`Observer`/`Builder`/`Singleton` côté
  `document-parser/`. Seul match (`tests/test_fernet_box.py:89`
  `TestModuleSingleton`) est un nom de classe de test, pas un pattern.
- **Aucune méta-programmation** : zéro `__metaclass__`,
  `__init_subclass__`, `__class_getitem__` côté prod.
- **Le port `Protocol` + adaptateurs thin-shim** introduits en 0.6.1
  pour `DocumentTreeReader`, `GraphReader`, `GraphWriter`,
  `DocumentGraphProjector` (cf. baseline 0.6.1-reaudit) restent
  inchangés et minimalistes en 0.6.2 — surface API minimale, un
  consommateur réel par port.
- **`graph_writer_factory`** injecté dans `StoreBackendResolver`
  (`services/store_backend_resolver.py:84,96`) reste un simple
  `Callable` (pas une classe `Factory`), inchangé et correctement
  scoped.
- **`FernetBox` (`infra/secrets/fernet_box.py`)** introduit en 0.6.1
  reste minimaliste : pas de rotation de clés, pas de KMS, pas de
  multi-key envelope — exactement le périmètre `STORE_SECRET_KEY` du
  cas d'usage actuel (#279). Conforme KISS.
- **Le nouveau `_to_response` dans `api/graph.py:64-73`** reste légitime
  (conversion `list[dict]` → `list[GraphNode]` via `GraphNode(**n)`), ne
  s'inscrit pas dans le pattern trivial signalé.

---

## Verdict partiel : **GO**

**Justification** : Score 92 / 100 sous formule pondérée master.md
(91.67 arrondi), zéro CRIT/MAJ, un seul MIN hérité de 0.6.0 et déjà
signalé en 0.6.1-reaudit (wrappers `_to_response` triviaux dans 4
routers API). Les 3 INFO sont tous hérités, inchangés, sans dégradation.

**Delta vs 0.6.1-reaudit** : à items identiquement conformes (7 / 8
identiques, même item 4.3 KO, mêmes 3 INFO sur les mêmes localisations),
le passage à la formule pondérée fait monter mécaniquement le score
de 87.5 à 92. Pas de régression KISS dans les commits 0.6.2 : les seuls
changements backend (`self_ref` carry, migration uv, slim docker) sont
chirurgicaux et n'introduisent aucune abstraction. Pas de nouveau pattern
Factory/Strategy/Observer, pas de méta-programmation.

**Delta de fond** : 0 (statu quo strict sur tous les items).

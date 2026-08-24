# Rapport d'audit : Clean Code

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 14 |
| Score | 61 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 4 |

**Detail du calcul** : somme des poids conformes = 11 (3.1.1=1, 3.1.2=1, 3.1.3=2, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur un total de 18 → `11 / 18 * 100 = 61`.

Perimetre audite : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`, au commit `6aaf98f` de `release/0.7.0`.

---

## Ecarts constates

### [MAJ] Fonctions d'orchestration qui font plusieurs choses (violation SRP)

- **Localisation** : `document-parser/services/chunk_service.py:574` (`push_to_store`), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`)
- **Constat** : plusieurs fonctions enchainent inline plusieurs responsabilites distinctes. `push_to_store` (117 lignes, 574-691) resout le slug→store, calcule le diff, execute le push, enregistre l'audit `ChunkPush` et fait l'upsert du lien `document_store_links` dans un seul corps. `write_document` (232 lignes, 69-310) construit et ecrit l'arbre complet du document en un bloc. `fetch_graph` (121 lignes, 137-263) assemble la requete, la projette et post-traite les aretes.
- **Regle violee** : item 3.2.1 — « Chaque fonction fait une seule chose (Single Responsibility) » (poids 2).
- **Remediation** : extraire des sous-fonctions nommees (`_resolve_store`, `_record_push`, `_upsert_link` pour `push_to_store` ; separation build/write pour `write_document`). Chaque etape doit etre une fonction testable isolement.

### [MAJ] Fichier fourre-tout : `chunk_service.py` melange trois concepts

- **Localisation** : `document-parser/services/chunk_service.py:146` (classe `ChunkService`), helpers de projection d'arbre `:885` (`_build_tree_nodes`), `:942` (`_build_item_subtree`), `:975` (`_make_node`), `:990` (`_display_label`), `:1015` (`_truncate`)
- **Constat** : un seul fichier de 1019 lignes porte (1) le service d'edition de chunks (CRUD, split, merge, rechunk), (2) la logique d'ingestion vers un store (`diff_against_store`, `push_to_store`, `list_pushes`, `_upsert_link_ingested`, `_mark_link_failed`), et (3) la projection d'affichage de l'arbre du document (`_build_tree_nodes`, `_build_item_subtree`, `_make_node`, `_display_label`, `_truncate`). Ces trois concepts appartiennent a des modules distincts.
- **Regle violee** : item 3.3.2 — « Un seul concept par fichier — pas de fichier fourre-tout » (poids 2).
- **Remediation** : sortir les helpers de projection d'arbre dans un module dedie (ex. `services/tree_projection.py`) et isoler la logique de push/diff vers un `ChunkStorePushService`. Le `ChunkService` ne doit garder que l'edition du chunkset.

### [MIN] Des fonctions depassent 30 lignes

- **Localisation** : `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 232 l.), `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 121 l.), `document-parser/services/chunk_service.py:574` (`push_to_store`, 117 l.), `document-parser/infra/neo4j/chunk_writer.py:55` (`write_chunks`, 108 l.), `document-parser/services/chunk_service.py:451` (`rechunk_document`, 85 l.) — ~48 fonctions au total au-dela du seuil.
- **Constat** : de nombreuses fonctions depassent nettement 30 lignes de corps, bien au-dela du boilerplate inevitable (mapping de settings, index-mapping du schema vectoriel).
- **Regle violee** : item 3.2.2 — « Aucune fonction ne depasse 30 lignes (hors boilerplate inevitable) » (poids 1).
- **Remediation** : decouper les plus longues (voir ecart 3.2.1) ; viser des corps < 30 lignes en extrayant les etapes.

### [MIN] Des fonctions ont plus de 4 parametres

- **Localisation** : `document-parser/services/chunk_service.py:149` (`ChunkService.__init__`, 12 params), `document-parser/services/store_service.py:236` (`update_store`, 10 params), `document-parser/services/store_service.py:185` (`create_store`, 9 params), `document-parser/services/store_backend_resolver.py:78` (8), `document-parser/services/analysis_service.py:82` (8), `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 7) — 20 fonctions au total.
- **Constat** : plusieurs signatures depassent 4 parametres. `create_store` / `update_store` prennent 9-10 champs en keyword-only (attenuation reelle mais toujours au-dela du seuil), et les constructeurs de services injectent jusqu'a 12 dependances.
- **Regle violee** : item 3.2.3 — « Aucune fonction n'a plus de 4 parametres » (poids 1).
- **Remediation** : regrouper les champs de `create_store`/`update_store` dans un DTO/value-object `StoreDraft`. Pour les constructeurs, envisager un objet de dependances ou la composition via le builder existant.

### [MIN] Fichiers sources au-dela de 300 lignes

- **Localisation** : `document-parser/services/chunk_service.py` (1019), `document-parser/api/schemas.py` (707), `document-parser/services/analysis_service.py` (553), `document-parser/domain/ports.py` (454) et 4 autres `.py` ; cote front `frontend/src/pages/StudioPage.vue` (1450), `frontend/src/features/chunking/ui/ChunkPanel.vue` (801), `frontend/src/pages/DocParseTab.vue` (782) et 21 autres.
- **Constat** : 8 fichiers Python (hors tests) et 24 fichiers front depassent 300 lignes. Nuance : plusieurs gros `.vue` le sont surtout a cause du bloc `<style scoped>` (ex. `StudioPage.vue` = 763 lignes de CSS, script de seulement 176 lignes) — le risque de maintenabilite du script y est faible.
- **Regle violee** : item 3.3.1 — « Aucun fichier source ne depasse 300 lignes » (poids 1).
- **Remediation** : prioriser le decoupage de `chunk_service.py` (voir 3.3.2). Cote front, extraire des sous-composants pour les pages > 700 lignes ; le CSS peut etre externalise mais reste secondaire.

### [INFO] Getters a memoisation paresseuse mutant un global de module

- **Localisation** : `document-parser/infra/opensearch_pool.py:131` (`get_pool`), `document-parser/infra/neo4j/driver_pool.py:161` (`get_pool`), `document-parser/infra/secrets/fernet_box.py:114` (`get_fernet_box`)
- **Constat** : ces `get_*` initialisent paresseusement un singleton (`global _pool ; if _pool is None: _pool = ...`), donc modifient un etat de module au premier appel.
- **Analyse** : item 3.2.5 juge CONFORME — l'effet est un cache idempotent, documente explicitement dans les docstrings (« built lazily »), et tous les getters retournant des donnees metier (`get_by_slug`, `get_analysis`, `get_document`, `get_tree`, `get_default`) sont des lectures pures. Le pattern singleton memoise n'est pas l'effet de bord cache vise par la regle.
- **Remediation** : aucune action requise ; garder les docstrings a jour. Optionnel : renommer en `pool()` / `ensure_pool()` si l'on veut lever toute ambiguite avec la convention `get_*`.

### [INFO] Argument-flag booleen `include_deleted`

- **Localisation** : `document-parser/persistence/chunk_repo.py:117`, `document-parser/domain/ports.py:157` (`find_for_document(..., include_deleted: bool = False)`)
- **Constat** : un booleen change ce que la requete renvoie (avec ou sans les chunks soft-deleted). C'est le seul flag-argument comportemental trouve ; les autres `bool` (`studio_mode_enabled`, `is_default`, `enabled`…) sont des champs de donnees, pas des flags.
- **Analyse** : item 3.2.4 juge CONFORME — idiome de repository tres repandu, portee etroite, defaut sur. Signale pour transparence.
- **Remediation** : optionnel — exposer deux methodes (`find_for_document` / `find_for_document_including_deleted`) si l'on veut eliminer le flag.

### [INFO] Parametres a une lettre dans les helpers de mapping

- **Localisation** : `document-parser/services/chunk_service.py:98` (`_chunk_to_audit_dict(c: Chunk)`), `:112` (`_bbox_from_dict(d: dict)`), `:116` (`_doc_item_from_dict(d: dict)`), `:851` (`_chunk_to_ingestion_dict(c: Chunk)`), `document-parser/persistence/chunk_repo.py:43` (`_chunk_to_params(c: Chunk)`)
- **Constat** : quelques helpers prives de 1-3 lignes utilisent `c` / `d` / `e` / `p` comme parametre.
- **Analyse** : items 3.1.2 / 3.1.4 jugees CONFORMES — l'annotation de type porte l'intention et la portee est minuscule. Le nommage global du code est excellent (verbes d'action, `remaining`, `sequence`, abbreviations etablies `dto`/`bbox`/`id`/`url`/`neo`).
- **Remediation** : cosmetique — renommer en `chunk` / `data` pour l'uniformite.

### [INFO] Constantes de configuration en valeur par defaut

- **Localisation** : `document-parser/services/analysis_service.py:88` (`conversion_timeout: int = 600`, `max_concurrent: int = _DEFAULT_MAX_CONCURRENT`)
- **Constat** : peu de magic numbers dans la logique metier ; les seuils sont soit nommes (`_DEFAULT_MAX_CONCURRENT`), soit des defauts de parametres explicites (`600`).
- **Analyse** : aucun risque ; observation positive plutot qu'ecart.
- **Remediation** : optionnel — extraire `600` dans une constante nommee `_DEFAULT_CONVERSION_TIMEOUT_S` pour l'homogeneite avec `max_concurrent`.

---

## Points positifs

- **Nommage** (3.1.1 / 3.1.4) : fonctions systematiquement verbales (`create_store`, `push_to_store`, `rechunk_document`, `split_chunk`, `merge_chunks`, `build_index_mapping`, `upload`) ; abbreviations limitees aux conventions etablies (`dto`, `bbox`, `id`, `url`, `neo`).
- **Langue** (3.1.3) : aucun texte francais dans le code source ; les traductions vivent bien dans `frontend/src/shared/i18n.ts`. Item de poids 2 pleinement conforme.
- **Imports** (3.3.3) : ordonnancement rigoureux et homogene sur tous les fichiers verifies — `from __future__`, stdlib, deps externes, puis imports internes (`domain` → `infra` → `persistence` → `services` → `api`).
- **Commentaires** (3.4.1) : commentaires orientes « pourquoi » exemplaires, referencant les issues et decisions de design (ex. `chunk_service.py:167` sur le port `DocumentTreeReader`, `feature-flags/store.ts` sur les flags de surface).
- **Dead code** (3.4.2) : aucun code commente laisse en place, ni cote Python ni cote frontend.
- **Getters metier** (3.2.5) : tous les `get_*` retournant des donnees du domaine sont des lectures pures, sans effet de bord.

---

## Verdict partiel : GO CONDITIONNEL

Score 61/100 (tranche 60-79), **0 ecart CRITICAL**, 2 ecarts MAJOR (sous le seuil bloquant de 3). Release autorisee sous condition d'un plan de remediation pour les deux MAJOR :

1. Decouper `chunk_service.py` en concepts distincts (edition de chunks / push vers store / projection d'arbre) — items 3.3.2 et 3.2.1.
2. Extraire les sous-etapes des fonctions d'orchestration longues (`push_to_store`, `write_document`, `fetch_graph`) — item 3.2.1.

Les MINOR (taille de fonctions/fichiers, nombre de parametres) sont a traiter au prochain cycle, en priorisant le decoupage de `chunk_service.py` qui adresse simultanement 3.2.1, 3.2.2, 3.2.3, 3.3.1 et 3.3.2.

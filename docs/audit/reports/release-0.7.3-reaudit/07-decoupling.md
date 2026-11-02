# Rapport de re-audit : Découplage

> **Re-audit de `release/0.7.3` @ `e01fd95` — score 89 → 94**

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Type** : re-audit après remédiation
**Référence** : rapport initial `release-0.7.3/07-decoupling.md` (`02adc68`, 89/100, GO, 0 CRIT, 2 MAJ)
**Remédiation examinée** : `git log 02adc68..e01fd95` (merge de la PR #367). Commit pertinent pour cet audit :
`8465931 refactor(frontend): move ConfigSource to shared/types (#audit-07)`.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 15 / 16 |
| Score | 94 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 0 |
| Écarts INFO | 12 |

Détail du calcul : somme des poids = 35 ; seul l'item **7.4.2** (poids 2) reste non
conforme. Poids conformes = 33. `33 / 35 * 100 = 94,29` → **94**.

### Périmètre de la remédiation

Sur les 36 fichiers modifiés entre `02adc68` et `e01fd95`, seuls 5 touchent le
périmètre de la fiche (`document-parser/` hors tests et dépendances, `frontend/src/`) :

| Fichier | Nature | Effet sur l'audit 07 |
|---------|--------|----------------------|
| `frontend/src/shared/types.ts` | + `ConfigSource` (l.1-5) | correctif 7.2.3 |
| `frontend/src/features/admin-config/types.ts` | import depuis `@/shared/types` | correctif 7.2.3 |
| `frontend/src/features/admin-config/index.ts` | retrait de la réexportation | correctif 7.2.3 |
| `frontend/src/features/mcp-config/types.ts` | import depuis `@/shared/types` | correctif 7.2.3 |
| `document-parser/services/analysis_service.py` | `deserialize` via `asyncio.to_thread` (#audit-12) | neutre (l'appel passe toujours par le port) |

Les autres changements de code (`infra/settings.py` : commentaire ;
`mcp_adapter/citation_app.html` : `lang="fr"` ; `pyproject.toml`, `uv.lock`,
`package*.json`, Dockerfiles : versions) sont sans effet sur le découplage. Aucun
fichier de `api/`, `domain/`, `persistence/`, `bootstrap/`, `main.py`,
`frontend/src/pages/`, `frontend/src/app/`, `frontend/src/shared/ui/` ni
`frontend/eslint.config.js` n'a changé : l'analyse initiale des items qui en
dépendent est reprise, avec citations revérifiées sur l'arbre courant.

### Mesures (analyse statique du working tree)

| Mesure | Initial (`02adc68`) | Re-audit (`e01fd95`) |
|--------|---------------------|----------------------|
| Imports feature → feature (hors tests) | 14, tous via barrel | **13, tous via barrel** (arête `mcp-config → admin-config` supprimée) |
| Imports profonds feature → internes d'une autre feature | 0 | 0 |
| `node_modules/.bin/eslint src` | 0 erreur (exit 0) | **0 erreur (exit 0)** |
| `node_modules/.bin/vue-tsc --noEmit` | — | **exit 0** (le retrait de la réexportation ne casse aucun consommateur) |
| Types définis dans une feature et consommés par une autre feature | 1 (`ConfigSource`) | **0** |
| `shared/` → internes de features | 2 (`AppSidebar.vue`) | 2 (inchangé) |
| Imports profonds `pages/` + `app/` → internes de features | 58 | inchangé (0 fichier modifié ; 52 par le script du re-audit, **même valeur** sur `02adc68`, l'écart avec 58 tient à la méthode de comptage) |
| `from docling` / `import docling` dans `services/` | 0 | 0 |
| `fastapi` / `starlette` dans `services/` ou `domain/` | 0 | 0 |
| Champs `dict` / `extra="allow"` dans un schéma de **réponse** | 2 | 2 (inchangé) |

Commandes de la fiche rejouées : 7.3.2 (`grep "from docling|import docling" services/`)
→ vide ; 7.4.2 (`grep "-> dict|-> Any|Dict[str, Any]" api/`) → vide (l'écart 7.4.2 est au
niveau *champ*, cf. ci-dessous) ; 7.2.4 → seul consommateur inter-store hors tests
`reasoning/store.ts:3,22`, qui n'appelle que l'action `focusElement`
(`reasoning/store.ts:51,55`) ; 7.2.2 complété par un scan exhaustif des imports `@/` et
relatifs de `frontend/src/` (hors tests), rejoué à l'identique sur une extraction
`git archive 02adc68` pour le différentiel.

---

## Vérification de la remédiation

| Item | Poids | Statut initial | Statut re-audit | Preuve (arbre `e01fd95`) |
|------|-------|----------------|-----------------|--------------------------|
| 7.1.1 REST-only front/back | 3 | Conforme | Conforme (=) | Client HTTP unique `frontend/src/shared/api/http.ts:5` (`apiFetch`), appelé par les `api.ts` de features (ex. `features/mcp-config/api.ts:1,17`) ; aucun fichier partagé ni import croisé front/back introduit. |
| 7.1.2 Types TS = schémas Pydantic | 3 | Conforme | Conforme (=, renforcé) | `ConfigSource` front (`frontend/src/shared/types.ts:5`, `'env' \| 'db'`) reflète désormais au même niveau partagé le littéral backend `document-parser/domain/app_config.py:17` (`Literal["env", "db"]`), publié par `api/schemas.py:679-682` et `:754`. |
| 7.1.3 Front mockable (`api.ts` par feature) | 2 | Conforme | Conforme (=) | 11 fichiers `frontend/src/features/*/api.ts`, dont `mcp-config/api.ts:17` ; inchangés. |
| 7.1.4 Back testable sans front | 2 | Conforme | Conforme (=) | `document-parser/tests/test_mcp_config_api.py:11,75` (`TestClient`) ; + test ajouté par la remédiation `tests/test_analysis_service.py` (#audit-12). |
| 7.1.5 Pas de logique métier dupliquée | 2 | Conforme | Conforme (=) | Garde UX `frontend/src/features/document/store.ts:75-77` et bornes MCP `features/mcp-config/types.ts:58-62` inchangées (INFO reconduits). |
| 7.2.1 Feature = store + api + ui | 2 | Conforme | Conforme (=) | `mcp-config/` et `admin-config/` gardent `api.ts`, `store.ts`, `types.ts`, `ui/`, `index.ts` ; `mcp-config/index.ts:1-2`. |
| 7.2.2 Frontière barrel + ESLint | 3 | Conforme | Conforme (=) | Règle `frontend/eslint.config.js:28-55` inchangée ; 13 imports feature → feature, tous vers un barrel (ex. `settings/ui/SettingsPanel.vue:112-114`, `document/ui/DocumentUpload.vue:49`) ; 0 import profond ; `eslint src` exit 0. |
| **7.2.3 Types partagés dans `shared/types.ts`** | 2 | **Non conforme [MAJ]** | **Conforme — RÉSOLU** | Définition `frontend/src/shared/types.ts:5` ; consommateurs `features/admin-config/types.ts:1` et `features/mcp-config/types.ts:1` importent `@/shared/types` ; réexportation retirée (`features/admin-config/index.ts:1-2`) ; plus aucune occurrence de `ConfigSource` dans une feature hors import (`grep -rn ConfigSource frontend/src`). |
| 7.2.4 Store n'accède pas au state d'un autre store | 2 | Conforme | Conforme (=) | `features/reasoning/store.ts:51,55` (action `focusElement`), `features/admin-config/store.ts:80,95` (action `reload`) ; fichiers inchangés. |
| 7.3.1 Repos → objets du domaine | 2 | Conforme | Conforme (=) | ex. `document-parser/persistence/document_repo.py:99,104` (`-> Document \| None`, `_row_to_document`) ; `persistence/` inchangé. |
| 7.3.2 Pas de types `docling.*` dans les services | 3 | Conforme | Conforme (=) | Commande fiche vide ; `docling_core` confiné à `infra/docling_importer.py:7` ; le changement #audit-12 garde l'appel sur le port : `services/analysis_service.py:180` (`asyncio.to_thread(self._docling_importer.deserialize, document)`). |
| 7.3.3 Changement de DB confiné à `persistence/` | 2 | Conforme | Conforme (=) | Aucun SQL ni `aiosqlite` hors `persistence/` ; annotations `Sqlite*Repository` sous `TYPE_CHECKING` (`services/store_service.py:23-25`) reconduites en INFO. |
| 7.3.4 Changement HTTP confiné à `api/` + `main.py` | 2 | Conforme | Conforme (=) | 0 fichier `fastapi`/`starlette` dans `services/` et `domain/` ; couplage localisé `bootstrap/mcp_mount.py:41-42,118` (INFO reconduit). |
| 7.4.1 Ports = signatures claires, types domaine | 2 | Conforme | Conforme (=) | `domain/ports.py:86` (`DoclingDocumentImporter`), `:423` (`PageRasterizer`), `:449` (`PageTextReader`) ; inchangé. |
| 7.4.2 Pas de `dict`/`Any` dans les responses | 2 | Non conforme [MAJ] | **Non conforme [MAJ]** (=) | `document-parser/api/schemas.py:334,349` (`StoreResponse.config: dict`), `api/graph.py:32` (`extra="allow"`) ; non traité, hors périmètre de la remédiation (ingestion dépréciée). |
| 7.4.3 Format de réponse cohérent | 1 | Conforme | Conforme (=) | `{"detail": ...}` uniforme (ex. `api/analyses.py:84-85`), erreurs typées `services/config_overrides.py:25` ; inchangé. |

### [MAJ] 7.2.3 — `ConfigSource` dans une feature : **RÉSOLU**

Vérifié sur le code :

1. **Définition déplacée** — `export type ConfigSource = 'env' | 'db'` vit en
   `frontend/src/shared/types.ts:5`, avec un commentaire (`:1-4`) nommant ses deux
   consommateurs. `shared/types.ts` reste une feuille (aucun `import`).
2. **Consommateurs rebranchés** — `frontend/src/features/admin-config/types.ts:1` et
   `frontend/src/features/mcp-config/types.ts:1` importent `@/shared/types` ; les usages
   `admin-config/types.ts:18` et `mcp-config/types.ts:12` sont inchangés.
3. **Barrel nettoyé** — `frontend/src/features/admin-config/index.ts` n'exporte plus que
   `useAdminConfigStore` (`:1`) et `ReasoningConfigSection` (`:2`).
4. **Dépendance parasite supprimée** — `mcp-config` ne référence plus `admin-config`
   nulle part (`grep admin-config src/features/mcp-config` vide) ; le seul consommateur
   des deux barrels reste `settings/ui/SettingsPanel.vue:113-114`.
5. **Pas de régression** — `eslint src` exit 0, `vue-tsc --noEmit` exit 0, aucun
   nouvel import croisé (13 vs 14). Les seuls types de feature réexportés ailleurs
   (`AnalysisOutcome`, `BatchLaunch`, `features/analysis/index.ts:2`) ne sont consommés
   que par des pages (`pages/DocWorkspacePage.logic.ts:9`, `pages/DocsLibraryPage.vue:276`),
   hors du champ « entre features » de 7.2.3.

**Conclusion : item 7.2.3 conforme**, le MAJ est levé. Le front s'aligne sur le backend,
où le même concept est déjà mutualisé (`domain/app_config.py:17`, importé par
`domain/mcp_config.py:25`).

### [MAJ] 7.4.2 — non traité (attendu)

Aucune modification de `api/schemas.py` ni `api/graph.py` dans `02adc68..e01fd95`.
Écart conservé à l'identique, cf. ci-dessous.

---

## Écarts restants

### [MAJ] `dict` non typé et modèle ouvert dans des schémas de réponse (item 7.4.2) — inchangé

- **Localisation** : `document-parser/api/schemas.py:349` (`StoreResponse.config: dict`,
  classe en `:334`) ; `document-parser/api/graph.py:32` (`model_config = {"extra": "allow"}`).
  Miroirs front : `frontend/src/features/store/api.ts:23` (`Record<string, unknown>`),
  `frontend/src/features/analysis/graphApi.ts:36` (`[key: string]: unknown`).
- **Constat** : identique au rapport initial. Contrat opaque des deux côtés sur le config
  store polymorphe (neo4j / opensearch) et sur les nœuds de graphe. Les deux surfaces
  appartiennent au périmètre ingestion, déprécié et supprimé en 0.8.0.
- **Règle violée** : 7.4.2 (poids 2).
- **Remédiation** : solder par la suppression de l'ingestion en 0.8.0 (à acter dans le
  plan 0.8.0), ou typer (union discriminée par `kind`, attributs cytoscape explicites) si
  l'ingestion est conservée.

### [INFO] Constats reconduits sans changement

Aucun des 12 INFO du rapport initial n'était dans le périmètre de la remédiation ; tous
restent valides. Analyse et remédiation détaillées : `release-0.7.3/07-decoupling.md`.
Localisations revérifiées sur `e01fd95` (seules celles de `shared/types.ts` ont bougé,
+6 lignes du fait de l'ajout de `ConfigSource`).

| # | Constat | Localisation vérifiée | Évolution |
|---|---------|-----------------------|-----------|
| 1 | `shared/ui` n'est pas une feuille : `AppSidebar.vue` importe deux stores de features et est réexporté par le barrel consommé par `mcp-config` et `settings` | `frontend/src/shared/ui/AppSidebar.vue:55-56`, `shared/ui/index.ts:1`, `features/mcp-config/ui/McpConfigSection.vue:376`, `features/settings/ui/SettingsPanel.vue:115` | = (à traiter avant 0.8.0, qui supprime `ingestion/store`) |
| 2 | Cycle de barrels `document` ↔ `analysis` (et `document` ↔ `chunks`) | `features/document/ui/DocumentUpload.vue:49`, `document/ui/DocumentActionsMenu.vue:41`, `document/store.ts:5-6` ; sens inverse `analysis/ui/AnalysisPanel.vue:61`, `analysis/ui/StructureViewer.vue:64` | = |
| 3 | Pages et shell importent en profondeur les internes de features (hors 7.2.2) | ex. `frontend/src/app/App.vue:52,54`, `app/router/index.ts:3` ; `pages/` non modifié | = (décompte identique aux deux commits) |
| 4 | Bornes MCP et règle d'hôte recopiées côté front, non publiées dans l'OpenAPI | `features/mcp-config/types.ts:58-62` vs `domain/mcp_config.py:29-35` ; `features/mcp-config/client.ts:41-46` ; `api/schemas.py:803-815` (sans `Field(ge, le)`, contrairement à `:691-695`) | = |
| 5 | Code HTTP dérivé du texte d'une exception (import d'analyse) | `api/analyses.py:84` ; `services/analysis_service.py:173` (`ValueError`), `:176` (`RuntimeError` non mappé) ; `DocumentNotFoundError` dispo en `services/navigation_errors.py:24` | = (le changement #audit-12 en `:177-180` n'y touche pas) |
| 6 | Contrat d'URL implicite backend → SPA (deep links MCP), non testé | `services/citation_service.py:292` ; `frontend/src/app/router/routes.ts:39-48` | = |
| 7 | Couplage framework HTTP étendu à `bootstrap/mcp_mount.py` ; façade MCP typée `Any` | `bootstrap/mcp_mount.py:41-42,118` ; `mcp_adapter/__init__.py:22` ; `infra/rate_limiter.py:18-19` | = |
| 8 | Deux casses pour la notion de page ; DTO wire anonyme | `features/document/api.ts:37-47` ; `shared/types.ts:145-150` (`Page`, ex `:139-144`) ; `api/schemas.py:119` | = (ligne décalée) |
| 9 | Champ de contrat orphelin `Document.stores?` | `frontend/src/shared/types.ts:45` (ex `:39`) | = (ligne décalée) |
| 10 | Pré-validation de taille de fichier côté front (garde UX) | `features/document/store.ts:75-77` | = |
| 11 | Règle ESLint plus étroite que « barrel uniquement » (ne couvre ni `shared/`, ni `pages/`, ni les chemins à deux segments) | `frontend/eslint.config.js:28-55` | = ; voir complément ci-dessous |
| 12 | Services annotés avec des repos SQLite concrets (sous `TYPE_CHECKING`) | `services/store_service.py:23-25,148-150`, `services/chunk_service.py:43-44`, `services/version_service.py:32`, `services/store_backend_resolver.py:43` ; Protocols `domain/ports.py:128,142` | = |

**Complément à l'INFO 11.** 7.2.3 vient de régresser puis d'être corrigé pour la
deuxième fois (`RechunkOptions` en 0.7.0, `ConfigSource` en 0.7.3), à chaque fois via
une réexportation `export type` dans un barrel de feature. Aucun garde-fou ne le
détecte : l'import passe par le barrel, donc la règle `no-restricted-imports` l'accepte.
Durcissement possible : dans `src/features/**`, interdire les imports *de type* depuis
`@/features/*` (`no-restricted-syntax` sur `ImportDeclaration[importKind='type']` et
`ImportSpecifier[importKind='type']` dont la source commence par `@/features/`), ce qui
forcerait tout type inter-features à passer par `@/shared/types`. À ce commit, la règle
ne lèverait aucune erreur (0 import de type inter-features).

### Nouveaux écarts

Aucun. La remédiation ne crée ni import croisé, ni dépendance `shared/` → feature, ni
type de bibliothèque dans un service, ni nouveau schéma de réponse non typé.

---

## Points positifs

- **Correctif minimal et complet.** Quatre fichiers, types uniquement, aucune
  modification d'exécution ; la réexportation devenue inutile est retirée plutôt que
  conservée « par compatibilité », et `vue-tsc` confirme qu'aucun consommateur n'en
  dépendait.
- **Graphe de features allégé.** L'arête `mcp-config → admin-config` disparaît : les
  deux sections de configuration sont désormais des features sœurs indépendantes,
  composées uniquement par `settings`.
- **Symétrie front/back.** `ConfigSource` est partagé au même niveau des deux côtés
  (`shared/types.ts:5` / `domain/app_config.py:17`), ce qui rend la correspondance
  7.1.2 lisible.
- **Remédiation transverse sans effet de bord sur le découplage.** Le passage de
  l'import Docling en thread (#audit-12) conserve l'appel derrière le port
  `DoclingDocumentImporter` ; aucun autre changement de la PR #367 ne touche les
  frontières.

---

## Verdict partiel : GO

Score de compliance **94/100**, en hausse de **89 → 94** (retour au niveau du re-audit
0.7.0). Le **[MAJ] 7.2.3** est levé et vérifié sur `e01fd95` (`ConfigSource` dans
`shared/types.ts:5`, consommateurs rebranchés, barrel nettoyé, ESLint et `vue-tsc`
propres). Il reste **0 CRIT**, **1 MAJ** (7.4.2, dette ingestion reportée, sous le seuil
master de > 3) et **12 INFO** non bloquants, tous reconduits.

Suivi (non bloquant) :
1. [MAJ] 7.4.2 — à solder avec la suppression de l'ingestion en 0.8.0.
2. Avant 0.8.0 : sortir `AppSidebar.vue` de `shared/ui` (INFO 1) et étendre la règle
   ESLint à `src/shared/**`, plus le garde-fou « types inter-features » (INFO 11).

# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`,
avec un examen approfondi du delta depuis 0.7.3 (`1de1929..eade7fa`) : editeur d'analyse
durable (#319 / #388 : flux de commandes, cache materialise, `DoclingDocumentEditor`,
`DoclingAnalysisProjector`, routes `/api/documents/{id}/analysis-editor|analysis-edits/*`,
feature front `analysis-editor/`), selection d'analyse active et provenance des chunks
(`document_analysis_state`), upgrade de base 0.7.3 → 0.7.4 (#391), ordre de fusion (#392),
chunks de provenance inconnue (#393), flag `ANALYSIS_EDITOR_ENABLED`, retrait de l'audit
trail `ChunkEdit`.
Methode : analyse statique uniquement (application non lancee, suites de tests non executees,
aucun lint ni build).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 8 |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 9 |

Poids total de la checklist : 12. Poids conformes : 9 (items 4.2, poids 2, et 4.5, poids 1,
non conformes). `score = 9 / 12 * 100 = 75`.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui (cf. INFO flux de commandes) |
| 4.2 | Resout le probleme actuel, pas hypothetique futur | 2 | **Non** |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui (cf. INFO) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (cf. INFO) |
| 4.5 | Configuration simple | 1 | **Non** |
| 4.6 | Pas d'indirection inutile | 2 | Oui (cf. INFO) |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui (cf. INFO introspection Docling) |
| 4.8 | Structures de donnees les plus simples | 1 | Oui (cf. INFO) |

### Metriques de perimetre

| Mesure | 0.7.3 | 0.7.4 |
|--------|-------|-------|
| Variables d'environnement booleennes parsees en ligne dans `Settings.from_env` | 8 | **9** (+ `ANALYSIS_EDITOR_ENABLED`, `infra/settings.py:279-280`) |
| Code backend de l'editeur (8 fichiers nouveaux) | — | 1 709 lignes |
| Feature frontend `analysis-editor` (hors tests) | — | 1 912 lignes |
| Types de commandes d'edition | — | 7 (`domain/analysis_editing.py:13-21`) |
| Routes HTTP ajoutees | — | 6 (`api/analysis_edits.py`) + parametre `edited` sur l'export |
| Tables SQLite ajoutees | — | 4 (`document_analysis_state`, `analysis_edit_streams`, `analysis_edit_commands`, `edited_analysis_cache`) + 2 triggers |
| Colonnes du cache `edited_analysis_cache` jamais relues | — | **5 / 10** (voir MIN 4.2) |
| Protocoles de deplacement acceptes par `moveElement` | — | 2 (un seul emis par l'UI) |
| Resultats des greps de la fiche (4.1 / 4.7) | `AppStateBuilder` seul / 1 `setattr` trivial | `AppStateBuilder` seul / `getattr` + `inspect.signature` sur l'API privee Docling (`infra/docling_editor.py:318-324`) |

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable) — reconduit de 0.7.0, inchange

- **Localisation** : `document-parser/domain/value_objects.py:153` (`LLMProviderType`, membre unique `OLLAMA` `:163`), `document-parser/domain/ports.py:379` (`LLMProvider`), `document-parser/infra/docling_agent_reasoning.py:138` (garde `NotImplementedError`), `document-parser/bootstrap/factories.py:103` (second garde par chaine), `document-parser/infra/settings.py:55` et `:234` (`LLM_PROVIDER_TYPE`)
- **Constat** : strictement inchange depuis 0.7.0 (seuls les numeros de ligne ont bouge apres le retrait de `ChunkEditAction` dans `value_objects.py`). Enum a un membre, tag `type` sur le port consomme par un seul garde, knob d'env, double garde factory + runner, champ « Provider: ollama » remonte jusqu'au panneau d'admin. C'est la **troisieme release consecutive** ou la dette est reportee.
- **Regle violee** : item 4.2 — « Le code resout le probleme actuel, pas un probleme hypothetique futur (pas de genericite prematuree) » (poids 2).
- **Remediation** : inchangee — assumer Ollama en dur (supprimer l'enum, le tag `type`, `LLM_PROVIDER_TYPE`, le double garde et `providerType` du panneau) ou ne garder que le port `LLMProvider` sans dispatch. Effort S. Ne fait pas a lui seul repasser l'item 4.2 conforme (voir MIN editeur ci-dessous).

---

### [MIN] Editeur d'analyse : plomberie pour des besoins non exprimes, colonnes et champs ecrits mais jamais lus (nouveau)

- **Localisation** :
  - cache : `document-parser/persistence/database.py:258-269` (table `edited_analysis_cache`), `document-parser/persistence/analysis_edit_repo.py:63-92` (ecriture des 10 colonnes), `document-parser/services/analysis_edit_service.py:86-98` (seule lecture) et `document-parser/infra/docling_projector.py:83-98` (`project_serialized`) ;
  - `warnings` : `document-parser/infra/docling_editor.py:30` (defaut `()`, jamais renseigne : `:74`), `document-parser/domain/analysis_editing.py:90`, `document-parser/api/schemas.py` (`AnalysisEditorResponse.warnings`), `frontend/src/features/analysis-editor/types.ts:55` ;
  - `referenceChanges` : calcule `document-parser/infra/docling_editor.py:63-74`, transporte jusqu'a `frontend/src/features/analysis-editor/types.ts:56`, lu nulle part dans `frontend/src` ;
  - `engine_version` : ecrit `document-parser/services/analysis_edit_service.py:35`, `:154`, jamais compare ; `previous_hash` ecrit `persistence/analysis_edit_repo.py:190`, jamais relu ;
  - reconstruction : route `document-parser/api/analysis_edits.py:208-217`, service `services/analysis_edit_service.py:248-269`, client `frontend/src/features/analysis-editor/api.ts:72` sans aucun appelant ;
  - second protocole de deplacement : `document-parser/infra/docling_editor.py:295-313` (`beforeElementId`), `document-parser/api/schemas.py` (`MoveElementEditRequest.before_element_id`), `frontend/src/features/analysis-editor/types.ts:15`, alors que l'UI n'emet que `targetElementId` + `placement` (`frontend/src/features/analysis-editor/store.ts:202`).
- **Constat** : le coeur de l'editeur (flux append-only + projection) repond a un besoin reel (historique, annulation d'une edition sauvegardee, base immuable). Mais autour, plusieurs elements servent un usage futur ou absent :
  - le cache stocke `content_markdown`, `content_html`, `pages_json`, `result_hash` et `updated_at` que **rien ne relit** : sur un cache valide, `load_editor` appelle `project_serialized`, qui revalide le document et **refait toute la projection** (Markdown, HTML, pages, modele). Le cache n'economise que le rejeu des commandes ; 5 colonnes sur 10 sont du poids mort a chaque sauvegarde ;
  - `warnings` est un canal de bout en bout (adaptateur → domaine → DTO → type TS) qui ne transporte jamais rien ; `referenceChanges` est calcule a chaque projection et envoye au client, qui l'ignore ;
  - `engine_version` et `previous_hash` sont persistes sans lecteur (aucune migration de moteur ni verification de chaine n'existe) ;
  - l'endpoint de reconstruction et son client n'ont pas d'entree dans l'UI ;
  - deux protocoles de deplacement coexistent pour la meme commande v1 ; le format `beforeElementId` est celui du design (`docs/design/analysis-editor.md:135`) mais n'est plus produit.
- **Regle violee** : item 4.2 (poids 2, deja non conforme par le MAJ ci-dessus). Classe MIN : rien n'est sur un chemin d'erreur, le cout est du code et du stockage en trop, pas un risque.
- **Remediation** : soit faire servir le cache (retourner `content_*`/`pages_json` stockes au lieu de reprojeter), soit retirer ces colonnes ; retirer `warnings` et `referenceChanges` du contrat tant qu'aucun consommateur n'existe ; documenter `engine_version`/`previous_hash` comme reserves ou les retirer ; brancher « Rebuild » dans l'UI ou retirer route + client ; si aucun flux v1 `beforeElementId` n'a ete persiste avant 0.7.4 (la feature est nouvelle), retirer ce chemin. Effort M.

### [MIN] Configuration MCP en couches (reconduit de 0.7.3, inchange) — +1 flag d'env

- **Localisation** : `document-parser/infra/settings.py:90-122` et `:259-278`, `document-parser/bootstrap/factories.py:240`, `document-parser/domain/mcp_config.py:41`, `document-parser/services/mcp_config_service.py:76` et `:100`, `document-parser/services/navigation_config.py:25` et `:64`, `document-parser/bootstrap/mcp_mount.py:98-101`, `document-parser/mcp_stdio.py:63-78` ; nouveau : `document-parser/infra/settings.py:124-126`, `:279-280`, `document-parser/api/state.py` (`analysis_editor_enabled`), `document-parser/api/deps.py` (`get_analysis_edit_service`), `document-parser/api/documents.py:147-148`, `frontend/src/features/feature-flags/store.ts:111-113`
- **Constat** : aucun des fichiers de config MCP n'a change depuis 0.7.3 : trois representations pour quatre knobs, `max_rounds` « live » mais non applique et fige dans les instructions HTTP, deux validations divergentes de `MCP_MAX_READ_TOKENS`, stdio qui ignore `enabled`, `ASK_MODE` a deux valeurs texte. La 0.7.4 ajoute un flag simple, `ANALYSIS_EDITOR_ENABLED` (booleen, par defaut `true`), copie dans `AppState` et expose au front : c'est la bonne forme pour un flag de deploiement. Sa garde est toutefois repartie en trois endroits (dependance FastAPI, route d'export, store front) et le flag ne couvre pas les effets durables : `ChunkService` et `ExportService` appliquent les editions sauvegardees via `active_result` meme flag eteint (`bootstrap/builder.py`, `active_result_service=analysis_edit_service`). Comportement defendable (les editions sont durables) mais non documente dans `docs/configuration.md`.
- **Regle violee** : item 4.5 — « Configuration simple — pas de systeme de config complexe la ou une variable d'env suffit » (poids 1).
- **Remediation** : inchangee pour le MCP (une seule source des bornes et defauts dans `domain/mcp_config.py`, `max_rounds` en env seul, stdio respecte `enabled`, `ASK_MODE` → booleen). Pour l'editeur : documenter que le flag masque l'edition, pas l'application des editions deja sauvegardees ; utiliser un helper `_env_bool` (cf. audit 05).

### [MIN] Carte de citation conservee mais desactivee par defaut (reconduit de 0.7.3, inchange)

- **Localisation** : `document-parser/infra/settings.py:119` et `:274`, `document-parser/mcp_adapter/apps.py:141-142` et `:146-228`, `document-parser/mcp_adapter/citation_app.html` (1 177 lignes), `document-parser/services/citation_service.py:57`
- **Constat** : inchange (`mcp_adapter/` intact depuis 0.7.3). Fonctionnalite couverte par `show_sources`, gardee « au cas ou » derriere `MCP_CITATION_CARD=false`.
- **Regle violee** : item 4.2 (deja compte).
- **Remediation** : inchangee — retirer la carte ou statuer explicitement dans le design #363.

---

### [INFO] Flux de commandes event-sourced avec chaine de hash (4.1 juge conforme)

- **Localisation** : `document-parser/persistence/database.py:233-269`, `document-parser/persistence/analysis_edit_repo.py:138-219`, `document-parser/services/analysis_edit_service.py:360-378`, `document-parser/domain/analysis_editing.py:119-145`
- **Constat** : l'editeur stocke l'intention (commandes append-only, `setCommandActive` pour revert/reapply) et rematerialise le resultat. C'est plus lourd qu'un « sauver le document edite », mais c'est ce qui permet l'annulation d'une edition sauvegardee au milieu de l'historique et garde la base immuable : le besoin est exprime (design `docs/design/analysis-editor.md`) et l'implementation reste lineaire (pas de bus, pas de projection asynchrone). La chaine `previous_hash → command_hash` et `UNIQUE(analysis_id, command_hash)` ajoutent une integrite de type registre pour une base SQLite locale mono-utilisateur ; la validite du cache pourrait reposer sur `applied_through_sequence` seul puisque le flux est append-only. Non bloquant.
- **Regle violee** : item 4.1 — observation.
- **Remediation** : aucune obligatoire ; si la chaine est conservee, centraliser son calcul (aujourd'hui en deux copies, cf. audit 05).

### [INFO] Introspection d'une API privee Docling (4.7 juge conforme)

- **Localisation** : `document-parser/infra/docling_editor.py:315-329` (`getattr(document, "_move_subtree")` + `inspect.signature(move).bind(...)`)
- **Constat** : `docling_core` n'expose pas de deplacement de sous-arbre public ; l'adaptateur appelle la methode privee apres avoir verifie sa signature, et echoue proprement sinon. C'est de la magie, mais justifiee, isolee dans un seul adaptateur et commentee (`:311-312`, `:317`). Le risque est la montee de version de `docling-core` (contrat prive), pas la complexite.
- **Regle violee** : item 4.7 — observation.
- **Remediation** : un test de contrat sur la version epinglee de `docling-core` (deja partiellement couvert par l'echec explicite) ; demander une API publique en amont.

### [INFO] Aller-retours JSON et double representation de l'arbre dans le projecteur (4.8 juge conforme)

- **Localisation** : `document-parser/infra/docling_projector.py:60-76` (modele construit en dict puis `json.dumps`), `document-parser/api/analysis_edits.py:60` (`json.loads` du meme modele a chaque reponse), `document-parser/infra/docling_projector.py:205-255` (`_tree` : arbre `node()` recursif, puis dicts `{"node", "children"}`, puis `freeze`)
- **Constat** : le modele d'editeur est serialise en chaine pour le cache, puis deserialise en processus pour chaque reponse HTTP, meme quand il vient d'etre calcule. `_tree` construit trois representations successives du meme arbre. Correct, mais plus de structures que necessaire.
- **Remediation** : garder le modele en objet dans `ProjectedAnalysis` et ne serialiser qu'a la persistance ; construire directement les `EditorTreeNode` dans la pile de titres.

### [INFO] Chemins de repli jamais pris en production (4.6 juge conforme)

- **Localisation** : `document-parser/services/export_service.py:40` (`active_result_service=None`), `:78-81`, `:96-99` ; `document-parser/services/chunk_service.py:376-385`, `:712-719`
- **Constat** : `ExportService` et `ChunkService` gardent une branche « pas de service d'editeur → derniere analyse terminee », alors que `bootstrap/builder.py` injecte toujours `analysis_edit_service`. Cette branche n'est atteinte que par les tests. Le chemin reel (route → service → `active_result` → `load_editor` → editeur → projecteur) reste dans les couches attendues, mais le rechunk et l'export reprojettent tout le document (Markdown + HTML + pages) pour n'en lire que `document_json` ou `content_markdown`.
- **Remediation** : rendre `active_result_service` obligatoire et supprimer la branche de repli ; exposer un `load_document_json(doc_id)` qui s'arrete au rejeu.

### [INFO] Pont MCP Apps ecrit a la main et present en deux copies (reconduit, inchange)

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:690-770`, `document-parser/mcp_adapter/sources_app.html:984-1060`
- **Constat** : inchange depuis 0.7.3.
- **Regle violee** : item 4.4 — observation (recoupe l'audit 05).
- **Remediation** : inchangee.

### [INFO] Aides mortes et relais sans valeur ajoutee (reconduit, inchange)

- **Localisation** : `document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`, `document-parser/mcp_adapter/server.py:90`, `document-parser/mcp_adapter/prompts.py:52`, `document-parser/services/mcp_config_service.py:100`, `document-parser/services/app_config_service.py:144`
- **Constat** : inchange. Rien de comparable dans l'editeur : `_require_document`/`_base_analysis` portent une regle, `_replay` (`analysis_edit_service.py:294-296`) est le seul relais trivial (2 lignes, 2 appelants).
- **Regle violee** : item 4.3 — observation.
- **Remediation** : inchangee (supprimer `_neutralise_all` ×2 et `INSTRUCTIONS`).

### [INFO] `PageRasterizer.crop(box, fmt)` : generalite residuelle (reconduit, inchange)

- **Localisation** : `document-parser/services/citation_image_service.py:91` (boite sentinelle `(0, 0, 10_000, 10_000)`)
- **Remediation** : inchangee (`encode_webp(png)`).

### [INFO] Repli d'environnement de developpement dans le chemin de production (reconduit, inchange)

- **Localisation** : `document-parser/services/document_service.py:119`
- **Remediation** : inchangee.

### [INFO] `ReasoningStepKind` a 7 valeurs, `StepId` `RootModel[str]`, `LLMProvider.health_check()` mort (reconduits de 0.7.0, inchanges)

- **Localisation** : `document-parser/domain/value_objects.py:193`, `document-parser/api/schemas.py:656`, `document-parser/domain/ports.py:404`
- **Constat** : inchanges (lignes decalees).
- **Regle violee** : item 4.2 (deja compte) — observations.
- **Remediation** : inchangees.

---

## Delta vs 0.7.3

Score : **75 → 75 (0)**. Items conformes : 6/8 → 6/8. Les deux items non conformes (4.2 et
4.5) l'etaient deja ; l'editeur ajoute des instances a 4.2 sans faire basculer d'autre item.

| Ecart 0.7.3 | Statut 0.7.4 | Detail |
|-------------|--------------|--------|
| [MAJ] Abstraction LLM-provider prematuree | **Toujours ouvert, inchange** | 3e report consecutif ; `value_objects.py:153` (etait `:167`) |
| [MIN] Configuration MCP en couches (4.5) | **Toujours ouvert, inchange** | + `ANALYSIS_EDITOR_ENABLED` (simple, mais garde repartie et portee non documentee) |
| [MIN] Carte de citation desactivee conservee (4.2) | **Toujours ouvert, inchange** | `mcp_adapter/` intact |
| [INFO] Pont MCP Apps en deux copies | Inchange | |
| [INFO] Aides mortes / relais | Inchange | |
| [INFO] `crop` residuel | Inchange | |
| [INFO] Repli de chemin de dev | Inchange | |
| [INFO] `ReasoningStepKind`, `StepId`, `health_check` | Inchanges | |

Nouveaux ecarts 0.7.4 : [MIN] plomberie speculative de l'editeur (4.2), et 4 INFO (flux
event-sourced avec chaine de hash, introspection Docling, aller-retours JSON, replis jamais
pris).

---

## Points positifs

- **Dispatch sans pattern** (4.1) : `DoclingDocumentEditor._apply_one` (`infra/docling_editor.py:107-134`) et `_commands` (`api/analysis_edits.py:86-107`) sont des `if/elif` par type de commande ; pas de registre de handlers, pas de classe par commande.
- **Outils standard reutilises** (4.4) : `DoclingDocument.validate_tree` / `validate_document` et l'aller-retour `model_validate_json` pour valider un document edite (`docling_editor.py:53-61`) ; `DoclingDocument.concatenate` pour la fusion des lots (`infra/docling_merger.py:26`) ; `delete_items` / `replace_item` de Docling pour les mutations ; `BEGIN IMMEDIATE` SQLite pour la concurrence d'ecriture (`analysis_edit_repo.py:151`) plutot qu'un verrou applicatif ; `sessionStorage` pour le brouillon.
- **Logique front pure et petite** : `features/analysis-editor/commands.ts` (82 l.) — repli des frappes, ordre de lecture, validation de fusion — sans Vue ni timers.
- **Reutilisation du viewer existant** : l'editeur passe par `PagePreviewWithOverlay` / `BboxCanvas` (props `readingOrderByRef`, `selectedRef`, `nextRef`) au lieu d'un second viewer.
- **Upgrade de base minimal** (#391) : `_upgrade_from_0_7_3` (`persistence/database.py:314-330`) — une table de 2 colonnes a ajouter et un `INSERT … SELECT` idempotent, pas de reintroduction d'un moteur de migrations.
- **Simplification active** : retrait de l'audit trail `ChunkEdit` jamais lu (modele, enum, table, repository, ecritures dans `version_service.restore`) ; `chunk_service.py` −84 lignes.
- **Flag de deploiement simple** : `ANALYSIS_EDITOR_ENABLED` est un booleen d'env, sans surcharge en base ni panneau.
- **Zero nouvelle meta-programmation** hors l'introspection documentee de `_move_subtree`.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL. Un seul ecart MAJOR (abstraction LLM-provider, reconduit sans
changement depuis 0.7.0, troisieme report), sous le seuil bloquant (> 3). Score 75 / 100 (60-79).
Conditions : planifier enfin le MAJ reconduit (0.8.0) ; pour repasser 4.2 conforme il faut
a la fois ce MAJ, la carte de citation et la plomberie speculative de l'editeur (cache
non relu, `warnings`, `referenceChanges`, `rebuild` sans UI, second protocole de
deplacement) ; 4.5 reste tenu par la config MCP.
